# critique_flag — RDI 후처리 비판 장치 사양서

**Status**: Day 2 오전 설계. Cowork 작성 → Code 구현 대기.
**Binds**: `src/rhythmscape/metrics/rdi.py` (RDI 계산) → `src/rhythmscape/metrics/critique.py` (플래그 부여).
**Upstream**: Research Design Committee 의장 권고 §4 (2026-04-23) + 리듬분석 철학자 §5-(1) Dressage Index 제안 + Red Team 제안 §IV-2/§IV-3.

---

## 1. 이 장치가 해결하는 문제

RDI는 "처방된 리듬(공식 배차)"과 "살아 있는 리듬(관측 배차)"의 격차를 수치화한다. 그러나 **격차가 클수록 병리이고, 격차가 0일수록 정상**이라는 암묵적 서사는 Lefebvre의 arrhythmia 개념을 정면으로 배반한다. Lefebvre에게 arrhythmia는 의학적 진단이 아니라 **사회적 리듬들의 강요된 동기화가 균열하는 순간**이며, 그 자체로 해방의 가능성을 품는다(*Éléments de rythmanalyse*, 1992/2004, Ch. 4). 반대로 prescribed와 lived가 완전히 동기화될 때야말로 Lefebvre가 가장 경계한 **dressage**(조련) — 신체를 산업적·국가적 시간에 종속시키는 완성된 권력 작동 — 의 전형이다.

Research Design Committee는 이 모순을 "수식 구조 자체에 새기지 않으면 '지표는 질문'이라는 선언은 서문의 면죄부로 남는다"고 진단했다. Red Team은 여기에 "RDI≈0을 dressage로 판정하되 산업지구라는 공간 태그로 판정하는 것은 이론적 회피"라고 추가 공격했다. 의장은 두 요구를 통합하는 단일 장치로 `critique_flag`를 권고했다.

`critique_flag`는 **RDI 계산 직후 DataFrame에 두 종류의 해석적 플래그를 자동 부여**하는 후처리 레이어다. 모든 수치 출력이 질문과 함께 제시되는 구조를 강제하되, 판정 기준을 공간적 선험이 아닌 **RDI 자체의 통계적 프로파일에서 도출**함으로써 Red Team의 공격을 수용한다.

---

## 2. 두 플래그 정의

### 2.1 `dressage_alert` — 완벽한 동기화의 역설

**발동 조건**: 해당 격자·시간대·노선에서 RDI magnitude가 지속적으로 0에 수렴.

**조작적 정의**:

```
dressage_alert ⇔
    (rdi_magnitude < τ_dress_abs)
    AND (rdi_magnitude ∈ lowest_decile of global distribution)
    AND (duration ≥ N_persist ticks)
```

- `τ_dress_abs` (절대 플로어): 0.05 (즉 5% 이내 편차). 분위수만 쓰면 "항상 하위 10%가 flag되는" 항상성 문제 발생 → 절대값과 AND로 결합
- `lowest_decile`: 전체 관측 분포의 10분위. 공간적 선험(예: industrial_zone 태그) 대신 후험적 분포로 판정
- `N_persist`: 연속 5틱 (=5분) 이상 지속. 단발적 정시 도착이 아닌 구조적 동기화만 포착

**해석적 메시지** (한국어 초안):
> 이 격자·시간대의 리듬은 처방된 시간표와 거의 완벽히 일치하고 있다. 이 동기화는 다음 중 무엇인가?
> (1) 산업 교대조·통학·출퇴근 리듬에 대한 체계적 종속의 징후(dressage)인가?
> (2) 이용자 편의를 위한 정당한 안정성인가?
> (3) 배차 간격이 실제 수요와 무관하게 설정된 결과로 우연히 만들어진 일치인가?
> 이 구분은 수치 내부에서 결정되지 않는다. 공간적·역사적 맥락의 조회를 요구한다.

### 2.2 `vitality_query` — 큰 이탈, 큰 불규칙

**발동 조건**: RDI magnitude 상위 10분위 AND variance 상위 10분위.

**조작적 정의**:

```
vitality_query ⇔
    (rdi_magnitude ∈ highest_decile)
    AND (rdi_variance ∈ highest_decile)
```

둘 다 높아야 발동. magnitude만 높으면 단순한 시스템 지연(혼잡)이고, variance만 높으면 측정 노이즈일 가능성이 있다. **큰 이탈이 불규칙하게 일어날 때**가 Lefebvre의 polyrhythmia — 여러 리듬의 충돌이 살아 있는 지점 — 와 가장 가까운 경험적 프록시다.

