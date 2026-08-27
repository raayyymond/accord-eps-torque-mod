# TRACE 2026-08-13 — THE CAR'S ACTUAL STEERING RATIO, MEASURED FROM ITS OWN LOGS

**Task:** measure `ratio(θ) = steering-wheel angle / road-wheel angle` across the whole corpus, with
two independent methods and every control run *before* the measurement, so the firmware table at
`0xC6B64` (swing `1084/899 = 1.206×`) can be judged adequate or under-scaled.

**Status of every claim below: EVIDENCE unless explicitly marked BELIEF.**
**No build and no calibration edit is proposed anywhere in this document.**

---

## 0. HEADLINE

| quantity | measured | firmware `0xC6B64` | verdict |
|---|---|---|---|
| swing over 0 → 120° (`ratio(floor)/ratio(120°)`) | **1.176  [1.147, 1.201]** | **1.206** | **ADEQUATE — the firmware is ~2.5 % over, not 40 % under** |
| further quickening 120° → 380° | **1.242  [1.181, 1.274]** | **1.000 (flat)** | 🛑 **UNCOMPENSATED — 20 % of rack ratio the table does not see** |
| ratio at the centre floor (0–50°) | 16.15  [15.89, 16.32] | — | — |
| ratio at 120° | 13.73  [13.44, 14.01] | — | — |
| ratio at 320–400° | 11.06  [10.85, 11.54] | — | — |
| angle-sensor centre offset θ₀ | **−4.25°** (spread ±0.12° over 4 speed bands) | — | openpilot's own learner: −4.78° |

⭐ **The desk estimate of 1.67–1.82× is REFUTED.** There is no ~1.4× angle-dependent plant-model
error over the range where the car is driven. Over 0–120° the firmware's compensation matches the
real rack to within 0.01–0.07 in normalised gain at *every* one of its knots.

🛑 **What did NOT hold: the rack does not stop quickening at 120°.** The pre-registered positive
control ("the plateau must come out flat") FAILS — and what it refutes is its own premise, not the
instrument. See §4.

---

## 1. DATA AND EXTRACTION

`rlog-tools/decode/extract_ratio_corpus.py` → `analysis-2020accord/_scratch/cache/ratio/{route}.npz`
(47 routes, **512,895 rows at 20 Hz = 427.4 min**; 1 route and 2 segments dropped on truncated
capnp tails, reported at extraction).

Taps: `carState` (vEgo, steeringAngleDeg, steeringRateDeg, steeringPressed, standstill,
gearShifter, brakePressed, yawRate), `carControl.latActive`, `livePose`
(angularVelocityDevice x/y/z + valid, velocityDevice.x), `gyroscope` (raw 3-axis),
CAN `0x1D0` src 1 (4 wheel speeds), `liveParameters` (angleOffset, steerRatio, stiffness, roll).

**Pairing convention:** every field is `np.interp`/hold-last from its OWN source timebase onto ONE
uniform 20 Hz grid. There is no `(t, probe)` pair here at all, so the `raw14` off-by-one trap
cannot apply — the cave bytes are not read by this study.

**Engagement key:** `carControl.latActive` (the field the brief mandates), never `cruiseState`.

**Sign convention — MEASURED, not assumed.** `corr(steeringAngleDeg, avz) = −0.961`;
`corr(avz, ws_rr − ws_rl) = −0.898`. So with the operator's frame (negative angle = right turn),
positive-left vehicle yaw is `−avz` and `+(ws_rr − ws_rl)`. Device frame is x-forward, y-right,
z-**down**, which is why the IMU z is negative on a left turn.

🛑 **`carState.yawRate` is IDENTICALLY ZERO on this car** — 0 nonzero samples out of 512,895.
Honda's carState never fills it. Method A is `livePose`, **not** `carState`. Anything in the kit
that reads `cs_yaw` is reading zeros.

---

## 2. THE ESTIMATORS

Steady-state kinematics about the **rear axle**, exact form (not the small-angle one — the `atan`
is worth 8 % at δ ≈ 26°):

```
yaw = v_rear · tan(δ) / (L + K v²)      ⇒   δ = atan( yaw · (L + K v²) / v_rear )
L = 2.830 m (wheelbase)   T_rear = 1.613 m   K fitted, see §5
```

