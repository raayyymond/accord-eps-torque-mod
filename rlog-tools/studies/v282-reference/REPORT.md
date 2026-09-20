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