**해석적 메시지** (한국어 초안):
> 이 격자·시간대에서 리듬이 크게 이탈하고, 그 이탈 자체도 불규칙하다. 이것은 다음 중 무엇인가?
> (1) 시스템 실패(사고·정체·결행)의 징후인가?
> (2) 생활세계의 자율적 리듬(장날, 시장 영업, 지역 행사, 종교 의례, 집회)과 대중교통 처방의 접합점인가?
> (3) 측정 노이즈의 누적인가?
> 이 구분은 현장 관찰 또는 공간적 맥락 조회를 요구한다.

---

## 3. 임계값 산출 로직

**원칙**: 임계값은 데이터에서 후험적으로 산출한다. 공간적·시간적 선험 태그는 사용하지 않는다.

**산출 시점**: RDI 전체 계산 완료 후, 플래그 부여 직전. 전체 관측 분포를 1회 주사하여 분위수를 계산하고, `config/critique_flag.yaml`에 기록한다.

**재현성 요건**:
- 분위수 계산에 사용한 데이터셋의 시간 범위, 노선 목록, 레코드 수를 `config/critique_flag.yaml`에 메타데이터로 저장
- 동일 데이터셋 → 동일 임계값. 랜덤 시드 불필요(순수 통계).
- 데이터가 추가되면 임계값 재산출. 이전 값은 `config/critique_flag.{YYYYMMDD}.yaml`로 아카이브.

**예시 구성**:
```yaml
# config/critique_flag.yaml
computed_at: "2026-04-23T18:00:00+09:00"
source_window: ["2026-04-23T08:12+09:00", "2026-04-23T17:30+09:00"]
routes: ["CWB379002710", "CWB379060000", "CWB379007100"]
n_observations: 5940
thresholds:
  dressage:
    magnitude_absolute: 0.05
    magnitude_decile_10: 0.038   # computed
    persistence_ticks: 5
  vitality:
    magnitude_decile_90: 0.412   # computed
    variance_decile_90: 0.087    # computed
```

---

## 4. 출력 스키마

RDI DataFrame에 4개 컬럼을 추가한다:

| 컬럼명 | 타입 | 설명 |
|---|---|---|
| `critique_flag` | `str \| None` | `"dressage_alert"`, `"vitality_query"`, 또는 `None` |
| `flag_message_ko` | `str \| None` | 한국어 해석 질문 (2.1/2.2의 메시지 텍스트) |
| `flag_message_en` | `str \| None` | 영문 번역 (이중 언어 브리프용. 초안은 Day 4 집필) |
| `flag_rationale` | `dict \| None` | 판정 근거. `{"rule": "magnitude<0.05 AND persistence=7ticks", "values": {...}}` |

플래그가 부여되지 않은 행은 네 컬럼 모두 `None`. 이것은 "플래그 없음 = 정상"이 아니라 **"현 장치로는 판정 유보"**를 뜻한다. 리포트 렌더링 단계에서 이 구분을 명시한다.

**별도 산출물**: `data/processed/tago/critique_flags_{YYYYMMDD}.parquet`로 플래그 부여된 행만 추출·보존. 메타데이터 분석(플래그 분포, 노선별 빈도)에 사용.

---

## 5. Opus 이론가 에이전트와의 연결

`critique_flag`는 이론가 에이전트의 **입력 선별자** 역할을 겸한다.

- `dressage_alert`가 부여된 격자·시간대는 **Lefebvre 에이전트 + Foucault 에이전트**로 라우팅 (조련 및 정상화 질문)
- `vitality_query`가 부여된 격자·시간대는 **Deleuze-Guattari 에이전트 + Lefebvre 에이전트**로 라우팅 (ritornello 및 polyrhythmia 질문)
- 플래그 없는 대량 관측은 에이전트 호출 대상이 아님 → API 비용 통제

의장 권고에 따라 에이전트 출력은 **의문문 목록 형식으로 고정**한다. 첫 줄에 인식론적 면책 문구 필수: "이것은 [이론가명]의 입장이 아니라, [이론가명]의 텍스트 계열로 훈련된 언어 모델이 생성한 확률적 응답이다." 이 프레이밍은 이론가 에이전트 프롬프트(Cowork 작업 ③) 설계에서 세부 처리한다.

---

## 6. 테스트 조건 (Code 구현 후 검증)

현재 확보된 103분치(2026-04-23 08:12~09:54) 데이터에서 다음을 확인한다:

