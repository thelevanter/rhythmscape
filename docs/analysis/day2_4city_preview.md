# Rhythmscape Day 2 오후 — 4도시 공시적 프리뷰

**작성 시각**: 2026-04-23 16:45 KST
**작성자**: Claude Code (구현), Cowork 리뷰 대기
**대상**: 케이, Day 3 RQ 결정 회의 입력 자료 (Day 2 오전 보고서 증보분)
**관련 문서**: `day2_morning_report.md` (오전 1차 관측), `add_city_selection_rationale.md` (4도시 이론 배치), `sejong_prescription_opacity.md` (처방 은닉 상세), `night_collection_rationale.md` (야간 수집 근거), `271_intervaltime_verification.md` (271 재해석)

---

## 한 줄 요약

Day 2 오후 14:42 KST부터 **4도시 TAGO 수집이 동시 가동**됐고, 현재 16:45
기준 3도시(창원·성남 분당·부산 영도)에 대해 **RDI 공시적 비교가 가능한
분포**가 확보됐다. 세종은 **처방 자체가 TAGO 연합에 없음**이 확인되어
공시적 비교의 *제4의 극* — "처방 은닉 도시" — 로 재프레임되었다. 세 가지
관찰이 두드러졌다: **(1) 성남 분당이 mean magnitude 0.796으로 세 도시
중 압도적 최고** (특권 통근 회랑 가설의 경험적 지지), **(2) 영도가 mean
variance 1.83으로 최고** (지형 제약 variance 가설 지지), **(3) 271의
"administrative representation vs operational practice" 재해석**이 Day 3-4
브리프의 개념 정밀화 포인트로 확정됐다.

---

## 1. 무엇을 측정한 것인가

Day 2 오전 보고서(`day2_morning_report.md`)와 동일한 RDI 수식:

```
RDI magnitude = | observed_interval − prescribed_interval | / prescribed_interval
```

차이점 두 가지:

1. **4도시 일반화**: `rdi.py`가 `--city/--all` 인자를 받도록 Block 1에서
   리팩토링. 출력은 도시별 분리(`rdi_{city}_{YYYYMMDD}.parquet`,
   `prescribed_intervals_{city}.parquet`). 네 도시가 동일 파이프라인을
   통과.
2. **관측 창이 8+ 시간**: 오전 보고는 3시간 창. 오늘 오후는 14:42 KST
   launchctl load 이후 2h + 기존 창원 full-day = 3도시 비교 가능 분포
   확보.

---

## 2. 관측 조건

| 항목 | 값 |
|---|---|
| 관측 창 | 2026-04-23 08:12 → 16:40 KST (창원), 14:42 → 16:40 KST (성남·세종·영도) |
| 대상 도시 | 4 (창원 flagship + 성남 분당 + 세종 + 부산 영도) |
| 대상 노선 | 총 12 (4도시 × 3노선) |
| 관측소 | 각 도시 9 (노선당 3, quartile_dir0 전략) |
| 시공간 격자 | 4,553 bins (30분 단위, 3도시 합계; 세종 0 bin — 처방 공백) |
| 플래그 부여 | 총 451 bins — dressage 417 + vitality 34 |
| 플래그 비율 | 창원 9.65% · 성남 9.25% · 영도 11.37% (spec §6 목표 5~15% 내) |

---

## 3. 핵심 발견 — 3도시 공시적 비교

### 3.1 관측 요약표

| 도시 | RDI bins | mean mag | median mag | mean var | dressage | vitality | flag rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| 창원 (flagship) | 2,871 | 0.346 | 0.350 | 1.00 | 262 | 15 | 9.65% |
| 성남 분당 | 811 | **0.796** | 0.533 | 1.36 | 67 | 8 | 9.25% |
| 부산 영도 | 871 | 0.285 | 0.131 | **1.83** | 88 | 11 | 11.37% |

### 3.2 성남 분당 — 특권 통근 회랑의 경험적 지지

성남 분당이 **mean magnitude 0.796으로 3도시 중 압도적 최고**. 창원
(0.346)·영도(0.285) 대비 2~3배 높음. 해석:

