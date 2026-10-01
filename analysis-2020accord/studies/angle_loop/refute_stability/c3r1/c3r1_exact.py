# -*- coding: utf-8 -*-
"""c3r1_exact.py -- EXACT periodic stability over the gated set (no averaging of the hold): rho at gain 1 and gain 2
(the exact 6 dB GM), and the least-damped closed-loop poles in 0.2-5.5 Hz (the R3* band) and 5-30 Hz, for C3-P / C3-F,
PID and I-frozen, hold offsets e -1 / 0 / 5 / 10, the gated frame box, speeds 1..35 at 0.5 + knots.
python c3r1_exact.py -> _scratch/.../exact.json, exact_out.txt"""
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
SP = sorted(set([round(x, 2) for x in np.arange(1.0, 35.01, 0.5)] + [3.1, 8.0, 11.9, 17.0, 26.9, 8.5, 9.0, 9.5, 15.75]))
ES = (-1, 0, 5, 10)
FR = [f for f in S.FRAMES if f[0] in ("nom", "FA.83", "FA1.155", "FB.83", "FB1.155")]
MEMS = S.SINGLE + S.COMBINED + ("b_lo*J_hi*tau6", "b_lo*ms_free*tau6", "b_q*ms_free*tau6")


def poles(lam):
    lam = lam[np.abs(lam) > 1e-6]
    s = np.log(lam.astype(complex)) / (10 * M.TS)
    fz = np.abs(s.imag) / (2 * np.pi)
    z = -s.real / np.maximum(np.abs(s), 1e-12)
    res = {}
    for lab, lo, hi in (("r3", 0.2, 5.5), ("hf", 5.0, 30.0)):
        j = np.where((fz > lo) & (fz <= hi))[0]
        if len(j):
            k = j[np.argmin(z[j])]
            res[lab] = (float(fz[k]), float(z[k]))
        else:
            res[lab] = (math.nan, math.nan)
    return res


def work(args):
    mem, v = args
    pl = M.member(mem, v)
    out = []
    for dn in ("C3-P", "C3-F"):
        for noI in (False, True):
            for e in ES:
                for fn, kap, jb in FR:
                    per = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb, noI=noI)
                    rho, _, _, lam = per.rho_ring()
                    rho2 = M.Periodic(D[dn], pl, v, e=e, kappa=kap, jb=jb, noI=noI, gain=2.0).rho_ring()[0]
                    pz = poles(lam)
                    out.append((dn, noI, e, fn, mem, v, rho, rho2, pz["r3"][0], pz["r3"][1], pz["hf"][0], pz["hf"][1]))
    return out


if __name__ == "__main__":
    jobs = [(m, v) for m in MEMS for v in SP]
    with Pool(14) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs, chunksize=4) for r in rr]
    json.dump(R, open(M.OUT / "exact.json", "w"))
    out = []
    for dn in ("C3-P", "C3-F"):
        for noI in (False, True):
            X = [r for r in R if r[0] == dn and r[1] == noI]
            lab = "PD (I frozen)" if noI else "PID"
            g = [r for r in X if r[4] in S.SINGLE + S.COMBINED]
            out.append(f"{dn} {lab}: {len(X)} points ({len(g)} gated); rho>=1: {sum(r[6] >= 1 for r in g)}; "
                       f"rho(x2)>=1 (exact GM < 6 dB): {sum(r[7] >= 1 for r in g)}; max rho {max(r[6] for r in g):.4f}")
            r3 = [r for r in g if not math.isnan(r[9])]
            w = min(r3, key=lambda r: r[9])
            out.append(f"   least-damped 0.2-5.5 Hz pole (gated): {w[8]:.2f} Hz zeta {w[9]:.3f} at {w[4]}@{w[5]} e{w[2]} {w[3]};"
                       f" points with zeta < 0.10: {sum(r[9] < 0.10 for r in r3)}, < 0.15: {sum(r[9] < 0.15 for r in r3)}")
            hf = [r for r in g if not math.isnan(r[11])]
            if hf:
                w = min(hf, key=lambda r: r[11])
                out.append(f"   least-damped 5-30 Hz pole (gated): {w[10]:.2f} Hz zeta {w[11]:.3f} at {w[4]}@{w[5]} e{w[2]} {w[3]}")
            rep = [r for r in X if r[4] not in S.SINGLE + S.COMBINED]
            if rep:
                w = max(rep, key=lambda r: r[6])
                w2 = min((r for r in rep if not math.isnan(r[9])), key=lambda r: r[9])
                out.append(f"   report products: max rho {w[6]:.4f}; least-damped R3* pole {w2[8]:.2f} Hz zeta {w2[9]:.3f} at "
                           f"{w2[4]}@{w2[5]} e{w2[2]} {w2[3]}")
    (Path(M.OUT) / "exact_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
