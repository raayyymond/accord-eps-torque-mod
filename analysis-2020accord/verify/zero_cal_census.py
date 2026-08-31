#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""THE CENSUS GAP: cals that are ZERO and NEVER VARIED -- invisible to every prior sweep.

WHY THIS EXISTS.  This kit censused the calibration surface twice and concluded the ratchet is not
calibration-reachable.  Both censuses had the same structural blind spot:

  * the FDR regression scored every cell that VARIED ACROSS BUILDS.  A cell that is 0 in stock and 0
    in all 161 images never varied, so no regression could assign it an effect -- it is not that it
    scored low, it is that it was never a candidate.
  * the starved-lane sweep walked every LERP.  A scalar OFF SWITCH is not a LERP.

A cal that is (a) zero and (b) actually read by an instruction is a lane that EXISTS IN SILICON and
is TURNED OFF.  Those were never priced.

METHOD, and why the naive version is wrong.  A first pass that treats every 2-byte offset as an
instruction's displacement halfword reports 13,666 "referenced" cal cells -- almost all artifact.
Real tp-relative loads are decoded here from the 4-byte Format VII encoding, derived from two
known-good sites (0x43066 -> 0xC674E, and 0x2A1F8 -> 0xC61B4):

    hw1 bits 0-4   base register   (tp = r5, gp = r4)
    hw1 bits 5-10  opcode          0x39 ld.h  0x3F ld.hu  0x3D ld.b  0x3C ld.bu  0x38 ld.w
    hw1 bits 11-15 destination
    hw2            disp16          (bit 0 is an opcode extension, not displacement)

That cuts 13,666 -> 1,567 cells with a real reader, of which 244 are zero, of which 89 have a reader
inside the torque path.

\U0001f6d1 WHAT THIS TOOL DOES NOT DO.  It finds candidates; it does not price them.  A zero cal may be
an off switch, a zeroed weight, an unused table slot, or a deadband whose zero means "no deadband"
(0xC62D0 is exactly that -- zero there is the ACTIVE setting).  Every hit needs a decompile before it
is called a lever.  Worked example in the docstring of the V112 handoff: 0xC60CC is the derivative
gain of a live PI controller, zero in every image -- a real switched-off D term, but its output
gp-0x6b78 reaches a state machine and a request struct, NOT the torque mixer, so it does not damp the
ratchet.  That is the shape of the work: the census finds it, the decompile adjudicates it.

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

import collections
import glob
import os
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMGDIR = os.path.join(FW, 'analysis-2020accord')
TP, CODE_END, CAL_LO, CAL_HI = 0xBF000, 0xC4000, 0xC4000, 0xD8000
OPC = {0x38: 'ld.w', 0x39: 'ld.h', 0x3D: 'ld.b', 0x3C: 'ld.bu', 0x3F: 'ld.hu'}

# the functions that actually reach the motor, from this kit's own record
ZONES = [(0x26000, 0x27000, '11-slot MIXER FUN_00026c80'),
         (0x28000, 0x29000, 'LKAS gain clamp FUN_00028ea6'),
         (0x2A000, 0x2C000, 'arbitration clamps FUN_0002b422'),
         (0x34300, 0x35000, 'BASE-ASSIST DAMPER FUN_00034350'),
         (0x35000, 0x36000, 'LERP FUN_000352b4'),
         (0x36000, 0x37000, 'return-centre / detent'),
         (0x38000, 0x3B000, 'aggregator + rate lanes'),
         (0x3B000, 0x3C000, 'FUN_0003bd7c'),
         (0x42000, 0x44000, 'EME shaper FUN_00042af8')]


def image(tag):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % tag))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    return open(p[0], 'rb').read() if p else None


def cal_readers(img):
    """Every cal cell with a REAL decoded tp-relative reader -> [(code_offset, form), ...]."""
    refs = collections.defaultdict(list)
    for off in range(0, CODE_END - 4, 2):
        hw1 = struct.unpack_from('<H', img, off)[0]
        if (hw1 & 0x1f) != 5:                       # base must be tp
            continue
        opc = (hw1 >> 5) & 0x3f
        if opc not in OPC:
            continue
        a = TP + (struct.unpack_from('<H', img, off + 2)[0] & 0xFFFE)
        if CAL_LO <= a < CAL_HI:
            refs[a].append((off, OPC[opc]))
    return refs


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else 'v112'
    img = image(tag)
    if img is None:
        print('  no image for tag %r' % tag)
        return
    print('=' * 78)
    print('  ZERO-VALUED CALS WITH A REAL READER   --   base image: %s' % tag)
    print('=' * 78)
    refs = cal_readers(img)
    zeros = [a for a in refs if a + 2 <= len(img) and struct.unpack_from('<h', img, a)[0] == 0]
    print('\n  %d cal cells have a real reader; %d of them are ZERO.\n' % (len(refs), len(zeros)))
    print('  %-12s %-32s %s' % ('cal', 'zone', 'reader sites'))
    print('  ' + '-' * 74)
    n = 0
    for a in sorted(zeros):
        for lo, hi, name in ZONES:
            s = [o for o, _ in refs[a] if lo <= o < hi]
            if s:
                print('  0x%08X   %-32s %s' % (a, name, ' '.join('0x%05X' % x for x in s[:5])))
                n += 1
                break
    print('  ' + '-' * 74)
    print('  %d zero cals with a reader in the TORQUE PATH.\n' % n)
    print('  \U0001f6d1 CANDIDATES, NOT LEVERS. Decompile each before calling it one: a zero can be an')
    print('     off switch, a zeroed weight, an unused slot, or a deadband whose zero is ACTIVE.')


if __name__ == '__main__':
    main()
