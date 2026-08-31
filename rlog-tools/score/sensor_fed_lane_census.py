#!/usr/bin/env python3
r"""THE FIVE SENSOR-FED LANES: what is built, what has flown, what is left. A completeness check.

THE CONSTRAINT THIS RESTS ON [EVIDENCE, on-car].  During the return to centre, "for 52-70 % of the
return the LKAS lane is a DC CONSTANT, yet the 6-9 Hz |tq| envelope is unchanged (railed 121.6/378.5
vs unrailed 125.5/277.4).  A constant cannot carry 7.8 Hz => THE RINGING ENTERS THROUGH A SENSOR-FED
LANE, NOT THE COMMAND LANE."  That excludes every command-side lever and leaves exactly five:

    r24/r26 · gp-0x6ad4 · gp-0x6b26 · gp-0x6bbe · the V89 plant-model path

\U0001f6d1 AND IT IS CONSISTENT WITH THE GAIN RESULT, WHICH LOOKS LIKE A CONTRADICTION AT FIRST.  The
forward gain 0xC6CD0 is a COMMAND-side cell, yet the anti-damping tracks it (rho -0.819).  Both hold:
the gain sets how much MOTION there is for the sensor-fed lanes to respond to, without being the entry
path itself.  The constraint is about where the ringing ENTERS; the gain correlation is about how hard
it is DRIVEN.

WHY A COMPLETENESS CHECK IS THE RIGHT MOVE NOW.  Two separate blind spots have already been found in
this arc: the FDR census cannot see cells that never varied (which is where V247's lever was hiding),
and the flown corpus cannot test cells no build ever moved.  So the useful question is not "what
correlates" but "of the five lanes the on-car evidence leaves open, which have actually been addressed
by a BUILT artefact, and which are still untouched".

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
FLOWN = ['V90', 'V91', 'V94', 'V96', 'V97', 'V98', 'V99', 'V100', 'V101', 'V102',
         'V103', 'V104', 'V105', 'V106', 'V107', 'V111', 'V112', 'V122']

# lane -> (its main cal cell, what the cell is, which shelf build addresses it)
LANES = [
    ('r24/r26',            0xC6446, 'Lever B, the torque-rate lane',        'V246 (1.5x)'),
    ('gp-0x6ad4',          0xC67C4, 'resonance-PID ceiling knee',           'V245 (knee 1280->512)'),
    ('gp-0x6b26',          0xC63AE, 'inertia / restored-damper weight',     'carried at Honda 1024'),
    ('gp-0x6bbe',          0xC63A2, 'viscous lane weight -- SINGLE READER',  '(none built)'),
    ('plant model',        0xC40D2, 'Coulomb slope k1',                     'V222 restored to 1020'),
]


def image(b):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % b.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    p = p or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % b.lower()))
    if not p:
        return None
    im = open(p[0], 'rb').read()
    return im if struct.unpack_from('<H', im, 0xC646C)[0] == 891 else None


def main():
    print('=' * 92)
    print('  THE FIVE SENSOR-FED LANES -- the on-car evidence leaves the ringing inside this set')
    print('=' * 92)

    flown_imgs = {b: image(b) for b in FLOWN}
    flown_imgs = {b: im for b, im in flown_imgs.items() if im is not None}
    shelf = {}
    for tag in ('v241', 'v245', 'v246', 'v247', 'v248'):
        im = image(tag)
        if im is not None:
            shelf[tag.upper()] = im
    car = flown_imgs.get('V122')

    print('\n  %-12s %-9s %-34s %-11s %s'
          % ('lane', 'cell', 'what it is', 'on the car', 'varied in flight?'))
    print('  ' + '-' * 88)
    untouched = []
    for name, addr, what, build in LANES:
        vals = {struct.unpack_from('<H', im, addr)[0] for im in flown_imgs.values()}
        varied = len(vals) > 1
        cur = struct.unpack_from('<H', car, addr)[0] if car else None
        print('  %-12s 0x%05X  %-34s %-11s %s'
              % (name, addr, what, str(cur),
                 'YES (%d values)' % len(vals) if varied else 'NEVER -- census blind'))
        if not varied:
            untouched.append((name, addr, what, build))
    print('  ' + '-' * 88)

    print('\n  WHICH ARE ADDRESSED BY A BUILT ARTEFACT?')
    print('  %-12s %-9s %s' % ('lane', 'cell', 'shelf build'))
    print('  ' + '-' * 66)
    for name, addr, what, build in LANES:
        moved = []
        for tag, im in sorted(shelf.items()):
            if car is None:
                continue
            if struct.unpack_from('<H', im, addr)[0] != struct.unpack_from('<H', car, addr)[0]:
                moved.append(tag)
        print('  %-12s 0x%05X  %s' % (name, addr, ', '.join(moved) if moved else build))
    print('  ' + '-' * 66)

    print('\n  \U0001f6d1 STILL UNADDRESSED BY ANY SHELF BUILD:')
    gap = []
    for name, addr, what, build in LANES:
        moved = any(car is not None and
                    struct.unpack_from('<H', im, addr)[0] != struct.unpack_from('<H', car, addr)[0]
                    for im in shelf.values())
        if not moved:
            gap.append((name, addr, what, build))
    if not gap:
        print('     none -- every one of the five has a built artefact against it.')
    else:
        for name, addr, what, build in gap:
            v = struct.unpack_from('<H', car, addr)[0] if car else None
            print('     %-12s 0x%05X = %-6s  %s' % (name, addr, v, what))
            print('     %-12s %s' % ('', 'record status: ' + build))
    print('\n  NOTE: the base-assist damper (gp-0x6bd0) is NOT in this set -- it is not sensor-fed in')
    print('  the sense meant here, it is the lane that OPPOSES the motion. V247/V248 act there.')
    print('\n  \U0001f6d1 "never varied in flight" means the correlation census could not test it, NOT')
    print('     that it is inert. That distinction is where V247 came from.')


if __name__ == '__main__':
    main()
