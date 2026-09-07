# STATE decision box as of 2026-09-05 (superseded 2026-09-06 by the grind #1 / V287 box) -- a record, not an instruction

## ✈ THE DECISION, IN ONE PLACE  — updated 2026-09-05 (**r3a + r3c FLEW: V282 unchanged, `SteerLatAccel` 4.0 then 3.6**; the LAF axis is NOT dead — the earlier "inert" verdict was a conditioning artefact; 🛑 **THE RESIDUAL IS A FUNCTION OF STEERING ANGLE, NOT SPEED** — the operator's speed split is confounded, he has no data above 10° of angle at 20+ m/s; the **SR map's ≥48° knots are ~9 % too low** and are the largest reachable term measured; the car's **true lat-accel-per-torque is ≈3.3**; **NO FIRMWARE CUT THIS SESSION**)

**ON THE CAR: V282**, unchanged across r39/r3a/r3c and confirmed **on the wire, not from the label** [EVIDENCE]: engaged-gated cave bit-6 duty **0.1140 / 0.1541 / 0.1561** and bit-5 **0.1341 / 0.1525 / 0.1678**, all strictly in (0,1) and far from r34/r35's exact 0.0000; byte-4 low 3 bits = 7 on 100 % of frames on all three. ⚠ The cave is **byte-identical V282↔V283**, so byte 4 can never separate those two; only a Ki fit on the 427 tap does. 427 saturation **0.0000 %** on all three (magnitude max 207/209/213 against a 1023 ceiling).

**THE TWO NEW DRIVES.** r3a = `75604b0a432fdc89_0000003a--283a39a1d6` (13 of 14 segments — **index 10 MISSING**, a real monotonic 60.02 s hole at route t 601.62→661.64 on the CAN clock = **597.02–657.04 on the `co_t` clock**); r3c = `…_0000003c--927965c2b4` (13 seg, no gaps). 🛑 **TRAP: `0000003a--4e55c1e0f4` and `0000003b--a4a7f4dbf1` are OLD-EPOCH (2026-08-01) routes from the dongle counter reset — match the full id with its hash suffix, always.** ⚠ **`analysis-2020accord/extract/extract_r3a_cache.py` already existed and belongs to the OLD epoch**; the current-epoch extractors are `extract_r3a_v282_cache.py` / `extract_r3c_v282_cache.py`, and **repo-root `_scratch/cache/r3a/` is the WRONG-EPOCH cache — do not read it.**

**SECONDS CONVENTION, BINDING:** true wire rate **100 Hz** (`count/span`), verified through two independent code paths. r39 **879.7 s** engaged (92.51 %), r3a **483.1 s** (65.94 %), r3c **593.7 s** (79.91 %). STATE's former "869.7 s" used `1/median(diff)` = 101.16 Hz and overstates fs by 1.3 %; frame *fractions* were unaffected. 🛑 **`grid()` lays a uniform axis across r3a's hole and inflates its `latActive` by exactly 60.0 s** (543.3 s phantom vs 483.3 s real) — mask the gap; `gap_starts`/`gap_ends` are in the caches.

**THE TUNE, ATTRIBUTED FROM THE WIRE** [EVIDENCE — LAF recovered exactly per frame as `-(p+i+d+f)/output`, since the PID runs in lat-accel space and LAF divides once at `interfaces.py:329`]: **LAF = 2.110000 / 4.000000 / 3.600000**, sd ~3e-7, n 63k/26k/35k. `kp = 0.800000` flat at every speed on all three (`controlsd.py:444` overwrites the whole `_k_p` schedule with the `SteerKP` toggle every frame). Full `initData.params` diff across the three routes gives **exactly three** substantive changes: `SteerLatAccel`; the git commit `8a28dcef8 → ffe28378f` (**one UI-only commit**, raises a slider ceiling, **zero lines under `controls/`, `locationd/`, `opendbc_repo/` or `common/`** — not a confound); and 🛑 **`Model`/`DrivingModel` `rdf43` → `tsfdo`**, a driving-model swap that **confounds r39 vs r3a/r3c**. ⇒ **r3a vs r3c is a CLEAN PAIR** (only LAF differs).

