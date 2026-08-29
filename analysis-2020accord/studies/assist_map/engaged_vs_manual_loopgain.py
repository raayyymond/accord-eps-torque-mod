# -*- coding: utf-8 -*-
"""Why the ratchet is ENGAGED-ONLY, from the census's own liveness table.

The assist map is always live and contributes s = 2.000 of the loop gain.  The rest of L
comes from lanes the census marks engagement-conditional:

    gp-0x6ad4  PID          0.2565
    gp-0x6ada  r24          0.049 - 0.293
    gp-0x6adc  r26          0.098 - 1.17   LIVE ONLY while gp-0x6b5e == 0
    FUN_36682               0.0032
    ceiling sum with the map at 2.000 = 2.825

So manual creep runs at L ~ 2.000 (the map alone) and engaged creep at L ~ 2.825.  With P
calibrated from the MEASURED engaged Q ratio, that difference alone should reproduce the
observed presence/absence -- a strong peak engaged, none in manual.

This is a falsifiable prediction, not a fit: P is set by the engaged measurement only, and
the manual arm is then PREDICTED.
"""
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

Q_EFF, Q_PASS = 40.0, 2.8
L_ENG = 2.825          # census ceiling, map at s=2.000 plus the engaged lanes
S_MAP = 2.000          # the map's own contribution, always live
L_MAN = S_MAP          # manual: the engagement-conditional lanes drop out

P = (1.0 - 1.0 / (Q_EFF / Q_PASS)) / L_ENG
print('P calibrated from the ENGAGED measurement only: P = %.4f' % P)
print('(Q_eff/Q_passive = %.1f  =>  |1-P.L| = %.4f  =>  P.L = %.4f)\n'
      % (Q_EFF / Q_PASS, 1.0 / (Q_EFF / Q_PASS), P * L_ENG))

print('%-10s %-8s %-9s %-11s %-11s %s' % ('arm', '|L|', 'P.L', '|1-P.L|', 'Q ratio', 'note'))
rows = {}
for nm, L in (('ENGAGED', L_ENG), ('MANUAL', L_MAN)):
    pl = P * L
    den = abs(1 - pl)
    rows[nm] = 1.0 / den
    print('%-10s %-8.3f %-9.4f %-11.4f %-11.2f %s'
          % (nm, L, pl, den, 1.0 / den, 'measured' if nm == 'ENGAGED' else 'PREDICTED'))
print('\n  predicted engaged/manual Q ratio = %.2f' % (rows['ENGAGED'] / rows['MANUAL']))
print('  MEASURED engaged/manual excess ratio (speed-matched, n=4) = 19.9 [4.82, 35.64]')
print('  and the manual arm sat BELOW its own null on 7/7 routes')

print('\nnow the cap lever, with BOTH arms recomputed (the map term is shared):')
print('%-8s %-7s %-9s %-9s %-9s %-9s %s'
      % ('cap', 's', 'L eng', 'Q eng', 'L man', 'Q man', 'engaged vs stock'))
base = None
for c in (2048, 1792, 1536, 1280, 1024):
    s = c / 1024.0
    Le = (L_ENG - S_MAP) + s
    Lm = s
    qe = 1.0 / abs(1 - P * Le)
    qm = 1.0 / abs(1 - P * Lm)
    if base is None:
        base = qe
    print('%-8d %-7.3f %-9.3f %-9.2f %-9.3f %-9.2f %s'
          % (c, s, Le, qe, Lm, qm,
             'stock' if c == 2048 else '%.1fx more damped' % (base / qe)))

print("""
[EVIDENCE] gp-0x6b4a == 0 -- the map input is the DRIVER TORQUE SENSOR alone.
Chain, byte-anchored: cal 0xC616C = 0 => a clamp with limit 0 annihilates its input =>
gp-0x6b76 in {0, 0x7FFF}, and 0x7FFF exceeds FUN_0003405a's own 20480 gate so it is forced
to 0 => gp-0x62e0[] == 0 => gp-0x6298[] == 0 => gp-0x6b4a == 0.
=> lowering the slope cap CANNOT touch the LKAS lane (gp-0x6b4c).  The earlier BELIEF is
   upgraded to EVIDENCE, and the feel cost falls entirely on driver-torque assist near
   centre, not on LKAS authority.

[BELIEF] the engaged/manual account above.  It reproduces the right ORDER (a large Q
contrast produced purely by the engagement-conditional lanes joining L) from a P fitted to
the engaged arm alone, but the census's per-lane magnitudes carry their own assumptions and
the manual arm's true L is not separately measured.""")
