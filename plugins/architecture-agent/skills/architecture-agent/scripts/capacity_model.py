#!/usr/bin/env python3
"""Calculate transparent traffic, storage, and availability estimates."""

from __future__ import annotations

import argparse
import json


def positive(value: float, label: str) -> float:
    if value <= 0:
        raise argparse.ArgumentTypeError(f"{label} must be positive")
    return value


def traffic(args: argparse.Namespace) -> dict[str, object]:
    average_rps = args.requests / args.active_seconds
    peak_rps = average_rps * args.peak_factor
    return {
        "mode": "traffic",
        "inputs": {
            "requests": args.requests,
            "active_seconds": args.active_seconds,
            "peak_factor": args.peak_factor,
            "request_bytes": args.request_bytes,
            "response_bytes": args.response_bytes,
        },
        "formulas": {
            "average_rps": "requests / active_seconds",
            "peak_rps": "average_rps * peak_factor",
            "peak_bandwidth_bytes_per_second": "peak_rps * (request_bytes + response_bytes)",
        },
        "results": {
            "average_rps": average_rps,
            "peak_rps": peak_rps,
            "peak_bandwidth_bytes_per_second": peak_rps
            * (args.request_bytes + args.response_bytes),
        },
        "uncertainty": "Inputs are estimates unless backed by measured evidence.",
    }


def storage(args: argparse.Namespace) -> dict[str, object]:
    raw = args.objects_per_day * args.object_bytes * args.retention_days
    replicated = raw * args.replication_factor
    total = replicated * (1 + args.index_overhead)
    return {
        "mode": "storage",
        "inputs": {
            "objects_per_day": args.objects_per_day,
            "object_bytes": args.object_bytes,
            "retention_days": args.retention_days,
            "replication_factor": args.replication_factor,
            "index_overhead": args.index_overhead,
        },
        "formulas": {
            "raw_bytes": "objects_per_day * object_bytes * retention_days",
            "total_bytes": "raw_bytes * replication_factor * (1 + index_overhead)",
        },
        "results": {"raw_bytes": raw, "total_bytes": total},
        "uncertainty": "Compression, tombstones, metadata, growth, and backups are not included.",
    }


def availability(args: argparse.Namespace) -> dict[str, object]:
    minutes = 365.25 * 24 * 60
    downtime = minutes * (1 - args.target / 100)
    return {
        "mode": "availability",
        "inputs": {"target_percent": args.target},
        "formulas": {"annual_downtime_minutes": "year_minutes * (1 - target_percent / 100)"},
        "results": {
            "annual_downtime_minutes": downtime,
            "monthly_downtime_minutes_average": downtime / 12,
        },
        "uncertainty": "A percentage alone does not define measurement scope or excluded windows.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    traffic_parser = commands.add_parser("traffic", help="estimate RPS and bandwidth")
    traffic_parser.add_argument("--requests", type=float, required=True)
    traffic_parser.add_argument("--active-seconds", type=float, required=True)
    traffic_parser.add_argument("--peak-factor", type=float, default=3.0)
    traffic_parser.add_argument("--request-bytes", type=float, default=0)
    traffic_parser.add_argument("--response-bytes", type=float, default=0)
    traffic_parser.set_defaults(calculate=traffic)
    storage_parser = commands.add_parser("storage", help="estimate retained storage")
    storage_parser.add_argument("--objects-per-day", type=float, required=True)
    storage_parser.add_argument("--object-bytes", type=float, required=True)
    storage_parser.add_argument("--retention-days", type=float, required=True)
    storage_parser.add_argument("--replication-factor", type=float, default=1)
    storage_parser.add_argument("--index-overhead", type=float, default=0)
    storage_parser.set_defaults(calculate=storage)
    availability_parser = commands.add_parser("availability", help="convert availability to downtime")
    availability_parser.add_argument("--target", type=float, required=True)
    availability_parser.set_defaults(calculate=availability)
    args = parser.parse_args()
    numeric = {
        key: value
        for key, value in vars(args).items()
        if isinstance(value, (int, float)) and key not in {"request_bytes", "response_bytes", "index_overhead"}
    }
    if any(value <= 0 for value in numeric.values()):
        parser.error("all counts, durations, factors, and targets must be positive")
    if args.mode == "availability" and not 0 < args.target < 100:
        parser.error("availability target must be between 0 and 100")
    if getattr(args, "index_overhead", 0) < 0:
        parser.error("index overhead must not be negative")
    print(json.dumps(args.calculate(args), ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
