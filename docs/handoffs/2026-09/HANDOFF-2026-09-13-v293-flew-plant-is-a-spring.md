# HANDOFF 2026-09-13 (night) — V293 FLEW: no classic grinding or stuttering, a NEW ratchet, and the plant underneath is a SPRING

> **Status at the time of writing.** V293 is **on the car**, flown once (route
> `75604b0a432fdc89_00000070--717f5a7866`, 2026-09-13 18:12–18:31, 19 segments, 1135.7 s, fork `Dom`
> `4247cb09e`). **Nothing was flashed and nothing was sent on any bus from this session** — the operator
> flashed and drove it himself. **No firmware was built or changed today after V293.** The fork side is a
> **Galaxy toggle config**, not fork code, and a **rev-2 config is being finalised** for the next drive
> (§9). The next-drive scorer (`v293_flight_read.py` v2) was **in progress at the time of writing.**
> Read `docs/STATE.md`'s decision box first; the previous narrative is
> `HANDOFF-2026-09-13-V292-FLEW-REVERT-V293-TORQUE-MODE-BUILT.md`.

---

## 1. The headline, in his words

The operator's symptom score for route 70, verbatim
(`rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt`, "OPERATOR SYMPTOM SCORE"):

> *"I did not experience any classic grinding or stuttering."*
>
> *"steering felt ratchety, like the wheel did not move smoothly but only snapped between angles rather
> than smoothly moving between them"*
>
> *"Sometimes steering felt loose and then sometimes there was oversteer and other times on hard
> transients, it would overshoot then correct slightly"*

🛑 **Read the first line as the kit's rules require it to be read: an ABSENCE of a complaint is not a
report of improvement, and nothing below licenses the word "fixed" for grinding, vibrating,
micro-ratcheting, ratcheting or excess friction.** He scores the symptoms; the bands in §3 are the
instrument. What is new and unambiguous is that he named **four fresh symptoms** — ratchety snapping,
loose, oversteer, and overshoot-then-correct — and every one of the four has now been measured with a
like-for-like control against V282 (§4, §5, §6).

He also said, earlier in the day, that the fork is *"tuned properly, just isn't modelling the resulting
torque."*

