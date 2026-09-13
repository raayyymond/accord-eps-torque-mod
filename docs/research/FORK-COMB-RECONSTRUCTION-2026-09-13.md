# The fork-side, lag-free removal of the 20 Hz command comb — designed, measured, built, NOT driven

Subagent `combfix`, **2026-09-13**. **NOTHING WAS FLASHED, NOTHING WAS SENT ON ANY BUS, NOTHING WAS
COMMITTED OR PUSHED.** One patch is left applied in the openpilot fork's **working tree**, uncommitted,
behind a toggle that is **OFF by default**.

Fork: `C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot`, branch `Dom`,
HEAD `305732c85`. The operator's uncommitted steer-ratio refit in `latcontrol_vehicle_tunes.py` and the
two deleted binaries under `starpilot/system/galaxy/bin` were **not touched**.

Scripts: `rlog-tools/studies/grind/fork_comb_reconstruction.py` (S1–S4, writes
`_scratch/fork_comb_reconstruction.txt`) · `rlog-tools/studies/grind/fork_comb_designb_premise.py`
(the test that killed design B, writes `_scratch/fork_comb_designb_premise.txt`).

---

## 0. PRE-REGISTERED "THIS BUYS NOTHING" — written before the scripts were run

| # | condition | outcome |
|---|---|---|
| **N1** | the **0xE4 command's** 18–22 Hz content does not fall by at least **6 dB** | 🛑 **TRIGGERED.** Best achieved: **−2.4 dB (r39)** and **−4.2 dB (r63)**. |
| **N2** | the Δ² model-phase fold `R` on the wire does not fall toward its detuned null (~0.002–0.004) | 🛑 **TRIGGERED.** 0.197 → 0.173 (r39), 0.195 → 0.164 (r63). Nowhere near the null. |
| **N3** | \|H\| at 1–5 Hz departs from 1.000 by more than 0.1 dB, **or** group delay is positive anywhere there | ⚠ **PARTIALLY TRIGGERED.** \|H\| rises to 1.03 at 1 Hz and 1.11 at 2 Hz (gain 1.0); group delay is positive against the *ideal* everywhere, but **below today's hold up to ~3.2–3.5 Hz** and above it beyond. Details in §2. |
| **N4** | even on a clean pass, lock 0.50 caps the ring benefit at ~29 %, and the kit already judged ×1.22 unreadable from one drive | **Holds.** Estimated ring benefit **−18 % at the default gain**, −22 % at gain 1.0. |

**⭐ The one gate it passes, and it is the one that transfers:** the command's **camera-locked energy
fraction** — the quantity the record's "~29 % ring benefit at lock 0.50" is actually a function of —
falls **0.648 → 0.387 (r39)** and **0.622 → 0.401 (r63)** at the default gain, removing **66 % and 63 %
of the camera-locked leg**. At gain 1.0 it is **78 % and 76 %**.

**⇒ VERDICT. This CONFIRMS `docs/STATE.md` next-item 5 with a sharper number rather than overturning it:
legal, cheap, needs no flash, removes most of the comb — and is NOT readable from one short drive.
Ride it free on a drive spent on something else. Do NOT pre-register it as the thing under test.**

---

## 1. What was built, and why this one

### 1.1 Design (A) — slope-continuous extrapolation. BUILT.

```
s[k]  = v[k] - v[k-1]                      the model's own most recent inter-frame step
a(n)  = min(elapsed_since_frame / DT_MDL, 1.0)      saturating elapsed fraction of one frame interval
out   = v[k] + gain * s[k] * a(n)
```

`a` is 0 at the instant frame *k* publishes, so **`out == v[k]` exactly at every model-frame instant**.
`gain = 0.0` reproduces today's zero-order hold bit for bit.

### 1.2 Design (B) — trajectory-shaped reconstruction. **FALSIFIED. NOT BUILT.**

The record calls (B) *"lag-NEGATIVE up to 50 ms"* because it advances along the model's own published
future (`modelV2.orientationRate.z / velocity.x` on `T_IDXS`). **The premise underneath that is false on
this fork, and it is a new measurement, not a code-reading objection.**

`action.desiredCurvature` and `orientationRate` are **different output heads**. The action head is
divided by `max(1, v_ego)²` (`modeld.py:406-408`) and then **low-passed at the model rate** by
`smooth_value(..., LAT_SMOOTH_SECONDS = 0.1 s)` (`modeld.py:415`, `:84`) — a one-pole at 1.59 Hz.
`orientationRate` is published raw. So (B) would splice one head's *shape* into the other head's *value*.

