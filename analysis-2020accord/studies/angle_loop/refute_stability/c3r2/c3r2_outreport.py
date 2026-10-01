# -*- coding: utf-8 -*-
"""c3r2_outreport.py -- reads outer_<P|F>.npz -> outreport_<P|F>.txt.  Per tau_o: exact rho >= 1, the least-damped ring
(frequency vs R3*'s 0.25 Hz lower edge), the actuator-break PM of the total loop, and the outer-break PM/GM (the
round-1 refuter's measure, which the design quotes as 'tau_o >= 1 s has PM >= 56, GM >= 8 dB')."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

WHICH = sys.argv[1] if len(sys.argv) > 1 else "P"
Z = np.load(M.OUT / f"outer_{WHICH}.npz")
A = Z["A"]
MEMS, AS, FRN, ES, TAUS = list(Z["MEMS"]), list(Z["AS"]), list(Z["FR"]), list(Z["ES"]), list(Z["TAUS"])
im, iv, ia, ifr, ie, it, ith, iPM, iFC, igu, igd, irho, ifq, iz, iPMo, iFCo, igo = range(17)
MSF = ("ms_free", "b_lo*ms_free", "b_q*ms_free")
out = []
P = out.append
mem = lambda r: MEMS[int(r[im])]  # noqa: E731
P(f"== {WHICH}: {len(A)} points (members {len(MEMS)}, a {AS}, frames {FRN}, e {ES}, tau_o {TAUS}) ==")
for k, tau in enumerate(TAUS):
    P(f"\n-- tau_o = {tau:.1f} s --")
    for at, asel in (("theta = 0", A[:, ia] == 0), ("op points a 1.0-2.5", A[:, ia] > 0)):
        for grp, gsel in (("gated non-ms_free", np.array([mem(r) not in MSF for r in A])),
                          ("ms_free family", np.array([mem(r) in MSF for r in A]))):
            S = A[(A[:, it] == k) & asel & gsel & (A[:, ith] <= 450)]
            if not len(S):
                continue
            un = S[(~np.isnan(S[:, irho])) & (S[:, irho] >= 1)]
            r = S[int(np.argmin(S[:, iPM]))]
            ro = S[int(np.argmin(S[:, iPMo]))]
            go = S[int(np.argmin(S[:, igo]))]
            lowz = S[(~np.isnan(S[:, iz])) & (S[:, iz] < 0.10)]
            P(f"  {at:20s} {grp:18s}: rho>=1 {len(un):5d}" + (f" (max {un[:, irho].max():.5f}, rings "
              f"{un[:, ifq].min():.2f}-{un[:, ifq].max():.2f} Hz, members {sorted(set(mem(x) for x in un))})" if len(un) else "")
              + f"; zeta<0.10 {len(lowz)}" + (f" (rings {lowz[:, ifq].min():.2f}-{lowz[:, ifq].max():.2f} Hz)" if len(lowz) else ""))
            P(f"      actuator-break min PM {r[iPM]:5.1f} ({mem(r)} v{r[iv]:.2f} a{AS[int(r[ia])]} {FRN[int(r[ifr])]} e{ES[int(r[ie])]} "
              f"fc {r[iFC]:.2f}; exact rho {r[irho]:.4f} ring {r[ifq]:.2f} Hz z {r[iz]:+.3f}) ; GMup min {S[:, igu].min():.1f}")
            P(f"      outer-break    min PM {ro[iPMo]:5.1f} ({mem(ro)} v{ro[iv]:.2f} a{AS[int(ro[ia])]} {FRN[int(ro[ifr])]} "
              f"e{ES[int(ro[ie])]} fc {ro[iFCo]:.2f} Hz) ; min GM {go[igo]:.1f} dB ({mem(go)} v{go[iv]:.2f} a{AS[int(go[ia])]})")
            # per-member worst actuator PM at this tau (gated members only)
            if grp == "gated non-ms_free" and at.startswith("op"):
                ws = []
                for m in sorted(set(mem(x) for x in S)):
                    X = S[[mem(x) == m for x in S]]
                    j = int(np.argmin(X[:, iPM]))
                    ws.append((X[j, iPM], m))
                ws.sort()
                P("      worst members (act PM): " + ", ".join(f"{m} {p:.1f}" for p, m in ws[:6]))
txt = "\n".join(out)
(M.OUT / f"outreport_{WHICH}.txt").write_text(txt, encoding="utf-8")
print(txt)
