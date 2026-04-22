#!/usr/bin/env python3
"""Generate launchd plists for the Rhythmscape TAGO batch.

Spec §8. Writes two property-list files:

- ``com.rhythmscape.tago-batch.tick.plist`` — fires every minute inside
  ``[window_start, window_end]`` (780 ``<dict>`` entries in a 12 h window).
- ``com.rhythmscape.tago-batch.anchor.plist`` — fires once per day at
  ``anchor_time``.

Usage
-----
    python scripts/gen_launchd_intervals.py \\
        --project-root /Users/dw/G-Drive2T/current_writings/Claude_Hackathon/rhythmscape \\
        --window 07:00-19:59 \\
        --anchor-time 06:55 \\
        --output-dir config/launchd

The output plists are ready to ``cp`` into ``~/Library/LaunchAgents/`` and
``launchctl load``.
"""

from __future__ import annotations

import argparse
import plistlib
import sys
from pathlib import Path


def parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def minute_entries(start: str, end: str) -> list[dict[str, int]]:
    """Return one ``{'Hour': h, 'Minute': m}`` entry per minute in the inclusive range."""
    sh, sm = parse_hhmm(start)
    eh, em = parse_hhmm(end)
    entries: list[dict[str, int]] = []
    h, m = sh, sm
    while (h, m) <= (eh, em):
        entries.append({"Hour": h, "Minute": m})
        m += 1
        if m >= 60:
            m = 0
            h += 1
        if h >= 24:
            break
    return entries


def build_tick_plist(
    project_root: Path,
    config_path: Path,
    window_start: str,
    window_end: str,
) -> dict:
    python_bin = project_root / ".venv" / "bin" / "python"
    logs_dir = project_root / "logs" / "tago"
    return {
        "Label": "com.rhythmscape.tago-batch.tick",
        "ProgramArguments": [
            str(python_bin),
            "-m",
            "rhythmscape.ingest.tago.scheduler",
            "--mode",
            "tick",
            "--config",
            str(config_path),
        ],
        "StartCalendarInterval": minute_entries(window_start, window_end),
        "WorkingDirectory": str(project_root),
        "StandardOutPath": str(logs_dir / "launchd.tick.out"),
        "StandardErrorPath": str(logs_dir / "launchd.tick.err"),
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        },
        "RunAtLoad": False,
        "KeepAlive": False,
    }


def build_anchor_plist(
    project_root: Path,
    config_path: Path,
    anchor_time: str,
) -> dict:
    python_bin = project_root / ".venv" / "bin" / "python"
    logs_dir = project_root / "logs" / "tago"
    ah, am = parse_hhmm(anchor_time)
    return {
        "Label": "com.rhythmscape.tago-batch.anchor",
        "ProgramArguments": [
            str(python_bin),
            "-m",
            "rhythmscape.ingest.tago.scheduler",
            "--mode",
            "anchor",
            "--config",
            str(config_path),
        ],
        "StartCalendarInterval": {"Hour": ah, "Minute": am},
        "WorkingDirectory": str(project_root),
        "StandardOutPath": str(logs_dir / "launchd.anchor.out"),
        "StandardErrorPath": str(logs_dir / "launchd.anchor.err"),
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        },
        "RunAtLoad": False,
        "KeepAlive": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Rhythmscape TAGO batch launchd plists"
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        required=True,
        help="Absolute path to the rhythmscape repo root",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/tago.yaml"),
        help="Path to tago.yaml (relative to project-root if not absolute)",
    )
    parser.add_argument(
        "--window",
        default="07:00-19:59",
        help="Tick window HH:MM-HH:MM (default 07:00-19:59)",
    )
    parser.add_argument(
        "--anchor-time",
        default="06:55",
        help="Anchor HH:MM (default 06:55)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("config/launchd"),
        help="Where to write the plists (relative to project-root if not absolute)",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"ERROR: project-root does not exist: {project_root}", file=sys.stderr)
        return 2

    config_path = args.config if args.config.is_absolute() else (project_root / args.config)
    output_dir = args.output_dir if args.output_dir.is_absolute() else (project_root / args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    start, end = args.window.split("-")
    tick_plist = build_tick_plist(project_root, config_path, start, end)
    anchor_plist = build_anchor_plist(project_root, config_path, args.anchor_time)

    tick_path = output_dir / "com.rhythmscape.tago-batch.tick.plist"
    anchor_path = output_dir / "com.rhythmscape.tago-batch.anchor.plist"

    with tick_path.open("wb") as fh:
        plistlib.dump(tick_plist, fh)
    with anchor_path.open("wb") as fh:
        plistlib.dump(anchor_plist, fh)

    n_entries = len(tick_plist["StartCalendarInterval"])
    print(f"✓ {tick_path}  ({n_entries} minute entries, window {start}-{end})")
    print(f"✓ {anchor_path}  (daily at {args.anchor_time})")
    print()
    print("Install with:")
    print(f"  cp {tick_path} ~/Library/LaunchAgents/")
    print(f"  cp {anchor_path} ~/Library/LaunchAgents/")
    print("  launchctl load ~/Library/LaunchAgents/com.rhythmscape.tago-batch.tick.plist")
    print("  launchctl load ~/Library/LaunchAgents/com.rhythmscape.tago-batch.anchor.plist")
    return 0


if __name__ == "__main__":
    sys.exit(main())
