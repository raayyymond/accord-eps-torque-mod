"""EXP A2: the time harness's OWN run() + metrics() + LaneCave (rec_time.py) on the design's OWN C0 row, at the knot
midpoints and the 5-10 m/s band the design's prediction table skips (5.5 / 6 / 6.5 / 7 / 10 / 15 / 22 m/s), all five
tracking scenarios.  Same scoring columns as rec_score.detail()."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "reconcile_c0"))
import numpy as np
import rec_time as R          # patches HT.LaneVec = LaneCave
import rec_time6 as R6
HT = R.HT
rows = R6.cands()[:1]          # C0 (with the bleed), exactly the design's row
cfg = HT.Cfg(rows)
fam = HT.VP.family()
members = sys.argv[1].split(",") if len(sys.argv) > 1 else ["nominal"]
speeds = [float(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else [5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 10.0, 15.0, 22.0]
HT.A_TURN.update({5.5: 45.0, 6.0: 40.0, 6.5: 36.0, 7.0: 33.0, 10.0: 20.0, 15.0: 8.0, 22.0: 4.0, 4.0: 70.0})
HT.RAMP_S.update({5.5: 2.0, 6.0: 1.5, 6.5: 1.5, 7.0: 1.0, 10.0: 1.0, 15.0: 1.0, 22.0: 1.0, 4.0: 2.5})
print("member  v    | s02 ev | s05 ev | ssm ev  ssm fit stick% | rh slips st slips | max snap | rh hunt p2p")
for m in members:
    for v in speeds:
        out = {}
        for nm in ("rh", "s02", "s05", "ssm", "st"):
            scn = HT.scenario(nm, v)
            r = HT.run(scn, cfg, fam[m], v)
            out[nm] = HT.metrics(nm, scn, r, v)
        tot = out["s02"]["dj_events"][0] + out["s05"]["dj_events"][0] + out["ssm"]["dj_events"][0] + out["rh"]["hold_slips"][0] + out["st"]["hold_slips"][0]
        snap = max(out[k]["dj_maxjump"][0] for k in ("s02", "s05", "ssm"))
        print("%-8s %5.1f | %3d | %3d | %3d  %5.2f %5.0f | %3d %3d | %5.2f | %5.2f  TOTAL %d" % (m, v, out["s02"]["dj_events"][0], out["s05"]["dj_events"][0], out["ssm"]["dj_events"][0], out["ssm"]["fit_gain"][0], out["ssm"]["stick_pct"][0], out["rh"]["hold_slips"][0], out["st"]["hold_slips"][0], snap, out["rh"]["hunt_p2p"][0], tot), flush=True)
