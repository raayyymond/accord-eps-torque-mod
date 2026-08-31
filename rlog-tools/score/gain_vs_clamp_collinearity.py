# -*- coding: utf-8 -*-
"""GAIN or CLAMP? V242/V243 move both together, so which one actually drives the anti-damping?

If it is the CLAMP, then gain could be raised while the clamp is held -- authority without ratchet,
which is exactly what the operator asked for. If it is the GAIN itself, the trade is hard.
"""
import glob
import os
import re
import struct
import sys

import numpy as np
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, 'rlog-tools/score')
from friction_dose_vs_antidamping import rez, BUILD, IMGDIR   # noqa: E402

CELLS = {'GAIN 0xC6CD0': 0xC6CD0, 'clamp+ 0xC61B2': 0xC61B2, 'clamp- 0xC61B4': 0xC61B4,
         'softEME 0xC674E': 0xC674E, 'shared 0xC646C': 0xC646C}


def cells_of(build):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q)] or \
        glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
    if not p:
        return None
    im = open(p[0], 'rb').read()
    if struct.unpack_from('<H', im, 0xC646C)[0] != 891:
        return None
    return {k: struct.unpack_from('<H', im, a)[0] for k, a in CELLS.items()}


rows = []
print('  %-6s %-6s' % ('route', 'build'), end='')
for k in CELLS:
    print(' %14s' % k, end='')
print(' %11s' % 'Re(Z) 6-9')
print('  ' + '-' * 96)
for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
    b = BUILD[r]
    c, z = cells_of(b), rez(r)
    if c is None or z is None:
        continue
    rows.append((b, c, z[0]))
    print('  %-6s %-6s' % (r, b), end='')
    for k in CELLS:
        print(' %14d' % c[k], end='')
    print(' %11.2f' % z[0])
print('  ' + '-' * 96)

v = np.array([x[2] for x in rows])
print('\n  which cell predicts the anti-damping?\n')
print('  %-18s %10s %10s %10s %s' % ('cell', 'distinct', 'rho', 'p', 'values'))
print('  ' + '-' * 74)
for k in CELLS:
    x = np.array([float(c[k]) for _, c, _ in rows])
    u = sorted(set(x))
    if len(u) < 2:
        print('  %-18s %10d %10s %10s %s  (no contrast)'
              % (k, len(u), '--', '--', [int(y) for y in u]))
        continue
    rho = stats.spearmanr(x, v)
    print('  %-18s %10d %+10.3f %10.4f %s'
          % (k, len(u), rho.correlation, rho.pvalue, [int(y) for y in u][:6]))
print()
print('  \U0001f6d1 cells that never vary across the flown corpus CANNOT be tested here -- that is an')
print('     absence of evidence, not evidence of absence.')
