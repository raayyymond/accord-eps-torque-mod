# -*- coding: utf-8 -*-
"""studies/grind/v282_prereg_duty.py -- PRE-REGISTRATION arithmetic for the V282 cave comparator repoint.

V282 changes four `ld.h` displacement halfwords inside the EXISTING flown cave (0xC4B34, hash d3bb75d8,
byte-identical since V105) so that two of its five 0x14A byte-4 bits carry:
    bit 6 := (|gp-0x6ada| >= |gp-0x6b38|)   = |r24| >= |T|                    (was |6b94| >= |4f64|, duty 0.0000)
    bit 5 := (|gp-0x6ada| >= |gp-0x6b94|)   = |r24| >= |aggregator sum|       (was |6ae2| >= |6b26|, duty 0.337)
No cal changes, no authority change, no new code, no length change.  Read-only.

This script computes what each duty MUST read for each candidate r24 gain arm, so the drive can be scored
against a number written down BEFORE it.  r24 is built in closed form at 1 kHz from the measured 0x18F bar,
T from the CAN-427 tap; the aggregator is NOT on the wire so bit 5 is predicted from T + r24 alone (a lower
bound on |sum|, hence an UPPER bound on bit 5's duty -- stated as such).

Arms in play (FUN_0003aa2c, verified from the image):
    gp-0x671d != 0            -> 0xC6442 = 1024        (a fault-debounce arm; the 7 Hz analysis's inversion case)
    gate == 0, rate arm       -> 0xC6440 = 2048  or Honda's LERP 2150-3072
    gate != 0 (engaged, flown)-> 0xC6446 = 5244
Run: python v282_prereg_duty.py
"""
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
V280 = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
ROUTES = ("r34", "r33", "r32")
OUT = []


def pr(s=""):
    print(s)
    OUT.append(s)


def rolling_low(x, half, q=2.0):
    n = len(x)
    cen = np.arange(0, n, max(1, half // 2))
    v = np.array([np.percentile(x[max(0, c - half):min(n, c + half + 1)], q) for c in cen])
    return np.interp(np.arange(n), cen, v)


def dejitter(t, P0, half):
    n = len(t)
    i = np.arange(n)
    r = t - i * P0
    env = rolling_low(r, half)
    step = np.r_[0.0, np.diff(env)]
    drops = np.round(np.cumsum(np.where(np.abs(step) > 0.6 * P0, step, 0.0)) / P0).astype(int)
    k = i + drops
    r2 = t - k * P0
    env2 = rolling_low(r2, half)
    P = P0 + (env2[-1] - env2[0]) / max(1, (k[-1] - k[0]))
    r3 = t - k * P
    env3 = rolling_low(r3, half)
    return k, P, k * P + env3


def grid_from(k, x, kmax):
    g = np.full(kmax + 1, np.nan)
    g[k] = x
    have = ~np.isnan(g)
    g[~have] = np.interp(np.flatnonzero(~have), np.flatnonzero(have), g[have])
    return g, have


def load(tag):
    D = dict(np.load(os.path.join(V280, tag + ".npz")))
    k18, P18, tn18 = dejitter(D["t18"], 0.01, 100)
    k1ab, P1ab, tn1ab = dejitter(D["t1ab"], 0.02, 50)
    ke4, Pe4, tne4 = dejitter(D["te4"], 0.01, 100)
    K = int(k18[-1])
    g = dict(tag=tag)
    g["t"] = np.interp(np.arange(K + 1), k18, tn18 - k18 * P18) + np.arange(K + 1) * P18
    g["bar"], have = grid_from(k18, D["tq"].astype(float) * 1.024, K)
    g["rate"], _ = grid_from(k18, D["rate"].astype(float), K)
    g["sca"], _ = grid_from(k18, D["sca"].astype(float), K)
    g["req"] = np.interp(g["t"], tne4, D["req"].astype(float)) > 0.5
    g["ang"] = np.interp(g["t"], D["t14"], D["ang"].astype(float))
    g["vego"] = np.interp(g["t"], D["tcs"], D["vego"].astype(float))
    g["eng"] = (g["sca"] > 0.5) & g["req"] & have
    fld = ((D["b0"].astype(int) & 3) << 8) | D["b1"].astype(int)
    Tm = np.where(fld >= 512, -1.0, 1.0) * (fld & 511) * 8.0
    g["T"] = np.interp(g["t"], tn1ab, Tm)     # 50 Hz held onto the 100 Hz frame axis
    return g


def r24_series(bar100, gain):
    """r24 at 1 kHz from the decompiled arithmetic, then decimated back to the 100 Hz frame axis.
       gp-0x4f60 = bar (same sign; the builder negates and the cache negates back)
       gp-0x4f62 = 0.5*(x[n] - x[n-4]) at 1 kHz, clamp +-5120
       r24 = clamp( -deadband( (gp-0x4f62 * gain)>>10, 3 ), +-8192 )    [gp-0x6752 = -1, confirmed on the wire]"""
    x = signal.resample_poly(bar100 - bar100[0], 10, 1) + bar100[0]
    d = np.zeros_like(x)
    d[4:] = 0.5 * (x[4:] - x[:-4])
    d = np.clip(d, -5120, 5120)
    s = np.trunc(d * gain / 1024.0)
    s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s) * 3)
    r = np.clip(-s, -8192, 8192)
    return r[::10][:len(bar100)]


