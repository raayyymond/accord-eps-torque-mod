---
name: accord-ratchet-is-a-lightly-damped-resonance
description: "The ~8 Hz ratcheting is a lightly-damped resonance (Q 14-29) on the motor/rack side, not a loop, not a limit cycle, not rim-side — the firmware search on it is CLOSED."
metadata: 
  node_type: memory
  type: reference
  originSessionId: e91b71d0-25c8-4a14-9b74-24c186211918
  modified: 2026-08-09T07:33:19.806Z
---

**[EVIDENCE] The ~8 Hz "ratcheting" is a LIGHTLY-DAMPED RESONANCE, Q ≈ 14–29.** Three methods, each
having survived its own control: **ring-down** (the only estimator that PASSES a control, log-log
r = +0.937 over ζ = 0.005–0.02) gives **ζ ≈ 0.017–0.036**, n = 5 edges; a **calibrated peak-aligned Welch
ladder** reads the car at **20.9** against a pure tone at **53.8** and a bursty AM tone at 52.1–52.5 ⇒
**limit cycle EXCLUDED**; and V86's own phase-slope bound required Q ≥ 2.4.

🛑 **NOT rim-side.** Torque PSD peaks ~6× and rate PSD ~3×, but the transfer function `|T/Ω|` **rises
smoothly straight through** (63 → 75 → 93 → 121, coherence 0.86–0.91). Positive control: injected Q=10 →
3.40× admittance peak, Q=3 → 1.52×; **the car → 1.30×, and not at the line.** ⇒ **also refutes "it is the
12.8 Hz wheel-on-torsion-bar mode pulled down by engagement"** — that mode is by definition rim motion
against the bar. **The mode is on the motor / rack / tyre side, which no channel on this bus observes.**

🛑 **THE FIRMWARE SEARCH ON IT IS CLOSED, by a SHAPE argument not an enumeration.** Every gain-bearing
element on the torque path is either a **flat Q10 scalar** (would lift the 26–31 and 32–38 Hz controls
too — they went *down*, 0.61–0.76) or a **differentiator** (favours HF, wrong direction). A band-limited
lift at 6–9 Hz needs a **resonant/biquad structure and none exists in the chain**. Corroborating: no −180°
crossing anywhere in 0.5–200 Hz with real PID gains; `|L|` never reaches unity in 18–27 Hz; a 2-pole EMA
has DC gain exactly 1 so no EMA can be the amplifier.

★ **Frequency tracks LOAD, not amplitude and not the command**: +0.467 Hz [+0.111, +0.927] over a 17.8×
column-torque range at fixed speed (+5.8% ⇒ +12% stiffness), vs −0.145 [−0.564, +0.325] against openpilot's
command. `d log f/d log A` = −0.034 ⇒ kills rate-limit (−1.0), backlash (positive), classic stick-slip.

**Falsified together** (all measured, not argued): cogging / commutation / worm mesh / belt / U-joint /
resolver (one regression — slope +0.0015 vs a required 0.354 over a 20:1 rate range) · engine order ·
wheel order (7.50 Hz intercept at v = 0; an order passes through the origin) · driver tremor (line is
*bigger* hands-off) · command jitter · ZOH/clock beat.

**There is no pre-existing tone to remove**: 0 of 97 fully-manual windows carry a line; engaged/manual
band power 11.7–13.4×. Engagement supplies the resonance, it does not amplify an existing tone.

See [[accord-4x-lkas-gain-is-the-frozen-variable]] and [[feedback-run-the-control-before-the-measurement]].
