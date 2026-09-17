# rev 6.4 measured against the goal — routes 6c / 6d

Session 2026-09-17. Goal: *match the model's desired lateral acceleration as closely as the fork
can, across all environments.*

Routes `0000006c` / `0000006d`, both `gitCommit 84766cdc` = rev 6.4, fetched through the **open**
comma API (`https://api.comma.ai/v1/route/<dongle>|<route>/files` needs no auth — this replaces the
Chrome-driving `fetch-rlogs` skill). 1185 s usable engaged, against route 76's 488 s.
Route 76 flew **rev 5** (`e44b6cd3`), not rev 6.4 — every earlier "rev 6.4" claim built on it was
an extrapolation.

## The headline (EVIDENCE)

Rev 6.4 **over-delivers** against the model's demand on the highway:

| band | rev 6.4 | coh | split-half | rev 5 |
|---|---|---|---|---|
| 0.15–0.30 Hz | **1.275** | 0.96 | 1.22 / 1.36 | 1.092 |
| 0.30–0.60 Hz | **1.333** | 0.91 | 1.25 / 1.24 | 1.118 |

Goal is 1.000. Confirmed four independent ways: cross-spectral |H|, band-passed time-domain
regression (agrees via `|H|·cos φ`), an independent analysis stream, and 3/3 adversarial verifiers
(all `CONFIRMED_ON_REV64`). A 0.29 s delay control validated the estimator; the naive
phasor-averaged version is biased low above ~1 Hz and must not be used there.

Rev 6.4's *absolute* band error is nonetheless **2.5× smaller** than rev 5's (0.027 vs 0.075 m/s²).
The residual is systematic overshoot rather than random mistracking — which is what reads as a slow weave.

## Regime map (EVIDENCE) — where the operator's notes actually live

Large angles and rate transients are a **low-speed** phenomenon in his driving:

| speed | usable | \|angle\| p99 | hold-map delivery | share of top-3% rate frames |
|---|---|---|---|---|
| 5–8 | 75 s | 181° | 0.688 | 89% (below 8 m/s) |
| 8–15 | 379 s | 63–97° | 0.73–0.80 | 10.5% |
| 15–22 | 326 s | 10–11° | 0.97–0.98 | 0.4% |
| 22–34 | 268 s | 5° | 0.99 | 0.1% |

Notes 3/4/5 (caster, jerk, rate transients) are **below 15 m/s**. Note 2 (5–10 s weave) is highway.
No route we own has a sustained >25° hold above 15 m/s, so the hold-map saturation stays
**unidentified at speed** — the next drive needs one (a held on-ramp) or any large-angle change is
uninterpretable.

Low-speed band metrics have coherence 0.08–0.50: a linear band metric does **not** apply there.
Use the instruments instead.

## Attribution — OPEN

The flown-config diff (rev 5 → rev 6.4) leaves only four lateral-relevant differences:
`AccordHoldLevel` (absent → on), `AccordFrictionHystBand` (absent → on), `AccordRefFilter`
(0.12 → 0.06), `AccordDither` (absent → 0.0, off). `AccordRateLoopGain` was **already 0.001** on
route 76, so it cannot explain the change (it is still 1.67× the module default).

The shaping stage itself measures 1.02–1.04, so the ref-filter change is not the cause.
Reconstructing the feedforward to ablate `AccordHoldLevel` **failed its validation gate**
(corr 0.74, needed 0.90) because `pid_log.f` folds in the friction hysteresis, rate loop and observer.

**The decisive experiment is a toggle, not an analysis:** fly
`analysis-2020accord/reference/toggle-config_V293_r64_ARM-B_holdlevel-off.json` — identical to what
flew except `AccordHoldLevel` off, asserted to be exactly one difference.

## Plant identification (EVIDENCE)

The "light damping" world (`b = 0.0006`) is **falsified** against the identified world
(`b = 0.0018–0.0049`): per-run bootstrap on a 0.25 s torque replay, 95% CI [+1.18, +3.97] deg,
ident wins 100% of resamples. Rev 6.4's headline gains were quoted in the light world; the car is
the identified one.

Fitted per speed band the plant beats a constant-velocity baseline by 24–29%. Inertia fits
8e-4–2e-3 against the bench's 8e-5 and is genuinely U-shaped, **but** it drifts 20× with horizon
above 22 m/s and the route-71 limit-cycle reconciliation fails — so it is **BELIEF, not actionable**.

