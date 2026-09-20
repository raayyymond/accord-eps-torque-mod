# The SteerFriction relay is NOT the instability mechanism — and the Tier B loop-gain class is CLOSED

**2026-09-20.** Two independent pre-registered attempts to build a controller-ordering safety statistic both
FAILED. Pre-registrations committed *before* each result: `PREREG_retrodiction_gate.md` (74a7e9d, failed at
879448f) and `PREREG_retrodiction_gate_2.md` (a8a3c56). Work in `rlog-tools/studies/v282-reference/{retrodict,gate2}/`.

> **Two independent pre-registered attempts to build a controller-ordering safety statistic have failed. The
> Tier B class is CLOSED PERMANENTLY for this kit. No third repair may be proposed. Closure beyond ARM-KP3's
> measured 15.9 % requires either an instrument this kit does not have, or an EPS-side change that restores the
> inner rate servo — a firmware question, out of scope by the operator's own standing constraint.**

## ⭐ THE DURABLE FINDING — the relay is almost certainly not what broke r71

| route | `SteerFriction` | relay live? | linear gain kp/LAF | outcome |
|---|---|---|---|---|
| **r71** | **0.011** | yes | **0.0607** | **LIMIT CYCLE at 2.34 Hz** |
| V282 ×3 | **0.010 – 0.030** | **yes** (pre-guard commits) | **0.150 – 0.379** | **CLEAN, months of driving** |
| r72 | 0.0 | no | 0.0607 | clean (matched control for r73) |
| rev 6.4 ×2 | 0.2120 back-filled | no (guard live) | 0.0714 | clean, flying now |

A **10 % dose difference** carrying a labelled outcome flip, against a **2.5–6.2× linear-gain difference pointing
the other way**, is a coincidence the anchor set was built around, not a mechanism. Corroborated from the opposite
direction on the wire: **the relay's own chatter signature in the controller OUTPUT is 1.7–1.8× LARGER on the
three CLEAN V282 routes (0.0465–0.0508) than on POSITIVE r71 (0.0277).**
⇒ Whatever separates the positives is **the loop's conversion of chatter into wheel motion**, not the chatter's
presence or its size.

## 🛑 WHY THE GATE WAS UNSATISFIABLE — a proof, not a sweep

The three V282old routes **strictly Pareto-dominate positive r71 on BOTH permitted terms simultaneously**:
3.3–6.2× on the linear branch (`SteerKP/SteerLatAccel`) **and** 2.73× on the relay branch (`SteerFriction/0.30`;
`get_friction` returns friction·latAccelFactor and the factor cancels against `torque_from_lateral_accel`, so the
relay branch is LAF-free). **No statistic monotone-increasing in those two terms can rank r71 above them** — at
any damping `b` across its full 70× range, any delay 55/75 ms, any plant, any crossing index, either jerk reading.
The class of statistic the gate tested is analytically incapable of passing on these anchors. That retires the
class far more cleanly than a numerical near-miss would.

## 🛑 AMPLITUDE CANNOT SCORE THESE ANCHORS EITHER
**r75 — a CLEAN rev 6.4 route — carries 5.5× the oscillatory energy of POSITIVE r73.** Any amplitude-based safety
score misranks routes already in hand. If a future instrument is built, score **frequency placement of the
closed-loop object**, not its amplitude.

## 🛑 `friction_jerk` IS REFERENCE-SIDE — it contributes NOTHING to the loop transfer
Verified in source (`latcontrol_torque.py`, read at the flown commits):
`:254 future_desired_lateral_accel = desired_curvature * vEgo**2` (planner) ·
`:304 expected_lateral_accel = curvature_request_buffer[-delay_frames] * vEgo**2` (the controller's OWN past
command) · `:315 desired_lateral_jerk` = filtered difference · `:600 friction_jerk` ← that ·
`:603 ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)`, `JERK_GAIN = 0.22` (`:40`).
**`measurement` enters the relay argument ONLY through `error_with_lsf`**, so `d(friction_jerk)/d(measurement) = 0`
exactly. The term is an **exogenous dither at a saturating element, not feedback phase lead**, and it moves a
−180° crossing by **0.00 Hz at any Kj**. Gate #2's pre-registration asserted the opposite ("a jerk term is phase
LEAD, which moves a −180° crossing UP in frequency") — **that premise was FALSE of the term it named**, and the
orchestrator wrote it. Under the faithful reading r73 stays at 1.89 Hz, 37 % below its window floor.

## 🛑 THE PER-COMMIT GUARD RULE (this is how r73 flew a relay nobody intended)
`friction_torque = 0.0 if friction_hyst > 0.0` **first appears at commit `08a5a7064` (rev 4).** Before it, the
application is unconditional. So **`AccordFrictionHyst` gates the relay ONLY at rev 4 and later.** r72/r73 flew
`e8e62f0e1` ⇒ r73's back-filled `SteerFriction` 0.2120 was **LIVE** (wire: coefficient of `clip(arg/0.30)` in
`pid_log.f` = **2.530** on r73 vs **0.311** on r72, same commit, everything else matched). All three V282 routes
are relay-live for the same reason. **This fork BACK-FILLS ABSENT KEYS WITH STOCK — always read the flown commit,
not just the param.**

## What survives, and what does not
- **ARM-KP3 is untouched** (the prereg insulated it in advance): `SteerKP` 3.0 + `AccordErrorNotchQ` 0.30 +
  `AccordTorqueKi` 0.60, predicted J 1.3512 → 1.2064 = **15.9 %**, command shake ×0.964. It rests on hand-verified
  notch algebra and the three-crossing derivation, not on any ordering statistic. It is a **mechanism check**
  scored on G0–G2, never on J (17.6–32.2 % of NULL draws already reach J ≤ 1.2064), and **it has never flown**.
- **What the failure costs ARM-KP3 is its LADDER**: there is now no validated statistic on which to re-derive the
  patched KP 5/6 points or Tier B 8/12/16. **15.9 % is the measured closure and there is no licensed path to a
  larger number from logged drives alone.**
- 🛑 **The temptation to refuse next session:** *"but if we dropped the V282 routes it goes 3/3."* True, and it is
  exactly the relabelling the fixed anchor set forbids.
- **Open, forward question (do NOT use it to reinterpret the gate):** r73's largest oscillation by 10× is at
  **2.775 Hz with the driver touching the wheel** (`steeringPressed` 19–42 % of each episode); its 4–5 Hz chatter
  is the object only under the hands-off convention. The asymmetry may be an amplitude artefact — r71's object
  never twists the bar hard enough to trip the flag, r73's does. Decidable from logs already in hand.

Related: [[accord-the-goal-gap-is-timing-and-half-of-it-is-accordreffilter]] ·
[[accord-lowspeed-actuator-rails-on-large-angle-transients]] ·
[[accord-torque-mode-loop-delay-is-55-75ms-and-xcorr-cannot-measure-it]] ·
[[feedback-attribute-the-build-from-the-tap-not-from-the-label]]
