---
name: accord-grinding-is-an-excited-resonance-no-excitation-to-remove
description: "🛑🛑⭐⭐⭐⭐⭐ VERDICT 2026-09-10: the grinding is (C) an EXCITED RESONANCE rung by ordinary broadband noise -- not forced, not a limit cycle. Every excitation candidate is now bounded or dead. The lever is max |1/(1+L)| across the WHOLE 12-26 Hz band, not a notch at one frequency."
metadata:
  node_type: memory
  type: project
---

🛑🛑 **VERDICT, 2026-09-10, from six agents on disjoint surfaces: the grinding is an EXCITED RESONANCE.
There is no excitation to remove that would fix it.** The question *"what excites the ring"* has been
answered, and the answer is *nothing in particular*.

## The decisive measurement — coherence time equals ring-down time

`cyclekind`, 11 routes / 6 builds / 715 episodes. Demodulate the band at its own f0 and measure the
complex-envelope autocorrelation. **A noise-rung damped pole gives |ρ(τ)| = exp(−ζω₀τ) exactly — so
coherence time EQUALS ring-down time. A drive or a limit cycle keeps phase for seconds.**

Measured τ_c: 0.35–0.87 s = **6.5–17.4 cycles**, implied ζ 0.009–0.025, **matching the independently
measured free-decay ζ** on every build. Sham band in the same windows: 0.18–0.38 s.

> **There is no persistent phase, therefore there is no persistent source.**

Four supporting signatures, none using V288 or the comb as an input: **Rice K = 0.00 on every build**
(Rayleigh envelope, no deterministic component, simulated null 0.550 [0.047–0.908]) · **no preferred
amplitude** (CVlog peak 0.64–0.84 *exceeds* CVlog of its own excitation 0.51–0.66 — the ring is BROADER
than what drives it) · **no plateau** (0.26–0.34, identical to band-limited noise) · **no hysteresis**
(null on all seven drive variables, every build) · **no harmonics** (relay-grade 3f₀ excluded by 15–25 dB).

## The census of excitation candidates — all bounded or dead [EVIDENCE]