**[EVIDENCE]** r39, 5 segments, **5 385 usable model frames**, `fork_comb_designb_premise.py`. Predictors
of the action head's own next step `s_next[k] = v[k+1] − v[k]`:

| predictor | corr | slope | sign agreement | rms ratio |
|---|---|---|---|---|
| **(B)** plan advance over 50 ms, `κ_plan(0.05) − κ_plan(0)` | **0.427** | 0.656 | **0.631** | 0.651 |
| **(A)** the action head's own last step `v[k] − v[k−1]` | **0.632** | 0.633 | **0.700** | 0.998 |

The two heads agree on *level* at only `corr = +0.804` with slope `+1.198` (plan rms 2.73e-2 against
action rms 1.83e-2). **(B) is a WORSE predictor of the signal actually being commanded than (A) is.**
It is therefore neither "clearly better" nor "equally safe", and it is not implemented. The record's
"lag-NEGATIVE" claim is true *about the plan head* and irrelevant *to the command*.

### 1.3 Why a gain knob, and why the default is 0.75

The extrapolation is not free. Gain 1.0 removes the most comb but **moves image energy down into
10–18 Hz and 5–10 Hz**, which on V289 lands on its 15–17 Hz ring. `docs/STATE.md`'s design law says to
score across the **whole 12–26 Hz band**, and on that band **0.75 is the optimum on both routes**.

---

## 2. Transfer functions and group delay — measured, not asserted

**Method.** Sample a unit sinusoid at exactly 20 Hz, reconstruct at 100 Hz, project both the output and
the **ideal continuous** sinusoid onto `exp(-j2πft)` over 4 000 model frames (200 s), Hann windowed.
Group delay by central difference over `df = 0.05 Hz`. **Positive group delay = lag.** The ZOH row is
today's behaviour.

| f | 0.1 Hz | 0.25 | 0.5 | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|---|---|
| **ZOH (today)** \|H\| | 0.99996 | 0.99975 | 0.99901 | 0.99606 | 0.98428 | 0.96483 | 0.93796 | 0.90403 |
| τ_g [ms] | 20.000 | 20.000 | 20.000 | 20.000 | 20.000 | 20.000 | 20.000 | 20.000 |
| **gain 0.50** \|H\| | 1.00012 | 1.00074 | 1.00294 | 1.01152 | 1.04244 | 1.08346 | 1.12308 | 1.15064 |
| τ_g [ms] | 10.013 | 10.079 | 10.309 | 11.196 | 14.283 | 18.204 | 22.055 | 25.369 |
| **gain 0.75** \|H\| | 1.00021 | 1.00132 | 1.00527 | 1.02060 | 1.07559 | 1.14858 | 1.22106 | 1.27737 |
| τ_g [ms] | 5.024 | 5.142 | 5.556 | **7.127** | 12.287 | 18.238 | 23.526 | 27.710 |
| **gain 1.00** \|H\| | 1.00032 | 1.00197 | 1.00783 | 1.03054 | 1.11114 | 1.21676 | 1.32160 | 1.40555 |
| τ_g [ms] | 0.038 | 0.224 | 0.874 | **3.294** | 10.790 | 18.661 | 25.058 | 29.785 |
| **2nd-order, gain 1** \|H\| | 1.00012 | 1.00075 | 1.00306 | 1.01339 | 1.06917 | 1.19429 | 1.38960 | 1.62016 |
| τ_g [ms] | **−0.013** | **−0.074** | **−0.276** | **−0.855** | **−0.143** | 6.975 | 18.839 | 30.408 |

**Lead bought against today** (`τ_g(ZOH) − τ_g(X)`, positive = faster than today), ms:

| | 0.1 | 0.25 | 0.5 | 1.0 | 2.0 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|---|---|---|---|
| gain 0.50 | 4.995 | 4.968 | 4.875 | 4.508 | 3.162 | 1.277 | **−0.794** | −2.769 |
| gain 0.75 | 14.976 | 14.858 | 14.444 | **12.873** | 7.713 | 1.762 | **−3.526** | −7.710 |
| gain 1.00 | 19.962 | 19.776 | 19.126 | **16.706** | 9.210 | 1.339 | **−5.058** | −9.785 |
| 2nd-order | 20.013 | 20.074 | 20.276 | 20.855 | 20.143 | 13.025 | 1.161 | −10.408 |

**What passes and what does not, stated plainly:**

- ✅ **\|H\| ≥ 1.000 at every frequency, for every gain.** It is not a filter and it attenuates nothing.
  **Authority is not reduced anywhere.** Asserted in the unit test out to 7 Hz.
