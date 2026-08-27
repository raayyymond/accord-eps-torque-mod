r"""THE SENSITIVITY BOUND, and a CORRECTED NULL -- I broke this once and this file is the repair.

🛑 THE DEFECT, IN MY OWN EARLIER WORK, FOUND BY THIS TEST AND PROVEN NUMERICALLY
   I used a PHASE-SHUFFLED SURROGATE as the null for "is there a modulation LINE at f0".
   Phase shuffling preserves the magnitude spectrum EXACTLY:
       |X| at 21.7 Hz -- original 924.9376, surrogate 924.9376, ratio 1.000000
   so an injected line survives into the surrogate untouched and the test has NO POWER against a
   spectral peak.  It is a valid null for PHASE / waveform structure and no null at all for this.
   The symptom that exposed it: injecting a 35 % modulation -- enormous and unmistakably audible --
   produced a detection rate of 0.11.  A detector that cannot see 35 % is not a detector.
   ⇒ **Every "surrogate [2.5, 97.5]" column I reported for an AM/modulation excess is VOID.**
     What survives untouched: the engaged-vs-manual ratios, and the label-PERMUTATION null
     (p = 0.890), which never used surrogates.

THE CORRECT NULL, used here.  The excess statistic is (band power)/(fitted background).  Under
"no line" it is ~1 with a spread set by the episode length and the envelope's own roughness.  Get
that spread EMPIRICALLY from CONTROL FREQUENCIES in the same episode -- same length, same noise,
same spectral slope, no injected line -- and threshold at its p97.5.

This file then does two things at once:
   1. the CORRECTED real-data verdict on grinds #1/#2/#3, and
   2. the DETECTION LIMIT: the modulation depth at which this instrument would have seen one.
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

FSE = 500.0
VLO, VHI = 0.0, 16.0
TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4', 'r95']
DEPTHS = [0.0, 0.02, 0.05, 0.10, 0.20, 0.35, 0.60]
RATES = [(21.0, 22.5, 'grind #1 ~21.7'), (43.0, 45.0, 'grind #2 ~44'),
         (45.0, 47.0, 'grind #3 ~46')]
CTRL = [15.5, 17.5, 19.0, 25.0, 31.0, 33.5, 36.0, 38.5, 51.0, 53.5, 56.0, 58.5]


def am_at(x, lo, hi, nper=1024):
    if len(x) < nper:
        return None
    f, p = signal.welch(x - x.mean(), fs=FSE, nperseg=nper, noverlap=nper // 2, detrend='linear')
    tgt = (f >= lo) & (f <= hi)
    bg = ((f >= 6) & (f <= 70)) & ~((f >= lo - 4) & (f <= hi + 4))
    if tgt.sum() < 2 or bg.sum() < 10:
        return None
    cf = np.polyfit(np.log(f[bg]), np.log(p[bg]), 1)
    return float(np.mean(p[tgt] / np.exp(np.polyval(cf, np.log(f[tgt])))))


def episodes_of(t, engaged=True, min_s=4.0):
    g = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s_grind.npz' % t))
    c = np.load(os.path.join(A.HERE, '_cache_%s' % t, '%s.npz' % t), allow_pickle=True)
    ct = c['t'].astype(float)
    te = g['t_env'].astype(float)
    eng = np.interp(te, ct, (c['cc_lat'].astype(float) > 0.5).astype(float)) > 0.5
    v = np.interp(te, ct, c['v_rear'].astype(float)) * 3.6
    j = int(np.flatnonzero((g['env_f'][:, 0] == 300) & (g['env_f'][:, 1] == 3000))[0])
    m = (eng if engaged else ~eng) & (v >= VLO) & (v < VHI) & ~g['splice'].astype(bool)
    if not engaged:
        m = m & (v >= A.V_ROLL)
    i = np.flatnonzero(np.diff(m.astype(np.int8)) != 0) + 1
    b = np.concatenate(([0], i, [len(m)]))
    return [g['env'][int(b[k]):int(b[k + 1]), j].astype(float) for k in range(len(b) - 1)
            if m[b[k]] and (b[k + 1] - b[k]) / FSE >= min_s]


EPS = {t: episodes_of(t) for t in TAGS}
EPM = {t: episodes_of(t, False) for t in TAGS}
for t in TAGS:
    print("  %-5s %-9s engaged %2d eps / %6.1f s   rolling-manual %2d eps / %6.1f s"
          % (t, A.NAMES[t], len(EPS[t]), sum(len(x) for x in EPS[t]) / FSE,
             len(EPM[t]), sum(len(x) for x in EPM[t]) / FSE))

# ---- the null distribution of the excess statistic, from control frequencies
print()
print("=" * 116)
print("THE CORRECTED NULL -- excess statistic at %d CONTROL frequencies where no line is claimed,"
      % len(CTRL))
print("   pooled over engaged episodes.  Same episode lengths, same envelope, no injected line.")
print("=" * 116)
NULLD = {}
for t in TAGS:
    v = []
    for x in EPS[t]:
        for f0 in CTRL:
            e = am_at(x, f0 - 0.75, f0 + 0.75)
            if e is not None:
                v.append(e)
    NULLD[t] = np.array(v)
    if len(v) > 10:
        print("  %-5s %-9s n=%4d   median %.3f   p95 %.3f   **p97.5 %.3f**   max %.3f"
              % (t, A.NAMES[t], len(v), np.median(v), np.percentile(v, 95),
                 np.percentile(v, 97.5), max(v)))

print()
print("=" * 116)
print("1. CORRECTED REAL-DATA VERDICT -- is there a line at each grind rate, engaged <16 km/h?")
print("=" * 116)
V = {}
for lo, hi, lab in RATES:
    print("\n  ---- %s (%s Hz) ----" % (lab, "%g-%g" % (lo, hi)))
    print("%-6s %-9s %8s %12s %12s %12s %10s" %
          ('route', 'build', 'gain', 'ENG excess', 'null p97.5', 'MAN excess', 'verdict'))
    for t in TAGS:
        if len(NULLD[t]) < 10:
            continue
        ev = [am_at(x, lo, hi) for x in EPS[t]]
        ev = [q for q in ev if q is not None]
        mv = [am_at(x, lo, hi) for x in EPM[t]]
        mv = [q for q in mv if q is not None]
        if not ev:
            continue
        thr = float(np.percentile(NULLD[t], 97.5))
        pt = float(np.mean(ev))
        V.setdefault(lab, {})[t] = dict(eng=pt, thr=thr,
                                        man=float(np.mean(mv)) if mv else None)
        print("%-6s %-9s %8.0fx %12.3f %12.3f %12s %10s"
              % (t, A.NAMES[t], A.GAIN[t], pt, thr,
                 ("%.3f" % np.mean(mv)) if mv else '-',
                 'LINE' if pt > thr else 'null'))

print()
print("=" * 116)
print("2. DETECTION LIMIT -- inject a known modulation into the REAL engaged envelope and ask")
print("   at what depth this instrument would have caught it.  Fraction of episodes clearing the")
print("   corrected null threshold.")
print("=" * 116)
LIM = {}
for lo, hi, lab in RATES:
    print("\n  ---- %s ----" % lab)
    print("%-6s %-9s" % ('route', 'build') + "".join("%9s" % ("m=%.0f%%" % (100 * d))
                                                     for d in DEPTHS))
    for t in ['r97', 'ra4', 'r9e']:
        thr = float(np.percentile(NULLD[t], 97.5))
        row = []
        for d in DEPTHS:
            hit = n = 0
            for x in EPS[t]:
                tt = np.arange(len(x)) / FSE
                y = x * (1 + d * np.sin(2 * np.pi * (0.5 * (lo + hi)) * tt))
                e = am_at(y, lo, hi)
                if e is None:
                    continue
                n += 1
                hit += int(e > thr)
            row.append(hit / n if n else np.nan)
        LIM.setdefault(lab, {})[t] = row
        print("%-6s %-9s" % (t, A.NAMES[t]) + "".join(("%9.2f" % x) if np.isfinite(x)
                                                      else "%9s" % '-' for x in row))
print()
print("  m=0 %% is the detector's FALSE-POSITIVE rate on real data (should sit near 0.025).")
print("  The first depth reaching ~0.8 is the DETECTION LIMIT: a modulation that deep WOULD have")
print("  been seen, so its absence in column m=0 %% is a real bound, not an absence of a number.")

json.dump({'null_p97_5': {t: float(np.percentile(NULLD[t], 97.5)) for t in TAGS
                          if len(NULLD[t]) > 10},
           'verdict': V, 'limit': LIM, 'depths': DEPTHS},
          open(os.path.join(A.HERE, '_scratch/out/_acoustic_sensitivity.json'), 'w'), indent=1, default=float)
print("\n  wrote _scratch/out/_acoustic_sensitivity.json")
