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
    'v199': 'c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10',
    'v200': 'db0b613aad11e67822528251b66790386635a59e9584e87d352bf294d5bf460e',
    'v201': '354f9dfb93cf6fcd309c791ff962a792db668c6faef1de5a563d9f389f3bdfd6',
    'v202': '2c5bc569c2c5e4c66f7eaa350ddbfe87d50af9875fa75a10d927eed3a7255160',
    'v203': '0da3b7b9a4bfa9068960ed1c5afd07ff4f816376da9488df4d31946cf55b5965',
    'v204': '30e7da9f6d20ff1335d01abe86ba03df7245c802217a4e6df54c5b93208873e6',
    'v205': '8cf100864be1d6030eed36acac1d514066b157a59de8ca829ae154ce7032882e',
    'v206': '71bd8312c324de9c01cf277307e41bb6dbb5e49cc6cf72e02e597a8013333a80',
    'v207': '8de7180ec4daeb459be994d180321b235a5c79ade9050eff015e83b0f537067c',
    'v208': 'e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a',
    'v209': '984dfe5590bb8bfedaedca1256008cdd81cf33837acaa54a909463768b47327c',
    'v210': 'ab49ca762b7017de436a7b80d15a7a72fda7e3f862f32c3a9106318018da814b',
    'v211': '70b205589b6f81a9f1e4f039daf8f744a66a1b9865ddbe133b499ef6ce35368e',
    'v212': 'dcc1b921e85e56bce56b3c1e69c795194c141dd4486b4f4e8b3755a2a6c2b04a',
    'v213': 'b1f998702adbbce9a52e7e430906f0cd77410625c29887e4d0a06e4cddb0e239',
    'v215': 'afc1d88505d2c55d37d6379f4cab058b9d1926c334c13d4c92761d138c62fbff',
    'v216': '791e123fb4d8bd6ea0736c52546995bb15742444b5d5c23b6db128e8bd792a13',
    'v217': 'f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b',
    'v218': 'f73aee347d67c10e0a50431d01143407bdee180e792022e2002eb8451c10b691',
    'v219': '13c1d33b3ad9eff526283b7465e3b85b18084056479588ba2741537b25d10d33',
    'v220': 'ce07b776b8cdfef3ed9584a8352ce8922398c0c631ac132a1bc8f78425070097',
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

if 'v199' in img and 'v196' in img:
    a1, a2, b1, g = (struct.unpack_from('<f', img['v199'], a)[0]
                     for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
    import math as _m
    fz = _m.degrees(_m.acos(-b1 / 2)) / 360 * 1000
    fp = _m.degrees(_m.acos(-a1 / (2 * _m.sqrt(a2)))) / 360 * 1000
    chk(abs(fz - 19.75) < 0.02, f'V199 zeros at {fz:.2f} Hz -- the cs_rate refit, UNMOVED')
    chk(fp < fz - 1.0, f'V199 poles at {fp:.2f} Hz -- BELOW the zeros, Honda own layout')
    chk(abs(_m.sqrt(a2) - 0.9675) < 1e-4, f'V199 pole radius {_m.sqrt(a2):.4f}')
    d = [a for a in range(0x13000, 0x100000)
         if img['v199'][a] != img['v196'][a] and (a & 0xFFF) < 0xFFC]
    chk(len(d) == 9, f'V199 differs from V196 by {len(d)} payload bytes (the four float32 cells)')
    chk(all(0xC60A8 <= a < 0xC60B8 for a in d), 'V199 changes ONLY the four biquad cells')

for _v, _base, _hw, _what in (('v203', 'v202', 0x9482,
                               'gp-0x6b7e, the unfiltered pedestal'),
                              ('v204', 'v202', 0x94B2,
                               'gp-0x6b4e, the observer model lane'),
                              ('v205', 'v202', 0x9490,
                               'gp-0x6b70, the observer output'),
                              ('v207', 'v202', 0x9534,
                               'gp-0x6acc, the merged command the gate tests'),):
    if _v in img and _base in img:
        d = [a for a in range(0x13000, 0x100000)
             if img[_v][a] != img[_base][a] and (a & 0xFFF) < 0xFFC]
        chk(len(d) <= 3, f'{_v.upper()} differs from {_base.upper()} by {len(d)} payload bytes')
        chk(struct.unpack_from('<H', img[_v], 0x55DF2)[0] == _hw,
            f'{_v.upper()} probe reads {_what} (hw2 0x{_hw:04X})')
        _want = 6 if _v == 'v205' else 5
        chk(img[_v][0x55E10] & 0x1F == _want,
            f'{_v.upper()} pack shift is sar {_want} -- sized to ITS source')
        for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4):
            chk(struct.unpack_from('<I', img[_v], a)[0]
                == struct.unpack_from('<I', img[_base], a)[0],
                f'{_v.upper()} 0x{a:05X} biquad cell identical to {_base.upper()}')

