#!/usr/bin/env python3
"""Second, non-FFT derivations for route `35`'s load-bearing claims.

The decisive claim is STRUCTURAL: V61 moved the engaged-creep mode from 21.18 Hz down to 18.25 Hz,
and V64 is claimed to have put it back. A pure gain change cannot move a resonance; a phase change
can. That claim must not rest on one estimator, and both estimators so far are periodograms.

Method C is TIME-DOMAIN and shares no code with A or B: band-pass 12-30 Hz, then estimate the
period from (i) the mean spacing of upward zero crossings and (ii) the first positive peak of the
autocorrelation. Neither touches an rfft bin index.

Also here: the speed composition of each build's engaged-creep arm, because the duty-cycle
difference between V64 and V59 (Method B medians 108.0x vs 37.7x) is only interpretable if the two
arms sit at comparable speeds; and the ST==3 placement.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _r31_common import runs_of, sustained, stat  # noqa: E402

POOLS = {"V59  route 2c": (ROOT / "_scratch/cache/r2c", "r2cs*"),
         "V61  route 31": (ROOT / "_scratch/cache/r31", "r31s*"),
         "V64  route 35": (ROOT / "_scratch/cache/r35", "r35s*")}


def segs(label):
    cache, pfx = POOLS[label]
    for f in sorted(cache.glob(pfx + ".npz")):
        d = {k: v for k, v in np.load(f).items()}
        d["_fs"] = 1.0 / np.median(np.diff(d["t"]))
        yield f.stem, d


def bandpass(x, fs, lo, hi):
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))


def f_zerocross(y, fs):
    """Upward zero crossings, sub-sample interpolated. Period = mean spacing."""
    s = np.signbit(y)
    idx = np.flatnonzero(s[:-1] & ~s[1:])          # - -> +
    if len(idx) < 3:
        return np.nan
    frac = -y[idx] / (y[idx + 1] - y[idx])
    tcr = (idx + frac) / fs
    return 1.0 / np.mean(np.diff(tcr))


def f_autocorr(y, fs, lo, hi):
    """First autocorrelation maximum inside the lag range allowed by [lo,hi] Hz."""
    y = y - y.mean()
    n = len(y)
    ac = np.correlate(y, y, "full")[n - 1:]
    a, b = int(np.floor(fs / hi)), int(np.ceil(fs / lo))
    if b >= len(ac) or b <= a + 1:
        return np.nan
    seg = ac[a:b + 1]
    j = int(np.argmax(seg)) + a
    if 0 < j < len(ac) - 1:                        # parabolic refine on the lag axis
        y0, y1, y2 = ac[j - 1], ac[j], ac[j + 1]
        den = y0 - 2 * y1 + y2
        j = j + (0.5 * (y0 - y2) / den if den != 0 else 0.0)
    return fs / j if j > 0 else np.nan


def main():
    print("=" * 100)
    print("METHOD C -- TIME-DOMAIN frequency, engaged creep, 12-30 Hz band-pass, no rfft bin index")
    print("=" * 100)
    NW = 256
    for label in POOLS:
        zc, ac, w = [], [], 0
        for _, d in segs(label):
            fs = d["_fs"]
            lat = d["cc_lat"] > 0.5
            m = lat & (d["cs_v"] > 0.3) & (d["cs_v"] <= 5.35)
            for a, b in runs_of(m, d["t"], NW):
                y = bandpass(d["tq"][a:b], fs, 12.0, 30.0)
                for i in range(0, len(y) - NW + 1, NW):
                    seg = y[i:i + NW]
                    if np.std(seg) < 20:           # a quiet window has no period to estimate
                        continue
                    z, c = f_zerocross(seg, fs), f_autocorr(seg, fs, 12.0, 30.0)
                    if np.isfinite(z):
                        zc.append(z)
                    if np.isfinite(c):
                        ac.append(c)
                    w += 1
        print(f"\n  {label}   {w} active windows (sd >= 20 counts)")
        print(f"    zero-crossing  {stat(zc, '')}")
        print(f"    autocorrelation{stat(ac, '')}")
        if zc and ac:
            print(f"    => median  zc {np.median(zc):5.2f} Hz | ac {np.median(ac):5.2f} Hz")

    print()
    print("=" * 100)
    print("SPEED COMPOSITION of each engaged-creep arm -- is the duty-cycle comparison matched?")
    print("=" * 100)
    for label in POOLS:
        vv, ee = [], []
        for _, d in segs(label):
            fs = d["_fs"]
            m = (d["cc_lat"] > 0.5) & (d["cs_v"] > 0.3) & (d["cs_v"] <= 5.35)
            vv.extend(d["cs_v"][m].tolist())
            ee.extend(np.abs(sustained(d["tq"], fs))[m].tolist())
        v = np.array(vv)
        print(f"  {label:16s} vEgo n={len(v)}  p10={np.percentile(v,10):.2f} "
              f"p50={np.percentile(v,50):.2f} p90={np.percentile(v,90):.2f} max={v.max():.2f} m/s")
        edges = [0.3, 1, 2, 3, 4, 5.35]
        h = np.histogram(v, bins=edges)[0]
        print(f"                   speed histogram {list(zip([f'{a}-{b}' for a,b in zip(edges,edges[1:])], (100*h/h.sum()).round(1)))}")

    print()
    print("=" * 100)
    print("ST==3 PLACEMENT and engagement-episode inventory, route 35")
    print("=" * 100)
    for name, d in segs("V64  route 35"):
        fs = d["_fs"]
        st3 = d["sstat"] == 3
        lat = d["cc_lat"] > 0.5
        eps = list(runs_of(lat, d["t"], 1))
        print(f"  {name}: ST==3 {int(st3.sum())} frames "
              f"({100*st3.mean():.2f}%)  in-engaged {int((st3 & lat).sum())}  "
              f"v@ST3 p50={np.percentile(d['cs_v'][st3],50):.2f} m/s" if st3.any() else
              f"  {name}: ST==3 0 frames")
        print(f"           engagement episodes: "
              + ", ".join(f"{d['t'][a]:.1f}-{d['t'][b-1]:.1f}s ({(b-a)/fs:.1f}s)" for a, b in eps))

    print()
    print("=" * 100)
    print("EVENT / probe cross-check, route 35 (second derivation of the detector null)")
    print("=" * 100)
    tot = Counter()
    allprobe = Counter()
    for name, d in segs("V64  route 35"):
        allprobe.update(d["probe"].astype(int).tolist())
        for e in json.loads((POOLS["V64  route 35"][0] / f"{name}_events.json").read_text()):
            tot[e["name"]] += 1
    print(f"  0x14A byte4 raw histogram, all segments: "
          f"{{{', '.join(f'0x{k:02X}: {v}' for k, v in sorted(allprobe.items()))}}}")
    n = sum(allprobe.values())
    armed = sum(v for k, v in allprobe.items() if k & 0x40)
    count = sum(v for k, v in allprobe.items() if k & 0x20)
    fsm = sum(v for k, v in allprobe.items() if k & 0x10)
    ovr = sum(v for k, v in allprobe.items() if k & 0x08)
    live = sum(v for k, v in allprobe.items() if k & 0x80)
    print(f"  n={n}  live(bit7) {live} ({100*live/n:.2f}%)  armed(bit6, gp-0x671a>=5) {armed}  "
          f"count(bit5, !=0) {count}  fsm(bit4, gp-0x67df!=0) {fsm}  ovr(bit3, gp-0x671d!=0) {ovr}")
    print(f"  watched events: " + ", ".join(
        f"{k}={tot.get(k,0)}" for k in ("steerUnavailable", "steerTempUnavailable", "canError",
                                        "controlsMismatch", "immediateDisable", "steerSaturated")))


if __name__ == "__main__":
    main()
