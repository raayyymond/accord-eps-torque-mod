# -*- coding: utf-8 -*-
"""c3r1_outer.py -- the fork outer loop stand-in: a fork angle integral theta_sp += (theta_ref - theta_meas) dt / tau_o
at 100 Hz with a 60 ms round trip, closed around the firmware angle loop T_ref (which carries the 0xE4 100 Hz hold).
L_o = T_ref * e^{-s 0.060} * (T_f / tau_o) / (1 - z_f^-1).  tau_o in {0.3, 0.5, 1.0, 2.0} s; every gated member, every
frame variant of the box, hold offsets e 0 and 10, every speed 1..35 (0.5).  Also the outer ring's frequency, to check
it against the R3* band (0.5-5.5 Hz).
python c3r1_outer.py -> _scratch/.../outer_out.txt"""
import math
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402

F = np.unique(np.concatenate([np.logspace(-3, math.log10(49.0), 900)]))
TAUS = (0.3, 0.5, 1.0, 2.0)
D = M.designs()
SP = [round(x, 2) for x in np.arange(1.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9]
MEMS = S.SINGLE + S.COMBINED


def work(args):
    mem, v = args
    pl = M.member(mem, v)
    res = []
    zf = np.exp(-2j * np.pi * F * 0.01)
    for jb in (1.0, 1 / 1.155):
        Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
        for kap in ((1.0, 0.83, 1.155) if jb == 1.0 else (0.83, 1.155)):
            for e in (0, 10):
                for dn in ("C3-P", "C3-F"):
                    Cth, Cw, Cref = M.controller(D[dn], v, F, e, kap)
                    K = M.Kout(F)
                    L = -K * (Cth * Pt + Cw * Pw)
                    Tr = K * Cref * Pt / (1 + L)
                    for tau in TAUS:
                        Lo = Tr * np.exp(-2j * np.pi * F * 0.060) * (0.01 / tau) / (1 - zf)
                        PM, FC, GM = M.pm_gm(Lo, F)
                        res.append((dn, tau, mem, v, jb, kap, e, PM, FC, GM))
    return res


if __name__ == "__main__":
    jobs = [(m, v) for m in MEMS for v in SP]
    with Pool(14) as pool:
        allr = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    out = []
    for dn in ("C3-P", "C3-F"):
        for tau in TAUS:
            R = [r for r in allr if r[0] == dn and r[1] == tau]
            pm = min(R, key=lambda r: r[7])
            gm = min(R, key=lambda r: r[9])
            nunst = sum(1 for r in R if r[7] < 0 or r[9] < 0)
            n45 = sum(1 for r in R if r[7] < 45)
            n30 = sum(1 for r in R if r[7] < 30)
            n6 = sum(1 for r in R if r[9] < 6)
            out.append(f"{dn} tau_o {tau:.1f}s: {len(R)} pts; min PM {pm[7]:.1f} ({pm[2]}@{pm[3]} jb{pm[4]:.3f} k{pm[5]:.3f} "
                       f"e{pm[6]}, fc {pm[8]:.2f} Hz); min GM {gm[9]:.1f} dB ({gm[2]}@{gm[3]} jb{gm[4]:.3f} k{gm[5]:.3f} "
                       f"e{gm[6]}); PM<45: {n45}, PM<30: {n30}, GM<6: {n6}, unstable(PM<0 or GM<0): {nunst}")
    (Path(M.OUT) / "outer_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
