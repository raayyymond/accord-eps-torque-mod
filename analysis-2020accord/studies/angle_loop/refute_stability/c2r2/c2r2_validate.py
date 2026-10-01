# -*- coding: utf-8 -*-
"""c2r2_validate.py -- positive controls for the independent model before any attack is trusted.
  V1  the four caves' tables parse from the bytes; G at the knots; the table address the cave loads
  V2  Re(T/omega) of V295 / V294 vs the designers' published row (C2 rev2-A sec 3.3) -- the impedance convention
  V3  published PM anchors (rev2-A sec 3.1, rev2-B sec 4.1) under the averaged-hold model
  V4  averaged-hold vs exact periodic: stability verdict and GM agree where they should
ANALYSIS ONLY."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402

D = M.load_designs()
print("== V1 tables (from the cave bytes)")
for nm, d in D.items():
    print(f"  {nm:4s} tbl@{d.tbl_addr:#x} sha {d.sha[:16]} rows {d.rows}")
    print("       G(3.1,8,10,11.75,15.5,17.5,26.9) =", [d.G(v) for v in (3.1, 8, 10, 11.75, 15.5, 17.5, 26.9)])

print("\n== V2 Re(T/omega), T counts per deg/s, d = 2, worst (min) over 1..35 m/s (V29x is speed independent)")
F = np.array([5, 7, 10, 13, 15, 17, 20, 25.0])
pub = {("V294", 0): [1.33, .67, .05, -.25, -.36, -.42, -.44, -.41], ("V295", 0): [2.46, 1.24, .09, -.47, -.66, -.77, -.82, -.76],
       ("V295", 10): [1.69, .08, -1.17, -1.50, -1.44, -1.26, -.89, -.25],
       ("P2", 0): [-.57, -.44, -.39, -.37, -.36, -.35, -.34, -.31], ("F2", 0): [-.84, -.84, -.86, -.84, -.81, -.77, -.69, -.55],
       ("P2", 10): [-.74, -.42, -.23, -.15, -.14, -.15, -.20, -.24], ("F2", 10): [-1.68, -1.62, -1.47, -1.20, -1.00, -.80, -.52, -.10]}
refs = {"V295": M.V295_REF, "V294": M.V294_REF, "P2": D["P2"], "F2": D["F2"]}
grid = np.arange(1.0, 35.01, 0.25)
for (nm, ea), row in pub.items():
    des = refs[nm]
    worst = np.full(len(F), 1e9)
    for v in (grid if des.dkind in ("fresh", "held") else [10.0]):
        worst = np.minimum(worst, M.re_t_over_w(des, v, F, ea, d=2))
    print(f"  {nm} age{ea:2d} mine " + " ".join(f"{x:+.2f}" for x in worst) + "   | published " +
          " ".join(f"{x:+.2f}" for x in row) + f"   max|d| {np.max(np.abs(worst - np.array(row))):.3f}")

print("\n== V3 PM anchors (averaged-hold LTI, min over the 1..35 m/s grid incl. knots)")
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
anchors = [("P2", "nominal", 64.9), ("P2", "J_hi", 46.7), ("P2", "b_q*J1.0", 37.4), ("P2", "b_q*J1.0+h10", 34.0),
           ("P2", "b_lo*J_hi", 37.4), ("P2", "J1.0", 39.0), ("P2", "J1.0+h10", 35.5), ("P2", "ms_free", 47.6),
           ("P2", "b_lo*J_hi*tau6+h10", 30.5), ("F2", "J_hi", 47.0), ("F2", "b_q*J1.0", 39.0), ("F2", "b_q*J1.0+h10", 33.4),
           ("D2a", "b_q*J1.0+h10", 34.0), ("B0r", "b_q*J1.0+h10", 34.0)]
for dn, mn, pubv in anchors:
    best = (1e9, None, None)
    for v in GRID:
        r, _ = M.lti_metrics(D[dn], M.member(mn, v), v)
        if np.isfinite(r["pm"]) and r["pm"] < best[0]:
            best = (r["pm"], v, r["fc"])
    print(f"  {dn:4s} {mn:22s} mine {best[0]:5.1f} @ {best[1]:5.2f} m/s fc {best[2]:.2f} Hz | published {pubv}")

print("\n== V4 averaged-hold vs exact periodic (rho, LTI GM vs exact GM)")
for dn, mn, v in (("P2", "nominal", 12.5), ("P2", "b_q*J1.0+h10", 26.9), ("F2", "b_lo*tau6+h10", 8.0),
                  ("F2", "nominal", 3.1), ("P2", "J_hi", 1.0), ("P2", "mode20", 17.0)):
    pl = M.member(mn, v)
    r, _ = M.lti_metrics(D[dn], pl, v)
    per = M.Periodic(D[dn], pl, v)
    rho, z, f, _ = per.rho_poles()
    gm = M.exact_gm_up(D[dn], pl, v)
    print(f"  {dn} {mn:16s} v {v:5.2f}  LTI PM {r['pm']:5.1f} GMup {r['gm_up']:5.1f} dB | exact rho {rho:.4f} "
          f"least-damped {f:5.2f} Hz z {z:.3f}  exact GMup {gm:5.1f} dB  (n_state {per.n})")
