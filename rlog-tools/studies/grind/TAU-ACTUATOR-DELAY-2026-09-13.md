# The LKAS actuator delay τ, measured — 2026-09-13

Subagent **taumeasure**. Analysis only: nothing was built, nothing was sent on any bus, nothing was
flashed, nothing was committed.

**Question.** The outer-loop stability verdict on the V293 torque-mode candidate hinges on τ. The fork's
`liveDelay.lateralDelay` reads `0.2000` flat, but that is the operator's `SteerDelay` toggle echoed
(`UseAutoSteerDelay = 0`), not an identification. The Honda port's prior is `steerActuatorDelay = 0.1`.
The adversary's thresholds: **pass at τ ≤ 0.20 s with margin** (repaired preset), **FAIL at τ ≥ 0.18 s**
(unrepaired preset), **unstable at τ = 0.30 s**.

---

## 0. Headline

1. **τ is not 0.10 s and not 0.20 s. On the current tune it is 0.15–0.21 s at motorway speed and
   0.23–0.26 s at 3–8 m/s**, measured on the channel the openpilot torque controller itself closes on.
   The path-following (yaw) channel is another 50–100 ms slower.
2. **τ rises steeply as speed falls** — the total is robust across estimators. ⚠ **The SPLIT between
   pure dead time and servo lag is NOT well identified**: the two parameters trade off in the fit, and
   they split differently on the two tunes (r39 puts the speed dependence in dead time, r6c puts it in
   the lag pole) while the totals agree. Quote the total, not the split.
3. **V292 did not change τ.** At matched tune, V282 (r6c) and V292 (r6d/e/f) agree inside the scatter of
   the three V292 routes themselves. **The lateral TUNE did change it**: the current SR 16.8 /
   LatAccel 6.0 tune is **20–55 ms slower** than the SR 12.5 tune r39 and r35 flew (20–45 ms by
   correlation peak, up to 55 ms by phase at 1 Hz). At 25+ m/s the bootstrap intervals do not overlap:
   r39 152 ms [148–154] against r6c 182 ms [175–191].
4. **The fork's `lateralDelayEstimate = 0.2479` is ~99 % a value inherited from earlier routes**, is
   gated at ≥ 15 m/s, and reads a yaw channel that lags the raw gyro by 73–90 ms. It is not an
   identification of the current configuration and should not be used as one.
5. **A single lumped τ is under-specified** — the correlation peak, the phase slope and the phase at
   1 Hz disagree by up to 100 ms on the same data because the path is not a pure delay. §4.3 gives
   **equivalent delay versus frequency**; read the row at the outer loop's crossover.
6. **No rate or torque limiting.** τ *falls* and gain *rises* with demand amplitude, so a fixed-τ linear
   margin is not invalidated by saturation. But the small-signal regime is the slow one (30–50 ms
   slower), and that is where a marginal loop first goes unstable.
7. **The brief's premise about the servo pole is off by a decade**: the fitted lag pole is 1.4–4.3 Hz,
   not 10–16 Hz, so the servo contributes 60–90 ms at 1 Hz, not ~12 ms. The dominant lag is the torque
   controller's own tracking bandwidth plus the steering plant, not the EPS rate servo.

---

## 1. Why the obvious measurement — 0xE4 command vs 0x18F rate — does not work [EVIDENCE]

Script: `tau_actuator_delay.py`, output `_scratch/tau_actuator_delay.txt`.

The brief asked for a cross-correlation of the 0xE4 command against the 0x18F steering rate. That was
run first, on 705 s of engaged hands-off r39 (V282), band-passed 0.2–2 Hz. It returns:

| quantity | value |
|---|---|
| cross-correlation peak lag | **−31 to −66 ms** (NEGATIVE: the wheel LEADS the command) |
| correlation at that peak | **r = +0.89 to +0.97** |
| first-order-plus-dead-time fit | **dead time 0 ms, servo lag 0 ms**, R² 0.79–0.91 |
| two-sided FIR mass at anticausal lags | 21–42 % |

A static gain of 0.018–0.024 deg/s per count explains 80–90 % of the variance with no lag at all.

**Reading.** The lead is about one openpilot round trip — this kit measured 21–26 ms for that in
`OUTER-LOOP-ID-2026-09-10` §5. The fork runs `AccordRatePlantFF` ON with `SteerLatAccel` 6.0 cutting
P/I torque authority ~2.5× (`project-starpilot-fork-lateral-state-2026-09-10`), so **the 0xE4 command is
largely an algebraic feedforward function of the rate the car is already doing.** The plant arm is buried
under the controller's own feedforward.

