#!/usr/bin/env python3
"""Render Rhythmscape 4-city HTML reports for Day-3 demo review.

Generates:
    reports/index.html               — 4-city dashboard
    reports/{city}.html               — per-city detail page (×4)

Per-city page contents:
    - Header + city-context block (routes, manifest role labels)
    - RDI time-series figure (4-city preview PNG link)
    - ARDI v0 heatmap (from docs/evidence/ardi_day3_4city_comparison PNG)
    - PRM v0 heatmap
    - Friction zones map
    - critique_flag sample messages (dressage + vitality excerpts)
    - Opus agent quotes (Changwon only for Day 3; other cities Day 4)

Index dashboard:
    - 4-city summary table (cells / ARDI / PRM / friction stats)
    - regional_fix 4-variation empirical confirmation
    - H-SJ double-structure evidence block
    - Links to per-city pages + evidence PNGs

Static HTML with minimal CSS. Design principle: *readable on GitHub
preview*, *self-contained via relative links*, *no JavaScript*. Day 4
can upgrade key panels to folium if time permits.
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml


CITY_LABELS = {
    "changwon": "창원 (flagship · 1970s 중화학 계획)",
    "seongnam_bundang": "성남 분당 (1990s 신도시 + 판교)",
    "sejong": "세종 (2010s 행정중심 계획)",
    "busan_yeongdo": "부산 영도 (비계획 반도 축적)",
}

CITY_THEORETICAL = {
    "changwon": "자동차 중심 격자 위에 덧씌워진 BRT. 3노선의 Lefebvrean 삼원 구조(eurhythmia·polyrhythmia·arrhythmia) 기준선.",
    "seongnam_bundang": "민간 자본 계획 도시. 분당 central spine + 강남 통근 회랑 + 고밀도 생활권 잔여. regional_fix 4변주의 *특권* 극.",
    "sejong": "계획 단계 통합 BRT + 행정중심 분산. 처방 은닉 + 계획 내재 dressage 이중 구조. regional_fix *필수성* 극.",
    "busan_yeongdo": "반도+봉래산 지형 제약. 다리 병목 구조화. regional_fix *왜곡* 극.",
}

CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "AppleSDGothicNeo", "Apple SD Gothic Neo", system-ui, sans-serif; max-width: 1080px; margin: 40px auto; padding: 0 24px; color: #222; line-height: 1.65; }
h1 { font-size: 1.9em; border-bottom: 2px solid #333; padding-bottom: 8px; }
h2 { margin-top: 2.5em; font-size: 1.4em; border-left: 4px solid #333; padding-left: 10px; }
h3 { font-size: 1.15em; color: #444; margin-top: 1.6em; }
table { border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 6px 12px; font-size: 0.95em; }
th { background: #f2f2f2; text-align: left; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
img { max-width: 100%; border: 1px solid #ccc; border-radius: 4px; margin: 10px 0; }
.flag { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 12px 0; border-radius: 0 4px 4px 0; }
.flag.dressage { background: #e3f2fd; border-color: #1976d2; }
.flag.vitality { background: #fce4ec; border-color: #d32f2f; }
.meta { color: #888; font-size: 0.9em; }
.quote { background: #f5f5f5; padding: 14px 18px; margin: 12px 0; border-left: 3px solid #666; font-size: 0.93em; }
.nav { background: #fafafa; padding: 12px 18px; border-radius: 4px; margin-bottom: 20px; }
.nav a { margin-right: 16px; text-decoration: none; color: #1976d2; }
.disclaimer { background: #fffbe6; border: 1px solid #e0c66d; padding: 10px 14px; font-size: 0.88em; border-radius: 4px; margin: 12px 0; }
.sig-block { background: #f0f7ff; border-left: 4px solid #3498db; padding: 12px 18px; margin: 16px 0; }
hr { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
.footer { margin-top: 4em; padding: 16px 0; border-top: 1px solid #ddd; color: #888; font-size: 0.88em; }
"""


