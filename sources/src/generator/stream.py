"""Synthetic sales events, one order each, drawn from the fitted model.

Reproducible: for a given seed and as-of date, event N always has the same content regardless of the rate
it was produced at or where a previous run stopped (`--start-seq` resumes exactly). Only `event_time` varies.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterator

import numpy as np

from .model import Model, rng_for

_TAG_STREAM = 3
# A key's modelled daily volume is split into about this many orders, so one event is not a whole day's quantity.
_ORDERS_PER_DAY = 6.0


@dataclass(frozen=True)
class StreamEvent:
    event_id: str
    seq: int
    event_time: datetime          # UTC
    cod_dia: str
    cod_cliente: str
    cod_produto: str
    cod_fabrica: str
    cod_organizacional: str
    faturamento: float
    imposto: float
    custo_variavel: float
    unidades: float
    quantidade_vendida: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_time"] = self.event_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return d


class EventGenerator:
    """`event(n)` depends only on the seed, the as-of date and `n`, never on call order or timing."""

    def __init__(self, model: Model, as_of: date):
        if as_of.year not in model.year_level:
            raise ValueError(f"model was not extended to {as_of.year}")
        m, y = model, as_of.year
        self.model = m
        weight = np.exp(m.key_logq)
        self._key_p = weight / weight.sum()
        self._price = m.base_price[y][m.key_product] * np.exp(m.client_price_effect[m.key_client])
        self._tax_rate = m.tax_rate[y][m.key_client, m.key_product]
        self._unit_cost = m.unit_cost[y][m.key_factory, m.key_product]
        self._daily_qty_mean = np.exp(m.key_logq + m.season[as_of.month - 1])

    def event(self, seq: int, event_time: datetime) -> StreamEvent:
        m = self.model
        rng = rng_for(m.seed, _TAG_STREAM, seq)
        key = rng.choice(m.n_keys, p=self._key_p)
        client, product, factory = int(m.key_client[key]), int(m.key_product[key]), int(m.key_factory[key])

        qty = max(0.5, round(float(self._daily_qty_mean[key] / _ORDERS_PER_DAY
                                   * (0.4 + rng.gamma(1.0 / _ORDERS_PER_DAY))), 2))
        price = float(self._price[key]) * float(np.exp(rng.normal(0.0, m.price_sigma)))
        revenue = round(qty * price, 2)
        return StreamEvent(
            event_id=str(uuid.uuid5(uuid.NAMESPACE_OID, f"{m.seed}:{seq}")), seq=seq,
            event_time=event_time, cod_dia=event_time.strftime("%Y%m%d"),
            cod_cliente=m.clients[client], cod_produto=m.products[product],
            cod_fabrica=m.factories[factory], cod_organizacional=m.client_org[client],
            faturamento=revenue, imposto=round(revenue * float(self._tax_rate[key]), 2),
            custo_variavel=round(qty * float(self._unit_cost[key]), 2),
            unidades=max(1.0, round(qty / float(m.product_litres[product]))), quantidade_vendida=qty,
        )


def iter_events(generator: EventGenerator, rate: float, *, start_time: datetime, start_seq: int = 0,
                count: int | None = None, duration: float | None = None, speed: float = 1.0, jitter: bool = True,
                sleep: Callable[[float], None] = time.sleep) -> Iterator[StreamEvent]:
    """Events at `rate` per simulated second (Poisson by default); simulated time runs `speed`x the wall clock."""
    pace = np.random.default_rng()   # pacing only; never affects content
    t0 = time.monotonic()
    seq = start_seq
    while count is None or seq - start_seq < count:
        elapsed = time.monotonic() - t0
        if duration is not None and elapsed >= duration:
            return
        yield generator.event(seq, start_time + timedelta(seconds=elapsed * speed))
        seq += 1
        interval = 1.0 / (rate * speed)
        sleep(pace.exponential(interval) if jitter else interval)
