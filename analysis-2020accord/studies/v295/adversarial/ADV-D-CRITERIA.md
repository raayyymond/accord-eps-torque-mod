# ADV-D (interlocks, downstream, closed-loop cost) on the BUILT V295 image: pre-registered FAIL criteria

Written 2026-09-30 12:30 PDT, BEFORE any V295 number of mine was computed. Subagent ADV-D (adversary D).
Target: `_v295_…_plain_image.bin`, claimed sha256 `5c044d65…40452ed`; base V294 `3143616d…89dbdd85`.

The verdict scale is the orchestrator's: PASS / PASS_WITH_DEFECTS / DO_NOT_FLASH.
- A **FAIL** below means DO_NOT_FLASH.
- A **DEFECT** means the image may stand but a stated claim, cost or read must be corrected before the operator drives it.

## 0. Identity (everything else is void if these fire)
- **D0-F1** The file on disk does not hash to `5c044d65…`, or its diff against V294 is not exactly {0xC63EA, 0xC63EB,
  0xC6FFC..0xC6FFF}, or u16 LE at 0xC63EA is not 1050. -> FAIL.
- **D0-F2** Any byte of the 0x14A cave / 427 tap sources, the LKAS lane code FUN_00028ea6, the forward path, the monitors
  named below differs from V294. -> FAIL (the "unchanged sources" premise is false).

## 1. Reader census (0xC63EA and every cell / state its value scales)
Cells: 0xC63EA (tp+0x73EA); fb state gp-0x3d30; r26-derived gp-0x6a34 (|r26>>5|); the published P/D/S/E cells of the
lane; T = gp-0x6b38 and its forward copies.
- **D1-F1** A second LIVE reader of 0xC63EA (any form: 4-byte, 6-byte, hw2 = disp|1, absolute LE32, register-built base)
  that is reachable code. -> FAIL (the one-reader premise of every dose bound is false).
- **D1-F2** A LIVE consumer of gp-0x3d30, gp-0x6a34 or a published PID cell outside the lane / forward path / 427 tap /
  known packer, whose value feeds a threshold, DTC, monitor or actuator path, and which the b change can newly push
  across a threshold. -> FAIL. Named but provably dead or value-insensitive -> report, not FAIL.
- **D1-D1** Any scan that cannot find its positive control. -> that null is void; if the null is load-bearing and cannot
  be re-established by a second method -> DEFECT (required before flash).

## 2. Interlocks and reachability
- **D2-F1** The lane's reachable instantaneous output grows: rail beyond +2461 / -2463, zero-command trim cap beyond 616,
  sub-rail slope different from V294, re-derived from the V295 image cells. -> FAIL.
- **D2-F2** Soft-EME: on the r71b byte-exact replay at b = 1050, an ENGAGED run of |trim| > 300 T lasting >= 75 ms occurs
  at vEgo >= 10 m/s (outside the parking/creep regime the design adversaries disclosed), or the lane's total |T| on any
  tick exceeds V294's replay maximum by > 50 % AND exceeds 2463 (V282's flown zero-command capability). -> FAIL.
  Any rise in dwell below 10 m/s -> disclosed risk, quantified (not a FAIL).
- **D2-F3** The >10 Hz reversal detector (FUN_000428d4, gp-0x6c2c), the forward-lane range monitor FUN_0002b57a, a
  governor ceiling or a lockstep comparator reads a quantity that b scales and whose threshold becomes newly reachable
  (the lane's contribution at the relevant frequency and amplitude crosses the threshold at b = 1050 but not at 567).
  -> FAIL.
- **D2-F4** A DTC / plausibility check reads the fb operand (x = gp-0x6a56) or r26 / s and b changes what it sees. -> FAIL
  if its threshold is reachable, else report.
- **D2-F5** The restart pulse is reachable in ROUTINE operation: the fb state is zeroed (sentinel != 1 path) on every
  engage / disengage / first tick with the wheel moving, so a b-scaled pulse occurs on normal engagements, AND its peak at
  plausible engage rates (<= 100 deg/s) exceeds 288 T. -> FAIL. Routine but <= 288 -> DEFECT (must be stated).
  Reachable only on a filter bail (|x| > 12000 or the polarity/guard fault) -> report with the bail's measured frequency.
- **D2-F6** A synthetic driver override (a swerve the driver makes against the lane) meets an opposing trim torque at
  b = 1050 larger than the flown V282 lane's opposing torque in the same manoeuvre (golden-model lanes, same x trace).
  -> FAIL (no flown precedent bounds it). Larger than V294 only -> disclosed cost, quantified.

## 3. Closed-loop cost (harness, V294 in the same batch, b = 1050 exactly, cells read from the V295 IMAGE)
- **D3-F1** Any member / speed / delay case that is stable on V294 is unstable on V295, or inner Ms at delay x1.5 > 1.5
  on any default or stress member. -> FAIL.
- **D3-F2** Outer loop with the unchanged fork law: GM on any member x speed x relay falls below V294's by > 5 % where
  V294's GM < 3, or PM on the identified family falls by > 10 deg at any speed, or light_b at 26.9 m/s GM < V294's.
  -> FAIL. PM loss 5-10 deg -> DEFECT (state it).
- **D3-F3** Tracking gain or turn-hold worse than V294 by > 0.02 in any band on nominal or light_b under lp. -> FAIL (the
  "unchanged" claim is false). 0.01-0.02 -> DEFECT.
- **D3-F4** Low-speed 0.5-1 Hz lateral error (band-passed plan - act) at 0-5 or 5-10 m/s on nominal or light_b above
  x1.6 V294. -> FAIL. Above the stated x1.4 envelope -> DEFECT (restate the cost).
- **D3-F5** Hard-turn 1.6-3 Hz wheel rate rises (> x1.05) at 5-10 m/s on nominal AND light_b under BOTH dists. -> FAIL
  (the only purpose of the dose is inverted).
- **D3-F6** A new limit cycle: the 1-5 Hz limit-cycle line prominence rises > +3 dB on any member under lp, or an on-centre
  hold hunts (new oscillatory line in the sim at |plan| < 0.4) that V294 lacks. -> FAIL.
- **D3-F7** 20 Hz stress modes: at any of 2 / 6 / 9 ms delay, V295's damping change vs open is more negative than 20 % of
  V282's change at the same delay and speed, or any stress-mode zeta < 0.05 where V294's is >= 0.05. -> FAIL.
  10-20 % of V282's -> DEFECT (the page must say "anti-damping", with the number).
- **D3-F8** |P/x| at 20 Hz >= 3 x V294 (6.24), or simulated delivered 5-30 Hz torque in any band > x2 V294 on any
  member. -> FAIL. > x1.5 (the trim-ratio lens's own F5-HF line) -> DEFECT (state it: the dose crossed that clause).

## 4. The three complaints
- **D4-F1** A complaint the decision calls "not reached" ("loose / understeer at highway turns") is predicted WORSE by more
  than the D3-F3 tolerance. -> FAIL of the claim (DEFECT if 0.01-0.02).
- The per-complaint prediction is reported as better / unchanged / worse with EVIDENCE/BELIEF; a prediction is not a
  symptom and nothing here calls a symptom fixed.

## What "DO_NOT_FLASH" would look like, in one line
A second live reader of b; a monitor/DTC newly reachable; a b-scaled restart pulse > 288 T on every engagement; an
inner/outer loop that V294 keeps stable going unstable; or the 20 Hz stress modes losing > 20 % of what V282 removed.