### 🛑🛑 THE RESIDUAL IS ON THE **ANGLE** AXIS, NOT THE SPEED AXIS — the session's main result
The operator reports understeer on hard corners < 20 mph and oversteer above. **In his driving those are the same event seen twice: "hard corner below 20 mph" ≡ large steering angle, and "above 20 mph" ≡ near centre. Above 10° of angle at 20–40 m/s the corpus has essentially NO DATA.** The two axes are confounded and **angle is the resolvable one.**

Map error (map/fit; **>1.00 = map ratio too high → oversteer; <1.00 = too low → understeer**), pooled:

| \|ang\| \ v | 2–6 m/s | 6–9 | 9–14 | 14–20 | 20–40 |
|---|---|---|---|---|---|
| **1.5–10°** | 0.995 | 1.021 | 1.031 | 1.016 | 1.037 |
| **10–25°** | 0.980 | 1.056 | 0.988 | 1.021 | *(n=160)* |
| **25–48°** | 0.994 | 1.007 | 1.017 | *(n=2)* | *(n=0)* |
| **48–90°** | *(n=242)* | **0.926** | 0.998 | *(n=0)* | *(n=0)* |
| **90–400°** | **0.932** | **0.936** | *(n=30)* | *(n=0)* | *(n=0)* |

Across the top row (speed, near centre) it is **flat within ±4 %**; down the 6–9 m/s column (angle) it breaks hard at 48°.

⭐ **THREE-WAY DECOMPOSITION of the angle→curvature mismatch** (r39): **FLAT** (ratio level) **0.006–0.012** — already spent by the map, do not touch · **ANGLE** (map knots ≥ 48°) **~0.09** — the big one, binds only at low speed · **SPEED** (near-centre slip) **0.042**, not resolvable.

**ARBITRATED ON A THIRD INSTRUMENT** [EVIDENCE]. Wheel-speed differential yaw from raw CAN **0x1D0** — no gyro, no roll model, no Kalman, no calibration matrix. 🛑 **`carState.wheelSpeeds` and `carState.yawRate` are BOTH identically zero on this platform** — dead channels; the real source is 0x1D0, now decoded as `w1d0_*` (backcalc schema v4). Rolling-radius mismatch calibrated out first (δ_rear +0.000628/+0.000703/+0.000747, which would fake +0.008–0.009 rad/s of yaw at 20 m/s). FWD **measured**, not assumed (front axle runs +0.016 m/s per m/s² of `aEgo`). Near-centre stratum (|sa| < 48°), scale-normalised, r39, 7–30 m/s: **spread 0.074 (wheel rear) / 0.037 (wheel front) / 0.054 (gyro)** against **0.155 / 0.089 / 0.096** unstratified. ⇒ **Restricting to near-centre roughly halves the spread on every instrument and leaves no resolvable crossing of 1.000. The excess is carried by ≥48° blocks, not by speed.** ⚠ The ≥48° stratum is itself **UNRESOLVED** on this instrument (10 gated blocks on r39) — large-angle events are transient and the steady-state gate removes them — so the map-knot finding rests on the two angle-fit pipelines, not on the wheel instrument.

### ✈ THE ONE CHANGE: raise the SR map's ≥48° knots ~×1.09. Everything else stays.
`selfdrive/controls/lib/latcontrol_vehicle_tunes.py:86`, breakpoints unchanged:
```
was  HONDA_ACCORD_STEER_RATIO_V = [16.00, 16.00, 15.02, 14.52, 13.97, 13.75, 13.50, 12.81, 11.67, 11.06]
now  HONDA_ACCORD_STEER_RATIO_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
```
Measured at low speed where tyre slip is negligible **and the roll term is 0.3–1 % of the signal**, so it is a rack-geometry measurement, immune to both the tyre model and the bank:

