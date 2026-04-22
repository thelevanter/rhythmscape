"""Lived-layer snapshot — real-time bus positions, every 60 s.

Spec §4.6. Emits ``data/raw/tago/locations/{city}_YYYYMMDD_HHMM00.parquet``.

The returned ``gpslati`` / ``gpslong`` are **map-matched** to the route
polyline, not raw GPS. Off-route observations are therefore invisible — RDI
here measures temporal discordance only, not spatial drift.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from rhythmscape.ingest.tago.client import TagoAPIError, TagoClient
from rhythmscape.ingest.tago.normalize import coerce_numeric, extract_items

log = structlog.get_logger(__name__)

SERVICE = "BusLcInfoInqireService"
OPERATION = "getRouteAcctoBusLcList"


def snapshot_locations(
    client: TagoClient,
    city_code: int,
    route_ids: list[str],
    snapshot_ts: datetime,
) -> pd.DataFrame:
    """Collect Lived-layer vehicle positions for all target routes at ``snapshot_ts``."""
    rows: list[dict] = []
    ts_iso = snapshot_ts.astimezone(timezone.utc).isoformat(timespec="seconds")

    for route_id in route_ids:
        try:
            body = client.call(
                SERVICE,
                OPERATION,
                {"cityCode": city_code, "routeId": route_id, "numOfRows": 100, "pageNo": 1},
            )
        except TagoAPIError as exc:
            log.warning(
                "locations_api_error",
                route_id=route_id,
                code=exc.code,
                msg=exc.msg,
            )
            continue

        for raw in extract_items(body):
            coerced = coerce_numeric(
                raw,
                {"gpslati": float, "gpslong": float, "nodeord": int},
            )
            rows.append(
                {
                    "snapshot_ts_utc": ts_iso,
                    "routeid": route_id,
                    "vehicleno": str(raw.get("vehicleno") or ""),
                    "nodeid": raw.get("nodeid"),
                    "nodenm": raw.get("nodenm"),
                    "nodeord": coerced.get("nodeord"),
                    "gpslati": coerced.get("gpslati"),
                    "gpslong": coerced.get("gpslong"),
                }
            )

    columns = [
        "snapshot_ts_utc",
        "routeid",
        "vehicleno",
        "nodeid",
        "nodenm",
        "nodeord",
        "gpslati",
        "gpslong",
    ]
    df = pd.DataFrame(rows, columns=columns)
    log.info("locations_snapshot", rows=len(df), routes_polled=len(route_ids))
    return df


def save_locations_snapshot(
    df: pd.DataFrame,
    out_dir: Path,
    city_name: str,
    snapshot_ts: datetime,
) -> Path:
    """Write to ``{out_dir}/{city}_YYYYMMDD_HHMM00.parquet``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = snapshot_ts.strftime("%Y%m%d_%H%M00")
    path = out_dir / f"{city_name}_{stamp}.parquet"
    suffix = 2
    while path.exists():
        path = out_dir / f"{city_name}_{stamp}_v{suffix}.parquet"
        suffix += 1
    df.to_parquet(path, compression="snappy", index=False)
    log.info("parquet_write", path=str(path), rows=len(df), kind="locations")
    return path
