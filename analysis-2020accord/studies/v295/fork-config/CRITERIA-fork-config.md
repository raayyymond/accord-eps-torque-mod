# CRITERIA: the V295 fork toggle config "r2" (written 2026-09-30 15:29 PDT, BEFORE any candidate number)

Subagent `fork-config`. Design only. Nothing is sent, flashed, deployed or committed; the fork is read-only.

Firmware under every candidate: **V295 cells** = V294 image cells with `fb_b` 567 -> 1050 (0xC63EA), read from the
V295 image and cross-checked against `Cells.v294().replace(fb_b=1050)`.
Control in every batch: **V295 + r1** (the V294 r1 toggles: Kp 0.9, Ki 0.3, LAF 14, friction 0.011, KiHigh 0).
Second control: **V294 + r1** (what flew on r71b; the harness's retrodiction anchor).

Knobs (existing params only): SteerLatAccel (LAF), SteerFriction (F, torque units), AccordTorqueKi (Ki),
AccordTorqueKiHigh (schedule 8 -> 18 m/s), SteerKP (Kp), KeepLearnedLatAccelOffset, lat delay (sensitivity only).

## Gates. A candidate that trips ANY gate is rejected (not "noted").

| id | gate (FAIL if) | where |
|---|---|---|
| G1 | identified family (nominal, b_lo, b_hi, F_lo, F_hi, J_lo, J_hi, tau6, tau0): outer Ms > 1.6 or GM < 3.0 or PM < 35 deg, relay small-signal slope INCLUDED, at any of 3.1 / 4 / 5 / 8 / 12 / 17 / 22 / 26.9 m/s; and never below min(V295+r1's GM, 1.5) | `outer_frf` with the candidate's toggles |
| G2 | light_b at 17 / 22 / 26.9 m/s: GM below 0.97 x V294+r1's light_b GM at that speed, or Ms above 1.10 x its Ms (the pessimistic world must not get worse than what flew) | same |
| G3 | RELAY / describing-function: the linear outer loop with the SteerFriction gain swept over k in [0, 2 x its small-signal slope] (x2 = amplitude margin) goes unstable at any member x speed incl. 3-8 m/s | DF sweep |
| G4 | ON-CENTRE HUNT, time domain (Karnopp plant + relay + integrator, zero planner demand, constant road-crown torque, 60 s, constant speed 3 / 4 / 5 / 8 / 12 / 17 / 22 / 27 m/s): a sustained oscillation in the last 30 s with angle p-p > 2 x V295+r1's at the same point, or > 1.0 deg absolute where r1 is < 0.5 deg | synthetic straight |
| G5 | OVERSTEER: tracking gain > 1.05 or turn-hold > 1.10 in ANY band on ANY scored member, dist lp or full | sweep / score |
| G6 | straight-line (|plan| < 0.4 m/s^2) wheel-rate rms in 1-3 Hz > 1.3 x V295+r1 on any identified member (lp) | sweep |
| G7 | 1-5 Hz limit-cycle line (harness `limit_cycle_peak`, dist lp) > V295+r1's + 3 dB on any member, or a NEW line > +3 dB prominence where r1 has none | sweep |
| G8 | hard-turn 1.6-3 Hz wheel rate at 5-10 or 15-22 m/s > 1.10 x V295+r1 on nominal or light_b (lp or full) | sweep |
| G9 | a 0.3-1.5 Hz straight-line hunt: straight-line 0.3-1 Hz wheel-rate rms > 1.3 x V295+r1 on identified members (lp) | sweep |
| G10 | divergence, NaN, the lane's int32 guard raising, or command slew-limited share > 2 x V295+r1 in any band | sim |
| G11 | J-style 0.15-2.4 Hz lat-accel error at >= 15 m/s worse than V295+r1 by > 10 % (nominal or light_b, lp) | sweep |

## The win condition (the design must EARN a change)

A config is only recommended over "r1 unchanged" if, against V295+r1 in the SAME batch, it raises
**tracking gain AND turn-hold at 8-22 m/s by >= +0.05 on BOTH nominal and light_b under dist lp**,
does not lower straight delivery at 0-10 m/s, and passes G1-G11.

## The FAIL sentence of this design (pre-registered)

> If no candidate passes G1-G11 and meets the win condition, **r2 = r1 unchanged**, and the report says the fork's
> existing knobs cannot close the 8-22 m/s gap safely on this harness. That is a valid deliverable, not a failure to
> deliver.

## Method rules (pre-registered)

- Every candidate is reported as a DIFFERENCE from V295+r1 in the same batch (the harness rule 1); absolute numbers
  only for the outer-loop metrics under lp, which retrodict.
- Outer-loop metrics are trusted under `lp` (FIT 4/5 bands tracking, 3/4 turn-hold); `full` counterfactuals are biased
  toward "no change" and are bracketed with light_b.
- Never quote simulated dwells/min.
- Warm start: the candidate's integrator starts from the logged r1 value. Its sensitivity (i scaled by LAF/14, and the
  first 3 s of each chunk excluded) is reported for the finalists; if a finalist's ranking flips under it, that is
  stated and the finalist is demoted.
- Two methods for every load-bearing number: the outer-loop margins by `outer_frf` AND by a closed-loop time-domain
  step / hunt check; the delivered tracking by the harness sim AND by a static closed-form hold estimate; the codec by
  the kit codec AND the fork's own `decode_parameters` (source extracted from `git show 20d24ab79:`).
- Codec: decode(encode(x)) == x for r2 and the revert; the encoded file decodes with the fork's own function; the kit's
  positive control (the operator's 2026-09-10 backup) passes first.
