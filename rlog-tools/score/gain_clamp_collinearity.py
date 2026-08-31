#!/usr/bin/env python3
r"""THE GAIN AND THE CLAMP ARE PERFECTLY COLLINEAR IN EVERY FLOWN BUILD.

THE FINDING.  Re(Z) at 6-9 Hz across 16 flown builds is a clean monotone dose-response in the forward
gain -- the best-supported relationship in the whole ratchet analysis:

    gain    n    median Re(Z)    range
    4.0x    6       -55.37       -46.6 .. -66.8
    6.0x    9       -68.49       -62.3 .. -74.9      <- the car (V112) sits here
    8.0x    1       -84.06

    4x -> 6x  =  -13.1 units per 2x  =  -6.6 per 1x
    6x -> 8x  =  -15.6 units per 2x  =  -7.8 per 1x

That is STEEPER than the -4.4 per 1x this kit has been quoting, which came from a single era-free
contrast (V101->V102).  The three-dose version is better supported and says the gain is worth ~13
units of Re(Z) between 6x and 4x -- **20 % of the 65-unit requirement from one cell.**

\U0001f6d1 AND HERE IS THE PROBLEM.  The tracking rule `clamp = gain * 512 // 891` was held EXACTLY on
every one of those builds:

    gain 4.0x  ->  clamp 2048        gain 6.0x  ->  clamp 3072        gain 8.0x  ->  clamp 4096

So the gain and the clamp are **PERFECTLY COLLINEAR IN THE ENTIRE FLOWN CORPUS**.  Nothing in this
data can distinguish "lower gain improves Re(Z)" from "lower clamp improves Re(Z)".  Both readings fit
all 16 builds exactly.

WHY IT MATTERS, and it is not academic.  The two readings make OPPOSITE predictions for the builds now
on the shelf, because those builds deliberately break the tracking:

    build   gain   clamp    if GAIN drives it        if CLAMP drives it
    V256    6.0x   4096     no change (~-68)         WORSE  (~-77, an 8x-era clamp)
    V258    4.0x   4096     BETTER (~-55)            WORSE  (~-77)
    V259    4.0x   4096     BETTER + damper          WORSE + damper

⇒ **V256 IS THE DISAMBIGUATING EXPERIMENT, and it is the highest-information build on the shelf.**
It moves the clamp ALONE (gain held at the car's 6x), which no build has ever done.  One short
symptomatic drive settles a relationship that 16 flown builds could not:

    V256 Re(Z) ~ unchanged from the car   => the CLAMP is inert for Re(Z); the gain drives it;
                                             V258/V259's predicted +13 is real and worth flying.
    V256 Re(Z) clearly WORSE (~ -77)      => the CLAMP drives it, the gain slope is an artifact of
                                             the tracking rule, and V258/V259 should NOT be flown as
                                             ratchet builds -- raising the clamp is what hurt.
    V256 Re(Z) clearly BETTER             => neither reading is right; something else tracks the era.

\U0001f6d1 PHYSICALLY THE GAIN READING IS MORE PLAUSIBLE -- the gain scales delivered torque at EVERY
command, while the clamp only binds at the rail (~30 % duty on the car) -- but plausible is not
measured, and the whole point of this file is that the corpus cannot tell them apart.

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
import statistics as st
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMG = os.path.join(FW, 'analysis-2020accord')

# coherence-gated 6-9 Hz Re(Z) per flown build, from antidamping_by_build.py
REZ = {'V90': -59.99, 'V91': -53.36, 'V96': -54.13, 'V98': -46.61, 'V99': -56.60,
       'V100': -66.83, 'V101': -84.06, 'V102': -74.91, 'V103': -72.28, 'V104': -64.77,
       'V105': -67.78, 'V106': -63.45, 'V107': -62.28, 'V111': -70.58, 'V112': -68.49,
       'V122': -70.13}
GAIN_CELL, CLAMP_CELL = 0xC6CD0, 0xC61B2


def image(tag):
    p = [q for q in glob.glob(os.path.join(IMG, '_%s_*plain_image.bin' % tag.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q) and 'SUPERSEDED' not in os.path.basename(q)]
    return open(p[0], 'rb').read() if p else None


def main():
    print('=' * 84)
    print('  GAIN vs CLAMP: PERFECTLY COLLINEAR IN EVERY FLOWN BUILD')
    print('=' * 84)
    rows = []
    for tag, rez in REZ.items():
        b = image(tag)
        if b is None:
            continue
        g = struct.unpack_from('<H', b, GAIN_CELL)[0]
        c = struct.unpack_from('<H', b, CLAMP_CELL)[0]
        rows.append((g / 891.0, c, rez, tag))
    rows.sort()
    print('\n  %-7s %8s %8s %9s %s' % ('build', 'gain', 'clamp', 'Re(Z)', 'clamp == gain*512//891 ?'))
    print('  ' + '-' * 62)
    collinear = True
    for g, c, rez, tag in rows:
        want = int(891 * g) * 512 // 891
        ok = (c == want)
        collinear &= ok
        print('  %-7s %7.2fx %8d %9.2f  %s%s'
              % (tag, g, c, rez, 'yes' if ok else 'NO  (want %d)' % want,
                 '   <== THE CAR' if tag == 'V112' else ''))
    print('  ' + '-' * 62)
    print('  tracking rule holds on EVERY flown build: %s' % collinear)

    print('\n  DOSE-RESPONSE BY GAIN')
    print('  %-8s %4s %14s %s' % ('gain', 'n', 'median Re(Z)', 'range'))
    print('  ' + '-' * 52)
    meds = {}
    for lo, hi, nm in ((3.9, 4.1, '4.0x'), (5.9, 6.1, '6.0x'), (7.9, 8.1, '8.0x')):
        v = [r[2] for r in rows if lo <= r[0] <= hi]
        if not v:
            continue
        meds[nm] = st.median(v)
        print('  %-8s %4d %14.2f  %.1f .. %.1f' % (nm, len(v), meds[nm], max(v), min(v)))
    print('  ' + '-' * 52)
    if '4.0x' in meds and '6.0x' in meds:
        d = meds['6.0x'] - meds['4.0x']
        print('  4x -> 6x: %+.1f units per 2x = %+.1f per 1x' % (d, d / 2))
    if '6.0x' in meds and '8.0x' in meds:
        d = meds['8.0x'] - meds['6.0x']
        print('  6x -> 8x: %+.1f units per 2x = %+.1f per 1x' % (d, d / 2))

    print('\n  \U0001f6d1 THE CORPUS CANNOT SEPARATE GAIN FROM CLAMP. Both fit all 16 builds exactly.')
    print('     V256 (clamp 4096, gain held at the car\'s 6x) is the FIRST build to break the')
    print('     tracking, so it is the disambiguating experiment -- and the highest-information')
    print('     build on the shelf. See the docstring for what each outcome licenses.')


if __name__ == '__main__':
    main()
