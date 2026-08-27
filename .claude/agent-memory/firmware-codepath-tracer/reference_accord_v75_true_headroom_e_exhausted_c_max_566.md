---
name: reference_accord_v75_true_headroom_e_exhausted_c_max_566
description: CORRECTS reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound.md's rung recommendations -- a full-grid binary search (not hand-picked corners) against builds/v50_v79/build_v74_tva.py's own damper_authority()/assert_no_clip() shows FactorE has ZERO remaining headroom on mode 26 (V74 already spent it -- 5 grid cells sit exactly at the 512 ceiling floor today) and FactorC's C_Y0 safe max is 566, not 908 or higher -- both my original Rung A/B and team-lead's C_Y0->908 candidate introduce real new clipping when checked against the FULL (speed,rate) grid instead of a single hand-picked corner.
metadata:
  type: reference
---

Task: team-lead adversarially challenged my first V75 headroom report (rightly) -- caught that I'd used
`C_Y0` (429, the creep value) instead of `C_Y3` (908, the true grid max, reached at speed>=8960/140km/h)
in the no-clip check, and proposed `C_Y0->908` as a fix delivering 2.12x dose at "zero clipping." I
adversarially checked THEIR fix too, using `builds/v50_v79/build_v74_tva.py`'s own exact functions over the full
99k-point grid it uses (`v in range(0,14001,32), r in range(0,4501,20)`), and **neither candidate
survives the full sweep.**

## The lesson, stated first because it is the durable part
**Any single hand-picked-corner formula for a 2-factor multiplicative LERP product
(`dose=(C(speed)*E(rate))>>10`) is insufficient** -- both my original "creep corner only" check and
team-lead's "global peak/ceiling ratio" check independently missed real violations. **The only trustworthy
method is a full grid sweep (or binary search driven by one) reproducing the actual firmware LERP+clamp,
exactly as `builds/v50_v79/build_v74_tva.py`'s own `assert_no_clip()` already does.** Do not shortcut this for any future
lever on this table family.

## The actual numbers, mode 26, V74 baseline [EVIDENCE, binary search over the exact grid, two rules agree]
```
TRUE safe max C_Y0 (E untouched, zero new clip anywhere): 566   (V74 today: 429).  dose@rate99 = 66 (1.32x)
TRUE safe max E_Y1=Y2 (C untouched, zero new clip anywhere): 539  == V74's CURRENT value. ZERO headroom.
```
Confirmed under BOTH a strict rule (`now>was AND now>512`, forbidding any movement of an already-saturating
cell) and a relaxed rule (`was<=512 AND now>512`, only forbidding NEW crossings, exempting nudges inside
an already-saturating region) -- **identical answer both ways.** For `E`, the relaxed-rule binding
constraint is FIVE grid cells sitting at EXACTLY 512 today (119-133 km/h, 594-671 deg/s) -- any positive
increment to `E_Y1` immediately pushes one of them to 513. **V74 already spent 100% of the rate-axis
margin; this is not a small headroom, it is none.**

## Why each hand-picked-corner check failed
- **My original check** (`(cy[2]*ey[3])>>10 <= floor`, `cy[2]=429`) only validated the newly-opened creep
  corner. It never checked what raising `E_Y1` does at `C_Y3=908` (highway speed, unchanged) -- because
  `FactorE` is rate-only and `FactorC` is speed-only, any `E` increase applies at EVERY speed
  simultaneously, including the untouched highway corner where V74 already sits at 477/512 = 93% of
  margin. My "Rung A" (`E_Y1,Y2->927`) clips at **45.62%** of the grid (worst: 140km/h @ 85 deg/s, an
  ordinary input, was=477->now=821). My "Rung B" clips at **58.24%**. BOTH RETRACTED.
- **Team-lead's check** (global surface peak / ceiling, unchanged before/after) is true in the sense that
  the VALUE 821 already existed somewhere on V74's surface (the far highway corner) -- but
  `assert_no_clip()` doesn't check "does the peak value exist somewhere," it checks "did the surface rise
  AT THIS LOCATION." `C_Y0->908` makes the ENTIRE creep band (0-2240 raw = 0-35km/h, LERP clamps flat
  below `X[0]`) read 908, and `E_Y3=927` is reachable there too -- `(908*927)>>10=821>512`, a NEW clip at
  creep+extreme-rate (a plausible panic/fast correction while nearly stationary), where V74 today only
  reaches 388. **8.27% of the grid clips**, not 0.00%. The "C_Y0=908+E_Y1->692" candidate clips **56.03%**.

## Physical framing that resolves the disagreement
A clip at 140km/h+848deg/s (both extreme simultaneously, plausibly unreachable) and a clip at creep speed
+848deg/s (a fast steering input while nearly stationary -- not equally implausible) are NOT the same risk
even though the numeric ceiling value is identical. GATE 2's actual concern (hard clipping inside a
feedback loop AT THE OPERATING REGION of the resonance) is about WHERE new saturation appears, not merely
whether the surface's global peak moves.

## Consequence for the ladder
Only `C_Y0: 429->566` (mode 26; other modes need their OWN binary search, using their own `C_Y3`/`E_Y3`)
is verified safe -- **1.32x dose at the creep operating point (66 vs 50 at rate 99; 87 vs 66 at rate
127)**, one cell per mode, byte address `0xD77DA` on mode 26. `E` is untouched because it CANNOT be
touched further under this ceiling. The friction lane (`0xC407E`, independent table) is unaffected by any
of this and still has its own ~17-20% headroom.

## Open — the ceiling table `0xC77A0` is now the ONLY path past 1.32x
With `E` structurally exhausted, `0xC77A0`'s static floor (512, per `ceiling_floor()`'s own `ys[0]`-only
read) is the SOLE blocking constraint on any further dose. See
[[reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin]] -- whether `gp-0x6ac2` genuinely provides
more real-world ceiling than the conservative static 512 during back-drive events is UNRESOLVED and
[BELIEF]; team-lead has a dedicated agent tracing it. Raising the ceiling table's own `Y[0]` is a
qualitatively different edit (relaxing a safety clamp, not a gain) and would need the SAME full-grid
binary-search treatment before trusting any number for it -- not yet done.

## Related
[[reference_accord_v75_ceiling_c77a0_noclip_asymmetry_and_aggregator_inclusive_bound]] -- supersedes its
Rung A/B recommendations specifically; the ceiling-table quantification (`0xC77A0`, `X=[300,800]
Y=[512,1024]`) and the aggregator-inclusive-boundary finding in that memory are UNAFFECTED and still stand.
[[reference_accord_gp6ac2_is_backdrive_rate_not_gp6ac0_twin]] -- the open item this correction depends on.
