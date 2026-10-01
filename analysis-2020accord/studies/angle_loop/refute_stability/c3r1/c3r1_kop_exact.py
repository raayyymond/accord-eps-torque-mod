# -*- coding: utf-8 -*-
"""c3r1_kop_exact.py -- exact periodic rho at every operating point (kop.json) whose LTI PM is below 30 deg, v >= 8:
how many are linearly UNSTABLE, and the least-damped pole there.  -> _scratch/.../kop_exact_out.txt"""
import json
import math
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_kop as K  # noqa: E402
import c3r1_sweep as S  # noqa: E402

D = M.designs()
FR = {f[0]: f for f in S.FRAMES}


def work(r):
    dn, noI, mem, v, a, th, s2, fn, e, PM, FC, GM = r
    _, kap, jb = FR[fn]
    pl = M.member(mem, v)
    pl.k *= s2
    rho, f, z, _ = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb).rho_ring()
    return (dn, mem, v, a, fn, e, PM, rho, f, z)


if __name__ == "__main__":
    R = json.load(open(M.OUT / "kop.json"))
    sel = [r for r in R if not r[1] and r[3] >= 8.0 and r[9] < 30.0]
    with Pool(14) as pool:
        X = pool.map(work, sel, chunksize=8)
    out = []
    for dn in ("C3-P", "C3-F"):
        Y = [x for x in X if x[0] == dn]
        un = [x for x in Y if x[7] >= 1.0]
        out.append(f"{dn}: {len(Y)} operating points (v >= 8) with LTI PM < 30; exact rho >= 1 (UNSTABLE): {len(un)}")
        by = {}
        for x in un:
            by.setdefault((x[1], x[3]), []).append(x)
        for (m, a), L in sorted(by.items()):
            w = max(L, key=lambda x: x[7])
            vs = sorted(set(x[2] for x in L))
            out.append(f"   {m:13s} a{a}: {len(L)} unstable pts at {vs[0]}..{vs[-1]} m/s; worst rho {w[7]:.4f} ({w[8]:.2f} Hz zeta {w[9]:.3f})"
                       f" at {w[2]} {w[4]} e{w[5]}; frames {sorted(set(x[4] for x in L))}")
        nomf = [x for x in un if x[4] == "nom" and x[5] == 0]
        out.append(f"   of which in the NOMINAL frame at native hold ages: {len(nomf)}"
                   + (f" ({sorted(set((x[1], x[3]) for x in nomf))})" if nomf else ""))
    (Path(M.OUT) / "kop_exact_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
