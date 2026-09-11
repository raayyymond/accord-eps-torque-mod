# Is the ~20 Hz grinding line a FORCED response to `modeld`'s 20 Hz frame cadence?

**Subagent `modelrate`, 2026-09-10. ANALYSIS ONLY — nothing built, nothing flashed, nothing sent on any bus.**

Routes: **r22** (V112, stock map ×1) · **r39** (V282) · **r5e_v288** (V288 rev 2) · **r62_v289 / r63_v289**
(V289 rev 1). All rlogs already on disk; nothing re-downloaded. 82 segments parsed.

Routes, second pass: **r35 (V281 rev 3)** added — six builds, V112 → V289, 101 segments.

Scripts: `modeld_cadence_extract.py` (timing extractor) · `modeld_cadence_vs_ring.py` (§1–§4) ·
`modeld_phase_lock.py` (the square-law detector) · `modeld_comb_decompose.py` (§5′–§6′, the
decomposition that decides it). Outputs in `_scratch/modeld_cadence_vs_ring.txt`,
`_scratch/modeld_phase_lock.txt`, `_scratch/modeld_comb_decompose.txt`; caches in
`_scratch/modeld/<tag>_cad.npz`; the step/hold arrays for `combsize` in
`_scratch/modeld_comb_for_combsize.npz`.

---

## VERDICT — **REVISED 2026-09-10, second pass. The first pass is RETRACTED in part; read §0.**

> **Both mechanisms are real and they are not alternatives.** A **constant, upstream, camera-locked
> 20 Hz forcing comb** exists on the command on *every* build (unchanged across six images spanning
> V112 → V289), and the EPS carries a **lightly damped ~20 Hz loop mode** that amplifies it. The
> grinding on V112 / V281r3 / V282 / V288 is the **product of the two**: on those builds
> **20–62 % of the grinding EXCESS energy in delivered driver torque is phase-locked to the camera
> clock.** What `modeld` does **not** set is the **frequency** — that is the plant's, which is why
> V289's notch moved the line to 16.5 Hz, where the camera-locked fraction is **exactly 0.000**.
>
> **The comb has never been removed on this car.** V289 removed the *mode*; nothing has ever removed
> the *excitation*.

Load-bearing evidence, in order:

| # | finding | where |
|---|---|---|
| 1 | The forcing is **identical on all six builds** (|Δ²cmd| model-phase fold R = 0.267–0.376, null 0.004–0.043) while the bar's 18–22 Hz response varies **×98** (4.49e4 → 459) | §5′.3 |
| 2 | On V289 the forcing is unchanged (0.368 / 0.371) and the response **collapses** (bar `R2_deb` 0.50 → 0.076 / 0.000) | §5′.3 |
| 3 | ⭐ **The ring MOVED to 16.47/16.48 Hz while `modeld` sat at 19.9995 Hz on those same routes** — a rejection with the CI excluding `f_model` by 3.5 Hz. **A forced line cannot sit 3.5 Hz off its forcing frequency**; this is physical, not statistical, and is the single strongest falsification here. The relocated line's zero camera content (`R2_deb` 0.0000, vs 35–66 % coherence with the wheel angle) is supporting-only. | §4, §5′.2 |
| 4 | 20–62 % of the grinding **excess** in bar is camera-locked on the four pre-V289 builds | §5′.2 |
| 5 | The plan is a **pure ZOH** — in-hold deviation exactly 0.000e+00 on every route — so the knot is a pure slope discontinuity | §5′.1 |
| 6 | `clip_curvature` **never** binds (0.000), so every knot is the staircase stepping | §2 |
| 7 | The STRONG "kick sets the episode rate" reading is **excluded** — V288 / V282 rate ratio **1.079 [0.605, 2.683]** engaged, **1.303 [0.809, 1.945]** in the matched v<12 regime; a 50 % reduction is excluded at p ≤ 0.006 | §10′ |

🛑 **NOT load-bearing, and must not be reported as a match:** the frequency comparison of §4. "Every CI
contains 19.9997" is a **failure to reject**, and those CIs are wide (r22 spans 19.93–20.97). The
phase-lock result is what carries this, not the frequency agreement.

## §0. WHAT I RETRACT FROM THE FIRST PASS, AND WHY

The first pass concluded "the grinding is NOT the forced response" on three falsifications.
**Two of them do not survive bias correction and I withdraw them.** The error is mine, and it is a
statistics error, not a measurement error.

`R2`'s null floor scales as **1/√N_eff**, and the strata are wildly unequal (r39 grinding 182.0 s,
measured floor 0.161; r5e grinding 98.9 s, floor 0.455; r63 quiet 30.7 s, floor 0.310). I compared raw
`R2` across those strata and **read non-detections as zeros.** Everything below uses the standard
coherence debiasing, which is sample-size robust:

```
R2_deb = sqrt( max( R2² − mean(R2²_detuned) , 0 ) )        70 detunings, |δ| ∈ [0.10, 0.80] Hz
```

| first-pass claim | status after debiasing |
|---|---|
| "V112: forcing present, response unlocked (bar −0.082)" | ❌ **RETRACTED** — bar `R2_deb` = **0.195**; 20 % of its grinding excess is camera-locked |
| "V288 removed the forced component from delivered torque (bar → −0.012 / −0.122)" | ❌ **RETRACTED** — bar `R2_deb` = **0.292**; 30 % of its grinding excess is camera-locked. The orchestrator's separate finding that V288's null is VOID (non-LTI cave, 1–7 % band attenuation, not 54 %) points the same way and I accept it. |
| "V289: line 3.5 Hz off `f_model`, zero locked fraction at 13–18 Hz" | ✅ **STANDS** — and is now better explained: the notch removed the *response*, not the forcing |

⚠ **Do not quote the first pass's §5/§6 tables.** They are superseded by §5′/§6′ below. Raw `R2` is
printed beside `R2_deb` throughout so the correction is auditable.


