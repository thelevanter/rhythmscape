#!/usr/bin/env python3
"""M8 — Sonnet 4.5 vs Opus 4.7 comparative experiment on a single Foucault call.

Picks the strongest Changwon BRT6000 dressage_alert sample from Day 3,
invokes Foucault agent twice (same system prompt, same user context,
different model), and writes both outputs to a comparison markdown.

Purpose: empirical defense of "Opus 4.7 Use 25%" hackathon scoring axis.
Target dimensions:
  - Axis 6 (self-critique) depth — ritual vs specific
  - Precision of critique on critique_flag's two structures
    (quantile thresholds, interrogative fixed form)
  - Output length + number of question items
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from rhythmscape.agents.caller import call_agent
from rhythmscape.agents.prompt_loader import load_prompt


def pick_strongest_dressage_sample() -> dict:
    """Pick the BRT6000 dressage_alert Day 3 sample with the smallest magnitude
    (= tightest synchronization, strongest dressage case)."""
    rdi = pd.read_parquet("data/processed/tago/rdi_changwon_20260424.parquet")
    rdi["time_bin"] = pd.to_datetime(rdi["time_bin"])
    dr = rdi[
        (rdi["critique_flag"] == "dressage_alert")
        & (rdi["route_id"] == "CWB379060000")
    ].sort_values("rdi_magnitude", ascending=True)  # smallest = most dressed
    if dr.empty:
        raise RuntimeError("no BRT6000 dressage_alert rows found")
    row = dr.iloc[0]

    rs = pd.read_parquet("data/raw/tago/route_stations/changwon_20260424.parquet")
    node_lookup = dict(zip(rs["nodeid"].astype(str), rs["nodenm"]))

    return {
        "city": "changwon",
        "route_id": str(row["route_id"]),
        "routeno": "BRT급행(6000)",
        "grid_id": str(row["station_id"]),
        "grid_name": node_lookup.get(str(row["station_id"]), "?"),
        "time_bin": row["time_bin"].isoformat(),
        "rdi_magnitude": float(row["rdi_magnitude"]),
        "rdi_variance": float(row["rdi_variance"]),
        "prescribed_interval": float(row["prescribed_interval"]),
        "observed_interval_median": float(row["observed_interval"]),
        "n_observations": int(row["n_observations"]),
        "critique_flag": "dressage_alert",
        "flag_rationale": (
            json.loads(row["flag_rationale"]) if row["flag_rationale"] else None
        ),
        "spatial_context": (
            f"{node_lookup.get(str(row['station_id']), '?')} — "
            "창원대로 BRT 전용차로 결절"
        ),
    }


def count_questions(text: str) -> int:
    import re

    return len(re.findall(r"^\s*Q\d+\.", text, flags=re.MULTILINE))


def extract_axis_6(text: str) -> str:
    """Crude extraction of the axis-6 block from a Foucault output."""
    import re

    # Find '축 6' heading
    m = re.search(r"\*\*축\s*6", text)
    if m is None:
        return "(axis-6 heading not found)"
    start = m.start()
    # Find end: next '##' heading or end of text
    rest = text[start:]
    end_m = re.search(r"\n##\s", rest)
    end = end_m.start() if end_m else len(rest)
    return rest[:end].strip()


def run_comparison(sample: dict, out_md: Path) -> None:
    load_dotenv(".env")
    foucault_prompt = load_prompt("foucault", lang="ko")

    models = [
        ("claude-sonnet-4-5", "Sonnet 4.5"),
        ("claude-opus-4-7", "Opus 4.7"),
    ]
    results = []
    for model, label in models:
        print(f"Calling {label} ({model})…")
        resp = call_agent(
            theorist="foucault",
            system_prompt=foucault_prompt,
            context=sample,
            model=model,
            max_tokens=4096,
        )
        results.append((label, model, resp))
        print(
            f"  {label}: {len(resp.text)} chars, "
            f"input_tokens={resp.input_tokens}, output_tokens={resp.output_tokens}"
        )

    # Write comparison markdown
    lines = [
        "# M8 — Sonnet 4.5 vs Opus 4.7 on Foucault · 창원 BRT6000 dressage",
        "",
        f"**Generated**: {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "**Foucault agent system prompt**: `prompts/ko/foucault.md` (identical for both models)",
        "**User context** (동일 입력, 모델만 변경):",
        "",
        "```yaml",
        *[f"{k}: {v}" for k, v in sample.items()],
        "```",
        "",
        "---",
        "",
        "## 비교 표",
        "",
        "| 차원 | Sonnet 4.5 | Opus 4.7 |",
        "|---|---|---|",
    ]

    chars = {label: len(resp.text) for label, _, resp in results}
    qs = {label: count_questions(resp.text) for label, _, resp in results}
    in_tok = {label: resp.input_tokens for label, _, resp in results}
    out_tok = {label: resp.output_tokens for label, _, resp in results}
    lines.append(
        f"| 출력 길이 (chars) | {chars['Sonnet 4.5']} | {chars['Opus 4.7']} |"
    )
    lines.append(f"| 의문문 수 (Q\\d+.) | {qs['Sonnet 4.5']} | {qs['Opus 4.7']} |")
    lines.append(f"| input_tokens | {in_tok['Sonnet 4.5']} | {in_tok['Opus 4.7']} |")
    lines.append(
        f"| output_tokens | {out_tok['Sonnet 4.5']} | {out_tok['Opus 4.7']} |"
    )
    lines.append("")
    lines.append("## 축 6 (자기-비판) 비교")
    lines.append("")
    for label, _, resp in results:
        lines.append(f"### {label}")
        lines.append("")
        lines.append("```")
        lines.append(extract_axis_6(resp.text))
        lines.append("```")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 전체 응답 원문")
    lines.append("")
    for label, model, resp in results:
        lines.append(f"### {label} (`{model}`)")
        lines.append("")
        lines.append("```")
        lines.append(resp.text.strip())
        lines.append("```")
        lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n✓ {out_md}")
    print()
    print(f"chars: Sonnet {chars['Sonnet 4.5']}  |  Opus {chars['Opus 4.7']}")
    print(f"Qs:    Sonnet {qs['Sonnet 4.5']}  |  Opus {qs['Opus 4.7']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/analysis/opus_vs_sonnet_comparison.md"),
    )
    args = parser.parse_args()
    sample = pick_strongest_dressage_sample()
    run_comparison(sample, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
