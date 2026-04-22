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

*빌드 시작일부터 매일 저녁 이 아래에 섹션 추가.*
