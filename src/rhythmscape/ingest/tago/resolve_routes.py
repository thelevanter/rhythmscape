"""Verify configured route IDs against TAGO — manifest-based, no regex.

Design note (2026-04-23): The original spec §4.8 resolved colloquial route
names to IDs via regex against ``routeno``/``startnodenm``/``endnodenm``.
That approach proved fragile — TAGO's response fields do not carry the
colloquial names we use internally (e.g. "마산합포 순환"), and patterns
matched zero candidates on the live data. Route selection is now an explicit
theoretical choice encoded in ``config/tago.yaml``:

    routes:
      - routeid: CWB379002710
        route_no: "271"
        route_type: 지선/순환
        theoretical_role: 마산합포 박물관 루프 — 도심 내부 리듬

This module's job is therefore to **verify** that each configured ``routeid``
actually exists in the TAGO route dump for the given ``cityCode``, and to
surface metadata (start/end nodes, route type) for provenance. If all
configured IDs resolve, exit 0. If any are missing, exit 99 with a diff.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path

import structlog
import yaml
from dotenv import load_dotenv

from rhythmscape.ingest.tago.client import TagoClient
from rhythmscape.ingest.tago.normalize import extract_items

log = structlog.get_logger(__name__)

SERVICE = "BusRouteInfoInqireService"
OPERATION = "getRouteNoList"


def dump_all_routes(client: TagoClient, city_code: int, page_size: int = 100) -> list[dict]:
    """Return every route in ``city_code`` as normalized dicts."""
    rows: list[dict] = []
    page_no = 1
    total_pages: int | None = None

    while True:
        body = client.call(
            SERVICE,
            OPERATION,
            {"cityCode": city_code, "numOfRows": page_size, "pageNo": page_no},
        )
        total_count = int(body.get("totalcount") or 0)
        if total_pages is None:
            total_pages = max(1, math.ceil(total_count / page_size)) if total_count else 1
            log.info("routes_dump_start", total=total_count, pages=total_pages)
        rows.extend(extract_items(body))
        if page_no >= (total_pages or 1):
            break
        page_no += 1
    return rows


def verify_manifest(
    manifest: list[dict],
    all_routes: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Cross-check configured routeids against the live TAGO dump.

    Returns
    -------
    verified
        Entries where the configured routeid was found, annotated with
        live metadata (``start``, ``end``, ``type``, ``no``).
    missing
        Entries where the configured routeid was absent from the dump.
    """
    by_id = {str(r.get("routeid")): r for r in all_routes}
    verified: list[dict] = []
    missing: list[dict] = []
    for entry in manifest:
        rid = str(entry.get("routeid") or "")
        live = by_id.get(rid)
        if live is None:
            missing.append(entry)
            continue
        verified.append(
            {
                **entry,
                "live_routeno": live.get("routeno"),
                "live_routetp": live.get("routetp"),
                "live_startnodenm": live.get("startnodenm"),
                "live_endnodenm": live.get("endnodenm"),
            }
        )
    return verified, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify TAGO route manifest in config/tago.yaml against live API"
    )
    parser.add_argument("--config", type=Path, default=Path("config/tago.yaml"))
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("TAGO_API_KEY", "")
    if not api_key:
        print("ERROR: TAGO_API_KEY not set in environment/.env", file=sys.stderr)
        return 99

    with args.config.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    city_code = int(cfg["tago"]["city"]["code"])
    manifest: list[dict] = cfg["tago"]["routes"]

    if not manifest:
        print("ERROR: tago.routes is empty — nothing to verify", file=sys.stderr)
        return 99

    with TagoClient(api_key=api_key) as client:
        all_routes = dump_all_routes(client, city_code)
    print(f"[verify] city_code={city_code} — dumped {len(all_routes)} routes")

    verified, missing = verify_manifest(manifest, all_routes)

    print(f"\n[verify] manifest: {len(manifest)} routeid(s)")
    for entry in verified:
        print(
            f"  ✓ {entry['routeid']}  (cfg={entry.get('route_no')} / "
            f"live={entry['live_routeno']}, type={entry['live_routetp']})"
        )
        print(
            f"      {entry['live_startnodenm']} ↔ {entry['live_endnodenm']}"
        )
        print(f"      role: {entry.get('theoretical_role', '(no role)')}")

    if missing:
        print(f"\n[verify] MISSING {len(missing)} routeid(s):", file=sys.stderr)
        for entry in missing:
            print(
                f"  ✗ {entry.get('routeid')}  (cfg route_no={entry.get('route_no')})",
                file=sys.stderr,
            )
        print(
            "\n[verify] Fix config/tago.yaml — a configured routeid was not found "
            "in the live TAGO dump for this city_code.",
            file=sys.stderr,
        )
        return 99

    print(f"\n[verify] all {len(manifest)} routeid(s) present in TAGO live dump — OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
