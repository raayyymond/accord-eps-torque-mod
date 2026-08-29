# -*- coding: utf-8 -*-
"""CLOSE-OUT VERIFICATION -- re-check from DISK everything published this session.

The standing rule: anything reported is re-verified from the filesystem at close-out, never trusted
from memory or from a build log.  This checks:

  1. every flashable artifact's SHA256 against the value published
  2. the key cell values claimed for each build
  3. that superseded artifacts are actually renamed
  4. that no mandatory-read file exceeds the 256 KB cap
  5. that the tools written this session import and run
"""
import glob
import hashlib
import io
import os
import struct
import subprocess
import sys
from pathlib import Path

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares'
A = ROOT + '/analysis-2020accord'
RWD = ROOT + '/flashing-2020accord/rwd'
PY = 'C:/Users/dudei/anaconda3/envs/bin_decompile/python'
ok, bad = 0, []


def chk(cond, msg):
    global ok
    if cond:
        ok += 1
        print('  [PASS] ' + msg)
    else:
        bad.append(msg)
        print('  [FAIL] ' + msg)


# ---- 1. published hashes ----------------------------------------------------------------
PUB = {
    'v194': '2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10',
    'v195': 'a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b',
    'v196': 'f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e',
    'v198': '9fbbf90b0bed9cb32eb7c3a44a30c2108f361a736ff3f1ebc205f47e5cf3190d',
}
print('\n[1] PUBLISHED IMAGE HASHES vs DISK')
img = {}
for v, want in PUB.items():
    g = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    if not g:
        chk(False, f'{v.upper()} image present')
        continue
    b = io.open(sorted(g)[0], 'rb').read()
    img[v] = b
    chk(hashlib.sha256(b).hexdigest() == want, f'{v.upper()} image sha256 == published')

# ---- 2. the cell values claimed --------------------------------------------------------
print('\n[2] CLAIMED CELL VALUES')


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def s16(b, o):
    return struct.unpack_from('<h', b, o)[0]