🛑 **A cmd→rate lag on this car is not a transport delay and must not be quoted as τ.**

What that pass *did* establish, and it is sound — coherence 0.93–0.98 over 0.2–1.5 Hz on every long
stretch (`tau_struct.py`):

- `cmd → rate` is a **GAIN** (|H| flat at 0.012–0.024 deg/s per count)
- `cmd → angle` is an **INTEGRATOR** (|H| ∝ 1/f, phase ≈ −90°)

so the EPS does close a rate loop on the command, consistent with the record.

---

## 2. What was measured instead, and why it is closed-loop-consistent

Scripts: `tau_extract_lat.py` (extraction), `tau_identify.py` (identification).

**Input, exogenous.** `controlsState.desiredCurvature` — verified identical to
`carControl.actuators.curvature` (slope 1.0000, corr 1.0000). It is the plan: it comes from the camera
and the road, not from the steering wheel. Its feedback path to the wheel (steer → lane position →
camera → model) is slow and double-integrating, so over 0.2–2 Hz it is dominated by road geometry.
This is tested below, not assumed.

**The planner's own lookahead cancels.** The controller commands `c_plan(t + τ_assumed)` and the car
realises it at `t + τ_true`, so the measured command→response lag is `τ_true` for any `τ_assumed`. The
operator's `SteerDelay = 0.2` therefore does not bias this measurement. [EVIDENCE: algebraic.]

**Two response channels, and they bracket the answer** [EVIDENCE, verified on r39]:

| channel | what it is | what its lag contains |
|---|---|---|
| `y_steer` | `carControl.currentCurvature` — curvature from the **steering angle** through the vehicle model. `controlsState…torqueState.actualLateralAccel` == `y_steer · v²` to slope 0.9999 / corr 1.0000, so this is the "actual" **the torque controller itself closes on** | the **EPS actuator** delay alone |
| `y_yaw` | the **raw gyro** (x-axis negated: slope −1.0046, corr −0.9965 against the calibrated yaw rate), 87.8 Hz, divided by vEgo | the **full lateral** delay — EPS actuator plus the vehicle's own yaw response |
| `y_pose` | `carControl.angularVelocity[2]` / v, the calibrated livePose yaw as controlsd held it — **lagd's own channel** | full lateral **plus the livePose estimator's lag** |

⇒ **Which τ applies to which loop.** The openpilot lateral *controller* loop closes on the
steering-angle channel (its own `actualLateralAccel` is steering-angle-derived), so **τ_EPS is the τ for
the controller loop**. The *path-following* loop closes through the vehicle's yaw, and it is what the
planner's lookahead (`steerActuatorDelay` / `lateralDelay`) must anticipate, so **τ_full is the τ for the
path loop.**

**Estimators** (all on the same stretches, so they are comparable):

| tag | method | bias direction |
|---|---|---|
| **NCC** | openpilot lagd's own masked normalised cross-correlation, mirrored verbatim in arithmetic, ROI 0…+650 ms, parabolic peak | the canonical number; directly comparable to the fork's own |
| **2-sided** | the same correlation read over −300…+650 ms. **Its job is to FAIL**: a negative peak means closed-loop contamination, exactly as the 0xE4 pair shows | — |
| **GD** | coherence-weighted slope of the unwrapped phase over 0.2–2 Hz, τ = −slope/360 | the delay that reproduces the measured **phase where the outer loop crosses over**; contains the servo lag |
| **FOPDT** | output-error fit of `y = K/(1+sT)·u(t−dead)`, grid on (dead, T), least squares on K | **splits pure dead time from servo lag** |
| **CI** | block bootstrap over whole stretches, 2.5/97.5 percentile | — |

**Masking.** `latActive` AND not `steeringPressed` AND not `saturated`, with a 2 s recovery buffer after
any of those going bad — lagd's own gate. Stretches ≥ 12 s. Speed bands 0–3, 3–8, 8–15, 15–25, 25+ m/s.

---

## 3. Validation — the checks that could have failed [EVIDENCE]

