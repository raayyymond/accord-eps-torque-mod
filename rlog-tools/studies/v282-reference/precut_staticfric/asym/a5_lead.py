"""A5: two remaining alternative explanations for the outward centre offset, and the V282 contrast.

(i) THE DESIRED-ANGLE LEAD.  During a dwell the wheel is stuck while the DEMAND keeps moving, so the
    feedforward is evaluated at angle_des, not at the actual angle.  hold(angdes) - hold(aa) is then an
    outward-pointing command component that is pure kinematics of the dwell, not a plant intercept.
    Does it account for the centre offset, and for the offset's growth with |angle|?
(ii) THE OBSERVER.  dob carries +0.010 of the +0.019 centre (A3).  Is its share angle-proportional too
    (= the observer measuring a map deficit) or flat (= a bias)?
(iii) V282 contrast: leave-one-route-out, the group difference with a CI, and the units objection
    (V282's wire output commands a RATE into a rate servo, so the same number is not the same torque).
"""
import json
import numpy as np
from alib import *

EP, W, PR = load()
c = cols(EP)
g, v, sj, route = c('group'), c('v'), c('sjump'), c('route')
N = len(EP); ar = np.arange(N)
aa_bk = W['aa'][:, PRE]
sgn = np.sign(aa_bk)
toward = (sj == -sgn)
dirn = np.where(toward, -1.0, 1.0)
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])
lev = np.array([PR[r].get('AccordHoldLevel', '0') == '1' for r in route])
IDX = PRE - 3
holdlev = np.array([hold_map(W['aa'][i], W['v'][i], bool(lev[i])) for i in range(N)])
holddes = np.array([hold_map(W['angdes'][i], W['v'][i], bool(lev[i])) for i in range(N)])
y_out = (W['cmd'][ar, IDX] - holdlev[ar, IDX]) * sgn
lead_t = (holddes[ar, IDX] - holdlev[ar, IDX]) * sgn        # outward torque from the desired-angle lead
lead_d = (W['angdes'][ar, IDX] - W['aa'][ar, IDX]) * sgn    # the lead itself, deg
absaa = np.abs(W['aa'][ar, IDX])
m28 = TQ & (v >= 2) & (v < 8)
m815 = TQ & (v >= 8) & (v < 15)
out = {}


def bci(fn, mask, nb=800, seed=3):
    est, lo, hi, bs = boot_routes(fn, route, mask, nb=nb, seed=seed)
    lo = np.nanpercentile(bs, 2.5, axis=0); hi = np.nanpercentile(bs, 97.5, axis=0)
    return est, lo, hi


print('=== (i) the desired-angle lead at breakaway, torque 2-8 ===')
for lab, mm in (('all', m28), ('away', m28 & ~toward), ('toward', m28 & toward)):
    print(f'  {lab:7s} lead_deg  p10/50/90 {np.percentile(lead_d[mm], [10, 50, 90]).round(2)}   '
          f'lead_torque p50 {np.median(lead_t[mm]):+.4f}')
    out[f'lead_{lab}'] = dict(lead_deg_p50=round(float(np.median(lead_d[mm])), 3),
                              lead_torque_p50=round(float(np.median(lead_t[mm])), 5))
print('  corr(y_out, lead_torque) =', round(float(np.corrcoef(y_out[m28], lead_t[m28])[0, 1]), 3),
      '  corr(lead_torque, |aa|) =', round(float(np.corrcoef(lead_t[m28], absaa[m28])[0, 1]), 3))


def lead_fit(ii):
    X = np.vstack([np.ones(N), lead_t, dirn]).T
    return np.linalg.lstsq(X[ii], y_out[ii], rcond=None)[0]


def lead_fit2(ii):
    X = np.vstack([np.ones(N), lead_t, absaa, dirn]).T
    return np.linalg.lstsq(X[ii], y_out[ii], rcond=None)[0]


for lab, fn, nms in (('+lead', lead_fit, ['intercept', 'per_lead_torque', 'halfwidth']),
                     ('+lead+|aa|', lead_fit2, ['intercept', 'per_lead_torque', 'slope_per_deg', 'halfwidth'])):
    est, lo, hi = bci(fn, m28)
    out[f'leadmodel_2_8{lab}'] = {n: [round(float(est[i]), 5), [round(float(lo[i]), 5), round(float(hi[i]), 5)]]
                                  for i, n in enumerate(nms)}
    print(f'  model {lab}: ' + '  '.join(f'{n}={est[i]:+.5f}[{lo[i]:+.5f},{hi[i]:+.5f}]' for i, n in enumerate(nms)))

