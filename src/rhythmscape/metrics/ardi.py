"""Automotive Rhythm Dominance Index (ARDI) v0 — static OSM-based.

v0 covers the two static components of the full ARDI formula
(``rhythmscape-spec.md`` §3.1):

    ARDI_v0(g) = w2 · road_space_ratio(g) + w3 · speed_regime(g)
               = 0.25 · road_space_ratio(g) + 0.15 · speed_regime(g)

The three dynamic components (``car_throughput_norm``,
``transit_frequency_norm``, ``walkable_surface_ratio``) will be added in
later revisions once their data sources are wired — for now v0 produces
a partial score scoped to the OSM-encoded spatial regime of the car
(where driving-surface takes up space, and at what designed velocity).

Pipeline:
1. Load OSM highway ways from a city-clipped ``.pbf`` (via osmium CLI
   to GeoJSON, then geopandas).
2. Estimate width and max-speed per way using ``highway`` class
   defaults where OSM tags are missing (Korean-context heuristics).
3. Build a 500 m grid in EPSG:5186 (GRS80 중부원점 TM).
4. For each cell: sum (length × width) of driving-relevant ways ⇒
   road area; divide by cell area ⇒ road_space_ratio.
5. For each cell: sum length of ways with effective max-speed ≥ 50 km/h
   divided by total driving-way length in cell ⇒ speed_regime.
6. Combine into ARDI_v0.

Output parquet: ``data/processed/osm/ardi_v0_{city}.parquet``
Columns: cell_id, geometry (WKT), road_space_ratio, speed_regime,
ardi_v0, road_length_m, road_area_m2, n_ways.
"""

from __future__ import annotations

import argparse
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import shapely.geometry
import structlog

log = structlog.get_logger(__name__)


# Korean-context driving-way defaults. Widths in metres, max-speed in km/h.
# Sources: 국토교통부 도로의 구조·시설 기준에 관한 규칙 + OSM tagging convention
# summaries for ROK. Used only when the OSM way lacks a ``width`` or
# ``maxspeed`` tag.
DRIVING_CLASSES: dict[str, tuple[float, int]] = {
    "motorway": (25.0, 100),
    "motorway_link": (10.0, 70),
    "trunk": (18.0, 80),
    "trunk_link": (10.0, 60),
    "primary": (15.0, 60),
    "primary_link": (8.0, 50),
    "secondary": (12.0, 60),
    "secondary_link": (8.0, 50),
    "tertiary": (9.0, 50),
    "tertiary_link": (7.0, 40),
    "unclassified": (7.0, 50),
    "residential": (6.0, 30),
    "living_street": (5.0, 20),
    "service": (4.0, 20),
}

# Classes we explicitly exclude from ARDI (non-driving surfaces).
NON_DRIVING_CLASSES = frozenset(
    [
        "footway",
        "path",
        "track",
        "pedestrian",
        "steps",
        "cycleway",
        "bridleway",
        "corridor",
        "elevator",
        "platform",
        "raceway",
        "construction",
        "proposed",
    ]
)

KOREA_TM_EPSG = 5186


# ---------------------------------------------------------------------------
# OSM loader
# ---------------------------------------------------------------------------


def export_highways_geojson(pbf_path: Path, out_geojson: Path) -> Path:
    """Run ``osmium`` to extract highway ways from a PBF to GeoJSON.

    Idempotent: overwrites ``out_geojson``. Requires ``osmium`` CLI.
    """
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    # 1. Filter PBF to highway ways
    filtered_pbf = out_geojson.with_suffix(".highway.pbf")
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
    # 2. Export to GeoJSON (linestrings)
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
    log.info("osmium_export", pbf=str(pbf_path), geojson=str(out_geojson))
    return out_geojson


def load_highways(geojson_path: Path) -> gpd.GeoDataFrame:
    """Load the highway GeoJSON into a GeoDataFrame and attach width/maxspeed defaults."""
    gdf = gpd.read_file(geojson_path)
    # Drop non-driving classes early
    gdf = gdf[~gdf["highway"].isin(NON_DRIVING_CLASSES)].copy()
    # Drop anything not in our driving class table (e.g. rare custom values)
    gdf = gdf[gdf["highway"].isin(DRIVING_CLASSES)].copy()
    gdf = gdf.reset_index(drop=True)

    # Attach class defaults
    default_widths = gdf["highway"].map({k: v[0] for k, v in DRIVING_CLASSES.items()})
    default_speeds = gdf["highway"].map({k: v[1] for k, v in DRIVING_CLASSES.items()})

    # Parse OSM width tag when present (may be "3.5 m" or plain float string)
    def parse_width(s):
        if s is None or pd.isna(s):
            return None
        try:
            return float(str(s).split()[0])
        except (ValueError, IndexError):
            return None

    def parse_speed(s):
        if s is None or pd.isna(s):
            return None
        try:
            txt = str(s).strip()
            if "mph" in txt.lower():
                return float(txt.lower().replace("mph", "").strip()) * 1.60934
            return float(txt.split()[0])
        except (ValueError, IndexError):
            return None

    parsed_width = gdf["width"].apply(parse_width) if "width" in gdf.columns else pd.Series(
        [None] * len(gdf), index=gdf.index
    )
    parsed_speed = gdf["maxspeed"].apply(parse_speed) if "maxspeed" in gdf.columns else pd.Series(
        [None] * len(gdf), index=gdf.index
    )

    gdf["est_width_m"] = parsed_width.fillna(default_widths).astype(float)
    gdf["est_maxspeed_kph"] = parsed_speed.fillna(default_speeds).astype(float)
    return gdf


# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------


def build_grid(
    bounds_wgs84: tuple[float, float, float, float],
    cell_size_m: int = 500,
) -> gpd.GeoDataFrame:
    """Construct a square grid of ``cell_size_m`` cells over ``bounds_wgs84``.

    Grid is built in EPSG:5186 (Korean metric TM) so cell sizes are truly
    metric, then returned still in EPSG:5186 (caller projects to WGS84
    for map overlay if needed).
    """
    bbox = gpd.GeoDataFrame(
        geometry=[shapely.geometry.box(*bounds_wgs84)], crs="EPSG:4326"
    ).to_crs(epsg=KOREA_TM_EPSG)
    xmin, ymin, xmax, ymax = bbox.total_bounds

    # Snap to nearest multiple of cell_size for tidy alignment.
    xmin = np.floor(xmin / cell_size_m) * cell_size_m
    ymin = np.floor(ymin / cell_size_m) * cell_size_m
    xmax = np.ceil(xmax / cell_size_m) * cell_size_m
    ymax = np.ceil(ymax / cell_size_m) * cell_size_m

    cols = np.arange(xmin, xmax, cell_size_m)
    rows = np.arange(ymin, ymax, cell_size_m)

    cells = []
    for cx in cols:
        for cy in rows:
            cells.append(shapely.geometry.box(cx, cy, cx + cell_size_m, cy + cell_size_m))

    grid = gpd.GeoDataFrame(
        {"cell_id": range(len(cells)), "geometry": cells},
        crs=f"EPSG:{KOREA_TM_EPSG}",
    )
    log.info("grid_built", n_cells=len(grid), cell_size_m=cell_size_m, bounds=bounds_wgs84)
    return grid


# ---------------------------------------------------------------------------
# Component computations
# ---------------------------------------------------------------------------


