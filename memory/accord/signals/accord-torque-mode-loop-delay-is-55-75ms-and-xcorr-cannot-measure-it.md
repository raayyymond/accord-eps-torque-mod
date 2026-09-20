# Torque-mode loop delay is 55–75 ms at 2.5 Hz, and a command↔acceleration xcorr CANNOT measure it

**Measured 2026-09-19** (`rlog-tools/studies/v282-reference/delay/`, workflow `wf_eae14cc9-dc0`: four independent
estimators each gated on recovering a known 30 ms **and** 60 ms from a synthetic plant driven by the real logged command,
then adjudication and an adversarial re-derivation).

| quantity | value | grade |
|---|---|---|
| `D_ctl` measured sample → its command on the bus | **11.0 ms** [10.9, 11.1], flat in speed, identical on V282 | EVIDENCE |
| `D_act` floor at 2.5 Hz (0xE4 → effect in carState) | **43.3 ms** = 24.8 ms transport + a 5 Hz pole | EVIDENCE for the legs covered |
| **`D_loop` at 2.5 Hz** | **54.3 ms floor; ~72 ms if the unmeasured post-tap stage is ~18 ms. Bracket 55–75, point 65.** | EVIDENCE + BELIEF |

`D_loop` is **frequency-dependent** (the actuation law is a pole, not pure transport) and **flat in speed** — so the kit's
measured speed-dependent lateral lag (0.15 s motorway → 0.25 s at 3–8 m/s) is plant/friction, **not** transport.

Chain, all value-matched: 0x14A arrives → carState +2.6 ms (but the sample is already 7.59 ms old, pandad poll aggregation)
→ controlsState +4.6–5.2 → carControl +0.25 → sendcan +5.6–6.2 → on bus +2.36 → firmware torque variable (427 tap) +3.8 ms
and a **5 Hz pole** (independently recovers the firmware's own output-lag cell 992/1024 = 5.05 Hz). Each 0xE4 carries the
command computed from the **previous** carState; the 11.0 ms counts that staleness exactly once.

## 🛑 The trap: a 1–6 Hz xcorr of command vs steering acceleration is NOT a delay

Put a **known 30 ms** through that recipe and it returns **1 ms at J = 1e-3 and 127 ms at J = 8e-5** — the bias spans
−29 to +107 ms and **flips sign with J**, the disputed parameter. It also fails once feedback and road disturbance are both
present, which is how the car runs. An orchestrator quoted 30 ms from it and had to withdraw it. The same statistic on a
V282 route (EPS rate servo) returns −5 to +21 ms, where the question is meaningless — use that as the discrimination control.

**What works:** an equation-error delay sweep (`u(t−D) = J·acc + b·rate + k·angle + F·sgn(rate)`, controls passed) as an
upper bound, and the message/CAN-chain decomposition through the firmware tap (no plant model) as a floor.

## Collateral corrections

- **`HONDA_ACCORD_EPS_INERTIA = 8e-5` is RIGHT within 25%.** Two estimators with passing controls put J = 5.7–7.3e-5 in
  every speed bin. The earlier 0.25 s-replay fit of J = 8e-4…2e-3 is **~15× too large** — withdrawn (it was BELIEF, never acted on).
- Same fits: b ≈ 7.1e-4 at <8 m/s falling ~10× by ≥15 m/s; F ≈ 0.020 at <8 m/s, matching `HONDA_ACCORD_HOLD_STATIC_FRICTION`.
  This conflicts with the earlier "identified world b = 0.0018–0.0049" replay result — unresolved; the delay error in that
  replay is the likely cause.
- **The fork's own `46–61 ms` comment is essentially confirmed** (structure right, mis-splits ~5 ms twice, total the best of
  the three inherited numbers). `HONDA_ACCORD_RATE_LOOP_RC = 0.01 s` **stands**.
- **"at 0.0012 it would cross [−180°]" is ~2× pessimistic**: |L| at the 3.5–4.9 Hz crossing is 0.34–0.57 at 0.0012, i.e.
  gain margin 1.8–2.9 — a halved margin, not a crossing. Arithmetic permits at most ~×1.5 (0.0006 → 0.0009).

## What it decides

Fraction of `AccordRateLoopGain` arriving as real damping (through `D_loop` + the 0.01 s rate filter): **+0.47 at 2.5 Hz at
the floor, +0.24 at 72 ms**, negative at 4–6 Hz at every `D_loop` in the bracket; damping boundary 4.08 → 3.08 Hz.
⇒ low-speed rate-loop gain is a **weak lever, not a dead one** — and the "dead" reading rests on the *unmeasured* 12–18 ms,
not on the measured floor (the adversary's correction). The low-speed candidate therefore becomes reference shaping below
8 m/s (no added loop gain, delay-independent, reach ceiling ~half the shake).

Only a signal **downstream of the firmware's torque variable** — the EPS's own current/torque telemetry, or a deliberate
logged dither on 0xE4 — can close the remaining 12–18 ms. No re-analysis of existing logs can.

**Unaffected: ARM-D.** The logged observer torque feeds the 1.5–3.5 Hz shake band in **64 of 64 cells** (every τ from 0 to
120 ms × every speed bin × all four observer routes), so that rationale never depended on the delay.
