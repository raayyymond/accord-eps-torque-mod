"""IS THE c4 LEVER EVEN POINTED AT THE HIGHWAY?  A band survey of V103 by speed.

The c4 lever's entire warrant is 6-9 Hz.  Before recommending a dose for the highway it is
worth asking whether 6-9 Hz is where the highway arm is actually loud on the car TODAY.

Statistic: engaged band-RMS of `rate_f` (deg/s), with the MANUAL arm in the same speed band
as the within-drive control, per band, per speed bin, on route 0x9e (V103, on the car).

🛑 `rate_f` is 0.7996x true deg/s -- every number here is on the same channel, so RATIOS and
   BAND CONTRASTS are valid; the absolute deg/s figures are 1.25x low.
🛑 Episode-level split-half control printed beside every number.
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
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import _gate2_boost_lib as L                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

NPER = int(round(4 * L.FS))
f = np.fft.rfftfreq(NPER, 1 / L.FS)
KPH = 3.6
VB = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100)]
FB = [(2, 4), (4, 6), (6, 9), (9, 13), (13, 18), (18, 22), (22, 26), (26, 31), (31, 40)]


def runs(mask):
    idx = np.flatnonzero(np.diff(mask.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], idx, [len(mask)]))
    return [(int(b[i]), int(b[i + 1])) for i in range(len(b) - 1)
            if mask[b[i]] and (b[i + 1] - b[i]) >= NPER]


def band_rms_runs(sig, mask, lo, hi, sub=None):
    sp = []
    for a0, b0 in runs(mask):
        r = L._win_spec(sig[a0:b0], sig[a0:b0], NPER, L.FS)
        if r is not None:
            sp.append((r[0].sum(0), len(r[0])))
    if not sp:
        return np.nan, 0
    if sub is not None:
        sp = sp[sub::2]
        if not sp:
            return np.nan, 0
    sel = (f >= lo) & (f < hi)
    Sxx = sum(s[0] for s in sp)
    nw = sum(s[1] for s in sp)
    return float(np.sqrt(Sxx[sel].sum() / nw * (f[1] - f[0]))), len(sp)


for tag, nm in (('r9e', 'V103 (ON THE CAR)'), ('r97', 'STOCK 1x baseline')):
    d = L.load(tag)
    eng = d['cc_lat'] > 0.5
    v = d['v_rear'].astype(float) * KPH
    rate = d['rate_f'].astype(float)
    print("=" * 118)
    print("%s -- route %s : ENGAGED band-RMS of rate_f (deg/s), by speed" % (nm, tag))
    print("=" * 118)
    print("%12s" % 'speed band' + "".join("%11s" % ("%g-%g" % b) for b in FB) + "%8s" % 'runs')
    for lo, hi in VB:
        m = eng & (v >= lo) & (v < hi)
        row, n = [], 0
        for a_, b_ in FB:
            r, n = band_rms_runs(rate, m, a_, b_)
            row.append(r)
        print("%7d-%-4d" % (lo, hi) + "".join(
            ("%11.4f" % x) if np.isfinite(x) else "%11s" % '-' for x in row) + "%8d" % n)
    print()
    print("  ENGAGED / MANUAL ratio in the SAME speed band (the within-drive control):")
    print("%12s" % 'speed band' + "".join("%11s" % ("%g-%g" % b) for b in FB))
    for lo, hi in VB:
        me = eng & (v >= lo) & (v < hi)
        mm = (~eng) & (v >= lo) & (v < hi)
        row = []
        for a_, b_ in FB:
            re_, _ = band_rms_runs(rate, me, a_, b_)
            rm_, _ = band_rms_runs(rate, mm, a_, b_)
            row.append(re_ / rm_ if (np.isfinite(re_) and np.isfinite(rm_) and rm_) else np.nan)
        print("%7d-%-4d" % (lo, hi) + "".join(
            ("%11.2f" % x) if np.isfinite(x) else "%11s" % '-' for x in row))
    print()
    print("  SPLIT-HALF CONTROL on the ENGAGED arm (half A / half B, interleaved runs):")
    print("%12s" % 'speed band' + "".join("%11s" % ("%g-%g" % b) for b in FB))
    for lo, hi in VB:
        m = eng & (v >= lo) & (v < hi)
        row = []
        for a_, b_ in FB:
            r0, n0 = band_rms_runs(rate, m, a_, b_, sub=0)
            r1, n1 = band_rms_runs(rate, m, a_, b_, sub=1)
            row.append(r0 / r1 if (np.isfinite(r0) and np.isfinite(r1) and r1) else np.nan)
        print("%7d-%-4d" % (lo, hi) + "".join(
            ("%11.2f" % x) if np.isfinite(x) else "%11s" % '-' for x in row))
    print()
