#!/usr/bin/env python3
"""Shared instruments for the V62 route-37 RATCHET analysis. Import; do not re-implement.

Everything here exists because a specific earlier method gave a wrong answer:

  LOCATOR -- `locate()` takes the argmax of the PROMINENCE spectrum (P / its own local median
  floor), not of P. A raw-power argmax on `tq` lands on the driver's own 1-3 Hz input, and giving
  it a band floor instead pins it to the band edge (17.7% of engaged windows at a 10 Hz edge,
  18.9% at a 5 Hz edge). On the prominence spectrum, edge pinning is 0.0%.

  POWER -- every prominence is reported next to a PHYSICAL amplitude (band RMS and band envelope
  p99, both in torque counts). `peak_prom` divides by a local median floor, so a modest tone in a
  very quiet window inflates the ratio without carrying energy. A prominence of 30,000 next to an
  RMS of 20 counts is a quiet floor; next to an RMS of 900 counts it is a real oscillation.

  EPISODES -- windows inside one contiguous run of a mask are NOT independent samples. `episodes()`
  groups them, so an n of 16 windows is reported as the 4-6 physical events it actually is.

  ALIASING -- fs is ~100.3-101.4 Hz. EVERY frequency here is indistinguishable from its aliases
  (7.4 Hz vs 93.1 Hz vs 107.9 Hz ...). Stated once; true everywhere.
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
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _r31_common as C  # noqa: E402

NFFT = 256
RATCHET_FREE = (5.0, 12.0)      # free locator range for the ratchet
GRIND_FREE = (17.0, 26.0)       # free locator range for the 21 Hz grinding mode
B_RAT = (6.0, 9.0)              # ratchet presence band
B_GRIND = (18.0, 26.0)          # grinding presence band

# Route -> build. Supplied by the orchestrator; 2b predates the labelled series.
ROUTES = [
    ("2b",        C.ROOT / "_scratch/cache/r2b", "r2bs", [0, 1, 2, 11, 12, 13]),
    ("2c/V59",    C.ROOT / "_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12]),
    ("31/V61",    C.ROOT / "_scratch/cache/r31", "r31s", [0, 1, 2, 3]),
    ("35/V64=V59", C.ROOT / "_scratch/cache/r35", "r35s", [0, 1, 2]),
    ("37/V62",    C.ROOT / "_scratch/cache/r37", "r37s", list(range(0, 15))),   # seg 0 INCLUDED
]

# Route-37 wall clock: single continuous boot clock, one offset for all 15 segments.
# Fitted over the post-NTP-sync clocks cluster by studies/sessions/r37/r37_wallclock.py (sd 0.054 s).
R37_OFF = 1785517810.5370


def prom_spectrum(f, P, halfwin=6.0, exclude=1.5):
    """P divided by its own local median floor, per bin."""
    R = np.full(len(P), np.nan)
    for j in range(1, len(P) - 1):
        near = (np.abs(f - f[j]) <= halfwin) & (np.abs(f - f[j]) > exclude) & (f > 0.3)
        if near.sum() < 5:
            continue
        fl = float(np.median(P[near]))
        if fl > 0:
            R[j] = P[j] / fl
    return R


def locate(f, P, lo, hi, halfwin=6.0, exclude=1.5):
    """(f0, prominence) of the most prominent line in [lo,hi], sub-bin refined in log power."""
    R = prom_spectrum(f, P, halfwin, exclude)
    m = (f >= lo) & (f <= hi) & np.isfinite(R)
    if not m.any():
        return np.nan, np.nan
    j = int(np.argmax(np.where(m, R, -np.inf)))
    if j <= 0 or j >= len(P) - 1:
        return float(f[j]), float(R[j])
    y0, y1, y2 = (np.log(P[j - 1] + 1e-300), np.log(P[j] + 1e-300), np.log(P[j + 1] + 1e-300))
    den = y0 - 2 * y1 + y2
    dl = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(f[j] + np.clip(dl, -0.5, 0.5) * (f[1] - f[0])), float(R[j])


def bandpass(x, fs, lo, hi):
    """Zero-phase brick-wall bandpass. Returns the real band-limited signal (counts)."""
    x = np.asarray(x, float) - np.mean(x)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))


def q_of(f, P, f0):
    return C.q_of(f, P, f0) if np.isfinite(f0) else np.nan


def windows(d, mask, fs, hop=NFFT, nfft=NFFT):
    """Per-window records inside contiguous runs of `mask`. `run` identifies the episode.

    hop == nfft gives DISJOINT windows (the default; use it for any statistic that will be
    counted). A smaller hop is for time resolution only.
    """
    out = []
    f = np.fft.rfftfreq(nfft, 1 / fs)
    for ep, (a, b) in enumerate(C.runs_of(mask, d["t"], nfft)):
        x = d["tq"][a:b]
        er = C.band_envelope(x, fs, *B_RAT)
        eg = C.band_envelope(x, fs, *B_GRIND)
        br = bandpass(x, fs, *B_RAT)
        bg = bandpass(x, fs, *B_GRIND)
        for i in range(0, len(x) - nfft + 1, hop):
            P = C.periodogram(x[i:i + nfft], fs, nfft)
            if P is None:
                continue
            sl = slice(a + i, a + i + nfft)
            w = slice(i, i + nfft)
            r = dict(ep=ep, run=(a, b), t0=float(d["t"][a + i]), i0=a + i)
            r["fr"], r["pr"] = locate(f, P, *RATCHET_FREE)
            r["fg"], r["pg"] = locate(f, P, *GRIND_FREE)
            r["Qr"] = q_of(f, P, r["fr"])
            r["Qg"] = q_of(f, P, r["fg"])
            # physical amplitudes, counts
            r["rms_r"] = float(np.sqrt(np.mean(br[w] ** 2)))
            r["rms_g"] = float(np.sqrt(np.mean(bg[w] ** 2)))
            r["env_r"] = float(np.percentile(er[w], 99))
            r["env_g"] = float(np.percentile(eg[w], 99))
            # raw band power, for comparability with power-based sweeps
            r["pow_r"] = float(P[(f >= B_RAT[0]) & (f <= B_RAT[1])].sum())
            r["pow_g"] = float(P[(f >= B_GRIND[0]) & (f <= B_GRIND[1])].sum())
            r["v"] = float(np.mean(d["cs_v"][sl]))
            r["ang"] = float(np.mean(np.abs(d["ang"][sl])))
            r["eff"] = float(np.mean(np.abs(C.sustained(d["tq"][sl], fs))))
            r["e4"] = float(np.mean(np.abs(d["e4tq"][sl])))
            r["lat"] = float(np.mean(d["cc_lat"][sl] > 0.5))
            r["gear"] = float(np.median(d["cs_gear"][sl])) if "cs_gear" in d else np.nan
            out.append(r)
    return out


def collect(cache, pfx, segs, hop=NFFT, mask_fn=None):
    """Window records for a whole route. mask_fn(d) -> boolean mask, default: all frames."""
    out = []
    for s in segs:
        p = cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, cache, pfx)
        fs = C.fs_of(d)
        m = np.ones(len(d["t"]), bool) if mask_fn is None else mask_fn(d)
        for r in windows(d, m, fs, hop=hop):
            r["seg"] = s
            r["fs"] = fs
            out.append(r)
    return out


def episodes(rs):
    """Group window records into physical episodes: (seg, run) pairs."""
    ep = {}
    for r in rs:
        ep.setdefault((r["seg"], r["run"]), []).append(r)
    return list(ep.values())


def wall37(seg_t0_mono, t):
    return time.strftime("%H:%M:%S", time.localtime(seg_t0_mono + R37_OFF + t))


def stat(v, pcts=(50, 90)):
    v = np.asarray([x for x in v if np.isfinite(x)], float)
    if not len(v):
        return "n=0"
    return "  ".join(f"p{p}={np.percentile(v, p):.4g}" for p in pcts)