def rel_evidence(from_path: Path, evidence_rel: str) -> str:
    """Compute relative path from an HTML file at from_path to docs/evidence/..."""
    # from_path = reports/{name}.html  → ../docs/evidence/<evidence_rel>
    depth = len(from_path.parts) - 1  # excluding the filename itself
    return ("../" * depth) + "docs/evidence/" + evidence_rel


def load_cities_manifest(cities_yaml: Path) -> dict:
    with cities_yaml.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def per_city_stats(city: str, stamp: str) -> dict:
    """Collect per-city numeric stats for a report row."""
    stats = {"city": city, "label": CITY_LABELS.get(city, city)}

    rdi_path = Path(f"data/processed/tago/rdi_{city}_{stamp}.parquet")
    if rdi_path.exists():
        rdi = pd.read_parquet(rdi_path)
        stats["rdi_bins"] = int(len(rdi))
        if len(rdi):
            stats["rdi_mean_mag"] = float(rdi["rdi_magnitude"].mean())
            stats["rdi_mean_var"] = float(rdi["rdi_variance"].mean())
            if "critique_flag" in rdi.columns:
                vc = rdi["critique_flag"].value_counts(dropna=False).to_dict()
                stats["dressage"] = int(vc.get("dressage_alert", 0))
                stats["vitality"] = int(vc.get("vitality_query", 0))
                stats["flag_rate_pct"] = round(
                    100 * rdi["critique_flag"].notna().mean(), 2
                )
    ardi_path = Path(f"data/processed/ardi/ardi_{city}_{stamp}.parquet")
    if ardi_path.exists():
        ardi = pd.read_parquet(ardi_path)
        stats["ardi_cells"] = int(len(ardi))
        stats["ardi_mean"] = float(ardi["ardi_v0"].mean())
        stats["ardi_speed_regime"] = float(ardi["speed_regime"].mean())
    prm_path = Path(f"data/processed/prm/prm_{city}_{stamp}.parquet")
    if prm_path.exists():
        prm = pd.read_parquet(prm_path)
        stats["prm_mean"] = float(prm["prm_v0"].mean())
        stats["prm_saturation"] = int((prm["prm_v0"] >= 0.95).sum())
    friction_path = Path(f"data/processed/friction/friction_zones_{city}_{stamp}.parquet")
    if friction_path.exists():
        fz = pd.read_parquet(friction_path)
        n_fz = int(fz["is_friction_zone"].sum())
        stats["friction_cells"] = n_fz
        stats["friction_rate_pct"] = round(100 * n_fz / max(len(fz), 1), 2)

    return stats


def sample_flag_rows(city: str, stamp: str) -> dict[str, list[pd.Series]]:
    """Return 2 dressage + 2 vitality sample rows for the city RDI (may be fewer)."""
    rdi_path = Path(f"data/processed/tago/rdi_{city}_{stamp}.parquet")
    out: dict[str, list[pd.Series]] = {"dressage_alert": [], "vitality_query": []}
    if not rdi_path.exists():
        return out
    rdi = pd.read_parquet(rdi_path)
    if "critique_flag" not in rdi.columns:
        return out
    for flag in out.keys():
        sub = rdi[rdi["critique_flag"] == flag].sort_values("rdi_magnitude", ascending=False)
        out[flag] = [sub.iloc[i] for i in range(min(2, len(sub)))]
    return out


def load_agent_excerpts(city: str) -> dict[str, str]:
    """Load rehearsal markdown (Day-3) — only Changwon has agent outputs."""
    if city != "changwon":
        return {}
    dir_path = Path("docs/evidence/opus_agents_rehearsal_20260424")
    out = {}
    for flag in ("dressage", "vitality"):
        candidates = sorted(dir_path.glob(f"{flag}_*.md"))
        if candidates:
            out[flag] = candidates[0].read_text(encoding="utf-8")
    return out