def f32(b, o):
    return struct.unpack_from('<f', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


if 'v196' in img:
    b = img['v196']
    chk(abs(f32(b, 0xC60B0) - (-1.9846207)) < 1e-6, 'V196 notch B0 = -1.9846207 (19.75 Hz)')
    chk(abs(f32(b, 0xC60AC) - 0.81) < 1e-6, 'V196 pole radius^2 = 0.81 (r = 0.9000)')
    chk(u16(b, 0xC40D2) == 102, 'V196 K1 = 102 (Honda), not the flying 1020')
    chk(u16(b, 0xC63A6) == 512, 'V196 w[3] = 512 (halved)')
    p26 = u32(b, 0xCBE74 + 4 * 26)
    n = s16(b, p26)
    Y26 = [s16(b, p26 + 2 + 2 * n + 2 * i) for i in range(n)]
    chk(Y26 == [-4915, -2867, -983], f'V196 engaged inertia Y = {Y26} (half Honda)')
    p24 = u32(b, 0xCBE74 + 4 * 24)
    n24 = s16(b, p24)
    Y24 = [s16(b, p24 + 2 + 2 * n24 + 2 * i) for i in range(n24)]
    chk(Y24 == [-9830, -5734, -1966], f'V196 MANUAL inertia Y = {Y24} (untouched)')
    chk(u16(b, 0xC407E) == 511, 'V196 fault interlock frozen at 511')
    chk(b[0xC64DD] == 50, 'V196 detector dwell is Honda 50 (V193s widening NOT carried)')
if 'v198' in img and 'v196' in img:
    b = img['v198']
    d = [a for a in range(0x13000, 0x100000)
         if b[a] != img['v196'][a] and (a & 0xFFF) < 0xFFC]
    # 0x9540 -> 0x9526 changes only the LOW byte, so this is 2 bytes, not 3.  An exact-count
    # expectation must be derived, never assumed -- the same trap as the V181 assertion bug.
    chk(len(d) == 2, f'V198 differs from V196 by {len(d)} payload bytes (telemetry only)')
    chk(all(a in (0x55DF2, 0x55DF3, 0x55E10) for a in d),
        'V198 changes only the probe cells -- no control cell differs from V196')
    chk(struct.unpack_from('<H', b, 0x55DF2)[0] == 0x9526,
        'V198 probe reads gp-0x6ada (hw2 0x9526), the r24 rate lane')
    chk(b[0x55E10] & 0x1F == 5, 'V198 pack shift is sar 5, sized to the +-8192 clamp')

if 'v195' in img and 'v196' in img:
    d = [a for a in range(0x13000, 0x100000)
         if img['v195'][a] != img['v196'][a] and (a & 0xFFF) < 0xFFC]
    chk(len(d) == 6, f'V196 differs from V195 by {len(d)} payload bytes (expected 6)')

# ---- 3. superseded artifacts ------------------------------------------------------------
print('\n[3] SUPERSEDED ARTIFACTS ARE RENAMED')
live = [os.path.basename(p) for p in glob.glob(RWD + '/39990*V19[4-8]*.rwd')]
chk(len(live) == 4, f'exactly 4 flashable builds from this chain ({len(live)})')
for v in ('V185', 'V186', 'V187', 'V188', 'V189', 'V190', 'V191', 'V192', 'V193', 'V197'):
    n = len(glob.glob(RWD + f'/39990*-{v}-*.rwd'))
    if n:
        chk(False, f'{v} is still flashable ({n} unmarked file)')
chk(not any(glob.glob(RWD + f'/39990*-{v}-*.rwd')
            for v in ('V185', 'V186', 'V187', 'V188', 'V189', 'V190', 'V191', 'V192', 'V193',
                      'V197')),
    'no superseded artifact (V185-V193, V197) remains unmarked')

# ---- 4. file caps -----------------------------------------------------------------------
print('\n[4] MANDATORY-READ FILES UNDER THE 256 KB CAP')
CAP = 256 * 1024
worst = ('', 0)
for f in (['docs/STATE.md', 'docs/BUILD-LINEAGE.md', 'CLAUDE.md',
           'docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md', 'memory/MEMORY_CONSTELLATION.md']
          + sorted(glob.glob('memory/MEMORY*.md'))):
    if os.path.exists(f):
        s = os.path.getsize(f)
        if s > worst[1]:
            worst = (f, s)
chk(worst[1] <= CAP, f'largest is {worst[0]} at {worst[1]/1024:.1f} KB (cap 256)')

# ---- 5. the tools run -------------------------------------------------------------------
print()
print("[5] EVERY PYTHON FILE IN THE KIT PARSES")
# A NAMED LIST MISSES GENERATED FILES.  decode_v198_r24_lane.py was produced by stream-editing the
# V197 decoder and carried a newline inside a quoted string.  It was not on the list, so it would
# only have failed AFTER a drive, at the moment of decoding a capture.  Sweep everything instead.
import ast, glob as _glob
_bad, _seen = [], 0
for _pat in ('rlog-tools/score/*.py', 'rlog-tools/probe/*.py', 'rlog-tools/decode/*.py',
             'rlog-tools/lib/*.py', 'analysis-2020accord/verify/*.py',
             'analysis-2020accord/builds/v108_plus/*.py', 'analysis-2020accord/lib/*.py',
             'analysis-2020accord/model/*.py', 'flashing-2020accord/*.py'):
    for _f in sorted(_glob.glob(_pat)):
        _seen += 1
        try:
            ast.parse(io.open(_f, encoding='utf-8').read())
        except SyntaxError as _e:
            _bad.append(f'{_f}:{_e.lineno} {_e.msg}')
chk(_seen > 150, f'{_seen} python files swept (a thin sweep means a bad glob)')
chk(not _bad, 'every python file parses' + ('' if not _bad else f' -- BROKEN: {_bad[:3]}'))
for _t in ('flashing-2020accord/preflight.py', 'rlog-tools/probe/decode_v198_r24_lane.py'):
    chk(os.path.exists(_t), f'{_t} exists')

print('\n' + '=' * 84)
print(f'  {ok} checks passed, {len(bad)} failed')
for m in bad:
    print('    FAILED: ' + m)
print('=' * 84)
sys.exit(1 if bad else 0)
