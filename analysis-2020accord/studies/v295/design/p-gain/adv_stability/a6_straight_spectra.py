# -*- coding: utf-8 -*-
"""a6 -- anchor (C) measured directly: is there a closed-loop resonance at 2-3.5 Hz on r71b's hands-off STRAIGHTS and
curves at speed?  light_b predicts, for V294, Ms 3.1 at 2.9 Hz on 22+ straights (GM 1.69) and Ms 2.0 at 2.7 Hz at 15-22;
the identified family predicts Ms <= 1.1.  Welch PSD of wheel rate (x/8), angle and command on segments >= 4 s,
median-normalised by a smooth (log-log linear) fit over 0.5-6 Hz excluding 1.8-3.6 Hz; report the peak excess dB in
2.0-3.5 Hz and where it sits.  Positive control: route 71-old's 2.34 Hz limit cycle is not in this cache, so the control is
SYNTHETIC: a lightly damped 2.9 Hz second-order line (zeta 0.16, Ms ~3) added to the r71b straight rate at the drive's
own rms -- the detector must see it."""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness")
import v295_harness as H  # noqa: E402

d = H.route()
th, v, idx, eng, ho, x = d["th"], d["v"], d["idx"], d["eng"], d["ho"], d["x"]
wire = d["cmd"]   # 0xE4 command (route()["wire"] is the raw 0x18F rate field)
la = d["ctl_la_des"]
rate = np.asarray(d["om"], float) if "om" in d else np.gradient(th) * 100
out = open(os.path.join(HERE, "a6_straight_spectra_out.txt"), "w")


def P(*a):
    s = " ".join(str(z) for z in a)
    print(s)
    out.write(s + "\n")


def runs(mask, min_len=400):
    m = np.asarray(mask, bool)
    idxs = np.flatnonzero(np.diff(np.concatenate([[0], m.astype(int), [0]])))
    return [(a, b) for a, b in zip(idxs[::2], idxs[1::2]) if b - a >= min_len]


def psd_segments(sig, segs, nper=256):
    acc, n = None, 0
    for a, b in segs:
        y = signal.detrend(np.nan_to_num(sig[a:b]))
        f, p = signal.welch(y, fs=100.0, nperseg=min(nper, b - a), noverlap=min(nper, b - a) // 2)
        if acc is None or len(p) != len(acc):
            if acc is not None and len(p) != len(acc):
                continue
            acc = np.zeros_like(p)
            ff = f
        acc += p * (b - a)
        n += (b - a)
    return ff, acc / max(n, 1)


def excess(f, p, lo=2.0, hi=3.5):
    fit = (f >= 0.5) & (f <= 6.0) & ~((f >= 1.8) & (f <= 3.6)) & (p > 0)
    c = np.polyfit(np.log(f[fit]), np.log(p[fit]), 2)
    base = np.exp(np.polyval(c, np.log(np.maximum(f, 1e-3))))
    band = (f >= lo) & (f <= hi)
    ex = 10 * np.log10(p[band] / base[band])
    j = int(np.argmax(ex))
    return float(ex[j]), float(f[band][j]), float(np.mean(ex))


regimes = [("straight 22+", (v >= 22) & (idx < 9) & (np.abs(la) < 0.3)),
           ("straight 15-22", (v >= 15) & (v < 22) & (idx < 9) & (np.abs(la) < 0.3)),
           ("straight 10-15", (v >= 10) & (v < 15) & (idx < 9) & (np.abs(la) < 0.3)),
           ("curve 22+", (v >= 22) & (idx >= 18)),
           ("curve 15-22", (v >= 15) & (v < 22) & (idx >= 25)),
           ("all 22+", (v >= 22))]
base_mask = eng & ho & np.isfinite(th)
for nm, msk in regimes:
    segs = runs(base_mask & msk)
    if not segs:
        P("%-15s no segments" % nm)
        continue
    tot = sum(b - a for a, b in segs) / 100
    res = []
    for sn, sig in (("rate", rate), ("angle", th), ("cmd", wire)):
        f, p = psd_segments(sig, segs)
        res.append("%s peak %+.1f dB @%.2f (mean %+.1f)" % ((sn,) + excess(f, p)))
    P("%-15s %d segs %.0f s | %s" % (nm, len(segs), tot, " | ".join(res)))

# synthetic positive control: add a lightly damped 2.9 Hz resonance's response to white noise, at the rate's own rms
P("\npositive control (synthetic): r71b 22+ straight rate + a 2.9 Hz zeta 0.16 second-order line at 50 % / 100 % of its rms")
segs = runs(base_mask & regimes[0][1])
rng = np.random.default_rng(1)
wn = 2 * np.pi * 2.9
bz, az = signal.bilinear([wn ** 2], [1, 2 * 0.16 * wn, wn ** 2], fs=100.0)
for frac in (0.5, 1.0):
    syn = rate.copy()
    for a, b in segs:
        e = signal.lfilter(bz, az, rng.normal(size=b - a))
        e *= frac * np.std(rate[a:b]) / np.std(e)
        syn[a:b] = rate[a:b] + e
    f, p = psd_segments(syn, segs)
    P("  added line at %.0f %% rms: peak %+.1f dB @%.2f (mean %+.1f)" % ((frac * 100,) + excess(f, p)))
out.close()
