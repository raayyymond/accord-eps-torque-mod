#!/usr/bin/env python3
r"""IS THIS .rwd ACTUALLY FLASHABLE?  The procedural gate, checked from the artifact backwards.

The builders assert correctness at BUILD time and `rwd_decodes_to_image.py` checks the payload
round-trips.  This asks the remaining question: would the flasher accept the file, and is it for THIS
car?  A build can be arithmetically perfect and still be unflashable -- wrong part number, wrong start
address, a truncated block table, a CRC the bootloader will reject.

\U0001f6d1 EVERY CHECK HERE RUNS AGAINST FLOWN BUILDS AS CONTROLS.  A check that fails on V122 -- which
is on the car and flashed successfully -- is a BROKEN CHECK, not a broken firmware.  That exact trap
has already cost this kit a false "DO NOT FLASH" once: `crack_cipher` failed on all three shelf builds
AND on V122, and only the control revealed it was the tool.

WHAT IS AND IS NOT COVERED.  This checks the ARTIFACT.  It cannot tell you the ECU will accept the
session, that the bus is right, or that openpilot is stopped -- those are the operator's gates and the
kit's safety rules cover them.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_d = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_d, ".pkgroot")):
    _n = _os.path.dirname(_d)
    if _n == _d:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _d = _n
# 🛑 builds/ is NESTED (builds/telemetry/, builds/v108_plus/, ...), so a flat list of
# top-level subdirs does not find build_vfourframe_tva. Walk one level down as well.
_p = [_d] + [_os.path.join(_d, s) for s in ("builds", "lib", "model", "verify", "extract")]
for _sub in ("builds",):
    _b = _os.path.join(_d, _sub)
    if _os.path.isdir(_b):
        _p += [_os.path.join(_b, x) for x in _os.listdir(_b)
               if _os.path.isdir(_os.path.join(_b, x))]
_sys.path[:0] = _p
for _v in ("_d", "_n", "_v", "_p", "_b", "_sub", "_os", "_sys"):
    globals().pop(_v, None)

import glob
import os
import re
import struct
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import build_vfourframe_tva as FF                             # noqa: E402
from encode_eps import parse_x31, build_decode_table          # noqa: E402

FW = os.environ.get('ACCORD_FIRMWARE_ROOT', r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
RWD = os.path.join(FW, 'flashing-2020accord', 'rwd')
PART = '39990-TVA,A160'
EXPECT_START = 0x13000
EXPECT_LEN = 970752
FLOWN = ('V122', 'V88', 'V108')
SHELF = ('V241', 'V245', 'V246', 'V247', 'V248', 'V249', 'V250', 'V251', 'V252', 'V253')


def find(tag):
    hits = [p for p in glob.glob(os.path.join(RWD, '*.rwd'))
            if re.search(r'-%s-' % tag, os.path.basename(p))
            and 'DO-NOT-FLASH' not in os.path.basename(p)]
    return hits[0] if hits else None


def checks(path):
    """Return a list of (name, ok, detail).

    \U0001f6d1 `parse_x31` returns a DICT {'blocks': [{'start':...}], 'encs': [bytes]} -- NOT a list
    of blocks. Treating it as a list is what made the first version of this file fail on all three
    FLOWN controls, which is precisely what the controls are for.
    """
    name = os.path.basename(path)
    out = [('part number', name.startswith(PART), name.split('-0x')[0][:56])]
    raw = open(path, 'rb').read()
    out.append(('non-empty', len(raw) > 1000, '%d bytes' % len(raw)))
    try:
        info = parse_x31(raw)
        # 🛑 build_decode_table takes (keys, ops) from the KNOWN V9B table -- not the raw
        # file. Calling it with the file is what broke the first version of this check.
        dec = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    except Exception as e:
        out.append(('parses as x31', False, str(e)[:44]))
        return out
    blocks, encs = info['blocks'], info['encs']
    out.append(('parses as x31', True, '%d block(s)' % len(blocks)))
    total = sum(len(e.translate(dec)) for e in encs)
    out.append(('payload length', total == EXPECT_LEN, '%d (want %d)' % (total, EXPECT_LEN)))
    start = blocks[0]['start']
    out.append(('start address', start == EXPECT_START,
                '0x%X (want 0x%X)' % (start, EXPECT_START)))
    # blocks must be contiguous and ascending -- a gap or overlap would flash garbage
    ok, detail = True, 'contiguous'
    cur = start
    for blk, enc in zip(blocks, encs):
        if blk['start'] != cur:
            ok, detail = False, 'gap/overlap at 0x%X (expected 0x%X)' % (blk['start'], cur)
            break
        cur += len(enc.translate(dec))
    out.append(('block layout', ok, detail))
    return out


def main():
    print('=' * 84)
    print('  FLASH READINESS -- checked from the artifact backwards, flown builds as controls')
    print('=' * 84)
    print()
    allrows = []
    for tag in FLOWN + SHELF:
        p = find(tag)
        status = 'FLOWN' if tag in FLOWN else 'shelf'
        if not p:
            print('  %-6s %-6s  NO .rwd FOUND' % (tag, status))
            continue
        res = checks(p)
        bad = [c for c in res if not c[1]]
        mark = 'OK' if not bad else 'FAIL: ' + ', '.join(c[0] for c in bad)
        print('  %-6s %-6s  %-44s %s'
              % (tag, status, os.path.basename(p)[:44], mark))
        allrows.append((tag, status, bad))
    print()
    ctl_bad = [t for t, s, b in allrows if s == 'FLOWN' and b]
    shelf_bad = [t for t, s, b in allrows if s == 'shelf' and b]
    if ctl_bad:
        print('  \U0001f6d1 A FLOWN BUILD FAILED (%s). THE CHECK IS BROKEN, NOT THE FIRMWARE.'
              % ', '.join(ctl_bad))
        print('     Do not act on any shelf verdict from this run.')
    elif shelf_bad:
        print('  \U0001f6d1 SHELF BUILDS FAILING with all controls passing: %s' % ', '.join(shelf_bad))
        print('     Controls passed, so these are real. Do not flash them.')
    else:
        print('  [OK] every artifact passes, and all %d flown controls pass too -- so the checks'
              % len(FLOWN))
        print('       can still discriminate. The shelf is procedurally flashable.')
    print('\n  \U0001f6d1 THIS CHECKS THE ARTIFACT ONLY. It says nothing about the bus, the ECU')
    print('     session, or whether openpilot is stopped -- those remain the operator gates:')
    print('       - openpilot/pandad killed  ->  tmux kill-server')
    print('       - the exact file and bus named by the operator, repeated back before proceeding')


if __name__ == '__main__':
    main()