---

## 1. `modeld`'s actual cadence [EVIDENCE]

Least-squares fit of the message clock on `modelV2.frameId`, per route. Method: every timestamp is
`evt.logMonoTime * 1e-9`; `timestampEof` is the camera's own end-of-frame stamp.

| route | build | N | span s | f from `logMonoTime` | f from `timestampEof` | `dfid != 1` |
|---|---|---|---|---|---|---|
| r22 | V112 (stock map) | 14 242 | 712.1 | **19.999741** ± 0.000001 | 19.999727 ± 0.000000 | 1 |
| r39 | V282 | 18 829 | 941.5 | **19.999719** ± 0.000000 | 19.999709 ± 0.000000 | 1 |
| r5e_v288 | V288 rev 2 | 17 233 | 861.7 | **19.998566** ± 0.000000 | 19.998569 ± 0.000000 | 1 |
| r62_v289 | V289 rev 1 | 19 384 | 969.3 | **19.999537** ± 0.000002 | 19.999536 ± 0.000002 | 1 |
| r63_v289 | V289 rev 1 | 13 982 | 699.0 | **19.999713** ± 0.000001 | 19.999713 ± 0.000000 | 0 |

- `frameDropPerc` **0.0** and `frameAge` **0** on every message of every route. `modelExecutionTime`
  32.3–34.4 ms. `dt` p1–p99 47.7–52.3 ms.
- The `timestampEof` fit and the `logMonoTime` fit agree to **3 × 10⁻¹¹ s/frame**, so this is the
  camera crystal, not a software ratekeeper.
- 🛑 **modeld does not vary route to route** — spread ±0.0006 Hz across five routes and three openpilot
  eras. **So "does the ring TRACK modeld" has no lever to pull**: there is nothing to track.

Other rates on the same clock (N/span):

| route | livePose | cameraOdometry | roadCameraState | controlsState | carControl | carOutput |
|---|---|---|---|---|---|---|
| r22 | 19.9990 | 19.9983 | 19.9997 | 99.567 | 99.566 | 99.503 |
| r39 | 19.9989 | 19.9981 | 19.9997 | 99.568 | 99.568 | 99.522 |
| r5e_v288 | 19.9976 | 19.9968 | 19.9988 | 99.571 | 99.571 | 99.534 |
| r62_v289 | 19.9981 | 19.9977 | 19.9993 | 99.582 | 99.582 | 99.529 |
| r63_v289 | 20.0009 | 20.0000 | 19.9997 | 99.577 | 99.577 | 99.525 |

**`livePose` is also 20 Hz** — but it is *not* the torque controller's measurement.
`latcontrol_torque.py:237`: `measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg - ...))`
— the **100 Hz unfiltered steering angle**, exactly as `STATE.md`'s fork-side echo note says.
`livePose`/`liveParameters` supply only `params.roll`. ⚠ **BELIEF, not tested here:** `liveParameters`
also publishes at 20 Hz (message census: 1200 per 60 s segment), and `roll` is read at 100 Hz into both
`clip_curvature` and the controller's `roll_compensation` — so there is a *second* 20 Hz staircase
entering the setpoint on the same clock. I did not extract it.

### Clock reconciliation [EVIDENCE] — done explicitly, because this is a 0.3 % frequency comparison

- The v280 CAN caches store **raw `logMonoTime` seconds** — `extract_r39_v280cache.py` appends
  `tm = evt.logMonoTime*1e-9` and subtracts no `t0`. So **modelV2 publish times and CAN receive times
  are already one clock with one zero.** No offset is applied anywhere in this study.
- Each CAN stream is put back on its own nominal frame counter by `creep20_loop_id.dejitter`, which
  **fits** the period **in device seconds per frame**:

| route | P18 (EPS 0x18F) | → Hz | Pe4 (device tx) | → Hz | P1ab (EPS) | → Hz |
|---|---|---|---|---|---|---|
| r22 | 0.01000049 | 99.99507 | 0.01004683 | 99.53388 | 0.02000043 | 49.99892 |
| r39 | 0.01000011 | 99.99889 | 0.01004526 | 99.54946 | 0.02000020 | 49.99950 |
| r5e_v288 | 0.01000082 | 99.99182 | 0.01004443 | 99.55766 | 0.02000191 | 49.99523 |
| r62_v289 | 0.01000028 | 99.99717 | 0.01004512 | 99.55078 | 0.02000061 | 49.99849 |
| r63_v289 | 0.01000023 | 99.99770 | 0.01004441 | 99.55786 | 0.02000046 | 49.99884 |

- **The EPS 0x18F clock — the channel every grinding frequency in this kit is measured on — is within
  0.008 % of the device clock.** A line read at 20.03 Hz on the k18 axis is 20.03 Hz ± 0.002 Hz in
  device seconds. **The 20.03-vs-20.00 gap is not a clock artefact.**
- 🛑 **The device's own 0xE4 transmit counter fits 99.53–99.56 Hz, not 100** — controlsd's `Ratekeeper`
  slips ~0.45 % low. Anything read on the 0xE4 counter axis at a nominal 100 Hz is biased 0.45 % high.
  Everything here uses the fitted `Pe4`.

---

## 2. What controlsd actually emits — and a correction to the record [EVIDENCE]

`controlsState.desiredCurvature` is the post-`clip_curvature` value
(`controlsd.py:803-806`). Hold length = consecutive 100 Hz ticks with a bit-identical float; a pure
20 Hz staircase gives 5, a rate-limited ramp gives 1.

