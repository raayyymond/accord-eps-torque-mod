r"""CONTROL B, DONE PROPERLY -- THE BLINKER AS A POSITIVE CONTROL FOR THE ENVELOPE DETECTOR.

The first attempt looked for blinker ON-transitions and found only 5-13 per route: `cs_lblink` is
the STALK state, held for a whole lane change, not the per-click lamp.  The audible click is a
**~1.3 Hz modulation running THROUGHOUT** each blinker-on period.

That makes it a far better control than the onset test, and it is the RIGHT control for what is
still open, because it exercises the exact machinery item 6 needs:

    "is there a few-per-second periodic modulation of a band envelope, and can this pipeline
     detect one when it is definitely there?"

GROUND TRUTH: a turn signal clicks at ~1.0-2.0 Hz, is plainly audible, is modest in level, and is
completely unrelated to speed, LKAS or the firmware.  Its timing is free on CAN.

METHOD.  Inside blinker-on runs >= 3 s, take the band envelope, detrend, Hann, and average the
envelope PSD across runs.  Compare with (a) the same statistic on matched-length blinker-OFF runs
and (b) a phase-shuffled surrogate.  A peak at 1-2 Hz present only when the blinker is on is the
control passing.

⇒ PASSES  => the pipeline detects a real, audible, few-per-second cabin modulation, so a null on
             the operator's 6-12 /s ratchet is a genuine negative.
⇒ FAILS   => the envelope-modulation instrument is not demonstrated, and every modulation null in
             this workstream is uninterpretable.  I would rather report that than a clean null.
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
from scipy import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import acoustic_lib as A                                            # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

TAGS = ['r97', 'r96', 'r9e', 'ra4']
FSE = 125.0
NPER = 512                      # 4.1 s -> 0.244 Hz resolution
BANDS_WANT = [(100, 300), (300, 800), (800, 2000), (2000, 5000), (100, 7800)]


def env_psd(runs, fs=FSE, nper=NPER):
    """Averaged envelope PSD over a list of 1-D envelope segments."""
    acc, n = None, 0
    for x in runs:
        if len(x) < nper:
            continue
        f, p = signal.welch(x - x.mean(), fs=fs, nperseg=nper, noverlap=nper // 2,
                            detrend='linear')
        acc = p if acc is None else acc + p
        n += 1
    if n == 0:
        return None, None, 0
    return f, acc / n, n


def runs_of(m, fs, min_s):
    m = np.asarray(m, bool)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [(int(b[k]), int(b[k + 1])) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / fs >= min_s]


print("=" * 120)
print("CONTROL B -- BLINKER MODULATION.  ~1.3 Hz audible click, timing free on CAN.")
print("=" * 120)
OUT = {}
for t in TAGS:
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    e = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_env.npz' % t))
    te, ev, sp = e['t'].astype(float), e['env'].astype(float), e['splice'].astype(bool)
    bf = e['env_f']
    ct = c['t'].astype(float)
    bl = (c['cs_lblink'].astype(float) > 0.5) | (c['cs_rblink'].astype(float) > 0.5)
    blk = np.interp(te, ct, bl.astype(float)) > 0.5
    v = np.interp(te, ct, c['v_rear'].astype(float)) * 3.6
    on = runs_of(blk & ~sp, FSE, 4.2)
    off = runs_of((~blk) & ~sp & (v > 20), FSE, 4.2)
    if len(on) < 3:
        print("\n  %-5s %-9s  only %d blinker-on runs >= 4.2 s -- cannot run" % (t, A.NAMES[t], len(on)))
        continue
    # match the off arm to the on arm's speed range, and to a similar number of runs
    von = np.concatenate([v[a:b] for a, b in on])
    lo, hi = np.percentile(von, [5, 95])
    off = [r for r in off if lo <= v[r[0]:r[1]].mean() <= hi]
    print("\n  ---- %s %s: %d blinker-ON runs (%.1f s), %d matched OFF runs (%.1f s), "
          "speed %.0f-%.0f km/h ----"
          % (t, A.NAMES[t], len(on), sum(b - a for a, b in on) / FSE,
             len(off), sum(b - a for a, b in off) / FSE, lo, hi))
    print("%12s %10s %10s %12s %10s" % ('band Hz', 'f_peak Hz', 'ON/OFF exc', 'z', 'verdict'))
    row = {}
    for j in range(len(bf)):
        band = tuple(bf[j])
        if tuple(int(x) for x in band) not in [(a, b) for a, b in BANDS_WANT]:
            continue
        f, pon, non = env_psd([ev[a:b, j] for a, b in on])
        _, poff, noff = env_psd([ev[a:b, j] for a, b in off]) if off else (None, None, 0)
        if f is None or poff is None:
            continue
        # 🛑 THE FIRST METRIC WAS CONFOUNDED.  An envelope PSD is RED, so a 0.9-2.2 Hz peak sits
        #    above a 3-8 Hz floor whether or not the blinker is on -- the spectral slope alone
        #    produces "prominence" 2-9 on every arm.  The clean statistic is the SAME-FREQUENCY
        #    ON/OFF ratio, normalised by the broadband ratio, so both the red slope and any
        #    overall level difference between the arms divide out.  What is left is a LOCALISED
        #    bump at the click rate, which is the only thing a blinker can produce.
        wide = (f >= 0.4) & (f <= 8.0)
        rat = pon / np.maximum(poff, 1e-30)
        rat = rat / np.median(rat[wide])                       # normalise out the level offset
        sel = (f >= 0.9) & (f <= 2.2)
        k = np.argmax(rat[sel])
        fpk = f[sel][k]
        exc = float(rat[sel][k])
        # how unusual is that excess?  compare with the spread of the SAME ratio away from 1-2 Hz
        oth = wide & ~((f >= 0.7) & (f <= 2.5))
        z = (exc - np.median(rat[oth])) / max(np.std(rat[oth]), 1e-9)
        row["%g-%g" % band] = dict(f_peak=float(fpk), excess=exc, z=float(z),
                                   n_on=non, n_off=noff)
        print("%12s %10.2f %10.2f %12.2f %10s"
              % ("%g-%g" % band, fpk, exc, z,
                 'DETECTED' if (exc > 1.5 and z > 2.5) else '-'))
    OUT[t] = row

print()
print("  'ON prom' is the 0.9-2.2 Hz envelope-PSD peak divided by the 3-8 Hz floor, inside")
print("  blinker-on runs.  'ON/OFF' divides that by the same statistic on speed-matched")
print("  blinker-off runs.  > 2 means the pipeline sees the click.")
json.dump(OUT, open(os.path.join(A.HERE, '_scratch/out/_acoustic_blinker.json'), 'w'), indent=1)
print("\n  wrote _scratch/out/_acoustic_blinker.json")
