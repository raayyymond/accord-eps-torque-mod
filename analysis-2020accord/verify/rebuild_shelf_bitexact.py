# -*- coding: utf-8 -*-
"""
RE-RUN EVERY SHELF BUILDER AND ASSERT IT REPRODUCES ITS PUBLISHED IMAGE BIT-FOR-BIT.

Roughly ten builders were generated this session by transforming earlier ones, and that method has
already produced real defects: a stale `_v200_` image-filename prefix, an inherited probe expectation,
a wrong payload-byte count, a docstring quoting the previous build's notch.  Each was caught -- but a
stale transformed constant that changes the IMAGE rather than a docstring is the one class none of the
other checks would catch, because every downstream check compares against the hash the builder itself
just produced.

The close-out contract's answer is to re-verify from disk, not from the report.  This runs each
builder in NON-WRITING mode and compares the SHA256 it computes against the hash published in
closeout_verify_published.py -- so a builder that has silently drifted from its artifact fails here.
"""
import hashlib
import os
import re
import subprocess
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(KIT)
PY = 'C:/Users/dudei/anaconda3/envs/bin_decompile/python'
FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    'C:/Users/dudei/Desktop/Projects/accord-firmwares')

# the shelf, and the hash each builder is expected to produce
SHELF = {
    'v199': 'c86646ab48c4a62546b4e7bafa59f8097d3bdd99ffdcd3aeabd9f93c7252dc10',
    'v210': 'ab49ca762b7017de436a7b80d15a7a72fda7e3f862f32c3a9106318018da814b',
    'v211': '70b205589b6f81a9f1e4f039daf8f744a66a1b9865ddbe133b499ef6ce35368e',
    'v208': 'e27b4fcc2dafd872feb25e5625544dbe4f9067a742cec1670d8d3dde176b1f7a',
    'v209': '984dfe5590bb8bfedaedca1256008cdd81cf33837acaa54a909463768b47327c',
    'v212': 'dcc1b921e85e56bce56b3c1e69c795194c141dd4486b4f4e8b3755a2a6c2b04a',
    'v213': 'b1f998702adbbce9a52e7e430906f0cd77410625c29887e4d0a06e4cddb0e239',
    'v215': 'afc1d88505d2c55d37d6379f4cab058b9d1926c334c13d4c92761d138c62fbff',
    'v216': '791e123fb4d8bd6ea0736c52546995bb15742444b5d5c23b6db128e8bd792a13',
    'v217': 'f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b',
    'v218': 'f73aee347d67c10e0a50431d01143407bdee180e792022e2002eb8451c10b691',
    'v219': '13c1d33b3ad9eff526283b7465e3b85b18084056479588ba2741537b25d10d33',
    'v220': 'ce07b776b8cdfef3ed9584a8352ce8922398c0c631ac132a1bc8f78425070097',
    'v221': '7bb0ba58956ca21064a815d0298c6994cf124b941c72aa76c03f8628a598c51b',
    'v222': '0e83c7074699d6ab3eee1c035974fa23b5b271c641662001b63fd89558512dae',
    'v223': 'a2f034df682cbd4a9ffe9f56787fd40d5465c4c36423362ce7dc03501fa81869',
    'v224': '21198a4d1f21ce8d07b25530fc2969466f5e644370220658008a499b2585f2c3',
    'v225': '34d1804120aa52a1131e50663eede9c16ab95e767a16d05dee277911410adac3',
    'v226': 'e45799ed7986139183e50b14d4a15b08085b453d3d1a97a580bda5d7d18e9850',
    'v227': '28b5f4c979660451cda9c457312b824622488201d96ecf1dbf3be90dd8d67434',
    'v228': '6cf12db9fc49aee29e46c169c05fc18415f2a970b477cdae1372d57805748b3c',   # flight candidate: V222 at the car 6x
    'v229': '078da4b1f22903a5364b54b0035790f0fac6453a4717e881290eefb15bc14a42',   # V228 + Honda's 55 Hz notch restored
    'v230': 'bb11115a54ba97b4216f7bb2a12c1a9da2d0ba4c7495d80f008d7bc35eac3f61',   # V229 + alpha2 3 -- BOTH cuts
    'v231': '34a4400d3d848069890a7d2be298d4ba3118e86251421d535f2f534676cace37',   # V229 + the biquad-state probe

}
# ARCHIVE: builds whose BUILDER must still reproduce its image, but which are NOT meant to be
# flashable -- their .rwd files are correctly SUPERSEDED-DO-NOT-FLASH-renamed. They were in the
# close-out's PUB list (published hash vs disk) but their builders were never re-run, which is
# the one drift class this file exists to catch. The 'exactly one flashable .rwd' rule below is
# a SHELF rule and deliberately does NOT apply to them.
ARCHIVE = {
    'v194': '2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10',
    'v195': 'a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b',
    'v196': 'f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e',
    'v198': '9fbbf90b0bed9cb32eb7c3a44a30c2108f361a736ff3f1ebc205f47e5cf3190d',
    'v200': 'db0b613aad11e67822528251b66790386635a59e9584e87d352bf294d5bf460e',
    'v201': '354f9dfb93cf6fcd309c791ff962a792db668c6faef1de5a563d9f389f3bdfd6',
    'v202': '2c5bc569c2c5e4c66f7eaa350ddbfe87d50af9875fa75a10d927eed3a7255160',
    'v203': '0da3b7b9a4bfa9068960ed1c5afd07ff4f816376da9488df4d31946cf55b5965',
    'v204': '30e7da9f6d20ff1335d01abe86ba03df7245c802217a4e6df54c5b93208873e6',
    'v205': '8cf100864be1d6030eed36acac1d514066b157a59de8ca829ae154ce7032882e',
    'v206': '71bd8312c324de9c01cf277307e41bb6dbb5e49cc6cf72e02e597a8013333a80',
    'v207': '8de7180ec4daeb459be994d180321b235a5c79ade9050eff015e83b0f537067c',
}

