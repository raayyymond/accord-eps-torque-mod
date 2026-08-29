# -*- coding: utf-8 -*-
"""Measure the gp-0x6b26 SATURATION DUTY that the current 3.0x dose implies.

V90 repointed CAN 427 MOTOR_TORQUE to gp-0x6b26 (0x55DF2 6894->da94) and flew route 77 with
HONDA's K.  V91 kept the same source and packer and flew route 78 at x1.5.  So r77 and r78
are the same signal at two known gains -- a natural experiment.

The open question the record leaves: at the flown 3.0x, gp-0x6b26 saturates its +-511 clamp
whenever the STOCK-referred value exceeds ~170.  V76 only ever tested >448 (0/63,477).  This
measures the whole distribution instead of one threshold.

A saturating -K*alpha becomes sign(alpha)*511 -- a RELAY, which is V80's failure mode.
"""
import os, sys
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CLAMP = 511.0


def load(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return None
    z = np.load(p, allow_pickle=True)
    d = {}
    for k in ('ab_mt', 'ab_t1ab', 'cc_lat', 'cs_v', 'cs_tq', 't', 'probe_build', 'ab_src'):
        if k in z.files:
            d[k] = np.asarray(z[k])
    return d


for tag in ('r77', 'r78', 'r79'):
    d = load(tag)
    if d is None or 'ab_mt' not in d:
        print('%s: no ab_mt' % tag)
        continue
    mt = np.asarray(d['ab_mt']).astype(float)
    mt = mt[np.isfinite(mt)]
    pb = d.get('probe_build')
    lab = ''
    try:
        lab = str(np.asarray(pb).ravel()[0])[:40]
    except Exception:
        pass
    src = ''
    try:
        u = np.unique(np.asarray(d.get('ab_src')).ravel())
        src = 'ab_src=%s' % u[:4]
    except Exception:
        pass
    print('\n=== %s  n=%d  probe_build=%r  %s' % (tag, len(mt), lab, src))
    if len(mt) == 0:
        continue
    a = np.abs(mt)
    print('  ab_mt      min %8.1f  max %8.1f  p50 %7.2f  p95 %7.2f  p99 %7.2f  p99.9 %7.2f'
          % (mt.min(), mt.max(), np.percentile(a, 50), np.percentile(a, 95),
             np.percentile(a, 99), np.percentile(a, 99.9)))
    # engaged subset
    if 'cc_lat' in d:
        lat = np.asarray(d['cc_lat']).astype(float)
        n = min(len(lat), len(mt))
        e = np.abs(mt[:n])[lat[:n] > 0.5]
        if len(e) > 100:
            print('  engaged    n=%-7d p50 %7.2f  p95 %7.2f  p99 %7.2f  max %7.2f'
                  % (len(e), np.percentile(e, 50), np.percentile(e, 95),
                     np.percentile(e, 99), e.max()))

print('\n' + '=' * 78)
print('SATURATION EXTRAPOLATION -- what the 3.0x dose implies')
print('=' * 78)
r77 = load('r77')
if r77 is None or 'ab_mt' not in r77:
    print('r77 unavailable; cannot extrapolate')
    sys.exit(0)
mt = np.abs(np.asarray(r77['ab_mt']).astype(float))
mt = mt[np.isfinite(mt)]
lat = np.asarray(r77['cc_lat']).astype(float) if 'cc_lat' in r77 else None
if lat is not None:
    n = min(len(lat), len(mt))
    eng = mt[:n][lat[:n] > 0.5]
else:
    eng = mt
print('r77 carries gp-0x6b26 at HONDA\'s K (V90 base = V89; V91 introduced the x1.5).')
print('engaged frames: %d' % len(eng))
print('\nThe CAN packer applies an unknown right shift s, so report EVERY plausible s:')
print('%3s %12s %14s %14s %14s' % ('s', 'implied max', 'sat duty @1.0x', '@1.5x', '@3.0x'))
for s in (0, 1, 3, 4, 5):
    v = eng * (2 ** s)                      # undo the packer shift -> gp-0x6b26 counts
    d10 = float(np.mean(v >= CLAMP))
    d15 = float(np.mean(v * 1.5 >= CLAMP))
    d30 = float(np.mean(v * 3.0 >= CLAMP))
    print('%3d %12.1f %13.4f%% %13.4f%% %13.4f%%'
          % (s, v.max(), 100 * d10, 100 * d15, 100 * d30))
print('\nEVERY row is the same measurement under a different packer assumption.')
print('The load-bearing question is whether the @3.0x column is NEGLIGIBLE for the s that')
print('is actually in force.  s is pinned by the max: gp-0x6b26 is HARD-CLAMPED to +-511,')
print('so the only admissible s are those whose implied max does NOT exceed 511.')
adm = [s for s in (0, 1, 3, 4, 5) if (eng * (2 ** s)).max() <= CLAMP * 1.02]
print('  admissible s (implied max <= 511): %s' % (adm if adm else 'NONE -- ab_mt is not gp-0x6b26'))
if adm:
    s = max(adm)
    v = eng * (2 ** s)
    print('\n  taking the LARGEST admissible s = %d (the tightest, least favourable case):' % s)
    for nm, g in (('Honda 1.0x', 1.0), ('V91   1.5x', 1.5), ('FLOWN 3.0x', 3.0)):
        print('    %-11s saturation duty %8.4f %%   p99 = %6.1f  (clamp 511)'
              % (nm, 100 * float(np.mean(v * g >= CLAMP)), np.percentile(v * g, 99)))
