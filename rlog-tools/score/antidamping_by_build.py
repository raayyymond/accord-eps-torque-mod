#!/usr/bin/env python3
r"""HAS ANY BUILD EVER MOVED THE 6-9 Hz ANTI-DAMPING?  Per-build Re(Z), coherence-controlled.

WHY THIS IS THE RIGHT TEST NOW.  The 6-9 Hz anti-damping measures as LINEAR and amplitude-independent
(~ -56 engaged vs -0.81 manual, 31/31 routes; see `rez_dilution_control.py` for the coherence control
that established this and retracted the earlier "damping runs out" reading).  A LINEAR,
engagement-caused effect must live in some lane -- and if any flown build's lever touched that lane, it
should have MOVED this number.  So ranking builds by Re(Z) at 6-9 Hz is a direct search for the source,
using the cross-build dose-response this kit trusts most.

    a build well off the pack  =>  its lever touched the anti-damping's lane. That names the target.
    every build the same       =>  no lever flown since V90 has come near it, which is itself the
                                   strongest statement yet about where NOT to look.

METHOD.  Engaged 2 s windows, band 6-9.5 Hz, `tq` against `cs_rate` -- both NON-RECTIFIED, so unlike
every 427-derived phase this is actually measured.  \U0001f6d1 HIGH-COHERENCE WINDOWS ONLY (>= 0.6):
coherence rises with oscillation amplitude, and pooling low-coherence windows imports exactly the
regression dilution that produced a retracted mechanism once already in this arc.  The control band
22-30 Hz is reported alongside, where a genuine amplitude-dependent nonlinearity does live.

\U0001f6d1 CONFOUNDED BY CONSTRUCTION, like every cross-build comparison in this corpus: builds differ
in more than one cell, routes differ in road and speed, and one route per build is the norm.  This is a
SCREEN for a large effect, not an attribution.

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

import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = {'r77': 'V90', 'r78': 'V91', 'r7d': 'V94', 'r7e': 'V96', 'r7f': 'V96',
         'r80': 'V97', 'r81': 'V98', 'r82': 'V99', 'r85': 'V100', 'r95': 'V101',
         'r96': 'V102', 'r9e': 'V103', 'ra4': 'V104', 'ra5': 'V105', 'ra6': 'V106',
         'r1e': 'V107', 'r21': 'V111', 'r22': 'V112', 'r24': 'V122'}
BAND = (6.0, 9.5)
CTL = (22.0, 30.0)
WIN_S = 2.0
MIN_COH = 0.60
MIN_WIN = 15


def cache_for(route):
    for p in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
              os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route, route + '.npz')):
        if os.path.exists(p):
            return p
    return None


def measure(path, band):
    z = np.load(path, allow_pickle=True)
    if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
        return None
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    r = np.asarray(z['cs_rate'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    if len(q) < n or len(r) < n:
        return None
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return None
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    w = int(WIN_S * fs)
    vals = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        cxy = np.mean(qq * np.conj(rr))
        coh = float(np.abs(cxy) ** 2 / max(den * float(np.mean(np.abs(qq) ** 2)), 1e-30))
        if coh < MIN_COH:
            continue
        vals.append(float((cxy / den).real))
    if len(vals) < MIN_WIN:
        return None
    return float(np.median(vals)), len(vals)


def main():
    print('=' * 84)
    print('  HAS ANY BUILD MOVED THE 6-9 Hz ANTI-DAMPING?   coherence >= %.2f windows only' % MIN_COH)
    print('=' * 84)
    print()
    print('  %-6s %-7s %12s %8s %12s %8s' %
          ('route', 'build', 'Re(Z) 6-9', 'wins', 'Re(Z) 22-30', 'wins'))
    print('  ' + '-' * 58)
    rows = []
    for r in sorted(BUILD, key=lambda k: int(BUILD[k][1:])):
        p = cache_for(r)
        if not p:
            continue
        a = measure(p, BAND)
        c = measure(p, CTL)
        if not a:
            continue
        rows.append((r, BUILD[r], a[0]))
        print('  %-6s %-7s %12.2f %8d %12s %8s' %
              (r, BUILD[r], a[0], a[1],
               ('%.2f' % c[0]) if c else '--', ('%d' % c[1]) if c else '--'))
    print('  ' + '-' * 58)
    if not rows:
        print('  nothing measurable.')
        return
    v = np.array([x[2] for x in rows])
    med, sd = float(np.median(v)), float(np.std(v))
    print('\n  median %+.2f   sd %.2f   range %+.2f .. %+.2f over %d builds'
          % (med, sd, v.min(), v.max(), len(rows)))
    print('\n  %-6s %-7s %10s %9s' % ('route', 'build', 'Re(Z)', 'z-score'))
    for r, b, x in sorted(rows, key=lambda t: t[2]):
        z = (x - med) / sd if sd > 0 else 0.0
        flag = '  <== OFF THE PACK' if abs(z) >= 2.0 else ''
        print('  %-6s %-7s %10.2f %9.2f%s' % (r, b, x, z, flag))
    if not any(abs((x - med) / sd) >= 2.0 for _, _, x in rows) or sd == 0:
        print('\n  => NO BUILD IS OFF THE PACK. No lever flown across this span has come near the')
        print('     6-9 Hz anti-damping -- consistent with the standing result that nothing has')
        print('     moved the ratchet, and it now has a mechanism-level statement behind it.')
    print('\n  \U0001f6d1 CONFOUNDED: builds differ in more than one cell and mostly one route each.')
    print('     A SCREEN for a large effect, not an attribution.')


if __name__ == '__main__':
    main()
