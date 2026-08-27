#!/usr/bin/env python3
"""Route `35` (V64) supplementary arms -- the ones the 4.0 s / 2.56 s windows cannot reach.

Three jobs the main script (studies/sessions/r35/analyze_r35_v64_grinding.py) leaves open:

 1. FRAGMENTATION. The near-stationary high-effort manual arm holds 7.3 s of data on route 35 but
    no contiguous run reaches 2.56 s, so an NFFT=256 pass reports n=0. That is a WINDOW-LENGTH
    null, not a physical null, and reporting it as "absent" would be a fabrication. Re-run at
    NFFT=128 (1.28 s, 0.79 Hz bins) -- coarser, but it can see the arm at all.
 2. ENVELOPE. Convention 5 wants peak / p99 band envelope alongside prominence, since the mode is
    bursty and the median is dominated by quiet time. Measured in each build's OWN tracking band
    (its located f0 +/- 1.5 Hz), never a fixed 18-26 Hz -- V61 moved out of that band.
 3. THE MANUAL PICTURE, HEAD TO HEAD. V61's manual arms are the thing V64 has to be compared
    against, with identical code on both caches.
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _r31_common import (band_envelope, peak_prom, periodogram, runs_of,  # noqa: E402
                         sustained, stat)

POOLS = {"V59  route 2c": ROOT / "_scratch/cache/r2c", "V61  route 31": ROOT / "_scratch/cache/r31",
         "V64  route 35": ROOT / "_scratch/cache/r35"}
PFX = {"V59  route 2c": "r2cs*", "V61  route 31": "r31s*", "V64  route 35": "r35s*"}
# each build's own located engaged-creep f0, from studies/sessions/r35/analyze_r35_v64_grinding.py Method A
F0 = {"V59  route 2c": 21.18, "V61  route 31": 18.25, "V64  route 35": 21.30}


def segs(label):
    for f in sorted(POOLS[label].glob(PFX[label] + ".npz")):
        d = {k: v for k, v in np.load(f).items()}
        d["_fs"] = 1.0 / np.median(np.diff(d["t"]))
        d["_eff"] = np.abs(sustained(d["tq"], d["_fs"]))
        d["_gear"] = d["cs_gear"] if "cs_gear" in d else np.full(len(d["t"]), -1.0)
        yield f.stem, d


def scan(label, sel, nfft, lo=12.0, hi=30.0, band=None):
    """Per-window prominence/f0 and per-window p99 band envelope over disjoint runs."""
    f0s, prom, env, nrun, secs = [], [], [], 0, 0.0
    for _, d in segs(label):
        fs = d["_fs"]
        m = sel(d["cc_lat"] > 0.5, d["_gear"], d["cs_v"], d["_eff"])
        for a, b in runs_of(m, d["t"], nfft):
            nrun += 1
            secs += (b - a) / fs
            x = d["tq"][a:b]
            e = band_envelope(x, fs, *band) if band else None
            for i in range(0, len(x) - nfft + 1, nfft):
                P = periodogram(x[i:i + nfft], fs, nfft, True)
                if P is None:
                    continue
                fr = np.fft.rfftfreq(nfft, 1 / fs)
                pk, pr = peak_prom(fr, P, lo, hi)
                if np.isfinite(pk) and np.isfinite(pr):
                    f0s.append(pk); prom.append(pr)
                if e is not None:
                    env.append(float(np.percentile(e[i:i + nfft], 99)))
    return dict(f0=np.array(f0s), prom=np.array(prom), env=np.array(env),
                nrun=nrun, secs=secs, nwin=len(prom))


def line(name, r, width=32):
    if not r["nwin"]:
        e = f"  envp99 n={len(r['env'])}" if len(r["env"]) else ""
        print(f"  {name:{width}s} {r['nrun']:2d} ep {r['secs']:6.1f} s   0 win -- NOT COMPUTABLE{e}")
        return
    ev = (f" | envp99 med {np.median(r['env']):7.1f} p99 {np.percentile(r['env'],99):8.1f}"
          if len(r["env"]) else "")
    print(f"  {name:{width}s} {r['nrun']:2d} ep {r['secs']:6.1f} s {r['nwin']:3d} win | "
          f"f0 med {np.median(r['f0']):5.2f} sd {r['f0'].std(ddof=1) if r['nwin']>1 else 0:4.2f} | "
          f"prom med {np.median(r['prom']):7.1f}x p90 {np.percentile(r['prom'],90):8.1f}x{ev}")


creep = lambda lat, g, v, e: lat & (v > 0.3) & (v <= 5.35)                             # noqa: E731
fwd = lambda lat, g, v, e: ~lat & (g == 2) & (v > 0.3)                                 # noqa: E731
fwd1k = lambda lat, g, v, e: ~lat & (g == 2) & (v > 0.3) & (e >= 1000)                 # noqa: E731
rev = lambda lat, g, v, e: ~lat & (g == 4) & (v > 0.3)                                 # noqa: E731
revall = lambda lat, g, v, e: ~lat & (g == 4)                                          # noqa: E731
nearstat = lambda lat, g, v, e: ~lat & (np.abs(v) <= 0.6) & (e >= 2200) & (e <= 3300)  # noqa: E731
dis_any = lambda lat, g, v, e: ~lat & (v > 0.3) & (v <= 5.35)                          # noqa: E731


def main():
    print("=" * 108)
    print("1.  FRAGMENTED ARMS at NFFT=128 (1.28 s, 0.79 Hz bins) -- window-length null vs real null")
    print("=" * 108)
    for label in POOLS:
        print(f"\n[{label}]")
        for nm, sel in (("near-stat manual eff 2200-3300", nearstat),
                        ("MANUAL fwd eff>=1000", fwd1k), ("MANUAL reverse (all v)", revall)):
            for nfft in (256, 128):
                line(f"{nm}  nfft={nfft}", scan(label, sel, nfft), width=36)

    print()
    print("=" * 108)
    print("2.  ENVELOPE p99 in each build's OWN tracking band (f0 +/- 1.5 Hz) -- engaged creep")
    print("=" * 108)
    for label in POOLS:
        b = (F0[label] - 1.5, F0[label] + 1.5)
        line(f"{label}  band {b[0]:.1f}-{b[1]:.1f} Hz", scan(label, creep, 256, band=b), width=42)
    print("\n  Cross-band control -- every build measured in EVERY build's band, engaged creep,")
    print("  p99 envelope only. If V64 were sitting at V61's frequency this would show it.")
    for label in POOLS:
        row = []
        for other in POOLS:
            b = (F0[other] - 1.5, F0[other] + 1.5)
            r = scan(label, creep, 256, band=b)
            row.append(f"{other.split()[0]}-band {np.percentile(r['env'],99):8.1f}"
                       if len(r["env"]) else f"{other.split()[0]}-band     n/a")
        print(f"  {label:16s} " + "   ".join(row))

    print()
    print("=" * 108)
    print("3.  THE MANUAL PICTURE HEAD TO HEAD -- identical code on all three caches")
    print("=" * 108)
    for nm, sel, nfft in (("ENGAGED creep", creep, 256), ("DISENGAGED, same speed window", dis_any, 256),
                          ("MANUAL fwd un-gated", fwd, 256), ("MANUAL fwd eff>=1000", fwd1k, 128),
                          ("MANUAL reverse", revall, 128), ("near-stat manual hi-effort", nearstat, 128)):
        print(f"\n[{nm}]  nfft={nfft}")
        for label in POOLS:
            line(label, scan(label, sel, nfft), width=18)

    print()
    print("=" * 108)
    print("4.  ENGAGED / DISENGAGED PROMINENCE RATIO, same speed window, per build")
    print("=" * 108)
    for label in POOLS:
        e, dd = scan(label, creep, 256), scan(label, dis_any, 256)
        if e["nwin"] and dd["nwin"]:
            print(f"  {label:16s} eng med {np.median(e['prom']):8.1f}x ({e['nwin']:3d} win)  "
                  f"dis med {np.median(dd['prom']):8.1f}x ({dd['nwin']:3d} win)  "
                  f"ratio {np.median(e['prom'])/np.median(dd['prom']):7.2f}x")
        else:
            print(f"  {label:16s} eng {e['nwin']} win  dis {dd['nwin']} win -- not computable")

    print()
    print("=" * 108)
    print("5.  EFFORT DISTRIBUTIONS -- is the engaged/disengaged comparison effort-confounded?")
    print("=" * 108)
    for label in POOLS:
        for nm, sel in (("engaged creep", creep), ("disengaged same-speed", dis_any)):
            vals = []
            for _, d in segs(label):
                m = sel(d["cc_lat"] > 0.5, d["_gear"], d["cs_v"], d["_eff"])
                vals.extend(d["_eff"][m].tolist())
            print(f"  {label:16s} {nm:22s} {stat(vals, '')}")
        print()


if __name__ == "__main__":
    main()
