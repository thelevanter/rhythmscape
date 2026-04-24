"""Route a critique_flag row to the appropriate theorist-agent set.

Routing rules (prompts/ko/lefebvre.md §운용 주석 기록):

    dressage_alert  → Lefebvre + Foucault   (조련·정상화)
    vitality_query  → Deleuze-Guattari + Lefebvre   (리토르넬로·polyrhythmia)

Flag-less bins are not routed — the critical device selects before
interpretation runs, keeping API cost bounded.
"""

from __future__ import annotations


ROUTING = {
    "dressage_alert": ("lefebvre", "foucault"),
    "vitality_query": ("deleuze_guattari", "lefebvre"),
}


def route(critique_flag: str | None) -> tuple[str, ...]:
    """Return the tuple of theorist slugs to invoke for a given flag value."""
    if critique_flag is None:
        return ()
    return ROUTING.get(critique_flag, ())


def all_theorists_for_flags(flags: list[str | None]) -> set[str]:
    """Union of theorists that any flag in the list would invoke."""
    out: set[str] = set()
    for f in flags:
        out.update(route(f))
    return out
