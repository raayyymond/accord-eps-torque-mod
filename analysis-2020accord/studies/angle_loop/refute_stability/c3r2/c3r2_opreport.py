# -*- coding: utf-8 -*-
"""c3r2_opreport.py -- reads opsweep_<P|F>.npz and writes opreport_<P|F>.txt: theta = 0 GATE 2, the operating-point GATE 2
(v >= 8 and v < 8 separately, theta_op <= 450 deg), exact rho >= 1, the per-member worst, and the rings of every failing
point (frequency, zeta) against the declared M-F1 (0.45-0.9 Hz, zeta 0.02-0.12, PM 1-21, rho < 1) and R3* (0.25-5.5 Hz)."""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

WHICH = sys.argv[1] if len(sys.argv) > 1 else "P"
Z = np.load(M.OUT / f"opsweep_{WHICH}.npz")
A = Z["A"]
MEMS = list(Z["MEMS"])
AS = list(Z["AS"])
FRN = list(Z["FR"])
ES = list(Z["ES"])
GATED_FR = [0, 1, 2, 3, 4]
SINGLE, COMBINED, MSF2 = M.SINGLE, M.COMBINED, M.MSF2
# columns
im, iv, ia, ifr, ie, ith, iPM, iFC, igu, igd, ipk, irho, ifr_, iz = range(14)
out = []
P = out.append


def bar(mem, e, strict):
    if mem in SINGLE:
        return 45.0 if (e <= 0 or strict) else 30.0
    if mem in COMBINED or mem in MSF2:
        return 30.0
    return None


def rows(sel):
    return A[sel]


mem_of = lambda r: MEMS[int(r[im])]  # noqa: E731
e_of = lambda r: ES[int(r[ie])]       # noqa: E731
fr_of = lambda r: FRN[int(r[ifr])]    # noqa: E731

gfr = np.isin(A[:, ifr], GATED_FR)
P(f"== {WHICH}: {len(A)} points ==")
for title, asel in (("theta = 0", A[:, ia] == 0), ("op points a>=1.0", A[:, ia] > 0)):
    for vt, vsel in (("v >= 8", A[:, iv] >= 8.0), ("v < 8", A[:, iv] < 8.0)):
        phys = A[:, ith] <= 450.0
        S = A[asel & vsel & gfr & phys]
        P(f"\n-- {title}, {vt}, gated frames, theta_op <= 450 deg: {len(S)} pts --")
        for strict in (False, True):
            fails = defaultdict(list)
            for r in S:
                m = mem_of(r)
                b = bar(m, e_of(r), strict)
                if b is None:
                    continue
                if r[iPM] < b or r[igu] < 6.0 or r[ipk] > 3.0 or (not np.isnan(r[irho]) and r[irho] >= 1.0):
                    fails[m].append(r)
            tag = "STRICT (aged singles at 45)" if strict else "R2 (aged singles at 30)"
            P(f"  [{tag}] failing members: " + (", ".join(f"{m} {len(v)}" for m, v in fails.items()) or "none"))
        un = S[(~np.isnan(S[:, irho])) & (S[:, irho] >= 1.0)]
        P(f"  exact rho >= 1: {len(un)}" + (f"; max {un[:, irho].max():.5f}" if len(un) else ""))
        for r in un[np.argsort(-un[:, irho])][:12]:
            P(f"     {mem_of(r):14s} v {r[iv]:6.2f} a {AS[int(r[ia])]:.2f} th {r[ith]:5.1f} {fr_of(r):7s} e{e_of(r):3d} "
              f"PM {r[iPM]:5.1f} rho {r[irho]:.5f} ring {r[ifr_]:.2f} Hz zeta {r[iz]:+.3f}")
        # per-member worst (PM - bar, R2 reading) and max rho
        P("  per member: worst PM (frame, e, v, a) | max rho (point) | min GMup | max pk")
        for m in SINGLE + COMBINED + MSF2:
            X = S[[mem_of(r) == m for r in S]]
            if not len(X):
                continue
            j = int(np.argmin(X[:, iPM]))
            r = X[j]
            rr = X[~np.isnan(X[:, irho])]
            rmax = f"{rr[:, irho].max():.4f}" if len(rr) else "  -   "
            if len(rr):
                q = rr[int(np.argmax(rr[:, irho]))]
                rmax += f" (v{q[iv]:.2f} a{AS[int(q[ia])]:.2f} {fr_of(q)} e{e_of(q)} {q[ifr_]:.2f}Hz z{q[iz]:+.3f})"
            P(f"    {m:14s} PM {r[iPM]:5.1f} ({fr_of(r)}, e{e_of(r)}, v{r[iv]:.2f}, a{AS[int(r[ia])]:.2f}, "
              f"{r[iFC]:.2f} Hz) | rho {rmax} | GM {X[:, igu].min():5.1f} | pk {X[:, ipk].max():+5.1f}")
        # rings of PM < 30 points
        low = S[(S[:, iPM] < 30) & (~np.isnan(S[:, irho]))]
        if len(low):
            for grp, mems in (("ms_free family", ("ms_free",) + MSF2), ("gated non-ms_free", None)):
                sel = np.array([(mem_of(r) in mems) if mems else (mem_of(r) in SINGLE + COMBINED and mem_of(r) != "ms_free")
                                for r in low])
                X = low[sel]
                if not len(X):
                    P(f"  PM<30 rings [{grp}]: none")
                    continue
                P(f"  PM<30 rings [{grp}]: {len(X)} pts; ring f {np.nanmin(X[:, ifr_]):.2f}-{np.nanmax(X[:, ifr_]):.2f} Hz; "
                  f"zeta {np.nanmin(X[:, iz]):+.3f}..{np.nanmax(X[:, iz]):+.3f}; PM {X[:, iPM].min():.1f}-{X[:, iPM].max():.1f}; "
                  f"v {X[:, iv].min():.2f}-{X[:, iv].max():.2f}; rho max {X[:, irho].max():.5f}")
