# Sejong BIS Scrape Plan — Day 3 Morning

**Status**: Reconnaissance only (Day 2 evening · 17:05 KST). Actual requests
deferred to Day 3 07:30+. This memo enables immediate execution.
**Target**: 세종 BIS public site (bus schedule section).
**Scope**: single-shot fetch per route, 3 routes (B2 / 1004 / 551). No
polling, no crawl.

---

## 1. Host correction

Cowork's `add_city_selection_rationale.md` §2.1 names `sejongbis.kr`.
That domain **does not resolve** (`NXDOMAIN`). The actual endpoint is:

- **`https://bis.sejong.go.kr/`** — desktop (redirects to
  `/web/main/main.view`)
- `https://mbis.sejong.go.kr/` — mobile (redirects to
  `/mobile/main/m_main.view`)

Sejong BIS is a **go.kr government site**. Public data; no login wall on
the route-search path examined.

## 2. Page and endpoint map

The desktop SPA sends three AJAX POSTs through an internal `ajaxCall()`
helper that uses standard jQuery `$.ajax` under the hood. Observed on
`/web/traffic/traffic_bus_line_search.view`:

| Step | Endpoint (POST) | Form data | Returns |
|---|---|---|---|
| 1 | `/web/traffic/searchBusRoute.do` | `{busRoute: <routeno>}` e.g. `"B2"` | Route candidate list with internal `busRouteId` |
| 2 | `/web/traffic/searchBusRouteDetail.do` | `{busRouteId: <id>}` | Station list for the route |
| 3 | **`/web/traffic/searchBusTimeList.do`** | `{busRouteId: <id>}` | **배차 시간표 — what we need** |
| 4 | `/web/traffic/searchBusRealLocationDetail.do` | `{busRouteId: <id>}` | Real-time positions (not needed; TAGO covers this) |

`busRouteId` is **Sejong BIS internal** — distinct from TAGO `routeid`.
A 2-step resolve is required: routeno ("B2") → Sejong `busRouteId` →
timetable.

## 3. Mapping our three TAGO routes to Sejong BIS

Our target routenos and TAGO routeids:

| routeno | TAGO routeid | expected Sejong lookup query |
|---|---|---|
| B2 | SJB293000362 | `busRoute="B2"` |
| 1004 | SJB293000178 | `busRoute="1004"` |
| 551 | SJB293000030 | `busRoute="551"` |

Because TAGO routeid `SJB293*` is not reusable against Sejong BIS, the
scrape must begin from the routeno text search. B2 disambiguation may
return multiple variants (outbound/inbound/short-turn) — match rule:
prefer the variant whose station count from `searchBusRouteDetail.do`
aligns with the TAGO `route_stations` we already hold for that routeid.

## 4. Data we expect to extract from `searchBusTimeList.do`

Unknown without fetching the live response (held off per scope). Based
on typical Korean BIS conventions the response likely contains some
combination of:

- First bus / last bus times per direction
- Dispatch intervals by day-type (weekday / Saturday / Sunday /
  holiday), possibly further split by time-of-day bands
- Possibly per-dispatch raw scheduled departure times

Minimum viable extraction for RDI alignment:

```
route_id        SJB293000362    # our canonical TAGO id
route_no        "B2"
daytype         weekday | sat | sun
peak_interval_min     <int>
off_peak_interval_min <int>     # same as peak if BIS does not split
prescribed_source     "sejongbis_scrape"
collected_at          <iso-8601>
source_url            https://bis.sejong.go.kr/web/traffic/searchBusTimeList.do
source_busroute_id    <Sejong internal id>    # for audit
```

Output parquet: `data/processed/tago/prescribed_intervals_sejong_external.parquet`.
Downstream `rdi.py` gains a `--prescribed-source` flag to load TAGO
plus external parquet in a single view; `prescribed_source` column is
propagated through to `rdi_sejong_20260423.parquet`.

## 5. Legal and ethical posture

- **`robots.txt`**: none (server returns an HTML error for the path,
  HTTP 200 with a Korean "요청한 경로가 존재하지 않습니다" body). Absent
  robots.txt is conventionally "allow all"; regardless, we respect
  standard scraping etiquette.
- **Volume**: 3 routes × 2 requests each = 6 POSTs total. Below any
  reasonable rate-limit threshold.