| id | δ estimator | needs | independent of |
|---|---|---|---|
| **A** | `atan(yaw_IMU · L / v_rear)` | IMU yaw, **rear** wheel pair | front wheels |
| **D** | `asin(yaw_IMU · L / v_front)` | IMU yaw, **front** wheel pair | rear wheels |
| **C** | `acos(v_rear / v_front)` | **wheel speeds only** | IMU, yaw, L, track, vEgo |
| **B** | `atan(yaw_rear_diff · L / v_rear)`, `yaw_rear_diff = (rr−rl−βv)/T` | rear wheel pair only | IMU entirely |

Nuisances, each measured rather than assumed:
- **IMU yaw bias** — per route, from **4,551 s of STANDSTILL**: median |bias| 1.4e-4 rad/s,
  max 6.9e-4 rad/s. Subtracted per route.
- **Rear tyre-radius mismatch β** — from straight driving at speed, `(rr−rl) = T·yaw + β·v`.
- **Front/rear radius calibration γ = 1.00151** — `v_front/v_rear` on straight driving, where
  geometry forces it to 1.

---

## 3. 🛑 THE LARGEST SYSTEMATIC IN THE STUDY: `vEgo` IS THE WRONG REFERENCE SPEED

The bicycle model is written about the **rear axle**, so `v` must be the rear-axle-centre speed —
which is exactly `(ws_rl + ws_rr)/2`, a rigid-body identity, on a car whose rear wheels are neither
driven nor steered. openpilot's `vEgo` is an average over **all four** wheels, and the front pair
run at `v/cos δ`.

Measured, primary band, by steering angle:

| \|θ\| deg | 0–5 | 60–100 | 150–250 | 250–400 |
|---|---|---|---|---|
| `v_front / v_rear` | 1.0016 | 1.0056 | 1.0372 | 1.1115 |
| `sec(δ)` predicted | 1.0000 | 1.0043 | 1.0343 | 1.0930 |
| `vEgo / v_rear` | 0.9894 | 0.9912 | 1.0163 | **1.0786** |

⇒ Using `vEgo` under-reads δ at large angle by ~8 %, over-reads the ratio there by the same amount,
and therefore **flattens the curve**. The first pass of this study used `vEgo` and reported
swing 1.109 with a *passing* plateau-flatness control. **Both were artefacts of that one choice.**
It was caught by estimator **C**, which uses no speed reference at all.

---

## 4. THE PRE-REGISTERED POSITIVE CONTROL FAILS — AND ITS PREMISE IS WHAT BREAKS

Local ratio beyond 120° (estimator A): 13.75, 13.71, 13.50, 12.81, 11.67, 11.06 at
θ = 121, 147, 191, 236, 303, 380°. Max/min **1.24**, CIs disjoint. **NOT FLAT.**

Two readings — the estimator is broken, or the rack keeps quickening. Four lines separate them:

**(a) Four estimators with disjoint dependencies agree; only the `vEgo` one is flat.**

| estimator | ratio @120° | ratio @320–400° | droop 120→380 |
|---|---|---|---|
| A  IMU + rear wheels | 13.73 [13.44, 14.01] | 11.06 [10.85, 11.54] | **1.242 [1.181, 1.274]** |
| D  IMU + front wheels | 13.78 [13.50, 14.04] | 11.38 [11.17, 11.88] | **1.211 [1.151, 1.243]** |
| B  rear differential, no IMU | 13.69 [13.00, 14.20] | 11.81 [10.78, 12.43] | **1.160 [1.077, 1.278]** |
| C  wheel speeds only, no IMU/L/T | 13.30 [12.39, 14.27] | 10.85 [10.45, 11.43] | **1.226 [1.119, 1.326]** |
| ~~vEgo~~ (biased, §3) | 14.08 | 14.26 | 0.988 |

A and D share no wheel pair. C shares no yaw source with any of them.

**(b) The synthetic-rack control — the decisive one.** `rlog-tools/studies/steering-ratio/ratio_null_droop.py` builds
three racks from the REAL θ and the REAL per-sample residual noise (resampled within speed bins)
and pushes them through the IDENTICAL pipeline:

| synthetic rack | swing(0→120) returned | droop(120→380) returned | truth | |
|---|---|---|---|---|
| constant ratio everywhere | 1.0014 [0.9935, 1.0088] | 1.0015 [0.9904, 1.0116] | (1.000, 1.000) | **PASS** |
| **measured notch, then EXACTLY FLAT beyond 120°** | 1.1695 | **0.9789 [0.9675, 0.9880]** | (1.176, 1.000) | **PASS** |
| the measured rack | 1.1697 | 1.2166 [1.2032, 1.2281] | (1.176, 1.242) | **PASS** |

