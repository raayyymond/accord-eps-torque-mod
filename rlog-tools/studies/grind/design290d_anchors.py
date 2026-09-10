# -*- coding: utf-8 -*-
"""studies/grind/design290d_anchors.py -- INDEPENDENT re-derivation of the two measured pole anchors the V290 plant
family is fitted to.  Agent design290d, 2026-09-09.  Reads nothing but the route caches; does NOT import
adv_v290_physics / adv_v290_relocation / grind1_* -- the point is a second method, not a re-run of the first.

Anchors under test (from the record):
  V282 (r39)          : closed-loop pole 20.0 Hz, zeta ~ 0.027
  V289 (r62 + r63)    : closed-loop pole 16.4-17.0 Hz, burst zeta_eff 0.02-0.13
  V288 (r5e)          : control -- should still sit at ~20 Hz (V288's cave was reference-side, inert on the loop)

Method (deliberately different from the census / relocation studies):
  f  : Welch PSD of the WHEEL RATE (cs_rate, 100 Hz), engaged samples only, per contiguous engaged run; peak in 8-30 Hz
       of the median-normalised spectrum, plus a parabolic interpolation of the peak bin.
  z  : free-decay.  Band-pass +-3 Hz (4th-order Butterworth, filtfilt) about the peak, Hilbert envelope, locate envelope
       local maxima above the 90th percentile of the engaged envelope, fit log(env) vs t over the following 60-250 ms
       window while the envelope is monotonically falling; zeta = -slope / (2 pi f).  Median over bursts + bootstrap CI.
  A negative/near-zero zeta cannot be seen this way (a growing envelope is discarded); the GROWTH side is reported as
  the fraction of bursts whose envelope grows over the same window -- that is the limit-cycle signature.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "analysis-2020accord", "_scratch", "cache"))
FS = 100.0
ROUTES = [("r39", "V282"), ("r5e_v288", "V288 rev 2"), ("r62_v289", "V289 rev 1"), ("r63_v289", "V289 rev 1")]


def load(key):
    d = np.load(os.path.join(CACHE, key, key + ".npz"), allow_pickle=True)
    t = d["t"]
    eng = (d["cc_lat"] > 0.5) & (d["sca"] > 0.5)
    return t, np.asarray(d["cs_rate"], float), eng, np.asarray(d["cs_v"], float)


def runs(mask, minlen):
    """contiguous True runs of at least minlen samples -> list of (i0, i1)."""
    m = np.concatenate(([False], mask, [False])).astype(np.int8)
    e = np.diff(m)
    a, b = np.where(e == 1)[0], np.where(e == -1)[0]
    return [(i, j) for i, j in zip(a, b) if j - i >= minlen]


def psd_peak(x_runs, flo=8.0, fhi=30.0, nper=512):
    """Welch-average over runs; return (f_peak, f, Pxx_normalised)."""
    P, W = None, 0.0
    for x in x_runs:
        if len(x) < nper:
            continue
        f, p = signal.welch(signal.detrend(x), FS, nperseg=nper, noverlap=nper // 2)
        if P is None:
            P = np.zeros_like(p)
        P += p * len(x); W += len(x)
    P /= W
    # normalise by a broad running median so the peak is a LINE, not the 1/f skirt
    k = 9
    med = signal.medfilt(P, k)
    R = P / np.maximum(med, 1e-30)
    m = (f >= flo) & (f <= fhi)
    i = np.argmax(P[m] / np.maximum(med[m], 1e-30))
    idx = np.where(m)[0][i]
    # parabolic interpolation on log power
    if 0 < idx < len(P) - 1:
        y0, y1, y2 = np.log(P[idx - 1]), np.log(P[idx]), np.log(P[idx + 1])
        d = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if (y0 - 2 * y1 + y2) != 0 else 0.0
        fpk = f[idx] + d * (f[1] - f[0])
    else:
        fpk = f[idx]
    return float(fpk), f, P, R


def decay(x_runs, f0, bw=3.0, wlo=0.06, whi=0.25):
    """free-decay zeta from the Hilbert envelope of the band-passed rate."""
    lo, hi = max(1.0, f0 - bw), min(48.0, f0 + bw)
    sos = signal.butter(4, [lo / (FS / 2), hi / (FS / 2)], btype="band", output="sos")
    zs, grow, n = [], 0, 0
    envs = []
    for x in x_runs:
        if len(x) < 200:
            continue
        y = signal.sosfiltfilt(sos, signal.detrend(x))
        env = np.abs(signal.hilbert(y))
        envs.append(env)
    if not envs:
        return np.nan, np.nan, np.nan, 0, np.nan
    thr = np.percentile(np.concatenate(envs), 90)
    n0, n1 = int(wlo * FS), int(whi * FS)
    for env in envs:
        pk, _ = signal.find_peaks(env, height=thr, distance=int(0.15 * FS))
        for p in pk:
            if p + n1 >= len(env):
                continue
            seg = env[p + n0: p + n1]
            if seg.min() <= 0:
                continue
            tt = np.arange(len(seg)) / FS
            s, _ = np.polyfit(tt, np.log(seg), 1)
            n += 1
            if s >= 0:
                grow += 1
                continue
            zs.append(-s / (2 * np.pi * f0))
    if not zs:
        return np.nan, np.nan, np.nan, n, grow / max(n, 1)
    zs = np.array(zs)
    bs = [np.median(np.random.RandomState(k).choice(zs, len(zs))) for k in range(400)]
    return float(np.median(zs)), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), n, grow / max(n, 1)


def main():
    print("design290d_anchors -- INDEPENDENT anchor re-derivation (Welch peak + Hilbert free-decay), wheel rate cs_rate @100 Hz")
    print("%-12s %-11s | %6s | %-28s | %-24s | %s" % ("route", "build", "f_pk Hz", "zeta free-decay [95% CI]", "n bursts / grow frac", "engaged s"))
    for key, build in ROUTES:
        t, r, eng, v = load(key)
        m = eng & (v > 3.0)
        rr = [signal.detrend(r[i:j]) for i, j in runs(m, 400)]
        if not rr:
            print("%-12s %-11s | no engaged runs" % (key, build)); continue
        fpk, f, P, R = psd_peak(rr)
        z, lo, hi, n, gf = decay(rr, fpk)
        secs = sum(len(x) for x in rr) / FS
        print("%-12s %-11s | %6.2f | %8.4f [%7.4f %7.4f]        | %5d / %.2f            | %.0f" % (key, build, fpk, z, lo, hi, n, gf, secs))
        m2 = (f >= 8) & (f <= 30)
        top = np.argsort(-(P[m2]))[:5]
        print("             top 8-30 Hz bins: " + "  ".join("%.1f Hz (x%.1f)" % (f[m2][i], R[m2][i]) for i in sorted(top, key=lambda i: -R[m2][i])))
    print("\nPooled V289 (r62+r63) and V282 (r39) re-checked with a common band 12-24 Hz sub-peak search:")
    for keys, build in [(["r39"], "V282"), (["r5e_v288"], "V288"), (["r62_v289", "r63_v289"], "V289")]:
        rr = []
        for key in keys:
            t, r, eng, v = load(key)
            m = eng & (v > 3.0)
            rr += [signal.detrend(r[i:j]) for i, j in runs(m, 400)]
        fpk, f, P, R = psd_peak(rr, 12.0, 24.0)
        z, lo, hi, n, gf = decay(rr, fpk)
        print("  %-6s f %.2f Hz   zeta %.4f [%.4f %.4f]  n %d  grow %.2f" % (build, fpk, z, lo, hi, n, gf))


if __name__ == "__main__":
    main()
