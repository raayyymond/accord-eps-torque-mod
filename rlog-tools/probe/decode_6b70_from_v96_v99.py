# -*- coding: utf-8 -*-
"""
gp-0x6b70's CLIP DUTY -- ANSWERED FROM SIX CACHED ROUTES, NO DRIVE.

V205 was built to measure whether gp-0x6b70 saturates, because the saturation census eliminated every
other clamp in the command->motor path.  But BUILD-LINEAGE-CATCHUP records that V96/V97 already put
it on CAN 427:

    "PROBE: CAN 427 <- gp-0x6b70 (LSB 12.8 ct, no-clip 8192*5>>6 = 640 <= 1023)"
    "b7 = gp-0x6b70 < 0 ... V96's own rungs"

So 427 carries the MAGNITUDE at raw = (|x| * 5) >> 6, i.e. LSB 12.8 counts, and the SIGN rides in
rung b7 -- the design law's sign-bit-plus-magnitude pattern.  The writer clamp +-8192 lands at
raw 640.  V100's changelog repoints 427 away from gp-0x6b70, which bounds the window: V96 through
V99, routes 7d / 7e / 7f / 80 / 81 / 82, all cached.

427 arrives at half the base rate, so engagement is aligned onto the 427 timebase rather than assumed.
"""
import glob

import numpy as np

C = 'analysis-2020accord/_scratch/cache'
LSB = 12.8
CLAMP_RAW = 640            # (8192 * 5) >> 6
ROUTES = [('r7d', 'V96 (aborted)'), ('r7e', 'V97'), ('r7f', 'V97'),
          ('r80', 'V97'), ('r81', 'V98'), ('r82', 'V99')]

print('=' * 100)
print('  |gp-0x6b70| FROM CAN 427, V96-V99.  clamp = 8192 counts = raw 640')
print('=' * 100)
print('  route  build            n_427   n_eng    p50     p95     max    AT CLAMP')
tot_eng = tot_clip = 0
for tag, build in ROUTES:
    f = glob.glob(f'{C}/{tag}/{tag}.npz')
    if not f:
        continue
    z = np.load(f[0], allow_pickle=True)
    if 'ab_mt' not in z.files or 'ab_t1ab' not in z.files:
        print(f'  {tag}: no 427 channel')
        continue
    mt = np.asarray(z['ab_mt'], float)
    t427 = np.asarray(z['ab_t1ab'], float)
    n = min(len(mt), len(t427))
    mt, t427 = mt[:n], t427[:n]
    # align engagement onto the 427 timebase -- do not assume the rates match
    if 'cc_lat' in z.files and 't' in z.files:
        tb = np.asarray(z['t'], float)
        lat = np.asarray(z['cc_lat'], float)
        m = min(len(tb), len(lat))
        eng = np.interp(t427, tb[:m], lat[:m]) > 0.5
    else:
        eng = np.ones(n, bool)
    x = mt[eng] * LSB
    if x.size < 200:
        print(f'  {tag:5s}  {build:15s}  {n:6d}  {int(eng.sum()):6d}   (too little engaged)')
        continue
    clip = (mt[eng] >= CLAMP_RAW).mean()
    tot_eng += int(eng.sum())
    tot_clip += int((mt[eng] >= CLAMP_RAW).sum())
    print('  %-6s %-15s %6d  %6d  %6.0f  %6.0f  %6.0f    %.6f'
          % (tag, build, n, int(eng.sum()), np.percentile(x, 50),
             np.percentile(x, 95), x.max(), clip))

print()
print('=' * 100)
print('  POOLED: %d engaged 427 frames, %d at the clamp -> duty %.6f'
      % (tot_eng, tot_clip, (tot_clip / tot_eng) if tot_eng else float('nan')))
print('=' * 100)
if tot_eng and tot_clip / tot_eng < 1e-4:
    print('  ** gp-0x6b70 DOES NOT SATURATE. **')
    print('  The saturation census eliminated every OTHER clamp in the command->motor path by')
    print('  structure or by measurement, and this was the only survivor.  It does not clip either.')
    print('  => the command-gated-saturation model has NO surviving clamp in this path, and V206 --')
    print('     which raises this ceiling 2x -- is raising a ceiling that is never reached.')
else:
    print('  gp-0x6b70 DOES reach its clamp; V206s ceiling raise is aimed at a live saturation.')