- **Schedule**: request cadence of 2 s between calls (well below the
  site's own concurrent user load).
- **User-Agent**: explicit string naming the project
  (`Rhythmscape-Hackathon/0.1 (+https://github.com/thelevanter/rhythmscape)`)
  so the site operator can identify and contact if needed.
- **공공데이터법 §38** (상시 제공 의무) and **전자정부법** apply
  to go.kr sites. Public data intended for reference is within fair use
  for a non-commercial research/hackathon project.
- **Storage**: parsed values only, no raw HTML archive. `source_url`
  recorded in the parquet's `source_url` column for provenance.
- **Abort conditions**: if 4xx status, rate-limit header, or CAPTCHA
  is encountered, abort immediately and surface to Cowork.

## 6. Implementation sketch (Day 3 morning, ≤ 60 min)

Module: `scripts/scrape_sejongbis_schedule.py` (single-shot, not a
persistent module).

```python
import time
import httpx
from bs4 import BeautifulSoup  # or lxml; new dep, confirm pyproject bump

BASE = "https://bis.sejong.go.kr"
UA = "Rhythmscape-Hackathon/0.1 (+https://github.com/thelevanter/rhythmscape)"

def resolve_bus_route_id(client, route_no: str) -> list[dict]:
    r = client.post(
        f"{BASE}/web/traffic/searchBusRoute.do",
        data={"busRoute": route_no},
        headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"},
    )
    r.raise_for_status()
    # response is HTML fragment; parse <li id="..."> entries
    # each li carries a busRouteId as its id attribute (ajaxSuccess builds them)
    ...

def fetch_timetable(client, bus_route_id: str) -> dict:
    r = client.post(
        f"{BASE}/web/traffic/searchBusTimeList.do",
        data={"busRouteId": bus_route_id},
        headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"},
    )
    r.raise_for_status()
    ...

def main():
    targets = [
        ("SJB293000362", "B2"),
        ("SJB293000178", "1004"),
        ("SJB293000030", "551"),
    ]
    with httpx.Client(timeout=15) as client:
        for tago_routeid, routeno in targets:
            candidates = resolve_bus_route_id(client, routeno)
            time.sleep(2)
            # pick variant; call fetch_timetable; parse intervals
            ...
```

Dependency bump required: `beautifulsoup4` or `lxml`. Already-present
stack (`httpx`, `pandas`, `pyarrow`, `pyyaml`) covers the rest.

## 7. Fallback if headway is not publishable

If `searchBusTimeList.do` returns only raw dispatch timestamps (no
summarized headway), derive headway as the mean diff between successive
scheduled departures per daytype × direction. Record this derivation
step in the parquet metadata so it cannot be confused with an
operator-declared value.

If the timetable returns dispatch counts but not headways AND dispatch
counts are not publicly accessible without a login wall (unlikely on
a go.kr public site, but possible), fall back to Cowork Day 3 decision
point: either contact 세종교통정보과 directly, or permanently leave
Sejong in the opacity category for the hackathon report.

## 8. Day 3 hand-off checklist

At 07:30+ Day 3, a clean execution sequence is:

1. `python scripts/scrape_sejongbis_schedule.py --routes B2,1004,551`
2. Verify `data/processed/tago/prescribed_intervals_sejong_external.parquet`
   has 9 rows (3 routes × 3 daytypes) with `prescribed_source=
   "sejongbis_scrape"`
3. Run `python -m rhythmscape.metrics.rdi --city sejong --date 20260424
   --prescribed-source sejongbis_external` (flag may need CLI
   addition first)
4. Smoke-check: `rdi_sejong_20260424.parquet` has rows > 0
5. 4-city preview with all four cities participating regains
   synchronic completeness.

---

## Appendix — Sejong BIS navigation (observed)

- `/web/main/main.view` — landing
- `/web/traffic/traffic_bus_line_search.view` — **route search (our entry
  point)**
- `/web/traffic/traffic_station_search.view` — station search
- `/web/traffic/traffic_route_explore.view` — origin-destination pathing
- `/web/traffic/traffic_real_time_bus.view` — real-time map
- `/web/atms/atms_traffic_main.view` — ATMS (road traffic, out of scope)
- Related: `/web/community/*`, `/web/information/*` — informational;
  not needed for schedule scrape.