🛑 A rack that is genuinely flat beyond 120° reads back as **0.979 [0.968, 0.988]**. The real data
give **1.242**. **The pipeline cannot manufacture the droop.**

**(c) Absolute-scale anchor.** Extrapolating the measured curve to full lock (~450°) gives
δ_max = **35.8°**. A 37.4 ft curb-to-curb turning circle implies δ_max ≈ 35°. The `vEgo` estimator
gives 31.0° and misses it. *[The 37.4 ft figure is BELIEF — published spec, not measured here.]*

**(d) Direction of the surviving physical bias makes the droop a LOWER bound.** Front tyre slip at
large angle reduces the yaw actually achieved, which *inflates* the apparent ratio there — i.e. it
works against the observed droop.

⇒ **Reported as EVIDENCE: the local steering ratio keeps falling past 120°, by a further
1.242× [1.181, 1.274] out to 380°.** The firmware's table is flat over that entire span.

---

## 5. THE CONTROLS

| # | control | result |
|---|---|---|
| 1 | **plateau flatness (pre-registered positive control)** | **FAIL** — premise refuted, not the instrument (§4) |
| 1′ | **synthetic constant-ratio rack** (replacement positive control) | **PASS** — 1.0014 / 1.0015 |
| 1″ | **synthetic firmware-shaped rack** | **PASS** — droop 0.979, real 1.242 |
| 1‴ | **recovery of the measured rack** | **PASS** |
| 2 | **within-band speed stratification** (the primary threat) | **PASS** — swing 1.214 / 1.185 / 1.200 at v = 1–2.5 / 2.5–3.5 / 3.5–5 m/s |
| 3 | shuffle | **UNINFORMATIVE BY CONSTRUCTION** — shuffling δ against θ kills the sign relation, every bin median → 0, null distribution came out [−1.43, +1.49]. Replaced by 1′. |
| 4 | **left vs right** | 1.208 [1.154, 1.239] vs 1.154 [1.124, 1.184] — same sign, overlapping. Rules out road camber, which would push the two sides opposite ways. |
| 5 | **engaged vs manual** (a plant property must not care) | **PASS** — 1.177 [1.137, 1.203] vs 1.195 [1.157, 1.262]; ratio@120° 13.70 vs 13.54 |
| 6 | hands on vs off wheel | 1.158 vs 1.172 — agree |
| 7 | **independent speed bands, shape** | 5–8 and 8–12 m/s reproduce the floor→flank→knee shape with knees at the same angles |
| 8 | **understeer gradient K, fitted not assumed** | K = 0.00225 s²/m; `K v²/L` ≤ **1.99 %** at 5 m/s ⇒ negligible inside the primary band |
| 9 | **secant predicted from local** | plateau error ≤ 0.22 % — the two representations are self-consistent |

**Sensitivity of swing(0→120), estimator A:**

| perturbation | swing |
|---|---|
| baseline (θ₀ = −4.25, L = 2.830, smooth 0.5 s, rate < 25 °/s) | **1.176 [1.147, 1.201]** |
| θ₀ = −3.25 / −5.25 / 0.00 | 1.163 / 1.158 / 1.096 |
| L = 2.75 / 2.91 m | 1.178 / 1.174 |
| steadiness rate < 10 / < 60 °/s | 1.179 / 1.174 |
| Ackermann-average road-wheel angle instead of the bicycle angle | −1.7 % |

**Bootstraps are over BLOCKS (episodes)** — contiguous runs broken at every route change, segment
change and >0.5 s time gap. 312 blocks in the primary band.

---

## 6. THE CURVE, AGAINST THE FIRMWARE TABLE

Measured local ratio normalised at 120°, vs the firmware's implied `1/(Y/Y_max)`:

| \|θ\| deg | measured | 95 % CI | firmware | fw − meas |
|---|---|---|---|---|
| 3.9 | 1.228 | [1.181, 1.285] | 1.204 | −0.023 |
| 6.3 | 1.213 | [1.154, 1.275] | 1.204 | −0.009 |
| 12.9 | 1.145 | [1.098, 1.199] | 1.201 | +0.056 |
| 17.4 | 1.180 | [1.142, 1.226] | 1.200 | +0.020 |
| 29.6 | 1.152 | [1.117, 1.188] | 1.195 | +0.044 |
| 37.9 | 1.176 | [1.142, 1.220] | 1.182 | +0.007 |
| 48.0 | 1.160 | [1.120, 1.206] | 1.152 | −0.008 |
| 60.2 | 1.094 | [1.049, 1.134] | 1.116 | +0.023 |
| 75.7 | 1.058 | [1.012, 1.098] | 1.059 | +0.001 |
| 94.5 | 1.018 | [0.970, 1.054] | 1.009 | −0.009 |
| 120.7 | 1.002 | [0.983, 1.024] | 1.000 | −0.002 |
| 191.4 | 0.983 | [0.946, 1.014] | 1.000 | +0.017 |
| 235.9 | 0.933 | [0.897, 0.965] | 1.000 | **+0.067** |
| 303.1 | 0.850 | [0.831, 0.875] | 1.000 | **+0.150** |
| 380.4 | 0.805 | [0.783, 0.844] | 1.000 | **+0.195** |

**Angular extent.** Measured: flat floor **0 → ~50°**, flank **~50 → ~95°**, then a much gentler
continued fall. Firmware knots: flat **0 → 34°**, flank **34 → 100°**, flat beyond. The upper knee
agrees (~95° vs 100°); the firmware starts its flank ~16° early. Breakpoint CIs are wide
(lower knee [13, 49]°, upper knee [60, 95]°) — **the knee positions are weakly determined and
should not be quoted to better than ±20°.**

---

## 7. EXPOSURE — AND WHERE THERE IS NO POWER

Seconds of valid, steady exposure:

| \|θ\| \ v (m/s) | 1–3 | 3–5 | 5–8 | 8–12 | 12–16 | 16–20 | 20–25 |
|---|---|---|---|---|---|---|---|
| 0–5 | 599 | 375 | 708 | 1500 | 2101 | 2059 | 1611 |
| 5–20 | 430 | 248 | 369 | 542 | 484 | 321 | 84 |
| 20–50 | 214 | 115 | 174 | 130 | 66 | 21 | 1 |
| 50–120 | 82 | 54 | 77 | 133 | 45 | 0 | 0 |
| **120–400** | **228** | **96** | **1** | **0** | **0** | **0** | **0** |

🛑 **Everything beyond 120° of wheel exists only below 5 m/s.** The whole ratio curve — floor *and*
outer region — is therefore measured *inside* the 1–5 m/s band, where `K v²/L ≤ 2 %`. That is why
the speed confound is structurally absent from the headline rather than merely controlled for.
**There is NO power at all for large angles at road speed, and none is claimed.**

Residual honest uncertainty beyond the bootstrap CI: the 5–8 and 8–12 m/s bands reproduce the
*shape* but their floor-to-knee amplitude runs 1.10–1.23 against the primary band's 1.16. **Treat
±0.05 as a systematic floor on the swing**, on top of the quoted CI.

---

## 8. FILES

| file | what |
|---|---|
| `rlog-tools/decode/extract_ratio_corpus.py` | corpus extractor → `_scratch/cache/ratio/*.npz` |
| `rlog-tools/lib/ratio_lib.py` | geometry, masks, block bootstrap, `v_ref` definition |
| `rlog-tools/studies/steering-ratio/measure_steering_ratio.py` | nuisance fits, QA, θ₀, curve + first-pass controls → `results.json` |
| `rlog-tools/studies/steering-ratio/ratio_controls.py` | synthetic null, secant-from-local, K fit, sensitivity → `controls.json` |
| `rlog-tools/studies/steering-ratio/ratio_final2.py` | **the reported numbers** — four estimators, curve, strata → `final2.json` |
| `rlog-tools/studies/steering-ratio/ratio_null_droop.py` | **the control that decides the >120° droop** → `null_droop.json` |
| `rlog-tools/studies/steering-ratio/ratio_final.py` | superseded first pass (vEgo reference) — kept for the record |

---

## 9. WHAT IS *NOT* ESTABLISHED HERE

- **That `0xC6B64`'s `Y` is a steering-ratio compensation at all**, or that it enters as `1/ratio`.
  That is the orchestrator's Ghidra finding; this study only measures the rack and puts the two
  curves side by side. The alignment over 0–120° is strong circumstantial support, not proof.
