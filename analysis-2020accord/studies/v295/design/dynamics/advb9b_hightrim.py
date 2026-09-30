"""ADV-bytes 9b: where do the |trim| > 300 T ticks of the A1017 replay sit (driver torque, speed, sign vs FF and vs bar)?"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
V295 = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(V295, "plant"), os.path.join(V295, "lib")):
    sys.path.insert(0, p)
import plib as P
import r71b_cache as RC
d = P.load(); c = RC.v294_cells(); sg = d["sg"]
z = np.load(os.path.join(HERE, "_scratch", "advb6_march.npz"))
Tn = d["T1k_null"]
for nm, T in (("V294", z["T0"]), ("A1017", z["T1"])):
    trim = sg * T - Tn
    hi = np.flatnonzero(np.abs(trim) > 300)
    k = hi // 10
    bar = d["bar"][k]; v = d["v"][k]; ff = Tn[hi]
    same_ff = np.mean(np.sign(trim[hi]) == np.sign(ff))
    corr_bar = np.corrcoef(trim[hi], bar)[0, 1] if len(hi) > 2 else float("nan")
    print(f"{nm}: {len(hi)} ticks |trim|>300 T; engaged {np.mean(d['eng'][k]):.2f}; |bar|>=400 {np.mean(np.abs(bar)>=400):.2f}; "
          f"max|bar| {np.abs(bar).max():.0f}; pressed {np.mean(d['pressed'][k]):.2f}; speed {np.percentile(v,5):.1f}-{np.percentile(v,95):.1f} m/s; "
          f"trim same sign as FF {same_ff:.2f}; corr(trim, bar) {corr_bar:+.2f}; |T_total| max {np.abs(sg*T)[hi].max():.0f}; distinct episodes {len(np.unique(hi//1000))}")
