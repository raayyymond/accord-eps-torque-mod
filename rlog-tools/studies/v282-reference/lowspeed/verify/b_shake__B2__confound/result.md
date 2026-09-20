# B2 confound check — result

Lens: "V282 is mostly one 62-segment route — leave it out and re-test" (dominant route =
0000006c--2bc842dbac), and "T64B has 4x demand" inside the torque-mode ('rev64') group.

## 1. Confirmed: the confound is real
0000006c--2bc842dbac supplies 322/432 = 74.5% of V282's <8 m/s window-weight (425 s of
~553 s, 31 usable runs >=4 s below 8 m/s in that one route alone). V282's aggregate <8 m/s
numbers (rate 2.61 [2.28,2.95], H 0.25 — both reproduced exactly from B2's own pipeline)
are therefore mostly one drive, not three independent ones.

## 2. Does the B2 ranking survive with that route pulled out?
V282 <8 m/s, excluding the dominant route (n=110, routes 64+65 only):
  rate 3.40 [2.74,3.99] deg/s (up from 2.61), H 0.33 (up from 0.25).

Torque-mode side, pulling out the 4x-demand route (T64B/6e) from 'rev64':
  T64-only (6c+6d) <8 m/s: rate 8.64 [6.59,10.51] (rev64 full was 9.74 [7.68,11.72]) —
  barely moves.
Independent route T4 (different day/road, separate low-demand config): rate 10.71 [7.66,13.52].

Net: torque-mode <8 m/s rate stays 8.6-10.7 deg/s across three route mixes (rev64 full,
T64-only, T4 alone); V282 <8 m/s rate is 2.6 (full) to 3.4 (dominant route removed). The
ranking (torque >> V282) SURVIVES the confound — CIs do not overlap in either version
(rev64/T64/T4 lower bounds 6.6-7.7 vs V282-excl-dominant upper bound 4.0). |H|: torque 0.73
(aggregate <8, unaffected — computed only from torque-mode routes) vs V282 0.25->0.33; still
torque ~2.2x V282's after the fix (was ~2.9x), and the qualitative claim "torque amplifies at
6-8 m/s (H>1), V282 doesn't" also survives (V282 excl-dominant H at 6-8: 0.45, still <1;
torque 1.23).

## 3. What does NOT survive: the <3 m/s sub-comparison
Not asserted as a headline number in B2, but worth flagging: at <3 m/s specifically, the
ranking is confound-sensitive. Full V282 <3: rate 3.92 [3.36,4.47] (clearly below rev64's
5.76 [2.85,9.00]). Excluding the dominant route, V282 <3 rate rises to 5.99 [4.78,7.19] —
statistically indistinguishable from rev64's 5.76. B2 does not make a <3 m/s-specific V282
claim, so this doesn't falsify anything written, but it means the effect at very low speed
is much weaker/unresolved once the single-route confound is removed, and any future claim
narrowed to <3 m/s should not lean on the full-group V282 number.

## 4. Not tested here (road/day matching)
"Different roads/days" was not independently re-matched by GPS/road segment in this pass —
only the route-mix (which routes contribute weight) was tested. The mechanism decomposition
itself (feed vs absorb, sum -7.83 / rl_fb +8.05) is computed entirely within torque-mode
routes and does not depend on V282 at all, so it is unaffected by this V282-side confound.

## Verdict
B2's central claims survive this confound lens: the internal torque-mode mechanism
decomposition (planner-driven terms feed, rate-loop measured-rate term absorbs, net ~zero,
same ranking at 0/30/60 ms) does not involve V282 and is untouched. The appended "vs V282"
comparison sentence survives directionally and with CIs still non-overlapping, though the
reported effect size (x3.7 wheel-rate ratio) shrinks to roughly x2.9-3.1 once the single
dominant V282 route is removed, and the |H| ratio shrinks from ~2.9x to ~2.2x. Recommend the
finding's confidence be kept, with a note that the "x3.7"/"0.73 vs 0.25" precision overstates
robustness slightly (true range roughly x2.2-3.7 depending on route weighting).
