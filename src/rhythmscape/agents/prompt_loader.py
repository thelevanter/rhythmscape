"""Prompt loader for theoretical agents.

Loads `prompts/{ko,en}/{theorist}.md` and strips the operational annotation
section (the part after ``## 운용 주석``) so the system prompt contains
only the theoretical framing that the agent sees.
"""

from __future__ import annotations

import re
from pathlib import Path


THEORISTS = ("lefebvre", "deleuze_guattari", "foucault")
LANGS = ("ko", "en")

# Operational annotation markers that separate agent-facing content from
# author/Code facing metadata. Anything at or after these headers is stripped.
OPERATIONAL_MARKERS = (
    r"^##\s*운용\s*주석",          # Korean
    r"^##\s*Operational\s*Notes",   # English fallback
    r"^##\s*Agent\s*Infrastructure",
)


def _strip_operational(text: str) -> str:
    lines = text.splitlines()
    cut = len(lines)
    for idx, line in enumerate(lines):
        for pat in OPERATIONAL_MARKERS:
            if re.match(pat, line):
                cut = idx
                break
        if cut != len(lines):
            break
    return "\n".join(lines[:cut]).rstrip() + "\n"


def load_prompt(theorist: str, lang: str = "ko", base: Path = Path("prompts")) -> str:
    """Return the agent-facing system prompt for a theorist in a language."""
    if theorist not in THEORISTS:
        raise ValueError(f"unknown theorist {theorist!r}; expected one of {THEORISTS}")
    if lang not in LANGS:
        raise ValueError(f"unknown lang {lang!r}; expected one of {LANGS}")
    path = base / lang / f"{theorist}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    raw = path.read_text(encoding="utf-8")
    return _strip_operational(raw)


def load_all(lang: str = "ko", base: Path = Path("prompts")) -> dict[str, str]:
    """Return {theorist: prompt_text} for all three theorists in the given language."""
    return {t: load_prompt(t, lang, base) for t in THEORISTS}
