---
name: accord-the-20hz-forcing-comb-is-real-and-half-the-rings-energy-is-locked-to-it
description: "🛑⭐⭐⭐⭐⭐ A real 20 Hz forcing comb IS on the 0xE4 command on every build -- modeld's 19.99974 Hz staircase, never smoothed because clip_curvature NEVER binds (0.000). CORRECTED 2026-09-11: lock fraction is ~0.50, not 3.5-14.5%; perfect deletion buys ~29% amplitude (~3 dB). But V289 already flew the un-forced case and it got WORSE (confounded)."
metadata:
  node_type: memory
  type: project
---

**There is a large, genuine 20 Hz forcing comb on openpilot's `0xE4` command, on every build including
the stock-map era, and this kit did not know it was there.** Found 2026-09-10. It is **not** the
grinding — see [[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]] — but it is real and
it is worth writing down.

## The comb [EVIDENCE]

- **`modeld` publishes at 19.99974 Hz**, fixed to ±0.0006 Hz across six routes (camera crystal, not a
  software rate — fits on `timestampEof` and `logMonoTime` agree to 3e-11 s/frame). **Zero frame drops**,
  `frameDropPerc` 0.0, `frameAge` 0, `modelExecutionTime` 34 ms. It does not vary, so *"does the ring
  track modeld"* has no lever to pull.
- 🛑 **`clip_curvature` NEVER rate-limits — binding fraction 0.000 in every route × stratum**, tested by
  direct equality against its own bound `MAX_LATERAL_JERK·jerk_factor/v²·DT_CTRL`.
  **`docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md` §2.1 is FALSE IN PRACTICE**: it claims
  clip_curvature "removes the raw staircase discontinuity before the PID ever sees it." It does not.
  **60–71 % of engaged ticks at v < 12 m/s carry `modelV2.action.desiredCurvature` bit-for-bit.**
- **`Δ²cmd` carries a line at f_model at 41–69× the local 14–26 Hz background** in grinding windows
  (r22 66.5 · r39 41.1 · r5e 56.7 · r62 38.6 · r63 68.8), against 2.4–9.8 in quiet.
  🛑 **H2 could never have seen this** — it tested the FIRST difference and value-repeat statistics, and
  a knotted ramp passes those trivially. **The signature of a knotted ramp is in the SECOND difference.**
- **Phase-locked to the camera clock**: model-phase fold of |Δ²cmd| beats its own detuned null **10–90×**
  on every build, both strata. Command locked fraction 19–33 % (R2 − measured floor +0.21 to +0.29).

## Why it is still not THE grinding — the arguments that survive debiasing

🛑 **Two arguments that used to sit here are WITHDRAWN** (biased estimator): *"the ring is NOT
camera-locked (0.035–0.145)"* — debiased it is **≈0.50** — and *"speed-matched the comb SHRINKS while the
ring grows"* — debiased the comb **grows** ×0.94–1.81. **What survives, and it is enough:**

- ⭐ **The FORCING is FLAT while the RESPONSE spans ×98.** Δ²cmd fold R = 0.267–0.376 (null 0.004–0.043)
  across six builds and three openpilot eras, while bar's 18–22 Hz energy runs 4.49e4 → 459. **A driver
  that does not change cannot explain a symptom that changes 98-fold.**
- ⭐ **The response outpaces the drive** — ring ×1.62–2.68 against comb ×0.94–1.81, i.e. **×1.3–2.3 more
  response than drive.** (This is the debiased remnant of the withdrawn claim; it is *consistent with
  partial amplification*, **not** a "constant driver" signature.)
- **V289 separates the two objects**: the ring moved to 16.46/16.55 Hz while modeld stayed at 19.9995 Hz.
  ⇒ On every pre-V289 build the loop's own mode and modeld's frame rate **coincide to 0.1 Hz**
  (20.07/20.10/20.11 vs 20.02) — **a coincidence, not a mechanism**, and it is what made the comb look
  causal. **V289 moved the mode 3.5 Hz away from the forcing and the grinding got LOUDER.**
- **`cyclekind`'s five rung-mode signatures** (coherence time = ring-down time, Rice K = 0.00, no preferred
  amplitude, no plateau, no hysteresis) use **neither** V288 nor the comb as an input and are untouched.
- **`slewburst`'s trigger null** (≤13 % of onsets, cap binds RR 0.83 [0.69, 0.96]) is untouched.

## ⭐ The actionable number — CORRECTED 2026-09-11

🛑 **An earlier version of this note said 3–8 %. That rested on a BIASED ESTIMATOR and is RETRACTED.**
`R2 − floor` is biased low by 0.12–0.22 (noise adds in power; subtracting a floor in amplitude
over-subtracts). **Debiased, the lock fraction is ≈0.50**, and all three agents' published numbers
reconcile once each one's bias is restored. See [[accord-r2-minus-floor-is-biased-low-use-r2-deb]].

