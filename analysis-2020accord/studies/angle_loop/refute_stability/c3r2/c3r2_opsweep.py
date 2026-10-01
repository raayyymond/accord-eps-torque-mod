# -*- coding: utf-8 -*-
"""c3r2_opsweep.py -- GATE 2 at theta = 0 AND at the curve operating points (k sech^2(theta_op/sat)), C3-rev2-P and -F.

Grid: v 1..35 at 0.25 + plant knots + 0.05 fine at 7..13.5; a in {0 (theta=0), 1.0 .. 2.5 step 0.25}; members SINGLE +
COMBINED + ms_free x {b_lo, b_q} (+ report members); frames gated (nom FA.83 FA1.155 FB.83 FB1.155) + physical (FAc FBc
FAo FBo); hold offsets e in {-1, 0, 10} (ages 0-9 / 1-10 / 11-20).  LTI PM / GM up / fc for every point; EXACT rho and
least-damped pole for every point with LTI PM < 40 (and every a = 0 point at the binding speeds).
Points with theta_op > 450 deg (past the rack) are kept but flagged.
usage: python c3r2_opsweep.py [P|F]   -> _scratch/.../opsweep_<P|F>.npz + opsweep_<P|F>.txt
"""
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

WHICH = sys.argv[1] if len(sys.argv) > 1 else "P"
DES = M.C3R2P if WHICH == "P" else M.C3R2F
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / 1.155),
      ("FB1.155", 1.155, 1 / 1.155), ("FAc", 1 / 1.155, 1.0), ("FBc", 1 / 1.155, 1 / 1.155),
      ("FAo", 1 / 0.962, 1.0), ("FBo", 1 / 0.962, 1 / 0.962))
GATED_FR = (0, 1, 2, 3, 4)
ES = (-1, 0, 10)
AS = (0.0, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5)
MEMS = M.SINGLE + M.COMBINED + M.MSF2 + M.REPORT
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]
                  + [round(x, 2) for x in np.arange(7.0, 13.51, 0.05)]))
F = M.F


def work(args):
    mem, v = args
    res = []
    for ia, a in enumerate(AS):
        pl0, ea = M.member(mem, v)
        th = M.theta_op(v, a) if a else 0.0
        s2 = 1 - math.tanh(th / M.sat(v)) ** 2 if a else 1.0
        pl = M.Plant(pl0.J, pl0.b, pl0.k * s2, pl0.d, pl0.mode)
        for ifr, (fn, kap, jb) in enumerate(FR):
            ch = M.plant_frf(pl, F, jb)
            for ie, e in enumerate(ES):
                L, Tr = M.loop_L(DES, pl, v, e=e + ea, kappa=kap, jb=jb, chans=ch)
                PM, FC, gmu, gmd = M.pm_gm(L)
                pk = M.peak530(L, Tr)
                rho = fr = z = np.nan
                if PM < 40.0:
                    rho, fr, z = M.Periodic(DES, pl, v, e=e + ea, kappa=kap, jb=jb).rho_ring()
                res.append((MEMS.index(mem), v, ia, ifr, ie, th, PM, FC, gmu, gmd, pk, rho, fr, z))
    return res


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(m, v) for m in MEMS for v in GRID]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    A = np.array(R, float)
    np.savez_compressed(M.OUT / f"opsweep_{WHICH}.npz", A=A, MEMS=np.array(MEMS), AS=np.array(AS),
                        FR=np.array([f[0] for f in FR]), ES=np.array(ES))
    print(f"{DES.name}: {len(A)} points in {time.time() - t0:.0f} s")
