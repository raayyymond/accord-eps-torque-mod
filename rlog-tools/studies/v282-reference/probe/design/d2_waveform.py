# -*- coding: utf-8 -*-
"""d2 -- choose the WAVEFORM, on measured cost, not on taste.

Every candidate is scored through the IDENTICAL analysis the study already runs (detrend, Hann,
rfft, nperseg 1024 at 100 Hz), averaged over random window offsets, so "power at 0.6-2.0 Hz per unit
PEAK amplitude" is measured the way the estimator will actually see it -- not from a textbook PSD.

Scores, all per unit PEAK amplitude of the injected setpoint signal (the peak is what the driver
feels and what risks the rail):
  E_band    fraction of the waveform's analysis power that lands in 0.6-2.0 Hz
  E_shake   fraction that lands in 1.8-3.5 Hz  (the shake band -- pure cost, and r71's 2.34 Hz)
  E_low     fraction that lands in 0.15-0.60 Hz (where 98 % of the tracking gap lives -- pure cost)
  CF        crest factor peak/rms
  eta       E_band / CF^2  == in-band power per unit peak^2   <-- the brief's figure of merit
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal as sg

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

FS, NPS = 100.0, 1024
DF = FS / NPS
BAND = (0.6, 2.0)
SHAKE = (1.8, 3.5)
LOW = (0.15, 0.60)
RNG = np.random.default_rng(7)


# ------------------------------------------------------------------ crest-factor optimisation
def schroeder_phases(amps):
    """Schroeder 1970, generalised to unequal amplitudes: phi_l = -2*pi*sum_{i<l}(l-i)*P_i."""
    P = np.asarray(amps, float) ** 2
    P = P / P.sum()
    n = len(P)
    phi = np.zeros(n)
    for l in range(n):
        phi[l] = -2.0 * np.pi * sum((l - i) * P[i] for i in range(l))
    return phi


def build(amps, phases, k_bins, n=NPS):
    t = np.arange(n) / FS
    x = np.zeros(n)
    for A, ph, k in zip(amps, phases, k_bins):
        x += A * np.cos(2.0 * np.pi * k * DF * t + ph)
    return x


def crest(x):
    return float(np.max(np.abs(x)) / np.sqrt(np.mean(x ** 2)))


def cf_optimise(amps, k_bins, iters=4000, restarts=24, n=NPS):
    """Van der Ouderaa / Guillaume time-frequency swapping: clip in time, restore the prescribed
    amplitude spectrum in frequency, repeat.  The amplitude spectrum is HELD EXACTLY, so the
    optimisation cannot cheat by moving power out of the band."""
    amps = np.asarray(amps, float)
    k_bins = np.asarray(k_bins, int)
    best_x, best_cf = None, np.inf
    for r in range(restarts):
        ph = schroeder_phases(amps) if r == 0 else RNG.uniform(-np.pi, np.pi, len(amps))
        x = build(amps, ph, k_bins, n)
        for _ in range(iters):
            c = crest(x)
            if c < best_cf:
                best_cf, best_x = c, x.copy()
            lim = 0.92 * np.max(np.abs(x))
            xc = np.clip(x, -lim, lim)
            X = np.fft.rfft(xc)
            ph = np.angle(X[k_bins])
            x = build(amps, ph, k_bins, n)
    return best_x, best_cf


# ------------------------------------------------------------------ analysis-domain scoring
def analysis_power(x_period, nrep=64):
    """Mean per-bin |rfft(detrend(x)*hann)|^2 over random 1024-sample windows of the repeated signal."""
    w = sg.get_window("hann", NPS)
    L = len(x_period)
    reps = int(np.ceil((NPS * 4 + L) / L)) + 2
    xx = np.tile(x_period, reps)
    acc = np.zeros(NPS // 2 + 1)
    for _ in range(nrep):
        s = int(RNG.integers(0, L))
        seg = xx[s:s + NPS]
        acc += np.abs(np.fft.rfft(sg.detrend(seg) * w)) ** 2
    return acc / nrep


def score(x_period, name, nrep=64):
    f = np.fft.rfftfreq(NPS, 1.0 / FS)
    S = analysis_power(x_period, nrep)
    tot = S.sum()
    b = lambda lo, hi: float(S[(f >= lo) & (f <= hi)].sum() / tot)
    pk = float(np.max(np.abs(x_period)))
    rms = float(np.sqrt(np.mean(x_period ** 2)))
    cf = pk / rms
    e_band = b(*BAND)
    return dict(name=name, cf=cf, e_band=e_band, e_shake=b(*SHAKE), e_low=b(*LOW),
                eta=e_band / cf ** 2, S=S, f=f, pk=pk, rms=rms)


# ------------------------------------------------------------------ candidates
def prbs(order, clock_hz, n_period=None):
    """Maximum-length sequence, +-1, held at clock_hz, tiled to a whole number of samples."""
    taps = {7: [7, 6], 9: [9, 5], 10: [10, 7], 11: [11, 9]}[order]
    N = 2 ** order - 1
    reg = np.ones(order, dtype=int)
    seq = np.empty(N)
    for i in range(N):
        seq[i] = 1.0 if reg[-1] else -1.0
        fb = reg[taps[0] - 1] ^ reg[taps[1] - 1]
        reg[1:] = reg[:-1]
        reg[0] = fb
    hold = int(round(FS / clock_hz))
    return np.repeat(seq, hold)


def chirp_sweep(T, f0=0.6, f1=2.0):
    t = np.arange(int(T * FS)) / FS
    return sg.chirp(t, f0, T, f1, method="linear")


if __name__ == "__main__":
    res = []

    # --- multisines on the 10.24 s grid.  Flat amplitude; tone spacing in BINS.
    for spacing, lo, hi, tag in [(3, 0.6, 2.0, "MS 3-bin 0.6-2.0"),
                                 (2, 0.6, 2.0, "MS 2-bin 0.6-2.0"),
                                 (3, 0.6, 1.6, "MS 3-bin 0.6-1.6"),
                                 (4, 0.6, 2.0, "MS 4-bin 0.6-2.0")]:
        k0, k1 = int(round(lo / DF)), int(round(hi / DF))
        ks = np.arange(k0, k1 + 1, spacing)
        A = np.ones(len(ks))
        x, cf = cf_optimise(A, ks, iters=1500, restarts=12)
        r = score(x, f"{tag} ({len(ks)} tones)")
        r["ks"] = ks.tolist()
        r["cf_opt"] = cf
        res.append(r)
        # Schroeder-only, for the record
        xs_ = build(A, schroeder_phases(A), ks)
        rs = score(xs_, f"{tag} SCHROEDER only")
        rs["ks"] = ks.tolist()
        res.append(rs)

    # --- chirps
    for T in (10.24, 20.48, 30.72):
        res.append(score(chirp_sweep(T), f"chirp 0.6-2.0 over {T:.2f}s"))

    # --- PRBS
    for order, clk in [(9, 4.0), (9, 6.0), (10, 5.0), (11, 4.0)]:
        res.append(score(prbs(order, clk), f"PRBS n={order} clk={clk:.1f}Hz"))

    print("WAVEFORM COMPARISON -- scored through the study's own analysis (Hann/1024, random offsets)")
    print(f"{'waveform':30s} {'CF':>6s} {'E_band':>7s} {'E_shake':>8s} {'E_low':>7s} {'eta':>7s} {'rel eta':>8s}")
    best = max(r["eta"] for r in res)
    for r in res:
        print(f"{r['name']:30s} {r['cf']:6.3f} {r['e_band']:7.3f} {r['e_shake']:8.3f} "
              f"{r['e_low']:7.3f} {r['eta']:7.4f} {r['eta']/best:8.2f}")

    json.dump([{k: v for k, v in r.items() if k not in ("S", "f")} for r in res],
              open(OUT / "d2_waveform.json", "w"), indent=1)
    print("\nwrote out/d2_waveform.json")
