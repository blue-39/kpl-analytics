from __future__ import annotations

import argparse
import json
from dataclasses import asdict

import uvicorn

from kpl_analytics.collector.pipeline import BackfillPipeline
from kpl_analytics.config import Settings
from kpl_analytics.warehouse.audit import audit_warehouse
from kpl_analytics.warehouse.database import Warehouse
from kpl_analytics.warehouse.demo import seed_demo


def _print(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kpl-analytics")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill = subparsers.add_parser("backfill", help="archive recent public competition data")
    backfill.add_argument("--days", type=int, default=730)
    backfill.add_argument("--refresh", action="store_true")

    subparsers.add_parser("build", help="rebuild DuckDB from the raw archive")

    demo = subparsers.add_parser("seed-demo", help="create deterministic local demo data")
    demo.add_argument("--battles", type=int, default=72)

    subparsers.add_parser("audit", help="check normalized data integrity")

    serve = subparsers.add_parser("serve", help="start the local analytics API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.from_env()
    warehouse = Warehouse(settings)

    if args.command == "backfill":
        summary = BackfillPipeline(settings).backfill(args.days, args.refresh)
        _print(asdict(summary))
    elif args.command == "build":
        _print(warehouse.rebuild_from_raw())
    elif args.command == "seed-demo":
        _print(seed_demo(warehouse, args.battles))
    elif args.command == "audit":
        _print(audit_warehouse(warehouse))
    elif args.command == "serve":
        uvicorn.run(
            "kpl_analytics.api.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main()
