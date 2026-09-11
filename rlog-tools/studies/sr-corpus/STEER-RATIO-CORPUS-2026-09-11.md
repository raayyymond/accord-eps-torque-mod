# The Accord's steering-ratio curve, measured over the whole corpus — 2026-09-11

**82 routes · 894 segments · 14.2 h of valid frames · 2.9 h after the core gate.**
Result: the fork's variable-ratio map was **too flat**. It quickened at **53 %** of the rate the rack
does. Shipped as StarPilot `57410c3b4` (branch `Dom`).

Scripts: `sr_extract.py` → `sr_lib.py` / `sr_lib2.py` → `sr_pool.py` · `sr_analyze.py` ·
`sr_episodes.py` · `sr_transit.py` · `sr_checks.py` · `sr_knots.py` · `sr_final.py`.
Independent adversarial pass in `audit/` (its own extractor and cache), pre-registered fail criteria
in `audit/PREREG-FAIL-CRITERIA.md`. Outputs land in the gitignored `_scratch/`; rerun to regenerate.

**EVIDENCE unless marked BELIEF.**

---

## 0. The instrument, and why it is firmware- and control-independent

```
sR_true = curvature_factor(v) * sa / ( -yaw_cal/v  -  roll_comp(roll, v) )
aR   = wheelbase - centerToFront
sf   = mass*(cF*aF - cR*aR) / (wheelbase^2 * cF * cR)
curvature_factor(v) = 1/(1 - sf*v^2)/wheelbase      roll_comp = 9.81*roll / ((1/sf) - v^2)
sa      = radians(carState.steeringAngleDeg)        # NOT offset-corrected — see §3
yaw_cal = ( rot_from_euler(liveCalibration.rpyCalib).T @ livePose.angularVelocityDevice )[2]
```

The right-hand side contains **no steering ratio**, so it settles "is the plan being delivered"
independently of what the controller believes. It uses only `carState`, `livePose`,
`liveCalibration`, `liveParameters.roll` and `carParams` geometry — **nothing the controller
produces**: no `desiredCurvature`, no `torqueState`, no `carOutput.torque`.

⭐ **It is kinematic — wheel angle to yaw rate — so it does not matter who turns the wheel.**
Engaged and manual driving both count, and driver torque is irrelevant. That is the whole reason the
corpus is 14.2 h instead of the ~2 h of engaged time, and it is where the large-angle data lives.
Measured invariance: split by `|carState.steeringTorque|` into <30 / 30-150 / ≥150, past 45° reads
**14.47 / 14.41 / 14.47**. Firmware invariance: a **stock-firmware, 98 %-manual** route reads
**15.82** at |sa| 35-400° where a **V289 rev 1, 83 %-engaged** route reads **15.88**.

Gates: calibrated, `v > 4 m/s`, `|steeringRateDeg| < 20`, `|sa| > 2°`.

---

## 1. The curve

| \|sa\| | n (s) | routes | sR | 95 % CI | spread | n_ep | longest | lag sweep |
|---|---|---|---|---|---|---|---|---|
| 2–5 | 5078 | 75 | 17.69 | 17.59–17.79 | **1.55** | 2004 | 7.02 s | stat +30 ms |
| 5–10 | 2934 | 75 | 17.37 | 17.30–17.43 | **0.55** | 1145 | 13.88 s | stat +60 ms |
| 10–20 | 1184 | 74 | 16.99 | 16.92–17.06 | **0.25** | 503 | 8.20 s | stat +90 ms |
| 20–28 | 458 | 72 | **16.89** | 16.83–16.95 | 0.10 | 164 | 10.66 s | stat +150 ms |
| 28–36 | 195 | 68 | **16.91** | 16.84–16.97 | 0.09 | 61 | 4.32 s | edge |
| 36–45 | 109 | 64 | 16.73 | 16.62–16.84 | 0.08 | 23 | 1.93 s | **MONO — DROPPED** |
| 45–55 | 120 | 65 | 16.45 | 16.31–16.57 | 0.08 | 31 | 2.85 s | **MONO — DROPPED** |
| 55–70 | 274 | 66 | **16.26** | 16.17–16.33 | 0.06 | 101 | 5.39 s | stat +210 ms |
| 70–85 | 77 | 60 | **15.97** | 15.91–16.03 | 0.02 | 19 | 2.13 s | stat +120 ms |
| 85–105 | 69 | 57 | **15.46** | 15.38–15.55 | 0.02 | 26 | 2.10 s | edge |
| 105–130 | 68 | 55 | **15.02** | 14.95–15.08 | 0.01 | 24 | 1.54 s | stat +150 ms |
| 130–165 | 104 | 60 | **14.67** | 14.63–14.70 | 0.01 | 33 | 1.73 s | stat +120 ms |
| 165–210 | 59 | 60 | **14.45** | 14.42–14.49 | 0.01 | 19 | 1.46 s | stat +120 ms |
| 210–270 | 29 | 38 | **14.09** | 14.03–14.17 | 0.01 | 11 | 1.96 s | stat +60 ms |
| 270–400 | 2 | — | — | — | — | — | — | **no data** |

