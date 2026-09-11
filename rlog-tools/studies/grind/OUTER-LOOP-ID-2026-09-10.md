# Is the grinding a limit cycle of the OUTER loop (the one that closes through openpilot)?

**Subagent `echoloop`, 2026-09-10. Analysis only — nothing built, nothing flashed, nothing sent on any bus.**

Scripts: `rlog-tools/studies/grind/outerloop_extract.py` (rlog → npz), `outerloop_params.py` (lateral
tuning), `outerloop_id.py` (sections 1–12). Output: `_scratch/outerloop_id.txt`,
`_scratch/outerloop_run.log`. Routes **r39 (V282), r5e (V288 r2), r62 + r63 (V289 r1), r35 (V281 r3)** —
five routes, 4,572 s, 461,224 controlsd frames.

---

## VERDICT

**NO. The outer loop's return ratio at the ring is 0.026–0.165, with an assumption-free upper bound of
0.096–0.189. It is 5–40× short of the unity gain a limit cycle requires, and the distance from the
critical point is 0.97–1.15 where a limit cycle needs ~0. The hypothesis is CLOSED.** [EVIDENCE]

> ⚠ **CORRECTION, made after the first issue of this file.** `pid_log.output` is `-output_torque`
> (`latcontrol_torque.py:725`), so in terms of the LOGGED variable the measured `∂output/∂meas` is
> **positive** — verified directly, +0.147 to +0.326 on all five routes. With `m = P·u + d` and
> `u = +K·m + w` the characteristic equation is `1 − P·K = 0`, so **the critical point is L = +1 and the
> right metric is `|1 − L|`, not `|1 + L|`, and the critical phase is ≈ 0°, not ±180°.** The first issue
> of this file had that backwards. **The verdict is unchanged — `|L|` is 0.026–0.165 either way — but the
> phase reading flips: r63's ∠L = +0.5° is the only route near the critical phase, and its `|L|` is
> 0.0263, 38× short.** `|1 − L|` per route: r39 1.069, r5e 1.088, r62 1.022, r63 0.974, r35 1.154.

Three secondary findings matter more than the null:

1. 🛑 **The brief's premise about the loop is wrong, and so is standing open item #3 in `STATE.md`.**
   `LatControlTorque`'s `measurement` is **not** yaw-derived. It is the **steering angle off CAN**
   (`latcontrol_torque.py:236`). There is no camera, no `modeld`, no IMU and no `livePose` in the
   feedback branch. The model only writes the **setpoint**. [EVIDENCE — source + log]
2. **The command's own 13–26 Hz content is 80–97 % SETPOINT-derived, not echoed measurement.** In the
   high-demand grinding stratum the fed-back-measurement term is 2.4–14.6 % of the command's band
   amplitude; the feedforward + integrator term is 27–85 %. The command is *forcing* the EPS at the ring
   frequency, and that forcing comes from upstream — `modelrate`'s territory. [EVIDENCE]