- **Whether the uncompensated >120° region matters for any symptom.** The operator's grinding and
  micro-ratcheting reports are at small angles and at road speed; >120° occurs only below 5 m/s.
- **Any absolute ratio to better than ~5 %.** A, D, B and C span 13.30–13.78 at 120°. The *shape*
  is much better determined than the level, and every headline number is a within-band ratio in
  which a level error cancels.
- **openpilot's own `liveParameters.steerRatio`** (median 11.82 over the corpus) is *not* used and
  does not agree with this measurement at any angle; its learner is fitted against openpilot's
  internal model, and the turning-circle anchor in §4(c) favours this measurement over it.

---

# 10. THE TWO-SIDED (UNFOLDED) CURVES — IS THE RACK SYMMETRIC?

**Added 2026-08-13.** `rlog-tools/studies/steering-ratio/ratio_two_sided.py` → `_scratch/cache/ratio/two_sided.json`.
Same corpus, same masks, same `v_ref` (rear axle), same block bootstrap. Nothing in §§1–9 is
re-litigated. The per-side scalars in §5 CONTROL 4 hinted at a 3–5 % level split; this section
unfolds the whole curve and decides whether that split is real.

## 10.0 SIGN MAPPING — verified, not assumed

`|θ−θ₀| > 50°`, primary band:

| side | n | yaw (+left) | `ws_rr − ws_rl` | δ_A |
|---|---|---|---|---|
| LEFT (sensor angle **>** θ₀) | 5031 | **+0.2278** rad/s | **+0.3743** m/s | **+15.64°** |
| RIGHT (sensor angle **<** θ₀) | 4147 | **−0.2361** rad/s | **−0.3854** m/s | **−13.01°** |

Right rear is the OUTER wheel in a left turn, so `ws_rr > ws_rl` there. **PASS** — the script
aborts if it does not. JSON carries three axes so nothing can be silently swapped: `theta`
(folded), `theta_sensor` (**LEFT +, RIGHT −** — the physical frame), `theta_plot`
(**LEFT −, RIGHT +** — as requested for plotting, = `−theta_sensor`).

## 10.1 THE TWO CURVES — local ratio, estimator A, v 1–5 m/s, PAIRED block bootstrap

Blocks are resampled JOINTLY, so the L/R column is a paired CI, not the difference of two
independent ones.

| \|θ−θ₀\| | LEFT local [95 % CI] | n | RIGHT local [95 % CI] | n | **L/R [95 % CI]** |
|---|---|---|---|---|---|
| 1.9 | 15.13 [13.91, 16.70] | 5359 | 17.04 [15.40, 19.21] | 3484 | 0.888 [0.764, 1.025] |
| 3.9 | 16.80 [16.03, 17.87] | 3195 | 16.91 [16.04, 18.02] | 1772 | 0.993 [0.916, 1.080] |
| 6.3 | 16.82 [15.68, 17.68] | 2930 | 16.33 [15.42, 17.44] | 2056 | 1.030 [0.937, 1.116] |
| 9.5 | 15.43 [14.27, 16.44] | 1746 | 15.84 [14.78, 16.60] | 1314 | 0.975 [0.898, 1.074] |
| 12.8 | 15.53 [14.63, 16.46] | 1575 | 15.93 [14.98, 16.81] | 1211 | 0.975 [0.904, 1.058] |
| 17.4 | 16.16 [15.41, 17.03] | 1529 | 16.13 [15.61, 16.92] | 1204 | 1.002 [0.930, 1.058] |
| 22.6 | 16.30 [15.44, 17.03] | 1146 | 16.01 [15.43, 16.83] | 1116 | 1.018 [0.947, 1.074] |
| 29.5 | 15.98 [15.42, 16.64] | 1012 | 15.55 [15.05, 16.15] | 1005 | 1.027 [0.979, 1.081] |
| 37.7 | 16.36 [15.64, 17.01] | 735 | 16.10 [15.51, 16.67] | 784 | 1.017 [0.962, 1.071] |
| 48.5 | 16.46 [15.72, 17.15] | 482 | 15.70 [15.07, 16.54] | 704 | 1.049 [0.975, 1.108] |
| 61.4 | 14.76 [14.16, 15.50] | 500 | 15.10 [14.40, 15.63] | 481 | 0.978 [0.927, 1.045] |
| 75.5 | 14.15 [13.64, 14.63] | 261 | 14.72 [13.91, 15.11] | 264 | 0.961 [0.920, 1.027] |
| 93.8 | 14.23 [13.64, 14.60] | 287 | 13.77 [13.22, 14.38] | 273 | 1.033 [0.976, 1.078] |
| 122.7 | 13.56 [13.24, 14.38] | 351 | 13.85 [13.48, 14.32] | 254 | 0.979 [0.941, 1.043] |
| 145.8 | 13.42 [12.91, 13.93] | 328 | 13.89 [13.36, 14.19] | 387 | 0.966 [0.921, 1.022] |
| 191.4 | 13.50 [12.82, 13.70] | 420 | 13.52 [13.09, 13.75] | 452 | 0.998 [0.947, 1.028] |
| 233.2 | 12.74 [12.37, 13.25] | 568 | 12.52 [12.23, 13.12] | 679 | 1.018 [0.964, 1.062] |
| 307.6 | 11.74 [11.53, 12.04] | 530 | 11.73 [11.53, 11.98] | 433 | 1.001 [0.973, 1.033] |
| 378.2 | 11.10 [10.59, 11.51] | 1600 | 11.66 [11.00, 12.01] | 714 | 0.952 [0.900, 1.018] |

