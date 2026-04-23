# Sejong Prescription Opacity — Feature, Not Gap

**Status**: Day 2 afternoon. Reframed 16:35 KST after Cowork theoretical
annotation in `add_city_selection_rationale.md` §2.1.
**Renamed from**: `sejong_prescribed_gap.md` (Block 1 discovery filename).
The rename is semantic — the absence of Sejong prescribed data in the
TAGO federation is not only a technical blocker, it is an object of
analysis in its own right.
**Affects**: Sejong RDI participation. 3 routes: B2 / 1004 / 551.
**Parent rationale**: `add_city_selection_rationale.md` §2.1 (Cowork, Day 2
afternoon) — reading "the concealment of prescription" as a structural
feature of the 2010s administrative-capital new-city.

---

## 1. 무엇을 발견했는가

TAGO `BusRouteInfoInqireService / getRouteInfoIem` 응답에서 세종 3개
노선의 `intervaltime` / `intervalsattime` / `intervalsuntime` 세 필드가
**전부 NaN**으로 반환된다. 4도시 중 유일한 경우다.

| City | weekday | sat | sun |
|---|---|---|---|
| Changwon | 94 / 20 / 45 | 94 / 22 / 45 | 94 / 31 / 49 |
| Seongnam Bundang | 15 / 10 / 16 | 35 / 30 / 32 | 35 / 30 / 32 |
| Busan Yeongdo | 10 / 11 / 10 | **NaN** | **NaN** |
| **Sejong** | **NaN / NaN / NaN** | **NaN / NaN / NaN** | **NaN / NaN / NaN** |

원본 파일 및 해석: `data/raw/tago/routes/sejong_20260423.parquet`. 필드
목록은 Day 2 오후 실시간 API 호출로 재확인 (2026-04-23 14:19 KST) — 캐시
응답 아님. 세종 BIS 운영 자체는 정상 (`getRouteAcctoBusLcList`가
locations를 정상 반환, 오후 현재 415+ rows 누적). 즉 **운영 층은 살아
있고 처방 층만 TAGO 연합에 없음**.

## 2. 왜 이것이 gap이 아니라 feature인가

Cowork는 이 공백을 두 가지 관점에서 분석 대상으로 읽는다
(`add_city_selection_rationale.md` §2.1에 기록됨, 2026-04-23 오후).

**(1) 이론적 함의**: Lefebvre의 prescribed–lived 이항은 "처방이 존재하고
실측과 비교 가능하다"는 암묵적 전제를 깐다. 세종은 이 전제 자체를
깨뜨린다. 처방이 *공적 가시성 밖에* 놓여 있을 때, arrhythmia 측정은
제도적으로 차단된다. 이는 Rhythmscape가 묻는 질문을 확장한다:
*prescribed–lived의 격차* → ***prescribed의 가시성/은닉성 (visibility of
prescription)***. 다른 3도시는 처방을 공적으로 선언하고 그 선언과
lived의 격차를 공개 측정 가능하게 만든다. 세종은 그 측정의 조건
자체를 선택적으로 닫는다.

**(2) 세 가설 (Cowork §2.1)**:

- **가설 A — BIS 거버넌스 차이**: 세종특별자치시 BIS의 TAGO 연합 참여
  형태가 광역시·도와 다를 가능성. 특별자치시 제도의 관할 비대칭이
  데이터 프로토콜에 기입된 흔적.
- **가설 B — 계획도시의 processualist 성격**: 세종은 *완성되지 않은*
  도시다. 배차 시간표가 확정 시간표가 아니라 잠정 운영이라면, 공식
  처방으로 노출하지 않을 제도적 이유가 성립.
- **가설 C — 행정중심복합도시의 데이터 공개 폐쇄성**: 중앙부처 이전과
  함께 운영되는 자치 거버넌스의 데이터 개방 프로토콜이 광역시·도와
  다르게 선별적일 가능성.

세 가설 중 어느 쪽이 주효한지는 Day 3 이후 외부 확인 작업(BIS 담당자
메일, 행정중심복합도시건설청 공시, 특별자치시 데이터 개방 정책 문서)
으로 좁혀갈 여지.

