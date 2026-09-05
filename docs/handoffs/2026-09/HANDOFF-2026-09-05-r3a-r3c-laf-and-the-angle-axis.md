# HANDOFF 2026-09-05 — r3a + r3c: the LAF sweep, and the residual is on the ANGLE axis

**Firmware: V282, UNCHANGED on all three routes. No build was cut this session.** Everything here is
openpilot-side. The session was an orchestrated read of two new drives against r39.

---

## The operator's report, verbatim

> "I wasn't able to tell the difference between the two, not even sure if it helped at all relative to
> lat accel = 2.11."
> "In general, it seems like we understeer on hard turns around corners <20 mph"
> "at 20+ mph, we oversteer"
> "the most desirable thing is to stop the consistent oversteer at 20+ mph. hard turns are just a nice
> to have."

And, on method — the instruction that shaped the whole session:

> "I would think it's more appropriate to keep and fix real physical values like that in place."

That principle turned out to be the right one **and** to point at the correct fix. It is why the
session did not end up recommending a flat steer-ratio de-tune.

---

## The routes

| | r39 | r3a | r3c |
|---|---|---|---|
| route id | `…_00000039--f56039af87` | `…_0000003a--283a39a1d6` | `…_0000003c--927965c2b4` |
| `SteerLatAccel` | 2.11 | **4.0** | **3.6** |
| segments | 16 | **13 of 14 — index 10 MISSING** | 13 |
| engaged (100 Hz convention) | 879.7 s (92.51 %) | 483.1 s (65.94 %) | 593.7 s (79.91 %) |
| engaged median speed | 9.62 m/s | **16.41** | 15.23 |
| s above 25 m/s | 61.9 | **176.8** | 113.2 |
| `userBookmark` presses | 2 | **0** | **0** |

🛑 **TRAPS.** `0000003a--4e55c1e0f4` and `0000003b--a4a7f4dbf1` are **old-epoch (2026-08-01)** routes
from the dongle counter reset. `analysis-2020accord/extract/extract_r3a_cache.py` already existed and
belongs to that old epoch; repo-root `_scratch/cache/r3a/` is the **wrong-epoch cache**. The
current-epoch extractors are `extract_r3a_v282_cache.py` / `extract_r3c_v282_cache.py`.

🛑 **r3a's missing segment is a real 60.02 s hole** — route t 601.62→661.64 on the CAN clock,
**597.02–657.04 on the `co_t` clock**. `grid()` lays a uniform axis straight across it and inflates
`latActive` by exactly 60.0 s (543.3 phantom vs 483.3 real). Every analysis statistic in this session
masked it; the census row in one interim report did not, and was corrected.

---

## What was confounded, and what was not

Full `initData.params` diff across the three routes yields **exactly three** substantive changes:

1. `SteerLatAccel` — the intended lever.
2. `GitCommit` `8a28dcef8 → ffe28378f` — **one UI-only commit** raising a slider ceiling. Zero lines
   under `controls/`, `locationd/`, `opendbc_repo/`, `common/`. **Not a confound.**
3. 🛑 **`Model` / `DrivingModel` `rdf43` → `tsfdo`** — a driving-model swap. **Confounds r39 vs
   r3a/r3c.**

⇒ **r3a vs r3c is a clean pair.** Ruled out as unchanged: SteerKP, SteerFriction, SteerDelay,
SteerRatio, ForceTorqueController, ForceAutoTune(Off), NNFF, all lane settings, every `carParams`
field, and the `liveParameters` structure.

**The tune was attributed from the wire, not the label.** The PID runs in lateral-acceleration space
and LAF divides once at `interfaces.py:329`, so `LAF = -(p+i+d+f)/output` on any unclipped engaged
frame. Measured **2.110000 / 4.000000 / 3.600000**, sd ~3e-7, n 63k/26k/35k. `kp = 0.800000` flat at
every speed on all three.

---

## The main result — the residual is a function of ANGLE, not speed

The operator's speed split is confounded with angle. **In his driving "hard corner below 20 mph" ≡
large steering angle and "above 20 mph" ≡ near centre**, and above 10° of steering at 20–40 m/s the
corpus has essentially no data. Map error (map/fit; >1.00 → oversteer, <1.00 → understeer):

