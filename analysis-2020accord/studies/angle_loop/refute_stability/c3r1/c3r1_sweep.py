# -*- coding: utf-8 -*-
"""c3r1_sweep.py -- the GATE-2 sweep on MY model: C3-P and C3-F over the credible set (+ report members), every hold
offset e = -1..10 (ages e+1..e+10: 'hold ages 1-20 each'), the frame box and the physical frame points, the fine speed
grid, and five loop states (PID, PD = I frozen, PID at the grab-rate fade 0.80, PD at the hands-on floor 0.297, PI with
D = 0 = the rate-invalid guard state).  Also |L(20 Hz)| vs V295 in the same frame.

python c3r1_sweep.py [rf_ms] [tag]   -> _scratch/angle_loop/refute-c3r1-stability/sweep_<tag>.npz
"""
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402

S_C, S_O = 1.155, 0.962
SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6", "b_lo*ms_free", "b_q*ms_free")
REPORT = ("b_lo*ms_free*tau6", "b_q*ms_free*tau6", "b_lo*J_hi*tau6", "J_hi2", "b_q*J_hi2", "b_lo*J_hi2",
          "b/1.9*J_hi", "b/1.9*J1.0", "b_lo_step", "b_lo_step*tau6", "bq10*J1.0", "J1.3", "b_q*J1.3", "light_b")
MEMBERS = SINGLE + COMBINED + REPORT
ES = tuple(range(-1, 11))
FRAMES = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / S_C),
          ("FB1.155", 1.155, 1 / S_C), ("FAc", 1 / S_C, 1.0), ("FBc", 1 / S_C, 1 / S_C), ("FAo", 1 / S_O, 1.0),
          ("FBo", 1 / S_O, 1 / S_O))
GATED_FRAMES = (0, 1, 2, 3, 4)
LOOPS = (("PID", False, 1.0, 1.0), ("PD", True, 1.0, 1.0), ("PID.80", False, 204 / 254, 1.0),
         ("PD.297", True, 76 / 254, 1.0), ("PI.D0", False, 1.0, 0.0))
GRID = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.25)] + [3.1, 8.0, 11.9, 17.0, 26.9]
                  + [round(x, 2) for x in np.arange(7.0, 13.51, 0.05)] + [round(x, 2) for x in np.arange(15.0, 16.51, 0.05)]))
DES = ("C3-P", "C3-F")
MET = ("PM", "fc", "GMu", "pk", "l20r")
F = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 1100), [5, 7, 10, 13, 15, 16, 17, 20, 25, 30]]))
I20 = int(np.argmin(abs(F - 20.0)))
B530 = (F >= 5) & (F <= 30)
_D = M.designs()


def plant_of(mem, v):
    return M.light_b(v) if mem == "light_b" else M.member(mem, v)


def work(args):
    mem, iv, rf = args
    v = GRID[iv]
    pl = plant_of(mem, v)
    out = np.full((len(DES), len(LOOPS), len(ES), len(FRAMES), len(MET)), np.nan, np.float32)
    chans = {}
    for jb in sorted(set(fr[2] for fr in FRAMES)):
        chans[jb] = M.plant_channels(pl, F, jb, rf)
    for ie, e in enumerate(ES):
        # V295 reference |L(20)| per frame (motor-frame controller: kappa scales it)
        CthV, CwV, _ = M.controller(_D["V295"], v, F, e, 1.0)
        for idd, dn in enumerate(DES):
            des = _D[dn]
            for il, (ln, noI, fade, kds) in enumerate(LOOPS):
                for ik_, (fn, kap, jb) in enumerate(FRAMES):
                    Pt, Pw = chans[jb]
                    Cth, Cw, Cref = M.controller(des, v, F, e, kap, noI=noI, kd_scale=kds)
                    K = M.Kout(F, fade)
                    L = -K * (Cth * Pt + Cw * Pw)
                    PM, FC, GMu = M.pm_gm(L, F)
                    Sx = 1 / (1 + L)
                    pk = max(np.abs(L * Sx)[B530].max(), np.abs(K * Cref * Pt * Sx)[B530].max())
                    LV = -M.Kout(F) * kap * (CwV * Pw)
                    l20r = abs(L[I20]) / abs(LV[I20])
                    out[idd, il, ie, ik_] = (PM, FC, GMu, 20 * math.log10(pk), l20r)
    return mem, iv, out


def main(rf=0.0, tag="base"):
    jobs = [(m, iv, rf) for m in MEMBERS for iv in range(len(GRID))]
    arr = np.full((len(MEMBERS), len(GRID), len(DES), len(LOOPS), len(ES), len(FRAMES), len(MET)), np.nan, np.float32)
    t0 = time.time()
    with Pool(15) as pool:
        for k, (mem, iv, out) in enumerate(pool.imap_unordered(work, jobs, chunksize=8)):
            arr[MEMBERS.index(mem), iv] = out
            if k % 2000 == 0:
                print(f"{k}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
                np.save(M.OUT / f"sweep_{tag}_partial.npy", arr)
    np.savez_compressed(M.OUT / f"sweep_{tag}.npz", arr=arr, members=np.array(MEMBERS), grid=np.array(GRID),
                        des=np.array(DES), loops=np.array([l[0] for l in LOOPS]), es=np.array(ES),
                        frames=np.array([f[0] for f in FRAMES]), met=np.array(MET), rf=rf)
    print(f"done {time.time() - t0:.0f}s")


if __name__ == "__main__":
    rf = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
    tag = sys.argv[2] if len(sys.argv) > 2 else "base"
    main(rf, tag)
