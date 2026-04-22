# TAGO 창원 버스 야간 배치 수집 — 사양서

> **Status**: 설계 확정. 구현 대기 (Claude Code).
> **작성**: 2026-04-22 (Day 1 저녁) / **버전**: v1.0
> **연계**: `rhythmscape-spec.md` v1.4 §9.2 / `99_Sources/api-references/tago-openapi.md`

---

## 0. 사양서의 목적

이 문서는 TAGO(국토교통부 교통빅데이터센터) 공개 API를 주기적으로 호출하여 창원시 3개 버스 노선의 **Prescribed(계획) / Expected(안내) / Lived(실측)** 시계열을 parquet로 수집·보존하는 배치 파이프라인의 설계를 규정한다. Claude Code는 이 문서를 유일한 구현 참조로 삼는다.

Lefebvre 리듬분석의 3층 구분(eurhythmia / polyrhythmia / arrhythmia)을 공공 버스 시스템의 **계획-안내-실측** 삼중 기록으로 조작화하는 것이 파이프라인의 이론적 전제다. Rhythmic Discordance Index(RDI)의 실시간 두께는 이 배치의 지속적 가동에 비례한다.

---

## 1. 확정 파라미터

| 항목 | 값 | 근거 |
|------|-----|------|
| 대상 도시 | 창원 (flagship) | `rhythmscape-spec.md` §2 |
| 대상 노선 수 | 3 (마산합포 순환 / 창원 중앙대로 / 마산↔창원 광역) | 스펙 §9.2 |
| 노선 ID 확정 방식 | 첫 실행 시 `getRouteNoList` 전량 덤프 후 이름 매칭 | CLAUDE.md "추측 금지" |
| 수집 윈도우 | 07:00–19:00 (Asia/Seoul, 연속 12h) | 핸드오프 Q2 확정 |
| 폴링 주기 | 60초 | 스펙 §9.2 |
| 일 호출 예산 | ~2,160 호출/일/엔드포인트 | 12h × 60분 × 3노선 |
| TAGO 한도 대비 | 22% (10,000/일/엔드포인트) | 안전 구간 |
| 첫 가동 시점 | 2026-04-22T22:00:00+09:00 | 핸드오프 Q3 |
| TAGO_API_KEY 상태 | 발급 완료, `.env` 삽입 완료 | 핸드오프 Q1 |
| 저장 포맷 | Apache Parquet (snappy) | 증분 append, 빠른 읽기 |
| 공간 좌표계 | TAGO는 WGS84 (EPSG:4326) | 원본 보존 |

---

## 2. API 매핑 (리듬 3층 × TAGO 엔드포인트)

| 층위 | 목적 | 서비스 | 엔드포인트 | 빈도 |
|------|------|--------|-----------|------|
| 앵커 | 정류소 메타(좌표) | BusSttnInfoInqireService | `getSttnNoList` | 일 1회 |
| (보조) | 노선 인덱스 | BusRouteInfoInqireService | `getRouteNoList` | 일 1회 |
| **Prescribed** | 배차간격·첫차·막차 | BusRouteInfoInqireService | `getRouteInfoIem` ★ | 일 1회 |
| **Expected** | 도착 예측 스냅샷 | ArvlInfoInqireService | `getSttnAcctoArvlPrearngeInfoList` | 60초 |
| **Lived** | 차량 실시간 위치 | BusLcInfoInqireService | `getRouteAcctoBusLcList` ★ | 60초 |

**주의**: TAGO 응답 JSON은 서비스별로 필드 대소문자 규칙이 혼재한다(시내버스 계열 소문자 vs 기타 카멜케이스). 파서는 응답 수신 직후 `_normalize_keys()`를 통해 모든 키를 소문자로 변환한다.

**추가 주의**: Lived 층의 `gpslati`·`gpslong`은 **맵매칭 후 좌표**다. 노선 이탈 관찰은 불가하며, 본 파이프라인의 RDI는 "시간 리듬의 불일치"에 한정된다(공간 이탈 리듬은 별도 과제).

---

## 3. 디렉터리 구조