| check | result | verdict |
|---|---|---|
| **Zero-lag control**: a pair with a lag of exactly 0 by construction | returns **0.0 ms** on every route and band | PASS |
| **Known-lag control**: the same command delayed by exactly 200 ms | returns **200.2 – 203.0 ms** | PASS — the method recovers a known lag to ≤ 3 ms |
| **Closed-loop contamination**: two-sided ROI on the curvature pair | peak **identical** to the one-sided peak on every band and route — no anticausal mass | PASS — this pair is not feedback-driven, unlike the 0xE4 pair |
| **Response-channel instrument lag**: is `currentCurvature` a filtered version of the angle? | `steeringAngleDeg → currentCurvature` = **−1.9 ms**, r 0.9913; `0x14A CAN angle → carState.steeringAngleDeg` = **+2.5 ms**, r 1.0000 | PASS — response channel adds ≤ ~3 ms; τ is not inflated by the instrument |
| **Polarity**, asserted not assumed | `d(ang)/dt = +1.00 · rate_x`, slope 0.994–1.017, corr 0.987–0.994 on all six routes | PASS — CPD = 8.0 and the sign are both right |
| **Cross-method agreement** on the EPS channel | NCC, GD and the FOPDT 1 Hz phase-equivalent agree within ~10–20 ms wherever coherence ≥ 0.85 | PASS |

**Known residual biases, stated:**

- The GD estimator is unreliable on the **yaw** channels (coherence at 1 Hz falls to 0.23–0.32 in some
  bands and the phase unwrap breaks). Where coherence < 0.7, the GD column is not used. The NCC and
  FOPDT columns are unaffected.
- `y_pose` carries the livePose estimator's lag; measured **+73 to +90 ms** above the raw gyro on the
  same stretches. **lagd's own number is inflated by that much.**
- Below ~3 m/s, curvature = yaw/v is numerically ill-conditioned and the correlations collapse
  (r ≈ 0.43). The 0–3 m/s rows are reported but **not usable**.

---

## 4. Results

### 4.1 The exposure, and what it can and cannot answer

Engaged, hands-off, non-saturated, in stretches ≥ 12 s, seconds per cell:

| route | build | tune | 0–3 | 3–8 | 8–15 | 15–25 | 25+ |
|---|---|---|---|---|---|---|---|
| r35 | V281r3 | SR 12.5 / LatAccel 2.11 / friction 0.03 | 0 | 0 | 143 | 116 | 81 |
| r39 | V282 | SR 12.5 / 2.11 / 0.03 | 0 | **17** | 126 | 107 | 48 |
| r6c | V282 | SR 16.84 / 6.0 / 0.01 | 58 | **113** | 256 | 441 | 1447 |
| r6d | V292 | SR 16.88 / 6.0 / 0.01 | 0 | 0 | 19 | 18 | 337 |
| r6e | V292 | SR 16.88 / 6.0 / 0.01 | 13 | 0 | 23 | 135 | 31 |
| r6f | V292 | SR 16.88 / 6.0 / 0.01 | 0 | **27** | 16 | 135 | 85 |

🛑 **Two confounds the reader must hold.** (a) r35/r39 ran a *different lateral tune* from r6c and the
three V292 routes. So **r39 vs r6c is a TUNE contrast at constant firmware**, and **r6c vs r6d/e/f is a
FIRMWARE contrast at constant tune** — the latter is the one that answers "did V292 change τ". (b) The
3–8 m/s cell has 130 s of V282 but only **27 s of V292**, on one route. The 3–8 m/s number is
well-determined for V282 and thin for V292.

### 4.2 τ by build and speed — correlation-peak lag, band 0.2–2 Hz

**EPS actuator channel** (the loop the torque controller closes; its own `actualLateralAccel` is this
signal). NCC peak lag in ms, 95 % block-bootstrap CI where the cell has ≥ 3 stretches:

| route | build | 3–8 | 8–15 | 15–25 | 25+ |
|---|---|---|---|---|---|
| r39 | V282 (old tune) | **260** ‡ | 224 [200–253] | 171 [160–201] | 152 [148–154] |
| r35 | V281r3 (old tune) | — | 203 [183–227] | 181 [169–194] | 158 ‡ |
| r6c | V282 (current tune) | **258 [251–264]** | 232 [219–247] | 211 [197–231] | 182 [175–191] |
| r6d | V292 | — | 260 ‡ | 252 ‡ | 170 [144–181] |
| r6e | V292 | — | 246 ‡ | 221 [207–233] | 199 [197–203] |
| r6f | V292 | **248** ‡ | 254 ‡ | 206 [197–215] | 195 ‡ |

‡ = fewer than 3 stretches, so the block bootstrap is degenerate and **no CI is quoted**. r6f's 3–8 cell
in particular has only 2 stretches (27 s); its bootstrap returns [248, 248], which is an artefact of
resampling 2 items, **not** a tight interval. Its coherence (0.99) and correlation (0.977) are the best
in the study, but it is still 27 s.

**Full lateral channel** (raw gyro yaw / v — the path-following loop, and what the planner's lookahead
must anticipate):

