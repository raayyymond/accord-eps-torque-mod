#!/usr/bin/env python3
r"""AUDIT BEFORE MEASURE -- can these caches carry a 40-50 Hz band at all, and is there any
highway-engaged exposure to look at?

WHY THIS FILE EXISTS FIRST
  The question handed to this session is "does the envelope of a HIGH-frequency band drive a LOW
  frequency oscillation at highway speed".  Every part of that sentence has a precondition that
  can fail silently in this kit's caches:

    P1  the row grid is ~100 Hz, so 40-50 Hz sits at 0.80-0.98 of Nyquist.  If the ECU updates the
        0x18F payload SLOWER than it transmits it (`0x18F staleness is 12.5 ms, not 10` --
        STATE.md defect #5), the stream is a ZOH staircase and its 40-50 Hz content is a
        SAMPLING ARTEFACT, not steering.
    P2  even with no ZOH, content above 50 Hz folds down.  A "40-49 Hz" reading may be 51-60 Hz.
    P3  427 (`x6b4c`/`x6b94`) is a ~42-50 Hz stream ZOH'd up -- it CANNOT carry 40-50 Hz.  The kit
        already caps it at 20 Hz (`v102_xb_lib.CH_NYQ`).
    P4  there must actually BE engaged frames above ~70 km/h.  r97 is claimed 82.8 % above
        35 km/h; that is not the same statement.

  None of this is a result.  It is the set of facts that decide which of the four hypotheses can
  even be tested, and it is reported whether or not it is convenient.

OUTPUT  `rlog-tools/_scratch/out/_hf_lf_audit.json`
"""
from __future__ import annotations
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
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROUTE_LABEL = {"97": "STOCK (V9b)", "9e": "V103", "96": "V102 6x", "85": "V100 4x",
               "95": "V101 8x", "73": "V88"}
ROUTES = ["9e", "97", "96", "95", "85"]
KMH = 3.6


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104, flush=True)


def whole(rt):
    return dict(np.load(L._cache_dir(rt) / ("r" + rt + ".npz"), allow_pickle=True))


# ---------------------------------------------------------------- P1/P2 native cadence ----------
def cadence(rt):
    """Native inter-arrival statistics for each raw CAN stream, plus the row grid."""
    d = whole(rt)
    out = {}
    for name, key in (("row", "t"), ("0x18F", "raw18_t"), ("0x14A", "raw14_t"),
                      ("0x1AB", "raw1ab_t"), ("wheelspeed", "ws_t"), ("carState", "cs_t")):
        if key not in d:
            continue
        t = np.asarray(d[key], float)
        dt = np.diff(t)
        dt = dt[np.isfinite(dt) & (dt > 0)]
        if not len(dt):
            continue
        out[name] = dict(n=int(len(t)), span_s=float(t[-1] - t[0]),
                         dt_med_ms=float(np.median(dt) * 1e3),
                         dt_p01_ms=float(np.percentile(dt, 1) * 1e3),
                         dt_p99_ms=float(np.percentile(dt, 99) * 1e3),
                         rate_hz=float(1.0 / np.median(dt)))
    return out


def zoh_audit(rt):
    """Repeat fraction of each analogue channel on its OWN native grid.

    A field transmitted at 100 Hz but recomputed at 80 Hz shows ~20 % exact repeats and its
    40-50 Hz content is a staircase artefact.  A field recomputed every frame shows ~0 % repeats
    away from the quantiser floor.
    """
    d = whole(rt)
    out = {}
    for ch, tk in (("tq", "raw18_t"), ("rate_f", "raw18_t"), ("ang", "raw18_t"),
                   ("rate_c", "raw14_t"), ("probe", "raw14_t")):
        if ch not in d:
            continue
        x = np.asarray(d[ch], float)
        x = x[np.isfinite(x)]
        if len(x) < 100:
            continue
        dif = np.diff(x)
        nz = dif[dif != 0]
        step = float(np.min(np.abs(nz))) if len(nz) else float("nan")
        out[ch] = dict(n=int(len(x)),
                       repeat_frac=float(np.mean(dif == 0.0)),
                       lsb=step,
                       iqr=float(np.percentile(x, 75) - np.percentile(x, 25)),
                       absmax=float(np.max(np.abs(x))))
    return out