```
rhythmscape/
├── src/rhythmscape/
│   ├── __init__.py
│   └── ingest/
│       ├── __init__.py
│       └── tago/
│           ├── __init__.py
│           ├── client.py         # HTTP 클라이언트 + 공통 에러 분기
│           ├── normalize.py      # 키 소문자 정규화, 타입 캐스팅
│           ├── stations.py       # 정류소 전수 덤프 (일 1회)
│           ├── routes.py         # 노선 메타 + Prescribed 시간표 (일 1회)
│           ├── arrivals.py       # Expected 60초 스냅샷
│           ├── locations.py      # Lived 60초 스냅샷
│           ├── scheduler.py      # 오케스트레이션 (launchd 진입점)
│           └── resolve_routes.py # 이름→routeid 매칭 (첫 실행용)
├── config/
│   ├── tago.yaml                 # 수집 설정 (아래 §5)
│   └── launchd/
│       └── com.rhythmscape.tago-batch.plist
├── data/
│   ├── raw/tago/                 # 원본 (읽기 전용)
│   │   ├── stations/
│   │   ├── routes/
│   │   ├── arrivals/
│   │   └── locations/
│   ├── processed/tago/           # 가공 (RDI 등 야간 후처리)
│   └── checkpoints/tago/         # 재개용 상태 파일
├── logs/tago/                    # structlog JSON 로그 (일별)
└── docs/
    ├── tago-batch-spec.md        # 이 파일
    └── evidence/
        └── tago_first_run_*.txt  # 첫 가동 타임스탬프 증빙
```

---

## 4. 모듈 명세

### 4.1 `client.py` — HTTP 클라이언트

**책임**: TAGO API 호출의 유일한 진입점. 재시도·에러 분기·레이트 제한·로깅을 캡슐화.

**의존**: `httpx`, `tenacity`, `structlog`, `pydantic`

```python
from typing import Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TagoAPIError(Exception):
    """TAGO 응답 자체가 에러를 반환한 경우 (resultCode != 00)"""
    def __init__(self, code: str, msg: str, endpoint: str):
        self.code = code
        self.msg = msg
        self.endpoint = endpoint
        super().__init__(f"[{endpoint}] {code}: {msg}")

class TagoQuotaExceeded(TagoAPIError):
    """코드 22 — 일일 호출 한도 초과"""

class TagoKeyUnregistered(TagoAPIError):
    """코드 30 — 등록되지 않은 서비스 키"""


class TagoClient:
    """TAGO 공개 API의 세션 단위 클라이언트.

    사용:
        client = TagoClient(api_key=os.environ["TAGO_API_KEY"])
        result = client.call("BusSttnInfoInqireService", "getSttnNoList", {"cityCode": 38010})
    """

    BASE = "https://apis.data.go.kr/1613000"
    DEFAULT_TIMEOUT = 10.0

    def __init__(self, api_key: str, timeout: float = DEFAULT_TIMEOUT):
        self.api_key = api_key
        self._http = httpx.Client(timeout=timeout)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPError)),
        reraise=True,
    )
    def call(self, service: str, operation: str, params: dict[str, Any]) -> dict:
        """단일 API 호출. 재시도는 네트워크 레벨만. TAGO 코드 에러는 즉시 raise."""
        ...

    def close(self) -> None:
        self._http.close()
```

**에러 분기 (call 내부)**:

```
httpx TimeoutException     → 재시도 (tenacity, 최대 3회)
httpx HTTPError (5xx)      → 재시도
httpx HTTPError (4xx)      → 즉시 실패 (raise, 기록)
응답 parsing 실패          → raise ValueError, 원본 바이트 logs/에 덤프
resultCode "22"            → raise TagoQuotaExceeded → 배치 중단
resultCode "30"            → raise TagoKeyUnregistered → 배치 중단 + 알림
resultCode "00"            → 정상 반환
기타 resultCode            → raise TagoAPIError
```

**레이트 제한**: TAGO는 공식 rate limit을 명시하지 않으나, 60초에 3노선 × 2엔드포인트 = 6회 호출로 여유. `asyncio` 없이 순차 호출로 충분.

---

