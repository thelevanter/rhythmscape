"""Expected-layer snapshot — per-station arrival predictions, every 60 s.

Spec §4.5. Emits ``data/raw/tago/arrivals/{city}_YYYYMMDD_HHMM00.parquet``.

For each target route this calls ``getSttnAcctoArvlPrearngeInfoList`` at every
station the route visits. Rows with no imminent arrival are dropped — we
preserve the API's sparsity rather than fabricating NULLs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from rhythmscape.ingest.tago.client import TagoAPIError, TagoClient
from rhythmscape.ingest.tago.normalize import coerce_numeric, extract_items

log = structlog.get_logger(__name__)

SERVICE = "ArvlInfoInqireService"
OPERATION = "getSttnAcctoArvlPrearngeInfoList"


def snapshot_arrivals(
    client: TagoClient,
    city_code: int,
    route_ids: set[str],
    station_ids: list[str],
    snapshot_ts: datetime,
) -> pd.DataFrame:
    """Collect Expected-layer rows for all (station, route) pairs at ``snapshot_ts``.

    ``route_ids`` is used to filter the response to only the routes we track —
    a station typically serves many routes, and we do not want to store
    arrivals for routes outside the target set.
    """
    rows: list[dict] = []
    ts_iso = snapshot_ts.astimezone(timezone.utc).isoformat(timespec="seconds")

    for node_id in station_ids:
        try:
            body = client.call(
                SERVICE,
                OPERATION,
                {"cityCode": city_code, "nodeId": node_id, "numOfRows": 100, "pageNo": 1},
            )
        except TagoAPIError as exc:
            log.warning(
                "arrivals_api_error",
                node_id=node_id,
                code=exc.code,
                msg=exc.msg,
            )
            continue

        for raw in extract_items(body):
            raw_rid = str(raw.get("routeid", ""))
            if raw_rid not in route_ids:
                continue
            coerced = coerce_numeric(
                raw,
                {"arrtime": int, "arrprevstationcnt": int},
            )
            rows.append(
                {
                    "snapshot_ts_utc": ts_iso,
                    "routeid": raw_rid,
                    "nodeid": node_id,
                    "arrtime_sec": coerced.get("arrtime"),
                    "arrprevstationcnt": coerced.get("arrprevstationcnt"),
                    "vehicletp": raw.get("vehicletp"),
                }
            )

    columns = [
        "snapshot_ts_utc",
        "routeid",
        "nodeid",
        "arrtime_sec",
        "arrprevstationcnt",
        "vehicletp",
    ]
    df = pd.DataFrame(rows, columns=columns)
    log.info("arrivals_snapshot", rows=len(df), stations_polled=len(station_ids))
    return df


def save_arrivals_snapshot(
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
    log.info("parquet_write", path=str(path), rows=len(df), kind="arrivals")
    return path
