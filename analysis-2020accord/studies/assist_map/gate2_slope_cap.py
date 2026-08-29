# -*- coding: utf-8 -*-
"""GATE 2 on the slope cap, anchored on the MEASURED Q ratio rather than a census phase.

My first pass used the census's L phase (-148 deg) with P as a positive real.  That gives
P.L in the third quadrant, |1-P.L| = 1.92 > 1, i.e. a loop that ADDS damping -- which
contradicts the measured fact that the loop CANCELS ~93 % of the mode's damping.  The
phase convention cannot be pinned from the census (it says P's phase "is not in the
image"), and the sign of the whole result depends on it.  So anchor on the measurement.

MEASURED:  Q_eff / Q_passive = 40 / 2.8 = 14.3   =>   |1 - P.L| = 1/14.3 = 0.0699
Near-cancellation of damping at a resonance is a real-axis phenomenon (the loop feeds back
in phase with velocity), so take P.L real positive = 1 - 0.0699 = 0.9301 at stock.
[ASSUMPTION, stated: P.L real-positive at the peak.  It is what the measured Q ratio
 requires, and it is the standard form for a damping-cancelling loop.]

The assist map contributes its own slope s directly to |L| (census table: 0.5 - 2.000),
and the cap pins s at 2.000 wherever it binds.  Lowering the cap to c moves the map's
contribution 2.000 -> c and leaves the other terms alone.
"""
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

Q_EFF, Q_PASSIVE = 40.0, 2.8
L_CEIL = 2.825          # census ceiling sum, with the map at s = 2.000
S_STOCK = 2.000

den_stock = 1.0 / (Q_EFF / Q_PASSIVE)
PL_stock = 1.0 - den_stock
P = PL_stock / L_CEIL              # calibrate P so P.L reproduces the measured ratio
L_other = L_CEIL - S_STOCK         # every term except the assist map

print('measured Q_eff/Q_passive = %.1f  =>  |1 - P.L| = %.4f  =>  P.L = %.4f at stock'
      % (Q_EFF / Q_PASSIVE, den_stock, PL_stock))
print('census |L| ceiling = %.3f with the map at s = %.3f  =>  other terms = %.3f, P = %.4f\n'
      % (L_CEIL, S_STOCK, L_other, P))

print('%-10s %-8s %-9s %-9s %-11s %-12s %s'
      % ('cap Q10', 's', '|L|', 'P.L', '|1-P.L|', 'Q ratio', 'vs stock'))
base = None
for c in (2048, 1792, 1536, 1280, 1024, 768):
    s = c / 1024.0
    L = L_other + s
    pl = P * L
    den = abs(1 - pl)
    qr = 1.0 / den
    if base is None:
        base = qr
    print('%-10d %-8.3f %-9.3f %-9.4f %-11.4f %-12.2f %s'
          % (c, s, L, pl, den, qr,
             'stock' if c == 2048 else '%.1fx MORE damped' % (base / qr)))

print("""
GATE 2 -- MAGNITUDE: PASSES, and the effect is large.  Halving the cap (2048 -> 1024)
raises the mode's damping by ~5x on this anchoring.

GATE 2 -- PHASE: the map term is a real gain, so lowering the cap SCALES |L| without
rotating it.  Under the real-positive P.L the measurement requires, |1 - P.L| can only move
away from zero as |L| falls => monotonically MORE damped, at every cap value, with no
value at which it reverses.  [EVIDENCE for the sign, given the stated assumption.]

WHAT WOULD FALSIFY THE ASSUMPTION: if P.L were NOT near the positive real axis, the
measured 14.3x damping cancellation could not arise from this loop at all, and the cause
would lie outside it.  The on-car test is the same either way -- lower the cap and see
whether the 8.64 Hz torque peak drops below its slope-matched null.

FEEL COST -- real, and it cuts against a standing operator constraint.  The cap binds over
the LOW-torque segments (X 0-100 to 0-450 depending on record), so lowering it reduces how
fast assist builds for small driver inputs: HEAVIER steering near centre, in exactly the
regime the operator asked to keep light.  A cap of 1536 (1.5x) is the smallest step with a
predicted effect (~2.4x) that clears the one-episode detection margin, so it is the honest
first dose rather than the largest.""")
