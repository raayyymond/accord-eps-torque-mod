# -*- coding: utf-8 -*-
"""WITHDRAWN-CLAIMS REGISTRY -- a claim retracted once must not reappear as fact.

    python analysis-2020accord/verify/withdrawn_claims.py

WHY THIS EXISTS. On 2026-08-30 four documents were found asserting claims that had been withdrawn
earlier the same day -- two of them in files the withdrawing agent had itself written, and one of them
inside the paragraph justifying a drive order. Each was found by hand, which works only when someone
happens to look. This makes it mechanical.

The failure is structural, not careless: a claim gets withdrawn in ONE place (a memory banner, a STATE
block) while the sentences it spawned live on in cards, pre-registrations and builder banners. Nothing
connects them.

HOW TO USE IT. When you withdraw a claim, add a row here. The row is a regex that should now match
NOWHERE except in text that also carries a retraction marker on the same line. That exception is what
lets a document DISCUSS the withdrawal ("an earlier version said X, which is wrong") without tripping.

WHAT IT CANNOT DO. It matches phrasing, not meaning. A claim restated in different words slips
through. It is a ratchet against literal reintroduction, not a proof of consistency.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# (regex, short label, where/why it was withdrawn)
WITHDRAWN = [
    (r'cannot make anything worse',
     'V228 "cannot make anything worse"',
     '2026-08-30: false. It cannot make the RATCHET worse; the notch is NOT flat at 40-49 Hz and '
     'V228 raises that band ~+5.9 dB.'),
    (r'r24 DAMPS at 6.9 ?Hz',
     'r24 DAMPS (absolute direction)',
     '2026-08-30: failed its retrodiction vs V88 (corr -0.803, positive required). Both "damps" and '
     '"pumps" are UNRESOLVED. The 187 ct MAGNITUDE stands.'),
    (r'r24/r26 PUMPS\s*[-−]431',
     'r24/r26 PUMPS -431..-1294 ct',
     '2026-08-30: measured 187 ct on 6 routes, and the direction is unresolved.'),
    (r'points the SAFE way',
     'the Lever B concern "points the SAFE way"',
     '2026-08-30: the direction was withdrawn; only the magnitude correction stands.'),
    (r'task 5 (?:is |= )100 ?Hz',
     'task 5 = 100 Hz',
     '2026-08-12: RETRACTED (address-coincidence derivation; contradicted by flown gp-0x6bbe '
     'telemetry). Task 5 rate is OPEN. Do not use a ZOH lag as a veto.'),
    (r'grind #2 is V62',
     '"grind #2 is V62\'s sar"',
     '2026-08-30: REFUTED -- V71c produced grind #2 carrying NEITHER sar byte. Origin is OPEN.'),
    (r"V230'?s? (?:alpha2 )?lever is probably inert|probably a no-op",
     'V230\'s lever called "probably inert"',
     '2026-08-30: MISREADING. The x1.5 null means UNMEASURABLE, not dead -- y = K*alpha is invariant '
     'to K while the motion is not. V94\'s 6x cut aborted a drive, proving the cell reaches the car.'),
    (r'no LINEAR lane is the ratchet|every lane damps at the ratchet',
     'the all-lanes ratchet scan conclusion',
     '2026-08-30: WITHDRAWN as unsupported. It scored cos(phase vs cs_rate), and cs_rate is at '
     'CHANCE for the ratchet (margin 1.03). Redone against cs_tq it has no discriminating power: '
     'all 7 lanes are filtered copies of the same sensor, coherence 0.95-0.98, phase 15.9-19.8 deg.'),
    (r'V230 is the (?:recommendation|lead)|DRIVE V230 FIRST',
     'V230 as the recommended build',
     '2026-08-30: its lever acts on the gp-0x6b26 lane, which is INVARIANCE-PARTITIONED -- a x1.5 '
     'dose measured INERT (p50 0.988) and a 6x cut ABORTED a drive. V229 is the lead.'),
    (r'OSTM0.{0,40}1000 ?Hz|1 ?kHz.{0,30}OSTM0',
     '1 kHz derived from OSTM0',
     '2026-08-30: the OSTM0 route is REFUTED (PCLK is 40 MHz, not 80). 1 kHz stands on the ON-CAR '
     'dwell alone.'),
]

# a line that also carries one of these is DISCUSSING the withdrawal, not asserting it
EXEMPT = re.compile(
    r'withdraw|retract|refut|supersed|disput|correct|WRONG|false|not settled|unresolved|'
    r'earlier version|no longer|struck|downgrad|I published|as EVIDENCE|not independently confirmed|not confirmed|⚠|🛑', re.I)

ROOTS = ['docs/**/*.md', 'memory/**/*.md', 'analysis-2020accord/**/*.py', 'rlog-tools/**/*.py']
# archives AND handoffs are RECORDS of what was believed then -- the kit's own convention
# is that they stay as written. Only live, instruction-bearing files are scanned.
SKIP = ('docs/archive/', 'docs/handoffs/', 'withdrawn_claims.py', '_scratch')

# a FILE carrying a caution banner in its opening block is exempt as a whole: the banner
# already tells the reader not to trust what follows, which is the correct pattern.
FILE_BANNER = re.compile(r'DISPUTED|SUPERSEDED|RETRACTED|WITHDRAWN|REFUTED|DO NOT SIZE A BUILD', re.I)


def files():
    out = set()
    for pat in ROOTS:
        for f in glob.glob(pat, recursive=True):
            n = f.replace('\\', '/')
            if any(s in n for s in SKIP):
                continue
            out.add(n)
    return sorted(out)


print('=' * 96)
print('  WITHDRAWN-CLAIMS REGISTRY')
print('=' * 96)
print()
fs = files()
print('  %d registered claims, scanned across %d live files' % (len(WITHDRAWN), len(fs)))
print('  (docs/archive/ is skipped: archives are a RECORD of what was believed, not an instruction)')
print()

hits = []
for f in fs:
    try:
        txt = io.open(f, encoding='utf-8', errors='replace').read()
    except OSError:
        continue
    if FILE_BANNER.search(txt[:1800]):   # bannered file: the banner covers it
        continue
    for i, line in enumerate(txt.split('\n'), 1):
        for rx, label, why in WITHDRAWN:
            if re.search(rx, line, re.I) and not EXEMPT.search(line):
                hits.append((f, i, label, line.strip()[:90]))

if hits:
    print('  %-46s %6s  %s' % ('file', 'line', 'claim'))
    for f, i, label, snip in hits:
        print('  %-46s %6d  %s' % (f[-46:], i, label))
        print('        %s' % snip)
else:
    print('  [OK] no withdrawn claim is asserted anywhere outside the archives.')

print()
for _, label, why in WITHDRAWN:
    print('  • %-38s %s' % (label, why))

print()
assert not hits, '%d withdrawn claim(s) asserted as fact' % len(hits)
print('  [EVIDENCE] %d claims registered, none reasserted.' % len(WITHDRAWN))
print('  [LIMIT]    matches PHRASING, not meaning. A claim restated in other words slips through;')
print('             this is a ratchet against literal reintroduction, not a consistency proof.')
