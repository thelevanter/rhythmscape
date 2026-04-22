"""Orchestration — the single launchd entry point for TAGO batch collection.

Spec §4.7. Two execution modes, selected via ``--mode``:

- ``anchor``: runs once per day (06:55 KST). Refreshes the station and
  route tables (Prescribed layer + spatial anchor).
- ``tick``: runs once per minute inside the 07:00-19:59 KST window.
  Collects Expected (arrivals) and Lived (locations) snapshots.

Exit codes:
    0  — normal
    22 — TAGO daily quota exceeded
    30 — TAGO service key unregistered
    99 — other failure
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import structlog
import yaml
from dotenv import load_dotenv

from rhythmscape.ingest.tago.arrivals import save_arrivals_snapshot, snapshot_arrivals
from rhythmscape.ingest.tago.client import (
    TagoAPIError,
    TagoClient,
    TagoKeyUnregistered,
    TagoQuotaExceeded,
)
from rhythmscape.ingest.tago.locations import save_locations_snapshot, snapshot_locations
from rhythmscape.ingest.tago.routes import (
    fetch_all_route_stations,
    fetch_routes,
    save_route_stations,
    save_routes,
    select_observatories,
)
from rhythmscape.ingest.tago.stations import fetch_stations, save_stations


@dataclass(frozen=True)
class Config:
    api_key: str
    city_code: int
    city_name: str
    route_ids: list[str]
    window_start: time
    window_end: time
    tz: ZoneInfo
    poll_interval_sec: int
    http_timeout_sec: float
    raw_base: Path
    processed_base: Path
    checkpoint_dir: Path
    logs_dir: Path


def load_config(path: Path) -> Config:
    """Load ``tago.yaml`` + ``.env`` into a typed ``Config``."""
    load_dotenv()
    with path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    tago = cfg["tago"]

    api_key_env = tago.get("api_key_env", "TAGO_API_KEY")
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        raise RuntimeError(f"Environment variable {api_key_env!r} is unset or empty")

    route_ids: list[str] = []
    for entry in tago["routes"]:
        rid = entry.get("routeid") or entry.get("route_id")
        if rid:
            route_ids.append(str(rid))

    tz = ZoneInfo(tago["collection"]["timezone"])
    ws = datetime.strptime(tago["collection"]["window_start"], "%H:%M").time()
    we = datetime.strptime(tago["collection"]["window_end"], "%H:%M").time()

    return Config(
        api_key=api_key,
        city_code=int(tago["city"]["code"]),
        city_name=tago["city"]["name"],
        route_ids=route_ids,
        window_start=ws,
        window_end=we,
        tz=tz,
        poll_interval_sec=int(tago["collection"]["poll_interval_sec"]),
        http_timeout_sec=float(tago["collection"]["http_timeout_sec"]),
        raw_base=Path(tago["storage"]["raw_base"]),
        processed_base=Path(tago["storage"]["processed_base"]),
        checkpoint_dir=Path(tago["storage"]["checkpoint_dir"]),
        logs_dir=Path(tago["storage"]["logs_dir"]),
    )


_SERVICE_KEY_RE = re.compile(r"(serviceKey=)[^&\s\"']+", re.IGNORECASE)


class _RedactServiceKey(logging.Filter):
    """Redact ``serviceKey=<value>`` from log records to prevent TAGO API key leaks.

    httpx's INFO-level request log writes the full URL including the serviceKey
    query parameter. This filter mutates the record message in place so both
    stdout and the daily JSON log never capture the plaintext key.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and "serviceKey=" in record.msg:
            record.msg = _SERVICE_KEY_RE.sub(r"\1***REDACTED***", record.msg)
        if record.args:
            try:
                record.args = tuple(
                    _SERVICE_KEY_RE.sub(r"\1***REDACTED***", str(a))
                    if isinstance(a, str) and "serviceKey=" in a
                    else a
                    for a in record.args
                )
            except Exception:
                pass
        return True


def configure_logging(logs_dir: Path, level: str = "INFO") -> None:
    """Set up structlog → JSON lines on stdout + daily file under ``logs_dir``.

    Also installs a global ``serviceKey=`` redaction filter so httpx's request
    log cannot leak the TAGO API key (CLAUDE.md §7 guardrail).
    """
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"tago_{date.today().strftime('%Y%m%d')}.log"

    handler_file = logging.FileHandler(log_path, encoding="utf-8")
    handler_stream = logging.StreamHandler(sys.stdout)
    redact = _RedactServiceKey()
    handler_file.addFilter(redact)
    handler_stream.addFilter(redact)
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler_file)
    root.addHandler(handler_stream)
    root.setLevel(level)

    # httpx logs every request at INFO with the full URL. Keep it at WARNING
    # so query strings never reach the handlers in the first place — the
    # redaction filter above is the second line of defence, not the primary one.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


