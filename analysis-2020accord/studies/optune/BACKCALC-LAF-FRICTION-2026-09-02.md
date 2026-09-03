# Back-calculated latAccelFactor and friction from route data — 2026-09-02 (subagent `opfit`)

Script: `backcalc_extract.py` (rlog → npz) and `backcalc_laf_friction.py` (fits) beside this file; raw output in
`_scratch/backcalc_out.txt`, machine-readable results in `_scratch/backcalc_results.json`.
Controller math inverted from the code at `openpilots/StarPilot` @ 3d4c625de (`torqued.py`, `latcontrol_torque.py`,
`opendbc/car/lateral.py::get_friction`, `controlsd.py::get_torque_control_params`). opmath's write-up
(`STARPILOT-DOM-TORQUE-MATH-2026-09-02.md`) had not appeared when this was written; the expressions below are
read from the code directly and should be reconciled against it when it lands.

## 0. Verdict in three lines

1. **The controller on r31/r32/r33 (V278 rev 3, V280 rev 2) ran the params.toml defaults, LAF 1.689 / friction 0.212 —
   torqued applied NOTHING** (EVIDENCE: `liveTorqueParameters.liveValid = 0` on every tick, filtered = defaults,
   and `-(p+i+d+f)/output` = 1.689 at p5 and p50 of active frames). torqued is stuck invalid on the modded EPS because
   the command never leaves ±0.1: the ±0.1–0.5 buckets never fill (bucket census below), `totalBucketPoints` is frozen at
   6653 on all three routes, and its raw LAF 4.7–5.1 is a TLS through central buckets from THIS build and outer buckets from
   an OLD cache. It is not a measurement of any car.
2. **The car's friction (torque needed before lateral accel responds) on V280 rev 2 is ≈ 0.01–0.03 torque units; the
   controller uses 0.212.** The friction "kick" ±0.212 is 1.8× the engaged |torque| p90 (0.117) on this build. Lowering
   SteerFriction is supported by the data, and 0.08 is still 3–4× above the measured deadband; the linear-band gain
   from friction is friction/0.30 per m/s² of error and is LAF-independent, so friction is the bigger lever (64 % of the
   small-signal gain at 25 m/s).
3. **The car's low-frequency LAF on V280 rev 2 is 8–11 m/s² per unit torque (IV 8.3–9.4, FIR DC 9.6–10.8, |P(0.1 Hz)|
   10.7–11.2), i.e. 5–6.5× the live 1.689** — and the plant is integrator-like (|P| falls ≈1/f from 0.1 to 1 Hz), so no
   single LAF makes the feedforward exact; the toggle max 2.53 is the reachable step, the real number needs
   `torque_data/params.toml:14`.

## 1. What was extracted (task 1)

Per route, every segment, onto a 100 Hz grid: `carOutput.actuatorsOutput.torque` and `torqueOutputCan` (= −torque×4096,
1:1 with the 0xE4 STEER_TORQUE counts, checked), 0xE4 STEER_TORQUE/STEER_REQUEST (src ≥ 128), 0x18F driver torque / rate /
SCA, `carState` vEgo / steeringTorque / steeringAngleDeg / steeringRateDeg / steeringPressed, `carControl.latActive`,
`controlsState.torqueState` (p i d f output error actualLateralAccel desiredLateralAccel desiredLateralJerk) and
desiredCurvature, `livePose` angular velocity + orientation, `liveCalibration.rpyCalib`, `liveParameters` roll /
angleOffset, `liveDelay.lateralDelay`, all `liveTorqueParameters` scalars, gyroscope, and `carParams.lateralTuning.torque`.
No `starpilotLateralState` events exist in these logs (the message is published only in a debug path), so the friction
threshold / scale were taken from the code (threshold = 0.30 at every speed for the Accord: `max(GM interp ≤ 0.27, 0.30)`).
`carParams` on all five routes: `lateralTuning.torque` LAF 1.6893, friction 0.2120, offset 0, deadzone 0°, steerRatio 16.33,
steerActuatorDelay 0.10 (liveDelay.lateralDelay = 0.200 engaged on every route), torqueBP/V [0, 4096].

Three "actual lateral accel" instruments: (a) torqued's own — `vEgo × yaw_calibrated − g·sin(roll_device)`, yaw rotated by
`rot_from_euler(rpyCalib).T` exactly as `PoseCalibrator` does; (b) the uncalibrated device yaw × vEgo; (c) the controller's
steering-angle vehicle-model measurement `torqueState.actualLateralAccel` (100 Hz). (a) and (b) agree to 0.1 % on every
route (the calibration is a ~1° pitch); (c) runs 15–35 % higher in slope and has a +0.1 instead of −0.3 intercept because
the pose instrument carries the road-crown/roll term and the vehicle model does not.

