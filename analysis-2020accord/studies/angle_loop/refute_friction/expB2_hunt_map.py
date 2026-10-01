"""EXP B2: HUNTING MAP -- a constant setpoint, no disturbance, 40 s.  Setpoint = a ramp (2 s) to a hold angle, then
held.  A self-sustained stick-slip limit cycle = slips that continue through the LAST 20 s with the setpoint constant.
Per speed x hold angle x member."""
import sys, json, time
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
members = sys.argv[1].split(",") if len(sys.argv) > 1 else ["nominal"]
SPEEDS = [float(s) for s in sys.argv[2].split(",")] if len(sys.argv) > 2 else [3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.5]
HOLDS = (0.3, 0.55, 1.0, 1.75, 3.0, 5.0, 8.0, 15.0, 30.0)
DUR = 40.0
cols = []
for m in members:
    for v in SPEEDS:
        for A in HOLDS:
            cols.append(dict(member=m, v=v, A=A, ref=lambda t, A=A: float(np.interp(t, [0, 1, 3, 100], [0, 0, A, A]))))
t0 = time.time()
rec = F.run(cols, DUR, rec_I=True)
tt = np.arange(rec["th"].shape[0]) * 1e-3
w = tt >= 20.0
res = []
print("[%.0f s]  member v  hold | slips(last 20 s) maxjump p2p(deg) | T p2p | hunting?" % (time.time() - t0))
for j, c in enumerate(cols):
    th = rec["th"][:, j].astype(float); om = rec["om"][:, j].astype(float); T = rec["T"][:, j].astype(float)
    stuck = om[w] == 0.0
    runs = F.HT._runs(stuck, 100)
    thw = th[w]
    jumps = [abs(thw[min(b + 500, len(thw) - 1)] - thw[b - 1]) for a, b in runs if b < len(thw) - 1]
    nsl = sum(1 for x in jumps if x >= 0.1)
    mj = max(jumps) if jumps else 0.0
    p2p = thw.max() - thw.min()
    Tp = T[w].max() - T[w].min()
    res.append(dict(member=c["member"], v=c["v"], A=c["A"], slips=nsl, maxjump=mj, p2p=p2p, Tp2p=Tp))
    print("%-8s %5.1f %5.2f | %3d  %5.2f  %5.2f | %5.0f | %s" % (c["member"], c["v"], c["A"], nsl, mj, p2p, Tp, "HUNT" if nsl >= 2 else ""))
(OUT / ("expB2_%s.json" % "_".join(members))).write_text(json.dumps(res))