🛑 **NOT ONE of the 19 bins has a L/R CI that excludes 1.**

| level statistic | LEFT | RIGHT | L/R | 95 % CI | |
|---|---|---|---|---|---|
| near 3–20° | 16.164 | 16.130 | 1.0021 | [0.9539, 1.0394] | null |
| floor 3–50° | 16.296 | 16.014 | 1.0176 | [0.9860, 1.0369] | null |
| mid 50–120° | 14.225 | 14.284 | 0.9959 | [0.9658, 1.0319] | null |
| ref 120° | 13.486 | 13.874 | 0.9721 | [0.9400, 1.0166] | **null** |
| lock ≥320° | 11.102 | 11.664 | 0.9518 | [0.9004, 1.0181] | **null** |
| swing 0→120 | 1.208 | 1.154 | 1.0468 | [0.9883, 1.0865] | null |
| droop 120→380 | 1.215 | 1.189 | 1.0213 | [0.9518, 1.0936] | null |
| **geo, all 19 bins** | — | — | **0.9918** | **[0.9801, 1.0027]** | null |
| geo, inner (<105°, 13 bins) | — | — | 0.9949 | [0.9773, 1.0127] | null |
| geo, **outer** (≥105°, 6 bins) | — | — | **0.9852** | **[0.9717, 0.9968]** | ⚠ marginal |

⇒ **The 3–5 % split of §5 CONTROL 4 is the noise on a median over 2–3 bins.** Pooling all bins
gives 0.8 % and covers 1. The only statistic that excludes 1 is the 6-bin outer pool, at 1.5 %,
with an upper bound of 0.9968 — marginal, and one of ten statistics tested.

## 10.2 POWER — the positive control that makes the null interpretable

Scale the RIGHT side's δ by `f`, which multiplies the true L/R ratio by exactly `f`, and push it
through the identical pipeline.

| inject | geo ALL | geo INNER | geo OUTER | ref120 | lock |
|---|---|---|---|---|---|
| **f = 1.00** (negative control) | 0.9918 [0.980, 1.003] | 0.9949 [0.977, 1.013] | 0.9852 [0.972, 0.997] | 0.9721 [0.937, 1.014] | 0.9518 [0.900, 1.012] |
| f = 0.98 | 0.9720 [0.960, 0.983] **✓** | 0.9750 [0.958, 0.992] **✓** | 0.9655 [0.952, 0.977] **✓** | 0.9526 [0.919, 0.993] **✓** | 0.9328 [0.882, 0.992] **✓** |
| f = 0.95 | 0.9422 [0.931, 0.952] **✓** | 0.9451 [0.929, 0.962] **✓** | 0.9360 [0.923, 0.947] **✓** | 0.9235 [0.891, 0.963] **✓** | 0.9042 [0.855, 0.961] **✓** |
| f = 0.90 | 0.8926 [0.882, 0.902] **✓** | 0.8954 [0.880, 0.911] **✓** | 0.8867 [0.875, 0.897] **✓** | 0.8749 [0.844, 0.912] **✓** | 0.8566 [0.810, 0.911] **✓** |

