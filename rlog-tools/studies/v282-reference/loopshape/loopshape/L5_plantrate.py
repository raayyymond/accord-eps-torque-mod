# -*- coding: utf-8 -*-
"""L5 -- the plant from COMMAND to STEERING RATE, and how much of the wheel motion the command
        explains, per band.

WHY THE DIRECT ESTIMATOR IS LEGITIMATE HERE.  S_uy/S_uu is biased toward -1/C_fb by the amount of
feedback in the loop.  L1/L3 MEASURED |L| in 1.8-3.5 Hz: 0.04-0.13 on every build at >=15 m/s.
With |L| that small the loop is effectively open and the bias term is of that order.  The IV
estimate is reported alongside wherever its instrument coherence allows, as the check.

Reported per route x band x speed bin:
  |P_rate| = |S_u,srate| / S_uu     deg/s per unit commanded torque
  gamma^2(u, srate)                 the fraction of the wheel RATE that the command explains
  incoherent wheel-rate rms         the part the command does NOT explain
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

import lp_lib as LP

OUT = Path(__file__).resolve().parent / "out"
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 1.80), (1.80, 3.50), (3.50, 6.00)]


def _self_test():
    """Positive control: a KNOWN command->rate plant driven in closed loop with a WEAK loop
    (|L| ~ 0.1, as measured in the shake band) plus a big disturbance.  The direct estimator must
    recover the known gain to within ~15%, and the coherence must read the driven fraction."""
    rng = np.random.default_rng(5)
    n = 300 * 100
    g = 700.0                      # deg/s per unit command, flat
    kp, laf = 1.0, 14.0
    r = signal.sosfiltfilt(signal.butter(2, 3.0, fs=LP.FS, output="sos"), rng.standard_normal(n)) * 5
    d = signal.sosfiltfilt(signal.butter(2, [1.8, 3.5], btype="band", fs=LP.FS, output="sos"),
                           rng.standard_normal(n)) * 3.0
    y = np.zeros(n); u = np.zeros(n); sr = np.zeros(n)
    for k in range(n):
        u[k] = -(kp * (r[k] - y[k])) / laf
        sr[k] = g * u[k] + d[k]
        if k + 1 < n:
            y[k + 1] = 0.02 * sr[k]          # tiny angle feedback => |L| small
    fw, Suu = signal.welch(u, LP.FS, nperseg=1024)
    _, Sus = signal.csd(u, sr, LP.FS, nperseg=1024)
    _, Sss = signal.welch(sr, LP.FS, nperseg=1024)
    b = (fw >= 1.8) & (fw < 3.5)
    ghat = float(np.average(np.abs(Sus[b]) / Suu[b], weights=Suu[b]))
    coh = float(np.average(np.abs(Sus[b]) ** 2 / (Suu[b] * Sss[b]), weights=Suu[b]))
    msg = f"    control: known g {g:.0f} -> estimated {ghat:.0f} ({100*(ghat/g-1):+.1f}%), coh {coh:.3f}"
    assert abs(ghat / g - 1) < 0.15, msg
    return msg


def do(route, vlo, vhi, nps=512):
    L = LP.load_loop(route)
    wins = LP.windows(L, vlo, vhi, nps, nps // 2)
    if len(wins) < 6:
        del L
        return None
    w = LP.hann(nps)
    f = np.fft.rfftfreq(nps, LP.DT)
    u = np.nan_to_num(L["out"]); sr = np.nan_to_num(L["sr"]); rr = np.nan_to_num(L["r"])
    Suu = np.zeros(len(f)); Sss = np.zeros(len(f)); Sus = np.zeros(len(f), complex)
    Srr = np.zeros(len(f)); Sru = np.zeros(len(f), complex); Srs = np.zeros(len(f), complex)
    for s, e, _ in wins:
        U = np.fft.rfft(signal.detrend(u[s:e]) * w)
        SS = np.fft.rfft(signal.detrend(sr[s:e]) * w)
        R = np.fft.rfft(signal.detrend(rr[s:e]) * w)
        Suu += np.abs(U) ** 2; Sss += np.abs(SS) ** 2; Sus += np.conj(U) * SS
        Srr += np.abs(R) ** 2; Sru += np.conj(R) * U; Srs += np.conj(R) * SS
    out = dict(route=route, fam=LP.GROUPS[route], n_win=len(wins), bands={})
    for f1, f2 in BANDS:
        b = (f >= f1) & (f < f2)
        if b.sum() < 1:
            continue
        gdir = float(np.average(np.abs(Sus[b]) / np.maximum(Suu[b], 1e-30), weights=Suu[b]))
        coh = float(np.average(np.abs(Sus[b]) ** 2 / np.maximum(Suu[b] * Sss[b], 1e-30), weights=Suu[b]))
        giv = float(np.average(np.abs(Srs[b]) / np.maximum(np.abs(Sru[b]), 1e-30), weights=Suu[b]))
        cru = float(np.average(np.abs(Sru[b]) ** 2 / np.maximum(Srr[b] * Suu[b], 1e-30), weights=Suu[b]))
        srms = float(np.sqrt(np.sum(Sss[b]) / len(wins) / nps ** 2 * 2 * nps / (w ** 2).sum() * nps))
        out["bands"][f"{f1}-{f2}"] = dict(g_dir=gdir, g_iv=giv, coh_u_sr=coh, coh_r_u=cru,
                                          sr_rms=srms, sr_rms_incoh=srms * np.sqrt(max(1 - coh, 0.0)))
    del L
    return out


if __name__ == "__main__":
    print(_self_test())
    for vlo, vhi in ((15.0, 22.0), (8.0, 15.0), (22.0, 99.0)):
        print("=" * 118)
        print(f"COMMAND -> STEERING RATE, {vlo}-{vhi} m/s.  g = deg/s per unit commanded torque.")
        print("  g_dir = direct (near-unbiased where |L| << 1)  g_iv = instrumental variable")
        print("  coh = fraction of the wheel RATE the command explains; rms/inc = total / unexplained deg/s")
        print("=" * 118)
        hdr = "  ".join(f"{a}-{b} Hz".center(23) for a, b in BANDS[2:5])
        print(f"{'rt':4s} {'fam':7s} " + hdr)
        print(f"{'':4s} {'':7s} " + "  ".join(f"{'g_dir  coh   rms   inc':23s}" for _ in BANDS[2:5]))
        allr = {}
        for route in LP.GROUPS:
            if not (LP.V.CACHE / f"{route}.npz").exists():
                continue
            r = do(route, vlo, vhi)
            if not r:
                continue
            allr[route] = r
            cells = []
            for f1, f2 in BANDS[2:5]:
                d = r["bands"].get(f"{f1}-{f2}")
                cells.append(f"{d['g_dir']:6.0f}{d['coh_u_sr']:6.2f}{d['sr_rms']:6.2f}{d['sr_rms_incoh']:6.2f}"
                             if d else " " * 23)
            print(f"{route[6:8]:4s} {r['fam']:7s} " + "  ".join(cells))
        json.dump(allr, open(OUT / f"L5_{int(vlo)}_{int(vhi)}.json", "w"), indent=1)
        print()
