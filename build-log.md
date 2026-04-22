# Rhythmscape — Build Log

**시작**: 2026-04-20 (빌드 전 준비 단계)

매일 저녁 30분, 이 파일 하단에 당일 섹션을 추가한다. 다음 날 아침 첫 1시간은 이 파일을 확인하고 조정하는 데 쓴다.

---

## 기록 템플릿

```markdown
## YYYY-MM-DD (요일) — Day N

### 오늘 한 일
- [x] 완료 항목 1
- [x] 완료 항목 2
- [ ] 미완 항목 (사유)

### 변경 파일
- rhythmscape/indicators/ardi.py (신규)
- rhythmscape/cli.py (수정: analyze 명령 추가)

### 막힘
- (블로커 설명 + 임시 우회 + 내일 해결안)

### 내일 첫 과업
1. ...
2. ...

### 토큰 소비
- Sonnet: $XX
- Opus: $XX
- 누적: $XX / $500
```

---

## 2026-04-20 (일) — D-2

### 오늘 한 일
- [x] Cowork 세션 재개, Automobile_Human + Research_tools 폴더 마운트 확인
- [x] 데이터 정찰: datago (TAGO + 창원 시내버스 API 확인), VWorld 작동 확인, KOSIS 30개 테이블 + 승용차 접근성 직격 테이블 확인
- [x] 재사용 자산 스캔: bigkinds_crawler, kosis/vworld/datago-mcp, stage1_analysis 파이프라인
- [x] 산출물 5종 작성:
  - rhythmscape-spec.md (전체 설계)
  - data-scouting-report.md (데이터 정찰 결과)
  - asset-reuse-matrix.md (재사용 매트릭스)
  - sprint-schedule.md (5일 스케줄)
  - prompts/ 이론 프롬프트 3종
- [x] 빌드 로그 시드 작성 (이 파일)

### 변경 파일 (Claude_Hackathon/)
- rhythmscape-spec.md (신규)
- data-scouting-report.md (신규)
- asset-reuse-matrix.md (신규)
- sprint-schedule.md (신규)
- prompts/automotive_rhythm_dominance.md (신규)
- prompts/pedestrian_residue.md (신규)
- prompts/friction_narrative.md (신규)
- build-log.md (신규 — 이 파일)

### 막힘
- 없음. 빌드 진입 준비 완료.
- 단, 선발 결과 미확인 상태. 발표 후 즉시 API 키 발급 + GitHub repo 생성 필요.

### 내일(D-1) 첫 과업
1. 선발 결과 확인 (이메일)
2. SGIS API 키 발급 신청
3. 기존 GitHub repo에 Rhythmscape 스켈레톤 커밋
4. OSM South Korea PBF 다운로드 시작
5. pyproject.toml + uv 환경 구축

### 토큰 소비
- Sonnet: (해커톤 전이므로 별도 계정 — 크레딧 $500은 빌드 시작 이후 집계 시작)

---

## 2026-04-21 (월) — D-1

### 오늘 한 일
- [x] GitHub repo `thelevanter/rhythmscape` 생성 (Public, empty)
- [x] 로컬 clone + 초기 3종 파일 작성·푸시
  - `.gitignore` (Python + macOS + 데이터 폴더 + OSM 바이너리 + Claude Code 캐시 + 데모 영상 원본)
  - `LICENSE` (MIT + 외부 데이터 라이선스 명시: ODbL, 공공누리, TAGO, BIGKinds, NLK, VWorld)
  - `README.md` (빌드 진행 배너, ARDI/PRM 지표 요약, Claude Code 역할, 이론 계보, BibTeX 인용)
- [x] 초기 커밋 해시: `5f0f8b9` — `chore: initial commit - README, MIT license, gitignore` (3 files, 214 insertions)
- [x] 원격 동기화 확인: `[new branch] main -> main` to `https://github.com/thelevanter/rhythmscape.git`

