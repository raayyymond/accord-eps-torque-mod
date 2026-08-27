---
name: accord-override-surge-and-two-dead-mechanisms
description: "In the override regime the two named 6-9 Hz mechanisms (authority-collapse-curve, sign-guard relay) are both dead — refuted with perfect exposure. But the same instrument found a NEW mechanism: the EPS zeroes LKAS authority 17.5-40.5% of override time while openpilot winds UP 6.7-15x, giving a real surge at ~0.5-1 Hz."
metadata:
  type: reference
---

# TWO 6–9 Hz MECHANISMS DIED IN THE OVERRIDE REGIME — AND A ~0.5–1 Hz SURGE APPEARED

Established 2026-08-12, scoring in the regime the operator actually produces the symptom in
(ENGAGED + HANDS-ON + OVERRIDE) rather than hands-off.
⇒ [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]]

## ☠ MECHANISM A — "the LKAS authority collapse curve is the 6–9 Hz exciter". **DEAD, five ways.** [EVIDENCE]

**The exposure was perfect**, which is what makes the null load-bearing: median override torque
**2235** against a **2240** knot, and **33–70 %** of override time above 2560 with authority at
exactly zero. The mechanism had every chance to appear.

1. **Crossing rate is 0.47–1.69 Hz.** The knot is crossed roughly once a second, not eight times.
2. **The reconstructed authority signal puts 88.4–94.9 % of its energy in 0.5–3 Hz**, peaking at
   **0.79 Hz** on every route. Nothing at 6–9.
3. **Sweeping the unit scale 0.6×–2.0× never gets the crossing rate above 1.22 Hz.** The null is not
   an artifact of a mis-scaled knot.
4. 🛑 **The chatter↔energy correlation INVERTS against its own negative control**: OVR
   **−0.194 / −0.255** vs MAN-ON **+0.400 / +0.495**. The manual arm shows the *stronger,
   opposite-signed* effect ⇒ the correlation tracks **how hard the driver is working**, not a
   firmware mechanism. (This is [[feedback-run-the-control-before-the-measurement]] earning its keep
   for the fifth time.)
5. **It is not an exciter either**: 6–9 Hz energy **falls** after a collapse edge, below the shuffled
   baseline. No onset ringing, no kick.

## ☠ MECHANISM B — "a sign-guard relay chatters when the driver opposes the command". **DEAD.** [EVIDENCE]

- **Request-bit duty is 1.0000 on every route**; drops/s **0.000**. The gate never opens, so the relay
  can never arm. Same failure class as [[accord-v64-null-is-on-the-gate]] — but here the gate is
  measured *closed*, which is a real refutation, not an uninterpretable null.
- **openpilot does not back off when overridden — it winds UP 6.7–15×.** The premise that override
  reduces the command is simply false.
- Direction reversals run **0.23–2.66 Hz** and are **lower** during override, not higher.

## ★★★★ THE POSITIVE FINDING — A REAL SURGE, AT ~0.5–1 Hz

Two measurements that only mean something together:
- **The EPS holds LKAS authority at exactly zero for 17.5–40.5 % of override time**, cycling at
  **~0.5–1.7 Hz**.
- **openpilot's controller winds up 6.7–15× during that time** (it does not see the authority kill).

⇒ Push the wheel, the EPS zeroes the assist, openpilot keeps integrating against the resistance;
ease back below the knot and **authority returns with a command an order of magnitude larger than
before.** That is a genuine surge mechanism, quantified, never previously described in this kit.

🛑 **It is at ~0.5–1 Hz, NOT 6–9 Hz.** It is not the grinding and it is not the micro-ratchet. It
would be felt as a **slow lurch or a "catch"** — the wheel going slack and then grabbing — during an
override. **The operator has not yet said whether he feels this.** Until he does, it is a measured
behaviour with no scored symptom attached, and it must not be reported as a cause of anything he has
complained about. (Standing rule: score bands; let the operator score symptoms.)

## HOW TO APPLY
- **Both A and B are struck. Do not re-propose either without new exposure of a kind that did not
  exist on 2026-08-12** — the exposure that killed them was as good as this corpus gets.
- The surge is a **question for the operator first, a lever second.**

## REPRODUCE
`rlog-tools/studies/v95-override/v95_override_authority_chatter.py` · `rlog-tools/studies/v95-override/v95_override_onset_ringing.py` ·
`rlog-tools/studies/v95-override/v95_override_exposure.py`

Links: [[reference-accord-steeringpressed-mask-excludes-the-symptom-regime]] ·
[[reference-accord-controls-killed-four-6to9hz-stories]] · [[feedback-run-the-control-before-the-measurement]] ·
[[accord-v64-null-is-on-the-gate]] · [[accord-engagement-amplifies-6-9hz]] ·
[[accord-v94-flew-and-the-lane-is-a-damper]]
