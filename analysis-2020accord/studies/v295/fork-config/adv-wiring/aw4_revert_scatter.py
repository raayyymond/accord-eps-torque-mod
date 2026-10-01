# -*- coding: utf-8 -*-
"""aw4_revert_scatter.py -- ADV "wiring+observability", part (c)/W10: can ONE drive decide the pre-registered REVERT
signature of V295-FORK-CONFIG-r2 s7 without false alarms?  Uses r71b (drive (1)'s reference) as the NO-CHANGE world:
two pseudo-drives drawn from r71b's own 5 s blocks (a within-route bootstrap = a LOWER bound on real drive-to-drive scatter).

 DART   'darty on-centre: straight-road 1-5 Hz wheel rate > x1.3 drive (1)'   -> rms of the 1-5 Hz band of the wheel rate
        (x_fw/8, 0.125 deg/s) on straight (|desired lat accel| < 0.2 m/s^2), hands-off, laterally engaged frames
 WEAVE  'a 0.2-1.5 Hz straight-road weave at >= 15 m/s (~0.6 deg p-p)'        -> p-p of the 0.2-1.5 Hz band of the wheel
        angle over 10 s straight hands-off windows at >= 15 m/s: is 0.6 deg above r71b's own background?
 Turn-hold / tracking oversteer limits: taken from ADV-B b7 (not recomputed), false-alarm odds by a normal approximation
        [BELIEF: approximation].
ANALYSIS ONLY.
"""
import os
import sys

import numpy as np
from scipy.signal import butter, sosfiltfilt

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"))
import r71b_cache as R  # noqa: E402
from scipy.stats import norm  # noqa: E402

LOG = []


def pr(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


D = R.load(with_raw=False)
G = R.grid100(D)
fs = 100.0
rate = np.asarray(G["x_fw"], float) / 8.0
ang = np.nan_to_num(G["cs_angle"])
v = np.nan_to_num(G["cs_vego"])
plan = np.nan_to_num(G["ctl_des_curv"]) * v ** 2
eng = np.asarray(G["eng"], bool)
pressed = np.nan_to_num(G["cs_pressed"]) > 0.5
prd = np.convolve(pressed.astype(int), np.ones(101, int), "same") > 0          # +-0.5 s dilation
HO = eng & ~prd
straight = np.abs(plan) < 0.2
bp15 = sosfiltfilt(butter(4, [1.0, 5.0], "bandpass", fs=fs, output="sos"), rate)
bpw = sosfiltfilt(butter(2, [0.2, 1.5], "bandpass", fs=fs, output="sos"), ang)
rng = np.random.default_rng(20260930)


def blocks(mask, n=500):
    idx = np.flatnonzero(mask)
    br = np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1)
    out = []
    for r in br:
        for i in range(0, len(r) - n + 1, n):
            out.append(r[i:i + n])
    return out


def pseudo(bl, secs):
    k = max(1, int(secs / 5))
    return np.concatenate([bl[q] for q in rng.integers(0, len(bl), k)])


pr("DART: 1-5 Hz wheel-rate rms, straight (|plan|<0.2) hands-off engaged; ratio of two r71b pseudo-drives (NO change)")
for lo, hi, name in ((0, 8, "0-8"), (8, 15, "8-15"), (15, 22, "15-22"), (22, 40, "22+"), (15, 40, ">=15"), (0, 40, "all")):
    m = HO & straight & (v >= lo) & (v < hi)
    bl = blocks(m)
    if len(bl) < 4:
        pr("   %-6s %4.0f s straight hands-off: too few 5 s blocks (%d)" % (name, m.sum() / 100, len(bl)))
        continue
    base = np.sqrt(np.mean(bp15[m] ** 2))
    row = []
    for secs in (30, 60, 120):
        rr = []
        for _ in range(2000):
            a, b = pseudo(bl, secs), pseudo(bl, secs)
            rr.append(np.sqrt(np.mean(bp15[b] ** 2)) / np.sqrt(np.mean(bp15[a] ** 2)))
        rr = np.array(rr)
        row.append("%3d s: 90%% [x%.2f, x%.2f], P(ratio > 1.3) %.2f" % (secs, *np.percentile(rr, [5, 95]), np.mean(rr > 1.3)))
    pr("   %-6s %4.0f s (%3d blocks), r71b %.2f deg/s | %s" % (name, m.sum() / 100, len(bl), base, " | ".join(row)))

