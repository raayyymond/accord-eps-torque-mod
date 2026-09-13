# -*- coding: utf-8 -*-
"""tau_bandcheck.py -- does the answer depend on the ANALYSIS BAND?  taumeasure, 2026-09-13.
Analysis only: builds nothing, sends nothing, flashes nothing, commits nothing.

The obvious attack on a band-passed cross-correlation: the path is not a pure delay (it carries a
first-order lag as well), so the lag you READ depends on which frequencies dominate the correlation.
If tau moved a lot with the band, the 0.2-2 Hz choice would be doing the work rather than the car.

This re-runs the same NCC on four bands and on the UNFILTERED (lagd-style, 5-tap Gaussian only) pair,
per route and speed band, on the EPS actuator channel.  A spread of a few tens of ms is expected and
harmless -- it is the first-order lag showing.  A spread comparable to tau itself would invalidate the
headline.  Also reports lagd's own smoothing for direct comparability.

Run: python rlog-tools/studies/grind/tau_bandcheck.py
Writes _scratch/tau_bandcheck.{txt,json}
"""
import json
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "tau")
sys.path.insert(0, HERE)
from tau_identify import load, runs, pooled_ncc, boot, FS, MINSTRETCH, MAX_LAG  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANDS = [(3.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 99.0)]
FBANDS = [(0.1, 1.0), (0.2, 2.0), (0.3, 1.5), (0.5, 3.0)]
ROUTES = [("r39", "V282"), ("r6c", "V282"), ("r6d_v292", "V292"), ("r6e_v292", "V292"),
          ("r6f_v292", "V292"), ("r35", "V281r3")]
CHANS = [("y_steer", "EPS actuator"), ("y_yaw", "full lateral (gyro)")]
OUT, RESULTS = [], []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def bp(x, lo, hi):
    b, a = signal.butter(4, [lo / (FS / 2), hi / (FS / 2)], btype="band")
    return signal.filtfilt(b, a, x)


def gauss5(x):
    """lagd's own smoothing: 5-tap Gaussian, sigma 1.0, no band-pass (lagd.py SMOOTH_K/SMOOTH_SIGMA)."""
    i = np.arange(5) - 2
    w = np.exp(-0.5 * (i / 1.0) ** 2); w /= w.sum()
    return np.convolve(x, w, mode="same")


def main():
    pr("=" * 132)
    pr("BAND SENSITIVITY of the NCC lag.  Same stretches, same estimator, four analysis bands + lagd's own")
    pr("(5-tap Gaussian, NO band-pass, DC left in).  A spread of a few tens of ms is the first-order lag showing;")
    pr("a spread comparable to tau itself would mean the band choice is doing the work.")
    pr("=" * 132)
    for ck, clab in CHANS:
        pr("")
        pr("### CHANNEL: %s" % clab)
        pr("%-10s %-8s %-9s %6s | %s %10s | %s"
           % ("route", "build", "band m/s", "s", "".join("%11s" % ("%g-%gHz" % f) for f in FBANDS),
              "lagd-style", "spread"))
        for tag, build in ROUTES:
            if not os.path.exists(os.path.join(CACHE, tag + "_lat.npz")):
                continue
            g = load(tag)
            for lo, hi in BANDS:
                m = g["ok"] & (g["v"] >= lo) & (g["v"] < hi)
                rr = runs(m, MINSTRETCH)
                if not rr:
                    continue
                vals = []
                for flo, fhi in FBANDS:
                    segs = [(bp(g["u_curv"][a:b], flo, fhi), bp(g[ck][a:b], flo, fhi)) for a, b in rr]
                    vals.append(1e3 * pooled_ncc(segs, 0.0, MAX_LAG)[0])
                raw = [(gauss5(g["u_curv"][a:b]), gauss5(g[ck][a:b])) for a, b in rr]
                lagd_v = 1e3 * pooled_ncc(raw, 0.0, MAX_LAG)[0]
                spread = max(vals) - min(vals)
                pr("%-10s %-8s %-9s %6.0f | %s %10.1f | %6.1f ms"
                   % (tag, build, "%g-%g" % (lo, hi), sum(b - a for a, b in rr) / FS,
                      "".join("%11.1f" % v for v in vals), lagd_v, spread))
                RESULTS.append(dict(route=tag, build=build, chan=ck, band="%g-%g" % (lo, hi),
                                    seconds=sum(b - a for a, b in rr) / FS,
                                    by_fband={"%g-%g" % f: v for f, v in zip(FBANDS, vals)},
                                    lagd_style=lagd_v, spread=spread))
    with open(os.path.join(HERE, "_scratch", "tau_bandcheck.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT))
    with open(os.path.join(HERE, "_scratch", "tau_bandcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(RESULTS, fh, indent=1, default=float)


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "_scratch"), exist_ok=True)
    main()
