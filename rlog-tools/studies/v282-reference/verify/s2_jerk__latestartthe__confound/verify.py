"""Adversarial CONFOUND verification of s2_jerk finding 'late-start-then-overshoot-no-settle'.

Re-derives the claim's headline numbers from the already-extracted per-event rows
(s2_jerk/_out/events_*.npz, built by s2_extract.py from v282cmp.py -- shared definitions),
using the SAME matching function as the original (s2_common.match), then stress-tests it:

  1. reproduce the exact reported numbers (sanity)
  2. leave-out the ONE dominant V282 route (0000006c--2bc842dbac, 62 segments) specifically
     -- not just report the loro min/max, name which route is which
  3. leave-out each V282 route in turn, and each T64 route in turn, report every one by name
  4. re-run matching with a TIGHTER speed caliper (cal_v 0.15 instead of 0.25) and see if the
     medians/CIs move
  5. per-route breakdown of matched pairs (which routes actually contribute to n=48)
  6. cross-check on la_pose (independent livePose-based lateral accel) already computed by
     the original extraction as pose.sgain / pose.bias_* -- reprinted here explicitly
  7. lat_delay (learned lateral delay) comparison V282 vs T64 events -- is the 'late start'
     explainable by a difference in the LEARNED delay compensation rather than an EPS-mode
     response-speed difference?
  8. fork-config sanity: V282 fork commits (0f98d8c7 / 57410c3b) vs T64 fork commit (84766cdc)
     -- confirm actualLateralAccel (cs_la_act) is computed by the IDENTICAL formula in both
     (checked separately via `git show <hash>:selfdrive/controls/lib/latcontrol_torque.py`,
     see verify_notes.txt) -- both do
     `measurement = -VM.calc_curvature(radians(steeringAngleDeg - angleOffsetDeg), vEgo, roll) * vEgo**2`
     byte-identical between 0f98d8c7 and 84766cdc, so the la_act signal chain is not a confound.
"""
import sys, json
import numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s2_jerk')
from s2_common import load_all, match, boot_diff, VBINS

OUT = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s2_jerk__latestartthe__confound'

rows, tr = load_all()
for r in rows:
    if 'act.settle' in r and not np.isfinite(r['act.settle']):
        r['act.settle'] = 2.5
REF_ALL = [r for r in rows if r['group'] == 'V282']
TQ_ALL = [r for r in rows if r['group'] == 'T64']
V282_ROUTES = sorted(set(r['route'] for r in REF_ALL))
T64_ROUTES = sorted(set(r['route'] for r in TQ_ALL))
print("V282 routes:", V282_ROUTES)
print("T64 routes:", T64_ROUTES)
print("V282 event counts by route (all speeds):", {rt: sum(1 for r in REF_ALL if r['route'] == rt) for rt in V282_ROUTES})
print("T64 event counts by route (all speeds):", {rt: sum(1 for r in TQ_ALL if r['route'] == rt) for rt in T64_ROUTES})

HEADLINE = ['act.sgain', 'pose.sgain', 'act.bias_0_20', 'act.bias_150_300', 'act.step_over', 'act.settle', 'act.slag']

def report(name, REF, TQ, cal_v=0.25):
    pairs = match(REF, TQ, cal_v=cal_v)
    hi = [p for p in pairs if p[1]['vb'] in (2, 3)]  # >=15 m/s
    print(f"\n== {name}: n_ref={len(REF)} n_tq={len(TQ)} n_pairs_all={len(pairs)} n_pairs_hi>=15={len(hi)}")
    if len(hi) < 5:
        print("   too few pairs, skip")
        return None
    out = {}
    for m in HEADLINE:
        b = boot_diff(hi, m)
        ref_med = float(np.nanmedian([p[0].get(m, np.nan) for p in hi]))
        tq_med = float(np.nanmedian([p[1].get(m, np.nan) for p in hi]))
        out[m] = dict(n=b['n'], ref=ref_med, tq=tq_med, diff=b['med'], ci_ev=b['ci_ev'])
        print(f"   {m:16s} n={b['n']:3d} ref={ref_med:+.3f} tq={tq_med:+.3f} diff={b['med']:+.3f} ci_ev=[{b['ci_ev'][0]:+.3f},{b['ci_ev'][1]:+.3f}]")
    # which V282 routes actually contribute to the hi>=15 matched pairs?
    contrib = {}
    for p in hi:
        contrib[p[0]['route']] = contrib.get(p[0]['route'], 0) + 1
    print("   ref-route contribution to hi>=15 matched pairs:", contrib)
    return out