| route | build | 3–8 | 8–15 | 15–25 | 25+ |
|---|---|---|---|---|---|
| r39 | V282 (old tune) | **333** | 276 | 228 | 191 |
| r6c | V282 (current tune) | **285** | 278 | 236 | 199 |
| r6d | V292 | — | 342 | 328 | 202 |
| r6e | V292 | — | 302 | 287 | 251 |
| r6f | V292 | **268** | 281 | 251 | 182 |

### 4.3 ⭐ The deliverable the outer-loop model actually needs — equivalent delay vs frequency

A single lumped τ is **under-specified**, because the path is not a pure delay: on r6c at 25+ m/s the
correlation peak, the phase-slope group delay and the phase at 1 Hz read **182, 288 and 210 ms**. Which
is right depends on **where the outer loop crosses over**. So the honest deliverable is

> **τ_eq(f) = −phase(f) / (360·f)** — the pure delay that reproduces the *measured* phase at frequency f.

**Read the row at your crossover.** EPS actuator channel, ms (coherence ≥ 0.7 in every cell shown;
the 0.2 Hz column is noisy because a small phase is divided by a small f, and ≥ 1.5 Hz loses coherence —
**0.3–1.0 Hz is the usable range**):

| route | build | band | 0.3 Hz | 0.4 Hz | 0.5 Hz | 0.7 Hz | 1.0 Hz |
|---|---|---|---|---|---|---|---|
| r6c | V282 | 3–8 | 248 | 230 | 240 | 252 | **242** |
| r6c | V282 | 8–15 | 177 | 174 | 201 | 221 | 235 |
| r6c | V282 | 15–25 | 147 | 151 | 187 | 224 | 239 |
| r6c | V282 | 25+ | 90 | 123 | 153 | 186 | 210 |
| r6f | V292 | 3–8 | 196 | 189 | 225 | 243 | **246** |
| r6d | V292 | 8–15 | 278 | 256 | 238 | 218 | 244 |
| r6e | V292 | 15–25 | 165 | 169 | 205 | 215 | 215 |
| r6f | V292 | 15–25 | 167 | 164 | 179 | 204 | 220 |
| r6d | V292 | 25+ | 80 | 91 | 139 | 186 | 201 |
| r6f | V292 | 25+ | 67 | 148 | 177 | 200 | 210 |
| r39 | V282 old tune | 3–8 | 219 | 267 | 212 | 251 | 285 |
| r39 | V282 old tune | 25+ | 198 | 148 | 129 | 126 | 155 |

**τ_eq rises with frequency in every cell.** That is the first-order lag showing on top of the dead time,
and it means a loop that crosses over higher pays more delay than one that crosses lower.

Full-lateral (path-loop) channel adds roughly **50–100 ms** over the EPS channel at 0.3–0.7 Hz, and is
not usable above ~1 Hz (the yaw response rolls off and the phase wraps).

### 4.4 Pure dead time vs servo lag — and a correction to the brief's premise

FOPDT output-error fit, EPS actuator channel:

| route | band | pure dead time | servo lag T | implied pole | 1 Hz phase-equivalent | R² |
|---|---|---|---|---|---|---|
| r39 | 3–8 | 180 ms | 110 ms | 1.4 Hz | 276 ms | 0.985 |
| r39 | 8–15 | 120 ms | 110 ms | 1.4 Hz | 216 ms | 0.933 |
| r39 | 15–25 | 80 ms | 94 ms | 1.7 Hz | 165 ms | 0.968 |
| r39 | 25+ | 80 ms | 81 ms | 2.0 Hz | 155 ms | 0.953 |
| r6c | 3–8 | 180 ms | 94 ms | 1.7 Hz | 265 ms | 0.875 |
| r6c | 8–15 | 160 ms | 81 ms | 2.0 Hz | 235 ms | 0.929 |
| r6c | 15–25 | 180 ms | 37 ms | 4.3 Hz | 217 ms | 0.935 |
| r6c | 25+ | 180 ms | 5 ms | — | 185 ms | 0.933 |

🛑 **The brief's premise that "the rate servo's own bandwidth ~10–16 Hz contributes a small lag" is
right about the size and wrong about the source.** The fitted lag pole is **1.4–4.3 Hz**, not 10–16 Hz.
A 13 Hz pole would contribute only ≈ **12 ms** of equivalent delay at 1 Hz; the pole actually measured
contributes **60–90 ms**. **The dominant lag is not the EPS rate servo** — it is the torque controller's
own closed-loop tracking bandwidth plus the steering plant.

