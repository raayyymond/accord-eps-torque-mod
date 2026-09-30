# CRITERIA — lens "robust-joint" (V295 design), written BEFORE any candidate number was computed

Subagent `robust-joint`, 2026-09-30. Design only. Written after reading the harness/census/plant/metric/bands reports
and the harness code, before running any scorer, sweep or spot-check.

## What the lens does
A joint, worst-case search over the cal knobs of the V294-class lane: fb_a, fb_b, fb_clamp C, e_shift in {0,1,2}
(opcode 0x29D76, only if the gain is large), Kp flat level and idx schedule, output-lag pair (0xC63EC/0xC63EE),
Kd bank + D clamp. Ki is EXCLUDED unless the census finding (it integrates the command, no leak, no anti-windup) is
defeated from the bytes — I do not expect to defeat it. Fast linear scorer first (harness primitives: lane_ctf,
loop_frf, outer_frf, closed_loop_modes), nonlinear byte-exact replay (sweep_drive / score) only on finalists.

## Pre-registered HARD constraints (evaluated on the WORST family member; a candidate violating any is infeasible)
- H-SAFE-1  M_SAFE rail |+| and |-| <= V294's (+2461 / -2463). Lane clamp 3072 untouched.
- H-SAFE-2  Cells.problems() empty; int32 minimum margin >= 2.0 (V294 4.06); b <= b_max.
- H-SAFE-3  trim cap (T at zero command) <= 2 x V294's 616 T (<= ~50 % of the rail); restart pulse at 100 deg/s
            <= 2 x V294's 144 T.
- H-HF-1    max over 10-25 Hz of |P/x| and of |T/x| <= 3.0 x V294's (rule 3 of the brief; V282 ground at 21.6 x).
- H-HF-2    stress members mode13 / mode20 / mode20_lo at 5 / 12 / 25 m/s: closed-loop zeta >= 0.8 x min(zeta_V294,
            zeta_open) and never < 0.05 absolute for mode13/mode20 (mode20_lo is ζ 0.02 open; there: >= 0.8 x open).
- H-LOOP-1  inner loop stable on every scored + stress member at 3.1/8/12/17/26.9 m/s, incl. delay x1.5; Ms <= 1.5.
- H-LOOP-2  OUTER loop (outer_frf, relay on and off) on every member incl. light_b at 5/8/12/17/26.9 m/s:
            GM >= 0.95 x min(GM_V294, 2.0) at the same (member, speed, relay), and Ms <= max(1.1 x Ms_V294, 1.5).
            i.e. where V294 already sits below GM 2 (light_b at highway) the candidate may not erode it by > 5 %.

## Objective (scalar, used for ranking only inside the feasible set)
J = w_T * M_TRACK_proxy + w1 * jerk_proxy + w2 * loose_low_proxy + w3 * loose_hwy_proxy, each normalised to V294 = 0,
improvement negative; worst member taken per term. Weights 1 / 1 / 1 / 1 (no complaint privileged). Terms:
- M_TRACK_proxy: closed-form alpha/cmd (inner loop closed) complex-gain R^2 over 1-3 and 3-8 Hz, weighted by the
  drive's command spectrum; reported per band.
- jerk_proxy: |omega/d| rms over 1.6-3 Hz with BOTH loops closed (road-torque sensitivity), 5-15 m/s members.
- loose_low_proxy: act/plan at 0.1-0.3 Hz with the fork FF + loop, 3.1-8 m/s (linear); sim tracking gain / straight
  delivery 0-10 m/s for finalists.
- loose_hwy_proxy: the same at 17-26.9 m/s; sim tracking gain / turn-hold 15-22 and 22+ for finalists.

## Pre-registered FAIL / demotion sentences
- F1 (harness): my spot-check of one lane tick vs the golden model mismatches, or my re-run of the V294 nominal lp
  5-10 m/s retrodiction row misses the report's tracking gain 0.865 by > 0.01 -> STOP, report a harness defect.
- F2 (nothing to ship): no feasible candidate improves V294 on at least one complaint proxy by a margin >= the
  V294-vs-V293 difference magnitude on that proxy (tracking gain >= +0.03 in the band, or hard-turn 1.6-3 Hz <= x0.9)
  on BOTH nominal and light_b under BOTH lp and full, without making any other complaint proxy worse by more than half
  that margin -> recommend "no change".
- F3 (not robust): the pick's sign of change vs V294 on its primary metric flips between nominal and light_b, or
  between dist full and lp -> demote it; take the next Pareto point that does not flip.
- F4 (hard constraint): the pick violates any H-* on any member in the finalist (nonlinear) scoring -> demote.
- F5 (unobservable): a changed value that cannot be attributed on the existing wire from ~30 s of engaged driving
  (FF identity / trim-footprint regression / byte-exact march of the cell set vs the 427 tap) -> that value is
  dropped from the pick (rule 6).
- F6 (process): quoting a simulated magnitude from a harness-NOT-FIT quantity (1-8 Hz wheel motion from the plant
  alone, dwells/min) as a prediction -> forbidden; only directions + margins across the family.

## What a "do not flash" from this lens looks like
F2 fires, or every Pareto point that moves a complaint proxy by the F2 margin violates H-LOOP-2 on light_b or
H-HF-2 on a stress member. Then the recommendation is "no change", with the Pareto front and the binding constraint.