# physical frames report
P("\n-- physical frame points (FAc FBc FAo FBo), op points v >= 8, theta_op <= 450: worst per member --")
S = A[(~gfr) & (A[:, ia] > 0) & (A[:, iv] >= 8) & (A[:, ith] <= 450)]
for m in SINGLE + COMBINED + MSF2:
    X = S[[mem_of(r) == m for r in S]]
    if len(X):
        r = X[int(np.argmin(X[:, iPM]))]
        rr = X[~np.isnan(X[:, irho])]
        P(f"    {m:14s} PM {r[iPM]:5.1f} ({fr_of(r)}, e{e_of(r)}, v{r[iv]:.2f}, a{AS[int(r[ia])]:.2f}) rho max "
          f"{(rr[:, irho].max() if len(rr) else float('nan')):.4f}")
# J1.3 inside its 10-16 m/s band (the brief: 'up to 1.3 at 10-16 m/s not excluded')
P("\n-- J1.3 family restricted to 10..16 m/s (op points, gated frames) --")
S = A[gfr & (A[:, ith] <= 450) & (A[:, iv] >= 10) & (A[:, iv] <= 16)]
for m in ("J1.3", "b_q*J1.3"):
    X = S[[mem_of(r) == m for r in S]]
    r = X[int(np.argmin(X[:, iPM]))]
    rr = X[~np.isnan(X[:, irho])]
    n30 = int((X[:, iPM] < 30).sum())
    P(f"    {m:10s} worst PM {r[iPM]:5.1f} ({fr_of(r)}, e{e_of(r)}, v{r[iv]:.2f}, a{AS[int(r[ia])]:.2f}, ring "
      f"{r[ifr_]:.2f} Hz z{r[iz]:+.3f}) ; PM<30 at {n30} pts ; rho max {(rr[:, irho].max() if len(rr) else float('nan')):.4f}")
# report members
P("\n-- report members (J1.3, b_q*J1.3, J_hi2, b_lo*J_hi2, x tau6 products): worst PM / max rho, op points, gated frames --")
S = A[gfr & (A[:, ith] <= 450)]
for m in M.REPORT:
    X = S[[mem_of(r) == m for r in S]]
    if len(X):
        r = X[int(np.argmin(X[:, iPM]))]
        rr = X[~np.isnan(X[:, irho])]
        P(f"    {m:18s} PM {r[iPM]:5.1f} ({fr_of(r)}, e{e_of(r)}, v{r[iv]:.2f}, a{AS[int(r[ia])]:.2f}) rho max "
          f"{(rr[:, irho].max() if len(rr) else float('nan')):.4f}")
txt = "\n".join(out)
(M.OUT / f"opreport_{WHICH}.txt").write_text(txt, encoding="utf-8")
print(txt)
