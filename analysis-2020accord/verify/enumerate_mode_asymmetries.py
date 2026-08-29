# -*- coding: utf-8 -*-
"""Every ENGAGED-vs-MANUAL asymmetry on the FLYING build, across all mode-record families.

[[accord-stock-mode24-equals-mode26-damper-is-ours]]: STOCK ships m24 == m26 byte-identical
across all six factor families.  The ratchet is engaged-amplified ~15x.
=> ANY m24-vs-m26 difference on the car is something THIS KIT introduced, and is therefore a
candidate for the engaged-only amplification.

Compare, per pointer table, the m24 record against m26/m27 on:
  * STOCK        (must be identical -- validates the premise)
  * V122         (the FLYING build -- the asymmetries the operator actually drives)
  * V183         (the current best build -- what we would be changing to)
"""
import io, os, struct, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'


def img(v):
    g = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0], 'rb').read() if g else None


stock = io.open(A + '/stock_fw_dump/code.bin', 'rb').read()
BUILDS = [('stock', stock), ('V122 FLYING', img('v122')), ('V183 best', img('v183'))]
TABLES = [(0xC9CCC, 'L1  (index |gp-0x6bcc|)'),
          (0xC9DB4, 'L3  (index gp-0x6a10, abs angle)'),
          (0xC9E9C, 'FactorC (index gp-0x6a5e)'),
          (0xC9F84, 'FactorE (index gp-0x6ac0, elec rate)'),
          (0xC77A0, 'L5  clamp (index gp-0x6ac2)'),
          (0xCBE74, 'inertia/friction (0xCBE74)')]
u32 = lambda b, o: struct.unpack_from('<I', b, o)[0]
s16 = lambda b, o: struct.unpack_from('<h', b, o)[0]


def rec(b, ptr, maxn=8):
    if not (0x13000 <= ptr < 0x100000):
        return None
    n = s16(b, ptr)
    if not (1 <= n <= maxn):
        return None
    X = [s16(b, ptr + 2 + 2 * i) for i in range(n)]
    Y = [s16(b, ptr + 2 + 2 * n + 2 * i) for i in range(n)]
    return n, X, Y


for tbl, nm in TABLES:
    print('')
    print('=== %s   table 0x%05X' % (nm, tbl))
    for bn, b in BUILDS:
        if b is None:
            print('   %-12s (image missing)' % bn)
            continue
        out = []
        p24 = u32(b, tbl + 4 * 24)
        r24 = rec(b, p24)
        if r24 is None:
            print('   %-12s m24 record unreadable at 0x%05X' % (bn, p24))
            continue
        for m in (26, 27):
            pm = u32(b, tbl + 4 * m)
            rm = rec(b, pm)
            if rm is None:
                out.append('m%d unreadable' % m)
            elif rm == r24:
                out.append('m%d == m24' % m)
            else:
                d = []
                if rm[1] != r24[1]:
                    d.append('X %s vs %s' % (rm[1], r24[1]))
                if rm[2] != r24[2]:
                    d.append('Y %s vs %s' % (rm[2], r24[2]))
                out.append('m%d DIFFERS: %s' % (m, '; '.join(d)))
        print('   %-12s %s' % (bn, '   |   '.join(out)))

print('')
print('=' * 100)
print('READ THIS AS: on STOCK every row should say "== m24" (the premise).')
print('Any DIFFERS on the FLYING row is an engaged-only asymmetry THIS KIT created,')
print('and is therefore a candidate cause of the ~15x engaged amplification of the ratchet.')