| route | stratum | ticks | h=1 | h=4 | h=5 | h=6 | **bind frac** | **passthru** |
|---|---|---|---|---|---|---|---|---|
| r22 | eng v<12 | 17 531 | 0.679 | 0.030 | 0.261 | 0.008 | **0.000** | 0.598 |
| r39 | eng v<12 | 58 202 | 0.580 | 0.035 | **0.361** | 0.013 | **0.000** | 0.695 |
| r5e_v288 | eng v<12 | 25 583 | 0.547 | 0.053 | **0.367** | 0.015 | **0.000** | 0.713 |
| r62_v289 | eng v<12 | 23 667 | 0.596 | 0.033 | **0.346** | 0.012 | **0.000** | 0.677 |
| r63_v289 | eng v<12 | 17 481 | 0.602 | 0.065 | **0.301** | 0.013 | **0.000** | 0.683 |
| r39 | eng v≥12 | 29 437 | 0.922 | 0.009 | 0.057 | 0.002 | **0.000** | 0.235 |

🛑 **`clip_curvature` NEVER rate-limits.** Binding fraction is **0.000** in every route × stratum,
tested by direct equality of `|Δ desiredCurvature|` against its own bound
`MAX_LATERAL_JERK · jerk_factor / v_ego² · DT_CTRL` (`drive_helpers.py:25-31`, `MAX_LATERAL_JERK = 5.0`).
**It is not the smoother `STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md` §2.1 credits it with being** —
that section says it "removes the raw staircase discontinuity before the PID ever sees it", and it only
does that when it binds, which on these routes is never.

**Exact pass-through** (`desiredCurvature` bit-identical to the latest `modelV2.action.desiredCurvature`)
is **0.60–0.71 of engaged ticks at v < 12 m/s** — the raw 20 Hz staircase reaches the PID undigested.

⚠ **BELIEF** for the non-pass-through remainder: `self.lane_centering.update(...)` (`controlsd.py:757`)
adds a 100 Hz first-order correction (τ = 0.4 s, gain 0.30, cap 0.004 1/m) and the operator's decoded
toggle backup has `LaneCentering = True`, `LaneCenteringE2EAuthority = 1.0`. It is inactive below
`_MIN_V_EGO = 5.0`, so the low-speed h=1 ticks must come from something else (the low-speed turn-hold
ratchet at `controlsd.py:745-755`, or `limit_curvature_to_plan`). **I did not verify which.** ⚠ r22
predates the 2026-09-03 toggle backup; its fork configuration is unverified.

**Positive control** — 5-bin fold of `|Δ²(desiredCurvature)|` on the model frame phase
(C = max bin mean / overall mean; 1.0 uniform, 5.0 a perfect knot):

| route | N | C | C (clock detuned +0.37 Hz) | Rayleigh R |
|---|---|---|---|---|
| r22 | 17 531 | 2.050 | 1.199 | 0.5352 |
| r39 | 58 202 | **2.309** | 1.038 | 0.6555 |
| r5e_v288 | 25 583 | 2.304 | 1.063 | 0.6716 |
| r62_v289 | 23 667 | 2.206 | 1.047 | 0.5827 |
| r63_v289 | 17 481 | 2.256 | 1.087 | 0.6197 |

r39's bin profile: **[1.469, 2.309, 1.128, 0.135, 0.075]** — the knot is in bins 0–2 and bins 3–4 are
nearly empty. Detuned: [0.976, 1.038, 1.025, 1.005, 0.957].

---

## 3. The SECOND difference of the 0xE4 command — what H2 never computed [EVIDENCE]

`Δ²cmd[n] = cmd[n] − 2·cmd[n−1] + cmd[n−2]` on the 0xE4 stream's own dejittered counter with its
**fitted** period. Strata are `H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md` §C's: baseline = engaged,
v < 12 m/s, |bar| < 400 raw, outside every episode; grinding = episode ticks.

| route | stratum | ticks | rms Δ² | P(f_model) | P median 14–26 Hz | **P(f_m)/med** | Δ² peak f |
|---|---|---|---|---|---|---|---|
| r22 | baseline | 9 062 | 48.9 | 38.3 | 16.1 | 2.37 | 25.99 |
| r22 | grinding | 7 312 | 60.4 | 1.35e3 | 20.4 | **66.53** | 19.84 |
| r39 | baseline | 37 053 | 32.5 | 33.6 | 6.18 | 5.43 | 19.99 |
| r39 | grinding | 18 118 | 69.2 | 2.63e3 | 64.0 | **41.10** | 20.00 |
| r5e_v288 | baseline | 11 817 | 46.2 | 104 | 10.6 | 9.85 | 19.99 |
| r5e_v288 | grinding | 9 854 | 84.9 | 4.17e3 | 73.5 | **56.69** | 19.91 |
| r62_v289 | grinding | 28 230 | 50.9 | 767 | 19.9 | **38.62** | 19.86 |
| r63_v289 | grinding | 35 443 | 50.0 | 1.14e3 | 16.6 | **68.78** | 19.96 |

Model-phase fold of `|Δ²cmd|`:

| route | stratum | C | C null | **R** | **R null** |
|---|---|---|---|---|---|
| r22 | baseline / grinding | 1.686 / 1.650 | 1.030 / 1.087 | **0.333 / 0.267** | 0.018 / 0.043 |
| r39 | baseline / grinding | 1.737 / 1.825 | 1.027 / 1.022 | **0.366 / 0.366** | 0.012 / 0.014 |
| r5e_v288 | baseline / grinding | 2.018 / 1.963 | 1.086 / 1.078 | **0.485 / 0.376** | 0.029 / 0.028 |
| r62_v289 | baseline / grinding | 1.983 / 1.850 | 1.025 / 1.030 | **0.512 / 0.368** | 0.021 / 0.015 |
| r63_v289 | baseline / grinding | 2.027 / 1.878 | 1.089 / 1.026 | **0.400 / 0.371** | 0.033 / 0.012 |

**R is 10–90× its own detuned null on every route, both strata, including the V112 stock-map era and
both V289 routes.** The 20 Hz knot comb is real and is on the wire. H2 could not have seen it: it
tested the *first* difference and value-repeat statistics, both of which a knotted ramp passes trivially.

---

## 4. Ring frequency against `modeld`'s rate, on the same clock [EVIDENCE]