**The one-paragraph answer: he is right, and the mis-modelling is a SHAPE error in three independent
directions, on a plant that V293 turned into something openpilot's model was never written for.**
[EVIDENCE — `rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md` §§B, D, F, G1.] V293 removed the
EPS's 1 kHz rate servo, and the car underneath it is a **spring plus Coulomb friction**: EPS torque
commands a steering **angle**, and the torque needed per degree is essentially **speed-independent**
(~0.019 torque units per degree above 15 m/s). openpilot's torque controller models a single
**lateral-acceleration** gain, `lat_accel = SteerLatAccel · torque`, with **no friction term** (`SteerFriction`
was 0.00 on this drive against a measured Coulomb term of 0.009–0.014 *in that toggle's own unit*), **no
speed law** (the measured factor runs ×1.9 from 8–15 to >22 m/s at matched demand, because angle → lateral
acceleration carries the v², and ×2.8 from small to large demand at fixed speed, which is the friction),
and **a stale learned offset of ~0.30 m/s² subtracted from every frame** — on a straight, five times the
demand itself. The feedback cannot paper over any of it, because the as-flown loop crosses over at
**0.034–0.25 Hz** with 110–136° of phase margin above 8 m/s: above about 0.1 Hz the car is running open
loop, so **every dynamic error is a feedforward error**. The integrator nevertheless carries **38 % of the
commanded torque in every speed band** — which is precisely what a persistently wrong static feedforward
looks like. The *level* is close (the feedforward delivers 89–106 % of demand above 8 m/s, 53 % below);
the *shape* is wrong twice over, and both errors are ×2–3.

---

## 2. The drive, and how it is attributed

**Three attribution gates passed; a fourth failed and is broken as written.** Gates and negative controls
are in the flight read's §§0–1 and the plant identification's §A.

| gate | result | method |
|---|---|---|
| **toggle** | ✅ PASS | All eight config keys present and correct in `initData.params`: `AccordRatePlantFF` 0, `SteerKP` 0.3, `AccordTorqueKi` 0.15, `SteerFriction` 0.0, `SteerLatAccel` 6.0, `ForceAutoTuneOff` 1, `AdvancedLateralTune` 1, `AccordTurnFFTaper` 0. `GitCommit` `4247cb09e`, branch `Dom`. `AccordCurvatureLead` ABSENT, as required |
| **Kp on the control path** | ✅ PASS | `torqueState.p / torqueState.error` = **0.3000** at 100 Hz, IQR [0.3000, 0.3000], 100.0 % of frames within 5 %, n 77,863 (the plant study reads the same on n 86,007). This is a **wire** read of the tune, not a parameter read, and it survives a mid-route toggle change |
| **the edit is live** | ✅ PASS | The zero-parameter within-frame identity `\|427 tap\| = f(cmd)·fade`: **R² +0.9862**, residual **22.2 counts** (gate ≤ 38), `sign(T) = sign(pred)` 0.983, at lag −20 ms, n 42,885. **The LKAS rate feedback is dead on the wire** |
| **branch (`f/D`)** | ❌ **FAIL, and the gate is BROKEN AS WRITTEN** | see below |

**The identity is the important one, and it is properly controlled.** [EVIDENCE] The estimator has **zero
free parameters** — no fitted scale, no offset — so R² → 1 means the *bytes predict the wire*. Its
**positive control** is a V293 tap synthesised from this route's own command by the byte-exact 1 kHz march
with the feedback clamped to ±0, decimated and quantised: R² p50 0.9688 over six windows. Its **negative
control** is the same estimator with V293's cells on six routes that are not V293: r6c −0.011, r39 −0.840,
r35 −0.069, and the three V292 routes −0.135 / −1.225 / −0.561. **Every one fails, which is what makes the
pass attributable.**

⭐ **A side result that closes a long-open question.** The identity was scored against three candidate fade
axes. `V293/bar` wins at **R² 0.9862**; `V293/speed` reaches only **0.4171**. **The override taper's X axis
is the `|bar|>>5` reading the kit's record already carried, not km/h** — which settles adversary A's
erratum and retires the derated-rail scare (2151 at 10 m/s, 736 at ≥ 20 m/s) that the km/h reading implied.
[EVIDENCE — the wire, against cells read from the built image; flight read §1.]

**Why the `f/D` gate is broken, and why it is not a mis-attribution.** [EVIDENCE — the fork source, read
function by function: `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` §3; and the plant study §§A2,
G1.] The HOWTO's premise was *"friction 0 ⇒ `f = desiredLateralAccel` exactly."* It cannot be, because the
two fields are **different quantities**:

```python
future_desired_lateral_accel = desired_curvature * vEgo**2                 # the CURRENT command
setpoint  = expected_lateral_accel + desired_lateral_jerk * lat_delay      # the 0.30 s DELAYED command + a jerk lead
pid_log.desiredLateralAccel = setpoint                                     # the gate's DENOMINATOR
ff = future_desired_lateral_accel - roll_compensation - latAccelOffset * roll_offset_fade
pid_log.f = ff                                                             # the gate's NUMERATOR -- never sees setpoint
```

Measured, `f = 0.866·(desiredCurvature·v²) − 0.300` with R² 0.876 over 806 s. A **constant additive
subtraction** is exactly what makes a ratio climb with magnitude, and it reproduces the whole of the
reported ramp: `f/D` reads 0.531 / 0.668 / 0.752 / 0.837 / 0.868 across demand bands while `1 − (D−f)/demand`
reads 0.575 / 0.671 / 0.741 / 0.840 / 0.872. **The gate was measuring an offset, not a branch.** It should
test the **slope** (0.866) or `D_future − f`, not the ratio. The whole-route ratio landed at 0.747 against a
0.75 threshold — it failed by 0.003 on a statistic that could not have passed.

The subtracted ~0.30 m/s² is itself actionable and is **not** road banking: split by turn direction it reads
**+0.316 left, +0.077 right, +0.364 near centre — all the same sign**, so it is a vehicle-frame bias.
[EVIDENCE — plant study §G1.] It is `liveTorqueParameters.latAccelOffsetFiltered`, taken every frame because
`KeepLearnedLatAccelOffset` = 1 and `useParams` is true on honda, **frozen by `ForceAutoTuneOff` = 1 and
inherited from the V282 tune.** [EVIDENCE for the plumbing — fork path §2, `controlsd.get_torque_control_params`.]

**Exposure.** Route 1135.7 s wall · laterally engaged **858.0 s (75.5 %)** · `latActive` agrees with the wire
on 99.79 % of frames · longitudinal-only confound only 15.0 s · hands-off 762 s · `|angle| ≥ 30°` 48.2 s ·
hands-off creep 1–3 m/s 29 s. Engaged by speed: <8 m/s 151.6 s · 8–15 187.3 s · 15–22 319.8 s · >22 199.4 s.
`steeringPressed` while engaged 51.6 s in **175 distinct episodes** — which is why no clean 10 s low-speed
window survives the override buffer and why every `<8 m/s` number in this handoff is indicative, not firm.

🛑 **The dongle's route counter RESET.** Routes `6c`–`70` are **newer** than the locally cached `a6`, and
counter `70` had already been used by an unrelated August route. Never decide "newest" or "already local"
from the counter; order by connect date/time and confirm the build from useradmin's `git_commit`. Recorded
in `.claude/skills/fetch-rlogs/SKILL.md` (the session's one edit to a tracked file).

---

> ⚠ CORRECTED by scorer v2 (three-term regression on r70, R² 0.99998, residual 0.0024 m/s²): the +0.34 m/s² gap between the command and `f` is **+0.41 m/s² of ROLL compensation** (a persistent +2.4° estimated `liveParameters.roll`, device levelling vs real camber UNDECIDED; r39/r35 read +1.7°) **plus a −0.07 m/s² learned `latAccelOffset`** (a restored cache; `liveValid` 0 % on r70). `KeepLearnedLatAccelOffset` 0 removes the 0.07, not 0.30; no toggle touches the roll term.

## 3. The bands — the instrument, never the verdict

🛑 **These are BANDS. The operator scored the symptoms in §1.** Every gate below was calibrated on V292,
the build he drove and rejected earlier the same day, so a gate that a rejected build would pass is not
in the list.

**One REVERT trigger fired: the outer loop.** [EVIDENCE — flight read §4, six routes.]

| | r70 (V293) | r6c (V282) | r39 (V282) | r35 (V281r3) | worst V292 |
|---|---|---|---|---|---|
| 1–4 Hz angle amplitude at 0–5 m/s, deg | **3.547** | 0.589 | 1.378 | 0.543 | 1.950 |
| 1–4 Hz angle amplitude at 10–20 m/s, deg | **0.563** | 0.134 | 0.149 | 0.131 | 0.370 |

That is **>1.5× every V282/V281r3 reference** and above every V292 route — the V276 signature, and the
orchestrator's pre-registered first revert trigger. **Coherence is not the discriminator** (it reads
0.88–1.00 at 1–4 Hz on every route in the corpus, because openpilot commands there and the car follows);
the **amplitude** is. The pre-registration's instruction on this trigger is *the fix is the fork toggle
config, not the firmware, but the drive stops.*

**The plant study confirms and strengthens it independently.** [EVIDENCE — §E5.] Measured as a peak
prominence above a log-log line fitted to the 0.6–0.9 Hz and 4–7 Hz shoulders, r70 carries a **genuine line
at 1.17–1.76 Hz** below 20 m/s — **6.51 / 11.78 / 7.65 dB** at 0–5 / 5–10 / 10–20 m/s against **−2.32 to
+2.21 dB on every reference route**. On the quantiser-free 0x18F rate channel the 1–4 Hz content is **4.8×
to 11.6× every reference in every band** (59.1 / 23.0 / 8.2 / 2.3 deg/s against r6c's 5.1 / 4.8 / 1.1 / 0.49).
[BELIEF, stated as such by the analysis: it is very likely the same object as the ratchet.]

**The other pre-registered clauses.**

| clause | r70 | gate | verdict |
|---|---|---|---|
| ring, present-window 18–22 Hz amplitude | **×0.434** of r6c (×0.413 of r39) | ≤ ×0.40 | ❌ **FAIL** |
| ring, drive-controlled (engaged ÷ same-route disengaged) | 1.882 vs r6c's 3.399 = **×0.554** | — | reported |
| **F7** (6–9 Hz strong-turn ripple per 100 s of high-angle time) | **0.00** | < 2.0 | ✅ PASS |
| tap ripple / level, p50 | **0.008** (p90 0.025) | < 0.25 | ✅ PASS |
| absolute 6–8.5 Hz tap ripple | **7.5 counts = ×0.103** of r6c's 73.1 | < ×1.5 | ✅ PASS |
| 13–17 Hz, hands-off 8–15 m/s | **×1.03** of r6c | < ×1.5 | ✅ PASS |
| b4 (`sign r24`) negative control | **0.392** vs r6c's 0.394 | unchanged | ✅ PASS |
| 5–9 Hz, hands-off 8–15 m/s | **×1.61** (×1.86 all speeds) | a broadband ×1.5 was PREDICTED | REPORT |
| 22–30 Hz | at most **×0.57** of r6c | — | REPORT |

**Three readings of those numbers that matter, and one that has to be stated carefully.**

1. ⭐ **The 6–9 Hz price was predicted and it arrived as a BROADBAND rise, not a line.** Predicted ×1.5;
   measured ×1.61 / ×1.86. The 5–9.5 Hz **line** excess is **+0.29 dB**, the *lowest of any route in the
   corpus* (r6c +0.50, r39 +0.97, r35 +1.87, V292 +0.84 to +1.40). **F7 fired zero times in 48.2 s of
   engaged high-angle driving**, against V292's 2.2–6.3 per 100 s. The servo's disturbance rejection was
   removed and the broadband floor rose by the predicted amount; the *resonant* 7 Hz object that V292
   re-armed did not come back. [EVIDENCE]
2. 🛑 **The ring FELL, and it MISSED its gate. Both are true, and the difference is decision-bearing.**
   The present-window amplitude is ×0.434 against a ≤ ×0.40 clause — a miss by 8 %. But **presence** fell
   far harder: the ring was present in **19 of 1,679 windows (1.1 %)** on r70 against **9.8 % on r6c, 20.9 %
   on r39, 16.2 % on r35 and 18.1–20.5 % on the three V292 routes.** And its centre moved: **f0 17.89 Hz**
   on r70 against 20.03–20.11 Hz on all six references. ⚠ **[BELIEF] The flight read's own header sentence
   — "the identity HOLDS and the ring did NOT fall" — should not be read as "unchanged."** The terminal
   null sentence's antecedent is *amplitude and ring-down unchanged with the loop open*; the measurement is
   a roughly halved amplitude on a tenth of the windows at a shifted frequency, on 19 surviving windows.
   **Whether that closes the whole in-loop class V38 → V293 is the orchestrator's and the operator's
   adjudication, not the scorer's, and it should be made explicitly rather than inherited from a header
   line.** The n = 19 thinness is the reason to be careful in *both* directions.
3. 🛑 **The engaged-attributable excess MOVED DOWN in frequency, and there is a line the scorer did not
   gate.** [EVIDENCE — flight read §§2, 5.] On the drive-controlled measure r70 reads 5–9 **1.707**, 9–13
   **3.289**, 13–17 **3.279**, 18–22 **1.882** — where every V282/V281r3 route peaks at 18–22 (3.40 / 3.92 /
   3.62) and is quiet at 9–13 (0.98–1.21). The shape of what engagement adds has changed: it is now a 9–17 Hz
   object, not a 20 Hz one. Consistently, the line table puts r70's 10–17 Hz peak at **10.55 Hz, +3.81 dB**,
   against **+1.83 / +2.25 / +2.84 dB** on the three reference routes, while its 17–24 Hz peak fell to
   **21.48 Hz, +1.31 dB** against +3.08 to +4.49 dB on every reference. ⚠ **`STATE.md`'s V293 revert list
   names "a 10–18 Hz line" as a trigger; the scorer gated the 13–17 Hz BAND (×1.03, pass) and never scored
   the line.** r70's +3.81 dB sits above all three references and below V292's worst (+6.33 dB at 14.84 Hz).
   **This is flagged, not adjudicated — it is an open item (§12).**

---

## 4. The plant, identified

Route 70 was designed as an **identification drive**, and it delivered one. All of this is
`rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md`; every gain is an **instrumental-variable**
estimate (`H = S_zy/S_zu`, instrument `controlsState.desiredCurvature·v²`), because the input is openpilot's
own output and a direct regression is biased — measured at 25 % at 15–22 m/s, in the direction a
feedback-contaminated estimate must go. Estimator controls: a zero-lag pair returns 0 ms, a pair delayed
200 ms returns 196 ms [182, 198].

**The plant is a SPRING.** [EVIDENCE — §B1.] Log-log slope of the transfer magnitude over the coherent
band: torque → **angle** reads **+0.111 / +0.117** at 15–22 and >22 m/s, torque → **rate** reads **+1.237 /
+1.241**. A spring gives (0, +1); an integrator gives (−1, 0). The rate channel is the angle channel
differentiated to within 0.13 — an internal consistency check the data passes. **V293 did exactly what it
was designed to do: it removed the rate servo, and the car underneath is a spring.**

**The spring is speed-FLAT; the v² lives in the vehicle, not the steering.** [EVIDENCE — §B3.] Torque per
degree of steady angle: **0.0192 at 15–22 m/s and 0.0190 at >22** — two independent cells agreeing to
**0.6 %**. So `k ~ v⁰`. Lateral acceleration per unit torque nevertheless rises with speed, because
`la = angle·v²/(SR·L·(1+Kv²))`. **That is why a single `SteerLatAccel` cannot be right at two speeds.**

**Friction and the LAF law.** [EVIDENCE — §§B4, B5.] Binning on speed and demand amplitude at once separates
the two: down a column at fixed speed the measured factor runs **×2.8** from small to large demand (3.40 →
9.43 at >22 m/s) — that is **Coulomb friction**; across a row at fixed amplitude it runs **×1.9** from 8–15
to >22 m/s (3.19 → 6.00) — that is **the v² law**. Fitted directly as `u = a·θ + b·θ̇ + F·sign θ̇ + u₀` on
0.5 Hz low-passed clean data, **F ≈ 0.012 of full-scale torque, stable across bands** (0.0131 / 0.0123 /
0.0137 / 0.0089), i.e. **24–32 delivered EPS counts, 40–52 counts of 0xE4 command**. Hysteresis half-width
measured independently from the angle–torque loop split by rate sign gives **30–77 counts** — the same
quantity. `F` is in **exactly `SteerFriction`'s unit**, because `get_friction` returns `friction·LAF` in
lat-accel space and the controller then divides by LAF.

**No inertia is identifiable, and no clean breakaway threshold exists on this drive.** [EVIDENCE — §§B2, B5.]
A second-order model `J·θ̈ + c·θ̇ + k·θ = G·u` reaches 0.98–0.99 where the first-order one reaches 0.98 and
**fails (0.07–0.10) where the first-order one does not**. Any resonance is above 1.5 Hz, where this drive has
no coherent excitation. The wheel is almost always already moving, and in steady turn-hold high torque
coexists with zero rate, so friction is identified from the **hysteresis**, not from a threshold.

**τ_eq.** [EVIDENCE — §B6.] Equivalent delay on the torque → angle channel is **0.19–0.34 s at 0.3–1 Hz**,
falling mildly with speed (0.263 s at 8–15 against 0.200 s at >22, both at 0.5 Hz) — consistent with the τ
study's totals on a different channel. **The dead-time / lag-pole split still does not identify** even with
the input now known (8–15 puts it in the pole, 15–22 and >22 put all of it in dead time). ⚠ **[BELIEF, and
the analysis says so] a 0.20–0.24 s pure transport delay between EPS torque and steering angle is not
physically credible for a rack** — the phase slope measures accumulated phase in a loop whose disturbance is
correlated with the instrument. **Quote `τ_eq` at the crossover; never read it as an actuator delay.**

**The steer ratio is NOT a cause.** [EVIDENCE — §D, row "—".] The controller's own `actualLateralAccel`
agrees with the raw gyro to **within 1 %** in every `|angle|` stratum from 2° to 400° and in every speed
band. Whatever ratio the fork served, the angle → lateral-acceleration conversion the controller closes on
is correct. This is worth stating plainly because the fork's SR map was the previous session's headline
finding and it is **not** what is wrong here.

**Where the torque came from, and the loop that could not fix it.** [EVIDENCE — §§C2, D1.] Shares of the
command: `f` 0.42 / 0.51 / 0.55 / 0.57, `p` 0.23 / 0.14 / 0.07 / 0.05, **`i` 0.35 / 0.35 / 0.38 / 0.38** by
speed band. `|i| > 0.4` for **55.7 s in 16 episodes**, longest 11.9 s, at median speed 6.2 m/s. On the
identified plant the as-flown loop reads:

| band | Kp_eff | Ki_eff | PM | crossover | Ms |
|---|---|---|---|---|---|
| 1–8 m/s | 6.634 | 3.317 | **−71.1°** | 3.64 Hz | 1.87 |
| 8–15 | 1.025 | 0.513 | 136.2° | 0.246 Hz | 1.15 |
| 15–22 | 0.492 | 0.246 | 115.6° | 0.045 Hz | 1.97 |
| >22 | 0.392 | 0.196 | 110.6° | 0.034 Hz | 1.65 |

🛑 **The binding band is below 8 m/s, and no `SteerKP` value fixes it.** The plant supports Kp_eff ≤ 1.93
there; the **low-speed factor alone is 6.33 at 4.5 m/s**, and `lsf` is **added** to `SteerKP`, not scaled by
it, so it cannot be tuned out from Galaxy. The implied `SteerKP` limit is **−4.40**. [EVIDENCE on the
arithmetic; BELIEF that this is the mechanism behind the 3.2 % low-speed torque rail and the wind-up
episodes, though both are consistent with it.] Above 15 m/s the optimiser wants Ki/Kp ≈ 10 /s — **[BELIEF]
do not fly that**, an integral-dominated loop will feel darty, which is one of the operator's own revert
triggers. **The safe move is to fix the feedforward and leave the gains alone**: with the FF correct and the
as-flown gains, every band above 8 m/s sits at PM 110–136° and Ms ≤ 1.97.

---

## 5. The ratchet, measured

`v293_ident_h.py`, `_h2.py`, `_k.py`. **Every statistic is run identically on three reference routes** (r6c
V282, r39 V282, r35 V281r3 — two builds, two lateral tunes).

🛑 **Two instrument facts had to be settled first, and both changed the answer.** The 0x14A angle field
quantises at 0.1°, so *any* angle-based smoothness measure reads 1.000 below about 10 deg/s whatever the
plant does — so every number comes from the **0x18F rate field** (0.125 deg/s), never from `d(angle)/dt`.
And the **driver-torque bar cannot stand in for `steeringPressed`** on this car: it reads EPS twist, and no
threshold separates the strata (at `|bar| < 800` it catches 98.2 % of hands-off frames and 0.1 % of
hands-on ones). Cross-route rows are therefore **all-engaged on both routes**, like-for-like.

**The decisive statistic is a RUN-LENGTH one: dwells per minute at the tightest threshold.** [EVIDENCE —
§H2, swept over four thresholds, smoothed detector applied identically to both routes.]

| stratum | th 0.25 deg/s | th 0.50 | th 1.00 | th 2.00 |
|---|---|---|---|---|
| r70 all-engaged 0–5 m/s | **15.23** | 33.78 | 36.43 | 38.41 |
| r70 all-engaged 5–10 | **7.66** | 29.45 | 40.64 | 40.05 |
| r70 all-engaged 10–20 | **4.56** | 32.90 | 41.05 | 41.21 |
| r70 all-engaged >20 | **1.24** | 24.95 | 44.34 | 38.98 |
| r6c all-engaged 0–5 | 0.39 | 12.80 | 26.57 | 37.63 |
| r6c all-engaged 5–10 | 0.64 | 18.63 | 33.28 | 35.36 |
| r6c all-engaged 10–20 | 0.44 | 25.41 | 39.62 | 33.58 |
| r6c all-engaged >20 | 0.20 | 21.82 | 48.84 | 26.92 |

**The wheel comes to a genuine stop 6.2× to 39× more often on V293.** At 0.5 deg/s the ratio is 1.1–2.6×;
at 1–2 deg/s the two builds converge and r6c sometimes exceeds. **The excess is specifically in genuine
stops, not in slow motion** — which reconciles the two earlier readings: the marginal distribution's shape
is unchanged, because the excess lives in a run-length statistic, not a marginal one.

**The median snap is the SAME on both builds; what differs is how long the wheel sits still first.**
[EVIDENCE — §H2.] At the 0.5 deg/s threshold, r70's dwell p90 is **0.78–1.11 s** against r6c's **0.375–0.625 s**
(1.3–2.6×) — on V293 the wheel can sit for nearly a second and then move. Snap p90 is also 1.5–2.9× larger
at 10–20 and >20 m/s. The scale-free headline measure ("of all the wheel travel in a 4 s window, what
fraction is delivered in the fastest 10 % of its frames", binned by each window's **own** rms wheel rate,
because r70's rms rate is 2–3× the references' in the same speed band) puts **V293 above all three
references in every bin, with the gap widening with activity**: 0.468 at q75–90 against 0.325–0.351, i.e.
+33 % to +44 %. Calibration on synthetic signals: a 1 Hz sine 0.157, band-limited noise 0.278, a 10-step
staircase 1.000.

🛑 **THE COMMAND IS EXONERATED, three ways.** [EVIDENCE — §§E1, H4.] The same concentration measure on the
0xE4 command reads 0.398–0.447 on r70 against 0.311–0.412 on the references, and is **flat across bins while
the wheel's rises**. Per-frame rms of the command step is **2.9× LOWER** on V293 (7.74 counts at 10–20 m/s
against 22.39 on r6c and 23.20 on r39). Around each slip, the largest single-frame command step is **12.0
counts on r70 against 36–44 on r6c**, with an **identical crest factor (3.6–4.4 on both)**. **The command got
smoother and the wheel got snappier. The car is doing the snapping.**

🛑 **THREE INDEPENDENT NULLS ON THE INTEGRATOR STICK-SLIP MECHANISM.** [EVIDENCE — §§E3, H3.]

1. **No excess spike at zero.** `P(rate = 0) ÷ P(0 < |rate| ≤ 0.25)` is **0.556–0.641 on every route and
   every band, V293 included**. A textbook stiction plateau would show as an excess spike; what grew is
   the whole low-rate mass.
2. **No breakaway above hold, and no wind-up ramp.** Measured on the 100 Hz command mapped to delivered
   counts (the 50 Hz, 8-count tap cannot resolve a 0.12 s dwell): breakaway minus hold reads
   +10.2 / −6.5 / −4.4 / +0.6 counts on r70 against +0.6 / −3.0 / +2.7 / +5.5 on r6c — **indistinguishable
   and not consistently positive.**
3. **The command does not traverse the Coulomb band across a dwell.** With F = 0.011 of full scale = 45
   counts of 0xE4, so 2F = 90, the command moves only **0.36–0.63 of 2F across a dwell, on BOTH builds**,
   and r70 is barely above r6c.

⇒ **It is not "the integrator winds torque up until breakaway."** The dwells are 0.11–0.13 s — far too short
for Ki = 0.15 to wind anything.

**What it is.** [BELIEF, with the competing reading stated — §E4.] A spring plus Coulomb friction (0.0115
torque/deg, 0.010–0.012 torque of friction) driven by a low-bandwidth command through a loop crossing over at
0.034–0.25 Hz. Inside the friction band the wheel does not move; when the command's own slow evolution
carries it out, the spring releases the stored deflection at once. That reproduces dwell-and-jump with no
wind-up and no zero spike. 🛑 **V282 had TWO friction linearisers and this drive removed both at once, so it
cannot separate them**: the EPS's own 1 kHz rate servo (a rate servo is the classic friction lineariser) and
the fork's rate-plant feedforward, whose `d(angle_des)/dt` term was **dithering the command** — which is why
V282's per-frame command step is 2.9× V293's, and dither is the other classic way friction gets linearised.
Snap size ≈ **2F/k(v)**: the friction band expressed in angle.

---

## 6. Loose, oversteer, and overshoot-then-correct

All three of the operator's remaining new symptoms were measured. [EVIDENCE — plant study §§G2, G3, G4.]

**"Loose" is not wander — it is STIFFNESS.** Angle wander (rms of the 0.1–1 Hz band-passed angle on
straight-ish stretches) is **lower** on V293 than on V282: 0.137 / 0.141 / 0.229 deg against r6c's
0.207 / 0.207 / 0.209. What is low is the **outer loop's stiffness** in torque per degree of angle error,
against the plant's own return spring:

| band | loop stiffness | the plant's own spring | ratio |
|---|---|---|---|
| 0–5 m/s | 0.0032 | 0.0023 | 1.4 |
| 5–10 | 0.0065 | ~0.006 | **1.1** |
| 10–20 | 0.0128 | 0.0115 | **1.1** |
| >20 | 0.0227 | 0.0154 | 1.5 |

**The loop is barely stiffer than the car's own return spring below 20 m/s**, so a disturbance moves the
wheel about as far as the loop then pulls it back — and with the feedforward near zero on a straight,
almost nothing else is holding it.

**"Oversteer" is real above 20 m/s and at larger demand.** Turn-hold windows ≥ 1.5 s give actual/desired
**0.937 at 10–20 m/s** (11 runs) and **1.093 at >20** (5 runs); by demand size, 0.937 at `|D|` 0.5–0.8 and
**1.078** at 0.8–1.2. That is the same finding as the closed-loop tracking gain, which rises **monotonically
0.884 → 1.020 → 1.123** with speed (R² 0.95 on all three): **under-turning below 15 m/s, over-turning above
22.** It is the LAF speed law showing up directly, and it matches §7's finding that the flown lateral-accel
feedforward over-commands by 1.9–2.1× above 15 m/s. Regime-wise: **under-delivers on straights (80.0 %) and
turn entry (95.7 %), over-delivers on turn hold (107.4 %) and turn exit (113.2 %)** — the friction error and
the LAF error showing up in different regimes, which is why a single scalar cannot fix both.

**"Overshoot then correct" is a FIXED excursion, not an under-damped loop.** 38 step events. Overshoot
0.166 (5–10 m/s, n 3), **0.437** (10–20, n 18), 0.341 (>20, n 8); time to peak 0.74 / 1.19 / 1.17 s; ring
0.78–1.56 Hz. **The discriminator**: absolute overshoot = −0.456·(step size) + 0.571, **R² 0.027, n 29** —
the slope is *not positive* and the fit explains nothing. The overshoot is a roughly fixed ~0.4–0.5 m/s²
excursion that does not scale with the step, which **rules out an under-damped linear loop** (that would
scale). Correlation with the integrator at the peak is +0.172, too weak for wind-up. **The two readings that
survive are a stiction release and the fixed 0.30 m/s² feedforward offset, and this drive does not separate
them.** [Stated as the analysis states it.] Lane changes (3 found, 24.0 s): peak actual / peak desired
**1.30**, error spectrum peaking at 0.39 Hz — not in the 1–4 Hz band of §3's revert trigger.

---

## 7. What the fork's map does to this plant

`docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md`, a full read of the lateral path at fork HEAD
`4247cb09e`, working tree clean. Cited by function name; every claim marked in that file.

🛑 **The fork carries an explicit plant model for this car, and the V293 config switches it off.**
[EVIDENCE — §0.] `HONDA_ACCORD_EPS_G_V` / `_K_V` in `latcontrol_vehicle_tunes.py` encode
`wheel rate = G(v)·torque − k(v)·angle`, identified on routes r34/r35/r39/r3a/r3c — **on the V280+
rate-servo firmware.** Its own comment states the case the operator is now describing from the seat:
*"A lat-accel feedforward (setpoint / latAccelFactor) is 3-10x too much torque on this plant; the P term
then has to cancel it and the loop settles above command."* With `AccordRatePlantFF = 0` the controller
takes the generic `else` branch and runs **exactly that** lat-accel feedforward.

**Four structural consequences, each EVIDENCE from the code with the real vehicle model.**

1. ⭐ **THE ANGLE-DOMAIN LOOP GAIN IS FLAT.** [§4.] `low_speed_factor` exists precisely to cancel the v² in
   the error, and it does so almost perfectly: the P loop gain in the angle domain is **33–37 counts per
   degree from 1 m/s all the way to 20 m/s**, rising only ×1.34 by 30 m/s. **A 2 Hz ring at 0–5 m/s and an
   elevated 2 Hz line at 10–20 m/s are the same instability, because the controller applies the same
   angle-domain gain at both** — which is exactly the pattern §3's revert trigger measured (3.547 deg at
   0–5 m/s, 0.563 at 10–20, both elevated; 5–10 and >20 m/s not). **There is nothing speed-selective to
   blame; what changed is the plant.**
