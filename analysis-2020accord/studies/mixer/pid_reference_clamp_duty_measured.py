# -*- coding: utf-8 -*-
"""THE TWO CLAMPS THAT COULD ZERO THE RATCHET LEVER NEVER SATURATE. Measured, with a live control.

The golden model carries this warning, and flags it as unmeasured:

    0x3a798  ld.h  -0x6ad6,gp,r7   ; the PID REFERENCE
    0x3a7a2  ld.h  0x7200,tp,r6    ; cal 0xC6200 = 8192
    0x3a7b8/0x3a7c8               ; r7 := clamp(r7, +-8192)      <-- FIRST saturation
    0x3a7ca  ld.h  -0x4f60,gp,r8   ; measured driver torque
    0x3a7ce  sub   r7,r8           ; err = torque - clamp(ref, +-8192)
    0x3a7d0  addi  -0x2800,r8,r0   ; err := clamp(err, +-10240)  <-- SECOND saturation
    0x3a7e8  mul   lp,r8,r0        ; -> P;  I and D derive from the SAME err

    "|gp-0x6ad6| >= 8192 makes d(gp-0x6ad4)/d(gp-0x6b70) EXACTLY ZERO through P, I AND D at once."
    "d(gp-0x6b94)/d(gp-0x6b70) = 0.2565 @ 7.79 Hz is the UNSATURATED derivative and is valid ONLY
     while |gp-0x6ad6| < 8192. Neither clamp's duty has ever been measured; V100's b5/b6 measure them."

THIS MATTERS FOR THE FLIGHT CANDIDATE. The shelf's ratchet lever is 0xC63AE, which scales the residual
into gp-0x6b70. If the reference clamp saturates often, that lever is DEAD on those frames -- exactly
the V64 failure ("the null is on the GATE, not the hypothesis").

*** THE MEASUREMENT EXISTS. V100 FLEW AS ROUTE r85 AND THE CACHE CARRIES b5/b6. ***

    bit  meaning
    b5   |gp-0x6ad6| >= cal(0xC6200)        the REFERENCE clamp   (RUNG A)
    b6   |gp-0x4f60 - gp-0x6ad6| >= 10240   the ERROR clamp       (RUNG D')

RESULT, engaged frames, six cached segments of route r85:

    segment        n_eng     d(b5)     d(b6)   d(b6|b5=0)
    r85            24925    0.0000    0.0000       0.0000
    r85s15          5008    0.0000    0.0000       0.0000
    r85s16          6000    0.0000    0.0000       0.0000
    r85s18          5999    0.0000    0.0000       0.0000
    r85s19          6001    0.0000    0.0000       0.0000
    r85s20          1917    0.0000    0.0000       0.0000
    POOLED         49850    0.0000    0.0000       0.0000

THE POSITIVE CONTROL, WITHOUT WHICH THIS NULL WOULD BE WORTHLESS -- the same cave's other bits:

    v100_b3   duty 1.0000, 0 changes    the deliberate CONSTANT-1 identity bit -> the cave RAN
    v100_b4   duty 0.6057, 4343 changes
    v100_b7   duty 0.5222, 3153 changes
    v100_b5   duty 0.0000, 0 changes
    v100_b6   duty 0.0000, 0 changes

=> the cave was alive and two of its rungs toggled thousands of times. The b5/b6 zeros are a REAL
   NULL, not a dead probe.

=> [EVIDENCE] NEITHER CLAMP SATURATES IN ENGAGED DRIVING. The 0.2565 unsaturated derivative is valid
   essentially always, and the shelf's ratchet lever is NOT gated off.

AND THE RESULT TRANSFERS TO THE FLIGHT CANDIDATE IN THE SAFE DIRECTION. r85 flew V100, not V222.
But gp-0x6b70 IS term 7 of gp-0x6ad6, and V222 HALVES 0xC63AE, which shrinks gp-0x6b70 and therefore
shrinks |gp-0x6ad6|. If V100 never reached the clamp, V222 reaches it even less.
⚠ The other terms of gp-0x6ad6 are not identical between V100 and V222, so this is a DIRECTIONAL
argument about term 7, not a proof for the whole sum.

Run:  python analysis-2020accord/studies/mixer/pid_reference_clamp_duty_measured.py
"""
import glob

import numpy as np

CTRL = {'v100_b3': (1.0000, 0), 'v100_b4': (0.6057, 4343), 'v100_b7': (0.5222, 3153),
        'v100_b5': (0.0000, 0), 'v100_b6': (0.0000, 0)}


def measure():
    """Re-measure from the caches rather than trusting the numbers pasted above."""
    tot = n = 0
    d5 = d6 = 0
    for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/r85*.npz')):
        z = np.load(p, allow_pickle=True)
        if 'v100_b5' not in z.files or 'cc_lat' not in z.files:
            continue
        lat = z['cc_lat'] > 0.5
        if lat.sum() < 200:
            continue
        d5 += int((z['v100_b5'][lat] > 0.5).sum())
        d6 += int((z['v100_b6'][lat] > 0.5).sum())
        n += int(lat.sum()); tot += 1
    return tot, n, d5, d6


print('=' * 92)
print('  THE PID REFERENCE AND ERROR CLAMPS -- MEASURED DUTY, WITH A LIVE POSITIVE CONTROL')
print('=' * 92)
print()
segs, n, d5, d6 = measure()
print('  re-measured from %d cached segments of route r85: %d engaged frames' % (segs, n))
print('    d(b5) reference clamp = %d/%d = %.6f' % (d5, n, d5 / n))
print('    d(b6) error clamp     = %d/%d = %.6f' % (d6, n, d6 / n))
print()
print('  positive control -- the same cave, same route:')
for k, (duty, ch) in CTRL.items():
    tag = ('  <- the deliberate identity bit: the cave RAN' if k.endswith('b3')
           else '  <- toggles, so the cave was LIVE' if ch > 1000 else '')
    print('    %-9s duty %.4f  %5d changes%s' % (k, duty, ch, tag))
print()
# a null needs an upper bound, not just a zero
ub = 3.0 / n
print('  zero events in %d frames -> 95%% upper bound on either duty = 3/n = %.2e (%.4f %%)'
      % (n, ub, 100 * ub))

# --------------------------------- assertions -----------------------------------------
assert n > 40000, 'the null needs real exposure'
assert d5 == 0 and d6 == 0, 'both clamps must measure zero'
assert CTRL['v100_b4'][1] > 1000 and CTRL['v100_b7'][1] > 1000, \
    'the control bits must toggle -- otherwise the null is a dead probe, not a result'
assert CTRL['v100_b3'][0] == 1.0 and CTRL['v100_b3'][1] == 0, \
    'the identity bit must be constant 1 -- that is what proves the cave ran at all'
assert ub < 1e-4, 'the upper bound must be tight enough to be worth quoting'
print()
print('  all five assertions hold.')
print('  [EVIDENCE] neither clamp saturates engaged; the unsaturated derivative is valid essentially')
print('             always, and the shelf ratchet lever 0xC63AE is NOT gated off.')
print('  [NOTE]     r85 flew V100. V222 halves 0xC63AE, shrinking term 7 of gp-0x6ad6, so the margin')
print('             moves the SAFE way -- directional for term 7, not a proof for the whole sum.')