⚠ **But do not quote the dead/lag SPLIT as if it were identified.** Dead time and lag pole trade off
against each other in a FOPDT fit, and the two tunes split the same total differently: r39 puts the speed
dependence in the **dead time** (80 → 180 ms while T stays 81–110 ms), r6c puts it in the **lag pole**
(dead flat at 160–180 ms while T goes 5 → 94 ms). **The totals agree and rise as speed falls
(155 → 276 ms on r39, 185 → 265 ms on r6c); the decomposition does not survive the tune change.** Use
the total, or better, the frequency table in §4.3.

### 4.5 Did V292 change τ? No. [EVIDENCE — null]

At **matched tune** (r6c = V282 vs r6d/r6e/r6f = V292, all SR 16.84–16.88 / LatAccel 6.0 / friction 0.01),
τ_eq at 1 Hz on the EPS channel:

| band | V282 (r6c) | V292 (r6d / r6e / r6f) |
|---|---|---|
| 3–8 | 242 | 246 (r6f) |
| 8–15 | 235 | 244 / 254 / 234 |
| 15–25 | 239 | 270 / 215 / 220 |
| 25+ | 210 | 201 / 218 / 210 |

**Differences are within the cell-to-cell scatter of the three V292 routes themselves.** The firmware
change did not move the actuator delay.

**The TUNE did.** r39/r35 (SR 12.5, LatAccel 2.11) against r6c (SR 16.84, LatAccel 6.0), both V282:

| estimator | band | old tune (r39 / r35) | current tune (r6c) |
|---|---|---|---|
| NCC peak | 25+ | **152 [148–154]** / 158 | **182 [175–191]** |
| NCC peak | 15–25 | 171 [160–201] / 181 [169–194] | 211 [197–231] |
| τ_eq at 1 Hz | 25+ | 155 / 157 | 210 |
| τ_eq at 1 Hz | 15–25 | 181 / 177 | 239 |

**The current tune is 20–55 ms slower than the tune r39 and r35 flew**, and at 25+ m/s the bootstrap
intervals do not overlap. Consistent with `SteerLatAccel` 6.0 cutting P/I torque authority ~2.5×.

### 4.6 The fork's own estimator — what `0.2479` actually is [EVIDENCE]

Audit of `selfdrive/locationd/lagd.py` (StarPilot @ Dom `a357cd2b5`) plus a census of `liveDelay` on all
six routes:

| route | applied `lateralDelay` | `lateralDelayEstimate` | distinct values over the route | std | validBlocks |
|---|---|---|---|---|---|
| r35 | 0.2 | 0.2267–0.2329 | 3 | ≤ 0.025 | 16 |
| r39 | 0.2 | **0.2272, frozen for all 948 s** | **1** | 0 | 16 |
| r6c | 0.2 | 0.2449–0.2515 | 33 | ≤ 0.030 | 50 |
| r6d | 0.2 | 0.2479–0.2495 | 5 | ≤ 0.011 | 50 |
| r6e | 0.2 | 0.2495–0.2521 | 3 | ≤ 0.019 | 50 |
| r6f | 0.2 | 0.2521–0.2537 | 3 | ≤ 0.011 | 50 |

- `lateralDelay = 0.2000` on every route — **the echoed `SteerDelay` toggle**, confirmed
  (`lagd.py:236-237`, `use_custom_steerActuatorDelay` branch). The brief was right.
- `lateralDelayEstimate` is a **real** identification (`lagd.py:244`) — but the block average is
  50 blocks × 100 updates, **all 50 seeded from the previous route's cached value**
  (`retrieve_initial_lag`, `BlockAverage.reset`). r6c's 33 distinct values mean ~32 accepted updates in
  3699 s, which moved the reported number by **0.0066**. It is **~99 % seed**. r39 and r35 produced
  essentially none at all.
  ⇒ **0.2479 is a very slow multi-drive average inherited across routes, not a measurement of the
  current configuration.**
- It is hard-gated at **`MIN_VEGO = 15.0 m/s`** (`lagd.py:25`), so it says **nothing about 3–8 m/s**.
- It reads the **livePose** yaw, which I measure to lag the raw gyro by **+73 to +90 ms** on identical
  stretches. **lagd's own number is inflated by that much.**

**Replaying lagd's own algorithm per speed band** (`tau_lagd_replicate.py`, every constant but MIN_VEGO
left at the fork's, no seed) shows **it structurally cannot produce a per-band number**: its 60 s window
needs 25 s of okay samples inside the band, which never survives speed-banding below 15 m/s. Of 205–728
windows per route, essentially all are rejected as "short". Where it does resolve (r6c ≥ 15 m/s) it
returns **0.310–0.329 s**, *above* the fork's own reported 0.245–0.2515 — again consistent with the
reported value being seed-dominated.

