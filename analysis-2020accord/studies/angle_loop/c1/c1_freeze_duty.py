# -*- coding: utf-8 -*-
"""c1_freeze_duty.py -- what does the C1 freeze cost when hands-off driver-torque noise crosses THR (|gp-0x4f68| > 512)?
Route a6 (c1_handsoff_torque.py, EVIDENCE): engaged & not pressed, |0x18F| > 500 wire in 2.9 % of frames overall,
25 % at |rate| 10-30 deg/s, 48 % at 30-60 deg/s.  Here the torque word is a random telegraph that sits above THR for a
fraction `duty` of the time in bursts of 50-300 ms (BELIEF: the burst shape), on the harness's own tracking references
(0.2 / 0.5 Hz sines of 0.3*A_TURN, and a ramp-and-hold of A_TURN), C1 lane, nominal plant (fric_lib.run).
Reports tracking gain (harness definition), turn-hold ratio, max hold error, per duty 0 / 3 / 10 / 25 / 50 %."""
import sys, json
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C
F = C.install_fric(tbl=C.c1_table(), thr=C.FRZ_THR, rampfrz=True, pol="freeze")
HT = C.HT
SPEEDS = (8.0, 12.5, 19.0, 26.0)
DUTIES = (0.0, 0.03, 0.10, 0.25, 0.50)
rng = np.random.default_rng(5)
def telegraph(duty, dur, seed):
    r = np.random.default_rng(seed)
    n = int(dur * 1000) + 10
    on = np.zeros(n, bool)
    if duty > 0:
        t = 0
        while t < n:
            L = int(r.integers(50, 300))
            gap = int(L * (1 - duty) / duty)
            t += int(r.integers(0, max(gap * 2, 1)))
            on[t:t + L] = True
            t += L
    return on
out = []
for kind in ("s02", "s05", "rh"):
    cols = []
    for v in SPEEDS:
        A = HT.A_TURN[v]
        for d in DUTIES:
            if kind == "rh":
                dur = 1.0 + 3.0 + 3.0 + 2.0
                ref = lambda t, A=A: float(np.interp(t, [0, 0.5, 1.5, 4.5, 100], [0, 0, A, A, A]))
            else:
                f = 0.2 if kind == "s02" else 0.5
                dur = (2.6 if kind == "s02" else 4.6) / f
                ref = lambda t, A=A, f=f: 0.3 * A * np.sin(2 * np.pi * f * t)
            on = telegraph(d, dur, int(v * 100 + d * 1000))
            cols.append(dict(member="nominal", v=v, duty=d, ref=ref, tq=lambda t, on=on: 700 if on[int(t * 1000)] else 0, dur=dur))
    dur = max(c["dur"] for c in cols)
    rec = F.run(cols, dur)
    wire = rec["wire"].astype(float) / 10.0
    nf = wire.shape[0]
    idx = (np.arange(nf) * 10 + HT.SLOT4_PHASE).clip(0, rec["th"].shape[0] - 1)
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    for j, c in enumerate(cols):
        if kind == "rh":
            w = (tt >= 3.0) & (tt < 4.5)
            val = float((rec["th"][w, j] / HT.A_TURN[c["v"]]).mean())
            err = float(np.abs(rec["sp"][w, j] - rec["th"][w, j]).max())
            out.append((kind, c["v"], c["duty"], val, err))
        else:
            f = 0.2 if kind == "s02" else 0.5
            fw = idx * 1e-3 >= 1.0 / f
            X = rec["sp"][idx, j][fw].astype(float); Y = wire[fw, j]; xm = X - X.mean()
            g = float((xm * (Y - Y.mean())).sum() / (xm ** 2).sum())
            out.append((kind, c["v"], c["duty"], g, 0.0))
lines = ["freeze duty -> tracking gain (s02, s05) and turn-hold ratio / max hold error deg (rh), C1, nominal plant"]
for v in SPEEDS:
    cells = []
    for d in DUTIES:
        s2 = [o for o in out if o[0] == "s02" and o[1] == v and o[2] == d][0][3]
        s5 = [o for o in out if o[0] == "s05" and o[1] == v and o[2] == d][0][3]
        rh = [o for o in out if o[0] == "rh" and o[1] == v and o[2] == d][0]
        cells.append(f"duty {d:4.2f}: {s2:.3f}/{s5:.3f} hold {rh[3]:.3f} err {rh[4]:.2f}")
    lines.append(f"  v {v:4.1f}: " + " | ".join(cells))
txt = "\n".join(lines)
print(txt)
(HERE / "freeze_duty.txt").write_text(txt, encoding="utf-8")
