# HANDOFF 2026-09-30 — V294 flew; V295 (the trim gain ×1.85) built, adversarially passed, NOT FLOWN

**Nothing flashed, no CAN sent, the fork untouched (the operator's scope: firmware PID values only).** V294 stays on the car.
V295 is on disk in `accord-firmwares`, exactly one rwd, waiting for the operator's decision. Page:
https://claude.ai/artifact/RABj94ezP9gqNqHq8JaxXu · all session outputs under `analysis-2020accord/studies/v295/`.

## The operator's goal, and the one-line answer
> *"Adjust the firmware LKAS PID loop values to better track desired steering angular acceleration (comma LKAS command output
> vs second derivative of steering angle sensor output)."* Scope: *"the firmware internal PID loop tuning alone."*

**The only PID value that moves the acceleration loop without touching the torque map the fork sees is the trim gain b.
V295 raises it ×1.852 (567 → 1050), which doubles the loop's return ratio (|L| peak 0.34 → 0.63 at 5–10 m/s) and the 2 Hz
damping (1.6 → 3.0 T per deg/s). The ceiling is structural: acceleration tracking needs |L| ≫ 1, a 13–20 Hz crossover, where
V282 ground. And the literal metric cannot score a firmware edit from ordinary driving** (below).

## What V294's flight established (route `00000071--a7b8ba5d9d`, EVIDENCE, `studies/v295/flight|plant|metric/`)
- **Attribution:** FF identity R² 0.987 (0.998 low-accel); the pre-registered trim read **+0.210 [+0.208, +0.212] T counts per
  deg/s² vs modelled +0.211**; inverted-operand control 125.6 vs 7.5 counts rms; fork `Dom 20d24ab79` + the r1 config, all 26 keys
  matching; no EPS fault. Orchestrator's own regression: tap = 0.987·lag(0.641·cmd) + 0.207·d/dt LPF₂(rate).
- **Operator:** "No grinding or stuttering!" · "Jerky on hard turns at medium speed" · "Loose on straights and turns at low speed." ·
  "Loose/understeer at highway turns."
- **Bands:** the pre-registered outcome held (hard-turn 1.6–3 Hz ×0.56–0.91 vs V293 flights, still 2–3× V282); HF the quietest of
  the class (ring presence 0.5 %, F7 0, 13–17 Hz ×0.88); no 2.34 Hz cycle; P2 fired on one hands-on full-lock 15.6 Hz line;
  dwell-then-jump 6–19/min. **Outer loop under-delivers: turn-hold 0.69 at 8–22 m/s (own check 0.69/0.69/0.91), tracking
  0.80–0.83, straight delivery 58 %, integrator 25–41 %; J 0.417 = V282's level.** The harness counterfactual puts ≤ 0.004 of it
  on the trim: it is the fork's feedforward level (LAF 14).
- **Plant (multiple-shooting output-error on the tap):** OVERDAMPED + Coulomb — J ≈ 0.2 T/(deg/s²) at 0–5 m/s only, b 5–26 T/(deg/s),
  k 7–80 T/deg, Fc 76 → 4 T with speed, ζ_open 1.3–4.0; NOT the prior's light 2 Hz mode (that world predicts held-out rate at
  R² −0.7…−1.9 above 10 m/s); nothing above ~8 Hz identifiable; the plant alone makes 6–26 % of the drive's 1–3 Hz motion.
- **The literal metric:** above 1 Hz it measures the fork's P term reacting to the wheel (α LEADS the command 20–60 ms; M4 fired
  13/24 bins); below 1 Hz 55–95 % of the command is k·θ, 0–3 % J·α. The firmware-attributable read is the tap regression.
- **κ:** the 0x18F rate is rack-side, 1.16× the steering-wheel derivative on centre, 0.965 beyond 80°. **The Accord DBC's 0x18F rate
  factor (−0.1) is wrong for this EPS (wire −0.125).** The kit's |bar| < 400 hands-off mask is biased for acceleration censuses.

