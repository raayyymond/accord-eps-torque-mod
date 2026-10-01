# -*- coding: utf-8 -*-
"""c3r1_twomass.py -- the 20 Hz / two-mass stress: a collocated flexible mode (f2 13..22 Hz, zeta2 0.02/0.05, wheel share
r2 0.2/0.4, both placements: 'mu' = free-free resonance at f2, 'jw' = wheel-side ring at f2) on nominal / b_lo / b_q /
J_hi, hold offsets e 0 and 10, kappa 0.83 / 1 / 1.155, speeds 3..33.  For C3-P, C3-F AND V295 on the same plant:
exact periodic rho (0.25 ms sub-steps), the closed-loop modal zeta near f2 (from the monodromy), LTI peak |Tc|, |Tref|
5-30 Hz.  A fail = rho >= 1, a 5-30 Hz peak > +3 dB, or a closed-loop modal zeta below V295's on the same plant.
python c3r1_twomass.py -> _scratch/.../twomass_out.txt, twomass.json"""
import itertools
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

D = M.designs()
F = np.unique(np.concatenate([np.logspace(-2, math.log10(499.0), 1500), np.arange(5, 30.01, 0.05)]))
B530 = (F >= 5) & (F <= 30)
F2S = (13.0, 15.0, 16.5, 17.0, 20.0, 22.0)
Z2S = (0.02, 0.05)
R2S = (0.2, 0.4)
CONV = ("mu", "jw")
BASES = ("nominal", "b_lo", "b_q", "J_hi")
SP = (3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 17.0, 20.0, 26.9, 33.0)


def modal(lam, f2):
    lam = lam[np.abs(lam) > 1e-6]
    s = np.log(lam.astype(complex)) / (10 * M.TS)
    fz = np.abs(s.imag) / (2 * np.pi)
    z = -s.real / np.maximum(np.abs(s), 1e-12)
    # aliasing: a pole at f2 > 50 Hz folds; f2 <= 22 Hz is below the 50 Hz fold of the 100 Hz monodromy
    j = np.where((fz > 0.6 * f2) & (fz < 1.6 * f2))[0]
    if not len(j):
        return math.nan, math.nan
    k = j[np.argmin(z[j])]
    return float(fz[k]), float(z[k])


def work(args):
    base, v = args
    res = []
    for f2, z2, r2, cv in itertools.product(F2S, Z2S, R2S, CONV):
        pl = M.member(base, v)
        pl.f2, pl.z2, pl.r2, pl.conv = f2, z2, r2, cv
        Pt, Pw = M.plant_channels(pl, F, 1.0, 0.0)
        for e in (0, 10):
            # V295 on the same plant (kappa 1)
            perV = M.Periodic(D["V295"], pl, v, e=e)
            rV, _, _, lamV = perV.rho_ring()
            fV, zV = modal(lamV, f2)
            for kap in (0.83, 1.0, 1.155):
                for dn in ("C3-P", "C3-F"):
                    Cth, Cw, Cref = M.controller(D[dn], v, F, e, kap)
                    K = M.Kout(F)
                    L = -K * (Cth * Pt + Cw * Pw)
                    Sx = 1 / (1 + L)
                    pk = 20 * math.log10(max(np.abs(L * Sx)[B530].max(), np.abs(K * Cref * Pt * Sx)[B530].max()))
                    per = M.Periodic(D[dn], pl, v, e=e, kappa=kap)
                    rho, _, _, lam = per.rho_ring()
                    fm, zm = modal(lam, f2)
                    res.append(dict(dn=dn, base=base, v=v, f2=f2, z2=z2, r2=r2, conv=cv, e=e, kap=kap, rho=rho,
                                    pk=pk, fm=fm, zm=zm, rV=rV, fV=fV, zV=zV))
    return res


if __name__ == "__main__":
    jobs = [(b, v) for b in BASES for v in SP]
    with Pool(14) as pool:
        R = [r for rr in pool.imap_unordered(work, jobs) for r in rr]
    json.dump(R, open(M.OUT / "twomass.json", "w"))
    out = []
    for dn in ("C3-P", "C3-F"):
        X = [r for r in R if r["dn"] == dn]
        nun = sum(r["rho"] >= 1 for r in X)
        npk = sum(r["pk"] > 3 for r in X)
        nV = sum((r["zm"] < r["zV"] - 1e-6) for r in X if not math.isnan(r["zm"]) and not math.isnan(r["zV"]))
        worstpk = max(X, key=lambda r: r["pk"])
        worstz = min((r for r in X if not math.isnan(r["zm"])), key=lambda r: r["zm"] / r["z2"])
        worstrel = min((r for r in X if not math.isnan(r["zm"]) and not math.isnan(r["zV"])), key=lambda r: r["zm"] - r["zV"])
        out.append(f"{dn}: {len(X)} points; rho>=1: {nun}; peak 5-30 Hz > +3 dB: {npk}; closed-loop modal zeta < V295's on the"
                   f" same plant: {nV}")
        out.append(f"   max rho {max(r['rho'] for r in X):.4f}; worst peak {worstpk['pk']:+.1f} dB at {worstpk['base']}@{worstpk['v']}"
                   f" f2 {worstpk['f2']} z2 {worstpk['z2']} r2 {worstpk['r2']} {worstpk['conv']} e{worstpk['e']} k{worstpk['kap']}")
        out.append(f"   lowest zeta_cl/zeta2 {worstz['zm'] / worstz['z2']:.2f} (zeta_cl {worstz['zm']:.4f} at {worstz['fm']:.1f} Hz)"
                   f" at {worstz['base']}@{worstz['v']} f2 {worstz['f2']} z2 {worstz['z2']} r2 {worstz['r2']} {worstz['conv']}"
                   f" e{worstz['e']} k{worstz['kap']}  [V295 same plant: {worstz['zV']:.4f}]")
        out.append(f"   largest deficit vs V295: zeta_cl {worstrel['zm']:.4f} vs V295 {worstrel['zV']:.4f} at {worstrel['base']}"
                   f"@{worstrel['v']} f2 {worstrel['f2']} z2 {worstrel['z2']} r2 {worstrel['r2']} {worstrel['conv']} e{worstrel['e']}"
                   f" k{worstrel['kap']}")
        for f2 in F2S:
            Y = [r for r in X if r["f2"] == f2 and not math.isnan(r["zm"])]
            if Y:
                a = np.array([r["zm"] / r["z2"] for r in Y])
                b = np.array([r["zm"] - r["zV"] for r in Y if not math.isnan(r["zV"])])
                out.append(f"     f2 {f2:4.1f}: zeta_cl/zeta2 min {a.min():.2f} median {np.median(a):.2f};"
                           f" (zeta_cl - zeta_V295) min {b.min():+.4f}, frac < 0 {np.mean(b < 0):.2f}")
    (Path(M.OUT) / "twomass_out.txt").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
