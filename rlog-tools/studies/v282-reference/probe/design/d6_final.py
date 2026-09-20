# -*- coding: utf-8 -*-
"""d6 -- the FINAL waveform: tone set, per-tone amplitudes, crest-factor-optimised phases,
        the margin-band extension, and every cost read off the measured transfers.

THE ESTIMATOR THE PROBE SERVES (exact algebra, no model):
    plant input  u_p = u_ctl + W ,  M = P*u_p + d ,  u_ctl = ff(Z) - C*M
 => u_p = [ff - C*d + W] / (1 + L)          and W is uncorrelated with ff and d
 => 1 + L(f) = S_WW(f) / S_{W,u_p}(f)       ONE DIVISION.  |1+L| IS the vector margin.
    P(f)      = S_{W,M} / S_{W,u_p}
    C_fb(f)   = L / P                        (falls out; also checkable against the analytic C)
u_p = (logged controller output) + (the probe), so u_p is known exactly once W is known exactly.

Requirements, per bin, at target coherence rho/(1+rho):
    margin 1+L :  S_WW >= rho * S_uu / |S|^2      (|S| ~ 1 here, so ~ the command's own power)
    plant  P   :  S_WW >= rho * S_mm / |P*S|^2
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
RNG = np.random.default_rng(11)


def xs(A, B):
    return np.mean(np.conj(A) * B, axis=0)


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


def schroeder(amps):
    P = np.asarray(amps, float) ** 2
    P = P / P.sum()
    return np.array([-2.0 * np.pi * sum((l - i) * P[i] for i in range(l)) for l in range(len(P))])


def build(amps, phases, ks, n=NPS, k0=0):
    t = (np.arange(n) + k0) / FS
    x = np.zeros(n)
    for A, ph, k in zip(amps, phases, ks):
        x += A * np.cos(2.0 * np.pi * k * DF * t + ph)
    return x


def cf_opt(amps, ks, iters=2500, restarts=40):
    """Time-frequency swapping with the amplitude spectrum HELD EXACTLY, plus a start-at-zero
    rotation so the waveform can be ramped in from zero with no step."""
    best_x, best_cf, best_ph = None, np.inf, None
    for r in range(restarts):
        ph = schroeder(amps) if r == 0 else RNG.uniform(-np.pi, np.pi, len(amps))
        x = build(amps, ph, ks)
        for _ in range(iters):
            c = float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))
            if c < best_cf:
                best_cf, best_x, best_ph = c, x.copy(), ph.copy()
            lim = 0.93 * np.max(np.abs(x))
            X = np.fft.rfft(np.clip(x, -lim, lim))
            ph = np.angle(X[ks])
            x = build(amps, ph, ks)
    # rotate the time origin to the sample where |x| is smallest AND rising slowest
    j = int(np.argmin(np.abs(best_x) + 0.02 * np.abs(np.gradient(best_x))))
    ph_rot = np.array([(p + 2 * np.pi * k * DF * j / FS) for p, k in zip(best_ph, ks)])
    ph_rot = (ph_rot + np.pi) % (2 * np.pi) - np.pi
    x_rot = build(amps, ph_rot, ks)
    return x_rot, best_cf, ph_rot


if __name__ == "__main__":
    W = pool("T64")
    f = W["f"]
    Z, M, U, UFB, Y, SR = W["Z"], W["M"], W["U"], W["UFB"], W["Y"], W["SR"]
    E = Z - M
    Szz, See, Smm, Suu = xs(Z, Z).real, xs(E, E).real, xs(M, M).real, xs(U, U).real
    Tzm, Tzu = xs(Z, M) / Szz, xs(Z, U) / Szz
    Tzsr, Tzy = np.abs(xs(Z, SR) / Szz), np.abs(xs(Z, Y) / Szz)
    P = xs(Z, M) / xs(Z, U)
    L = P * (xs(Z, UFB) / xs(Z, E))
    S = 1.0 / (1.0 + L)
    n = Z.shape[0]
    wps = n / W["sec"]

    def req(k, rho, what):
        if what == "margin":
            return np.sqrt(rho * Suu[k]) / np.abs(S[k]) / G
        return np.sqrt(rho * Smm[k]) / np.abs(P[k] * S[k]) / G

    # ---------------------------------------------------------------- CORE set (the brief's band)
    CORE = [7, 10, 13, 16, 19, 22]          # 0.684 .. 2.148 Hz, 3-bin spacing
    # ---------------------------------------------------------------- MARGIN set (where VM binds)
    MARG = [26, 32, 38, 44, 50, 56]          # 2.54 .. 5.47 Hz, 6-bin spacing

    for tag, KS, rho in [("CORE 0.68-2.15 Hz  (identification)", CORE, 7.0 / 3.0),
                         ("MARGIN 2.5-5.5 Hz  (vector margin only)", MARG, 7.0 / 3.0)]:
        print(f"\n=== {tag}, target coherence 0.70")
        A_m = np.array([req(k, rho, "margin") for k in KS])
        A_p = np.array([req(k, rho, "plant") for k in KS])
        A = np.maximum(A_m, A_p) if "CORE" in tag else A_m
        x, cf, ph = cf_opt(A, np.array(KS), iters=1200, restarts=16)
        pk = float(np.max(np.abs(x)))
        print(f"  crest factor {cf:.3f}   rms {np.sqrt(np.mean(x**2)):.5f}   PEAK {pk:.5f} unit torque")
        print(f"  {'f Hz':>6s} {'bin':>4s} {'A_margin':>9s} {'A_plant':>9s} {'A used':>9s} "
              f"{'phase deg':>10s} | {'rate d/s':>9s} {'path m/s2':>10s} {'ang deg':>8s} {'slew/fr':>8s}")
        for k, am, ap, a, p_ in zip(KS, A_m, A_p, A, ph):
            zeq = a * np.abs(P[k] * S[k]) / max(np.abs(Tzm[k]), 1e-9)
            print(f"  {f[k]:6.3f} {k:4d} {am:9.5f} {ap:9.5f} {a:9.5f} {np.degrees(p_):10.1f} | "
                  f"{zeq*Tzsr[k]:9.4f} {zeq*Tzy[k]:10.4f} {zeq*Tzsr[k]/(2*np.pi*f[k]):8.4f} "
                  f"{2*np.pi*f[k]*a/FS:8.5f}")
        zeqs = np.array([a * np.abs(P[k] * S[k]) / max(np.abs(Tzm[k]), 1e-9) for k, a in zip(KS, A)])
        rate_rms = float(np.sqrt(np.sum((zeqs * Tzsr[KS]) ** 2) / 2))
        path_rms = float(np.sqrt(np.sum((zeqs * Tzy[KS]) ** 2) / 2))
        slew = float(np.max(np.abs(np.diff(np.tile(x, 3)))))
        print(f"  TOTALS: wheel-rate rms {rate_rms:.4f} deg/s | path rms {path_rms:.4f} m/s^2 | "
              f"peak slew {slew:.5f}/frame ({slew/0.03*100:.1f} % of the Honda 0.03 limiter)")
        np.savez(OUT / f"d6_{'core' if 'CORE' in tag else 'margin'}.npz",
                 ks=np.array(KS), amps=A, phases=ph, x=x, cf=cf, f=f[KS])
        print("  " + "  ".join(f"({k}, {a:.6f}, {p_:+.6f})" for k, a, p_ in zip(KS, A, ph)))

    # --------------------------------------------------------------- shake-band audit of the CORE set
    D = np.load(OUT / "d6_core.npz")
    xc = D["x"]
    w = sg.get_window("hann", NPS)
    acc = np.zeros(NPS // 2 + 1)
    for _ in range(200):
        s = int(RNG.integers(0, NPS))
        seg = np.tile(xc, 4)[s:s + NPS]
        acc += np.abs(np.fft.rfft(sg.detrend(seg) * w)) ** 2
    acc /= 200
    tot = acc.sum()
    for lo, hi, nm in [(0.6, 2.2, "probe band"), (1.8, 3.5, "SHAKE band"),
                       (0.15, 0.60, "0.15-0.60 (98 % of the gap)"), (2.2, 50.0, "above 2.2 Hz")]:
        b = (f >= lo) & (f <= hi)
        print(f"  CORE waveform: {acc[b].sum()/tot*100:6.2f} % of its analysis power in {nm}")

    # --------------------------------------------------------------- duration
    print("\n=== DURATION for the CORE probe")
    print(f"  measured window yield on T64: {wps:.4f} windows per second of qualifying driving")
    print(f"  {'coh':>5s} {'n_win':>6s} {'sec':>6s} {'SE |1+L|':>9s} {'SE phase':>9s}")
    for c in (0.5, 0.6, 0.7, 0.8):
        for nw in (6, 10, 15, 20, 30):
            ne = nw / 1.125
            se = np.sqrt((1 - c) / (2 * ne * c))
            if nw in (10, 20):
                print(f"  {c:5.2f} {nw:6d} {nw/wps:6.0f} {se*100:8.1f}% {np.degrees(se):8.1f} deg")