| \|angle\| | fitted SR | 95 % CI | map | map/fit |
|---|---|---|---|---|
| 0–10° | 16.362 | [15.86, 16.93] | 16.00 | 0.978 |
| 10–25° | 16.072 | [15.51, 16.70] | 16.00 | 0.996 |
| 25–48° | 16.554 | [16.11, 16.85] | 16.00 | 0.967 |
| **48–76°** | **16.567** | [15.92, 17.09] | 15.05 | **0.909** |
| **76–121°** | **15.278** | [15.24, 15.31] | 13.93 | **0.912** |
| **121–200°** | **14.749** | [14.53, 14.96] | 13.62 | **0.924** |
| **200–400°** | **14.081** | [14.04, 14.13] | 12.86 | **0.913** |

Independently confirmed on a second instrument: at v < 9, `R_m` is **flat** across angle strata (1.07–1.21) while `1/rho` swings **1.086 (<48°) → 0.935 (≥121°)** — a 14 % move entirely on the measurement, replicated on all three arms. 🛑 **The earlier attribution of the low-speed shortfall to the P-only firmware deadband was WITHDRAWN by its own author; it is the map's high-angle knots.** ⭐ Because it is a LERP, the ≥48° knots move without touching the 0–48° flat segment, and **median |sa| above 11 m/s is 5–8°, so this cannot touch the highway behaviour.** ⚠ Direction solid across four bins; **magnitude rests on 3–8 s per bin** — if it overshoots, halve it (×1.045), do not revert. Knots scaled ×1.09 and clamped at 16.00 to keep the table monotone non-increasing.

### ⭐ THE CAR'S TRUE LAT-ACCEL-PER-TORQUE IS ≈3.3 — and the LAF axis is NOT dead
🛑 **RETRACTION: "the LAF dose is measurably inert" was an artefact of conditioning on `|setpoint| > 0.5`**, which selects only the top amplitude decile. Unconditioned whole-route road gain is **monotone**: 1.1215 [1.1031,1.1401] @ 2.11 → 1.1055 [1.0480,1.1580] @ 3.6 → **1.0387** [0.9588,1.1140] @ 4.0 (CIs still overlap — direction, not a resolved effect).

| route | assumed LAF | n | median \|meas\|/\|ctrl\| | **LAF_true implied** |
|---|---|---|---|---|
| r39 | 2.11 | 19,514 | 1.515 | **3.20** |
| r3c | 3.60 | 14,427 | 0.909 | **3.27** |
| r3a | 4.00 | 13,155 | 0.841 | **3.37** |

Three assumed values spanning 1.9×, implied truth agreeing to **5 %** — that invariance is the check that it measures the plant, not the assumption. It sits between the flown 2.11 and torqued's unused `latAccelFactorRaw` (4.89–5.84), and is a **third** number against the two prior sizings (4.0 and 9.5). **EVIDENCE-grade for "≈3.2–3.4", not for a third decimal. Recommendation: `SteerLatAccel` 3.6.** Priced trade by amplitude (road gain, gyro, SR-free): large-command **1.126 → 1.117 → 1.048**; small-command **0.794 → 0.547 → 0.540** (CIs do not overlap — but ⚠ **perfectly confounded with the `tsfdo` model swap**).

**THE GAIN ERROR IS A FUNCTION OF COMMAND AMPLITUDE, NOT SPEED** [EVIDENCE, pooled, no curve selection]: gain vs speed **1.130 / 1.131 / 1.110 / 1.107** across 5–9 / 9–14 / 14–20 / 20–40 m/s — flat and marginally falling; gain vs |setpoint| **0.687 → 0.757 → 0.836 → 1.061 → 1.124 → 1.200 → 1.128**, a ~1.4× rise **present in every speed column separately**. Two regimes: below ~0.10 m/s² the feedforward **points the wrong way** (`f/setp` = −0.42/−0.46) because `ff = future_desired − roll·g·roll_offset_fade` and `roll·g` ≈ 0.22–0.33 m/s² exceeds the whole bin, with the fade already at 1.0 above 2.5 m/s; above 0.35 m/s² P and I both turn negative and the car still delivers 1.12–1.20×.

