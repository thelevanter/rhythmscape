"""Rhythmic Discordance Index (RDI) v0 — magnitude only.

RDI translates Lefebvre's *arrhythmia* into an operational scalar:

    RDI(g, t, route) = |observed_interval − prescribed_interval| / prescribed_interval

Semantic layer binding (see ``docs/tago-batch-spec.md`` §2):

- **Prescribed**: ``getRouteInfoIem`` — official headway in ``routes/*.parquet``
- **Lived**: ``getRouteAcctoBusLcList`` — GPS vehicle positions in
  ``locations/*.parquet``
- **Expected** (NOT used here): ``getSttnAcctoArvlPrearngeInfoList`` —
  arrival predictions. This is the *system's forecast*, not lived reality,
  and must not be conflated with Lived. Reserved for three-layer analysis
  in a later session.

RDI v0 therefore computes Observed interval entirely from successive
vehicle passages at the same station, reconstructed from the locations
parquet. No ``arrivals_*.parquet`` is read here.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Block A — Prescribed intervals
# ---------------------------------------------------------------------------


def build_prescribed_intervals(routes_df: pd.DataFrame) -> pd.DataFrame:
    """Reshape the daily routes parquet into a long prescribed-interval table.

    The raw routes parquet carries one row per route with three headway
    columns (weekday / Saturday / Sunday). This helper melts it to one row
    per (route, daytype) with a single headway value, plus provenance.

    Output schema matches the Day 2 handoff (§A.2):

        route_id | daytype | peak_interval_min | off_peak_interval_min
                 | source  | collected_at

    ``peak_interval_min`` and ``off_peak_interval_min`` are set equal for
    Day 2 — TAGO does not split headway by peak / off-peak. Time-of-day
    decomposition is deferred to Day 3+.
    """
    daytype_cols = {
        "weekday": "intervaltime",
        "sat": "intervalsattime",
        "sun": "intervalsuntime",
    }

    rows: list[dict] = []
    for _, r in routes_df.iterrows():
        rid = str(r.get("routeid") or r.get("requested_route_id") or "")
        collected_at = str(r.get("collected_at_utc") or "")
        for daytype, col in daytype_cols.items():
            raw = r.get(col)
            try:
                val = float(raw) if raw is not None and str(raw) != "" else None
            except (TypeError, ValueError):
                val = None
            rows.append(
                {
                    "route_id": rid,
                    "daytype": daytype,
                    "peak_interval_min": val,
                    "off_peak_interval_min": val,
                    "source": "BusRouteInfoInqireService/getRouteInfoIem",
                    "collected_at": collected_at,
                }
            )

    out = pd.DataFrame(
        rows,
        columns=[
            "route_id",
            "daytype",
            "peak_interval_min",
            "off_peak_interval_min",
            "source",
            "collected_at",
        ],
    )
    return out


def save_prescribed_intervals(df: pd.DataFrame, out_path: Path) -> Path:
    """Write prescribed intervals to parquet at ``out_path``."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, compression="snappy", index=False)
    log.info("prescribed_intervals_written", path=str(out_path), rows=len(df))
    return out_path


def resolve_daytype(ts_local: datetime) -> str:
    """Return 'weekday' | 'sat' | 'sun' for a local (Asia/Seoul) datetime."""
    wd = ts_local.weekday()
    if wd == 5:
        return "sat"
    if wd == 6:
        return "sun"
    return "weekday"


# ---------------------------------------------------------------------------
# Block B — Observed intervals & RDI magnitude
# ---------------------------------------------------------------------------