def compute_components(
    grid: gpd.GeoDataFrame,
    highways: gpd.GeoDataFrame,
    speed_threshold_kph: float = 50.0,
) -> pd.DataFrame:
    """Compute road_space_ratio and speed_regime per grid cell.

    Both in [0, 1]. road_space_ratio may exceed 1 when overlapping roads
    saturate a cell — we clip to 1 for the ARDI combination.
    """
    if highways.crs != grid.crs:
        highways = highways.to_crs(grid.crs)
    cell_area_m2 = float(grid.geometry.area.iloc[0])

    # Spatial intersection of each way with each overlapping cell.
    # Using overlay with how='intersection' is correct but expensive; for
    # ~14k ways × ~2k cells a spatial index-assisted intersection is
    # needed. We use geopandas overlay with how='intersection' which
    # internally uses STRtree.
    inter = gpd.overlay(
        highways[["highway", "est_width_m", "est_maxspeed_kph", "geometry"]],
        grid[["cell_id", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    if inter.empty:
        log.warning("no_intersection", highways=len(highways), grid=len(grid))
        grid_out = grid.copy()
        grid_out["road_length_m"] = 0.0
        grid_out["road_area_m2"] = 0.0
        grid_out["road_space_ratio"] = 0.0
        grid_out["speed_regime"] = 0.0
        grid_out["n_ways"] = 0
        return grid_out

    inter["length_m"] = inter.geometry.length
    inter["area_m2"] = inter["length_m"] * inter["est_width_m"]
    inter["is_highspeed"] = inter["est_maxspeed_kph"] >= speed_threshold_kph
    inter["highspeed_length_m"] = np.where(
        inter["is_highspeed"], inter["length_m"], 0.0
    )

    agg = (
        inter.groupby("cell_id")
        .agg(
            road_length_m=("length_m", "sum"),
            road_area_m2=("area_m2", "sum"),
            highspeed_length_m=("highspeed_length_m", "sum"),
            n_ways=("length_m", "size"),
        )
        .reset_index()
    )
    agg["road_space_ratio"] = (agg["road_area_m2"] / cell_area_m2).clip(upper=1.0)
    agg["speed_regime"] = np.where(
        agg["road_length_m"] > 0,
        agg["highspeed_length_m"] / agg["road_length_m"],
        0.0,
    )

    result = grid.merge(agg, on="cell_id", how="left")
    for col in ("road_length_m", "road_area_m2", "road_space_ratio", "speed_regime", "n_ways"):
        if col == "n_ways":
            result[col] = result[col].fillna(0).astype(int)
        else:
            result[col] = result[col].fillna(0.0)
    return result


# ---------------------------------------------------------------------------
# ARDI v0 combination
# ---------------------------------------------------------------------------


DEFAULT_WEIGHTS_V0 = {
    "w_road_space_ratio": 0.25,  # w2 in spec §3.1
    "w_speed_regime": 0.15,  # w3 in spec §3.1
}


def compute_ardi_v0(
    grid_with_components: gpd.GeoDataFrame,
    weights: dict | None = None,
) -> gpd.GeoDataFrame:
    w = weights or DEFAULT_WEIGHTS_V0
    out = grid_with_components.copy()
    out["ardi_v0"] = (
        w["w_road_space_ratio"] * out["road_space_ratio"]
        + w["w_speed_regime"] * out["speed_regime"]
    )
    return out


def save_ardi(gdf: gpd.GeoDataFrame, out_path: Path) -> Path:
    """Write the ARDI grid to parquet (geometry as WKT for portability)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geometry_wkt"] = gdf.geometry.to_wkt()
    df["crs_epsg"] = KOREA_TM_EPSG
    df.to_parquet(out_path, compression="snappy", index=False)
    log.info("ardi_v0_written", path=str(out_path), rows=len(df))
    return out_path


def run_for_city(
    city: str,
    pbf_path: Path,
    osm_base: Path = Path("data/processed/osm"),
    ardi_base: Path = Path("data/processed/ardi"),
    cell_size_m: int = 500,
    weights: dict | None = None,
    for_date: date | None = None,
) -> dict:
    """End-to-end: pbf → highways → grid → components → ARDI_v0 → parquet.

    Outputs under ``ardi_base`` with a date-stamped filename so multiple
    city runs coexist. Intermediate GeoJSON stays under ``osm_base``.
    """
    if for_date is None:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    geojson_path = osm_base / f"{city}_highway.geojson"
    export_highways_geojson(pbf_path, geojson_path)
    highways = load_highways(geojson_path)
    bounds = tuple(highways.to_crs("EPSG:4326").total_bounds)
    grid = build_grid(bounds, cell_size_m=cell_size_m)
    grid_comp = compute_components(grid, highways)
    ardi = compute_ardi_v0(grid_comp, weights)
    stamp = for_date.strftime("%Y%m%d")
    out_path = ardi_base / f"ardi_{city}_{stamp}.parquet"
    save_ardi(ardi, out_path)
    return {
        "city": city,
        "out_path": str(out_path),
        "n_cells": int(len(ardi)),
        "n_cells_with_roads": int((ardi["road_length_m"] > 0).sum()),
        "mean_ardi": float(ardi["ardi_v0"].mean()),
        "max_ardi": float(ardi["ardi_v0"].max()),
        "mean_road_space_ratio": float(ardi["road_space_ratio"].mean()),
        "mean_speed_regime": float(ardi["speed_regime"].mean()),
        "n_ways_loaded": int(len(highways)),
    }


def _load_city_slugs(cities_yaml: Path) -> list[str]:
    import yaml

    with cities_yaml.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    return sorted((cfg.get("cities") or {}).keys())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute ARDI v0 per city.")
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="Single city slug. Mutually exclusive with --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run for every city in --cities manifest.",
    )
    parser.add_argument(
        "--cities",
        type=Path,
        default=Path("config/cities.yaml"),
    )
    parser.add_argument(
        "--pbf",
        type=Path,
        default=None,
        help="Single-city override path. Ignored with --all.",
    )
    parser.add_argument(
        "--osm-base",
        type=Path,
        default=Path("data/processed/osm"),
    )
    parser.add_argument(
        "--ardi-base",
        type=Path,
        default=Path("data/processed/ardi"),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="YYYYMMDD for output filename (default: today Asia/Seoul)",
    )
    parser.add_argument("--cell-size-m", type=int, default=500)
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
    for city in cities:
        pbf = args.pbf if args.pbf and not args.all else (args.osm_base / f"{city}.pbf")
        if not pbf.exists():
            print(f"✗ {city:<20} SKIP: PBF not found at {pbf}")
            continue
        r = run_for_city(
            city=city,
            pbf_path=pbf,
            osm_base=args.osm_base,
            ardi_base=args.ardi_base,
            cell_size_m=args.cell_size_m,
            for_date=for_date,
        )
        print(
            f"✓ {r['city']:<20} cells={r['n_cells']:<5} roads={r['n_cells_with_roads']:<5} "
            f"mean_ARDI={r['mean_ardi']:.4f}  max={r['max_ardi']:.4f}  "
            f"rsr={r['mean_road_space_ratio']:.4f}  sr={r['mean_speed_regime']:.4f}  "
            f"ways={r['n_ways_loaded']}"
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
