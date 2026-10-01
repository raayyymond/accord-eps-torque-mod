"""EXP G: AMPLITUDE DEPENDENCE of the tracking gain -- the goal's tracking criterion scored the way the harness scores it
(slope of the 100 Hz wire angle on the received setpoint, after the first cycle) but at LANE-KEEPING amplitudes.
The harness's s02/s05 amplitudes are 0.3*A_TURN = 9 / 3.6 / 1.5 / 0.9 / 0.75 deg at 8 / 12.5 / 19 / 26 / 30 m/s; a
friction / quantiser dead zone shows only at small amplitude."""
import sys, json
import numpy as np
import fric_lib as F
OUT = F.HERE.parents[3] / "_scratch" / "angle_loop" / "refute-friction"
members = sys.argv[1].split(",") if len(sys.argv) > 1 else ["nominal"]
SPEEDS = (5.0, 8.0, 10.0, 12.5, 19.0, 26.0, 30.0)
AMPS = (0.2, 0.3, 0.5, 1.0, 2.0)
FREQS = (0.2, 0.5)
DUR = 15.0
cols = []
for m in members:
    for v in SPEEDS:
        for a in AMPS:
            for f in FREQS:
                cols.append(dict(member=m, v=v, amp=a, f=f, ref=lambda t, a=a, f=f: a * np.sin(2 * np.pi * f * t)))
rec = F.run(cols, DUR)
wire = rec["wire"].astype(float) / 10.0
nf = wire.shape[0]
idx = (np.arange(nf) * 10 + F.HT.SLOT4_PHASE).clip(0, rec["th"].shape[0] - 1)
fr_t = idx * 1e-3
res = []
print("member   v    amp   f  | track gain (harness def) | fit gain  phase deg | stick%")
tt = np.arange(rec["th"].shape[0]) * 1e-3
for j, c in enumerate(cols):
    fw = fr_t >= 1.0 / c["f"]
    X = rec["sp"][idx, j][fw].astype(float); Y = wire[fw, j]
    xm = X - X.mean()
    g = (xm * (Y - Y.mean())).sum() / (xm ** 2).sum()
    w = tt >= 1.0 / c["f"]
    th = rec["th"][w, j].astype(float)
    s_ = np.sin(2 * np.pi * c["f"] * tt[w]); c_ = np.cos(2 * np.pi * c["f"] * tt[w])
    A_ = 2 * np.mean(th * s_); B_ = 2 * np.mean(th * c_)
    fg = np.hypot(A_, B_) / c["amp"]; ph = np.degrees(np.arctan2(B_, A_))
    om = rec["om"][w, j]
    stick = 100.0 * np.mean(om == 0.0)
    res.append(dict(member=c["member"], v=c["v"], amp=c["amp"], f=c["f"], gain=float(g), fit=float(fg), ph=float(ph), stick=float(stick)))
    flag = "  <-- outside 0.95-1.05" if (c["v"] >= 8 and not (0.95 <= g <= 1.05)) else ""
    print("%-8s %5.1f %4.1f %4.1f | %6.3f | %6.3f %7.1f | %5.1f%s" % (c["member"], c["v"], c["amp"], c["f"], g, fg, ph, stick, flag))
(OUT / ("expG_%s.json" % "_".join(members))).write_text(json.dumps(res))
