# -*- coding: utf-8 -*-
"""RELIABLE reader census for a tp-relative calibration cell.

WHY THIS EXISTS
---------------
The kit's standard method -- scan the image for the 16-bit displacement, in both the plain and the
`| 1` form -- has a false-positive rate that ranges from bad to useless, because the displacement
bytes occur inside other instructions' encodings:

    0xC407E   raw 4  hits ->  3 real   (0x07028 was `dispose 0x0, {r25,r27,r29,lp}, lp`)
    0xC4004   raw 7  hits ->  3 real   (0x0B8DE was `mov 0xfedf5004, r8` -- a RAM ADDRESS)
    0xC642A   raw 52 hits ->  1 real   (0x3A118 was `cmpf.s le, r28, r15, 0x5` -- an FP compare)
    0xC642C   raw 43 hits ->  1 real

98 % noise on the worst of them.  A census is load-bearing -- it is how blast radius is decided
before an edit -- so guessing from raw hits is not acceptable.

THE FILTER
----------
V850 Format-VII loads/stores encode the BASE REGISTER in the low 5 bits of the FIRST halfword:

    ld.h  0x740a, tp, r12   ->  bytes 25 67 0a 74   hw1 = 0x6725,  0x6725 & 0x1F = 5 = tp
    ld.hu 0x7936, tp, r14   ->  bytes e5 77 37 79   hw1 = 0x7725,  ... & 0x1F = 5
    ld.w  0x5004, tp, r14   ->  bytes 25 77 05 50   hw1 = 0x7725,  ... & 0x1F = 5

So a genuine tp-relative access must have  (hw1 & 0x1F) == 5.  Requiring that reproduces every
hand-verified census in this kit exactly, at a fraction of the noise.

⚠ IT IS A FILTER, NOT A PROOF.  It removes false positives; it cannot invent a hit it never saw.
Two things it still will not catch:
  * the 6-byte gp/tp form, where disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F);
  * an access through a register loaded with the absolute address (e.g. `mov 0xfedf5004, r8`
    then `ld.w 0[r8]`) -- which is exactly what 0x0B8DE turned out to be.
ALWAYS confirm the survivors at the instruction boundary (Ghidra `disassemble_bytes`) before
resting a build on the count.  Python and Ghidra in parallel, adjudicate disagreements.

USAGE:  python analysis-2020accord/verify/tp_cal_readers.py 0xC642A [0xC642C ...]
"""
import os, sys, glob, struct

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
TP = 0xBF000
CODE_LO, CODE_HI = 0x1000, 0xC0000


def census(img, cell):
    disp = cell - TP
    raw, real = [], []
    for d in (disp, disp | 1):
        t = struct.pack('<H', d)
        i = img.find(t)
        while i != -1:
            a = i - 2
            if i % 2 == 0 and CODE_LO <= a < CODE_HI:
                raw.append(a)
                hw1 = struct.unpack_from('<H', img, a)[0]
                if (hw1 & 0x1F) == 5:
                    real.append(a)
            i = img.find(t, i + 1)
    return sorted(set(raw)), sorted(set(real))


cands = glob.glob(os.path.join(ROOT, '**', 'stock_fw_dump', 'code.bin'), recursive=True)
if not cands:
    print('  stock code.bin not found under %s' % ROOT)
    sys.exit(1)
img = open(cands[0], 'rb').read()

cells = [int(a, 0) for a in sys.argv[1:]] or [0xC407E, 0xC4004, 0xC640A, 0xC63A6]
for cell in cells:
    raw, real = census(img, cell)
    print('  0x%05X (tp+0x%04X) = %d' % (cell, cell - TP, struct.unpack_from('<H', img, cell)[0]))
    print('     raw hits      %3d   %s' % (len(raw), ' '.join('0x%05X' % a for a in raw[:12])))
    print('     tp-filtered   %3d   %s' % (len(real), ' '.join('0x%05X' % a for a in real[:12])))
    if len(raw) != len(real):
        print('     => %d false positive(s) removed. CONFIRM the survivors in Ghidra before'
              ' resting a build on this.' % (len(raw) - len(real)))
    print()