## 2. torqued replication (task 2)

Point qualification copied from `handle_log`: latActive over [t−2 s, t+lag], no steeringPressed in that window, vEgo > 15,
|steer| > 0.02, |lat| ≤ 1, steer = −torque sampled `lag` earlier, at each livePose tick (20 Hz); buckets FIFO 1500;
fit = TLS by SVD of [x, 1, y]; friction = 1.5 × std of the perpendicular spread.

| route | build | qualified pts (this route) | bucket census (−0.5…+0.5, 8 bins) | calculable on own points | my TLS (LAF / offset / friction) | logged raw at route end | residual |
|---|---|---|---|---|---|---|---|
| r97 | stock | 6936 | [91, 259, 656, 1174, 1500, 1500, 643, 270] | yes | **1.739 / −0.398 / 0.132** (2000-pt subsample ×20: 1.746 ± 0.028, 0.132 ± 0.002) | 2.419 / −0.370 / 0.181 | LAF −0.68 (−28 %), friction −0.05 (−27 %) |
| r22 | V112 | 2950 | [0, 1, 133, 1500, 938, 188, 9, 0] | no (outer buckets empty) | — | 5.347 / −0.200 / 0.123 | not comparable |
| r31 | V278r3 | 567 | [0, 0, 3, 421, 134, 9, 0, 0] | no | — | 4.733 / −0.238 / 0.138 | not comparable |
| r32 | V280r2 | 3059 | [0, 0, 1, 1500, 1229, 10, 0, 0] | no | — | 5.056 / −0.212 / 0.140 | not comparable |
| r33 | V280r2 | 2338 | [0, 0, 9, 1475, 853, 1, 0, 0] | no | — | 4.837 / −0.211 / 0.140 | not comparable |
| chain r31→r32→r33 (buckets carried like the device cache) | | | [0, 0, 13, 1500, 1500, 20, 0, 0] | no | — | | |

**Why the stock residual is −28 % and why that is not a pipeline error (EVIDENCE):** r97 starts with 10 961 cached bucket
points from earlier drives and torqued's logged raw LAF *falls monotonically from 3.05 to 2.42 across the route* as the
FIFO buckets replace cached points with r97's own; my per-route buckets hold only r97's 6093 points. The direction and
the trend are exactly what the cache explains. My stock TLS (1.74) sits on the Honda-fleet params.toml value (1.689);
the OLS/IV/FIR estimates of the stock car below (1.1–1.4) bracket it from below. The friction residual has the same cause.

**Pipeline consistency checks that passed:** `torqueOutputCan = −4096 × torque` on every route; `p/error = 0.600` at p50
(SteerKP flat 0.6, as recorded); on r22/r97 where torqued WAS valid, `-(p+i+d+f)/output` reproduces
`latAccelFactorFiltered` (2.26 vs 2.18–2.34; 2.28 vs 2.25–2.31); the f-regression recovers friction×LAF = 0.333 / 0.399 /
0.348 / 0.339 / 0.353 → friction 0.147 / 0.175 / 0.206 / 0.201 / 0.209 against the logged filtered 0.148 / 0.177 / 0.212 /
0.212 / 0.212 (within 3 %).

**On the modded builds torqued can never become valid** (EVIDENCE from the bucket census): the ±0.1–0.5 buckets need
100/300/500 points and receive 0–20 per route because the engaged |torque| p90 is 0.117 (r32) / 0.611 (r33, one hard
manoeuvre) / 0.356 (r22); `totalBucketPoints` stays at exactly 6653 through r31, r32 and r33 and `calPerc` at 84.

## 3. What the CAR actually is (task 2, per build)

steer = −torque delayed by liveDelay (0.2 s); torqued's qualification but no |lat| ≤ 1 cut (|lat| ≤ 3), v > 15 unless
stated. "coulomb" is c in the inverse regression `torque = lat/LAF + b + c·sign(steeringRateDeg)` (the torque needed
before lateral accel responds, in torque units); "hyst" is the intercept split of `lat = s·torque + b` by rate sign, in
torque units. "IV" = instrumental-variable slope with `torqueState.desiredLateralAccel` as the instrument (immune to the
closed-loop bias that pulls OLS down when the road-crown disturbance feeds back into the command). FIR = 30-tap, 20 Hz,
0–1.5 s, sum of taps = DC gain.