Episodes are `grind1_census_v282.py`'s recipe, search band widened per build per `STATE.md`'s two-object
picture. `f0` corrected from the k18 axis by `0.01/P18`. Demand-gated high-demand subset (idx ≥ 20) —
`STATE.md`'s separation of the grinding mode from the low-demand 12–14 Hz road line:

| route | build | n eps | **f0 median** | 95 % CI (4 000-draw bootstrap) | f_model | f0 − f_model |
|---|---|---|---|---|---|---|
| r22 | V112 stock map | 31 | 20.446 | 19.933 – 20.973 | 19.99974 | +0.446 |
| r39 | V282 | 49 | 20.056 | 19.983 – 20.258 | 19.99972 | +0.056 |
| r5e_v288 | V288 rev 2 | 33 | 20.079 | 19.957 – 20.201 | 19.99857 | +0.080 |
| **r62_v289** | V289 rev 1 | 25 | **16.467** | **15.881 – 16.630** | 19.99954 | **−3.533** |
| **r63_v289** | V289 rev 1 | 27 | **16.483** | **16.247 – 16.811** | 19.99971 | **−3.516** |

- On V112 / V282 / V288 **every CI contains modeld's rate.** The frequency test alone **cannot separate**
  the ring from the forcing on those builds — it is underpowered, and I will not claim the +0.06/+0.08
  offsets are real.
- **On V289 the line is 3.5 Hz away**, while modeld ran at 19.9995 Hz on those very routes.
  **A firmware byte cannot move a forced line off its forcing frequency.**

---

## 5′. THE DECOMPOSITION — camera-locked comb / angle echo / free

Script `modeld_comb_decompose.py`, output `_scratch/modeld_comb_decompose.txt`. Route **r35 (V281 rev 3)**
added, so six builds now. **Every fraction below is debiased.**

### 5′.0 The detector, and a method failure worth recording

My first phase statistic — the amplitude-weighted circular mean of (instantaneous phase − model phase) —
**failed its own positive control**: `controlsState.desiredCurvature`, a signal *generated on the model
clock*, scored R = 0.060 against a detuned null of 0.163. The cause is structural: a staircase's 20 Hz
component is a sawtooth whose amplitude **flips sign** whenever the plan's slope does, so its phase hops
by π and the circular mean cancels. The correct detector is the square law, which detects lock **modulo π**:

```
R2 = | Σ z(t)² · exp(−2i·θ(t)) |  /  Σ |z(t)|²      z = analytic signal of the band-passed channel
                                                    θ = 2π·(continuous model frame index at t)
```

Split z into a part locked to θ (any real, sign-changing amplitude on one phase axis) plus a
uniform-phase part; then E_inphase − E_quadrature = E_locked, so **R2 is exactly the fraction of in-band
energy phase-locked to the camera clock**, and ψ = ½·arg(Σ z²e^{−2iθ}) is its phase axis. On r39's `bar`
during grinding, ψ measured on the two halves of the route gives **−29.5° and −29.9°** — agreement to
0.4° across halves separated by hundreds of seconds.

The **echo** is separated by regressing each channel on the measured steering angle in-band,
`g = ⟨z_x, z_a⟩ / ⟨z_a, z_a⟩` (|g| the gain, arg g the loop delay), with γ² debiased by 24 circular
shifts of the angle.

### 5′.1 The knot, measured [EVIDENCE]

- **The plan is a PURE ZOH.** rms deviation of `desiredCurvature` from its own hold mean, over holds ≥ 4
  ticks, is **exactly 0.000e+00 on all six routes**. The plan is bit-identical inside every hold, so
  **the knot is a pure slope discontinuity and there is nothing to remove but the discontinuity.**
- **Command sensitivity, measured not assumed**: OLS of raw 0xE4 on `carControl.actuators.torque` over
  engaged frames gives **−3520 to −4011 counts per unit torque, R² 0.854–0.982**. In-band (18–22 Hz)
  counts per 1e-4 1/m of curvature: 3.1–9.5.
- **Step size at the knots**, engaged (|step| p50 → in 0xE4 counts; rms counts in brackets):
  r22 grind 5.71e-5 → 1.75 [12.7] · r35 3.69e-5 → 3.51 [36.8] · r39 6.43e-5 → 3.62 [25.6] ·
  r5e 1.44e-4 → 6.45 [32.0] · r62 2.90e-6 → 0.22 [28.1] · r63 2.32e-6 → 0.09 [15.6].
  **The distribution is heavy-tailed** — median 0.1–6.5 counts, rms 12.7–46.6 counts — so the comb's
  energy comes from a minority of large steps, not from the typical one.
- **In-band command content in RAW 0xE4 COUNTS** (rms, and the camera-locked part of it):

| route | build | quiet: cmd rms / locked | grinding: cmd rms / locked | grinding: bar rms / locked |
|---|---|---|---|---|
| r22 | V112 stock map | 10.84 / 8.45 | 20.95 / **12.56** | 149.84 / **66.21** |
| r35 | V281 rev 3 | 6.47 / 4.77 | 27.38 / **22.61** | 84.51 / **65.70** |
| r39 | V282 | 6.95 / 5.58 | 24.52 / **20.12** | 64.65 / **45.74** |
| r5e_v288 | V288 rev 2 | 11.69 / 8.01 | 34.62 / **29.75** | 73.54 / **39.73** |
| r62_v289 | V289 rev 1 | 14.56 / 8.66 | 19.17 / **13.78** | 15.15 / **4.17** |
| r63_v289 | V289 rev 1 | 23.59 / 18.06 | 18.84 / **14.45** | 16.04 / **0.00** |

⭐ **Read the last two columns as a transfer gain.** bar_locked ÷ cmd_locked during grinding:
**5.27 (V112) · 2.91 (V281r3) · 2.27 (V282) · 1.34 (V288) · 0.30 (V289 r62) · 0.00 (V289 r63)** —
against 0.85–2.03 in the quiet stratum. **The command-side comb barely moves; what the EPS does with
it moves by a factor of ∞.**

