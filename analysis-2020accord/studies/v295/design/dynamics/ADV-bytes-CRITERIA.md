# ADV-bytes-dynamics — pre-registered FAIL criteria (written BEFORE any number was computed)

Adversary "bytes+instrument" against the `dynamics` lens candidate **A1017** (0xC63E8 1011 -> 1017, b 0xC63EA held 567).
Subagent, 2026-09-30. Written after reading only V295-DESIGN-dynamics.md, CRITERIA-dynamics.md and the census report;
no script run, no byte read, no simulation yet. Default verdict if a claim cannot be reproduced: **REFUTED**.

A FAIL on any item below means **"do not flash A1017 as designed"** (REFUTED); a claim that is wrong but whose
correction leaves the edit safe and observable is a finding and moves the verdict to SURVIVES_WITH_CHANGES.

## (a) Bytes and arithmetic — from the V294 IMAGE, not the designer's constants
- **FB-1** The image at `_v294_…plain_image.bin` does not hash to 3143616d…dbdd85, or 0xC63E8 != 1011 (LE F3 03),
  or 0xC63EA != 567 -> FAIL (the design was built on the wrong base).
- **FB-2 reader census.** Any LIVE reader of 0xC63E8 other than 0x28F8A — in any encoding (4-byte disp16 on tp or any
  base register, `hw2 = disp|1`, the 6-byte extended form, a base+disp pair via movhi/mov imm32, an LE32 pointer into
  0xC63E0..0xC63EF in data, a bulk copy of the cal page to RAM) — that is not proven dead or benign -> FAIL.
  The scan must find two positive controls (0x28F8A for 0xC63E8, 0x28F86 for 0xC63EA) or its null is void.
- **FB-3 second consumers of the changed signal.** r26 / gp-0x6a34 / the fb state gp-0x3d30 / the published PID cells
  (gp-0x6b2e, -0x6b32, -0x6b34, -0x6b36) having a reachable reader outside the lane that the edit changes materially
  (a monitor, plausibility check, the damper mode made reachable) -> FAIL unless proven unreachable.
- **FB-4 int32.** Any intermediate (a*s, b*x, E*Kp, the output-lag products a_L*L and S*b_L, (y*ramp), (yr*pol*5346))
  able to reach |.| >= 2^31 for any reachable x (|x| <= 12000 after the producer's saturation and the bail) at a=1017
  -> FAIL. My re-derived worst-case a*s margin < 2.0 -> the designer's own F2 fires -> FAIL.
- **FB-5 delivered surface.** At zero wheel rate the steady-state T(idx) for any of the 241 demand indices, the rail
  (+2461/-2463), the sub-rail slope, or monotonicity differs from V294 -> FAIL (the edit claims to touch none of them).
- **FB-6 settling / dither.** At any constant x in [-12000, 12000] the fb operand r26 fails to settle to exactly 0, or a
  sustained |r26| >= 1 dither appears that V294 does not have -> FAIL (new zero-input torque ripple).
- **FB-7 restart pulse.** My re-derived restart-pulse peak or duration differs from the designer's (17/52/174/503 T;
  433 ms >50 T at 300 deg/s) by more than 20 % -> the claim is REFUTED (finding); a pulse able to exceed the lane rail
  or any interlock threshold -> FAIL.

## (b) Interlocks
- **FB-8** The edit newly reaches the soft-EME band 5120..5325, a governor ceiling, the forward-lane monitor
  FUN_0002b57a, a lockstep comparator, a DTC plausibility threshold, or the record's "Honda oscillation detector" that
  V294 does not already reach -> FAIL. "Not found" is not enough: the monitor's operand must be traced to show the edit
  cannot move it past its threshold, or it counts as unproven.

## (c) Lineage
- **FB-9** 0xC63E8 at 1017 (or the same class — the fb pole moved DOWN on the DIFFERENCE operand beyond 1011) has been
  flown and falsified -> FAIL. Any lineage statement in the design (stock 923/1560, V289 875/2301, V291/V292 962/958,
  V293 923, V294 1011/567, V294 ladder a in [1000,1018]) that the build scripts / lineage do not support -> finding.

## (d) Observability — ONE short drive (15-30 s symptomatic + ordinary driving)
- **FB-10** On the byte-exact model with the r71b route's own command, rate and tap residual:
  (i) the exact-model regression (beta) separates A1017 from V294 at z >= 3 in fewer than 80 % of 30 s windows, OR
  (ii) the real-tap null (V294 flight) reads |z| > 3 in more than 10 % of windows, OR
  (iii) the metric agent's trim-footprint |K|(0.3-1 Hz) regression, run ON A SYNTHETIC A1017 FLIGHT with its own
  code, reads outside [0.25, 0.41] (the designer's 0.33 +/- 25 %), OR its 30 s-window spread makes the pre-registered
  thresholds (>= 0.28 live; > 0.45 "arithmetic wrong"; <= 0.19-ish "not A1017") misfire in more than 20 % of windows
  on either the synthetic A1017 or the real V294 flight
  -> the pre-registered wire read is not what the design says: FAIL if the edit cannot be attributed in one short
  drive at all; SURVIVES_WITH_CHANGES if a re-worded read (longer window, pooled, different threshold) works.
  Also report at 15 s windows (the doctrine's lower end).
- **FB-11** A changed value with no instrument on the wire -> FAIL (only one value changes here: `a`).

## (e) One build, cal-only
- **FB-12** Applying the edit to the V294 image changes anything besides 0xC63E8's low byte and the checksum(s)
  covering it, or the checksum scheme covering 0xC63E8 is not the one V294's own builder already exercised
  on this cell -> FAIL (not cal-only / not proven).
