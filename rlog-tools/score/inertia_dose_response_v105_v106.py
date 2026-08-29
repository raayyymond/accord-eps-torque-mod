# -*- coding: utf-8 -*-
"""
A MEASURED, UNREAD DOSE-RESPONSE ON THE INERTIA CELL -- from caches, no drive.

V106 = V105BASE-GP6B26.X3.0.D7A5C-D7A6C: a SINGLE-VARIABLE change that TRIPLES the inertia term.
Both flew (routes a5 and a6) and both are cached.  Their caves share rung b5:

    b5 = ( |gp-0x6ae2| >= |gp-0x6b26| )     modelled friction vs the INERTIA term

Tripling |inertia| must LOWER P(friction >= inertia).  That is a directional prediction the pair can
test, and 0xD7A5C is exactly the cell V196/V199/V202 HALVE -- so this says whether that lever reaches
the car at all, and which way.

Per the kit's own rule, bootstrap over ENGAGED EPISODES, not frames: frames are autocorrelated and a
frame-level CI manufactures significance.  b7 and b4 are carried unchanged between the two builds, so
they are the controls -- if they move as much as b5, the difference is exposure, not dose.
"""
import glob

import numpy as np

C = 'analysis-2020accord/_scratch/cache'
RNG = np.random.default_rng(20260829)


def episodes(tag):
    d = np.load(glob.glob('%s/%s/%s.npz' % (C, tag, tag))[0], allow_pickle=True)
    eng = np.asarray(d['cc_lat']).astype(float) > 0.5
    p = np.asarray(d['probe']).astype(int)
    n = min(len(p), len(eng))
    eng, p = eng[:n], p[:n]
    out, i = [], 0
    while i < n:
        if not eng[i]:
            i += 1
            continue
        j = i
        while j < n and eng[j]:
            j += 1
        if j - i >= 100:                      # ignore slivers
            out.append(p[i:j])
        i = j
    return out


def boot(ep_a, ep_b, bit, n=4000):
    fa = np.array([((e >> bit) & 1).mean() for e in ep_a])
    wa = np.array([len(e) for e in ep_a], float)
    fb = np.array([((e >> bit) & 1).mean() for e in ep_b])
    wb = np.array([len(e) for e in ep_b], float)
    obs = np.average(fb, weights=wb) - np.average(fa, weights=wa)
    ds = np.empty(n)
    for k in range(n):
        ia = RNG.integers(0, len(fa), len(fa))
        ib = RNG.integers(0, len(fb), len(fb))
        ds[k] = np.average(fb[ib], weights=wb[ib]) - np.average(fa[ia], weights=wa[ia])
    return obs, np.percentile(ds, 2.5), np.percentile(ds, 97.5), len(fa), len(fb)


A, B = episodes('ra5'), episodes('ra6')
print('=' * 96)
print('  INERTIA DOSE-RESPONSE:  V105 (route a5)  ->  V106 (route a6, inertia x3.0, ONE cell)')
print('  episode bootstrap, 4000 resamples, episodes weighted by length')
print('=' * 96)
print('  %d engaged episodes on ra5, %d on ra6' % (len(A), len(B)))
print()
print('  rung   meaning                              V105     V106     delta   95%% CI')
rows = [(5, 'b5 = |friction| >= |INERTIA|   DOSED'),
        (7, 'b7 = a sign rung              CONTROL'),
        (4, 'b4 = a sign rung              CONTROL')]
res = {}
for bit, nm in rows:
    obs, lo, hi, na, nb = boot(A, B, bit)
    fa = np.average([((e >> bit) & 1).mean() for e in A],
                    weights=[len(e) for e in A])
    fb = np.average([((e >> bit) & 1).mean() for e in B],
                    weights=[len(e) for e in B])
    res[bit] = (obs, lo, hi)
    sig = 'EXCLUDES 0' if (lo > 0 or hi < 0) else 'includes 0'
    print('   %-5s %-36s %.4f   %.4f   %+.4f  [%+.4f, %+.4f]  %s'
          % ('b%d' % bit, nm, fa, fb, obs, lo, hi, sig))

print()
o5, l5, h5 = res[5]
ctrl = max(abs(res[7][0]), abs(res[4][0]))
print('  Tripling the inertia term must LOWER P(friction >= inertia).  Observed %+.4f.' % o5)
if h5 < 0 and abs(o5) > ctrl:
    print('  => DIRECTION CORRECT, CI excludes zero, and the move is larger than either control')
    print('     (%.4f vs %.4f).  ** The inertia cell 0xD7A5C REACHES THE CAR, and its sign is'
          % (abs(o5), ctrl))
    print('     confirmed on-car. **  V196/V199/V202 HALVE that same cell, i.e. the opposite')
    print('     direction, so they should push b5 UP.')
elif h5 < 0:
    print('  => direction correct and CI excludes zero, BUT a control moved comparably (%.4f).'
          % ctrl)
    print('     Treat as suggestive, not established -- the two drives differ in exposure.')
else:
    print('  => CI includes zero. NOT established.')