2. 🛑 **There is NO derivative term.** `LatControlTorque.__init__` constructs `PIDController` with no third
   positional argument, `k_d` defaults to 0, `_k_d` is assigned nowhere outside `common/pid.py`, and
   `torqueState.d` is always 0.0. **A P-only loop on a plant that integrates torque into angle has only the
   plant's own damping for phase margin.**
3. 🛑 **`SteerKP` cannot fix the low speeds and `SteerLatAccel` is the only uniform lever.** At 3 m/s
   `SteerKP` contributes 0.3 of an effective 15.1, so driving it to its 3.0 ceiling moves the gain by 18 %;
   below ~7 m/s it is nearly inert. **`SteerLatAccel` divides P, I and the feedforward together**, so it
   scales the angle-domain loop gain **uniformly at every speed** — one number that would both halve the
   loop gain everywhere and cut the feedforward over-command. The fork's own constant block records
   `LAT_ACCEL_FACTOR_MAX_MULT = 10.0` with the comment that the measured lat-accel-per-torque was 12–15 on
   the previous firmware. [BELIEF that 12–15 transfers to V293 — it was measured on a rate plant; §2.]
4. **A reference-path delay at 2 Hz.** `setpoint = expected + LPF_{1.2 Hz}(future − expected)` is a
   complementary filter: at DC the setpoint equals the current command, but **above ~1.2 Hz it reverts to
   the 0.30 s delayed command.** Near 2 Hz the controller's target is a third of a second stale while the P
   term chases it at ~35 counts/deg with no derivative. That is a reference-path delay, not a feedback one,
   so it does not by itself close an unstable loop — but it is the structural note that sits directly under
   §3's 1–4 Hz line. **Test: compare `torqueState.desiredLateralAccel` against `controlsState.desiredCurvature·v²`
   in the 1–4 Hz band and look for the phase split.**