| \|ang\| \ v | 2–6 m/s | 6–9 | 9–14 | 14–20 | 20–40 |
|---|---|---|---|---|---|
| 1.5–10° | 0.995 | 1.021 | 1.031 | 1.016 | 1.037 |
| 10–25° | 0.980 | 1.056 | 0.988 | 1.021 | *(n=160)* |
| 25–48° | 0.994 | 1.007 | 1.017 | *(n=2)* | *(n=0)* |
| **48–90°** | *(n=242)* | **0.926** | 0.998 | *(n=0)* | *(n=0)* |
| **90–400°** | **0.932** | **0.936** | *(n=30)* | *(n=0)* | *(n=0)* |

Speed axis (top row): flat within ±4 %. Angle axis (6–9 m/s column): a hard break at 48°.

**Three-way decomposition (r39):** FLAT (ratio level) **0.006–0.012** — spent, do not touch · **ANGLE
(map knots ≥48°) ~0.09** — the largest reachable term measured · SPEED (near-centre slip) **0.042**,
not resolvable.

### Arbitrated on a third instrument
Two agents disagreed 3× on the size of the speed dependence (0.131 vs 0.042). The tiebreaker was
**wheel-speed differential yaw from raw CAN `0x1D0`** — no gyro, no roll model, no Kalman, no
calibration matrix.

🛑 **`carState.wheelSpeeds` and `carState.yawRate` are both identically zero on this platform** —
dead channels returning a silent zero. Real source is 0x1D0, now decoded as `w1d0_*`. Rolling-radius
mismatch calibrated out first (δ_rear +0.000628/+0.000703/+0.000747 — enough to fake +0.008–0.009
rad/s of yaw at 20 m/s). FWD **measured**, not assumed (front axle runs +0.016 m/s per m/s² of `aEgo`).

Near-centre (|sa| < 48°), scale-normalised, r39, 7–30 m/s — spread **0.074 / 0.037 / 0.054** (wheel
rear / wheel front / gyro) against **0.155 / 0.089 / 0.096** unstratified. **Restricting to
near-centre halves the spread on every instrument and leaves no resolvable crossing of 1.000.** The
excess is carried by ≥48° blocks. The two agents were never actually in conflict — one recovered the
other's 0.042 exactly on the same stratum, and from 11 m/s up the two pipelines return **identical
values**.

⚠ The ≥48° stratum is itself **unresolved** on the wheel instrument (10 gated blocks on r39):
large-angle events are transient and a steady-state gate removes them. The knot finding rests on the
two angle-fit pipelines.

---

## The change to fly

`selfdrive/controls/lib/latcontrol_vehicle_tunes.py:86`, breakpoints unchanged:

```
was  HONDA_ACCORD_STEER_RATIO_V = [16.00, 16.00, 15.02, 14.52, 13.97, 13.75, 13.50, 12.81, 11.67, 11.06]
now  HONDA_ACCORD_STEER_RATIO_V = [16.00, 16.00, 16.00, 15.83, 15.23, 14.99, 14.72, 13.96, 12.72, 12.06]
```

| \|angle\| | fitted SR | 95 % CI | map | map/fit |
|---|---|---|---|---|
| 0–10° | 16.362 | [15.86, 16.93] | 16.00 | 0.978 |
| 10–25° | 16.072 | [15.51, 16.70] | 16.00 | 0.996 |
| 25–48° | 16.554 | [16.11, 16.85] | 16.00 | 0.967 |
| **48–76°** | **16.567** | [15.92, 17.09] | 15.05 | **0.909** |
| **76–121°** | **15.278** | [15.24, 15.31] | 13.93 | **0.912** |
| **121–200°** | **14.749** | [14.53, 14.96] | 13.62 | **0.924** |
| **200–400°** | **14.081** | [14.04, 14.13] | 12.86 | **0.913** |

Measured at low speed where slip is negligible **and the roll term is 0.3–1 % of the signal**, so it
is a rack-geometry measurement, immune to both the tyre model and the bank. Confirmed independently:
at v < 9, `R_m` is flat across angle strata (1.07–1.21) while `1/rho` swings 1.086 (<48°) → 0.935
(≥121°) — a 14 % move entirely on the measurement, on all three arms.

**Why it is safe:** the table is a LERP, so the ≥48° knots move without touching the 0–48° flat
segment; and **median |sa| above 11 m/s is 5–8°**, so it cannot touch the highway behaviour either
way. Knots scaled ×1.09 and clamped at 16.00 to keep the table monotone non-increasing.

⚠ Direction solid across four bins; **magnitude rests on 3–8 s per bin**. If it overshoots, halve it
(×1.045) rather than reverting.