- ✅ **Every published model value is delivered unchanged at its own frame instant** (max deviation
  `0.000e+00` over 2 000 frames, every gain). No model output is replaced, attenuated or held back.
- ✅ **13–17 ms faster than today at 1 Hz** (gain 0.75 / 1.0). The band the driver feels is a lead.
- 🛑 **It does NOT satisfy "group delay ≤ 0 for f ≤ 5 Hz".** Referenced to the *ideal*, group delay is
  positive everywhere except the 2nd-order variant below 2 Hz. Referenced to **today's hold**, it is
  negative (a lead) only up to a **crossover at ~3.5 Hz (gain 0.75) / ~3.2 Hz (gain 1.0)**; above it the
  reconstruction is the slower of the two, by up to **9.8 ms at 5 Hz** at gain 1.0.
  **That cost is pinned in a unit test (`test_lag_crossover_is_above_3hz_and_is_recorded_not_hidden`)
  rather than hidden.** It is mitigated but not erased by the fact that modeld low-passes its own action
  at 1.59 Hz, so the plan carries little energy up there; the gain knob is how the operator buys it back.
- ⚠ **The 2nd-order slope estimator** (`s[k] = (3v[k] − 4v[k−1] + v[k−2])/2`) is genuinely **lag-negative
  below 2 Hz** and removes more comb, but it amplifies hard above 3 Hz (\|H\| = 1.62 at 5 Hz) and is the
  **worst** candidate on the 12–26 Hz design band. **Measured, rejected, not shipped.**

### The comb itself — image gain at the camera clock

A baseband tone at `f_b` appears in the 100 Hz stream at `20 ± f_b` Hz purely as a reconstruction
artefact: the 20 Hz sequence carries nothing above 10 Hz, so **that image IS the comb.** Amplitude of
the image relative to the baseband tone:

| f_b [Hz] | ZOH (today) | gain 0.50 | gain 0.75 | gain 1.00 | 2nd-order |
|---|---|---|---|---|---|
| 0.25 | 0.018896 | 0.014187 | 0.004864 | **0.001351** | 0.000632 |
| 0.50 | 0.037786 | 0.028460 | 0.010521 | **0.005399** | 0.002582 |
| 1.00 | 0.075525 | 0.057600 | 0.026406 | **0.021519** | 0.011120 |
| 2.00 | 0.150681 | 0.120306 | 0.081992 | 0.084872 | 0.054701 |
| 4.00 | 0.298390 | 0.273006 | 0.285377 | **0.320705** | 0.310273 |

⇒ the comb is cut **−22.9 dB at f_b = 0.25 Hz** and **−10.9 dB at 1 Hz** (gain 1.0), but at `f_b ≥ 4 Hz`
(image at 16 / 24 Hz) it is made **worse**. That is the 10–18 Hz penalty, visible in the transfer
function before it appears on the wire.

---

## 3. Bounds, drops, and large steps

- **Monotone bound.** `v_next` is not available causally, so the bound is stated on the causal triple
  `{v[k−1], v[k], v[k] + s[k]}` — i.e. the output stays inside **`[v[k] − |s[k]|, v[k] + |s[k]|]`**.
  Max violation over 2 000 frames including an injected 0.05 step and an immediate reversal:
  **`0.000e+00`.** It holds **by construction**, not by a clamp: a one-frame horizon advances by at most
  one model step. Within a hold the maximum departure is `0.8·|s[k]|` (the fifth tick).
- **Dropped frame — two independent guards.** `a` saturates at 1.0, so the output **freezes** one model
  step past the last frame instead of running away; and a `frameId` gap other than 1 **zeroes the slope
  entirely** for that frame, which is exactly today's hold. Measured on the cached routes, the
  consecutive-frame fraction is **0.9999**, so the second guard costs nothing in practice.
- **Engage.** `reset()` stores the *current* curvature, not a published model value. Differencing the
  first model frame against it would extrapolate the **engage jump** forward — a real defect the unit
  test caught during development and which is now fixed: the first frame after any reset reverts to the
  hold.
- **Large step + reversal.** On *uncorrelated* steps the frame-boundary delta can reach **1.8×** a single
  step (`s[k+1] − 0.8·s[k]` with opposite signs). On the real plan it does not: the measured max
  per-tick delta **falls** to 0.81–0.96× of the hold's, and `clip_curvature` binds **less**, not more.