print('\n  centre by |aa| bin AFTER removing the lead torque (y_out - lead_t):')
y2 = y_out - lead_t


def med_c(ii, yy):
    a = ii[~toward[ii]]; t = ii[toward[ii]]
    if len(a) < 3 or len(t) < 3:
        return np.array([np.nan, np.nan])
    return np.array([(np.median(yy[a]) + np.median(yy[t])) / 2.0, (np.median(yy[a]) - np.median(yy[t])) / 2.0])


rows = {}
for a0, a1 in [(0, 1), (1, 2), (2, 4), (4, 8), (8, 1e9)]:
    mm = m28 & (absaa >= a0) & (absaa < a1)
    if (mm & ~toward).sum() < 3 or (mm & toward).sum() < 3:
        continue
    est, lo, hi = bci(lambda ii: med_c(ii, y2), mm)
    rows[f'{a0}-{a1}'] = dict(n=int(mm.sum()), centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                              halfwidth=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]])
    print(f'   |aa| {a0:>2}-{a1:<4} n={int(mm.sum()):3d} centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  hw {est[1]:+.5f}')
out['centre_by_absaa_leadremoved_2_8'] = rows

print('\n=== (ii) the observer share vs |aa|, torque 2-8 ===')
dob_out = W['dob'][ar, IDX] * sgn
OBS = np.isin(g, ['T64', 'T64B', 'T5'])    # rev 4 (route 75) has no observer: dob == 0 there
print('  |dob| at breakaway rms: observer routes', round(float(np.sqrt(np.mean(W['dob'][m28 & OBS, IDX] ** 2))), 5),
      ' rev4 route 75', round(float(np.sqrt(np.mean(W['dob'][m28 & ~OBS, IDX] ** 2))), 5))
print('  NATURAL EXPERIMENT -- centre with vs without an observer (model-M, robust median):')
for lab, mm in (('observer routes', m28 & OBS), ('rev4 no observer', m28 & ~OBS)):
    e = med_c(np.where(mm)[0], y_out)
    print(f'   {lab:18s} n={int(mm.sum()):3d} centre {e[0]:+.5f}  hw {e[1]:+.5f}')
    out[f'natexp_{lab.replace(" ", "_")}'] = dict(n=int(mm.sum()), centre=round(float(e[0]), 5), halfwidth=round(float(e[1]), 5))
est, lo, hi = bci(lambda ii: med_c(ii, dob_out), m28 & OBS)
print(f'   dob centre on observer routes only: {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]')
out['dob_centre_observer_routes'] = [round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]]

print('\n  OUTWARD TRAVEL the design wants to cut, by |aa| bin (cmd at breakaway - cmd at dwell start, away eps):')
d0i = np.maximum(c('w_d0'), 0)
trav = (W['cmd'][ar, IDX] - W['cmd'][ar, d0i]) * sgn
rows = {}
for a0, a1 in [(0, 1), (1, 2), (2, 4), (4, 1e9)]:
    for lab, sel in (('away', ~toward), ('toward', toward)):
        mm = m28 & (absaa >= a0) & (absaa < a1) & sel
        if mm.sum() < 5:
            continue
        est, lo, hi = bci(lambda ii: np.array([np.median(trav[ii])]), mm)
        rows[f'{a0}-{a1}|{lab}'] = [int(mm.sum()), round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]]
        print(f'   |aa| {a0:>2}-{a1:<4} {lab:7s} n={int(mm.sum()):3d} median rise {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]')
out['travel_by_absaa'] = rows
rows = {}
for a0, a1 in [(0, 1), (1, 2), (2, 4), (4, 8), (8, 1e9)]:
    mm = m28 & (absaa >= a0) & (absaa < a1)
    if (mm & ~toward).sum() < 3 or (mm & toward).sum() < 3:
        continue
    est, lo, hi = bci(lambda ii: med_c(ii, dob_out), mm)
    rows[f'{a0}-{a1}'] = dict(n=int(mm.sum()), dob_centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]])
    print(f'   |aa| {a0:>2}-{a1:<4} n={int(mm.sum()):3d} dob centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]')
