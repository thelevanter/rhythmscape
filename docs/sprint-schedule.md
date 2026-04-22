# Rhythmscape — 5일 스프린트 스케줄 (v1.3 개정, 2026-04-21)

**해커톤 기간**: 2026-04-22(수) 01:00 ~ 2026-04-27(월) 09:00 KST
**총 빌드 윈도우**: 5일 + 8시간 ≈ 128시간
**실질 투입**: 하루 10~12시간 × 5 = 50~60시간
**케이 + Claude Code 페어 작업**: Cowork(제시카)는 설계·검토, Claude Code는 실구현
**스코프 (v1.3)**: 4개 도시 (창원 full / 부산 영도구 full / 진주 indicators / 사천 minimal) + 이중 언어 브리프

---

## 0. 원칙

- **수직 슬라이스 우선**: 첫날부터 CLI → 데이터 1개 → 지표 1개 → HTML 렌더까지 연결된 최소 파이프라인을 만든다. 이후 각 층위를 두껍게 한다.
- **매일 저녁 돌이킴**: 당일 진척을 `build-log.md`에 기록하고 다음 날 첫 1시간을 조정에 쓴다.
- **3회 땜질 규칙**: 같은 버그를 세 번 땜질하면 설계로 되돌아온다(CLAUDE.md 지침).
- **데이터는 일요일 밤 사전 수집**: TAGO·OSM은 빌드 시작 전 확보해 빌드 중 API 장애 리스크를 차단.
- **데모 영상은 4일차부터**: 5일차에 몰아넣지 않는다.

---

## 1. D-1 (4/21 화) — 선발 발표 & 사전 준비

**컨디션**: 하루 여유. 오전은 일상 업무, 저녁부터 준비.

| 시간 | 과업 | 산출 |
|------|------|------|
| 오전 | 선발 발표 확인 | 메일 수신 |
| 13:00 | API 키 발급 (SGIS, data.go.kr 활용승인) | 키 확보 |
| 14:00 | 기존 GitHub repo 활용 — Rhythmscape용 브랜치 생성 + 초기 커밋 (비어 있는 구조) | `rhythmscape/` 스켈레톤 커밋 |
| 15:00 | OSM PBF 다운로드 시작 (백그라운드) | `data/raw/osm/south-korea-latest.osm.pbf` |
| 16:00 | pyproject.toml + uv 환경 구축 | `uv sync` 작동 |
| 17:00 | `.env.example`, `config.yaml` 초안 | 리포지터리 스켈레톤 |
| 19:00 | 이론 프롬프트 3종 초안 작성 | `prompts/critical_indicators/*.md` |
| 22:00 | TAGO 창원 버스 야간 배치 수집 시작 (cron) | 새벽 완료 예정 |
| 23:00 | 수면 | — |

---

## 2. Day 1 (4/22 수) — 파이프라인 뼈대 + 첫 지표 슬라이스

**테마**: 끝부터 끝까지 연결된 최소 파이프라인.

### 오전 (09:00-13:00)
- CLI 진입점 구축 (`cli.py` with Typer)
- `config.py` pydantic 스키마
- `ingest/osm.py` — pyrosm으로 창원 bbox 도로+보행 네트워크 로드
- `harmonize/crs.py` — EPSG:5186 통일

### 점심 후 (14:00-18:00)
- `ingest/tago.py` — 지난 밤 캐시된 정류소·노선 parquet 로드
- `ingest/kosis.py` — DT_444001_011_A 호출 + 캐시
- 격자 생성 (마산합포구 bbox × 500m)
- 각 ingest의 단위 테스트 (smoke)

### 저녁 (19:00-23:00)
- `indicators/ardi.py` — **MVP 수식만 먼저** (road_space_ratio + speed_regime 2개 컴포넌트)
- 결과 parquet 출력 확인
- folium으로 ARDI 히트맵 렌더링 → `outputs/day1_preview.html` 확인

**Day 1 DoD**: CLI 한 줄 실행으로 ARDI 히트맵이 HTML로 뜬다. 완벽하지 않아도 연결되어 있다.

---

## 3. Day 2 (4/23 목) — PRM + 담론 층위 + 이론 프롬프트

### 오전 (09:00-13:00)
- `indicators/prm.py` — 보행 네트워크 연결도 + SGIS 인구 × inverse ARDI
- SGIS API 호출 (키 발급 완료 가정)
- 결과 parquet + 예비 지도

### 점심 후 (14:00-18:00)
- `ingest/bigkinds.py` — 서브프로세스로 bigkinds_crawler 호출
- 경남신문·경남도민일보 키워드 수집 (4개 키워드, 5년치)
- 백그라운드 수집 진행 중 다음 작업

