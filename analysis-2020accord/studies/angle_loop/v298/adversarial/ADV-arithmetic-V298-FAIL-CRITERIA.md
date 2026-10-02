# ADV-ARITHMETIC V298 — FAIL criteria, written BEFORE any byte was read (2026-10-01)

Adversary: ARITHMETIC. Target: built image `_v298_V298-ANGLELOOP...A16A_plain_image.bin`
(sha256 177abf04...2066). Job: make it FAIL.

Verdict scale: PASS / PASS_WITH_DEFECTS / DO_NOT_FLASH. DO_NOT_FLASH is returned if ANY of F1..F9 holds
on a REACHABLE input domain (reachable = any wire value of 0xE4 / angle / rate the decoder can deliver,
plus engage/disengage/first-tick/bail transitions). A defect that is bounded, sign-correct and below the
stock rail is PASS_WITH_DEFECTS.

- **F1 OVERFLOW / WRAP SIGN FLIP** — any intermediate (E, P, D, I, Kp*E, Ki*G*E, lerp products, the
  r26 sum 8th[n]+8th[n-1], the final sum) wraps in its register or in a narrower STORE width and is read
  back with the opposite sign or a wrapped magnitude, on a reachable angle / setpoint range.
- **F2 INTEGRAL BOUND BROKEN** — the A3 angle-referenced bound can go negative, can be bypassed by a
  signed/unsigned compare mismatch, or does not bound I at the claimed value at every G and every angle;
  or I can escape the bound through the freeze / op-skip / CAM paths.
- **F3 SENTINEL** — the 0x7FFF (16-bit) / 0x7FFFFFFF (32-bit) first-tick sentinel is consumed as a real
  sample on any entry path (engage, re-engage after op-skip, after CAM, after bail) producing a D or
  E kick, or the cave reads a cell the skip epilogue left at the sentinel.
- **F4 CONTROL-FLOW / LINK** — a branch/jr target in the FLIGHT cave or in-place edits lands anywhere
  other than an instruction boundary that the design's arithmetic expects; the table pointer is off;
  a return path leaves lp/sp/a callee-saved register different from what the host function requires.
- **F5 CAM / FREEZE NOT INERT** — the camera (r25=0) path writes non-zero torque or does not decay I to
  exactly 0 (e.g. a sar-toward-minus-infinity floor that parks I at -1 forever and delivers a bias);
  the freeze path integrates.
- **F6 G-TABLE LERP** — X axis not monotone, the 0xFFFF terminator read as signed -1 (lookup always
  segment 0 or never terminates), divide/shift producing a slope sign error or a step discontinuity at a
  knot larger than one G quantum, or an out-of-table index.
- **F7 MIRROR DISAGREEMENT** — my integer re-implementation, built from the image bytes, disagrees with
  the common scorer's lane (score_time CandLane / Cpu2) or the lane mirror on any tick. A disagreement
  that changes delivered torque sign or exceeds the design bound => DO_NOT_FLASH; one that is only a
  quantum => defect.
- **F8 DELIVERED SURFACE EXCEEDS THE RAIL / CLAIMS** — with Kp 112 x5, Kd 48 x4, Ki 40, the delivered
  torque surface reaches a value the downstream clamps were not sized for, or the surface the builder
  reports is not the surface the image computes.
- **F9 I QUANTUM** — the sar-5 integral increment is 0 for every reachable error at some G (dead
  integrator), or sar-toward-minus-infinity rounding creates a non-zero mean drift under zero-mean error
  that is UNBOUNDED (bounded small drift = defect).

What does NOT count as FAIL here: interlock/downstream consumer census (adversary 4), unit chain
(adversary 2), build-script assertion census (adversary 3). Those are reported only if they fall out.
