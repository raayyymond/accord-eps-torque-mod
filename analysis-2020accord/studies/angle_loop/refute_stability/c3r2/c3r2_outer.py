# -*- coding: utf-8 -*-
"""c3r2_outer.py -- the fork outer-loop stand-in (100 Hz angle integral on the setpoint, 60 ms round trip) closed around
the C3-rev2 inner loop, at theta = 0 AND at the curve operating points.  tau_o in {0.3, 0.5, 1.0, 2.0} s.
LTI PM/GM on the total loop; EXACT rho with the fork as explicit states for every point with LTI PM < 35 or GM < 6.
usage: python c3r2_outer.py [P|F] -> outer_<P|F>.npz"""
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
DES = {"P": M.C3R2P, "F": M.C3R2F, "P56": M.C3P56}[WHICH]
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / 1.155),
      ("FB1.155", 1.155, 1 / 1.155))
ES = (0, 10)
AS = (0.0, 1.0, 1.5, 2.0, 2.5)
TAUS = (0.3, 0.5, 1.0, 2.0)
MEMS = M.SINGLE + M.COMBINED + M.MSF2
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9]
                  + [round(x, 2) for x in np.arange(8.0, 16.01, 0.25)]))
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
                Lin, KCP = M.loop_L(DES, pl, v, e=e + ea, kappa=kap, jb=jb, chans=ch)
                Tin = KCP / (1 + Lin)
                w = 2 * np.pi * F
                for it, tau in enumerate(TAUS):
                    L, Tr = M.loop_L(DES, pl, v, e=e + ea, kappa=kap, jb=jb, chans=ch, tau_o=tau)
                    PM, FC, gmu, gmd = M.pm_gm(L)
                    Lo = Tin * np.exp(-1j * w * 0.060) * (0.01 / tau) / (1 - np.exp(-1j * w * 0.01))
                    PMo, FCo, gmuo, gmdo = M.pm_gm(Lo)
                    rho = fr = z = np.nan
                    if PM < 35.0 or gmu < 6.0 or PMo < 45.0 or gmuo < 6.0:
                        rho, fr, z = M.Periodic(DES, pl, v, e=e + ea, kappa=kap, jb=jb, tau_o=tau).rho_ring()
                    res.append((MEMS.index(mem), v, ia, ifr, ie, it, th, PM, FC, gmu, gmd, rho, fr, z, PMo, FCo, gmuo))
    return res


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(m, v) for m in MEMS for v in GRID]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    A = np.array(R, float)
    np.savez_compressed(M.OUT / f"outer_{WHICH}.npz", A=A, MEMS=np.array(MEMS), AS=np.array(AS),
                        FR=np.array([f[0] for f in FR]), ES=np.array(ES), TAUS=np.array(TAUS))
    print(f"{DES.name}: {len(A)} points in {time.time() - t0:.0f} s")
