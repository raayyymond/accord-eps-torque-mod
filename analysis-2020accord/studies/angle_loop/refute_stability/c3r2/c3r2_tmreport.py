# -*- coding: utf-8 -*-
"""c3r2_tmreport.py -- twomass_<P|F>.npz -> tmreport_<P|F>.txt"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

W = sys.argv[1] if len(sys.argv) > 1 else "P"
Z = np.load(M.OUT / f"twomass_{W}.npz")
A = Z["A"]
MEMS, PLC = list(Z["MEMS"]), list(Z["PLC"])
im, iv, if2, iz2, ir2, ipl, ie, ik, irho, irhov, ifm, izm, ifv, izv, ipk = range(15)
out = [f"== {W}: {len(A)} two-mass stress points =="]
out.append(f"  unstable (rho >= 1): {int((A[:, irho] >= 1).sum())} ; max rho {A[:, irho].max():.4f} ; V295 on the same plants: "
           f"unstable {int((A[:, irhov] >= 1).sum())}, max rho {A[:, irhov].max():.4f}")
out.append(f"  5-30 Hz closed-loop peak > +3 dB: {int((A[:, ipk] > 3).sum())} ; max {A[:, ipk].max():+.2f} dB")
dz = A[:, izm] - A[:, izv]
below = dz < 0
out.append(f"  mode zeta below V295's on the same plant: {int(below.sum())} / {len(A)} ({100 * below.mean():.0f} %) ; "
           f"worst dzeta {dz.min():+.4f}")
j = int(np.argmin(dz))
r = A[j]
out.append(f"     worst: {MEMS[int(r[im])]} v{r[iv]} f2 {r[if2]} z2 {r[iz2]} r2 {r[ir2]} {PLC[int(r[ipl])]} e{int(r[ie])} k{r[ik]:.3f}: "
           f"mode {r[ifm]:.2f} Hz z {r[izm]:.4f} vs V295 {r[ifv]:.2f} Hz z {r[izv]:.4f}")
for f2 in sorted(set(A[:, if2])):
    s = A[:, if2] == f2
    out.append(f"  f2 {f2:4.1f}: below-V295 {100 * below[s].mean():3.0f} % ; min mode zeta {np.nanmin(A[s, izm]):.4f} (V295 "
               f"{np.nanmin(A[s, izv]):.4f}) ; zeta/zeta2 min {np.nanmin(A[s, izm] / A[s, iz2]):.2f} ; max pk {A[s, ipk].max():+.2f} dB")
txt = "\n".join(out)
(M.OUT / f"tmreport_{W}.txt").write_text(txt, encoding="utf-8")
print(txt)
