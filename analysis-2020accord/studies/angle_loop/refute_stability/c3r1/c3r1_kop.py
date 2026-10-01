# -*- coding: utf-8 -*-
"""c3r1_kop.py -- GATE 2 at the OPERATING POINT of a steady curve.  The identified plant's spring is
k*sat(v)*tanh(theta/sat(v)) (v294_plant; sat(v) = 19.3 + 546 exp(-v/3.01), the prior's, BELIEF), so the small-signal
stiffness about a hold at theta_op is k*sech^2(theta_op/sat).  Every GATE-2 number on the design page linearises at
theta = 0 (k itself).  theta_op = SR * L * a / v^2 (deg; SR 16, L 2.83 m -- the round-2 nonlinear refuter's sizing),
a in {1.0, 1.5, 2.0, 2.5} m/s^2 (the design's own turn-hold sizes: a <= 2.0, and a 2.5 = r71b's sustained max <= 18 m/s).
Loops: PID (the I is not bound-limited in a hands-off hold: the bound slope exceeds k_eff) and PD (I frozen).
Frames: the gated box + the outward physical points (|theta| > 27.7 deg: d(gp-0x6a00)/d(lin) 1.032 .. 0.962).
python c3r1_kop.py -> _scratch/.../kop_out.txt, kop.json"""
import json
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

D = M.designs()
F = S.F
SR, LWB = 16.0, 2.83
AS = (1.0, 1.5, 2.0, 2.5)
SP = sorted(set([round(x, 2) for x in np.arange(3.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9]))
FRS = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155", "FAo", "FBo")]
MEMS = S.SINGLE + S.COMBINED


def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)


def theta_op(v, a):
    return SR * LWB * a / (v * v) * 180 / math.pi


def work(args):
    mem, v = args
    res = []
    for a in AS:
        th = theta_op(v, a)
        sech2 = 1 - math.tanh(th / sat(v)) ** 2
        pl = M.member(mem, v)
        pl.k = pl.k * sech2
        for fn, kap, jb in FRS:
            Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
            for dn in ("C3-P", "C3-F"):
                for e in (0, 10):
                    for noI in (False, True):
                        Cth, Cw, Cref = M.controller(D[dn], v, F, e, kap, noI=noI)
                        L = -M.Kout(F) * (Cth * Pt + Cw * Pw)
                        PM, FC, GM = M.pm_gm(L, F)
                        res.append((dn, noI, mem, v, a, th, sech2, fn, e, PM, FC, GM))
    return res


if __name__ == "__main__":
    jobs = [(m, v) for m in MEMS for v in SP]
    with Pool(14) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    json.dump(R, open(M.OUT / "kop.json", "w"))
    out = ["theta_op / sech^2 by speed (a 1.0 / 1.5 / 2.0 / 2.5): " +
           "; ".join(f"{v}: " + "/".join(f"{theta_op(v, a):.0f}deg x{1 - math.tanh(theta_op(v, a) / sat(v)) ** 2:.2f}"
                                         for a in AS) for v in (5, 8, 10, 12.5, 15, 17, 20, 26.9))]
    for dn in ("C3-P", "C3-F"):
        for noI in (False, True):
            for a in AS:
                X = [r for r in R if r[0] == dn and r[1] == noI and r[4] == a]
                for lab, sel, bar in (("singles e0", lambda r: r[2] in S.SINGLE and r[8] == 0, 45),
                                      ("aged singles + combined", lambda r: not (r[2] in S.SINGLE and r[8] == 0), 30)):
                    Y = [r for r in X if sel(r)]
                    w = min(Y, key=lambda r: r[9])
                    nf = sum(r[9] < bar for r in Y)
                    vs = sorted(set(r[3] for r in Y if r[9] < bar))
                    out.append(f"{dn} {'PD ' if noI else 'PID'} a {a}: {lab:24s} min PM {w[9]:5.1f} at {w[2]}@{w[3]} e{w[8]} {w[7]}"
                               f" (theta_op {w[5]:.0f} deg, k x{w[6]:.2f}, fc {w[10]:.2f}); < {bar}: {nf} pts"
                               + (f" at {vs[0]}..{vs[-1]} m/s" if vs else ""))
                gm = min(X, key=lambda r: r[11])
                out.append(f"      min GM {gm[11]:.1f} dB at {gm[2]}@{gm[3]} {gm[7]} e{gm[8]}")
    (Path(M.OUT) / "kop_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
