# Claude Code 핸드오프 — TAGO 창원 배치 구현

> **이 문서를 가장 먼저 읽는 Claude Code 세션을 위한 작업 지시서.**
> **사양 확정일**: 2026-04-22 Day 1 저녁 (제시카 + 케이 합의)
> **목표 마감**: 2026-04-22 ~22:00 KST (오늘 밤 첫 가동)

---

## 0. 지금 무엇이 벌어지고 있나

Rhythmscape 해커톤 Day 1 저녁. 이미 결정된 것:
- 리포 셸 완성 (`pyproject.toml`, `CLAUDE.md`, `README.md`, 디렉터리 골조)
- TAGO API 키 발급 완료, `.env` 삽입 완료
- 수집 범위·윈도우·폴링 주기 확정 (피크 확장 12h, 60초)
- **사양서 완성** → `docs/tago-batch-spec.md` v1.0

이제 **네가 할 일**은 이 사양서를 따라 실제 코드와 설정을 만들고, 오늘 밤 22시 이전에 launchd까지 등록해 Lived 시계열 수집을 가동하는 것이다.

---

## 1. 반드시 먼저 읽을 것 (이 순서)

1. `docs/tago-batch-spec.md` — 이번 작업의 완전한 설계 사양 (**주 문서**)
2. `CLAUDE.md` (이 리포 루트) — 프로젝트 공통 지침, 특히 §5 코딩 원칙 + §7 가드레일
3. `~/G-Drive2T/Obsidian/urban_traverse/99_Sources/api-references/tago-openapi.md` — TAGO 13개 API 레퍼런스 (§3 리듬 3층 매핑, §4.1~§4.4 MVP 4종, §6 에러코드)
4. `~/G-Drive2T/current_writings/Claude_Hackathon/rhythmscape-spec.md` — §9.2 (수집 예산), §3.4 (RDI 수식 — 네가 생성할 parquet가 여기 먹인다)

읽기 전 구현 시작 금지.

---

## 2. 작업 순서 (spec §12 축약본)

구체 명령은 사양서 §12 참조. 여기는 단계만:

1. **의존성 설치**: httpx, tenacity, structlog, pandas, pyarrow, pyyaml, pydantic
2. **모듈 6개 작성**: `src/rhythmscape/ingest/tago/` 하에 client, normalize, stations, routes, arrivals, locations, scheduler, resolve_routes (8개 파일, spec §4)
3. **config/tago.yaml 작성** (spec §5)
4. **resolve_routes.py 1회 실행** → routeid 3개 확정 → config에 주입
5. **`--mode anchor` 수동 실행**으로 stations/routes parquet 생성 확인
6. **`--mode tick` 수동 실행**으로 arrivals/locations parquet 생성 확인
7. **launchd plist 작성 + 분 단위 엔트리 생성 스크립트**
8. **launchctl load로 등록**
9. **첫 가동 타임스탬프 커밋** (증빙용)

---

## 3. 이번 세션 DoD (spec §14)

모두 충족해야 세션 종료:

- [ ] 6개 모듈 import 성공
- [ ] resolved route_id 3개 config에 주입
- [ ] anchor 수동 실행 성공
- [ ] tick 수동 실행 성공 (행 수 > 0)
- [ ] launchd 두 job 등록 (`launchctl list | grep rhythmscape` 확인)
- [ ] `docs/evidence/tago_first_run_utc.txt` 커밋
- [ ] `.env` 커밋 제외 검증 (`git status --ignored`)
- [ ] API 키 grep 검사 공백

---

## 4. 반드시 지킬 것 (사양서 범위 외 일반 원칙)

### 4.1 API 키 노출 금지
- `TAGO_API_KEY`는 **오직 `.env`에서만** 로드
- 코드·로그·테스트·주석 어디에도 평문 노출 불가
- 커밋 전 `git grep "TAGO_API_KEY="`로 평문 누출 검사 (설정 파일의 `api_key_env: TAGO_API_KEY` 같은 참조는 OK)

