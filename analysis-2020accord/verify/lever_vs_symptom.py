# -*- coding: utf-8 -*-
"""Does the Coulomb relay's knee move the ratchet?

The relay is FUN_0003b8f6: fVar13 = clamp(POL * gp-0x6abc * 12 / cal(0xC40BC), -1, +1).
Below the knee it is viscous, above it a pure sign -- the mechanism the kit has blamed for
the engaged 6-9 Hz amplification since V80.

The nine scored routes happen to span the knee over 10x (300 to 3000), and the ratchet did
NOT move across them.  That is a direct test: if the relay sets the ratchet, ratchet excess
must track the knee.

Knee values are read from each build's own image, not from notes.
"""
import glob
import os
import re
import sys

import numpy as np
from scipy import stats

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
KNEE = 0xC40BC
GAIN = 0xC6CD0
FRIC = 0xC40D2

# route -> build, and the measured cs_tq excesses from the validated estimator
ROUTES = [('r78', 91, 9.8, 6.1), ('r7e', 96, 16.5, 28.9), ('r7f', 96, 32.9, 14.3),
          ('r96', 102, 49.4, 248.2), ('ra4', 104, 15.8, 54.7), ('ra6', 106, 67.8, 25.3),
          ('r1e', 107, 28.8, 27.7), ('r22', 112, 35.8, 15.0), ('r24', 122, 33.2, 14.0)]


def img_for(v):
    for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
        m = re.search(r'_v(\d+)', os.path.basename(p).lower())
        if m and int(m.group(1)) == v:
            return p
    return None


def u16(a, off):
    return int(a[off]) | (int(a[off + 1]) << 8)


print('%-6s %-6s %-8s %-8s %-8s %-9s %s'
      % ('route', 'build', 'knee', 'gain', 'friction', 'RATCHET', 'GRIND'))
rows = []
for tag, v, er, eg in ROUTES:
    p = img_for(v)
    if p is None:
        print('%-6s V%-5d  -- no image' % (tag, v))
        continue
    a = np.fromfile(p, dtype=np.uint8)
    k, g, fr = u16(a, KNEE), u16(a, GAIN), u16(a, FRIC)
    print('%-6s V%-5d %-8d %-8d %-8d %-9.1f %.1f' % (tag, v, k, g, fr, er, eg))
    rows.append((k, g, fr, er, eg))

k = np.array([r[0] for r in rows], float)
g = np.array([r[1] for r in rows], float)
fr = np.array([r[2] for r in rows], float)
er = np.array([r[3] for r in rows], float)
eg = np.array([r[4] for r in rows], float)

print('\nknee spans %.0f - %.0f  (%.1fx)' % (k.min(), k.max(), k.max() / k.min()))
print('%-26s %-22s %s' % ('predictor', 'vs RATCHET', 'vs GRIND'))
for nm, x in (('knee 0xC40BC', k), ('gain 0xC6CD0', g), ('friction 0xC40D2', fr)):
    if len(set(x)) < 3:
        print('%-26s  -- only %d distinct values' % (nm, len(set(x))))
        continue
    r1, p1 = stats.spearmanr(x, er)
    r2, p2 = stats.spearmanr(x, eg)
    print('%-26s rho %+.2f  p %.3f      rho %+.2f  p %.3f' % (nm, r1, p1, r2, p2))

print('\nratchet grouped by knee:')
for kv in sorted(set(k)):
    m = k == kv
    print('  knee %-6.0f  n=%d  ratchet median %.1f   grind median %.1f'
          % (kv, m.sum(), np.median(er[m]), np.median(eg[m])))

lo, hi = er[k <= 600], er[k >= 1800]
if len(lo) and len(hi):
    print('\n  knee<=600 ratchet median %.1f   vs  knee>=1800 median %.1f   ratio %.2f'
          % (np.median(lo), np.median(hi), np.median(hi) / np.median(lo)))
    print('  (split-half floor on this endpoint is 1.63x -- a ratio inside that is no effect)')
