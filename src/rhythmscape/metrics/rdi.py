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


def load_locations(locations_dir: Path, for_date: date | None = None) -> pd.DataFrame:
    """Read every ``locations/*.parquet`` into one DataFrame, optionally filtered to one local date.

    Expected schema (from ``ingest/tago/locations.py``):
        snapshot_ts_utc, routeid, vehicleno, nodeid, nodenm, nodeord,
        gpslati, gpslong

    The filename encodes the local date (YYYYMMDD), so we use it to subset
    without parsing every file's content. When ``for_date`` is None, all
    files are concatenated.
    """
    if not locations_dir.exists():
        raise FileNotFoundError(f"locations directory missing: {locations_dir}")

    if for_date is not None:
        stamp = for_date.strftime("%Y%m%d")
        paths = sorted(locations_dir.glob(f"*_{stamp}_*.parquet"))
    else:
        paths = sorted(locations_dir.glob("*.parquet"))

    if not paths:
        raise FileNotFoundError(f"no locations parquet matched in {locations_dir}")

    frames = [pd.read_parquet(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    df["snapshot_ts_utc"] = pd.to_datetime(df["snapshot_ts_utc"], utc=True)
    df["vehicleno"] = df["vehicleno"].astype(str)
    df["routeid"] = df["routeid"].astype(str)
    df["nodeid"] = df["nodeid"].astype(str)
    log.info("locations_loaded", files=len(paths), rows=len(df))
    return df


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
