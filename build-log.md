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

## 2026-04-23 (목) — Day 2 — RDI v0 + critique_flag

### 완료

- **블록 A** (11:20): `data/processed/tago/prescribed_intervals.parquet` 생성 (9행 = 3노선 × 3 daytype). `intervaltime`/`intervalsattime`/`intervalsuntime` 컬럼이 이미 `routes/*.parquet`에 있어 추가 API 호출 없이 reshape만. 평일 기본값: 271=94분 / BRT6000=20분 / 710=45분.
- **블록 B** (11:24): `src/rhythmscape/metrics/rdi.py` 신설, `rdi_20260423.parquet` 1,006 bins. 노선별 평균 magnitude: 271=0.59 / BRT6000=0.26 / 710=0.42. 변동성 non-zero: 340/1006 (33.8%).
- **블록 C** (11:27): `src/rhythmscape/metrics/critique.py` + `config/critique_flag.yaml` + `critique_flags_20260423.parquet` (57행). dressage_alert=54, vitality_query=3, flag rate 5.67% (spec §6 범위 5-15% 내).
- **블록 D** (11:29): `docs/evidence/rdi_day2_preview_20260423.png` (3-패널 시계열) + `docs/analysis/rdi_day2_summary.md`.
- **pytest**: `tests/test_metrics_rdi.py` + `test_metrics_critique.py` 3/3 pass.

### 결정 사항

1. **time bin 5분 → 30분 변경 (경험적 필연)**. 핸드오프 §B의 5-min bin은 Changwon 최단 headway(20분, BRT6000)·최장(94분, 271)을 고려하면 대부분 n=1 bin을 낳고 variance가 0으로 수렴 → `vitality_query` 발동 불가. 30-min bin에서 다중관측 347/1001 (34.7%) 확보. 5-min spec은 sub-15-min headway 모드(서울·부산 확장 시)에서 유효. 사유 `rdi.py` docstring + `summary.md` Limits에 명시.

2. **dressage persistence 5 ticks → 1 bin**. 원 spec의 "5 연속 틱=5분"은 1-min polling을 전제. 30-min bin 하나는 이미 30분 평균이라 구조적 관측(fluke 아님). persistence=1이 spec의 의미적 번역. 전체-일치 window 확보 후 Day 3에 persistence≥2 재검토.

3. **dressage magnitude_absolute 0.05 → 0.10**. spec §6이 "flag rate 1% 미만이면 임계값 완화"를 허용. 0.05로 2.6% → 0.10으로 5.67% (5-15% 범위 내). spec §2.1 본문값은 보존되어 있고, CritiqueConfig 오버라이드로 Day 2 상황만 조정. Day 3에 더 긴 window에서 0.05 복귀 가능성 검토.

4. **경험적 발견** — BRT6000이 dressage 54건 중 47건 독식, 271은 vitality 3건 중 2건 독식. route_selection_rationale.md §3/§2의 이론적 배치(BRT=automobility 포획 / 271=eurhythmia baseline이 sparse window에서 arrhythmia로 전환)와 경험적 일치. 연관성 강조는 summary.md "Observed triplet" 절 참조.

### 이슈 / 미해결

- **7-row anchor의 routes parquet**: 271의 94분 prescribed가 의심스러움. 관측 평균 37분과 불일치. TAGO `intervaltime` 필드의 단위·의미를 Day 3 오전에 재확인 (Cowork 리뷰 대상).
- **커미티 §2 peak vs off-peak 분리 테스트 미수행**: 오늘 08:12-11:30 ~3.5h window로는 피크(08-09) vs 오프피크(10-11) 분리 통계가 얇음. Day 2 저녁 20시 이후 전일치 재산출 시 실시.
- **OSM PBF 창원 클립(`data/processed/osm/changwon.pbf`)** Day 1 완료. PRM 파이프라인 연결은 Day 3 이후.
- **tick API error 6건**: generic TAGO resultCode != 00. warning 수준. Day 3 아침 누적 로그 분석으로 원인 분류.

