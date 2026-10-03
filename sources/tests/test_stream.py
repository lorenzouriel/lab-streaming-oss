"""EventGenerator and pacing (no database needed)."""
import json
import time
from datetime import date, datetime, timezone

import pytest

from generator.cli import main
from generator.model import Model, load_config
from generator.stream import EventGenerator, iter_events

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(scope="session")
def generator():
    return EventGenerator(Model(load_config(), last_year=2026), date(2026, 1, 1))


def test_event_is_pure_function_of_seq(generator):
    assert generator.event(123, T0) == generator.event(123, T0)
    assert generator.event(123, T0) != generator.event(124, T0)


def test_event_content_ignores_the_timestamp(generator):
    e1, e2 = generator.event(5, T0), generator.event(5, T0.replace(hour=9, minute=30))
    assert e1.cod_cliente == e2.cod_cliente and e1.faturamento == e2.faturamento
    assert e1.event_time != e2.event_time


def test_content_does_not_depend_on_the_wall_clock_month():
    model = Model(load_config(), last_year=2026)
    jan, jul = EventGenerator(model, date(2026, 1, 15)), EventGenerator(model, date(2026, 7, 15))
    assert EventGenerator(model, date(2026, 1, 15)).event(7, T0) == jan.event(7, T0)
    assert jan.event(7, T0).quantidade_vendida != jul.event(7, T0).quantidade_vendida   # seasonality from as-of


def test_values_are_sane(generator):
    for seq in range(200):
        e = generator.event(seq, T0)
        assert e.faturamento > 0 and e.imposto >= 0 and e.custo_variavel >= 0
        assert e.quantidade_vendida > 0 and e.unidades >= 1
        assert e.cod_cliente and e.cod_produto and e.cod_fabrica and e.cod_organizacional
        assert e.cod_dia == "20260101"


def test_covers_the_key_universe(generator):
    seen = {(e.cod_cliente, e.cod_produto, e.cod_fabrica) for e in (generator.event(s, T0) for s in range(3000))}
    assert len(seen) > 500


def test_codes_exist_in_the_dimension_files(generator):
    from generator.model import DATA_DIR
    def first_col(name):
        return {line.split(",", 1)[0] for line in (DATA_DIR / "dims" / f"{name}.csv").read_text("utf-8").splitlines()[1:]}
    clients, products, factories, orgs = (first_col(n) for n in
                                          ("dim_cliente", "dim_produto", "dim_fabrica", "dim_organizacional"))
    for e in (generator.event(s, T0) for s in range(1000)):
        assert e.cod_cliente in clients and e.cod_produto in products
        assert e.cod_fabrica in factories and e.cod_organizacional in orgs


def test_rate_and_jitter_never_change_content(generator):
    fast = list(iter_events(generator, rate=500, count=10, start_time=T0))
    slow = list(iter_events(generator, rate=500, count=10, start_time=T0, jitter=False))
    assert [e.seq for e in fast] == list(range(10))
    assert [(e.cod_cliente, e.faturamento) for e in fast] == [(e.cod_cliente, e.faturamento) for e in slow]


def test_start_seq_resumes_exactly(generator):
    whole = list(iter_events(generator, rate=1000, count=6, start_time=T0))
    resumed = list(iter_events(generator, rate=1000, count=3, start_seq=3, start_time=T0))
    assert [(e.cod_cliente, e.faturamento) for e in resumed] == [(e.cod_cliente, e.faturamento) for e in whole[3:]]


def test_duration_stops_on_time(generator):
    t0 = time.monotonic()
    assert list(iter_events(generator, rate=20, duration=0.3, start_time=T0))
    assert time.monotonic() - t0 < 1.0


def test_cli_stdout_writes_json_lines(capsys):
    assert main(["stream", "--count", "3", "--rate", "1000", "--as-of", "2026-01-01"]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [r["seq"] for r in rows] == [0, 1, 2]
    assert all(r["event_time"].endswith("Z") for r in rows)
