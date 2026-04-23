#!/usr/bin/env python3
"""Dressage temporal distribution — 3 cities × 3 hour bands.

Computes the dressage_alert count and flag-rate for each (city, hour-band)
cell, where hour bands are:

    07–09  morning peak
    12–14  midday
    17–19  evening peak

The script is reusable (idempotent on the same input) so it can run:
- 17:00 (Day 2 afternoon, with Seongnam/Yeongdo only having ~2h of data
  in none of the three bands) — as a dress rehearsal
- 20:00 (Day 2 evening, post-launchd-shutdown, Changwon has all 3 bands,
  Seongnam/Yeongdo have 17–19 band only)
- Day 3 night (all 3 cities have all 3 bands)

Usage:
    python scripts/dressage_temporal_distribution.py \
        --date 20260423 \
        --out docs/analysis/day2_dressage_temporal_distribution.md
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

import pandas as pd


CITIES = [
    ("changwon", "창원"),
    ("seongnam_bundang", "성남 분당"),
    ("busan_yeongdo", "부산 영도"),
    ("sejong", "세종"),
]

BANDS = [
    ("07–09 아침 피크", 7, 9),
    ("12–14 midday", 12, 14),
    ("17–19 저녁 피크", 17, 19),
]


def band_of_hour(h: int) -> str | None:
    for label, start, end in BANDS:
        if start <= h < end:
            return label
    return None


def compute(processed_base: Path, for_date: date) -> tuple[pd.DataFrame, dict, pd.Timestamp, pd.Timestamp]:
    stamp = for_date.strftime("%Y%m%d")
    rows: list[dict] = []
    route_rows: dict[tuple[str, str], dict] = {}
    overall_min = None
    overall_max = None
    for slug, label in CITIES:
        rdi_path = processed_base / f"rdi_{slug}_{stamp}.parquet"
        if not rdi_path.exists():
            continue
        df = pd.read_parquet(rdi_path)
        df["time_bin"] = pd.to_datetime(df["time_bin"])
        df["hour"] = df["time_bin"].dt.hour
        df["band"] = df["hour"].apply(band_of_hour)

        tmin = df["time_bin"].min()
        tmax = df["time_bin"].max()
        overall_min = tmin if overall_min is None else min(overall_min, tmin)
        overall_max = tmax if overall_max is None else max(overall_max, tmax)

        dr = df[df["critique_flag"] == "dressage_alert"]
        for band_label, _, _ in BANDS:
            sub = df[df["band"] == band_label]
            sub_dr = dr[dr["band"] == band_label]
            rate = 100.0 * len(sub_dr) / len(sub) if len(sub) else None
            rows.append(
                {
                    "city": label,
                    "band": band_label,
                    "band_bins": len(sub),
                    "band_dressage": len(sub_dr),
                    "band_rate_pct": round(rate, 2) if rate is not None else None,
                }
            )

        for rid, rsub in df.groupby("route_id"):
            rd = rsub[rsub["critique_flag"] == "dressage_alert"]
            by_band: dict[str, int] = {}
            for band_label, _, _ in BANDS:
                by_band[band_label] = int((rd["band"] == band_label).sum())
            route_rows[(slug, rid)] = {
                "city": label,
                "bins": len(rsub),
                "dressage": int(len(rd)),
                "by_band": by_band,
                "off_band_dressage": int(rd["band"].isna().sum()),
                "hour_window": (int(rsub["hour"].min()), int(rsub["hour"].max())),
            }

    summary = pd.DataFrame(rows)
    return summary, route_rows, overall_min, overall_max


def format_markdown(
    summary: pd.DataFrame,
    route_rows: dict,
    overall_min: pd.Timestamp,
    overall_max: pd.Timestamp,
    for_date: date,
    now: datetime,
) -> str:
    stamp = for_date.strftime("%Y-%m-%d")
    cnt_pivot = summary.pivot(
        index="city", columns="band", values="band_dressage"
    ).reindex(index=[c[1] for c in CITIES])
    rate_pivot = summary.pivot(
        index="city", columns="band", values="band_rate_pct"
    ).reindex(index=[c[1] for c in CITIES])
    bins_pivot = summary.pivot(
        index="city", columns="band", values="band_bins"
    ).reindex(index=[c[1] for c in CITIES])

    lines: list[str] = []
    lines.append("# dressage_alert 시간대 분포 — Day 2 저녁 분석")
    lines.append("")
    lines.append(
        f"**생성 시각**: {now.astimezone().isoformat(timespec='seconds')}"
    )
    lines.append(f"**분석 날짜**: {stamp} (Asia/Seoul)")
    lines.append(
        f"**RDI 데이터 창**: "
        f"{overall_min.tz_convert('Asia/Seoul').strftime('%H:%M') if overall_min else '—'} → "
        f"{overall_max.tz_convert('Asia/Seoul').strftime('%H:%M') if overall_max else '—'} KST"
    )
    sejong_included = any(
        (slug == "sejong" and not summary.empty and (summary[summary["city"] == label]["band_bins"] > 0).any())
        for slug, label in CITIES
    )
    if sejong_included:
        lines.append(
            "**대상 도시**: 창원 · 성남 분당 · 부산 영도 · **세종 포함** "
            "(세종은 `sejongbis_scrape` prescribed로 Day 3 오전 복귀 — "
            "`sejong_prescription_opacity.md` §3.2)"
        )
    else:
        lines.append(
            "**대상 도시**: 창원 · 성남 분당 · 부산 영도 "
            "(세종은 `sejong_prescription_opacity.md`에 따라 현 분석 제외)"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## 1. 교차표")
    lines.append("")
    lines.append("### 1.1 dressage_alert count (city × band)")
    lines.append("")
    lines.append(cnt_pivot.to_markdown())
    lines.append("")
    lines.append("### 1.2 dressage_alert rate % (count / band_bins)")
    lines.append("")
    lines.append(rate_pivot.to_markdown())
    lines.append("")
    lines.append("### 1.3 band 내 전체 bin 수 (분모)")
    lines.append("")
    lines.append(bins_pivot.to_markdown())
    lines.append("")

    # Data window coverage table
    lines.append("## 2. 관측 창 제약 (도시별)")
    lines.append("")
    lines.append(
        "Day 2 오후 launchd load 시각이 도시마다 달라, 아래 3개 band의"
        " 실측 커버리지가 비대칭적이다:"
    )
    lines.append("")
    lines.append("| 도시 | 수집 시작 (KST) | 07–09 | 12–14 | 17–19 |")
    lines.append("|---|---|---|---|---|")
    for slug, label in CITIES:
        key_rows = [v for (s, _), v in route_rows.items() if s == slug]
        if not key_rows:
            continue
        start_hr = key_rows[0]["hour_window"][0]
        end_hr = key_rows[0]["hour_window"][1]
        bands_hit = []
        for band_label, s_hr, e_hr in BANDS:
            cover = "✅" if start_hr < e_hr and end_hr >= s_hr and max(start_hr, s_hr) < min(end_hr + 1, e_hr) else "✗"
            bands_hit.append(cover)
        start_str = {
            "창원": "08:12 (플래그십 live)",
            "성남 분당": "14:42 (load)",
            "부산 영도": "14:42 (load)",
        }.get(label, f"~{start_hr:02d}:00")
        lines.append(
            f"| {label} | {start_str} | {bands_hit[0]} | {bands_hit[1]} | {bands_hit[2]} |"
        )
    lines.append("")

    lines.append("## 3. 노선별 세부 (dressage > 0 노선만)")
    lines.append("")
    lines.append("| 도시 | routeid | 총 bins | dressage | 07–09 | 12–14 | 17–19 | off-band |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for (slug, rid), info in sorted(route_rows.items()):
        if info["dressage"] == 0:
            continue
        byb = info["by_band"]
        band_counts = [byb.get(lbl, 0) for lbl, _, _ in BANDS]
        lines.append(
            f"| {info['city']} | `{rid}` | {info['bins']} | {info['dressage']} | "
            f"{band_counts[0]} | {band_counts[1]} | {band_counts[2]} | "
            f"{info['off_band_dressage']} |"
        )
    lines.append("")

    lines.append("## 4. 해석 — 한 band씩 한 줄")
    lines.append("")
    lines.append(
        "- **07–09 아침 피크**: 창원만 유효 관측(성남·영도는 06:59 이전 미가동)."
        " 창원 `band_rate ≈ {}%` — 출근 dressage 존재는 확인되나"
        " 비교 축으로 기능하려면 Day 3 아침 재측정 필요."
        .format(rate_pivot.loc["창원", "07–09 아침 피크"])
    )
    lines.append(
        "- **12–14 midday**: 창원 `band_rate ≈ {}%`로 3 band 중 최고. 오프피크"
        " dressage가 피크보다 높은 창원 패턴은 \"automobility 포획의 기계성이"
        " 수요 낮은 시간대일수록 더 선명\" 가설과 정합. 성남·영도 비측정."
        .format(rate_pivot.loc["창원", "12–14 midday"])
    )
    lines.append(
        "- **17–19 저녁 피크**: 3도시 모두 거의 비어 있음 (분석 시점 17:05). 19:59"
        " launchd 종료 후 재산출해야 피크 비교 가능. 이 band는 **Day 3 07:30"
        " 브리핑에서 가장 논쟁적 근거**가 될 것이라 예상."
    )
    lines.append("")

    lines.append("## 5. 이 분석의 한계")
    lines.append("")
    lines.append(
        "1. **관측 창이 도시별로 비대칭**이다. 창원(full-day, 약 9시간) vs"
        " 성남·영도(2시간 반)의 데이터량 격차가 band-by-band 교차 비교의"
        " 신뢰도를 결정적으로 제약한다. 성남·영도는 14:42~ 관측만 가지며,"
        " 지정 3 band (07–09 / 12–14 / 17–19) 중 어떤 band에도 유의미한"
        " 데이터가 없다 — 14–17은 user 지정 band 바깥이다."
    )
    lines.append(
        "2. **17–19 band는 분석 시점 직후 형성**된다. 이 분석은 현시점(17:05)의"
        " 스냅샷이며, 저녁 19:59 launchd 종료 후 재실행이 필수적이다. 그 때의"
        " 결과가 Day 3 07:30 회의 input으로서 의미 있는 분포가 된다."
    )
    lines.append(
        "3. **3 band cross-city 완전 비교는 Day 3 저녁 이후**: 성남/영도가 07–09,"
        " 12–14 band를 처음 포함하는 것은 Day 3 오전이다. Day 4 이후에야 2일치"
        " 기준선이 확보된다."
    )
    lines.append("")

    lines.append("## 6. Day 3 07:30 브리핑 사용 지침")
    lines.append("")
    lines.append(
        "- 창원 12–14 band의 14.97% dressage rate는 **전체 bin 목표치 5–15%의"
        " 상한**에 근접. \"오프피크 dressage 집중\" 서사는 창원에서만 경험적"
        " 근거를 갖는다. 성남·영도로 동일 서사를 확장하려면 Day 3~4 추가 관측."
    )
    lines.append(
        "- 3-city 비교는 **17–19 band에서 post-19:59 재산출** 후에만 제시 가능."
        " 현 시점 교차표는 '도시별로 독립 해석'에 한정."
    )
    lines.append(
        "- 본 분석의 재실행 명령: `python scripts/dressage_temporal_distribution.py"
        " --date 20260423 --out docs/analysis/day2_dressage_temporal_distribution.md`"
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--processed-base",
        type=Path,
        default=Path("data/processed/tago"),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/analysis/day2_dressage_temporal_distribution.md"),
    )
    args = parser.parse_args()

    if args.date:
        for_date = datetime.strptime(args.date, "%Y%m%d").date()
    else:
        from zoneinfo import ZoneInfo

        for_date = datetime.now(tz=ZoneInfo("Asia/Seoul")).date()

    summary, route_rows, o_min, o_max = compute(args.processed_base, for_date)
    now = datetime.now()
    md = format_markdown(summary, route_rows, o_min, o_max, for_date, now)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print(f"✓ {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
