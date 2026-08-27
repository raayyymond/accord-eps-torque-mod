#!/usr/bin/env python3
r"""V100(r85) vs V101(r95): matched-cell spectra (#3) and the two SYMPTOM-SPECIFIC tests.

#3   Did the dominant frequency MOVE, and is there a NEW LINE at 8x that was absent at 4x?
GRIP Does applying driver torque KILL the band, as the operator reports?  (the kit's own idiom:
     the partial slope of log band RMS on log|driver torque| at matched wheel rate, symptom band
     against the 32-38 Hz control band)
WO   Wheel order 1 at 0.489 * v Hz -- ruled in or out explicitly.
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
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


W = {r: L.sel(L.windows(r, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=65)
     for r in ("85", "95")}
CELLS = []
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a = L.sel(W["85"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b = L.sel(W["95"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        if len(a) >= 5 and len(b) >= 5:
            CELLS.append(((vlo, vhi), (rlo, rhi), a, b))
print("matched cells: %d   V100 win=%d  V101 win=%d"
      % (len(CELLS), sum(len(c[2]) for c in CELLS), sum(len(c[3]) for c in CELLS)))

win = np.hanning(NFFT)


def medspec(recs, ch):
    P = []
    for r in recs:
        f, p = L.psd(r["_blk"][ch][r["_sl"]], L.FS, win)
        P.append(p)
    return f, np.median(np.asarray(P), axis=0)


# =====================================================================================================
hdr("#3a -- MEDIAN SPECTRA per matched cell.  Peaks and their prominence over a local median floor.")


def peaks(f, p, fmin=4.0, fmax=49.0, half=2.0):
    out = []
    m = (f >= fmin) & (f <= fmax)
    ff, pp = f[m], p[m]
    for i in range(1, len(pp) - 1):
        if pp[i] <= pp[i - 1] or pp[i] <= pp[i + 1]:
            continue
        loc = (ff >= ff[i] - half) & (ff <= ff[i] + half)
        floor = np.median(pp[loc])
        out.append((float(ff[i]), float(np.sqrt(pp[i])), float(pp[i] / floor)))
    out.sort(key=lambda x: -x[2])
    return out[:4]


for ch in ("tq", "rate_c"):
    print("\n  channel %s   (peak freq Hz, band RMS-equivalent, prominence over +/-2 Hz median)" % ch)
    for (vlo, vhi), (rlo, rhi), a, b in CELLS:
        fa, pa = medspec(a, ch)
        fb, pb = medspec(b, ch)
        wo = 0.489 * (np.median([r["v"] for r in a]) / 3.6)
        print("   %-11s %-9s  wheel-order1 ~%4.1f Hz" % ("%d-%d km/h" % (vlo, vhi),
                                                         "%d-%d d/s" % (rlo, rhi), wo))
        for lbl, f_, p_ in (("V100", fa, pa), ("V101", fb, pb)):
            pk = peaks(f_, p_)
            print("        %s  " % lbl + "   ".join("%5.1f Hz p=%.2f" % (a_, c_) for a_, b_, c_ in pk))

# =====================================================================================================
hdr("#3b -- POOLED matched-cell spectrum RATIO V101/V100 vs frequency (log-mean over cells)")
for ch in ("tq", "rate_c"):
    acc = []
    for (vlo, vhi), (rlo, rhi), a, b in CELLS:
        fa, pa = medspec(a, ch)
        fb, pb = medspec(b, ch)
        acc.append(np.log(np.sqrt(pb / np.maximum(pa, 1e-30))))
    R = np.exp(np.mean(np.asarray(acc), axis=0))
    print("\n  channel %s -- amplitude ratio in 2 Hz bins:" % ch)
    s = ""
    for lo in range(2, 50, 2):
        m = (fa >= lo) & (fa < lo + 2)
        s += "%2d-%2d:%5.2f  " % (lo, lo + 2, np.exp(np.mean(np.log(R[m]))))
        if lo % 12 == 10:
            print("      " + s)
            s = ""
    if s:
        print("      " + s)
    lo_, hi_ = np.percentile(R[(fa >= 4) & (fa <= 49)], [10, 90])
    print("      => 10th-90th pct of the ratio across 4-49 Hz: %.2f .. %.2f  (flat = BROADBAND"
          " LEVEL SHIFT, not a new mode)" % (lo_, hi_))

# =====================================================================================================
hdr("GRIP -- does applying driver torque KILL the band?  within-cell slope of log(bandRMS) on"
    " log|driver torque|")
print("   The kit already measured this on the ratchet: grip slope -0.720 [-0.918,-0.500] against a")
print("   control-band -0.216, CIs disjoint (accord-ratchet-axis-is-wheel-rate).  Same idiom here.")


def grip_slope(cells_idx, key, nboot=2000, seed=71):
    rng = np.random.default_rng(seed)
    pts = []
    for c in CELLS:
        recs = c[cells_idx]
        x = np.log1p(np.array([r["tqmed"] for r in recs]))
        y = np.log(np.array([r.get(key, np.nan) for r in recs]))
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 6:
            continue
        x, y = x[m] - x[m].mean(), y[m] - y[m].mean()
        blk = np.array([int(r["t0"] // 15.0) for r, ok in zip(recs, m) if ok])
        pts.append((x, y, blk))
    if not pts:
        return dict(slope=np.nan, lo=np.nan, hi=np.nan, n=0)

    def fit(sel_):
        X = np.concatenate([p[0][s] for p, s in zip(pts, sel_)])
        Y = np.concatenate([p[1][s] for p, s in zip(pts, sel_)])
        return float(np.sum(X * Y) / np.sum(X * X)) if np.sum(X * X) > 0 else np.nan
    full = [np.ones(len(p[0]), bool) for p in pts]
    s0 = fit(full)
    out = []
    for _ in range(nboot):
        sel_ = []
        for x, y, blk in pts:
            u = np.unique(blk)
            pick = rng.integers(0, len(u), len(u))
            idx = np.concatenate([np.nonzero(blk == u[j])[0] for j in pick])
            s = np.zeros(len(x), bool)
            s[np.unique(idx)] = True
            sel_.append(s)
        out.append(fit(sel_))
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(slope=s0, lo=float(lo), hi=float(hi), n=sum(len(p[0]) for p in pts))


for ch in ("tq", "rate_c"):
    print("\n  channel %s" % ch)
    for idx, lbl in ((2, "V100 r85 (4x)"), (3, "V101 r95 (8x)")):
        row = []
        for bn in ("6-9", "18-22", "26-31", "32-38"):
            g = grip_slope(idx, ch + "|" + bn)
            row.append("%s %+5.2f[%+5.2f,%+5.2f]" % (bn, g["slope"], g["lo"], g["hi"]))
        print("   %-16s %s" % (lbl, "  ".join(row)))

# =====================================================================================================
hdr("WO -- WHEEL ORDER 1 (0.489 * v Hz).  Is any 'line' just a tyre?")
for (vlo, vhi), (rlo, rhi), a, b in CELLS:
    v = np.median([r["v"] for r in a] + [r["v"] for r in b]) / 3.6
    print("   %-11s %-9s  v=%4.1f m/s  wheel order 1 = %4.1f Hz   order 2 = %4.1f Hz"
          % ("%d-%d km/h" % (vlo, vhi), "%d-%d d/s" % (rlo, rhi), v, 0.489 * v, 0.978 * v))
print("""
   The matched cells span 5-65 km/h, so wheel order 1 sweeps ~1 Hz to ~9 Hz across them.  A line
   that is FIXED in Hz across cells is NOT a wheel order; a line that tracks 0.489*v IS.""")

print("\n[done]")
