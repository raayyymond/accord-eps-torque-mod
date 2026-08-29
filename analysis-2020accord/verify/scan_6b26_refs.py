# -*- coding: utf-8 -*-
"""Locate every site referencing gp-0x6b26 (disp16 = 0x94DA) by raw LE byte scan.
Python is the mandated second method: operand-text search cannot see register-indirect
writes, and search_instructions silently undercounts unanalysed regions."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
b = io.open('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
            'stock_fw_dump/code.bin', 'rb').read()
TARGETS = {0x94DA: 'gp-0x6b26', 0x93D4: 'gp-0x6c2c', 0x93D2: 'gp-0x6c2e'}
for want, nm in TARGETS.items():
    hits = [i for i in range(0, len(b) - 1, 2) if (b[i] | (b[i + 1] << 8)) == want]
    print('%-10s disp 0x%04X : %d aligned halfword hit(s)' % (nm, want, len(hits)))
    for i in hits:
        print('    0x%05X   ctx %s' % (i, b[max(0, i - 6):i + 6].hex()))