1. **두 플래그가 실제로 발현하는가?** 전체의 5~15% 범위가 합리적. 50%를 넘으면 임계값이 너무 느슨하고, 1% 미만이면 너무 빡빡하다.
2. **임계값이 안정적인가?** 전체 데이터 vs 피크 시간만(예: 08:30~09:30) 분리 산출 비교. 격차가 크면 시간대별 분리 임계값 필요.
3. **노선별 편차 확인.** 3개 노선 중 특정 노선에만 플래그가 몰리면, 그 노선의 배차 자체가 체계적으로 어긋났음을 시사. 별도 섹션으로 리포트에 기록.
4. **false positive 체크.** 심야·새벽 등 배차량 자체가 적은 시간대가 dressage로 오분류되지 않는지 확인. 필요시 `min_departures_per_hour` 필터 추가.

---

## 7. Red Team이 경고한 함정과 방어선

| 공격 | 방어 설계 |
|---|---|
| "산업지구 태그로 dressage 판정은 spatial prejudice" | 공간 태그 불사용. 분포적 후험만으로 산출 |
| "RDI≈0 = 조련이라는 역설적 낙인" | 플래그 메시지를 **서술문이 아닌 의문문**으로 고정. 판정이 아닌 질문 호출 |
| "위원회 위시리스트 = 구현 불가" | 이 장치는 **추가 데이터 없이** RDI 파이프라인 후처리만으로 완성. 구현 파일 1개(~150줄) |
| "비판적 대시보드의 역설" | HTML 리포트 렌더링 단계에서 플래그 메시지를 수치 *옆*이 아닌 *위*에 배치. 수치가 질문의 하위에 위치하는 시각적 위계 강제 |
| "이론의 증발" | 플래그 메시지 본문에 이론가·저작·장절을 각주로 명시(최소 1건/메시지) |

---

## 8. 구현 가이드 (Code 핸드오프용)

**파일 배치**:
- `src/rhythmscape/metrics/critique.py` (신규) — 임계값 산출, 플래그 부여 함수
- `config/critique_flag.yaml` (신규) — 임계값 영속화
- `data/processed/tago/critique_flags_{YYYYMMDD}.parquet` (신규) — 플래그 부여 행 추출

**핵심 함수 시그니처**:
```python
def compute_thresholds(rdi_df: pd.DataFrame) -> dict:
    """전체 분포에서 dressage/vitality 임계값을 산출하여 yaml로 저장."""

def apply_critique_flags(rdi_df: pd.DataFrame, thresholds: dict) -> pd.DataFrame:
    """RDI DataFrame에 critique_flag, flag_message_ko/en, flag_rationale 컬럼 추가."""

def extract_flagged_rows(rdi_df: pd.DataFrame) -> pd.DataFrame:
    """플래그 부여된 행만 추출하여 별도 parquet 저장."""
```

**의존성**: pandas, pyyaml. 기존 스택 내부 자원만 사용.

**랜덤 시드**: 불필요. 분위수 계산은 결정론적.

**체크포인트**: 임계값 산출과 플래그 부여를 분리 단계로 두면, 임계값 재산출 없이 플래그만 재부여 가능. 중단·재개 지원.

---

## 9. 미결 사항 (Day 3~4 작업)

- **플래그 메시지 영문 초안**: Day 4 이중 언어 브리프 집필 시 케이 검수
- **시간대 분리 임계값**: 테스트 조건 §2 결과에 따라 도입 여부 결정
- **`min_departures_per_hour` 필터 값**: 테스트 조건 §4 결과에 따라 설정
- **Opus 에이전트 라우팅 로직**: 이론가 프롬프트 완성(Cowork ③) 후 통합 설계

---

## 10. 참조

1. **Lefebvre, H.** (1992/2004) *Éléments de rythmanalyse*, Ch. 4 "Dressage." Éditions Syllepse / Continuum. — 조련 개념의 원전.
2. **Research Design Committee** (2026-04-23) "Rhythmscape 프로젝트 개관 심의." 의장 권고 §4 "방법론적 방향" — `critique_flag` 설계의 직접 근거.
3. **리듬분석 철학자 위원** (2026-04-23) 개입 권고 §5-(1) "Dressage Index 도입" — 임계값 기반 자동 플래깅 제안의 원안.
4. **Red Team 보고서** (2026-04-23) §II "리듬분석 철학자 치명적 약점 2" — 공간 태그 판정의 이론적 회피 공격. 본 설계에서 분위수 기반 산출로 수용.
5. **Kitchin, R. & Lauriault, T. P.** (2018) "Toward critical data studies," in *Thinking Big Data in Geography*. Univ. of Nebraska Press. — actionable data의 수행성 비판, 플래그 메시지의 의문문 고정 근거.

---

**End of spec. Implementation starts on handoff.**