### 🛑 THE STANDING CURVE ERROR IS REAL — and no mechanism proposed this session survives
`pid_log.desiredLateralAccel = setpoint` and `pid_log.actualLateralAccel = measurement` (`latcontrol_torque.py:672-673`, verified at the flown commit), so **`R_m` is exactly the ratio the loop nulls** and the comparison-artefact hypothesis dies by construction. Physical folded raw error (`ctl_error / (1 + lsf/kp)`, kp 0.8) on r39: **−0.125 / −0.096 / −0.059 / −0.076 m/s²** by speed band, every CI excluding zero, against **−0.025 on straights**. Replicated on r3a/r3c.
- ⭐ **CONFIRMED — the integrator cannot pre-charge against a direction-reversing bias.** Folded error −0.120 with **unfolded +0.014** on balanced L/R counts; unfolded `i` holds **+0.19** (road crown / alignment) while the direction-reversing part is never cancelled. This is the mechanism.
- 🛑 **KILLED — the `k_i_eff`-vs-speed convergence story.** The arithmetic is right (`error_with_lsf = error × (1 + lsf/kp)`, `lsf ∝ 1/v²`, effective `k_i` falls 0.55→0.16, a measured 3.9–6.8× collapse, wire/pred 0.97–1.03). The mechanism is not what drives the signal: the dimensionless group `k_i_eff × T_curve` is **non-monotone** (rho −0.133, n 81); the residual is **smallest** at 22–40 m/s; τ(error) = **0.85 s against a 5.9 s median curve**, settling at `e_inf` = −0.167; `i` moves **2×** the error it fails to remove; and the error **GROWS** with time-in-curve (−0.023 → −0.266 over 3 s) where an unconverged integrator gives decay.
- 🛑 **KILLED — the setpoint-construction / lead-term story.** Stripping the lead makes the excess **worse** (1.113 → 1.123 → 1.133 on r39, all three routes, both instruments). `R_m` is flat within 1.5 % across a **±0.30 s** setpoint shift and never approaches 1.000 ⇒ **it is a SCALE, not a phase.**
- 🛑 **KILLED — the roll-compensation artefact.** Note the leading minus at `:232`: for `roll > 0` the term **adds** to the measurement and **lowers** `1/rho`, so it **masks** the spread rather than creating it. Deleting it takes r39's spread **0.131 → 0.318** and r3a's 0.106 → 0.374. Arithmetic closes to the digit (folded `Rm` +0.173 vs roll-free measurement 0.978 ⇒ bias factor 0.8495; 1.243 × 0.8495 = 1.056 vs 1.058 measured). The bank correlation is nonetheless real — `mean(roll·sign(turn))` +0.029…+0.064 rad at speed, while the *unfolded* mean goes negative, i.e. genuine road bank, **not** a constant mounting offset.
- **STRUCK:** `get_honda_accord_ff_scale` sits at its 0.90 floor through most of every curve — a 9 % FF **cut**, wrong sign; removing it would make the over-delivery **bigger**. And `unwind_detected` is **exactly 0.0000 inside curves, structurally** (it needs |setpoint| < 0.3; a curve is > 0.5) ⇒ **STATE's "curve-exit unwind freeze" cannot act inside a curve at all.** Both closed.

### 🛑 PINNED PARAMETERS — three now, all from the operator's own toggles
1. `liveParameters.steerRatio` = **12.500000, sd 0.000e+00** — pinned by `ForceAutoTuneOff` (`paramsd.py:29-31`) *and* overwritten by the map (`controlsd.py:478`). Inert twice over.
2. 🛑 `liveParameters.stiffnessFactor` = **1.000000, sd 0.000e+00** — same pin, but **NOT inert**: it flows `controlsd.py:468` → `update_params` → `cF`/`cR` → `calc_slip_factor` → `curvature_factor(v)`. **The only live handle on the speed-dependent term, and it has never been allowed to learn.** Sign: `sf ∝ 1/x`, so raising it REDUCES modelled understeer. **Do not move it** — the decomposition puts the near-centre speed term at 0.042 and not resolvable.
3. `liveDelay.lateralDelay` = **0.200000, sd 0.0000** — pinned by `SteerDelay` with `UseAutoSteerDelay` = 0; `lat_delay` = 0.300 s exactly on all three routes. Not a cross-route confound.
paramsd IS running and converging — `angleOffsetDeg` and `roll` vary continuously with thousands of unique values. Only the SR and stiffness **outputs** are discarded at publish.

