# Rhythmscape

**A Critical Urban Diagnostic Assistant.**

> *"Whose rhythm is the infrastructure built for, and what settlement life gets left in the gaps?"*

Built with Claude Code for the *Built with Opus 4.7* Hackathon
(April 22–27, 2026).

🚧 **Status**: Hackathon build in progress. Expect rapid changes.

---

## Transparency Note

This project is built entirely during the hackathon week
(2026-04-22 → 2026-04-27 KST). Planning documents (spec, scoping,
literature scouting) and the theoretical prompt framework — informed
by Lefebvre's rhythmanalysis, Deleuze–Guattari's refrain theory,
Foucault's governmentality, and critical-geographic accounts of
automobility (Urry, Sheller, Dant) — predate the hackathon as
**past experience**, consistent with the rule clarification provided
by Anthropic moderators on 2026-04-22 in the `#-office-hours` channel
of the official Claude Developer Discord (moderated by
Ado | Claude):

> "The requirement is to build a new project with valid GitHub
> commits from when the hackathon started to when it ends. That's
> not to say you can't take inspiration and learnings from prior
> works into building the hackathon project, but the code for the
> hackathon needs to be written this week."

**All application code in this repository is written during the
hackathon week.** Verbatim moderator rulings are preserved in
`docs/evidence/` for audit purposes.

---

## What it does

A Python package + CLI that ingests a city's transport networks,
settlement indicators, and local discourse, then produces a
self-contained HTML report identifying **friction zones** — places
where the rhythm of automotive infrastructure collides with the
rhythm of settlement life.

- **Flagship city**: Changwon (Masan-hoewon district) — a 1970s
  planned industrial city whose grid was laid out on the assumption
  of universal car ownership.
- **Scale-up**: Busan/Yeongdo · Jinju · Sacheon (Gyeongsangnam-do).

**Core indicators**:
- **Automotive Rhythm Dominance Index (ARDI)** — spatio-temporal
  car-regime score per grid cell
- **Pedestrian Residue Map (PRM)** — where walking life survives the
  automotive capture

**Theoretical grounding**: Lefebvre's rhythmanalysis, Urry/Sheller/
Dant's automobility theory, Deleuze–Guattari's refrain theory,
Foucault's governmentality, Brenner/Harvey on uneven development.

---

## Installation (coming)

```bash
# uv (recommended)
uv sync

# Copy env template and fill in API keys
cp .env.example .env
# ANTHROPIC_API_KEY, KOSIS_API_KEY, SGIS_SERVICE_ID / SGIS_SECRET_KEY,
# TAGO_API_KEY, VWORLD_API_KEY
```

Usage details will expand as the build proceeds.

---

## Repository layout (target)

```
rhythmscape/
├── src/rhythmscape/      # Python package (ingest / harmonize / indicators / interpret / render)
├── cities/               # per-city config (yaml)
├── prompts/              # theoretical prompt library (ko, en)
├── docs/                 # spec, evidence, api references
├── notebooks/            # demo + exploration
└── tests/                # pytest
```

---

## License

MIT (see [LICENSE](LICENSE)). External data sources carry their own
licenses — OSM (ODbL), KOSIS/SGIS (Korean public-data standard
licence), BIGKinds (KPF terms of use).

---

## Citation

```bibtex
@software{rhythmscape2026,
  author  = {Gimm, Dong-Wan},
  title   = {Rhythmscape: A Critical Urban Diagnostic Assistant},
  year    = {2026},
  url     = {https://github.com/thelevanter/rhythmscape}
}
```

---

## Author

Dong-Wan Gimm (@thelevanter)
Department of Sociology, Kyungnam University
Critical Geography · Urban Studies
