# ADV-dynamics: pre-registered FAIL criteria (written 2026-09-30, BEFORE any number of mine was computed)

Adversary "dynamics" on the V295 fork toggle config r2 (gated = r1) and r2alt (r1 + AccordTorqueKiHigh 0.8).
Subagent; design-only; nothing sent / flashed / deployed / committed. Fork `Dom 20d24ab79` read-only.

Comparators in every test: **V295 + r1** (drive 1), **V295 + r2alt** (drive 2 candidate), **V294 + r1** (what flew, r71b).

## What a FAIL looks like (any one fires -> the verdict for that config is REFUTED or SURVIVES_WITH_CHANGES as stated)

| id | attack | FAIL if | consequence |
|---|---|---|---|
| X0 | reproduction | my independent outer-loop linearisation (own code from the fork source, not `fc_lib`) differs from the designer's §4 table by > 10 % in Ms, or > max(10 %, 0.3) in GM, or > 10 deg in PM, at any tabled speed on nominal / light_b; OR the designer's r1 lp retrodiction (.840/.865/.586/.764/.917) does not reproduce to 0.005; OR r2alt's 8-22 m/s tracking delta on nominal lp does not reproduce within +-0.015 | REFUTED by default for the unreproduced number |
| X1 | "r2alt = r1 below 8 m/s" | the fork's Ki schedule reads anything other than vEgo with breakpoints (8, 18), or the integrator's stored state makes a speed change produce an output step (i stored un-multiplied), or any other key path differs below 8 m/s | REFUTED for the claim; r2alt's low-speed prediction void |
| X2 | (a) outer margins | r2alt, identified family, any speed 3.1-26.9 m/s, pipe 22 / 42 / 62 ms, relay slope on or off: Ms > 1.6 or GM < 3.0 or PM < 35 deg | REFUTED (r2alt) |
| X3 | (a) light_b | r2alt at 17 / 22 / 26.9 m/s, pipe 22 / 42 / 62 ms: GM < 0.97 x V294+r1's (the flown state) or Ms > 1.10 x V294+r1's | REFUTED (r2alt) |
| X4 | (b) relay DF | any member x speed (3-27 m/s) x pipe: the loop with the friction relay gain at any fraction k in (0, 2] of its small-signal slope has a DF-predicted limit cycle (Nyquist of L_lin crosses -1/N(A)) for r2alt where r1 has none | REFUTED (r2alt); if r1 too, report it as a standing defect of drive (1) |
| X5 | (b) LSF-inflated low-speed relay | at 3-5 m/s the effective relay slope (F/0.30)(1+lsf/Kp)/LAF-scaled exceeds the slope at which my DF sweep goes marginal on any identified member (i.e. margin < x1.5) | flag for BOTH configs (pre-existing), not r2alt-specific |
| X6 | (b) nonlinear on-centre | time-domain Karnopp replay (zero demand + crown torque) shows a sustained 3-6 Hz chatter (route 73's class) > 0.2 deg p-p, OR a new 0.2-1.5 Hz hunt > 0.5 deg p-p at >= 15 m/s on the identified family (not only light_b), for r2alt where r1 has none | REFUTED (r2alt) if on the identified family; confirm designer's G4 if only light_b |
| X7 | (c) oversteer | r2alt tracking gain > 1.05 or turn-hold > 1.05 in any band, any member (identified + light_b), lp or full | REFUTED (r2alt) |
| X8 | (c) 2.34 Hz class | on light_b at >= 19 m/s on a sustained curve: a 2.0-2.7 Hz line in wheel rate > +3 dB above V295+r1's, or a closed-loop outer pole in 2-2.7 Hz with zeta < 0.10 under r2alt | REFUTED (r2alt) |
| X9 | (d) hard-turn | r2alt's hard-turn 1.6-3 Hz at 15-22 m/s EXCEEDS V294+r1's (the flown state) on nominal or light_b, lp or full -> it gives back ALL of V295's firmware gain there | REFUTED (r2alt) - stronger than the designer's G8, which is vs V295+r1 |
| X10 | (d) 1-5 Hz line | r2alt's 1-5 Hz limit-cycle line > +3 dB above V295+r1 on any member | REFUTED (r2alt) |
| X11 | (e) wind-up | synthetic long curve (1.5-2.5 m/s^2 for 10-20 s at 18-27 m/s, then straight): r2alt's post-curve lateral-accel overshoot (opposite sign) > 1.5 x r1's AND > 0.15 m/s^2 absolute, or its settling time > 2 x r1's | SURVIVES_WITH_CHANGES at most (a warning on the page) unless > 0.3 m/s^2 -> REFUTED |
| X12 | (e) engage / override | the real controller does not reset / freeze the integrator on steeringPressed or inactive in a way that bounds what r2alt's larger Ki can accumulate; or the engage transient with r2alt exceeds r1's by > 20 % | SURVIVES_WITH_CHANGES (a stated risk) |

## What SURVIVES looks like
All of X0-X12 clear for r1 (drive 1 has no new defect) and r2alt fails none beyond the designer's own disclosed G4 (light_b only)
and G8 (vs V295+r1, not vs V294+r1).

## Method rules
- Two methods for every load-bearing number: (1) my own linearisation of the fork law (from the fork source) and the firmware
  lane (from the harness's evidence-exact lane / golden model), and (2) the harness's nonlinear time-domain replay.
- Designer scripts are spot-checked, not trusted.
- Python = `python` (bin_decompile). No CAN, no flash, no deploy, no commit; the fork is read-only.
