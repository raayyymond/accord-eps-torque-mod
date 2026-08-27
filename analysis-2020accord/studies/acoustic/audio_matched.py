"""AUDIO, SPEED-MATCHED.  [min episode length lowered 2.0 s -> 1.0 s so the STOCK manual arm
has enough episodes for the decisive engaged/manual control -- declared, not silent.]  Corrects two defects in `studies/acoustic/audio_stock_vs_6x.py`.

🛑 DEFECT 1 -- C1 WAS CONFOUNDED BY SPEED.  Manual < 16 km/h is mostly PARKED (v p50 = 0.0 on
   every route) while engaged sits at 7-10 km/h, and the measured speed slope is 0.32-0.55 dB per
   km/h at 100 Hz.  A 10 km/h gap is 3-5 dB = 1.4-1.8x in amplitude -- which fully accounts for
   the "engaged-only" 100-200 Hz ratios of 1.4-1.98 I printed.  ⇒ REDONE on 5-16 km/h, where both
   arms have real exposure and their medians agree to ~1 km/h (r97 8.6/9.1 · r96 9.7/9.9 ·
   r9e 8.6/8.1 · ra4 10.8/13.0).

🛑 DEFECT 2 -- THE SUB-100 Hz WIDE BANDS ARE AN ARTIFACT, NOT A MEASUREMENT.  The extractor uses a
   1024-point window at 16 kHz => 15.6 Hz bins, so the (5,15) and (21,28) bands contain NO bin
   centre and read exactly 0.0.  That is a RESOLUTION failure, not an absence of signal: a
   65536-point FFT on the same data showed 21-28 Hz at 4.89e12.  **Those two rows must not be
   quoted.**  Sub-100 Hz acoustic work needs a >= 16384-point window and is not attempted here.
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
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import _gate2_boost_lib as L

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KPH, FR = 3.6, 62.5
TAGS = ('r97', 'r96', 'r9e', 'ra4')
NAMES = {'r97': 'STOCK 1x', 'r96': 'V102 6x', 'r9e': 'V103 6x', 'ra4': 'V104 6x'}
VLO, VHI = 5.0, 16.0


def load(tag):
    a = np.load(os.path.join(HERE, '_cache_%s' % tag, '%s_audio.npz' % tag))
    d = L.load(tag)
    tc, ta = d['t'].astype(float), a['t'].astype(float)
    return dict(t=ta, tob=a['tob'].astype(float), tob_f=a['tob_f'],
                eng=np.interp(ta, tc, (d['cc_lat'] > 0.5).astype(float)) > 0.5,
                v=np.interp(ta, tc, d['v_rear'].astype(float) * KPH))


A = {t: load(t) for t in TAGS}
TOBF = A['r97']['tob_f']


def M(R, eng=True):
    return (R['eng'] if eng else ~R['eng']) & (R['v'] >= VLO) & (R['v'] < VHI)


def eps(m):
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k+1])) for k in range(len(b)-1)
            if m[b[k]] and (b[k+1]-b[k]) >= int(1.0*FR)]


def boot(Pa, Pb, nb=3000, seed=17):
    if len(Pa) < 3 or len(Pb) < 3:
        return None
    pt = np.sqrt(np.concatenate(Pb).mean() / np.concatenate(Pa).mean())
    rg = np.random.default_rng(seed)
    d = np.array([np.sqrt(np.concatenate([Pb[j] for j in rg.integers(0,len(Pb),len(Pb))]).mean()
                  / np.concatenate([Pa[j] for j in rg.integers(0,len(Pa),len(Pa))]).mean())
                  for _ in range(nb)])
    return pt, np.percentile(d,2.5), np.percentile(d,97.5), len(Pb), len(Pa)


def per_ep(R, m, col):
    return [R['tob'][s:t2, col] for s, t2 in eps(m)]


print("=" * 118)
print("SPEED-MATCHED WINDOW 5-16 km/h -- exposure and speed agreement")
print("=" * 118)
print("%8s %12s %10s %12s %10s" % ('route','eng s / eps','eng v p50','man s / eps','man v p50'))
for t in TAGS:
    R = A[t]
    me, mm = M(R, True), M(R, False)
    print("%8s %6.1f / %-4d %10.1f %6.1f / %-4d %10.1f"
          % (t, me.sum()/FR, len(eps(me)), np.median(R['v'][me]),
             mm.sum()/FR, len(eps(mm)), np.median(R['v'][mm])))

print()
print("=" * 118)
print("C1 (CORRECTED) -- ENGAGED / MANUAL at 5-16 km/h.  Road, wind, ENGINE and HVAC do not know")
print("   whether LKAS is on.  An ENGAGED-ONLY band on the 6x builds but not stock is ours.")
print("=" * 118)
print("%9s" % 'band Hz' + "".join("%24s" % NAMES[t] for t in TAGS))
for i, fc in enumerate(TOBF):
    cells = []
    for t in TAGS:
        R = A[t]
        r = boot(per_ep(R, M(R, False), i), per_ep(R, M(R, True), i))
        cells.append("%.2f [%.2f,%.2f]" % (r[0], r[1], r[2]) if r else "-")
    print("%9.0f" % fc + "".join("%24s" % c for c in cells))
print("  ⇒ a band is OURS only if the 6x cells are clearly >1 AND the STOCK cell is not.")

print()
print("=" * 118)
print("ITEM 1 (CORRECTED) -- STOCK vs each 6x build, ENGAGED, 5-16 km/h")
print("=" * 118)
print("%9s %22s %22s %22s" % ('band Hz','V102/STOCK','V103/STOCK','V104/STOCK'))
for i, fc in enumerate(TOBF):
    base = per_ep(A['r97'], M(A['r97'], True), i)
    cells = []
    for t in ('r96','r9e','ra4'):
        r = boot(base, per_ep(A[t], M(A[t], True), i))
        cells.append("%.2f [%.2f,%.2f]" % (r[0], r[1], r[2]) if r else "-")
    print("%9.0f" % fc + "".join("%22s" % c for c in cells))
print()
print("  🛑 THE TEST: a band that is GRINDING must be elevated on ALL THREE 6x builds versus")
print("     stock, in the same direction, and engaged-only.  A band elevated on one build only is")
print("     that DRIVE, not that BUILD CLASS.")
