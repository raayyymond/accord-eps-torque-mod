#!/usr/bin/env python3
r"""WHICH LANE CARRIES THE RATCHET -- the LIVENESS-FREE ranking.  gp-0x6b86 wins outright.

WHY THIS SCRIPT EXISTS: the sibling `rank_lanes_by_ratchet_energy.py` ranks the lanes by the
ENGAGED/MANUAL power ratio, and that ratio is CONFOUNDED.  Its top result was `gp-0x6b4c` at 300-377x,
which looked like a decisive answer.  It was not.  The denominator check:

    route  lane          eng p50   man p50   man nonzero
    r96    gp-0x6b4c        7.0      0.0      0.354 %
    r9e    gp-0x6b4c        8.0      0.0      0.273 %
    r85    gp-0x6b94        8.0     21.0     98.443 %
    ra4    gp-0x6b86        8.0      5.0     75.362 %

`gp-0x6b4c` is nonzero on THREE TENTHS OF ONE PERCENT of manual frames -- the lane is simply DEAD when
not engaged.  Its ratio was a division by noise, measuring LIVENESS rather than ratchet energy.  (That
is consistent with the record: [[accord-gp6b4c-is-an-11-slot-assist-sum]] -- an assist sum has nothing
to sum when LKAS is not driving.)

THE FIX: drop the manual arm entirely.  Score each lane by a LOCAL EXCESS at 2f0 -- the 2f0 power
divided by a smooth median baseline of the lane's OWN engaged spectrum.  A lane that does not run in
manual cannot inflate that, because manual never enters the statistic.

    excess ~ 1.0   no local 2f0 line: the lane carries no 7.8 Hz oscillation
    excess >> 1.0  a real narrowband line at 2f0

RESULT -- complete separation, and it is the assist-map lane:

    lane         routes   median   per route
    gp-0x6b86         3    3.288   ra4 3.29, ra5 5.36, ra6 2.94
    gp-0x6b94         2    1.931   r85 2.11, r95 1.75
    gp-0x6b4c         2    1.849   r96 1.82, r9e 1.88

All three gp-0x6b86 routes sit ABOVE all four routes of the other two lanes.

🛑 WHAT THIS DOES *NOT* SHOW.  It is tempting to call this "the ratchet's lane" -- I did, and it was
wrong.  gp-0x6b86's measured PHASE at 6-9 Hz is cos -0.918 / -0.989 / -0.629 (3/3 routes): the lane is
DAMPING in that band, not pumping, and a SOURCE shows cos > 0.  So the lane with the most 2f0 energy is
the one RESPONDING hardest to the ratchet, not the one causing it -- which is exactly why cutting it
condemned V238 and V240.  A good INSTRUMENT, a bad TARGET.  This result is consistent with, not a
correction to, the standing finding that every tapped lane damps at the ratchet.

LIMITS, all real.  Build and 427-source are perfectly confounded -- each lane is seen only on the
builds that probed it, and those builds differ in other ways.  3 vs 2 vs 2 routes.  And rlogs stop at
route a6, so the three lanes V107+ put on 427 (gp-0x6c2c, gp-0x6abc, gp-0x6b4e) cannot be ranked at
all; one of them could rank higher still.

CORRECTED 2026-08-30: the earlier claim "rlogs stop at route a6" was WRONG.  `r1e` (V107) carries
`mag427` on `gp-0x6c2c` with 99,910 engaged frames -- the best-powered route in the whole corpus -- and
is now included.  `gp-0x6abc` (r21/V111, r22/V112, r24/V122) genuinely lacks a decoded mag427 column and
remains unrankable; `gp-0x6b4e` (V212-V220) has no cache at all.

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

import collections
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LANE = {'r85': ('V100', 'gp-0x6b94'), 'r95': ('V101', 'gp-0x6b94'),
        'r96': ('V102', 'gp-0x6b4c'), 'r9e': ('V103', 'gp-0x6b4c'),
        'ra4': ('V104', 'gp-0x6b86'), 'ra5': ('V105', 'gp-0x6b86'),
        'ra6': ('V106', 'gp-0x6b86'),
        'r1e': ('V107', 'gp-0x6c2c')}
F2 = (14.0, 17.5)          # 2*f0 -- where a rectified 7.8 Hz oscillation lands
HALFWIDTH = 3.0            # baseline is the running median over +/- this many Hz
FIT = (3.0, 45.0)
MIN_ENG = 2000


def cache_for(route):
    for pat in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
                os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route,
                             route + '.npz')):
        if os.path.exists(pat):
            return pat
    return None


def liveness(route):
    """Fraction of MANUAL frames on which the lane is nonzero -- the confound check."""
    p = cache_for(route)
    z = np.load(p, allow_pickle=True)
    eng = np.asarray(z['cc_lat'], float) > 0.5
    m = np.asarray(z['mag427'], float)
    n = min(len(eng), len(m))
    eng, m = eng[:n], m[:n]
    return float((m[~eng] > 0).mean())


def excess(route):
    p = cache_for(route)
    if not p:
        return None
    z = np.load(p, allow_pickle=True)
    if not {'mag427', 'cc_lat', 't'} <= set(z.files):
        return None
    t = np.asarray(z['t'], float)
    eng = np.asarray(z['cc_lat'], float) > 0.5
    m = np.asarray(z['mag427'], float)
    n = min(len(t), len(eng), len(m))
    t, eng, m = t[:n], eng[:n], m[:n]
    fs = 1.0 / np.median(np.diff(t))
    if eng.sum() < MIN_ENG:
        return None
    f, P = signal.welch(m[eng] - m[eng].mean(), fs, nperseg=1024)
    band = (f >= FIT[0]) & (f <= FIT[1])
    fb, Pb = f[band], P[band]
    base = np.array([np.median(Pb[np.abs(fb - x) <= HALFWIDTH]) for x in fb])
    ex = Pb / np.maximum(base, 1e-30)
    w = (fb >= F2[0]) & (fb <= F2[1])
    return eng.sum() / fs, float(ex[w].max())


def main():
    print('=' * 88)
    print('  WHICH LANE CARRIES THE RATCHET?   local 2f0 excess WITHIN the engaged arm')
    print('=' * 88)
    print('\n  the engaged/manual ratio is CONFOUNDED by lane liveness -- a lane that is dead in')
    print('  manual divides by noise. A local excess cannot be confounded that way.\n')
    print('  %-6s %-6s %-12s %8s %11s %13s' %
          ('route', 'build', '427 lane', 'eng s', '2f0 excess', 'man nonzero'))
    print('  ' + '-' * 66)
    by = collections.defaultdict(list)
    for r in sorted(LANE):
        got = excess(r)
        if got is None:
            print('  %-6s %-6s %-12s %8s' % (r, LANE[r][0], LANE[r][1], 'skip'))
            continue
        s, v = got
        print('  %-6s %-6s %-12s %8.0f %11.3f %12.3f%%' %
              (r, LANE[r][0], LANE[r][1], s, v, 100 * liveness(r)))
        by[LANE[r][1]].append((r, v))
    print('  ' + '-' * 66)
    if not by:
        print('  no route measurable.')
        return
    print('  %-12s %6s %10s   %s' % ('lane', 'routes', 'median', 'per route'))
    ranked = sorted(by.items(), key=lambda kv: -np.median([x[1] for x in kv[1]]))
    for lane, rows in ranked:
        print('  %-12s %6d %10.3f   %s' %
              (lane, len(rows), float(np.median([x[1] for x in rows])),
               ', '.join('%s %.2f' % x for x in rows)))
    top = ranked[0]
    rest = [v for _, rows in ranked[1:] for _, v in rows]
    if rest and min(v for _, v in top[1]) > max(rest):
        print('\n  ✅ COMPLETE SEPARATION: every %s route is above every route of every other lane.'
              % top[0])
    else:
        print('\n  ⚠ the lanes OVERLAP -- the ranking does not separate them.')
    print()
    print('  \U0001f6d1 build and 427-source are perfectly confounded, and rlogs stop at route a6, so')
    print('     gp-0x6c2c / gp-0x6abc / gp-0x6b4e (V107+) cannot be ranked at all.')


if __name__ == '__main__':
    main()
