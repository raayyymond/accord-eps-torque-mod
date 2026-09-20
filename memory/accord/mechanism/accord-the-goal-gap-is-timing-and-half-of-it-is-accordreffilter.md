# The torque-mode gap on the OPERATOR'S GOAL METRIC is TIMING, not gain — and ~half of it is one toggle the V282 reference never had

**Measured 2026-09-20.** Goal: *"Match the model's desired lateral acceleration as closely as the fork across all
possible environments for the torque mode EPS. Compare against recent V282 non torque mode EPS routes as a reference
for what 'good' looks like."* Study: `rlog-tools/studies/v282-reference/hsurface/`. 16 cached routes, 10.2 ks
laterally engaged (V282 4200 s, V282old 1822 s, V293 torque 5989 s); |H| over 4 speed × 6 frequency × 3
demand-amplitude strata, magnitudes averaged per bin (never phasors), coherence + null floor + split-half floor +
route-cluster CI per cell, every headline cell re-measured by a time-domain method sharing no code.

## 🛑 |H| IS THE WRONG SCALAR — rank on in-band tracking error instead

Decomposing in-band error power into `(|H|−1)² + 2|H|(1−cos φ) + incoherent`: at 0.15–0.30 Hz, ≥15 m/s, the **gain
term is 3.0 % of torque mode's total error and 6.1 % of V282's.** Across the 0.15–0.30 Hz row the gain share is
**0–3 % in every speed × amplitude cell** (0–8/A1 aside at 11 %), and the gain *difference* is −0.011 to +0.003 —
zero or in torque mode's favour. V282's 0.89 and torque's 0.96–1.14 are misses of the same size in **opposite
directions**. Use NRMSE (RMS of achieved−desired lateral accel in units of in-band demand RMS); it charges gain,
phase and unexplained motion together, which is what "match as closely as" means.

⚠ **The published event gain "V282 0.95–0.99 vs T64 1.29" DOES NOT REPRODUCE.** Re-run with `v282cmp.jerk_events`
+ `event_metrics` unchanged: V282 median 0.994 (n=38) — that half reproduces — but T64 is **1.090** (n=5), pooled
torque **1.024** (n=40). Only the PEAK RATIO reaches 1.61–1.73, and that is the 1.8–3.5 Hz shake, which this metric
transmits 2–6× more weakly than steering rate does. **Do not carry 1.29 forward.**

## ⭐ `AccordRefFilter` — the largest identified term, and it is a TOGGLE

Two cascaded `FirstOrderFilter`s on the setpoint (`latcontrol_torque.py:164-165, 326`), so group lag = **2·RC** at
low frequency. Default 0.12, bounds 0.0–0.5 (`starpilot_variables.py:836`), **explicit bypass at
`accord_ref_rc > 0.0`** (`:323`) with states kept primed at `:328-329`, so a bypass has no engage transient.

Measured model → logged-shaped-setpoint group lag, each route against **its own flown value from its own initData**:

| flown RF | routes | measured | 2·RC predicts |
|---|---|---|---|
| ABSENT | all 6 V282/V282old + r70 + r71 | **12–18 ms** | — |
| 0.06 | r6c / r6d / r6e (rev 6.4) | **117–124 ms** | 120 |
| 0.12 | r72 / r73 / r75 / r76 | **253 ms** | 239 |

15/15 routes with data agree, zero exceptions, `|H_xz|` 1.01–1.10 ⇒ **pure phase.** Its share of the 0.15–0.60 Hz
tracking-error gap, two independent methods: **47 %** (re-reference the metric to the logged setpoint) and **49 %**
(the torque routes that flew with NO filter read NRMSE 0.638 against V282's 0.434 and the RF revs' 0.849).

🛑 **It DOES NOT EXIST in the reference fork.** `git grep accord_ref_filter` returns **0 hits** at `0f98d8c75` and
`57410c3b` — the commits all three V282 reference routes flew — and 10 hits at the torque commits. This is not a
tuning difference; it is a stage "good" never had. Flown `liveDelay.lateralDelay` 0.200 s on V282 vs 0.274–0.302 s
on the torque revs.

⚠ **At 0.60–1.20 Hz the same toggle acts with the OPPOSITE SIGN** — it currently suppresses the fork's own
reference-stage gain bump. Removing it entirely re-arms ~+7 % of 0.6–1.2 Hz reference gain, **not** the ~+28 % a
naive read gives, because rev 6.4 already carries `HONDA_ACCORD_JERK_LP_HZ = 4.0` which the V282-era commits did
not. (LTI composition of measured legs ⇒ BELIEF.) Hence halve to 0.03, not zero.

## The gap is TWO regimes needing different levers

- **REGIME A — 0.15–0.60 Hz, all speeds, ~86 % of exposure:** a pure **timing** miss of **+140 to +340 ms**. Gain
  share 0–3 %. This is the operator's *loose / overshoot-then-correct* at speed.
