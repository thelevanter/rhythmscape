# 야간 수집 활성화 근거 — Night Collection Rationale

**Status**: Day 2 오후 결정. Day 3 07:30 RQ 회의 직후 plist 반영.
**Decided by**: 케이 + 제시카 (2026-04-23 오후).
**Affects**: 4도시 launchd tick 윈도우. 창원 · 성남 분당 · 세종 · 부산 영도.
**Binds**: `config/launchd/com.rhythmscape.tago-batch.{city}.tick.plist`의 StartCalendarInterval.

---

## 1. 결정

현재 tick 윈도우(07:00~19:59 KST, 분당 1회)에 **야간 저빈도 tick(20:00~06:59, 10분당 1회)**를 추가한다. 4도시 모두 동일 적용.

---

## 2. 왜 이 결정이 필요한가 — 이론적 근거

Day 1~2 초기 설계는 **피크 확장 12시간 윈도우**로 가동됐다. API 한도 보수적 관리와 주간 관측 완결성이라는 실용적 이유였다. 그러나 Research Design Committee 심의 + Day 2 오후 이론적 재검토 결과, **야간 수집의 부재는 프로젝트의 이론적 허리를 무너뜨리는 공백**으로 판정되었다.

### 2.1 Lefebvre의 *dressage*는 야간에 극단이 드러난다

리듬분석 철학자 위원의 지적: *Éléments de rythmanalyse* Ch. 4에서 Lefebvre는 조련(dressage)을 *prescribed rhythm이 lived rhythm으로 내면화되는 과정* — 즉 "간격이 0으로 수렴하는 과정 자체가 권력 작동의 완성태"로 정의한다. 이 내면화의 극단은 **야간·새벽**에 드러난다. 구체적으로:

- **창원 심야 산업단지 교대조 셔틀**: 2교대·3교대 체계의 교대 시각이 00:00·04:00·08:00에 고정되어 있고, 이를 맞추는 버스의 처방·실측 일치도가 가장 완벽해지는 구간이 **22:30~05:30** 사이다. 이것이 dressage의 경험적 극단점이며 RDI ≈ 0의 가장 진한 표본이 된다.
- **분당 서울 방면 광역 막차**: 9407·M버스의 22:00~24:30 막차 구간은 *특권적 통근 회랑*이 "오늘의 노동을 끝낸다"는 순간을 수행한다. lived의 불규칙성이 막차 구간에서 유독 가시화된다.
- **세종 대전 유성 연계 심야**: 행정중심도시 통근자의 귀가 막차 패턴은 *신도시가 완결되지 않았음*을 드러내는 리듬적 증거다.

야간 수집을 생략하면 이 세 층의 데이터가 모두 부재한다. Research Design Committee 리듬분석 철학자의 "빠진 층 — bio-rhythm, cosmological rhythm, dressage" 지적의 실질 내용이 바로 여기다.

### 2.2 Urry의 *system of automobility*는 24시간 체계다

모빌리티 비판 사회학자 위원이 짚은 지점: automobility는 단지 자동차 교통량이 아니라 *체계*다(Urry 2004). 대중교통이 대부분 멈추는 **00:00~05:00 사이**에 자동차 체계는 오히려 고유한 리듬을 드러낸다 — 배달 노동, 택시 야간 운행, 물류 차량, 심야 귀가. 이 시간대에 *대중교통 lived rhythm이 거의 0*이라는 사실 자체가 **automobility의 지배성**을 정량화한다. "버스가 0대 지나가는 시공간"의 좌표는 자동차 체계의 양성적 측정치다.

### 2.3 RDI 분석의 완결성

RDI는 *처방된 리듬과 살아 있는 리듬의 격차*를 시간 함수로 측정한다. 12시간 창은 하루의 절반에 대한 격차만 관찰하며, 본질적으로 *부분 분석*이다. 주·야의 대비가 가장 중요한 구조적 변수가 될 수 있는 상황에서 야간을 원천적으로 제거하면, 낮의 magnitude·variance 패턴을 해석할 기준선이 사라진다.

