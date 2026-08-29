# -*- coding: utf-8 -*-
"""RE-VERIFY every gp-relative scan with a method that has NO opcode whitelist and NO
disp-parity assumption.

Two holes were found in my earlier scans:
  1. hw2 = (disp | 1) for ld.h/ld.w and st.h/ld.hu pairs -- the recorded V850 trap.
  2. an opcode whitelist that omitted ld.hu (0x3F) and other forms.
Either alone produces a FALSE NULL, and GATE 1 for V175 rests on the claim that gp-0x6b26 has
exactly one writer.  Redo it: accept ANY opcode, accept hw2 in {D, D|1}, require reg1 == gp.
Report the opcode actually seen so nothing is filtered away silently.
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
b = io.open('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
            'stock_fw_dump/code.bin', 'rb').read()

# V850E2 Format VII 4-byte, reg1-base.  opcode = (hw1>>5)&0x3F, reg1 = hw1&0x1F, reg2 = hw1>>11
# Loads read; stores write.  Names for the ones actually observed in this image.
NAME = {0x38: 'ld.b', 0x39: 'ld.h/ld.w', 0x3A: 'st.b', 0x3B: 'st.h/st.w',
        0x3C: 'ld.bu?', 0x3D: 'st?', 0x3E: 'ld?', 0x3F: 'ld.hu'}
WRITE_OPS = {0x3A, 0x3B, 0x3D}


def scan(off):
    D = (0x10000 - off) & 0xFFFF
    out = []
    for i in range(2, len(b) - 1, 2):
        h2 = b[i] | (b[i + 1] << 8)
        if h2 != D and h2 != (D | 1):
            continue
        h1 = b[i - 2] | (b[i - 1] << 8)
        if (h1 & 0x1F) != 4:                 # reg1 must be gp
            continue
        op = (h1 >> 5) & 0x3F
        out.append((i - 2, op, h1 >> 11, h2))
    return out


TARGETS = [
    (0x6b26, 'gp-0x6b26  INERTIA -- GATE 1 for V175 rests on this'),
    (0x6982, 'gp-0x6982  Y-scale input'),
    (0x6984, 'gp-0x6984  X-scale input'),
    (0x6bd0, 'gp-0x6bd0  w[0] damper'),
    (0x6bbe, 'gp-0x6bbe  w[1] viscous'),
    (0x6b46, 'gp-0x6b46  w[2]'),
    (0x6b4e, 'gp-0x6b4e  w[4]'),
    (0x6b4c, 'gp-0x6b4c  w[5]'),
]
for off, nm in TARGETS:
    h = scan(off)
    w = [x for x in h if x[1] in WRITE_OPS]
    r = [x for x in h if x[1] not in WRITE_OPS]
    print('\n=== %s' % nm)
    print('    total gp-relative sites: %d   (writers %d, readers %d)' % (len(h), len(w), len(r)))
    for a, op, r2, h2 in w:
        print('      WRITE 0x%05X  op 0x%02X %-10s r%-2d  hw2=%04X'
              % (a, op, NAME.get(op, '?'), r2, h2))
    for a, op, r2, h2 in r:
        print('      read  0x%05X  op 0x%02X %-10s r%-2d  hw2=%04X'
              % (a, op, NAME.get(op, '?'), r2, h2))

print('\n' + '=' * 74)
print('OPCODE CENSUS across all targets -- shows what a whitelist would have dropped')
from collections import Counter
c = Counter()
for off, _ in TARGETS:
    for a, op, r2, h2 in scan(off):
        c[op] += 1
for op, n in sorted(c.items()):
    print('   op 0x%02X  %-10s  %d site(s)%s'
          % (op, NAME.get(op, '?'), n, '   <- MISSED by the old whitelist' if op > 0x3B else ''))