🛑 **Git state — do not push to `Dom`.** Local `Dom` (`3d4c625de`) shares **no merge base** with the
flown commit; `origin/Dom` (`f55ad9162`) is **2158 commits** off it and the flown commit is on no
remote branch. Branch from `ffe28378f` — exactly what was flown — as `accord-sr-map-ge48deg`.

---

## Retractions and killed hypotheses

Four mechanisms were proposed this session. **Three died, including both of the orchestrator's.**

- 🛑 **KILLED — the `k_i_eff`-vs-speed convergence story (orchestrator's).** The arithmetic is right:
  `error_with_lsf = error × (1 + lsf/kp)`, `lsf ∝ 1/v²`, effective `k_i` falls 0.55 → 0.16, a measured
  3.9–6.8× collapse (wire/pred 0.97–1.03). The mechanism is not what drives the signal. `k_i_eff ×
  T_curve` is **non-monotone** (rho −0.133, n 81); the residual is **smallest** at 22–40 m/s;
  **τ(error) = 0.85 s against a 5.9 s median curve**, settling at `e_inf` = −0.167; `i` moves **2×**
  the error it fails to remove; and the error **grows** with time-in-curve (−0.023 → −0.266 over 3 s)
  where an unconverged integrator gives decay.
- 🛑 **KILLED — the roll-compensation artefact (orchestrator's, sign inverted).** `calc_curvature`
  carries a leading minus at `:232`, so for `roll > 0` the term **adds** to the measurement and
  **lowers** `1/rho` — it **masks** the spread rather than creating it. Deleting it takes r39's spread
  **0.131 → 0.318**. Arithmetic closes to the digit (folded `Rm` +0.173 vs roll-free measurement
  0.978 ⇒ bias 0.8495; 1.243 × 0.8495 = 1.056 vs 1.058 measured). The bank correlation is real
  (`mean(roll·sign(turn))` +0.029…+0.064 rad at speed) but the *unfolded* mean goes negative, i.e.
  genuine road bank, **not** a constant mounting offset.
- 🛑 **KILLED — the setpoint-construction / lead-term story.** Stripping the lead makes the excess
  **worse** (1.113 → 1.123 → 1.133 on r39, all three routes, both instruments). `R_m` is flat within
  1.5 % across a **±0.30 s** setpoint shift and never approaches 1.000 ⇒ **a SCALE, not a phase.**
- ⭐ **SURVIVED — the integrator cannot pre-charge against a direction-reversing bias.** Folded curve
  error −0.120 with **unfolded +0.014** on balanced L/R counts; unfolded `i` holds +0.19 (road crown /
  alignment) while the direction-reversing part is never cancelled.

**Other retractions:**
- 🛑 **"The LAF dose is measurably inert" — RETRACTED.** It was an artefact of conditioning on
  `|setpoint| > 0.5`, which selects only the top amplitude decile. Unconditioned road gain is
  **monotone**: 1.1215 → 1.1055 → **1.0387** across LAF 2.11 → 3.6 → 4.0.
- 🛑 **"The low-speed shortfall is the P-only firmware deadband" — WITHDRAWN by its own author.** It
  is the SR map's high-angle knots. `R_m` is flat across angle strata while `1/rho` swings 14 %.
- **STRUCK:** `get_honda_accord_ff_scale` sits at its 0.90 floor through most of every curve — a 9 %
  FF **cut**, wrong sign; removing it would make the over-delivery bigger. And `unwind_detected` is
  **exactly 0.0000 inside curves, structurally** (needs |setpoint| < 0.3; a curve is > 0.5) ⇒
  STATE's "curve-exit unwind freeze" **cannot act inside a curve at all.**

---

## The other actionable number: true LAF ≈ 3.3

| route | assumed LAF | n | median \|meas\|/\|ctrl\| | LAF_true implied |
|---|---|---|---|---|
| r39 | 2.11 | 19,514 | 1.515 | **3.20** |
| r3c | 3.60 | 14,427 | 0.909 | **3.27** |
| r3a | 4.00 | 13,155 | 0.841 | **3.37** |

Three assumed values spanning 1.9×, implied truth agreeing to 5 % — the invariance is the check.
**Recommendation: `SteerLatAccel` 3.6.** Priced by amplitude: large-command gain 1.126 → 1.117 →
**1.048**; small-command 0.794 → 0.547 → 0.540 (⚠ confounded with the model swap).

**The gain error is a function of command amplitude, not speed:** gain vs speed 1.130 / 1.131 / 1.110
/ 1.107; gain vs |setpoint| 0.687 → 1.200, present in every speed column separately. Below ~0.10 m/s²
the feedforward **points the wrong way** (`f/setp` = −0.42/−0.46) because `ff = future_desired −
roll·g·roll_offset_fade` and `roll·g` ≈ 0.22–0.33 m/s² exceeds the whole bin.

---

## Pinned parameters — three, all from the operator's own toggles

1. `liveParameters.steerRatio` = **12.500000, sd 0** — pinned by `ForceAutoTuneOff`
   (`paramsd.py:29-31`) *and* overwritten by the map (`controlsd.py:478`). Inert twice over.
2. 🛑 `liveParameters.stiffnessFactor` = **1.000000, sd 0** — same pin, but **NOT inert**: it flows
   `controlsd.py:468` → `update_params` → `cF`/`cR` → `calc_slip_factor` → `curvature_factor(v)`.
   The only live handle on the speed-dependent term, never allowed to learn. `sf ∝ 1/x`, so raising
   it reduces modelled understeer. **Do not move it** — the near-centre speed term is 0.042 and not
   resolvable.
3. `liveDelay.lateralDelay` = **0.200000, sd 0** — `lat_delay` = 0.300 s exactly. Not a confound.

paramsd **is** running and converging (`angleOffsetDeg` and `roll` vary continuously); only the SR and
stiffness outputs are discarded at publish.

---

## Defects found or closed

1. ✅ **CLOSED — dec39's 91-field cache had no driver in the repo.** Reconstructed as
   `rlog-tools/decode/extract_r39_r3a_r3c.py`; reproduces `r39.npz` **byte-for-byte**
   (sha256 `9563baa9…`, 16,014,213 B, all 91 fields equal), JSON sidecars byte-identical.
2. ✅ **FIXED — `backcalc_extract.py` mixed the two 0x0E4 sources.** `m.src >= 128` caught the stock
   camera (128) alongside openpilot (129); now `E4_SRC = 129`. Old rule held **exactly 2×** the frames
   (144,451 → 72,057); `e4_req` mean 0.3424 → 0.6678; **69 of 73 fields bit-identical**. New
   provenance keys; schema v4 adds `w1d0_*`. ⚠ The 9 legacy `_backcalc.npz` still carry the old rule
   and lack `e4_src_rule` — that absence is the tell. Unsafe only in `e4_cmd`/`e4_req`/`eng_wire`.
3. ✅ **FIXED — `r39_1ab.json`'s 427 descriptor.** `0.2 → 8.0` counts/LSB; sar-3 (×8) is correct,
   bit 9 is the sign. No measured value changed.
4. **REPORTED, NOT FIXED — `extract_r39_v280cache.py` takes each segment's `lo` from `initData`**,
   the process-start stamp, so `r39_marks.json`'s `lo_route`/`t_in_seg` are meaningless and gaps
   computed from `lo` come out negative. Data unaffected. New extractors add `lo_can`.
5. **`carState.wheelSpeeds` and `carState.yawRate` are identically zero** on this platform.
6. **Dongle route-counter reset** — two routes numbered `0000003a`. (Standing.)

---

## Next, in order

1. **Fly the ≥48° map knots ALONE.** Score on hard-turn feel and on `1/rho` in the ≥48° strata.
2. **`SteerLatAccel` → 3.6**, not on the same drive as the map change.
3. 🛑 **Instrument `steer_limited_by_safety`.** It fires on **29–37 % of curve frames** and is **not
   logged**. It is symmetric in the error sign (0.311 vs 0.303) and `R_m` is identical with and
   without it, so it does not carry the anomaly — but on a modded EPS pushing authority into the
   safety rate limiter it is the largest unmeasured term in the loop. `starpilot_lateral_state`
   already logs `unwindDetected` and `lowSpeedFactor`; `backcalc_extract.py` does not capture them.
4. **A deliberate large-angle data pass** before trusting the ≥48° magnitude — 3–8 s per bin is the
   whole basis and normal driving barely samples that regime.
5. Still open from r39: the **plant-magnitude identification drive**.

---

## Method note — what made this session work

The decisive move was the operator's own pushback: *a single flat steer-ratio number cannot produce a
sign flip across speed.* That killed the orchestrator's opening hypothesis and forced the question
onto the axis that turned out to be resolvable. Two of the three mechanisms proposed afterwards were
the orchestrator's own, and both were falsified by agents explicitly briefed to try to break them —
including one where the orchestrator's sign was inverted and the effect ran the other way. **Every
brief that asked an agent to kill a hypothesis got a kill.** That is the pattern worth repeating.
