# -*- coding: utf-8 -*-
"""c3r2_outdetail.py -- tau_o = 1.0 / 2.0 s detail: per gated member (tier bars, e0 vs e10), the outer-break GM/PM, the
least-damped < 5 Hz ring, and the exact rho >= 1 points.  -> outdetail_<P|F>.txt"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
W = sys.argv[1] if len(sys.argv) > 1 else "P"
Z = np.load(M.OUT / f"outer_{W}.npz"); A = Z["A"]
MEMS, AS, FRN, ES, TAUS = list(Z["MEMS"]), list(Z["AS"]), list(Z["FR"]), list(Z["ES"]), list(Z["TAUS"])
im, iv, ia, ifr, ie, it, ith, iPM, iFC, igu, igd, irho, ifq, iz, iPMo, iFCo, igo = range(17)
out = []
for tau in (1.0, 2.0):
    k = TAUS.index(tau)
    out.append(f"\n== {W} tau_o {tau} s, op points a 1.0-2.5 (theta_op <= 450), gated frames ==")
    out.append("member        e  | act PM (pt)                      | outer PM | outer GM (pt)            | least-damped <5 Hz ring (pt)        | max rho")
    for m in M.SINGLE + M.COMBINED + M.MSF2:
        for e in (0, 10):
            S = A[(A[:, it] == k) & (A[:, ia] > 0) & (A[:, im] == MEMS.index(m)) & (A[:, ie] == ES.index(e)) & (A[:, ith] <= 450)]
            r = S[np.argmin(S[:, iPM])]; g = S[np.argmin(S[:, igo])]; o = S[np.argmin(S[:, iPMo])]
            R = S[(~np.isnan(S[:, iz])) & (S[:, ifq] < 5)]
            zs = f"{R[np.argmin(R[:, iz]), iz]:+.3f} {R[np.argmin(R[:, iz]), ifq]:.2f} Hz v{R[np.argmin(R[:, iz]), iv]:.2f} a{AS[int(R[np.argmin(R[:, iz]), ia])]}" if len(R) else "-"
            mr = f"{np.nanmax(S[:, irho]):.5f}" if np.isfinite(S[:, irho]).any() else "-"
            bar = 45 if (m in M.SINGLE and e == 0) else 30
            flag = " <" if r[iPM] < bar else ""
            out.append(f"{m:13s} {e:2d} | {r[iPM]:5.1f}{flag:2s} v{r[iv]:5.2f} a{AS[int(r[ia])]} {FRN[int(r[ifr])]:7s} | {o[iPMo]:5.1f}    | "
                       f"{g[igo]:5.1f} v{g[iv]:5.2f} a{AS[int(g[ia])]} {FRN[int(g[ifr])]:7s} | {zs:35s} | {mr}")
    S = A[(A[:, it] == k) & (A[:, ia] > 0) & (A[:, ith] <= 450)]
    U = S[(~np.isnan(S[:, irho])) & (S[:, irho] >= 1)]
    out.append(f"rho>=1 points: {len(U)}")
    for r in U[np.argsort(-U[:, irho])][:10]:
        out.append(f"   {MEMS[int(r[im])]:13s} v{r[iv]:6.2f} a{AS[int(r[ia])]} th {r[ith]:5.1f} {FRN[int(r[ifr])]:7s} e{ES[int(r[ie])]:2d} rho {r[irho]:.5f} ring {r[ifq]:.2f} Hz z {r[iz]:+.4f} (act PM {r[iPM]:.1f}, outer GM {r[igo]:.1f})")
    # speeds/a of rho>=1 by member
    for m in sorted(set(MEMS[int(x)] for x in U[:, im])):
        X = U[U[:, im] == MEMS.index(m)]
        out.append(f"   {m}: {len(X)} pts, v {X[:, iv].min():.2f}-{X[:, iv].max():.2f}, a {sorted(set(AS[int(x)] for x in X[:, ia]))}, frames {sorted(set(FRN[int(x)] for x in X[:, ifr]))}, e {sorted(set(ES[int(x)] for x in X[:, ie]))}")
txt = "\n".join(out)
(M.OUT / f"outdetail_{W}.txt").write_text(txt, encoding="utf-8")
print(txt)
