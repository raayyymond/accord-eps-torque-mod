# -*- coding: utf-8 -*-
"""Every st.h into the assist-map knot block, decoded PROPERLY, with its source register.

Encoding pinned from real bytes at 0x38FD0 (`st.h r0, -0x6430, gp` = 64 07 d0 9b):
    hw1 = 0x0764 : bits[4:0]=reg1=4(gp)  bits[10:5]=0x3B  bits[15:11]=reg2=0 (source)
    hw2 = 0x9BD0 : disp16, bit0 is the st.h/st.w discriminator (0 => st.h)

My earlier pass labelled top6=0x3B as "st.w" and so could not tell store-zero from a real
write.  The question that matters: is there ANY st.h into the block whose SOURCE REGISTER
IS NOT r0?  If not, every write to these knots is a clear, and the values must arrive by a
bulk copy or a register-indirect store that no operand-text search can see.
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
XLO, XHI = -0x6430, -0x641c        # X knots
YLO, YHI = -0x6444, -0x6432        # Y knots


def hw(i):
    return int(a[i]) | (int(a[i + 1]) << 8)


def sext16(v):
    return v - 0x10000 if v & 0x8000 else v


rows = []
for i in range(0, n - 4, 2):
    h1 = hw(i)
    if (h1 & 0x1F) != GP:
        continue
    if ((h1 >> 5) & 0x3F) != 0x3B:
        continue
    h2 = hw(i + 2)
    kind = 'st.h' if (h2 & 1) == 0 else 'st.w'
    d = sext16(h2 & 0xFFFE)
    if not (XLO <= d <= XHI or YLO <= d <= YHI):
        continue
    src = (h1 >> 11) & 0x1F
    rows.append((i, kind, d, src))

print('st.h / st.w into the knot block, decoded with the pinned encoding')
print('%-10s %-6s %-10s %-8s %s' % ('addr', 'kind', 'disp', 'src reg', 'note'))
nz = 0
for i, kind, d, src in rows:
    note = 'STORE-ZERO (clear)' if src == 0 else '*** NON-ZERO SOURCE ***'
    if src != 0:
        nz += 1
    print('0x%05X   %-6s gp%+#7x   r%-7d %s' % (i, kind, d, src, note))
print('\ntotal %d stores, of which %d have a NON-r0 source' % (len(rows), nz))

if nz == 0:
    print("""
=> EVERY st.h into these knots is a CLEAR.  The values therefore arrive either by a bulk
   copy (ld/st through a pointer) or a register-indirect store, neither of which any
   operand-text search can see.  Look for a loop whose destination pointer is loaded with
   the block's absolute address.""")
    # gp = 0xFEDF8000 per the kit's constant; the block's absolute addresses
    GPV = 0xFEDF8000
    print('\n   block absolute addresses: X 0x%08X-0x%08X   Y 0x%08X-0x%08X'
          % (GPV + XLO, GPV + XHI, GPV + YLO, GPV + YHI))
    # look for movhi/movea pairs that materialise an address inside the block
    lo16 = [(GPV + d) & 0xFFFF for d in range(YLO, XHI + 1, 2)]
    want = set(lo16)
    hi = ((GPV + YLO) >> 16) & 0xFFFF
    hits = []
    for i in range(0, n - 8, 2):
        h1 = hw(i)
        if ((h1 >> 5) & 0x3F) != 0x32:      # movhi
            continue
        if hw(i + 2) != hi and hw(i + 2) != (hi + 1) & 0xFFFF:
            continue
        for j in (i + 4, i + 6, i + 8):
            if j + 4 > n:
                break
            hj = hw(j)
            if ((hj >> 5) & 0x3F) == 0x31:  # movea
                v = hw(j + 2)
                if v in want or ((v - 0x10000) & 0xFFFF) in want:
                    hits.append((i, j, hw(i + 2), v))
                break
    print('\n   movhi/movea pairs materialising an address in the block: %d' % len(hits))
    for i, j, h, v in hits[:15]:
        print('     movhi 0x%04X @0x%05X  +  movea 0x%04X @0x%05X  => 0x%08X'
              % (h, i, v, j, (h << 16) + sext16(v)))
