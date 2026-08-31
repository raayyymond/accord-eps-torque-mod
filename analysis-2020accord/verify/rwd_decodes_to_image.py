#!/usr/bin/env python3
r"""INDEPENDENT CHECK: does each .rwd on disk decode to exactly the image it claims?

The builders already assert this at build time, and `rebuild_shelf_bitexact.py` re-runs them.  This
asks the same question from the OTHER end -- from the flashable artifact backwards -- so a file that
was corrupted, truncated or replaced after its build would be caught.  Flown builds are included as
controls: if they fail, the CHECK is broken, not the shelf.

\U0001f6d1 TWO TRAPS, BOTH HIT WHILE WRITING THIS.

1. `crack_cipher()` is for ORIGINAL HONDA `.rwd` files, where the table is unknown and must be
   recovered from a known plaintext (the part number).  **The kit's own builds are encoded with a
   KNOWN table** -- `build_decode_table(FF.V9B["keys"], FF.V9B["ops"])`, which is what every builder
   uses.  Calling `crack_cipher` on them fails, and it fails on the FLOWN builds too.

2. `roundtrip()` derives the expected part number from the filename with
   `39990[-]?(...)[-_]?(...)`, but the kit's filenames use a **COMMA** -- `39990-TVA,A160`.  The regex
   misses, `expected` becomes None, and the crack cannot be confirmed.

Together those produced a "DO NOT FLASH" on three builds that are fine.  **The control is what caught
it: V122 -- the build on the car -- failed identically.**  A check that condemns the firmware currently
running the vehicle is a broken check, not a discovery.

`parse_x31` returns `blocks` as a list of dicts (`{'start', 'length'}`), not tuples.

Usage:  python analysis-2020accord/verify/rwd_decodes_to_image.py
"""
import glob
import os
import sys

for _p in ('analysis-2020accord/lib', 'analysis-2020accord/builds'):
    sys.path.insert(0, os.path.abspath(_p))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from encode_eps import parse_x31, build_decode_table          # noqa: E402
import build_vfourframe_tva as FF                             # noqa: E402

FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    'C:/Users/dudei/Desktop/Projects/accord-firmwares')
RWD = os.path.join(FW, 'flashing-2020accord', 'rwd')
IMG = os.path.join(FW, 'analysis-2020accord')
# flown builds FIRST -- they are the control. If they fail, the check is broken.
BUILDS = ('V122', 'V88', 'V108', 'V241', 'V242', 'V243',
          'V245', 'V246', 'V247', 'V248', 'V249', 'V250')
FLOWN = {'V122', 'V88', 'V108'}


def main():
    dec = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    assert dec is not None, 'the kit decode table did not build'
    print('=' * 72)
    print('  DOES EACH .rwd DECODE TO EXACTLY ITS IMAGE?   (flown builds are the control)')
    print('=' * 72)
    print('  %-6s %-8s %9s %11s  %s' % ('build', 'status', 'start', 'bytes', 'payload vs image'))
    print('  ' + '-' * 62)
    bad_flown = bad_new = seen = 0
    for v in BUILDS:
        rg = [p for p in glob.glob(os.path.join(RWD, '39990*.rwd'))
              if '-%s-' % v in p and 'SUPERSEDED' not in p and 'RATCHET-COST' not in p]
        ig = [p for p in glob.glob(os.path.join(IMG, '*plain_image.bin'))
              if '_%s_' % v.lower() in p and 'SUPERSEDED' not in p]
        if not rg or not ig:
            continue
        seen += 1
        info = parse_x31(open(rg[0], 'rb').read())
        img = open(ig[0], 'rb').read()
        bad = tot = 0
        for blk, enc in zip(info['blocks'], info['encs']):
            plain = enc.translate(dec)
            tot += len(plain)
            seg = img[blk['start']:blk['start'] + len(plain)]
            bad += sum(1 for a, b in zip(plain, seg) if a != b)
        print('  %-6s %-8s   0x%05X %11d  %s'
              % (v, 'flown' if v in FLOWN else 'shelf', info['blocks'][0]['start'], tot,
                 'IDENTICAL' if bad == 0 else '*** %d bytes differ ***' % bad))
        if bad:
            if v in FLOWN:
                bad_flown += 1
            else:
                bad_new += 1
    print('  ' + '-' * 62)
    if bad_flown:
        print('  \U0001f6d1 A FLOWN BUILD FAILED -- the CHECK is broken, not the shelf. Do not report')
        print('     this as a firmware defect until the control passes.')
    elif bad_new:
        print('  \U0001f6d1 %d shelf build(s) do not match their image -- investigate BEFORE flashing.'
              % bad_new)
    else:
        print('  [OK] all %d decode to exactly their images, controls included.' % seen)
    assert not bad_flown and not bad_new, 'rwd/image mismatch'


if __name__ == '__main__':
    main()
