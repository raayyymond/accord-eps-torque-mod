---
name: reference_accord_smooth_angle_gain_table_0xc6b64_opposite_roles
description: 🛑🛑 THE 2026-08-05 REJECTION IS ITSELF REFUTED, 2026-08-13 -- BOTH pillars are dead. "Problem 2, wrong variable" is FALSE (gp-0x6a10 IS absolute angle; the subtracted offset is HARD-CLAMPED to +/-13.0deg by cal 0xC633A=130, assembly-proven at 0x3fc36-0x3fc5a). "Problem 1, reach" is FALSE (engaged |angle| reaches 346-380deg over n=14,289 cc_lat frames; the FULL 1.2058x swing is exercised -- the 0-45deg band it was priced over was wrong). The table is now understood as a PARTIAL VARIABLE-RATIO-RACK COMPENSATION on the driver-torque term of the plant model, under-scaled ~3x in log terms. See [[reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists]] -- READ THAT FIRST; everything below is kept only as the historical record of a rejection that did not hold.
  ORIGINAL (SUPERSEDED) description: KILLED BY TEAM-LEAD CROSS-CHECK 2026-08-05 -- do not re-propose. Byte-dumped a smooth, gp-0x6a10-indexed 13-point LERP table (0xC6B64-0xC6B9A, never referenced by any build script) read by TWO live consumers in opposite roles (divisor->r26 weight; multiplier->gp-0x6ad4). Table itself and both consumer roles independently VERIFIED correct by team-lead's own byte read. But REJECTED as the near-centre mechanism on two counts: (1) magnitude is ~2 orders of magnitude too small -- only 3.8% gain change over the measured 0-45deg region (most of the table's 20.6% swing sits at 34-100deg, outside the measured band) against a measured ~3.2x amplitude swing; (2) WRONG VARIABLE -- gp-0x6a10 is an angle-TRACKING-ERROR (target-actual), not absolute steering position, and the data's conditioning variable (D1's "mid") is explicitly absolute position with movement (span) held separate. Standing bar for a replacement candidate: >2x gain change over 0-45deg of ABSOLUTE angle, reaching the aggregator. The team-lead is now recording the near-centre angle gradient as most likely a PLANT property (self-aligning torque / rack friction), not a firmware lever -- keep as a diagnostic fact, not a lever, unless a new candidate clears that bar.
metadata:
  type: reference
---

# `0xC6B64` table: one angle curve, two aggregator paths, opposite polarity (2026-08-05) -- REJECTED as mechanism, kept as structural fact

> # 🛑🛑 CORRECTION, 2026-08-13 -- THE REJECTION BELOW DID NOT HOLD. BOTH PILLARS ARE DEAD.
> - **"Problem 2 -- wrong variable, judged fatal" is FALSE.** `gp-0x6a10` is **absolute steering angle**:
>   `FUN_0003fc16` computes `|gp-0x69ca - clamp(gp-0x69e0+gp+0x641c, ±cal(0xC633A))|` and
>   **`0xC633A` = 130 counts = ±13.0°**, a HARD clamp (`0x3fc44`-`0x3fc5a`, `subr r0,r14`/`subr r0,r15`
>   are the negates). A correction bounded to ±13° cannot make the signal a tracking error.
>   `builds/v80_v107/build_v86_tva.py:141` reached the same conclusion independently from DATA (99.94 % match to
>   `|angle| ≥ 0.85°`).
> - **"Problem 1 -- reach" is FALSE.** It priced the table over an assumed 0-45° band. Actual engaged
>   `|angle|` reaches **346-380°** (n = 14,289 frames, `cc_lat` ≥ 0.5, routes r80/r81/r82) and the
>   **full 1.2058× swing is exercised**. ⚠ The 0-45° figure came from the WRONG ENGAGEMENT KEY --
>   `cs_eng` is all-zero on r80/r81; **use `cc_lat`**.
> - **The magnitude point survives only against the near-centre hypothesis it was aimed at**, not against
>   the rack-ratio reading: the table is a **partial variable-ratio-rack compensation** on the
>   driver-torque term of the plant model, under-scaled ~3× in log terms.
> - 🛑 **Consumer 2's role here is stated correctly but its SIGNIFICANCE was missed** -- see
>   [[reference_accord_rack_ratio_c6b64_is_absolute_angle_and_no_notch_exists]]. **Read that first.**
> Everything below is retained as the historical record of a rejection that did not hold.

