# -*- coding: utf-8 -*-
"""d10 -- FINAL.  Group A only.  The 13.965 Hz control tone is DROPPED (d9 priced it at 3.4 deg/s of
wheel rate on a transfer that is non-causal at that frequency -- U at 14 Hz is DRIVEN BY the
measurement, not driving it, so |S_U,SR|/S_UU there reads the controller, and the fork's own
simulation of the same quantity disagrees with it by ~100x.  An uncertifiable cost on a control
tone is not a control).  Its job is done instead by three controls that cost NOTHING:

  C1 SKIRT   a tone exactly on bin k, Hann-windowed and exactly periodic in the window, puts
             HALF its amplitude (a quarter of its power) on bins k+-1, with a fixed phase relation.
             Measured at k+-1 -> confirms the probe was periodic and undisturbed: a gate that fired,
             a ramp still running, or a lost frame all break it.  3-bin spacing keeps skirts disjoint.
  C2 EMPTY   S_WW is exactly 0 on every non-tone bin, so running the SAME estimator there returns
             the estimator's own null distribution, on the same windows, with no added excitation.
             "Is the tone-bin answer distinguishable from nothing" stops being a belief.
  C3 WIRE    the probe is added AFTER pid_log.output is written, so (e4_cmd - 4089*cs_out) is the
             probe ALONE on the CAN wire.  Per window its SNR is -1 to +9 dB (d8), so this is a
             COHERENT average over n windows: +10*log10(n) = +11.5 dB at n=14.

Costs are the MAX of two estimators of the command -> wheel-rate gain (direct H1, and the IV with Z
as instrument), because the direct one is closed-loop-biased wherever U is driven by the feedback.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
STUDY = HERE.parents[1]
F1 = STUDY / "shapedgain" / "frontier" / "out"
sys.path.insert(0, str(STUDY / "loopshape" / "loopshape"))
import lp_lib as LP  # noqa: E402

FS, NPS, G = 100.0, 1024, 256.0
DF, LSB, KPAR = FS / NPS, 1.0 / 4089.0, 0.002295
RNG = np.random.default_rng(17)
RHO = 7.0 / 3.0
GA = [7, 10, 13, 16]


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


def cf_opt(a, ks, iters=6000, restarts=160):
    best, ks = (np.inf, None, None), np.asarray(ks)
    for r in range(restarts):
        ph = schroeder(a) if r == 0 else RNG.uniform(-np.pi, np.pi, len(a))
        x = build(a, ph, ks)
        for _ in range(iters):
            c = float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))
            if c < best[0]:
                best = (c, x.copy(), ph.copy())
            lim = (0.86 + 0.12 * RNG.random()) * np.max(np.abs(x))
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
    Tusr_d, Tuy_d = np.abs(xs(U, SR) / Suu), np.abs(xs(U, Y) / Suu)
    Tusr_iv = np.abs(xs(Z, SR) / xs(Z, U))
    Tuy_iv = np.abs(xs(Z, Y) / xs(Z, U))
    Tusr, Tuy = np.maximum(Tusr_d, Tusr_iv), np.maximum(Tuy_d, Tuy_iv)
    g_ze = coh(Z, E)

    A = np.array([max(np.sqrt(RHO * Suu[k]) / np.abs(S[k]),
                      np.sqrt(RHO * Smm[k]) / np.abs(P[k] * S[k])) / G for k in GA])
    x, cf, ph = cf_opt(A, GA)
    pk = float(np.max(np.abs(x)))

    print("=" * 96)
    print("PROBE  'AccordIdProbe'  -- periodic multisine, command node, 10.24 s period, 100 Hz")
    print("=" * 96)
    print(f"  tones 4 | crest factor {cf:.3f} | rms {np.sqrt(np.mean(x**2)):.6f} | "
          f"PEAK {pk:.6f} unit torque = {pk/LSB:.1f} counts of 0xE4")
    print(f"  x[0] = {x[0]:+.7f}  | peak slew {np.max(np.abs(np.diff(np.tile(x,3)))):.6f}/frame = "
          f"{np.max(np.abs(np.diff(np.tile(x,3))))/0.03*100:.1f} % of the Honda +-0.03/frame limiter")
    print(f"  AccordDither ships 0.008-0.012 with a 0.02 ceiling: this peak is {pk/0.02*100:.0f} % of "
          f"that ceiling, at 1/10 the frequency.\n")
    print(f"  {'bin':>4s} {'f Hz':>7s} {'A':>9s} {'cts':>6s} {'phase rad':>11s} | "
          f"{'wheel rate deg/s':>17s} | {'path m/s2':>10s} | {'angle deg':>10s}")
    for k, a, p_ in zip(GA, A, ph):
        print(f"  {k:4d} {f[k]:7.3f} {a:9.6f} {a/LSB:6.1f} {p_:+11.6f} | "
              f"{a*Tusr[k]:17.4f} | {a*Tuy[k]:10.4f} | {a*Tusr[k]/(2*np.pi*f[k]):10.4f}")
    print(f"  {'':4s} {'PEAK':>7s} {np.sum(A):9.6f} {np.sum(A)/LSB:6.1f} {'':11s} | "
          f"{np.sum(A*Tusr[GA]):17.4f} | {np.sum(A*Tuy[GA]):10.4f} | "
          f"{np.sum(A*Tusr[GA]/(2*np.pi*f[GA])):10.4f}   (sum of amplitudes)")
    rr = np.sqrt(np.sum((A * Tusr[GA]) ** 2) / 2)
    ry = np.sqrt(np.sum((A * Tuy[GA]) ** 2) / 2)
    ra = np.sqrt(np.sum((A * Tusr[GA] / (2 * np.pi * f[GA])) ** 2) / 2)
    print(f"  {'':4s} {'RMS':>7s} {np.sqrt(np.sum(A**2)/2):9.6f} {'':6s} {'':11s} | "
          f"{rr:17.4f} | {ry:10.4f} | {ra:10.4f}")

    print("\n  WHAT IT COSTS, against what the car already does on these very windows")
    for lo, hi, nm in [(0.15, 0.60, "0.15-0.60 (98 % of the tracking gap)"),
                       (0.60, 1.80, "0.60-1.80 (the probe's own band)"),
                       (1.80, 3.50, "1.80-3.50 (THE SHAKE BAND, x3.1 vs V282)"),
                       (3.50, 8.00, "3.50-8.00")]:
        b = (f >= lo) & (f <= hi)
        nsr, ny = KPAR * np.sqrt(Ssr[b].sum()), KPAR * np.sqrt(Syy[b].sum())
        asr = np.sqrt(sum((a * Tusr[k]) ** 2 / 2 for k, a in zip(GA, A) if lo <= f[k] <= hi))
        ay = np.sqrt(sum((a * Tuy[k]) ** 2 / 2 for k, a in zip(GA, A) if lo <= f[k] <= hi))
        print(f"    {nm:42s} wheel rate {nsr:6.3f} -> {np.sqrt(nsr**2+asr**2):6.3f} deg/s "
              f"(x{np.sqrt(nsr**2+asr**2)/nsr:5.3f}) | path {ny:6.4f} -> "
              f"{np.sqrt(ny**2+ay**2):6.4f} m/s2 (x{np.sqrt(ny**2+ay**2)/ny:5.3f})")
    print(f"    wheel angle: {ra:.3f} deg rms, {np.sum(A*Tusr[GA]/(2*np.pi*f[GA])):.3f} deg peak, "
          f"vs the 0.1 deg quantiser and the measured 1.1-1.3 deg backlash band 2F/k at 19-26 m/s")

    print("\n  PRE-REGISTERED COHERENCE, and the CI one drive buys")
    print(f"  {'f Hz':>7s} {'coh(Z,E) today':>15s} {'-> coh(W,u_p)':>14s} {'coh(W,M)':>9s} | "
          f"{'n=6':>16s} {'n=10':>16s} {'n=14':>16s}")
    for k, a in zip(GA, A):
        Sww = (a * G) ** 2
        c_up = np.abs(S[k]) ** 2 * Sww / (np.abs(S[k]) ** 2 * Sww + Suu[k])
        c_m = np.abs(P[k] * S[k]) ** 2 * Sww / (np.abs(P[k] * S[k]) ** 2 * Sww + Smm[k])
        cis = []
        for nw in (6, 10, 14):
            se = np.sqrt((1 - c_up) / (2 * (nw / 1.125) * c_up))
            cis.append(f"{se*100:5.1f}% {np.degrees(se):5.1f}d")
        print(f"  {f[k]:7.3f} {g_ze[k]:15.3f} {c_up:14.3f} {c_m:9.3f} | " + " ".join(f"{c:>16s}" for c in cis))
    print(f"\n  yield {wps:.4f} windows/s  =>  n=6: {6/wps:.0f} s | n=10: {10/wps:.0f} s | "
          f"n=14: {14/wps:.0f} s of engaged, hands-off, >=15 m/s driving in runs >= 30 s")
    print(f"  a 30 s run gives 4.9 windows, a 45 s run 7.8, a 60 s run 10.7 "
          f"=> n=10 is TWO 30 s runs or ONE 60 s run; n=14 is three 30 s runs.")

    np.savez(OUT / "d10_final.npz", ks=np.array(GA), amps=A, phases=ph, x=x, cf=cf, f=f[GA])
    print("\n  PATCH COEFFICIENTS (bin, amplitude, phase_rad):")
    for k, a, p_ in zip(GA, A, ph):
        print(f"    ({k:2d}, {a:.6f}, {p_:+.6f}),   # {f[k]:6.3f} Hz, {a/LSB:4.1f} counts")
