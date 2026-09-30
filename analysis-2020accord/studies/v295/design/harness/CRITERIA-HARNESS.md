# V295 design harness — pre-registered gates and tolerances

Subagent `harness`, 2026-09-30. **Written BEFORE any harness number was computed** (only the inputs' reports and
code were read: census, plant, metric, flight, bands, the golden model, the fork at `20d24ab79`). Any later
change to a threshold below is declared in V295-HARNESS.md as POST-HOC with the reason.

## H1 LANE (byte-exact, parametrised)
- H1a: harness lane == golden model (`lkas_fb_lag` + `lkas_rate_pid_tick`), tick for tick on T **and** on E, I, P,
  D, S, y, on >= 50,000 random ticks, over at least: V294 cells; V294 + Ki live (8, 64); V294 + Kd live (128 with
  D clamp 10240); Ki + Kd live together; V282-class (sum operand, e_shift 5, C 46080); random Kp/Kd banks with
  non-flat knots; e_shift 0..5; tapers < 254. **FAIL = any mismatching tick.**
- H1b: the int32 guard must RAISE on a constructed overflow (b above b_max at |x| 12000; a Kp·E product past
  2^31) and must NOT raise on the V294 cells over the whole r71b replay. **FAIL = a positive control that does
  not raise, or a raise on V294.**
- H1c: the harness lane driven by r71b's recorded command + 0x18F rate reproduces the plant study's byte-exact
  march `plib.march` **bit for bit** at 1 kHz (same convention), and the 427 tap to <= 10 counts rms hands-off
  engaged (plib's G1 read 3.64). **FAIL = any mismatch vs plib, or > 10 counts vs the tap.**

## H2 PLANT
- H2a: with kappa off and the same member, the harness plant reproduces `v294_plant.simulate` (open loop and
  closed through Lane294) to <= 1e-9 deg / deg/s on every tick. **FAIL otherwise.**
- H2b: the kappa(angle) option must reproduce the metric agent's measured ratio d(angle)/d(integrated x/8):
  1.16 +- 0.03 on centre (|angle| < 20 deg) and 0.965 +- 0.02 beyond 160 deg, on a synthetic sweep.

## H3 FORK OUTER LOOP (HARD GATE)
- H3a (REAL fork, replay of r71b's logged inputs): over laterally-active frames (torqueState.active),
  torqueState.output R2 >= 0.999 and rms <= 0.003 torque units; p, i, f each R2 >= 0.995; carOutput torque (after
  the 0.03/frame rate limiter) R2 >= 0.999; the 0xE4 count reproduced within +-1 count on >= 99 % of active frames.
  **FAIL = any clause.** A FAIL means the fork model is NOT usable for mode B and V295-HARNESS.md says so first.
- H3b (the vectorised port vs the REAL fork): max |delta| <= 1e-9 on p, i, f, output over the whole replay AND over
  a closed-loop run. **FAIL = the port is not used; the real fork runs instead (slow path).**

## H4 RETRODICTION (mode B = closed loop on the recorded planner demand; mode A = recorded command, exogenous)
Measured values are computed by THE SAME CODE on r71b's recorded signals (and cross-checked against the bands
report's quoted numbers). Per speed band 0-5 / 5-10 / 10-15 / 15-22 / 22+:

| metric | FIT | DIRECTIONAL | NOT FIT |
|---|---|---|---|
| tracking gain act/plan (slope, hands-off, |plan| > 0.3 m/s^2) | abs diff <= 0.05 | sim < 0.97 (reproduces under-delivery) and abs diff <= 0.12 | otherwise |
| turn-hold act/plan (|plan| 0.8-1.5) | abs diff <= 0.06 | abs diff <= 0.15 | otherwise |
| integrator share |i|/(|f|+|p|+|i|) | abs diff <= 0.08 | abs diff <= 0.15 | otherwise |
| 0xE4 command rms (engaged) | ratio in [1/1.15, 1.15] | [1/1.5, 1.5] | otherwise |
| trim/FF rms ratio (the lane's own split) | ratio in [1/1.25, 1.25] | [1/2, 2] | otherwise |
| wheel-rate rms 0.3-1 / 1-3 / 3-8 Hz | ratio in [1/1.3, 1.3] | [1/2, 2] | otherwise |
| 1.6-3 Hz wheel-rate rms in hard turns (|plan| >= 1.5 or |angle| > 60) | ratio in [1/1.5, 1.5] | [1/2.5, 2.5] | otherwise |
| dwell-then-jump events per minute | ratio in [1/3, 3] | [1/10, 10] | otherwise |

**Band verdict.** FIT = tracking gain, turn hold, command rms and 1-3 Hz wheel rate all FIT and no metric NOT
FIT. NOT FIT = tracking gain or turn hold NOT FIT, or >= 3 metrics NOT FIT. Otherwise DIRECTIONAL ONLY. A band
with < 30 s of hands-off engaged exposure (or < 5 s for the hard-turn metric) reports "NOT TESTABLE" for that
metric, never FIT.

**What a harness FAIL looks like (written down so the pass can return it):** mode B does not reproduce the
under-delivery (sim tracking gain >= 0.95 where the drive read 0.80-0.83) at 8-22 m/s, or the command rms is off
by more than x1.5 in two bands, or any member diverges under the V294 cells. If that happens the report's first
line says: "the harness cannot retrodict V294's outer loop; M_DRIVE numbers are not decision-grade".

## H5 SCORING API
- Deterministic: two identical calls give bit-identical dicts (hash printed).
- V293 control (C = 0 -> trim off) must show |trim| == 0 on every tick and M_LOOP |L| == 0.
- The V294 baseline's M_SAFE rail must read 2461 and the as-built b_max 2301 (census values); torque at zero
  command <= 616 (census).
