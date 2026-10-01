# -*- coding: utf-8 -*-
"""c3r2_twomass.py -- the 20 Hz / two-mass stress: a collocated two-mass mode (motor angle sensed) at f2 13..22 Hz,
zeta2 0.02/0.05, r2 0.2/0.4, two placements ('mu' = free-free at f2, 'wheel' = wheel-side ring at f2), on nominal /
b_lo / b_q / J_hi, e 0/10, kappa 0.83/1/1.155, 10 speeds.  EXACT rho for C3-rev2-P/F and V295 on the SAME plant; the
least-damped 8..40 Hz closed-loop pole (the mode) zeta vs V295's; LTI 5-30 Hz peak.  -> twomass_<P|F>.npz"""
import itertools
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
F2S = (13.0, 15.0, 16.5, 17.0, 20.0, 22.0)
Z2S = (0.02, 0.05)
R2S = (0.2, 0.4)
PLC = ("mu", "wheel")
MEMS = ("nominal", "b_lo", "b_q", "J_hi")
ES = (0, 10)
KAPS = (0.83, 1.0, 1.155)
SPEEDS = (3.0, 5.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 20.0, 26.9)
F = M.F


def mode_pole(P):
    lam = P.poles()
    s = np.log(lam.astype(complex)) / (10 * M.TS)
    fr = np.abs(s.imag) / (2 * np.pi)
    sel = (fr > 8) & (fr < 45)
    if not sel.any():
        return np.nan, np.nan
    z = -s.real[sel] / np.abs(s[sel])
    j = int(np.argmin(z))
    return float(fr[sel][j]), float(z[j])


def work(args):
    mem, v = args
    res = []
    pl0, ea = M.member(mem, v)
    for f2, z2, r2, plc in itertools.product(F2S, Z2S, R2S, PLC):
        pl = M.Plant(pl0.J, pl0.b, pl0.k, pl0.d, (f2, z2, r2, plc))
        ch = M.plant_frf(pl, F, 1.0)
        for e in ES:
            for kap in KAPS:
                Pc = M.Periodic(DES, pl, v, e=e, kappa=kap)
                Pv = M.Periodic(M.V295D, pl, v, e=e, kappa=kap)
                rho = Pc.rho_ring()[0]
                rhov = Pv.rho_ring()[0]
                fm, zm = mode_pole(Pc)
                fv, zv = mode_pole(Pv)
                L, Tr = M.loop_L(DES, pl, v, e=e, kappa=kap, chans=ch)
                pk = M.peak530(L, Tr)
                res.append((MEMS.index(mem), v, f2, z2, r2, PLC.index(plc), e, kap, rho, rhov, fm, zm, fv, zv, pk))
    return res


if __name__ == "__main__":
    t0 = time.time()
    jobs = [(m, v) for m in MEMS for v in SPEEDS]
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=1) for r in rr]
    A = np.array(R, float)
    np.savez_compressed(M.OUT / f"twomass_{WHICH}.npz", A=A, MEMS=np.array(MEMS), PLC=np.array(PLC))
    print(f"{DES.name}: {len(A)} points in {time.time() - t0:.0f} s")
