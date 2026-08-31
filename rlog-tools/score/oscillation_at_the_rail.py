#!/usr/bin/env python3
r"""IS THERE MORE OSCILLATION WHEN THE COMMAND IS AT ITS RAIL?  The "peak command oscillation" test.

WHY.  Of the operator's three symptoms -- grinding, LKAS authority, peak command oscillation -- the
third is the one this arc has examined least.  There is a specific mechanism for it that has never been
tested: the forward clamp saturates on 13-45 % of engaged frames (openpilot commands past 512 counts,
and the clamp tracks the gain such that 512 is the threshold at EVERY gain).  While saturated the loop
is briefly OPEN -- openpilot asks for more and gets a fixed value -- which is the textbook setup for a
limit cycle at the rail.

THE TEST.  Split engaged frames by whether the command is at the rail, and compare band energy in each
state.  Bands are reported as a FRACTION of total in-window energy so route loudness divides out.

\U0001f6d1 THE CONFOUND, AND IT IS SEVERE.  Saturation is not random: openpilot rails when it is asking
for a lot of steering, which is also when the road is demanding, the driver may be fighting it, and
lateral acceleration is high.  So "more oscillation while railed" is exactly what a pure bystander
would produce.  Two things are therefore reported:

  * the raw split, which is confounded;
  * a CONTROL BAND (12-18 Hz, between the two symptom bands). If the control moves as much as the
    symptom bands, the split is measuring "hard driving" and nothing else.

WHAT A REAL RESULT WOULD LOOK LIKE.  Symptom bands elevated while railed AND the control band flat.
Anything else is not evidence, and this script says so rather than leaving it to the reader.

\U0001f6d1 IF IT IS REAL, IT CUTS AGAINST THE CURRENT ADVICE.  More gain means more headroom before the
rail, hence LESS saturation -- so the gain ladder (V242/V243) would REDUCE this symptom even while it
raises the ratchet. That is a genuine trade the operator would need to make, not a bug.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import glob
import os
import sys

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SAT_THRESHOLD = 512.0        # clamp/gain is identically 512 on every build
WIN_S = 2.0
BANDS = {'ratchet 6-9.5': (6.0, 9.5), 'control 12-18': (12.0, 18.0),
         'grinding 22-30': (22.0, 30.0)}


def windows(path):
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cc_lat', 'co_tqcan'} <= set(z.files):
        return {}
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    c = np.abs(np.asarray(z['co_tqcan'], float))[:n]
    if len(q) < n or len(c) < n:
        return {}
    fs = 1.0 / np.median(np.diff(t))
    tot = np.abs(signal.hilbert(q - q.mean())) + 1e-9
    envs = {}
    for name, (lo, hi) in BANDS.items():
        a, b = lo / (fs / 2), hi / (fs / 2)
        if b >= 1.0:
            return {}
        bb, aa = signal.butter(3, [a, b], btype='band')
        envs[name] = np.abs(signal.hilbert(signal.filtfilt(bb, aa, q - q.mean())))
    w = int(WIN_S * fs)
    out = {k: ([], []) for k in BANDS}      # (railed, free)
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        railed = (c[sl] >= SAT_THRESHOLD).mean() > 0.5
        for k in BANDS:
            frac = float(np.mean(envs[k][sl]) / np.mean(tot[sl]))
            out[k][0 if railed else 1].append(frac)
    return out


def main():
    print('=' * 84)
    print('  IS THERE MORE OSCILLATION WHEN THE COMMAND IS AT ITS RAIL?')
    print('=' * 84)
    print('\n  the clamp tracks the gain so the rail is at 512 counts of openpilot command on EVERY')
    print('  build. While railed the loop is briefly OPEN -- the setup for a limit cycle.\n')
    agg = {k: ([], []) for k in BANDS}
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        try:
            got = windows(p)
        except Exception:
            continue
        for k, (a, b) in got.items():
            agg[k][0].extend(a)
            agg[k][1].extend(b)

    nr = len(agg['ratchet 6-9.5'][0])
    nf = len(agg['ratchet 6-9.5'][1])
    print('  %d railed windows, %d free windows\n' % (nr, nf))
    if nr < 50 or nf < 50:
        print('  too few windows in one arm to compare.')
        return
    print('  %-16s %11s %11s %9s %11s' % ('band', 'railed', 'free', 'ratio', 'Mann-Whitney p'))
    print('  ' + '-' * 64)
    res = {}
    for k in ('ratchet 6-9.5', 'control 12-18', 'grinding 22-30'):
        a, b = np.array(agg[k][0]), np.array(agg[k][1])
        u = stats.mannwhitneyu(a, b, alternative='two-sided')
        ratio = np.median(a) / max(np.median(b), 1e-12)
        res[k] = ratio
        print('  %-16s %11.5f %11.5f %9.3f %11.2e'
              % (k, np.median(a), np.median(b), ratio, u.pvalue))
    print('  ' + '-' * 64)
    print('\n  READING')
    ctl = res['control 12-18']
    sym = max(res['ratchet 6-9.5'], res['grinding 22-30'])
    if sym > 1.15 and abs(ctl - 1.0) < 0.10:
        print('  => SYMPTOM BANDS ELEVATED AT THE RAIL WITH THE CONTROL FLAT. That is a real rail')
        print('     effect, and it CUTS AGAINST the current advice: more gain means more headroom')
        print('     before the rail, so V242/V243 would REDUCE this symptom while raising the ratchet.')
    elif abs(ctl - 1.0) >= 0.10:
        print('  => THE CONTROL BAND MOVED TOO (ratio %.3f). The split is measuring HARD DRIVING, not' % ctl)
        print('     the rail. No conclusion about peak command oscillation can be drawn from this.')
    else:
        print('  => no elevation at the rail beyond the control. The saturation limit-cycle mechanism')
        print('     is NOT supported by this corpus.')


if __name__ == '__main__':
    main()
