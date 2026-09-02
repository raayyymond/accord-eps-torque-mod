---
name: accord-sign-e-alone-cannot-measure-damping
description: A telemetry bit carrying sign(E) of the LKAS rate PID reads ~0.50 duty at EVERY reference scale K, in oscillation and in normal driving alike, because E's sign follows the direction of motion. The quantity that discriminates damping is sign(E) != sign(feedback) -- the lane OPPOSING the wheel. V278's tap was redesigned to that comparator (xor r7,r9 / shr 0x1f) after the plain sign(E) design was falsified offline on the V276 log.
metadata:
  type: feedback
---

# sign(E) alone cannot measure damping -- 2026-09-01 [EVIDENCE, from the V276 log]

`E = 32*setpoint - feedback`. On a straight road the setpoint is small and re-signed from the command each tick,
and the feedback alternates with the wheel, so **P(E<0) is 0.48-0.50 in oscillation and 0.43-0.48 in normal
driving at every K from 1 to 6** (`rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py`). A bit that carries it
measures the direction of motion, not the loop's state.

**The discriminating quantity is `sign(E) != sign(fb)`** -- the lane's push opposes the wheel's motion:
0.94 stock / 0.86 at K=2 / 0.57 at V276 in oscillation. V278 carries it as one comparator in the CAN-427
packer: `ld.w -0x6cf8[gp],r9; ld.w -0x3d30[gp],r7; xor r7,r9; shr 0x1f,r9` -> bit 9.

**Why it matters:** the first V278 window was built, decoded field-by-field, passed 450/450 and an arithmetic
adversarial pass -- and would have flown as an instrument that measures nothing. It was caught only because the
dose computation ran the same statistic on the log first. **Run the instrument's statistic offline on a flown
log BEFORE cutting the tap.** This is the probe-design law (a comparator, not a quantised threshold) applied
to the comparator's OWN choice of operands.

**How to apply:** for any "state of the loop" bit, write down what it reads under the null AND under the
alternative, from existing data, before encoding it. See [[accord-feedback-operand-is-a-two-sample-sum-dc-30-89]].