**A units mismatch inside the fork, worth reporting separately.** `full_lateral_delay(x) = x + 0.2`
(`starpilot/common/lateral_delay.py`), and `SteerDelay` defaults to that full value
(`starpilot_variables.py:815`). So the operator's **0.2 is a FULL lateral delay, implying a vehicle part
of 0.0**, against a stock Honda default of 0.1 vehicle / 0.3 full. But the toggle branch in `lagd.py`
assigns the raw toggle **without** the `full_lateral_delay` wrapper the fallback branch applies, so the
field carries two conventions depending on which branch wrote it.

### 4.7 Is τ amplitude-dependent? Yes — and it goes the *opposite* way to rate limiting [EVIDENCE]

The concern was that `SteerLatAccel` 6.0 cuts P/I torque authority ~2.5×, so a large demand might be
**rate- or torque-limited** rather than merely delayed — in which case a fixed-τ linear margin would be
optimistic exactly where the loop spends it. Limiting has a signature: **lag rises and gain falls with
amplitude.** Stretches were split into terciles by band-passed demand rms (`tau_amplitude.py`):

| route | band | LOW demand | MID | HIGH | demand range | \|H\| @1 Hz, LOW → HIGH |
|---|---|---|---|---|---|---|
| r6c | 8–15 | 267 ms | 236 | **219** | 2.8× | 0.65 → **1.03** |
| r6c | 25+ | 212 ms | 184 | **176** | 2.4× | 1.15 → **1.29** |
| r6c | 15–25 | 213 ms | 227 | 205 | 3.0× | 1.17 → 1.03 |
| r6c | 3–8 | 249 ms | — | 266 | 1.6× | 0.59 → 0.58 |
| r39 | 8–15 | 255 ms | — | **221** | 1.4× | 0.76 → 0.86 |
| r39 | 15–25 | 192 ms | — | **165** | 1.9× | 1.43 → 1.36 |
| r6f | 15–25 | 199 ms | — | 205 | 1.8× | 1.01 → 1.18 |

**Gain RISES and lag FALLS (or is flat) with amplitude.** That is not limiting — it is the opposite. The
mechanism is a **friction / deadband** nonlinearity: at small demand the wheel does not break away
cleanly, so the response is weak and late; at larger demand the system tracks better.

Consequences for the verdict:

- **A fixed-τ linear margin is not invalidated by saturation.** There is no evidence of rate or torque
  limiting in the amplitudes these routes visit.
- **But the small-signal regime is the slow one**, and that is where a marginal loop first goes unstable
  and where the operator's grinding and micro-ratcheting live. For a small-amplitude stability question,
  **use the LOW-demand row, which is 30–50 ms slower.**
- Partly offsetting: the small-signal **gain is also lower** (|H| 0.59–0.76 versus 1.0–1.4), which
  reduces loop gain and is stabilising. The two effects pull opposite ways and the net must be taken in
  the loop model, not asserted here.
- ⭐ **At low speed the loop is both slower and weaker.** Delivered gain |H| at 1 Hz, current tune:
  **r6c 3–8 m/s reads 0.57** (0.58–0.59 in both amplitude terciles, so it is not an amplitude effect)
  and r6f 3–8 reads 0.69, against **1.07–1.32 at 15–25 and 25+**. The wheel is realising roughly
  half to two-thirds of the commanded curvature at 3–8 m/s.

⚠ **The gain column is NOT comparable across the two tunes.** `carControl.currentCurvature` is computed
from the steering angle using the tune's own `SteerRatio`, so the SR 12.5 routes (r39, r35) report an
inflated "actual" — they read |H| 1.7–2.3 at motorway where the SR 16.8 routes read 1.1–1.3, and roughly
16.8/12.5 = 1.34 of that is the assumed ratio, not the car. **A constant scale factor does not move a
correlation peak or a phase, so every τ in this document is unaffected**; only the |H| comparison across
tunes is confounded. (The measured true ratio is ~16–17.6 — `accord-forks-variable-sr-map-is-too-flat-measured-2026-09-10`.)

### 4.8 Band sensitivity — does the 0.2–2 Hz choice do the work? No.

Same stretches, same estimator, four analysis bands (`tau_bandcheck.py`). Spread across bands:
**10–90 ms, median ~32 ms** on the EPS channel. Enough to matter at the margin, not enough to change any
verdict. The unfiltered lagd-style variant (DC left in) is erratic — 0.0 ms on two r35 cells, 525 ms on
r6c 3–8 — which is exactly why lagd must throw away most windows with its `corr ≥ 0.95` and
`confidence ≥ 0.7` gates.

