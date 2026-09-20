# -*- coding: utf-8 -*-
"""d9 -- THE SHIPPED DESIGN, after d8 corrected d7's Parseval factor (2.407x) and replaced the
three-transfer chained cost with the one-step command -> wheel-rate transfer.

d8's corrected numbers killed the 6-tone CORE: it added x1.41 to the 1.8-3.5 Hz wheel rate, the
band whose x3.1 vs V282 is the operator's first complaint.  |T_U,SR| rises 102 -> 542 -> 1146 deg/s
per unit torque from 0.68 to 4.3 Hz, so every tone above ~1.8 Hz costs 5-11x what one below it does.

GROUP A (ships first, `AccordIdProbe`):  0.684 / 0.977 / 1.270 / 1.562 Hz + a 13.965 Hz control.
    EXACTLY ZERO power in 1.8-3.5 Hz -> the shake band is untouched, by construction, not by luck.
GROUP B (`AccordIdProbeHi`, off by default): 1.855 / 2.148 / 2.539 / 3.125 / 3.711 / 4.297 Hz,
    priced here so the operator decides with the number in front of him.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS, G = 100.0, 1024, 256.0
DF = FS / NPS
LSB = 1.0 / 4089.0
KPAR = 0.002295                     # numeric Parseval factor from d8
RNG = np.random.default_rng(5)
RHO = 7.0 / 3.0


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


def schroeder(a):
    Pw = np.asarray(a, float) ** 2
    Pw /= Pw.sum()
    return np.array([-2 * np.pi * sum((l - i) * Pw[i] for i in range(l)) for l in range(len(Pw))])


def build(a, ph, ks, n=NPS):
    t = np.arange(n) / FS
    return sum(A * np.cos(2 * np.pi * kk * DF * t + p) for A, p, kk in zip(a, ph, ks))


def cf_opt(a, ks, iters=4000, restarts=80):
    best = (np.inf, None, None)
    ks = np.asarray(ks)
    for r in range(restarts):
        ph = schroeder(a) if r == 0 else RNG.uniform(-np.pi, np.pi, len(a))
        x = build(a, ph, ks)
        for _ in range(iters):
            c = float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))
            if c < best[0]:
                best = (c, x.copy(), ph.copy())
            lim = (0.88 + 0.09 * RNG.random()) * np.max(np.abs(x))
            ph = np.angle(np.fft.rfft(np.clip(x, -lim, lim))[ks])
            x = build(a, ph, ks)
    cf, x, ph = best
    j = int(np.argmin(np.abs(x) + 0.05 * np.abs(np.gradient(x))))
    ph = (ph + 2 * np.pi * ks * DF * j / FS + np.pi) % (2 * np.pi) - np.pi
    return build(a, ph, ks), cf, ph


if __name__ == "__main__":
    meta = json.load(open(F1 / "f1_meta.json"))
    cols, sec = None, 0.0
    for r in [q for q, g in LP.GROUPS.items() if g == "T64"]:
        D = np.load(F1 / f"f1_{r}.npz")
        sel = D["vmed"] >= 15.0
        if cols is None:
            cols = {q: [] for q in ("Z", "M", "U", "UFB", "Y", "SR")}
            f = D["f"]
        for q in cols:
            cols[q].append(D[q][sel])
        sec += meta[r]["sec"]
        del D
    Z, M, U, UFB, Y, SR = (np.concatenate(cols[q]) for q in ("Z", "M", "U", "UFB", "Y", "SR"))
    E = Z - M
    n, wps = Z.shape[0], Z.shape[0] / sec
    Szz, Suu, Smm, Ssr, Syy = (xs(q, q).real for q in (Z, U, M, SR, Y))
    P = xs(Z, M) / xs(Z, U)
    S = 1.0 / (1.0 + P * (xs(Z, UFB) / xs(Z, E)))
    Tusr, Tuy, Tum = np.abs(xs(U, SR) / Suu), np.abs(xs(U, Y) / Suu), np.abs(xs(U, M) / Suu)
    g_usr, g_uy = coh(U, SR), coh(U, Y)

    def amp(kk, group):
        a_m = np.sqrt(RHO * Suu[kk]) / np.abs(S[kk]) / G            # for 1+L
        a_p = np.sqrt(RHO * Smm[kk]) / np.abs(P[kk] * S[kk]) / G    # for P
        return max(a_m, a_p) if group == "A" else a_m

    GA = [7, 10, 13, 16]
    GCAL = [143]
    GB = [19, 22, 26, 32, 38, 44]
    A_A = np.array([amp(kk, "A") for kk in GA] + [max(amp(143, "cal"), 8 * LSB)])
    A_B = np.array([amp(kk, "A") if kk in (19, 22) else amp(kk, "B") for kk in GB])
    A_B = np.maximum(A_B, 4 * LSB)      # quantiser floor: no tone below 4 counts of 0xE4

    xA, cfA, phA = cf_opt(A_A, GA + GCAL)
    xB, cfB, phB = cf_opt(A_B, GB)

    for tag, ks, Aa, x, cf, ph in [("GROUP A  (AccordIdProbe = 1.0)", GA + GCAL, A_A, xA, cfA, phA),
                                   ("GROUP B  (AccordIdProbeHi)", GB, A_B, xB, cfB, phB)]:
        pk = float(np.max(np.abs(x)))
        print(f"\n=== {tag}")
        print(f"    crest factor {cf:.3f}   rms {np.sqrt(np.mean(x**2)):.5f}   PEAK {pk:.5f} unit torque "
              f"= {pk/LSB:.1f} counts of 0xE4   x[0] = {x[0]:+.6f}")
        print(f"    peak slew {np.max(np.abs(np.diff(np.tile(x,3)))):.5f}/frame = "
              f"{np.max(np.abs(np.diff(np.tile(x,3))))/0.03*100:.1f} % of the Honda 0.03 limiter")
        print(f"    {'bin':>4s} {'f Hz':>7s} {'A':>9s} {'cts':>6s} {'phase rad':>11s} | "
              f"{'d rate d/s':>11s} {'coh':>5s} | {'d path':>8s} {'coh':>5s} | {'d ang deg':>9s}")
        for kk, a, p_ in zip(ks, Aa, ph):
            print(f"    {kk:4d} {f[kk]:7.3f} {a:9.6f} {a/LSB:6.1f} {p_:+11.6f} | "
                  f"{a*Tusr[kk]:11.4f} {g_usr[kk]:5.2f} | {a*Tuy[kk]:8.4f} {g_uy[kk]:5.2f} | "
                  f"{a*Tusr[kk]/(2*np.pi*f[kk]):9.4f}")
        print(f"    {'':4s} {'BANDS':>7s}")
        for lo, hi, nm in [(0.60, 1.80, "0.6-1.8"), (1.80, 3.50, "SHAKE 1.8-3.5"),
                           (3.50, 6.00, "3.5-6.0"), (13.0, 15.0, "CAL")]:
            now_sr = KPAR * np.sqrt(Ssr[(f >= lo) & (f <= hi)].sum())
            now_y = KPAR * np.sqrt(Syy[(f >= lo) & (f <= hi)].sum())
            add_sr = np.sqrt(sum((a * Tusr[kk]) ** 2 / 2 for kk, a in zip(ks, Aa) if lo <= f[kk] <= hi))
            add_y = np.sqrt(sum((a * Tuy[kk]) ** 2 / 2 for kk, a in zip(ks, Aa) if lo <= f[kk] <= hi))
            print(f"    {'':4s} {nm:>14s}  wheel rate today {now_sr:6.3f} + {add_sr:6.3f} "
                  f"= x{np.sqrt(now_sr**2+add_sr**2)/max(now_sr,1e-9):5.3f}  |  path today {now_y:6.4f} "
                  f"+ {add_y:6.4f} = x{np.sqrt(now_y**2+add_y**2)/max(now_y,1e-9):5.3f}")
        np.savez(OUT / f"d9_{'A' if 'A ' in tag else 'B'}.npz", ks=np.array(ks), amps=Aa,
                 phases=ph, x=x, cf=cf, f=f[ks])

    print("\n\n=== EXPECTED COHERENCE AND CI, GROUP A")
    print(f"  measured yield {wps:.4f} qualifying windows per second (T64, >=15 m/s, hands-off, runs >=30 s)")
    print(f"  {'f Hz':>7s} {'coh(Z,E) today':>15s} {'coh(W,u_p) pred':>16s} {'coh(W,M) pred':>14s} "
          f"{'SE|1+L| n=10':>13s} {'SE arg':>8s}")
    g_ze = coh(Z, E)
    for kk, a in zip(GA + GCAL, A_A):
        Sww = (a * G) ** 2
        c_up = np.abs(S[kk]) ** 2 * Sww / (np.abs(S[kk]) ** 2 * Sww + Suu[kk])
        c_m = np.abs(P[kk] * S[kk]) ** 2 * Sww / (np.abs(P[kk] * S[kk]) ** 2 * Sww + Smm[kk])
        se = np.sqrt((1 - c_up) / (2 * (10 / 1.125) * c_up))
        print(f"  {f[kk]:7.3f} {g_ze[kk]:15.3f} {c_up:16.3f} {c_m:14.3f} "
              f"{se*100:12.1f}% {np.degrees(se):7.1f}d")
    print(f"\n  {'n_win':>6s} {'seconds':>8s} {'runs of 30 s':>13s} {'runs of 60 s':>13s}")
    for nw in (6, 10, 14, 20):
        print(f"  {nw:6d} {nw/wps:8.0f} {nw/4.9:13.1f} {nw/10.7:13.1f}")
    print("  (a 30 s run yields 2*30/10.24 - 1 = 4.9 windows; a 60 s run 10.7)")

    print("\n\n=== PATCH COEFFICIENTS")
    for tag, ks, Aa, ph in [("A", GA + GCAL, A_A, phA), ("B", GB, A_B, phB)]:
        print(f"  GROUP {tag}:")
        for kk, a, p_ in zip(ks, Aa, ph):
            print(f"    ({kk:3d}, {a:.6f}, {p_:+.6f}),   # {f[kk]:6.3f} Hz, {a/LSB:5.1f} counts")
