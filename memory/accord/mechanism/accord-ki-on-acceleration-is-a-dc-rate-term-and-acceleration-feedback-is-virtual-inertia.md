---
name: accord-ki-on-acceleration-is-a-dc-rate-term-and-acceleration-feedback-is-virtual-inertia
description: "LOOP TERMS 2026-09-30: the integral of acceleration is rate, so Ki on V294's operand (r26 = tick difference of the 2 Hz-lagged rate) is a DC rate term -Ki*omega_lp, BOUNDED by construction (sum r26 telescopes to the lag state), unusable only because 4*sp shares the operand; the plant is spring + damper + Coulomb with J negligible below the b/J corner, so acceleration feedback = virtual INERTIA (nothing at steering frequencies, anti-damping at 20 Hz) and rate feedback = virtual DAMPING (the term Coulomb rides on: V282 creep vs V293 snap); no P-only loop of any quantity breaks a stuck wheel (torque = the map at alpha = omega = 0; V282 had no growing term, the fork's integrator breaks the wheel in every build); do NOT move the fork to command angular acceleration (cannot hold a turn without an EPS double integrator = a fragile angle loop); candidate cave: I reads -r26 only, setpoint stays in P -> DC + washout damping with a free HF/DC ratio Kp*c/Ki."
metadata:
  type: project
---

**EVIDENCE (bytes + r71b plant):** V294 lane: `s = (a·s + b·x)>>10` (a 1011, b 567 → 1050 in V295; pole 2.02 Hz,
DC gain b/13), `r26 = clamp(s_new − s_old, ±1024)`, `E = 4·sp − r26`, `P = (E·Kp)>>8`, Ki 0, Kd 0. Σ_{n} r26 =
s[N] − s[0] (telescoping; the clamp binds only above ~125 deg/s per ms). So an I term on r26 is `−Ki·(s − s_engage)`
= a rate term through the 2 Hz lag, bounded by |s|max. Continuous form: `r26 = dt·ω_p·(ω − ω_lp)` = a WASHOUT
(high-passed rate): acceleration below 2 Hz, rate above. Plant (studies/v295/plant): J ≈ 0.2 T/(deg/s²) (0–5 m/s
only), b 4.9–26 T/(deg/s), k 6.5–80 T/deg, Fc 76 → 4 T with speed; overdamped ζ 1.3–4.

**What follows (BELIEF where marked):**
- Acceleration feedback adds virtual inertia; with J this small it changes nothing below the b/J corner (4 Hz at
  low speed, ~20 Hz at highway speed per the model) and de-damps the 20 Hz mode. Rate feedback adds virtual
  damping, the term that sets post-breakaway motion (V282 creep vs V293 snap, dwell-then-jump 3–23×). V294/V295's
  washout damps only above 2 Hz → the 2–2.7 Hz jerk mode, not the ratchet/looseness below 1 Hz.
- Stuck wheel: α = ω = 0 ⇒ P-only torque = Kp·4·sp = the map, for a torque, rate or acceleration operand alike.
  No V282 term grows on a stuck wheel (an earlier claim that "torque rises at 1 kHz" was WRONG); the fork's 100 Hz
  integrator does the breaking in every build.
- Fork → angular-acceleration command: in a held turn α_des = 0 ⇒ P = 0, I = Ki·(ω_des − ω) ⇒ the hold torque
  must come from an EPS-integrated ω_des the fork cannot see — an angle loop built the fragile way. Worked through
  it collapses to torque mode + 1 kHz rate damping. The torque command IS an angle-like demand on this plant
  (lat-accel ∝ v²·δ = kθ at DC). Keep the torque interface. (2026-09-13 design note: angle if ever.)
- Candidate cave (NOT traced/built): the I accumulate reads −r26 only. P on E = FF + washout; I on −r26 = DC rate
  damping, 2 Hz roll-off. With `ω_lp = ω·ω_p/(s+ω_p)` and `ω − ω_lp = ω·s/(s+ω_p)`, the summed feedback is
  `ω·(Ki·ω_p + Kp·c·s)/(s+ω_p)`: DC gain Ki, HF gain Kp·c, corner ω_p — a lead-lag on rate with a FREE HF/DC
  ratio (Kp·c = Ki ⇒ flat rate feedback to the 5 Hz output lag). Hazards: engage init (accumulator 0 while s may be
  ~10 k counts at 30 deg/s), reset lags disengage 0.1–2.05 s, no wire instrument for the accumulator.

Related: [[feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify]], [[accord-lkas-pid-ki-integrates-the-command-and-taper-axis-is-driver-torque]],
[[accord-literal-cmd-vs-alpha-metric-is-fork-dominated-plant-overdamped]], [[accord-v294-flew-r71b-v295-trim-gain-x1852-built]].
