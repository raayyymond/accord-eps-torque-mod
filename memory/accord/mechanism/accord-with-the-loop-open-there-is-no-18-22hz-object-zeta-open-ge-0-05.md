---
name: accord-with-the-loop-open-there-is-no-18-22hz-object-zeta-open-ge-0-05
description: "🛑🛑⭐⭐⭐⭐⭐ MEASURED 2026-09-13 (35 routes, 4,759 s lateral-disengaged): with the LKAS rate loop OPEN there is NO 18–22 Hz object at all — pooled spectrum has no resonance (prominence 1.00/1.25, below a no-mode control); a mode of ζ ≤ 0.03 carrying the same energy WOULD have been found ⇒ ζ_open ≥ 0.05 or non-modal. Load-matched amplitude ratio OFF/engaged 0.21 (×4.5); V289's relocated 16 Hz ring is ALSO engagement-gated; V289's notch removed the 20 Hz mode outright. The T ring's drive on V282 is 88 % LINEAR rate feedback, 20 % command, 0.35 % quantiser kicks."
metadata:
  node_type: memory
  type: project
---

**The 18–22 Hz grinding object is a creature of the CLOSED engaged loop.** Subagent `openloop`,
2026-09-13, `rlog-tools/studies/grind/OPENLOOP-RING-DAMPING-2026-09-13.md`.

- **[EVIDENCE]** Lateral-disengaged (STEER_REQUEST = 0, which opens the EPS rate loop AND the engaged-only
  r24 lane), 35 cached routes, 4,759 s in ≥ 10.24 s segments (3,696 s at 0–4 m/s, 119 segments): pooled
  Welch carries **no resonance in 16–26 Hz** — Lorentzian bump 1.56 (bar) / 1.14 (rate), model-free
  prominence 1.00 / 1.25, both **below** the 1.26–1.48 a synthetic no-mode control returns. Engaged at the
  same speeds: bump 20.4 / 22.5, ζ 0.0356 [0.023, 0.057] at 21.5 Hz; **V282 alone ζ = 0.0164 [0.0126, 0.0222]**
  at 20.01 Hz — an independent estimator landing inside the record's coherence-time range.
- **[EVIDENCE] The bound:** replacing the measured open-loop 18–22 Hz energy with a synthetic mode of known ζ
  at the same amplitude is **detected for ζ ≤ 0.03 and invisible from ζ ≥ 0.05** ⇒ **ζ_open ≥ 0.05**, and the
  real data's prominence sits below even a ζ = 0.5 mode carrying all the energy — the open-loop content is
  the broadband continuum.
- **Not the same object weakly:** only 24 % of disengaged 12–26 Hz lines sit in 18–22 (engaged 59 %); the
  level gate reads 0.0009 vs 0.4247 (×451); 0.000 on 27 of 35 routes.
- **Amplitude, load-matched (both bar-rms and rate-rms IQR):** OFF/engaged **0.2145 [0.204, 0.227]** on bar,
  **0.2217** on rate at 0–4 m/s; vs the 26–34 Hz neighbour band (0.686 / 0.559) the mode-specific
  suppression is **×2.5–3.2**. The record's ×33–72 is a PRESENCE RATE across a 40-raw gate at the engaged
  median — both numbers are right, they are different claims.
- ⭐ **V289's 15–17 Hz ring is ALSO engagement-gated** (engaged bump 11.2, ζ 0.040; loop-open bump 1.52,
  prom 0.73 on 467 s) — the pole that took V289's margin is another closed-loop object, not a plant mode.
- ⭐ **V289's notch = an in-situ loop-opening at 20 Hz on the car**: 18–23 Hz reads NO LINE (bump 2.78) vs
  V282's LINE (ζ 0.012, bump 6.6) — cutting the loop at 20 Hz removed the 20 Hz mode outright.
- 🛑 **The limit:** STEER_REQUEST = 0 removes the LKAS excitation with the loop, so "no object" has two
  readings — ζ_open ≥ 0.05, or a low-ζ mode that only LKAS torque excites. The matched disengaged windows
  carry MORE driver torque (446 vs 419 rms) and MORE wheel motion (238 vs 138) and 0.4 deg/s of broadband
  18–22 Hz rate to feed on, which narrows but does not refute reading 2. **Both readings say the same
  thing for a build: opening the loop above ~8 Hz removes the object.**
- **Estimator corrections:** `design290d_anchors.decay()` (DESIGN-V290B §A.2's per-build ζ) returns
  0.036–0.040 for band-limited noise with NO mode and for every true ζ 0.05–0.30 — it cannot resolve ζ;
  the coherence-time method is sound for ζ 0.02–0.05 and saturates above (0.053 on no mode). The 12–14 Hz
  "road/plant line" is a short-window prominence, not a resolvable resonance on either label.
- **Drive decomposition (byte-exact mirror, r39):** feedback leg 0.879 of the T ring, command 0.202, one
  quantiser step of dither 0.003 — the ring is **~16 LSB on the 0x18F rate channel** (1.98 deg/s); the
  0.17–0.28 LSB figure was the 0x14A ANGLE channel openpilot reads. See
  [[accord-the-ring-is-16-rate-lsb-not-sub-lsb-unit-trap]].

Related: [[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]] ·
[[accord-v291-c10-built-fb-pole-10hz-plus-r24-cut-loop-opening-class]] ·
[[accord-fb-pole-down-class-does-everything-but-fails-the-7hz-gate-r24-arm-is-the-blocker]]