| build (routes) | n | OLS slope @0.2 s (r) | OLS @best lag | IV slope (lag 0.2/0.5/0.8) | FIR DC (cum. at 0.2/0.5/1.0/1.5 s) | 1st-order K, τ, Td | coulomb (tq) | hyst (tq) | intercept (m/s²) |
|---|---|---|---|---|---|---|---|---|---|
| stock (r97) | 6996 | 1.125 (0.78) | 1.26 @0.6 s | 1.13 / 1.19 / 1.18 | **1.41** (−0.26 / 0.66 / 0.96 / 1.41) | 1.47, 0.70 s, 0.15 s | −0.052 | 0.116 | −0.36 |
| V112 (r22) | 2990 | 3.20 (0.65) | 3.82 @0.6 s | 6.03 / 6.11 / 5.91 | **5.04** (0.27 / 1.62 / 3.24 / 5.04) | 5.79, 1.0 s, 0.20 s | −0.025 | 0.054 | −0.34 |
| V278r3 (r31) | 567 | 1.90 (0.45) | 2.91 @0.55 s | 6.92 / 6.66 / 4.12 | **7.48** (0.87 / 2.64 / 5.04 / 7.48) | 6.07, 0.5 s, 0.25 s | −0.011 | 0.028 | −0.47 |
| V280r2 (r32) | 3063 | 4.37 (0.62) | 4.94 @0.5 s | 8.31 / 8.32 / 7.89 | **10.81** (0.92 / 4.00 / 7.48 / 10.81) | 12.4, 1.0 s, 0.10 s | −0.006 | 0.013 | −0.26 |
| V280r2 (r33) | 2412 | 3.78 (0.56) | 4.62 @0.45 s | 9.40 / 8.86 / 7.59 | **9.62** (0.51 / 3.65 / 6.73 / 9.62) | 11.5, 1.0 s, 0.10 s | −0.008 | 0.030 | −0.32 |
| V280r2 pooled | 5475 | 4.18 (0.60) | | | | | −0.007 | 0.019 | −0.29 |

Spectral H1 estimate |P(f)| (lat accel per unit torque; 100 Hz vehicle-model instrument, Welch 10.24 s on engaged
v > 15 runs ≥ 20 s; the 20 Hz pose instrument agrees below 0.7 Hz and loses coherence above 1 Hz):

| build | 0.1 Hz | 0.2 | 0.3 | 0.5 | 0.7 | 1.0 | 1.5 | 2 | 3 | 5 | 7.5 Hz | coh @7.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| stock r97 | 1.64 | 1.36 | 1.10 | 0.71 | 0.70 | 0.62 | 0.22 | 0.64 | 0.57 | 0.74 | 0.90 | 0.85 |
| V112 r22 | 5.96 | 4.59 | 2.68 | 1.77 | 1.43 | 1.17 | 0.42 | 0.47 | 0.65 | 0.67 | 0.87 | 0.85 |
| V278r3 r31 | 6.17 | 4.91 | 3.82 | 1.79 | 1.54 | 1.49 | 0.69 | 0.32 | 0.44 | 0.47 | 0.60 | 0.90 |
| V280r2 r32 | 11.18 | 7.66 | 5.38 | 4.02 | 3.12 | 2.50 | 1.70 | 0.59 | 0.80 | 0.72 | 0.84 | 0.94 |
| V280r2 r33 | 10.68 | 7.49 | 4.69 | 3.03 | 2.52 | 2.27 | 1.79 | 0.43 | 0.57 | 0.59 | 0.79 | 0.92 |

Readings:
- **Stock reads ≈ the Honda-fleet LAF** (1.4–1.6 at 0.1–0.2 Hz vs params.toml 1.689) — the pipeline's sanity anchor
  (EVIDENCE).