**🛑 Verdict, team-lead 2026-08-05, after independently re-byte-reading the whole table and re-deriving
the magnitude: NOT the mechanism. Do not re-propose without clearing the bar stated in the description
above.** [SUPERSEDED -- see the correction block above.] The table's existence, byte values, virginity (0 of 65 build images write it), and both
consumer roles are all CONFIRMED correct -- this is a real structural fact, just not a large enough or
correctly-keyed one. Read the two problems below before citing this table in any future near-centre work.

Follow-up to the retracted "5-degree window" hunt. Team-lead's revised target: a SMOOTH angle-indexed
gain/surface (not a threshold), live at creep, reaching the aggregator, acting with OPPOSITE sign on two
different loops. This closes F4's (sibling agent) second flagged gap in `a`'s (`gp-0x69a4`, r26's
relative weight) producer chain -- the `tp+0x7b66-0x7b98` boost-curve table -- and finds it is shared
with a second, previously-traced live function.

## The table [EVIDENCE, byte-read, cross-checked against BOTH consumers' decompile anchors]

`tp+0x7b64` (count=13, u16) through `tp+0x7b9a` = **`0xC6B64-0xC6B9A`**. Zero mentions in any
`build_v*_tva.py` (genuinely unexplored, not RULE-4-style referenced-but-untested). Struct format
matches the established count-dependent LERP convention exactly (verified: my independently-computed
X[12]/Y[12] byte-match the decompile's own `tp+0x7b7e`/`tp+0x7b98` anchor reads precisely).
```
X (gp-0x6a10 counts, ASSUMED 0.1 deg/count per gp-0x69ca's confirmed scale -- NOT independently
   re-verified for gp-0x6a10 specifically this session):
  0   340   640   850  1000  1200  1400  1576  1736  1916  2084  2280  4776
  (deg: 0  34.0  64.0  85.0 100.0 120.0 140.0 157.6 173.6 191.6 208.4 228.0 477.6)
Y:  899   908   981  1078  1083  1084  1084  1084  1084  1084  1084  1084  1084
```
**Smooth, monotonic rise 899->1084 (~20%) over roughly the first 100 degrees of index, then flat.** Not
a step, not a deadband -- a genuine gradient, centred at the origin.

## Consumer 1 (SOLID) -- feeds r26's own weight, DIVISOR role

Inside `FUN_000389ec` (the 9-slot slew-target producer traced in
[[reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected]]):
```
uVar48 = LERP(gp-0x6a10, this table)     [if gp-0x6a10 < 10001, else flat 1024]
term = ((scale_A * scale_B >> 7) << 10) / uVar48        # uVar48 is a DIVISOR
```
`term` feeds the rate-limited slot-fill mechanism -> `gp-0x6442`-family -> `FUN_000352b4`'s own
interpolation -> `gp-0x69a4` ("a") -> **r26**, one of the 11 confirmed `gp-0x6b98` summands (per
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]]). Being a DIVISOR: near-centre
(LERP=899, smallest) -> `term` LARGEST; away from centre (LERP=1084) -> `term` SMALLEST. **Amplifies
r26's contribution near centre, attenuates it away from centre.**

## Consumer 2 (THINNER, same table) -- feeds toward gp-0x6ad4, MULTIPLIER role

