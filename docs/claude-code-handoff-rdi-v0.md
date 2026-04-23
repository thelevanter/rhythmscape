# Claude Code 핸드오프 — RDI v0 + critique_flag 구현

> **이 문서를 가장 먼저 읽는 Claude Code 세션을 위한 작업 지시서.**
> **사양 확정일**: 2026-04-23 Day 2 오전 (제시카 + 케이 합의, Research Design Committee 심의 결과 반영)
> **목표 마감**: 2026-04-23 **18:30 KST** (창원 3노선 RDI 시각화 PNG + summary.md까지)
> **역산 근거**: Cowork 19:00~20:30 Code 결과 리뷰 → 22:30 RQ 후보 압축 완료 → 23:00 취침 → Day 3 07:30 RQ 결정 회의.
> **이 마감이 미끄러지면**: 블록 D(시각화)만 Day 3 아침 07:00~07:30으로 이월 가능. 블록 A·B·C는 오늘 안에 반드시 완료.

---

## 0. 지금 무엇이 벌어지고 있나

Rhythmscape 해커톤 Day 2 오전. 이미 진행 중인 것:
- TAGO 수집기가 launchd로 가동 중. 현재 약 100분치 parquet 누적 (08:12~). 이 세션 중에도 계속 쌓임.
- anchor 3종(routes, route_stations, stations) 확보
- OSM 창원 클립 완료
- **Research Design Committee 심의 완료** (4위원 + Red Team + 의장 권고). 전문은 `/tmp/rhythmscape_committee_result.txt` (606줄, 68KB). 케이·제시카가 공유하는 메모리.

**오늘 Day 2에 결정된 것**:
- 연구질문 최종 결정은 **Day 3 오전으로 공식 연기**. 오늘은 RQ에 무관한 공통분모 작업만.
- RQ5(에이전트 자체가 연구대상)는 데모 내러티브 층위로만 활용. 로그 인프라 생략.
- 4도시 유형학 주장은 유지하되 "분석적 깊이의 의도적 차등화"로 프레이밍 변경. 창원 심층, 영도 대조, 진주·사천 add-city 데모.

이제 **네가 할 일**은 이미 쌓이고 있는 TAGO 데이터로 **RDI v0 (magnitude만)**를 계산하고, **critique_flag 후처리**를 함께 구현하고, **창원 3노선 시계열 시각화 한 장**을 오늘 저녁까지 내는 것이다. ARDI·PRM은 내일 이후.

---

## 1. 반드시 먼저 읽을 것 (이 순서)

1. **`docs/analysis/critique_flag_spec.md`** — 오늘 오전 제시카 집필. 후처리 장치의 완전 사양. 임계값 산출 로직, 출력 스키마, Red Team 방어선까지 포함. **이번 작업의 주 문서.**
2. **`CLAUDE.md`** (리포 루트) — §5 코딩 원칙, §7 가드레일
3. **`../rhythmscape-spec.md`** §3.4 (RDI 수식), §9 (MVP 스코프)
4. **`docs/tago-batch-spec.md`** §3 (리듬 3층 매핑 — 왜 locations만 쓰고 arrivals(=ArvlInfoInqireService)는 "lived"로 쓰지 않는지)
5. **`docs/analysis/sentinel_rationale.md`** — 전략적 관측소 선정 근거. RDI 공간 해석의 이론적 기반
6. **`docs/analysis/route_selection_rationale.md`** — 3개 노선 선정 근거

읽기 전 구현 시작 금지.

---

## 2. 작업 순서

### 블록 A — Prescribed interval 확보 (예상 30분~1시간)

**목표**: 3개 노선의 공식 배차 간격을 확보하여 `data/processed/tago/prescribed_intervals.parquet`에 저장한다.