`spread` = the three-estimator bracket (TLS-through-origin, OLS y\|x, 1/OLS x\|y). Rows above 20° use
a **fixed-effects fit: per-route free intercept, one common slope.**

🛑 **The 2–20° rows carry no verdict.** Bracket width 1.55/0.55/0.25, denominator SNR 2.5 at 2–5°,
per-route dispersion sd 0.69 (range 14.50–17.40 over 59 routes). Every split that disagreed anywhere
— driver torque (16.00 vs 16.56), engaged vs hands-on manual (16.34 vs 19.70), firmware arm
(15.77 → 17.01), free-offset guard (+1.30) — **disagreed only below ~20°.** Above 90° all four agree
inside CI.

⭐ **The one-line statement of the whole problem:**
**the offset is identified at low angle, the slope is identified at high angle, and neither is
identified at both.**

---

## 2. The shape statistic — the headline, and the number a reshape consumes

**`sR(20–45°) − sR(130–165°) = 2.16`, 95 % CI **[2.09, 2.22]**, systematic **±0.12**.**
One joint regression over both bins with shared per-route intercepts — *not* a difference of two
independently-quoted rows. Method spread behind the ±0.12:

| variant | lo | hi | shape |
|---|---|---|---|
| all frames | 16.82 | 14.66 | 2.158 |
| wind-in | 17.51 | 14.74 | 2.772 |
| wind-out | 16.12 | 14.56 | 1.564 |
| wind-in/out **midpoint** | | | **2.168** |
| steady episodes | 16.71 | 14.63 | 2.081 |
| τ = +150 ms | 16.64 | 14.62 | 2.016 |

**The fork map fell 16.33 → 15.18 = 1.15 over the same span — 53 % of the true rate.**

🛑 **Quote the SHAPE, not the level.** Bands are **shape ±0.12, level ±0.57**. The level term is the
4 % gyro-vs-wheel-speed yaw-scale disagreement, which **asymptotes flat at ~0.96 from 50° up** and is
therefore multiplicative and constant: 4 % of 16.1 minus 4 % of 14.6 is 0.06 on a 2.16-unit
difference. It moves both ends together and cancels in the shape.

---

## 3. Served minus measured — the sign flips at ~50°

| \|sa\| | measured | served | Δ | % | verdict |
|---|---|---|---|---|---|
| 20–28 | 16.89 | 16.33 | −0.556 | −3.3 % | **map TOO LOW** |
| 28–36 | 16.91 | 16.33 | −0.581 | −3.4 % | **map TOO LOW** |
| 55–70 | 16.26 | 16.31 | +0.057 | +0.4 % | within band |
| 70–85 | 15.97 | 16.16 | +0.185 | +1.2 % | too high |
| 85–105 | 15.46 | 15.54 | +0.084 | +0.5 % | marginal |
| 105–130 | 15.02 | 15.35 | +0.324 | +2.2 % | too high |
| 130–165 | 14.67 | 15.18 | +0.514 | +3.5 % | too high |
| 165–210 | 14.45 | 15.07 | **+0.622** | **+4.3 %** | worst |
| 210–270 | 14.09 | 14.41 | +0.316 | +2.2 % | too high |

A served ratio that is **too high** makes `calc_curvature` **under-read**, which the loop answers by
**over-delivering** — the operator's oversteer on roundabouts and 90°+ corners, absent on the
motorway because the sign flips at ~50°.

**Neither place sR enters produces an error the controller can see.** It sits in the measurement
path, and on this fork the rate-plant feedforward builds `angle_des` through it as well. The
integrator drives the biased error to zero, so the loop converges perfectly onto the wrong road
curvature while `pid_log.error` reads 0.

---

## 4. Four attacks, and what each killed