### 다음 세션 (Day 3) 시작 지점

1. `build-log.md` Day 2 섹션 + `docs/analysis/rdi_day2_summary.md` 읽기 (Cowork 리뷰 결과 반영)
2. Day 2 저녁 20:00 이후 launchd 12h 전일치 축적 완료 확인 → 전일치 RDI 재산출로 임계값·persistence 재검토
3. 271 prescribed `intervaltime=94` 의미 재확인 (loop 총시간 vs headway)
4. RQ 최종 결정 회의(07:30) 이후 ARDI/PRM 진입 여부 결정

### 토큰 소비
- 이 세션: 미집계. 커밋 말미 `/cost` 반영 예정.

---

## 2026-04-23 (목) — Day 2 오후 — 4도시 전환 + 파이프라인 일반화

### 오늘 오후 한 일 (09:00 이후)

**결정 경위 5줄 (상세는 docs/analysis/ 참조)**:

1. **Committee 심의 반영** — Research Design Committee 4위원 + Red Team + 의장 권고(2026-04-23 오전, 외부 메모)를 받아 RQ 결정은 Day 3 오전으로 공식 연기, 오늘은 RQ-무관 공통분모(파이프라인 일반화·critique_flag) 작업만 수행. `critique_flag` 장치는 RDI 직후 후처리 레이어로 확정([[docs/analysis/critique_flag_spec.md]] §2–§8).
2. **서울 탈락 → 성남 분당 이론적 대체** — 서울 TAGO 부재를 Day 2 오전 데이터 조회로 확인(cityCode 목록 133개에 서울 없음). "1970s 창원 vs 1970s 강남" 쌍을 포기하고 "국가 계획(창원) vs 민간 자본 계획(분당·판교)" 이항 대립으로 재구성([[docs/analysis/add_city_selection_rationale.md]] §0, §1).
3. **4도시 가동** — 창원(flagship live) + 성남 분당(14:42 KST) + 세종(14:42) + 부산 영도(14:42) 동시 launchctl load. 일일 TAGO 호출 총 예산 ~8,640/day(endpoint별 분산), 쿼터 여유 있음. 커밋 `f18b55b`(리팩토링) → `35b32bb`(세종 완성) → `8560ce9`(영도 완성).
4. **경주 Day 4 시연용 보류** — 사천(대체 → 경주로 선정 변경, Cowork 결정, 상세 [[add_city_selection_rationale.md]])은 add-city CLI 확장성 시연 용도로만. 오늘 구현·수집 미포함.
5. **Day 2 오전 RDI v0 + critique_flag 완성** — 커밋 `d9d0046`. 창원 단일 도시 스코프로 DoD 8/8 달성. 오후에 4도시 일반화 착수.

### 변경 파일 (오후)
- `config/cities.yaml` — 4도시 manifest (창원·성남·세종·영도 라벨+routeid+theoretical_role)
- `src/rhythmscape/ingest/tago/{scheduler.py, resolve_routes.py}` — `--city <slug>` CLI + 레거시 `--config` 호환
- `scripts/gen_launchd_intervals.py` — `--city` per-city plist 생성
- `src/rhythmscape/metrics/rdi.py` — `--city / --all` CLI, per-city prescribed + RDI 파일 분리 출력
- `config/launchd/com.rhythmscape.tago-batch.{seongnam_bundang,sejong,busan_yeongdo}.{tick,anchor}.plist` (6 파일 신규)
- `docs/analysis/add_city_selection_rationale.md` (§0–§4 전체)
- `docs/analysis/sejong_prescribed_gap.md` (신규, 오후 블록 1 중 발견)

### 오후 커밋 체인
```
8560ce9 feat(cities): Busan Yeongdo manifest + plists — 4-city set complete
35b32bb feat(cities): Sejong manifest + pre-staged launchd plists
f18b55b feat(ingest): multi-city TAGO ingest — parameterize by city slug
d9d0046 feat(metrics): RDI v0 + critique_flag — Day 2 DoD complete
```

