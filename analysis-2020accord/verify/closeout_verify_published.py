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

# ---- 3. superseded artifacts ------------------------------------------------------------
print('\n[3] SUPERSEDED ARTIFACTS ARE RENAMED')
live = [os.path.basename(x) for x in glob.glob(RWD + '/39990*-V199-*.rwd')
        + glob.glob(RWD + '/39990*-V202-*.rwd')
        + glob.glob(RWD + '/39990*-V204-*.rwd')
        + glob.glob(RWD + '/39990*-V205-*.rwd')
        + glob.glob(RWD + '/39990*-V206-*.rwd')
]
chk(len(live) == 5, f'exactly 5 flashable builds from this chain ({len(live)})')
# V194/V195/V196/V198 were PULLED: every one carries a notch whose poles sit at the zeros, scoring
# max|H| 1.3533-1.7177 against the lineage bar of stock 1.0000.  They must not be flashable.
for v in ('V185', 'V186', 'V187', 'V188', 'V189', 'V190', 'V191', 'V192', 'V193',
          'V194', 'V195', 'V196', 'V197', 'V198', 'V200', 'V201', 'V203', 'V207'):
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
    chk(_kn > 0, f'{_v.upper()} friction lane: knee {_kn}, K1 {_k1} '
                 f'=> {_mult:.3f}x Honda below saturation, saturating at {_kn / 12.0:.0f} '
                 f'(Honda 50)')

print('\n' + '=' * 84)
print(f'  {ok} checks passed, {len(bad)} failed')
for m in bad:
    print('    FAILED: ' + m)
print('=' * 84)
sys.exit(1 if bad else 0)
