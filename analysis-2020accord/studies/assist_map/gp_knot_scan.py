# -*- coding: utf-8 -*-
"""Who writes the base-assist map's 10 knots?  Raw LE byte scan, BOTH gp encodings.

FUN_000352b4 READS the curve from gp-0x6444..gp-0x641e (X knots) and builds slopes into
gp-0x37d6...  If the knots are RAM, something must write them, and that writer's source
table is in the image -- which is what is needed to compute the map's local slope, hence
|L|, hence GATE 2 on the slope cap 0xC6384.

search_instructions returned zero, which CLAUDE.md requires confirming by byte scan, since
it scans only already-analysed instructions AND operand text cannot see register-indirect
writes at all.

V850 gp = r4.  Two encodings for a gp-relative access:
  4-byte Format VII : opcode | reg | disp16          (st.h forces disp LSB = 1)
  6-byte extended   : disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)
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
GP = 4
LO, HI = -0x6444, -0x641c          # the knot block, inclusive-ish


def hw(i):
    return int(a[i]) | (int(a[i + 1]) << 8)


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


hits = []
for i in range(0, n - 6, 2):
    h1 = hw(i)
    reg1 = h1 & 0x1F
    if reg1 != GP:
        continue
    op = (h1 >> 5) & 0x7FF

    # --- 4-byte Format VII: ld.h/ld.hu/st.h all use disp16 with the LSB trick
    top6 = (h1 >> 5) & 0x3F
    if top6 in (0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F):
        d = sext16(hw(i + 2) & 0xFFFE)
        if LO <= d <= HI:
            kind = {0x3A: 'ld.w', 0x3B: 'st.w', 0x38: 'ld.b', 0x3C: 'st.b',
                    0x39: 'ld.h', 0x3D: 'st.h', 0x3E: 'ld.hu/st.h?', 0x3F: 'ld.bu?'}.get(top6, '?')
            hits.append((i, 4, kind, d, 'fmtVII'))

    # --- 6-byte extended form
    if i + 6 <= n:
        d2 = (sext16(hw(i + 2)) << 7) | ((h1 >> 4) & 0x7F)
        if LO <= d2 <= HI:
            hits.append((i, 6, 'ext(op=0x%03X)' % op, d2, 'ext6'))

print('raw scan of the knot block gp%+#x .. gp%+#x  (both encodings)' % (LO, HI))
print('candidate accesses: %d' % len(hits))
seen = {}
for addr, sz, kind, d, form in hits:
    seen.setdefault(kind, 0)
    seen[kind] += 1
for k, v in sorted(seen.items(), key=lambda kv: -kv[1]):
    print('  %-16s %d' % (k, v))

st = [h for h in hits if h[2].startswith('st')]
print('\nSTORE-shaped candidates: %d' % len(st))
for addr, sz, kind, d, form in st[:25]:
    print('  0x%05X  %-14s gp%+#7x  (%s, %d bytes)  bytes %s'
          % (addr, kind, d, form, sz, a[addr:addr + sz].tobytes().hex()))

print('\nALL candidates by address (first 40), for adjudication against Ghidra:')
for addr, sz, kind, d, form in hits[:40]:
    print('  0x%05X  %-16s gp%+#7x  %s' % (addr, kind, d, form))

# The same block, but asking whether it is instead a bulk copy target: look for the knot
# VALUES as a contiguous ROM table.  A 10-knot X curve is monotone ascending.
print('\nlooking for a monotone 10-knot u16 table in the cal region (a copy SOURCE):')
found = 0
for base in range(0xC4000, 0xCD000, 2):
    v = [int(a[base + 2 * k]) | (int(a[base + 2 * k + 1]) << 8) for k in range(10)]
    if all(0 < v[k] < v[k + 1] for k in range(9)) and v[9] <= 0x6400 and v[0] >= 8:
        print('  0x%05X  %s' % (base, v))
        found += 1
        if found >= 12:
            break
if not found:
    print('  none with that shape')
