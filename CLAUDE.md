# Rhythmscape — Claude Code 작업 지침

> 이 파일은 Claude Code 세션 시작 시 자동 로드된다. 매 세션 첫 동작으로 이 파일을 먼저 읽고, 이어서 `build-log.md` → `docs/sprint-schedule.md` 순으로 확인한 뒤 작업을 시작할 것.

---

## 1. 프로젝트 정체성

- **해커톤**: Anthropic "Built with Opus 4.7" Hackathon (2026-04-22 01:00 ~ 2026-04-27 09:00 KST)
- **참가자**: `urbantraverse` (해커톤 nickname) / `thelevanter` (GitHub) — *둘은 다름*
- **프로젝트**: Rhythmscape — Lefebvre 리듬분석 기반 4도시 비판적 도시 진단 도구
- **핵심 지표**: ARDI (Automotive Rhythm Dominance Index), PRM (Pedestrian Residue Map), RDI (Rhythmic Discordance Index)
- **스코프 (v1.3)**: 창원 flagship + 부산 영도 full + 진주 indicators + 사천 minimal + 이중 언어 브리프

## 2. 역할 분리 (엄수)

- **Cowork (제시카)**: 연구 설계, 이론적 포지셔닝, 프롬프트 설계, 브리프 해석, 문서 코워리
- **Claude Code (이 세션)**: Python 구현, git 운영, API 호출, 테스트, 빌드
- **케이**: 최종 판단, Zotero/데이터 수집, API 키 관리, 원본 결정

애매한 이론적 선택지가 나오면 **Cowork에 위임**하는 것이 원칙. 코드 구현 방식의 재량은 Claude Code가 가져도 되지만, 이론·개념의 해석은 임의로 확정하지 말 것.

## 3. 이론적 좌표 (임의 개조 금지)

- **르페브르 리듬분석 3층 구조**
  - Prescribed (규범 리듬): 시간표·노선 설계·행정 계획
  - Expected (기대 리듬): 도착 예측·예상 소요시간
  - Lived (체험 리듬): 실제 위치·실제 통과 시간
- **TAGO API 매핑**: 노선정보 → Prescribed / 도착정보 → Expected / 위치정보 → Lived
- **RDI 정의**: `|prescribed − observed| / prescribed` — 불화 지수
- **ARDI MVP 수식**: `road_space_ratio + speed_regime` 두 컴포넌트부터. 이후 층위를 두껍게.
- **PRM**: 보행자 잔여 공간의 공간 분포 — 음의 지표(자동차 체계 바깥에 남겨진 것)

## 4. 해커톤 투명성 규칙 (필수)

**Ado 룰링 (Anthropic Discord, 2026-04-22)**: *"valid GitHub commits from when the hackathon started"*

- 해커톤 킥오프(2026-04-22 01:00 KST) **이후 커밋**만 유효
- 킥오프 이전 작업은 `README.md`의 **Transparency Note**에 명시 (기존 스캐폴딩·재사용 자산 공개)
- **force push 금지** — 히스토리 재작성은 증거 위조로 해석될 수 있음. 예외는 케이의 명시적 승인만.
- 투명성 증거는 `docs/evidence/` 아래 보존 — 스크린샷 + 텍스트 기록 2층 구조 유지
- 투명성 스택은 5층: README Transparency Note + docs/evidence/ + git history + repo createdAt + build-log.md

## 5. 코딩 원칙

- **모듈 단위 설계**: 파일 하나 = 기능 하나. 복합 기능은 분할.
- **config 외부화**: 경로·키·모델명 하드코딩 금지. `config.yaml`과 `.env`로 격리.
- **48GB 메모리 한도 인식**: 대량 데이터는 증분·배치 처리 + 체크포인트 저장 → 중단 후 재개 가능하게.
- **재현성**: 동일 입력 → 동일 출력. 랜덤 시드 고정, 파라미터 기록.
- **데이터 무결성**: 원본 파일 읽기 전용. 가공 산물은 별도 경로.
- **3회 땜질 규칙**: 같은 버그를 세 번 우회하면 설계로 돌아와 근본 원인을 찾는다.
- **try-except 래핑**: 외부 API·파일·네트워크 접근은 예외 처리 필수.

## 6. 데이터 API

