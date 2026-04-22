"""Route metadata + Prescribed timetable — daily snapshot of the target routes.

Spec §4.4. Emits ``data/raw/tago/routes/{city}_YYYYMMDD.parquet`` once per day.
Each row is a route's Prescribed layer: first/last-bus times + weekday/sat/sun
dispatch intervals. This file is the operational realization of Lefebvre's
"prescribed rhythm" — the temporal promise that governance encodes.
"""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from rhythmscape.ingest.tago.client import TagoAPIError, TagoClient
from rhythmscape.ingest.tago.normalize import coerce_numeric, extract_items

log = structlog.get_logger(__name__)

SERVICE = "BusRouteInfoInqireService"
OPERATION = "getRouteInfoIem"
OPERATION_STATIONS = "getRouteAcctoThrghSttnList"

PRESCRIBED_FIELDS = [
    "routeid",
    "routeno",
    "routetp",
    "startvehicletime",
    "endvehicletime",
    "intervaltime",
    "intervalsattime",
    "intervalsuntime",
    "startnodenm",
    "endnodenm",
]


def fetch_route_info(client: TagoClient, city_code: int, route_id: str) -> dict | None:
    """Return the Prescribed-layer metadata for a single route, or None if absent."""
    body = client.call(
        SERVICE,
        OPERATION,
        {"cityCode": city_code, "routeId": route_id},
    )
    items = extract_items(body)
    if not items:
        log.warning("route_info_empty", route_id=route_id, city_code=city_code)
        return None
    row = items[0]
    out = {field: row.get(field) for field in PRESCRIBED_FIELDS}
    out["requested_route_id"] = route_id
    out["collected_at_utc"] = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    return out


def fetch_routes(client: TagoClient, city_code: int, route_ids: list[str]) -> pd.DataFrame:
    """Fetch Prescribed-layer metadata for every route id. Missing rows are skipped."""
    rows: list[dict] = []
    for rid in route_ids:
        try:
            row = fetch_route_info(client, city_code, rid)
        except TagoAPIError as exc:
            log.warning("route_info_api_error", route_id=rid, code=exc.code, msg=exc.msg)
            continue
        if row is not None:
            rows.append(row)
    columns = PRESCRIBED_FIELDS + ["requested_route_id", "collected_at_utc"]
    df = pd.DataFrame(rows, columns=columns)
    # TAGO routeno mixes numeric-looking ("271") and descriptive ("BRT급행(6000)") strings.
    # Force all metadata columns to string so parquet write never hits a type-inference
    # failure on the descriptive outlier.
    for col in columns:
        df[col] = df[col].astype("string")
    return df


def save_routes(df: pd.DataFrame, out_dir: Path, city_name: str, run_date: date) -> Path:
    """Write to ``{out_dir}/{city}_YYYYMMDD.parquet``; preserve existing via ``_v2`` suffix."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{city_name}_{run_date.strftime('%Y%m%d')}"
    path = out_dir / f"{base}.parquet"
    suffix = 2
    while path.exists():
        path = out_dir / f"{base}_v{suffix}.parquet"
        suffix += 1
    df.to_parquet(path, compression="snappy", index=False)
    log.info("parquet_write", path=str(path), rows=len(df), kind="routes")
    return path


def fetch_route_stations(
    client: TagoClient,
    city_code: int,
    route_id: str,
    page_size: int = 100,
    inter_page_sleep_sec: float = 0.5,
) -> pd.DataFrame:
    """Fetch the ordered stations traversed by one route via ``getRouteAcctoThrghSttnList``.

    Returns a DataFrame with columns ``routeid, nodeid, nodenm, nodeord,
    gpslati, gpslong, updowncd, collected_at_utc``. Ordering follows
    ``nodeord`` (route sequence index).
    """
    collected_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    page_no = 1
    total_pages: int | None = None

    while True:
        body = client.call(
            SERVICE,
            OPERATION_STATIONS,
            {
                "cityCode": city_code,
                "routeId": route_id,
                "numOfRows": page_size,
                "pageNo": page_no,
            },
        )
        total_count = int(body.get("totalcount") or 0)
        if total_pages is None:
            total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1

        for raw in extract_items(body):
            coerced = coerce_numeric(
                raw,
                {"nodeord": int, "gpslati": float, "gpslong": float},
            )
            rows.append(
                {
                    "routeid": route_id,
                    "nodeid": coerced.get("nodeid"),
                    "nodenm": coerced.get("nodenm"),
                    "nodeord": coerced.get("nodeord"),
                    "gpslati": coerced.get("gpslati"),
                    "gpslong": coerced.get("gpslong"),
                    "updowncd": coerced.get("updowncd"),
                    "collected_at_utc": collected_at,
                }
            )
        if page_no >= (total_pages or 1):
            break
        page_no += 1
        if inter_page_sleep_sec > 0:
            time.sleep(inter_page_sleep_sec)

    df = pd.DataFrame(
        rows,
        columns=[
            "routeid",
            "nodeid",
            "nodenm",
            "nodeord",
            "gpslati",
            "gpslong",
            "updowncd",
            "collected_at_utc",
        ],
    )
    if not df.empty:
        df = df.sort_values("nodeord").reset_index(drop=True)
    log.info("route_stations_fetched", route_id=route_id, rows=len(df))
    return df


def fetch_all_route_stations(
    client: TagoClient,
    city_code: int,
    route_ids: list[str],
) -> pd.DataFrame:
    """Fetch station lists for all target routes and concatenate into one DataFrame."""
    frames: list[pd.DataFrame] = []
    for rid in route_ids:
        try:
            frames.append(fetch_route_stations(client, city_code, rid))
        except TagoAPIError as exc:
            log.warning(
                "route_stations_api_error",
                route_id=rid,
                code=exc.code,
                msg=exc.msg,
            )
    if not frames:
        return pd.DataFrame(
            columns=[
                "routeid",
                "nodeid",
                "nodenm",
                "nodeord",
                "gpslati",
                "gpslong",
                "updowncd",
                "collected_at_utc",
            ]
        )
    return pd.concat(frames, ignore_index=True)


def save_route_stations(
    df: pd.DataFrame,
    out_dir: Path,
    city_name: str,
    run_date: date,
) -> Path:
    """Write to ``{out_dir}/{city}_YYYYMMDD.parquet``; preserve existing via ``_v2`` suffix."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{city_name}_{run_date.strftime('%Y%m%d')}"
    path = out_dir / f"{base}.parquet"
    suffix = 2
    while path.exists():
        path = out_dir / f"{base}_v{suffix}.parquet"
        suffix += 1
    df.to_parquet(path, compression="snappy", index=False)
    log.info("parquet_write", path=str(path), rows=len(df), kind="route_stations")
    return path