**✓ = CI excludes 1.** ⇒ **A uniform 2 % left/right asymmetry would have been detected.** The
null is therefore informative, not underpowered: **a real rack asymmetry ≥ 2 % is EXCLUDED.**

## 10.3 ⭐ THE θ₀ SWEEP — the asymmetry is NOT a centre-offset artefact

θ₀ swept −7.00 → −1.50° in 0.25° steps; both sides rebuilt from scratch at every value.

| θ₀ | geo ALL | geo INNER | **geo OUTER** | floor | ref120 | lock |
|---|---|---|---|---|---|---|
| −7.00 | 0.9997 | 1.0061 | 0.9861 | 1.0244 | 0.9774 | 0.9355 |
| −6.00 | 1.0038 | 1.0125 | 0.9852 | 1.0243 | 0.9738 | 0.9533 |
| −5.25 | 0.9979 | 1.0028 | **0.9873** ← min | 1.0008 | 0.9805 | 0.9516 |
| **−4.25 (joint fit)** | 0.9917 | 0.9948 | 0.9852 | 1.0176 | 0.9721 | 0.9518 |
| −3.50 | 0.9921 | 0.9960 | 0.9837 | 1.0062 | 0.9653 | 0.9683 |
| −2.50 | 0.9883 | 0.9917 | 0.9809 | 0.9972 | 0.9669 | 0.9536 |
| −1.50 | 0.9875 | 0.9919 | 0.9780 | 0.9932 | 0.9561 | 0.9494 |

(full 23-row sweep in `two_sided.json → theta0_sweep`)

- **geo OUTER spans only 0.9780 → 0.9873 and NEVER reaches 1.** No plausible θ₀ makes the two
  sides coincide, and no plausible θ₀ can manufacture the residual either — its total leverage is
  **0.9 %**, less than the statistic's own CI half-width (1.3 %).
- geo ALL and geo INNER cross 1 inside the sweep, but their minima sit at the **grid edge**
  (−7.00) and the sweep is flat to ±0.8 % — there is no minimum to find.

🛑 **VERDICT: REAL vs ARTEFACT is decided against ARTEFACT — θ₀ is exonerated.** But what remains
is 1.5 %, not the 3–5 % the folded summary suggested.

### 10.3a The per-side θ₀ "disagreement" is a chord-extrapolation artefact

A one-sided fit must EXTRAPOLATE to the δ = 0 crossing, and on a curved δ(θ) the two chords split
symmetrically about the true centre, by an amount that GROWS with the fit window:

| fit window \|θ−θ₀\| ≤ | LEFT θ₀ | RIGHT θ₀ | split | **midpoint** |
|---|---|---|---|---|
| 8° | −4.121 | −4.334 | +0.213 | **−4.228** |
| 12° | −4.048 | −4.370 | +0.322 | **−4.209** |
| 18° | −4.037 | −4.419 | +0.382 | **−4.228** |
| 25° | −3.977 [−4.100, −3.868] | −4.429 [−4.515, −4.349] | +0.452 | **−4.203** |
| 40° | −3.983 | −4.478 | +0.495 | **−4.231** |

The split grows monotonically with window; the **midpoint is pinned at −4.20 to −4.23° at every
window**, against the joint fit **−4.251°**. ⇒ **This is the signature of extrapolation along a
chord, not two different centres.** [EVIDENCE — the window monotonicity plus the pinned midpoint.]
The disjoint CIs at a fixed window are real but measure the chord error, not the sensor zero.

## 10.4 THE CONFOUNDS

| confound | test | result |
|---|---|---|
| **IMU** | estimators with/without it | A **0.9852** [0.971, 0.998] · D **0.9839** [0.970, 0.996] · **B 0.9998** [0.966, 1.044] · **C 1.0028** [0.961, 1.039] (geo OUTER) |
| **additive δ bias** | survives in SECANT, cancels in LOCAL | local geo 0.9918 vs secant geo 0.9914 — identical ⇒ **not an additive bias** |
| **exposure, speed** | narrow speed bands, outer region | 1–2 m/s **0.9819** [0.965, 1.015] · 2–3 **0.9901** [0.971, 1.009] · 1–3 **0.9861** [0.974, 1.005] · 3–5 **1.0042** [0.969, 1.015] — **CI covers 1 in EVERY band** |
| **exposure, reweighted** | speed-matched + common-θ rebuild | geo **1.0018** (unstable in the outer bins — see below) |
| **road crown** | per-route heterogeneity, 10 routes ≥60 s | **Cochran Q = 5.32, df = 9, Q/df = 0.59 ⇒ HOMOGENEOUS**; pooled 0.9801 |
| **engaged vs manual** | a plant property must not care | ENGAGED geo ALL 0.9931 [0.983, 1.007] / OUTER 0.9702 [0.963, 0.994] · MANUAL geo ALL 0.9688 [0.941, 0.994] / OUTER 0.9957 [0.971, 1.010] — **the two disagree about WHERE the residual sits** |

