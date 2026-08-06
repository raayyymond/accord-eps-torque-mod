# ★★★ THE 7.8 Hz MICRO RATCHET — Q ≈ 14, a ring-down, load-dependent f0, and NO trigger

**Measured 2026-08-05 (session data agents).** This **supersedes the recorded Q ≈ 40**, which was a
window artefact of the earlier estimator. The mode is the thing the operator calls the *micro* ratchet —
*"not audible, felt in the column"*, correct because **7.8 Hz is below the ~20 Hz hearing threshold**.

## What it is — [EVIDENCE]

- **Q ≈ 14** at f0 ≈ 7.79 Hz. Supersedes Q ≈ 40 ([[accord-ratchet-q-measured-40]] is amended).
- **A ring-down**, not a sustained limit cycle — it decays rather than self-sustaining.
- **f0 FALLS with load.** This is what kills the stick-slip reading: stick-slip has a harmonic series and
  a trigger, and this has **neither**.
- **Engagement-required**, hands-off-conditional: pooled 73/88 = 83.0% engaged hands-off vs
  **0/118 = 0.0%** manual hands-off, Fisher p = 3.8e-41, build-independent.
- 🛑 **No build in this kit has ever moved it** — V72 included (attenuation 1.0, three instruments).

## 🛑 Why the firmware cannot be generating the rate

**The scheduler is mod-100**, so only **{1000, 500, 200, 100, 10} Hz** are reachable. **A 7.8 Hz
firmware divider does not exist** — struck 2026-08-05. The mode is a **plant resonance the firmware
sustains or fails to damp**, not a cadence the firmware emits.

## The friction lane's transfer at this frequency — 🛑 CORRECTED FIGURES

Any analysis quoting **"−14.5 dB / +4.4°"** for `gp-0x6c2c` into the friction lane is **stale and
wrong**. The correct values:

| frequency | gain |
|---|---|
| **7.79 Hz** | **3.08× = +9.8 dB** |
| **20.9 Hz** | **7.496×** |

⇒ The lane **amplifies** at both symptom frequencies rather than attenuating. Any ladder or sizing built
on the −14.5 dB figure is void and must be re-derived. (Recorded here because the two memories that
carried the stale number — a `reference_accord_friction_lane_fun36c12…` and a
`reference_accord_gp6b26_friction_lane_damping_candidate` — **do not exist in this repo**; if they turn
up in another store, correct them against this file.)

## Why there has never been damping at its speeds

Both dead zones bite: FactorC's speed dead zone (`X[0]` = 2240 = 35 km/h on the live modes) and
FactorE's rate dead zone (`X[0]` = 60). See [[reference-accord-two-dead-zones-speed-and-rate]].
⚠ **`gp-0x6ac0` in-burst is 99 counts [94, 113]** — inside FactorE's dead zone (`X[0]` = 60), on its
first rising segment. At that rate a `FactorC Y[0]` raise alone delivers **6** against a requirement of
~43 [30, 60], so it is homeopathic; **opening the rate dead zone is the lever** (both zones open ⇒ ~50, at `FactorE X[0]: 60 → 12`).

## ⚠ Distinguish MICRO from MACRO

**MACRO** is the large ratchet the operator reports as fixed on V72. It is **unmeasured and
unattributed** — both purpose-built instruments fail their own positive control, so the null is
uninterpretable in both directions. The r26 correlation is a **leading hypothesis only**; see
[[reference-accord-v42-fix-was-the-r26-kill]].

Related: [[accord-two-ratchets-micro-is-the-779hz-line]], [[accord-ratchet-is-engagement-required]],
[[accord-ratchet-characterised-on-route-4f]], [[accord-ratchet-is-a-saturated-resonance]].