- `ingest/vworld.py` — 행정구역 폴리곤 확보
- 마산합포구 폴리곤을 격자 필터링에 적용

### 저녁 (19:00-23:00)
- `interpret/claude_client.py` — Claude API 호출 래퍼 + 프롬프트 캐싱
- 이론 프롬프트 3종 최종화
  1. `automotive_rhythm_dominance.md` — ARDI 값 해석
  2. `pedestrian_residue.md` — PRM 값 해석
  3. `friction_narrative.md` — zone 단위 500자 브리프

**Day 2 DoD**: PRM 히트맵 + 담론 데이터 1차 수집 + Claude 호출 1회 성공(샘플 브리프 생성).

---

## 4. Day 3 (4/24 금) — Friction Zone + 역사 레이어 + 중간 리뷰

### 오전 (09:00-13:00)
- `indicators/friction.py` — ARDI 상위 20% ∩ PRM 하위 20% 공간 클러스터링
- scipy.ndimage 또는 sklearn 사용
- Zone 3~5개 자동 식별 → GeoJSON 출력

### 점심 후 (14:00-18:00)
- 역사 레이어 인덱스 구축
  - 1920년대 357건 중 마산·창원 지명 언급 기사 필터링
  - 1960년대 馬山日報 72건 내 현재 friction zone 인근 지명 매칭
- `render/html_template.py` 역사 탭 추가

### 저녁 (19:00-22:00)
- **중간 리뷰** — pipeline-review-board 스킬 또는 Cowork 자체 검토
  - 빌드 진척 vs 스코프 재평가
  - 블로커 식별
  - 스코프 축소 필요 판단
- **v1.3 핵심 과업 — add-city 템플릿 구축**
  - `rhythmscape/cli_add_city.py` — 템플릿 복제 + config 생성 + 데이터 엔드포인트 매핑
  - `cities/_template.yaml` — 도시별 가변 필드 골격
  - 창원 config를 템플릿 소스로 검증

### 밤 (22:00-23:00)
- 스코프 조정 결정 (필요시)
- 부산 영도구 bbox + TAGO 엔드포인트 사전 수집 cron 설정 (Day 4 아침에 데이터 준비되도록)

**Day 3 DoD**: Friction zone이 창원 지도 위에 표시되고, 각 zone에 한국어 브리프가 붙는다. 역사 탭 초안 동작. **`rhythmscape add-city --from-template changwon` 명령이 설계 수준으로 완성**됨.

---

## 5. Day 4 (4/25 토) — **스케일업 데이**: 부산 영도구 + 진주 + 사천 + 리포트 렌더러 완성

### 오전 (09:00-13:00) — 부산 영도구 full 분석
- `rhythmscape add-city --name busan-yeongdo --from-template changwon` 실행
- 영도구 OSM 서브셋·TAGO·KOSIS 자동 매핑 검증
- 반도 지형 특유의 가중치 조정 (`terrain_adjustments` 섹션)
- `rhythmscape analyze --city busan-yeongdo --mode full --lang ko,en` 완주
- **실패 시 즉시 폴백**: Day 4 12시까지 영도가 안 돌면 창원 확장(마산회원구 추가)으로 전환

### 점심 후 (14:00-16:00) — 진주 indicators-only
- `rhythmscape add-city --name jinju --from-template changwon`
- 진주 원도심 bbox 설정
- `rhythmscape analyze --city jinju --mode indicators-only` 완주
- brief 생성 건너뛰고 ARDI + PRM 히트맵까지만

### 16:00-17:30 — 사천 minimal
- `rhythmscape add-city --name sacheon --from-template changwon`
- `rhythmscape analyze --city sacheon --mode minimal --indicators ardi` 완주
- ARDI 히트맵 단독 생성

### 17:30-19:00 — 리포트 렌더러 완성
- `render/folium_report.py` 최종 (시간 슬라이더, 레이어 토글, zone 팝업)
- `render/html_template.py` 한·영 토글 구현
- `render/bilingual_template.py` 신규 — 한·영 병기 리포트

### 저녁 (19:00-23:00) — 이중 언어 브리프 배치 생성
- `rhythmscape batch --cities changwon,busan-yeongdo --lang ko,en --use-batch-api`
  - Anthropic Batch API로 야간 처리 (50% 할인)
  - 창원 friction zone 5~7개 × 2언어 + 부산 3~5개 × 2언어 = 16~24건
  - 완료까지 최대 24시간이므로 Day 5 오전에 결과 확인