---

## 3. 실행 계획

### 3.1 plist 업데이트 시점

**Day 3 07:30 KST 직후** (RQ 최종 결정 회의 종료 후). 07:30~08:00 사이에 Code가 4도시 plist 업데이트 + launchctl reload. 07:30은 야간 시간대를 막 지난 시점이므로 충돌 없음.

### 3.2 새 스케줄 (수집 창)

```
주간: 07:00 ~ 19:59 KST, 분당 1회
야간: 20:00 ~ 06:59 KST, 10분당 1회
```

### 3.3 예산 영향

- 주간 유지: 분당 × 780분 × 4도시 × 3 endpoints ≈ 기존대로 ~7,200 호출/일
- 야간 추가: 10분당 × 660분 × 4도시 × 3 endpoints ≈ ~864 호출/일
- **총 ~8,064/10,000 (80%)** — 한도 20% 마진 확보

per-endpoint quota 구조는 Day 2 오후 Code가 Block 3에서 rate-limit 헤더 모니터링 활성화. Day 3 아침 데이터로 endpoint별 분산 확인.

### 3.4 사전 실험

**Day 2 저녁 19:30~19:45 KST 사이**에 실험 tick 1회 실행:
- TAGO가 차량 0대 상황을 어떻게 응답하는지 확인
- `locations=0, arrivals=0` 응답을 체크포인트·로그가 정상 처리하는지
- 문제 발견 시 Day 3 오전 수정 후 본반영

---

## 4. 데이터 해석 원칙 (분석 단계 주의사항)

야간 수집 개시 후 RDI·ARDI·PRM 분석에서 다음 원칙을 견지한다:

- **"차량 0대"는 결측이 아니라 데이터다.** 심야 배차 간격이 공식적으로 없는 시공간에서 관측 0대는 *prescribed == undefined, lived == silent*의 이중 조건이다. RDI 계산에서 이 구간은 단순 NaN이 아니라 *eurhythmic silence* (동기화된 침묵)으로 별도 범주화.
- **dressage_alert 임계값 재검토**. 야간 데이터 포함 후 전체 분포의 분위수가 변동한다. Day 4 오전 `critique_flag.yaml` 임계값 재산출 필수.
- **시간대 분리 분석**. 07-09 출근 피크, 12-14 비피크, 17-19 퇴근 피크, 22-24 막차, 00-05 심야 다섯 구간으로 분할하여 기술 통계를 도시별로 비교. 이 분할은 Edensor(2010)의 *urban rhythm segmentation* 선행 연구와 정합한다.

---

## 5. 해커톤 이후 확장

이 결정은 해커톤 범위의 제한적 야간 수집이다. 학술 연구 단계에서는 다음 확장이 가능하다:

- **주말·공휴일 야간 리듬** — 심야 영업·유흥·관광 리듬의 극단
- **명절 주기 리듬** — 설·추석의 이동 패턴이 도시별 automobility 체계를 어떻게 교란하는가
- **KTDB 5분 단위 도로 교통량 교차** — Day 2 커미티 모빌리티 사회학자 위원의 핵심 권고, 야간 자동차 리듬 측정

---

## 6. 참조

1. **Lefebvre, H.** (1992/2004) *Éléments de rythmanalyse*, Ch. 4 "Dressage" — 야간 조련의 극단점
2. **Urry, J.** (2004) "The 'System' of Automobility," *Theory, Culture & Society* 21(4–5) — 24시간 자동차 체계
3. **Edensor, T.** (2010) "Thinking about Rhythm and Space," in *Geographies of Rhythm* — 도시 리듬의 시간대별 분할
4. **Research Design Committee** (2026-04-23) 리듬분석 철학자 위원 §3 "빠진 층" — bio-rhythm, cosmological, dressage
5. Rhythmscape `docs/analysis/day2_morning_report.md` — Day 2 오전 RDI v0 결과, 야간 수집 부재가 해석에 남긴 한계

---

**End of rationale. Day 3 07:30 RQ 회의 종료 후 Code가 plist 업데이트 실행.**
