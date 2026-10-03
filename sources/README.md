# sources

The CDC source for this lab. It was trimmed down from [`lab-sources`](../../lab-sources) to the streaming path only. It does two things:

- Loads the Fruit Juice dimension tables into Postgres.
- Writes synthetic sales events into `fruit_juice.stream_sales`, one order per row. Debezium captures that table.

```bash
uv sync
uv run generator dims                                   # schema + 6 dims (idempotent)
uv run generator stream --sink postgresql --rate 10      # 10 events/s until Ctrl+C
uv run generator stream --count 5 --as-of 2026-01-01    # JSON Lines to stdout
uv run pytest
```

| Flag | Meaning |
|---|---|
| `--sink` | `stdout` (default) or `postgresql` |
| `--rate` | Events per simulated second (Poisson; `--no-jitter` for a fixed interval) |
| `--count` / `--duration` | Stop after N events / N wall-clock seconds |
| `--as-of` | Simulated start date: sets the event timestamps, the model year and the seasonality (default: now) |
| `--speed` | Simulated-time multiplier |
| `--start-seq` | First event number. Resumes a stopped stream with no gap or overlap |
| `--seed` | Overrides `seed` in `data/config.toml` |

**Reproducible.** For a given seed and `--as-of` date, event *N* always has the same content and `event_id` (`uuid5(seed:seq)`). Only `event_time` depends on when it was produced. The Postgres sink is idempotent: a re-sent `event_id` is a no-op. Because of the primary key, duplicates can never reach CDC through this table. The pipeline gets its duplicates from redelivery instead.

**Connection.** Settings come from `POSTGRES_HOST/PORT/USER/PASSWORD/DATABASE`, read from the environment first, then from the repo-root `.env`. If neither has them, the defaults are `127.0.0.1:5432`, user `postgres`, password `postgres`, database `postgres`.

## Layout

```
src/generator/
  model.py        fitted calibration (2013-2015) extended year by year with seeded steps
  stream.py       EventGenerator (event N = pure function of seed, as-of, N) and pacing
  postgres.py     schema, dimension load, idempotent stream_sales sink
  cli.py          `generator dims` / `generator stream`
  data/           config.toml, calibration.json, schema.sql, dims/*.csv (57 clients, 35 products, ...)
```

## Differences from lab-sources

- **Removed:**
  - batch generation, `fit`, `validate` and `export-original`
  - the file writers: csv, parquet, json, mongodb, and the SQL scripts
  - the `load` command, and the `file`, `sqlserver`, `mongodb` and `kafka` sinks
  - `dim_tempo` and the fact tables
  - the calibration fields used only by the batch facts
  - the pyarrow dependency
- **Fixed:** seasonality used to come from the wall-clock month, so the content of event *N* changed from month to month. It now comes from `--as-of`.
- **Unchanged:** for the same seed and month, the first 5,000 events are byte-identical to `lab-sources`.
- **Added:** dimension tables now have primary keys, which Debezium needs to key change events. They have no foreign keys.