- **Low-frequency authority scales with the map:** V112 ≈ 3.6× stock, V278r3 ≈ 4× (thin data), V280r2 ≈ 6.5–7× at
  0.1 Hz — consistent with the ×6 line map (EVIDENCE for the delivered authority; the ×6 is the build's own number).
- **The modded plant is integrator-like:** |P| falls ≈ 1/f between 0.1 and 1 Hz on every modded build (11 → 2.5 on V280r2),
  and the FIR taps keep accumulating through 1.5 s, whereas stock saturates (0.66 → 0.96 → 1.41). This is the rate-servo
  picture already in memory (`accord-lkas-commands-rate-not-torque`): the 0xE4 count is a rate reference, so a torque-
  proportional feedforward is structurally the wrong shape on these builds, and the P/I terms must fight the ff on every
  manoeuvre. BELIEF on the mechanism; EVIDENCE on the shape.
- **Above ~2 Hz the H1 estimate is not the plant** (BELIEF, strong): every build reads 0.8–0.9 at 7–8 Hz with coherence
  0.85–0.97 — that is 1/Gc (the controller's inverse, 1/1.10 = 0.91), the textbook closed-loop identification artefact
  when the loop's own noise dominates. Do not read the 7.5 Hz column as plant gain; the ring band needs a driven or
  open-loop measurement (the loopgain study's G(f) from the wire is the right instrument for that).
- **Nonlinearity by |torque|:** on V280r2 99 % of qualified points are |torque| < 0.1, so the 0.1–0.3 and > 0.3 rows are
  empty (n 63 / 0); V112: slope 3.74 (|tq| < 0.1) vs 3.33 (0.1–0.3), n 3545 / 778; stock: 1.04 / 1.21 / 0.94 across the
  three bands with hysteresis widening 0.106 → 0.113 → 0.236 tq. No evidence of a slope break on the modded builds
  within the range they are driven in.
- **Speed dependence (v > 10):** V280r2 pooled OLS 4.11 (10–20 m/s, n 4130) vs 3.58 (20–30, n 2607) vs 3.66 (30–45,
  n 69); V112 3.11 vs 4.65; stock 0.88 / 1.18 / 1.38. Within the noise of these fits (r ≈ 0.55–0.8); the FIR/IV per speed
  band were not split (too few 20 s runs). BELIEF: no speed dependence worth a schedule.
- **Friction / deadband:** the coulomb term is NEGATIVE (i.e. zero within noise) on every modded build (−0.006 to −0.025 tq;
  adding the sign term reduces the inverse-fit residual by only 1–2 %); the hysteresis half-width is 0.013–0.030 tq on
  V280r2, 0.054 on V112, 0.116 on stock. In torque units the car's deadband on V280r2 is **≈ 0.02 ± 0.01** (EVIDENCE, two
  estimators, two routes). torqued's own friction statistic on the same points (1.5 × perpendicular spread) is 0.045 on
  V280r2 — that number is instrument noise projected through the slope, not friction.

## 4. Ideal parameters for V280 rev 2 and the gain arithmetic (task 3)

Small-signal torque per m/s² of lateral-accel error, in the friction term's linear band (|err_lsf + 0.22·jerk| < 0.30):

    Gc(v) = (kp + lsf(v)) / LAF  +  friction / 0.30        kp = 0.6 (SteerKP), lsf(25 m/s) = 0.068, lsf(15) = 0.25
    L0(v) = Gc(v) × LAF_true                               (loop DC gain through the car's low-frequency LAF)

The friction term's slope is LAF-independent (`get_friction` multiplies by LAF and `torque_from_lateral_accel` divides
it back out), so LAF only scales the P/I share. Above the 0.30 band the friction term is a relay of amplitude
`friction` (in torque units): 0.212 → 868 counts on the wire, i.e. the friction kick alone is 1.8× the engaged
|torque| p90 on r32 and 35 % of the 2481-count rail.

| parameter set (V280 rev 2, v = 25 m/s) | LAF | friction | Gc (tq per m/s²) | friction share | Gc ratio vs live | L0 with LAF_true = 9.6 |
|---|---|---|---|---|---|---|
| **live on r32/r33** (params.toml defaults, torqued invalid) | 1.689 | 0.212 | 1.102 | 64 % | 1.00 | 10.6 |
| the earlier suggestion | 1.689 | 0.08 | 0.662 | 40 % | 0.60 | 6.4 |
| suggestion + toggle-max LAF | 2.53 | 0.08 | 0.531 | 50 % | 0.48 | 5.1 |
| **friction at the measured deadband** | 1.689 | 0.025 | 0.479 | 17 % | 0.43 | 4.6 |
| **deadband friction + toggle-max LAF** | 2.53 | 0.025 | 0.347 | 24 % | 0.32 | 3.3 |
| ideal ff for lane-change band (0.3–0.5 Hz) | 5.0 | 0.025 | 0.217 | 38 % | 0.20 | 2.1 |
| ideal ff for steady curves (0.1 Hz / IV / FIR) | 9.6 | 0.025 | 0.153 | 54 % | 0.14 | 1.5 |

At 15 m/s the live Gc is 1.287 (friction 55 %); the same rows scale accordingly (`_scratch/backcalc_out.txt`, GAIN table).

**Ideal values and their distance from live (V280 rev 2):**
- **friction: ≈ 0.02–0.03** (measured deadband 0.013–0.030 tq; coulomb 0). Live 0.212 is **7–10× too high**, direction DOWN.
  0.08 is a 2.6× cut in the friction gain but is still 3–4× the car's deadband; the data support going to ~0.03.
  SteerFriction's toggle range is 0–1 so 0.03 is settable; torqued's own floor is 0.106 (0.5 × 0.212) and could never get
  there even if it validated.
- **latAccelFactor: 5 (lane-change band) to 10 (steady curves)**, vs live 1.689 — **3–6× too low**, direction UP. The
  toggle max is 2.53 (1.5 × 1.689); 5–10 needs `torque_data/params.toml:14` (which also re-bases the toggle range and
  torqued's caps). Because the plant is integrator-like no single value is exact; 5 is the value that makes the feedforward
  right for the manoeuvre that rings (a highway lane change, ≈ 0.3 Hz), 9–10 for steady lane keeping.
- **latAccelOffset:** the pose instrument's intercept is −0.26 to −0.47 m/s² on every route (road crown at the operator's
  usual roads / device roll); torqued's raw offset says the same (−0.21 to −0.37). With torqued invalid the controller
  uses 0. Not a gain lever; noted because a custom-LAF run with ForceAutoTuneOff also freezes this at 0.
- **steeringAngleDeadzoneDeg = 0** on all routes; `apply_center_deadzone` is therefore a no-op and the friction term is
  live at every error size (EVIDENCE from carParams).

**Which lever, and how far the ring moves (EVIDENCE for the ratios, BELIEF that Gc ratio ≈ |L(7.5 Hz)| ratio):** the
outer-loop gain at the ring is Gc × |plant(7.5 Hz)|; the plant term is build-fixed and not identifiable from this data
(see §3), so the change in loop gain from a parameter edit is the Gc ratio above. SteerFriction is the bigger lever
(64 % of Gc) and the data say it is 7–10× too high; going 0.212 → 0.03 alone is 0.43×; 0.212 → 0.08 is 0.60×. LAF at the
toggle max adds another 0.75× on top (0.32× combined at friction 0.025). LAF to 5–10 via params.toml gets 0.14–0.20× and
also fixes the feedforward magnitude, which is the thing that makes the P/I terms work hard on every manoeuvre.

## 5. torqued's caps and clips on this car (task 4)

- Caps (`torqued.py:25,27,94-97`): LAF ∈ [0.7, 1.3] × 1.689 = [1.18, 2.196]; friction ∈ [0.5, 1.5] × 0.212 = [0.106, 0.318].
  The car on V280r2 sits at LAF 5–11 and friction ≈ 0.02 — **both outside what torqued is allowed to apply, in the same
  direction the ring wants.** Even a valid torqued would deliver 2.196 / 0.106 at best.
- The memory's "raw LAF 4.5–5.2 on V276" is real but is not a measurement of V276 or V280: it is a TLS through central
  buckets from the current build plus outer buckets from an old cache (points frozen at 6653), and `liveValid` is false,
  so nothing was applied. What the controller ran on r31/r32/r33 was 1.689 / 0.212 (EVIDENCE, §0).
- On r22 (V112, valid torqued) the filtered LAF drifted 2.18 → 2.34, ABOVE the 2.196 cap in the current tree. BELIEF: r22
  was logged on an older StarPilot with a different sanity factor, or a restored cache from such a build; the current
  code cannot produce 2.34. Not load-bearing here.
- torqued's friction statistic (1.5 × spread) on V280r2 points is 0.045 and is noise-driven (§3); its `|lat| ≤ 1` cut is
  harmless on these routes (slope 4.35 vs 4.37 with/without); its ±0.5 bucket bounds are what make it structurally unable
  to validate on a ×6 build.

## 6. Caveats, plainly

- r31 has 567 qualified points (V278r3 was driven slow: vEgo p50 8.7 m/s); its numbers are indicative only.
- All fits are closed-loop identification. OLS/FIR are biased DOWN by disturbance feedback; the IV estimate is the
  consistent one at low frequency and the stock anchor (1.4–1.7 vs 1.689) says the bias is modest there. Above ~2 Hz the
  spectral estimate is the controller inverse, not the plant.
- The ideal LAF for an integrator-like plant is frequency-dependent by construction; the two numbers given (5 and 9.6)
  bracket the band the operator drives in. A lat-jerk-based feedforward would fit this plant better than any LAF, but that
  is a code change, not a toggle, and out of scope here.
- opmath's expression was not available; if it carries terms beyond `(kp+lsf)/LAF + friction/0.30` (e.g. the jerk
  path's 0.22 gain, or the Accord ff taper `get_honda_accord_ff_scale`, which is ≤ 10 % and only above 0.45 m/s²), the
  ratios in §4 change by that term only.
