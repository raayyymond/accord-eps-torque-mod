---
name: reference_accord_cs_v_units_are_meters_per_second_not_kph
description: The `cs_v` field in the rlog-tools/analysis-2020accord telemetry caches (_cache_r9e, _cache_ra4, _cache_r85, etc.) is in METERS PER SECOND, not km/h, despite reading like a plausible km/h value at a glance (e.g. p50~8.3 looks like a plausible low urban km/h, but is actually 8.3 m/s = 29.9 km/h). Treating it as km/h silently produces speed thresholds/bins that are 3.6x too permissive -- caught this session after reporting a "low-speed <15kph = 61-65% of samples" figure that was actually "<15 m/s = <54 km/h". Verification method and the field to use instead documented below.
metadata:
  type: reference
---

# `cs_v` is m/s, not km/h -- a unit trap in this kit's telemetry caches, 2026-08-22

Found mid-`feel-impact` task while building the pre-registered `tq` discriminator (V103 `r9e` vs V104
`ra4`). I had used `cs_v` directly as if it were km/h (a `v<15` filter intending "under 15 km/h") in an
earlier report this same session, and it silently produced the wrong regime.

## The trap [EVIDENCE, cross-checked 2 independent ways]

`cs_v`'s numeric range LOOKS like a plausible km/h series at a glance -- p50~8.3, p90~26, max~31 on a
typical route -- exactly the kind of number an urban-driving low-speed channel would produce **if it
were km/h**. It is not. **`cs_v` is in meters per second.**

1. **Cross-field check**: `cs_v * 3.6` matches `ws_kph` (a separately, independently decoded wheel-speed
   CAN field, present in the same caches) at every percentile checked, to within ~0.1%: p50 29.92 vs
   29.94, p90 93.52 vs 93.52, p99 109.62 vs 109.62, max 113.32 vs 113.38 (route `ra4`).
2. **Cross-agent check**: using the corrected units (`cs_v*3.6`), engaged time above 80 km/h reproduced
   another agent's (`dose-highway`'s) INDEPENDENTLY-derived figures almost exactly -- 55.1s vs their
   reported 54.5s on `r9e` (1 contiguous episode both ways), 140.3s vs their reported 140.4s on `ra4` (3
   contiguous runs both ways). This cross-source agreement is what gave real confidence the fix was
   right, not just internally self-consistent.

## Consequence of getting this wrong [own error, corrected same session]

Reported "low-speed (`cs_v`<15) = 61-65% of engaged samples" on `r9e`/`r96`/`r97` earlier this session,
intending "under 15 km/h" (~9.3 mph, relevant to the operator's own named symptom window "low speed <10
mph"). **The actual filter applied was `cs_v < 15 m/s` = `<54 km/h`** -- a materially different, much
less selective threshold. Corrected figure, same routes, actually-under-15-km/h: **~15.7% (`ra4`) /
~16.4% (`r9e`)** of engaged time. The qualitative conclusion drawn from the wrong number ("not
highway-dominated, thousands of samples in the low-speed corner") happened to still hold at the
corrected threshold too, by luck of the underlying distribution -- **do not assume that will be true in
general; re-verify any prior `cs_v`-based km/h claim in this kit's record before relying on it.**

## What to use instead

- For a genuine km/h value: **`cs_v * 3.6`**, or use **`ws_kph`** directly (already in the right units,
  per-wheel array, shape `(N_slower_rate, 4)` -- note this is often a DIFFERENT length/rate than the main
  per-frame arrays like `tq`/`cs_v`/`t`, so it is not a drop-in same-length substitute without
  resampling; `cs_v*3.6` is the length-matched choice for per-frame work).
- `cs_v_raw` and `v_rear` are also in m/s (both track `cs_v` closely in these caches) -- same trap
  applies to them.

## Related
Found during the `tq` discriminator design for
[[reference_accord_v104_share_bound_and_tq_discriminator_results]] (same session). No prior memory
recorded this unit convention -- flagging as a first-instance trap for this kit's telemetry-cache work,
distinct from the firmware-disassembly traps in `firmware-decompile`'s skill file.