### 4.2 `normalize.py` — 응답 정규화

**책임**: 대소문자 혼재 해소, 타입 강제 변환.

```python
def normalize_keys(obj: Any) -> Any:
    """dict의 모든 키를 소문자로 변환. list는 재귀. 기타는 그대로.

    TAGO는 서비스별로 키 케이스가 다르다 (nodeid vs gpsLati vs arrtime).
    수집 직후 이 함수를 한 번 통과시키면 이후 모든 파싱이 소문자 기준으로 단일화된다.
    """
    ...

def coerce_numeric(row: dict, fields: list[str]) -> dict:
    """지정 필드를 float/int로 강제 변환. 실패 시 None으로 저장 (유실 허용)."""
    ...
```

**반드시 정규화할 필드**:
- 좌표: `gpslati`, `gpslong` → float
- 도착 예측 초: `arrtime` → int
- 남은 정류소 수: `arrprevstationcnt` → int
- 정류소 순번: `nodeord` → int
- 차량번호: `vehicleno` → str (앞자리 0 보존)

---

### 4.3 `stations.py` — 정류소 전수 덤프 (일 1회)

**책임**: 창원시 전 정류소의 (nodeid, nodenm, gpslati, gpslong)을 parquet로 저장.

```python
def fetch_changwon_stations(client: TagoClient, city_code: int) -> pd.DataFrame:
    """페이지네이션을 돌며 전수 수집. DataFrame 반환.

    컬럼: nodeid, nodenm, gpslati, gpslong, citycode, collected_at_utc
    """
    ...

def save_stations(df: pd.DataFrame, out_dir: Path, run_date: date) -> Path:
    """data/raw/tago/stations/changwon_YYYYMMDD.parquet 로 저장.
    동일 파일 존재 시 덮어쓰지 않고 suffix _v2, _v3 로 보존.
    """
    ...
```

**실행 주기**: 매일 1회 (launchd에서 06:55에 트리거). 06:55인 이유는 07:00 배치 진입 전 앵커 자료 갱신 보장.

---

### 4.4 `routes.py` — 노선 메타 + Prescribed 시간표 (일 1회)

**책임**: 3노선의 `getRouteInfoIem` 호출로 **평일/토/일 × 배차간격·첫차·막차**를 parquet로 저장.

```python
def fetch_route_info(client: TagoClient, city_code: int, route_id: str) -> dict:
    """단일 노선의 Prescribed 층 메타 1건 반환.

    반환 필드 (정규화 후):
        routeid, routeno, routetp,
        startvehicletime, endvehicletime,
        intervaltime (평일),
        intervalsattime (토),
        intervalsuntime (일),
        startnodenm, endnodenm
    """
    ...

def save_routes(rows: list[dict], out_dir: Path, run_date: date) -> Path:
    """data/raw/tago/routes/changwon_YYYYMMDD.parquet"""
    ...
```

**실행 주기**: 매일 1회 (stations 직후, 06:56).

---

### 4.5 `arrivals.py` — Expected 60초 스냅샷

**책임**: 3노선 대상, 60초마다 모든 정류소의 도착 예측을 수집.

```python
def snapshot_arrivals(
    client: TagoClient,
    city_code: int,
    route_ids: list[str],
    station_ids: list[str],  # 해당 노선이 경유하는 정류소 집합
) -> pd.DataFrame:
    """Expected 층 1회 스냅샷.

    컬럼:
        snapshot_ts_utc, routeid, nodeid, arrtime_sec,
        arrprevstationcnt, vehicletp
    """
    ...

def save_arrivals_snapshot(df: pd.DataFrame, out_dir: Path, ts: datetime) -> Path:
    """data/raw/tago/arrivals/changwon_YYYYMMDD_HHMMSS.parquet"""
    ...
```

**주의**:
- `arrtime_sec`는 TAGO가 초 단위로 반환. 그대로 보존.
- 예측이 없는 정류소는 행 자체가 누락됨 (NULL 행 생성 금지 — 원본 충실).

---

### 4.6 `locations.py` — Lived 60초 스냅샷

