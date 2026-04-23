# RDI Day-2 Preview — 창원 3노선

**Source**: `data/processed/tago/rdi_20260423.parquet` · **Generated**: 2026-04-23T11:29:24+09:00

**Observation window** (Asia/Seoul): 2026-04-23 08:00 → 2026-04-23 11:00

**Total bins**: 1006 · **Flagged**: 57 (5.67% · spec §6 target 5–15%)

## Per-route summary

| 노선 | bins | mean mag | median mag | max mag | mean var | dressage | vitality |
|---|---:|---:|---:|---:|---:|---:|---:|
| 271 (`CWB379002710`) | 46 | 0.592 | 0.622 | 0.936 | 0.456 | 0 | 2 |
| 710 (`CWB379007100`) | 510 | 0.415 | 0.417 | 1.400 | 0.333 | 7 | 0 |
| BRT6000 (`CWB379060000`) | 450 | 0.258 | 0.200 | 3.949 | 1.455 | 47 | 1 |

## Reading

- `mean mag` is the mean of |observed − prescribed| / prescribed per bin. 0 = *eurhythmia* (schedule honored); ≥ 1 = observed headway at least doubled or halved vs. prescribed.
- `mean var` is the mean of population stdev (ddof=0) of observed intervals within each bin. 0 when a bin holds a single observation.
- `dressage` / `vitality` are post-hoc interpretive flags, not judgments — see `critique_flag_spec.md` §2 for interrogative semantics.

## Observed triplet (Day-2 reading, to be revised by Cowork)

- **BRT6000 carries 47/54 of all `dressage_alert`.** The route with the tightest adherence to prescribed rhythm — empirical coherence with the 'automobility capture' framing in `route_selection_rationale.md` §3 (Urry 2004; Sheller & Urry 2000).
- **271 carries 2/3 of all `vitality_query`.** Sparse service (94-min prescribed, ~37-min observed median) yields both high magnitude and high variance — consistent with the 'circular eurhythmia baseline' framing, now appearing as *arrhythmia* at the extremes of its sparse window.
- **710 falls between** — 7 dressage, 0 vitality. Its mid-magnitude regime (0.42 mean) matches the framing of 광역 부재의 증상적 대체: observed service denser than the prescribed 45-min headway, but without the tight BRT-style regularity.

## Limits of this reading

- Window is ~3 hours (morning only). Peak vs off-peak separation is deferred to Day 3+.
- Bin width was empirically raised from 5 min (handoff §B) to 30 min because headways (20–94 min) exceed 5-min bin widths, collapsing variance to 0 everywhere. Revisit when sub-15-min-headway routes are added.
- Dressage persistence was set to 1 bin instead of the spec's 5 ticks. Rationale: a 30-min bin already averages multiple vehicle passages and is structurally non-fluke by construction. Persistence ≥ 2 bins with a full-day window should be revisited Day 3.
- Quartile-grid observatories are used as a *contrastive baseline* (see `sentinel_rationale.md` §3). Thematic observatories (transfer hubs, inflection points) are not yet active.

## Evidence artefacts

- `docs/evidence/rdi_day2_preview_20260423.png`
- `data/processed/tago/rdi_20260423.parquet`
- `data/processed/tago/critique_flags_20260423.parquet`
- `config/critique_flag.yaml`
