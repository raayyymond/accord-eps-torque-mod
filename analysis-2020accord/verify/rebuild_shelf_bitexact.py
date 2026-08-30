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
    'v214': '4be4d47c1f0ad0deacbac46bd020cf5e02f06896144455766be48e330dbcedb5',
}
BD = os.path.join(KIT, 'builds', 'v108_plus')
IMGD = os.path.join(FW, 'analysis-2020accord')

ok, bad = 0, []
print('=' * 96)
print('  SHELF REBUILD -- does each builder still produce the artifact it published?')
print('=' * 96)
env = dict(os.environ, ACCORD_FIRMWARE_ROOT=FW)
for v, want in sorted(SHELF.items()):
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
print(f'  {ok}/{len(SHELF)} shelf builders reproduce bit-for-bit')
for m in bad:
    print('    FAILED: ' + m)
print('=' * 96)
sys.exit(1 if bad else 0)
