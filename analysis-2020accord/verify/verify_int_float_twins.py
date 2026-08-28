# -*- coding: utf-8 -*-
"""VERIFY EVERY DOCUMENTED int/float TWIN PAIR ON A BUILT IMAGE.

WHY THIS EXISTS
---------------
This firmware guards several calibrations with a FLOAT MIRROR that a monitor compares against the
INT cal.  Raising one side without the other does not fail at build time and does not fail on the
bench -- it HARD-FAULTS THE ECU ON THE ROAD.

It has happened twice:
  * V21-V24 doubled the integer envelope and desynced the int-vs-float consistency monitors
    => DTC 0xF00049.
  * V73 raised the gp-0x6b26 int clamp 0xC407E 511 -> 850 and left its float twin 0xC4004 at 0.5
    (= 512).  FUN_00036d74 compares gp-0x6b26/1024 against that float and calls FUN_000462e6 on a
    range violation, so every excursion past 512 faulted => V74 and V75 both hard-faulted.

The invariant, in every family below, is Honda's own:

        float * 1024  ==  int          (the b26 ceiling ships as int+1: 0.5*1024 = 512 = 511+1)

RUN THIS ON EVERY BUILT IMAGE.  A mismatch here is a fault waiting for a road test.

USAGE:  python analysis-2020accord/verify/verify_int_float_twins.py [image.bin ...]
        with no arguments it checks every *_plain_image.bin under ACCORD_FIRMWARE_ROOT.
"""
import os, sys, glob, struct

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')

# (family, [(int_addr, float_addr, offset)])  -- offset is int - float*1024, Honda's own convention
FAMILIES = [
    ('b26 ceiling  (FUN_00036d74 monitor)', [(0xC407E, 0xC4004, -1)]),
    ('direction corridor', [(0xC674E, 0xC6598, 0), (0xC6750, 0xC659C, 0),
                            (0xC675A, 0xC65AC, 0), (0xC675C, 0xC65B0, 0)]),
    ('boost floor',        [(0xC6768, 0xC65C4, 0), (0xC676A, 0xC65C8, 0),
                            (0xC676C, 0xC65CC, 0)]),
]
TOL = 2.0


def check(path):
    b = open(path, 'rb').read()
    s16 = lambda a: struct.unpack_from('<h', b, a)[0]
    f32 = lambda a: struct.unpack_from('<f', b, a)[0]
    name = os.path.basename(path)
    bad = []
    for fam, pairs in FAMILIES:
        for ia, fa, off in pairs:
            i, f = s16(ia), f32(fa)
            if abs(f * 1024 - (i + off)) > TOL:
                bad.append((fam, ia, i, fa, f))
    if bad:
        print('  [FAIL] %s' % name)
        for fam, ia, i, fa, f in bad:
            print('         %-34s int 0x%05X = %-7d  float 0x%05X = %-10.4f (x1024 = %.0f)'
                  % (fam, ia, i, fa, f, f * 1024))
            print('         => raising one side alone is what hard-faulted V74/V75.  FIX BOTH.')
    else:
        print('  [PASS] %s  -- all %d documented twin pairs matched'
              % (name, sum(len(p) for _, p in FAMILIES)))
    return not bad


args = sys.argv[1:]
if not args:
    args = sorted(glob.glob(os.path.join(ROOT, '**', '*_plain_image.bin'), recursive=True))
    args += sorted(glob.glob(os.path.join(ROOT, '**', 'stock_fw_dump', 'code.bin'), recursive=True))
if not args:
    print('  no images found under %s' % ROOT)
    sys.exit(1)
ok = True
for p in args:
    ok &= check(p)
print('\n  %s' % ('ALL IMAGES PASS' if ok else 'AT LEAST ONE IMAGE HAS A DESYNCED TWIN -- DO NOT FLASH IT'))
sys.exit(0 if ok else 1)