🛑 **The single most informative line:** the outer residual is present in **both IMU-based**
estimators (A 0.9852, D 0.9839) and **absent in both IMU-free** ones (B 0.9998, C 1.0028). B and
C are 3× less precise, so this does not *exclude* a rack asymmetry — but their point estimates
land on 1.000 and 1.003. [EVIDENCE for the four numbers; **BELIEF** that the residual is IMU-side.]

⚠ **The exposure imbalance in the outer region is severe and in the wrong direction to ignore.**
Beyond 120° of wheel, LEFT sits at 1–2 m/s (103 s of 184) while RIGHT is spread to 5 m/s (48 s of
138). Front-tyre slip grows with speed and DEPRESSES achieved yaw, which INFLATES the apparent
ratio — so the faster-driven side reads slower. **That is exactly the sign of the residual.**
Inside every narrow speed band the residual's CI covers 1.

⚠ **The speed-matched rebuild is only trustworthy inside ~120°.** Matching by `min(n_L, n_R)`
across speed sub-bins discards most of the outermost bin's data, and its per-bin L/R scatters from
0.878 to 1.274 there (against 0.98–1.06 inside 120°); it returns lock 13.08 (L) vs 10.26 (R)
against the unmatched 11.10 / 11.66. **Read its geo = 1.0018 as an inner-region statement.**

⚠ **Tyre / alignment asymmetry is UNRESOLVABLE from this data.** Nothing here can separate a rack
property from a per-side toe or tyre-radius property; both would move δ(θ) the same way. Any real
residual must be reported as a *vehicle* asymmetry, never attributed to the rack specifically.

## 10.5 THE ANSWER

**[EVIDENCE] The rack is left/right symmetric to within ~1.5 %, and a real asymmetry ≥ 2 % is
excluded by a positive control.** The 3–5 % level split visible in the folded study's per-side
summary scalars is **not** reproduced by the full paired comparison: every one of the 19 per-bin
CIs covers 1, and so do `ref120` (0.9721 [0.940, 1.017]) and `lock` (0.9518 [0.900, 1.018]).

**[EVIDENCE] It is NOT an artefact of θ₀.** The centre offset has 0.9 % total leverage on the
outer L/R level over −7 → −1.5°, and cannot drive it to 1 anywhere. The per-side θ₀ refits
(−3.977 vs −4.429) differ by 0.45°, but that split grows with the fit window while its midpoint
stays pinned at −4.21 ± 0.02° — chord extrapolation, not two centres.

**[BELIEF, well-supported] The 1.5 % outer residual is instrument- or exposure-side, not
mechanical.** It is present only in the two IMU-based estimators, dies inside every narrow speed
band, and sits exactly where the two sides' speed exposure is most mismatched.

⇒ **In one sentence for the operator: the rack is symmetric — left and right turns quicken the
same way, to within about 1.5 %, and the small left/right difference in the earlier summary was
measurement noise plus unequal exposure, not the steering.**

### Why he only ever sees positive angle
Not a vehicle property and not measurable from this data: every published curve in §§0–9 is folded
on `|θ − θ₀|` by construction (`curve_from(..., fold=True)`), so a folded plot **cannot** show a
negative angle. The unfolded curves are now in `two_sided.json` with all three sign axes.

## 10.6 FILES ADDED

| file | what |
|---|---|
| `rlog-tools/studies/steering-ratio/ratio_two_sided.py` | per-side curves, paired bootstrap, θ₀ sweep, injection power control, confounds |
| `analysis-2020accord/_scratch/cache/ratio/two_sided.json` | the deliverable — per-side `theta`/`local`/`local_lo`/`local_hi`/`n_bin`, all three sign axes, per-side θ₀, the sweep, every confound |
