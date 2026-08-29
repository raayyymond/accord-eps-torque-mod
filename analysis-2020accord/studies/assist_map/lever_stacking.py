# -*- coding: utf-8 -*-
"""Should V168 and V172 be COMBINED, and what is left in the loop after V172?

They attack the same lane by different means: the cap scales the map's slope at every
frequency, the filter attenuates it at the resonance.  Combining them multiplies, so the
question is whether the extra damping is worth carrying BOTH feel costs.

Then: after V172, how much of the loop gain is the assist map and how much is everything
else?  That names whether a third lever is even worth looking for.
"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# anchoring, unchanged: measured Q_eff/Q_passive = 14.3 at stock
P = 0.9300 / 2.825
L_OTHER = 0.825            # every loop term except the assist map
S_STOCK = 2.000
FILT_FLY, FILT_V172 = 0.9790, 0.4441      # section gain at 8.64 Hz

def q(L):
    return 1.0 / abs(1 - P * L)

base = q(L_OTHER + S_STOCK * FILT_FLY / FILT_FLY)   # stock reference: s = 2.0 effective
base = q(L_OTHER + S_STOCK)
print('%-34s %-10s %-10s %-11s %s' % ('build', 'eff s', '|L|', 'Q ratio', 'vs stock'))
CASES = [
    ('STOCK / flying', S_STOCK, 1.0),
    ('V168  cap 1536', S_STOCK * 1536 / 2048, 1.0),
    ('V171  cap 1024', S_STOCK * 1024 / 2048, 1.0),
    ('V172  filter retune', S_STOCK, FILT_V172 / FILT_FLY),
    ('V172 + cap 1536 (stacked)', S_STOCK * 1536 / 2048, FILT_V172 / FILT_FLY),
    ('V172 + cap 1024 (stacked)', S_STOCK * 1024 / 2048, FILT_V172 / FILT_FLY),
]
for nm, s_eff, fmul in CASES:
    s = s_eff * fmul
    L = L_OTHER + s
    print('%-34s %-10.3f %-10.3f %-11.2f %.1fx' % (nm, s, L, q(L), base / q(L)))

print('\nMARGINAL value of stacking the cap ON TOP of V172:')
qa = q(L_OTHER + S_STOCK * (FILT_V172 / FILT_FLY))
qb = q(L_OTHER + S_STOCK * 1536 / 2048 * (FILT_V172 / FILT_FLY))
qc = q(L_OTHER + S_STOCK * 1024 / 2048 * (FILT_V172 / FILT_FLY))
print('  V172 alone            %.1fx more damped than stock' % (base / qa))
print('  V172 + cap 1536       %.1fx   => marginal gain %.2fx for the FULL static weight cost'
      % (base / qb, qa / qb))
print('  V172 + cap 1024       %.1fx   => marginal gain %.2fx' % (base / qc, qa / qc))

print('\nWHAT IS LEFT IN THE LOOP AFTER V172')
s_after = S_STOCK * (FILT_V172 / FILT_FLY)
L_after = L_OTHER + s_after
print('  assist map share   %.3f of |L| = %.0f %%' % (s_after, 100 * s_after / L_after))
print('  everything else    %.3f of |L| = %.0f %%' % (L_OTHER, 100 * L_OTHER / L_after))
print('  (census names those: PID 0.2565, r24 0.049-0.293, r26 0.098-1.17 live only while')
print('   gp-0x6b5e==0, FUN_00036682 0.0032 -- all ENGAGEMENT-CONDITIONAL)')
need = (1 - 1.0 / 3.0) / P      # what |L| would give a Q ratio of 3
print('\n  to reach a Q ratio of 3.0 (a 4.8x improvement) needs |L| <= %.3f' % need)
print('  V172 leaves |L| = %.3f, so it is %s' % (L_after, 'ALREADY THERE' if L_after <= need else 'still above'))
print('  driving |L| below that needs the ENGAGEMENT-CONDITIONAL terms, not the map.')
