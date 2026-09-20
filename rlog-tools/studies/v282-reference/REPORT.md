# V282 as the reference for "good" — torque mode (V293) compared

2026-09-17. Workflow `wf_1d953145-061`: 5 analysis streams, every finding attacked on 3 lenses (33 findings: 18 held,
15 fell), completeness critic, 4 gap fills, synthesis. The orchestrator then re-derived the decision-bearing numbers
(`orch_crux.py`, `orch_observer_work.py`). Tags: **[O]** orchestrator re-derived · **[S]** survived verification ·
**[G]** gap fill, not adversarially verified.

## Routes

| group | routes (counter--hash) | EPS | fork |
|---|---|---|---|
| V282 (reference) | 64--ce6b0b0ebb, 65--b9f78988bd, 6c--2bc842dbac | V282 rate servo | LAF 6.0, Kp 0.9, rate-plant FF |
| V282old | 39--f56039af87, 3a--283a39a1d6, 3c--927965c2b4 | V282 | older fork, LAF 2.1–4.0 |
| T64 / T64B | 6c--68c6e94b17, 6d--05e83bb04f / 6e--6ca3e014fd | V293 torque | rev 6.4 / + HoldLevel off |
| T5 / T4 | 76--d0b7ea7e4d / 75--6c8687d5bd | V293 | rev 5 / rev 4 |

Attribution (EVIDENCE): r64/r65/r6c fly after the 2026-09-09 revert to V282 and before V292/V293 on 2026-09-13; their
0x14A b4[3:7] code family matches documented V282 routes and differs from V288/V289/V292.

## What good looks like, and the gap

**1. Wheel shake is the clearest separator** [O][S]. 1.8–3.5 Hz steering-rate RMS, 10 s blocks, matched speed × |angle|,
route-cluster bootstrap. Ratio to V282:

| speed m/s, \|angle\| 0–5° | V282 deg/s | V282old | T64 | T64B | T5 | T4 |
|---|---|---|---|---|---|---|
| 0–8 | 0.64 | ×1.1 | ×1.8 [1.0,3.3] | ×4.0 | — | ×4.0 |
| 8–15 | 0.39 | ×1.3 | ×3.1 [2.6,3.4] | ×5.4 | ×6.5 | ×5.8 |
| 15–22 | 0.25 | ×0.9 | ×3.1 [3.0,3.5] | ×4.4 | ×4.4 | ×5.8 |
| >22 | 0.20 | ×1.2 | ×2.6 [2.4,3.3] | ×5.2 | ×3.4 | ×3.3 |

Same EPS with an older fork reads ×1 → it belongs to the torque-mode EPS, not the fork version. It grows with angle and
transient size: ×10 in rate-transient events below 15 m/s, ×4–12 hands-off above 15° [S]. Rev 6.4 is the least shaky
torque rev. Peak 2.5–3.0 Hz [G]. Not the Honda rate limiter (binds less on torque than on V282) [S].

**2. Highway tracking** [O]. |H| model → livePose yaw·v, ≥15 m/s, runs ≥41 s:

| band Hz | V282 | V282old | T64 | T64B | T5 | T4 |
|---|---|---|---|---|---|---|
| 0.08–0.25 | 0.89 | 1.37 | 1.09 | 0.97 | 1.05 | 0.98 |
| 0.15–0.30 | 0.90 | 1.34 | 1.17 | 1.07 | 1.05 | 1.02 |
| 0.30–0.60 | 1.12 | 1.45 | 1.31 | 1.65 | 1.25 | 1.53 |

V282 was slightly soft on small corrections and was not called loose. V282old over-delivered on the same EPS, so gain
alone is fork-dependent. ⚠ T64B/T5/T4 are single routes on different roads — weak cross-rev evidence.

