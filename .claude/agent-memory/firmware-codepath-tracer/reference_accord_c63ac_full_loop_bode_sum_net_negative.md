---
name: reference_accord_c63ac_full_loop_bode_sum_net_negative
description: Full-loop (not isolated-stage) Bode-sum analysis of raising 0xC63AC, extending the kit's own eps_loop_gain_model.py anchor. FINDING, ROBUST across every attribution-fraction and both calibration anchors tried -- raising 0xC63AC's HF-gain cost (already on record, 1.38x at 21Hz for cal=205) dominates its own phase-lag credit once the loop is closed; predicted |L| and Q move UP (worse), not down, at every dose 150-300 tested. REVERSES a same-day earlier recommendation (this agent's own) to rank 0xC63AC as the #1 bet -- that recommendation was made on isolated-stage DC-gain/phase evidence only, before the loop-closure computation existed.
metadata:
  type: reference
---

Computed 2026-08-19, in response to an orchestrator task to pre-register 0xC63AC and settle whether
raising it nets ADD or REMOVE phase margin at 23.4Hz ("do the full Bode sum, or say you cannot").

## Method [EVIDENCE for the isolated stage; MODEL/BELIEF for the loop closure, both clearly separated]

Isolated stage (`gp-0x374c += ((target-gp-0x374c)*0xC63AC)>>10`, single-pole discrete EMA): exact,
numpy-verified, cross-checked against `reference_accord_c63ac_is_the_pure_lead_pole_lever.md`'s prior
table (matches to rounding: 1.38x @21Hz for cal=205 reproduced exactly).

Loop closure: extended `analysis-2020accord/eps_loop_gain_model.py`'s own anchor
(`|L(21.4Hz)|=0.875`, `Q=13.6` at V38/4x, giving `zeta_bare=0.294`) by letting the carrier phase vary
with frequency through 0xC63AC's OWN stage delta specifically (everything else in the carrier held at
the script's original "≈+90° rate-feedback, frequency-flat" simplification), generalized via the
standard 2nd-order phase-slope result `d(argP)/dw|w0 = -2*Q_bare/w0` to find the SHIFTED alignment
frequency, then re-evaluating `|L|` there via `Lmag_new = Lmag*|stage_delta|^p*plant_falloff(df)`.
`p` (attribution -- what fraction of the "a382/model carrier"'s gain+phase is actually the 0xC63AC
stage specifically, vs. Path 2's many OTHER stages) is an UNMEASURED free parameter, swept 0.25/0.5/1.0.
Second anchor: route 0x95's relayed (23.38Hz, Q=47.4) point, `|L|` inferred by carrying `zeta_bare`
from anchor A (an assumption -- the bare plant did not change between eras, only loop gain m did).
[BELIEF: I did not independently inspect route 0x95's raw data or `r95_qshift.py`'s output this
session -- this number and which of its two states is "today's" configuration are RELAYED, not
verified by me directly.]

## Finding -- ROBUST, both anchors, all three attribution fractions

Raising `0xC63AC` from 102 predicts `Q` moving UP (worse), never down, at every cal in {150,205,256,
300} tested. At the p=1.0/anchor-A case, predicted `|L|` exceeds 1.0 (the hard self-excitation edge)
at cal>=150. Even at the most conservative p=0.25/anchor-A: cal=150 -> Q 13.6->21.8, cal=300 ->
Q 13.6->45.0 -- WORSE at every dose, no sweet spot found by a 102-600 sweep. **The magnitude/HF-gain
cost (already on record before this session: 1.08-1.75x across 7.79-42Hz for cal=205) dominates the
phase-lag credit once the loop is closed.** A simpler, anchor-independent corroboration of the same
conclusion (no frequency-shift modeling needed): at cal=205, p=1.0, `0.875 * 1.38(magnitude ratio
@21Hz, already-established) = 1.208 > 1` -- already past the edge from pure gain alone, before any
phase-shift analysis.

## 🛑 Consequence -- reverses this agent's own same-day earlier recommendation

Earlier the same session, before this loop-closure computation existed, `0xC63AC` was ranked bet #1
on isolated-stage evidence (DC gain 1.000000, virgin, comfortable phase credit at 7-28Hz). **That
ranking is WITHDRAWN.** The isolated-stage facts are still true and still evidence-grade; what changed
is that the full-loop computation this session shows the accompanying HF-gain increase is large
enough to plausibly overwhelm the phase credit once the loop actually closes. **Do not propose raising
`0xC63AC` without independently closing the same gap this finding is built on** (Path 2's local gain
attribution -- the same unresolved quantity behind [[reference_accord_fun38148_six_weight_v95_candidate_census]]'s
Q5 blocker on the six lane weights). V97's 102->150 flight (uninterpretable) is CONSISTENT with this
finding under a low-attribution reading, not just with the old "DC gain 1 so nothing to see" reading.

## Alpha-match with `0xC40D0` — a real design constraint, not habit

`0xC40D0` (408/4096) and `0xC63AC` (102/1024) share the identical alpha (0.099609375) to the last bit
-- STOCK Honda, not this kit's doing. They sit on the disturbance observer's two DIFFERENT arms
(MODEL, via `FUN_0003b8f6`; ACTUAL, via `FUN_00038148`) whose difference IS the residual Path 2 feeds
forward. Mismatching their dynamics injects a residual ARTIFACT proportional to the two arms' phase
DIVERGENCE at whatever frequency they disagree — a textbook disturbance-observer design hazard, not
mere consistency for its own sake. If `0xC63AC` is ever moved, `0xC40D0` should move with it
(paired value = `0xC63AC` x 4, e.g. 205<->820) to preserve the match, UNLESS a deliberate MISMATCH is
the point of a future experiment.

## Related
[[reference_accord_c63ac_is_the_pure_lead_pole_lever]] -- the isolated-stage facts this file does not
change. [[reference_accord_gp6b26_closed_both_directions_v94_aborted]] -- the sibling case (a
different lever) where a clean isolated-signal theory also failed once measured in the closed loop;
same caution class. `analysis-2020accord/eps_loop_gain_model.py` -- the anchor script this extends.