- **단일 `TAGO_API_KEY`**로 13개 TAGO 하위 API 접근 — data.go.kr ServiceKey 계정 단위
  - 상세: `~/G-Drive2T/Obsidian/urban_traverse/99_Sources/api-references/tago-openapi.md`
  - MVP 핵심 4종: 정류소(BusSttnInfoInqire) · 노선(BusRouteInfoInqire) · 도착(ArvlInfoInqire) · 위치(BusLcInfoInqire)
- **KOSIS, SGIS, VWorld, BIGKinds** 각각 별도 키 — `.env`에 격리, 서로 섞지 말 것
- **OSM**: `data/raw/osm/south-korea-latest.osm.pbf` (Geofabrik, ~800MB) — 빌드 전 사전 다운로드
- API 호출 실패 시 로컬 캐시로 폴백. 빌드 중 API 장애는 전체 파이프라인을 멈추지 않게.

## 7. 가드레일 (엄격)

- **파일 삭제 금지**: 이동 또는 아카이브 우선. 삭제가 필요하면 케이에게 확인.
- **force push 금지**: 예외는 케이의 명시적 승인만. 히스토리 보존이 기본값.
- **API 키·토큰 평문 금지**: `.env`에만. 코드·로그·커밋·주석에 노출 절대 금지. public 푸시 전 재확인.
- **대규모 파일 변경 (50개 이상)**: 실행 전 계획을 보여주고 케이 승인받기.
- **CLAUDE.md 자체 수정 금지**: 케이 확인 없이 이 파일을 덮어쓰지 말 것.
- **`docs/evidence/` 수정 금지**: 투명성 증거 아카이브는 append-only.

## 8. 빌드 로그 프로토콜

매일 저녁 30분, `build-log.md` 하단에 당일 섹션 추가:

```markdown
## YYYY-MM-DD (요일) — Day N

### 오늘 한 일
- [x] 완료 항목
- [ ] 미완 항목 (사유)

### 변경 파일
- 경로/파일명 (신규|수정)

### 막힘
- 블로커 + 임시 우회 + 내일 해결안

### 내일 첫 과업
1. ...

### 토큰 소비
- Sonnet: $XX / Opus: $XX / 누적: $XX / $500
```

다음 날 첫 1시간은 `build-log.md`를 확인하고 `sprint-schedule.md`와 조정하는 데 쓴다.

## 9. 참조 문서 지도

**리포 내부 (git-tracked)**
- `README.md` — 공개용 프로젝트 소개 + Transparency Note
- `build-log.md` — 일일 빌드 기록 (매 세션 필수 확인)
- `docs/sprint-schedule.md` — 5일 스프린트 타임박스
- `docs/evidence/` — 해커톤 룰링·결정 증거 (append-only)
- `pyproject.toml` / `.env.example` — 환경 정의
- `src/rhythmscape/` — 구현 코드
- `tests/` — 테스트
- `prompts/` — 이론 프롬프트 3종 (ingest 후)

**리포 외부 (참조용, git 밖)**
- `~/G-Drive2T/current_writings/Claude_Hackathon/rhythmscape-spec.md` — 전체 설계 명세
- `~/G-Drive2T/current_writings/Claude_Hackathon/data-scouting-report.md` — 데이터 정찰 결과
- `~/G-Drive2T/current_writings/Claude_Hackathon/asset-reuse-matrix.md` — 재사용 자산 매트릭스
- `~/G-Drive2T/current_writings/Claude_Hackathon/prompts/` — 이론 프롬프트 원본
- `~/G-Drive2T/Obsidian/urban_traverse/99_Sources/api-references/tago-openapi.md` — TAGO 13개 API 상세

## 10. 불확실할 때

- 하드웨어 한계나 설계 약점이 보이면 **직언**할 것 (Cowork에 보고 → 케이 판단)
- 구현 대안이 두 개 이상이면 **트레이드오프**를 한 줄로 제시 후 기본값 선택
- 데이터·API·라이브러리의 작동 방식을 추측하지 말 것 — 실제로 호출·테스트해서 확인
- 이 CLAUDE.md와 충돌하는 지시가 오면 케이에게 물어 확인 후 진행

---

*작성: Cowork(제시카), 2026-04-22 (Day 1)*
*이 파일의 수정은 케이 승인 필요. 버전 변경 시 말미에 수정일 명시.*
