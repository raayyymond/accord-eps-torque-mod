---
name: feedback-reducing-a-gain-is-not-a-safety-class
description: V94 RCA — "cal-only, and REDUCING" was treated as a safety class that exempts a change from real GATE 2 review; the build asserted its own safety and 133/133 passed on a wrong premise.
metadata:
  type: feedback
---

🛑🛑 **"A scalar adds ZERO phase and strictly REDUCES that lane's loop gain" is NOT a GATE 2 answer.**
It is `builds/v80_v107/build_v94_tva.py:117`, and it is how V94 shipped a lever that made the car unsafe to drive.

**Why:** reducing a gain is monotonically safe only for a *driving* term. For a **damping** term, reducing
loop gain is exactly what destabilises the loop. V94 cut `0xCBE74` (mode 24 ×0.50, modes 26/27 ×0.25 — a
6× cut against V92) on the reasoning that `gp-0x6b26 = −K·α` is "apparent inertia, nothing is dissipated,"
so lowering it was "strictly safe on both binding bounds" (`builds/v80_v107/build_v94_tva.py:106`). On-car: the operator
reported grinding and stuttering bad enough to shake the whole car and stopped driving at walking pace.
Measured on route `7d`: motor acceleration **3–7× up above 9 Hz**, column-torque↔wheel-rate coherence at
18–31 Hz the highest of any drive in the corpus. See [[accord-v94-flew-and-the-lane-is-a-damper]].

**The premise was refutable — but NOT by the desk calculation, and that is the sharper lesson.**
`gp-0x6c2c` is a first difference sandwiched between **two EMA poles whose coefficients are readable from
the image** (`0xC643C`=37>>7, `0xC40DC`=22>>6). Nobody computed the phase at all, which was the first
failure. But when the orchestrator finally did compute it (2026-08-12), it produced **+75° vs rate ⇒ 26 %
dissipative at 7.8 Hz — and that was ALSO WRONG.**

🛑 **MEASURED, on two independent drives, ω-partialled with a shuffled control: `gp-0x6b26` sits at
`+137°/+139°` vs WHEEL rate at 6–9 Hz ⇒ |cos| = 0.73, contributing `+518/+565` counts of POSITIVE
`Re(Z)`.** It is a **real 6–9 Hz damper**, not a 26 % one. The desk calculation was of the *producer's*
filter phase against *motor* rate; the measurement is of the *delivered lane* against *wheel* rate, with
the plant in between. ⇒ [[accord-gp6b26-is-a-real-6to9hz-damper]]

**So the rule is not "do the arithmetic" — it is "measure the delivered lane."** Two successive phase
stories about this same lane were wrong in a decision-bearing way within four days of each other. A
producer's transfer function is not the lane's contribution to impedance at the wheel, and no amount of
care with the image's filter coefficients closes that gap. "Acceleration-derived" is not synonymous with
"purely inertial", and neither is any number derived without the plant in the loop.

**Five compounding failures, in the order they occurred:**
1. **Algebra not done.** The dissipative fraction was never computed; "inertia" was asserted from the
   producer's identity alone.
2. **The motivating null was a measurement artifact.** V91/V92's ×1.5 measured **0.99** and was read as
   "the dose is not in force." But `gp-0x6b26 = K·α` and α is *what K damps* — in a stable closed loop the
   **product is invariant to K**. The instrument was structurally incapable of measuring its own dose.
   **Nobody asked whether the instrument could measure the thing it was pointed at.**
3. **Direction was derived, never measured.** Seven built variants had moved this lever, **all UP**. Zero
   DOWN. `d(symptom)/dK` had never been observed. The kit's own "FALSIFIED ≠ INERT ≠ never-tried" rule was
   applied to the *lever* and not to the *direction*.
4. **GATE 2 was satisfied by a sentence that assumes its conclusion** — see the quote above. The gate
   exists precisely to catch this class and the build routed around it by self-classifying as cal-only.
5. **The assertion suite encoded the wrong premise as a PASS condition**:
   `check(y_max_all < y_max_stock, "the largest gain magnitude STRICTLY DECREASES")`. **133/133 green
   measured internal consistency with a wrong premise, not safety.**
⊕ Aggravating: not single-variable (22 cal bytes, 3 records, 2 fallbacks, 1 code byte; mode 24 moved for
the first time in the kit's history), and over-sized (×0.25 when ×0.75 would have shown direction), against
a standing precedent that large moves on a damping term cause qualitative regime changes
([[accord-v80-damper-relay-and-grind1-inert]], "worst grinding ever").

**How to apply:**
- **A gain change on a term you believe is a damper is a GATE 2 change, not a cal-only change.** Compute
  the term's **phase relative to rate** at the target band, from the image's own filter coefficients, and
  state the **dissipative fraction as a number**. A sentence is not a gate.
- **Before trusting any dose measurement, write the loop equation for the measured variable.** If the
  instrument is the product of the gain and something the gain controls, it **cannot** measure that gain.
  Measure the *input* (here `gp-0x6c2c`) or a symptom instead.
- **Never reverse a lever's direction on a mechanism story alone.** Require either a measured
  dose-response sign, or a small probe step (≤ ×0.75) sized so a wrong sign is recoverable.
- **Audit the assertion suite for premise-encoding.** An assertion that restates the build's hypothesis
  is not a check; it is the hypothesis wearing a green tick.

**What went RIGHT and should be kept:** byte-exact verification, recorded hashes, exactly one `.rwd` per
build number, a working single-frame identity test, no fault of any kind on-car, and a build the operator
could stop safely. V94 also produced the kit's **first in-force `0xCBE74` dose measurement** and a positive
control proving the lane reaches the motor. It was an expensive experiment, not a catastrophe — but the
last line of defence was the operator's hands, and it should not have been.