**3. High-jerk events ≥15 m/s** [S]. V282: event gain 0.95–0.99, settles in 0.55–0.9 s, error at 1.5–2.5 s ≈ 0.
T64: gain 1.29, still +14% of the step at 1.5–2.5 s, not settled by 2.5 s; drifting the wrong way before release peaks in
42–47% of events vs 4–14%. Post-peak shake burst ×4 V282's.

**4. Stick-slip** [S]. Jump after a dwell, p90: 3.6° vs 1.4° below 15 m/s; 12.6° vs 1.5° below 8 m/s.

**5. Timing** [G]. +0.19 s behind V282 at each build's logged lead; +0.09 s [−0.02,+0.13] at a common lead. The extra lag is
concentrated on small corrections (+0.22–0.25 s at 0.15–0.3 Hz), ~0 on large ones — slow dynamics, not the round trip.

**6. No gap** in steady large lateral accel (0.94–1.13 in every group) [S].

**7. Self-centring (note 3) is untested**, not absent: no V282 low-speed hands-off large-angle turns exist to compare.

## Mechanism for the shake at speed [O]

- **Command → wheel acceleration latency: 30 ms** on all five torque routes (xcorr, 1–6 Hz); controls latency ~1 ms.
- **The disturbance observer injects energy into the 1.5–3.5 Hz band.** Logged `accordObserverTorque` (fork schema),
  b_eq = −⟨T(t−τ), rate⟩/⟨rate,rate⟩, >0 damps:

| route | speed | observer @30 ms | whole command @30 ms |
|---|---|---|---|
| T64 6c | ≥15 | −3.93e-4 | +0.12e-4 |
| T64 6d | ≥15 | −3.44e-4 | +2.26e-4 |
| T64B 6e | ≥15 | −3.54e-4 | +2.03e-4 |
| T5 76 | ≥15 | −3.31e-4 | +1.12e-4 |
| all | 8–15 | −2.2 to −2.4e-4 | +4.0 to +5.9e-4 |

  Feeds at every delay 0–120 ms. At ≥15 m/s it cancels most of the damping the rest of the command provides.
  ⚠ `latcontrol_torque.py:850` logs `-accord_dob_torque`; the orchestrator's first pass missed that and read the sign backwards.
- Counter-evidence: rev 4 (no observer) was not less shaky than rev 5 — confounded by rev 4's 40% lower rate-loop gain.
- The closed-loop simulator FAILS validation (0/13 band rankings, shake under-predicted ×2–3). No doses from it.

## Next drive: ARM-D — observer off

`analysis-2020accord/reference/toggle-config_V293_r64_ARM-D_observer-off.json` — rev 6.4 as flown, `AccordDobHz 0.6 → 0.0`,
exactly one change (asserted). No code change: `HondaAccordDisturbanceObserver.update` returns 0 when `f_hz <= 0`.

- **Targets:** wheel shake at ≥8 m/s; unsettled high-jerk events; possibly the straight-road over-gain (note 2).
- **Readout:** matched 1.8–3.5 Hz steering-rate RMS vs T64 (confirm if < 0.8× with CI excluding 1); straight-road |H|
  0.08–0.25 Hz vs T64 1.09 / V282 0.89; event gain and 1.5–2.5 s error.
- **Risk (BELIEF, stated before the drive):** the observer removes crown and hold error; without it only Ki 0.3 does → loose on
  long bends or crowned roads, the outcome ranked worst. Guard: 0.05–0.15 Hz gain below V282's 0.86, or the event error at
  1.5–2.5 s going negative. Fallback if loose: rev 4's Ki schedule (`AccordTorqueKiHigh`), a separate drive.
- **Drive content:** ≥300 s straight motorway in runs ≥51 s; bends at 15–22 and >22 m/s; one held on-ramp; some 8–15 m/s turns.

## Not doing