---

## 5. Against the adversary's thresholds

The adversary's figures: **pass at τ ≤ 0.20 s with margin** (repaired preset), **FAIL at τ ≥ 0.18 s**
(unrepaired preset), **unstable at τ = 0.30 s**.

🛑 **First, a question that must be settled before those thresholds are applied: WHICH τ do they mean?**
Two different delays exist in this system and they differ by 50–100 ms:

- **τ_EPS** — command to steering-angle response. The openpilot lateral **controller** loop closes on
  exactly this signal (`actualLateralAccel` == steering-angle curvature × v², corr 1.0000), so if the
  adversary's model is the controller loop, this is the number.
- **τ_full** — command to **yaw** response. The **path-following** loop closes through this, and it is
  what `steerActuatorDelay` / `lateralDelay` feeds as the planner's lookahead.

**Where the measurements fall** (current tune; the range spans crossover 0.5–1.0 Hz, which is where the
outer loop is stated to cross):

| cell | τ_EPS (controller loop) | τ_full (path loop, 0.3–0.7 Hz) |
|---|---|---|
| 25+ m/s | **0.14 – 0.22 s** | 0.15 – 0.30 s |
| 15–25 m/s | **0.18 – 0.24 s** | 0.22 – 0.30 s |
| 8–15 m/s | **0.19 – 0.27 s** | 0.21 – 0.33 s |
| **3–8 m/s** | **0.23 – 0.25 s** | **0.20 – 0.34 s** |

(τ_EPS spans crossover 0.5–1.0 Hz across the four current-tune routes, dropping r6d's 18 s 15–25 cell.
The correlation-peak estimator gives 170–199 ms at 25+, 206–221 at 15–25, 246–260 at 8–15, 248–258 at
3–8, i.e. the same picture read a different way.)

Read against the stated thresholds:

- **τ ≤ 0.20 s (pass with margin).** Satisfied **only** on the controller-loop channel, **only** at
  ≥ 15 m/s, and **only** if the crossover is at or below ~0.6 Hz. **Not satisfied in the 3–8 m/s band on
  any channel at any usable frequency.**
- **τ ≥ 0.18 s (FAIL threshold for the unrepaired preset).** **Exceeded in every 3–8 m/s cell at every
  usable frequency**, and exceeded in most other cells once the crossover reaches 0.5 Hz. On the
  old SR 12.5 tune (r39, r35) the motorway cells sat at 0.13–0.18 s and would have cleared it; **on the
  current tune they do not.**
- **τ = 0.30 s (unstable).** Reached on the **path-loop** channel at 3–8 m/s (0.28–0.34 s on r6c) and
  approached at motorway on r6c (0.296 s at 0.5 Hz). **Not** reached on the controller-loop channel
  anywhere.

**What I am NOT saying.** I am not returning a stability verdict — that belongs to whoever owns the loop
model, who must first say which τ their threshold refers to and where their loop crosses over. What I am
saying is that **the value the fork is flying (`SteerDelay` 0.2, and a stale `lateralDelayEstimate` of
0.248) is not the measured delay of the current configuration, and the measured delay is above 0.18 s in
every low-speed cell.**

### 5.1 The weakest parts of this, stated plainly

- **The 3–8 m/s cell is V282-dominated.** 130 s of V282 (r6c 113 s + r39 17 s) against **27 s of V292**
  on one route (r6f). The V282 number is well-determined (CI 251–264 ms); the V292 number at that speed
  rests on 27 s, though its coherence is the best in the whole study (0.95–0.99).
- **The tune confound is real and only partly separable.** r35/r39 flew a different lateral tune from
  every other route, so "old tune" and "V281r3/V282-on-r39" are not independent. The firmware null in
  §4.5 is clean because r6c and r6d/e/f share a tune; the tune contrast in §4.5 is clean because r39 and
  r6c share a firmware. No cell separates both at once.
- **The three estimators disagree by up to ~100 ms** on the same data (§4.3). This is not estimator
  error — it is the path not being a pure delay — but it does mean any single quoted τ carries that
  ambiguity unless the crossover frequency is named.
- **GD is unreliable wherever coherence at 1 Hz falls below ~0.7**, which happens on the yaw channels in
  several bands. Those cells rest on NCC and FOPDT only.
- **0–3 m/s is not measurable** by this method: curvature = yaw/v is ill-conditioned and the
  correlations collapse to r ≈ 0.43–0.59. Those rows are printed but must not be used.
- **Nothing here is a null from the wrong image**: these are all flight data, per route, per build, with
  the build attributed from the route's own `initData` params and commit, not from a label.

