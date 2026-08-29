# -*- coding: utf-8 -*-
"""GATE 1 on the residual-LERP RAM window, and find what fills it from flash.

X at gp-0x64b8..0x64a6, Y at gp-0x641c..0x640a.  In FUN_00038148 these are read gp-relative,
so unlike FUN_00036c12 (which dereferences the 0xCBE74 pointer table directly) this table is
COPIED into RAM.  Find the copier.

Classify EVERY reference to the relevant disp16 values by V850 opcode:
  Format VII (4B): hw1 = (reg2<<11)|(op<<5)|reg1   op 0x38 ld.b 0x39 ld.h 0x3A st.b 0x3B st.h
  Format VI  (4B): op 0x30 addi, 0x31 movea, 0x32 movhi  -- an ADDRESS being formed = a copy dest
A st.* means a per-element writer; a movea/addi means the base address is taken (memcpy).
"""
import io, struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
b = io.open('C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/'
            'stock_fw_dump/code.bin', 'rb').read()
OPS = {0x30: 'addi', 0x31: 'movea', 0x32: 'movhi',
       0x38: 'ld.b', 0x39: 'ld.h', 0x3A: 'st.b', 0x3B: 'st.h'}
TARGETS = {
    0x64B8: 'X[0]  gp-0x64b8', 0x64A6: 'X[8]  gp-0x64a6',
    0x641C: 'Y[0]  gp-0x641c', 0x640A: 'Y[8]  gp-0x640a',
    0x64B6: 'X[1]  gp-0x64b6  (the LERP walk start)',
}
for off, what in TARGETS.items():
    disp = (0x10000 - off) & 0xFFFF
    print('\n=== %s   disp16 0x%04X' % (what, disp))
    found = []
    for i in range(2, len(b) - 1, 2):
        if (b[i] | (b[i + 1] << 8)) != disp:
            continue
        hw1 = b[i - 2] | (b[i - 1] << 8)
        op = (hw1 >> 5) & 0x3F
        r1, r2 = hw1 & 0x1F, hw1 >> 11
        nm = OPS.get(op)
        if nm is None:
            continue
        # Format VI (addi/movea/movhi) uses reg1 as source; Format VII uses reg1 as base
        found.append((i - 2, nm, r1, r2))
    if not found:
        print('    no classified reference')
    for a, nm, r1, r2 in found:
        tag = ''
        if nm in ('st.h', 'st.b'):
            tag = '   <== PER-ELEMENT WRITER'
        elif nm in ('movea', 'addi') and r1 == 4:
            tag = '   <== ADDRESS TAKEN (memcpy destination?)'
        print('    0x%05X  %-6s r%-2d, r%-2d%s' % (a, nm, r1, r2, tag))

print('\n' + '=' * 76)
print('Does any code form the ADDRESS of the window (a block copy)?')
print('Looking for movea/addi with reg1 = gp(r4) and a disp inside [-0x64b8, -0x640a]:')
lo, hi = (0x10000 - 0x64B8), (0x10000 - 0x640A)
seen = []
for i in range(2, len(b) - 1, 2):
    d = b[i] | (b[i + 1] << 8)
    if not (lo <= d <= hi):
        continue
    hw1 = b[i - 2] | (b[i - 1] << 8)
    op = (hw1 >> 5) & 0x3F
    if op not in (0x30, 0x31) or (hw1 & 0x1F) != 4:
        continue
    seen.append((i - 2, OPS[op], 0x10000 - d, hw1 >> 11))
for a, nm, off, r2 in seen:
    print('    0x%05X  %s -0x%04X[gp] -> r%d' % (a, nm, off, r2))
if not seen:
    print('    NONE -- the window is not addressed as a block by any movea/addi on gp.')
    print('    => it is filled either by per-element stores, or by a copy whose destination')
    print('       register is computed elsewhere (register-indirect -- invisible to this scan).')
