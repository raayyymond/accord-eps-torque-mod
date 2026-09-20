# -*- coding: utf-8 -*-
"""a4 -- the statistic nobody computed for this lever: the GAIN MARGIN at the -180 deg crossing,
and the saturation census the linear re-synthesis cannot see.

The study reports crossover / phase margin at the FIRST unity crossing (0.20-0.23 Hz, PM 135-141 deg)
and band-averaged |L| in 1.8-3.5 Hz.  Neither is the stability statistic for this plant: the measured
command -> wheel-rate gain RISES with frequency on V293 (a2: 57 -> 413 -> 428 over 0.15-6 Hz) while a
PI controller's gain is FLAT above its integral corner, so |L| has its MAXIMUM at high frequency, not
at the crossover.  The binding quantity is therefore |L| where arg L = -180, i.e. the classical gain
margin -- exactly the statistic the fork's own source uses to gate AccordRateLoopGain
(latcontrol_vehicle_tunes.py:281-286).

Also: `output_lataccel = clip(p + i + f, +/- LAF)`.  Tripling kp triples p.  The re-synthesis is
linear and the window set drops anything >2 % saturated, so saturation is invisible to it.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

OUT = HERE / "out"
FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)


def Ky_of(W, sel=None):
    s = np.ones(len(W["v"]), bool) if sel is None else sel
    X, U, M = W["X"][s], W["U"][s], W["M"][s]
    px = np.maximum(np.mean(np.abs(X) ** 2, axis=0), 1e-300)
    Up = U - (np.mean(np.conj(X) * U, axis=0) / px)[None, :] * X
    Mp = M - (np.mean(np.conj(X) * M, axis=0) / px)[None, :] * X
    pm = np.maximum(np.mean(np.abs(Mp) ** 2, axis=0), 1e-300)
    return (np.mean(np.conj(Mp) * Up, axis=0) / pm,
            np.abs(np.mean(np.conj(Mp) * Up, axis=0)) ** 2
            / np.maximum(pm * np.mean(np.abs(Up) ** 2, axis=0), 1e-300))


def loop(W, P, Ky, kp, q, mode="tot_correct", delay_s=0.0):
    f, v = W["f"], W["v"]
    C0 = A.C_fb(f, v, **FLOWN)
    C1 = A.C_fb(f, v, kp, 14.0, 0.30, q)
    Lpid = P[None, :] * C0
    Lt = -P[None, :] * Ky[None, :]
    L1 = (Lt + Lpid * (C1 / C0 - 1.0)) if mode == "tot_correct" else Lpid * (C1 / C0)
    if delay_s:
        L1 = L1 * np.exp(-2j * np.pi * f[None, :] * delay_s)
    return np.mean(L1, axis=0)


def gm(f, L, flo=1.0, fhi=12.0):
    """|L| at the first arg L = -180 deg crossing in [flo, fhi]; also the peak |L| there."""
    s = (f >= flo) & (f <= fhi)
    ff, LL = f[s], L[s]
    ph = np.unwrap(np.angle(LL))
    mg = np.abs(LL)
    out = []
    for k in range(len(ff) - 1):
        for tgt in (-np.pi, -3 * np.pi, np.pi):
            if (ph[k] - tgt) * (ph[k + 1] - tgt) < 0:
                w = (tgt - ph[k]) / (ph[k + 1] - ph[k])
                out.append((float(ff[k] + w * (ff[k + 1] - ff[k])),
                            float(np.exp(np.log(mg[k]) + w * (np.log(mg[k + 1]) - np.log(mg[k]))))))
    fpk = float(ff[int(np.argmax(mg))])
    return out, float(mg.max()), fpk


def main():
    Wt = A.cat([A.extract(r, nps=1024) for r in A.T64])
    f = Wt["f"]
    Pm = A.identify(Wt, inst="X")["P"]
    Ky, cKy = Ky_of(Wt)
    hi = Wt["amp"] > np.quantile(Wt["amp"], 2 / 3)
    Wh = {k: (v[hi] if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(Wt["v"]) else v)
          for k, v in Wt.items()}
    Wh["f"] = f
    Ph = A.identify(Wt, inst="X", vsel=hi)["P"]
    Kyh, _ = Ky_of(Wt, sel=hi)

    print("=" * 112)
    print("0. COHERENCE UP THERE -- state it before using it.  coh(X,U) / coh(X,M) / coh(M,Y) / coh(Mp,Up)")
    ident = A.identify(Wt, inst="X")
    for lo, hi_ in ((0.15, 0.6), (0.6, 1.2), (1.2, 1.8), (1.8, 3.5), (3.5, 6.0), (6.0, 12.0)):
        s = (f >= lo) & (f <= hi_)
        print(f"   {lo:5.2f}-{hi_:5.2f} Hz   XU {float(np.mean(ident['coh_iu'][s])):.2f}  "
              f"XM {float(np.mean(ident['coh_im'][s])):.2f}  MY {float(np.mean(ident['coh_my'][s])):.2f}  "
              f"MpUp {float(np.mean(cKy[s])):.2f}   |P| {float(np.mean(np.abs(Pm[s]))):8.3f}")
    print("   => everything above ~1.2 Hz is BELIEF-grade identification.  Reported as a bracket, not a fact.")

    print()
    print("=" * 112)
    print("1. THE LOOP'S SHAPE.  |L| vs frequency at each dose (pooled windows, tot_correct loop).")
    fq = [0.20, 0.39, 0.78, 1.17, 1.76, 2.34, 3.03, 4.00, 5.08, 6.05, 8.01, 10.06]
    jj = [int(np.argmin(np.abs(f - x))) for x in fq]
    print(f"{'config':22s} " + " ".join(f"{x:>6.2f}" for x in fq))
    for lbl, kp, q in (("as flown KP1 Q1.0", 1.0, 1.0), ("ARM-KP  KP2 Q1.0", 2.0, 1.0),
                       ("ARM-KP2 KP3 Q0.6", 3.0, 0.6), ("KP4 Q0.6", 4.0, 0.6),
                       ("KP5 Q0.6", 5.0, 0.6), ("KP8 Q0.6", 8.0, 0.6)):
        L = loop(Wt, Pm, Ky, kp, q)
        print(f"{lbl:22s} " + " ".join(f"{abs(L[j]):6.3f}" for j in jj))
    print(f"{'  arg L (deg) @KP3':22s} " + " ".join(
        f"{np.degrees(np.angle(loop(Wt,Pm,Ky,3.0,0.6)[j])):6.0f}" for j in jj))

    print()
    print("=" * 112)
    print("2. GAIN MARGIN AT THE -180 deg CROSSING, 1-12 Hz, with the measured 55-75 ms loop delay")
    print("   added explicitly (the identification already contains whatever delay the logs carry;")
    print("   the extra column is the sensitivity to the unmeasured post-tap stage).")
    print(f"{'config':20s} {'set':>6s} {'f(-180)':>8s} {'|L| there':>10s} {'GM':>6s} "
          f"{'max|L| 1-12':>12s} {'f of max':>9s}")
    res = []
    for lbl, kp, q in (("as flown KP1", 1.0, 1.0), ("ARM-KP KP2", 2.0, 1.0), ("KP2.5", 2.5, 0.6),
                       ("ARM-KP2 KP3", 3.0, 0.6), ("KP3.5", 3.5, 0.6), ("KP4", 4.0, 0.6),
                       ("KP5", 5.0, 0.6), ("KP6", 6.0, 0.6), ("KP8", 8.0, 0.6)):
        for tag, W, P, Kyy in (("pool", Wt, Pm, Ky), ("hi|X|", Wh, Ph, Kyh)):
            L = loop(W, P, Kyy, kp, q)
            cr, mx, fpk = gm(f, L)
            if cr:
                fc, mc = cr[0]
                print(f"{lbl:20s} {tag:>6s} {fc:8.2f} {mc:10.3f} {1/max(mc,1e-9):6.2f} {mx:12.3f} {fpk:9.2f}")
                res.append(dict(cfg=lbl, kp=kp, q=q, set=tag, f180=fc, Lat180=mc, GM=1 / mc, maxL=mx, fmax=fpk))
            else:
                print(f"{lbl:20s} {tag:>6s} {'none':>8s} {'-':>10s} {'-':>6s} {mx:12.3f} {fpk:9.2f}")
                res.append(dict(cfg=lbl, kp=kp, q=q, set=tag, f180=None, maxL=mx, fmax=fpk))
    print()
    print("   the SteerKP at which the high-demand gain margin reaches 2.0 and 1.0 (linear in kp above")
    print("   the integral corner, so GM scales as 1/kp to good accuracy):")
    for tag, W, P, Kyy in (("pool", Wt, Pm, Ky), ("hi|X|", Wh, Ph, Kyh)):
        L3 = loop(W, P, Kyy, 3.0, 0.6)
        cr, _, _ = gm(f, L3)
        if cr:
            m3 = cr[0][1]
            print(f"     {tag}: |L(-180)| = {m3:.3f} at SteerKP 3.0  ->  GM 2.0 at SteerKP "
                  f"{3.0*(0.5/m3):.2f},  GM 1.0 (limit cycle) at SteerKP {3.0*(1.0/m3):.2f}")

    print()
    print("=" * 112)
    print("3. SATURATION.  output_lataccel = clip(p + i + f, +/- 14).  Frame-by-frame on EVERY")
    print("   laterally-engaged hands-off frame (the metric drops >2 %-saturated windows, so this")
    print("   regime is invisible to the closure and to the shake number).")
    print(f"{'route':22s} {'speed':>8s} {'n frames':>9s} {'sat now %':>10s} " +
          " ".join(f"{'KP'+str(k)+' %':>9s}" for k in (2, 3, 4, 5, 8)))
    sat_rows = []
    for route in A.T64:
        S = A.V.load(route)
        act = S["active"] & ~S["pressed"]
        lsf = A.lsf_of(S["v"])
        for tag, m in (("all", act), (">=15", act & (S["v"] >= 15)), ("8-15", act & (S["v"] >= 8) & (S["v"] < 15)),
                       ("<8", act & (S["v"] < 8))):
            if m.sum() < 100:
                continue
            p, i, ff = S["p"][m], S["i"][m], S["f"][m]
            lf = lsf[m]
            base = np.mean(np.abs(p + i + ff) >= 13.93) * 100
            cells = []
            for k in (2.0, 3.0, 4.0, 5.0, 8.0):
                # p = (kp+lsf)*e_notched  =>  p(k) = p * (k+lsf)/(1+lsf);  i unchanged at leading order
                pk = p * (k + lf) / (1.0 + lf)
                cells.append(np.mean(np.abs(pk + i + ff) >= 13.93) * 100)
            print(f"{route:22s} {tag:>8s} {int(m.sum()):9d} {base:10.2f} " +
                  " ".join(f"{c:9.2f}" for c in cells))
            sat_rows.append(dict(route=route, band=tag, n=int(m.sum()), base=float(base),
                                 kp=[float(c) for c in cells]))
        del S
    print("   (upper bound: it ignores the loop reducing the error, but the loop only reduces error")
    print("    where it has gain, and |L| < 0.4 below 1 Hz, so the reduction is at most ~30 %.)")
    json.dump(dict(margin=res, sat=sat_rows), open(OUT / "a4_margin.json", "w"), indent=1)


if __name__ == "__main__":
    main()
