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


def _program_args(
    project_root: Path,
    mode: str,
    config_path: Path | None,
    cities_path: Path | None,
    city: str | None,
) -> list[str]:
    """Assemble the scheduler CLI arguments. Prefers --city over --config."""
    python_bin = project_root / ".venv" / "bin" / "python"
    args = [
        str(python_bin),
        "-m",
        "rhythmscape.ingest.tago.scheduler",
        "--mode",
        mode,
    ]
    if city is not None:
        args += ["--cities", str(cities_path), "--city", city]
    else:
        args += ["--config", str(config_path)]
    return args


def _label(suffix: str, city: str | None) -> str:
    if city is None:
        return f"com.rhythmscape.tago-batch.{suffix}"
    return f"com.rhythmscape.tago-batch.{city}.{suffix}"


def _log_name(kind: str, city: str | None) -> str:
    """Filename suffix for launchd stdout/stderr — per-city if given."""
    if city is None:
        return f"launchd.{kind}"
    return f"launchd.{city}.{kind}"


def build_tick_plist(
    project_root: Path,
    config_path: Path | None,
    window_start: str,
    window_end: str,
    cities_path: Path | None = None,
    city: str | None = None,
) -> dict:
    logs_dir = project_root / "logs" / "tago"
    return {
        "Label": _label("tick", city),
        "ProgramArguments": _program_args(
            project_root, "tick", config_path, cities_path, city
        ),
        "StartCalendarInterval": minute_entries(window_start, window_end),
        "WorkingDirectory": str(project_root),
        "StandardOutPath": str(logs_dir / f"{_log_name('tick', city)}.out"),
        "StandardErrorPath": str(logs_dir / f"{_log_name('tick', city)}.err"),
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin",
        },
        "RunAtLoad": False,
        "KeepAlive": False,
    }


def build_anchor_plist(
    project_root: Path,
    config_path: Path | None,
    anchor_time: str,
    cities_path: Path | None = None,
    city: str | None = None,
) -> dict:
    logs_dir = project_root / "logs" / "tago"
    ah, am = parse_hhmm(anchor_time)
    return {
        "Label": _label("anchor", city),
        "ProgramArguments": _program_args(
            project_root, "anchor", config_path, cities_path, city
        ),
        "StartCalendarInterval": {"Hour": ah, "Minute": am},
        "WorkingDirectory": str(project_root),
        "StandardOutPath": str(logs_dir / f"{_log_name('anchor', city)}.out"),
        "StandardErrorPath": str(logs_dir / f"{_log_name('anchor', city)}.err"),
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
        default=None,
        help="Legacy single-city yaml path (e.g. config/tago.yaml). "
        "Mutually exclusive with --city.",
    )
    parser.add_argument(
        "--cities",
        type=Path,
        default=Path("config/cities.yaml"),
        help="Multi-city manifest path (default config/cities.yaml)",
    )
    parser.add_argument(
        "--city",
        type=str,
        default=None,
        help="City slug from --cities. Produces per-city plists with "
        "Label com.rhythmscape.tago-batch.<city>.{tick,anchor}.",
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

    if args.config is None and args.city is None:
        parser.error("either --config <yaml> or --city <slug> must be provided")
    if args.config is not None and args.city is not None:
        parser.error("--config and --city are mutually exclusive")

    project_root = args.project_root.resolve()
    if not project_root.is_dir():
        print(f"ERROR: project-root does not exist: {project_root}", file=sys.stderr)
        return 2

    output_dir = args.output_dir if args.output_dir.is_absolute() else (project_root / args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = None
    cities_path = None
    if args.config is not None:
        config_path = args.config if args.config.is_absolute() else (project_root / args.config)
    else:
        cities_path = args.cities if args.cities.is_absolute() else (project_root / args.cities)

    start, end = args.window.split("-")
    tick_plist = build_tick_plist(
        project_root, config_path, start, end, cities_path=cities_path, city=args.city
    )
    anchor_plist = build_anchor_plist(
        project_root, config_path, args.anchor_time, cities_path=cities_path, city=args.city
    )

    suffix = "" if args.city is None else f".{args.city}"
    tick_path = output_dir / f"com.rhythmscape.tago-batch{suffix}.tick.plist"
    anchor_path = output_dir / f"com.rhythmscape.tago-batch{suffix}.anchor.plist"

    with tick_path.open("wb") as fh:
        plistlib.dump(tick_plist, fh)
    with anchor_path.open("wb") as fh:
        plistlib.dump(anchor_plist, fh)

    n_entries = len(tick_plist["StartCalendarInterval"])
    target_label = args.city or "(legacy)"
    print(f"✓ {tick_path}  ({n_entries} minute entries, window {start}-{end})  [{target_label}]")
    print(f"✓ {anchor_path}  (daily at {args.anchor_time})  [{target_label}]")
    print()
    print("Install with:")
    print(f"  cp {tick_path} ~/Library/LaunchAgents/")
    print(f"  cp {anchor_path} ~/Library/LaunchAgents/")
    print(f"  launchctl load ~/Library/LaunchAgents/{tick_path.name}")
    print(f"  launchctl load ~/Library/LaunchAgents/{anchor_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
