#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""CENSUS EVERY PARAMETRIC PUMP IN THE ENGAGED PATH, RANKED BY DEPTH.

WHY.  V59 flew 2026-07-30 and MEASURED a parametric gain pump: the boost-amplitude index gp-0x6ba6
has its own spectrum peaking at 42.19 Hz = 2x the 21.09 Hz grinding mode (prominence 11.10x,
coherence 0.795, 13 disjoint runs), and it is ABSENT disengaged.  A rate-dependent gain driven by a
RECTIFIED rate sweeps at 2x the mode frequency, so any such curve is a parametric pump at 2f into a
mode at f -- the textbook parametric-resonance condition, and the mode at f is the grinding mode.

The kit priced exactly TWO curves (0xD28DC / 0xD2888) and only for mode slot 10, which this car does
not use.  **Nobody ever asked how many others there are.**  This does.

🛑 METHOD CORRECTION 2026-09-01 -- THE ORIGINAL RUN-DETECTION WAS UNSOUND.
The pointer families are packed BACK TO BACK with no terminator: slot 58 of one family is slot 0 of
the next, and it dereferences to a perfectly valid record. So "walk until an entry stops looking like
a record" NEVER terminates at the real boundary -- it runs to whatever cap you set. Worse, a
"run of aligned words pointing into the record region" merges ALL adjacent families into ONE run and
reports a wrong base, which is what produced 27 tables and 0 rows on the first attempt here.

**A FAMILY'S SIZE IS THE STRIDE BETWEEN KNOWN BASES, NEVER A PROPERTY OF ITS ENTRIES.**
    gap 0xE8 = 58 slots  -- damper, boost, rate-lane surface. Selected by gp+0x63fd.
    gap 0x70 = 28 slots  -- Kp/Kd/quadrant block at 0xCB7D4..0xCBA04. Selected by gp-0x674e.
The record's "the pointer array is 34 slots, a GIVEN bound" is WRONG; slots 34-57 exist and parse.

METHOD.
  1. Find the mode-indexed POINTER TABLES mechanically: runs of >= 16 four-byte-aligned words in the
     0xC8000-0xD0000 region whose values all land in the mode-record region 0xD0000-0xD8000.
     (Retained for discovery only -- see the correction above before trusting any LENGTH it implies.)
  2. For each table, follow slot MODE_ENGAGED (26) and slot MODE_MANUAL (24) and parse the record as
     [npt][X x npt][Y x npt].
  3. Score each curve by its parametric depth over the operating range:
         g   = Y(op_hi) / Y(op_lo)          (the gain ratio the index actually sweeps)
         eps = (1 - g) / (1 + g)            (the modulation depth that pumps at 2f)
     eps is what sets the pump strength; a FLAT curve has eps = 0 and cannot pump at all.

🛑 eps ONLY MEANS 'PUMP' FOR A MULTIPLICATIVE GAIN CURVE.  Several rows below are ADDITIVE
torque curves (FactorC 0xD77D0 = [0,234,429,908], FactorE 0xD780C = [0,140,539,927], and the other
Y[0]==0 rows).  Modulating a TORQUE is not parametric pumping -- only modulating a GAIN is.  Those
rows score eps = 1.000 purely because Ymin = 0, and that is an ARTEFACT of the formula, not a deep
pump.  Read the eps ranking only across the multiplicative rows.

\U0001f6d1 WHAT THIS IS AND IS NOT.  It ranks CANDIDATES by how much modulation each curve could inject.
It does NOT prove any of them drives the mode -- V59's own note is that causality cannot be settled
from rectified data, because a mode dying for its own reasons pins the index and produces identical
numbers.  Only an intervention separates drive from echo.  This census says WHICH curves are worth
intervening on, in what order.

\U0001f6d1 AND THE OPERATING RANGE IS ASSUMED, NOT MEASURED, FOR EVERY CURVE BUT THE TWO V59 PROBED.
Each curve has its own index with its own distribution; only gp-0x6ba6's was ever measured
(76.93 % <512, 18.46 % 512-1k, 4.57 % 1k-2k, 0.04 % >=2k).  For the rest this uses the record's own
X range as a proxy, which OVERSTATES depth for any index that lives near one end.  Read the ranking,
not the decimals.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import glob
import os
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMGDIR = os.path.join(FW, 'analysis-2020accord')
PTR_LO, PTR_HI = 0xC8000, 0xCE000          # where the pointer tables live (below the records)
REC_LO, REC_HI = 0xCE000, 0xE0000          # where the mode records live -- WIDER than the
                                           # 0xD0000-0xD8000 first assumed: real tables run
                                           # from 0xCE5E8 up past 0xD98DC, and a narrow
                                           # window truncates every run AND shifts the base
