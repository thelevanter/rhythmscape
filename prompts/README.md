# Rhythmscape — Theoretical Prompt Library

This directory houses bilingual (Korean / English) prompts that turn
critical-geographic concepts into operational interpretation engines
for Claude Opus 4.7.

## Structure

```
prompts/
├── ko/   # Korean prompts (primary audience: Korean urban researchers, activists)
└── en/   # English prompts (primary audience: international critical-geography readers)
```

## Planned prompt families (populated during hackathon week)

- `ardi_interpret` — explains Automotive Rhythm Dominance Index scores
  with Lefebvre's polyrhythmia / eurhythmia / arrhythmia vocabulary.
- `prm_interpret` — explains Pedestrian Residue Map gaps with
  Deleuze-Guattari's refrain and Urry/Sheller/Dant's compulsion of
  automobility.
- `embodied_residue` — interprets what remains when automotive capture
  is incomplete, drawing on Gimm (2026) on Physical AI's embodied
  residue, scale-translated to urban infrastructure.

## Design principles

1. **Bilingual, not translated** — Korean and English prompts are
   written for their respective discourse conventions, not rendered
   from one to the other.
2. **Operational, not decorative** — each prompt produces a defined
   output schema (label, severity, citation anchors) that downstream
   rendering code consumes.
3. **Theoretically load-bearing** — prompts cite specific passages
   (author, year, chapter/section) rather than invoking theorists as
   mood lighting.
