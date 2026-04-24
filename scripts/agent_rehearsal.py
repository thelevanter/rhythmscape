#!/usr/bin/env python3
"""Opus 4.7 theoretical-agent rehearsal — Day 3 single-shot test.

Selects one ``dressage_alert`` and one ``vitality_query`` row from Day-2
Changwon RDI, routes them through the appropriate theorist agents, and
writes the outputs as markdown under
``docs/evidence/opus_agents_rehearsal_20260424/``.

Success criteria (K-2 block):
- Each agent's first line states the epistemic disclaimer
- Output is a question list, not a judgment paragraph
- A self-diagnosis section appears
- Foucault's axis-6 self-critique is not ritual filler

Usage:
    python scripts/agent_rehearsal.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from rhythmscape.agents.caller import call_agent, call_agents_for_flag
from rhythmscape.agents.convergence import compute_pairwise_jaccard
from rhythmscape.agents.prompt_loader import load_all
from rhythmscape.agents.router import route


def pick_rehearsal_rows() -> dict[str, dict]:
    """Pick one dressage_alert + one vitality_query from Day-2 Changwon RDI."""
    chang = pd.read_parquet("data/processed/tago/rdi_changwon_20260423.parquet")
    chang["time_bin"] = pd.to_datetime(chang["time_bin"])

    # dressage: BRT6000 sample (carrier of "automobility capture" narrative)
    dressage_row = chang[
        (chang["critique_flag"] == "dressage_alert")
        & (chang["route_id"] == "CWB379060000")
    ].iloc[0]

    # vitality: 271 sample (sparse window arrhythmia)
    vitality_row = chang[
        (chang["critique_flag"] == "vitality_query")
        & (chang["route_id"] == "CWB379002710")
    ].iloc[0]

    # nodename lookup
    rs = pd.read_parquet("data/raw/tago/route_stations/changwon_20260423.parquet")
    node_lookup = dict(zip(rs["nodeid"].astype(str), rs["nodenm"]))

    def row_to_context(row, route_hints):
        return {
            "city": "changwon",
            "route_id": str(row["route_id"]),
            "routeno": route_hints.get(str(row["route_id"]), "?"),
            "grid_id": str(row["station_id"]),
            "grid_name": node_lookup.get(str(row["station_id"]), "?"),
            "time_bin": row["time_bin"].isoformat(),
            "rdi_magnitude": float(row["rdi_magnitude"]),
            "rdi_variance": float(row["rdi_variance"]),
            "prescribed_interval": float(row["prescribed_interval"]),
            "observed_interval_median": float(row["observed_interval"]),
            "n_observations": int(row["n_observations"]),
            "critique_flag": str(row["critique_flag"]),
            "flag_rationale": (
                json.loads(row["flag_rationale"])
                if row["flag_rationale"]
                else None
            ),
            "spatial_context": route_hints.get("_spatial", None),
        }

    dressage_hints = {
        "CWB379060000": "BRT급행(6000)",
        "_spatial": "의창동환승센터 — 창원대로 BRT 전용차로 결절, 성주사역 환승센터↔덕동공영차고지 운행 주간 정오",
    }
    vitality_hints = {
        "CWB379002710": "271",
        "_spatial": "한우아파트 (마산합포구) — 창원시립마산박물관 순환, 저밀도 주거지, 오전 피크 후반",
    }

    return {
        "dressage": row_to_context(dressage_row, dressage_hints),
        "vitality": row_to_context(vitality_row, vitality_hints),
    }


def run_rehearsal(out_dir: Path, model: str) -> None:
    load_dotenv(".env")
    prompts = load_all(lang="ko")
    samples = pick_rehearsal_rows()

    out_dir.mkdir(parents=True, exist_ok=True)
    all_report_lines: list[str] = []
    all_report_lines.append(
        "# Opus 4.7 theoretical-agent rehearsal — Day 3 (2026-04-24)\n"
    )
    all_report_lines.append(f"**Model**: `{model}`")
    all_report_lines.append(
        f"**Generated**: {datetime.now().astimezone().isoformat(timespec='seconds')}"
    )
    all_report_lines.append(
        "**Routing**: dressage_alert → (Lefebvre, Foucault) · "
        "vitality_query → (Deleuze-Guattari, Lefebvre)"
    )
    all_report_lines.append("")

    for flag, ctx in samples.items():
        theorists = route(ctx["critique_flag"])
        print(
            f"\n--- {flag.upper()} sample: {ctx['route_id']} @ {ctx['grid_name']} "
            f"(RDI={ctx['rdi_magnitude']:.3f}) → {theorists} ---"
        )
        responses = call_agents_for_flag(
            theorists=theorists,
            prompts=prompts,
            context=ctx,
            model=model,
        )
        # Pairwise Jaccard (3-agent convergence skeleton — here only 2 per flag)
        sims = compute_pairwise_jaccard(responses)

        sample_file = out_dir / f"{flag}_{ctx['route_id']}_{ctx['grid_id']}.md"
        lines = [
            f"# {flag.upper()} rehearsal — {ctx['route_id']} @ {ctx['grid_name']}",
            "",
            "## Input context (YAML)",
            "",
            "```yaml",
            *[f"{k}: {v}" for k, v in ctx.items()],
            "```",
            "",
            "## Routing",
            "",
            f"- critique_flag = `{ctx['critique_flag']}` → theorists = {list(theorists)}",
            "",
        ]
        for resp in responses:
            lines += [
                f"## {resp.theorist.capitalize()} — output",
                "",
                "```",
                resp.text.strip(),
                "```",
                "",
                f"*tokens: input={resp.input_tokens} (cache_create={resp.cache_creation_tokens}, "
                f"cache_read={resp.cache_read_tokens}) output={resp.output_tokens}*",
                "",
            ]
        if sims:
            lines += ["## Pairwise Jaccard (skeleton — Day 4 확장)", ""]
            for s in sims:
                lines.append(
                    f"- `{s.theorist_a}` × `{s.theorist_b}`: J={s.jaccard:.4f} "
                    f"(shared={s.shared_tokens}, a_only={s.a_only_tokens}, b_only={s.b_only_tokens})"
                )
            lines.append("")

        sample_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"  ✓ {sample_file}")
        all_report_lines.append(f"## {flag.upper()} → [{sample_file.name}]({sample_file.name})")
        for resp in responses:
            first_line = (resp.text.strip().splitlines() or [""])[0][:120]
            all_report_lines.append(f"  - **{resp.theorist}**: {first_line}")
        all_report_lines.append("")

    index_file = out_dir / "README.md"
    index_file.write_text("\n".join(all_report_lines), encoding="utf-8")
    print(f"\n✓ index: {index_file}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("docs/evidence/opus_agents_rehearsal_20260424"),
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-opus-4-7",
        help="Anthropic model ID. User spec mentioned 'claude-opus-4-6' but "
        "the hackathon model family is 4.7; override if needed.",
    )
    args = parser.parse_args()
    run_rehearsal(args.out_dir, args.model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
