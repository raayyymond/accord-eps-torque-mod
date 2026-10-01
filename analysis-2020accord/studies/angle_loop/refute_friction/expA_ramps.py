"""EXP A: slow setpoint ramps (curve entry/exit at lane-keeping steering rates) -- dwell-then-jump with the time
harness's OWN detector (HT.dwell_jump), per speed, rate and member.  The harness never ran a slow ramp: its references
are 0.2/0.5/0.3 Hz sinusoids and 1-3 s ramps (>= 2.5 deg/s at every speed)."""
import sys, json, time
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
SPEEDS = (3.0, 4.0, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 10.0, 12.5, 19.0, 26.0)
RATES = (0.25, 0.5, 1.0, 2.0)
members = sys.argv[1].split(",") if len(sys.argv) > 1 else ["nominal"]
T0, TR, TH = 1.0, 8.0, 4.0
DUR = T0 + TR + TH + TR + TH
def mkref(r):
    A = r * TR
    return lambda t: float(np.interp(t, [0, T0, T0 + TR, T0 + TR + TH, T0 + 2 * TR + TH, DUR], [0, 0, A, A, 0, 0]))
cols = []
for m in members:
    for v in SPEEDS:
        for r in RATES:
            cols.append(dict(member=m, v=v, rate=r, ref=mkref(r)))
t = time.time()
rec = F.run(cols, DUR)
ev, jmax, dw, stick = F.dj_on(rec, T0, DUR)
sl = F.slips(rec, T0, DUR)
res = []
print("member  v   rate  dj_ev  max_snap  stick%%  hold-slips(all)   [run %.0f s]" % (time.time() - t))
for j, c in enumerate(cols):
    res.append(dict(member=c["member"], v=c["v"], rate=c["rate"], ev=int(ev[j]), jmax=float(jmax[j]), stick=float(stick[j]), slips=int(sl[j]), dw_excess_pm=float(dw[j])))
    print("%-8s %5.1f %5.2f  %3d   %5.2f   %5.1f   %3d   dwell-excess/min %5.1f" % (c["member"], c["v"], c["rate"], ev[j], jmax[j], stick[j], sl[j], dw[j]))
(OUT / ("expA_%s.json" % "_".join(members))).write_text(json.dumps(res))