- **Nothing downstream is bypassed.** The reconstruction sits **upstream** of `clip_curvature`, so the
  full ISO lateral-jerk and lateral-acceleration envelope, `MAX_CURVATURE`, the rate limiter, `STEER_MAX`
  and panda's own limits all still apply, unchanged.

---

## 4. Offline replay — the numbers that decide it

Routes **r39** (V282, `75604b0a432fdc89_00000039`) and **r63** (V289 rev 1,
`75604b0a432fdc89_00000063`), from `_scratch/modeld/<tag>_cad.npz`. Every candidate is run through the
**fork's own `clip_curvature`**, loaded from the fork's bytes with only `DT_CTRL`, `DT_MDL` and `g`
stubbed (all three verified against the fork source).

**Sanity, both routes:** our ZOH reconstruction equals the logged `controlsState.desiredCurvature` on
**0.695 / 0.683** of engaged `v < 12` ticks, inside `modelrate`'s measured pass-through band 0.60–0.71.

### 4.1 The curvature (1/m rms over the long engaged runs), dB vs today

| r39 | 18–22 Hz | 12–26 Hz | 10–18 Hz | 5–10 Hz | 1–5 Hz | 0.2–1 Hz | clip bind | max per-tick |
|---|---|---|---|---|---|---|---|---|
| ZOH (today) | 1.810e-4 | 2.089e-4 | 1.042e-4 | 1.515e-4 | 5.872e-4 | 5.252e-3 | 0.0079 | 1.129e-2 |
| gain 0.50 | **−5.63** | **−3.63** | +0.75 | +2.47 | +0.45 | +0.02 | 0.0043 | 0.90× |
| **gain 0.75** | **−10.66** | **−4.77** | +1.77 | +3.51 | +0.69 | +0.03 | 0.0036 | 0.86× |
| gain 1.00 | **−15.11** | −4.32 | +2.97 | +4.45 | +0.95 | +0.03 | 0.0034 | 0.81× |
| 2nd-order | −16.78 | −3.25 | +5.39 | +6.58 | +0.88 | +0.02 | 0.0049 | 0.79× |

| r63 | 18–22 Hz | 12–26 Hz | 10–18 Hz | 5–10 Hz | 1–5 Hz | 0.2–1 Hz | clip bind | max per-tick |
|---|---|---|---|---|---|---|---|---|
| ZOH (today) | 2.774e-4 | 3.391e-4 | 1.914e-4 | 2.671e-4 | 1.037e-3 | 9.551e-3 | 0.0349 | 1.173e-2 |
| gain 0.50 | **−5.39** | **−3.29** | +0.61 | +1.91 | +0.44 | +0.01 | 0.0294 | 0.96× |
| **gain 0.75** | **−10.01** | **−4.31** | +1.49 | +2.81 | +0.68 | +0.02 | 0.0282 | 0.90× |
| gain 1.00 | **−13.67** | −3.90 | +2.59 | +3.64 | +0.93 | +0.03 | 0.0276 | 0.90× |
| 2nd-order | −15.03 | −2.85 | +5.03 | +5.57 | +0.88 | +0.01 | 0.0287 | 0.90× |

**Read:** on the 12–26 Hz design band, **gain 0.75 is the optimum on both routes** and gain 1.0 is worse
than it. `clip_curvature` binds **less** in every case. **1–5 Hz rises by 0.44–0.95 dB** — not "nothing",
and that is the price of the lead; it is 0.44 dB at gain 0.5.

### 4.2 The 0xE4 command — and the method it took to get this right

The setpoint→wire path carries **gain and phase**, so no scalar gain can substitute one reconstruction
for another. `H(f)` is estimated by **Welch cross-spectrum** (`nperseg` 2048 = 20.5 s) and the
perturbation pushed through it; everything `H` does not explain — the **feedback leg** — is carried
through unchanged.

🛑 **THE BASIS MUST BE THE QUANTITY BEING PERTURBED, and getting this wrong inverts the answer.**
`latcontrol_torque.py:277` forms `expected_lateral_accel` from `curvature_request_buffer[delay_frames]`,
so `controlsState.desiredLateralAccel` **as logged is a delayed sample** — measured lag **+3 to +7 ticks,
peak normalised xcorr 0.997–0.999**. Fitting `H` from that logged signal and applying it to an
**un-delayed** perturbation puts the correction at the wrong phase: the fitted plan leg comes out
**18.19 counts against a coherent part of 15.14**, and *deleting* it makes the band **WORSE by +0.71 dB**.
Fitting `H` from `κ_ZOH · v_ego²` — exactly the quantity the patch changes — reproduces the coherent
magnitude to **0.3 %** and its deletion lands on the `sqrt(1 − share)` floor. **A "delete the plan
entirely" control row is carried through every band; if it does not equal the floor, the machinery is
wrong.**