### ✈ NEXT — in order
1. **Fly the ≥48° map knots ALONE** (branch `accord-sr-map-ge48deg` off the flown `ffe28378f`; ⚠ local `Dom` shares **no history** with the flown commit and `origin/Dom` is 2158 commits off it — **do not push to `Dom`**). Score on the operator's hard-turn feel and on `1/rho` in the ≥48° strata.
2. **`SteerLatAccel` → 3.6**, not with the map change on the same drive.
3. 🛑 **INSTRUMENT `steer_limited_by_safety`.** It fires on **29–37 % of curve frames** and is **not logged**. It is symmetric in the error sign (0.311 vs 0.303 on r39) and `R_m` is identical with and without it, so it does **not** carry the anomaly — but on a modded EPS pushing authority into the safety rate limiter it is the largest unmeasured term in the loop. `starpilot_lateral_state` already logs `unwindDetected` and `lowSpeedFactor`; `backcalc_extract.py` does not capture them.
4. **A deliberate large-angle data pass** before trusting the ≥48° magnitude — 3–8 s per bin is the whole basis, and normal driving barely samples that regime.
5. Still open from r39, unchanged: the **plant-magnitude identification drive** (427 `T` tap and 0x18F rate simultaneously under broadband excitation).

### 🛑 DEFECTS FOUND OR CLOSED THIS SESSION
1. ✅ **CLOSED — dec39's 91-field cache had no driver in the repo.** Reconstructed as `rlog-tools/decode/extract_r39_r3a_r3c.py`; it reproduces `r39.npz` **byte-for-byte** (sha256 `9563baa9…`, 16,014,213 B, all 91 fields equal) and `_events`/`_census_seg`/`_segments` JSON byte-identical.
2. ✅ **FIXED — `backcalc_extract.py` mixed the two 0x0E4 sources.** `m.src >= 128` caught the stock camera (src 128) alongside openpilot (129); now `E4_SRC = 129`. Measured: the old rule held **exactly 2×** the frames (144,451 → 72,057) and `e4_req` mean 0.3424 → 0.6678. **69 of 73 fields were bit-identical.** New provenance keys `e4_src_rule` / `gap_starts` / `gap_ends` / `segments_present` / `segments_missing`; schema v4 adds `w1d0_*`. ⚠ **The 9 legacy `_backcalc.npz` still carry the old rule and lack `e4_src_rule` — that absence is the tell.** Unsafe only in `e4_cmd`/`e4_req`/`eng_wire`; not rebuilt.
3. ✅ **FIXED — `r39_1ab.json`'s 427 descriptor was wrong.** `0.2 → 8.0` counts/LSB; the kit's sar-3 (×8) decode is correct, bit 9 is the sign (`b0 ∈ {128,130}`, magnitude max 207–213 vs a 1023 ceiling). No measured value changed.
4. **REPORTED, NOT FIXED — `extract_r39_v280cache.py` records each segment's `lo` from `initData`**, which is the process-start stamp, so `r39_marks.json`'s `lo_route`/`t_in_seg` are meaningless and any gap computed from `lo` comes out negative. `r39.npz` data unaffected; STATE's `MARKS` are `t_route` and unaffected. New extractors add `lo_can`.
5. **`carState.wheelSpeeds` and `carState.yawRate` are identically zero** on this platform — dead channels that return a silent zero rather than an error.
6. **The dongle's route counter RESET** — two routes numbered `0000003a`. Check the epoch of every cache before a cross-route comparison. (Standing.)

---