def extract_agent_first_questions(markdown_body: str, theorist: str, n: int = 3) -> list[str]:
    """Crude extraction of first N '**축 X**' + 'Q<num>.' blocks from rehearsal markdown."""
    # Scope to the theorist section.
    heading = f"## {theorist.capitalize()} — output"
    start = markdown_body.find(heading)
    if start == -1:
        return []
    body = markdown_body[start:]
    # Stop at next '## ' or 'pairwise'
    for end_marker in ("\n## ", "## Pairwise"):
        end = body[len(heading):].find(end_marker)
        if end != -1:
            body = body[: len(heading) + end]
            break
    # Extract Q-items — lines starting with 'Q\d+\.'
    import re

    qs = []
    for line in body.splitlines():
        m = re.match(r"\s*(Q\d+\.)\s*(.+)", line)
        if m:
            qs.append((m.group(1) + " " + m.group(2)).strip())
            if len(qs) >= n:
                break
    return qs


def render_flag_box(flag_name: str, row: pd.Series, role_labels: dict) -> str:
    flag_class = "dressage" if flag_name == "dressage_alert" else "vitality"
    route_id = str(row.get("route_id", ""))
    role = role_labels.get(route_id, "")
    msg_ko = html.escape(str(row.get("flag_message_ko", "") or ""))
    # Nicely split the Korean message on its own line per rhetorical question
    msg_html = msg_ko.replace("\n", "<br>\n")
    tb = pd.Timestamp(row["time_bin"]).strftime("%Y-%m-%d %H:%M")
    return (
        f'<div class="flag {flag_class}">'
        f'<b>{flag_name}</b> · <span class="meta">{route_id} · '
        f'{html.escape(role)} · {tb} · rdi_magnitude={row.get("rdi_magnitude", 0):.4f} · '
        f'variance={row.get("rdi_variance", 0):.4f} · n_obs={int(row.get("n_observations", 0))}</span>'
        f'<br><br>{msg_html}'
        f"</div>"
    )