# ---------------------------------------------------------------- P4 highway exposure -----------
def exposure(rt):
    """Engaged / manual seconds by speed stratum, on the uniform grid the analysis will use."""
    bins = [(0, 20), (20, 40), (40, 70), (70, 200)]
    acc = {("eng" if e else "man", i): 0.0 for e in (0, 1) for i in range(len(bins))}
    tot = 0.0
    for blk in L.all_blocks(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        tot += len(v) / L.FS
        for i, (lo, hi) in enumerate(bins):
            m = (v >= lo) & (v < hi)
            acc[("eng", i)] += float(np.sum(m & eng)) / L.FS
            acc[("man", i)] += float(np.sum(m & ~eng)) / L.FS
    return dict(total_s=tot,
                bins=["%d-%d" % b for b in bins],
                eng_s=[acc[("eng", i)] for i in range(len(bins))],
                man_s=[acc[("man", i)] for i in range(len(bins))])


# ---------------------------------------------------------------- P2 spectral shape -------------
def hf_shape(rt, nfft=512):
    """Mean engaged-highway PSD of `tq` and `rate_c`, reported band by band up to Nyquist.

    A monotone rise into the last bins, or a flat shelf that does not decay, is the signature of
    ZOH/aliasing rather than a mode.
    """
    win = np.hanning(nfft)
    got = {"tq": [], "rate_c": []}
    f = None
    for blk in L.all_blocks(rt):
        v = np.asarray(blk["v_rear"], float) * KMH
        eng = np.asarray(blk["cc_lat"], float) > 0.5
        n = len(v)
        for s in range(0, n - nfft + 1, nfft // 2):
            sl = slice(s, s + nfft)
            if eng[sl].mean() < 0.98 or np.median(v[sl]) < 70.0:
                continue
            for ch in got:
                if ch not in blk:
                    continue
                x = np.asarray(blk[ch][sl], float)
                if not np.all(np.isfinite(x)):
                    continue
                f, p = L.psd(x, L.FS, win)
                got[ch].append(p)
    out = {}
    for ch, ps in got.items():
        if not ps or f is None:
            out[ch] = None
            continue
        P = np.mean(np.asarray(ps), axis=0)
        rows = []
        for lo in range(0, 50, 5):
            m = (f >= lo) & (f < lo + 5)
            rows.append(dict(band="%d-%d" % (lo, lo + 5), rms=float(np.sqrt(P[m].sum()))))
        out[ch] = dict(nwin=len(ps), rows=rows)
    return out


def main():
    res = {}
    for rt in ROUTES:
        if not reg(rt):
            print("route %s: NO CACHE" % rt)
            continue
        hdr("ROUTE %s  (%s)" % (rt, ROUTE_LABEL.get(rt, rt)))
        c = cadence(rt)
        print("-- native cadence")
        for k, v in c.items():
            print("   %-11s n=%-8d span=%8.1fs  dt med=%6.2f ms (p01 %6.2f / p99 %6.2f)  = %6.2f Hz"
                  % (k, v["n"], v["span_s"], v["dt_med_ms"], v["dt_p01_ms"], v["dt_p99_ms"],
                     v["rate_hz"]))
        z = zoh_audit(rt)
        print("-- ZOH / quantiser audit  (repeat_frac near 0.20 => 80 Hz content in a 100 Hz stream)")
        for k, v in z.items():
            print("   %-8s repeats=%.4f  lsb=%.4g  iqr=%.4g  |max|=%.4g"
                  % (k, v["repeat_frac"], v["lsb"], v["iqr"], v["absmax"]))
        e = exposure(rt)
        print("-- exposure on the uniform grid (seconds)   total %.1f s" % e["total_s"])
        print("   %-10s %s" % ("km/h", "  ".join("%9s" % b for b in e["bins"])))
        print("   %-10s %s" % ("ENGAGED", "  ".join("%9.1f" % s for s in e["eng_s"])))
        print("   %-10s %s" % ("manual", "  ".join("%9.1f" % s for s in e["man_s"])))
        h = hf_shape(rt)
        print("-- engaged >=70 km/h mean PSD, band RMS (nfft 512 = 5.12 s)")
        for ch, o in h.items():
            if o is None:
                print("   %-8s (no windows)" % ch)
                continue
            print("   %-8s nwin=%d" % (ch, o["nwin"]))
            print("      " + "  ".join("%s:%.4g" % (r["band"], r["rms"]) for r in o["rows"]))
        res[rt] = dict(cadence=c, zoh=z, exposure=e, hf_shape=h)
    (HERE / "_scratch/out/_hf_lf_audit.json").write_text(json.dumps(res, indent=1))
    print("\nwrote", HERE / "_scratch/out/_hf_lf_audit.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
