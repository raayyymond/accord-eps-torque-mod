# ADV-A (arithmetic) — FAIL criteria, written BEFORE any V295 number was computed

Subagent "ADV-A arithmetic", 2026-09-30. Target: the BUILT V295 image on disk,
`../accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-...TORQUE.TAP_plain_image.bin`.
Only thing computed before this file: the image sha256 (certutil), to confirm I attack the right file:
`5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed` (matches the builder's report).

Every cell value used below is re-read from the image bytes by my own decoder (LE, tp = 0xBF000), never
from the build script or the brief. Decision bounds quoted from the orchestrator's brief are the only
external numbers, and they are gates, not inputs.

## DO_NOT_FLASH — any one of these fires

- **F1** The image on disk does not hash to `5c044d65…52ed`, or the V294 base does not hash to `3143616d…dbdd85`.
- **F2** Whole-file diff V295 vs V294 is not exactly {0xC63EA, 0xC63EB, 0xC6FFC..0xC6FFF}; or the u16 LE at
  0xC63EA != 1050; or the block [0xC6000, 0xC6FFC) CRC does not equal the trailer; or 0x28FA4 is not the
  `subr` / 0x29D76 not the `shl 0x2` in the V295 image.
- **F3** The Ghidra decompile/disassembly of FUN_00028ea6 (+ the PID at 0x29D76..0x2A23C) shows the b cell
  loaded or used differently from my mirror (signedness, shift, product order, a second reader of 0xC63EA
  in the function, clamp ordering) in a way that changes any delivered number.
- **F4** My integer mirror (written from the bytes/decompile, not copied from the golden model) differs from
  the golden model `lkas_fb_lag` + `lkas_rate_pid_tick` on any of >= 50,000 random ticks at the V295 cells
  (including clamp binds and bails), and the disagreement cannot be adjudicated in the mirror's favour
  with no change to the build's quoted numbers.
- **F5** Any 32-bit product or sum in the lane can wrap for a reachable input: a*s, b*x (|x| <= 12000,
  the guard), E*Kp, taper*S, out-lag a*s and S*b, y*ramp, yr*pol*gain. Reachable = from ANY state the
  recursion can reach (cold boot, bail, long march at the guard), not only the constant-x fixed point.
- **F6** int32 margin at the |x| = 12000 fixed point < 2.0 (the decision's own bound).
- **F7** Delivered surface at r26 = 0 (golden-surface march, 241 idx x 2 signs) differs from V294 at any cell,
  or rail != +2461/-2463, or zero-command torque differs from V294.
- **F8** Restart pulse at <= 100 deg/s (x <= 800 counts, 8 counts per deg/s) exceeds 288 T at ANY lane in
  idx 0..240 x demand sign x rate sign, measured my own way (including the output-lag fixed-point
  interval's worst end, not only the cold-boot end).
- **F9** |P/x| at 20 Hz >= 3 x V294's (decision bound "HF controller gain < x3 of V294").
- **F10** A reachable delivered |T| exceeds the V294 rail (2461 / 2463) — i.e. the trim adds authority above
  the rail.
- **F11** r26 fails to settle to exactly 0 at a constant x from some reachable state AND the settled
  delivered T then differs from V294's by > 5 counts (a static-surface change the decision says is absent).

## PASS_WITH_DEFECTS — reported, not a block

- **D1** r26 settles to a nonzero value / small limit cycle but the static T differs by <= 5 counts.
- **D2** The sinusoid-march trim gain differs from the closed-form linear gain by > 5 % in magnitude or
  > 5 deg in phase anywhere in 0.3–30 Hz in the unclamped regime (the dose analysis rests on the linear
  reading), but not enough to break F9.
- **D3** Restart pulse at 300 deg/s or at the 1500 deg/s guard grows by more than x2.2 vs V294 (the brief
  quotes "~2x"), or any restart number the brief does not disclose that is materially worse than quoted.
- **D4** Route replay (r71b) shows: override resistance (hands-on frames) up by more than x2.3 vs V294
  (brief: "roughly doubles"); or |trim| > 300 T dwell up by more than x3; or the P clamp / r26 clamp
  binding on the route where V294 did not bind, in a way the brief does not disclose.
- **D5** Any >>10 floor producing a DC bias in r26 under zero-mean noise beyond the telescoping bound
  (|mean r26| > 2 max|s| / N).
- **D6** Any claim in the builder's report that my re-derivation contradicts (numbers, census, semantics).

## PASS

None of F1–F11 fire. D-items, if any, are listed with EVIDENCE.

## What a FAIL looks like, concretely

A single lane in the restart envelope at 289 T; a reachable wrap of a*s from a non-fixed-point state
(e.g. a long march at x = +12000 followed by a reversal to -12000 so s swings past its fixed point);
a 20 Hz |P/x| >= 6.24; my mirror and the golden model disagreeing on the b term's floor; or a surface
cell at r26 = 0 that moved.
