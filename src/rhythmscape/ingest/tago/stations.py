"""Station anchor dump — daily snapshot of every bus stop in the target city.

Spec §4.3. Emits ``data/raw/tago/stations/{city}_YYYYMMDD.parquet`` once per day.
"""

from __future__ import annotations

import math
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from rhythmscape.ingest.tago.client import TagoClient
from rhythmscape.ingest.tago.normalize import coerce_numeric, extract_items

log = structlog.get_logger(__name__)

SERVICE = "BusSttnInfoInqireService"
OPERATION = "getSttnNoList"


def fetch_stations(
    client: TagoClient,
    city_code: int,
    page_size: int = 100,
    inter_page_sleep_sec: float = 0.5,
) -> pd.DataFrame:
    """Page through all stations in ``city_code`` and return a normalized DataFrame.

    Columns: ``nodeid``, ``nodenm``, ``gpslati``, ``gpslong``, ``citycode``,
    ``collected_at_utc``.
    """
    collected_at = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []
    page_no = 1
    total_pages: int | None = None

    while True:
        body = client.call(
            SERVICE,
            OPERATION,
            {"cityCode": city_code, "numOfRows": page_size, "pageNo": page_no},
        )
        total_count = int(body.get("totalcount") or 0)
        if total_pages is None:
            total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1
            log.info(
                "stations_page_count",
                total_count=total_count,
                total_pages=total_pages,
                city_code=city_code,
            )

        items = extract_items(body)
        for raw in items:
            coerced = coerce_numeric(raw, {"gpslati": float, "gpslong": float})
            rows.append(
                {
                    "nodeid": coerced.get("nodeid"),
                    "nodenm": coerced.get("nodenm"),
                    "gpslati": coerced.get("gpslati"),
                    "gpslong": coerced.get("gpslong"),
                    "citycode": city_code,
                    "collected_at_utc": collected_at,
                }
            )
        log.info(
            "stations_page_fetched",
            page_no=page_no,
            rows_in_page=len(items),
            rows_total=len(rows),
        )
        if page_no >= (total_pages or 1):
            break
        page_no += 1
        if inter_page_sleep_sec > 0:
            time.sleep(inter_page_sleep_sec)

    return pd.DataFrame(
        rows,
        columns=["nodeid", "nodenm", "gpslati", "gpslong", "citycode", "collected_at_utc"],
    )


def save_stations(df: pd.DataFrame, out_dir: Path, city_name: str, run_date: date) -> Path:
    """Write to ``{out_dir}/{city}_YYYYMMDD.parquet``; preserve existing files via ``_v2`` suffix."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{city_name}_{run_date.strftime('%Y%m%d')}"
    path = out_dir / f"{base}.parquet"
    suffix = 2
    while path.exists():
        path = out_dir / f"{base}_v{suffix}.parquet"
        suffix += 1
    df.to_parquet(path, compression="snappy", index=False)
    log.info("parquet_write", path=str(path), rows=len(df), kind="stations")
    return path