results = {}

# 1. baseline reproduction (should match s2_results.json exactly)
results['baseline'] = report('BASELINE (all V282 routes, all T64 routes)', REF_ALL, TQ_ALL)

# 2/3. leave-one-route-out, named explicitly
for rt in V282_ROUTES:
    REF = [r for r in REF_ALL if r['route'] != rt]
    results[f'drop_ref_{rt}'] = report(f'DROP V282 route {rt}', REF, TQ_ALL)

for rt in T64_ROUTES:
    TQ = [r for r in TQ_ALL if r['route'] != rt]
    results[f'drop_tq_{rt}'] = report(f'DROP T64 route {rt}', REF_ALL, TQ)

# 4. tighter speed caliper
results['tight_speed_caliper'] = report('TIGHTER speed caliper (cal_v=0.15)', REF_ALL, TQ_ALL, cal_v=0.15)

# 6. explicit la_pose printout already inside HEADLINE (pose.sgain)

# 7. lat_delay: does T64 simply have a larger LEARNED lateral delay than V282, which alone
#    would explain a 'late start' as a bookkeeping artifact rather than the EPS being slower?
pairs = match(REF_ALL, TQ_ALL)
hi = [p for p in pairs if p[1]['vb'] in (2, 3)]
ld_ref = np.array([p[0].get('lat_delay', np.nan) for p in hi])
ld_tq = np.array([p[1].get('lat_delay', np.nan) for p in hi])
slag_ref = np.array([p[0].get('act.slag', np.nan) for p in hi])
slag_tq = np.array([p[1].get('act.slag', np.nan) for p in hi])
print(f"\n== lat_delay (learned) at matched pairs, hi>=15 (n={len(hi)}):")
print(f"   V282 median lat_delay = {np.nanmedian(ld_ref):.3f} s   T64 median lat_delay = {np.nanmedian(ld_tq):.3f} s   diff = {np.nanmedian(ld_tq - ld_ref):+.3f} s")
print(f"   V282 median act.slag (measured response lag) = {np.nanmedian(slag_ref):.3f} s   T64 = {np.nanmedian(slag_tq):.3f} s   diff = {np.nanmedian(slag_tq - slag_ref):+.3f} s")
# if the slag difference is fully explained by the lat_delay difference, corr(slag_diff, ld_diff) across
# events should be high and the slope near 1; also compare the MAGNITUDE
dld = ld_tq - ld_ref
dslag = slag_tq - slag_ref
ok = np.isfinite(dld) & np.isfinite(dslag)
if ok.sum() > 5:
    corr = float(np.corrcoef(dld[ok], dslag[ok])[0, 1])
    print(f"   corr(d(lat_delay), d(act.slag)) across {ok.sum()} pairs = {corr:.3f}  (paired, not causal, but a high corr + slope~1 would say the 'late start' reading is just a delay-compensation bookkeeping difference)")
    A = np.vstack([dld[ok], np.ones(ok.sum())]).T
    slope, intercept = np.linalg.lstsq(A, dslag[ok], rcond=None)[0]
    print(f"   slope of d(act.slag) on d(lat_delay) = {slope:.3f}, intercept = {intercept:.3f}")

results['lat_delay_check'] = dict(
    n=int(len(hi)), ld_ref_med=float(np.nanmedian(ld_ref)), ld_tq_med=float(np.nanmedian(ld_tq)),
    ld_diff_med=float(np.nanmedian(dld)), slag_ref_med=float(np.nanmedian(slag_ref)),
    slag_tq_med=float(np.nanmedian(slag_tq)), slag_diff_med=float(np.nanmedian(dslag)),
    corr_dld_dslag=corr if ok.sum() > 5 else None, slope=float(slope) if ok.sum() > 5 else None)

json.dump(results, open(f'{OUT}/verify_results.json', 'w'), indent=1, default=float)
print("\nWrote", f'{OUT}/verify_results.json')
