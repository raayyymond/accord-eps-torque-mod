# -*- coding: utf-8 -*-
"""Which calibration cells did EVERY build V91-V122 leave byte-identical?

The ratchet is firmware-caused, engaged-only, and did not move across V91->V122 in a test
with power to see 1.9x.  So the responsible cell is one those builds all left alone.

Intersect: bytes identical across every V91..V122 image AND identical to stock.  Report by
region so the calibration blocks stand out from code.
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
imgs = {}
for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
    m = re.search(r'_v(\d+)', os.path.basename(p).lower())
    if not m:
        continue
    v = int(m.group(1))
    if 91 <= v <= 122:
        imgs.setdefault(v, p)

print('images in the V91-V122 window: %d  (%s)'
      % (len(imgs), ' '.join('V%d' % v for v in sorted(imgs))))
if len(imgs) < 4:
    print('too few images to intersect')
    sys.exit(0)

arrs = {}
for v, p in sorted(imgs.items()):
    arrs[v] = np.fromfile(p, dtype=np.uint8)
n = min(len(a) for a in arrs.values())
print('common length %d bytes (%.2f MB)' % (n, n / 1048576.0))

vs = sorted(arrs)
base = arrs[vs[0]][:n]
same = np.ones(n, dtype=bool)
for v in vs[1:]:
    same &= (arrs[v][:n] == base)
print('bytes identical across ALL %d images: %d  (%.2f %%)'
      % (len(vs), same.sum(), 100.0 * same.sum() / n))
diff = ~same
print('bytes that ANY build in the window changed: %d' % diff.sum())

# where the changes are, so the untouched calibration space is what remains
print('\nchanged-byte extents (runs merged within 64 bytes):')
idx = np.where(diff)[0]
if len(idx):
    runs, s, p_ = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p_ > 64:
            runs.append((s, p_))
            s = i
        p_ = i
    runs.append((s, p_))
    for a, b in runs:
        print('  0x%05X - 0x%05X  (%d bytes)' % (a, b, b - a + 1))

CAL = [('0xC4000 params', 0xC4000, 0xC5000), ('0xC5000 model coeff', 0xC5000, 0xC6000),
       ('0xC6000 main cal', 0xC6000, 0xC7000), ('0xC7000', 0xC7000, 0xC8000),
       ('0xC9000 damper tables', 0xC9000, 0xCA000), ('0xCB000', 0xCB000, 0xCC000),
       ('0xCC000 gain arrays', 0xCC000, 0xCD000)]
print('\nuntouched fraction by calibration region:')
print('%-24s %-10s %-10s %s' % ('region', 'bytes', 'changed', 'untouched'))
for nm, lo, hi in CAL:
    if hi > n:
        continue
    d = diff[lo:hi].sum()
    print('%-24s %-10d %-10d %.1f %%' % (nm, hi - lo, d, 100.0 * (hi - lo - d) / (hi - lo)))