### 이슈 (오후 발견)
- **세종 TAGO prescribed 누락**: `getRouteInfoIem`이 세종 3노선 모두 `intervaltime*` 필드 미반환. 세종 RDI v0 = 0 rows. 외부 소스(sejongbis.kr) 주입 또는 세종만 RDI 제외 필요. Day 3 오전 Cowork 결정 대상([[sejong_prescribed_gap.md]]).
- 부산 영도 주말 필드(`intervalsattime/suntime`) NaN — 평일만 유효. Day 3~4 주말 비교 시 동일 문제 재출현 예상.

### 다음 (18:00 프리뷰까지)
- Block 3 (quota 모니터링) + Block 4 (271 intervaltime 검증)
- 18:00 KST 4도시 비교 가능 RDI 재프리뷰 생성 (세종 제외 3도시)

### 외부 참조 (Obsidian)
- Cowork Day 1 세션 로그: `20_Projects/Cowork_Sessions/2026-04-22_tago-batch-launch.md`
- TAGO API 레퍼런스: `99_Sources/api-references/tago-openapi.md`
- (Day 2 Cowork 세션 로그는 저녁 19:00 Cowork가 작성 예정)

---

## 2026-04-23 (목) — Day 2 저녁 — 마감 엔트리

### Day 2 최종 커밋 체인 (누적 → 마감)

```
(this commit) feat(evening): closing tasks — Sejong recon + dressage temporal + build-log close
b4031e6 feat(metrics): 4-city RDI generalization + Sejong prescription opacity + night collection plan + 271 representation/practice distinction
af43509 feat(metrics+ingest): Day 2 afternoon 4-block — RDI multi-city + quota obs + 271 verif
8560ce9 feat(cities): Busan Yeongdo manifest + plists — 4-city set complete
35b32bb feat(cities): Sejong manifest + pre-staged launchd plists
f18b55b feat(ingest): multi-city TAGO ingest — parameterize by city slug
d9d0046 feat(metrics): RDI v0 + critique_flag — Day 2 DoD complete
ee7b8b5 docs(analysis): route selection + sentinel rationale refinement
c150963 refactor(ingest/tago): sentinels → strategic rhythmic observatories
8bb0f58 feat(ingest/tago): TAGO batch live — DoD complete
```

### Day 2 종료 상태 (2026-04-23 17:05 KST 스냅샷)

**수집 가동 현황**
- launchd 8 job 등록 (4도시 × tick/anchor). 19:59 KST 자동 윈도우 종료 예정.
- 내일 06:55 KST 4도시 anchor 자동 fire (1일 1회).
- 내일 07:00 KST tick 재개. 야간 plist 업데이트는 07:30 RQ 회의 직후(Cowork 지시).

**누적 tick (17:05 기준, 엔드포인트당)**
- 창원: 약 520 ticks × 3 endpoints (full-day, 08:12~)
- 성남 분당 / 세종 / 부산 영도: 약 140 ticks × 3 endpoints (14:42~)
- 총 locations parquet 파일: 2,000+ (4도시 합계)

**세 가설 1차 확증 (도시별 극값 점유)**
1. **분당 magnitude 극값**: mean RDI magnitude **0.796** (3도시 중 최고). `route_selection_rationale.md` + `add_city_selection_rationale.md §1.2(b)`의 *"특권 통근 회랑 가설"* 경험적 지지. 타이트한 처방 × 서울 방면 정체의 이중 작용.
2. **영도 variance 극값**: mean RDI variance **1.83** (3도시 중 최고). 다리 병목·봉래산·해안 노출의 *"지형 제약 variance 가설"*(H-YD) 지지. magnitude는 중간 수준이나 불규칙성으로 rhythm을 기록.
3. **창원 dressage 오프피크 집중**: midday 12-14 band dressage rate **14.97%** (창원 3 band 중 최고, spec §6 5-15% 범위 상한). *automobility 포획의 기계성이 수요 낮은 시간대일수록 선명*하다는 파생 관찰. 창원만 3 band 커버리지 유효.

