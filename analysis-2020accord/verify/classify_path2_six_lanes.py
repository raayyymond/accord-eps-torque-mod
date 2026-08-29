# -*- coding: utf-8 -*-
"""Classify all six lanes of FUN_00038148's Path-2 sum: who WRITES each, and is it a derivative?

The sum is  Sigma_k (x_k * gate_k * w[k]) >> 10  with w[k] at tp+0x73a0..0x73aa = 0xC63A0..AA.
gp-0x6b26 is already proved to be K*acceleration (omega^2).  If another lane is also a
derivative, it is a second lever of the same frequency-selective family.

V850 Format VII 4-byte gp-relative:  hw1 = (reg2<<11) | (op<<5) | reg1,  hw2 = disp16
  op 0x38 ld.b   0x39 ld.h   0x3A st.b   0x3B st.h        reg1 must be 4 (gp)
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
b = io.open('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
            'stock_fw_dump/code.bin', 'rb').read()

LANES = [
    (0xC63A0, 0x6bd0, 0x800,  'w[0] gp-0x6bd0  base-assist damper (FactorC x FactorE)'),
    (0xC63A2, 0x6bbe, 0x800,  'w[1] gp-0x6bbe  VISCOUS + DC pedestal (~90 ct/(rad/s))'),
    (0xC63A4, 0x6b46, 0x400,  'w[2] gp-0x6b46  ??? -- shares the +-1024 gate with the inertia lane'),
    (0xC63A6, 0x6b26, 0x400,  'w[3] gp-0x6b26  INERTIA = K * acceleration  [PROVED]'),
    (0xC63A8, 0x6b4e, 0x2800, 'w[4] gp-0x6b4e  ???'),
    (0xC63AA, 0x6b4c, 0x2800, 'w[5] gp-0x6b4c  11-slot assist sum'),
]
OPS = {0x38: 'ld.b', 0x39: 'ld.h', 0x3A: 'st.b', 0x3B: 'st.h'}

for wcal, off, gate, what in LANES:
    disp = (0x10000 - off) & 0xFFFF
    print('\n=== %s' % what)
    print('    weight 0x%05X   gate |x| <= %d   disp16 0x%04X' % (wcal, gate, disp))
    writers, readers, other = [], [], []
    for i in range(2, len(b) - 1, 2):
        if (b[i] | (b[i + 1] << 8)) != disp:
            continue
        hw1 = b[i - 2] | (b[i - 1] << 8)
        if (hw1 & 0x1F) != 4:                      # reg1 must be gp
            other.append(i)
            continue
        op = (hw1 >> 5) & 0x3F
        rec = (i - 2, OPS.get(op, '0x%02X' % op), hw1 >> 11)
        (writers if op in (0x3A, 0x3B) else readers if op in (0x38, 0x39) else other).append(rec)
    print('    WRITERS: %s' % (', '.join('0x%05X %s r%d' % w for w in writers) or 'none found'))
    print('    readers: %d   (%s)' % (len(readers),
          ', '.join('0x%05X' % r[0] for r in readers[:8]) or '-'))
    if other:
        print('    non-gp / unclassified halfword matches: %d' % len(other))