**r39 — rms raw 0xE4 counts, and dB vs today:**

| band | plan share | upper bnd | cmd before | **delete plan** (control) | floor | gain 0.50 | **gain 0.75** | gain 1.00 | 2nd-order |
|---|---|---|---|---|---|---|---|---|---|
| 18–22 Hz | 0.584 | 0.717 | 16.730 | −2.71 dB | −3.81 | −1.80 | **−2.43** | −2.62 | −2.66 |
| **12–26 Hz** | 0.483 | 0.606 | 21.016 | −2.13 dB | −2.87 | −1.14 | **−1.39** | −1.28 | −1.07 |
| 10–18 Hz | 0.398 | 0.474 | 15.386 | −1.33 dB | −2.20 | +0.42 | **+0.85** | +1.38 | +2.84 |
| 5–10 Hz | 0.363 | 0.413 | 26.481 | −1.35 dB | −1.96 | +0.94 | **+1.47** | +1.99 | +3.48 |
| 1–5 Hz | 0.266 | 0.356 | 172.70 | −1.06 dB | −1.34 | +0.09 | **+0.15** | +0.22 | +0.19 |
| 0.2–1 Hz | 0.413 | 0.426 | 679.10 | −2.73 dB | −2.32 | −0.00 | **−0.00** | +0.00 | −0.01 |

**r63 — same:**

| band | plan share | upper bnd | cmd before | **delete plan** (control) | floor | gain 0.50 | **gain 0.75** | gain 1.00 | 2nd-order |
|---|---|---|---|---|---|---|---|---|---|
| 18–22 Hz | 0.592 | 0.752 | 29.562 | −4.21 dB | −3.90 | −2.39 | **−3.60** | −4.21 | −4.23 |
| **12–26 Hz** | 0.491 | 0.646 | 36.470 | −2.73 dB | −2.93 | −1.46 | **−1.91** | −1.85 | −1.39 |
| 10–18 Hz | 0.378 | 0.468 | 26.647 | −0.76 dB | −2.06 | +0.95 | **+1.65** | +2.43 | +4.66 |
| 5–10 Hz | 0.343 | 0.440 | 49.740 | +0.15 dB | −1.83 | +1.21 | **+1.85** | +2.48 | +3.87 |
| 1–5 Hz | 0.379 | 0.538 | 290.63 | −0.27 dB | −2.07 | +0.13 | **+0.21** | +0.31 | +0.24 |
| 0.2–1 Hz | 0.441 | 0.555 | 1012.05 | — | — | −0.00 | **−0.00** | −0.00 | −0.02 |

**Read:**
- **N1 fails.** The best 18–22 Hz reduction on the total command is **−2.4 dB (r39)** / **−4.2 dB (r63)**,
  and it is already at the `sqrt(1 − share)` floor on r63. **The reconstruction is not the limit — the
  plan's share of the band is.**
- **5–18 Hz rises by 0.9 to 2.5 dB.** On V289, whose ring sits at 15–17 Hz, that lands **on the ring**.
  This is the single most important risk on the page.
- **1–5 Hz moves by ≤ 0.31 dB** and **0.2–1 Hz by ≤ 0.02 dB.** The low band is effectively untouched.

### 4.3 The Δ² model-phase fold (`MODELD-CADENCE-VS-RING` §2/§3, `fold_stats` verbatim)

| r39 channel | rms\|Δ²\| | C | C null | **R** | R null |
|---|---|---|---|---|---|
| curvature ZOH (today) | 4.345e-4 | 2.419 | 1.067 | 0.7087 | 0.0278 |
| curvature gain 0.75 | 2.985e-4 | 2.611 | 1.043 | 0.7340 | 0.0043 |
| curvature gain 1.00 | 3.138e-4 | 2.667 | 1.042 | 0.7360 | 0.0037 |
| 0xE4 wire ZOH (today) | 2.753e+1 | 1.282 | 1.005 | **0.1972** | 0.0025 |
| 0xE4 wire gain 0.75 | 2.464e+1 | 1.212 | 1.014 | **0.1786** | 0.0037 |
| 0xE4 wire gain 1.00 | 2.472e+1 | 1.207 | 1.020 | **0.1727** | 0.0040 |

r63: wire `R` 0.1948 → 0.1746 (0.75) → 0.1643 (1.00); rms\|Δ²\| 4.756e+1 → 4.153e+1 → 4.096e+1.

