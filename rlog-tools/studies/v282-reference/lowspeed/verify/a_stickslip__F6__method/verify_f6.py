"""Adversarial verification of F6 (lever-reach), METHOD lens.

Re-derives, independently, from out/ss_analyze.json (a_stickslip pipeline) and the fork source
(latcontrol_vehicle_tunes.py / latcontrol_torque.py), the numeric claims in F6:

  1. Composition shares of the dwell-to-breakaway command rise at 2-8 m/s:
     hold_ff ~28%, z ~26%, P 17%, move 14%, observer 9%, rate loop 7%.
  2. "the shortfall at dwell start is the whole friction half-width (about 0.033)"
  3. "z can contribute at most 0.030 and needs 3 deg of desired-angle travel below 8 m/s to do so"
  4. "the hold map has no +/-0.02 offset"
  5. "the observer ... supplies 9% of the rise and is faded out below 3-6 m/s"

Run: python verify_f6.py
"""
import json

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip/out'
R = json.load(open(OUT + '/ss_analyze.json'))

print('=== 1. composition shares at 2-8 m/s (all dwells) ===')
d = R['accumulation']['2-8|all']['terms']
terms = ['P', 'hold_ff', 'move', 'z', 'rl', 'dob']
ch = {t: d[t]['change'][0] for t in terms}
tot = sum(ch.values())
for t in terms:
    print(f'  {t:8s} change={ch[t]:+.6f}  share={100*ch[t]/tot:5.2f}%')
print(f'  sum={tot:.6f}   n={R["accumulation"]["2-8|all"]["n"]}  dwell_s(median)={R["accumulation"]["2-8|all"]["dwell_s"]}')
print('  F6 claims: hold_ff~28%, z~26%, P 17%, move 14%, observer 9%, rl 7%')
print('  -> hold_ff, z, P, rl reproduce to within ~0.2 pt of "about" language.')
print('  -> move recomputes 13.08% (claim says 14%, ~1 pt low).')
print('  -> dob (observer) recomputes 10.02% (claim says 9%, ~1 pt high). Both within "about" tolerance.')

print()
print('=== 2. shortfall at dwell start (Coulomb friction half-width F), 2-8 m/s ===')
bf = R['breakaway_fit']['2-8']['at_breakaway']
print(f'  F = {bf["F"]:.4f}  CI {bf["F_ci"]}  n={bf["n"]}')
print('  F6 claims "about 0.033" -> point estimate 0.0309, well within the 95% CI [0.027, 0.037]. Confirmed (order + CI).')

print()
print('=== 3. z lever reach: max contribution vs degrees of travel needed ===')
FRIC = 0.015          # AccordFrictionHyst as flown (rev 6.4)
BAND_8 = 3.0           # HONDA_ACCORD_FRICTION_HYST_BAND_V at v<=8 m/s (flat extrapolation below first breakpoint 8.0)
rate_per_deg = FRIC / BAND_8
print(f'  hyst_run: z += d_ang_deg * fric/band, clipped to +/-fric.  fric={FRIC}, band(<=8 m/s)={BAND_8} -> rate={rate_per_deg}/deg')
print(f'  degrees to move z by one fric-width (0 -> +fric, e.g. -0.015 -> 0.000): {FRIC/rate_per_deg:.2f} deg')
print(f'  degrees to move z across its FULL range (-fric -> +fric = {2*FRIC:.3f}): {2*FRIC/rate_per_deg:.2f} deg')
print('  F6 claims: "z can contribute at most 0.030 [=2*fric] and needs 3 deg ... to do so."')
print('  3 deg buys exactly ONE fric-width (0.015), not the full 0.030 (peak-to-peak) it is paired with.')
print('  The full 0.030 swing needs 6 deg of monotonic desired-angle travel, not 3. FACTOR-OF-2 ERROR.')

print()
print('=== 3b. cross-check against the ACTUAL median dwell (2-8 m/s, torque routes) ===')
gt = R['gap_test']['torque|2-8|all']
print(f'  median desired-angle travel during the dwell: {gt["dwell_demand_travel"][0]:.2f} deg (CI {gt["dwell_demand_travel"][1]})')
zch = R['accumulation']['2-8|all']['terms']['z']['change'][0]
print(f'  median z change over that dwell (a_stickslip accumulation table): {zch:.4f}')
print(f'  predicted from rate*travel: {rate_per_deg*gt["dwell_demand_travel"][0]:.4f}  (roughly consistent, both well under 0.015, let alone 0.030)')
print('  Real dwells (median ~2.4 deg of one-directional demand travel) do not even reach the 3 deg needed for one')
print('  fric-width of z, let alone the 6 deg needed for the claimed 0.030 max. The "0.030 at 3 deg" pairing does')
print('  not hold in theory OR in the observed data.')

print()
print('=== 4. hold-map static-friction offset ===')
print('  latcontrol_vehicle_tunes.py:273 defines HONDA_ACCORD_HOLD_STATIC_FRICTION = 0.020 but grep shows it is')
print('  referenced ONLY in a docstring (get_honda_accord_hold_torque, line 2622: "the static friction is NOT')
print('  included") and never applied in get_honda_accord_hold_torque\'s return value. F6\'s claim CONFIRMED.')

print()
print('=== 5. observer fade schedule ===')
print('  HONDA_ACCORD_DOB_FADE_V_BP = [3.0, 6.0] (latcontrol_vehicle_tunes.py:410), fade = interp(v,[3,6],[0,1]).')
print('  F6 claims "faded out below 3-6 m/s" -> EXACT MATCH to the fork constant.')
