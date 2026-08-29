# -*- coding: utf-8 -*-
"""Find the base-assist curve in the ROM .data init image.

Only 3 st.h target the 20-knot block and 2 of them are clears, so the values arrive by bulk
copy -- the classic embedded pattern of copying an initialised-data section from ROM to RAM
at boot.  If so the curve IS in the image, just not in the cal region.

Shape constraints, all from the decompile rather than guessed:
  X: 10 knots, strictly ascending, bounded by the input clamp cal(0xC6200) = 8192
  Y: 10 knots, ascending (a power-assist curve is monotone), bounded by the output
     clamp 0x3000 = 12288
  and the per-segment slope dY/dX must be plausible against the cap cal(0xC6384)/1024 = 2.000

Search the WHOLE image, both orders (X-then-Y and Y-then-X), and report how many segments
would hit the cap for each candidate -- which is the number GATE 2 actually needs.
"""
import os
import sys

import numpy as np

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
a = np.fromfile(os.path.join(ROOT, 'stock_fw_dump/code.bin'), dtype=np.uint8)
n = len(a)
XCLAMP, YCLAMP, CAP = 8192, 0x3000, 2048 / 1024.0

v = a[:n - (n % 2)].view('<u2')


def knots(i, k=10):
    return [int(x) for x in v[i:i + k]]


cands = []
for i in range(0, len(v) - 20):
    X = knots(i)
    if X[0] != 0 and X[0] > 512:
        continue
    if not all(X[j] < X[j + 1] for j in range(9)):
        continue
    if X[9] > XCLAMP or X[9] < XCLAMP // 8:
        continue
    Y = knots(i + 10)
    if not all(Y[j] <= Y[j + 1] for j in range(9)):
        continue
    if Y[9] > YCLAMP or Y[9] < 256:
        continue
    sl = [(Y[j + 1] - Y[j]) / float(X[j + 1] - X[j]) for j in range(9)]
    cands.append((i * 2, X, Y, sl))

print('candidate X,Y knot pairs across the WHOLE image: %d\n' % len(cands))
for off, X, Y, sl in cands[:12]:
    binds = sum(1 for s in sl if s >= CAP)
    print('0x%05X' % off)
    print('   X     %s' % ' '.join('%6d' % x for x in X))
    print('   Y     %s' % ' '.join('%6d' % y for y in Y))
    print('   slope %s' % ' '.join('%6.2f' % s for s in sl))
    print('   max slope %.3f   cap %.3f   binds on %d of 9 segments\n' % (max(sl), CAP, binds))

if not cands:
    print('none with X-then-Y; trying Y-then-X ordering')
    for i in range(0, len(v) - 20):
        Y = knots(i)
        X = knots(i + 10)
        if not (all(X[j] < X[j + 1] for j in range(9)) and all(Y[j] <= Y[j + 1] for j in range(9))):
            continue
        if X[9] > XCLAMP or X[9] < XCLAMP // 8 or Y[9] > YCLAMP or Y[9] < 256:
            continue
        sl = [(Y[j + 1] - Y[j]) / float(X[j + 1] - X[j]) for j in range(9)]
        print('0x%05X  X %s' % (i * 2, X))
        print('          Y %s' % Y)
        print('          max slope %.3f  binds %d/9' % (max(sl), sum(1 for s in sl if s >= CAP)))
        cands.append((i * 2, X, Y, sl))
        if len(cands) >= 8:
            break

print('\n--- relaxing: ANY 10 ascending u16 bounded by 8192 with a paired ascending block ---')
if len(cands) == 0:
    loose = 0
    for i in range(0, len(v) - 20):
        X = knots(i)
        if not all(X[j] < X[j + 1] for j in range(9)) or X[9] > XCLAMP:
            continue
        loose += 1
    print('  %d ascending 10-knot u16 runs bounded by 8192 exist image-wide' % loose)
    print('  (so the constraint that failed is the PAIRED Y block, not the X shape)')
