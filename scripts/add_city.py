#!/usr/bin/env python3
"""Rhythmscape ``add-city`` — single-shot scaling demo.

Minimal-mode flow (ARDI-only, no TAGO tick collection):
    1. Verify TAGO cityCode against the live registry
    2. Extract the city's OSM PBF from ``data/raw/osm/south-korea-latest.osm.pbf``
    3. Compute ARDI v0 on a 500 m grid
    4. Produce a heatmap PNG + a minimal markdown report
    5. Print total elapsed seconds (the 30-second demo budget)

Live demo (Day 4): ``python scripts/add_city.py --name gyeongju --mode minimal``
(the packaged form ``rhythmscape add-city --name ... --mode minimal`` is a
Day-5 polish item — a ``pyproject.toml`` ``[project.scripts]`` entry.)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = [
    "AppleGothic",
    "Apple SD Gothic Neo",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
from dotenv import load_dotenv


# Bounding boxes (approximate) for demonstration cities the user may request.
# Small to keep PBF extraction + ARDI fast for the 30-second demo target.
KNOWN_CITY_BBOX = {
    "gyeongju": (129.10, 35.75, 129.40, 35.95),
    "jinju": (128.00, 35.12, 128.20, 35.26),
    "sacheon": (128.00, 34.90, 128.15, 35.05),
}


def verify_citycode(name: str, city_code: int) -> str | None:
    """Confirm the TAGO cityCode maps to the requested city name."""
    load_dotenv(".env")
    from rhythmscape.ingest.tago.client import TagoClient
    from rhythmscape.ingest.tago.normalize import extract_items

    api_key = os.environ.get("TAGO_API_KEY", "")
    if not api_key:
        return None
    try:
        with TagoClient(api_key=api_key) as c:
            body = c.call(
                "BusSttnInfoInqireService",
                "getCtyCodeList",
                {"numOfRows": 500, "pageNo": 1},
            )
            for item in extract_items(body):
                if int(item.get("citycode", 0)) == city_code:
                    return str(item.get("cityname", ""))
    except Exception:
        return None
    return None


def extract_pbf(
    name: str,
    bbox: tuple[float, float, float, float],
    source_pbf: Path,
    out_pbf: Path,
) -> None:
    out_pbf.parent.mkdir(parents=True, exist_ok=True)
    w, s, e, n = bbox
    subprocess.run(
        [
            "osmium",
            "extract",
            "--bbox",
            f"{w},{s},{e},{n}",
            "--overwrite",
            str(source_pbf),
            "-o",
            str(out_pbf),
        ],
        check=True,
    )


def run_minimal(name: str, city_code: int, bbox: tuple[float, float, float, float]) -> dict:
    t0 = time.perf_counter()
    timings: dict[str, float] = {}

    # 1. Validate cityCode
    label = verify_citycode(name, city_code)
    timings["cityCode_verify"] = round(time.perf_counter() - t0, 2)

    # 2. Extract OSM PBF
    t1 = time.perf_counter()
    pbf_path = Path(f"data/processed/osm/{name}.pbf")
    extract_pbf(name, bbox, Path("data/raw/osm/south-korea-latest.osm.pbf"), pbf_path)
    timings["pbf_extract"] = round(time.perf_counter() - t1, 2)

    # 3. Run ARDI
    t2 = time.perf_counter()
    from rhythmscape.metrics.ardi import run_for_city as run_ardi

    stamp = datetime.now().strftime("%Y%m%d")
    stats = run_ardi(
        city=name,
        pbf_path=pbf_path,
        osm_base=Path("data/processed/osm"),
        ardi_base=Path("data/processed/ardi"),
        cell_size_m=500,
    )
    timings["ardi_compute"] = round(time.perf_counter() - t2, 2)

    # 4. Viz
    t3 = time.perf_counter()
    import geopandas as gpd
    import pandas as pd
    import shapely.wkt

    df = pd.read_parquet(f"data/processed/ardi/ardi_{name}_{stamp}.parquet")
    df["geometry"] = df["geometry_wkt"].apply(shapely.wkt.loads)
    gdf = gpd.GeoDataFrame(
        df.drop(columns="geometry_wkt"),
        geometry="geometry",
        crs="EPSG:5186",
    ).to_crs("EPSG:4326")

    fig, ax = plt.subplots(figsize=(10, 9))
    gdf.plot(
        column="ardi_v0",
        cmap="viridis",
        ax=ax,
        legend=True,
        linewidth=0.04,
        edgecolor="grey",
        legend_kwds={"shrink": 0.6, "label": "ARDI v0"},
    )
    ax.set_title(
        f"{label or name} — ARDI v0 (add-city minimal rehearsal)\n"
        f"cells={stats['n_cells']}, with_roads={stats['n_cells_with_roads']}, "
        f"mean={stats['mean_ardi']:.4f}, max={stats['max_ardi']:.4f}, "
        f"speed_regime={stats['mean_speed_regime']:.2%}",
        fontsize=10,
        loc="left",
    )
    ax.set_axis_off()
    png_path = Path(f"docs/evidence/{name}_addcity_ardi_{stamp}.png")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    timings["viz"] = round(time.perf_counter() - t3, 2)

    timings["total"] = round(time.perf_counter() - t0, 2)

    return {
        "label": label,
        "stats": stats,
        "png": str(png_path),
        "timings": timings,
        "stamp": stamp,
    }


def write_rehearsal_md(name: str, city_code: int, mode: str, result: dict, out_md: Path) -> None:
    stats = result["stats"]
    timings = result["timings"]
    label = result["label"] or name
    lines = []
    lines.append(f"# {label} add-city 리허설 — Day 3 ({datetime.now().strftime('%Y-%m-%d')})")
    lines.append("")
    lines.append(f"**CLI (계획)**: `rhythmscape add-city --name {name} --mode {mode}`")
    lines.append(f"**실제 실행**: `python scripts/add_city.py --name {name} --mode {mode}`")
    lines.append(f"**cityCode 검증 결과**: `{city_code}` → `{label or '(verification failed)'}`")
    lines.append("")
    lines.append("## 실행 흐름 + 단계별 소요")
    lines.append("")
    lines.append("| 단계 | 소요 (초) |")
    lines.append("|---|---:|")
    lines.append(f"| 1. cityCode TAGO 검증 | {timings['cityCode_verify']:.2f} |")
    lines.append(f"| 2. OSM PBF bbox 추출 | {timings['pbf_extract']:.2f} |")
    lines.append(f"| 3. ARDI v0 산출 (500m grid, osmium → geopandas → overlay) | {timings['ardi_compute']:.2f} |")
    lines.append(f"| 4. Heatmap PNG | {timings['viz']:.2f} |")
    lines.append(f"| **총합** | **{timings['total']:.2f}** |")
    lines.append("")
    lines.append(f"**Day 4 라이브 데모 30초 목표**: {'✅ 통과' if timings['total'] <= 30 else '⚠ 초과 (' + str(timings['total']) + 's)'} ")
    lines.append("")
    lines.append("## ARDI v0 결과")
    lines.append("")
    lines.append(f"- cells: `{stats['n_cells']}`")
    lines.append(f"- cells with roads: `{stats['n_cells_with_roads']}`")
    lines.append(f"- mean ARDI: `{stats['mean_ardi']:.4f}`")
    lines.append(f"- max ARDI: `{stats['max_ardi']:.4f}`")
    lines.append(f"- mean road_space_ratio: `{stats['mean_road_space_ratio']:.4f}`")
    lines.append(f"- mean speed_regime: `{stats['mean_speed_regime']:.4f} ({stats['mean_speed_regime']:.2%})`")
    lines.append(f"- OSM driving ways loaded: `{stats['n_ways_loaded']}`")
    lines.append(f"- ARDI parquet: `{stats['out_path']}`")
    lines.append(f"- Heatmap: `{result['png']}`")
    lines.append("")
    lines.append("## 한계 (minimal mode 명시적 trade-off)")
    lines.append("")
    lines.append(
        "- RDI 산출 불가 — 본격 분석은 TAGO tick 수집이 수일 누적되어야 함. "
        "minimal 모드는 **ARDI 단독의 공간 지표만 제공**."
    )
    lines.append(
        "- PRM / friction zone 생략 — 보행 네트워크 + ARDI 상위 decile 계산은 "
        "full 모드(add-city --mode full)에서 활성화."
    )
    lines.append(
        "- critique_flag / Opus 에이전트 비활성화 — RDI 산출이 선행 조건."
    )
    lines.append("")
    lines.append("## 사용 의도")
    lines.append("")
    lines.append(
        "해커톤 심사 시 **\"4도시 + α\" 확장성**을 증명하는 라이브 데모. 주어진 "
        "도시 이름 → 30초 내에 OSM 인프라 기반 ARDI 지도 산출. 본격 분석은 "
        "`--mode full`로 TAGO 수집 가동 후 수일치 자료 누적을 요구."
    )
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, required=True, help="City slug (lowercase)")
    parser.add_argument("--city-code", type=int, default=None)
    parser.add_argument("--mode", type=str, choices=["minimal", "full"], default="minimal")
    parser.add_argument("--bbox", type=str, default=None, help="w,s,e,n override")
    parser.add_argument(
        "--out-md",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    if args.mode != "minimal":
        parser.error("only --mode minimal is implemented for the Day-3 rehearsal")

    if args.bbox:
        w, s, e, n = [float(x) for x in args.bbox.split(",")]
        bbox = (w, s, e, n)
    elif args.name in KNOWN_CITY_BBOX:
        bbox = KNOWN_CITY_BBOX[args.name]
    else:
        parser.error(f"no known bbox for {args.name!r}; pass --bbox w,s,e,n")

    city_code = args.city_code or {"gyeongju": 37130, "jinju": 37050, "sacheon": 38330}.get(args.name)
    if city_code is None:
        parser.error(f"no known cityCode for {args.name!r}; pass --city-code")

    result = run_minimal(args.name, city_code, bbox)

    out_md = args.out_md or Path(
        f"docs/evidence/{args.name}_addcity_rehearsal_{result['stamp']}.md"
    )
    write_rehearsal_md(args.name, city_code, args.mode, result, out_md)

    print()
    print(
        f"✓ add-city {args.name} complete in {result['timings']['total']:.2f}s "
        f"(30s target: {'pass' if result['timings']['total'] <= 30 else 'FAIL'})"
    )
    print(f"  cityCode {city_code} → {result['label'] or '?'}")
    print(f"  ARDI: {result['stats']['n_cells']} cells, "
          f"mean {result['stats']['mean_ardi']:.4f}, "
          f"speed_regime {result['stats']['mean_speed_regime']:.2%}")
    print(f"  PNG: {result['png']}")
    print(f"  markdown: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