**Two more facts from that read that bound the risk of anything done here.** [EVIDENCE — §§1, 4.] The Honda
rate limiter is `STEER_DELTA_UP = STEER_DELTA_DOWN = 3`, class-level, **no speed term, not driver-torque
aware** (±0.03/frame = 122.88 counts/frame, 0 to full scale in 0.333 s), and **panda safety imposes no
magnitude, rate, driver-allowance or RT-interval limit on 0xE4 at all** — the entire steer check is a
block-when-not-allowed test. **The only ceilings are the ±4096 clamp and the EPS firmware itself.**

**The fork's spring feedforward, re-fitted against the plant we just measured.** [EVIDENCE — plant study
§§F1–F4.] Solving the identified balance for the fork's own parametrisation gives `G = 1/b`, `k = a/b`,
`k/G = a` with no extra assumption, jointly fitted on the same frames, with a 2000-resample block bootstrap
over 27 clean stretches (738 s). Against the fork's breakpoints, **`G` is 2.85–2.92× larger and `k` is
5.8–6.3× larger than the tables carry** — but **the hold term uses only the ratio**, and there it is
**1.4× to 2.6× too small**:

| band | v | fork hold `k/G` | measured `a` | spring_scale needed | measured `b` | rate_gain needed |
|---|---|---|---|---|---|---|
| 1–8 | 4.93 | 0.00163 | 0.00228 | 1.40 | 0.00180 | 0.216 |
| 8–15 | 11.96 | 0.00353 | 0.00764 | **2.16** | 0.00366 | 0.355 |
| 15–22 | 18.94 | 0.00536 | 0.01149 | **2.14** | 0.00409 | 0.345 |
| >22 | 22.80 | 0.00600 | 0.01539 | 2.56 | 0.00489 | 0.384 |

