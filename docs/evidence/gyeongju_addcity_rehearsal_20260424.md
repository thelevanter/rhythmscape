# gyeongju add-city 리허설 — Day 3 (2026-04-24)

**CLI (계획)**: `rhythmscape add-city --name gyeongju --mode minimal`
**실제 실행**: `python scripts/add_city.py --name gyeongju --mode minimal`
**cityCode 검증 결과**: `37130` → `gyeongju`

## 실행 흐름 + 단계별 소요

| 단계 | 소요 (초) |
|---|---:|
| 1. cityCode TAGO 검증 | 0.12 |
| 2. OSM PBF bbox 추출 | 1.00 |
| 3. ARDI v0 산출 (500m grid, osmium → geopandas → overlay) | 1.10 |
| 4. Heatmap PNG | 0.23 |
| **총합** | **2.45** |

**Day 4 라이브 데모 30초 목표**: ✅ 통과 

## ARDI v0 결과

- cells: `3591`
- cells with roads: `1509`
- mean ARDI: `0.0397`
- max ARDI: `0.2054`
- mean road_space_ratio: `0.0172`
- mean speed_regime: `0.2357 (23.57%)`
- OSM driving ways loaded: `7378`
- ARDI parquet: `data/processed/ardi/ardi_gyeongju_20260424.parquet`
- Heatmap: `docs/evidence/gyeongju_addcity_ardi_20260424.png`

## 한계 (minimal mode 명시적 trade-off)

- RDI 산출 불가 — 본격 분석은 TAGO tick 수집이 수일 누적되어야 함. minimal 모드는 **ARDI 단독의 공간 지표만 제공**.
- PRM / friction zone 생략 — 보행 네트워크 + ARDI 상위 decile 계산은 full 모드(add-city --mode full)에서 활성화.
- critique_flag / Opus 에이전트 비활성화 — RDI 산출이 선행 조건.

## 사용 의도

해커톤 심사 시 **"4도시 + α" 확장성**을 증명하는 라이브 데모. 주어진 도시 이름 → 30초 내에 OSM 인프라 기반 ARDI 지도 산출. 본격 분석은 `--mode full`로 TAGO 수집 가동 후 수일치 자료 누적을 요구.