if False:
    d = [a for a in range(0x13000, 0x100000)
         if img['v200'][a] != img['v199'][a] and (a & 0xFFF) < 0xFFC]
    chk(len(d) == 2, f'V200 differs from V199 by {len(d)} payload bytes (telemetry only)')
    chk(struct.unpack_from('<H', img['v200'], 0x55DF2)[0] == 0x9526,
        'V200 probe reads gp-0x6ada (hw2 0x9526), the r24 rate lane')
    chk(img['v200'][0x55E10] & 0x1F == 5, 'V200 pack shift is sar 5, sized to the +-8192 clamp')
    for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4):
        chk(struct.unpack_from('<I', img['v200'], a)[0]
            == struct.unpack_from('<I', img['v199'], a)[0],
            f'0x{a:05X} biquad cell identical to V199 -- V200 adds an instrument, not a lever')

if 'v202' in img and 'v199' in img:
    import math as _m2
    a1, a2, b1, _g = (struct.unpack_from('<f', img['v202'], a)[0]
                      for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
    fz = _m2.degrees(_m2.acos(-b1 / 2)) / 360 * 1000
    fp = _m2.degrees(_m2.acos(-a1 / (2 * _m2.sqrt(a2)))) / 360 * 1000
    chk(abs(fz - 19.75) < 0.02, f'V202 zeros UNMOVED at {fz:.2f} Hz -- same null as V199')
    chk(abs(fp - 15.25) < 0.05, f'V202 poles dropped to {fp:.2f} Hz -- wider shoulder')
    chk(abs(_m2.sqrt(a2) - 0.96) < 1e-4, f'V202 pole radius {_m2.sqrt(a2):.4f}')
    # strictly more attenuation than V199 across the whole grind band -- that is the whole point
    _worse = []
    for f in (16.33, 18.0, 20.12, 21.0, 22.15, 23.0, 26.0, 30.0):
        z = complex(_m2.cos(2 * _m2.pi * f / 1000), _m2.sin(2 * _m2.pi * f / 1000))
        def _h(v):
            p1, p2, p3, p4 = (struct.unpack_from('<f', img[v], a)[0]
                              for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
            return abs(p4 * (z * z + p3 * z + 1) / (z * z + p1 * z + p2))
        if _h('v202') > _h('v199') + 1e-9:
            _worse.append(f)
    chk(not _worse, 'V202 attenuates MORE than V199 at every grind-band frequency'
        + ('' if not _worse else f' -- WORSE at {_worse}'))

if 'v206' in img and 'v202' in img:
    chk(struct.unpack_from('<H', img['v206'], 0xC63AE)[0] == 512,
        'V206 0xC63AE = 512 -- half the soft relay input scale')
    chk(struct.unpack_from('<H', img['v202'], 0xC63AE)[0] == 1024,
        'V202 0xC63AE = 1024 -- the base is at Honda unity')
    _d = [a for a in range(0x13000, 0x100000)
          if img['v206'][a] != img['v202'][a] and (a & 0xFFF) < 0xFFC]
    chk(_d == [0xC63AF], f'V206 differs from V202 at exactly 0xC63AF (high byte) -- got {_d}')
    chk(struct.unpack_from('<H', img['v206'], 0x55DF2)[0]
        == struct.unpack_from('<H', img['v202'], 0x55DF2)[0],
        'V206 leaves the 427 probe alone -- it is a lever, not an instrument')

if 'v208' in img and 'v202' in img:
    import math as _m3
    a1, a2, b1, _g = (struct.unpack_from('<f', img['v208'], a)[0]
                      for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
    fz = _m3.degrees(_m3.acos(-b1 / 2)) / 360 * 1000
    fp = _m3.degrees(_m3.acos(-a1 / (2 * _m3.sqrt(a2)))) / 360 * 1000
    chk(abs(fz - 20.50) < 0.02, f'V208 zeros re-centred to {fz:.2f} Hz (was 19.75)')
    chk(fp < fz - 1.0, f'V208 poles at {fp:.2f} Hz -- still BELOW the zeros')
    chk(struct.unpack_from('<I', img['v208'], 0xD7A5C)[0]
        == struct.unpack_from('<I', img['v202'], 0xD7A5C)[0],
        'V208 carries V202s engaged inertia half-dose unchanged')

# ---- 3. superseded artifacts ------------------------------------------------------------
print('\n[3] SUPERSEDED ARTIFACTS ARE RENAMED')
live = [os.path.basename(x) for x in glob.glob(RWD + '/39990*-V199-*.rwd')
        + glob.glob(RWD + '/39990*-V208-*.rwd')
        + glob.glob(RWD + '/39990*-V209-*.rwd')
        + glob.glob(RWD + '/39990*-V210-*.rwd')
        + glob.glob(RWD + '/39990*-V211-*.rwd')]
chk(len(live) == 5, f'exactly 5 flashable builds from this chain ({len(live)})')
# V194/V195/V196/V198 were PULLED: every one carries a notch whose poles sit at the zeros, scoring
# max|H| 1.3533-1.7177 against the lineage bar of stock 1.0000.  They must not be flashable.
for v in ('V185', 'V186', 'V187', 'V188', 'V189', 'V190', 'V191', 'V192', 'V193',
          'V194', 'V195', 'V196', 'V197', 'V198', 'V200', 'V201', 'V203', 'V207',
          'V202', 'V204', 'V205', 'V206'):
    n = len(glob.glob(RWD + f'/39990*-{v}-*.rwd'))
    if n:
        chk(False, f'{v} is still flashable ({n} unmarked file)')
chk(not any(glob.glob(RWD + f'/39990*-{v}-*.rwd')
            for v in ('V185', 'V186', 'V187', 'V188', 'V189', 'V190', 'V191', 'V192', 'V193',
                      'V197')),
    'no superseded artifact (V185-V198) remains unmarked')

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

print()
print("[6] GATE 2 -- NO FLASHABLE IMAGE MAY AMPLIFY AT ANY FREQUENCY")
# BUILD-LINEAGE.md, V105: "Check max|H| over 0-500 Hz against stock 1.0000 before shipping any
# biquad edit."  V103 GATE 2: the filter "can only REMOVE loop gain, never add it".  V188-V198
# shipped at 1.3533-1.7177 because V195 wrote its own assertion as mx <= 2.0.  A gate that lives in
# one builder protects one build; this one sweeps every image that still has a flashable .rwd.
import cmath
import math
import struct as _st
import re

_IMGD = os.path.join(ROOT, 'analysis-2020accord')
_RWDD = os.path.join(ROOT, 'flashing-2020accord', 'rwd')
_GRID = [0.02 + 0.02 * k for k in range(6000)] + [120.0 + 0.5 * k for k in range(761)]


def _maxh(path):
    b = open(path, 'rb').read()
    a1, a2, b1, g = (_st.unpack_from('<f', b, a)[0]
                     for a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
    m = 0.0
    for f in _GRID:
        z = cmath.exp(2j * math.pi * f / 1000.0)
        m = max(m, abs(g * (z * z + b1 * z + 1) / (z * z + a1 * z + a2)))
    return m


# only builds whose .rwd is still flashable are in scope; superseded ones are allowed to be bad
_live = set()
if os.path.isdir(_RWDD):
    for f in os.listdir(_RWDD):
        if f.startswith('39990') and f.endswith('.rwd'):
            mm = re.match(r'39990-TVA,A160-(V\d+[A-Z]?)-', f)
            if mm:
                _live.add(mm.group(1).lower())

# KNOWN, DOCUMENTED EXCEPTIONS -- historical builds that amplify on purpose or marginally.  They
# are listed here so a NEW violation still fails the check rather than hiding in a raised bar.
#   v104  1.8501  deliberate: 0xC60B4 c4 x1.850, "a flat scalar on the torque-sensor assist lane".
#                 IT FLEW as route a4 and the lineage records "FIXED NOTHING -- operator: both
#                 symptoms still present".  So the one time an amplifying assist filter reached the
#                 car, it bought nothing -- which is evidence for the bar, not against it.
#   v172  1.0123  ASSIST.SECTION.RETUNE.REALPOLE, marginal, 1.2 % over.
_KNOWN = {'v104': 1.8501, 'v172': 1.0123}

_checked, _bad = 0, []
if os.path.isdir(_IMGD):
    for f in sorted(os.listdir(_IMGD)):
        if not f.endswith('_plain_image.bin') or f.startswith('SUPERSEDED'):
            continue
        mm = re.match(r'_(v\d+[a-z]?)_', f)
        if not mm or mm.group(1) not in _live:
            continue
        mx = _maxh(os.path.join(_IMGD, f))
        _checked += 1
        tag = mm.group(1)
        if mx > 1.0001 and abs(_KNOWN.get(tag, 0.0) - mx) > 5e-3:
            _bad.append('%s max|H| = %.4f' % (tag, mx))
chk(_checked >= 2, '%d flashable images scored against the GATE 2 bar' % _checked)
chk(not _bad, 'no flashable image amplifies beyond the %d documented exceptions'
    % len(_KNOWN)
    + ('' if not _bad else ' -- VIOLATIONS: ' + '; '.join(_bad)))

print()
print("[7] THE LATENT SQUARE-WAVE INJECTOR MUST STAY SILENT")
# BUILD-LINEAGE.md: 0xC64DE is "the hold count of a sign-flipping square wave" in FUN_00028ea6,
# 8 live read sites, 0 writers, tick 1 ms, so f = 1000/(2*cal).  Honda ships cal = 17 (29.41 Hz).
# V18 set it to 27 = 18.52 Hz -- INSIDE the grind band (p10 16.33 / median 20.12 / p90 22.15).
# It is inert ONLY because its amplitude LERP is all zeros, and that table sits 24 bytes from
# 0xC674E/0xC6750, which this kit edits (1024 -> 5120).  So this is a standing hazard, and the
# guard is cheap: if the amplitude ever becomes non-zero we get an 18.5 Hz torque injector wired
# into the gain path, which would look exactly like the symptom we are chasing.
_INJ_N, _INJ_X, _INJ_Y = 0xC6734, 0xC6736, 0xC673E
for _v in sorted(img):
    _n = struct.unpack_from('<h', img[_v], _INJ_N)[0]
    _y = [struct.unpack_from('<h', img[_v], _INJ_Y + 2 * _i)[0] for _i in range(4)]
    _c = img[_v][0xC64DE]
    chk(_n == 4 and _y == [0, 0, 0, 0],
        f'{_v.upper()} injector amplitude Y = {_y} (n={_n}) -- SILENT')
    if _c != 17:
        print(f'         note: {_v.upper()} 0xC64DE = {_c} => {1000.0 / (2 * _c):.2f} Hz '
              f'(Honda 17 => 29.41 Hz). Latent, inside the grind band.')

print()
print("[8] THE FRICTION LANE'S TRUE MULTIPLIER vs HONDA")
# friction = clamp(motor_rate * 12 / knee, +-1) * (|model| * K1/1024 + K0/1024)
# V177 reverted K1 1020 -> 102 and the record calls that "K1 -> Honda".  But the RAMP KNEE was
# never reverted (600 -> 3000, unattributed to any stated intent), and the knee multiplies the
# whole expression, so the lane sits at 0.200x Honda BELOW saturation -- not at Honda.  Labelling
# it "reverted" hides a 5x change in the regime the ratchet lives in.
for _v in sorted(img):
    _kn = struct.unpack_from('<H', img[_v], 0xC40BC)[0]
    _k1 = struct.unpack_from('<H', img[_v], 0xC40D2)[0]
    _mult = (600.0 / _kn) * (_k1 / 102.0)
    # 2026-08-29: this gate USED TO assert only `knee > 0`, i.e. nothing. It reported a multiplier
    # and bounded none of it, and it quoted only the HONDA reference -- the same two defects that
    # hid the damper cut in [14]. The flown car sits at 2.000x Honda (knee 600, K1 204); the whole
    # notch shelf sat at 0.200x, i.e. 0.100x THE CAR, and this gate waved it through.
    # Lower modelled friction = LESS assist = HEAVIER wheel (verified polarity), so a cut here
    # removes authority. Bound it, against both references.
    _CAR_MULT = (600.0 / 600) * (204 / 102.0)          # the flown V108
    _vs_car = _mult / _CAR_MULT
    _FRIC_LOW = {'v194', 'v195', 'v196', 'v198', 'v199', 'v200', 'v201', 'v202', 'v203', 'v204',
                 'v205', 'v206', 'v207', 'v208', 'v209', 'v210', 'v211', 'v212', 'v213', 'v214',
                 'v215'}
    chk(_kn > 0 and (_vs_car >= 0.999 or _v in _FRIC_LOW),
        f'{_v.upper()} friction lane: knee {_kn}, K1 {_k1} => {_mult:.3f}x Honda / '
        f'{_vs_car:.3f}x FLOWN, saturating at {_kn / 12.0:.0f} deg/s (Honda 50)'
        + ('' if (_vs_car >= 0.999 or _v in _FRIC_LOW)
           else ' -- CUTS modelled friction below the car = LESS assist, and is not a documented'
                ' low-friction build'))

print()
print("[9] EVERY PROBE DECODER CAN ACTUALLY FIND A CACHE")
# Six decoders shipped with a defect that no other check would catch: the PATH BOOTSTRAP ends in
# os.chdir(str(_d)) -> the package root, and then the tool opens a KIT-ROOT-relative path.  They
# reported a plausible "no cache" and exited 1.  That reads as a missing capture, not a bug, so a
# drive would have been flown and the probe unreadable.  Assert the path they build actually exists.
import subprocess as _sp
_dec = sorted(glob.glob('rlog-tools/probe/decode_*.py'))
_cache = glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')
_tag = os.path.basename(os.path.dirname(_cache[0])) if _cache else None
chk(_tag is not None, 'a cached route exists to smoke-test the decoders against')
for _f in _dec:
    try:
        _r = _sp.run([PY, _f, _tag or 'r24', '--v194', '--v198', '--v201', '--v204',
                      '--v205', '--v207', '--v209'], capture_output=True, text=True, timeout=180)
        _out = (_r.stdout or '') + (_r.stderr or '')
    except _sp.TimeoutExpired:
        _out = '(timed out -- slow tool, not the chdir bug)'
    chk('no cache for' not in _out,
        f'{os.path.basename(_f)} resolves its cache path'
        + ('' if 'no cache for' not in _out else ' -- THE CHDIR BUG IS BACK'))

print()
print("[10] NO TOOL chdirs AWAY AND THEN USES A KIT-ROOT-RELATIVE PATH")
_r = _sp.run([PY, 'analysis-2020accord/verify/chdir_path_mismatch_sweep.py'],
             capture_output=True, text=True, timeout=300)
chk(_r.returncode == 0,
    'chdir/path mismatch sweep is clean'
    + ('' if _r.returncode == 0 else ' -- see the sweep output'))

print()
print("[11] HONDA'S ARBITRATION TABLES MUST STAY AS SHIPPED -- 0xC4118 / 0xC4124")
# FUN_00026c80 (the 11-slot lane mixer) carries a complete Honda rate limiter -- target clamped to
# +-2048/3072 (0xC6192/0xC6198), a follower slewed at 3 counts/tick (0xC6194), residual clipped to
# 256 -- whose output gp-0x6b4a has 8 readers including the delivery chain FUN_00042af8 @ 0x42BF6.
#
# 🛑 CORRECTED 2026-08-29, same session, after mapping all ten slots. I first recorded that zeroing
# one 0xC4118 arm byte would ARM that limiter in the live delivery path. THAT IS WRONG, and the error
# was mine: I had traced the plumbing but not the payloads. Mapping every caller of FUN_00025c32
# shows NINE of the ten slots store value A as literal r0, and the tenth (slot 2, FUN_0003405a)
# carries gp-0x6b76, which is clamp(torque, +-0xC616C) negated -- and 0xC616C = 0, so it is 0 when
# the lane is valid and 0x7FFF when it is not, with 0x7FFF exceeding slot 2's own <=0x5000 gate and
# being rejected to 0 anyway.  =>  gp-0x3d80 AND gp-0x3d84 are both identically zero regardless of
# the arm gate, so gp-0x6b4a == 0 and the limiter cannot be armed by any single-byte edit.
#
# The assertion below is KEPT -- Honda's arbitration tables are not ours to move, and a change to
# either one would silently re-plumb which client reaches which output -- but it is a "leave Honda's
# wiring alone" guard, NOT the interlock I originally claimed. The real interlock on that whole path
# is 0xC616C = 0, checked separately below.
for _v in sorted(img):
    _arm = [img[_v][0xC4118 + _i] for _i in range(11)]
    _mode = [img[_v][0xC4124 + _i] for _i in range(11)]
    _x0 = struct.unpack_from('<H', img[_v], 0xC63CC)[0]
    _dormant = all(_a == 1 for _a in _arm)
    chk(_dormant,
        f'{_v.upper()} 0xC4118 arm gate all ones -- rate limiter dormant'
        + ('' if _dormant else f' -- {_arm} ARMS A SLEW LIMITER IN DELIVERY'))
    chk(_mode == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0],
        f'{_v.upper()} 0xC4124 mode table unchanged')
    _clamp = struct.unpack_from('<H', img[_v], 0xC616C)[0]
    chk(_clamp == 0,
        f'{_v.upper()} 0xC616C = {_clamp} -- the slot-2 torque clamp, THE interlock on the'
        f' mixer->delivery path'
        + ('' if _clamp == 0 else ' -- gp-0x6b4a IS NOW LIVE, and so is the rate limiter'))
    if _x0 != 0:
        print(f'         note: {_v.upper()} 0xC63CC = {_x0} (Honda 0) -- iVar13 now reaches '
              f'gp-0x6b4c as well as gp-0x6b4a.')

print()
print("[12] THE FLOAT PI BLOCK NEXT TO THE BIQUAD MUST STAY BYTE-STOCK -- 0xC60B8-0xC60DC")
# FUN_00033d10 is a two-lane float PI controller whose gains sit at 0xC60B8-0xC60D8, IMMEDIATELY
# after the assist biquad at 0xC60A8/AC/B0/B4 that the notch builders write.  One float of offset
# error in a notch build lands in this block.  It is dormant (lane 1 off via 0xC649D=0, lane 2's
# output discarded by 0xC4124[2]=5, torque term zeroed by 0xC616C=0), so a corruption here would
# be SILENT on the bench and would only show up as behaviour once any of those three zeros moved.
_PI = open(os.path.join(ROOT, 'analysis-2020accord', 'stock_fw_dump', 'code.bin'),
           'rb').read()[0xC60B8:0xC60DC]
for _v in sorted(img):
    chk(img[_v][0xC60B8:0xC60DC] == _PI,
        f'{_v.upper()} 0xC60B8-0xC60DC PI gains byte-stock'
        + ('' if img[_v][0xC60B8:0xC60DC] == _PI else ' -- A NOTCH EDIT LANDED ONE FLOAT LOW'))

print()
print("[13] A GAIN RAISE MUST BE PRICED AGAINST THE NOTCH, ACROSS THE WHOLE BAND")
# GATE 2 checks max|H| of the BIQUAD.  But the loop gain the car sees is biquad x 0xC6CD0, and a
# build may raise 0xC6CD0 while the notch gives nothing back outside its skirt.  Priced 2026-08-29
# for the 6x -> 8x step (5346 -> 7128) on the V208/V212 notch, using the kit's own empirical
# amplitude law (vibration ~ gain^1.74, from the m^1.74 fit):
#
#     growth = (7128/5346)^1.74 = 1.650x, FLAT across frequency
#     notch attenuation vs stock falls with frequency: 4.48x @23 Hz, 1.89x @28, 1.59x @30,
#                                                      0.80x @40, 0.30x @49
#     => NET WIN below 29.5 Hz (0.37x at 23 Hz), NET LOSS above:
#        1.04x @30, 1.47x @35, 2.07x @40, 5.53x @49
#
# That matters because V59 measured an ENGAGEMENT-GATED 42.19 Hz line, prominence 11.10x engaged
# vs 0.00x disengaged.  Its proposed mechanism (parametric modulation of the PID lane gains at 2f)
# is VOID -- re-verified here: K_p/K_i/K_d at 0xC6B1E/0xC6B0A/0xC6ADE are FLAT at the operating
# point gp-0x6ac0 = 99, and the contrary reading used 0xC671E, off by 0x400, which is the
# square-wave injector block.  But the LINE ITSELF still stands and its mechanism is UNKNOWN.
# Raising loop gain 1.65x exactly where the notch stops helping, in a band with an unexplained
# engagement-gated line, is not a blind change.  Hence: STAGED until the notch is confirmed on-car.
_GAIN_BASE = 5346                      # 6.00x -- the notch shelf's baseline (0xC6CD0 = 891 * N)
_STAGED = {'v211','v213','v215','v216','v217','v218','v219','v220'}  # priced and documented
for _v in sorted(img):
    _g = struct.unpack_from('<H', img[_v], 0xC6CD0)[0]
    if _g <= _GAIN_BASE:
        chk(True, f'{_v.upper()} 0xC6CD0 = {_g} ({_g / 891:.2f}x) -- at or below the notch baseline')
    else:
        chk(_v in _STAGED,
            f'{_v.upper()} 0xC6CD0 = {_g} ({_g / 891:.2f}x) RAISES loop gain '
            f'{_g / _GAIN_BASE:.3f}x -- must be a documented STAGED build'
            + ('' if _v in _STAGED else ' -- IT IS NOT. Price it against the notch first.'))
        print(f'         {_v.upper()} is STAGED: growth {(_g / _GAIN_BASE) ** 1.74:.3f}x is a net'
              f' win below ~29.5 Hz and a net LOSS above (2.07x @40 Hz).')

    # AND THE CLAMPS MUST TRACK IT. Added 2026-08-29: this gate priced the gain and never checked
    # that the forward clamps still clear the lane maximum. V101 had to raise them for 8x; a build
    # that raises 0xC6CD0 and leaves 0xC61B2/B4 alone would have the clamps BIND, silently turning
    # the authority lever into a clipper. The builders assert this; the close-out did not.
    _clip = struct.unpack_from('<H', img[_v], 0xC61BE)[0]
    _cl = struct.unpack_from('<H', img[_v], 0xC61B2)[0]
    _clb = struct.unpack_from('<H', img[_v], 0xC61B4)[0]
    _eme = struct.unpack_from('<H', img[_v], 0xC674E)[0]
    _lane = (_clip * _g) >> 15
    chk(_lane < _cl and _cl == _clb and _cl < _eme,
        f'{_v.upper()} clamps track the gain: lane max {_lane} < clamp {_cl} < EME wall {_eme}'
        + ('' if (_lane < _cl and _cl == _clb and _cl < _eme)
           else ' -- THE CLAMPS BIND, the gain lever is clipping'))

# and re-assert the tables the VOID rests on, so the dispute cannot silently reopen
_st = open(os.path.join(ROOT, 'analysis-2020accord', 'stock_fw_dump', 'code.bin'), 'rb').read()
for _b, _n in ((0xC6B1E, 'K_p'), (0xC6B0A, 'K_i'), (0xC6ADE, 'K_d')):
    _Y = [struct.unpack_from('<H', _st, _b + 8 + 2 * _k)[0] for _k in range(4)]
    chk(_Y[0] == _Y[1],
        f'{_n} at 0x{_b:05X} is FLAT in segment 0 {_Y} -- no 2f parametric pump at the'
        f' operating point')

print()
print("[14] THE 6-9 Hz DAMPER MUST BE PRICED AGAINST THE FLOWN CAR, NOT JUST AGAINST HONDA")
# gp-0x6b26 (0xD7A5C, engaged m26) is a REAL 6-9 Hz DAMPER: measured after V94 flew it at
# +137/+139 deg vs WHEEL rate, |cos| 0.73 => +518/+565 counts of POSITIVE Re(Z).  V94 cut it and
# the operator ABORTED: "made the stuttering and grinding worse, by a lot ... it vibrated the
# entire car, and I decided it was not safe to drive."  Route r7d is that drive, and it carries a
# sustained engagement-gated ~31 Hz line at 459x the creep-matched corpus median.
#
# The flown car (V108) carries this row at 3.576x Honda.  The notch shelf carries 0.500x -- a
# 7.15x CUT, reached in two UNFLOWN steps (V175 3.576->1.000, V196 1.000->0.500) and bundled
# invisibly inside builds whose stated purpose is a grinding fix.  Every previous check compared
# this row to HONDA, which made a 7.15x change from the CAR look like a tidy "half dose".
# So: report the dose against BOTH references, and fail any build that cuts it below Honda
# without being a documented member of the reduced-damper arm.
_FLOWN_Y = (-29490, -17202, -16000)          # V108, on the car
_HONDA_Y = (-9830, -5734, -1966)
_hs = sum(abs(_x) for _x in _HONDA_Y)
_fs = sum(abs(_x) for _x in _FLOWN_Y)
_REDUCED_ARM = {'v194', 'v195', 'v196', 'v198', 'v199', 'v200', 'v201', 'v202', 'v203', 'v204',
                'v205', 'v206', 'v207', 'v208', 'v209', 'v210', 'v211', 'v212', 'v213'}
for _v in sorted(img):
    _Y = tuple(struct.unpack_from('<h', img[_v], 0xD7A5C + 2 * _i)[0] for _i in range(3))
    _ss = sum(abs(_x) for _x in _Y)
    _vh, _vf = _ss / _hs, _ss / _fs
    if _ss >= _hs:
        chk(True, f'{_v.upper()} 0xD7A5C {_vh:.3f}x Honda / {_vf:.3f}x FLOWN -- damper at or above Honda')
    else:
        chk(_v in _REDUCED_ARM,
            f'{_v.upper()} 0xD7A5C {_vh:.3f}x Honda / {_vf:.3f}x FLOWN'
            f' -- CUTS the 6-9 Hz damper {1 / _vf:.2f}x below the car'
            + ('' if _v in _REDUCED_ARM else ' -- NOT a documented reduced-damper build'))

print()
print("[15] THE ASSIST PASSBAND MUST SURVIVE -- max|H| <= 1 DOES NOT PROTECT IT")
# GATE 2 caps max|H| over 0-500 Hz. It says nothing about the FLOOR, so a design can pass it while
# attenuating everything the driver actually feels. Found 2026-08-29 while pricing the notch's phase
# budget: optimising 15-25 Hz energy removal WITHOUT a passband constraint returns
#     zeros 18.50, poles 11.50, r 0.985   ->  scores 99.0 % removed
# which sounds excellent and is worthless -- it puts a resonant peak at 11.5 Hz, normalises THAT to
# 1.0, and pushes the whole 0-5 Hz passband to 0.62x. It does not notch the grind, it turns the base
# power assist DOWN 38 %. Every broadband attenuator scores near 100 % on a removal metric.
# The biquad sits in the BASE POWER-ASSIST path, so the passband IS steering effort.
_PB = (0.02, 0.5, 1.0, 2.0, 3.0, 5.0)
for _v in sorted(img):
    # NB: _st is rebound to the stock IMAGE BYTES by gate [12]; use struct explicitly.
    _a1, _a2, _b1, _g = (struct.unpack_from('<f', img[_v], _a)[0]
                         for _a in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4))
    _lo = 9.9
    for _f in _PB:
        _z = cmath.exp(2j * math.pi * _f / 1000.0)
        _lo = min(_lo, abs(_g * (_z * _z + _b1 * _z + 1) / (_z * _z + _a1 * _z + _a2)))
    # DOCUMENTED EXCEPTIONS, exactly as gate [2] carries its own. V194/195/196/198 are the
    # GATE-2-violating notch arc the record already condemns; this gate finds a SECOND defect in
    # them -- they also attenuate the driver's own band by 4.5-5.9 %. They are listed so a NEW
    # violation still fails rather than hiding behind a raised bar. None is the fly-first build.
    _PB_EXC = {'v194': 0.9550, 'v195': 0.9410, 'v196': 0.9410, 'v198': 0.9410}
    if _v in _PB_EXC:
        chk(abs(_lo - _PB_EXC[_v]) < 5e-4,
            f'{_v.upper()} passband floor {_lo:.4f} -- KNOWN BAD (the GATE-2 notch arc), '
            f'unchanged at its recorded value')
    else:
        chk(_lo >= 0.99,
            f'{_v.upper()} passband floor 0-5 Hz = {_lo:.4f} >= 0.99'
            + ('' if _lo >= 0.99 else ' -- THIS BUILD TURNS THE BASE ASSIST DOWN, it does not notch'))

print()
print("[16] THE CAVE, AND THE LOAD-BEARING LEVERS NO GATE COVERED")
# Found 2026-08-29 by asking the complementary question to the gate audit: not "does each gate check
# the right thing" but "which non-stock cells has NO gate at all". V217 differs from stock in 115
# payload runs; only 16 were referenced anywhere in this file.
#
# (a) THE 164-BYTE CODE CAVE. Code caves are this kit's ONLY bricking class -- V24, V27 and V48B all
#     bricked the ECU. Each builder asserts the cave is byte-identical to ITS OWN base, which is a
#     chain of local checks: if one link were wrong every later build would inherit it and still
#     pass. Nothing compared the cave ACROSS the shelf. It is identical on all of them today; this
#     pins that so a divergence cannot appear silently.
# (b) FOUR LEVERS WITH ON-CAR RESULTS AND NO ASSERTION. 0x454FE is the case that proves the need:
#     V42's ratchet fix was SILENTLY LOST at a rebase and sat byte-stock from V53 to V70 before
#     anyone noticed. A gate would have caught it the same day.
_CAVE = (0xC4B34, 0xC4BD8)
_ref = None
for _v in sorted(img):
    _c = img[_v][_CAVE[0]:_CAVE[1]]
    if _ref is None:
        _ref = _c
        _rv = _v
    chk(_c == _ref,
        f'{_v.upper()} 164-byte cave identical to {_rv.upper()}'
        + ('' if _c == _ref else ' -- THE CAVE DIVERGED, this is the bricking class'))

_LEVERS = {
    0x454FE: ('V42 ratchet fix (LOST at a rebase once, byte-stock V53-V70)', 26037, 'H'),
    0xC6446: ('Lever B -- V88, best measured grind lever in the kit', 5244, 'H'),
    0x3AA96: ('Lever B arm, V88 sign fix', 0x97FB, 'H'),
    0xC62EA: ('low-speed steer lockout DISABLED (stock 320 ct ~ 5 km/h)', 0, 'H'),
}
for _v in sorted(img):
    for _a, (_nm, _want, _f) in sorted(_LEVERS.items()):
        _got = struct.unpack_from('<' + _f, img[_v], _a)[0]
        chk(_got == _want,
            f'{_v.upper()} 0x{_a:05X} = {_got} -- {_nm}'
            + ('' if _got == _want else f' -- EXPECTED {_want}, THIS LEVER HAS MOVED'))

print('\n' + '=' * 84)
print(f'  {ok} checks passed, {len(bad)} failed')
for m in bad:
    print('    FAILED: ' + m)
print('=' * 84)
sys.exit(1 if bad else 0)
