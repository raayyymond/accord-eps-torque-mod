# -*- coding: utf-8 -*-
"""f10: the learned latAccelOffset on r71b -- is it a live, converged learner or a restored cache?  And does it match
what the drive itself says the steady bias is (the mean of the fork's straight-road error / integrator)?"""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import r71b_cache as RC
import fc_lib as F
H = F.H

D = RC.load(with_raw=False)
ks = sorted(k for k in D if k.startswith("ltp_"))
print("ltp fields:", ks)
t = D["ltp_t"]
for k in ks:
    if k == "ltp_t":
        continue
    a = np.asarray(D[k], float)
    print("  %-14s n %5d  first %.4f  last %.4f  p5/p50/p95 %s  unique %d" % (k, len(a), a[0], a[-1],
          np.round(np.percentile(a, [5, 50, 95]), 4).tolist(), len(np.unique(np.round(a, 5)))))
print("route span %.0f s; ltp messages %d" % (t[-1] - t[0], len(t)))
# the drive's own steady bias on straights: integrator (lat-accel units) and roll comp while hands-off engaged
d = H.route()
ch = H.route_chunks()
I, E, R, O = [], [], [], []
for a, b in ch:
    v = d["v"][a:b]
    plan = d["ctl_des_curv_f"][a:b] * v ** 2
    st = (np.abs(plan) < 0.2) & (v > 8)
    I.append(d["ctl_i_f"][a:b][st]); O.append(d["ltp_off_f"][a:b][st]); R.append(d["lpar_roll_f"][a:b][st] * 9.81)
    E.append((d["ctl_la_des_f"][a:b] - d["ctl_la_act_f"][a:b])[st])
I, E, R, O = (np.concatenate(x) for x in (I, E, R, O))
print("straights v > 8, |plan| < 0.2 (%.0f s): integrator p50 %+.3f (m/s^2 equiv), error p50 %+.3f, roll comp p50 %+.3f, "
      "learned offset p50 %+.3f" % (len(I) / 100, np.median(I), np.median(E), np.median(R), np.median(O)))
print("sign convention: ff -= offset * fade, so the offset ADDS %+.3f m/s^2 to the command; the integrator holds %+.3f on top"
      % (-np.median(O), np.median(I)))