### 변경 파일 (Claude_Hackathon/)
- initial-commit/.gitignore (신규 — 푸시된 버전은 752B)
- initial-commit/LICENSE (신규 — 푸시된 버전은 1795B)
- initial-commit/README.md (신규 — 푸시된 버전은 3112B)

### 막힘
- Google Drive 동기화 지연으로 Cowork에서 작성한 파일이 Mac 로컬에 즉시 나타나지 않음.
  - 우회: heredoc(`cat > file << 'EOF'`)으로 터미널에서 직접 파일 생성. 향후 Cowork → Mac 전달은 heredoc 또는 명시적 대기를 기본값으로 한다.
- zsh `interactive_comments` 미설정으로 `#` 주석이 명령으로 해석됨.
  - 우회: heredoc 블록에는 `#` 주석을 넣지 않음. 필요하면 `setopt interactive_comments` 한 줄 선행.

### 내일(D-Day / 4/22) 첫 과업
1. 선발 결과 확인 (미확인 상태 지속 시에도 빌드는 진행)
2. SGIS API 키 발급 신청 (승인까지 1-2일 소요 가능)
3. OSM South Korea PBF 다운로드 시작 — `data/raw/osm/south-korea-latest.osm.pbf` (Geofabrik, ~800MB, 백그라운드)
4. pyproject.toml + uv 환경 구축 (`uv sync` 작동 확인)
5. `.env.example`, `config.yaml` 초안 커밋
6. 이론 프롬프트 3종(`prompts/`)을 로컬 repo로 이식
7. TAGO 창원 버스 야간 배치 수집 cron 설정 (첫 수집 기록 확보)

### 토큰 소비
- 해커톤 크레딧 $500 집계는 D-Day부터 시작. 오늘까지는 준비 세션.

---

## 2026-04-22 (수) → 2026-04-23 (목) — Day 1

### 오늘 한 일

**Day 1 아침 — 투명성 스택**
- [x] 해커톤 룰링 evidence archive 작성 (`docs/evidence/2026-04-22_rules-clarification.md` — Ado | Claude + Joshua Jerin verbatim 보존)
- [x] 로컬 git 초기화 (main), 첫 커밋 `3492b43` (kickoff 01:00 KST 이후)
- [x] GitHub repo `thelevanter/rhythmscape` 삭제 후 재생성 — pre-kickoff createdAt 제거. 최종 createdAt 2026-04-22 08:39 KST
- [x] force push 1회(케이 승인) + delete+recreate 1회(delete_repo scope). 이후 force push 금지 원칙 재확인

**Day 1 오후 — 인프라 + 워크플로 문서**
- [x] `CLAUDE.md`, `build-log.md`, `docs/sprint-schedule.md` 커밋(`eb9bd30`)

**Day 1 저녁 — TAGO 사양서 + 구현**
- [x] Cowork 세션에서 `docs/tago-batch-spec.md` v1.0 확정 (창원 3노선, 12h 윈도우, 60s 폴링)
- [x] 의존성 설치: httpx / tenacity / structlog / pandas / pyarrow / pyyaml / pydantic / python-dotenv (+ pytest)
- [x] 8개 TAGO 모듈 작성: `client / normalize / stations / routes / arrivals / locations / scheduler / resolve_routes`
- [x] `config/tago.yaml` 작성 (manifest 방식 — 이전 regex pattern에서 개선)
- [x] resolve_routes 검증: cityCode 38010 · 3개 routeid 모두 live TAGO에 존재
- [x] anchor 실행: stations 2752 / routes 3 / route_stations 203 행
- [x] tick 실행: arrivals 10행 / locations 20행 (DoD "rows > 0" 통과)
- [x] launchd plist 2종 생성 (tick 780 엔트리, anchor 06:55 daily), load 완료
- [x] `docs/evidence/tago_first_run_utc.txt` 기록