def load_locations(
    locations_dir: Path,
    for_date: date | None = None,
    city: str | None = None,
) -> pd.DataFrame:
    """Read ``locations/*.parquet`` into one DataFrame, optionally filtered.

    Expected schema (from ``ingest/tago/locations.py``):
        snapshot_ts_utc, routeid, vehicleno, nodeid, nodenm, nodeord,
        gpslati, gpslong

    Filenames follow ``{city}_YYYYMMDD_HHMM00.parquet``. When ``city`` is
    given, only that city's files are loaded — critical for the 4-city
    multi-tenant layout where every city's parquets sit in the same
    directory.
    """
    if not locations_dir.exists():
        raise FileNotFoundError(f"locations directory missing: {locations_dir}")

    prefix = f"{city}_" if city else ""
    if for_date is not None:
        stamp = for_date.strftime("%Y%m%d")
        paths = sorted(locations_dir.glob(f"{prefix}*{stamp}_*.parquet"))
    else:
        paths = sorted(locations_dir.glob(f"{prefix}*.parquet"))

    if not paths:
        raise FileNotFoundError(
            f"no locations parquet matched in {locations_dir} "
            f"(city={city}, date={for_date})"
        )

    frames = [pd.read_parquet(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df["snapshot_ts_utc"] = pd.to_datetime(df["snapshot_ts_utc"], utc=True)
    df["vehicleno"] = df["vehicleno"].astype(str)
    df["routeid"] = df["routeid"].astype(str)
    df["nodeid"] = df["nodeid"].astype(str)
    log.info("locations_loaded", files=len(paths), rows=len(df), city=city)
    return df


def load_routes_parquet(
    routes_dir: Path,
    city: str,
    for_date: date,
) -> pd.DataFrame:
    """Load the most recent routes parquet for ``city`` on ``for_date``."""
    stamp = for_date.strftime("%Y%m%d")
    path = routes_dir / f"{city}_{stamp}.parquet"
    if not path.exists():
        candidates = sorted(routes_dir.glob(f"{city}_*.parquet"))
        if not candidates:
            raise FileNotFoundError(
                f"no routes parquet for city={city} in {routes_dir}"
            )
        path = candidates[-1]
        log.warning(
            "routes_parquet_fallback",
            city=city,
            used=str(path),
            expected_stamp=stamp,
        )
    return pd.read_parquet(path)


def compute_vehicle_passages(locations_df: pd.DataFrame) -> pd.DataFrame:
    """Detect the first tick at which each vehicle is observed at each station.

    A "passage" is the earliest ``snapshot_ts_utc`` for which a
    (routeid, vehicleno, nodeid) triplet appears in successive snapshots.
    Once a vehicle moves to a different nodeid, the previous station's
    passage is closed and a new passage is opened at the new station.

    Implementation: sort by (routeid, vehicleno, snapshot_ts), then for each
    vehicle treat a nodeid change as a new passage. The passage timestamp
    is the first snapshot at which the vehicle is at that nodeid.
    """
    if locations_df.empty:
        return locations_df.iloc[0:0].assign(passage_ts_utc=pd.Series(dtype="datetime64[ns, UTC]"))

    df = locations_df.sort_values(["routeid", "vehicleno", "snapshot_ts_utc"]).copy()
    prev_node = df.groupby(["routeid", "vehicleno"])["nodeid"].shift(1)
    df["is_new_passage"] = df["nodeid"] != prev_node
    passages = df[df["is_new_passage"]].copy()
    passages = passages.rename(columns={"snapshot_ts_utc": "passage_ts_utc"})
    return passages[
        ["routeid", "vehicleno", "nodeid", "nodeord", "passage_ts_utc"]
    ].reset_index(drop=True)


def compute_observed_intervals(passages_df: pd.DataFrame) -> pd.DataFrame:
    """For each (routeid, nodeid), compute the gap (minutes) between successive vehicles.

    An observed interval is the time between the passage of one vehicle and
    the passage of the *next* vehicle at the same station. Same vehicle
    passing twice (e.g. a circular route) yields a valid interval too —
    both entries contribute to headway reconstruction.

    Output: one row per completed interval.
        routeid | nodeid | vehicleno_prev | vehicleno_next
                | t_prev | t_next | observed_interval_min
    """
    if passages_df.empty:
        return pd.DataFrame(
            columns=[
                "routeid",
                "nodeid",
                "vehicleno_prev",
                "vehicleno_next",
                "t_prev",
                "t_next",
                "observed_interval_min",
            ]
        )

    df = passages_df.sort_values(["routeid", "nodeid", "passage_ts_utc"]).copy()
    df["vehicleno_prev"] = df.groupby(["routeid", "nodeid"])["vehicleno"].shift(1)
    df["t_prev"] = df.groupby(["routeid", "nodeid"])["passage_ts_utc"].shift(1)
    df = df.rename(
        columns={"vehicleno": "vehicleno_next", "passage_ts_utc": "t_next"}
    )
    df = df.dropna(subset=["t_prev"]).copy()
    df["observed_interval_min"] = (
        (df["t_next"] - df["t_prev"]).dt.total_seconds() / 60.0
    )
    df = df[df["observed_interval_min"] > 0]
    return df[
        [
            "routeid",
            "nodeid",
            "vehicleno_prev",
            "vehicleno_next",
            "t_prev",
            "t_next",
            "observed_interval_min",
        ]
    ].reset_index(drop=True)


def aggregate_rdi(
    intervals_df: pd.DataFrame,
    prescribed_df: pd.DataFrame,
    tz: str = "Asia/Seoul",
    bin_minutes: int = 30,
) -> pd.DataFrame:
    """Bin observed intervals by (route × station × time_bin) and compute RDI.

    For each bin, ``observed_interval`` is the mean of constituent intervals,
    ``rdi_variance`` is their population stdev (ddof=0, so single-observation
    bins carry variance 0 rather than NaN).

    RDI magnitude:

        rdi_magnitude = | observed_interval − prescribed_interval |
                        / prescribed_interval

    where ``prescribed_interval`` is looked up per (route_id, daytype) from
    ``prescribed_df``. ``daytype`` is resolved from the bin's local time.

    **Bin width note** (Day 2, 2026-04-23): the handoff specified 5-minute
    bins, but Changwon's minimum observed headway is 20 min (BRT6000) and
    the maximum is 94 min (271). A 5-min bin therefore almost never holds
    two intervals at the same station, so variance would collapse to 0
    everywhere and ``vitality_query`` could never fire. The default is set
    to 30 min empirically — it yields multi-observation bins on all three
    routes (271: 2, 710: 56, BRT6000: 289 at the Day-2 11:20 cutoff).
    Finer bins can be requested explicitly when headways allow.
    """
    if intervals_df.empty:
        return pd.DataFrame(
            columns=[
                "route_id",
                "station_id",
                "time_bin",
                "observed_interval",
                "prescribed_interval",
                "rdi_magnitude",
                "rdi_variance",
                "n_observations",
            ]
        )

    df = intervals_df.copy()
    df["t_bin_local"] = (
        df["t_next"].dt.tz_convert(tz).dt.floor(f"{bin_minutes}min")
    )
    df["daytype"] = df["t_bin_local"].apply(resolve_daytype)

    # Population stdev (ddof=0): a bin with a single observation has spread 0
    # by definition rather than NaN (sample stdev). This keeps rdi_variance
    # well-defined for the quantile computation in critique_flag, while the
    # ``n_observations`` column preserves the information that a variance
    # of 0 may mean "no intervals to measure" rather than "perfectly regular".
    grouped = (
        df.groupby(["routeid", "nodeid", "t_bin_local", "daytype"])
        .agg(
            observed_interval=("observed_interval_min", "mean"),
            rdi_variance=("observed_interval_min", lambda s: float(s.std(ddof=0))),
            n_observations=("observed_interval_min", "size"),
        )
        .reset_index()
    )
    grouped["rdi_variance"] = grouped["rdi_variance"].fillna(0.0)

    prescribed_lookup = prescribed_df.set_index(["route_id", "daytype"])[
        "peak_interval_min"
    ].to_dict()
    grouped["prescribed_interval"] = grouped.apply(
        lambda r: prescribed_lookup.get((r["routeid"], r["daytype"])), axis=1
    )
    grouped = grouped.dropna(subset=["prescribed_interval"])
    grouped["rdi_magnitude"] = (
        (grouped["observed_interval"] - grouped["prescribed_interval"]).abs()
        / grouped["prescribed_interval"]
    )

    grouped = grouped.rename(
        columns={
            "routeid": "route_id",
            "nodeid": "station_id",
            "t_bin_local": "time_bin",
        }
    )
    return grouped[
        [
            "route_id",
            "station_id",
            "time_bin",
            "observed_interval",
            "prescribed_interval",
            "rdi_magnitude",
            "rdi_variance",
            "n_observations",
        ]
    ].reset_index(drop=True)


def save_rdi(df: pd.DataFrame, out_path: Path) -> Path:
    """Persist the RDI magnitude table as parquet."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, compression="snappy", index=False)
    log.info("rdi_written", path=str(out_path), rows=len(df))
    return out_path


def compute_rdi(
    locations_df: pd.DataFrame,
    prescribed_df: pd.DataFrame,
    tz: str = "Asia/Seoul",
    bin_minutes: int = 30,
) -> pd.DataFrame:
    """End-to-end: locations → passages → intervals → RDI DataFrame.

    Convenience wrapper used by the Day-2 preview and the pytest smoke.
    """
    passages = compute_vehicle_passages(locations_df)
    intervals = compute_observed_intervals(passages)
    return aggregate_rdi(intervals, prescribed_df, tz=tz, bin_minutes=bin_minutes)


# ---------------------------------------------------------------------------
# Per-city orchestrator + CLI entry point
# ---------------------------------------------------------------------------


def run_for_city(
    city: str,
    for_date: date,
    raw_base: Path = Path("data/raw/tago"),
    processed_base: Path = Path("data/processed/tago"),
    bin_minutes: int = 30,
    tz: str = "Asia/Seoul",
    use_existing_prescribed: bool = False,
) -> dict:
    """Build prescribed + RDI parquets for a single city.

    Writes:
        {processed_base}/prescribed_intervals_{city}.parquet  (unless
            ``use_existing_prescribed`` is True and the file already exists)
        {processed_base}/rdi_{city}_{YYYYMMDD}.parquet

    ``use_existing_prescribed=True`` is how externally-sourced prescribed
    data (e.g. Sejong via bis.sejong.go.kr scrape) survives a re-run. The
    existing parquet is loaded as-is, with whatever ``prescribed_source``
    tagging the scraper wrote.
    """
    stamp = for_date.strftime("%Y%m%d")
    prescribed_path = processed_base / f"prescribed_intervals_{city}.parquet"
    if use_existing_prescribed and prescribed_path.exists():
        prescribed_df = pd.read_parquet(prescribed_path)
        log.info(
            "prescribed_intervals_reused",
            path=str(prescribed_path),
            rows=int(len(prescribed_df)),
            sources=sorted(
                prescribed_df["prescribed_source"].dropna().unique().tolist()
                if "prescribed_source" in prescribed_df.columns
                else ["unlabeled"]
            ),
        )
    else:
        routes_df = load_routes_parquet(raw_base / "routes", city, for_date)
        prescribed_df = build_prescribed_intervals(routes_df)
        save_prescribed_intervals(prescribed_df, prescribed_path)

    locations_df = load_locations(raw_base / "locations", for_date=for_date, city=city)
    rdi_df = compute_rdi(
        locations_df, prescribed_df, tz=tz, bin_minutes=bin_minutes
    )
    rdi_path = save_rdi(
        rdi_df,
        processed_base / f"rdi_{city}_{stamp}.parquet",
    )
    return {
        "city": city,
        "for_date": stamp,
        "prescribed_path": str(prescribed_path),
        "rdi_path": str(rdi_path),
        "rdi_rows": int(len(rdi_df)),
        "locations_rows": int(len(locations_df)),
    }


def _load_city_slugs(cities_yaml: Path) -> list[str]:
    import yaml

    with cities_yaml.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return sorted((cfg.get("cities") or {}).keys())


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute RDI v0 per city — writes prescribed + rdi parquets."
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City slug (e.g. changwon). Omit with --all to run every city "
        "in --cities.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run for every city in --cities. Mutually exclusive with --city.",
    )
    parser.add_argument(
        "--cities",
        type=Path,
        default=Path("config/cities.yaml"),
        help="Multi-city manifest (default config/cities.yaml)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Local date YYYYMMDD (default: today in Asia/Seoul)",
    )
    parser.add_argument(
        "--raw-base",
        type=Path,
        default=Path("data/raw/tago"),
    )
    parser.add_argument(
        "--processed-base",
        type=Path,
        default=Path("data/processed/tago"),
    )
    parser.add_argument(
        "--bin-minutes",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--use-existing-prescribed",
        action="store_true",
        help="Skip rebuilding prescribed_intervals_{city}.parquet from TAGO "
        "routes. Required for Sejong after bis.sejong.go.kr scrape.",
    )
    args = parser.parse_args(argv)

    if not args.all and args.city is None:
        parser.error("either --city <slug> or --all is required")
    if args.all and args.city is not None:
        parser.error("--city and --all are mutually exclusive")

    if args.date:
        for_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    cities = _load_city_slugs(args.cities) if args.all else [args.city]
    results: list[dict] = []
    for city in cities:
        try:
            r = run_for_city(
                city=city,
                for_date=for_date,
                raw_base=args.raw_base,
                processed_base=args.processed_base,
                bin_minutes=args.bin_minutes,
                use_existing_prescribed=args.use_existing_prescribed,
            )
            results.append(r)
            print(
                f"✓ {city:<20} rdi_rows={r['rdi_rows']:<5} "
                f"locations_rows={r['locations_rows']:<6} → {r['rdi_path']}"
            )
        except FileNotFoundError as exc:
            print(f"✗ {city:<20} SKIPPED: {exc}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
