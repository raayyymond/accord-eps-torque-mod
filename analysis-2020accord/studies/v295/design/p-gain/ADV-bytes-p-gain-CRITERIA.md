# ADV-bytes-p-gain — pre-registered FAIL criteria (written BEFORE any number was computed)

Adversary "bytes+instrument" against the `p-gain` lens candidate **R1.3_8_100**
(Kp bank 0xCB994, all 28 records: X [0,8,54,100,208], Y [1248,1248,1104,960,960]; V294 slot 7 X [0,68,112,136,208], Y 960 x5).
Subagent, 2026-09-30. Written after reading only V295-DESIGN-p-gain.md, CRITERIA-p-gain.md and the spec JSON's key list;
no byte read, no script run, no simulation yet. Default verdict if a claim cannot be reproduced: **REFUTED**.

A FAIL on any item below means **"do not flash R1.3_8_100 as designed"** (REFUTED). A claim that is wrong but whose
correction leaves the edit safe and observable is a finding and moves the verdict to SURVIVES_WITH_CHANGES.

## (a) Bytes and arithmetic — from the V294 IMAGE, not the designer's constants
- **PB-1 base.** The V294 plain image does not hash to 3143616d…dbdd85; or u32(0xCB994 + 4*k) for k = 0..27 is not the
  28 record addresses in the spec; or any record's current X/Y bytes differ from the spec's `bytes_v294`; or the live
  record (slot 7) is not X [0,68,112,136,208] / Y 960 x5 -> FAIL (design built on the wrong base).
- **PB-2 record extent / aliasing.** Any byte the edit changes lies inside ANOTHER bank's record (another pointer table
  whose LE32 entries point into [rec, rec+0x16) of any of the 28), or any LE32 in the image other than the 0xCB994
  table points into a changed Kp record, or the 24-byte stride hides a different layout (e.g. the count word is read,
  records overlap) -> FAIL unless the second consumer is proven dead.
- **PB-3 reader census of 0xCB994 and of the 28 records.** Any LIVE reader of the pointer table 0xCB994 other than the
  Kp LERP at 0x29DC6.. (in any encoding: mov imm32, movhi/movea pair, a tp/gp-relative form, an LE32 data pointer,
  a bulk copy to RAM), or any direct reader of the record bytes (absolute address), not proven dead or benign -> FAIL.
  The scan must find its positive control (the known 0x29DC6 site, and the known Kd-bank reader for 0xCB7D4) or its
  null is void.
- **PB-4 second consumers of the LERP output.** If the Kp LERP result (or the P term it scales) is stored to a cell with
  a reachable reader outside the lane (a monitor, a plausibility check, a published cell compared to a threshold) that
  the new values can move past a threshold V294 does not reach -> FAIL unless proven unreachable.
- **PB-5 LERP arithmetic.** My own read of the listing/decompile does not confirm: signed divide, 32-bit sub/mul, zxh,
  hard-coded 5 knots (count word unread), and the boundary branches (idx <= X0 -> Y0; idx >= X4 -> Y4). If a falling
  segment can produce a Kp outside [960, 1248] at any idx in 0..240 (incl. idx values beyond 208 and any negative/
  over-range idx the index producer can emit) -> FAIL.
- **PB-6 int32.** Any intermediate (E*Kp, the LERP numerator, a*s, b*x, output-lag products, (y*5346)) able to reach
  |.| >= 2^31 for a reachable input at the new values -> FAIL. Designer's stated min margin 4.06 not reproduced within
  5 % -> finding.
- **PB-7 delivered surface.** At zero wheel rate, my own integer march of T(idx) for all 241 idx (golden model AND a
  second independent method): any non-monotone step (T(idx+1) < T(idx)), rail != +2461/-2463, rail first reached at an
  idx different from the design's 239, or a torque change at idx >= 100 vs V294 -> FAIL (the design claims none).
  Largest static increase not +85 T at idx 51 (within 2 T) -> finding.
- **PB-8 zero-command torque and restart pulse.** My re-derived zero-command trim cap or restart pulse differs from
  801 T and 18/56/188/545 T by more than 10 % -> finding (REFUTED claim); either able to exceed the lane rail -> FAIL.

## (b) Interlocks
- **PB-9** The new values newly reach the soft-EME band 5120..5325, a governor ceiling, the forward-lane monitor
  FUN_0002b57a's threshold, a lockstep comparator, a DTC plausibility threshold, or the P clamp 15360 / sum clamp in a
  region where V294 does not -> FAIL unless the monitor's operand is traced and shown unable to cross its threshold.
  "Not found" is not enough.

## (c) Lineage
- **PB-10** A non-flat or regressive Kp on the torque/trim operand, or moved Kp X knots, has flown and been falsified ->
  FAIL. Any lineage statement in the design (stock rising 248..696, V281r3/V282 248 flat, V283 Ki 50, V293 120 x28,
  V294 960 x28, V279 256, V281r2 X moved, V284 shaped slot 7 shelved, V285 Kp 0) that the build scripts / lineage do not
  support -> finding; if the "what is different this time" argument (V284's shelving reason does not apply) is false
  -> FAIL.

## (d) Observability — ONE short drive (15-30 s symptomatic + ordinary driving)
- **PB-11 R-PLATEAU.** On the byte-exact model with r71b's own command, rate and tap residual, with MY OWN code:
  (i) the synthetic candidate flight reads outside [1.25, 1.40] in more than 10 % of qualifying 20 s windows, OR
  (ii) the real V294 tap reads outside [0.95, 1.05] in more than 10 % of qualifying windows, OR
  (iii) fewer than 50 % of 20 s engaged windows (or of 15 s windows) qualify (enough hands-off idx 0-8 frames), OR
  (iv) a pessimistic residual model (residual scaled with the torque, x1.3) collapses the separation
  -> the pre-registered edit-live read is not what the design says. FAIL if the Kp plateau cannot be attributed in one
  short drive at all; SURVIVES_WITH_CHANGES if a re-worded read works.
- **PB-12 each changed value.** The changed values are Y0=Y1 (1248), X1 (8), Y2 (1104) at X2 (54), X3 (100). For each,
  estimate the CI with which a drive of r71b's length (and a 30 s episode) can separate the candidate from V294 AND from
  a plausible mis-build (flat 1248 x28; plateau without taper). If a changed value has NO read at any exposure -> FAIL.
  If it is readable only over a whole ordinary drive (not one episode) -> finding, the design must say so in its null
  sentence (the design already concedes R-SHAPE needs minutes above idx 50 — verify the minutes).
- **PB-13 null sentences.** Each of the three null sentences must be decidable from the stated instrument at the stated
  threshold with the measured spread (e.g. "1.00 +- 0.05" vs the real-tap spread; "turn-hold <= 0.72" vs r71b's own
  per-episode spread; "hard-turn cell > x1.10" vs route-to-route spread). A threshold inside its own instrument's noise
  -> finding (SURVIVES_WITH_CHANGES), or FAIL if it is the edit-live read.

## (e) One build, cal-only
- **PB-14** Applying the spec to the V294 image changes anything besides the 252 payload bytes in the 28 records and
  the checksum(s) covering those 5 pages, or the checksum scheme covering 0xE4000-0xE8FFF is not the one V294's own
  builder already exercised on these records, or any code byte / opcode changes -> FAIL (not cal-only / not proven).
  (Design only: the edit is applied in memory for counting; no image or .rwd is written.)