**(a) Transit / lag bias — RETIRED, by the tests its own author specified.**
The large-angle samples are transits, not dwells, and a lag between steer and yaw biases a slope.
- *rate → 0 regression*: slope per 10 °/s = −0.080 / −0.056 / −0.031 / −0.014 / **+0.011** / −0.013
  across 20-45 / 45-70 / 70-100 / 100-130 / 130-165 / 165-250. **Largest at LOW angle, vanishing at
  high angle — the opposite of what the objection predicts.** Rate-0 intercepts sit on the raw values.
  🛑 The slope is **not** consistent across bins, so it is an angle-dependent effect, not one lag
  bias — **do not publish a corpus-wide corrected curve from it.**
- *wind-in vs wind-out*: split = 1.384 / 0.671 / 0.283 / 0.298 / 0.193 / 0.162, shrinking
  monotonically with angle, and the **midpoint equals the raw value to ≤0.02 in every band** — the
  bias is symmetric and cancels in the pooled fit. T2 and T4 agree in all six bands.
- *one-sided lag sweep* τ ∈ [0, +250 ms] (negative shifts are physically inadmissible): variation
  **0.21 / 0.17 / 0.09 / 0.04 / 0.03 / 0.07** — **plateau in every band** against a pre-registered
  0.30 pass / 0.80 fail threshold, argmin interior, drifting 220 → 100 ms as angle rises.

**(b) Tyre-stiffness degeneracy — REAL, and defeated by a fixed-speed control.**
`cfac·L` is 0.78–0.86 at 2–5° but **0.979–0.984 at 120–400°**, so stiffness carries 15–22 % of the
near-centre number and **2 %** of the far one. Scaling the `carParams` stiffnesses by k ≈ 0.5 — inside
openpilot's own valid band [0.2, 5.0] — flattens the binned table almost completely. **From the
binned table alone, "the rack quickens" and "the book stiffness is half wrong" are degenerate.**
What defeats it: re-running the entire sweep **inside v 4–9 m/s alone**, where `sf·v²` has no
leverage, agrees with the all-speed curve to **≤0.02 above 70°**. With the purely kinematic factor
instead, the columns explode (16.8 → 27.4 across speed) — the slip term is real and is doing its job.

**(c) `paramsd` circularity — not the defect, but it pointed at one.**
Free-intercept minus `angleOffsetDeg` = **+0.006° (sd 0.232)** across 67 routes at 2–10°. The learner
was not injecting a ratio error. 🛑 **The real defect was ours:** pooling all routes into *one* free
intercept, when routes have different true offsets, cost **+2.8 sR units at 2–10°** (pooled 20.22 vs
per-route 17.46) and 0.10 at 90–400°. Replaced by the fixed-effects fit.

**(d) Gyro / calibration chain — exonerated, and it strengthens the finding.**
An IMU-free yaw rate from raw CAN `0x1D0` wheel speeds (verified: `v_ws/vEgo` median 0.9991, corr
0.99999) moves the high-angle ratio **lower**, not higher (r39 14.50 → 14.07). Below 5° it is pure
quantiser noise (corr 0.41–0.51) and cannot arbitrate the near-centre end at all.

---

## 5. ⭐ The counter-intuitive one: long dwells make the fit WORSE

Restricting the high-angle bins to episodes longer than 1 s reads **13.46 and 12.96** — over a unit
below everything else, which would have widened the band to ±0.7.

**Those fits are not identified.** Three-estimator spread **3.92** at 130–165° (8 routes, 11.5 s) and
**8.62** at 100–130° (11 routes); they needed the sample floor dropped to 0.6 s to run at all. Guard
run on the per-route signed differences: **6 of 8 below their own all-frames value, two-sided sign
test p = 0.289** — scattered, not one-sided; sd 16.04, and **one route returns a negative steering
ratio**. At 105–130° it is 6 of 11, p = 1.000. The *identified* episode subset (22 routes, spread
0.03) reads **14.70 at 130–165 against 14.67 all-frames** — agreement.

**Mechanism:** a >3 s episode at high angle is by construction low-speed and near-constant-curvature,
so `denom` has almost no variance inside the subset. A slope-through-origin needs spread in x; with x
near-constant plus noise it degenerates to a ratio-of-means and the three estimators fly apart.
**Long dwells make the physics cleaner and the fit worse.** This is why the planned manoeuvre
(`docs/guides/DRIVE-CARD-STEER-RATIO-2026-09-11.md`) sweeps a *range* of locks rather than holding one.

Excluded under the same pre-specified identifiability rule (spread < 0.15 and ≥ 20 routes) that
condemned the small-angle end — 1.81 cannot be discarded as unidentified while 8.62 is treated as a
warning.

---

## 6. What shipped, and what stays frozen