**One scalar `AccordEpsSpringScale` = 2.15 leaves residuals of 35 % / 1 % / 1 % / 19 %** — exact in the two
best-determined bands, off at the ends, and the 35 % is the band where nothing is identified. Torque
commanded per degree of steady angle, divided by what the plant needs (1.000 is correct):

| band | lat-accel FF (flown) | plant FF as shipped | plant FF × 2.15 |
|---|---|---|---|
| 1–8 | 0.650 | 0.716 | 1.542 |
| 8–15 | **1.140** | 0.462 | **0.995** |
| 15–22 | **1.901** | 0.467 | **1.005** |
| >22 | **2.057** | 0.390 | 0.840 |

⇒ **The toggles are enough.** Reshaping the tables is code and is only justified if a second drive shows the
19–35 % end residual matters. ⚠ Two caveats stated by the analysis: **the pole is the least determined
quantity** (the joint fit puts `k` at 1.3–3.1 rad/s, part B's flat magnitude to 1.2 Hz puts it above 7.5;
both agree the fork's 0.35–0.50 1/s is wrong by at least 5×, and the hold term is unaffected because it uses
only the ratio); and **two values of `a` exist in the study, differing 1.6×** — **use the joint fit for a
feedforward**, because the IV number has friction folded into the spring and the fork applies friction
separately, so using it would double-count.

