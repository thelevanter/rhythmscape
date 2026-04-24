"""Friction Zone v0 — cells where car dominance and pedestrian infrastructure co-exist.

**Design correction (Day 3 afternoon, 2026-04-24)**: initial v0 used
PRM >= p90 as the pedestrian condition, but PRM_v0 = walk_connectivity ×
(1 - ARDI_normalized) × settlement_density. The (1 - ARDI_norm) factor
makes PRM↑ structurally anti-correlated with ARDI↑, so the intersection
"ARDI top decile ∩ PRM top decile" is mathematically excluded by
construction. Empirical verification on all 4 cities confirmed 0
friction cells — a design artefact, not an absence of friction.

Corrected definition: substitute ``walk_connectivity`` (the independent
component of PRM) for the pedestrian condition. Friction is then:

    ARDI_v0              >= p90 (city-scoped)
    walk_connectivity    >= p90 (city-scoped)

This captures the original intent — a spatial pocket where the car regime
dominates *and* pedestrian infrastructure is simultaneously dense, i.e.
where two rhythm systems physically contest the same ground. PRM is still
computed and joined for interpretation, but not part of the gate.

Output: ``data/processed/friction/friction_zones_{city}_{YYYYMMDD}.parquet``
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely.wkt
import structlog

log = structlog.get_logger(__name__)


def load_layer(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_parquet(path)
    df["geometry"] = df["geometry_wkt"].apply(shapely.wkt.loads)
    return gpd.GeoDataFrame(
        df.drop(columns="geometry_wkt"),
        geometry="geometry",
        crs=f"EPSG:{int(df['crs_epsg'].iloc[0])}",
    )


def compute_friction_zones(
    city: str,
    ardi_parquet: Path,
    prm_parquet: Path,
    ardi_decile: float = 0.9,
    walk_decile: float = 0.9,
) -> gpd.GeoDataFrame:
    """Join ARDI + PRM on cell_id, flag top-decile ARDI ∩ top-decile walk_connectivity."""
    ardi = load_layer(ardi_parquet)[
        ["cell_id", "ardi_v0", "road_length_m", "speed_regime", "road_space_ratio", "geometry"]
    ]
    prm = load_layer(prm_parquet)[
        ["cell_id", "prm_v0", "walk_connectivity", "inverse_car_dominance", "walk_length_m"]
    ]
    merged = ardi.merge(prm, on="cell_id", how="inner")

    ardi_cut = float(merged["ardi_v0"].quantile(ardi_decile))
    walk_cut = float(merged["walk_connectivity"].quantile(walk_decile))

    merged["ardi_in_top_decile"] = merged["ardi_v0"] >= ardi_cut
    merged["walk_in_top_decile"] = merged["walk_connectivity"] >= walk_cut
    merged["is_friction_zone"] = (
        merged["ardi_in_top_decile"] & merged["walk_in_top_decile"]
    )

    # Friction score ranks cells by joint intensity of the two gates.
    # Using ARDI × walk_connectivity keeps it on the same scale as the
    # thresholds and avoids the (1-ARDI) collapse that broke PRM-based
    # ranking.
    merged["friction_score"] = merged["ardi_v0"] * merged["walk_connectivity"]

    log.info(
        "friction_zones_computed",
        city=city,
        total_cells=int(len(merged)),
        ardi_cutoff=round(ardi_cut, 4),
        walk_cutoff=round(walk_cut, 4),
        friction_cells=int(merged["is_friction_zone"].sum()),
        friction_rate_pct=round(100 * merged["is_friction_zone"].mean(), 2),
    )
    return merged


def save_friction(
    gdf: gpd.GeoDataFrame, out_path: Path, flagged_only: bool = False
) -> Path:
    if flagged_only:
        gdf = gdf[gdf["is_friction_zone"]].copy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geometry_wkt"] = gdf.geometry.to_wkt()
    df["crs_epsg"] = int(gdf.crs.to_epsg())
    df.to_parquet(out_path, compression="snappy", index=False)
    log.info("friction_zones_written", path=str(out_path), rows=len(df), flagged_only=flagged_only)
    return out_path


def run_for_city(
    city: str,
    ardi_base: Path = Path("data/processed/ardi"),
    prm_base: Path = Path("data/processed/prm"),
    friction_base: Path = Path("data/processed/friction"),
    for_date: date | None = None,
) -> dict:
    if for_date is None:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()
    stamp = for_date.strftime("%Y%m%d")
    ardi_path = ardi_base / f"ardi_{city}_{stamp}.parquet"
    prm_path = prm_base / f"prm_{city}_{stamp}.parquet"

    gdf = compute_friction_zones(city, ardi_path, prm_path)
    out_path = friction_base / f"friction_zones_{city}_{stamp}.parquet"
    save_friction(gdf, out_path)

    fz = gdf[gdf["is_friction_zone"]]
    return {
        "city": city,
        "out_path": str(out_path),
        "total_cells": int(len(gdf)),
        "friction_cells": int(len(fz)),
        "friction_rate_pct": round(100 * len(fz) / max(len(gdf), 1), 2),
        "mean_friction_score": float(fz["friction_score"].mean()) if len(fz) else 0.0,
        "max_friction_score": float(fz["friction_score"].max()) if len(fz) else 0.0,
        "ardi_cutoff_p90": float(gdf["ardi_v0"].quantile(0.9)),
        "walk_cutoff_p90": float(gdf["walk_connectivity"].quantile(0.9)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", type=str, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--cities", type=Path, default=Path("config/cities.yaml"))
    parser.add_argument("--ardi-base", type=Path, default=Path("data/processed/ardi"))
    parser.add_argument("--prm-base", type=Path, default=Path("data/processed/prm"))
    parser.add_argument(
        "--friction-base", type=Path, default=Path("data/processed/friction")
    )
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args(argv)

    if not args.all and args.city is None:
        parser.error("either --city or --all required")
    if args.all and args.city is not None:
        parser.error("--city and --all are mutually exclusive")

    if args.date:
        for_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    if args.all:
        import yaml

        with args.cities.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        cities = sorted((cfg.get("cities") or {}).keys())
    else:
        cities = [args.city]

    for city in cities:
        try:
            r = run_for_city(
                city=city,
                ardi_base=args.ardi_base,
                prm_base=args.prm_base,
                friction_base=args.friction_base,
                for_date=for_date,
            )
        except FileNotFoundError as exc:
            print(f"✗ {city:<20} SKIP: {exc}")
            continue
        print(
            f"✓ {r['city']:<20} total={r['total_cells']:<5} friction={r['friction_cells']:<4} "
            f"rate={r['friction_rate_pct']:.2f}%  "
            f"ARDI_p90={r['ardi_cutoff_p90']:.4f}  walk_p90={r['walk_cutoff_p90']:.4f}  "
            f"max_score={r['max_friction_score']:.4f}"
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
