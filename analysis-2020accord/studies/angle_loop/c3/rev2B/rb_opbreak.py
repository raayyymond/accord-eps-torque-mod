# -*- coding: utf-8 -*-
r"""rb_opbreak.py -- per-member operating-point GATE 2 (F1) at a chosen Ki, on the independent refuter model, to see
whether the a 2.0-2.5 curve-hold PM shortfall is CONFINED to the J~=2 ms_free family (BELIEF-disfavored by the held-out
ident) or also hits core members (nominal, b_hi, J_hi, J1.0).  Prints worst PM and exact rho per member.
usage: python rb_opbreak.py [ki]"""
import math
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
RS = HERE.parents[1] / "refute_stability" / "c3r1"
sys.path.insert(0, str(RS)); sys.path.insert(0, str(HERE))
import c3r1_model as M  # noqa: E402
import c3r1_sweep as S  # noqa: E402
import rb_table as T  # noqa: E402

KI = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0
F = S.F
DES = {"C3B-P": M.Design("C3B-P", "fresh", kd=48, ki=KI, rows=tuple(T.GB_P)),
       "C3B-F": M.Design("C3B-F", "held", kd=24, ki=KI, rows=tuple(T.GB_F))}
MEMS = S.SINGLE + S.COMBINED
GF = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
SP = sorted(set([round(x, 2) for x in np.arange(8.0, 28.01, 0.5)] + [11.9, 17.0, 26.9]))
SR, LWB = 16.0, 2.83


def bar(mem, e):
    return (45.0 if e <= 0 else 30.0) if mem in S.SINGLE else 30.0


def work(args):
    mem, v = args
    res = []
    for a in (1.0, 1.5, 2.0, 2.5):
        s2 = 1 - math.tanh(SR * LWB * a / (v * v) * 180 / math.pi / (19.3 + 546 * math.exp(-v / 3.01))) ** 2
        pl = M.member(mem, v)
        pl.k *= s2
        for fn, kap, jb in GF:
            Pt, Pw = M.plant_channels(pl, F, jb, 0.0)
            for dn in ("C3B-P", "C3B-F"):
                for e in (-1, 0, 10):
                    L = -M.Kout(F) * sum(x * y for x, y in zip(M.controller(DES[dn], v, F, e, kap)[:2], (Pt, Pw)))
                    PM = M.pm_gm(L, F)[0]
                    rho = M.Periodic(DES[dn], pl, v, e=e, kappa=kap, jb=jb).rho_ring()[0] if PM < 20 else 0.0
                    res.append((dn, mem, v, a, PM, rho, bar(mem, e)))
    return res


if __name__ == "__main__":
    with Pool(15) as pool:
        R = [r for rr in pool.imap_unordered(work, [(m, v) for m in MEMS for v in SP], chunksize=2) for r in rr]
    out = [f"operating-point GATE 2 per member, Ki {KI:.0f}, v>=8 (worst over a, frame, e)"]
    for dn in ("C3B-P", "C3B-F"):
        out.append(f"-- {dn} --")
        for mem in MEMS:
            X = [r for r in R if r[0] == dn and r[1] == mem]
            w = min(X, key=lambda r: r[4] - r[6])
            maxrho = max(r[5] for r in X)
            fails = sum(r[4] < r[6] for r in X)
            flag = "  <<< ms_free" if "ms_free" in mem else ""
            unst = "  UNSTABLE" if maxrho >= 1.0 else ""
            out.append(f"   {mem:16s} worst PM {w[4]:5.1f} (bar {w[6]:.0f}) at a{w[3]} {w[2]}m/s; maxrho {maxrho:.4f}; "
                       f"fails {fails}{flag}{unst}")
    txt = "\n".join(out)
    (M.KIT / "_scratch" / "angle_loop" / "c3-rev2B" / f"opbreak_ki{int(KI)}.txt").write_text(txt)
    print(txt)
