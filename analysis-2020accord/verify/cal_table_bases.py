# -*- coding: utf-8 -*-
"""THE AUTHORITATIVE LIST OF CALIBRATION TABLE BASES -- derived from the CODE, not guessed.

Why this exists.  Twice in one session a cell the record treats as a SCALAR turned out to be a knot
in a count/X/Y LERP table:

    0xC676A  recorded "non-stock since V25, ZERO READERS FOUND, may be inert"
             -> Y[1] of the table at 0xC6760.  Reached by POINTER ARITHMETIC (add 0x2, r6), which a
                tp-displacement scan cannot see.  Only a ladder's SATURATION arms are displacement-
                addressed, so a scan finds the ENDS of a table and misses the MIDDLE.
    0xC674E  recorded as "the EME wall", a scalar that V211/V219 assert must exceed the tracking
             clamp -> Y[0] of the table at 0xC6748.  The firmware never makes that comparison; the
             archive had noticed both that and the "exactly one reader" without connecting them.

A pattern-matching detector is NOT good enough: scanning for "a small count followed by ascending
values" proposes 0xC63C6 as a base, which would have overturned the (correct) finding that
0xC63CC = 0 is a genuine scalar x0.  There is no movea to 0xC63C6, so it is not a base.

The layout, confirmed from two independent ladders:

    base+0        knot count n
    base+2        X[0..n-1]      ascending
    base+2+2n     Y[0..n-1]

A base is REAL only if some instruction materialises it: `movea <disp>, tp, rN`, opcode 0x31 with
reg1 = tp (r5).  That is what this enumerates.

Run:  python analysis-2020accord/verify/cal_table_bases.py
"""
import glob
import os
import struct
import sys

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
A = os.path.join(ROOT, 'analysis-2020accord')
ST = open(os.path.join(A, 'stock_fw_dump', 'code.bin'), 'rb').read()
TP = 0xBF000
LO, HI = 0xC4000, 0xC7000


def s16(b, a):
    return struct.unpack_from('<h', b, a)[0]


def u16(b, a):
    return struct.unpack_from('<H', b, a)[0]


def movea_bases(b=ST):
    """Every `movea <disp>, tp, rN` landing in the cal region -- the REAL bases."""
    out = {}
    for i in range(2, len(b) - 3, 2):
        h1 = b[i] | (b[i + 1] << 8)
        if (h1 & 0x1F) != 5 or ((h1 >> 5) & 0x3F) != 0x31:
            continue
        d = b[i + 2] | (b[i + 3] << 8)
        if d & 0x8000:
            d -= 0x10000
        a = TP + d
        if LO <= a < HI:
            out.setdefault(a, []).append(i)
    return out


def tables(b=ST):
    """Bases that are also well-formed count/X/Y tables, with their byte extents."""
    out = []
    for B in sorted(movea_bases(b)):
        n = s16(b, B)
        if not (1 <= n <= 8):
            continue
        # !! AXES MAY BE SIGNED **OR** UNSIGNED. Reading them as signed only rejected FIVE
        # well-formed tables whose axis crosses 0x8000 -- including 0xC6A08 in the delivery chain
        # and 0xC68FC inside the assist section that carries our own notch. Accept either.
        Xs = [s16(b, B + 2 + 2 * i) for i in range(n)]
        Xu = [u16(b, B + 2 + 2 * i) for i in range(n)]
        if Xs == sorted(Xs):
            X, sign = Xs, 'signed'
        elif Xu == sorted(Xu):
            X, sign = Xu, 'UNSIGNED'
        else:
            continue
        out.append({'base': B, 'n': n, 'X': X, 'axis': sign,
                    'lo': B + 2, 'hi': B + 2 + 4 * n})
    return out


def field_of(addr, tabs=None):
    """If addr is a knot of a real table, name it. Otherwise None."""
    for t in (tabs if tabs is not None else tables()):
        if t['lo'] <= addr < t['hi']:
            k = (addr - t['lo']) // 2
            return (t['base'], t['n'],
                    'X[%d]' % k if k < t['n'] else 'Y[%d]' % (k - t['n']))
    return None


if __name__ == '__main__':
    bs = movea_bases()
    ts = tables()
    print('%d movea bases in 0x%05X-0x%05X; %d are well-formed count/X/Y tables'
          % (len(bs), LO, HI, len(ts)))
    print()
    assert 0xC6748 in bs and 0xC6760 in bs and 0xC6754 in bs, 'known bases must be found'
    assert 0xC63C6 not in bs, '0xC63C6 is NOT a base -- the pattern detector was a false positive'
    print('  [PASS] 0xC6748 / 0xC6754 / 0xC6760 are real bases')
    print('  [PASS] 0xC63C6 is NOT a base -- 0xC63CC = 0 is a genuine scalar x0')
    print()
    hits = sorted(glob.glob(os.path.join(A, '_v*_*plain_image.bin')))
    hits = [h for h in hits if 'SUPERSEDED' not in os.path.basename(h)]
    for h in hits[-1:]:
        b = open(h, 'rb').read()
        ch = sorted({i & ~1 for i in range(LO, HI)
                     if ST[i] != b[i] and (i & 0xFFF) < 0xFFC})
        ins = [(c, field_of(c, ts)) for c in ch]
        ins = [(c, f) for c, f in ins if f]
        print('  %s' % os.path.basename(h))
        print('    %d changed cal cells, %d are TABLE FIELDS:' % (len(ch), len(ins)))
        for c, (B, n, role) in ins:
            print('      0x%05X  %-5s of 0x%05X (n=%d)  %6d -> %6d'
                  % (c, role, B, n, s16(ST, c), s16(b, c)))
    print()
    print('  A cell inside a table extent must NOT be reasoned about as a scalar.')