**책임**: 3노선 각각의 현재 운행 중 차량 위치 수집.

```python
def snapshot_locations(
    client: TagoClient,
    city_code: int,
    route_ids: list[str],
) -> pd.DataFrame:
    """Lived 층 1회 스냅샷.

    컬럼:
        snapshot_ts_utc, routeid, vehicleno,
        nodeid, nodenm, nodeord,
        gpslati, gpslong  # 맵매칭된 좌표 — 노선 이탈 관찰 불가
    """
    ...
```

**주의**: `gpslati`·`gpslong`은 맵매칭 좌표라는 사실을 컬럼 주석 + 스키마 README에 명시. 향후 RDI 계산 시 혼동 방지.

---

### 4.7 `scheduler.py` — 오케스트레이션

**책임**: launchd가 호출하는 단일 진입점. 일일/분당 작업을 조율.

```python
def run_daily_anchor(cfg: Config) -> None:
    """06:55~06:59 1회 실행. stations + routes 갱신."""
    ...

def run_minute_tick(cfg: Config) -> None:
    """07:00~19:00 매 분 실행. arrivals + locations 각 1회 호출."""
    ...

def main() -> int:
    """CLI 진입점. argparse로 mode={anchor, tick} 분기.
    종료코드:
        0  정상
        22 TAGO 쿼터 초과
        30 TAGO 미등록 키
        99 기타 실패
    """
    ...
```

**중요**: `run_minute_tick`은 60초 tick 내에서 완료되어야 한다(→ `run_minute_tick`의 전체 소요 ≤ 30초 설계 목표, 타임아웃 10초 × 2엔드포인트 × 3노선 최악 60초 → 이때는 다음 tick 건너뜀).

---

### 4.8 `resolve_routes.py` — 이름→routeid 매칭 (첫 실행 1회)

**책임**: 첫 가동 시 `getRouteNoList` 전수 덤프 후 "마산합포 순환", "창원 중앙대로", "마산↔창원 광역" 3개 노선의 routeid를 식별하여 `config/tago.yaml`에 주입.

```python
def resolve_route_ids(
    client: TagoClient,
    city_code: int,
    route_name_patterns: list[str],  # 정규식
) -> dict[str, str]:
    """routename → routeid 매핑 반환.
    매칭 애매할 경우 다중 후보를 로그로 출력 + 케이에게 확인 요청 (exit 99).
    """
    ...
```

**실행**: 첫 가동 전 수동 1회 실행. 결과를 `config/tago.yaml`에 붙여넣는다. Claude Code 실행 메모에 이 단계 명시.

---

## 5. 설정 파일 `config/tago.yaml`

```yaml
tago:
  api_base: "https://apis.data.go.kr/1613000"
  api_key_env: "TAGO_API_KEY"  # 실제 값은 .env에서 로드
  city:
    name: changwon
    code: 38010  # 행정표준코드관리시스템 기준 창원시 법정동 코드 (resolve 단계에서 검증)
  routes:
    # resolve_routes.py 첫 실행 후 여기 자동 주입
    - name: "마산합포 순환"
      pattern: "^마산합포\\s*순환"
      route_id: null  # resolve 후 채움
    - name: "창원 중앙대로"
      pattern: "중앙대로"
      route_id: null
    - name: "마산↔창원 광역"
      pattern: "(마산.*창원|창원.*마산).*(광역|급행)"
      route_id: null
  collection:
    window_start: "07:00"
    window_end: "19:00"
    timezone: "Asia/Seoul"
    poll_interval_sec: 60
    http_timeout_sec: 10
    retry_attempts: 3
  limits:
    daily_call_budget: 2160
    hard_quota_code: "22"
    unregistered_key_code: "30"
  storage:
    raw_base: "data/raw/tago"
    processed_base: "data/processed/tago"
    checkpoint_dir: "data/checkpoints/tago"
    logs_dir: "logs/tago"
    parquet_compression: "snappy"
  observability:
    log_level: "INFO"
    log_format: "json"
    log_rotation_daily: true

reproducibility:
  random_seed: 42
  record_params_path: "data/processed/tago/provenance/{date}.json"
```

