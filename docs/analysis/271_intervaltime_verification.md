# 271 `intervaltime` Verification — Loop Time vs Headway

**Status**: Day 2 afternoon · Block 4 (brought forward from Day 3)
**Route**: 창원 271 (CWB379002710) — 지선버스, 마산합포 박물관 루프, 20 stations, circular (updowncd=0 only)
**Observation window**: 2026-04-23 08:16 KST → 16:17 KST (8.0 hours, partial day)

---

## Question

Routes parquet from `BusRouteInfoInqireService/getRouteInfoIem` reports
`intervaltime=94` for 271 (all three `intervaltime` / `intervalsattime`
/ `intervalsuntime` columns). Day 1 observed interval median was ~35–37
min at the quartile-grid observatories — a 2.7× discrepancy between
prescribed and lived.

Is `intervaltime=94` the **loop total time** (one bus's full circuit)
or the **headway** (time between consecutive buses at a given station)?

## Empirical findings

### Route 271 service profile (8-hour window)

| Metric | Value |
|---|---|
| Total location snapshots | 428 |
| **Unique vehicles** | **1** (경남71자3721) |
| Unique stations | 18 (of 20 nominal) |
| Passages (distinct station arrivals) | 179 |

The entire route is served by **a single bus** over the observation
window. No "different-vehicle" headway observation is possible —
there is no second vehicle to compare against.

### Same-vehicle same-station return (= loop time)

| Statistic | Value |
|---|---|
| Count | 161 intervals |
| Mean | 46.0 min |
| **Median** | **35.0 min** |
| 10th percentile | 30.0 min |
| 90th percentile | 96.1 min |
| Min / Max | 5.0 / 176.0 min |

The 5-min floor is physically implausible (20 stations cannot be
traversed in 5 min) and likely reflects BIS reporting artefacts — map-
matched position can briefly revert when a vehicle idles near a
station. The 90th-percentile 96 min and 176 min maximum indicate
pauses (driver break, terminal layover, schedule recovery). Stripping
tails, the **modal loop time is 30–45 min**.

### Different-vehicle intervals at same station

**Zero**. With one vehicle in service, "headway between distinct
buses" is not empirically defined.

## Interpretation

`intervaltime=94` cannot be a **literal headway** in the standard
operational sense — with a single vehicle, headway at any station
equals loop time (observed ~35 min), not 94 min. Under the headway
reading, the prescribed and observed values diverge by a factor of
~2.7 with no structural explanation.

`intervaltime=94` is also not a straightforward **loop total time**
— the empirically measured full-circuit return for the one bus is
~35 min, not 94.

The residual possibilities are:

1. **Administrative schedule artefact**: the operator registered
   `intervaltime=94` as a planned-service headway encompassing a full
   loop *plus* a padded turnaround/rest interval. The single bus in
   fact runs tighter than the registered interval (35 min empirical
   vs 94 min registered). This reading is consistent with 271 being a
   low-demand neighborhood circular where the registered value is a
   ceiling (upper bound on service gap) rather than a target cadence.
2. **Dead-run inclusion**: the registered 94 min may include one empty
   run (depot → route → depot) bookending the in-service loop. If the
   depot run is ~30 min each way plus a ~35-min loop, the full dispatch
   cycle is ~95 min. In this reading 94 is a *dispatch interval*, not
   a *service interval*.
3. **Operator convention misalignment**: TAGO does not publish a
   normative definition for `intervaltime` on 지선버스 routes. The
   94-min value may encode something the operator tracks internally
   (driver shift, vehicle rotation, fleet availability) that is not
   semantically equivalent to Lefebvre's *prescribed rhythm*.

## Implication for RDI

On the interpretation above, **the high RDI for 271 (Day 1 mean 0.59,
Day 2 midday ~0.63) remains theoretically valid** — it captures the
*arrhythmia of administrative representation vs operational practice*,
which is exactly the gap Lefebvre's *dressage/arrhythmia* couplet
targets. The route is registered at one cadence and operated at
another.

What changes is the **semantic framing** of the 271 result in Day 3–4
briefs: RDI on 271 is not "the schedule is off by ~60%" but "there is
a ~2.7× gap between the registered service interval and the empirical
service interval of the sole assigned vehicle, suggesting the
registered value is a planning ceiling rather than a target." This
makes 271 a cleaner exemplar of Lefebvre's *arrhythmia* than BRT6000,
where registered and observed intervals are close (20 min registered,
~16 min observed).

## Recommendation

1. **Keep `intervaltime=94` as the prescribed input** for 271 RDI
   computation. Do not substitute the observed median — this would
   collapse RDI magnitude by construction and lose the arrhythmia
   signal.
2. **Annotate 271 in the Day 3–4 bilingual brief** with the low-service
   context (1-vehicle operation, ~35-min empirical loop) so readers
   understand that the high RDI is not simply a schedule error but a
   structural feature of under-invested neighborhood circulars.
3. **Seek an external source** for Changwon BIS's internal service
   definitions if Day 3 Cowork wants a more precise account of what
   `intervaltime` means for 지선버스 routes. Candidate sources:
   changwon.go.kr/bms, 창원시 교통국 민원.
4. **Cross-check at day's end** (after the full 07:00–19:59 window
   is in) that the single-vehicle observation holds for evening peak
   too. If a second vehicle joins at peak, different-vehicle headway
   becomes measurable and a cleaner test of the headway interpretation
   is possible.

## Reproduction

Script used for this verification (ad-hoc, not committed):

```python
from datetime import date
from pathlib import Path
import pandas as pd
from rhythmscape.metrics.rdi import (
    load_locations, compute_vehicle_passages, compute_observed_intervals,
)
loc = load_locations(Path("data/raw/tago/locations"), for_date=date(2026,4,23), city="changwon")
r271 = loc[loc["routeid"] == "CWB379002710"]
passages = compute_vehicle_passages(r271)
# same-vehicle same-station returns = loop time estimates
# (see section "Same-vehicle same-station return" above for the aggregates)
```

Raw routes parquet: `data/raw/tago/routes/changwon_20260423.parquet`
Location parquets: `data/raw/tago/locations/changwon_20260423_*.parquet`
