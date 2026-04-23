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


def minute_entries(
    start: str,
    end: str,
    stride_minutes: int = 1,
) -> list[dict[str, int]]:
    """Return ``{'Hour': h, 'Minute': m}`` entries between ``start`` and ``end``.

    - ``stride_minutes`` controls step (1 = every minute, 10 = every ten).
    - When ``end < start`` the window is overnight (e.g. ``20:00-06:59``):
      we iterate forward through midnight and wrap into the next day.

    The inclusive-endpoint rule is "stop at or before ``end``"; an entry is
    placed at ``end`` only if the stride lands exactly on it, otherwise we
    stop at the last stride-aligned minute that is still ≤ ``end``.
    """
    sh, sm = parse_hhmm(start)
    eh, em = parse_hhmm(end)
    start_min = sh * 60 + sm
    end_min = eh * 60 + em
    day = 24 * 60

    if end_min >= start_min:
        span = end_min - start_min
    else:
        span = (day - start_min) + end_min
    # Inclusive of both endpoints if stride divides span evenly; otherwise
    # the last entry is at start_min + floor(span / stride) * stride.
    n_steps = span // stride_minutes + 1

    entries: list[dict[str, int]] = []
    for i in range(n_steps):
        abs_min = (start_min + i * stride_minutes) % day
        h, m = divmod(abs_min, 60)
        entries.append({"Hour": h, "Minute": m})
    return entries


def merged_entries(*windows: tuple[str, str, int]) -> list[dict[str, int]]:
    """Union of multiple ``(start, end, stride)`` windows, deduplicated.

    Used to stitch a day-tick window (07:00-19:59 stride 1) and a night-tick
    window (20:00-06:59 stride 10) into one launchd ``StartCalendarInterval``
    array, keeping exactly one job Label per city.
    """
    seen: set[tuple[int, int]] = set()
    out: list[dict[str, int]] = []
    for start, end, stride in windows:
        for entry in minute_entries(start, end, stride_minutes=stride):
            key = (entry["Hour"], entry["Minute"])
            if key in seen:
                continue
            seen.add(key)
            out.append(entry)
    # Sort by (hour, minute) for readability in the resulting plist.
    out.sort(key=lambda e: (e["Hour"], e["Minute"]))
    return out


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
    night_window: tuple[str, str] | None = None,
    night_stride_minutes: int = 10,
) -> dict:
    """Generate the tick plist. When ``night_window`` is provided, a second
    (stride-spaced, overnight) window is merged into the same job.

    The single-job design keeps one launchd Label per city regardless of
    day/night split — simpler lifecycle (one unload/load) and unified log
    file.
    """
    logs_dir = project_root / "logs" / "tago"
    if night_window is None:
        intervals = minute_entries(window_start, window_end)
    else:
        intervals = merged_entries(
            (window_start, window_end, 1),
            (night_window[0], night_window[1], night_stride_minutes),
        )
    return {
        "Label": _label("tick", city),
        "ProgramArguments": _program_args(
            project_root, "tick", config_path, cities_path, city
        ),
        "StartCalendarInterval": intervals,
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
        help="Day tick window HH:MM-HH:MM (default 07:00-19:59)",
    )
    parser.add_argument(
        "--night-window",
        default=None,
        help="Optional night tick window HH:MM-HH:MM (e.g. 20:00-06:59). "
        "Overnight windows are supported (end < start wraps through midnight). "
        "When provided, merged into the same tick plist with --night-stride.",
    )
    parser.add_argument(
        "--night-stride",
        type=int,
        default=10,
        help="Night window stride in minutes (default 10)",
    )
    parser.add_argument(
        "--anchor-time",
        default="06:55",
        help="Anchor HH:MM (default 06:55). Staggered per city to avoid "
        "TAGO session-pool saturation when large cities paginate.",
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
    night_win = None
    if args.night_window:
        ns, ne = args.night_window.split("-")
        night_win = (ns, ne)
    tick_plist = build_tick_plist(
        project_root,
        config_path,
        start,
        end,
        cities_path=cities_path,
        city=args.city,
        night_window=night_win,
        night_stride_minutes=args.night_stride,
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