### 5′.2 Three-way decomposition, 18–22 Hz, grinding stratum [EVIDENCE]

| route | channel | E | R2 raw | floor | **R2_deb** | **γ²(angle)** | R2 perp | \|g\| c/deg |
|---|---|---|---|---|---|---|---|---|
| r22 | 0xE4 cmd | 878 | 0.378 | 0.304 | **0.359** | 0.084 | 0.420 | 108 |
| r22 | bar | 4.49e4 | 0.224 | 0.303 | **0.195** | 0.818 | 0.079 | 2366 |
| r35 | 0xE4 cmd | 1500 | 0.685 | 0.224 | **0.682** | 0.257 | 0.405 | 445 |
| r35 | bar | 1.43e4 | 0.610 | 0.218 | **0.604** | 0.659 | 0.000 | 2183 |
| r39 | 0xE4 cmd | 1203 | 0.676 | 0.184 | **0.673** | 0.244 | 0.447 | 443 |
| r39 | bar | 8360 | 0.506 | 0.161 | **0.501** | 0.511 | 0.000 | 1683 |
| r5e | 0xE4 cmd | 2397 | 0.742 | 0.249 | **0.738** | 0.179 | 0.627 | 460 |
| r5e | bar | 1.08e4 | 0.333 | 0.455 | **0.292** | 0.562 | 0.000 | 1712 |
| r62 | 0xE4 cmd | 735 | 0.524 | 0.221 | **0.517** | 0.002 | 0.509 | 85 |
| r62 | bar | 459 | 0.097 | 0.148 | **0.076** | 0.003 | 0.076 | 74 |
| r63 | 0xE4 cmd | 710 | 0.592 | 0.172 | **0.589** | 0.004 | 0.589 | 84 |
| r63 | bar | 515 | 0.033 | 0.114 | **0.000** | 0.001 | 0.000 | 43 |

**V289's own band, 13–18 Hz, grinding:** bar E = **8700 / 1.72e4** (enormous — this is the symptom the
operator still feels), `R2_deb` = **0.0000 / 0.0000**, γ²(angle) = **0.351 / 0.489**. Command at 13–18 Hz:
`R2_deb` 0.0000, E only 206 / 214. **The relocated line is a real oscillation of the wheel with no
relationship whatever to the camera clock.**