### 4.2 원본 불변
- `data/raw/tago/` 파일은 **생성 후 절대 수정/삭제 금지**
- 가공은 `data/processed/` 별도 경로
- 재수집 필요 시 `_v2`, `_v3` 접미사로 병행 보존

### 4.3 추측 금지
- routeid를 사전에 가정하지 말 것 — **반드시 `getRouteNoList`로 전수 덤프 후 이름 매칭**
- 필드 대소문자를 가정하지 말 것 — 반드시 `normalize_keys()` 통과 후 접근
- 창원 cityCode를 `38010`로 사양서에 써뒀지만 `resolve_routes` 단계에서 검증 (틀리면 응답 빈 배열 → 즉시 raise)

### 4.4 체크포인트와 재진입
- `data/checkpoints/tago/state.json`을 매 tick 후 갱신
- 재기동 시 이 파일을 먼저 읽어 쿼터/중복 방어

### 4.5 에러 처리
- 네트워크 에러: tenacity 3회 재시도 후 다음 tick 넘김
- TAGO 코드 22·30: 즉시 배치 중단 + 로그 알림 (spec §9.1)
- 응답 파싱 실패: 원본 바이트를 `logs/tago/raw_dump_*.bin`에 보존하고 다음 tick 계속

### 4.6 땜질 3회 금지
- 같은 실패를 3번 이상 반복 땜질하면 설계 재검토 단계 진입. 제시카(Cowork 세션)에 돌아와 상의.

---

## 5. 가동 후 해야 할 것

1. **build-log.md에 Day 1 섹션 추가**:
   - 아침: 투명성 스택 정비
   - 오후: 인프라(Tailscale, Screen Sharing)
   - 저녁: TAGO 사양서 확정
   - 밤: 배치 구현 + 첫 가동 (이 세션)

2. **Obsidian에 세션 로그 기록**:
   - 경로: `20_Projects/Cowork_Sessions/2026-04-22_tago-batch-launch.md`
   - 코드 세션 결과와 첫 가동 검증 결과 요약

3. **제시카에게 복귀 보고**:
   - 첫 가동 타임스탬프
   - DoD 8개 항목 체크 결과
   - 발견된 이슈 (응답 필드 특이사항, 에러코드 실제 관측 등)

---

## 6. 트러블슈팅 포인트 (사전 안내)

| 증상 | 의심 원인 | 확인 |
|------|----------|------|
| 코드 30 (미등록 키) | API 키 URL 이중 인코딩 | 디코딩된 원본 키를 `.env`에 저장했는지 |
| 응답 빈 배열 | cityCode 오류, routeid 오류 | resolve_routes 로그에서 후보 확인 |
| 대소문자 KeyError | normalize 누락 | 응답 직후 `_normalize_keys()` 적용 여부 |
| tick 60초 초과 | 타임아웃 과다, 재시도 과다 | `http_timeout_sec: 10`, 재시도 3회 유지 |
| launchd 미작동 | plist 권한/경로 오류 | `launchctl list \| grep rhythmscape`, `log show --predicate 'subsystem == "com.apple.xpc.launchd"'` |
| `gpslati` 이상 | 맵매칭 좌표 (노선 이탈 시 관찰 불가) | 정상. spec §2 주석 참조 |

---

## 7. 이 세션 끝내는 방법

DoD 8개 항목을 `docs/tago-batch-spec.md` §14 체크박스에 실제로 `[x]` 표시하여 커밋하고, 커밋 메시지에 "TAGO batch live — DoD complete"를 남긴다. 그 다음 제시카에게 한 줄로 보고:

> "TAGO 배치 가동 확인. 첫 가동 UTC: <타임스탬프>. DoD 8/8. Day 2 아침까지 Lived 샘플 누적 예정."

---

**문서 작성**: 제시카 (Cowork) · **구현 주체**: Claude Code · **판단자**: 케이
