---
name: reference_accord_v276_crossover_threshold_and_packer_rectifies_sign
description: The raw-count crossover threshold (E<0 requires feedback_lag_out > 32*setpoint_ceiling) for FUN_00028ea6's LKAS rate PID, tabulated across candidate reference-scale factors K with the ratio-preserving 0xC62E6 value for each -- resolves a team discrepancy about absolute deg/s figures (both were right, just different points in an unclosed unit-conversion chain). Also documents that the CAN-427 packer template (0x55df0-0x55e16) RECTIFIES its source cell via an abs() call before scaling, so it cannot currently carry a sign bit -- any design wanting sign(E) on the wire needs the packer restructured, not just its two edit sites changed.
metadata:
  type: reference
---

# V276 crossover threshold in raw counts, and why the packer can't carry sign(E) yet

Traced 2026-09-01, from the V276 image (`_v276_V276-V268BASE-REFERENCE6X.MAP.FEEDBACK_plain_image.bin`)
plus fresh disassembly of `code.bin` @0x55df0-0x55e16. Extends
[[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]] and
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]].

## The mechanism this supports (team-lead's synthesis, corroborated)
`E = 32*setpoint - feedback_lag_out`. `E<0` (the loop's damping/negative-feedback region) requires
`feedback_lag_out > 32*setpoint_ceiling`. V276 scaled BOTH the setpoint (via `0xC9A88`) and the feedback
clamp (`0xC62E6`) by the same K=6, preserving Honda's ratio exactly — but the PHYSICALLY ACHIEVABLE
`feedback_lag_out` (set by real rack/sensor dynamics, untouched by calibration) did not scale. So the
crossover threshold moved 6x in absolute terms while what the car can actually deliver stayed put --
pushing the loop almost entirely into P-saturated, sign(error)-relay behaviour.

## Crossover threshold, per live slot (EVIDENCE, read from the V276 image, `0xC9A88` map)

| K | slot 1/0/3/4/6/7 (ceil 172) threshold | slot 8/9 (ceil 188) threshold | required `0xC62E6` |
|---|---|---|---|
| 1 (stock) | 5504 | 6016 | 7680 |
| 1.5 | 8256 | 9024 | 11520 |
| 2 | 11008 | 12032 | 15360 |
| 2.5 | 13760 | 15040 | 19200 |
| 3 | 16512 | 18048 | 23040 |
| 4 | 22016 | 24064 | 30720 |
| 6 (current V276) | 33024 | 36096 | 46080 |

`threshold / required_0xC62E6` is a CONSTANT 0.7167 at every K by construction (both scale together to
preserve Honda's 1.395 setpoint:feedback ratio). This is why two team members quoting different absolute
deg/s crossover figures were BOTH right — the disagreement was in where the disputed ~8-count/deg-s
sensor-scale factor got applied in each one's derivation, not in the underlying facts. This table needs
no such factor.

**Physical sanity cross-check (BELIEF — uses the V276 build docstring's own 27 deg/s median-achieved-rate
and "31.1 deg/s at the 7680 clamp" figures to back out an implied 246.9 raw-per-deg/s)**: median achieved
rate ≈ 6668 raw. Crosses the K=1 threshold (5504) but sits below K=1.5's (8256) — consistent with "stock
crosses over routinely; K>=1.5 pushes the crossover mostly out of median reach."

**P-saturation duty is NOT a useful axis to pick K by**: structurally (fb=0, idx=240, matching the V276
build script's own bound), P already saturates for K>1.03 in every live slot — stock (K=1) already sits
at 97.4-109.7% of its own clamp. Nearly every candidate K looks "saturated" by this metric; the crossover
threshold above is the real discriminator.

**Recommendation (offered, not built): K=2**, threshold 11008/12032, required `0xC62E6`=15360. Clears the
median-achieved-rate crossover with margin while giving 2x stock reference (vs 6x today). K=1.5 is the
more conservative fallback. Neither touches `0xC61B4`(3072)/`0xC6CD0`(5346)/the assist-map Y-ceiling —
zero peak-torque cost, same shape of fix as [[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]].

## The CAN-427 packer RECTIFIES — cannot carry sign(E) without restructuring (EVIDENCE)

Disassembled the packer template fresh, `0x55df0-0x55e16` (`code.bin`, stock — structurally identical to
what V273/V276/V277 edit in place):
```
55df0: ld.h  <disp>[gp], r6      ; load ONE signed 16-bit source cell            <- the only edit site
55df4: jarl  0x49a5a, lp         ; r10 = abs(r6)                                  <-- RECTIFIES, kills sign
55df8: mov   r10, r6
55dfa: ori   0xffff, r0, r7
55dfe: jarl  0x49a78, lp         ; r10 = min(r6, 0xFFFF)
55e02: andi  0xffff, r10, r6
55e06: mul   0x5, r6, r0         ; *5
55e0a: movea 0x3ff, r0, r8       ; ceiling 1023
55e0e: mov   0x0, r7             ; floor (this + the sar imm are the two edit sites V276 used)
55e10: sar   0x3, r6             ; >> imm  (cal-configurable shift)
55e12: jarl  0x49a90, lp         ; r10 = clamp(r6, r7, r8)  -> [0,1023]
55e16: andi  0xffff, r10, r6     ; final wire value
55e1a: jarl  0x21864, lp         ; hand off to CAN frame builder
```
This pipeline carries exactly ONE rectified magnitude into the 10-bit field. `sign(E)` (from `gp-0x6cf8`,
32-bit, already published every tick per [[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]])
and `P-at-clamp` (compare `|gp-0x6b32|` to `0xC61BC`, also already published) are cheap to SOURCE but
need the packer RESTRUCTURED (new comparison logic replacing the abs/min/mul/clamp chain), not just its
two existing edit sites (source disp @0x55df2, sar-imm @0x55e10, floor @0x55e0e) changed. Proposed layout:
bit9=sign(E), bit8=P-at-clamp, bits0-7=selector(4)+coarse demand(4). `FUN_00055d80`'s r6/r7/r8 scratch
(saved, never restored, per [[reference-accord-clamp-helpers-and-packer-scratch]]) gives register room.
**This is a CODE change, not cal-only — needs GATE 1/GATE 2 before anyone cuts it**, unlike the
reference-scale/clamp levers this note otherwise supports.

## Related
[[reference_accord_c61be_sum_clamp_starves_d_term_v276_oscillation]] — the sum-clamp finding this extends.
[[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] — base PID decode.
[[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]] — the free gp-cell taps used here.
