#!/usr/bin/env python3
"""THE CRUX, VERIFIED A SECOND WAY: mean periodograms per speed bin, no argmax anywhere.

🛑 WHY THIS FILE EXISTS. `studies/highway/highway_order_test.py` reported the median per-window prominence-argmax
of the 30-49.5 Hz band and got ~42 Hz in EVERY speed bin, which reads as "a fixed mode". That
estimator has a bias I had to check before believing it: on a window with NO line, the argmax
scatters across the band and its MEDIAN lands near the band centre. The band centre of 30-49.5 is
39.75 Hz -- close enough to 42 that the "fixed mode" could be the estimator, not the car.

The check: average the periodogram over hundreds of windows per speed bin and read the peak of the
AVERAGED spectrum. Averaging suppresses the scatter that biases an argmax, and a line that is
really there survives it. No band-limited argmax is used to produce any number below.

A first pass on IMU `ay` already showed the two are NOT the same:
    23-27 m/s  the 30-50 Hz mean spectrum rises MONOTONICALLY to the band edge -- no 42 Hz peak
    30-35 m/s  a clear local peak at 42.2 Hz
so the "fixed at 42 Hz in every speed bin" claim from the argmax is at least partly the estimator.

Usage:  python studies/highway/highway_meanspec.py
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import _grind2_lib as G          # noqa: E402
import _r47_imu_lib as I         # noqa: E402
import highway_event_hunt as H   # noqa: E402

OUT = HERE / "_scratch/out/_hwy_meanspec.json"
NFFT = 256
CIRC = H.CIRC
VB = [(22, 25), (25, 28), (28, 31), (31, 35)]


def peak_of_mean(f, P, lo, hi):
    """Peak of an AVERAGED spectrum, with its prominence over the band's own local floor.
    No per-window argmax is involved, so the band-centre bias does not apply."""
    m = (f >= lo) & (f <= hi)
    idx = np.flatnonzero(m)
    j = idx[int(np.argmax(P[idx]))]
    near = (np.abs(f - f[j]) <= 6.0) & (np.abs(f - f[j]) > 1.5) & (f > 0.3)
    floor = float(np.median(P[near])) if near.sum() >= 5 else np.nan
    if 0 < j < len(P) - 1:
        y0, y1, y2 = (np.log(P[j - 1]), np.log(P[j]), np.log(P[j + 1]))
        den = y0 - 2 * y1 + y2
        d = 0.5 * (y0 - y2) / den if den != 0 else 0.0
        f0 = f[j] + np.clip(d, -0.5, 0.5) * (f[1] - f[0])
    else:
        f0 = f[j]
    return float(f0), (float(P[j] / floor) if floor and floor > 0 else np.nan)


def accumulate(chan):
    """{(route, vbin): (f, mean P, n)} for one channel, engaged only."""
    acc = {}
    for rt, cd, pfx, segs, bld, kd in H.ROUTES:
        for s in segs:
            dc = H.load_seg(cd, pfx, s)
            if dc is None:
                continue
            fsc = 1.0 / float(np.median(np.diff(dc["t"])))
            v = np.abs(dc["cs_v"])
            lat = (dc["cc_lat"] > 0.5).astype(float)
            if chan == "bar":
                u, odr, tt = np.asarray(dc["tq"], float), fsc, dc["t"]
                vi, li = v, lat
            else:
                p = ROOT / cd / f"{pfx}{s}_imu.npz"
                if not p.exists():
                    continue
                di = dict(np.load(p))
                g = chan[0]
                u, odr, _, tt = I.uniform(di["at"] if g == "a" else di["gt"], di[chan])
                vi = I.lerp(tt, dc["t"], v)
                li = I.hold(tt, dc["t"], lat)
            f = np.fft.rfftfreq(NFFT, 1 / odr)
            for i in range(0, len(u) - NFFT + 1, NFFT // 2):
                sl = slice(i, i + NFFT)
                sp = float(np.mean(vi[sl]))
                if np.mean(li[sl]) < 0.9:
                    continue
                k = H.vbin(sp) if False else None
                for bi, (a, b) in enumerate(VB):
                    if a <= sp < b:
                        k = bi
                        break
                if k is None:
                    continue
                P = (G.periodogram(u[sl], odr, NFFT, True) if chan == "bar"
                     else I.periodogram(u[sl], odr, NFFT, True))
                if P is None:
                    continue
                key = (rt, k)
                if key not in acc:
                    acc[key] = [f, np.zeros(len(f)), 0]
                acc[key][1] += P
                acc[key][2] += 1
    return acc


def main():
    store = {}
    for chan in ("ay", "gz", "bar"):
        acc = accumulate(chan)
        G.hdr(f"MEAN PERIODOGRAM, channel {chan}, engaged. Peak of the AVERAGED spectrum in\n"
              f"30-49.5 Hz, per route and speed bin. 'ord3' is where wheel order 3 would sit.")
        print(f"    {'route':>6}{'Kd':>6}{'speed':>9}{'n win':>7}{'peak Hz':>10}{'prom':>8}"
              f"{'ord3':>8}{'ord2':>8}{'  peak 8-30':>12}{'prom':>7}{'ord1':>7}")
        rows = []
        for (rt, k) in sorted(acc, key=lambda x: (x[0], x[1])):
            f, P, n = acc[(rt, k)]
            if n < 40:
                continue
            P = P / n
            a, b = VB[k]
            vm = (a + b) / 2.0
            f0, pr = peak_of_mean(f, P, 30.0, 49.5)
            fl, pl = peak_of_mean(f, P, 8.0, 30.0)
            print(f"    {rt:>6}{H.KD[rt]:>6.2f}{f'{a}-{b}':>9}{n:>7}{f0:>10.2f}{pr:>8.2f}"
                  f"{3 * vm / CIRC:>8.2f}{2 * vm / CIRC:>8.2f}{fl:>12.2f}{pl:>7.2f}"
                  f"{vm / CIRC:>7.2f}")
            rows.append(dict(route=rt, kd=H.KD[rt], vbin=[a, b], n=n, f0=f0, prom=pr,
                             f_lo=fl, prom_lo=pl))
        store[chan] = rows
        # pooled over routes, which is the cleanest read of "does the line move with speed"
        print(f"\n    POOLED OVER ROUTES ({chan}):")
        print(f"    {'speed':>9}{'n win':>7}{'peak Hz':>10}{'prom':>8}{'ord3':>8}"
              f"{'  peak 8-30':>12}{'prom':>7}{'ord1':>7}")
        pooled = {}
        for (rt, k), (f, P, n) in acc.items():
            if k not in pooled:
                pooled[k] = [f, np.zeros(len(f)), 0]
            pooled[k][1] += P
            pooled[k][2] += n
        for k in sorted(pooled):
            f, P, n = pooled[k]
            if n < 40:
                continue
            P = P / n
            a, b = VB[k]
            vm = (a + b) / 2.0
            f0, pr = peak_of_mean(f, P, 30.0, 49.5)
            fl, pl = peak_of_mean(f, P, 8.0, 30.0)
            print(f"    {f'{a}-{b}':>9}{n:>7}{f0:>10.2f}{pr:>8.2f}{3 * vm / CIRC:>8.2f}"
                  f"{fl:>12.2f}{pl:>7.2f}{vm / CIRC:>7.2f}")
            store.setdefault(chan + "_pooled", []).append(
                dict(vbin=[a, b], n=n, f0=f0, prom=pr, f_lo=fl, prom_lo=pl))
        print("    prom = peak / its own local median floor. The kit treats > 4 as a real line;\n"
              "    the 8-30 Hz column is the POSITIVE CONTROL and must reproduce order 1.")
    OUT.write_text(json.dumps(store, indent=1, default=float))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
