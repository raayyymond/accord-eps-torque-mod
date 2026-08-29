# -*- coding: utf-8 -*-
"""The base-assist curve's SOURCE table, and the local slope that sets |L|.

0x39A0C onward blends each RAM knot toward a cal table at ep = tp+0x7564 = 0xC6564:

    ld.hu  -0x6444, gp, r10        # RAM Y knot
    movea  0x7564, tp, ep          # ep = 0xC6564   <-- the SOURCE
    sld.h  0x0, ep, r16            # cal[0]
    cvtf.uws r10, r12 / cvtf.ws r16, r7
    mulf.s  r28, r12, r8 / maddf.s r7, r28, r8, r6   # float blend, coeff r28

repeating for -0x6442, -0x6440, -0x643e ... i.e. the whole Y block, against consecutive
halfwords of the table.  So the curve IS in the image after all -- the RAM copy is a
slewed follower of 0xC6564, not an independent state.

With the curve readable, the map's local slope at the creep operating point is computable,
which is what GATE 2 on the slope cap 0xC6384 needs.
"""
import glob
import os
import re
import sys

import numpy as np

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
TBL = 0xC6564
CAP = 0xC6384
CLAMP = 0xC6200
a = np.fromfile(os.path.join(ROOT, 'stock_fw_dump/code.bin'), dtype=np.uint8)


def u16(b, o):
    return int(b[o]) | (int(b[o + 1]) << 8)


def s16(b, o):
    v = u16(b, o)
    return v - 0x10000 if v >= 0x8000 else v


print('cal table at 0x%05X (tp+0x7564), first 24 halfwords:' % TBL)
for r in range(3):
    print('  +%02X: %s' % (r * 16, ' '.join('%6d' % u16(a, TBL + r * 16 + 2 * k) for k in range(8))))

print('\nas signed:')
for r in range(3):
    print('  +%02X: %s' % (r * 16, ' '.join('%6d' % s16(a, TBL + r * 16 + 2 * k) for k in range(8))))

# The X block is gp-0x641e..gp-0x6430 (10 knots) and Y is gp-0x6444.. ; the loop at 0x39A0C
# walks Y.  Look for the X source too: scan nearby cal space for a monotone 10-knot ramp
# ending at or below the input clamp 0xC6200 = 8192.
clamp = u16(a, CLAMP)
cap = u16(a, CAP)
print('\ninput clamp 0xC6200 = %d ;  slope cap 0xC6384 = %d (Q10 = %.3f)' % (clamp, cap, cap / 1024.0))

print('\nmonotone 10-knot candidates in 0xC6400-0xC6700 bounded by the input clamp:')
cands = []
for base in range(0xC6400, 0xC6700, 2):
    v = [u16(a, base + 2 * k) for k in range(10)]
    if all(0 <= v[k] < v[k + 1] for k in range(9)) and v[9] <= clamp:
        cands.append((base, v))
for base, v in cands[:10]:
    print('  0x%05X  %s' % (base, v))

# Treat 0xC6564 as the Y curve and pair it with each X candidate; report the slopes and
# whether the cap binds.
Y = [u16(a, TBL + 2 * k) for k in range(10)]
print('\nY curve read at 0x%05X: %s' % (TBL, Y))
for base, X in cands[:6]:
    sl = [(Y[k + 1] - Y[k]) / float(X[k + 1] - X[k]) if X[k + 1] != X[k] else float('inf')
          for k in range(9)]
    binds = sum(1 for s in sl if s >= cap / 1024.0)
    print('\n  X from 0x%05X:' % base)
    print('    X %s' % ' '.join('%6d' % x for x in X))
    print('    Y %s' % ' '.join('%6d' % y for y in Y))
    print('    slope %s' % ' '.join('%6.2f' % s for s in sl))
    print('    cap %.3f binds on %d of 9 segments' % (cap / 1024.0, binds))

print('\nhas the source table ever moved?')
vals = {}
for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
    m = re.search(r'_v(\d+)', os.path.basename(p).lower())
    if not m:
        continue
    b = np.fromfile(p, dtype=np.uint8)
    key = b[TBL:TBL + 20].tobytes().hex()
    vals.setdefault(key, []).append(int(m.group(1)))
print('  0x%05X first 20 bytes: %d distinct value(s) across %d images'
      % (TBL, len(vals), sum(len(v) for v in vals.values())))
for k, v in vals.items():
    print('    %s  on %d builds%s' % (k, len(v), '' if len(v) > 3 else ' %s' % sorted(v)))