- 동시에 창원·부산 HTML 리포트 수동 생성(브리프 플레이스홀더로 우선 구조 확정)
- 데모 노트북 `notebooks/demo.ipynb` 작성
- 재현성 체크리스트 작성

**Day 4 DoD**:
- [ ] 4개 도시 모두 실행 성공 (모드는 각각 full/full/indicators-only/minimal)
- [ ] Batch API로 이중 언어 브리프 생성 제출 완료 (결과는 Day 5 오전)
- [ ] HTML 리포트 구조 완성 (브리프는 Day 5에 최종 삽입)

---

## 6. Day 5 (4/26 일) — 이중 언어 완성 + 통합 대시보드 + 데모 영상 + 제출

### 오전 (09:00-11:00) — Batch API 결과 수거 및 삽입
- Day 4 밤에 제출한 이중 언어 브리프 배치 결과 수거
- `rhythmscape check-parity` 실행 — 한·영 논지 일치성 자동 검증
- 창원·부산 HTML 리포트에 최종 브리프 삽입

### 11:00-13:00 — 4개 도시 통합 대시보드
- `index.html` 생성: 4개 도시 ARDI 분포 비교 + 도시 유형별 프로파일 카드
- `comparative/scale_narrative.md` 이중 언어 생성 (도시 유형학 서술 2페이지)

### 점심 후 (14:00-16:00) — README 이중 언어 + 리포지터리 공개
- `README.md` (영어) + `README.ko.md` (한국어) 완성
- GitHub 최종 정리, Public 전환 확인
- code-safety-audit 스킬로 안전 검증 실행
- citation-auditor 스킬로 영어 브리프 인용 감사

### 16:00-19:00 — 데모 영상 최종 녹화 (3분)
- 스크립트는 spec §10.1 v1.3 개정판 기반
- **핵심 장면**: `rhythmscape add-city --name busan-yeongdo --from-template changwon` 실시간 실행 (30초)
- **마무리 장면**: 4개 도시 통합 대시보드 ARDI 비교 (20초)
- 자막 한·영 병기
- YouTube 비공개 업로드 + 링크 확보

### 저녁 (19:00-22:00) — 해커톤 제출
- 제출 페이지 작성 (한·영 병기 설명)
  - 프로젝트 설명 (spec §1 + §4 요약)
  - "4개 도시 × 이중 언어" 차별화 강조
  - 데모 영상 링크
  - GitHub 링크
- 22:00-23:00 최종 확인 후 제출 (마감 4/27 09:00 KST, 약 10시간 여유)

### 밤 (23:00-) — 예비 시간
- 마지막 버그 대응 또는 휴식

**Day 5 DoD**: 제출 완료. 모든 산출물(한·영 이중) 공개 가능 상태. 4개 도시 통합 대시보드 접근 가능.

---

## 7. 일일 리츄얼

### 매일 아침 (30분)
- 전날 build-log.md 확인
- 오늘 과업 3개 확정 (이상 설정 금지)
- 막힌 지점 Cowork에 공유

### 매일 저녁 (30분)
- `build-log.md`에 진척 기록
- 변경 파일 목록
- 막힘 리스트
- 다음 날 첫 과업

### 2시간마다
- 커밋. 메시지 규칙: `[day2] indicators: PRM 1차 구현`
- 주요 실패 시 이전 커밋으로 복귀 가능

---

## 8. 리스크 관리

### 8.1 지연 시 폴백 (우선순위 순)

1. **데모 영상이 안 나옴** → 3분을 2분으로 단축, 정적 캡처로 대체
2. **역사 레이어 지연** → 완전히 제거(1920/1960은 MVP 외부로)
3. **PRM 수식 버그** → 단순 보행 네트워크 밀도로 단순화
4. **Friction zone 클러스터링 버그** → 임계값 단순 마스크로 대체
5. **kepler.gl 실패** → folium만 유지
6. **BIGKinds 수집 지연** → 담론 레이어 제거(ARDI/PRM만으로 스토리)

### 8.2 도시 변경

창원 GTFS/TAGO가 완전 실패할 경우 → 부산 또는 서울. 그러나 로컬 정당성 상실 = 서사 약화. 도시 변경은 **최후 수단**.

### 8.3 심사 압박

만약 심사 기준이 "기술의 혁신성"에 과도하게 쏠려 있다고 판단되면, 이론적 서사를 약화하고 "Theory-to-indicator translation via Claude Code"를 *자동화된 인간 판단*으로 재포지셔닝.

---

## 9. 토큰·예산 관리 (v1.3 개정 — Max 플랜 + API 크레딧 이중 구조)

### 9.1 결제 수단 분리

