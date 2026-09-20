# -*- coding: utf-8 -*-
"""Step 0 -- census before any |H| is computed.

Per route: usable seconds by speed bin, the LAF fitted FROM THE LOG (not from a toggle), the
|output| >= 0.98 rail census, and the la_pose sign/correlation check.  ANALYSIS ONLY.
"""
import sys, os
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import v282cmp as C   # noqa: E402

SPD = [(0, 2), (2, 8), (8, 15), (15, 22), (22, 40)]
print(C._self_test())
print()
print(f"{'route':24s} {'grp':8s} {'LAFfit':>7s} {'maxerr':>8s} | " +
      " ".join(f"{lo}-{hi:<3}" for lo, hi in SPD) + "   railfr%  rail_s  corr(pose,act) sgn")
for rk, meta in C.ROUTES.items():
    S = C.load(rk)
    m = C.usable(S)
    pre = (S["p"] + S["i"] + S["f"])
    out = S["out"]
    # fit LAF from unsaturated frames: out = -pre/LAF
    un = m & (np.abs(out) < 0.95)
    laf = float(np.dot(pre[un], -out[un]) / max(np.dot(out[un], out[un]), 1e-30))
    pred = -np.clip(pre, -laf, laf) / laf
    err = float(np.abs(pred - out)[m].max())
    rail = m & (np.abs(out) >= 0.98)
    sec = [f"{(m & (S['v'] >= lo) & (S['v'] < hi)).sum()/C.FS:6.0f}" for lo, hi in SPD]
    cc = float(np.corrcoef(np.nan_to_num(S["la_pose"][m]), np.nan_to_num(S["la_act"][m]))[0, 1])
    print(f"{rk:24s} {meta['group']:8s} {laf:7.3f} {err:8.1e} | " + " ".join(sec) +
          f"  {100*rail.sum()/max(m.sum(),1):7.3f} {rail.sum()/C.FS:7.1f}  {cc:+.3f}")
    del S