def runs(mask, min_len):
    dd = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)) if b - a >= min_len]


STRATA = [
    ("creep engaged hands-off (v 1-3, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
    ("creep engaged hands-off (v 1-6, |bar|<400)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
    ("loaded high-angle engaged (v 2-9, |ang|>30)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30)),
    ("all engaged", lambda g: g["eng"]),
]
GAINS = (5244.0, 3072.0, 2048.0, 1024.0, 512.0)


def main():
    gs = {t: load(t) for t in ROUTES}
    pr("=" * 116)
    pr("V282 PRE-REGISTRATION -- predicted duty of the two repointed cave comparator bits, on V280 rev 2")
    pr("data (r32/r33/r34).  bit6 = |r24| >= |T| ; bit5 = |r24| >= |T + r24| (upper bound: the real")
    pr("aggregator carries more lanes, so the true bit-5 duty is AT OR BELOW the number printed).")
    pr("=" * 116)
    for name, fn in STRATA:
        pr("")
        pr("  %s" % name)
        pr("    %-28s %10s %10s %12s %12s %10s" %
           ("0xC6446 arm", "bit6 duty", "bit5 duty", "|r24| p50", "|T| p50", "n frames"))
        for gain in GAINS:
            b6 = []
            b5 = []
            r_all = []
            t_all = []
            for t in gs:
                g = gs[t]
                m = fn(g)
                if m.sum() < 200:
                    continue
                r = r24_series(g["bar"], gain)
                T = g["T"]
                b6.append((np.abs(r) >= np.abs(T))[m])
                b5.append((np.abs(r) >= np.abs(T + r))[m])
                r_all.append(np.abs(r)[m])
                t_all.append(np.abs(T)[m])
            if not b6:
                pr("    %-28s   NO DATA" % ("%.0f" % gain))
                continue
            b6 = np.concatenate(b6)
            b5 = np.concatenate(b5)
            lbl = {5244.0: "5244  (flown, engaged arm)", 3072.0: "3072  (Honda LERP top)",
                   2048.0: "2048  (0xC6440 stock arm)", 1024.0: "1024  (0xC6442 fault arm)",
                   512.0: "512   (the 7 Hz proposal)"}[gain]
            pr("    %-28s %10.3f %10.3f %12.0f %12.0f %10d" %
               (lbl, b6.mean(), b5.mean(), np.median(np.concatenate(r_all)),
                np.median(np.concatenate(t_all)), len(b6)))
    pr("")
    pr("  READING: bit 6's duty separates the arms by a wide margin in every stratum, so ONE drive with")
    pr("  any engaged creep in it reads the arm off directly.  That is the number the whole grinding")
    pr("  verdict rests on and it is not otherwise obtainable.")
    with open(os.path.join(SCR, "v282_prereg_duty.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")


main()
