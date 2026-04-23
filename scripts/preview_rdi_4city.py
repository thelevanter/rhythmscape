#!/usr/bin/env python3
"""Day-2 afternoon 4-city preview — RDI time-series + Sejong opacity panel.

Produces a single PNG (4 panels: Changwon, Seongnam Bundang, Busan Yeongdo,
Sejong-opacity) and prints a compact per-city summary block that can be
pasted into ``day2_4city_preview.md``.

The three RDI-participating cities share a common x-axis (Asia/Seoul time)
and show ``rdi_magnitude`` at their highest-count observatory, with
``dressage_alert`` (blue dot) and ``vitality_query`` (red triangle)
markers overlaid. The fourth panel is a prescription-opacity diagnostic
for Sejong — locations rows accumulating (healthy operational layer)
against a blank prescribed track (TAGO intervaltime absent). This visually
frames Sejong as "hidden prescription" rather than missing data.

Inputs:
    data/processed/tago/rdi_{city}_20260423.parquet  (with critique_flag cols)
    data/raw/tago/locations/{city}_20260423_*.parquet (for Sejong panel)

Outputs:
    docs/evidence/rdi_day2_4city_preview_{YYYYMMDD}.png
    (summary printed to stdout for day2_4city_preview.md integration)
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd


matplotlib.rcParams["font.family"] = [
    "AppleGothic",
    "Apple SD Gothic Neo",
    "Noto Sans CJK KR",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


PARTICIPATING = [
    ("changwon", "창원 (플래그십)", {
        "CWB379002710": "271 (마산합포 박물관 순환)",
        "CWB379060000": "BRT6000 (성주사역↔덕동)",
        "CWB379007100": "710 (불모산↔마산대)",
    }),
    ("seongnam_bundang", "성남 분당 (수도권 신도시)", {
        "GGB228000179": "101 (오리↔수서 central spine)",
        "GGB204000024": "9407 (분당↔강남 직행좌석)",
        "GGB204000146": "누리2 (분당 내부 고밀도)",
    }),
    ("busan_yeongdo", "부산 영도 (반도 지형)", {
        "BSB5200008000": "8 (태종대↔서부터미널, 영도대교 관통)",
        "BSB5200113000": "113 (영도중리↔신평, 사하구 연결)",
        "BSB5290407000": "영도구7 (청학동↔동삼그린힐)",
    }),
]
SEJONG_SLUG = "sejong"


def pick_station_per_route(df: pd.DataFrame) -> dict[str, str]:
    picks: dict[str, str] = {}
    for rid, sub in df.groupby("route_id"):
        counts = sub.groupby("station_id").size().sort_values(ascending=False)
        picks[rid] = str(counts.index[0])
    return picks


def _draw_rdi_panel(ax, city_slug: str, city_label: str, route_labels: dict[str, str], rdi_df: pd.DataFrame):
    route_stations = pick_station_per_route(rdi_df)
    cmap = {
        list(route_labels.keys())[0]: "#444",
        list(route_labels.keys())[1]: "#1f77b4",
        list(route_labels.keys())[2]: "#d97706",
    }
    for rid, rlabel in route_labels.items():
        stn = route_stations.get(rid)
        if stn is None:
            continue
        series = (
            rdi_df[(rdi_df["route_id"] == rid) & (rdi_df["station_id"] == stn)]
            .sort_values("time_bin")
        )
        if series.empty:
            continue
        ax.plot(
            series["time_bin"],
            series["rdi_magnitude"],
            linewidth=0.9,
            marker="o",
            markersize=2.6,
            color=cmap.get(rid, "#666"),
            label=rlabel,
            alpha=0.85,
        )
        dr = series[series["critique_flag"] == "dressage_alert"]
        if len(dr):
            ax.scatter(
                dr["time_bin"],
                dr["rdi_magnitude"],
                color="#1f77b4",
                s=36,
                marker="o",
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )
        vt = series[series["critique_flag"] == "vitality_query"]
        if len(vt):
            ax.scatter(
                vt["time_bin"],
                vt["rdi_magnitude"],
                color="#d62728",
                s=50,
                marker="^",
                edgecolor="white",
                linewidth=0.6,
                zorder=3,
            )

    ax.axhline(y=1.0, linestyle="--", color="#aa0000", alpha=0.25, linewidth=0.6)
    ax.set_title(city_label, fontsize=10, loc="left", fontweight="bold")
    ax.set_ylabel("RDI magnitude")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=6, framealpha=0.9, ncol=1)
    ax.set_ylim(bottom=0)


def _draw_sejong_opacity_panel(ax, locations_dir: Path, for_date: date):
    """Panel 4: Sejong locations accrual timeline + annotation on missing prescribed.

    Shows locations row count per 30-min bin over time (healthy operational
    layer) with a dotted placeholder line at y=0 representing the absent
    prescribed track — making the asymmetry visible.
    """
    stamp = for_date.strftime("%Y%m%d")
    paths = sorted(locations_dir.glob(f"{SEJONG_SLUG}_{stamp}_*.parquet"))
    frames = [pd.read_parquet(p) for p in paths]
    if not frames:
        ax.text(0.5, 0.5, "Sejong locations missing", ha="center", va="center")
        return
    df = pd.concat(frames, ignore_index=True)
    df["snapshot_ts_utc"] = pd.to_datetime(df["snapshot_ts_utc"], utc=True)
    df["t_bin"] = df["snapshot_ts_utc"].dt.tz_convert("Asia/Seoul").dt.floor("30min")
    cnt = df.groupby("t_bin").size().reset_index(name="locations_rows")

    ax.fill_between(
        cnt["t_bin"],
        0,
        cnt["locations_rows"],
        color="#bbdefb",
        alpha=0.6,
        label="locations (operational, healthy)",
    )
    ax.plot(
        cnt["t_bin"],
        cnt["locations_rows"],
        color="#1565c0",
        linewidth=1.2,
    )
    # Dashed "prescribed = absent" track
    ax.axhline(
        y=0.0,
        linestyle=":",
        color="#c62828",
        linewidth=1.4,
        label="prescribed (hidden — TAGO intervaltime NaN)",
    )
    ax.text(
        0.98,
        0.90,
        "※ 세종 처방은 TAGO 연합 데이터에 없음.\n운영 층은 정상 — 처방 은닉 자체가 분석 대상.",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=7.5,
        color="#333",
        bbox=dict(boxstyle="round,pad=0.4", fc="#fff3cd", ec="#ffe082", lw=0.5),
    )
    ax.set_title(
        "세종 — 처방 은닉 도시 (Prescription Opacity)",
        fontsize=10,
        loc="left",
        fontweight="bold",
    )
    ax.set_ylabel("locations rows / 30min bin")
    ax.grid(alpha=0.2)
    ax.legend(loc="upper left", fontsize=7, framealpha=0.9)
    ax.set_ylim(bottom=0)


def build_figure(processed_base: Path, raw_locations: Path, for_date: date, out_path: Path) -> Path:
    fig, axes = plt.subplots(4, 1, figsize=(13, 11.5), sharex=False)
    stamp = for_date.strftime("%Y%m%d")

    for ax, (slug, label, routes) in zip(axes[:3], PARTICIPATING):
        rdi_path = processed_base / f"rdi_{slug}_{stamp}.parquet"
        if not rdi_path.exists():
            ax.text(0.5, 0.5, f"no rdi parquet for {slug}", ha="center", va="center")
            continue
        rdi_df = pd.read_parquet(rdi_path)
        rdi_df["time_bin"] = pd.to_datetime(rdi_df["time_bin"])
        _draw_rdi_panel(ax, slug, label, routes, rdi_df)

    _draw_sejong_opacity_panel(axes[3], raw_locations, for_date)
    axes[3].set_xlabel("time (Asia/Seoul)")

    fig.suptitle(
        f"Rhythmscape Day-2 afternoon — 4-city synchronic preview ({stamp})",
        fontsize=12,
        y=0.995,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def build_summary(processed_base: Path, for_date: date) -> str:
    """Return a markdown-ready per-city summary block."""
    lines = []
    stamp = for_date.strftime("%Y%m%d")
    for slug, label, _ in PARTICIPATING:
        rdi_path = processed_base / f"rdi_{slug}_{stamp}.parquet"
        if not rdi_path.exists():
            continue
        rdi_df = pd.read_parquet(rdi_path)
        total = len(rdi_df)
        if total == 0:
            continue
        mean_mag = rdi_df["rdi_magnitude"].mean()
        median_mag = rdi_df["rdi_magnitude"].median()
        mean_var = rdi_df["rdi_variance"].mean()
        dr = int((rdi_df["critique_flag"] == "dressage_alert").sum())
        vt = int((rdi_df["critique_flag"] == "vitality_query").sum())
        rate = 100.0 * (dr + vt) / total
        lines.append(
            f"| {label} | {total} | {mean_mag:.3f} | {median_mag:.3f} | "
            f"{mean_var:.2f} | {dr} | {vt} | {rate:.2f}% |"
        )

    # Sejong separately
    sejong_rdi = processed_base / f"rdi_{SEJONG_SLUG}_{stamp}.parquet"
    sejong_block = ""
    if sejong_rdi.exists():
        sejong_df = pd.read_parquet(sejong_rdi)
        sejong_block = (
            f"\n**세종 (opacity)**: RDI bins = {len(sejong_df)} "
            f"(prescribed NaN → 전수 drop). "
            f"locations 수집 정상 작동 (3 routes, 10+ vehicles, 38 stations)."
        )

    return (
        "| 도시 | RDI bins | mean mag | median mag | mean var | dressage | vitality | flag rate |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(lines)
        + sejong_block
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed-base",
        type=Path,
        default=Path("data/processed/tago"),
    )
    parser.add_argument(
        "--raw-locations",
        type=Path,
        default=Path("data/raw/tago/locations"),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="YYYYMMDD (Asia/Seoul). Default: today",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    if args.date:
        for_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    stamp = for_date.strftime("%Y%m%d")
    out = args.out or Path(f"docs/evidence/rdi_day2_4city_preview_{stamp}.png")
    png = build_figure(args.processed_base, args.raw_locations, for_date, out)
    print(f"✓ {png}")
    print()
    print(build_summary(args.processed_base, for_date))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
