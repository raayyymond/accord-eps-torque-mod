# PRE-REGISTRATION — reading V282 from ONE drive (strong turns + 60 s of hands-off creep)

Written **2026-09-03, BEFORE the drive.** Build: **V282** = V281 rev 3 (Kp flat at Y[0]) + four `ld.h` displacement halfwords in the V105 telemetry cave
(0xC4B34), 10 bytes vs rev 3, read-only, no cal change: CAN 0x14A byte 4 **bit 6 = |r24| ≥ |T|** (gp-0x6ada vs gp-0x6b38) and **bit 5 = |r24| ≥ |aggregator|**
(gp-0x6ada vs gp-0x6b94); bit 4 = sign(r24) (unchanged since V105), bit 7 = sign(gp-0x6b4c), bit 3 = sign(gp-0x3680). The 427 delivered-torque tap is kept, so
**every V281 rev 3 statistic in `../osc-highangle/PREREG-V281-READ.md` reads unchanged on this drive** — V282 answers V281's question AND the r24 question.
Source: `docs/research/GRINDING-DEEP-ANALYSIS-2026-09-03.md` (V282 section, §7.x prereg), `7HZ-STRONG-TURN-DEEP-ANALYSIS-2026-09-03.md`. Scripts to reuse:
`rlog-tools/studies/grind/` (deepgrind's), `rlog-tools/studies/osc-highangle/r24_deembed.py`, `strongturn_r34.py`, `grind_r34_operator.py`.
**Do not move a threshold after the log lands.** Record the StarPilot toggle backup (SR 12.5 / LAF 2.11 / friction 0.03 / KP 0.6 expected).

## Why
Both deep analyses converge: the engaged-only r24 lane (flat gain 0xC6446 = 5244 when engaged, ×10 stock, on the 4-tap derivative of the column twist) PUMPS the
7 Hz strong-turn ripple (loop share 1.17 vs the LKAS servo's 0.81) and DAMPS the 20 Hz creep grind (~83 % of the aggregator's 20 Hz damping). Every ranking scales
with |r24|, which is a closed-form estimate: r24 is not on the wire, and FUN_0003aa2c carries a gain arm the record never had — gp-0x671d ≠ 0 selects 0xC6442 = 1024,
at which the servo, not r24, is the pump. The flip point is r24 = 566 counts (effective gain 3909); the flown 5244 is only ×1.34 above it.

## Predictions
| statistic | frames | predicted |
|---|---|---|
| (A) bit-6 duty P(|r24| ≥ |T|) | engaged lateral, hands-off (|bar| < 400 raw), creep 1–3 m/s | **0.300** if the 5244 arm is live; 0.188 at 3072; 0.132 at 2048; **0.065 at 1024**; 0.029 at 512 (from r32/r33/r34 chain replay) |
| (B) bit-5 duty P(|r24| ≥ |aggregator|) | same | > 0 and < 1; the positive control (it works today) |
| (C) bit-4 (sign r24) phase re the wheel rate at 18–22 Hz, creep | same | **−6 ± 25°** (replicates deepgrind's read of r31–r34) |
| (D) bit-6 duty in the 7 Hz strong-turn episodes (|angle| ≥ 30°, idx ≥ 68) | | ≥ 0.5 (r24 ≥ T on most of the cycle) if r24 is the pump |
| (E) all V281 rev 3 statistics (a)–(k) | per PREREG-V281-READ.md | unchanged predictions |

## Decision rule
- (A) ≥ 0.22 → **r24 is the dominant 20 Hz lane at the 5244 arm; 0xC6446 must NOT be cut for grinding.** The grind lever is then a loop shape that keeps r24
  (output-lag pole 5 → 15 Hz ± 0xC6446 → 2048), sized against the 25–50 Hz blind spot before it is built.
- (A) ≤ 0.10 → the 1024 arm is live: r24 is ~148 counts, the SERVO is the 7 Hz pump after all, creep20's ranking governs the grind, and the next trace is gp-0x671d.
- 0.10 < (A) < 0.22 → licenses nothing about grinding; trace gp-0x671d and re-read the chain's dt factor.
- (D) ≥ 0.5 with the 7 Hz episodes still present on V281 rev 3's Kp → the r24 pump reading is confirmed on the wire; (D) < 0.2 with episodes present → the servo is the pump.
- **FAIL:** (A) or (B) reading 0.000 or 1.000 over ≥ 20 s of engaged creep (a dead or railed comparator — the edit did not do what the decode says), or (C) outside
  −6 ± 25° (the sign bit is not r24, or the timing model is wrong). Either → do not act on any r24 number until the cave is re-decoded.
- **Cost FAIL (must be invisible):** the 427 tap stops decoding, a new DTC, or any change in feel the operator reports → V282 is a code edit that did more than its decode.

## Risk stated before the drive
None intended: the cave, hook and every calibration are byte-identical to V281 rev 3 except four load displacements; authority unchanged. The V281 rev 3 risks apply
(low-demand deadband under road load, −8 % full-demand rate, stalled push −29…−48 % at idx 26–80, the idx-26 thin class). Bits 5/6 previously carried an unrelated
comparator (duty ~0) and a working one; openpilot does not parse them (adversary B to confirm).

## What refutes this pre-registration
(A) at 0.300 but (D) < 0.2 (r24 big in creep yet not the 7 Hz pump — the two analyses' phase picture is wrong); (C) replicating while (A) reads ≤ 0.10 (the sign
bit is r24 but its magnitude is small — the chain's dt/scale is wrong, not the arm).
