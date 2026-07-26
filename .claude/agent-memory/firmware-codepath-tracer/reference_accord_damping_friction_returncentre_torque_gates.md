---
name: reference-accord-damping-friction-returncentre-torque-gates
description: Byte-dumped LERP tables for FUN_00034350 (damping) and FUN_00036c12 (friction), both mode-10, keyed on gp-0x6a5e AVG driver torque -- damping rises 0 to 877(Q10) with torque, friction falls in magnitude from -9830 to -1966 (opposite direction). Also corrects FUN_00036388 (return-centre): its gp-0x6a5e threshold cal is 0 (vacuous), NOT a real hands-on/off gate. Flags an unresolved 3-way contradiction on gp-0x6abe's live/pinned state that gates the damping term's reachability.
metadata:
  type: reference
---

Found 2026-07-20/21 tracing hands-on/off discriminators in the torque command path for team-lead's V38
21Hz hands-off-only vibration investigation. Scope: `FUN_00034350` (damping, `gp-0x6bd0`),
`FUN_00036c12` (friction, `gp-0x6b26`), `FUN_00036388` (return-centre, `gp-0x6b62`) — all mode-10
(this car's confirmed assist-mode index, per existing `eps_lkas_chain_model.py` notes).

## Damping table `0xC9E9C` (mode 10, resolved via pointer array to `0xD27BC`) [VERIFIED byte dump]

Keyed DIRECTLY on `gp-0x6a5e` (AVG voted driver column torque), gate: `gp-0x6a5e <= 0x7d00(32000) AND
gp-0x67f4==1` (plausibility flag), else flat unity (1024).
```
X = (2240, 3840, 5120, 8960)
Y = (0, 235, 430, 877)          -- Q10, RISING with driver torque
```
Zero at `gp-0x6a5e<=2240`, growing to `877/1024≈0.856` by `gp-0x6a5e>=8960`. This is the ONE table found
this session whose shape matches "term requires driver torque to activate" — i.e. more damping-term
contribution when hands are on, none when hands are off. **See the open contradiction below before
treating this as reachable.**

Sibling table `0xC9CCC` (mode 10, resolved to `0xD2738`) is keyed on `gp-0x698a` (NOT `gp-0x6a5e` —
corrects the `eps_lkas_chain_model.py` `FUN_00034350` docstring, which mislabeled this table "AVG
torque, plausibility-gated"). Its Y values are **flat 1024 at all 4 breakpoints (205,1331,2355,3072)** —
a structural no-op regardless of what `gp-0x698a` represents. `gp-0x698a`'s identity was not traced.

## ⚠ UNRESOLVED — gp-0x6abe live/pinned state, 3-way disagreement, do not cite the damping finding without resolving this first

The damping term's OUTER gate is `|gp-0x6abe| <= ~12936` (code-immediate-derived) combined with a final
`if gp-0x6abe>0: negate`. Whether this outer gate is ever satisfied in normal driving depends entirely
on whether `gp-0x6abe` carries a live signed value or is pinned to a sentinel:

1. `reference_accord_fun34350_damping_term_live_and_gated.md` (this same memory dir): claims `gp-0x6abe`
   is **LIVE in normal driving**, pinned to `32767` only in abnormal (rate-saturating) conditions.
2. `eps_lkas_chain_model.py`'s `FUN_00034350` docstring (`analysis-2020accord/eps_lkas_chain_model.py`,
   `assist_shaping_lanes()`): claims the **OPPOSITE** — pinned in normal driving, live only in abnormal.
3. My own quick re-trace this session of `FUN_00041464` (`gp-0x6abe`'s sole producer,
   `0x415a0-0x41a30`ish) found the real gating structure is more complex than either summary: an OUTER
   selector `r6` (set at `0x415ca` via `setfnc`, based on whether `|gp-0x4f50|>=13001`, i.e. genuinely
   "rate abnormal") picks between TWO nearly-identical guarded blocks (`0x4169c` region vs `0x41902`
   region), each of which independently checks a debug/factory CRC magic constant
   (`0x49d6b173` + a companion byte at `tp+0x50ed`/`tp+0x50ee` == `0xE9`) before computing a "live" value
   — and in THIS ROM (`tp+0x7134`=1000, `tp+0x748e`=0, both identity constants per prior sessions), the
   "live" computation reduces to the SAME `32767` the pin path writes anyway. I traced far enough to see
   both CRC-magic-fails else-branches pin to `0x7fff`, but did **not** finish confirming there is no live
   path anywhere in shipped (non-debug) firmware, and I may have conflated `gp-0x6abe`
   (`FUN_00034350`'s actual dependency) with an adjacent sibling write to `gp-0x6abc` at `0x41978` in the
   same function — these are two different variables four bytes apart and easy to mix up under time
   pressure.

**Action needed before anyone builds on the damping-table finding**: a clean, dedicated re-trace of
`FUN_00041464` start to finish (it's not huge, roughly `0x41464-0x41a30`), pinning down (a) which of
`gp-0x6abe`/`gp-0x6abc` is written where, (b) whether the CRC-magic condition can EVER be true outside a
debug/factory build, and (c) whether `gp-0x6abe` genuinely varies sign in shipped firmware or is a
constant `32767`. If it's a constant, `FUN_00034350`'s damping term is structurally dead (its outer gate
`<=12936` would never pass) regardless of the `0xC9E9C` table's shape, and the "reduces loop gain when
driver torque is high" hope for this lane collapses.

## Friction table `0xCBE74` (mode 10, resolved to `0xD2A44`) [VERIFIED byte dump]

Keyed DIRECTLY on `gp-0x6a5e`, gate: `gp-0x671a < 0xff AND gp-0x67f4==1`, sub-selected by
`gp-0x671a < cal(tp+0x74fd=0xC64FD)=5` (else flat `tp+0x740a`; fully invalid path uses flat `tp+0x740c`).
Only 3 points (not 4 — smaller struct, count=3):
```
X = (0, 1280, 5760)
Y = (-9830, -5734, -1966)      -- all negative, RISING (less negative) with driver torque
```
Magnitude is LARGEST (most negative, ~9830) at `gp-0x6a5e≈0` (hands-off) and shrinks ~5x by
`gp-0x6a5e>=5760`. **Opposite direction from the damping table** — this is a term that's BIGGEST
hands-off, not smallest. Downstream it's scaled by `gp-0x6c2c` (an angle/rate-like signal, exact
identity not traced this session) and IIR-filtered into `gp-0x6b26`. Reads structurally like static-
friction compensation (motor fights more friction when the driver isn't helping) rather than a
resonance-loop-gain control — real magnitude difference between hands-on/off, but the WRONG direction
for a "loop gain drops when driver helps" hypothesis; if anything it argues for MORE total commanded
torque hands-off, which is directionally consistent with more energy available for a hands-off-only
oscillation, not less.

## FUN_00036388 (return-centre) — correction: NOT a real hands-on/off gate [VERIFIED]

First-pass reading of the compound accumulator gate looked like it required `gp-0x6a5e >= threshold`.
**Byte-read the actual cal: `0xC62E2 = 0`.** Since `gp-0x6a5e` is unsigned, `gp-0x6a5e >= 0` is always
true — this AND-term is vacuous. The real live constraint on the special increment path is
`gp-0x6ac0 < cal(0xC620C)=200` (motor electrical rate must be very low) AND `gp-0x67fe==2` (HOLDING
substate specifically). **Correcting my own first-pass read before it got reported as a finding** — do
not treat return-centre as driver-torque-gated. Also confirmed in passing: hysteresis window
`tp+0x718a` (`0xC618A`) = 1024.

## Related
[[reference-accord-fun34350-damping-term-live-and-gated]] — one side of the gp-0x6abe contradiction
[[reference-accord-gp67ac-aggregator-lane-suppression-gate]] — the aggregator gate that can drop ALL of
  these lanes (damping/friction/return-centre included) wholesale, found the same session
[[reference-accord-fun3a382-resonance-lane-unfiltered-correction]] — sibling lane, same investigation
