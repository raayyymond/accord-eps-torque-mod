#!/usr/bin/env python3
r"""WHICH LANE CARRIES THE RATCHET?  Ranked by 2f0 energy in the clamped 427 channel.

This is the question the whole post-V38 arc has failed to answer.  The record closed it as
unanswerable -- "427 lane ranking is not possible from the existing caches; only r95 carries a decoded
427 magnitude channel; would need re-extraction from the rlogs" -- and that closure had two premises,
both of which have now moved:

  * the extract/ toolchain was DEAD since the 2026-08-26 reorg and is now fixed;
  * `mag427` is RECTIFIED (FUN_00055d80 clamps it to [0, 0x3ff]), which destroys PHASE -- but a
    rectified narrowband signal at f0 puts its ENERGY at 2f0, and the 15.6 Hz engaged excess measures
    3.2-5.6x the 7.8 Hz one on all three ra-routes.  Energy is recoverable.

CAN 427 carried a DIFFERENT LANE on each build, so the corpus is a natural experiment:

    gp-0x6b94   r85 (V100),  r95 (V101)
    gp-0x6b4c   r96 (V102),  r9e (V103)
    gp-0x6b86   ra4 (V104),  ra5 (V105),  ra6 (V106)

For each route: engaged-vs-manual power ratio of `mag427` at 2f0 (14-17.5 Hz), which is where a
7.8 Hz lane oscillation lands after rectification.  The lane whose routes show the largest engaged
excess is carrying the most ratchet-band energy.

READING IT
  * one lane clearly above the others  => where the ratchet is most VISIBLE.  🛑 NOT where it enters:
    that needs the lane's PHASE, and every lane so far measures DAMPING at 6-9 Hz.  See the sibling
    `rank_lanes_liveness_free.py`, which also fixes this script's engaged/manual liveness confound.
  * all comparable                     => the ratchet is not concentrated in any one of these three,
    and the remaining candidates (gp-0x6c2c, gp-0x6abc, gp-0x6b4e) need routes this corpus lacks.

WHAT THIS IS NOT.  Build and 427-source are perfectly confounded -- each lane is observed only on the
builds that happened to probe it, and those builds differ in other ways too.  This is a SCREEN.  It
also cannot rank the three lanes the corpus never probed: rlogs stop at route a6, so V107+ (gp-0x6c2c,
gp-0x6abc, gp-0x6b4e) are unavailable.

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
import glob
import os
import re
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LANE = {'r85': ('V100', 'gp-0x6b94'), 'r95': ('V101', 'gp-0x6b94'),
        'r96': ('V102', 'gp-0x6b4c'), 'r9e': ('V103', 'gp-0x6b4c'),
        'ra4': ('V104', 'gp-0x6b86'), 'ra5': ('V105', 'gp-0x6b86'),
        'ra6': ('V106', 'gp-0x6b86')}
F0 = (6.5, 9.5)
F2 = (14.0, 17.5)          # 2*f0 -- where a rectified 7.8 Hz oscillation lands
MIN_ENG = 2000
SPD_BIN = 5.0


def cache_for(route):
    for pat in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
                os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route,
                             route + '.npz')):
        if os.path.exists(pat):
            return pat
    return None


def measure(route, speed_match):
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
    em, mm = eng.copy(), ~eng
    if speed_match and 'cs_v' in z.files:
        v = np.abs(np.asarray(z['cs_v'], float))[:n] * 3.6
        b = np.floor(v / SPD_BIN).astype(int)
        sh = np.intersect1d(np.unique(b[em]), np.unique(b[mm]))
        if len(sh):
            keep = np.isin(b, sh)
            em, mm = em & keep, mm & keep
    if em.sum() < MIN_ENG or mm.sum() < 500:
        return None
    f, Pe = signal.welch(m[em] - m[em].mean(), fs, nperseg=1024)
    _, Pm = signal.welch(m[mm] - m[mm].mean(), fs, nperseg=1024)
    R = Pe / np.maximum(Pm, 1e-30)
    b0 = (f >= F0[0]) & (f <= F0[1])
    b2 = (f >= F2[0]) & (f <= F2[1])
    return (em.sum() / fs, float(np.median(R[b0])), float(np.median(R[b2])))


def run(speed_match):
    print('  %-6s %-6s %-12s %8s %10s %10s' %
          ('route', 'build', '427 lane', 'eng s', 'f0 ratio', '2f0 ratio'))
    print('  ' + '-' * 60)
    by = collections.defaultdict(list)
    for r in sorted(LANE):
        got = measure(r, speed_match)
        if got is None:
            print('  %-6s %-6s %-12s %8s' % (r, LANE[r][0], LANE[r][1], 'skip'))
            continue
        s, a, b = got
        print('  %-6s %-6s %-12s %8.0f %10.3f %10.3f' % (r, LANE[r][0], LANE[r][1], s, a, b))
        by[LANE[r][1]].append((r, b))
    print('  ' + '-' * 60)
    if not by:
        print('  no route measurable.')
        return None
    print('  %-12s %6s %10s   %s' % ('lane', 'routes', 'median 2f0', 'per route'))
    ranked = sorted(by.items(), key=lambda kv: -np.median([x[1] for x in kv[1]]))
    for lane, rows in ranked:
        med = float(np.median([x[1] for x in rows]))
        print('  %-12s %6d %10.3f   %s' % (lane, len(rows), med,
                                           ', '.join('%s %.2f' % x for x in rows)))
    return ranked


def main():
    print('=' * 88)
    print('  WHICH LANE CARRIES THE RATCHET?   engaged/manual power in the CLAMPED 427 channel')
    print('=' * 88)
    print('\n  [A] ALL ENGAGED FRAMES')
    a = run(False)
    print('\n  [B] SPEED-MATCHED  (the arms differ in speed; this is the record\'s own requirement)')
    b = run(True)
    print()
    if a and b:
        top_a, top_b = a[0][0], b[0][0]
        if top_a == top_b:
            print('  ✅ BOTH passes rank %s highest.' % top_a)
        else:
            print('  \U0001f6d1 THE TWO PASSES DISAGREE (%s vs %s) -- the ranking is NOT robust to'
                  % (top_a, top_b))
            print('     speed matching, so it does not identify a lane.')
    print()
    print('  \U0001f6d1 build and 427-source are perfectly confounded: each lane is seen only on the')
    print('     builds that probed it. A SCREEN, not an attribution. And rlogs stop at route a6, so')
    print('     gp-0x6c2c / gp-0x6abc / gp-0x6b4e (V107+) cannot be ranked at all.')


if __name__ == '__main__':
    main()