1. `data/raw/tago/routes/changwon_20260423.parquet`를 먼저 열어 **어떤 컬럼이 있는지** 확인한다. TAGO `BusRouteInfoInqireService`의 `getRouteInfoIem` 또는 유사 엔드포인트 응답이 이미 잡혀 있다면 배차 간격(`intervaltime` 또는 유사 필드)이 있을 가능성이 높다.
2. 배차 관련 컬럼이 **있으면**: 정규화하여 `prescribed_intervals.parquet` (schema: `route_id | daytype | peak_interval_min | off_peak_interval_min | source | collected_at`) 생성.
3. **없으면**: `src/rhythmscape/ingest/tago/routes.py`를 확장하여 배차 정보 추가 수집. 3노선 × 1회 호출 = 3 request. API 한도 영향 없음.
4. peak/off-peak 구분이 없으면 평일 기본값 하나만. 시간대 분리는 Day 3~4에.

**체크포인트**: `prescribed_intervals.parquet`이 존재하고 3개 노선 모두 배차 간격이 숫자로 채워져 있다.

---

### 블록 B — Observed interval 추출 → RDI magnitude (예상 2~3시간)

**목표**: 누적된 `locations/*.parquet`에서 실제 배차 간격을 노선×정류장×시간대로 재구성하고, prescribed와의 magnitude를 계산한다.

1. **모듈 신설**: `src/rhythmscape/metrics/__init__.py` + `src/rhythmscape/metrics/rdi.py`.
2. **Observed interval 계산 알고리즘**:
    - 모든 `locations/*.parquet` 파일을 노선×차량ID(vehicleno 또는 plateno)로 그룹화
    - 각 차량이 특정 정류장(gpslati/gpslong으로부터 가장 가까운 관측소)을 "통과"한 시각을 산출
    - 동일 정류장을 통과하는 연속 차량의 시간 차이 = observed interval
    - 5분 윈도우로 집계(`time_bin` 컬럼 추가)
3. **주의 — 커미티 경고 수용**: `BusLcInfoInqireService`(GPS 위치) 기반 산출만 사용한다. `ArvlInfoInqireService`(도착 예측, arrtime)는 "lived"가 아니라 "expected"다. arrivals parquet은 이번 RDI에서 참조하지 않는다. 향후 3층(prescribed-expected-lived) 분리 분석용으로 보존.
4. **RDI magnitude 공식**:
   ```
   rdi_magnitude(g, t, route) = |observed_interval - prescribed_interval| / prescribed_interval
   ```
5. **variance 추가**: 5분 bin 내 observed_interval의 표준편차. `critique_flag`의 `vitality_query` 판정에 필요.
6. 출력: `data/processed/tago/rdi_{YYYYMMDD}.parquet`
   - schema: `route_id | station_id | time_bin | observed_interval | prescribed_interval | rdi_magnitude | rdi_variance | n_observations`

**체크포인트**: RDI parquet이 생성되고, 최소 한 노선·한 정류장에서 시간대별 magnitude 시계열이 그려진다.

---

### 블록 C — critique_flag 후처리 (예상 1~1.5시간)

**목표**: `critique_flag_spec.md` §2~§4 정의대로 플래그를 부여한다.

1. 신설: `src/rhythmscape/metrics/critique.py`. 사양서 §8의 세 함수 시그니처를 그대로 구현:
    - `compute_thresholds(rdi_df) -> dict`
    - `apply_critique_flags(rdi_df, thresholds) -> pd.DataFrame`
    - `extract_flagged_rows(rdi_df) -> pd.DataFrame`
2. 임계값을 `config/critique_flag.yaml`로 영속화 (사양서 §3 예시 참조).
3. 플래그 메시지 한국어 텍스트는 사양서 §2.1 / §2.2에 있는 초안을 **그대로** 사용한다. 영문은 Day 4 집필 예정이므로 `flag_message_en` 컬럼은 빈 값(None).
4. 플래그 부여된 행만 `data/processed/tago/critique_flags_{YYYYMMDD}.parquet`로 별도 추출.
5. **테스트 조건** (사양서 §6):
    - 전체 행 대비 플래그 비율이 5~15%인지
    - 50% 초과나 1% 미만이면 임계값 조정 필요 → 사양서 §3의 `magnitude_absolute` 값을 재검토
    - 노선별 플래그 분포 기록

**체크포인트**: critique_flags parquet이 생성되고, 최소 한 건의 `dressage_alert`와 한 건의 `vitality_query`가 실제 발현된다.

---

### 블록 D — 시각화 한 장 (예상 1시간)

**목표**: 오늘 저녁 Cowork 리뷰용 차트 하나.