| 용도 | 결제 수단 | 비용 규모 |
|------|----------|----------|
| Claude Code 에이전트 세션 (코드 생성·iter·디버깅) | **Claude Max 플랜** ✅ | 플랜 한도 내 |
| 실험·재시도·리팩토링 | Claude Max 플랜 ✅ | 플랜 한도 내 |
| ARDI/PRM 브리프 파이프라인 (anthropic SDK 직접 호출) | $500 API 크레딧 | ~$12 |
| HTML 내러티브 (창원·부산 이중 언어) | $500 API 크레딧 | ~$4 |
| 스케일 비교 서술 (comparative/scale_narrative.md) | $500 API 크레딧 | ~$2 |
| check-parity 검증 (한·영 일치성 자동 검증) | $500 API 크레딧 | ~$3 |
| **$500 실제 소진 예상** | | **~$25** |
| **$475 백업 연료** (Max 한도 초과 시 API로 우회) | | 대기 중 |

### 9.2 Max 플랜 한도 관리

- **Claude Code 기본은 Sonnet 4.6** — Opus는 수동 승급만
- Opus가 필요한 이론적 번역·복잡한 리팩토링은 하루 2~3시간으로 제한
- Max 5시간 롤링 윈도우 한도 임박 시 → API 크레딧으로 우회 가능(백업 연료)

### 9.3 Batch API 필수 활용

비대화형 작업은 **전량 Batch API**로. 50% 할인.
- 친쿠영역 이중 언어 브리프 (Day 4 밤 → Day 5 오전 수거)
- 스케일 비교 서술 생성
- check-parity 검증 배치

### 9.4 Prompt Caching

이론 프롬프트 3종은 system prompt에 `cache_control: {type: ephemeral}` 설정. 반복 호출 비용 90% 절감.

### 9.5 Usage Alert

Anthropic Console에 **$100 알림** 설정. $500 크레딧 예상 소진이 $25인데 $100 도달했다면 설계상 문제가 있다는 신호.

---

## 10. Cowork(제시카)와 Claude Code 역할 분배

### Cowork (제시카) — 이 세션
- 설계 문서 유지보수
- 이론 프롬프트 리뷰
- 중간 리뷰 및 방향 조정
- 케이와의 전략 대화
- 데모 영상 스크립트 검토

### Claude Code — VS Code 터미널
- 실제 코딩 (파일 생성·수정)
- 테스트 실행
- 디버깅
- 커밋 메시지 작성
- 라이브러리 설치 및 환경 설정

**역할이 섞이면 안 된다**. Cowork는 VS Code 파일을 직접 쓰지 않는다(세션 격리). Claude Code는 이 해커톤 폴더의 전략 문서를 수정하지 않는다.

---

## 11. 케이가 유일하게 해야 할 일

1. 선발 발표 확인 및 케이 계정 활성화 (4/21)
2. SGIS API 키 발급 (4/21 오전)
3. 매일 저녁 30분 build-log 확인
4. 심사 제출 버튼 클릭 (4/26 밤)

나머지는 모두 Cowork + Claude Code가 수행한다.

---

## 12. 우승이 아니어도 얻는 것 (v1.3 확장)

이 스프린트가 끝난 시점에 케이가 가질 것:

- **오픈소스 패키지 Rhythmscape** (지속 가능, 4개 도시 실증)
- **비판지리학 × AI 엔지니어링의 드문 교차점 포지셔닝**
- **4개 도시 재현 가능 분석 인프라**: 창원(플래그십) + 부산 영도구 + 진주 + 사천 — "도시 유형학" 실증
- **1920~2026년을 관통하는 자동차 리듬 데이터셋** (창원 중심, 담론 레이어 포함)
- **영어 학술 초고 즉시 투입 가능**: 이중 언어 브리프가 *Environment and Planning D*, *Mobilities* 급 저널 투고 초안으로 전환 가능
- **후속 논문 최소 3편 분량의 실증 엔진**:
  1. 방법론 논문 — ARDI/PRM 지표 정의 및 검증 (《한국지리학회지》 또는 *Urban Geography*)
  2. 사례 논문 — 창원/부산/진주/사천 도시 유형학 (*International Journal of Urban Sciences*)
  3. 이론 논문 — Lefebvrean rhythmanalysis의 한국 중규모 도시 적용 (*Environment and Planning D*)
- **Claude Code를 학술 엔진으로 사용한 공개 사례** — 이 자체가 독립 논문 거리

우승은 보너스다. 이 스프린트 자체가 케이의 학술 궤도를 한 단계 끌어올린다.

---

*매일 저녁 이 문서를 참조하고, 실제 진척과의 차이를 조정하라. 계획은 지도이지 족쇄가 아니다.*
