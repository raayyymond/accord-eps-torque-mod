# -*- coding: utf-8 -*-
"""rsn_r79_twist.py -- EVIDENCE on route 79 (V298 flown): the hands-off reaction-twist tail that the V299 thresholds
sit on.  carState (100 Hz, the fork's own inputs): steeringTorque raw (|word| = raw x 1.024), steeringPressed,
steeringAngleDeg / RateDeg, vEgo; carControl latActive.  Hands-off = latActive & not pressed & no press within +-1 s.
Reads: |raw| tail by speed band; per latActive-minute rates of (a) instant > 1200 raw (G4 hard path), (b) > 600 raw
held >= 8 frames (G4 debounce), (c) > 1229 words (V299 freeze) vs > 512 words (V298 freeze); and P(> 1200 | |alpha|
bin) with alpha = d(rate)/dt, so the higher wheel accelerations of config B can be read off the measured curve.
ANALYSIS ONLY.  Vectorised; < 5 s."""
import sys
import time
from pathlib import Path

import numpy as np

T0 = time.perf_counter()
KIT = Path(__file__).resolve().parents[5]
F = np.load(KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280" / "r79_fork.npz")
t = F["t_cs"].astype(float)
raw = F["cs_tq"].astype(float)
press = F["cs_press"].astype(bool)
v = F["cs_vego"].astype(float)
rate = F["cs_rate"].astype(float)
lat = np.interp(t, F["t_cc"].astype(float), F["cc_latActive"].astype(float)) > 0.5
dt = np.median(np.diff(t))
k = int(round(1.0 / dt))
pw = np.convolve(press.astype(float), np.ones(2 * k + 1), "same") > 0
ho = lat & ~pw
a = np.gradient(rate, t)
a = np.convolve(a, np.ones(3) / 3, "same")
minutes = ho.sum() * dt / 60.0
print(f"dt {dt*1000:.1f} ms; latActive {lat.sum()*dt/60:.1f} min; hands-off {minutes:.1f} min")


def runs_ge(m, n):
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    s, e = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return int(np.count_nonzero((e - s) >= n))


ar = np.abs(raw)
print("| speed band | hands-off min | |raw| p90 | p99 | p99.9 | max | >1200 raw entries /min | >600 raw held 8 frames /min | >1229 w (V299 frz) entries /min | >512 w (V298 hard) entries /min |")
print("|---|---|---|---|---|---|---|---|---|---|")
for lo, hi in ((0, 5), (5, 8), (8, 12.5), (12.5, 40)):
    m = ho & (v >= lo) & (v < hi)
    mins = m.sum() * dt / 60.0
    if mins < 0.2:
        continue
    x = ar[m]
    e1200 = np.count_nonzero(np.diff((ar > 1200) & m) == 1)
    e600 = runs_ge((ar > 600) & m, 8)
    e1229 = np.count_nonzero(np.diff((ar * 1.024 > 1229) & m) == 1)
    e512 = np.count_nonzero(np.diff((ar * 1.024 > 512) & m) == 1)
    print(f"| {lo}-{hi} m/s | {mins:.1f} | {np.percentile(x, 90):.0f} | {np.percentile(x, 99):.0f} | "
          f"{np.percentile(x, 99.9):.0f} | {x.max():.0f} | {e1200 / mins:.2f} | {e600 / mins:.2f} | {e1229 / mins:.2f} | {e512 / mins:.1f} |")
print("\nP(|raw| > 1200) and P(|raw| > 600) vs |alpha| (hands-off, v < 8 m/s):")
m8 = ho & (v < 8)
for lo, hi in ((0, 100), (100, 300), (300, 600), (600, 1000), (1000, 2000), (2000, 1e9)):
    s = m8 & (np.abs(a) >= lo) & (np.abs(a) < hi)
    if s.sum() < 50:
        print(f"  |alpha| {lo}-{hi}: n {s.sum()}")
        continue
    print(f"  |alpha| {lo:.0f}-{hi:.0f} deg/s^2: n {s.sum():6d}  P>1200 {np.mean(ar[s] > 1200):.4f}  P>600 {np.mean(ar[s] > 600):.3f}  "
          f"|raw| p99 {np.percentile(ar[s], 99):.0f}  |rate| p50 {np.median(np.abs(rate[s])):.0f}")
print(f"wall {time.perf_counter() - T0:.1f} s")