| candidate | bound | agent |
|---|---|---|
| discrete command kicks (slew-cap binds, idx steps, Δ² spikes, sign reversals) | **≤ 13 %** of burst onsets; cap binds **RR 0.83 [0.69, 0.96]** — *below* chance once the detector opens | `slewburst` |
| road / chassis input | **null**, 30 route×IMU tests; chassis does not carry the mode at all | `slewburst` |
| self-oscillation / limit cycle | **falsified on 5 independent signatures** | `cyclekind` |
| outer loop through openpilot | **\|L\| = 0.026–0.165**, bound 0.096–0.189, ≤ 0.38 adverse; needs 1.0 | `echoloop` |
| steering-angle quantiser echo | **falsified as a coherent link** — residual cmd↔angle coherence **0.022** after removing the camera clock | `combsize` |
| camera comb (modeld's 20 Hz staircase) | **real, and the ONE candidate not bounded small — lock fraction ≈0.50 debiased**; perfect deletion buys **≈29 % amplitude (~3 dB)**. ⚠ But V289 already flew the un-forced case and it got WORSE (confounded) | `combsize` §12 |

**Command side, total:** whole-band ablation through the byte-exact mirror gives the command's *entire*
in-band content = **11.56 of 57.21 counts (20.2 %) on r39/V282**, and **5.21 of 125.86 (4.1 %) on
r63/V289**. The **feedback leg carries 88–100 %** on every route. Comb and echo are **competing
partitions of one command-side budget**, not additive sources.

## ⭐ The grinding is ENGAGEMENT-GATED [EVIDENCE, the session's most operator-legible result]

`echoloop`, 17 cached routes, 6 builds **plus stock**, 20,761 engaged vs 5,905 lateral-disengaged windows.
Load-matched inside speed bins on **both** driver-torque and wheel-rate IQR:

| stratum | engaged | lateral OFF | |
|---|---|---|---|
| 0–4 m/s, load-matched | **0.3617** (bar 267, rate 100) | **0.0108** (bar **376**, rate **205**) | **×33** |
| 4–8 m/s | 0.4986 | 0.0286 | ×17 |
| high demand (idx ≥ 20), 0–4 m/s | — | — | **×72** |

**More driver torque and more wheel motion on the disengaged side, and the line is 33× rarer.** Per-route
disengaged rate **0.000–0.0505 on all 17 routes including stock**. ⇒ The 20 Hz object needs LKAS torque.
🛑 It **cannot separate inner from outer** — `STEER_REQUEST = 0` opens the EPS's own rate loop too; the
|L| bound is what does that. ⚠ Power: decisive at 0–8 m/s; only 120 disengaged windows total at 8–25 m/s;
**zero above 25 m/s in the entire cache.**
🛑 The **shape-only** gate does NOT go to zero disengaged (0.25–0.50 at median f0 **12–14 Hz**) — that is
the low-demand road/plant line, present with the loop open. **The two-object picture holds on this cut.**

## 🛑 WITHDRAWN 2026-09-11 — what used to stand here was a BIASED-ESTIMATOR ARTEFACT

The retracted text claimed *"bar is 34 % camera-locked, the ANGLE only 2 %, so a torque comb barely moves
the column's inertia and openpilot measures the angle"*, and *"speed-matched, the comb SHRINKS while the
ring grows"*. **Both are artefacts of `R2 − floor`, which is biased low by 0.12–0.22 and whose bias scales
with stratum length** — see [[accord-r2-minus-floor-is-biased-low-use-r2-deb]].
**Debiased: the angle is ~40 % camera-locked** (command 0.624 · bar 0.534 · angle 0.401), **and the comb
GROWS ×0.94–1.81** (r39's CI excludes 1 in the *opposite* direction, 1.29 [1.08, 1.59]).
**What survives at true strength: the response outpaces the drive by ×1.3–2.3, not ×2.5–4.0** — consistent
with **partial amplification**, and **not** a "constant driver, varying damping" signature.
⇒ **The synthesis below loses one of its six premises; five remain.**

## What still says the comb is not THE grinding

- ⭐ **The FORCING is FLAT across six builds and three openpilot eras (Δ²cmd fold R 0.267–0.376, null
  0.004–0.043) while the RESPONSE spans ×98** (bar 18–22 Hz energy 4.49e4 → 459). **A driver that does not
  change cannot explain a symptom that changes 98-fold.**
- **V289 moved the mode 3.5 Hz off the forcing and the grinding got LOUDER** — 1.71× r39's on 0.30–0.45×
  the command drive (matched speed × demand). ⚠ Confounded: the notch also spent 30° of margin at 15–17 Hz.
- **`cyclekind`'s five rung-mode signatures** and **`slewburst`'s trigger null** use neither V288 nor the
  comb as an input and are untouched.

## 🛑 WHAT THIS LICENSES — the design law

> **Under (C) the lever is the SENSITIVITY PEAK |1/(1+L)| across the WHOLE 12–26 Hz band, not a notch at
> one frequency. Design against max Ms over 12–26 Hz and PRE-REGISTER THE WHOLE BAND.**

**V289 is the proof and the trap in one drive:** it killed the 20 Hz object completely and spent the 30°
of margin the already-present 15–17 Hz pole had. The 18–22 Hz census gate was blind to exactly what went
wrong. **RULED OUT: drive-hunting, and nonlinearity-hunting** — the D clamp, the sum clamp, the
123/frame slew cap and rack stiction are **not** what sets the amplitude.

## Corrections of record made by this verdict

- **"f0 pinned to +0.4 Hz across Kp 248→696" is NOT supported** — acting Kp is confounded with demand
  index. Identified matched-cell contrast: **+1.80 Hz [−0.02, +4.46]**. Correct statement: *any gain
  effect on f0 is small and poorly determined; the phase effect is large and unambiguous* (−3.78 Hz).
- **f0 falls with vehicle speed** (−0.11 to −0.21 Hz per m/s) and does **not** scale with shaft speed —
  a plant-stiffness signature, which independently kills any external fixed-frequency drive.
- `pid_log.output` is **negated** torque ⇒ the characteristic equation is `1 − P·K = 0`: **the critical
  point is L = +1, the metric is |1 − L|, the critical phase is ~0°, NOT ±180°.**

## Top open item

🛑 **The IMU is the highest-value missing instrument** — every proxy used is a CAN channel from *inside*
the steering system, so none can say whether the residual excitation is road, rack or motor. Cached for
one route only.

Related: [[accord-v288-null-is-void-filter-was-transparent-at-the-ring]] ·
[[accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it]] ·
[[accord-episodes-of-hardcodes-the-18-22hz-gate]] ·
[[accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance-d-dominated]] ·
[[accord-20hz-line-is-plant-mode-clamp-explanation-falsified-two-line-census]]