MODE_ENGAGED, MODE_MANUAL = 26, 24
MIN_RUN = 16                                # a mode table has at least this many slots

# the two curves V59 actually probed, for anchoring
KNOWN = {0xD28DC: 'AMP1 (V58/V59/V60 studied this, mode slot 10)',
         0xD2888: 'AMP4 (V58/V59/V60 studied this, mode slot 10)'}


def image(tag):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*plain_image.bin' % tag))
         if 'DO-NOT-FLASH' not in os.path.basename(q) and 'SUPERSEDED' not in os.path.basename(q)]
    return open(p[0], 'rb').read() if p else None


def u16(b, a):
    return struct.unpack_from('<h', b, a)[0]


def u32(b, a):
    return struct.unpack_from('<I', b, a)[0]


def find_tables(img):
    """Runs of >= MIN_RUN aligned words all pointing into the mode-record region."""
    out, run, start = [], 0, None
    for a in range(PTR_LO, PTR_HI - 4, 4):
        v = u32(img, a)
        if REC_LO <= v < REC_HI:
            if run == 0:
                start = a
            run += 1
        else:
            if run >= MIN_RUN:
                out.append((start, run))
            run, start = 0, None
    if run >= MIN_RUN:
        out.append((start, run))
    return out


def record(img, p):
    n = u16(img, p)
    if not (2 <= n <= 8) or not (REC_LO <= p < REC_HI - 4 * n - 2):
        return None
    X = [u16(img, p + 2 + 2 * k) for k in range(n)]
    Y = [u16(img, p + 2 + 2 * n + 2 * k) for k in range(n)]
    if any(X[k] >= X[k + 1] for k in range(n - 1)):     # X must be strictly increasing
        return None
    if max(Y) <= 0:
        return None
    return n, X, Y


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'v112'
    img = image(tag)
    if img is None:
        print('  no image for %r' % tag)
        return
    print('=' * 96)
    print('  PARAMETRIC PUMP CENSUS  --  every mode-selected rate curve, ranked by depth   [%s]' % tag)
    print('=' * 96)

    tables = find_tables(img)
    print('\n  %d mode-indexed pointer table(s) found in [0x%05X, 0x%05X)\n'
          % (len(tables), PTR_LO, PTR_HI))

    rows, anchors = [], []
    for base, n in tables:
        if n <= MODE_ENGAGED:
            continue
        pe, pm = u32(img, base + MODE_ENGAGED * 4), u32(img, base + MODE_MANUAL * 4)
        re_, rm = record(img, pe), record(img, pm)
        if re_ is None:
            continue
        npt, X, Y = re_
        g = min(Y) / max(Y)
        eps = (1 - g) / (1 + g)
        # is this table one of the two V59 probed?
        anchor = ''
        if n > 10:
            p10 = u32(img, base + 10 * 4)
            if p10 in KNOWN:
                anchor = KNOWN[p10].split('(')[0].strip()
                anchors.append((base, p10, KNOWN[p10]))
        rows.append((eps, base, n, pe, pm, npt, X, Y, rm is not None and pe != pm, anchor))

    if anchors:
        print('  ANCHORS -- tables whose slot 10 matches an address the V58/V59/V60 record names:')
        for base, p10, why in anchors:
            print('    table 0x%06X slot 10 -> 0x%06X   %s' % (base, p10, why))
        print()

    rows.sort(reverse=True)
    print('  %-8s %-9s %-9s %-6s %-5s %s' % ('eps', 'table', 'idx26', 'npt', 'm24?', 'Y (engaged)'))
    print('  ' + '-' * 92)
    for eps, base, n, pe, pm, npt, X, Y, part, anchor in rows:
        flag = ' <== ' + anchor if anchor else ''
        print('  %-8.3f 0x%06X 0x%06X %-6d %-5s %s%s'
              % (eps, base, pe, npt, 'yes' if part else 'NO', Y, flag))
    print('  ' + '-' * 92)
    print('  eps = (1-g)/(1+g), g = Ymin/Ymax. A FLAT curve has eps = 0 and cannot pump at all.')
    print('  "m24?" = does mode 24 (MANUAL) resolve to a DIFFERENT record? If NO, an edit is not')
    print('  mode-partitioned and would change manual feel too.')
    print('\n  \U0001f6d1 CANDIDATES RANKED BY POSSIBLE DEPTH -- not proof any of them drives the mode.')
    print('     Causality cannot be settled from rectified data; only an intervention can.')
    print('     The operating range is the record\'s own X span except for the two V59 probed,')
    print('     so depth is OVERSTATED for any index that lives near one end.')


if __name__ == '__main__':
    main()