**What fills the gap as you move from the model toward the wheel** (the orchestrator's question): on the
command the comb dominates and **survives removing the echo** (`R2 perp` 0.41–0.63 vs γ²(angle) only
0.08–0.26). On `bar` the comb's share falls to 0.20–0.60 and `R2 perp` → 0.000 — but ⚠ **`R2 perp` is
degenerate for `bar`**: `bar` and the angle are the same physical oscillation (γ² 0.51–0.82), so
subtracting `g·angle` removes almost all of `bar` and the residual carries nothing. **Do not read
"R2 perp = 0 on bar" as "no comb in bar."** The informative number for `bar` is `R2_deb`.

**The grinding EXCESS** (dE = E_grind − E_quiet), which is what we are trying to explain:

| route | band | dE | dE cam | dE echo | dE free | **cam share** |
|---|---|---|---|---|---|---|
| r22 | bar 18–22 | 4.41e4 | 8 667 | 3.66e4 | −1 136 | **0.197** |
| r35 | bar 18–22 | 1.38e4 | 8 489 | 9 354 | −4 090 | **0.617** |
| r39 | bar 18–22 | 7 661 | 3 928 | 4 153 | −419 | **0.513** |
| r5e | bar 18–22 | 9 629 | 2 884 | 5 851 | 894 | **0.300** |
| **r62** | **bar 13–18** | 6 621 | **−15** | 2 747 | 3 889 | **0.000** |
| **r63** | **bar 13–18** | 1.36e4 | **0** | 7 583 | 6 032 | **0.000** |

(cam and echo overlap by construction — the angle echo of a comb-driven ring is coherent with both
references — so the columns do not sum to dE.)

### 5′.3 V289, head on: the forcing is unchanged, the response collapsed [EVIDENCE]

| route | build | **cmd Δ² comb R** (forcing) | cmd `R2_deb` | **bar E 18–22** | **bar `R2_deb`** | bar `R2_deb` 13–18 |
|---|---|---|---|---|---|---|
| r22 | V112 stock map | 0.2667 | 0.359 | 4.49e4 | 0.195 | 0.0000 |
| r35 | V281 rev 3 | 0.3557 | 0.682 | 1.43e4 | 0.604 | 0.0000 |
| r39 | V282 | 0.3658 | 0.673 | 8 360 | 0.501 | 0.0017 |
| r5e_v288 | V288 rev 2 | 0.3757 | 0.738 | 1.08e4 | 0.292 | 0.0044 |
| **r62_v289** | V289 rev 1 | **0.3677** | 0.517 | **459** | **0.076** | 0.0000 |
| **r63_v289** | V289 rev 1 | **0.3707** | 0.589 | **515** | **0.000** | 0.0000 |

(detuned null for the forcing column is 0.004–0.043 on every route.)

🛑 **The forcing column is flat to ±0.05 across six builds and three openpilot eras. The response column
spans a factor of 98.** The orchestrator's reading is **confirmed**: V289's 20.04 Hz Q3 notch removed
the loop's *response* at the comb frequency, and what remains at 16.5 Hz is a different mode that the
comb does not drive at all.

### 5′.4 The angle-quantiser echo, checked against `oplpf`'s prediction

`oplpf` predicts 1 LSB (0.1°) of steering angle is worth 13.2 / 20.6 / 52.8 raw counts at 5 / 15 / 30 m/s
— i.e. **132 / 206 / 528 counts per degree** through P only. Measured in-band |g| (counts/deg):

| route | 0–8 | 8–16 | 16–24 | 24–40 | γ² range |
|---|---|---|---|---|---|
| r35 | 347 | 316 | 273 | 440 | 0.144–0.178 |
| r39 | 264 | 324 | 317 | 393 | 0.136–0.166 |
| r5e | 267 | 394 | 147 | 60 | 0.007–0.163 |
| r22 | 43 | 173 | 399 | — | 0.009–0.152 |
| r62 | 27 | 78 | 102 | 98 | 0.000–0.024 |
| r63 | 118 | 54 | 78 | 142 | 0.000–0.043 |

**The mechanism is real and the order of magnitude is right**, and on r22 it rises with speed as
predicted. ⚠ But |g| is a **closed-loop** ratio, not the open-loop P gain — the command also drives the
angle — so it is not a clean test of the 13.2/20.6/52.8 numbers, and it is 2× the prediction at low
speed on r35/r39. **The load-bearing number is γ²: the angle explains only 10–18 % of the command's
in-band energy on the pre-V289 builds, against the comb's 36–74 %.** On V289 the echo collapses to
0.000–0.043 because the wheel is no longer ringing at 20 Hz. **The echo is real but secondary.**

---

## 6′. SIZING A LAG-FREE REMOVAL OF THE COMB [EVIDENCE — sizing only, NOT a design]

⚠ **Framing, per the operator:** an LPF anywhere in the command path is off the table —
*"a bandaid which harms the model's driving authority (delays and limits output slew)."* And
`memory/feedback/builds/feedback-no-openpilot-side-modifications.md` stands against fork changes
generally. **This is evaluation, not a recommendation.** The point is that a slope-continuous
reconstruction is *not* a filter: it does not attenuate the band, it removes a discontinuity that the
ZOH manufactures.

Applied offline to each route's real 20 Hz `modelV2.action.desiredCurvature` series, resampled to the
100 Hz tick grid, engaged & v < 12 m/s. Energy as a fraction of ZOH:

| route | ZOH 12–26 (abs) | LERP 12–26 | EXTRAP 12–26 | ZOH 18–22 (abs) | **LERP 18–22** | **EXTRAP 18–22** |
|---|---|---|---|---|---|---|
| r22 | 6.34e-8 | 0.0227 | 0.553 | 4.47e-8 | **0.0016** | **0.0659** |
| r35 | 4.28e-8 | 0.0270 | 0.682 | 2.62e-8 | **0.0020** | **0.0650** |
| r39 | 6.87e-8 | 0.0190 | 0.477 | 4.99e-8 | **0.0017** | **0.0349** |
| r5e_v288 | 2.09e-7 | 0.0369 | 1.046 | 9.78e-8 | **0.0023** | **0.1086** |
| r62_v289 | 7.60e-8 | 0.0217 | 0.571 | 5.21e-8 | **0.0020** | **0.0365** |
| r63_v289 | 2.88e-7 | 0.0211 | 0.573 | 1.96e-7 | **0.0016** | **0.0388** |

- **LERP** (linear between the last two *received* values) removes **99.8 %** of the plan's 18–22 Hz
  energy and 96–98 % of 12–26 Hz — **but costs one model frame, 50 ms, of lag.**
- **EXTRAP** (slope extrapolation from the last two received values, **zero added lag**) removes
  **89.1–96.5 %** at 18–22 Hz. Across the wider 12–26 Hz band it removes only ~43–52 %, **and on r5e it
  makes it slightly worse (×1.046)** — because the extrapolator still jumps when the next frame lands
  and its slope estimate is noisy. **Its cost is overshoot, not delay.**
- `modeld` already applies `smooth_value(..., LAT_SMOOTH_SECONDS = 0.1)` before publishing
  (`modeld.py:346,375`); everything measured here is what that smoothing **leaves**.
- **Expected ceiling on the car**, combining with §5′.2: the comb is 20–62 % of the grinding excess on
  the pre-V289 builds, so removing ~90 % of it at source should remove **~18–56 % of the grinding
  excess energy**, i.e. **0.9–1.5 dB to 3.6 dB** — a partial effect, not a cure. **BELIEF**, because it
  assumes the mode's response is linear in the excitation, which `V290-PARAMETRIC-HAZARD-2026-09-09.md`
  shows is not safe to assume for this clamped loop.
- 🛑 **The firmware also zero-order-holds the 100 Hz command into its 1 kHz loop.** That is a *second*
  ZOH in series and it is `fwpath`'s; nothing here bounds it.

---

## 7′. RECONCILIATION WITH `slewburst`'s NULL — I agree with the orchestrator

`slewburst` found that over 514 burst onsets on 5 routes, Δ²cmd spikes ≥ 150 account for
**0 % [0, 2.0 %]** of onsets, which slightly *avoid* them. That is **compatible** with a strong comb, and
I have a measurement for it rather than only an argument:

**the comb is at full strength in the QUIET stratum.** |Δ²cmd| model-phase fold R, quiet vs grinding:
**0.333/0.267 (r22) · 0.366/0.366 (r39) · 0.485/0.376 (r5e) · 0.512/0.368 (r62) · 0.400/0.371 (r63)**.
And the camera-locked command content is present in quiet on every build (4.8–18.1 raw counts rms).

⇒ **The comb is a SUSTAINED FORCING, not a TRIGGER.** It is equally present when nothing is happening,
so it cannot be what selects the moment a burst starts; what selects that is loop gain. This matters for
what a fix must do: **removing the comb should lower the sustained amplitude of the ~20 Hz response, and
should NOT be expected to change the episode RATE.**

---

## 8′. WHAT I STILL CANNOT DETERMINE

1. 🛑 **Whether the comb is the *only* thing driving the ~20 Hz mode, or one driver among several.**
   R2 cannot separate "an additive forced line" from "a resonance kicked by a phase-locked impulse
   train": the mode's decay time is ~0.13 s (ζ ≈ 0.03 at 20 Hz) and kicks arrive every 50 ms, so
   successive kicks *maintain* phase lock either way. The camera-locked share (20–62 %) bounds the
   comb's contribution from below and the free share bounds the rest, but the split is not causal.
2. Whether the +0.056 / +0.080 Hz gaps of §4 are real. Not resolvable; **§4 is a failure to reject, not
   a match**, and must not be presented as one.
3. Why r22's camera share (0.197) is so much lower than r35/r39 (0.617/0.513) with the same forcing.
   Loop gain (stock map vs ×6) is the obvious reading but untested; r22's grinding stratum is only
   73.5 s.
4. The non-pass-through ticks' attribution (`lane_centering`, τ 0.4 s, `LaneCentering=True`,
   `LaneCenteringE2EAuthority=1.0`; inactive below 5 m/s so it cannot explain the low-speed h=1 ticks)
   — **BELIEF**. `liveParameters` as a second 20 Hz staircase into `roll_compensation` — **BELIEF**,
   observed in the message census only, not extracted.
