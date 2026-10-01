# -*- coding: utf-8 -*-
"""c3r2_loops.py -- the OTHER loops the integral policy and the fade create, at theta = 0 and at the curve op points:
  PD     I frozen (hard freeze |tq| > 512, opposing-hand freeze > 300, A3 bound, ramp) at the hands-off fade 254
  PD297  I frozen at the hands-on fade floor 76/256 (fadeB 77, |tq| >> 5 >= 96)
  PID80  I LIVE at fade 204/256 (fadeA 205: gp-0x6830 >= 20, |tq| <= 512 so fadeB 255)
  PI0    D = 0 (rate invalid) -- only meaningful for the DEFAULT fallback C3B-F (the primary skips the lane)
usage: python c3r2_loops.py [P|F] -> loops_<P|F>.npz"""
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
      ("FB1.155", 1.155, 1 / 1.155))
ES = (-1, 0, 10)
AS = (0.0, 1.0, 1.5, 2.0, 2.5)
LOOPS = (("PD", 0.0, 1.0, 254 / 256), ("PD297", 0.0, 1.0, 76 / 256), ("PID80", None, 1.0, 204 / 256),
         ("PI0", None, 0.0, 254 / 256))
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
                for il, (ln, ki, kds, fade) in enumerate(LOOPS):
                    L, Tr = M.loop_L(DES, pl, v, e=e + ea, kappa=kap, jb=jb, chans=ch, fade=fade, ki=ki, kd_scale=kds)
                    PM, FC, gmu, gmd = M.pm_gm(L)
                    rho = fr = z = np.nan
                    if PM < 35.0 or gmu < 6.0:
                        rho, fr, z = M.Periodic(DES, pl, v, e=e + ea, kappa=kap, jb=jb, fade=fade, ki=ki,
                                                kd_scale=kds).rho_ring()
                    res.append((MEMS.index(mem), v, ia, ifr, ie, il, th, PM, FC, gmu, gmd, rho, fr, z))
    return res


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(m, v) for m in MEMS for v in GRID]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    A = np.array(R, float)
    np.savez_compressed(M.OUT / f"loops_{WHICH}.npz", A=A, MEMS=np.array(MEMS), AS=np.array(AS),
                        FR=np.array([f[0] for f in FR]), ES=np.array(ES), LOOPS=np.array([x[0] for x in LOOPS]))
    print(f"{DES.name}: {len(A)} points in {time.time() - t0:.0f} s")