HoldLevel off (flown: worse in band, more shake) · ARM-C rate gain 1.0 (saturates below 8 m/s per the fork's own record) ·
friction-hysteresis cuts before ARM-D reads · rate-loop gain changes (sign depends on delay; rev 4's lower gain showed no
benefit) · new terms (Smith predictor, inertia FF) ranked on the failed simulator · anything aimed at note 3 without a
reference · firmware changes.

## Unknowns

- Mechanism of the shake and stick-slip **below 8 m/s**, where 89% of large rate transients occur.
- Whether the operator felt V282old's drives were smooth (gain 1.3–1.5 on the same EPS).
- Plant Coulomb friction: 0.018–0.024 by equation error vs 0.011–0.020 in fork comments.
- Gap fills (timing budget, low-speed reference, straight-road weave, texture term direction) are not adversarially verified.

## Instrument facts

- `carState.yawRate` is 0 on all 11 routes — use livePose yaw·v (corr 0.986–0.995 with actualLateralAccel).
- `v282cmp.event_metrics` lag is biased toward 0 on step windows.
- The fork's `cereal/car.capnp` is a git symlink on Windows; pycapnp crashes on it. Use `fill_straightroad/forkparse.py`.
- 0xE4 is sent on bus 1 on this car; `e4 ≈ −4089 × pid_log.output`.


## Loop delay, resolved (2026-09-19) — and two of my own claims withdrawn

Workflow `wf_eae14cc9-dc0`: four independent estimators, each required to recover a known 30 ms and 60 ms on a synthetic
plant driven by the real logged command before its real-data number counted; then adjudication and an adversarial pass that
re-derived the load-bearing legs by its own methods.

| quantity | value | grade |
|---|---|---|
| D_ctl (measured sample -> its command on the bus) | **11.0 ms** [10.9, 11.1], flat in speed, same on V282 | EVIDENCE |
| D_act floor at 2.5 Hz (0xE4 -> effect in carState) | **43.3 ms** = 24.8 ms transport + a 5 Hz pole | EVIDENCE for the legs it covers |
| **D_loop at 2.5 Hz** | **54.3 ms floor; 72 ms if the unmeasured post-tap stage is ~18 ms. Working bracket 55-75, point 65.** | EVIDENCE + BELIEF |

- ⭐ **WITHDRAWN: my 30 ms.** It was the peak of a 1-6 Hz cross-correlation of command against steering acceleration, which
  equals the delay only if inertia dominates that band. It does not (the spring mode sits at 0.9-2.1 Hz inside it). Put a
  KNOWN 30 ms through the same recipe and it returns **1 ms at J=1e-3 and 127 ms at J=8e-5**. The estimator also fails once
  feedback and road disturbance are both present, which is how the car actually runs. It is a real plant-phase statistic, not
  a delay.
- **The fork's own 46-61 ms comment is essentially confirmed** — right in structure, mis-splitting ~5 ms in two legs, and the
  best of the three inherited numbers. The measurement vindicates it rather than revising it.
- ⭐ **WITHDRAWN: my inertia finding.** The cloud-session replay fit J = 8e-4..2e-3. Two estimators with passing controls put
  **J = 5.7-7.3e-5 in every speed bin and band**, so the fork's `HONDA_ACCORD_EPS_INERTIA = 8e-5` is right within 25% and my
  figure was ~15x too large. It was marked BELIEF and never acted on. The same fits put b at 7.1e-4 (<8 m/s) falling ~10x by
  >=15 m/s, which also conflicts with the earlier "identified world b = 0.0018-0.0049"; unresolved, and the delay error in
  that replay is the likely cause.
- The 427-tap fit independently recovered the firmware's own output-lag cell (992/1024 = 5.05 Hz).

### What the delay does to the low-speed rate-loop lever

Fraction of `AccordRateLoopGain` that arrives as real rate-opposing damping, through D_loop in series with the 0.01 s rate filter:

| D_loop @2.5 Hz | 1.8 Hz | 2.5 Hz | 3.5 Hz | 5 Hz | 6 Hz | damps below |
|---|---|---|---|---|---|---|
| 54.3 (floor) | +0.69 | **+0.47** | +0.16 | -0.20 | -0.34 | 4.08 Hz |
| 72.3 (X=18 ms) | +0.55 | **+0.24** | -0.16 | -0.51 | -0.57 | 3.08 Hz |
| a hypothetical 30 ms | +0.89 | +0.80 | +0.63 | +0.30 | +0.07 | 6.33 Hz |

Independently reproduced by the adversary from its own measured FIR (+0.50 / +0.27 at the two brackets, boundary 4.06 / 3.11 Hz).

**Verdict: a weak lever, not a dead one** — and the adversary was right to say the clean "dead" reading rests on the
unmeasured 12-18 ms, not on the floor. It delivers 24-47% of nominal damping at the shake frequency, de-damps 4-6 Hz at every
D_loop in the bracket, and the gain margin permits at most about x1.5 (0.0006 -> 0.0009). The pre-registered gate said
~30 ms means room and ~60 ms closes it; the measurement landed on the closing side, so the low-speed candidate becomes
reference shaping below 8 m/s (no added loop gain, delay-independent, reach ceiling about half the shake).

Two fork constants re-read against the measurement: `HONDA_ACCORD_RATE_LOOP_RC = 0.01 s` **stands** (rev 5's 0.03 -> 0.01 was
right, if slightly under-done). The comment "at 0.0012 it would cross" is **~2x pessimistic**: |L| at the 3.5-4.9 Hz crossing
is 0.34-0.57 at 0.0012, i.e. gain margin 1.8-2.9, not a crossing.

### ARM-D survives the delay question

The logged observer torque feeds the 1.5-3.5 Hz band in **64 of 64 cells** — every tau from 0 to 120 ms, every speed bin,
all four observer routes, with positive controls on the estimator. So ARM-D's rationale never depended on which delay was
right. It is far stronger at speed (b_eq -2.5 to -3.4e-4 at >=15 m/s) than below 8 m/s (-0.2 to -1.4e-4), which is why it is
a highway/mid-speed lever and why no low-speed arm can share its drive.

⚠ Read `orch_observer_work.py`'s observer column only. Its "total cmd" column was challenged as sign-inconsistent; I checked
and both columns are in the +left frame (cs_out = -output_torque = +left, confirmed by corr(e4, acceleration) < 0 with
e4 = -4089*cs_out), so the columns agree — but at the measured 55-75 ms, not the 30 ms I first used, that column reads the
whole command as FEEDING the band at >=15 m/s (-0.5 to -2.9e-4), which strengthens ARM-D rather than weakening it.

---

# The low-speed outward deficit, resolved (2026-09-19) — and a retraction of my own, one commit old

Four candidate low-speed levers died today; the underlying defect they were aiming at turned out to be real,
additive, and **not reachable by any existing toggle**. Every number below is EVIDENCE, hand-checked by the
orchestrator in `lowspeed/a_stickslip/orch_crux_check.py` and `orch_crux_check2.py`, each gated on reproducing
`ss_centring_fit`'s five coefficients to <5e-7 before anything else was trusted.

## 🛑 RETRACTED, same day: "the 0.020 intercept does not exist as a constant"

Commit `05fe5ac` claimed the intercept was a parameterisation artefact because the band centre "spans 454x with
angle". **That reading was wrong, and it was wrong in a specific, instructive way.** The 454x was driven entirely
by the first quintile straddling zero, and the quantity I binned had a *linear* `k*|angle|` already subtracted —
0.056 torque at 10 deg, steeper than the fork's own map. Against the map itself the picture is different:

| \|angle\| (deg) | n_aw/n_tw | S (no fit) | levelled MAP | SHORTFALL | required MULT | F |
|---|---|---|---|---|---|---|
| 0.0 – 0.6 | 16/10 | +0.0037 | −0.0005 | +0.0043 | — (map ~0) | +0.0368 |
| 0.6 – 2.5 | 22/38 | +0.0259 | +0.0028 | **+0.0231** | **9.2x** | +0.0353 |
| 2.5 – 10  | 11/37 | +0.0555 | +0.0113 | **+0.0442** | **4.9x** | +0.0273 |
| >10       | 3/8   | +0.1051 | +0.0716 | +0.0335 | **1.5x** | +0.0329 |

`S = (median u_away + median u_toward)/2` with `u = cmd*sign(angle)` needs **no fit, no k, no c, no episode
selection** — outward breakaways sit on the band's upper edge `S+F`, inward on the lower `S-F`, so the average is
the centre by construction. The map is recomputed per route honouring its own flown `AccordHoldLevel`
(6c/6d ON, 6e/75/76 off — read from each route's params, not from labels).

**So the additive deficit is real and well determined where the data is thickest: +0.0231 at 0.6–2.5 deg.**
What does *not* exist is angle-*proportionality* — and that is the finding that matters, because it kills a
different set of levers than I thought.

## The required multiplier spans 9.2x → 1.5x — so every multiplicative lever is DOMINATED

Not merely imprecise: **dominated**. Sized for 1 deg it over-holds several-fold at 8; sized for 8 deg it delivers
a fraction of what 1 deg needs. That disqualifies `AccordHoldLevel`, the `HONDA_ACCORD_HOLD_K_V` schedule and
`AccordEpsSpringScale` on shape alone, at any dose. The additive shortfall is the stabler parameterisation, and
it is the one the remedy must use.

## Nothing winds during the stick — the integrators only CARRY the deficit

Median change from dwell start to breakaway, outward frame:

| \|angle\| (deg) | n | d_dob | d_I | d_cmd | cmd @ dwell start |
|---|---|---|---|---|---|
| 0.0 – 0.6 | 26 | **+0.0000** | +0.0005 | +0.0119 | +0.0182 |
| 0.6 – 2.5 | 60 | **+0.0000** | +0.0012 | −0.0144 | +0.0249 |
| 2.5 – 10  | 48 | **+0.0000** | +0.0007 | −0.0341 | +0.0793 |

The command is **already at full level when the dwell starts** and then *decays*. The observer contributes
exactly zero change and the integrator ~0.001, against a centre of 0.02–0.09. ⇒ The deficit is a **STANDING
condition the stick does not create**; "an integrator winding on the deficit during the stick" is dead as a
*cause*. Which integrator carries it is set only by which one is running: route 75 flew the observer OFF
(no `AccordDobHz` key ⇒ `update` returns 0) and its PID's I carries the same amount alone.

## 🛑 The 0.033 "Coulomb half-width" is NOT a Coulomb magnitude

Same instants, matched angle 0.6–2.5 deg:

| instant | S | F |
|---|---|---|
| dwell start | +0.0234 | **+0.0030** |
| start + 25% | +0.0246 | +0.0048 |
| start + 50% | +0.0233 | +0.0073 |
| breakaway−3 | +0.0259 | **+0.0353** |
| breakaway | +0.0270 | +0.0376 |

**S holds while F grows twelve-fold.** So F at detection is an upper bound containing the command's overshoot
past the true edge plus the 0.3 deg detector lag — it is not the friction. This retracts the other half of
`05fe5ac`: "the friction-shaped quantity is the flat 0.033 half-width" is not supported, and **`AccordFrictionHyst`
must not be re-sized against 0.033** (the "0.015 = 45% of measured" framing is void). True Coulomb is somewhere
between the fork's separately identified 0.010–0.012 and 0.030; unresolved.

## ⭐ Why the intercept is missing: the fork's own supplier does not point the right way

`latcontrol_vehicle_tunes.py:227` states the map "was fitted with a static-friction intercept of 0.020 torque,
which is NOT in the table: the hysteresis feedforward (AccordFrictionHyst) supplies it in the direction of the
last desired motion." `HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020` at `:273` is defined and **read by no code**.

Measured, z at breakaway projected into the outward frame — the frame the deficit lives in:

| route | n | median z_outward | median \|z\| |
|---|---|---|---|
| 6c | 17 | −0.0066 | 0.0106 |
| 6d | 17 | +0.0012 | 0.0088 |
| 6e | 45 | −0.0030 | 0.0101 |
| 75 | 53 | −0.0038 | 0.0073 |
| 76 | 13 | −0.0032 | 0.0140 |
| **pooled** | 145 | **−0.0038** CI [−0.0060, −0.0030] | 0.0095 |

**The term is running — |z| median 0.0095 — and its outward-frame contribution is ~0 or the wrong sign, on 5/5
routes.** It is keyed on *desired-angle motion*, and a dwell is *defined* by the demand moving, so it points
wherever the demand points, not outward. The hold feedforward supplies only 20–35% of the command that actually
holds the wheel at 2–8 m/s; the rest is carried by whichever integrator is enabled.

## What this licenses, and what it does not

- The remedy's shape is settled: **additive, odd in desired angle, saturating, knee below ~1 deg**, ~+0.021 at
  0.6–2.5 deg, near zero below 0.4 deg (measured requirement there +0.0006). The residue above 2.5 deg
  (0.031–0.048) is **not separable from a slope excess** and should be left to the integrator until measured
  densely at 3–15 deg, where n thins to 6 away-episodes.
- **No existing toggle has this parity** ⇒ a small fork code change, not a toggle config. `AccordFrictionHyst`
  is the wrong frame; `AccordDobHz` / `AccordTorqueKi` change who pays and how fast, not whether.
- 🛑 **An unsettled DESIGN question comes before any drive:** `get_honda_accord_hold_torque` is *also* the
  observer's internal model and the observer is called with the **measured** angle. Put the term inside that
  function and it becomes a near-relay inside a loop whose DC gain is ~1 above 6 m/s — the class that already
  produced route 71's 2.34 Hz limit cycle. Leave it out and the observer reads the raise as a disturbance and
  cancels it inside its 0.6 Hz corner. The design must state which, and show the relay margin at zero angle.
- 🛑 **The `AccordHoldLevel` contrast is struck from the plan — it is an IDENTITY, not an experiment.** S is a
  property of the car, so turning the level off moves `S − map` by exactly +0.15*map with no information about
  cause. Measured move +0.0004 against a within-arm route scatter of 0.021 (19x). No number of repeats fixes it.

## Four levers closed today, for the record

| lever | why it died |
|---|---|
| `AccordFFRateGain` 0.5 → 2.0 | ceiling 0.60 below 8 m/s; toggle clamped at 1.5; sized on dwells where 4x the gain moves the peak 5%, while the whole effect lands on the 7% of frames that are transients |
| hysteresis (ceiling, band) | slope-bound; full coverage needs 5.7x hold stiffness; best permitted reaches 46% |
| symmetric `0.020*sign(angle)` intercept | on the intercept model it moves error between halves; and inward travel already exceeds outward (0.0374 vs 0.0262, 5/5 routes) |
| one-sided outward term | null control void (28% of returns take ≥25% dose *inward* via the sign re-arm); adds x1.16 to the command's 1.8–3.5 Hz RMS; `s_a` is flat 1.000 from 4 to 400 deg so it has no large-angle taper at all; delivers exactly 0.000 on the 62 frames where it is at full value, because they are already railed |

## Carried forward: the actuator is already saturating

On the flown config, below 8 m/s, the total command rails **16 times / 0.65 s**, longest episode 0.21 s, 98–100%
of episodes at |wheel angle| > 30 deg (median 166–300). At those frames the feedforward carries 1.00–1.05 of the
command against P's 0.11–0.13. For each episode's duration the output is not a function of demand or error.
This is measured on routes already driven, in the regime the operator describes as jerky and not gradual, and
**no lever discussed today addresses it** — most would deepen it.
