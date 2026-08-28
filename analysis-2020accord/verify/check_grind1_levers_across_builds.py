# -*- coding: utf-8 -*-
"""Does the build on the car carry LEVER B -- the kit's BEST measured grind-#1 fix?

Lever B (V67/V68/V71c):
    0x3AA96   C5 -> FB     repoints ld.bu -0x683c[gp] -> -0x6806[gp], the LKAS gate
                           (gate == latActive 99.983 %)
    0xC6446  512 -> 5244   the arm
Measured on-car: grind #1 0.40 [0.27, 0.58] -- BEST IN THE KIT -- and creep grind #2 -> 0 bursts
(P(0) = 0.0005). Mode-proof.

Lever A (V62): 0x3AB76 + 0x3AC20  AA -> A9.  grind #1 0.39 [0.32, 0.48], operator "gone",
but the r24 half raised 40-49 Hz x11.7 => it CAUSED grind #2.

accord-v88-lever-b-restored says V88 restored Lever B on a V87 base. Check whether that
survived into the current line.
"""
import glob, os

FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
TAGS = ['_v90_', '_v91_', '_v92_', '_v96_', '_v97_', '_v98_', '_v99_', '_v100_', '_v101_',
        '_v102_', '_v103_', '_v104_', '_v105_', '_v106_', '_v107_', '_v108_', '_v109_',
        '_v111_', '_v112_', '_v113_', '_v115_', '_v116_', '_v117_', '_v120_', '_v121_']

rows = [('STOCK', open(glob.glob(FR + '/**/code.bin', recursive=True)[0], 'rb').read())]
for t in TAGS:
    g = [x for x in glob.glob(os.path.join(FR, t + '*plain_image.bin')) if 'SUPERSEDED' not in x]
    if g:
        rows.append((t.strip('_').upper(), open(g[0], 'rb').read()))

print("LEVER B -- the kit's BEST measured grind-#1 fix (0.40 [0.27,0.58], + grind #2 -> 0)\n")
print("  build     0x3AA96          0xC6446        0x3AB76   0x3AC20     LEVER B?  LEVER A?")
nb = na = 0
for name, d in rows:
    gate = d[0x3AA96]
    arm = int.from_bytes(d[0xC6446:0xC6448], 'little')
    a26 = d[0x3AB76]
    a24 = d[0x3AC20]
    hasB = (gate == 0xFB) and (arm == 5244)
    hasA = (a26 == 0xA9) and (a24 == 0xA9)
    if name != 'STOCK':
        nb += hasB
        na += hasA
    print("  %-8s  %02X %-12s  %-5d %-8s  %02X %-6s  %02X %-6s  %-8s  %s"
          % (name, gate, '(LKAS gate)' if gate == 0xFB else '(stock)',
             arm, '(ARMED)' if arm == 5244 else '(stock)',
             a26, 'A9' if a26 == 0xA9 else 'stock',
             a24, 'A9' if a24 == 0xA9 else 'stock',
             'YES' if hasB else 'no', 'YES' if hasA else 'no'))
n = len(rows) - 1
print("\n  builds carrying LEVER B: %d of %d" % (nb, n))
print("  builds carrying LEVER A: %d of %d" % (na, n))
