# -*- coding: utf-8 -*-
"""SCORE V141 -- THE r24 PUMP LANE, MEASURED FOR THE FIRST TIME.

WHAT V141 PROBES
----------------
V141 points the 427 probe at gp-0x6ADA, the r24 pump-lane mirror written at the very end of the
aggregator FUN_0003aa2c:
        *(short *)(gp - 0x6ada) = (short)iVar16;      // post-deadband, post-polarity, post-clamp
Nothing in the firmware reads that mirror, so it is free telemetry.  V141 also raises the lane's
deadband, cal 0xC61F6, from Honda's 3 counts to 96.

    wire = min((|lane| * 5) >> 3, 1023)      =>   lane = (wire << 3) / 5
    lane  96 -> wire  60        lane 192 -> wire 120        saturates at |lane| >= 1637

THE THREE OUTCOMES THIS SEPARATES -- AND WHY THE PROBE IS THE POINT
---------------------------------------------------------------------
V140/V141's honest weakness is the DOSE.  96 was centred on an ESTIMATE that the grind is a 1-3 %
of full-scale lane oscillation.  The lane amplitude during a grind has never been measured.

    operator says GRINDING GONE                  -> the dose was right.  Done.
    grinding PERSISTS and the lane is ~ DEAD     -> the r24 lane is NOT the grind source.
                                                    STOP raising this deadband.  Next lever is
                                                    elsewhere entirely.
    grinding PERSISTS and the lane is ACTIVE     -> the lane is live through the deadband.
                                                    Raise it to 192 and re-fly.

Without the probe the middle and bottom cases look identical, and the kit would keep stepping a
deadband on a lane unrelated to the symptom -- the same failure that wasted builds on the
base-assist damper family (V134) earlier in this session.

USAGE:  python rlog-tools/score/score_v141_pump.py <route> [more routes]
        python rlog-tools/score/score_v141_pump.py --baseline r24     (a NON-V141 route, for shape)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

SAR = 3
DEADBAND = 96              # cal 0xC61F6 in V141
LANE_CLAMP = 8192
CREEP = (1.0, 24.0)        # km/h -- the operator's remaining symptom regime
DEAD_FRAC = 0.90           # "lane is dead" if this fraction of engaged creep frames read zero


def wire_to_lane(w):
    return (np.asarray(w, dtype=float) * (1 << SAR)) / 5.0


def load(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  %s: no cache' % tag)
        return None
    z = np.load(p, allow_pickle=True)
    need = ('ab_mt', 'cs_v', 'cc_lat')
    if any(k not in z.files for k in need):
        print('  %s: missing one of %s' % (tag, need))
        return None
    pb = str(np.atleast_1d(z['probe_build'])[0]) if 'probe_build' in z.files else '?'
    mt = np.asarray(z['ab_mt']).astype(float)
    v = np.asarray(z['cs_v']).astype(float)
    lat = np.asarray(z['cc_lat']).astype(float)
    n = min(len(mt), len(v), len(lat))
    return pb, mt[:n], v[:n] * 3.6, lat[:n]


def run(tag, baseline=False):
    r = load(tag)
    if r is None:
        return
    pb, mt, kph, lat = r
    print('\n=== %s  (probe_build %s) ===' % (tag, pb))
    if not baseline and 'V141' not in pb.upper():
        print('  \U0001f6d1 probe_build is %r, not V141 -- the 427 tap is NOT on gp-0x6ADA here,'
              ' so these numbers are a DIFFERENT signal.  Refusing to interpret.' % pb)
        print('     (re-run with --baseline to look at the shape anyway)')
        return
    creep = (kph >= CREEP[0]) & (kph < CREEP[1])
    eng = creep & (lat > 0.5)
    man = creep & (lat < 0.5)
    for nm, m in (('engaged creep', eng), ('manual creep', man)):
        if m.sum() < 200:
            print('  %-14s only %d frames -- too few to read' % (nm, m.sum()))
            continue
        w = np.abs(mt[m])
        lane = wire_to_lane(w)
        zero = float((w == 0).mean())
        sat = float((w >= 1023).mean())
        print('  %-14s n=%6d   wire p50 %5.1f  p90 %6.1f  p99 %6.1f  max %6.1f'
              % (nm, m.sum(), *[np.percentile(w, q) for q in (50, 90, 99)], w.max()))
        print('  %-14s            lane p50 %5.0f  p90 %6.0f  p99 %6.0f   (deadband %d)'
              % ('', *[np.percentile(lane, q) for q in (50, 90, 99)], DEADBAND))
        print('  %-14s            frac exactly ZERO %.4f      frac SATURATED %.4f'
              % ('', zero, sat))
        if nm.startswith('engaged'):
            print()
            if zero >= DEAD_FRAC:
                print('  ✅ VERDICT: the r24 lane is DEAD in engaged creep (%.1f %% of frames zero).'
                      % (100 * zero))
                print('     If grinding PERSISTS, this lane is NOT the source -- STOP raising this')
                print('     deadband and look elsewhere.  If grinding is GONE, the deadband did it.')
            else:
                print('  ⚠ VERDICT: the r24 lane is ACTIVE through the deadband (%.1f %% zero,'
                      ' p90 lane %.0f).' % (100 * zero, np.percentile(lane, 90)))
                print('     If grinding persists, the dose was too SMALL -- next rung is 192,')
                print('     which is still only %.2f %% of the +-%d lane clamp.'
                      % (100.0 * 192 / LANE_CLAMP, LANE_CLAMP))


if __name__ == '__main__':
    bl = '--baseline' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        print(__doc__)
        sys.exit(0)
    for t in args:
        run(t, baseline=bl)