def select_observatories(
    route_stations_df: pd.DataFrame,
    strategy: str = "quarters_dir0",
) -> pd.DataFrame:
    """Pick strategic rhythmic observatories per route for Expected-layer polling.

    "Observatory" rather than "sentinel": the station is theorized as a
    Lefebvrean listening post for polyrhythmia, not a checkpoint. See
    ``docs/analysis/sentinel_rationale.md`` for the full selection
    rationale and its RDI interpretation binding.

    Day 1 (2026-04-23) empirical finding: the naive "mid" strategy landed on
    terminal/turnaround stations for bidirectional routes (BRT6000 nodeord 39
    = 덕동공영차고지, 710 nodeord 54 = 마산대학교종점). Arrivals API at a
    terminal returns 0 because buses at the terminal are not "arriving" —
    they have already arrived. Default now restricts to ``updowncd==0``
    (forward leg) and picks three interior ordinal points (n/4, n/2, 3n/4)
    per route, avoiding both termini. 9 observatories × 720 ticks/day =
    6,480 calls, well under the 10k per-endpoint quota.

    Strategies
    ----------
    - ``"quarters_dir0"`` (default): direction 0 only, nodeord at n/4,
      n/2, 3n/4. Three observatories per route, terminal-free,
      single-direction.
    - ``"mid"``: single observatory at ``nodeord ≈ len/2`` across both
      directions (legacy; subject to terminal collision on bidirectional
      routes).
    - ``"end"`` / ``"start"``: terminal picks — diagnostic use only.
    """
    if route_stations_df.empty:
        return route_stations_df.iloc[0:0]

    picks: list[pd.Series] = []
    for rid, grp in route_stations_df.groupby("routeid"):
        if strategy == "quarters_dir0":
            if "updowncd" in grp.columns:
                dir0 = grp[grp["updowncd"] == 0]
                if dir0.empty:
                    dir0 = grp
            else:
                dir0 = grp
            ordered = dir0.sort_values("nodeord").reset_index(drop=True)
            n = len(ordered)
            if n == 0:
                continue
            if n >= 4:
                idxs = [n // 4, n // 2, (3 * n) // 4]
            elif n >= 3:
                idxs = [0, n // 2, n - 1]
            elif n == 2:
                idxs = [0, 1]
            else:
                idxs = [0]
            for i in idxs:
                picks.append(ordered.iloc[i])
        else:
            ordered = grp.sort_values("nodeord").reset_index(drop=True)
            if strategy == "start":
                picks.append(ordered.iloc[0])
            elif strategy == "end":
                picks.append(ordered.iloc[-1])
            else:
                picks.append(ordered.iloc[len(ordered) // 2])
    return pd.DataFrame(picks).reset_index(drop=True)