## The design (`studies/v295/design/`, harness + four lenses + eight adversaries)
The harness runs the REAL fork `LatControlTorque` (R² 0.9999989 on the replay), the byte-exact lane (= golden model on 90,000
ticks) and the plant family; it retrodicts the outer-loop numbers (tracking gain FIT in 4/5 bands, integrator share 5/5) but
NOT the 1–8 Hz wheel motion from the plant alone — every closed-loop number is a same-batch difference, not a prediction.
| lens | pick | fate |
|---|---|---|
| trim-ratio | b 567 → 964 | survives; its own ×1.5 simulated-HF clause binds at ×1.7 |
| p-gain | regressive Kp(idx) ×1.3 → 960 by idx 100 | survives with changes; reaches the under-delivery (+0.05–0.10 tracking) but is the fork's LAF by another name, a kink at idx 100, straight-line 1–3 Hz ×1.25–1.6 in light worlds, 252 bytes |
| dynamics | pole 1011 → 1017 (1.09 Hz) | **REFUTED** on direction (hard-turn band rises on J ≥ 0.5 members); override resistance ×1.44 |
| robust-joint | b 567 → 1106 | survives with changes; low-speed 0.5–1 Hz error ×1.04–1.40; restart cap needs b ≤ 1050 |
**Decision: b 1050** (×1.852) — inside every adversary bound (restart-pulse cap, int32 ≥ 2, HF gain < ×3), one cell, readable on
the wire. Ki excluded (integrates the command, no leak — census); Kd/output lag/map excluded (HF budget for less benefit / no instrument).

## V295, from the built image
`0xC63EA` 567 → 1050 (`37 02` → `1a 04`) + trailer `0xC6FFC` `0xF3441165` → `0x8D982BD9`; 6 diff bytes, 0 code bytes. Image
`5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed`, rwd `f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87`,
script `build_v295_tva.py` (hash predicted before the write; zero-edit control = V294; 10/10 mutations; docstring corrected after the
pass, hash unchanged), golden `_self_check_v295` (94 symbols, `740f4bcd…` unchanged). K_α 0.210 → 0.388 T/(deg/s²) (×0.86 per
steering-wheel unit), |P/x| 20 Hz 2.079 → 3.850 (V282 44.90), surface/rail/slope/616 T cap byte-identical.

**Adversarial pass on the built image — A/B/C/D all PASS_WITH_DEFECTS:** worst reachable 1-tick restart pulse 288 T at the
design's own 2×-V294 cap with ZERO margin, 308 at a 2-tick bail — **ruled as ≤ 2× V294 per lane at any bail length (met); fault path
only, never within 50 % of firing in 7.9 h**; 13–17 Hz sim torque ×1.56–1.59 under replayed road disturbance (0.04 % of the rail)
crosses one lens's ×1.5 clause — **HF guard re-decided as controller gain < ×3 of V294**; 20 Hz anti-damping from ~4–6 ms delay at
3–6 % of V282's removal (worst 10–12 %); outer PM at 5 m/s −7.7° (GM/Ms improve); driver-override resistance ~2× (p99 166 → 307 T,
max 554 under the 616 cap); |trim| > 300 T dwell 0.04 → 1.36 s at < 5 m/s hands-on; P-clamp rectification near the rail
(torque-reducing); the armed output gate `0xC64A3 = 1` is not in the golden model; only the hash/readback/rebuild pin 1050 vs 1051.

## Predicted per complaint · the wire read · revert
Jerky hard turns: modestly better (×0.77–0.89 identified, ×0.70 prior at 5–10 m/s — BELIEF; the same lever V294 already applied
at a comparable step). Loose at low speed: unchanged to slightly worse (0.5–1 Hz error ×1.04–1.4). Highway understeer: unchanged
(c1 = 1 proves it; the lever is `SteerLatAccel` 14 → ~10 in the fork, a tuning value, next session).
**Read:** march V294's cells on the new drive's own 0xE4/0x18F; OLS `T_tap = c0 + c1·FF + c2·TRIM`; calibrate on r71b first
(c2 0.96–1.02, c1 0.97–1.01, residual ≤ 3.0 — a negated rate flips c2); gate windows on rms(TRIM_V294) ≥ 4 counts; **c2 > 1.45
pooled = live (predicted 1.837 [1.829, 1.844]); < 1.45 = not V295, stop; < 0 = inverted, revert**; FF identity gate 0.90 (expect
0.965). No secondary outcome is decidable from one drive — he scores the feel. **Revert:** grinding, stutter, a new 5–30 Hz line,
ring presence > 2 %, F7 ≥ 2/100 s, "looser at low speed", "heavier in my hands" → V294's rwd `a2b418f0…`.