---

## 6. 환경 변수 `.env`

**이미 삽입 완료**:
```
TAGO_API_KEY=<실제키>  # URL 디코딩 전 원본 형태로 보존
```

**주의**: TAGO는 URL 인코딩된 키와 디코딩된 키 두 가지를 제공한다. `httpx.get(params=...)`은 자동 인코딩하므로 **디코딩된 원본 키**를 `.env`에 저장한다. 이중 인코딩 시 코드 30이 발생한다 — 디버깅 첫 후보.

---

## 7. 저장 스키마

### 7.1 원본 (`data/raw/tago/`) — 읽기 전용

| 경로 | 스키마 |
|------|--------|
| `stations/changwon_YYYYMMDD.parquet` | nodeid, nodenm, gpslati(float), gpslong(float), citycode, collected_at_utc |
| `routes/changwon_YYYYMMDD.parquet` | routeid, routeno, routetp, startvehicletime, endvehicletime, intervaltime, intervalsattime, intervalsuntime, startnodenm, endnodenm, collected_at_utc |
| `arrivals/changwon_YYYYMMDD_HHMMSS.parquet` | snapshot_ts_utc, routeid, nodeid, arrtime_sec(int), arrprevstationcnt(int), vehicletp |
| `locations/changwon_YYYYMMDD_HHMMSS.parquet` | snapshot_ts_utc, routeid, vehicleno, nodeid, nodenm, nodeord(int), gpslati(float), gpslong(float) |

**파일명 규칙**:
- 날짜·시각은 UTC가 아닌 **Asia/Seoul 로컬 시간**을 쓴다 (운용 편의).
- 스냅샷 파일은 분 단위 정밀도 (YYYYMMDD_HHMM00). 60초 주기이므로 초 단위 변동 불필요.

### 7.2 가공 (`data/processed/tago/`) — 야간 후처리

| 경로 | 용도 |
|------|------|
| `rdi_window_YYYYMMDD.parquet` | RDI 일일 집계 |
| `provenance/YYYYMMDD.json` | 실행 파라미터·해시·Git SHA 기록 |

### 7.3 체크포인트 (`data/checkpoints/tago/`)

```json
{
  "last_anchor_run": "2026-04-22T06:55:34+09:00",
  "last_tick_utc": "2026-04-22T13:23:00Z",
  "consecutive_failures": 0,
  "quota_tripped_date": null,
  "resolved_route_ids": {
    "masanhappo_circular": "GNA001",
    "changwon_jungang": "GNA012",
    "masan_changwon_gwangyeok": "GNA037"
  }
}
```

**용도**: 재기동 시 이 파일을 먼저 읽어 중복 호출·쿼터 회피. `quota_tripped_date`가 당일이면 tick은 no-op로 빠진다.

---

## 8. launchd plist

**경로**: `config/launchd/com.rhythmscape.tago-batch.plist`

