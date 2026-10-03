"""`generator dims` loads the dimensions into Postgres; `generator stream` emits sales events."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone

from .model import Model, load_config
from .stream import EventGenerator, iter_events


def _stream(args, cfg) -> int:
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
    cfg = {**cfg, "seed": args.seed if args.seed is not None else cfg["seed"]}
    generator = EventGenerator(Model(cfg, last_year=as_of.year), as_of)
    start = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc) if args.as_of \
        else datetime.now(timezone.utc)

    if args.sink == "postgresql":
        from .postgres import PostgresSink
        sink = PostgresSink()
        write = sink.write
    else:
        sink = None
        write = lambda e: print(json.dumps(e.to_dict(), ensure_ascii=False), flush=True)  # noqa: E731

    print(f"streaming -> {args.sink} at {args.rate:g}/s (seed {cfg['seed']}, as-of {as_of}, speed {args.speed:g}x)",
          file=sys.stderr)
    emitted = 0
    try:
        for event in iter_events(generator, args.rate, start_time=start, start_seq=args.start_seq, count=args.count,
                                 duration=args.duration, speed=args.speed, jitter=not args.no_jitter):
            write(event)
            emitted += 1
    except KeyboardInterrupt:
        pass
    finally:
        if sink:
            sink.close()
    print(f"stopped after {emitted:,} event(s); resume with --start-seq {args.start_seq + emitted}", file=sys.stderr)
    return 0


def _dims(_args, _cfg) -> int:
    from .postgres import connect, load_dims
    with connect() as conn:
        for name, n in load_dims(conn).items():
            print(f"{name:<20} {n:>4} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="generator", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("dims", help="create the source schema and load the six dimension tables (idempotent)")
    s = sub.add_parser("stream", help="emit sales events, one order each")
    s.add_argument("--sink", choices=["stdout", "postgresql"], default="stdout")
    s.add_argument("--rate", type=float, default=1.0, help="events per (simulated) second")
    s.add_argument("--count", type=int, help="stop after N events")
    s.add_argument("--duration", type=float, help="stop after N wall-clock seconds")
    s.add_argument("--as-of", help="simulated start date YYYY-MM-DD (default: now)")
    s.add_argument("--speed", type=float, default=1.0, help="simulated-time multiplier")
    s.add_argument("--start-seq", type=int, default=0, help="first event number, to resume a stopped stream")
    s.add_argument("--seed", type=int)
    s.add_argument("--no-jitter", action="store_true", help="fixed interval instead of a Poisson process")
    args = p.parse_args(argv)
    return {"dims": _dims, "stream": _stream}[args.cmd](args, load_config())
