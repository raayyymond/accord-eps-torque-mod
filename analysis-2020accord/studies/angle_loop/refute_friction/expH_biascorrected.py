"""EXP H: THE BIAS-CORRECTED WORLD the plant report itself prescribes at speed (V294-PLANT-IDENT-r71b.md, G3a: the
estimator of record is biased at >= 10 m/s, b x1.7-1.9 high AND Fc x0.46-0.58 low; Fc -24 % at 5-10 m/s).  The family
carries the two corrections as SEPARATE corners (b_lo, F_hi); the evidence-preferred world has BOTH.  Member 'bc':
b = b_lo's b, friction x2 at the >= 10 m/s knots, x1.3 at the 8 m/s knot, nominal at 3.1 m/s.
Runs the time harness's OWN run() + metrics() + LaneCave on the design's own C0 row (rec_time6.cands()[0])."""
import sys, os
from dataclasses import replace
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reconcile_c0"))
import numpy as np
import rec_time as R
import rec_time6 as R6
HT = R.HT
VP = HT.VP
cfg = HT.Cfg(R6.cands()[:1])
fam = VP.family()
nom, blo = fam["nominal"], fam["b_lo"]
fx = np.where(VP.V_CENTRES >= 10.0, 2.0, np.where(VP.V_CENTRES >= 5.0, 1.3, 1.0))
bc = replace(blo, name="bc", Fc=nom.Fc * fx, Fs=nom.Fs * fx, note="b_lo + G3a friction correction")
mems = {"nominal": nom, "bc": bc}
speeds = [float(s) for s in sys.argv[1].split(",")] if len(sys.argv) > 1 else [8.0, 12.5, 19.0, 26.0, 30.0]
print("member  v   | tg0.2  tg0.5 | hold  | ssm ev  s02 ev  s05 ev  rh slips st slips | max snap | T_hf hold  T_hf sin | hunt p2p")
for mn, m in mems.items():
    for v in speeds:
        out = {}
        for nm in ("rh", "s02", "s05", "ssm", "st"):
            scn = HT.scenario(nm, v)
            r = HT.run(scn, cfg, m, v)
            out[nm] = HT.metrics(nm, scn, r, v)
        g = lambda k, f: out[k][f][0]  # noqa: E731
        snap = max(g(k, "dj_maxjump") for k in ("s02", "s05", "ssm"))
        print("%-7s %5.1f | %5.3f %5.3f | %5.3f | %3d %3d %3d %3d %3d | %5.2f | %5.1f %5.1f | %5.2f" % (
            mn, v, g("s02", "track_gain"), g("s05", "track_gain"), g("rh", "hold_ratio"), g("ssm", "dj_events"),
            g("s02", "dj_events"), g("s05", "dj_events"), g("rh", "hold_slips"), g("st", "hold_slips"), snap,
            max(g("rh", "T_hf"), g("st", "T_hf")), max(g("s02", "T_hf"), g("s05", "T_hf"), g("ssm", "T_hf")),
            max(g("rh", "hunt_p2p"), g("st", "hunt_p2p"))), flush=True)