⇒ **At lock 0.50, perfectly deleting the comb cuts ring amplitude by 1 − √(1−0.50) = ≈29 %, ~3 dB.**
That is inside the readable range, unlike the retracted 3 %.

🛑 **TWO COUNTERWEIGHTS OF EQUAL WEIGHT, and the first is the reason not to act on the 29 % yet:**
1. **V289 is ALREADY the flown version of "remove the coherent 20 Hz forcing", and the symptom got WORSE.**
   Its relocated 16.5 Hz ring carries **0.000** camera lock and is **1.71×** r39's (matched speed × demand)
   on **0.30–0.45×** the command drive. ⚠ **Confounded** — the notch also spent 30° of margin at 15–17 Hz —
   so not a clean refutation, but it is the only configuration ever flown with no coherent forcing and it
   went the wrong way.
2. **The 29 % assumes the locked energy VANISHES.** If the mode is rung by whatever broadband excitation
   remains at unchanged loop gain, the ring returns lower but non-zero. **Nothing measures that.**
   ⇒ **The transient test** (`docs/specs/design/SPEC-COMB-TRANSIENT-TEST-2026-09-10.md`) — interrupt or
   phase-step the comb for one model frame and time the envelope decay — **is the only experiment that
   would.** Zero authority, zero lag, no flash.

⚠ **Two findings in the earlier version of this note are WITHDRAWN**, both artefacts of the biased
estimator: *"the comb does not grow when the car grinds"* (debiased it **does** grow, ×0.94–1.81, and
r39's CI excludes 1 in the **opposite** direction — what survives is that the response outpaces the drive
by ×1.3–2.3) and *"bar is 34 % camera-locked while the ANGLE is only 2 %, so a torque comb barely moves
the column"* (**the angle is ~40 % locked**; the column-inertia explanation goes with it).

## If it is ever done: the lag-free forms

The operator has **forbidden a command LPF** (see [[feedback-no-openpilot-side-modifications]]) and he is
right on the numbers — the colleagues' filter costs 100–280 ms of group delay and −32° to −59° at 1 Hz.
Lag-free alternatives, in order:
1. **Slope extrapolation from the last two model frames — zero lag.**
2. ⭐ **Trajectory-shaped reconstruction — LAG-NEGATIVE by up to 50 ms.** `modelV2.orientationRate` is a
   full XYZTData with its own t axis, already converted live at `longitudinal_planner.py:682`. Sampling
   at *now* rather than at the frame timestamp leads a ZOH. ⚠ It is the PLAN, a different object from the
   ACTION head — the minimal correct form keeps `action.desiredCurvature` as the per-frame anchor and
   uses the plan only for intra-frame SHAPE.
3. Linear interpolation between two received frames — **costs +50 ms**, he would reject it.
4. ⚠ Linear extrapolation alone: Δ 0.24 when the model is clean but **1.14 (WORSE) when innovation is
   large** — derivative noise amplification.
- `modeld` already applies `smooth_value(..., LAT_SMOOTH_SECONDS = 0.1)` at `modeld.py:346,375`, and
  `lat_delay` adds it back as lead — self-compensating.

## Two clock facts worth keeping

- **The device's own `0xE4` tx counter fits 99.53–99.56 Hz, not 100** — anything read on that axis at a
  nominal 0.01 s is biased **0.45 % high.** Use the fitted period.
- **The v280 CAN caches store raw `logMonoTime` seconds with no t0 subtracted**, so modelV2 publish times
  and CAN receive times are already one clock. The EPS `0x18F` stream is within **0.008 %** of the device
  clock, so a 20.03-vs-20.00 gap is **not** a clock artefact.

## ⚠ Method trap, paid for twice this session

**R2's null floor scales as 1/√N_eff, so a low R2 on a short stratum is a NON-DETECTION, not a zero.**
`modelrate` had to retract a V288 claim for exactly this (98.9 s stratum, floor 0.455, reading 0.333 —
below its own floor). And **a detuned-clock null does not collapse unless |Δf|·T ≫ 1**: at 3 s windows
and Δf 0.37 Hz the floor sat at 84 % of signal. Use **12 s+ windows**, a **measured** floor (max over
detuned clocks), the **bias-corrected** estimator `R2_deb = √(max(R2² − mean(R2²_detuned), 0))`, and
**state N_eff per stratum.**
🛑 And the detector itself: **the plain circular mean FAILS its own positive control** — a staircase's
20 Hz component is a sawtooth whose amplitude flips sign with the plan's slope, so the phase hops by π
and the mean cancels. **Use the square law, R2 = |Σ z²e^(−2iθ)|/Σ|z|², which locks modulo π and equals
the locked fraction of in-band energy exactly.**

Related: [[accord-grinding-is-an-excited-resonance-no-excitation-to-remove]] ·
[[accord-v288-null-is-void-filter-was-transparent-at-the-ring]] ·
[[accord-0xe4-command-is-not-a-staircase-slew-cap-is-the-excitation-grind1-is-a-rung-bell]] ·
[[accord-h1-torque-table-resolution-is-false-map-scale-is-a-gain-effect]]