pr("\nWEAVE: p-p of the 0.2-1.5 Hz band of the wheel ANGLE over 10 s straight hands-off windows (r71b background)")
for lo, hi, name in ((15, 22, "15-22"), (22, 40, "22+"), (15, 40, ">=15")):
    m = HO & straight & (v >= lo) & (v < hi)
    wins = blocks(m, n=1000)
    if not wins:
        pr("   %-6s no 10 s straight window" % name)
        continue
    pp = np.array([bpw[w].max() - bpw[w].min() for w in wins])
    rms = np.array([np.sqrt(np.mean(bpw[w] ** 2)) for w in wins])
    pr("   %-6s %2d windows: p-p deg p10 %.2f p50 %.2f p90 %.2f max %.2f ; rms p50 %.3f ; windows with p-p >= 0.6 deg: %d/%d"
       % (name, len(wins), *np.percentile(pp, [10, 50, 90]), pp.max(), np.median(rms), int(np.sum(pp >= 0.6)), len(wins)))
    # a sustained 0.6 deg p-p sinusoid (the predicted light_b hunt, 0.2-0.9 Hz) ADDED to each window: detectable by amplitude?
    for f0 in (0.3, 0.6, 0.9):
        t = np.arange(1000) / fs
        hunt = 0.3 * np.sin(2 * np.pi * f0 * t)
        pp2 = np.array([(bpw[w] + hunt).max() - (bpw[w] + hunt).min() for w in wins])
        pr("          + a 0.6 deg p-p %.1f Hz hunt: p-p p50 %.2f (x%.2f of background p50) ; windows whose p-p exceeds the "
           "background p90: %.2f" % (f0, np.median(pp2), np.median(pp2) / np.median(pp), np.mean(pp2 > np.percentile(pp, 90))))

pr("\nOVERSTEER limits vs ADV-B b7 no-change d-v-d 90 % bands (normal approx, sigma = half-width / 1.645) [BELIEF: approx]")
# (band, r71b value, predicted r2alt value, d-v-d 90% half-width at the exposure r71b gives, exposure)
rows = [("TRACK 22+ (>1.05)", 0.9235, 0.965, 0.080, "60 s"), ("TRACK 15-22 (>1.05)", 0.8304, 0.925, 0.061, "120 s"),
        ("HOLD 0-5 (>1.10)", 0.9609, 0.9609, 0.260, "60 s"), ("HOLD 5-10 (>1.10)", 0.7722, 0.815, 0.154, "120 s"),
        ("HOLD 15-22 (>1.10)", 0.6725, 0.79, 0.149, "120 s"), ("HOLD 22+ (>1.10)", 0.9428, 0.975, 0.240, "60 s")]
p_none = []
for name, base, pred, hw, ex in rows:
    s = hw / 1.645
    thr = 1.05 if name.startswith("TRACK") else 1.10
    p0 = 1 - norm.cdf((thr - base) / s)
    p1 = 1 - norm.cdf((thr - pred) / s)
    p_none.append(p1)
    pr("   %-20s r71b %.3f pred %.3f  d-v-d +-%.3f (%s): P(fires) under NO change %.3f ; under r2alt as predicted %.3f"
       % (name, base, pred, hw, ex, p0, p1))
pr("   P(at least one oversteer limit fires on a drive where r2alt behaves EXACTLY as predicted) ~ %.2f (independence assumed)"
   % (1 - np.prod([1 - p for p in p_none])))
open(os.path.join(HERE, "out", "aw4_revert_scatter_out.txt"), "w", encoding="utf-8").write("\n".join(LOG) + "\n")