**설치**: `cp config/launchd/*.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/com.rhythmscape.tago-batch.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rhythmscape.tago-batch.tick</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/DW/G-Drive2T/current_writings/rhythmscape/.venv/bin/python</string>
        <string>-m</string>
        <string>rhythmscape.ingest.tago.scheduler</string>
        <string>--mode</string>
        <string>tick</string>
        <string>--config</string>
        <string>/Users/DW/G-Drive2T/current_writings/rhythmscape/config/tago.yaml</string>
    </array>

    <key>StartCalendarInterval</key>
    <array>
      <!-- 07:00~19:59 매 분 -->
      <!-- 13시간 × 60분 = 780 엔트리 필요. 실제 작성 시 Python으로 생성 -->
    </array>

    <key>StandardOutPath</key>
    <string>/Users/DW/G-Drive2T/current_writings/rhythmscape/logs/tago/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>/Users/DW/G-Drive2T/current_writings/rhythmscape/logs/tago/launchd.err</string>

    <key>WorkingDirectory</key>
    <string>/Users/DW/G-Drive2T/current_writings/rhythmscape</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>

    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

**별도 plist (일일 앵커)**: `com.rhythmscape.tago-batch.anchor.plist` — 06:55 1회 실행, mode=anchor.

**주의**:
- `StartCalendarInterval`에 780개 `<dict>`를 손으로 박으면 디지털 인간으로서 자기혐오에 빠지므로, `scripts/gen_launchd_intervals.py`를 별도 작성해 분 단위 엔트리를 생성·주입한다.
- 대안으로 `StartInterval` 60초를 쓰면 윈도우 외 시간에도 깨어남 → 불필요한 호출 방지를 위해 `scheduler.py` 내부에서 윈도우 체크 후 no-op 처리도 가능. 단 단순성을 위해 `StartCalendarInterval` 방식 우선.

---

## 9. 에러 분기 로직

### 9.1 tick 실패 처리

```
http timeout / 5xx        → tenacity 재시도 (3회)
http 4xx                  → 즉시 실패, 체크포인트에 기록, 다음 tick 계속
TagoQuotaExceeded (22)    → 체크포인트 quota_tripped_date=오늘, 당일 남은 tick no-op
TagoKeyUnregistered (30)  → 체크포인트 기록, launchd job unload 요청 로그 + exit 30
기타 TagoAPIError         → 기록, 다음 tick 계속 (단, consecutive_failures ≥ 10 시 알림)
응답 parsing 실패         → 원본 바이트를 logs/tago/raw_dump_YYYYMMDD_HHMMSS.bin 에 보존
```

### 9.2 재기동 시 복원 순서

1. `data/checkpoints/tago/state.json` 로드
2. `quota_tripped_date`가 오늘이면 mode=tick 즉시 no-op
3. `resolved_route_ids`가 비어있으면 `resolve_routes.py` 먼저 1회 실행
4. 정상 tick 진입

---

## 10. 로깅 정책

**structlog JSON**, 일별 로테이션.

```python
import structlog
log = structlog.get_logger()
log.info("tick_start", route_ids=route_ids, tick_ts=ts.isoformat())
log.warning("tago_api_error", code="22", endpoint="getRouteAcctoBusLcList", route_id=rid)
```

**필수 이벤트**:
- `anchor_start`, `anchor_complete` (stations + routes)
- `tick_start`, `tick_complete`, 소요 ms
- `tago_api_error` (code, endpoint, route_id)
- `quota_exceeded` (date, total_calls)
- `parquet_write` (path, rows, bytes)

**보안**: `api_key`는 절대 로그에 쓰지 않는다. 로그 prefilter로 "TAGO_API_KEY" 문자열 포함 필드는 `***REDACTED***` 치환.

---

## 11. 재현성 (provenance)

매일 익일 00:30 `provenance/YYYYMMDD.json` 생성:

```json
{
  "date": "2026-04-22",
  "config_sha256": "<config/tago.yaml 해시>",
  "git_sha": "<rhythmscape HEAD>",
  "resolved_route_ids": {...},
  "total_ticks": 720,
  "successful_ticks": 718,
  "failed_ticks": 2,
  "failure_reasons": {"timeout": 2},
  "raw_file_hashes": {
    "stations/changwon_20260422.parquet": "sha256:...",
    "routes/changwon_20260422.parquet": "sha256:...",
    "arrivals_count": 720,
    "locations_count": 720
  }
}
```

이 파일이 해커톤 투명성 증빙의 **일일 아카이브**다.

---

## 12. 실행 순서 (Claude Code용, 복붙 가능)

```bash
# 0. 전제: rhythmscape/ 루트에 cd, .venv 활성화, .env 로드 확인
cd /Users/DW/G-Drive2T/current_writings/rhythmscape
source .venv/bin/activate  # (없으면: uv venv && uv pip install -e .)

# 1. 의존성 추가 (pyproject.toml dependencies에 반영 후 sync)
uv pip install httpx tenacity structlog pandas pyarrow pyyaml pydantic

# 2. 소스 스켈레톤 생성 (이 사양서의 §3, §4 따라)
#    Claude Code가 src/rhythmscape/ingest/tago/*.py 6개 + config/tago.yaml 생성