- **REGIME B — 0.60–1.20 Hz, large demand, 8–22 m/s, ~17.5 % of exposure:** an **amplification** miss, |H| 1.20 →
  **2.15** at 8–15 m/s (V282 1.20), and the **timing is BETTER**. Excess error power splits +2.35 gain / +1.17
  phase / **+3.14 incoherent** — ~45 % is motion the demand does not explain. **This is the TOP of the
  exposure-weighted ranking and no known lever reaches it.**

**Residual after every named mechanism: ~50 % of the 0.15–0.60 Hz gap and ~100 % of the 0.60–1.20 Hz gap.** After
the RF is divided out the EPS+plant leg is still +105 to +158 ms slower at 0.15–0.30 Hz.

## 🛑 ACTUATOR SATURATION IS FALSIFIED AS AN OWNER — and the contrast is REVERSED

Orchestrator hand-check, 11 routes, `|pid_log.output| ≥ 0.995`, laterally engaged hands-off:

| group | >8 m/s | railed | <8 m/s | railed |
|---|---|---|---|---|
| V282 | 3465.5 s | **0.000 %** | 734.6 s | **2.264 %** |
| V282old | 1343.5 s | 0.001 % | 478.2 s | **2.771 %** |
| T64 (rev 6.4) | 980.6 s | **0.000 %** | 213.0 s | 0.164 % |
| T64B / T4 / T5 | 1519.8 s | 0.000 % | 488.1 s | 0.077 / 0.014 / 0.000 % |

**Zero railed frames above 8 m/s in 2480 s of torque-mode engaged time**, where 79 % of exposure and every readable
Regime-A cell lives. Below 8 m/s **V282 rails 13.8× MORE than rev 6.4.** Its predicted signature is absent too:
|H| *rises* with demand in both builds and the 8–15 m/s lag gap **shrinks** at large demand (+318 ms at A1 → +10 ms
at A3, reproduced time-domain as +340/+150/+20). ⇒ An earlier session promoted railing as the session's best
finding; it owns none of the goal gap. **Caveat on the reversal: LAF ran 6.0 on V282 vs 14.0 on torque, so V282's
rail sits at 0.43× the physical demand — the claim is that torque mode's actuator is essentially NEVER saturated
where the gap lives, not that V282's is worse.**

## The one brief mechanism whose fingerprint SURVIVES, and it extends upward

The **hold-FF additive deficit** ([[accord-lowspeed-hold-ff-is-missing-an-additive-intercept-not-a-stiffness]]):
its signature is a lag penalty confined to SMALL demand, and that is exactly what the map shows — **+318 ms at
8–15 m/s / small demand decaying to ~+10 ms at large demand**, present **up to 15–22 m/s**, not only below 8. An
integrator supplying a standing feedforward term costs precisely that. Signature = EVIDENCE; attribution = BELIEF.
⇒ It should be sized against the 8–15 and 15–22 small-demand cells, where V282 *can* score it, rather than only
against 0–8 m/s dwell data where **no reference exists**.

## 🛑 Traps and non-experiments recorded

- **Requiring every frame of a 20.48 s window inside one speed bin leaves ZERO readable cells below 15 m/s** — not
  for lack of data (7 runs/259 s below 8 m/s, 31 runs/1553 s at 8–15) but because their median speed SPAN is
  9.4–9.6 m/s. Relaxing to "median window speed in bin" lifts coverage 34–41 % → 85.7 %.
- **The missing drive content is HELD-SPEED engaged stretches, not distance.** Resolving 0.15 Hz needs ≥20.5 s
  continuous laterally-engaged hands-off. Ask for ≥6 runs of ≥41 s held inside 8–12 m/s and ≥6 at 4–7 m/s on gentle
  continuous curvature.
- **0–8 m/s above p95 demand 0.3 m/s² (14.4 % of torque exposure) can never be scored** — V282 has 0–2 windows
  there in every band and is no longer flashed.
- **1.20–2.40 Hz is readable but empty of build difference** (V282 |H| 3.567 / NRMSE 4.155 vs torque 3.611 / 4.101).
  2.40–4.00 Hz is a zero-lag planner echo. Do not rank either.
- **Do not rank the torque revs against each other on this metric:** rev 6.4 flew both a different jerk low-pass
  (4.0 Hz) and a different RF (0.06 vs 0.12) from revs 4/5, and the X→Z stage differs between revs by more than the
  revs differ end to end.
- **The input is not exogenous** — `desiredCurvature` is the planner's output *after* lane centering, so every |H|
  here is a closed-loop statistic. The comparison stands; attributing a cell to the EPS alone does not.
- Within-group confounds read from the wire: r6d and r75 silently flew `SteerFriction 0.212` while r6c/r6e/r72/r76
  flew 0.0; r70 flew `AccordRatePlantFF = 0` and `SteerKP 0.3`.

Related: [[accord-lowspeed-actuator-rails-on-large-angle-transients]] ·
[[accord-torque-mode-loop-delay-is-55-75ms-and-xcorr-cannot-measure-it]] ·
[[feedback-fork-side-experiments-are-toggle-configs-not-code]] ·
[[feedback-attribute-the-build-from-the-tap-not-from-the-label]]
