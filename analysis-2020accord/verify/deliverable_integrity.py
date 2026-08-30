# -*- coding: utf-8 -*-
"""END-TO-END INTEGRITY PASS — every deliverable present, every tool executing, every hash from disk.

    python analysis-2020accord/verify/deliverable_integrity.py

The close-out contract says anything REPORTED must be re-verified from the filesystem at close-out,
because agent replies are not evidence. This runs that check over the whole 2026-08-30 deliverable set
in one command, so a stale artifact or a broken tool is found NOW rather than on the day of a drive.

It checks four things and nothing else:
  1. every document exists AND contains a sentinel string proving its key content is present
  2. every tool actually EXECUTES (exit 0) -- not that it exists, that it runs
  3. every artifact hash is re-read from disk and compared to what was reported
  4. both repos are clean, so nothing reported is uncommitted

It runs the OTHER gates rather than duplicating them, because a gate nobody invokes is a gate
that does not exist -- which is exactly how four broken memory pointers survived until
2026-08-30. One command, everything verified.

Re-run it after any change to the shelf. If a hash moves, either a build was re-cut (in which case the
record must be updated) or something is wrong.
"""
import glob
import hashlib
import io
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FW = os.environ.get('ACCORD_FIRMWARE_ROOT', 'C:/Users/dudei/Desktop/Projects/accord-firmwares')
PY = 'C:/Users/dudei/anaconda3/envs/bin_decompile/python'
fails = []


def ok(cond, label, detail=''):
    print('  [%s] %-56s %s' % ('PASS' if cond else 'FAIL', label, detail))
    if not cond:
        fails.append(label)


print('=' * 92)
print('  FINAL INTEGRITY PASS')
print('=' * 92)
print()
print('  DOCUMENTS')
for f, must in [
    ('docs/STATE.md', 'THE DECISION, IN ONE PLACE'),
    ('docs/scoring/DRIVE-CARD-V228.md', 'DRIVE V228 TWICE'),
    ('docs/scoring/DRIVE-CARD-V230-V229-V228.md', 'DRIVE **V230** FIRST'),
    ('docs/scoring/DRIVE-CARD-V222.md', 'SAFER SIBLING'),
    ('docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md', 'CANNOT do'),
    ('docs/specs/design/CAVE-SPECS-THE-TWO-REMAINING-INSTRUMENTS.md', 'GATE RESULTS'),
    ('docs/handoffs/2026-08/HANDOFF-2026-08-30-the-cal-search-closes.md', 'WITHDRAWN'),
    ('docs/BUILD-LINEAGE.md', 'RULE 5b'),
]:
    e = os.path.exists(f)
    has = e and must in io.open(f, encoding='utf-8', errors='replace').read()
    ok(e and has, os.path.basename(f), '%.0f KB' % (os.path.getsize(f) / 1024) if e else 'MISSING')

print()
print('  TOOLS (must actually execute)')
for cmd, label in [
    (['analysis-2020accord/verify/closeout_verify_published.py'], 'closeout verifier'),
    (['analysis-2020accord/verify/no_orphan_bytes.py', 'v228'], 'orphan-byte gate (V228)'),
    (['rlog-tools/score/score_8x_experiment.py', '--selftest'], 'pre-registered scorer selftest'),
    (['rlog-tools/decode/extract_route_generic.py', '--check', 'V228'], 'generic extractor tap check'),
    (['rlog-tools/score/rez_spectrum.py'], 'Re(Z) spectrum instrument'),
    (['analysis-2020accord/verify/memory_index_consistency.py'], 'memory-index consistency'),
    (['analysis-2020accord/verify/withdrawn_claims.py'], 'withdrawn-claims registry'),
    (['analysis-2020accord/verify/rebuild_shelf_bitexact.py'], 'shelf rebuilds bit-exact'),
]:
    try:
        r = subprocess.run([PY] + cmd, capture_output=True, timeout=420, text=True,
                           encoding='utf-8', errors='replace')
        good = r.returncode == 0
    except Exception as ex:
        good, r = False, None
    ok(good, label, '' if good else 'exit!=0')

print()
print('  ARTIFACTS (hashes re-read from disk, not from the record)')
EXPECT = {'v222': '0e83c7074699d6ab', 'v228': '6cf12db9fc49aee2', 'v223': 'a2f034df682cbd4a'}
for tag, want in EXPECT.items():
    g = [f for f in glob.glob('%s/analysis-2020accord/_%s_*plain_image.bin' % (FW, tag))
         if 'SUPERSEDED' not in os.path.basename(f)]
    got = hashlib.sha256(open(g[0], 'rb').read()).hexdigest()[:16] if len(g) == 1 else '?'
    ok(got == want, '%s image sha256' % tag.upper(), '%s (want %s)' % (got, want))

for tag, want in (('V228', 'b90a200ce53c7f37'), ('V222', '0766d45cbad4bde1')):
    g = [f for f in glob.glob('%s/flashing-2020accord/rwd/*%s-*.rwd' % (FW, tag))
         if 'SUPERSEDED' not in os.path.basename(f) and 'DO-NOT-FLASH' not in os.path.basename(f)]
    got = hashlib.sha256(open(g[0], 'rb').read()).hexdigest()[:16] if len(g) == 1 else '?'
    ok(got == want, '%s rwd sha256' % tag, '%s (want %s)' % (got, want))

print()
print('  BASELINE DATA')
ok(os.path.exists('analysis-2020accord/_scratch/cache/r24/r24_grind.npz'),
   'r24 audio baseline (created this session)')
ok(os.path.exists('analysis-2020accord/_scratch/cache/r24/r24.npz'), 'r24 CAN cache')

print()
print('  REPOS CLEAN')
for d, label in ((os.getcwd(), 'kit'), (FW, 'firmwares')):
    r = subprocess.run(['git', '-C', d, 'status', '--porcelain'], capture_output=True, text=True)
    ok(r.stdout.strip() == '', '%s repo clean' % label, r.stdout.strip()[:40])

print()
print('=' * 92)
if fails:
    print('  %d FAILURE(S): %s' % (len(fails), ', '.join(fails)))
else:
    print('  ALL CHECKS PASS -- the deliverable set is complete and self-consistent.')
print('=' * 92)
sys.exit(1 if fails else 0)