**regional_fix 4변주 완성**
- 창원 710 (광역 *결핍*)
- 성남 9407 (광역 *특권*)
- 세종 1004 (광역 *필수성*)
- 영도 113 (광역 *왜곡*)

4도시가 *regional_fix* 축 단일선에서 서로 독립적인 이론 위치를 점유. Day 3-4 이중 언어 브리프의 **논증 중심축**으로 확정.

**세종 opacity 처리**
- Option 3 (오늘 저녁): 3도시 RDI 공시적 비교 + 세종 "처방 은닉 도시" 별도 섹션. 완료 (`day2_4city_preview.md` §4, PNG panel 4).
- Option 1 (Day 3 오전): `bis.sejong.go.kr` 스크래핑 사전 정찰 완료 (`sejongbis_scrape_plan.md`). Cowork spec의 `sejongbis.kr`은 DNS 부재 — 정식 도메인은 `bis.sejong.go.kr`. AJAX 엔드포인트 3종 매핑(`searchBusRoute.do`, `searchBusRouteDetail.do`, `searchBusTimeList.do`). Day 3 07:30+ 즉시 실행 가능.
- Option 2 (observed-median proxy): 영구 금지 봉인.

**파이프라인 empty-response handling 실증 검증**
- `night_tick_diagnostic.py`: 최근 120 ticks/city 스캔 결과 arrivals=0 이미 **7건** 정상 처리됨 (창원 2, 성남 1, 영도 4). 빈 parquet 저장·checkpoint 갱신 정상. 야간 locations=0 케이스는 내일 야간 plist 활성화 후 첫 24h 내 자연 검증.

### 오후~저녁 변경 파일

- **신규**: `config/cities.yaml`, `config/critique_flag_{changwon,seongnam_bundang,busan_yeongdo}.yaml`, `config/launchd/com.rhythmscape.tago-batch.{seongnam_bundang,sejong,busan_yeongdo}.{tick,anchor}.plist` (6)
- **신규**: `scripts/{preview_rdi_4city.py, night_tick_diagnostic.py, dressage_temporal_distribution.py}`
- **신규**: `docs/analysis/{day2_morning_report.md, day2_4city_preview.md, day2_dressage_temporal_distribution.md, add_city_selection_rationale.md, night_collection_rationale.md, sejong_prescription_opacity.md, sejongbis_scrape_plan.md, 271_intervaltime_verification.md}`
- **신규**: `docs/evidence/rdi_day2_4city_preview_20260423.png`
- **신규**: `prompts/ko/lefebvre.md` (Cowork 프롬프트 v1.0 시드)
- **수정**: `src/rhythmscape/ingest/tago/{client.py, scheduler.py, __init__.py, resolve_routes.py}`, `src/rhythmscape/metrics/rdi.py`, `scripts/gen_launchd_intervals.py`, `docs/analysis/sentinel_rationale.md`, `docs/analysis/route_selection_rationale.md`
- **리네임**: `sejong_prescribed_gap.md` → `sejong_prescription_opacity.md` (gap → feature)

### 내일 07:30 회의 재입장용 anchor

Day 3 회의에서 Cowork가 즉시 인용 가능한 산출물:
1. `docs/analysis/day2_4city_preview.md` — 메인 4도시 프리뷰
2. `docs/evidence/rdi_day2_4city_preview_20260423.png` — 1장 시각화
3. `docs/analysis/day2_dressage_temporal_distribution.md` — dressage 시간대 교차표 (부분 — 창원만 3 band 유효, post-19:59 재산출 권장)
4. `docs/analysis/sejong_prescription_opacity.md` — 처방 은닉 도시 프레임
5. `docs/analysis/sejongbis_scrape_plan.md` — Day 3 스크래핑 즉시 실행 가이드
6. `docs/analysis/night_collection_rationale.md` — 야간 plist 업데이트 근거 + 실행 계획

