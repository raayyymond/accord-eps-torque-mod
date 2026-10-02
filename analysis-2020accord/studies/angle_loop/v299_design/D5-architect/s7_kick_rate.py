# -*- coding: utf-8 -*-
r"""s7_kick_rate.py -- D5-architect.  How often would (b)'s BREAKAWAY KICK have fired on route 79?  The kick fires when
the fork's filtered setpoint slope (5-frame boxcar + 30 ms pole of the applied setpoint co_ang) exceeds +-thr deg/s with
a sign different from the last one that did.  Rate per minute of latActive time by speed band, for thr 0.5 / 1 / 2
deg/s, and the share of kicks landing on 'straights' (|setpoint| < 3 deg).  Fork cache only, vectorised.  Wall printed."""
import sys, time
from pathlib import Path
import numpy as np
from scipy.signal import lfilter
t0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "v298_flight"))
import m3_lane as M  # noqa: E402
F = np.load(M.CACHE / "r79_fork.npz")
tco = F["t_co"]
jc = np.clip(np.searchsorted(F["t_cc"], tco, side="right") - 2, 0, len(F["t_cc"]) - 1)
lat = F["cc_latActive"][jc].astype(bool)
co = F["co_ang"].astype(float)
v = np.r_[F["cs_vegoraw"][:1], F["cs_vegoraw"][:-1]].astype(float)
sl = np.r_[np.zeros(5), (co[5:] - co[:-5]) / 0.05]
a = np.exp(-0.01 / 0.03)
sl = lfilter([1 - a], [1, -a], sl)
for thr in (0.5, 1.0, 2.0):
    sg = np.where(np.abs(sl) > thr, np.sign(sl), 0.0)
    sg = np.where(lat, sg, 0.0)
    nz = np.flatnonzero(sg)
    prev = np.r_[0.0, sg[nz][:-1]]
    fire = np.zeros(len(sg), bool)
    fire[nz[sg[nz] != prev]] = True
    out = []
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 99)):
        m = lat & (v >= lo) & (v < hi)
        out.append("%d-%d m/s %.1f/min (straight %.0f%%)" % (lo, hi, fire[m].sum() / max(m.sum() / 6000, 1e-9),
                                                             100 * (fire[m] & (np.abs(co[m]) < 3)).sum() / max(fire[m].sum(), 1)))
    print("thr %.1f deg/s: " % thr + " | ".join(out))
print("wall %.1f s" % (time.time() - t0))

# ---- the DEBOUNCED trigger: 0.5 s boxcar slope of the applied setpoint, |slope| > thr, the sign held >= 30 frames,
#      fires once per new sign (the drift-onset kick)
t1 = time.time()
sl50 = np.r_[np.zeros(50), (co[50:] - co[:-50]) / 0.5]
for thr in (0.5, 1.0):
    sg = np.where(lat & (np.abs(sl50) > thr), np.sign(sl50), 0.0)
    k = np.arange(len(sg))
    chg = np.r_[True, sg[1:] != sg[:-1]]
    start = np.maximum.accumulate(np.where(chg, k, 0))
    held = (sg != 0) & (k - start >= 30)
    nz = np.flatnonzero(held)
    prev = np.r_[0.0, sg[nz][:-1]]
    fire = np.zeros(len(sg), bool)
    fire[nz[(sg[nz] != prev) | (np.r_[True, np.diff(nz) > 1])]] = True
    out = []
    for lo, hi in ((0, 5), (5, 10), (10, 20), (20, 99)):
        m = lat & (v >= lo) & (v < hi)
        out.append("%d-%d m/s %.1f/min (straight %.0f%%)" % (lo, hi, fire[m].sum() / max(m.sum() / 6000, 1e-9),
                                                             100 * (fire[m] & (np.abs(co[m]) < 3)).sum() / max(fire[m].sum(), 1)))
    print("DEBOUNCED thr %.1f deg/s (0.5 s slope, sign held 0.3 s): " % thr + " | ".join(out))
print("wall (debounced part) %.2f s" % (time.time() - t1))