### 변경 파일
- pyproject.toml (수정: dependencies 추가)
- src/rhythmscape/ingest/__init__.py (신규)
- src/rhythmscape/ingest/tago/{__init__.py, client.py, normalize.py, stations.py, routes.py, arrivals.py, locations.py, scheduler.py, resolve_routes.py} (신규)
- config/tago.yaml (신규)
- config/launchd/com.rhythmscape.tago-batch.{tick,anchor}.plist (신규)
- scripts/gen_launchd_intervals.py (신규)
- docs/evidence/tago_first_run_utc.txt (신규)
- docs/tago-batch-spec.md (수정: §14 DoD 체크박스)

### 핵심 결정과 근거

1. **config/tago.yaml 구조 개선** — 원안의 regex pattern 방식은 TAGO 응답 변동에 취약해서 routeid + theoretical_role 명시 방식으로 전환. resolve_routes는 "해결자"에서 "검증자"로 역할 변경. 케이 결정 (2026-04-23 08:00 KST).

2. **3개 노선 경험적 재해석** — 스펙의 콜로퀴얼 이름("마산합포 순환", "창원 중앙대로", "마산↔창원 광역")이 TAGO 응답 필드와 매칭되지 않음. 창원에 광역버스 타입 부재. 결정:
   - 271 (CWB379002710 · 지선/순환) — 마산합포 박물관 루프
   - BRT6000 (CWB379060000 · 좌석/BRT급행) — 성주사역↔덕동 (창원대로 arterial)
   - 710 (CWB379007100 · 좌석) — 불모산↔마산대 (광역 부재의 증상적 대체)

3. **Sentinel 전략: quarters_dir0** — 원안의 "모든 정류소 polling"은 일일 쿼터 100배 초과. 노선당 mid sentinel 1개 방식은 BRT6000/710의 mid가 턴어라운드 터미널에 걸려 arrivals 0 반환. 최종: 방향 0의 1/4·1/2·3/4 3개 sentinel per route = 9 stations × 720 tick = 6,480/day ✅

4. **Anchor idempotency** — 동일 날짜 재실행 시 stations/routes/route_stations 파일 존재하면 재수집 skip. TAGO 세션 풀 포화 회피.

5. **API 키 로그 redaction** — httpx의 기본 INFO 로그가 serviceKey를 URL에 평문 기록. `logging.Filter` + `httpx` 로거 WARNING 강등 이중 방어. 초기 유출 로그는 `logs/tago/_quarantine/`로 격리.

### 교훈과 발견

- **스펙의 §7.4 트래픽 예산 "~600"은 오타로 판단** — 실제 설계 의도는 §1의 "~2,160/엔드포인트/일". 문서 간 내부 정합성 체크 필요.
- **TAGO route_stations는 양방향 전체 노선을 한 sequence로 반환** — 바이디렉셔널 노선(updowncd 0/1)의 mid는 턴어라운드 지점. 반드시 updowncd 필터링 필요.
- **sentinel 선택은 이론적 선택** — Cowork 재검토 대상으로 기록. "arrivals API의 의미론"(도착 예정이지, 현 위치 아님)에 대한 암묵적 가정이 있음.

### 막힘

- **launchd 첫 fire 검증**: `launchctl list`에 등록됐으나, 이 세션 시점에 아직 fire 결과(`logs/tago/launchd.tick.out`) 미확보. 내일 아침 06:55 anchor + 07:00 첫 tick 확인 필요.

### 내일(Day 2) 첫 과업
1. launchd 실제 fire 확인 — `logs/tago/launchd.tick.{out,err}` + data/raw/tago/arrivals, locations 누적 확인
2. Sentinel 전략 Cowork 재검토 (이론적 위치, 노선별 적정 sentinel 수)
3. sprint-schedule Day 2 체크 → RDI 집계 스크립트 설계 시작
4. OSM PBF 다운로드 완료 확인

### 토큰 소비
- 이 세션: 미집계 (추후 `/cost` 스냅샷 시 기록)
- 누적: $XX / $500

---

*빌드 시작일부터 매일 저녁 이 아래에 섹션 추가.*