log = structlog.get_logger(__name__)


def _load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_checkpoint(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False, default=str)
    tmp.replace(path)


def _checkpoint_path(cfg: Config) -> Path:
    return cfg.checkpoint_dir / "state.json"


def run_daily_anchor(cfg: Config) -> int:
    """Run the daily stations + routes refresh."""
    log.info(
        "anchor_start",
        city=cfg.city_name,
        city_code=cfg.city_code,
        route_count=len(cfg.route_ids),
    )

    if not cfg.route_ids:
        log.error("anchor_no_routes", hint="run resolve_routes.py --write first")
        return 99

    run_date = datetime.now(tz=cfg.tz).date()
    stations_dir = cfg.raw_base / "stations"
    routes_dir = cfg.raw_base / "routes"
    route_stations_dir = cfg.raw_base / "route_stations"
    date_stamp = run_date.strftime("%Y%m%d")
    stations_today = stations_dir / f"{cfg.city_name}_{date_stamp}.parquet"
    routes_today = routes_dir / f"{cfg.city_name}_{date_stamp}.parquet"
    route_stations_today = route_stations_dir / f"{cfg.city_name}_{date_stamp}.parquet"

    import pandas as pd

    with TagoClient(
        api_key=cfg.api_key,
        timeout=cfg.http_timeout_sec,
        raw_dump_dir=cfg.logs_dir,
    ) as client:
        if stations_today.exists():
            stations_df = pd.read_parquet(stations_today)
            log.info(
                "anchor_stations_skipped_idempotent",
                path=str(stations_today),
                rows=int(len(stations_df)),
            )
        else:
            stations_df = fetch_stations(client, cfg.city_code)
            save_stations(stations_df, stations_dir, cfg.city_name, run_date)

        if routes_today.exists():
            routes_df = pd.read_parquet(routes_today)
            log.info(
                "anchor_routes_skipped_idempotent",
                path=str(routes_today),
                rows=int(len(routes_df)),
            )
        else:
            routes_df = fetch_routes(client, cfg.city_code, cfg.route_ids)
            save_routes(routes_df, routes_dir, cfg.city_name, run_date)

        if route_stations_today.exists():
            route_stations_df = pd.read_parquet(route_stations_today)
            log.info(
                "anchor_route_stations_skipped_idempotent",
                path=str(route_stations_today),
                rows=int(len(route_stations_df)),
            )
        else:
            route_stations_df = fetch_all_route_stations(
                client, cfg.city_code, cfg.route_ids
            )
            save_route_stations(
                route_stations_df, route_stations_dir, cfg.city_name, run_date
            )

    checkpoint = _load_checkpoint(_checkpoint_path(cfg))
    checkpoint["last_anchor_run"] = datetime.now(tz=cfg.tz).isoformat(timespec="seconds")
    checkpoint["last_anchor_rows_stations"] = int(len(stations_df))
    checkpoint["last_anchor_rows_routes"] = int(len(routes_df))
    _write_checkpoint(_checkpoint_path(cfg), checkpoint)

    log.info(
        "anchor_complete",
        stations=int(len(stations_df)),
        routes=int(len(routes_df)),
        route_stations=int(len(route_stations_df)),
    )
    return 0


def _within_window(now_local: datetime, cfg: Config) -> bool:
    t = now_local.time()
    if cfg.window_start <= cfg.window_end:
        return cfg.window_start <= t <= cfg.window_end
    return t >= cfg.window_start or t <= cfg.window_end


def _quota_already_tripped(checkpoint: dict[str, Any], today: date) -> bool:
    tripped = checkpoint.get("quota_tripped_date")
    if not tripped:
        return False
    try:
        return datetime.fromisoformat(str(tripped)).date() == today
    except ValueError:
        return str(tripped) == today.isoformat()


