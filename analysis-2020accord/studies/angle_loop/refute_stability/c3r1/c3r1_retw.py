# -*- coding: utf-8 -*-
"""c3r1_retw.py -- Re(T/omega) 5-25 Hz for C3-P / C3-F vs V294 / V295 under the phase conditions the design's claims
depend on: hold offset e (ages e+1..e+10), kappa, transport, a rate-former window lag rf (resolver-delta mean), and a
one-tick-late fresh read (C3-P).  Worst over 1-35 m/s (T counts per deg/s, > 0 damps).
python c3r1_retw.py -> _scratch/.../retw_out.txt"""
import itertools
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402

D = M.designs()
FQ = np.array([5, 7, 10, 13, 15, 17, 20, 25], float)
SP = np.arange(1.0, 35.01, 0.25)
out = []
P = lambda *a: out.append(" ".join(str(x) for x in a))  # noqa: E731


def worst(nm, **kw):
    return np.min([M.retw(D[nm], v, FQ, **kw) for v in SP], axis=0)


def fmt(a):
    return " ".join(f"{x:+6.2f}" for x in a)


P("Re(T/w) worst over 1-35 m/s; columns", " ".join(f"{int(f)}Hz" for f in FQ))
P("\n(1) the design's own condition (e 0 = ages 1-10, kappa 1, 2 ms, rf 0) and the physical kappa 0.866")
for kap in (1.0, 1 / 1.155):
    for nm in ("V294", "V295", "C3-P", "C3-F"):
        P(f"  k{kap:.3f} {nm:5s}", fmt(worst(nm, kappa=kap)))

P("\n(2) condition grid: candidate worst / V295 worst in the SAME condition, at each frequency.  'X' = V295 damps (>0)"
  " while the candidate anti-damps.  Only candidate-negative entries count.")
rows = []
for e, kap, tau, rf in itertools.product((-1, 0, 2, 5, 10, 20), (0.83, 1 / 1.155, 1.0, 1.155), (0.0, 2.0, 6.0),
                                         (0.0, 0.5, 1.5, 3.0)):
    V = worst("V295", e=e, kappa=kap, tau=tau, rf_ms=rf)
    for nm, late in (("C3-P", 0), ("C3-P", 1), ("C3-F", 0)):
        C = worst(nm, e=e, kappa=kap, tau=tau, rf_ms=rf, abe_late=late)
        r = []
        for c, vv in zip(C, V):
            if c >= 0:
                r.append(0.0)
            elif vv >= 0:
                r.append(np.inf)
            else:
                r.append(c / vv)
        rows.append((nm + ("+late" if late else ""), e, kap, tau, rf, C, V, np.array(r)))
for nm in ("C3-P", "C3-P+late", "C3-F"):
    R = [x for x in rows if x[0] == nm]
    P(f"\n  {nm}: {len(R)} conditions")
    for j, f in enumerate(FQ):
        rr = np.array([x[7][j] for x in R])
        nbad = int(np.sum(rr > 1.0))
        k = int(np.argmax(np.where(np.isfinite(rr), rr, 1e9)))
        x = R[k]
        P(f"    {int(f):2d} Hz: conds > 1x V295: {nbad:3d}/{len(R)}; worst ratio {rr[k]:.2f} at e{x[1]} k{x[2]:.3f} "
          f"tau{x[3]:.0f} rf{x[4]} (cand {x[5][j]:+.2f}, V295 {x[6][j]:+.2f})")
P("\n(3) the design's specific claims re-read: '13 Hz 0.79x V295', '20 Hz 0.52x', 'C3-F 13 Hz 1.9x'")
for nm in ("C3-P", "C3-F"):
    for e in (-1, 0, 10):
        for kap in (1.0, 1 / 1.155):
            for rf in (0.0, 1.5):
                C = worst(nm, e=e, kappa=kap, rf_ms=rf)
                V = worst("V295", e=e, kappa=kap, rf_ms=rf)
                P(f"  {nm} e{e:<3d} k{kap:.3f} rf{rf}: 13 Hz {C[3]:+.2f} vs V295 {V[3]:+.2f} ({C[3] / V[3] if V[3] < 0 else float('inf'):.2f}x);"
                  f" 20 Hz {C[6]:+.2f} vs {V[6]:+.2f} ({C[6] / V[6] if V[6] < 0 else float('inf'):.2f}x)")
(Path(M.OUT) / "retw_out.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
