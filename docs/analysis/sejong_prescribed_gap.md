# Sejong Prescribed Interval Gap — TAGO Data Absence

**Discovered**: 2026-04-23 Day 2 afternoon (Block 1 RDI generalization)
**Affects**: Sejong (cityCode 12) — all three selected routes
**Status**: Blocking for RDI v0 on Sejong. 3-city prefigure on 18:00 preview.

---

## Finding

TAGO `BusRouteInfoInqireService / getRouteInfoIem` returns the following
fields for every Sejong route (verified 14:19 KST):

```
routeid, routeno, routetp, startnodenm, endnodenm,
startvehicletime, endvehicletime
```

It **omits** `intervaltime`, `intervalsattime`, and `intervalsuntime` —
the three headway fields that the Lefebvrean Prescribed layer requires.

By contrast, the other three cities publish headway fields:

| City | intervaltime (weekday) | intervalsattime | intervalsuntime |
|---|---|---|---|
| Changwon | 94 / 20 / 45 | 94 / 22 / 45 | 94 / 31 / 49 |
| Seongnam Bundang | 15 / 10 / 16 | 35 / 30 / 32 | 35 / 30 / 32 |
| Busan Yeongdo | 10 / 11 / 10 | **NaN** | **NaN** |
| **Sejong** | **NaN / NaN / NaN** | **NaN** | **NaN** |

Yeongdo exposes weekday only. Sejong exposes nothing.

## Cause (hypothesis)

Sejong BIS does not publish headway metadata to the TAGO federation.
The Sejong routes appear in the `getRouteNoList` dump and their
`route_stations` / `location` streams are live — operational data is
available, only the *prescribed schedule* side of the Lefebvre triad
is missing from TAGO for this city.

This is an *operator-side* gap in the data source, not a code defect
in the Rhythmscape pipeline. The ingest layer correctly pulls every
field TAGO returns; TAGO itself returns nothing for these keys.

## RDI v0 impact

`rdi_sejong_20260423.parquet` has **0 rows** after Block 1 generalization.
Reason: `aggregate_rdi` joins observed intervals to prescribed on
(route_id, daytype). With all prescribed values NaN, the join drops
every row via `dropna(subset=["prescribed_interval"])`.

Sejong therefore cannot participate in the 18:00 KST 4-city RDI preview.
Other three cities (Changwon, Seongnam, Yeongdo) compute normally.

## Options for Sejong Prescribed recovery (Cowork decision — Day 3)

1. **External source injection**: Sejong BIS public website
   (www.sejongbis.kr) publishes a 배차표 (dispatch schedule) for each
   route. Scrape once per day, inject as a manual supplement alongside
   TAGO prescribed for the other cities. Adds ~30–60 min of work.
2. **Observed-median proxy** (last resort): use the observed-interval
   median as a stand-in for prescribed. This inverts the semantic of
   RDI — magnitude collapses toward 0 by construction — and should be
   declared with a separate column `prescribed_source` so downstream
   analysis does not conflate it with TAGO-sourced prescribed.
3. **Drop Sejong from RDI analysis**: keep Sejong in locations/observed
   tables for spatial and descriptive statistics, but exclude from any
   prescribed-vs-lived comparison. The 4-city typology survives with
   "Sejong has no public prescribed" as a finding in itself — possibly
   theoretically interesting (a 2010s new town that does not publicly
   commit to a schedule).

## Yeongdo weekend gap (minor)

Yeongdo publishes weekday `intervaltime` but returns NaN for
`intervalsattime` and `intervalsuntime`. For weekday-only analysis
this is non-blocking. Day 3–4 weekend comparison would require the
same external-source injection pattern as Sejong.

## Archive

- Routes raw parquet: `data/raw/tago/routes/sejong_20260423.parquet`
- Full raw response field list verified via live API call at 14:19 KST
  (no cached response used).
- Locations data healthy: 419 rows / 10 vehicles / 38 stations across
  3 Sejong routes at the time of this write-up.