out['dob_centre_by_absaa_2_8'] = rows
# and P, I for comparison
for nm in ('P', 'I', 'hold_ff'):
    xx = W[nm][ar, IDX] * sgn
    r2 = {}
    for a0, a1 in [(0, 2), (2, 1e9)]:
        mm = m28 & (absaa >= a0) & (absaa < a1)
        est, lo, hi = bci(lambda ii: med_c(ii, xx), mm)
        r2[f'{a0}-{a1}'] = [round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]]
    out[f'{nm}_centre_by_absaa'] = r2
    print(f'   {nm:8s} centre |aa|<2 {r2["0-2"][0]:+.5f}  |aa|>=2 {r2["2-1000000000.0"][0]:+.5f}')

print('\n=== (iii) V282 contrast ===')
V = g == 'V282'


CMD_OUT = W['cmd'][ar, IDX] * sgn


def cen_hw_k(ii):
    """FREE linear spring in the outward frame -- the only spec meaningful for a rate-servo command.
    cmd*sgn = centre + halfwidth*dir + slope*|aa|."""
    X = np.vstack([np.ones(N), np.where(toward, -1.0, 1.0), absaa]).T
    co = np.linalg.lstsq(X[ii], CMD_OUT[ii], rcond=None)[0]
    return np.array([co[0], co[1], co[2]])      # centre, halfwidth, slope per deg (outward frame)


for lab, mm in (('torque 2-8', m28), ('V282 2-8', V & (v >= 2) & (v < 8)),
                ('torque 8-15', m815), ('V282 8-15', V & (v >= 8) & (v < 15))):
    est, lo, hi = bci(cen_hw_k, mm)
    out[f'cenhwk_{lab}'] = dict(n=int(mm.sum()), centre=[round(float(est[0]), 5), [round(float(lo[0]), 5), round(float(hi[0]), 5)]],
                                halfwidth=[round(float(est[1]), 5), [round(float(lo[1]), 5), round(float(hi[1]), 5)]],
                                slope_per_deg=[round(float(est[2]), 5), [round(float(lo[2]), 5), round(float(hi[2]), 5)]])
    print(f'  {lab:12s} n={int(mm.sum()):3d} centre {est[0]:+.5f} [{lo[0]:+.5f},{hi[0]:+.5f}]  hw {est[1]:+.5f}  '
          f'slope {est[2]:+.5f} torque/deg [{lo[2]:+.5f},{hi[2]:+.5f}]')
print('  V282 2-8 route LOO (centre):')
mv = V & (v >= 2) & (v < 8)
for r in np.unique(route[mv]):
    mm = mv & (route != r)
    e = cen_hw_k(np.where(mm)[0])
    print(f'    drop {r} (n-{int((mv & (route == r)).sum()):3d})  centre {e[0]:+.5f}  hw {e[1]:+.5f}  slope {e[2]:+.5f}')
    out[f'v282_loo_{r}'] = dict(centre=round(float(e[0]), 5), n_dropped=int((mv & (route == r)).sum()))
for r in np.unique(route[mv]):
    mm = mv & (route == r)
    e = cen_hw_k(np.where(mm)[0])
    print(f'    only {r} (n={int(mm.sum()):3d})  centre {e[0]:+.5f}  hw {e[1]:+.5f}  slope {e[2]:+.5f}')

# group difference with a CI: resample each group's routes independently
rng = np.random.default_rng(17)
ut, uv = np.unique(route[m28]), np.unique(route[mv])
pt = {r: np.where(m28 & (route == r))[0] for r in ut}
pv = {r: np.where(mv & (route == r))[0] for r in uv}
d0 = cen_hw_k(np.where(m28)[0])[0] - cen_hw_k(np.where(mv)[0])[0]
bs = []
for _ in range(1500):
    it = np.concatenate([pt[r] for r in rng.choice(ut, len(ut))])
    iv = np.concatenate([pv[r] for r in rng.choice(uv, len(uv))])
    bs.append(cen_hw_k(it)[0] - cen_hw_k(iv)[0])
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f'  centre(torque 2-8) - centre(V282 2-8) = {d0:+.5f} [{lo:+.5f},{hi:+.5f}]')
out['group_diff_centre_2_8'] = [round(float(d0), 5), [round(float(lo), 5), round(float(hi), 5)]]
# LAF per group (the command is divided by it)
print('  median SteerLatAccel: torque', np.median(c('LAF')[m28]), ' V282', np.median(c('LAF')[mv]))
out['LAF_torque'] = float(np.median(c('LAF')[m28])); out['LAF_v282'] = float(np.median(c('LAF')[mv]))
json.dump(out, open('out/a5_lead.json', 'w'), indent=1)