---

## 6. Files

| file | what |
|---|---|
| `tau_orient.py` | polarity and scale sanity, hands-off definition, exposure census |
| `tau_struct.py` | is cmd→rate a gain or a differentiator (decides whether a lag is meaningful) |
| `tau_actuator_delay.py` | the 0xE4-wire attempt, and the evidence that it cannot work |
| `tau_extract_lat.py` | pulls carControl / controlsState / livePose / liveDelay / modelV2 / gyro from the rlogs |
| `tau_identify.py` | the identification: NCC, two-sided NCC, group delay, FOPDT, bootstrap CIs, controls |
| `tau_lagd_replicate.py` | the fork's own estimator replayed per speed band, no seed |
| `tau_phase_table.py` | ⭐ equivalent delay vs frequency — the table the loop model should read |
| `tau_amplitude.py` | amplitude-tercile test for rate/torque limiting |
| `tau_bandcheck.py` | band-sensitivity of the answer |

Outputs in `_scratch/tau_*.{txt,json}` beside them. Route caches in
`analysis-2020accord/_scratch/cache/tau/<tag>_lat.npz`.

## 7. Reading for the fork, recorded at the operator's request (2026-09-13, orchestrator)

**The operator's position, verbatim in substance:** he is skeptical that the speed-dependent lag is a
controls artefact rather than a real, physically variable delay, and he may implement a variable lateral
(and longitudinal) delay in StarPilot if a real one exists. This section separates what this study can and
cannot say about that.

**What is established [EVIDENCE, §4].** The command-to-response lag of the CLOSED outer loop rises as speed
falls (25+ m/s ≈ 0.15–0.18 s → 3–8 m/s ≈ 0.25 s on the current tune); it is not a pure transport delay (three
estimators disagree by up to 100 ms on the same data; the fitted lag pole is 1.4–4.3 Hz); the tune moved the
total by 20–55 ms (r39's SR 12.5 / LAF 2.11 tune was faster than today's LAF 6.0 tune); the lag is
amplitude-dependent in the friction direction (small-signal 30–50 ms slower, gain lower); and at 3–8 m/s the
wheel realises only 0.57–0.69 of the commanded curvature at 1 Hz. The dead-time/pole split is NOT identified.

**What could produce the speed dependence — three candidates, none excluded here:**
1. **The EPS firmware's own speed-dependent output scaling (neither "controls" nor "tire physics").** The
   LKAS output passes one fade stage whose speed half (table D at 0xCBBC4, factor 255 → 77 across its axis;
   axis UNIT OPEN — see `ADVERSARIAL-V293-PREREG` erratum) derates the delivered torque with speed in ONE
   direction. The record's on-car reading is a ×0.42–0.51 delivered/simulated multiplier at 3–9 m/s
   (V278r3), and this study's 0.57–0.69 realised curvature at 3–8 m/s is the same shape. A lower plant gain
   at low speed makes the closed loop slower — an apparent delay that a delay model would mis-attribute and
   a speed-dependent gain would fix. Identical on V282 and V293 (byte-stock on both).
2. **Rack Coulomb friction / deadband [physical, nonlinear].** §4.7: lag falls and gain rises with
   amplitude — the opposite of rate limiting. Small motions at creep are exactly where friction dominates.
   A variable delay cannot represent this; a friction/deadband compensator can.
3. **The outer-loop tune [controls].** LAF 6.0 cut P/I authority ×2.5 and the measured total moved with it;
   the `low_speed_factor` and the friction compensator's `error_with_lsf` input change the effective loop
   gain with speed (see the standing fork defect in `docs/STATE.md`).

**Evidence for a physically variable transport delay:** the r39 FOPDT fit places the speed dependence in
the dead time (80 → 180 ms) — but the r6c fit places it in the pole with dead time flat at 160–180 ms, and
the two are indistinguishable on this data. **Not established either way.**

**What would decide it, cheaply:** the V293 identification drive. In torque mode the EPS lane is
open-loop (T = f(cmd)·fade, one tick) and the fork's rate-plant feedforward is bypassed, so the
0xE4 → steering-rate pair loses the anticausal contamination of §1 and measures the PLANT (rack + tire +
fade) directly, per speed band and per amplitude tercile. If the dead time is flat with speed there, the
speed dependence on V282 was the servo + tune + fade; if it still grows toward 0.18 s at creep, it is
physical and a variable delay is warranted. Run `tau_identify.py` on that route with the 0xE4 pair
re-enabled and compare against §4.4.

**Longitudinal:** nothing in this session bears on it; no longitudinal delay was measured.