5. r22 predates the 2026-09-03 toggle backup; nothing about that route's fork configuration is verified.

---

## 9′. 🛑 V288 IS **VOID AS AN AMPLITUDE TEST** AND **VALID AS A PHASE TEST** — they are different experiments

Standing correction, put here because it will otherwise be lost the next time someone re-reads the
amplitude correction and assumes it kills everything V288 was used for.

`combsize` / the orchestrator established that V288's cave is **not LTI** — `delta>>4` plus
`if step == 0 and delta != 0: step = 1` — and that at the ring's real amplitude (4.0–10.7 setpoint
counts) its measured fundamental gain at 20.3 Hz is **0.95–0.99**. So **V288 attenuated the 18–22 Hz
band by 1–7 %, not the 54 % everyone assumed, and its null as an AMPLITUDE test is VOID.**

**Nothing in §5′ rests on that number.** I did not infer removal from an assumed gain; I measured two
different things:

| what V288 did to the 18–22 Hz band in delivered driver torque | measured |
|---|---|
| total energy | **went UP**: 8 360 → 1.08e4 (grinding), 699 → 1 186 (quiet) |
| camera-**locked** energy | 4 185 → 3 158, i.e. **−25 %** |
| camera-locked **fraction** `R2_deb` | 0.501 → **0.292** |
| split-half phase axis ψ | **−29.5° / −29.9°** (agreeing to 0.4°) → **−67° / +89°** (incoherent) |
| the command's own locked fraction | **untouched**: 0.673 → 0.738 |

⭐ **That is the signature of a PHASE SCRAMBLER, not an attenuator.** The anti-stick branch barely
touched the amplitude — consistent with the 0.95–0.99 gain — while degrading the coherence of what it
passed. **A nonlinearity can destroy phase lock while leaving band energy alone; the 1–7 % attenuation
and the locked-fraction collapse are not in conflict, they are the same fact seen twice.**

⚠ **But the phase test is weaker than it first looked, and this matters for §10′.** The locked fraction
halved; the locked **energy** only fell **25 %**, i.e. the kick amplitude fell about **13 %**. V288 is
therefore a **13 %-dose** natural experiment, not a removal.

---

## 10′. BOUNDING THE ONE THING THAT COULD OVERTURN THIS — does the kick set the RATE?

Script `modeld_rate_ci.py`, output `_scratch/modeld_rate_ci.txt`.

**The reading under test.** If the camera-locked comb is a phase-locked **kick** that re-triggers a free
mode rather than a tone that adds to it, then it sets episode **rate**, not amplitude. V288 partially
destroyed the kick's phase coherence (§9′), so it should show a **lower** episode rate. It does not.

Recipe matched to `GRIND1-CENSUS-V288-R5E-2026-09-08.md` §3 (same episode detector, same 30 s engaged
blocks). Both arms are V282-family so the 18–22 Hz gate is correct for both; `fvlc_lib.BAND` only
departs from 18–22 for V289, which is not in this contrast. The **ratio** CI is new — the census
computed only the marginals.

| route | build | n eps | eng s | ep / eng h [CI] | n in v<12 | eng v<12 s | ep/h in v<12 [CI] |
|---|---|---|---|---|---|---|---|
| r39 | V282 | 79 | 879.8 | 323.2 [262.6, 382.9] | 59 | 584.2 | 357.4 [291.1, 423.9] |
| r3a | V282 | 13 | 483.3 | 96.8 [37.7, 159.2] | 11 | 141.2 | 280.4 [142.2, 427.2] |
| r3c | V282 | 38 | 593.9 | 230.4 [117.3, 366.2] | 27 | 209.9 | 446.0 [227.1, 640.8] |
| **r5e_v288** | **V288** | **46** | **641.6** | **258.1 [159.8, 358.2]** | **34** | **256.9** | **476.4 [311.9, 617.5]** |

