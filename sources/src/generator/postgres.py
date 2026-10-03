"""Postgres side: schema, dimension load and the stream_sales sink.

Connection comes from POSTGRES_* in the environment, then the repo-root `.env`, then lab defaults.
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

from .model import DATA_DIR
from .stream import StreamEvent

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"   # <repo>/sources/src/generator -> <repo>/.env
DIMS = ["dim_categoria", "dim_marca", "dim_produto", "dim_cliente", "dim_fabrica", "dim_organizacional"]
_DEFAULTS = {"HOST": "127.0.0.1", "PORT": "5432", "USER": "postgres", "PASSWORD": "postgres", "DATABASE": "postgres"}


def _dotenv() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    pairs = (line.split("=", 1) for line in ENV_FILE.read_text(encoding="utf-8").splitlines()
             if "=" in line and not line.lstrip().startswith("#"))
    return {k.strip(): v.strip().strip("\"'") for k, v in pairs}


def connect():
    import psycopg
    file_env = _dotenv()
    c = {k: os.environ.get(f"POSTGRES_{k}", file_env.get(f"POSTGRES_{k}", v)) for k, v in _DEFAULTS.items()}
    conn = psycopg.connect(host=c["HOST"], port=c["PORT"], user=c["USER"], password=c["PASSWORD"],
                           dbname=c["DATABASE"], autocommit=True)
    conn.execute((DATA_DIR / "schema.sql").read_text(encoding="utf-8"))
    return conn


def load_dims(conn) -> dict[str, int]:
    """Insert the fixed dimension universe; existing keys are left alone, so re-running is a no-op."""
    counts = {}
    for name in DIMS:
        with open(DATA_DIR / "dims" / f"{name}.csv", encoding="utf-8", newline="") as fh:
            header, *rows = list(csv.reader(fh))
        cols = ", ".join(h.lower() for h in header)
        marks = ", ".join(["%s"] * len(header))
        with conn.cursor() as cur:
            cur.executemany(f"INSERT INTO fruit_juice.{name} ({cols}) VALUES ({marks}) ON CONFLICT DO NOTHING",
                            [[v or None for v in row] for row in rows])
        counts[name] = conn.execute(f"SELECT count(*) FROM fruit_juice.{name}").fetchone()[0]
    return counts


class PostgresSink:
    """Idempotent: re-sending an already-seen event_id is a no-op."""

    _SQL = ("INSERT INTO fruit_juice.stream_sales VALUES (%(event_id)s, %(seq)s, %(event_time)s, %(cod_dia)s, "
            "%(cod_cliente)s, %(cod_produto)s, %(cod_fabrica)s, %(cod_organizacional)s, %(faturamento)s, "
            "%(imposto)s, %(custo_variavel)s, %(unidades)s, %(quantidade_vendida)s) ON CONFLICT (event_id) DO NOTHING")

    def __init__(self):
        self._conn = connect()

    def write(self, event: StreamEvent) -> None:
        self._conn.execute(self._SQL, event.to_dict())

    def close(self) -> None:
        self._conn.close()
