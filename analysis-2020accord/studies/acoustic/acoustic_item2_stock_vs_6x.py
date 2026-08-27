r"""ITEM 2 -- THE HEADLINE: does any AUDIBLE band separate STOCK 1x from 6x, engaged, < 16 km/h?

The operator's word is GRINDING.  Grinding is a SOUND.  Every instrument in this project has run
on channels whose Nyquist is 25-50 Hz, so 100 Hz - 8 kHz has never been looked at.  This script
looks, under the controls the project has paid for four times over.

ORDER OF OPERATIONS IS DELIBERATE AND IS NOT NEGOTIABLE:
   C0  LEAKAGE CONTROL   -- is the 100-160 Hz region just spectral leakage from the huge sub-100 Hz
                            road rumble through the 1024-pt Hann window?  If yes, those rows are
                            not "audible band" measurements at all.
   C1  THE NULL          -- within-route split-half.  What does this estimator return at truth=1.0?
   C2  ENGAGED / MANUAL  -- at matched ROLLING speed.  The decisive control: road, wind, engine
                            order and HVAC do not know whether LKAS is engaged.
   C3  SPEED             -- the contrast is computed speed-MATCHED by re-weighting, always; the raw
                            unmatched number is printed beside it so the correction is visible.
   THEN, and only then, the stock-vs-6x table.

usage:  python studies/acoustic/acoustic_item2_stock_vs_6x.py
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
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
SIX = ['r96', 'r9e', 'ra4']
VLO, VHI = 0.0, 16.0

R = {}
for t in TAGS:
    try:
        R[t] = A.load(t)
    except FileNotFoundError:
        print("  %s: no audio cache" % t)
TOBF = R['r97']['tob_f']
NB = len(TOBF)


def bar(x, lo=0.5, hi=3.0, w=26):
    """A log-scaled ASCII bar with 1.0 marked, so the eye can find a separating band."""
    import math
    if not np.isfinite(x) or x <= 0:
        return ' ' * w
    p = (math.log(min(max(x, lo), hi)) - math.log(lo)) / (math.log(hi) - math.log(lo))
    one = int(round((math.log(1.0) - math.log(lo)) / (math.log(hi) - math.log(lo)) * (w - 1)))
    k = int(round(p * (w - 1)))
    s = [' '] * w
    s[one] = '|'
    s[k] = '#' if k != one else '#'
    return ''.join(s)


print("=" * 126)
print("C0  LEAKAGE CONTROL -- is the low end of the third-octave set REAL, or Hann leakage from")
print("    the sub-100 Hz road rumble?  1024-pt window at 16 kHz = 15.6 Hz bins.")
print("=" * 126)
# synthetic: a pure 25 Hz tone at the measured sub-100 Hz level, through the SAME window,
# and what it deposits in each third-octave band.
SR, NFFT = 16000, 1024
win = np.hanning(NFFT + 1)[:NFFT]
ff = np.fft.rfftfreq(NFFT, 1 / SR)
sel = [(ff >= c / 2 ** (1 / 6)) & (ff < c * 2 ** (1 / 6)) for c in TOBF]
tt = np.arange(NFFT) / SR
leak = np.zeros(NB)
for f0 in (12.0, 25.0, 45.0, 70.0):          # the real sub-100 Hz content
    x = np.sin(2 * np.pi * f0 * tt)
    x = x - x.mean()
    P = np.abs(np.fft.rfft(x * win)) ** 2
    tot = P.sum()
    leak = np.maximum(leak, np.array([P[m].sum() / tot for m in sel]))
print("  worst-case fraction of a sub-100 Hz tone's TOTAL power that lands in each band:")
print("   " + "".join("%9.0f" % f for f in TOBF[:10]))
print("   " + "".join("%9.1e" % v for v in leak[:10]))
Rr = R['r97']
m97 = A.mask(Rr, True, VLO, VHI)
low = Rr['wide'][m97][:, :6].sum(1).mean()          # 5-100 Hz measured power, engaged <16
print("  measured engaged <16 km/h power, r97:  sub-100 Hz %.3e   100 Hz band %.3e   1 kHz band %.3e"
      % (low, Rr['tob'][m97][:, 0].mean(), Rr['tob'][m97][:, 10].mean()))
print("  => leakage into the 100 Hz band bounded by %.3e (= sub-100 power x %.1e), which is"
      % (low * leak[0], leak[0]))
print("     %.4f of the measured 100 Hz band.  " % (low * leak[0] / Rr['tob'][m97][:, 0].mean())
      + ("LEAKAGE IS NEGLIGIBLE." if low * leak[0] / Rr['tob'][m97][:, 0].mean() < 0.05
         else "*** LEAKAGE IS NOT NEGLIGIBLE -- low bands suspect ***"))
# empirical corroboration: if a band were leakage-dominated it would track the low band ~perfectly
print()
print("  empirical corroboration -- corr(log band, log sub-100 Hz) within r97 engaged <16 km/h:")
lo97 = np.log(np.maximum(Rr['wide'][m97][:, :6].sum(1), 1e-30))
cs = [np.corrcoef(lo97, np.log(np.maximum(Rr['tob'][m97][:, i], 1e-30)))[0, 1] for i in range(NB)]
print("   " + "".join("%8.0f" % f for f in TOBF[:12]))
print("   " + "".join("%8.2f" % c for c in cs[:12]))
print("  a leakage-dominated band would sit at r ~ 1.0.")

print()
print("=" * 126)
print("C1  THE NULL -- within-route split-half on the SAME estimator, r97 and ra4, engaged <16 km/h")
print("=" * 126)
print("%9s %28s %28s" % ('band Hz', 'r97 split-half [2.5, 97.5]', 'ra4 split-half [2.5, 97.5]'))
NULLW = {}
for i in range(0, NB, 2):
    n1 = A.split_half_null(R['r97'], A.mask(R['r97'], True, VLO, VHI), i)
    n2 = A.split_half_null(R['ra4'], A.mask(R['ra4'], True, VLO, VHI), i)
    NULLW[i] = (n1, n2)
    f = lambda n: ("%.3f  [%.3f, %.3f]" % (n['p50'], n['p2_5'], n['p97_5'])) if n else "insufficient"
    print("%9.0f %28s %28s" % (TOBF[i], f(n1), f(n2)))
sp = [max(n[0]['spread'] if n[0] else 1, n[1]['spread'] if n[1] else 1) for n in NULLW.values()]
NULL_SPREAD = float(np.median(sp))
print("  median null 95%% SPREAD (p97.5/p2.5) = %.3f  =>  a between-route amplitude ratio must sit"
      % NULL_SPREAD)
print("  outside roughly [%.2f, %.2f] before it is worth a sentence." %
      (1 / np.sqrt(NULL_SPREAD), np.sqrt(NULL_SPREAD)))

print()
print("=" * 126)
print("C2  THE DECISIVE CONTROL -- ENGAGED / ROLLING-MANUAL amplitude ratio, matched speed, <16 km/h")
print("=" * 126)
print("    Road noise, wind, engine order and HVAC do not know whether LKAS is engaged.")
print("    MANUAL is restricted to v >= %.0f km/h: 73-83 %% of every route's manual <16 km/h time is"
      % A.V_ROLL)
print("    PARKED, and a parked car is not exchangeable with a rolling one.")
print()
avail = [t for t in TAGS if t in R]
print("%9s" % 'band Hz' + "".join("%14s" % A.NAMES[t] for t in avail))
EM = {t: [None] * NB for t in avail}
for i in range(NB):
    row = []
    for t in avail:
        r = A.speed_matched_ratio(R[t], R[t], A.mask(R[t], False, VLO, VHI),
                                  A.mask(R[t], True, VLO, VHI), i, nboot=600, seed=3)
        EM[t][i] = r
        row.append(r)
    print("%9.0f" % TOBF[i] + "".join(
        ("%14s" % ("%.2f[%.2f,%.2f]" % (r['ratio'], r['lo'], r['hi']))) if r else "%14s" % '-'
        for r in row))
print("  ENGAGED/MANUAL amplitude ratio at a common speed mixture.  ~1.0 = the band does not care")
print("  about LKAS.  A band that is >1 on the 6x builds and ~1 on stock is the target signature.")

print()
print("=" * 126)
print("ITEM 2 -- STOCK 1x vs 6x ACROSS 100 Hz - 8 kHz, ENGAGED, < 16 km/h, SPEED-MATCHED")
print("=" * 126)
print("%9s %11s %11s %20s %20s %20s   %s" %
      ('band Hz', 'raw V104/', 'matched', 'V102/STOCK', 'V103/STOCK', 'V104/STOCK', 'V104/STOCK'))
print("%9s %11s %11s %20s %20s %20s   %s" %
      ('', 'STOCK', 'shift', '[95% CI]', '[95% CI]', '[95% CI]', '0.5 <-- 1 --> 3'))
OUT = {}
for i in range(NB):
    r97m = A.mask(R['r97'], True, VLO, VHI)
    raw = np.sqrt(R['ra4']['tob'][A.mask(R['ra4'], True, VLO, VHI)][:, i].mean()
                  / R['r97']['tob'][r97m][:, i].mean())
    cells = []
    for t in SIX:
        r = A.speed_matched_ratio(R['r97'], R[t], r97m, A.mask(R[t], True, VLO, VHI), i)
        cells.append(r)
    OUT[float(TOBF[i])] = {t: (None if c is None else
                               dict(ratio=c['ratio'], lo=c['lo'], hi=c['hi']))
                           for t, c in zip(SIX, cells)}
    s = lambda c: ("%.2f [%.2f, %.2f]" % (c['ratio'], c['lo'], c['hi'])) if c else '-'
    ra4c = cells[-1]
    print("%9.0f %11.2f %11s %20s %20s %20s   %s" %
          (TOBF[i], raw, ("%+.0f%%" % (100 * (ra4c['ratio'] / raw - 1))) if ra4c else '-',
           s(cells[0]), s(cells[1]), s(cells[2]),
           bar(ra4c['ratio']) if ra4c else ''))

print()
print("  'raw' is the UNMATCHED ratio; 'matched shift' is how much the speed re-weighting moved it.")
print("  A large shift means that band is speed-driven and the raw number was an artefact.")

# ---- the separating-band verdict
print()
print("=" * 126)
print("VERDICT -- which bands separate stock from ALL THREE 6x routes, beyond the null?")
print("=" * 126)
lim = np.sqrt(NULL_SPREAD)
hits = []
for i in range(NB):
    c = [OUT[float(TOBF[i])][t] for t in SIX]
    if any(x is None for x in c):
        continue
    lo = min(x['lo'] for x in c)
    r = [x['ratio'] for x in c]
    consistent_up = lo > max(lim, 1.0)
    consistent_dn = max(x['hi'] for x in c) < min(1 / lim, 1.0)
    if consistent_up or consistent_dn:
        hits.append((TOBF[i], r, lo, 'UP' if consistent_up else 'DOWN'))
if hits:
    for f, r, lo, d in hits:
        print("   %6.0f Hz  %-4s  V102 %.2f  V103 %.2f  V104 %.2f   (worst-case CI edge %.2f, "
              "null limit %.2f)" % (f, d, r[0], r[1], r[2], lo, lim))
else:
    print("   NONE.  No third-octave band from 100 Hz to 8 kHz separates stock from all three 6x")
    print("   routes beyond the within-route null.  Reported as a NEGATIVE RESULT, not a failure.")

json.dump({'bands': OUT, 'null_spread': NULL_SPREAD},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_item2.json'), 'w'), indent=1)
print("\n  wrote _scratch/out/_acoustic_item2.json")