def render_city_page(city: str, stats: dict, stamp: str, cities_manifest: dict) -> str:
    label = CITY_LABELS.get(city, city)
    theory = CITY_THEORETICAL.get(city, "")
    cfg = (cities_manifest.get("cities") or {}).get(city, {})
    routes = cfg.get("routes", [])
    role_labels = {r.get("routeid", ""): f'{r.get("route_no", "")} · {r.get("theoretical_role", "")}' for r in routes}

    flags = sample_flag_rows(city, stamp)
    agents = load_agent_excerpts(city)

    def num(v, fmt="{:.4f}", none_str="—"):
        return fmt.format(v) if v is not None and not (isinstance(v, float) and v != v) else none_str

    parts = []
    parts.append(f"<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>")
    parts.append(f"<title>{html.escape(label)} · Rhythmscape Day-3</title>")
    parts.append(f"<style>{CSS}</style></head><body>")

    parts.append("<div class='nav'>")
    parts.append(f"<a href='index.html'>← 4-city dashboard</a>")
    for other in CITY_LABELS:
        if other != city:
            parts.append(f"<a href='{other}.html'>{CITY_LABELS[other].split(' (')[0]}</a>")
    parts.append("</div>")

    parts.append(f"<h1>{html.escape(label)}</h1>")
    parts.append(f"<p class='meta'>Day 3 리포트 · 분석 날짜 {stamp} (Asia/Seoul) · 생성 {datetime.now().astimezone().isoformat(timespec='minutes')}</p>")
    parts.append(f"<p>{html.escape(theory)}</p>")

    # ---- 노선 manifest ----
    parts.append("<h2>3노선 구성</h2><table>")
    parts.append("<tr><th>route_no</th><th>routeid</th><th>route_type</th><th>theoretical_role</th></tr>")
    for r in routes:
        parts.append(
            f"<tr><td>{html.escape(str(r.get('route_no','')))}</td>"
            f"<td><code>{html.escape(str(r.get('routeid','')))}</code></td>"
            f"<td>{html.escape(str(r.get('route_type','')))}</td>"
            f"<td>{html.escape(str(r.get('theoretical_role','')))}</td></tr>"
        )
    parts.append("</table>")

    # ---- 핵심 수치 ----
    parts.append("<h2>핵심 지표</h2><table>")
    parts.append("<tr><th>지표</th><th>값</th><th>해석</th></tr>")
    parts.append(f"<tr><td>RDI bins</td><td class='num'>{stats.get('rdi_bins','—')}</td><td>처방-관측 대조 격자 수 (Day 2)</td></tr>")
    parts.append(f"<tr><td>RDI mean magnitude</td><td class='num'>{num(stats.get('rdi_mean_mag'))}</td><td>(|observed − prescribed|/prescribed)의 평균</td></tr>")
    parts.append(f"<tr><td>RDI mean variance</td><td class='num'>{num(stats.get('rdi_mean_var'))}</td><td>bin 내 관측 변동성</td></tr>")
    parts.append(f"<tr><td>dressage_alert</td><td class='num'>{stats.get('dressage','—')}</td><td>처방과 완벽 동기화 (조련)</td></tr>")
    parts.append(f"<tr><td>vitality_query</td><td class='num'>{stats.get('vitality','—')}</td><td>큰 이탈 + 큰 불규칙 (polyrhythmia)</td></tr>")
    parts.append(f"<tr><td>critique flag rate</td><td class='num'>{num(stats.get('flag_rate_pct'), '{:.2f}%')}</td><td>spec §6 목표 5-15%</td></tr>")
    parts.append(f"<tr><td>ARDI cells</td><td class='num'>{stats.get('ardi_cells','—')}</td><td>500m 격자 수</td></tr>")
    parts.append(f"<tr><td>ARDI mean</td><td class='num'>{num(stats.get('ardi_mean'))}</td><td>자동차 점유 (road_space_ratio × 0.25 + speed_regime × 0.15)</td></tr>")
    parts.append(f"<tr><td>ARDI speed_regime</td><td class='num'>{num(stats.get('ardi_speed_regime'), '{:.2%}')}</td><td>≥50km/h 도로 비율</td></tr>")
    parts.append(f"<tr><td>PRM mean</td><td class='num'>{num(stats.get('prm_mean'))}</td><td>보행 잔여 (walk_conn × (1-ARDI_norm))</td></tr>")
    parts.append(f"<tr><td>PRM saturation (≥0.95)</td><td class='num'>{stats.get('prm_saturation','—')}</td><td>\"pure pedestrian residue\" cells</td></tr>")
    parts.append(f"<tr><td>Friction zones</td><td class='num'>{stats.get('friction_cells','—')} ({num(stats.get('friction_rate_pct'),'{:.2f}%')})</td><td>ARDI ≥ p90 ∩ walk_connectivity ≥ p90</td></tr>")
    parts.append("</table>")

    # ---- ARDI / PRM heatmap (4-city image, single shared view) ----
    here = Path(f"reports/{city}.html")
    parts.append("<h2>ARDI v0 · PRM v0 heatmap (4-city 공통)</h2>")
    parts.append(f"<img src='{rel_evidence(here, 'ardi_day3_4city_comparison_20260424.png')}' alt='ARDI 4-city'>")
    parts.append(f"<img src='{rel_evidence(here, 'prm_day3_4city_comparison_20260424.png')}' alt='PRM 4-city'>")

    # ---- Friction zones ----
    parts.append("<h2>Friction zones (ARDI↑ ∩ walk_connectivity↑)</h2>")
    parts.append(f"<img src='{rel_evidence(here, 'friction_day3_4city_comparison_20260424.png')}' alt='Friction zones 4-city'>")

    # ---- RDI preview (Day-2 4-city) ----
    parts.append("<h2>RDI 시계열 (Day 2 4-city preview)</h2>")
    parts.append(f"<img src='{rel_evidence(here, 'rdi_day2_4city_preview_20260423.png')}' alt='RDI 4-city preview'>")

    # ---- critique_flag sample messages ----
    parts.append("<h2>critique_flag 대표 인용</h2>")
    if flags["dressage_alert"]:
        parts.append("<h3>dressage_alert (완벽한 동기화의 역설)</h3>")
        for row in flags["dressage_alert"][:1]:
            parts.append(render_flag_box("dressage_alert", row, role_labels))
    if flags["vitality_query"]:
        parts.append("<h3>vitality_query (큰 이탈 + 큰 불규칙)</h3>")
        for row in flags["vitality_query"][:1]:
            parts.append(render_flag_box("vitality_query", row, role_labels))
    if not flags["dressage_alert"] and not flags["vitality_query"]:
        parts.append("<p class='meta'>플래그 부여된 bin 없음.</p>")

    # ---- Opus agent quotes (Changwon only) ----
    if agents:
        parts.append("<h2>Opus 4.7 이론가 에이전트 질문 (Changwon rehearsal)</h2>")
        parts.append("<div class='disclaimer'>이하 질문들은 각 이론가 텍스트 계열로 훈련된 언어 모델이 생성한 확률적 응답이며, 해당 이론가의 입장이 아닙니다. 연구자의 비판적 독해를 대체하지 않습니다.</div>")
        if "dressage" in agents:
            parts.append("<h3>dressage_alert (BRT6000 @ 의창동환승센터) → Lefebvre + Foucault</h3>")
            for t in ("lefebvre", "foucault"):
                qs = extract_agent_first_questions(agents["dressage"], t, n=2)
                if qs:
                    parts.append(f"<div class='quote'><b>{t.capitalize()}</b><br>" + "<br><br>".join(html.escape(q) for q in qs) + "</div>")
        if "vitality" in agents:
            parts.append("<h3>vitality_query (271 @ 한우아파트) → Deleuze-Guattari + Lefebvre</h3>")
            for t in ("deleuze_guattari", "lefebvre"):
                qs = extract_agent_first_questions(agents["vitality"], t, n=2)
                if qs:
                    parts.append(f"<div class='quote'><b>{t.capitalize()}</b><br>" + "<br><br>".join(html.escape(q) for q in qs) + "</div>")
    else:
        parts.append(
            '<h2>Opus 이론가 에이전트 질문</h2>'
            '<p class="meta">Day 3 rehearsal은 창원 샘플에 한정. '
            '다른 도시는 Day 4 플래그 격자별 호출 예정.</p>'
        )

    parts.append("<div class='footer'>Rhythmscape · Day 3 afternoon snapshot · "
                 f"reports generated {datetime.now().astimezone().isoformat(timespec='minutes')}</div>")
    parts.append("</body></html>")
    return "".join(parts)


