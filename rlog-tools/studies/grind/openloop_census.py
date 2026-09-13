# -*- coding: utf-8 -*-
"""openloop_census.py -- the 2 s window census over ALL 35 cached routes, engaged and lateral-OFF.
Subagent `openloop`, 2026-09-13.  ANALYSIS ONLY.

This is the substrate for OPENLOOP-RING-DAMPING-2026-09-13.md.  It extends the 2026-09-10
engagement-gating scan (outerloop_openloop.py secA, 18 routes from cache/v280) to every route in
analysis-2020accord/_scratch/cache, because the DISENGAGED stratum is the rare one and the question
here lives entirely inside it.

Per window it records, on the SAME estimator the census reports use (GI.line_of / C20.bamp):
    f0_w, prom_w  -- most prominent line in 12-26 Hz on the driver-torque bar    (the record's gate)
    f0_h, prom_h  -- most prominent line in 17-23 Hz                             (the GRINDING object)
    f0_l, prom_l  -- most prominent line in 11-15 Hz                             (the road/plant line)
    A_<ch>_<band> -- band amplitude (sqrt(2)*std of a 4th-order zero-phase Butterworth) on
                     bar / rate (deg/s) / ang, in 18-22, 12-14.5 and the 26-34 neighbour band
    operating point: v, idx, bar rms, rate rms, steeringPressed fraction
Run: python openloop_census.py [--force]
"""
import os
import pickle
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import openloop_lib as L                       # noqa: E402
import _grind2_lib as G2                       # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
W, STEP = 200, 50
NFFT = 1024
BANDS = {"hi": (18.0, 22.0), "lo": (12.0, 14.5), "nb": (26.0, 34.0)}
CHANS = ("bar", "rate", "ang")
PKL = os.path.join(L.SCR, "openloop_census_rows.pkl")


def scan(tag):
    g = L.load(tag)
    n = g["n"]
    eng, off = g["eng"], g["off"]
    ch = {"bar": g["bar"], "rate": g["rate_dps"], "ang": g["ang"]}
    rows = []
    # pre-filter each channel ONCE per route per band -- 4th-order zero-phase Butterworth over the
    # whole route, then take the window's std.  Identical to C20.bamp per window except for edge
    # effects at the window boundary, which are common to both labels and both strata.
    filt = {}
    for cn, x in ch.items():
        for bn, (lo, hi) in BANDS.items():
            filt[(cn, bn)] = L.bp(x, lo, hi)
    for a in range(0, n - W, STEP):
        b = a + W
        e, o = eng[a:b], off[a:b]
        if e.all():
            lab = 1
        elif o.all():
            lab = 0
        else:
            continue
        bar = ch["bar"][a:b]
        f, P = signal.periodogram(bar - bar.mean(), fs=FS, window="hann", nfft=NFFT)
        sl = (f >= 4.0) & (f <= 34.0)
        fs_, Ps_ = f[sl], P[sl]
        R = G2.prom_spectrum(fs_, Ps_, 6.0, 1.5)
        f0w, pw = G2.locate(fs_, Ps_, 12.0, 26.0, R=R)
        f0h, ph = G2.locate(fs_, Ps_, 17.0, 23.0, R=R)
        f0l, pl = G2.locate(fs_, Ps_, 11.0, 15.0, R=R)
        if not np.isfinite(f0w):
            continue
        r = dict(tag=tag, eng=lab, a=a, f0w=float(f0w), pw=float(pw),
                 f0h=float(f0h), ph=float(ph), f0l=float(f0l), pl=float(pl),
                 v=float(np.median(g["vego"][a:b])), idx=float(np.median(g["idx"][a:b])),
                 barrms=float(np.std(bar)), raterms=float(np.std(g["wire"][a:b])),
                 press=float(np.mean(g["press"][a:b])))
        # the census's own A: band amplitude at the located line, f0w +- 2 Hz, on bar
        r["A"] = float(L.band(bar, f0w - 2.0, f0w + 2.0))
        for cn in CHANS:
            for bn in BANDS:
                r["A_%s_%s" % (cn, bn)] = float(np.sqrt(2.0) * np.std(filt[(cn, bn)][a:b]))
        rows.append(r)
    return rows


def main():
    force = "--force" in sys.argv
    if os.path.exists(PKL) and not force:
        print("cached:", PKL)
        return
    rows = []
    for t in L.routes():
        try:
            r = scan(t)
        except Exception as exc:
            print("  %-10s SKIPPED: %s" % (t, str(exc)[:80]), flush=True)
            continue
        ne = sum(x["eng"] for x in r)
        print("  scanned %-10s %-9s  engaged %6d  lateral-OFF %6d"
              % (t, L.BUILD.get(t, "?"), ne, len(r) - ne), flush=True)
        rows += r
    with open(PKL, "wb") as fh:
        pickle.dump(rows, fh, protocol=4)
    ne = sum(x["eng"] for x in rows)
    print("TOTAL %d windows: %d engaged, %d lateral-OFF, %d routes"
          % (len(rows), ne, len(rows) - ne, len(set(r["tag"] for r in rows))))


if __name__ == "__main__":
    main()
