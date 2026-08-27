#!/usr/bin/env python3
"""Near-Nyquist census: does the V62 torsion bar alternate sample-to-sample, and is that NEW?

Route 37 windows carry sharp peaks at 47-50 Hz against a ~101 Hz sample rate (Nyquist 50.7). Two
samples per cycle is the limit of what CAN can represent, so:

  * the TRUE frequency is not determined -- a measured f is indistinguishable from k*fs +/- f;
  * but "the reported torsion-bar value alternates sign every sample" is itself a measurable,
    alias-free FACT about the signal, and it is what a grinding driver would feel.

Metrics, all computed identically on every cached route:
  NYQFRAC  fraction of window power above 0.90*Nyquist        (spectral)
  ALT      lag-1 autocorrelation of tq (a perfect alternation gives -1)  (time domain, no FFT)
  ZCR      zero-crossings of the mean-removed high-passed signal, per second
Two independent methods (spectral + time domain) because a near-Nyquist claim is exactly where a
single FFT-based method is least trustworthy.
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
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402

NF = 256
ROUTES = [
    ("2b", C.ROOT / "_scratch/cache/r2b", "r2bs", [0, 1, 2, 11, 12, 13]),
    ("2c", C.ROOT / "_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("31 (V61)", C.ROOT / "_scratch/cache/r31", "r31s", [0, 1, 2, 3]),
    ("35 (V64=V59)", C.ROOT / "_scratch/cache/r35", "r35s", [0, 1, 2]),
    ("37 (V62)", C.ROOT / "_scratch/cache/r37", "r37s", list(range(1, 15))),
]


def hp(x, fs, fc=30.0):
    X = np.fft.rfft(x - x.mean())
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[f < fc] = 0
    return np.fft.irfft(X, n=len(x))


def scan(cache, pfx, segs):
    out = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        x = d["tq"]
        f = np.fft.rfftfreq(NF, 1 / fs)
        nyq = fs / 2
        for i in range(0, len(x) - NF + 1, 64):
            seg = x[i:i + NF]
            P = C.periodogram(seg, fs, NF)
            if P is None:
                continue
            tot = P[1:].sum()
            hi = P[f >= 0.90 * nyq].sum()
            y = seg - seg.mean()
            r1 = float(np.dot(y[:-1], y[1:]) / (np.dot(y, y) + 1e-30))
            z = hp(seg, fs)
            zc = float((np.diff(np.sign(z)) != 0).sum()) * fs / NF / 2.0
            out.append((hi / max(tot, 1e-30), r1, zc,
                        float(np.mean(d["cs_v"][i:i + NF])),
                        float(np.mean(d["cc_lat"][i:i + NF] > 0.5)), s, float(d["t"][i]), fs))
    return out


def main():
    print("NEAR-NYQUIST CENSUS on the torsion-bar channel (NFFT=256, hop=64)\n")
    print(f"{'route':14s} {'nwin':>5s} {'Nyq':>6s} | {'NYQFRAC p50':>11s} {'p90':>7s} {'p99':>7s} "
          f"{'max':>7s} | {'n>0.10':>7s} {'n>0.25':>7s} | {'lag1 min':>9s} {'n<-0.3':>7s} | "
          f"{'ZCR p99':>8s} {'max':>7s}")
    store = {}
    for name, cache, pfx, segs in ROUTES:
        r = scan(cache, pfx, segs)
        store[name] = r
        if not r:
            continue
        nf = np.array([a[0] for a in r])
        r1 = np.array([a[1] for a in r])
        zc = np.array([a[2] for a in r])
        print(f"{name:14s} {len(r):5d} {r[0][7]/2:6.2f} | {np.median(nf):11.4f} "
              f"{np.percentile(nf,90):7.4f} {np.percentile(nf,99):7.4f} {nf.max():7.4f} | "
              f"{int((nf>0.10).sum()):7d} {int((nf>0.25).sum()):7d} | {r1.min():9.3f} "
              f"{int((r1<-0.3).sum()):7d} | {np.percentile(zc,99):8.1f} {zc.max():7.1f}")

    print("\nRATE per 1000 windows (exposure differs 3-5x between routes, so counts alone mislead):")
    print(f"{'route':14s} {'NYQFRAC>0.10':>13s} {'NYQFRAC>0.25':>13s} {'lag1<-0.3':>11s}")
    for name, r in store.items():
        if not r:
            continue
        nf = np.array([a[0] for a in r])
        r1 = np.array([a[1] for a in r])
        n = len(r)
        print(f"{name:14s} {1000*(nf>0.10).sum()/n:13.2f} {1000*(nf>0.25).sum()/n:13.2f} "
              f"{1000*(r1<-0.3).sum()/n:11.2f}")

    print("\nWorst windows on route 37 by NYQFRAC (where the bar alternates most):")
    r37 = sorted(store["37 (V62)"], key=lambda a: -a[0])[:20]
    print(f"   {'seg':>3s} {'t0':>7s} {'NYQFRAC':>8s} {'lag1':>7s} {'ZCR':>7s} {'v':>6s} "
          f"{'lat':>4s}")
    for a in r37:
        print(f"   {a[5]:3d} {a[6]:7.2f} {a[0]:8.4f} {a[1]:7.3f} {a[2]:7.1f} {a[3]:6.2f} "
              f"{a[4]:4.2f}")


if __name__ == "__main__":
    main()
