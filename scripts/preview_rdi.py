#!/usr/bin/env python3
"""Day-2 RDI preview — three-panel time-series PNG + markdown summary.

Inputs:
    data/processed/tago/rdi_{YYYYMMDD}.parquet (includes critique_flag cols)

Outputs:
    docs/evidence/rdi_day2_preview_{YYYYMMDD}.png
    docs/analysis/rdi_day2_summary.md

Design: one subplot per route. x = time_bin (local Asia/Seoul), y =
rdi_magnitude. For each route, a single representative station is chosen
(the station with the most bins, breaking ties by earliest first bin).
Flag markers overlaid: dressage_alert = filled blue dot, vitality_query =
filled red triangle. A dashed line at y=1.0 marks "observed headway doubled
or halved vs. prescribed" (the arrhythmia threshold in spec §3.4).
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


ROUTE_LABELS = {
    "CWB379002710": "271 (마산합포 박물관 순환 · prescribed 94min)",
    "CWB379060000": "BRT6000 (성주사역↔덕동 · prescribed 20min)",
    "CWB379007100": "710 (불모산↔마산대 · prescribed 45min)",
}


def pick_representative_station(df: pd.DataFrame) -> str:
    """Pick the station with most bins for each route; tie-break by earliest first bin."""
    counts = df.groupby("station_id").size().rename("n").to_frame()
    firsts = df.groupby("station_id")["time_bin"].min().rename("t0")
    joined = counts.join(firsts).sort_values(["n", "t0"], ascending=[False, True])
    return str(joined.index[0])


def build_figure(rdi_df: pd.DataFrame, out_path: Path) -> Path:
    route_ids = [r for r in ROUTE_LABELS if r in rdi_df["route_id"].unique()]
    n_panels = len(route_ids)
    fig, axes = plt.subplots(n_panels, 1, figsize=(12, 2.8 * n_panels), sharex=False)
    if n_panels == 1:
        axes = [axes]

    for ax, rid in zip(axes, route_ids):
        route_df = rdi_df[rdi_df["route_id"] == rid]
        if route_df.empty:
            ax.text(0.5, 0.5, f"no data for {rid}", ha="center")
            continue
        station = pick_representative_station(route_df)
        series = route_df[route_df["station_id"] == station].sort_values("time_bin")

        ax.plot(
            series["time_bin"],
            series["rdi_magnitude"],
            color="#444",
            linewidth=1.1,
            marker="o",
            markersize=3,
            label=f"RDI magnitude",
        )
        ax.axhline(
            y=1.0,
            linestyle="--",
            color="#aa0000",
            alpha=0.35,
            linewidth=0.8,
            label="arrhythmia threshold (|Δ|≥prescribed)",
        )

        dressage = series[series["critique_flag"] == "dressage_alert"]
        if len(dressage):
            ax.scatter(
                dressage["time_bin"],
                dressage["rdi_magnitude"],
                color="#1f77b4",
                s=70,
                marker="o",
                edgecolor="white",
                linewidth=1.0,
                zorder=3,
                label=f"dressage_alert (n={len(dressage)})",
            )
        vitality = series[series["critique_flag"] == "vitality_query"]
        if len(vitality):
            ax.scatter(
                vitality["time_bin"],
                vitality["rdi_magnitude"],
                color="#d62728",
                s=90,
                marker="^",
                edgecolor="white",
                linewidth=1.0,
                zorder=3,
                label=f"vitality_query (n={len(vitality)})",
            )

        ax.set_title(
            f"{ROUTE_LABELS[rid]}  — station {station}",
            fontsize=10,
            loc="left",
        )
        ax.set_ylabel("RDI magnitude")
        ax.grid(alpha=0.25)
        ax.legend(loc="upper left", fontsize=7, framealpha=0.9)
        ax.set_ylim(bottom=0)

    axes[-1].set_xlabel("time (Asia/Seoul)")
    fig.suptitle(
        "Rhythmscape Day-2 RDI preview — 창원 3노선 quartile-grid observatories",
        fontsize=12,
        y=0.995,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def build_summary(rdi_df: pd.DataFrame, source_parquet: Path) -> str:
    per_route = rdi_df.groupby("route_id").agg(
        bins=("rdi_magnitude", "size"),
        mean_magnitude=("rdi_magnitude", "mean"),
        median_magnitude=("rdi_magnitude", "median"),
        max_magnitude=("rdi_magnitude", "max"),
        mean_variance=("rdi_variance", "mean"),
    )
    flag_counts = (
        rdi_df.groupby(["route_id", "critique_flag"]).size().unstack(fill_value=0)
    )
    for col in ("dressage_alert", "vitality_query"):
        if col not in flag_counts.columns:
            flag_counts[col] = 0
    flag_counts = flag_counts[["dressage_alert", "vitality_query"]]
    joined = per_route.join(flag_counts, how="left").fillna(0)

    window_start = pd.Timestamp(rdi_df["time_bin"].min())
    window_end = pd.Timestamp(rdi_df["time_bin"].max())
    total_bins = len(rdi_df)
    total_flags = int(rdi_df["critique_flag"].notna().sum())
    flag_rate = 100.0 * total_flags / max(total_bins, 1)

    lines = [
        "# RDI Day-2 Preview — 창원 3노선",
        "",
        f"**Source**: `{source_parquet}` · **Generated**: "
        f"{datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        f"**Observation window** (Asia/Seoul): "
        f"{window_start.strftime('%Y-%m-%d %H:%M')} → "
        f"{window_end.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Total bins**: {total_bins} · **Flagged**: {total_flags} "
        f"({flag_rate:.2f}% · spec §6 target 5–15%)",
        "",
        "## Per-route summary",
        "",
        "| 노선 | bins | mean mag | median mag | max mag | mean var | dressage | vitality |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rid, row in joined.iterrows():
        label = ROUTE_LABELS.get(rid, rid).split(" (")[0]
        lines.append(
            f"| {label} (`{rid}`) | {int(row['bins'])} | "
            f"{row['mean_magnitude']:.3f} | {row['median_magnitude']:.3f} | "
            f"{row['max_magnitude']:.3f} | {row['mean_variance']:.3f} | "
            f"{int(row['dressage_alert'])} | {int(row['vitality_query'])} |"
        )

    lines += [
        "",
        "## Reading",
        "",
        "- `mean mag` is the mean of |observed − prescribed| / prescribed per bin. "
        "0 = *eurhythmia* (schedule honored); ≥ 1 = observed headway at least doubled "
        "or halved vs. prescribed.",
        "- `mean var` is the mean of population stdev (ddof=0) of observed intervals "
        "within each bin. 0 when a bin holds a single observation.",
        "- `dressage` / `vitality` are post-hoc interpretive flags, not judgments — "
        "see `critique_flag_spec.md` §2 for interrogative semantics.",
        "",
        "## Observed triplet (Day-2 reading, to be revised by Cowork)",
        "",
        "- **BRT6000 carries 47/54 of all `dressage_alert`.** The route with the "
        "tightest adherence to prescribed rhythm — empirical coherence with the "
        "'automobility capture' framing in `route_selection_rationale.md` §3 "
        "(Urry 2004; Sheller & Urry 2000).",
        "- **271 carries 2/3 of all `vitality_query`.** Sparse service (94-min "
        "prescribed, ~37-min observed median) yields both high magnitude and high "
        "variance — consistent with the 'circular eurhythmia baseline' framing, "
        "now appearing as *arrhythmia* at the extremes of its sparse window.",
        "- **710 falls between** — 7 dressage, 0 vitality. Its mid-magnitude "
        "regime (0.42 mean) matches the framing of 광역 부재의 증상적 대체: "
        "observed service denser than the prescribed 45-min headway, but "
        "without the tight BRT-style regularity.",
        "",
        "## Limits of this reading",
        "",
        "- Window is ~3 hours (morning only). Peak vs off-peak separation is "
        "deferred to Day 3+.",
        "- Bin width was empirically raised from 5 min (handoff §B) to 30 min "
        "because headways (20–94 min) exceed 5-min bin widths, collapsing "
        "variance to 0 everywhere. Revisit when sub-15-min-headway routes are added.",
        "- Dressage persistence was set to 1 bin instead of the spec's 5 ticks. "
        "Rationale: a 30-min bin already averages multiple vehicle passages and "
        "is structurally non-fluke by construction. Persistence ≥ 2 bins with a "
        "full-day window should be revisited Day 3.",
        "- Quartile-grid observatories are used as a *contrastive baseline* "
        "(see `sentinel_rationale.md` §3). Thematic observatories "
        "(transfer hubs, inflection points) are not yet active.",
        "",
        "## Evidence artefacts",
        "",
        "- `docs/evidence/rdi_day2_preview_20260423.png`",
        "- `data/processed/tago/rdi_20260423.parquet`",
        "- `data/processed/tago/critique_flags_20260423.parquet`",
        "- `config/critique_flag.yaml`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rdi",
        type=Path,
        default=Path("data/processed/tago/rdi_20260423.parquet"),
    )
    parser.add_argument(
        "--png",
        type=Path,
        default=Path("docs/evidence/rdi_day2_preview_20260423.png"),
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("docs/analysis/rdi_day2_summary.md"),
    )
    args = parser.parse_args()

    rdi = pd.read_parquet(args.rdi)
    rdi["time_bin"] = pd.to_datetime(rdi["time_bin"])
    png = build_figure(rdi, args.png)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(build_summary(rdi, args.rdi), encoding="utf-8")
    print(f"✓ png: {png}")
    print(f"✓ summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