```python
HONDA_ACCORD_STEER_RATIO_ANGLE_BP  = [0.0, 23.0, 31.0, 61.0, 76.0, 95.0, 116.0, 151.0,
                                      178.0, 227.0, 236.0, 303.0, 380.0]
HONDA_ACCORD_STEER_RATIO_V         = [16.89, 16.89, 16.89, 16.26, 15.97, 15.46, 15.02, 14.67,
                                      14.45, 14.09, 14.25, 12.98, 12.31]
HONDA_ACCORD_STEER_RATIO_NOMINAL   = 16.89   # was 16.00
HONDA_ACCORD_STEER_RATIO_LEVEL_MIN = 0.60    # toggle 10.13
HONDA_ACCORD_STEER_RATIO_LEVEL_MAX = 1.25    # toggle 21.11
# SteerRatio toggle -> 16.89
```

Values are **absolute served ratios** (`V[0] == NOMINAL`), so the array reads as real ratios and the
toggle means exactly "the on-centre ratio" at scale 1.0000.

🛑 **Three segments are conventions, not measurements.** Marked in the source and in the tests:
- **0–23°** pinned — the not-identified region of §1.
- **31–61°** interpolated across the 36-45 and 45-55 bins, which failed the lag-plateau test.
- **236°+** FROZEN at what the old map served (13.96/12.72/12.06 × 16.33/16.00), **verified unchanged
  to ≤0.002 at 236/260/303/340/380/450**. 1306 s of data exists above 303° but its median speed is
  **1.41 m/s** — parking — and 0.1 s survives `v > 4`. The estimator divides yaw by speed, so that
  end is structurally out of reach. The **227 → 236 step (14.09 → 14.25, +0.16) is deliberate**;
  smoothing it would mean silently editing a frozen knot.

🛑 **Truncating the array at 227 would have been a safety defect**, not a tidy-up: `np.interp` holds
its end value, so the map would serve a flat 14.09 to full lock instead of falling to 12.31 — **+1.8
units at lock, in the one region proven unmeasurable.**

⚠ **This is a COMPENSATION curve, not physical rack geometry.** `calc_curvature` uses κ = δ/L rather
than tan(δ)/L, so a *perfectly constant* rack would read 1.4 % low at 200° and 3.3 % at 300°. It is
excluded from the band because it cancels against the consumer — the map feeds the same function —
but do not cite these numbers as the rack's true ratio.

---

## 7. Retraction ledger

| claimed | status |
|---|---|
| rack reads 17.14 near centre ⇒ map under-delivers ~5 % on straights | **RETRACTED** — below 20° is not identified (§1) |
| map over-states the ratio everywhere past 45° | **SUPERSEDED** — the sign flips at ~50° once the intercept is freed (§3) |
| the fall is ~1.5 units, band ±0.45 | **BOTH WRONG** — 2.16 [2.09, 2.22], band ±0.12 (§2) |
| r64/r65 are the densest large-angle routes in the corpus | **RETRACTED** — 213.5 s past 45° gates down to **27 s**; median speed there is 2.95 m/s, one 0.87 s episode past 100°, **0.0 s** in the 250-400 bin |
| five routes agreeing at 16.67–16.98 identifies the near-centre level | **RETRACTED** — five routes sharing one noise-regime bias; **0 of 67 routes** have spread < 0.30 there |
| `liveParameters.steerRatio` gives the served ratio per route | **WRONG** — it is published *upstream* of the Accord map, which `controlsd` overwrites by direct assignment; it reads 12.500 on r39 while the map is what ran |
| block-bootstrap CIs on the first curve | **NOT INTERVALS** — `tls_ci` computed `nb = max(len(x)//blk, 2)`, resampling 2 blocks from 2 on a short bin and printing zero width |

---

## 8. What is still not measured

- **Below ~20°** — structurally, not for want of data (9196 s there). Needs a different estimator, not
  more driving.
- **270–400°** — 2 s gated. Only reachable by driving large lock *above 4 m/s*, which ordinary driving
  never does.
- **Multi-second dwells above 120°** — longest in 14.2 h is 1.78 s.

The last two are what `docs/guides/DRIVE-CARD-STEER-RATIO-2026-09-11.md` is for: ~15 min, manual,
matched ramps plus constant-lock circles at 90/135/180/270/360°. **BELIEF:** two laps at 180° gives
36 s of continuous dwell. Slip is not an obstacle — at 180° lock and 5 m/s the understeer correction
is 1.8 % and is *modelled*, so a constant-lock circle is the clean case, not a compromised one.