(r39's 323.2 and the V282 pool's 239.1 reproduce the census's 323 and 239 exactly.)

### The ratio, V288 / V282 pool

| exposure definition | ratio | 95 % CI (blocks only) | 95 % CI (**route-cluster**) | excludes a reduction below |
|---|---|---|---|---|
| engaged (census definition) | **1.079** | [0.646, 1.622] | **[0.605, 2.683]** | **40 %** |
| **matched regime: engaged & v < 12 m/s** | **1.303** | [0.835, 1.825] | **[0.809, 1.945]** | **19 %** |

Bootstrap tail probabilities (route-cluster, the honest one — it also resamples the three V282 routes,
because their scatter is 97–323 ep/h and there is only ONE V288 route):

| hypothesised reduction | ratio | engaged | **matched v<12** |
|---|---|---|---|
| 50 % | 0.50 | **EXCLUDED**, p = 0.0063 | **EXCLUDED**, p = 0.0004 |
| 30 % | 0.70 | not excluded, p = 0.0687 | **EXCLUDED**, p = 0.0070 |
| 25 % | 0.75 | not excluded, p = 0.1022 | **EXCLUDED**, p = 0.0124 |
| 20 % | 0.80 | not excluded, p = 0.1484 | **EXCLUDED**, p = 0.0229 |

### 🛑 What this does and does NOT bound — read this before quoting the table

1. **The STRONG form of the kick reading is excluded.** "The comb is the dominant trigger, so degrading
   it roughly halves the episode rate" is ruled out under **both** exposure definitions (p ≤ 0.006).
2. **In the matched grinding regime, a ≥20 % rate reduction is excluded** (p ≤ 0.023). Under the
   census's wider engaged definition it is not (p = 0.069 at 30 %).
3. ⚠ **Part of the matched-regime exclusion comes from the point estimate being ABOVE 1 (1.303), not
   from precision alone.** V288's route was faster and twice as slew-capped as any V282 route
   (`GRIND1-CENSUS-V288` §6) and its v<12 exposure is only 257 s, so some of that 1.303 may be the
   speed profile rather than the build. **Treat the engaged-wide row as the conservative one.**
4. 🛑 **The real limitation is the DOSE, not the statistics.** V288 cut the delivered camera-locked
   **energy** by only **25 %** (§9′) — a ~13 % cut in kick amplitude. So this natural experiment asks:
   *"did a 13 % smaller kick produce a ≥20 % lower rate?"* and answers **no**.
   - ⇒ **A strictly LINEAR kick-energy → episode-rate relation is disfavoured** (a 25 % energy cut
     should have given ~25 % fewer episodes; that is excluded at p = 0.012 in the matched regime).
   - ⇒ **A sub-linear or threshold-like relation is NOT excluded**, and neither is a large rate effect
     from *fully* removing the comb. **Nothing here has ever removed the comb.**

### What would settle it

Overdispersion φ measured from the 30 s block counts: **2.08** (V288), **2.53** (V282 pool). For a rate
ratio x at 95 % confidence, `N_ep ≳ φ·(1.96/|ln x|)²·2` per arm:

| target | N_ep per arm | routes like r5e (46 ep each) |
|---|---|---|
| 30 % reduction | 126 | **~2.7** |
| 20 % reduction | 321 | ~7.0 |
| 10 % reduction | 1 442 | ~31.3 |

**~3 more V288-class routes would settle the 30 % question** — but only for a 13 % dose. The decisive
experiment is not more routes at this dose; it is **one build, or one fork configuration, that actually
removes the comb**, which §6′ says a zero-lag slope extrapolation would do to 89–96.5 % at 18–22 Hz.

⇒ **Verdict status: SECURE against the strong kick reading, BOUNDED but not closed against the weak
one.** This does not change what §6′ licenses — a fork-side interpolation should still be sized against
episode **rate**, not amplitude, before it costs a drive — and it sharpens why: rate is the endpoint the
existing evidence is weakest on.

---

## 11′. TWO STATISTICS THAT LOOK CONTRADICTORY AND ARE NOT

The report contains both of these and they must be read as the different things they are:

- §3: the Δ²cmd **power at `f_model` relative to the local 14–26 Hz band median** goes
  **2.4–9.8 (quiet) → 38.6–68.8 (grinding)**, a 5–10× rise.
- §7′: the |Δ²cmd| model-phase fold **R** is **0.333–0.512 (quiet) → 0.267–0.376 (grinding)**, i.e. flat
  or slightly lower.

**Both are true.** The first is a **power ratio against a local background**; the second is a **locked
fraction of the in-band energy**. During grinding the command's absolute in-band content rises sharply
(cmd rms 6.5–11.7 → 19–35 raw counts, §5′.1) and so does the comb's absolute content — but the *share*
of it that is camera-locked does not rise, because the echo and the free part grow alongside. **The
comb gets bigger in absolute terms and does not get more dominant in relative terms.**

The conclusion — **sustained forcing, not a trigger** — follows from the second statistic (the comb is
at full locked strength when nothing is happening) and is independently corroborated: `slewburst`
bounded every discrete trigger class at ≤ 13 % of burst onsets, with cap binds at RR 0.83 [0.69, 0.96].

---

## 12′. CORRECTIONS OF RECORD CARRIED INTO THIS FILE SO IT STANDS ALONE

1. 🛑 **`STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md` §2.1 is FALSIFIED IN PRACTICE.** It says
   `clip_curvature` "removes the raw staircase discontinuity before the PID ever sees it." **Its
   binding fraction is 0.000 in every route × stratum** of six routes (§2), tested by direct equality
   against its own bound — it only removes the discontinuity when it binds, which on this record is
   never. **Two orchestrator briefs inherited that claim.** A flag has been added at the head of that
   file's §2.1.
2. **`slewburst` has been stopped and its §A2 ("V288 falsified the echo") is RETRACTED** by the
   orchestrator. Its trigger-class bound (≤ 13 % of burst onsets; cap binds RR 0.83 [0.69, 0.96])
   stands and is cited in §11′.
3. ⚠ **The 0xE4 transmit counter fits 99.53–99.56 Hz, not 100** (§1) — controlsd's `Ratekeeper` slips
   ~0.45 % low. **Anything read on the 0xE4 counter axis at a nominal 100 Hz is biased 0.45 % high**,
   which at 20 Hz is 0.09 Hz — larger than several of the frequency differences this kit has argued
   over. Every 0xE4-axis number in this file uses the fitted period.
4. **V288 is VOID as an amplitude test and VALID as a phase test** (§9′).
5. **§4's frequency comparison is a FAILURE TO REJECT, not a match**, for V112/V281r3/V282/V288 — the
   CIs are wide (r22 spans 19.93–20.97). It is only a **rejection** for V289, where the CI excludes
   `f_model` by 3.5 Hz; that rejection is a physical argument (a forced line cannot sit 3.5 Hz off its
   forcing frequency) and it is the strongest single falsification in the file. Lead V289 with the
   displacement; the locked-fraction number there is supporting-only.
