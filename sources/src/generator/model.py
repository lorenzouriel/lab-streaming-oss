"""Yearly state of the generative model: the fitted calibration (2013-2015) extended to later years.

Later years evolve from the previous one with a per-year seeded step, so year Y never depends on how
far the model is extended past Y.
"""
from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import numpy as np

DATA_DIR = Path(__file__).resolve().parent / "data"

_TAG_YEAR = 1   # spawn_key tags keep the random streams for different purposes apart


def rng_for(seed: int, *spawn_key: int) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy=seed, spawn_key=spawn_key)))


def load_config(path: Path | None = None) -> dict[str, Any]:
    with open(path or DATA_DIR / "config.toml", "rb") as fh:
        return tomllib.load(fh)


class Model:
    def __init__(self, cfg: dict[str, Any], last_year: int, calibration: Path = DATA_DIR / "calibration.json"):
        cal = json.loads(calibration.read_text(encoding="utf-8"))
        self.cfg = cfg
        self.seed = int(cfg["seed"])
        self.clients: list[str] = cal["clients"]
        self.products: list[str] = cal["products"]
        self.factories: list[str] = cal["factories"]
        self.client_org: list[str] = cal["client_org"]
        self.product_litres = np.array(cal["product_litres"])
        keys = cal["keys"]
        self.key_client = np.array(keys["client"])
        self.key_product = np.array(keys["product"])
        self.key_factory = np.array(keys["factory"])
        self.key_logq = np.array(keys["log_qty"])
        self.n_keys = len(self.key_client)
        self.season = np.array(cal["season"])
        self.price_sigma = float(cal["price_sigma"])
        self.client_price_effect = np.array(cal["client_price_effect"])

        # yearly tables, indexed by calendar year
        self.year_level = {y: float(cal["year_level"][str(y)]) for y in cal["anchor_years"]}
        self.base_price = {y: np.array(cal["base_price"][str(y)]) for y in cal["anchor_years"]}  # [product]
        self.unit_cost = {y: np.array(cal["unit_cost"][str(y)]) for y in cal["anchor_years"]}    # [factory, product]
        self.tax_rate = {y: np.array(cal["tax_rate"][str(y)]) for y in cal["anchor_years"]}      # [client, product]

        last = cal["anchor_years"][-1]
        growth = float(np.exp(self.year_level[last] - self.year_level[last - 1]) - 1)
        latent_cost = self.unit_cost[last].copy()
        for y in range(last + 1, last_year + 1):
            growth, latent_cost = self._extend(y, growth, latent_cost)

    def _extend(self, y: int, prev_growth: float, latent_cost: np.ndarray) -> tuple[float, np.ndarray]:
        vol, prc = self.cfg["volume"], self.cfg["prices"]
        rng = rng_for(self.seed, _TAG_YEAR, y)

        growth = vol["terminal_growth"] + (prev_growth - vol["terminal_growth"]) * vol["growth_decay"]
        self.year_level[y] = self.year_level[y - 1] + np.log1p(growth) + rng.normal(0.0, vol["shock_sigma"])

        prev = self.base_price[y - 1]
        price = prev * np.exp(rng.normal(np.log1p(prc["inflation"]), prc["price_sigma"], prev.shape))
        self.base_price[y] = price

        latent_cost = latent_cost * np.exp(rng.normal(np.log1p(prc["cost_inflation"]), prc["cost_sigma"],
                                                      latent_cost.shape))
        cap = np.maximum(1.0, np.floor(prc["cost_cap_ratio"] * price))[None, :]
        self.unit_cost[y] = np.minimum(np.maximum(1.0, np.rint(latent_cost)), cap)

        tax_step = 1.0 + prc["tax_drift"] + rng.normal(0.0, prc["tax_sigma"])
        self.tax_rate[y] = np.minimum(self.tax_rate[y - 1] * tax_step, prc["tax_cap"])
        return growth, latent_cost
