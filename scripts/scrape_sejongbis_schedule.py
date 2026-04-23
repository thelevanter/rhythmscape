#!/usr/bin/env python3
"""Sejong BIS timetable scraper — single-shot.

Fills the Sejong prescription-opacity gap by pulling per-dispatch timetables
from `bis.sejong.go.kr` for our three TAGO routeids. The Sejong BIS
``busRouteId`` is the TAGO ``SJB``-prefix-stripped number (empirically
verified 2026-04-24 07:45 KST), so no text search is required.

Output: ``data/processed/tago/prescribed_intervals_sejong.parquet``
(overwrites the all-NaN version produced from TAGO route metadata).
Every row carries ``prescribed_source="sejongbis_scrape"`` to flag it as
externally sourced.

Per-day-type dispatch flags observed in ``searchBusTimeList.do`` rows:
- ``week_operation_flag`` → weekday
- ``sat_operation_flag`` → Saturday
- ``holidy_operation_flag`` → Sunday & public holidays (Sejong convention)
- ``vacation_operation_flag`` → school-vacation weekdays (we ignore —
  Rhythmscape treats this as weekday)

Headway derivation per (route, daytype):
    count = dispatches where flag == "1"
    first = min(departure_time), last = max(departure_time)
    span_min = (last_hhmm → minutes) − (first_hhmm → minutes)
    mean_headway_min = span_min / (count − 1)  if count ≥ 2 else None

Usage:
    python scripts/scrape_sejongbis_schedule.py
    python scripts/scrape_sejongbis_schedule.py --routes SJB293000362,SJB293000178,SJB293000030
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import structlog

log = structlog.get_logger(__name__)

UA = "Rhythmscape-Hackathon/0.1 (+https://github.com/thelevanter/rhythmscape)"
BASE = "https://bis.sejong.go.kr"
SCHEDULE_URL = f"{BASE}/web/traffic/searchBusTimeList.do"

DAYTYPE_FLAGS = {
    "weekday": "week_operation_flag",
    "sat": "sat_operation_flag",
    "sun": "holidy_operation_flag",
}

DEFAULT_TAGO_ROUTEIDS = [
    "SJB293000362",  # B2
    "SJB293000178",  # 1004
    "SJB293000030",  # 551
]


def hhmm_to_min(s: str) -> int:
    """Convert '0600' / '2320' / '2425' (overnight) strings to minutes since midnight.
    Sejong BIS sometimes returns times >= 24:00 for after-midnight dispatches.
    """
    s = s.strip()
    if not s:
        raise ValueError(f"empty hhmm: {s!r}")
    h, m = int(s[:-2]), int(s[-2:])
    return h * 60 + m


def fetch_schedule(client: httpx.Client, bus_route_id: str) -> list[dict]:
    r = client.post(SCHEDULE_URL, data={"busRouteId": bus_route_id})
    r.raise_for_status()
    data = r.json()
    return data.get("busTimeList") or []


def derive_daytype_metrics(dispatches: list[dict]) -> dict[str, dict]:
    """For each daytype, compute count, first, last, and mean headway."""
    out: dict[str, dict] = {}
    for daytype, flag in DAYTYPE_FLAGS.items():
        runs = [
            d for d in dispatches
            if str(d.get(flag, "")).strip() == "1" and str(d.get("departure_time", "")).strip()
        ]
        if not runs:
            out[daytype] = {
                "count": 0,
                "first_hhmm": None,
                "last_hhmm": None,
                "mean_headway_min": None,
            }
            continue
        times_min = sorted(hhmm_to_min(str(d["departure_time"]).strip()) for d in runs)
        first_min, last_min = times_min[0], times_min[-1]
        count = len(times_min)
        mean_headway = (last_min - first_min) / (count - 1) if count >= 2 else None
        out[daytype] = {
            "count": count,
            "first_hhmm": f"{first_min // 60:02d}{first_min % 60:02d}",
            "last_hhmm": f"{last_min // 60:02d}{last_min % 60:02d}",
            "mean_headway_min": round(mean_headway, 2) if mean_headway is not None else None,
        }
    return out


def scrape(tago_routeids: list[str], inter_request_sleep_sec: float = 2.0) -> pd.DataFrame:
    rows: list[dict] = []
    collected_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    headers = {
        "User-Agent": UA,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE}/web/traffic/traffic_bus_line_search.view",
    }
    with httpx.Client(timeout=15, headers=headers) as c:
        for idx, tago_rid in enumerate(tago_routeids):
            bus_route_id = tago_rid.removeprefix("SJB")
            try:
                dispatches = fetch_schedule(c, bus_route_id)
            except Exception as exc:
                log.error("sejongbis_fetch_failed", tago_routeid=tago_rid, error=str(exc))
                continue
            metrics = derive_daytype_metrics(dispatches)
            for daytype, m in metrics.items():
                rows.append(
                    {
                        "route_id": tago_rid,
                        "daytype": daytype,
                        "peak_interval_min": m["mean_headway_min"],
                        "off_peak_interval_min": m["mean_headway_min"],
                        "dispatch_count": m["count"],
                        "first_hhmm": m["first_hhmm"],
                        "last_hhmm": m["last_hhmm"],
                        "source": "bis.sejong.go.kr/web/traffic/searchBusTimeList.do",
                        "prescribed_source": "sejongbis_scrape",
                        "collected_at": collected_at,
                        "source_url": f"{SCHEDULE_URL}?busRouteId={bus_route_id}",
                    }
                )
            log.info(
                "sejongbis_scraped",
                tago_routeid=tago_rid,
                bus_route_id=bus_route_id,
                dispatch_counts_by_daytype={k: v["count"] for k, v in metrics.items()},
            )
            if idx < len(tago_routeids) - 1:
                time.sleep(inter_request_sleep_sec)
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--routes",
        type=str,
        default=",".join(DEFAULT_TAGO_ROUTEIDS),
        help="Comma-separated TAGO routeids (SJB prefix kept)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/processed/tago/prescribed_intervals_sejong.parquet"),
    )
    parser.add_argument("--sleep-sec", type=float, default=2.0)
    args = parser.parse_args()

    ids = [r.strip() for r in args.routes.split(",") if r.strip()]
    df = scrape(ids, inter_request_sleep_sec=args.sleep_sec)
    if df.empty:
        print("✗ no rows scraped", flush=True)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out, compression="snappy", index=False)
    print(f"✓ {args.out}  ({len(df)} rows)")
    print()
    print(
        df[["route_id", "daytype", "dispatch_count", "first_hhmm", "last_hhmm", "peak_interval_min"]]
        .to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