- 분당의 3노선 중 9407(분당↔강남 직행좌석, prescribed 10분)과 101(오리↔
  수서 central spine, prescribed 15분)이 **prescribed를 매우 타이트하게
  설정**한 상태에서 실측이 벌어져 RDI가 누적.
- `route_selection_rationale.md` (분당 §1.2(b))의 *"광역 자본 결절의 과잉
  / 특권적 통근 회랑"* 가설과 경험적 일치. **타이트한 처방 × 서울 방면
  정체 민감성 = 큰 RDI**.
- 이것은 분당의 "잘못"이 아니라 *타이트한 약속이 먼저 존재해야만 큰 괴리
  도 측정 가능*하다는 측정 구조의 귀결이기도 하다. Lefebvre 용어로는
  *polyrhythmia* — 민간 자본이 설정한 약속과 도시 교통 체계 lived의
  충돌이 가장 선명하게 드러나는 도시.

### 3.3 영도 — 지형 제약의 variance 집약

영도가 **mean variance 1.83으로 3도시 중 최고** (창원 1.00, 성남 1.36).
mean magnitude는 0.285로 낮지만 variance는 최고 — **"격차가 크지 않으나
불규칙성이 체계적으로 존재"**의 전형. 해석:

- `add_city_selection_rationale.md` §3.1 가설 H-YD ("영도는 prescribed와
  lived의 격차가 지형-인프라 제약에 의해 *구조적으로* 생산된다")와
  경험적 일치.
- 다리 병목(영도대교/부산대교), 봉래산 중앙 돌기, 해안선 도로가 만드는
  관측 variance의 누적. 창원·분당이 *magnitude 격차*로 rhythm을 쓴다면,
  영도는 *variance*로 쓴다.
- 영도구7(마을버스 · 봉래산) vs 8번(영도대교 관통)의 variance 차이가
  Day 3에 분해 분석 대상.

### 3.4 창원 — magnitude·variance 중간치의 안정적 기준

창원이 mean magnitude 0.346, variance 1.00으로 세 도시 중 *중간*. 단일
도시만 오전 8시부터 8+ 시간 누적된 샘플이라 절대 수치 비교에는 주의
필요(다른 두 도시는 2시간만 누적).

- 단위 시간 샘플 밀도로 보정하면 창원은 bin당 n_observations 지표가
  다른 도시보다 풍부하여 noise가 낮음 — Lefebvre의 *eurhythmia*에 가장
  가까운 baseline 포지션 유지.
- **271**의 "administrative representation vs operational practice"
  재해석(Day 2 오후 Block 4, `271_intervaltime_verification.md`)으로
  창원 RDI의 이론적 무게가 더 정밀해졌다 — RDI=0.6에서 관측되는 arrhythmia
  는 "schedule off by 60%"가 아니라 "registered service ceiling vs
  single-vehicle operational practice"의 격차.

---

## 4. 세종 — 처방 은닉 도시 (Prescription Opacity)

Day 2 오후 Block 1 RDI 일반화 과정에서 **TAGO `getRouteInfoIem`이 세종
3노선 모두의 `intervaltime*` 3개 필드를 NaN으로 반환**한다는 사실이
확인됐다. 4도시 중 유일한 경우.

**이론적 함의** (`add_city_selection_rationale.md` §2.1, Cowork 기록):

Lefebvre의 prescribed-lived 이항은 "처방이 존재하고 실측과 비교 가능하다"
는 암묵적 전제 위에 있다. 세종은 이 전제를 깨뜨린다. Rhythmscape의
질문을 확장:

```
prescribed–lived 격차 → prescribed의 가시성 / 은닉성 (visibility of prescription)
```

세 가설이 열린 채로 남아 있다 (§2.1):
- **A. BIS 거버넌스 차이** — 특별자치시 제도의 데이터 프로토콜 비대칭
- **B. Processualist 계획도시** — 배차가 *잠정 운영*이라 공식 노출 안 함
- **C. 행정중심도시의 데이터 공개 폐쇄성** — 자치 거버넌스의 선별적 개방

Day 3 오전에 `sejongbis.kr` 스크래핑으로 외부 보강(`prescribed_source=
"sejongbis_scrape"` 태그). `observed-median proxy`는 영구 금지(RDI
의미 뒤집힘). 상세: `sejong_prescription_opacity.md`.

**관찰**: 세종의 **locations 수집은 정상** — 운영 층은 살아있고 처방 층
만 부재. 이 비대칭 자체가 4도시 비교의 *제4의 극*을 구성한다. PNG 4번째
패널이 이 비대칭을 도표화(locations rows/bin은 자라고, prescribed는 0
dashed line으로 표시).

---

## 5. critique_flag 4도시 분포

`critique_flag_spec.md` §2의 두 플래그가 세 도시에서 모두 발현. 설계
목표 범위(5~15%) 내 안정적 수렴.

### 5.1 축별 집약 패턴 (3도시 교차)

**dressage_alert** — 완벽한 동기화의 역설:
- 창원 262 / 성남 67 / 영도 88
- 관측 시간 보정(bin 수 대비 비율)하면: 창원 9.13% / 성남 8.26% / 영도
  10.10% — 영도가 가장 dressage 밀도 높음
- 영도의 dressage 우세는 *지형이 오히려 규범적 리듬을 강제*하는 경로
  (다리 병목이 운행 쟁투를 줄이고, 배차 준수 의지를 높이는 효과)로
  해석 가능. Day 3 이후 노선별 분해 필요.

**vitality_query** — 큰 이탈 + 큰 불규칙:
- 창원 15 / 성남 8 / 영도 11
- 세 도시 모두 magnitude 상위 + variance 상위 교집합에서 발동. 성남이
  8건으로 절대 수는 적으나, 분당의 9407 한 노선에 집중될 가능성 높음
  (Day 3 분해 분석).

### 5.2 플래그 메시지의 도시별 tuning (Day 3~4)

현재 플래그 메시지는 spec §2.1/§2.2의 한국어 초안 그대로(4도시 공통). Day
3~4 이중 언어 브리프 집필 시 **도시별 맥락 annotation** 추가 예정. 예:

- 창원 dressage_alert → "이 완벽한 동기화는 산업단지 교대조 셔틀의
  dressage인가, 야간 저수요 격자의 우연인가?"
- 분당 dressage_alert → "이 완벽한 동기화는 지식노동자 통근 리듬의
  체계적 종속인가, 민간 자본 계획 도시의 정시성 덕목인가?"
- 영도 dressage_alert → "이 완벽한 동기화는 다리 병목이 강제하는
  operational rigidity인가, 관광-gentrified 공간의 안정화된 리듬인가?"

---

## 6. 방법론적 편차·조정 (Day 2 오후 신규)

오전 보고서에 기록된 3건(bin 5→30분, persistence 5→1, absolute 0.05→
0.10)에 더해, 오후에 발생한 3건 추가:

1. **세종 RDI v0 제외** (Option 3): prescribed NaN으로 인한 전수 drop.
   `sejong_prescription_opacity.md` 참조.
2. **영도 bbox spatial filter ≥30%**: 부산 cityCode 21 전체 302 노선에서
   영도구 내부 정류장 비율 30%+ 필터링. 결과 9/12 노선 필터 통과, 3축
   매칭 가능.
3. **271 prescribed 해석 유지** (Block 4): `intervaltime=94`를 관측 median
   37분으로 대체하지 않고 그대로 유지. **RDI의 Lefebvrean "administrative
   representation vs operational practice" 의미**를 보존. 기록:
   `271_intervaltime_verification.md`.

---

## 7. 한계와 유보

- **2h vs 8h 샘플 불균형**: 창원만 full-day 근접, 다른 3도시는 14:42
  load부터. 저녁 19:59 tick 종료 시점에 전 도시 5+ 시간 분포 확보 후
  재평가.
- **세종 RDI 전면 부재**: Day 3 오전 `sejongbis.kr` 보강 후 재포함.
- **주말 prescribed 누락 (영도)**: 평일 전용 분석에서는 비블로킹. 주말
  분석에서 재출현 예상.
- **야간 수집 미반영**: `night_collection_rationale.md` §3.1에 따라 Day 3
  07:30 RQ 회의 직후 plist 업데이트. 오늘 저녁 19:30~19:45 실험 tick
  1회로 빈 응답 처리 검증.
- **타임스탬프 정렬**: 4도시 tick이 14:42에 동시 load됐으나 첫 fire는
  분 경계(14:47). 1~5분 오차 가능, 시계열 비교 시 주의.
- **critique_flag 임계값은 도시별 분리 산출**. 교차 도시 비교 시
  "도시 A의 dressage 임계는 도시 B의 임계와 다르다" 주의. `config/
  critique_flag_{city}.yaml` 각 파일 참조.

---

## 8. 이것이 왜 중요한가 — 해커톤적 맥락 (Day 2 오후 추가)

오전에 이미 수행한 세 가지(파이프라인 가동·이론-경험 정렬·비판 장치
실증)에 더해, 오후에 세 가지가 확보됐다.

1. **4도시 공시적 비교 가능성 실증**: 단일 코드 경로(`--city` 인자)로
   4도시를 동등 처리할 수 있음이 확인됐다. `config/cities.yaml`
   manifest 방식의 재현성 입증. 심사 Reproducibility(15%) 직접 근거.
2. **"처방 은닉"이라는 제4의 이론적 범주 발견**: 세종의 TAGO 데이터
   공백이 Rhythmscape 프레임을 확장시켰다. Lefebvre의 prescribed-lived
   이항에 "visibility of prescription" 차원이 추가된 셈. Day 3~4 논문
   수준 확장의 자양분.
3. **"administrative representation vs operational practice" 재개념화**:
   271 검증(Block 4)이 RDI 해석의 정밀도를 상승시켰다. "약속과 실측의
   격차"라는 순진한 버전을 넘어, **"행정적 표상과 운영 실무의 격차"**
   라는 Lefebvrean 정밀판이 생겼다.

그 결과, Day 3 07:30 RQ 회의는 **4도시 분포를 본 뒤의 결정**이 된다.
이론만으로 RQ를 고르는 것이 아니라, 3도시(세종 opacity) 경험 분포에
비추어 *어느 도시 조합이 가장 날카로운 칼날을 가지는지* 판단 가능.

---

## 9. 다음 단계

### 오늘 저녁 (16:45 이후)
- 18:00 Cowork 리뷰용으로 이 보고서 + PNG 제출
- **19:30~19:45 실험 tick 1회** — TAGO 차량 0대 상황 응답 검증
  (`night_collection_rationale.md` §3.4)
- 19:59 주간 tick 종료 후 전일 분포 최종 확보

### 내일 아침 (Day 3)
- 07:30~08:30 RQ 최종 결정 회의
- **08:30~ 즉시**: 야간 수집 plist 업데이트 + launchctl reload
  (`night_collection_rationale.md` §3.1)
- 09:00~ 세종 `sejongbis.kr` 스크래핑 모듈 개발 (Option 1)
- 10:00~ RQ 결정에 따라 ARDI 또는 다음 분석 착수

---

**산출물**
- 시각화: `docs/evidence/rdi_day2_4city_preview_20260423.png`
- 도시별 RDI: `data/processed/tago/rdi_{changwon,seongnam_bundang,busan_yeongdo}_20260423.parquet`
- 플래그: `data/processed/tago/critique_flags_{city}_20260423.parquet`
- 임계값: `config/critique_flag_{city}.yaml` (3개)
- 스크립트: `scripts/preview_rdi_4city.py`
- 분석 문서:
  - `sejong_prescription_opacity.md`
  - `271_intervaltime_verification.md`
  - `night_collection_rationale.md` (Cowork)
  - `add_city_selection_rationale.md` (Cowork)
- 로그: `rhythmscape/build-log.md` Day 2 오후 엔트리

**커밋**: (TBD — 이 보고서 포함 consolidated 커밋 준비 중)
