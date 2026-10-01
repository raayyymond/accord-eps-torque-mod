"""EXP B3: the hunting limit cycle re-run on the time harness's OWN run() + LaneCave (rec_time.py, the design's C0 row)
+ PlantVec, i.e. independent of fric_lib: a step to a constant setpoint, held 40 s; slips in the last 20 s."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reconcile_c0"))
import numpy as np
import rec_time as R
import rec_time6 as R6
HT = R.HT
cfg = HT.Cfg(R6.cands()[:1])
fam = HT.VP.family()
HT.A_TURN.update({4.0: 70.0, 5.5: 45.0, 6.0: 40.0, 6.5: 36.0, 7.0: 33.0})
HT.RAMP_S.update({4.0: 2.5, 5.5: 2.0, 6.0: 1.5, 6.5: 1.5, 7.0: 1.0})
print("member  v   step | slips(last 20 s)  p2p deg  T p2p | cycle period s")
for m, v, A in [("nominal", 3.0, 3.0), ("nominal", 3.0, 0.5), ("nominal", 4.0, 3.0), ("nominal", 5.0, 3.0), ("nominal", 5.0, 5.0),
                ("F_hi", 5.0, 3.0), ("F_hi", 6.0, 3.0), ("F_hi", 7.0, 8.0), ("b_lo", 5.0, 3.0), ("F_lo", 3.0, 3.0), ("F_lo", 4.0, 3.0)]:
    scn = HT.scenario("st", v)
    scn.update(dur=40.0, ref=lambda t, A=A: np.where(t >= 0.5, A, 0.0), step=A)
    r = HT.run(scn, cfg, fam[m], v)
    th, om, T = r["th"][:, 0].astype(float), r["om"][:, 0].astype(float), r["T"][:, 0].astype(float)
    w = slice(20000, 40000)
    sl = HT._slips(th[w, None], om[w, None])[0]
    stuck = om[w] == 0.0
    runs = HT._runs(stuck, 100)
    per = np.mean(np.diff([a for a, b in runs])) * 2e-3 if len(runs) > 2 else float("nan")
    print("%-8s %4.1f %4.1f | %3d  %6.2f  %5.0f | %5.1f" % (m, v, A, sl, th[w].max() - th[w].min(), T[w].max() - T[w].min(), per))
