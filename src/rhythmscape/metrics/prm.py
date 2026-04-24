"""Pedestrian Residue Map (PRM) v0 — pedestrian-surface residue metric.

Implements the three-factor product from ``docs/analysis/prm_spec.md``:

    PRM(g, t) = walk_connectivity(g) × inverse_car_dominance(g, t)
                × settlement_density(g)

v0 simplifications (per prm_spec.md §3):
- walk_connectivity: OSM pedestrian-accessible way length / cell_area,
  clipped and normalized to [0, 1].
- inverse_car_dominance: 1 - ARDI_v0_normalized where normalization is
  city-scoped (ARDI / ARDI_max_in_city).
- settlement_density: constant 1.0 until SGIS population grid is wired
  in (v0.5 work).

Output column set keeps provenance of each factor so downstream analysis
can inspect which component drove a given PRM value.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import date, datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely.wkt
import structlog

log = structlog.get_logger(__name__)


# Pedestrian-accessible highway classes.
# - footway / path / pedestrian / steps / living_street: primary walking
# - residential: mixed-use but typically walkable in Korean cities
# - track: rural footpath
# - service: semi-walkable (parking lots, driveways) — INCLUDED per §2.1
#   but can be stripped by passing include_service=False.
PEDESTRIAN_CLASSES = frozenset(
    [
        "footway",
        "path",
        "pedestrian",
        "steps",
        "living_street",
        "residential",
        "track",
        "service",
    ]
)

KOREA_TM_EPSG = 5186


def export_pedestrian_geojson(pbf_path: Path, out_geojson: Path) -> Path:
    """Filter the city PBF to pedestrian highways and export to GeoJSON."""
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    filtered_pbf = out_geojson.with_suffix(".walk.pbf")
    subprocess.run(
        [
            "osmium",
            "tags-filter",
            str(pbf_path),
            "w/highway",
            "-o",
            str(filtered_pbf),
            "--overwrite",
        ],
        check=True,
    )
    subprocess.run(
        [
            "osmium",
            "export",
            str(filtered_pbf),
            "-o",
            str(out_geojson),
            "--overwrite",
            "--geometry-types=linestring",
        ],
        check=True,
    )
    log.info("walk_osmium_export", pbf=str(pbf_path), geojson=str(out_geojson))
    return out_geojson


def load_pedestrian_ways(geojson_path: Path, include_service: bool = True) -> gpd.GeoDataFrame:
    """Load pedestrian-accessible highway ways."""
    gdf = gpd.read_file(geojson_path)
    classes = set(PEDESTRIAN_CLASSES)
    if not include_service:
        classes.discard("service")
    gdf = gdf[gdf["highway"].isin(classes)].copy().reset_index(drop=True)
    return gdf


def load_ardi_grid(ardi_parquet: Path) -> gpd.GeoDataFrame:
    """Rehydrate the ARDI v0 parquet into a GeoDataFrame in EPSG:5186."""
    df = pd.read_parquet(ardi_parquet)
    df["geometry"] = df["geometry_wkt"].apply(shapely.wkt.loads)
    return gpd.GeoDataFrame(
        df.drop(columns="geometry_wkt"),
        geometry="geometry",
        crs=f"EPSG:{int(df['crs_epsg'].iloc[0])}",
    )


def compute_walk_connectivity(
    grid: gpd.GeoDataFrame,
    walk_ways: gpd.GeoDataFrame,
    saturation_length_per_m2: float = 0.01,
) -> pd.DataFrame:
    """Walk length per cell normalized by a saturation constant.

    ``saturation_length_per_m2`` = 0.01 means 0.01 m walkway per m² cell
    (= 10 m per 1000 m²) reaches walk_connectivity = 1.0. A 500 m cell
    (= 250,000 m²) saturates at 2,500 m of walkable way, which is
    reasonable for dense Korean residential blocks.
    """
    if walk_ways.crs != grid.crs:
        walk_ways = walk_ways.to_crs(grid.crs)
    cell_area_m2 = float(grid.geometry.area.iloc[0])

    inter = gpd.overlay(
        walk_ways[["highway", "geometry"]],
        grid[["cell_id", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    if inter.empty:
        out = grid[["cell_id"]].copy()
        out["walk_length_m"] = 0.0
        out["n_walk_ways"] = 0
        out["walk_connectivity"] = 0.0
        return out

    inter["length_m"] = inter.geometry.length
    agg = (
        inter.groupby("cell_id")
        .agg(
            walk_length_m=("length_m", "sum"),
            n_walk_ways=("length_m", "size"),
        )
        .reset_index()
    )
    agg["walk_connectivity"] = (
        (agg["walk_length_m"] / cell_area_m2) / saturation_length_per_m2
    ).clip(upper=1.0)
    return agg


def compute_prm_v0(
    city: str,
    ardi_parquet: Path,
    pbf_path: Path,
    osm_base: Path = Path("data/processed/osm"),
    saturation_length_per_m2: float = 0.01,
    include_service_walk: bool = True,
) -> gpd.GeoDataFrame:
    """End-to-end PRM v0 for one city. Returns a GeoDataFrame ready to save."""
    # 1. Walk network → GeoJSON → pedestrian ways
    walk_geojson = osm_base / f"{city}_walk.geojson"
    export_pedestrian_geojson(pbf_path, walk_geojson)
    walk_ways = load_pedestrian_ways(walk_geojson, include_service=include_service_walk)
    log.info("walk_ways_loaded", city=city, n=len(walk_ways))

    # 2. ARDI grid (cell_id, geometry, ardi_v0)
    ardi_grid = load_ardi_grid(ardi_parquet)

    # 3. walk_connectivity per cell
    walk_agg = compute_walk_connectivity(
        ardi_grid, walk_ways, saturation_length_per_m2=saturation_length_per_m2
    )

    # 4. Merge
    merged = ardi_grid.merge(walk_agg, on="cell_id", how="left")
    merged["walk_length_m"] = merged["walk_length_m"].fillna(0.0)
    merged["n_walk_ways"] = merged["n_walk_ways"].fillna(0).astype(int)
    merged["walk_connectivity"] = merged["walk_connectivity"].fillna(0.0)

    # 5. inverse_car_dominance (city-scoped normalization)
    ardi_max = float(merged["ardi_v0"].max())
    if ardi_max > 0:
        merged["ardi_normalized"] = merged["ardi_v0"] / ardi_max
    else:
        merged["ardi_normalized"] = 0.0
    merged["inverse_car_dominance"] = 1.0 - merged["ardi_normalized"]

    # 6. settlement_density (v0 constant)
    merged["settlement_density"] = 1.0

    # 7. PRM v0
    merged["prm_v0"] = (
        merged["walk_connectivity"]
        * merged["inverse_car_dominance"]
        * merged["settlement_density"]
    )
    return merged


def save_prm(gdf: gpd.GeoDataFrame, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geometry_wkt"] = gdf.geometry.to_wkt()
    df["crs_epsg"] = KOREA_TM_EPSG
    df.to_parquet(out_path, compression="snappy", index=False)
    log.info("prm_v0_written", path=str(out_path), rows=len(df))
    return out_path


def run_for_city(
    city: str,
    ardi_parquet: Path,
    pbf_path: Path,
    osm_base: Path = Path("data/processed/osm"),
    prm_base: Path = Path("data/processed/prm"),
    for_date: date | None = None,
    saturation_length_per_m2: float = 0.01,
) -> dict:
    if for_date is None:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    gdf = compute_prm_v0(
        city=city,
        ardi_parquet=ardi_parquet,
        pbf_path=pbf_path,
        osm_base=osm_base,
        saturation_length_per_m2=saturation_length_per_m2,
    )
    stamp = for_date.strftime("%Y%m%d")
    out_path = prm_base / f"prm_{city}_{stamp}.parquet"
    save_prm(gdf, out_path)

    return {
        "city": city,
        "out_path": str(out_path),
        "n_cells": int(len(gdf)),
        "n_cells_walk": int((gdf["walk_length_m"] > 0).sum()),
        "mean_walk_connectivity": float(gdf["walk_connectivity"].mean()),
        "mean_inverse_car_dominance": float(gdf["inverse_car_dominance"].mean()),
        "mean_prm_v0": float(gdf["prm_v0"].mean()),
        "max_prm_v0": float(gdf["prm_v0"].max()),
        "n_walk_ways": int(gdf["n_walk_ways"].sum()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute PRM v0 per city.")
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Single city slug. Mutually exclusive with --all.",
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--cities", type=Path, default=Path("config/cities.yaml"))
    parser.add_argument("--pbf", type=Path, default=None)
    parser.add_argument(
        "--ardi-base", type=Path, default=Path("data/processed/ardi")
    )
    parser.add_argument("--osm-base", type=Path, default=Path("data/processed/osm"))
    parser.add_argument("--prm-base", type=Path, default=Path("data/processed/prm"))
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--saturation-length-per-m2", type=float, default=0.01)
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
    stamp = for_date.strftime("%Y%m%d")

    if args.all:
        import yaml

        with args.cities.open("r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh)
        cities = sorted((cfg.get("cities") or {}).keys())
    else:
        cities = [args.city]

    for city in cities:
        ardi_path = args.ardi_base / f"ardi_{city}_{stamp}.parquet"
        if not ardi_path.exists():
            print(f"✗ {city:<20} SKIP: ARDI not found at {ardi_path}")
            continue
        pbf = args.pbf if args.pbf and not args.all else (args.osm_base / f"{city}.pbf")
        if not pbf.exists():
            print(f"✗ {city:<20} SKIP: PBF not found at {pbf}")
            continue
        r = run_for_city(
            city=city,
            ardi_parquet=ardi_path,
            pbf_path=pbf,
            osm_base=args.osm_base,
            prm_base=args.prm_base,
            for_date=for_date,
            saturation_length_per_m2=args.saturation_length_per_m2,
        )
        print(
            f"✓ {r['city']:<20} cells={r['n_cells']:<5} walk={r['n_cells_walk']:<5} "
            f"mean_PRM={r['mean_prm_v0']:.4f}  max={r['max_prm_v0']:.4f}  "
            f"walk_conn={r['mean_walk_connectivity']:.4f}  "
            f"inv_car={r['mean_inverse_car_dominance']:.4f}  ways={r['n_walk_ways']}"
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