def run_minute_tick(cfg: Config) -> int:
    """Run a single 60 s tick: Expected + Lived snapshots for all target routes."""
    checkpoint = _load_checkpoint(_checkpoint_path(cfg))
    now_local = datetime.now(tz=cfg.tz)
    today = now_local.date()

    if _quota_already_tripped(checkpoint, today):
        log.info("tick_noop_quota_tripped", date=today.isoformat())
        return 0

    if not _within_window(now_local, cfg):
        log.info("tick_noop_out_of_window", now_local=now_local.isoformat())
        return 0

    if not cfg.route_ids:
        log.error("tick_no_routes", hint="run resolve_routes.py --write first")
        return 99

    import pandas as pd

    route_stations_path = _latest_artifact(
        cfg.raw_base / "route_stations", cfg.city_name, today
    )
    if route_stations_path is None:
        log.error(
            "tick_missing_route_stations_anchor",
            hint="run --mode anchor first (route_stations parquet absent)",
        )
        return 99

    route_stations_df = pd.read_parquet(route_stations_path)
    observatories_df = select_observatories(route_stations_df, strategy="quarters_dir0")
    station_ids = [
        str(x) for x in observatories_df["nodeid"].dropna().unique().tolist()
    ]
    if not station_ids:
        log.error(
            "tick_no_observatories",
            hint="route_stations parquet is empty",
        )
        return 99

    log.info(
        "tick_start",
        route_ids=cfg.route_ids,
        observatories=station_ids,
        snapshot_iso=now_local.isoformat(),
    )

    start_ts = datetime.now(tz=timezone.utc)
    snapshot_ts = now_local

    try:
        with TagoClient(
            api_key=cfg.api_key,
            timeout=cfg.http_timeout_sec,
            raw_dump_dir=cfg.logs_dir,
        ) as client:
            arrivals_df = snapshot_arrivals(
                client=client,
                city_code=cfg.city_code,
                route_ids=set(cfg.route_ids),
                station_ids=station_ids,
                snapshot_ts=snapshot_ts,
            )
            save_arrivals_snapshot(
                arrivals_df,
                cfg.raw_base / "arrivals",
                cfg.city_name,
                snapshot_ts,
            )
            locations_df = snapshot_locations(
                client=client,
                city_code=cfg.city_code,
                route_ids=cfg.route_ids,
                snapshot_ts=snapshot_ts,
            )
            save_locations_snapshot(
                locations_df,
                cfg.raw_base / "locations",
                cfg.city_name,
                snapshot_ts,
            )
    except TagoQuotaExceeded as exc:
        checkpoint["quota_tripped_date"] = today.isoformat()
        checkpoint["last_error"] = f"quota: {exc}"
        _write_checkpoint(_checkpoint_path(cfg), checkpoint)
        log.error("quota_exceeded", endpoint=exc.endpoint, date=today.isoformat())
        return 22
    except TagoKeyUnregistered as exc:
        checkpoint["last_error"] = f"key_unregistered: {exc}"
        _write_checkpoint(_checkpoint_path(cfg), checkpoint)
        log.error("key_unregistered", endpoint=exc.endpoint)
        return 30
    except TagoAPIError as exc:
        checkpoint["consecutive_failures"] = int(checkpoint.get("consecutive_failures", 0)) + 1
        checkpoint["last_error"] = f"{exc.code}: {exc}"
        _write_checkpoint(_checkpoint_path(cfg), checkpoint)
        log.warning("tick_api_error", code=exc.code, endpoint=exc.endpoint)
        return 0

    elapsed_ms = int((datetime.now(tz=timezone.utc) - start_ts).total_seconds() * 1000)
    checkpoint["last_tick_utc"] = start_ts.isoformat(timespec="seconds")
    checkpoint["last_tick_rows_arrivals"] = int(len(arrivals_df))
    checkpoint["last_tick_rows_locations"] = int(len(locations_df))
    checkpoint["consecutive_failures"] = 0
    _write_checkpoint(_checkpoint_path(cfg), checkpoint)

    log.info(
        "tick_complete",
        elapsed_ms=elapsed_ms,
        arrivals=int(len(arrivals_df)),
        locations=int(len(locations_df)),
    )
    return 0


def _latest_artifact(directory: Path, city_name: str, today: date) -> Path | None:
    """Find today's parquet artifact, or the most recent prior file if today's is missing."""
    if not directory.exists():
        return None
    today_path = directory / f"{city_name}_{today.strftime('%Y%m%d')}.parquet"
    if today_path.exists():
        return today_path
    candidates = sorted(directory.glob(f"{city_name}_*.parquet"))
    return candidates[-1] if candidates else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rhythmscape TAGO batch scheduler")
    parser.add_argument("--mode", choices=["anchor", "tick"], required=True)
    parser.add_argument("--config", type=Path, default=Path("config/tago.yaml"))
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    configure_logging(cfg.logs_dir)

    try:
        if args.mode == "anchor":
            return run_daily_anchor(cfg)
        return run_minute_tick(cfg)
    except TagoQuotaExceeded:
        return 22
    except TagoKeyUnregistered:
        return 30
    except Exception as exc:
        log.exception("scheduler_fatal", error=str(exc))
        return 99


if __name__ == "__main__":
    sys.exit(main())