---

## 8. The authority question, answered — and nothing was changed

The operator asked whether V293 is **"more than 6× the stock LKAS available torque"**, and said *"if not,
don't change anything."* **Answer: yes at the very top of the demand axis, by 2.8 %, and below ×6 everywhere
else. Nothing was changed.** [EVIDENCE — verified by the orchestrator from the three images with the golden
model's `lkas_rate_pid_surface`.]

| quantity | value |
|---|---|
| peak delivered lane torque, V293 | 2461 counts |
| peak delivered lane torque, stock (stalled wheel) | 399 counts |
| **peak ratio** | **×6.17** |
| worst index | **×6.20 at demand index 239** |
| above ×6 only at | demand indices **231–254** |
| median over idx 1–254 | **×4.35** |
| minimum | **×3.79 at idx 128** |
| V282 on the same axis | above ×6 at **every** index, **×19 at the bottom** |

**Every authority cell is exactly ×6.000**: the assist-map ceiling 172 → 1032, the forward gain 891 → 5346
(via a repointed displacement at `0x2A1F0` to the private cell `0xC6CD0`), and the output clamp `0xC61B4`
512 → 3072. The P clamp `0xC61BC` and the sum clamp `0xC61BE` are **15360, unchanged from stock**, and the
stock feedback clamp `0xC62E6` is **7680** (V282's 46080 was 6× stock; V293 sets it to 0).

**The 2.8 % surplus is the P term, and it is arithmetic, not a lever.** Kp 120 flat on the ×6 map computes
P = 15480, which the **stock** P clamp truncates to **15360 = 1.0265× stock's 14964**. Kp 115 would land
×5.96. **This was not changed**, per the operator's instruction. ⚠ **Never say "authority unchanged" about
V293 and never show only the rail**: the sub-rail slope is **10.34 counts/idx against V282's 21.35**, so
below idx 116 V293 delivers 0.47–0.49 of V282's stalled-wheel torque and meets it only at idx 239–240. *The
peak is identical and needs twice the demand to reach.* The wire agrees: `|427 tap| = 0.6077·|0xE4 cmd|`
(R² 0.966) against the built image's 0.6385, a **95.2 % agreement**, and `cmd = −3988.5·actuators.torque`
(R² 0.978) ⇒ STEER_MAX 4096, full-scale torque 1.0 buying 2489 delivered counts and the rail reached at
`|torque| = 0.989`. [EVIDENCE — plant study §A4.]

---

## 9. The rev-2 fork package — tables in CODE, the rest a toggle config — and what would falsify it

**The toggles-vs-code verdict FLIPPED in the last hour of the session.** The three-feedforward replay
(`V293-PLANT-IDENT-2026-09-13.md` §I, `v293_ident_m.py`) showed that **no single `AccordEpsSpringScale`
fits the plant's shape**: the old rate-loop tables need ×1.2 at 5 m/s and ×2.1 from 12.5 m/s up, so a
scalar that is right at speed **over-holds ~2.1× below 8 m/s** — the dangerous direction (it over-steers
the operator into low-speed turns, in the band where the hard-coded low-speed factor already leaves the
loop marginal). The plant tables were therefore replaced **in fork code**, the one place the shape lives:

| fork `selfdrive/controls/lib/latcontrol_vehicle_tunes.py` | was (V280–V292 rate loop) | **now (V293, route 70)** |
|---|---|---|
| `HONDA_ACCORD_EPS_G_V` at [5, 12.5, 18.5, 28.5] m/s (deg/s per unit torque = 1/b) | [120, 95, 85, 70] | **[550, 271, 246, 167]** |
| `HONDA_ACCORD_EPS_K_V` at [4, 8, 12.5, 18.5, 28.5] m/s (1/s = a/b) | [0.17, 0.28, 0.35, 0.45, 0.50] | **[0.30, 1.00, 2.30, 2.77, 3.91]** |
| hold torque per degree k/G at [5, 12.5, 18.5, 28.5] | 0.00165 / 0.00368 / 0.00529 / 0.00714 | **0.00202 / 0.00794 / 0.01125 / 0.01539** |

Fork commit **`66cf4454a` on `Dom`** (base `4247cb09e`; the old tables kept in the comment for a
V282-class image; `test_latcontrol.py` expectations updated — the openpilot test runtime is not
installable on this host, so the assertions were evaluated on a pure mirror of the function). The
feedforward consumes only k/G (hold) and 1/G (move), never k alone, so the tables' weak pole does not
enter the command. The 4–5 m/s knots are BELIEF (b's CI crosses zero; the conservative, smaller hold was
taken); 28.5 m/s is extrapolated. Replay residual against the torque the plant actually needed (§I):
**0.042 / 0.042 / 0.007 / 0.010** by band for the new tables, against 0.210 / 0.037 / 0.031 / 0.021 for
the best toggle-only option and 0.080 / 0.045 / 0.045 / 0.049 for the flown branch with `SteerLatAccel`
5.4; hold ratio **1.19 / 0.94 / 0.99 / 0.84** against 3.20 / 1.52 / 1.54 / 1.29 (old ×3.3) and
0.98 / 1.27 / 2.11 / 2.29 (the flown lat-accel branch).

**The rev-2 toggle config** — `analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.json`
(generator `tools/make_galaxy_toggle_config.py`, 15 keys, a delta; **requires the fork at or after
`66cf4454a`**):

| key | rev 1 (flown) | **rev 2** | why |
|---|---|---|---|
| `AccordRatePlantFF` | 0 | **1** | the only **spring** feedforward in the fork — the shape V293's plant has — now on the V293 tables; also restores the `d(angle_des)/dt` command dither that was one of the two friction linearisers V293 removed |
| `AccordEpsSpringScale` / `AccordEpsGainScale` | 1.0 (inert) | **1.0 / 1.0** | the tables carry the identification |
| `AccordFFRateGain` | 0.5 (inert) | **0.5** | with the new tables 1/G IS the measured viscous term, but the term is fed a planner-limited reference: the adversarial replay of route 70's own demand showed the FF alone past full scale for 0.34 s below 8 m/s at 1.0 (max 1.13); at 0.5 the max is 0.81 |
| `SteerFriction` | 0.00 | **0.011** | the measured Coulomb term (0.0098–0.0120 in this toggle's own unit); describing-function check (§K): no relay limit cycle below 0.0235 at 4.5 m/s on this config |
| `SteerLatAccel` | 6.0 | **14.0** | in the plant-FF branch it scales ONLY P and I — the one lever on the low-speed loop gain (the low-speed factor is ADDED to Kp, so `SteerKP` cannot reduce it): as flown PM −11° / Ms 12 at 4.5 m/s → Ms 2.16 |
| `SteerKP` | 0.3 | **0.85** | buys back the hold stiffness at speed ("loose"); the Ms ≤ 2 bound at >22 m/s is `SteerKP` ≤ 0.92 at LAF 14 (Ms ≈ 1/(1 − Kp_norm) with the 0.20–0.24 s dead time) |
| `AccordTorqueKi` | 0.15 | **0.30** | the live integral gain is Ki·(1 + lsf/Kp): 3× lower than flown at 4.5 m/s (the wind-up band), 0.6× at speed |
| `KeepLearnedLatAccelOffset` | 1 | **0** | drops the −0.07 m/s² learned offset (a restored cache, `liveValid` 0 % on r70). ⚠ CORRECTED by scorer v2 (three-term regression on r70, R² 0.99998, residual 0.0024 m/s²): the +0.34 m/s² gap between the command and `f` is **+0.41 m/s² of ROLL compensation** (a persistent +2.4° estimated `liveParameters.roll`, device levelling vs real camber UNDECIDED; r39/r35 read +1.7°) **plus a −0.07 m/s² learned `latAccelOffset`** (a restored cache; `liveValid` 0 % on r70). `KeepLearnedLatAccelOffset` 0 removes the 0.07, not 0.30; no toggle touches the roll term. The replay note stands: on the flown branch removing the offset term made the residual worse (0.067 vs 0.045 at 15–22) — it was compensating that branch's over-holding |
| `SteerDelay` / `UseAutoSteerDelay` | 0.2 / 0 | **0.2 / 0** | τ_eq 0.19–0.34 s supports 0.20–0.22; not a lever worth a drive |
| pins | `ForceAutoTuneOff` 1 · `ForceAutoTune` 0 · `AdvancedLateralTune` 1 · `AccordTurnFFTaper` 0 | **unchanged** | restated so the file is self-sufficient |

Predicted on the identified plant (§J/§K, "R2′" adapted to the tables): Ms **1.78** at 15–22 m/s, **≈1.9**
at >22, **PM 68° / Ms 2.16 at 4.5 m/s** (as flown: −11° / 12.3); 1 m/s² step overshoot **0.48 / 0.38**
(as flown 1.41 / 1.56, i.e. ÷3–4); FF hold ratio **1.01 / 1.00** at 15–22 / >22 (as flown 1.90 / 2.06);
controller hold stiffness at speed **≈ as flown** (0.0104 / ~0.013 u/deg). ⚠ **Every config, this one
included, still fails the margin bound at 3 m/s** — the low-speed factor's doing (14.8 added to Kp), and
the plant there is an extrapolation of the study's weakest cell: read that row as a direction. The
adversarial pass on the package is `docs/review/ADV-REV2-FORK-PACKAGE-2026-09-13.md`.

🛑 **The mismatch hazard is NOT symmetric and the step order still binds.** The firmware stays V293; the
fork must be updated on the device to `66cf4454a` or later **before** the rev-2 config is restored (on the
old tables `AccordRatePlantFF` 1 under-holds ×2.1 above 12 m/s). Reverting the fork side is: restore the
rev-1 config (`toggle-config_V293_torque_mode.json`), restart. A torque-mode config on a **rate-servo**
image is over-delivery that **nothing downstream catches** (§7: panda applies no limit to 0xE4) — never
create that state. **Safe Mode resets these keys** — always a route *out* of the config, never into it.

**On the friction compensator's LSF inflation** (`error_with_lsf` into `get_friction`, gain
`(friction/0.30)·(1 + lsf/Kp)`): with `SteerKP` 0.85 the inflation at 4.5 m/s is 8.4 (it was 22 at Kp 0.3),
and the describing-function check found **no limit cycle at 0.011 on either the flown or the rev-2 config**
(first sustaining value 0.0235 at 4.5 m/s on rev 2). The V293-clearance rule "friction > 0 requires Kp ≤ 1.0"
is respected (0.85). [EVIDENCE — `V293-PLANT-IDENT` §K; BELIEF that a describing function is adequate.]

**What would falsify rev 2 on the next drive.** [EVIDENCE-grade pre-registration, from the plant study §D2.]
All five should move together if the feedforward-and-friction diagnosis is right:

| instrument | now (route 70) | expected direction |
|---|---|---|
| tracking gain of actual on desired, by speed | 0.884 / 1.020 / 1.123 | **flatten toward 1.00** across bands |
| integrator's share of the command | 0.38 in every band | **fall well below 0.38** |
| straight-line delivery | 80.0 % | **rise** |
| rate-magnitude concentration at q75–90 | 0.468 | **fall toward the references' 0.325–0.351** |
| 1–4 Hz rate content at 10–20 m/s | 8.2 deg/s | **fall toward r6c's 1.1** |

⭐ **And the one thing route 70 could not do, which rev 2 can**: the firmware and the fork config changed
together, so the drive cannot separate the two friction linearisers it removed. **If the friction and
feedforward changes move the ratchet statistics and not the tracking, or the reverse, that separates the
two causes.**

**The next-drive scorer** is `v293_flight_read.py` **v2**, **in progress at the time of writing**. Three
things go into it: **(i) config-file attribution** — score `initData.params` directly against the delta
`.json` rather than against a hard-coded expectation, since the rev-2 file is the definition; **(ii) a
repaired branch identity** — the `f/D` ratio is replaced, because it measures the offset, not the branch
(§2); the discriminating read is **`torqueState.f` against `starpilotLateralState.feedforward`**, which are
equal under the rate-plant-off arm and diverge under the rate-plant arm, with the regression slope (0.866)
as the backup; and **(iii) the four symptom instruments** of §§5–6 — the dwell-per-minute sweep and the
rate-magnitude concentration for *ratchety*, the loop-stiffness-versus-plant-spring ratio for *loose*, the
turn-hold actual/desired for *oversteer*, and the step-event excursion-versus-step-size regression for
*overshoot-then-correct* — each with its V282/V281r3 reference row, because every one of them was only
interpretable on route 70 because three reference routes were run through the identical code.

🛑 **Two scorer bugs must be carried into v2 or they will silently corrupt it.** The kit's cereal declares
`epsTelemetry @137` while the fork declares `starpilotLateralState @137` — **same slot, same struct id
`0xc2243c65e0340384`, different layout** — and a second collision of the same shape at `@116`
(`modelDataV2SP` vs the fork's `customReserved9`). Any kit decoder reading either from a 2026-09 fork rlog
reads **garbage**. And the 427 tap's wire polarity is **`sign(T) = +sign(cmd)`**, not the `−sign(cmd)`
inherited from V279's docstring.

---

## 10. If an inner loop ever comes back — which quantity?

The operator asked, verbatim: *"something we may need to look into in the future is introducing just enough
closed-loop LKAS inner loop control, issue is that it isn't controlling the right quantity... or what if we
made the E = setpoint − (derivative of filtered angular velocity or filtered derivative angular velocity)?"*
The answer is written up in `docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md`, and it is three
sentences long. **An angular-acceleration loop adds electronic inertia, leaves the friction band `2F/k`
completely unchanged, and turns command → angle into a double integrator — worse than V282's single one, and
the derivative of a 0.125 deg/s-quantised rate needs so much filtering that the loop has no authority at the
4–9 Hz dwell timescale.** **An ANGLE loop — an electronic spring — is the right quantity: it shrinks the
friction band to `2F/(k + K_e)`, speeds the spring pole, and leaves the plant as command → angle, exactly
what the fork's spring feedforward already models.** **The order of rungs is toggles first (rev 2, §9), then
a fork-side 100 Hz rate-feedback term with a few-Hz crossover and no firmware, then — and only then — a
firmware angle loop, which is a CAVE and therefore the kit's only bricking class, needing both gates of
`BUILD-LINEAGE.md` Part 2; never an angular-acceleration loop and never a half-open feedback clamp, which
would be a hybrid neither controller can model.**

---

## 11. Files touched this session

From `git status` in the kit (the only tracked-file edit is the skill; everything else is new and untracked):

**Edited**
- `.claude/skills/fetch-rlogs/SKILL.md` — the route-counter reset (+5/−1).
- `rlog-tools/studies/grind/v293_flight_read.py` — the v2 scorer of §9, **still being written as this
  handoff was finished**; treat its state as unsettled until the orchestrator says otherwise.

**New — reports**
- `rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt` (28.2 KB) — the pre-registered scorecard,
  with the operator's verbatim symptom score appended.
- `rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md` (49.4 KB) — sections 0, A–H and D.
- `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` (41.1 KB) — sections 0–8.
- `docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md` (4.1 KB).
- `docs/handoffs/2026-09/HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md` — this file.

**New — identification scripts** (`rlog-tools/studies/grind/`)
`v293_ident_lib.py`, `v293_ident_extract.py`, `v293_ident_surface.py`, and passes
`v293_ident_{a,b,b2,b3,c,d,e,f,g,h,h2,i,i2,j,k,m,n}.py`. **`b3`, `f`, `g`, `h2`, `i2` and `j` are the final
passes; `b` and `b2` are superseded and say so in their own docstrings.** Outputs are in
`rlog-tools/studies/grind/_scratch/v293_ident_*.{txt,json}`; the extraction wrote its own cache at
`analysis-2020accord/_scratch/cache/tau/r70_v293_ident.npz` and did not touch the orchestrator's.

**New — scorer v2 (§9), landing as this handoff was finished**
- `rlog-tools/studies/grind/v293_symptom_instruments.py` — the four symptom instruments.
- `rlog-tools/studies/grind/v293_ident_n.py`.

**Added after the draft:** `analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.json` (+ `.decoded.json`),
`tools/make_galaxy_toggle_config.py` (rev-2 entry), fork commit `66cf4454a` (tables), `docs/review/ADV-REV2-FORK-PACKAGE-2026-09-13.md`,
the scorer v2 files, the page v7. The kit commit at close-out carries all of it.

---

## 12. Open questions and next steps

> **Sample-rate check (operator's question, 2026-09-13 night — measured on route 70's own CAN timestamps):** the steering feedback is **100 Hz**, not 50 — `0x14A` STEERING_SENSORS (angle) and `0x18F` STEER_STATUS (rate, 0.125 deg/s LSB) both arrive at 100.9 Hz median (p5–p95 9.1–11.3 ms), `0xE4` goes out at 100 Hz, and the samples are FRESH each frame (identical consecutive values only 5 % on the rate and 10 % on the angle while moving, equal on both frame parities — a 50 Hz-held value re-sent at 100 Hz would read ~100 % on one parity). Only the **427 torque tap (`0x1AB`) is 50 Hz** (49.7 Hz), and a fork rate loop would not use it. So a 100 Hz rate-feedback term in the fork has a 100 Hz measurement to close on; its delay budget is the openpilot round trip (~20–40 ms) plus the EPS torque-map response, not a sample-rate floor. [EVIDENCE — `r70_v293.npz` timestamps]

1. ⭐ **The rev-2 package is the next action**: fork `66cf4454a` on the device FIRST, then restore
   `toggle-config_V293_torque_mode_r2.json`, restart openpilot (order of §9; checklist in
   `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`). **The drive after it is
   the one that separates the two friction linearisers** — the one thing route 70 structurally could not do.
2. 🛑 **The 1–4 Hz outer-loop line is a live REVERT trigger and it has NOT been addressed by anything yet.**
   3.547 deg at 0–5 m/s, 0.563 at 10–20, a genuine 1.17–1.76 Hz line at 6.5–11.8 dB prominence, rate-channel
   content 4.8–11.6× every reference. The pre-registration's disposition is *the fix is the fork side, not
   the firmware*, and §7's flat angle-domain loop gain says the same. **Rev 2 must be scored against it
   first, and it is the reason the next drive is still not a symptom drive.**
3. 🛑 **The in-loop class: is it closed or not?** The terminal null sentence's antecedent was *amplitude and
   ring-down UNCHANGED with the loop open*. What was measured is a ring at **×0.434 amplitude on 1.1 % of
   windows against 9.8–20.9 %**, at **17.89 Hz instead of 20.0**, on **n = 19** windows — a marginal miss of
   its own ≤ ×0.40 clause, not a null. **[BELIEF] This needs an explicit adjudication rather than inheriting
   the scorer's header line**, and the thinness cuts both ways.
4. ⚠ **The 10.55 Hz line at +3.81 dB was never gated.** `STATE.md` named "a 10–18 Hz line" as a revert
   trigger; the scorer gated the 13–17 Hz band (×1.03, pass). r70 sits above all three reference routes
   (+1.83 to +2.84 dB) and below V292's worst (+6.33). **Decide whether this fires the trigger, and gate the
   LINE, not only the band, in scorer v2.**
5. ⭐ **The engaged-attributable excess moved from 18–22 Hz down to 9–17 Hz** on the drive-controlled measure
   (9–13 ×2.98 and 13–17 ×1.75 of r6c's, while 18–22 fell to ×0.55). That is a change of *shape*, not only
   of level, and it has not been explained. It is probably the same object as item 4.
6. **Fix the `f/D` gate in `V293-FLIGHT-READ-HOWTO.md`** before it is used to reject a future drive. It
   should test the slope or `D_future − f`. [Flagged by both the plant study and the fork read.]
7. **The `<8 m/s` band is thin and estimator-dependent** (151.6 s engaged but no clean 10 s window survives
   the override buffer, because the driver touched the wheel 175 times), and **the 8–15 m/s spring constant
   moves ×2.3 between estimator settings** — the one cell the analysis explicitly will not defend as a single
   number. A quieter low-speed stretch would close both.
8. **Only 3 lane changes and 6 roundabout episodes** — those rows are anecdotes with numbers attached.
9. **The two cereal slot collisions (`@137`, `@116`) are still in the kit's own schema** and were worked
   around with a patched copy. Fix at the next tooling pass, or every future kit decoder reading a fork rlog
   silently mis-decodes.
10. ⭐ **The taper axis question is CLOSED by the wire** — it is the `|bar|>>5` reading, not km/h (§2). Open
    item 3 of the previous handoff can be retired, and the derated-rail scare with it.
11. **The IMU remains the top missing instrument.** Nothing so far separates road from rack from motor, and
    §6's overshoot finding is one of the places that costs: the two surviving readings (a stiction release
    and the fixed 0.30 m/s² offset) are not separable without it.
12. **Carried from the V292 close-out and still open**: `gp-0x6806`'s engaged state; the r26 base-assist arm
    `0xC6444` moving with the `0x3AA96` gate; `0xC61C0`/`C2`/`C4` still without a lineage entry; and the B
    adversary's six tool and document defects (its §9), each of which can silently corrupt a later result.