⚠ The design bench (`smallsig_simlib`) had **never** been compared to route data: 24 scripts import
it, none loads a route. `smallsig_33_validate.py` checks it against its own formula.

## Layout

- `instruments/` — the three metrics notes 3/4/5 had none of: `instr_hold_error`,
  `instr_rate_tracking`, `instr_jerk`, plus `instr_common`. Each carries a positive control.
  ⚠ They report against **both** `cs_la_des` (the shaped setpoint) and the model demand
  (`cs_des_curv·v²`) — `pid_log.desiredLateralAccel` is post-ref-filter, so a metric built on it
  measures tracking of the controller's own setpoint, not of the model.
- `scripts/` — `build_cache_rev64.py` rebuilds the caches from rlogs; `rev64_*` are the goal
  measurements in order; `orch_*` are the plant-identification and bench-replay work;
  `make_ab_config.py` emits the A/B toggle configs.
- `results/` — instrument output and all 33 findings from the diagnostic streams.

Caches live under `_scratch/cache/tau/` (gitignored, regenerate with `build_cache_rev64.py`).

## Adversarial verification — 33 findings, 18 held, 15 overturned

Every finding was attacked on three independent lenses, all briefed with the rev 6.4 data the
original streams did not have. Change findings were attacked for false positives (arithmetic,
premise/code-path, attribution); nulls were attacked for false **negatives** (statistical power,
regime scope, alternative method). Verdicts in `results/verdict_tally.json`.

**Every proposed rev 7 constant change was overturned.** `hold-level-double-count` (3/3),
`ff-stiffness-collapse-large-angle` (3/3), `holdsat-floor-fix` (3/3),
`viscous-term-never-got-the-level-correction` (3/3), `rate-ff-half-globally` (2/3),
`ff-rate-filter-costs-phase-not-magnitude` (2/3). The diagnosis is solid; the prescriptions are not.
**There is no rev 7 to ship from this session.**

`hold-level-double-count` is the instructive one: its headline "1.19× too stiff" came from dividing
a **sum of magnitudes** by a **real part** — different quantities. Under any self-consistent framing
the number is 0.92–1.04, i.e. no over-stiffness, and the celebrated "two unrelated estimators
agreeing to within 2%" was an artifact of that mismatch. What survives is only the *direction*:
the hold level, not the band schedule, is where in-band stiffness moved (101% vs −1% of the
in-phase rise). ⚠ Its k_TRUE is identified in **closed loop** from a signal containing the
feedforward under test, so it cannot by construction show the model is stiffer than the plant.

**Four of six nulls fell** — the reason to verify nulls at all:
- `ratelimit-falsified` (3/3) — the null pooled all engaged frames, dominated by highway where the
  limiter never binds. Conditioned on angle, the Honda rate limiter binds in **0.55% of frames at
  10–20°** vs the 0.094% the pooled figure showed. Measured on rev 5 only; rev 6.4 was simulated.
- `no-inertia-term-in-ff` (3/3) — "only 12% of the deficit" was computed for ≥8 m/s. On rev 6.4,
  J·acc is **22% at 5–8 m/s and 44% at 0–5 m/s**, the regime holding 96% of large transients.
- `physics-says-no-saturation-at-20deg` (2/2) — a steady-state Fiala curve never checked against
  measured response. Event-based measurement at 20–22° gives 0.78–0.94 where physics says 0.92–0.99.
- `instr-suite-built` (3/3) — the 11 positive controls only test synthetic injected defects.
  ⚠ **On real rev 6.4 data the instruments have no power in the large-angle bins** (r6c: 0.0 s of
  quasi-static data above 10°). They are correct code, not yet useful measurements.

**What held and is decision-bearing:** `midband-overdelivery` (0/3, 3/3 CONFIRMED_ON_REV64) and
`fine-band-also-over` (1/3, 3/3) — the defect is real. `steeringrate-lsb-8x-wrong` (1/3) — the rate
loop reads a **1.0 deg/s LSB** where its comment assumes 0.125. `rateloop-dominates-command-jerk`
(1/3). `cs-la-des-is-the-setpoint-not-the-model` (1/3). `move-limit-never-binds-above-8` (0/3).
`caster-untestable-no-quasi-static-large-angle-data` and `holdsat-unidentified-at-speed` — the
large-angle question cannot be answered by any route we own.