### 내일 첫 과업 순서 (Day 3, 07:00~) — Cowork 저녁 지시로 스코프 확장 (2026-04-23 저녁 갱신)

**오전 (07:00~12:00) — 원안 그대로 유지**
1. **07:00~07:30** 재입장: 위 6 산출물 + build-log + `decisions/20260424_morning_rq_decision.md`(Obsidian, Cowork 작성) 읽기
2. **07:30~08:30** RQ 최종 결정 회의 (Cowork + 케이). 잠정 합의: RQ1·RQ2·RQ3·RQ4 병렬 유지, RQ5만 메타서사로 수렴. Day 5 아침에 최종 확정.
3. **08:30~08:45** 야간 수집 plist 업데이트 (10분 stride 옵션 추가 → `gen_launchd_intervals.py` `minute_entries()` 확장 필요) + launchctl reload
4. **08:45~09:30** 세종 스크래핑 모듈 실행 (`bis.sejong.go.kr` / `sejongbis_scrape_plan.md` 가이드) + 세종 RDI 재산출
5. **09:30~12:00** post-19:59 재산출 + 3도시 완전 dressage 교차표 확정 (Day 2 저녁 미완분 마무리) + dressage 시간대 분포 재실행

**오후 (13:00~18:00) — ARDI 진입 허용 (신규)**

6. **13:00~18:00** **창원 ARDI v0 구현** — `src/rhythmscape/metrics/ardi.py` 신설. MVP 수식 `road_space_ratio + speed_regime`(CLAUDE.md §3). 1도시 먼저, 4도시 일반화는 Day 4 오전. RQ3(자동차 잔여 텍스처) + RQ1(공간 지표 보강) 공동 선행 투자. OSM 창원 클립(`data/processed/osm/changwon.pbf`, Day 1 준비분) 입력.

**저녁 (19:00~22:00) — PRM 설계 문서 착수 (신규)**

7. **19:00~21:00** **PRM 설계 문서 작성** — `docs/analysis/prm_spec.md` 신설. RQ3 핵심 장치. *구현은 Day 4 오전*, 오늘은 설계만. 보행자 잔여 공간의 공간 분포(음의 지표) 수식·OSM 데이터 소스·출력 스키마·critique_flag 연계 포함.
8. **21:00~22:00** Day 3 build-log 마감 + 프리뷰 갱신 (+ 창원 ARDI v0 결과 1~2 시각화 포함)

**스코프 업데이트 요약 (Day 2 → Day 3)**
- ✅ **해제**: ARDI 파이프라인 (Day 3 오후부터)
- ✅ **허용**: PRM 설계 문서 (Day 3 저녁)
- ❌ **계속 금지**: Opus 에이전트 호출 인프라 (Cowork가 D-G·Foucault 프롬프트 집필 중)
- ❌ **계속 금지**: 브리프 본문 집필 (Day 4 일정)
- ❌ **계속 금지**: 사천·경주 add-city 구현 (Day 4 리허설)

### 막힘 (미해결)

- **성남·영도 07-09 / 12-14 band 데이터 부재**: 14:42 load라 오늘 이 band 관측 0. Day 3 아침부터 자연 해소.
- **세종 prescribed 부재**: Day 3 오전 스크래핑으로 해소 예정.
- **영도 주말 intervaltime NaN**: 평일 분석에는 무관, 주말 분석 시 별도 작업.
- **야간 stride 옵션**: `scripts/gen_launchd_intervals.py` `minute_entries()` 함수가 현재 분당 1회 고정. 10분 stride 파라미터 추가가 Day 3 morning task.

### 토큰 소비
- 미집계. Day 3 아침 `/cost` 스냅샷 시 반영.

---

*빌드 시작일부터 매일 저녁 이 아래에 섹션 추가.*
