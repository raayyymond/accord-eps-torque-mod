# -*- coding: utf-8 -*-
"""LKAS AUTHORITY READOUT -- how often is openpilot's command pinned at its rail?

When |sc_tq| sits at +-4096 the controller has no authority left: further lateral error cannot be
answered because there is no more command to give. Rail duty AT MATCHED LATERAL DEMAND is a direct
authority metric and needs no model of the plant.

    python rlog-tools/score/score_authority.py <route-tag> [build]

Compares against route r24 -- the drive on the car (V122, forward gain 6x, Lever B 5244) -- inside
lateral-demand bins, so route content cannot fake a result.

Background and controls: analysis-2020accord/studies/mixer/lkas_command_rail_duty_vs_gain.py
"""
import os
import sys

import numpy as np

RAIL = 4096.0
BINS = [(0.00, 0.15), (0.15, 0.40), (0.40, 0.80), (0.80, 1.60), (1.60, 50.0)]
MIN_N = 200

# route r24 / V122 -- the car. Rail duty % per bin, and the exposure behind each.
BASE_DUTY = np.array([1.16, 2.46, 3.99, 19.47, 22.63])
BASE_N = np.array([39578, 10087, 5893, 1649, 1445])


def load(tag):
    for p in ('analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag),
              '_scratch/cache/%s/%s.npz' % (tag, tag)):
        if os.path.exists(p):
            return np.load(p, allow_pickle=True)
    raise SystemExit('no cache for route %r' % tag)


def duty_by_demand(d):
    """Rail duty and exposure per lateral-demand bin, engaged frames only."""
    lat = d['cc_lat'] > 0.5
    cmd = np.abs(d['sc_tq'].astype(float))[lat]
    vel = np.abs(d['cs_v'].astype(float))[lat]
    cur = np.abs(d['ct_curv'].astype(float))[lat]
    demand = cur * vel ** 2
    duty, n = [], []
    for lo, hi in BINS:
        m = (demand >= lo) & (demand < hi)
        n.append(int(m.sum()))
        duty.append(100.0 * (cmd[m] >= RAIL * 0.999).mean() if m.sum() else np.nan)
    return np.array(duty), np.array(n), lat.sum()


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    tag = argv[1]
    build = argv[2] if len(argv) > 2 else '(build not named)'
    d = load(tag)
    duty, n, n_eng = duty_by_demand(d)

    print('=' * 86)
    print('  LKAS AUTHORITY -- command rail duty by lateral demand   route %s   %s' % (tag, build))
    print('=' * 86)
    print()
    print('  %-22s %s' % ('demand |curv|*v^2', ' '.join('%11s' % ('%.2f-%.2f' % b) for b in BINS)))
    print('  %-22s %s' % ('THIS DRIVE',
                          ' '.join('%10.2f%%' % v if k >= MIN_N else '      .    '
                                   for v, k in zip(duty, n))))
    print('  %-22s %s' % ('   exposure (frames)', ' '.join('%11d' % k for k in n)))
    print('  %-22s %s' % ('r24 = THE CAR (6x)', ' '.join('%10.2f%%' % v for v in BASE_DUTY)))
    rel = np.where(n >= MIN_N, duty / BASE_DUTY, np.nan)
    print('  %-22s %s' % ('   ratio vs the car',
                          ' '.join('%11s' % ('%.2fx' % r if np.isfinite(r) else '.') for r in rel)))
    print()
    print('  engaged frames %d; bins with fewer than %d are suppressed, not estimated.'
          % (n_eng, MIN_N))
    print()

    usable = np.isfinite(rel)
    if not usable.any():
        print('  NOT INTERPRETABLE -- no demand bin reached %d engaged frames. Drive a route with'
              % MIN_N)
        print('  some curvature at speed; creep in a straight line cannot exercise the command.')
        return 0

    print('  PRE-REGISTERED READING (fixed before any V221 drive):')
    print('    ratio <= 0.70 in the 0.15-0.80 bins   the gain step bought authority back')
    print('    ratio 0.70 - 1.40                     no resolvable change')
    print('    ratio >= 1.40                         AUTHORITY GOT WORSE -- fall back to V216/V217,')
    print('                                          which are the same build at 6x')
    mid = rel[1:3][np.isfinite(rel[1:3])]
    if len(mid):
        g = float(np.exp(np.mean(np.log(mid))))
        verdict = ('BOUGHT AUTHORITY BACK' if g <= 0.70 else
                   'GOT WORSE' if g >= 1.40 else 'NO RESOLVABLE CHANGE')
        print()
        print('    0.15-0.80 geometric mean ratio  %.2fx  ->  %s' % (g, verdict))

    print()
    print('  !! WHAT THIS CANNOT SETTLE. The corpus has NO CLEAN 8x POINT: the only 8x route (r95,')
    print('  V101) removed Lever B in the same build, so it is not usable as gain evidence. And a')
    print('  V221 drive changes gain AND Lever B together against the car, so a good result cannot')
    print('  be attributed to either one alone. V216 is the same build at 6x if you want that split.')
    print()
    print('  Rail events are SUSTAINED (p50 475-732 ms) and same-signed between runs, with steer')
    print('  rate 6-21x higher than off-rail -- honest saturation in large manoeuvres, not hunting.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