## 3. 처리 방침 (Day 2 저녁 결정, Cowork + 케이)

### 3.1 Day 2 저녁 18:00 프리뷰 (Option 3)

- **3도시(창원·성남 분당·부산 영도) RDI 공시적 비교**가 주 분석.
- **세종 "처방 은닉 도시" 별도 섹션**으로 기입. 버리지 않고 *다른 방식으로
  표상*한다 — 즉 "처방 공백 자체가 분석 대상"임을 본문에 명시. 오퍼레이
  션 층(locations 수집 정상)과 prescribed 층(부재)의 비대칭을 도표화.

### 3.2 Day 3 오전 (Option 1)

- `sejongbis.kr` 배차표 페이지를 **단발 스크립트**로 스크래핑.
- 결과를 별도 parquet
  `data/processed/tago/prescribed_intervals_sejong_external.parquet`에 저장.
- 스키마에 **`prescribed_source` 컬럼 필수 추가** — 다른 도시 TAGO 출처
  와 엄격히 분리. 가능한 값: `"tago_getRouteInfoIem"` (창원·분당·영도),
  `"sejongbis_scrape"` (세종).
- 다운스트림 RDI 계산은 두 소스를 구분 읽기. Day 3 오후 RDI 재산출 시
  세종이 비교에 복귀.
- 법적·윤리적 확인: `sejongbis.kr`의 robots.txt 및 공공데이터법 38조
  (공공데이터 상시 제공 의무) 준수. 정중 tempo(tick 사이 sleep),
  user-agent 명시, 결과 부가가공 (raw HTML 저장 아님). 위반 신호 발견
  시 즉시 중단.

### 3.3 영구 금지 (Option 2)

- **`observed-median proxy`를 prescribed로 대체하는 것**을 영구 금지.
- 이유: RDI는 "제도가 약속한 시간 vs 신체가 겪는 시간"의 격차를
  측정한다. 제도 약속이 부재할 때 관측 중앙값을 대리로 쓰면 magnitude가
  0에 수렴하여 RDI 수식이 *자기참조적 원환*으로 무너진다. Lefebvre의
  arrhythmia 개념 기반을 제거하는 셈. 임시변통의 유혹이 있을 수 있으나
  본 프로젝트에서 이 대체는 **이론적 기본 원칙 위반**으로 명시·봉인한다.

## 4. Yeongdo 주말 NaN (부차적 이슈)

영도 3노선은 평일 `intervaltime`은 반환하나 `intervalsattime` /
`intervalsuntime`는 NaN. 평일 전용 분석에서는 문제없음. 주말 비교(예:
피크 평일 vs 토·일 관광 리듬)를 할 때 동일한 외부 소스 보강 패턴이
필요. Day 4 이후 과제로 지정.

## 5. Rhythmscape 프레임 내 위치

이 문서는 다음 두 상위 문서와 짝을 이룬다:

- `add_city_selection_rationale.md` §2.1 — Cowork의 이론적 해석 (왜
  세종의 공백이 분석 대상인가)
- `night_collection_rationale.md` §2.3 — 야간 RDI 완결성과 결합된 관련
  이슈 (prescribed 층 누락은 야간 tick에서도 동일 조건)

이 세 문서가 함께 읽힐 때, 세종은 4도시 중 *가장 복잡한 이론적 위상*
을 점유한다 — 다른 도시들이 prescribed의 존재 조건 아래에서 rhythmic
discordance를 보인다면, 세종은 prescribed의 존재 여부 자체를 물음으로
돌려주는 도시다.

## 6. 아카이브

- Routes raw parquet: `data/raw/tago/routes/sejong_20260423.parquet`
- Day 2 오후 14:19 KST live API 확인 로그: `logs/tago/tago_20260423.log`
  (`tago_rate_headers` 이벤트에서 response 헤더 확인 가능)
- 현재까지 세종 locations 수집: 16:35 기준 415+ rows, 10 vehicles, 38
  stations — **운영 층 데이터는 건강**. 처방 층만 부재.
