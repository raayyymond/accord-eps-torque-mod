# -*- coding: utf-8 -*-
"""c1r2_trackmetric.py -- the GOAL'S OWN tracking metric, turned into a frequency weighting, so a linear T_ref can be
scored the way the car will be scored.  ANALYSIS ONLY.

THE METRIC (rlog-tools/studies/grind/v293_symptom_instruments.tracking_gain, grep "THE GAIN OF ACTUAL ON DESIRED"):
the OLS slope of actualLateralAccel on desiredLateralAccel, BOTH low-passed by a zero-phase 4th-order 0.5 Hz
Butterworth (sosfiltfilt), over engaged runs >= 10 s, per band <8 / 8-15 / 15-22 / >22 m/s.
For a linear Y = T*X, that slope is   sum_f |H(f)|^4 S_xx(f) Re T(f)  /  sum_f |H(f)|^4 S_xx(f)
(|H|^2 per filtfilt, applied to both X and Y).  S_xx is MEASURED here: the desired-lateral-accel spectrum of route
r71b (75604b0a432fdc89_00000071--a7b8ba5d9d, V294 + fork Dom 20d24ab79), engaged (carControl latActive), per band,
Welch per run, run-length weighted.  EVIDENCE for the spectrum (one route; BELIEF that it is representative).

WHAT THE SCORE MEANS: slope_inner(band) = the INNER angle loop's factor in the goal's tracking gain, i.e. the gain the
metric would read if the fork's VSR map, look-ahead and vehicle response were perfect.  It is NOT the on-car gain;
the on-car gain is this factor times the fork/vehicle factor (which the fork owns).

Output: c1/trackmetric_weights.json (f grid + normalised weights per band) and trackmetric.txt.
usage: python c1r2_trackmetric.py"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[3]
SRC = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"
WJSON = HERE / "trackmetric_weights.json"
BANDS = ((0.0, 8.0, "<8"), (8.0, 15.0, "8-15"), (15.0, 22.0, "15-22"), (22.0, 99.0, ">22"))
FGRID = np.round(np.arange(0.0025, 1.0001, 0.0025), 6)


def build():
    d = np.load(SRC)
    t = d["t_cs"]
    la = d["cs_la_des"]
    act = d["cs_active"] > 0.5
    v = np.interp(t, d["t_cst"], d["vego"])
    fs = 1.0 / float(np.median(np.diff(t)))
    sos = signal.butter(4, 0.5, "lowpass", fs=fs, output="sos")
    H2 = np.abs(signal.sosfreqz(sos, worN=FGRID, fs=fs)[1]) ** 2
    out = dict(route="75604b0a432fdc89_00000071--a7b8ba5d9d", fs=fs, f=FGRID.tolist(), bands={})
    lines = [f"# c1r2_trackmetric: route r71b, fs {fs:.2f} Hz; weights = |H_0.5Hz filtfilt|^4 * S_dd(f), normalised"]
    for lo, hi, nm in BANDS:
        m = act & (v >= lo) & (v < hi)
        e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
        runs = [(a, b) for a, b in zip(e[::2], e[1::2]) if b - a >= 10 * fs]
        if not runs:
            continue
        acc = np.zeros(len(FGRID))
        ntot = 0
        for a, b in runs:
            x = la[a:b] - np.mean(la[a:b])
            n = b - a
            f, P = signal.welch(x, fs=fs, nperseg=min(n, int(40 * fs)), detrend="constant")
            acc += np.interp(FGRID, f, P) * n
            ntot += n
        P = acc / ntot
        w = P * H2 ** 2
        w = w / w.sum()
        cdf = np.cumsum(w)
        out["bands"][nm] = dict(w=w.tolist(), sec=ntot / fs, runs=len(runs))
        lines.append(f"band {nm:>5s}: {ntot / fs:5.0f} s in {len(runs)} runs | weight median {FGRID[np.searchsorted(cdf, .5)]:.3f} Hz,"
                     f" p90 {FGRID[np.searchsorted(cdf, .9)]:.3f} Hz, share > 0.2 Hz {w[FGRID > 0.2].sum():.3f},"
                     f" > 0.5 Hz {w[FGRID > 0.5].sum():.4f}")
    WJSON.write_text(json.dumps(out))
    (HERE / "trackmetric.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return out


_W = None


def weights():
    global _W
    if _W is None:
        if not WJSON.exists():
            build()
        js = json.loads(WJSON.read_text())
        _W = (np.array(js["f"]), {k: np.array(b["w"]) for k, b in js["bands"].items()})
    return _W


def band_of(v):
    for lo, hi, nm in BANDS:
        if lo <= v < hi:
            return nm
    return ">22"


def slope(T_of_f, v):
    """the metric's slope for a linear T (callable on an f array), using the band of speed v."""
    f, W = weights()
    w = W[band_of(v)]
    return float(np.sum(w * np.real(T_of_f(f))))



def selfcheck():
    """POSITIVE CONTROL: filter the route's own desired lat accel through known linear T's, run the kit's REAL
    tracking_gain() on (desired, filtered), and compare with slope() from the weights."""
    import sys
    sys.path.insert(0, str(KIT / "rlog-tools" / "studies" / "grind"))
    import v293_symptom_instruments as SI
    d = np.load(SRC)
    t = d["t_cs"]
    la = d["cs_la_des"]
    act = d["cs_active"] > 0.5
    v = np.interp(t, d["t_cst"], d["vego"])
    fs = 1.0 / float(np.median(np.diff(t)))
    assert abs(fs - SI.FS) / SI.FS < 0.02, (fs, SI.FS)
    lines = ["POSITIVE CONTROL (the kit's own tracking_gain on synthetic Y = T*X vs the weighted prediction):"]
    tests = {"lag 0.25 s": lambda s: 1 / (1 + 0.25 * s), "delay 0.20 s": lambda s: np.exp(-0.2 * s),
             "2nd order 0.6 Hz z0.5": lambda s: (2 * np.pi * .6) ** 2 / (s ** 2 + 2 * .5 * 2 * np.pi * .6 * s + (2 * np.pi * .6) ** 2),
             "gain 0.9 + lag 0.5 s": lambda s: 0.9 / (1 + 0.5 * s)}
    worst = 0.0
    for nm, Tf in tests.items():
        # apply T in the frequency domain per contiguous engaged run (zero-padded FFT, causal for these T)
        y = np.zeros_like(la)
        n = len(la)
        N = 1 << int(np.ceil(np.log2(2 * n)))
        F = np.fft.rfftfreq(N, 1 / fs)
        y = np.fft.irfft(np.fft.rfft(la, N) * Tf(2j * np.pi * F), N)[:n]
        g = SI.tracking_gain(la, y, v, act, bands=[(lo, hi) for lo, hi, _ in BANDS], names=[b[2] for b in BANDS])
        cells = []
        for lo, hi, bn in BANDS:
            meas = g[bn]["slope"]
            pred = slope(lambda f: Tf(2j * np.pi * f), (lo + min(hi, 40)) / 2)
            if meas is not None:
                worst = max(worst, abs(meas - pred))
                cells.append(f"{bn}: meas {meas:.3f} pred {pred:.3f}")
        lines.append(f"  {nm:24s} " + " | ".join(cells))
    lines.append(f"  worst |meas - pred| = {worst:.4f}")
    print("\n".join(lines))
    with open(HERE / "trackmetric.txt", "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return worst


if __name__ == "__main__":
    build()
    selfcheck()