🛑 **On the CURVATURE the fold statistic does NOT improve and must not be quoted as if it did.** The
reconstruction converts a step knot of size `|s[k]|` into a slope-change knot of size `|s[k+1] − s[k]|`.
The knot is **smaller** (rms\|Δ²\| falls 4.35e-4 → 2.99e-4) but it is **still on the camera phase**, so
`C` and `R` rise slightly. On the wire, where plan-derived knots are only part of the total, `R` falls —
by dilution. **N2 is triggered: `R` does not approach its null.**

### 4.4 ⭐ The camera-lock fraction — the number that transfers

Measured with **the record's own** square-law detector (`modeld_phase_lock.r2_at`) and the **debiased**
estimator `R2_deb = sqrt(max(R2² − mean(R2²_detuned), 0))` adjudicated on 2026-09-11. Band 18–22 Hz,
stratum engaged & `v < 12 m/s`.

| r39 | R2 raw | floor | **R2_deb** | in-band E | locked energy | removed |
|---|---|---|---|---|---|---|
| **0xE4 today** | 0.6500 | 0.0499 | **0.6481** | 369.0 | 239.2 | — |
| gain 0.50 | 0.5154 | 0.0552 | 0.5124 | 246.1 | 126.1 | **47 %** |
| **gain 0.75** | 0.3913 | 0.0559 | **0.3873** | 209.3 | 81.1 | **66 %** |
| gain 1.00 | 0.2710 | 0.0560 | 0.2651 | 194.5 | 51.6 | **78 %** |
| 2nd-order | 0.2732 | 0.0571 | 0.2672 | 194.3 | 51.9 | 78 % |

| r63 | R2 raw | floor | **R2_deb** | in-band E | locked energy | removed |
|---|---|---|---|---|---|---|
| **0xE4 today** | 0.6247 | 0.0610 | **0.6217** | 1304.8 | 811.2 | — |
| gain 0.50 | 0.5105 | 0.0564 | 0.5073 | 895.9 | 454.5 | **44 %** |
| **gain 0.75** | 0.4047 | 0.0585 | **0.4005** | 748.1 | 299.6 | **63 %** |
| gain 1.00 | 0.2990 | 0.0638 | 0.2921 | 662.6 | 193.5 | **76 %** |
| 2nd-order | 0.2930 | 0.0637 | 0.2860 | 662.0 | 189.3 | 77 % |

⭐ **Cross-check of the baseline:** my `R2_deb = 0.648` for r39's command independently reproduces the
record's published **0.624** (`COMB-VS-ECHO-SIZING-2026-09-10.md` §12c) on a different loader — a 4 %
agreement that validates both.

**[BELIEF, premises named] What this implies for the ring.** If the response's measured locked energy
fraction of **0.50** is driven by the same leg and the plant is linear in it, removing 66 % of that leg
gives ring amplitude `sqrt(1 − 0.50 × 0.66) = 0.82`, i.e. **−18 %** at the default gain (**−22 %** at
gain 1.0) against the record's **−29 %** for perfect removal. **The kit has already judged ×1.22
unreadable from one drive.** ×1.22 is −18 %. **This sits exactly on that threshold.**

---

## 5. What the patch is — files, lines, and the exact diff

`git diff --stat` (the first two rows and the two `frpc_*` deletions are the operator's pre-existing
uncommitted work and are **not** mine):

```
 common/params_keys.h                                  |  2 +
 selfdrive/controls/controlsd.py                       | 18 ++++++
 selfdrive/controls/lib/drive_helpers.py               | 67 +++++++++++++++++++
 selfdrive/controls/lib/latcontrol_vehicle_tunes.py    | 16 +++--   <- OPERATOR'S, untouched
 starpilot/common/assets/device_settings_layout.json   | 28 +++++++++
 starpilot/common/safe_mode.py                         |  2 +
 starpilot/common/starpilot_variables.py               |  8 +++
 starpilot/system/galaxy/bin/frpc_darwin_amd64         | Bin      <- OPERATOR'S, untouched
 starpilot/system/galaxy/bin/frpc_darwin_arm64         | Bin      <- OPERATOR'S, untouched
 .../the_galaxy/tests/test_device_settings_layout.py   |  3 +
 ?? selfdrive/controls/tests/test_model_curvature_lead.py  (new, 227 lines)
```