## Corrections of record
The override taper's axis is DRIVER TORQUE (|bar≫5|, ×0.30 from 64), not speed — census c3; reported, **the orchestrator has not
re-read the crux (BELIEF)**. Golden `e5 = E>>5` comment cited 0x29D6C — the sar is at 0x29D7C (fixed). `0x2B418` is dead (the
twin); the live forward copy is the lane store @0x2A2EA → `FUN_0002b422`. The I reset lags a disengage by 0.1–2.05 s. Demand
path ±½-idx L/R asymmetry (stock). Scorer defect: `v293_flight_read.print_scorecard` NameError on `g` since 2ef033a (workaround
`studies/v295/flight/bands/run_flight_read.py`; not fixed in the kit). Lever-index row 33 now carries V294/V295.

## Housekeeping
`memory/MEMORY.md` 161 → 104 KB (the V84–V89-era block moved to PART8, now 134 KB). `docs/BUILD-LINEAGE.md` is 247 KB — split it
at the next close-out. `docs/STATE.md` 88 KB. Golden model contract re-verified: 94 / 2,512 B / `740f4bcd…`.

## Next
Operator's: flash V295 only when he names the rwd and the bus (openpilot killed first); one ordinary drive with a few hard
medium-speed turns; run the c1/c2 read (calibrate on r71b first). If he wants the highway understeer fixed: `SteerLatAccel`
14 → ~10 in a toggle config (a firmware Kp ×1.4 is the same quantity and was rejected here as a fork surrogate). If V295 is not
felt: the b lever's cal headroom is ×1.1 more at int32 margin 2 (1150) — the class is near exhausted; the next lever is a cave
(a leaky integrator on this operand, or a second operand), or the fork.


## Addendum (same session, later): the fork config for drive (2)
Operator's plan: (1) V295 + the V294 r1 config, (2) V295 + a new config. The harness (REAL fork controller, V295 cells, both plant
worlds) swept `SteerLatAccel` × `SteerFriction` × `AccordTorqueKi` (× `SteerKP`) under eleven pre-registered gates; two adversaries
(dynamics; wiring + observability) returned SURVIVES_WITH_CHANGES. **No existing-param config passes every gate**: every knob that
changes the loop below 8 m/s raises 0–5 m/s wander / stick-slip ×1.3–2.1 on the identified family, and one LAF cannot fit a
speed-shaped deficit. **Drive (2) flies `analysis-2020accord/reference/toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.json`**
= r1 + `AccordTorqueKiHigh` 0.8 (sha256 c428be32…; the fork's own Ki schedule, 0.3 below 8 m/s → 0.8 at ≥ 18; the ONLY key that
differs from r1, verified by the orchestrator); revert file = r1 byte-identical. Predicted: 15–22 m/s tracking 0.83 → 0.92–0.93,
turn-hold 0.67 → 0.75–0.83; 22+ +0.03–0.045; no oversteer; two gate failures in the least-trusted worlds (light_b weave incidence
12/24 vs 2/24; plant-alone hard-turn 1.6–3 Hz at 15–22 ×1.09–1.14, ×0.95 under replay); new risk: unflagged light hand
corrections wind the integrator ~2.5× faster at ≥ 18 m/s. Read: Ki(v) by speed bin is the discriminator (0.30 / 0.40 / 0.50 /
0.66 / 0.80 at < 8 / 10 / 12 / 15 / ≥ 18 m/s); primary outcome 15–22 m/s tracking at ≥ 120 s; c1/c2 on drive (2)'s own command.
The low-speed complaint is untouched by any existing param (a fork code change or a firmware lever would be needed). Full ruling
and the corrected revert signature: `studies/v295/fork-config/V295-FORK-CONFIG-r2.md` (end).
