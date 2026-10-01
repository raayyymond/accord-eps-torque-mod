# -*- coding: utf-8 -*-
"""c3r2_loopsreport.py -- loops_<P|F>.npz -> loopsreport_<P|F>.txt (PD / PD297 / PID80 / PI0, theta = 0 and op points)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

W = sys.argv[1] if len(sys.argv) > 1 else "P"
Z = np.load(M.OUT / f"loops_{W}.npz")
A = Z["A"]
MEMS, AS, FRN, ES, LOOPS = list(Z["MEMS"]), list(Z["AS"]), list(Z["FR"]), list(Z["ES"]), list(Z["LOOPS"])
im, iv, ia, ifr, ie, il, ith, iPM, iFC, igu, igd, irho, ifq, iz = range(14)
MSF = ("ms_free", "b_lo*ms_free", "b_q*ms_free")
out = []
for k, ln in enumerate(LOOPS):
    if W == "P" and ln == "PI0":
        out.append("\n-- PI0: not applicable to the primary (op-skip routes an invalid rate to 0x2A164: no torque path) --")
        continue
    out.append(f"\n-- {W} loop {ln} --")
    for at, asel in (("theta = 0", A[:, ia] == 0), ("op a 1.0-2.5", A[:, ia] > 0)):
        for grp, gs in (("gated non-ms_free", [m not in MSF for m in MEMS]), ("ms_free family", [m in MSF for m in MEMS])):
            gsel = np.array([gs[int(x)] for x in A[:, im]])
            S = A[(A[:, il] == k) & asel & gsel & (A[:, ith] <= 450)]
            if not len(S):
                continue
            fails = []
            for r in S:
                m = MEMS[int(r[im])]
                bar = 45.0 if (m in M.SINGLE and ES[int(r[ie])] <= 0) else 30.0
                if r[iPM] < bar or r[igu] < 6:
                    fails.append(r)
            un = S[(~np.isnan(S[:, irho])) & (S[:, irho] >= 1)]
            r = S[int(np.argmin(S[:, iPM]))]
            fm = sorted(set(MEMS[int(x[im])] for x in fails))
            out.append(f"  {at:13s} {grp:18s}: fails(R2 bars, GM 6) {len(fails):5d} {fm} ; rho>=1 {len(un)}"
                       + (f" max {un[:, irho].max():.5f} ({sorted(set(MEMS[int(x)] for x in un[:, im]))})" if len(un) else "")
                       + f" ; min PM {r[iPM]:.1f} ({MEMS[int(r[im])]} v{r[iv]:.2f} a{AS[int(r[ia])]} {FRN[int(r[ifr])]} "
                         f"e{ES[int(r[ie])]}, ring {r[ifq]:.2f} Hz z {r[iz]:+.3f}) ; min GM {S[:, igu].min():.1f}")
txt = "\n".join(out)
(M.OUT / f"loopsreport_{W}.txt").write_text(txt, encoding="utf-8")
print(txt)