def render_index(all_stats: list[dict], stamp: str) -> str:
    parts = []
    parts.append(f"<!DOCTYPE html><html lang='ko'><head><meta charset='utf-8'>")
    parts.append("<title>Rhythmscape Day-3 · 4-city dashboard</title>")
    parts.append(f"<style>{CSS}</style></head><body>")
    parts.append("<h1>Rhythmscape — 4-city synchronic dashboard</h1>")
    parts.append(f"<p class='meta'>Day 3 afternoon · {stamp} KST · 리포트 생성 {datetime.now().astimezone().isoformat(timespec='minutes')}</p>")

    parts.append(
        "<p>"
        "네 도시(창원·성남 분당·세종·부산 영도)는 Lefebvre의 prescribed-lived 이항 "
        "위에서 <b>서로 독립적인 이론 위치</b>를 점유한다. 본 대시보드는 Day 3 오후 "
        "시점의 ARDI · PRM · RDI · friction zone 교차 관측을 요약한다."
        "</p>"
    )

    # ---- City cards ----
    parts.append("<h2>도시별 요약</h2>")
    parts.append("<table><tr>"
                 "<th>도시</th><th>RDI bins</th><th>flag rate</th>"
                 "<th>ARDI mean</th><th>speed_regime</th>"
                 "<th>PRM mean</th><th>PRM sat</th>"
                 "<th>Friction</th></tr>")
    for s in all_stats:
        slug = s["city"]
        parts.append(
            f"<tr><td><a href='{slug}.html'>{html.escape(s['label'])}</a></td>"
            f"<td class='num'>{s.get('rdi_bins','—')}</td>"
            f"<td class='num'>{s.get('flag_rate_pct','—')}%</td>"
            f"<td class='num'>{s.get('ardi_mean',0):.4f}</td>"
            f"<td class='num'>{s.get('ardi_speed_regime',0):.2%}</td>"
            f"<td class='num'>{s.get('prm_mean',0):.4f}</td>"
            f"<td class='num'>{s.get('prm_saturation','—')}</td>"
            f"<td class='num'>{s.get('friction_cells','—')} ({s.get('friction_rate_pct','—')}%)</td></tr>"
        )
    parts.append("</table>")

    # ---- regional_fix 4변주 ----
    parts.append("<h2>regional_fix 4변주 — 광역 축의 네 독립 극</h2>")
    parts.append(
        "<div class='sig-block'>"
        "<b>4도시가 regional_fix 단일 축에서 서로 독립적인 이론 위치를 점유</b>:"
        "<table>"
        "<tr><th>도시</th><th>노선</th><th>역할</th></tr>"
        "<tr><td>창원</td><td>710</td><td>광역 <b>결핍</b> — 공식 광역버스 타입 부재, 좌석으로 대체</td></tr>"
        "<tr><td>성남 분당</td><td>9407</td><td>광역 <b>특권</b> — 강남 직행좌석, 통근 회랑</td></tr>"
        "<tr><td>세종</td><td>1004</td><td>광역 <b>필수성</b> — 대전 유성-세종 행복도시 결합</td></tr>"
        "<tr><td>부산 영도</td><td>113</td><td>광역 <b>왜곡</b> — 다리 병목을 통과한 사하구 연결</td></tr>"
        "</table>"
        "</div>"
    )

    # ---- H-SJ double structure ----
    parts.append("<h2>H-SJ 이중 구조 — 세종의 처방 은닉 + 계획 내재 dressage</h2>")
    parts.append(
        "<div class='sig-block'>"
        "세종은 TAGO 연합에 prescribed 배차 데이터를 공개하지 않는 "
        "<b>처방 은닉 도시</b>였다. Day 3 오전 <code>bis.sejong.go.kr</code> "
        "직접 스크래핑으로 외부 처방 확보 후 RDI 재산출. 두 층에서 일관된 증거:"
        "<ul>"
        "<li><b>RDI 층</b>: 세종 17-19 band dressage rate <b>13.89%</b> ≈ 창원 midday <b>14.97%</b></li>"
        "<li><b>ARDI 층</b>: 세종 speed_regime <b>31.2%</b> > 창원 <b>27.2%</b> (4도시 최고)</li>"
        "<li><b>PRM 층</b>: 세종 saturation cells <b>43개</b> (4도시 최다)</li>"
        "</ul>"
        "즉 세종은 자동차 dressage와 보행 residue를 *동시에* 설계한다. "
        "H-SJ 가설이 단일 층이 아닌 세 층 모두에서 확증."
        "</div>"
    )

    # ---- Friction bimodal finding ----
    parts.append("<h2>Friction zone 이원 모드 — 0.4% vs 2.2%</h2>")
    parts.append(
        "<div class='sig-block'>"
        "<b>4도시 friction rate이 두 모드로 분리</b>:"
        "<ul>"
        "<li><b>~0.4%</b>: 창원 (0.41%), 세종 (0.39%) — 국가 주도 계획의 자동차/보행 공간 분리</li>"
        "<li><b>~2.2%</b>: 성남 분당 (2.20%), 부산 영도 (2.21%) — <i>완전 다른 맥락이 동일 밀도로 수렴</i></li>"
        "</ul>"
        "분당은 자본 주도 계획이 자동차+보행을 모두 <b>고밀도로 설계</b>한 결과. "
        "영도는 반도 지형이 자동차+보행을 <b>공간 부족으로 겹치게</b>한 결과. "
        "구조적 원인이 정반대이나 물리적 결과는 동일한 5배 집중. "
        "Day 4 이중 언어 브리프의 핵심 발견."
        "</div>"
    )

    # ---- Evidence images ----
    parts.append("<h2>시각적 증거</h2>")
    # from reports/index.html → ../docs/evidence/
    for title, fname in [
        ("RDI 4-city 시계열 (Day 2 preview)", "rdi_day2_4city_preview_20260423.png"),
        ("ARDI v0 4-city 비교 (road_space_ratio + speed_regime)", "ardi_day3_4city_comparison_20260424.png"),
        ("PRM v0 4-city 비교 (보행 잔여)", "prm_day3_4city_comparison_20260424.png"),
        ("Friction zones v0 4-city (ARDI↑ ∩ walk_connectivity↑)", "friction_day3_4city_comparison_20260424.png"),
    ]:
        parts.append(f"<h3>{html.escape(title)}</h3>")
        parts.append(f"<img src='../docs/evidence/{fname}' alt='{html.escape(title)}'>")

    # ---- Methodological notes ----
    parts.append("<h2>방법론적 조정 (Day 2-3 누적)</h2>")
    parts.append(
        "<ul>"
        "<li>RDI: bin 5분 → 30분 (최단 headway 20분 초과 배제), persistence 5틱 → 1 bin, dressage abs 0.05 → 0.10 (flag rate 5-15% 수렴)</li>"
        "<li>Sejong prescribed: TAGO 은닉 → bis.sejong.go.kr 스크래핑 (prescribed_source=\"sejongbis_scrape\")</li>"
        "<li>Sejong variants: Day 2 bbox-only pick(minor) → Day 3 B2 000362→000077 + 550 000030→000029 교체 (tick 창 유효 overlap 복구)</li>"
        "<li>Friction zone: PRM↑ → walk_connectivity↑로 게이트 변경 (PRM = walk_conn × (1-ARDI_norm)이라 ARDI↑와 수학적 anti-correlate)</li>"
        "<li>Anchor stagger: 06:55/06:57/06:59/07:01 (TAGO 30/30 세션 풀 포화 회피, Yeongdo 최후 배치)</li>"
        "<li>야간 수집: 20:00-06:59 stride 10 (Day 2 저녁 plist 병합)</li>"
        "</ul>"
    )

    parts.append("<div class='footer'>Rhythmscape Day-3 · generated "
                 f"{datetime.now().astimezone().isoformat(timespec='minutes')} · "
                 "Built with Opus 4.7 Hackathon</div>")
    parts.append("</body></html>")
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=None)
    parser.add_argument("--cities-yaml", type=Path, default=Path("config/cities.yaml"))
    parser.add_argument("--out-dir", type=Path, default=Path("reports"))
    args = parser.parse_args()

    if args.date:
        stamp = args.date
    else:
        from zoneinfo import ZoneInfo

        stamp = datetime.now(tz=ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")

    cities_manifest = load_cities_manifest(args.cities_yaml)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    all_stats = []
    for city in CITY_LABELS:
        # RDI uses Day 2 stamp for most cities; we use stamp but prefer
        # whichever parquet exists. Just use the given stamp.
        # For RDI, Day 2 (20260423) has richest data for non-Changwon cities.
        # We'll collect stats across both possible dates.
        stats = per_city_stats(city, stamp)
        # Fallback: if RDI empty under today's stamp, check Day 2
        if not stats.get("rdi_bins"):
            stats_day2 = per_city_stats(city, "20260423")
            # Merge RDI-related fields from day2 if present
            for k in ("rdi_bins", "rdi_mean_mag", "rdi_mean_var", "dressage", "vitality", "flag_rate_pct"):
                if k in stats_day2:
                    stats[k] = stats_day2[k]
        all_stats.append(stats)

        page_html = render_city_page(city, stats, stamp, cities_manifest)
        out_path = args.out_dir / f"{city}.html"
        out_path.write_text(page_html, encoding="utf-8")
        print(f"✓ {out_path}")

    index_html = render_index(all_stats, stamp)
    index_path = args.out_dir / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"✓ {index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
