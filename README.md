# lab-streaming-oss

Streaming and event-driven pipeline on a fully **open-source, local** stack, replaying the Fruit Juice sales data from [`lab-sources`](../lab-sources) as an event stream. This is the reference implementation the cloud streaming labs mirror.

## Stack

| Layer | Tooling |
|---|---|
| Broker | Redpanda or Apache Kafka (KRaft), Schema Registry |
| CDC | Debezium (PostgreSQL → Kafka) via Kafka Connect |
| Stream processing | Apache Flink (SQL / PyFlink) or Spark Structured Streaming |
| Sinks | Apache Iceberg on MinIO (history), ClickHouse |
| Observability | Kafka UI / Redpanda Console, Prometheus, Grafana |
| Runtime | Docker Compose |
| CI/CD | GitHub Actions, pre-commit, integration tests with testcontainers |

## Architecture

Replay producer (and Debezium CDC from PostgreSQL) → Kafka topics → Flink jobs (dedup, enrichment joins with dimensions, windowed KPIs, late-data handling via watermarks) → Iceberg (lakehouse) and ClickHouse (serving) → Grafana dashboard.

Patterns covered: Lambda vs Kappa, exactly-once sinks, dead-letter topics, schema evolution, replay and backfill.

## CI/CD plan

- PR: lint, spin up the compose stack in CI, replay a small sample, assert on sink contents.
- Merge: build and publish images, tag release. Optional stretch: Kubernetes with Strimzi and the Flink operator.

## Status

Scaffold only. Depends on the replay producer planned for `lab-sources` (`generator replay`). Planned contents: `docker-compose.yml`, `flink/`, `connectors/`, `producer/`, `tests/`, `.github/workflows/`.

## Prerequisites

Docker Desktop, about 8 GB RAM free, Python 3.11+, `uv`.