Inside `FUN_0003b8f6` (the mostly-dead-outputs PI-shaped function from
[[reference_accord_angle_position_scale_0p1_deg_per_count_settled]]'s "one thin survivor"):
```
uVar17 = LERP(gp-0x6a10, THE SAME table)
fVar18 = fVar13 * uVar17 * 0.0009765625 + fVar18         # uVar17 is a MULTIPLIER
```
Being a MULTIPLIER: near-centre (899, smallest) -> term SMALLEST; away from centre (1084) -> term
LARGEST. **The OPPOSITE sign relationship from Consumer 1, on the exact same underlying curve.** Reaches
`gp-0x6ad4` via the already-traced `gp-0x6bfc->gp-0x6bfe->FUN_00038148->gp-0x6b70->gp-0x6ad6->
FUN_0003a382` chain -- still not sized against `FUN_0003b8f6`'s other (feedback-dominated) terms.

## 🛑 REJECTED — team-lead's independent cross-check, verbatim reasoning

**Team-lead re-byte-read the table independently and got the same values** (their read: `Y[3]=1060`
where mine read `1078` -- immaterial, one halfword transcription difference, does not change the shape
or verdict). Confirmed: byte-identical stock and V72, written by 0 of 65 images, not in
`[0xC5000,0xC5FFC)`. **The table and both consumer roles are real.** Two independent reasons it is still
not the mechanism:

**Problem 1 — magnitude ~2 orders of magnitude short where the data lives.** The measured effect (D1/D3)
spans 0-45 deg, where the ratchet climbs ~3.2x. Priced through the Consumer-1 divisor role at the
assumed 0.1 deg/count:
```
   0 deg -> Y=899.0   rel gain 1.0000
  10 deg -> Y=901.6   rel gain 0.9971
  22 deg -> Y=904.8   rel gain 0.9936
  34 deg -> Y=908.0   rel gain 0.9901
  45 deg -> Y=934.8   rel gain 0.9617
 100 deg -> Y=1083    rel gain 0.8301
```
**Over the ENTIRE measured 0-45 deg region the gain moves only 3.8%** -- most of the table's 20.6% total
swing sits between 34 and 100 deg, OUTSIDE where the data shows the gradient. Explaining a 3.2x amplitude
swing from a 3.8% gain change would require the loop sitting within ~4% of a describing-function
stability boundary on all six measured arms simultaneously -- not credible as a general mechanism.

**Problem 2 — wrong variable, judged fatal.** `gp-0x6a10` is an angle-TRACKING-ERROR (target minus
actual, built as `gp-0x69ca - slew(...)` per
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]]). D1's decomposition is
explicitly `span` (how far the wheel moved) × `mid` (WHERE on the angle axis it sat) -- the measured
conditional is on **absolute steering position**, holding movement fixed. A tracking error is small at
steady state REGARDLESS of absolute angle, driven by how hard the controller is working, not by rack
position. Unless `gp-0x6a10` happens to correlate strongly with absolute position (not shown, not
assumed safe), it is not the variable the data is conditioned on.

**Standing bar for any replacement candidate**: a gain that varies by more than ~2x over 0-45 deg of
ABSOLUTE steering angle (not a derived error term), reaching the aggregator. Nothing found in either
round of this hunt comes close. **Team-lead is recording the near-centre angle-position gradient as most
likely a PLANT property** (self-aligning torque / rack friction / assist level varying with rack
position) rather than a firmware lever, and keeping the angle-axis SEPARATION itself (the two modes
genuinely differ on `mid`, nothing else in either battery separates them) as a diagnostic fact.

## What this is and is not (superseded by the rejection above, kept for the record)

IS: one real, smooth, byte-dumped angle-indexed curve, reaching the aggregator through TWO
independently-live paths in mathematically opposite roles on the same input -- verified correct, closes
F4's open producer-chain gap, but too small and keyed on the wrong variable to be the near-centre
mechanism (see rejection above).

IS NOT: proof that r26 and gp-0x6ad4/resonance carry the two different measured frequencies (ratchet
vs grind #1) -- that is a frequency-content attribution outside what firmware structure alone can settle.
Also not independently confirmed: `gp-0x6a10` sharing the exact `gp-0x69ca` scale; a creep-specific gate
on this particular sub-computation (the parent apparatus runs on live task 1 generally, per
`get_function_callers` on the sibling `FUN_0003b8f6` -> `FUN_0002214a`, but not re-checked for THIS
computation specifically this round).

## Related
[[reference_accord_gp69a4_slot_fill_slew_mechanism_and_0xc6564_link_corrected]] -- Consumer 1's parent
mechanism (the 9-slot slew, previously traced without this table's content).
[[reference_accord_angle_position_scale_0p1_deg_per_count_settled]] -- source of Consumer 2 (the
FUN_0003b8f6 thin survivor) and the angle scale this table's X-axis is interpreted against.
[[reference_accord_near_centre_structure_hunt_angle_tracking_chain_found]] -- the session's earlier
work on gp-0x6a10's OTHER (boost-lane, flat-zero-at-creep) consumer.