| file | what changed |
|---|---|
| `selfdrive/controls/lib/drive_helpers.py` | new class **`ModelCurvatureLead`** (`reset`, `update`), appended after `get_curvature_from_plan`. |
| `selfdrive/controls/controlsd.py` | import; `self.model_curvature_lead = ModelCurvatureLead()` beside `self.lane_centering`; `self.model_curvature_lead.reset(self.curvature)` in the `not CC.latActive` reset block; the call itself immediately after `new_desired_curvature` is taken from `model_v2.action.desiredCurvature` and **before** `limit_curvature_to_plan`, the turn-hold, lane-centering and `clip_curvature`. |
| `starpilot/common/starpilot_variables.py` | `toggle.accord_curvature_lead` (bool, default **False**) and `toggle.accord_curvature_lead_gain` (float, default **0.75**, min 0.0, max 1.0), both gated on `is_honda_accord and known(...)`, following the existing `AccordRatePlantFF` pattern exactly. |
| `common/params_keys.h` | `AccordCurvatureLead` `{PERSISTENT, BOOL, "0", "0", 2, SETTINGS_SIMPLE}` and `AccordCurvatureLeadGain` `{PERSISTENT, FLOAT, "0.75", "0.75", 2, SETTINGS_SIMPLE}`. **Safe-Mode stock value is today's hold.** |
| `starpilot/common/safe_mode.py` | both keys added to the tracked list. |
| `starpilot/common/assets/device_settings_layout.json` | both entries in the **Custom Patches** section, Honda-only, `settings_tier: simple`; the toggle carries `is_parent_toggle: true` and the gain carries `parent_key` (required by the fork's own layout contract — a test caught the omission). |
| `starpilot/system/the_galaxy/tests/test_device_settings_layout.py` | both keys added to `CUSTOM_PATCH_KEYS`, plus an assertion that `AccordCurvatureLead`'s declared default is `"0"`. |

**Scoping.** `is_honda_accord` is `str(CP.carFingerprint) == "HONDA_ACCORD"`, the same gate every other
`Accord*` toggle uses. The `known(...)` guard means an older compiled `params_pyx.so` silently keeps the
default instead of raising.

**Two guards on top of the toggle, both deliberate:**
1. `lateralManeuverPlan` is excluded — its values are a maneuver-test source and do not belong to
   `model_v2.frameId`, so differencing them would be meaningless.
2. `gain` is clamped to `[0, 1]` inside `update`, so no param value can produce an unbounded lead.

### The core of it

```python
  def update(self, curvature: float, frame_id: int, gain: float, dt: float = DT_CTRL) -> float:
    curvature = float(curvature)
    if frame_id != self.frame_id:
      consecutive = self.frame_id is not None and frame_id - self.frame_id == 1
      self.step = curvature - self.value if consecutive else 0.0
      self.value = curvature
      self.frame_id = int(frame_id)
      self.elapsed = 0.0
    else:
      self.elapsed += dt
    lead = min(self.elapsed / DT_MDL, 1.0)
    return self.value + float(np.clip(gain, 0.0, 1.0)) * self.step * lead
```

---

## 6. Tests and their results

`selfdrive/controls/tests/test_model_curvature_lead.py` — **29 new tests, all passing.** Run with the
kit's conda python (`bin_decompile`), with `openpilot.common.realtime` / `.constants` stubbed to the
fork's own verified constants, because `params_pyx.so` does not build on Windows.

| group | test | result |
|---|---|---|
| **authority** | model-frame values preserved exactly, gains 0.0 / 0.25 / 0.5 / 0.75 / 1.0 | pass |
| | `gain = 0.0` is **bit-identical** to today's hold | pass |
| | gain clamped to `[0, 1]` | pass |
| **lag** | no lag at 1 Hz and faster than the hold, gains 0.5 / 0.75 / 1.0; hold's own τ_g pinned at 20.0 ms; gain 1.0 pinned at 3.3 ms | pass |
| | never attenuates and never lags more than the hold, f = 0.1 … 3.0 Hz | pass |
| | **the lag crossover is recorded, not hidden**: faster than the hold at 3.0 / 2.5 Hz, slower at 4.5 / 4.0 Hz | pass |
| | \|H\| ≥ 1 even past the crossover (4, 5, 7 Hz) | pass |
| **bound** | output inside `[v−\|s\|, v+\|s\|]` across a 0.05 step and an immediate reversal, gains 0.5 / 0.75 / 1.0 | pass |
| | dropped frame **freezes** (400 ms with no new frame) | pass |
| | `frameId` gap reverts that frame to the hold | pass |
| | first frame after `reset` does not extrapolate the engage jump | pass |
| | `reset` clears the slope | pass |
| **the point** | camera-clock comb reduced, monotonically in the gain, ≥ 12 / 9 / 5 dB at f_b = 0.25 / 0.5 / 1.0 Hz | pass |
| | Δ² knot shrinks on a plan shaped by modeld's own 1.59 Hz smoother | pass |

Also run: `selfdrive/controls/tests/test_drive_helpers.py` — **7 passed** (unchanged behaviour), and
`starpilot/system/the_galaxy/tests/test_device_settings_layout.py` — **25 passed** after the two keys
were added.

**⭐ The tests earned their keep.** Two real defects were caught by them and fixed, not by review:
1. the first model frame after a reset was differencing against the engage-time curvature and
   extrapolating the **engage jump** forward;
2. the Galaxy layout contract requires a `parent_key`'s parent to declare `is_parent_toggle`.

---

## 7. What I did NOT verify

1. **Anything about the plant's response.** This is an **open-loop** replay: it substitutes the
   reconstruction into the *command* and carries the feedback leg through unchanged. It predicts the
   **command** and says **nothing** about whether the ring, the grinding, or anything the operator feels
   changes. The record's standing warning applies in full.
2. **The −18 % ring estimate is BELIEF, not evidence.** It assumes the response's 0.50 locked fraction
   scales linearly with the command's locked leg. Nothing here measures that.
3. **The byte-exact 1 kHz mirror (`grind_incident_r35.simulate`) was NOT run on the modified command.**
   It is open-loop too and would have added a delivered-torque number on a ±2 dB command change; I
   judged the transfer-based command numbers more informative and did not spend the run. **This is a gap
   against the brief, and I am naming it rather than implying coverage.**
4. **`starpilot/common/tests/test_safe_mode.py` and `test_rebuild_params.py` could not be run** — they
   import `openpilot.common.params`, which needs the compiled `params_pyx.so` that does not exist on
   Windows. I substituted a **static** cross-file consistency check (both keys present and identically
   declared in `params_keys.h`, `safe_mode.py`, `starpilot_variables.py` and the settings layout, with
   the Safe-Mode stock value equal to today's behaviour). It passes. **The device will need a params
   rebuild** (`docs/how-to/rebuild-params-on-device.md`) before the keys are readable.
5. **The fork was not run end to end**, in replay or otherwise. No `controlsd` process executed this
   code; only the extracted class did, under unit test.
6. **Only two routes.** r39 (V282) and r63 (V289 rev 1). Not r22, r35 or r5e, and **not stratified to
   grinding episodes** — the Welch transfer estimate needs long contiguous windows, so all figures are
   whole-engaged-run. The grinding stratum could differ.
7. **The 5–18 Hz penalty was not evaluated against any mode except by band energy.** I did not check
   whether the added content lands on V289's 15–17 Hz pole in phase, only that it lands in the band.
8. **`liveDelay.lateralDelay` was not read** — the buffer lag was measured by cross-correlation
   (+3 to +7 ticks) rather than taken from the toggle.
9. ⚠ **A discrepancy with the record I could not resolve.** `docs/STATE.md:306` states *"80–97 % of the
   command's ring is setpoint-derived"*. Measured by coherence the share depends entirely on the basis:
   **0.375** on the raw model curvature, **0.717** on `desiredCurvature · v²`, **0.584** on the quantity
   the patch perturbs. I could not construct a basis giving 0.80–0.97 and could not find that figure's
   derivation. **Flagging it; not asserting the record is wrong.**
10. **`ruff` / the fork's linter was not run** — not installed in any available environment.
11. **Nothing was committed or pushed**, in either repo, as instructed.

---

## 8. Recommendation

1. **Default the toggle OFF** — as built. It has never been driven.
2. If it is flown: **`AccordCurvatureLeadGain = 0.75`**. It is the measured optimum on the 12–26 Hz
   design-law band on both routes, keeps 13 ms of lead at 1 Hz, and costs half the 5–18 Hz penalty of
   gain 1.0.
3. **Do not pre-register it as the thing under test.** At −18 % predicted ring amplitude it sits on the
   kit's own readability threshold. Ride it free on a drive spent on something else, exactly as
   `docs/STATE.md` next-item 5 already says.
4. **If it is flown on a V289-class build, watch 15–17 Hz, not 20 Hz.** The reconstruction adds
   +1.5 to +1.7 dB at 10–18 Hz, which is where V289's ring lives.
5. **The 2nd-order variant is measured and rejected** — better at 20 Hz, worse everywhere the design law
   says to look.
