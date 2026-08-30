# -*- coding: utf-8 -*-
"""CAN 427 carries a DIFFERENT VARIABLE AT A DIFFERENT SCALE on nearly every build.

This exists because a table in STATE.md pooled 427 statistics across six routes under one clamp
threshold, and one of those routes was on a build whose 427 carried a different variable at a 32x
different shift.  The row was also labelled with a build that NEVER FLEW.  It was the only row in the
pool with a clamp event.  Nothing pools across 427 without checking this first.

DECODER.  The packer at 0x55DF2 is a gp-relative load; 0x55DF2/3 are the disp16 little-endian, and
0x55E10 is the `sar` whose low 5 bits are the shift.  gp = 0xFEDF8000.

    disp   = sext16(image[0x55DF2] | image[0x55DF3] << 8)
    source = gp + disp                      (reported as gp-0xNNNN)
    shift  = image[0x55E10] & 0x1F
    wire   = (|source| * 5) >> shift        -- so the LSB is 32x apart between sar 1 and sar 6

It reproduces the chain BUILD-LINEAGE states in prose, from the images, with no hand-decoding:
V87 gp-0x6b98 sar3 · V90/V91 gp-0x6b26 sar3 · V92 gp-0x6bbe sar4 · V93 gp-0x6b26 sar3 ·
V94 gp-0x6b26 sar1 · V96..V99 gp-0x6b70 sar6 -- and continues it past where the prose stops.

Run:  ACCORD_FIRMWARE_ROOT=... python analysis-2020accord/verify/can427_source_per_build.py
"""
import glob, os, sys

GP = 0xFEDF8000
OFF_SRC, OFF_SHIFT = 0x55DF2, 0x55E10
ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares') + '/analysis-2020accord'

# route -> the build that actually FLEW it.  probe_build in each cache is the ground truth.
FLEW = {'r73': 'v88', 'r7d': 'v94', 'r7e': 'v97', 'r7f': 'v97', 'r80': 'v97',
        'r81': 'v98', 'r82': 'v99', 'r95': 'v101', 'ra4': 'v104', 'r1e': 'v107',
        'r22': 'v112', 'r24': 'v122', 'r77': 'v90'}

# what BUILD-LINEAGE states in prose -- the decoder must reproduce every one of these
STATED = {'v87': (-0x6b98, 3), 'v90': (-0x6b26, 3), 'v91': (-0x6b26, 3), 'v92': (-0x6bbe, 4),
          'v93': (-0x6b26, 3), 'v94': (-0x6b26, 1), 'v96': (-0x6b70, 6), 'v97': (-0x6b70, 6),
          'v98': (-0x6b70, 6), 'v99': (-0x6b70, 6)}


def image_for(v):
    g = [p for p in glob.glob(ROOT + '/*plain_image.bin')
         if ('_%s_' % v) in os.path.basename(p).lower()
         and 'SUPERSEDED' not in os.path.basename(p)]
    return open(g[0], 'rb').read() if g else None


def decode(b):
    d = b[OFF_SRC] | (b[OFF_SRC + 1] << 8)
    if d & 0x8000:
        d -= 0x10000
    return d, b[OFF_SHIFT] & 0x1F


BUILDS = ['v87', 'v90', 'v91', 'v92', 'v93', 'v94', 'v96', 'v97', 'v98', 'v99',
          'v100', 'v101', 'v104', 'v107', 'v112', 'v122',
          'v212', 'v213', 'v215', 'v216', 'v217', 'v218', 'v219', 'v220']

print('=' * 86)
print('  CAN 427 SOURCE AND SCALE, DECODED FROM EACH IMAGE')
print('=' * 86)
print()
print('  %-6s %-14s %-6s %-9s %s' % ('build', 'source', 'shift', 'LSB rel', 'flew route(s)'))
got, missing = {}, []
for v in BUILDS:
    b = image_for(v)
    if b is None:
        missing.append(v); continue
    d, sh = decode(b)
    got[v] = (d, sh)
    routes = ' '.join(r for r, bb in sorted(FLEW.items()) if bb == v) or '--'
    print('  %-6s gp-0x%04x      sar %-2d %-9s %s' % (v, -d, sh, '%dx' % (1 << sh), routes))
if missing:
    print()
    print('  images not on disk (skipped, not failed): %s' % ' '.join(missing))

print()
print('  --- the decoder must reproduce what BUILD-LINEAGE says in prose ---')
bad = 0
for v, want in STATED.items():
    if v not in got:
        continue
    ok = got[v] == want
    bad += not ok
    print('    %-5s decoded gp-0x%04x sar %-2d  vs stated gp-0x%04x sar %-2d   %s'
          % (v, -got[v][0], got[v][1], -want[0], want[1], 'ok' if ok else 'MISMATCH'))
assert bad == 0, 'the decoder disagrees with BUILD-LINEAGE on %d build(s)' % bad

print()
print('  --- the specific defect this file exists to stop recurring ---')
v94, v96 = got.get('v94'), got.get('v96')
if v94 and v96:
    print('    r7d FLEW V94: 427 = gp-0x%04x at sar %d' % (-v94[0], v94[1]))
    print('    the table pooled it against V96-V99: 427 = gp-0x%04x at sar %d'
          % (-v96[0], v96[1]))
    print('    => different VARIABLE and a %dx different LSB. Not poolable.'
          % (1 << abs(v96[1] - v94[1])))
    assert v94[0] != v96[0], 'V94 and V96 must be shown to read different variables'
    assert abs(v96[1] - v94[1]) >= 5, 'the shift gap must be at least 32x'
assert FLEW['r7d'] == 'v94', 'r7d flew V94; V96 was BUILT, VERIFIED, UNFLASHED'

print()
print('  --- does the shelf still telemeter what the car does? ---')
car = got.get('v122')
if car:
    for v in [b for b in BUILDS if b.startswith('v2') and b in got]:
        same = got[v] == car
        print('    %-5s %s the car (gp-0x%04x sar %d)%s'
              % (v, 'MATCHES  ' if same else 'DIFFERS from',
                 -got[v][0], got[v][1], '' if same else '   <- readout is NOT comparable to r24'))

print()
print('  RULE: before pooling any 427 statistic across routes, decode this cell for every build')
print('  in the pool and drop any route whose source or shift differs. A clamp threshold, an LSB,')
print('  or a percentile computed across a mixed pool is meaningless.')