# 3. 첫 routeid 해결 (수동 1회)
python -m rhythmscape.ingest.tago.resolve_routes \
    --city-code 38010 \
    --config config/tago.yaml
# 결과의 route_id들을 config/tago.yaml에 붙여넣기

# 4. 앵커 1회 수동 실행 (연결 검증)
python -m rhythmscape.ingest.tago.scheduler --mode anchor --config config/tago.yaml
# 기대: data/raw/tago/stations/changwon_20260422.parquet 생성

# 5. tick 1회 수동 실행 (스냅샷 검증)
python -m rhythmscape.ingest.tago.scheduler --mode tick --config config/tago.yaml
# 기대: arrivals/ + locations/ 스냅샷 parquet 생성, 행 수 > 0

# 6. launchd plist 분 단위 엔트리 생성
python scripts/gen_launchd_intervals.py \
    --template config/launchd/com.rhythmscape.tago-batch.plist \
    --window 07:00-19:59

# 7. launchd 등록
cp config/launchd/com.rhythmscape.tago-batch.*.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.rhythmscape.tago-batch.tick.plist
launchctl load ~/Library/LaunchAgents/com.rhythmscape.tago-batch.anchor.plist

# 8. 첫 가동 증빙 기록
date -u "+%Y-%m-%dT%H:%M:%SZ" > docs/evidence/tago_first_run_utc.txt
git add docs/evidence/tago_first_run_utc.txt && git commit -m "evidence: TAGO batch first run timestamp"

# 9. 모니터링
tail -f logs/tago/*.log
# 또는
launchctl list | grep rhythmscape
```

**오늘 밤 22시까지 1-8단계 완료가 목표**. 9단계는 상시 백그라운드.

---

## 13. 투명성 증빙

Ado 룰링(2026-04-22): "valid GitHub commits from when the hackathon started."

본 배치의 코드·설정·첫 가동 타임스탬프는 모두 해커톤 기간 내 커밋으로 증명된다:
- `src/rhythmscape/ingest/tago/**` — 2026-04-22 작성 커밋
- `config/tago.yaml`, `config/launchd/*.plist` — 2026-04-22 작성 커밋
- `docs/evidence/tago_first_run_utc.txt` — 첫 가동 타임스탬프
- 일일 `provenance/*.json` — 배치의 매일 작동 증빙

---

## 14. 품질 게이트 (Definition of Done, Day 1)

이 배치가 Day 1 "완료"로 선언되려면 **모두** 충족:

- [x] `src/rhythmscape/ingest/tago/` 6개 모듈 import 성공 (실제 8개 작성: client, normalize, stations, routes, arrivals, locations, scheduler, resolve_routes)
- [x] `resolve_routes.py` 실행으로 3개 routeid 확정 + config에 주입 (manifest 검증 방식: 271 / BRT6000 / 710 모두 live TAGO 확인)
- [x] `--mode anchor` 수동 실행 → stations(2752)·routes(3)·route_stations(203) parquet 생성
- [x] `--mode tick` 수동 실행 → arrivals(10)·locations(20) parquet 생성, 행 수 > 0
- [x] launchd 두 job 모두 `launchctl list`에 등록 확인 (`com.rhythmscape.tago-batch.tick` + `.anchor`)
- [x] 첫 가동 타임스탬프 `docs/evidence/tago_first_run_utc.txt` 커밋 (2026-04-22T23:18:45Z)
- [x] `.env` 커밋 제외 확인 (`git status --ignored` → `!! .env`)
- [x] API 키 노출 grep 검사: `grep -ri "TAGO_API_KEY=" --exclude=.env` → 문서 레퍼런스만 (실제 키 값 0건)

---

## 15. 남은 의사결정 (사양서 범위 외, 다음 단계)

- RDI 집계 스크립트(야간 후처리): `ingest/tago/aggregate_rdi.py` — Day 2 오전 설계.
- OSM 네트워크와의 공간 조인: PRM 계산 단계에서 별도 사양서.
- 다른 도시 확장(부산·진주·사천): `city` 블록 파라미터화 — Day 3 이후.

---

**End of spec** · 구현 주체: Claude Code · 설계 리뷰: 제시카 + 케이
