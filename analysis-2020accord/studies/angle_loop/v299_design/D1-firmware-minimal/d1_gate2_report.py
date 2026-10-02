# -*- coding: utf-8 -*-
"""d1_gate2_report.py -- re-tabulate d1_gate2's rows inside the PHYSICAL envelope (theta_op <= the angle of a 3.0 m/s^2
curve at that speed, SR 16, L 2.83, and <= 470 deg lock) and split the J~2 ms_free products (declared report-only by
the V298 design) from the credible set.  Reads out/d1_gate2_rows.npy.  Wall < 1 s."""
import math, time
from pathlib import Path
import numpy as np
t0 = time.time()
HERE = Path(__file__).resolve().parent
import sys
R = np.load(HERE.parents[4] / "_scratch" / "v299_D1" / ("d1_gate2_kd_rows.npy" if len(sys.argv) > 1 else "d1_gate2_rows.npy"))
part, dn, mem = R[:, 0], R[:, 1], R[:, 2]
v, th = R[:, 3].astype(float), R[:, 4].astype(float)
noI = R[:, 5] == "True"
e = R[:, 6].astype(int)
PM, GM, pk, rho, bar = (R[:, i].astype(float) for i in (8, 10, 11, 12, 13))
thmax = np.minimum(16 * 2.83 * 3.0 / v ** 2 * 180 / math.pi, 470.0)
phys = th <= thmax + 1e-6
msf = np.char.find(mem.astype(str), "ms_free") >= 0
out = ["d1_gate2_report: PHYSICAL op-points only (theta <= theta(v, 3 m/s^2), <= 470 deg)",
       "part design loop | credible set: n PM<bar GM<6 pk>3 rho>=1 worst(PM-bar @ member v th e) | ms_free products: n PM<bar"]
for p_ in ("A", "B", "C", "D", "E"):
    for d in sorted(set(dn[part == p_])):
        for lp in (False, True):
            m = (part == p_) & (dn == d) & (noI == lp) & phys
            c = m & ~msf
            f = c & (PM < bar)
            if c.sum() == 0:
                continue
            j = np.flatnonzero(c)[np.argmin((PM - bar)[c])]
            out.append(f"{p_} {d:8s} {'PD ' if lp else 'PID'} | {c.sum():5d} {f.sum():4d} {(c & (GM < 6)).sum():3d} "
                       f"{(c & (pk > 3)).sum():3d} {(c & (rho >= 1)).sum():3d}  {PM[j]-bar[j]:+6.1f} @ {mem[j]} {v[j]} th{th[j]:.0f} e{e[j]}"
                       f" | {(m & msf).sum():5d} {(m & msf & (PM < bar)).sum():4d}")
out.append("")
out.append("B/C per speed (credible set, physical): worst PM - bar, PID | PD")
for d in ("V298", "Kp168", "Kp224", "G0-1400", "G0-1600", "Kd36", "Kd24"):
    row = []
    for vv in (2.0, 3.1, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0):
        m = np.isin(part, ["B", "C", "E"]) & (dn == d) & phys & ~msf & (v == vv)
        if m.sum() == 0:
            row.append("   -   ")
            continue
        a = (PM - bar)[m & ~noI].min() if (m & ~noI).any() else np.nan
        b = (PM - bar)[m & noI].min() if (m & noI).any() else np.nan
        row.append(f"{a:+4.0f}|{b:+3.0f}")
    out.append(f"  {d:8s} " + " ".join(row) + "   (v 2 3.1 4 5 6 7 8 9 10)")
out.append(f"wall {time.time()-t0:.2f} s")
(HERE / "out" / ("d1_gate2_kd_report.txt" if len(sys.argv) > 1 else "d1_gate2_report.txt")).write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