1. `notebooks/rdi_day2_preview.ipynb` 또는 `scripts/preview_rdi.py`로 간단히.
2. 3개 노선, 각 노선의 대표 정류장 하나씩, 08:12~현재까지의 `rdi_magnitude` 시계열 3개 subplot.
3. `critique_flag`가 부여된 bin은 색상 또는 마커로 강조. dressage_alert = 파란색, vitality_query = 빨간색.
4. 출력: `docs/evidence/rdi_day2_preview_{YYYYMMDD}.png`
5. 동시에 짧은 요약: `docs/analysis/rdi_day2_summary.md`에 노선별 평균 magnitude, variance, 플래그 빈도를 markdown 표로 기록.

**체크포인트**: PNG 하나 + markdown 요약 하나.

---

## 3. 이번 세션 DoD

모두 충족해야 세션 종료. **18:30 KST까지 도착이 목표.**

- [ ] `prescribed_intervals.parquet` 존재, 3개 노선 모두 값 채워짐
- [ ] `src/rhythmscape/metrics/rdi.py` + `critique.py` 구현, pytest 스모크 테스트 1건씩
- [ ] `rdi_{YYYYMMDD}.parquet` 생성, 컬럼 명세 일치
- [ ] `config/critique_flag.yaml` 생성, 임계값 + 메타데이터 기록
- [ ] `critique_flags_{YYYYMMDD}.parquet` 생성, 최소 2건 플래그 발현
- [ ] `rdi_day2_preview_{YYYYMMDD}.png` 생성 — **Cowork 저녁 리뷰(19:00~) 전까지 도착 필수**
- [ ] `rdi_day2_summary.md` 작성 — 노선별 평균 magnitude, variance, 플래그 빈도를 markdown 표로
- [ ] `build-log.md`에 Day 2 엔트리 추가 (블록 A/B/C/D 각 완료 시각 + 이슈 + 내일 시작 지점)

**중간 체크포인트 권장**:
- 13:00 블록 A 완료 여부
- 15:30 블록 B 중간 산출물
- 17:30 블록 C 완료
- 18:30 블록 D 완료 → Cowork 전달

---

## 4. 피할 것 (CLAUDE.md §6 + 커미티 경고 수용)

- **arrivals parquet을 "lived"로 쓰지 말 것.** `ArvlInfoInqireService`는 "expected" 층이다. RDI v0는 locations(GPS)만 사용.
- **임계값에 공간 태그(industrial_zone, cbd 등)를 쓰지 말 것.** Red Team의 공격 지점. 분위수 후험 산출만.
- **플래그 메시지를 서술문으로 바꾸지 말 것.** 사양서의 의문문 형식을 그대로 유지. 판정이 아닌 질문 호출.
- **랜덤 시드 고정 없이 추출 순서 정하지 말 것.** 이번 파이프라인은 전부 결정론이어야 함.
- **기존 수집기 코드를 건드리지 말 것.** ingest/tago/는 가동 중이다. metrics/는 신설.
- **ARDI, PRM 코드는 오늘 쓰지 말 것.** 내일 이후 작업.

---

## 5. 보고 형식

세션 종료 시 `build-log.md`에 다음 형식으로 누적:

```
## Day 2 — 2026-04-23 — RDI v0 + critique_flag

### 완료
- 블록 A: prescribed_intervals.parquet 생성 (HH:MM). 노선별 배차: ...
- 블록 B: RDI magnitude 계산 (HH:MM). 총 관측 bin 수: N. 노선별 평균 magnitude: ...
- 블록 C: critique_flag 부여 (HH:MM). dressage_alert: N건, vitality_query: N건, 전체 대비 비율: X%
- 블록 D: 시각화 (HH:MM)

### 결정 사항
- ...

### 이슈 / 미해결
- ...

### 다음 세션 (Day 3) 시작 지점
- ...
```

Cowork(제시카)는 저녁에 `build-log.md`와 `rdi_day2_preview.png`를 읽고 리뷰한다. 그걸 기반으로 내일 오전에 RQ 최종 결정.

---

**End of handoff. 사양서(`docs/analysis/critique_flag_spec.md`) 먼저 읽고 시작.**