BD = os.path.join(KIT, 'builds', 'v108_plus')
IMGD = os.path.join(FW, 'analysis-2020accord')

ok, bad = 0, []
print('=' * 96)
print('  SHELF REBUILD -- does each builder still produce the artifact it published?')
print('=' * 96)
env = dict(os.environ, ACCORD_FIRMWARE_ROOT=FW)
for v, want in sorted({**SHELF, **ARCHIVE}.items()):
    b = os.path.join(BD, f'build_{v}_tva.py')
    if not os.path.exists(b):
        bad.append(f'{v.upper()}: builder missing at {b}')
        print(f'  [FAIL] {v.upper()} builder missing')
        continue
    r = subprocess.run([PY, b], cwd=ROOT, capture_output=True, text=True, env=env, timeout=900)
    m = re.search(r'image SHA256\s+([0-9a-f]{64})', r.stdout)
    if m is None:
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        bad.append(f'{v.upper()}: builder did not emit an image hash -- {tail}')
        print(f'  [FAIL] {v.upper()} builder produced no hash')
        continue
    got = m.group(1)
    na = re.search(r'(\d+)/(\d+) assertions passed', r.stdout)
    asserts = na.group(0) if na else 'no assertion line'
    if got == want:
        ok += 1
        print(f'  [PASS] {v.upper()} reproduces {got[:16]}...  ({asserts})')
    else:
        bad.append(f'{v.upper()}: builder now makes {got[:16]}..., published {want[:16]}...')
        print(f'  [FAIL] {v.upper()} DRIFTED: builder {got[:16]}... vs published {want[:16]}...')

    # and the artifact on disk must match too
    hits = [f for f in os.listdir(IMGD)
            if f.startswith(f'_{v}_') and f.endswith('plain_image.bin')]
    if not hits:
        bad.append(f'{v.upper()}: no image on disk')
        print(f'         !! no _{v}_*plain_image.bin on disk')
    else:
        d = hashlib.sha256(open(os.path.join(IMGD, hits[0]), 'rb').read()).hexdigest()
        if d != want:
            bad.append(f'{v.upper()}: DISK image {d[:16]}... != published {want[:16]}...')
            print(f'         !! disk image {d[:16]}... != published')

# the .rwd on disk is what actually gets flashed -- it must decode back to the same image
RWDD = os.path.join(FW, 'flashing-2020accord', 'rwd')
print()
print('  THE .rwd ON DISK IS WHAT GETS FLASHED -- checking each is present and unique')
for v in sorted(SHELF):
    hits = [f for f in os.listdir(RWDD)
            if f.startswith('39990') and f'-{v.upper()}-' in f and f.endswith('.rwd')]
    if len(hits) == 1:
        sz = os.path.getsize(os.path.join(RWDD, hits[0]))
        print(f'  [PASS] {v.upper()} exactly one flashable .rwd, {sz} bytes')
    else:
        bad.append(f'{v.upper()}: {len(hits)} flashable .rwd files (want exactly 1)')
        print(f'  [FAIL] {v.upper()} has {len(hits)} .rwd files')

print()
print('=' * 96)
print(f'  {ok}/{len(SHELF) + len(ARCHIVE)} builders reproduce bit-for-bit '
      f'({len(SHELF)} shelf + {len(ARCHIVE)} archive)')
for m in bad:
    print('    FAILED: ' + m)
print('=' * 96)
sys.exit(1 if bad else 0)
