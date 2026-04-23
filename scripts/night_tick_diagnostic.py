#!/usr/bin/env python3
"""Night-tick empty-response diagnostic.

Purpose: verify that the existing pipeline handles TAGO responses in the
``locations=0, arrivals=0`` regime gracefully — the regime we expect to
enter once night collection is activated (`night_collection_rationale.md`
§3.4 calls for an experimental tick at 19:30–19:45 KST on Day 2).

How to run:
    python scripts/night_tick_diagnostic.py                 # inspect only
    python scripts/night_tick_diagnostic.py --live-tick     # also run one
                                                            # manual tick
                                                            # per city NOW

Inspect mode walks ``data/raw/tago/{arrivals,locations}/*.parquet`` and
reports, per city, how many recent ticks returned zero rows. This gives
empirical evidence of whether the pipeline has already encountered the
``zero-vehicle`` regime cleanly.

Live-tick mode invokes the scheduler's tick for each of the four cities
and examines the just-written parquet. Useful when run in the 19:30
window to see "border" responses.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import date, datetime
from pathlib import Path

import pandas as pd


CITIES = ["changwon", "seongnam_bundang", "sejong", "busan_yeongdo"]


def inspect_recent(raw_base: Path, for_date: date, last_n: int = 60) -> pd.DataFrame:
    """Summarize the last ``last_n`` tick parquets per city for both endpoints."""
    stamp = for_date.strftime("%Y%m%d")
    rows = []
    for kind in ("arrivals", "locations"):
        for city in CITIES:
            paths = sorted((raw_base / kind).glob(f"{city}_{stamp}_*.parquet"))
            recent = paths[-last_n:] if last_n > 0 else paths
            zero_count = 0
            nonzero_count = 0
            for p in recent:
                try:
                    n = len(pd.read_parquet(p))
                except Exception:
                    continue
                if n == 0:
                    zero_count += 1
                else:
                    nonzero_count += 1
            rows.append(
                {
                    "kind": kind,
                    "city": city,
                    "inspected": zero_count + nonzero_count,
                    "zero_rows": zero_count,
                    "nonzero_rows": nonzero_count,
                    "zero_rate_pct": (
                        100.0 * zero_count / max(zero_count + nonzero_count, 1)
                    ),
                }
            )
    return pd.DataFrame(rows)


def run_live_tick(city: str) -> int:
    """Invoke the scheduler in tick mode for one city. Blocks until complete."""
    cmd = [
        ".venv/bin/python",
        "-m",
        "rhythmscape.ingest.tago.scheduler",
        "--mode",
        "tick",
        "--city",
        city,
    ]
    print(f"\n=== live tick: {city} ===")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout.strip().splitlines()[-4:] if r.stdout else "(no stdout)")
    if r.returncode:
        print(f"  returncode={r.returncode} stderr={r.stderr[:200]}")
    return r.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-base", type=Path, default=Path("data/raw/tago"))
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="YYYYMMDD, default: today in Asia/Seoul",
    )
    parser.add_argument(
        "--last-n",
        type=int,
        default=60,
        help="Inspect the last N parquets per city (default 60 ≈ 1h)",
    )
    parser.add_argument(
        "--live-tick",
        action="store_true",
        help="Run a manual tick per city now (in addition to inspection)",
    )
    args = parser.parse_args()

    if args.date:
        for_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    print(f"Night-tick diagnostic · {datetime.now().astimezone().isoformat(timespec='seconds')}")
    print(f"Scanning last {args.last_n} ticks per city for {for_date}")

    if args.live_tick:
        for city in CITIES:
            run_live_tick(city)
        print()

    summary = inspect_recent(args.raw_base, for_date, last_n=args.last_n)
    print()
    print(summary.to_string(index=False))
    print()

    # Surface any empty-response accidents
    zeros = summary[summary["zero_rows"] > 0]
    if zeros.empty:
        print("(no zero-row ticks found in scanned window)")
    else:
        print("Zero-row ticks detected (empty-response handling verified):")
        for _, r in zeros.iterrows():
            print(
                f"  {r['kind']:<10} {r['city']:<20} "
                f"{int(r['zero_rows'])}/{int(r['inspected'])} ticks "
                f"({r['zero_rate_pct']:.1f}%)"
            )
    print()
    print(
        "Expectation at night: locations zero-rate will climb sharply past "
        "22:00 KST, arrivals zero-rate near 100% post-23:00."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
