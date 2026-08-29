# -*- coding: utf-8 -*-
"""What is left to win after V173, and is any of it worth a build?

r26 turned out to be gated off, so L_other is 0.31-0.55 (PID 0.2565 + r24 0.049-0.293 +
0.0032), not the census's 0.825.  Re-anchor P on that and price every remaining term as a
MARGINAL gain on top of V173 -- because that is the only number that decides whether to
build again before driving.

Anchor is unchanged in kind: the MEASURED Q_eff/Q_passive = 14.3 at stock fixes P.L = 0.93,
so P = 0.93 / |L|_stock.  The correction changes |L|_stock, hence P, hence every ratio.
"""
import sys
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

S_STOCK = 2.000
FILT_FLY, FILT_V173 = 0.978950, 0.476076
PID, R24, MISC = 0.2565, 0.171, 0.0032        # r24 mid of 0.049-0.293

print('%-13s %-9s %-9s %-9s %-9s %s' % ('L_other', 'P', 'stock Q', 'V173 Q', 'V173 gain', 'note'))
for lo, tag in ((0.825, 'census (r26 IN, now known wrong)'),
                (0.55, 'corrected, high'), (0.43, 'corrected, mid'), (0.31, 'corrected, low')):
    P = 0.93 / (S_STOCK + lo)
    q0 = 1 / abs(1 - P * (S_STOCK + lo))
    s173 = S_STOCK * FILT_V173 / FILT_FLY
    q1 = 1 / abs(1 - P * (s173 + lo))
    print('%-13.3f %-9.4f %-9.2f %-9.2f %-9s %s' % (lo, P, q0, q1, '%.1fx' % (q0 / q1), tag))

print('\nMARGINAL gain of each REMAINING lever, ON TOP of V173 (L_other = 0.43)')
lo = 0.43
P = 0.93 / (S_STOCK + lo)
s173 = S_STOCK * FILT_V173 / FILT_FLY
base = 1 / abs(1 - P * (s173 + lo))
print('%-34s %-9s %-11s %s' % ('remove / reduce', 'new |L|', 'Q ratio', 'MARGINAL vs V173'))
for nm, newlo, extra in (('nothing (V173 alone)', lo, 0.0),
                         ('kill the PID entirely', lo - PID, 0.0),
                         ('kill r24 entirely', lo - R24, 0.0),
                         ('kill PID AND r24', lo - PID - R24, 0.0),
                         ('+ slope cap 1536 as well', lo, -s173 * (1 - 1536 / 2048.0)),
                         ('+ slope cap 1024 as well', lo, -s173 * (1 - 1024 / 2048.0))):
    L = s173 + extra + newlo
    q = 1 / abs(1 - P * L)
    print('%-34s %-9.3f %-11.2f %.2fx' % (nm, L, q, base / q))

print("""
READING
  Any lever whose MARGINAL gain is under ~1.3x is not worth a build before a drive: the
  measurement floor on a single episode is 1.63x split-half, so an effect that small could
  not be told apart from noise even if it were real.""")
