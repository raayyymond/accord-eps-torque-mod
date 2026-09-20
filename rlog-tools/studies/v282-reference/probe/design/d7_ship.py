# -*- coding: utf-8 -*-
"""d7 -- the SHIPPED waveform: one 10.24 s period carrying three tone groups, plus every audit.

  CORE   0.68-2.15 Hz, 6 tones   -- makes the 0.6-2.0 Hz identification (Tier B) SCOREABLE
  MARGIN 2.5-5.5 Hz, 6 tones     -- measures |1+L| where the vector margin actually binds (3.4-4.9)
  CAL    13.965 Hz, 1 tone       -- POSITIVE CONTROL: |1+L| here MUST read 1.00.  The fork already
                                    picked 14 Hz as the gap between the 5-9 Hz wheel band and the
                                    17.9 Hz ring, and runs AccordDither there at 0.008-0.012, so
                                    the loop provably has no gain at it.  If this tone does not
                                    return 1.00 +/- its own SE, the INSTRUMENT is broken and
                                    nothing else in the run is read.

Everything is priced off the measured transfers, and every quoted transfer carries its coherence.
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
RNG = np.random.default_rng(3)
RHO = 7.0 / 3.0


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


def coh(A, B):
    return np.abs(xs(A, B)) ** 2 / np.maximum(xs(A, A).real * xs(B, B).real, 1e-300)


def pool(fam, vlo=15.0):
    routes = [r for r, g in LP.GROUPS.items() if g == fam]
    cols, vm, sec = None, [], 0.0
    meta = json.load(open(F1 / "f1_meta.json"))
    for r in routes:
        p = F1 / f"f1_{r}.npz"
        if not p.exists():
            continue
        D = np.load(p)
        sel = D["vmed"] >= vlo
        if cols is None:
            cols = {k: [] for k in ("X", "Y", "Z", "M", "UFB", "UFF", "U", "SR")}
            f = D["f"]
        for k in cols:
            cols[k].append(D[k][sel])
        vm.append(D["vmed"][sel]); sec += meta[r]["sec"]
        del D
    return dict(f=f, sec=sec, vmed=np.concatenate(vm), **{k: np.concatenate(v) for k, v in cols.items()})


def schroeder(a):
    Pw = np.asarray(a, float) ** 2
    Pw = Pw / Pw.sum()
    return np.array([-2 * np.pi * sum((l - i) * Pw[i] for i in range(l)) for l in range(len(Pw))])


def build(a, ph, ks, n=NPS):
    t = np.arange(n) / FS
    return sum(A * np.cos(2 * np.pi * k * DF * t + p) for A, p, k in zip(a, ph, ks))


def cf_opt(a, ks, iters=3000, restarts=60):
    best = (np.inf, None, None)
    for r in range(restarts):
        ph = schroeder(a) if r == 0 else RNG.uniform(-np.pi, np.pi, len(a))
        x = build(a, ph, ks)
        for _ in range(iters):
            c = float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))
            if c < best[0]:
                best = (c, x.copy(), ph.copy())
            lim = (0.90 + 0.06 * RNG.random()) * np.max(np.abs(x))
            ph = np.angle(np.fft.rfft(np.clip(x, -lim, lim))[ks])
            x = build(a, ph, ks)
    cf, x, ph = best
    j = int(np.argmin(np.abs(x) + 0.05 * np.abs(np.gradient(x))))
    ph = (ph + 2 * np.pi * np.asarray(ks) * DF * j / FS + np.pi) % (2 * np.pi) - np.pi
    return build(a, ph, ks), cf, ph


if __name__ == "__main__":
    W = pool("T64")
    f = W["f"]
    Z, M, U, UFB, Y, SR = W["Z"], W["M"], W["U"], W["UFB"], W["Y"], W["SR"]
    E = Z - M
    Szz, Smm, Suu = xs(Z, Z).real, xs(M, M).real, xs(U, U).real
    Tzm, Tzu = xs(Z, M) / Szz, xs(Z, U) / Szz
    Tzsr, Tzy = np.abs(xs(Z, SR) / Szz), np.abs(xs(Z, Y) / Szz)
    g_zsr, g_zy, g_zm = coh(Z, SR), coh(Z, Y), coh(Z, M)
    P = xs(Z, M) / xs(Z, U)
    L = P * (xs(Z, UFB) / xs(Z, E))
    S = 1.0 / (1.0 + L)
    n, wps = Z.shape[0], Z.shape[0] / W["sec"]
    Ssr = xs(SR, SR).real                     # the wheel-rate spectrum we are adding to

    CORE = [7, 10, 13, 16, 19, 22]
    MARG = [26, 32, 38, 44, 50, 56]
    CAL = [143]
    KS = CORE + MARG + CAL

    A = []
    for k in KS:
        a_marg = np.sqrt(RHO * Suu[k]) / np.abs(S[k]) / G
        a_plant = np.sqrt(RHO * Smm[k]) / np.abs(P[k] * S[k]) / G
        A.append(max(a_marg, a_plant) if k in CORE else a_marg)
    A = np.array(A)
    x, cf, ph = cf_opt(A, np.array(KS))
    pk, rms = float(np.max(np.abs(x))), float(np.sqrt(np.mean(x ** 2)))

    print("SHIPPED WAVEFORM -- one 1024-sample (10.24 s) period, 100 Hz, unit torque")
    print(f"  tones {len(KS)}   crest factor {cf:.3f}   rms {rms:.5f}   PEAK {pk:.5f}")
    print(f"  x[0] = {x[0]:+.6f}  (rotated to a near-zero start so the engage ramp has no step)")
    print(f"  peak slew {np.max(np.abs(np.diff(np.tile(x,3)))):.5f}/frame = "
          f"{np.max(np.abs(np.diff(np.tile(x,3))))/0.03*100:.1f} % of the Honda 0.03/frame limiter")
    print(f"\n  {'grp':>5s} {'bin':>4s} {'f Hz':>7s} {'A':>9s} {'phase rad':>10s} | "
          f"{'d rate':>8s} {'coh':>5s} | {'d path':>8s} {'coh':>5s} | {'d ang':>7s} | {'|L| now':>8s}")
    grp = lambda k: "CORE" if k in CORE else ("MARG" if k in MARG else "CAL")
    for k, a, p_ in zip(KS, A, ph):
        zeq = a * np.abs(P[k] * S[k]) / max(np.abs(Tzm[k]), 1e-9)
        print(f"  {grp(k):>5s} {k:4d} {f[k]:7.3f} {a:9.6f} {p_:+10.6f} | "
              f"{zeq*Tzsr[k]:8.4f} {g_zsr[k]:5.2f} | {zeq*Tzy[k]:8.4f} {g_zy[k]:5.2f} | "
              f"{zeq*Tzsr[k]/(2*np.pi*f[k]):7.4f} | {abs(L[k]):8.3f}")

    # ---- audits
    w = sg.get_window("hann", NPS)
    acc = np.zeros(NPS // 2 + 1)
    for _ in range(300):
        s = int(RNG.integers(0, NPS))
        acc += np.abs(np.fft.rfft(sg.detrend(np.tile(x, 4)[s:s + NPS]) * w)) ** 2
    acc /= 300
    print("\nSPECTRAL AUDIT of the shipped waveform (its own analysis power)")
    for lo, hi, nm in [(0.60, 2.20, "CORE band"), (2.40, 5.60, "MARGIN band"),
                       (1.80, 3.50, "SHAKE band 1.8-3.5"), (0.15, 0.60, "0.15-0.60, 98 % of the gap"),
                       (6.0, 12.0, "6-12 Hz"), (13.0, 15.0, "CAL tone")]:
        b = (f >= lo) & (f <= hi)
        print(f"  {acc[b].sum()/acc.sum()*100:6.2f} %  {nm}")

    print("\nWHEEL-RATE COST vs what the wheel already does (measured Ssr on the same windows)")
    for lo, hi, nm in [(0.60, 2.20, "CORE band"), (1.80, 3.50, "SHAKE band"), (2.40, 5.60, "MARGIN band")]:
        b = (f >= lo) & (f <= hi)
        now = np.sqrt(Ssr[b].sum()) / G * np.sqrt(2)           # equivalent-amplitude rms, same units
        addp = 0.0
        for k, a in zip(KS, A):
            if lo <= f[k] <= hi:
                zeq = a * np.abs(P[k] * S[k]) / max(np.abs(Tzm[k]), 1e-9)
                addp += (zeq * Tzsr[k]) ** 2 / 2
        add = np.sqrt(addp)
        print(f"  {nm:14s} today {now:7.4f} deg/s rms | probe adds {add:6.4f} "
              f"=> x{np.sqrt(now**2+add**2)/max(now,1e-9):5.3f}")

    print("\nDURATION (measured yield 0.1735 qualifying windows/s on T64)")
    print(f"  {'coh':>5s} {'n_win':>6s} {'sec':>6s} {'SE |1+L|':>9s} {'SE arg':>8s}")
    for c in (0.5, 0.7):
        for nw in (6, 10, 14, 20):
            se = np.sqrt((1 - c) / (2 * (nw / 1.125) * c))
            print(f"  {c:5.2f} {nw:6d} {nw/wps:6.0f} {se*100:8.1f}% {np.degrees(se):7.1f}d")

    np.savez(OUT / "d7_ship.npz", ks=np.array(KS), amps=A, phases=ph, x=x, cf=cf, f=f[KS])
    print("\n--- COEFFICIENT TABLE for the patch (bin, amplitude, phase_rad) ---")
    for k, a, p_ in zip(KS, A, ph):
        print(f"  ({k:3d}, {a:.6f}, {p_:+.6f}),   # {f[k]:6.3f} Hz  {grp(k)}")
    print("\nwrote out/d7_ship.npz")