3. **The colleagues' LPF is NOT ACTIVE on this car** (`carcontroller.py:286` gates it to
   `HONDA_CIVIC_BOSCH` + `EPS_MODIFIED`), and if switched on it would not be closing a stability margin —
   there is none to close. It would work as an **excitation cut**: ×0.030–0.096 on the command's own
   16–20 Hz content at τ = 0.10–0.28 s. That is a real, sizeable lever on finding 2, for a different
   reason than the one the colleagues give. [EVIDENCE for the numbers, BELIEF for "that is why it helps
   on their cars"]

---

## 1. The channel openpilot actually differentiates into `measurement` [EVIDENCE]

Read from the fork, not inferred:

```
latcontrol_torque.py:236  measured_curvature = -VM.calc_curvature(radians(CS.steeringAngleDeg
                                               - params.angleOffsetDeg), CS.vEgo, params.roll)
latcontrol_torque.py:237  measurement = measured_curvature * CS.vEgo**2
latcontrol_torque.py:296  error    = setpoint - measurement
latcontrol_torque.py:297  error_with_lsf = error * (1 + low_speed_factor / current_kp)
carstate.py:187           CS.steeringAngleDeg = cp.vl["STEERING_SENSORS"]["STEER_ANGLE"]   (0.1 deg LSB)
common/pid.py:47-49       p = k_p*error ; d = k_d*error_rate,  k_d = 0 on this car  (log: d == -0)
```

So the outer loop is **EPS motor → rack/column angle → the EPS's own angle frame on CAN → `carState` →
`LatControlTorque` (pure gain at 13–26 Hz, no lead, no derivative) → `0xE4`**. Confirmed on the log:
`corr(Δmeasurement, −(π/180)·v²·Δangle/(SR·L)) = 0.896`, slope 0.83, over 53,358 engaged frames of r62
with |Δv| < 0.02 m/s.

**Publish rates and aliasing** (five routes, all consistent):

| channel | rate | Nyquist | a 16.5 / 20 Hz ring |
|---|---|---|---|
| CAN `0x14A` angle → `carState` → `controlsState` | 99.6 Hz | 49.8 Hz | **not aliased** |
| `livePose` (yaw rate) | 19.86–19.93 Hz | **9.93 Hz** | **folds to 3.5 Hz / 0.0 Hz** |
| `modelV2` / `cameraOdometry` | 20.02 Hz | 10.0 Hz | folds to 3.5 Hz / 0.0 Hz |
| device `gyroscope` | 89.0 Hz | 44.5 Hz | not aliased |

⚠ **The aliasing risk the brief asked about is real but it is in a channel that is NOT in the control
loop.** `livePose` publishes at 19.9 Hz, so a 20 Hz ring folds to DC there and a 16.5 Hz ring to 3.5 Hz.
If anyone ever proposes yaw feedback, or reads `livePose`/`cameraOdometry` to score the ring, that is a
trap. It does not affect the present loop, because the loop does not use them.

**The measurement channel is quantisation-marginal, though**: the wheel-angle ring is 0.0295–0.0469° in
the high-demand grinding stratum — **0.29–0.47 of the 0.1° `STEER_ANGLE` LSB**. openpilot sees the ring
mostly as dither on one count. [EVIDENCE]

---

## 2. The ring IS present in openpilot's measurement [EVIDENCE]

Band-agnostic census: 2 s windows / 0.5 s step, **lateral engaged** = `controlsState.active` AND
`carControl.latActive` AND `0x18F` SCA AND `0xE4` STEER_REQUEST (the kit's own four-flag definition).
`f0` = most prominent 12–26 Hz peak of the driver-torque bar; PRESENT = prominence ≥ 8 AND bar band
amplitude ≥ 40 raw. Ratios present/absent of the band amplitude at f0 ± 2 Hz:

| route | build | bar | wheel rate | 0xE4 cmd | **measurement** | setpoint | error | output |
|---|---|---|---|---|---|---|---|---|
| r39 | V282 | 2.69 | 2.21 | 1.89 | **2.15** | 1.54 | 1.81 | 1.81 |
| r5e | V288 r2 | 2.56 | 1.53 | 0.73 | **2.15** | 1.23 | 1.33 | 0.68 |
| r62 | V289 r1 | 2.70 | 2.74 | 1.27 | **2.12** | 1.29 | 1.66 | 1.18 |
| r63 | V289 r1 | 4.38 | 2.57 | 1.24 | **2.37** | 0.86 | 1.79 | 1.17 |
| r35 | V281 r3 | 3.45 | 2.24 | 1.80 | **2.85** | 1.66 | 1.72 | 1.70 |

The measurement carries the ring on every route, ×2.1–2.9 above quiet. So the loop *can* see it. The
question is only whether the return gain is enough to sustain it.

**Demand gating reproduces the record's two-object picture independently** (§10 of the script). Gating
on median window demand index ≥ 20:

| route | build | pooled f0 | **high-demand f0** |
|---|---|---|---|
| r39 | V282 | 15.58 | **20.10** |
| r5e | V288 r2 | 14.63 | **20.11** |
| r62 | V289 r1 | 13.23 | **16.46** |
| r63 | V289 r1 | 13.27 | **16.55** |
| r35 | V281 r3 | 13.92 | **20.07** |

That is `STATE.md`'s high-demand line — 20.0 Hz on V282/V288/V281r3, 16.2–16.7 Hz on V289 — recovered
from a completely different pipeline. The pooled medians land near the spurious ~14.8 Hz the record
warns about. **Everything decision-bearing below uses the high-demand stratum.**

---

## 3. The outer loop's return ratio [EVIDENCE]

### 3.1 The feedback gain K — exact, not estimated

`output = -(p + i + d + f, clipped)/latAccelFactor` exactly. `-(p+i+d+f)/output` is a hard constant on
every route (**p5 == p95**): **2.1100** on r39/r35, **6.0000** on r5e/r62/r63. So `T' = -1/LAF` exactly,
and the earlier OLS fit that returned R² 0.56 was being corrupted by the ±1.000 rail (which binds on
1.4–2.8 % of engaged frames — the loop is *open* there).

| route | LAF (live, measured) | kp (measured) | lsf_gain p50 | K_P = kp·lsf/LAF | rail duty |
|---|---|---|---|---|---|
| r39 | 2.1100 | 0.8000 | 2.506 | 0.950 | 0.0283 |
| r5e | 6.0000 | 0.9000 | 1.420 | 0.213 | 0.0258 |
| r62 | 6.0000 | 0.9000 | 1.294 | 0.194 | 0.0158 |
| r63 | 6.0000 | 0.9000 | 1.299 | 0.195 | 0.0151 |
| r35 | 2.1100 | 0.6000 | 2.483 | 0.706 | 0.0140 |

⚠ **Two record corrections fall out of this.** (a) `kp` is **0.80** on r39, **0.90** on r5e/r62/r63 and
0.60 only on r35 — the memory `accord-honda-kp-ki-scale-never-acted-kp-is-0600-on-all-60-routes` no
longer holds for the recent routes. (b) the live `latAccelFactor` is **6.00** on r5e/r62/r63 — outside
torqued's own cap band (1.182–2.196) recorded in
`project-operator-starpilot-toggles-decoded-2026-09-03.md`, so `ForceAutoTune` is no longer driving it.
The back-calc memory's "the car needs LAF 5 to 10" appears to have been acted on. `carParams` still
ships 1.68933 / 0.21205; those are **not** what ran.

### 3.2 There is a SECOND feedback path, and it is bigger than P

`latcontrol_torque.py:547`:
```
ff += friction_scale * get_friction(error_with_lsf + 0.22*friction_jerk, deadzone, threshold, params)
```
`get_friction`'s first argument **contains the measurement**, so the feedforward carries a parallel
feedback branch. Its slope is `friction·LAF/0.30` inside the linear region and zero once saturated
(`friction_threshold` = 0.30 everywhere for this car, `friction_scale` = 1.0).

Measured by band-passing to 12–26 Hz and regressing `f` on `[meas, setp, desiredCurvature,
desiredLateralJerk, setp/v²]` over the high-demand grinding windows (R² 0.67–0.95):

| route | ∂f/∂meas | K_P | **K_total** | ratio |
|---|---|---|---|---|
| r39 | +0.034 | 1.374 | 1.433 | ×1.04 |
| r5e | −2.114 | 0.776 | 2.598 | ×3.35 |
| r62 | −2.072 | 1.284 | 4.239 | ×3.30 |
| r63 | −0.579 | 0.550 | 0.903 | ×1.64 |
| r35 | +0.118 | 0.918 | 1.099 | ×1.20 |

Those slopes sit inside the theoretical ceiling `friction·LAF/0.30` for friction ≈ 0.11–0.15, which is
torqued's own filtered range. **All numbers below use K_total, not K_P.**

### 3.3 |L| at the ring

`m = P·u + d`, `u = +K·m + w` (K measured positive in the logged sign convention — see the correction
at the top), so `L = P·K` and a limit cycle needs `L ≈ +1`, i.e. `|1−L| ≈ 0` and `∠L ≈ 0°`.
`P` is estimated in **closed loop** with the **setpoint as instrument**: `P_IV = S(m,r)/S(u,r)`. The
setpoint drives the feedback *and* the feedforward branch through the same `1/(1+L)` factor, so that
factor cancels and the feedforward path need not be separated. `r` is exogenous at 13–26 Hz because
`clip_curvature` (drive_helpers.py:25-52) limits against **`prev_curvature`, never the measurement** —
checked, because if it clipped against the angle the instrument would be void. [EVIDENCE]

**High-demand stratum, grinding windows:**

| route | build | f0 | **\|L_IV\|** | ∠L | **\|1−L\|** | **\|L\| upper bound** |
|---|---|---|---|---|---|---|
| r39 | V282 | 20.10 | 0.0744 | −156° | 1.069 | **0.144** |
| r5e | V288 r2 | 20.11 | 0.0927 | +161° | 1.088 | **0.096** |
| r62 | V289 r1 | 16.46 | 0.0278 | +140° | 1.022 | **0.178** |
| r63 | V289 r1 | 16.55 | 0.0263 | +0.5° | 0.974 | **0.189** |
| r35 | V281 r3 | 20.07 | 0.1646 | −158° | 1.154 | **0.165** |

The **upper bound** is a second method with **no causality assumption at all**:
```
|L| <= K_total * |d(0xE4)/d(output)| * (A_ang / A_cmd) * (pi/180) * v^2 / (SR * L_wb)
     = K_total * 4095.2       * (A_ang / A_cmd) * (pi/180) * v^2 / 46.21
```
`A_ang/A_cmd` is the ratio of the two *measured* ring amplitudes, which is an upper bound on the causal
gain from command to wheel because the wheel's ring is demonstrably not all caused by the command.
Dropping the tyre-stiffness and roll terms only makes the last factor larger, so the bound holds.
⚠ **The one way this bound could fail:** if the command-driven component of the wheel's ring were
partly cancelled by a disturbance-driven component locked in antiphase, the measured `A_ang` could sit
below `|∂ang/∂cmd|·A_cmd`. That needs a phase-locked antiphase disturbance at the ring on all five
routes; I have no evidence for it and it is not what a plant mode does, but it is the assumption the
bound rests on and it is stated rather than buried.
`d(0xE4)/d(limited torque) = −4095.2 with R² 1.00000` on every route — measured, matching
`carcontroller.py:306+321` and giving the ±123 counts/frame rate limit the record already knows.

**Even at the most adverse plausible friction** (0.318, torqued's cap, with LAF 6.00 → ∂f/∂meas ≤ 6.36,
K_total ≈ 8× K_P) the bound stays at 0.29–0.38. There is no parameter setting inside the fork's own
ranges that brings this loop to unity at the ring.

### 3.4 The naive estimate would have lied in the flattering direction

`P_direct = S(m,u)/S(u,u)` is biased **towards −1/K** in closed loop — it manufactures `|L| = 1`. On r35
it reads `|L| = 0.265` against the IV's 0.017, a 16× inflation with ∠L = +0.1° (i.e. pointing at the
wrong half-plane entirely). A pass that had used it would have produced a confident false positive.
[EVIDENCE — both printed side by side in §4 of the log]

### 3.5 Estimator control

The same setpoint-instrumented estimator was run on a transfer whose truth is known exactly — `output`
→ `0xE4`, static gain −4095.2, ~one frame of transport. It returns −421 to −2159 counts (−48 % to
−90 % of truth) with group delay +9.5 to +15.1 ms. **So the IV under-reads magnitude by 2–10× at these
frequencies.** That direction is *conservative* for the verdict (it makes `|L|` look smaller), which is
exactly why the independent upper bound in 3.3 is the number to lean on — and the bound is computed from
amplitudes and the exact wire gain, not from the IV.

---

## 4. Echo vs forcing — the phase-free decomposition [EVIDENCE]

`output = u_meas + u_setp + u_rest` is an **algebraic identity**, not an estimate:
```
u_meas = -T'*kp*lsf*meas     the FED-BACK measurement (the ECHO)
u_setp = +T'*kp*lsf*setp     the setpoint through the same P gain
u_rest =  T'*(i + d + f)     integrator + feedforward
```
Verified on rail-free windows: **residual rms 3.9e-9 vs output rms 0.12–0.16** — exact to float
precision. (On railed windows the identity legitimately breaks; those windows are excluded and counted.)

**High-demand stratum, band amplitude at f0 ± 2 Hz:**

| route | f0 | output | u_meas (ECHO) | u_setp | u_rest (FF+I) |
|---|---|---|---|---|---|
| r39 | 20.10 | 1.07e-2 | 1.27e-3 (**11.8 %**) | 8.61e-3 (80.2 %) | 2.91e-3 (27.1 %) |
| r5e | 20.11 | 1.87e-2 | 4.53e-4 (**2.4 %**) | 3.43e-3 (18.4 %) | 1.58e-2 (84.6 %) |
| r62 | 16.46 | 1.23e-2 | 3.69e-4 (**3.0 %**) | 2.42e-3 (19.6 %) | 1.01e-2 (81.7 %) |
| r63 | 16.55 | 6.73e-3 | 6.80e-4 (**10.1 %**) | 1.23e-3 (18.2 %) | 5.43e-3 (80.6 %) |
| r35 | 20.07 | 1.14e-2 | 1.66e-3 (**14.6 %**) | 8.41e-3 (73.8 %) | 4.09e-3 (35.9 %) |

⚠ Note `u_rest` contains the friction term, which §3.2 showed is partly measurement-driven — so the
"echo" share is a **lower** bound and the true split is somewhere between these numbers and (echo +
the friction part of u_rest). Even so, `u_setp + u_rest` traces back to the **setpoint** on every route,
and the command carries **17–43 raw counts** of ring at the wire. **The command is forcing the EPS at
the ring frequency far more than it is echoing it.**

---

## 5. The transport delay, in legs [EVIDENCE]

| route | leg1 `0x14A` → `meas` | leg2 `output` → `0xE4` | **round trip (wheel → command)** | control `meas`→`error` |
|---|---|---|---|---|
| r39 | +10.32 ms (coh 0.39) | +12.48 ms (0.47) | **+22.80 ms** | −5.3 ms, −150° |
| r5e | +10.42 ms (0.40) | +14.46 ms (0.36) | **+24.87 ms** | +0.9 ms, −176° |
| r62 | +10.27 ms (0.44) | +15.95 ms (0.25) | **+26.22 ms** | +0.7 ms, −179° |
| r63 | +9.40 ms (0.51) | +11.82 ms (0.26) | **+21.22 ms** | +1.0 ms, −179° |
| r35 | +10.34 ms (0.45) | +12.55 ms (0.48) | **+22.89 ms** | −1.3 ms, +180° |

The control (`meas` → `error`, an exact zero-delay 180° path by construction) returns ~0 ms and ~180° on
four of five routes, so the estimator is sound. **Leg 1 is +9.4 to +10.4 ms on all five routes — one CAN
frame.** The openpilot round trip is **21–26 ms, tight and consistent.**

**This settles the echo-vs-forcing discriminator the brief asked for.** An echo through openpilot costs
~23 ms, not the "camera + model + controlsd" tens-to-hundreds of ms the brief expected — because the
camera and the model are **not in the feedback branch**. So a delay measurement alone cannot separate
"echo" from "forced at 20 Hz by a 20 Hz upstream clock": 23 ms at 20 Hz is 166° of phase, and the
forcing path (modelV2 → setpoint) has its own delay. **The share decomposition in §4, not the delay, is
what separates them**, and it says forcing.

⚠ Leg 3 (`0xE4` → wheel angle) has coherence 0.03–0.21 and is not usable; its group delay swings
−17 to +82 ms across routes. That is itself consistent with the command not driving the wheel's ring.
The inter-stream offset caveat (the kit's "3.9 ms / +28°") applies to legs 1–3 individually but cancels
in the closed cycle; it does **not** apply to the `meas`/`output`/`setp` triple, which all come off
**one message on one tick** — which is why `|L|` was estimated from those three and not from the wire.

---

## 6. The open-loop natural experiment — NO POWER on these routes [EVIDENCE, null]

| route | speed bin | engaged n / present rate | lateral-OFF n / present rate | 95 % upper bound off |
|---|---|---|---|---|
| r39 | 0–4 m/s | 231 / 0.273 | 83 / **0.000** | 0.036 |
| r5e | 0–4 | 209 / 0.306 | 370 / **0.000** | 0.008 |
| r62 | 0–4 | 149 / 0.483 | 521 / **0.000** | 0.006 |
| r62 | 4–8 | 199 / 0.472 | 30 / **0.000** | 0.100 |
| r63 | 0–4 | 113 / 0.558 | 202 / 0.010 | — |
| r35 | 4–8 | 319 / 0.310 | 28 / 0.071 | — |
| **all five** | **≥ 8 m/s** | 1,800+ windows | **0–1 windows** | **no exposure** |

**Above 8 m/s there is essentially no lateral-disengaged exposure on any of these five routes**, so the
test the brief asked for cannot be run there. At creep the null is clean and on r39 it is better than
matched: the lateral-OFF 0–4 m/s stratum has driver-torque rms **362 vs 259** engaged and wheel-rate rms
**256 vs 122** engaged — *more* load and *more* motion — and still **0 of 83 windows** carry the line
against 63 of 231 (27 %) engaged.

🛑 **But this cannot separate inner from outer, and must not be quoted as if it could.** With
STEER_REQUEST = 0 the EPS receives no LKAS command at all, so disengaging opens the **EPS's own rate
loop** as well as openpilot's. The result says "the ring needs LKAS torque", which the kit already knew.
The decisive evidence is §3, not this.

---

## 7. What the colleagues' LPF would do [EVIDENCE for the numbers]

`get_civic_bosch_modified_torque_lpf_tau` (carcontroller.py:27–66) returns τ ∈ [0.10, 0.28] s, applied at
:294–298 as a one-pole discrete LPF at 100 Hz. **`carcontroller.py:286` gates the whole block on
`carFingerprint == CAR.HONDA_CIVIC_BOSCH and CP.flags & HondaFlags.EPS_MODIFIED` — it is NOT active on
the Accord.** Nothing filters the operator's command today.

| τ (s) | fc (Hz) | \|H\| @13 Hz | \|H\| @16.5 Hz | \|H\| @20 Hz | ∠H @16.5 Hz | \|H\| @1 Hz | ∠H @1 Hz |
|---|---|---|---|---|---|---|---|
| 0.05 | 3.18 | 0.224 | 0.181 | 0.154 | −51° | 0.946 | −17° |
| 0.10 | 1.59 | 0.119 | 0.096 | 0.081 | −56° | 0.835 | −32° |
| 0.16 | 0.99 | 0.076 | 0.061 | 0.052 | −57° | 0.695 | −44° |
| 0.22 | 0.72 | 0.056 | 0.045 | 0.038 | −58° | 0.578 | −53° |
| 0.28 | 0.57 | 0.044 | 0.035 | 0.030 | −59° | 0.488 | −59° |

**The stability answer: there is no τ range "that would stabilise it", because nothing is unstable.**
`|L|` is already 0.026–0.165; the LPF would take it to 0.002–0.016, which is a change from "far from −1"
to "further from −1". As a stabiliser it is a solution to a problem this loop does not have.

**The excitation answer is the interesting one.** §4 says the command carries 17–43 raw counts of ring
at the wire and that 80–97 % of it is setpoint-derived. A τ = 0.16 s pole cuts that by **×0.061 at
16.5 Hz and ×0.052 at 20 Hz** — it would very nearly delete the command's own ring content. **Steady-state
tracking cost:** ×0.695 magnitude and **−44.2° of phase at 1 Hz**, ×0.955 and −16.7° at 0.3 Hz. On a car
already running LAF 6.00 that phase loss inside the lane-keeping bandwidth is not free and would need
its own drive to score — but it is a *different* and much smaller risk than the loop-shaping class
`STATE.md` is currently out of moves in, because it sits **outside** the EPS entirely and is a one-line
fork change with no flash. [numbers EVIDENCE; "this is why it helps their Civics" is BELIEF — I did not
measure their cars]

---

## 8. The null, stated plainly, and what I could not determine

**Stated null:** the outer loop's gain at the ring frequency is 0.026–0.165 (bound ≤ 0.189, ≤ 0.38 under
the most adverse plausible friction) and `|1 − L|` is 0.97–1.15 where a limit cycle needs ~0. Only one
route (r63) sits near the critical phase at all, and its `|L|` is 0.0263 — 38× short of unity.
**The sustaining mechanism is not the loop that closes through openpilot.
Standing open item #3 in `STATE.md` should be closed as written** — its premise ("openpilot's unfiltered
100 Hz *angle* measurement is what makes the command's own 20 Hz line an echo") is half right about the
channel and wrong about the direction: the angle measurement is indeed the feedback, and it is indeed
unfiltered, but the command's 20 Hz line is **not** an echo of it.

**What I could not determine:**
- **Where the setpoint's 13–26 Hz content comes from.** §4 hands the question to `modelrate` with a
  number attached: 80–97 % of the command's ring band is setpoint-derived, and the high-demand line sits
  at 20.1 Hz on V282/V288/V281r3 — within 0.1 Hz of `modeld`'s 20.02 Hz publish rate — but at
  16.46/16.55 Hz on V289, which is **not** a multiple or alias of 20 Hz. **A pure upstream-clock forcing
  explanation must account for V289's 16.5 Hz.** I did not test it.
- **The exact live `friction`.** `carParams` ships 0.21205 but the live `latAccelFactor` is 6.00, so the
  live params are neither `carParams`' nor torqued's. The rlogs do not carry the toggle state — per
  `project-operator-starpilot-toggles-decoded-2026-09-03.md`, that needs the backup file. I bounded the
  answer instead of guessing it; the verdict is insensitive across the whole plausible range.
- **The open-loop test above 8 m/s.** No exposure on these five routes. If the operator can produce ~60 s
  of manual driving at 10–20 m/s on the same road as an engaged stretch, the test becomes runnable — but
  it still would not separate inner from outer, so I would not spend a drive on it.
- **Leg 3 (command → wheel)**, the EPS plant itself, at coherence 0.03–0.21. Not estimable from these
  routes by this method.

---

# ADDENDUM, same day — the open-loop test at real power, and the delay reconciliation

Added after the first issue, on the orchestrator's re-scope. Script
`rlog-tools/studies/grind/outerloop_openloop.py`, log `_scratch/outerloop_openloop.txt`. `outerloop_id.py`
and its numbers are untouched.

## A. Does the ring appear with lateral disengaged? — 17 routes, 6 builds + stock [EVIDENCE]

Section 6 above had no power above 8 m/s. Every route already in
`analysis-2020accord/_scratch/cache/v280` carries the fields the test needs, so it runs over **17 routes
with no new rlog reads** (`r2e`'s cache lacks the `0x1AB` fields the loader wants and was skipped).
**20,761 engaged windows and 5,905 lateral-disengaged windows.** Two gates side by side, because the
kit's engaged/manual confound record says a level gate is confounded by how much the wheel is moving:
LEVEL = prominence ≥ 8 **and** bar band amplitude ≥ 40 raw; SHAPE = prominence ≥ 8 only.

| speed m/s | n engaged | LEVEL rate eng | SHAPE rate eng | f0 eng | n OFF | LEVEL rate OFF | SHAPE rate OFF | f0 OFF |
|---|---|---|---|---|---|---|---|---|
| 0–4 | 2115 | 0.362 | 0.603 | 19.8 | 4996 | **0.0076** | 0.451 | 13.0 |
| 4–8 | 3193 | 0.499 | 0.641 | 19.9 | 276 | **0.0362** | 0.272 | 12.1 |
| 8–13 | 4518 | 0.434 | 0.606 | 15.8 | 51 | 0.196 | 0.255 | 14.4 |
| 13–18 | 4614 | 0.387 | 0.640 | 13.8 | 30 | 0.233 | 0.500 | 12.8 |
| 18–25 | 3233 | 0.446 | 0.700 | 12.1 | 39 | 0.051 | 0.103 | 12.0 |
| 25–40 | 3088 | 0.890 | 0.983 | 13.3 | **0** | — | — | — |

**Load-matched** (disengaged windows restricted, inside each speed bin, to the engaged interquartile
range of *both* driver-torque rms and wheel-rate rms):

| speed | n eng | LEVEL eng | barRMS / rateRMS eng | n OFF matched | LEVEL OFF | barRMS / rateRMS OFF |
|---|---|---|---|---|---|---|
| 0–4 | 2115 | 0.3617 | 267 / 100 | 371 | **0.0108** | 376 / 205 |
| 4–8 | 3193 | 0.4986 | 252 / 68 | 35 | **0.0286** | 417 / 136 |
| ≥ 8 | — | — | — | 0–1 | — | no exposure |

**Per route the disengaged LEVEL rate is 0.000–0.0505 on every one of 17 routes — including stock
(r97, 0.0130) — against an engaged 0.33–0.67.** No single route carries the pooled result.

**High-demand engaged stratum (idx ≥ 20) against disengaged at the same speed:** ×72 at 0–4 m/s,
×20 at 4–8 m/s.

**Reading it:**
- ⭐ **The high-demand ~20 Hz object is engagement-gated**, and at creep the disengaged stratum has
  *more* driver torque (376 vs 267 rms) and *more* wheel rate (205 vs 100) than the engaged one and
  still shows it 33× less often. This is not a load or an exposure artefact.
- **But the SHAPE gate does NOT go to zero disengaged** (0.25–0.50), at a median f0 of **12–14 Hz**
  against the engaged 19.8–20.0 Hz. That is the low-demand road/plant line, and it is present with the
  loop open. **The two-object picture holds on this cut too: the 12–14 Hz line is not engagement-gated;
  the 20 Hz one is.**
- 🛑 **This still cannot separate inner from outer.** With STEER_REQUEST = 0 the EPS gets no LKAS
  command at all, so its own rate loop is open too. It establishes that the 20 Hz object requires LKAS
  torque; §3 is what establishes that the loop carrying it is not openpilot's.
- **Power:** decisive at 0–8 m/s (5,272 disengaged windows). At 8–25 m/s there are 120 disengaged
  windows in total across 17 routes and the estimates there (0.196, 0.233, 0.051) are not separable
  from the engaged rates. **Above 25 m/s there is still zero disengaged exposure in the entire cache.**

## B. Reconciling the two `0x14A` → `0xE4` delay numbers [EVIDENCE]

| route | stratum | f0 | phase @ f0 | coh @ f0 | group-delay slope 13–25 Hz | mean coh |
|---|---|---|---|---|---|---|
| r39 | pooled | 15.58 | −102.5° | 0.189 | −38.8 ms | 0.187 |
| r35 | pooled | 13.92 | −106.7° | 0.426 | −23.4 ms | 0.210 |
| **r39** | **hi-demand** | **20.10** | **−21.8°** | **0.577** | −40.6 ms | 0.174 |
| **r5e** | **hi-demand** | **20.11** | **+28.2°** | **0.403** | −37.3 ms | 0.079 |
| **r35** | **hi-demand** | **20.07** | **−16.6°** | **0.555** | −38.4 ms | 0.167 |
| r62 | hi-demand | 16.46 | −12.7° | 0.076 | −102.0 ms | 0.053 |
| r63 | hi-demand | 16.55 | −128.5° | 0.031 | +26.3 ms | 0.037 |

**`slewburst`'s ~0° is REPRODUCED** — on the high-demand stratum, at coherence 0.40–0.58, on the three
routes where the 20 Hz object is strongest.

**And it is not the openpilot echo.** I checked the sign chain empirically rather than by reasoning,
because I had already made one sign slip: over 0.3–2 Hz on engaged frames, `∂meas/∂ang` = −0.003 to
−0.018, `∂output/∂meas` = +0.147 to +0.326, `∂cmd/∂output` = −2782 to −3797 ⇒ **`∂cmd/∂ang` is POSITIVE
on the wire** (predicted +2.7 to +8.3 counts/deg, measured +0.5 to +3.1). So the wire-angle → wire-command
path is **non-inverting at DC**, and a 21–26 ms echo would put the command at **−152° to +172°** relative
to the angle at 20.1 Hz — not at ~0°.

⚠ I specifically tested and **rejected** the obvious rescue ("slewburst forgot the feedback's 180°
inversion, so −166° + 180° = +14° ≈ 0"). There is no such inversion on the wire; the measured DC sign
is positive. **slewburst's inference stands and my first-pass objection to it was wrong.**

The group-delay slope on this pair (−37 to −41 ms where coherence is usable) disagrees with both, but
its mean coherence is 0.05–0.21 and it is not usable — the same reason §5's leg 3 was discarded. **The
reliable delay numbers remain the decomposed ones** (leg 1 at coherence 0.39–0.51, leg 2 at 0.25–0.48),
which give the 21–26 ms round trip.

**Net:** three independent routes to the same place — `|L| ≤ 0.19` (§3), the command's ring being
2.4–14.6 % echo (§4), and now a wire phase at ~0° that an echo cannot produce (B). **Two signals near
in phase with no round trip is what a COMMON DRIVER looks like**, which is `modelrate`'s hypothesis,
reached here from the loop-identification side.
