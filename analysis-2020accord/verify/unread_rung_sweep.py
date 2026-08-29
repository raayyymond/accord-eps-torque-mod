# -*- coding: utf-8 -*-
"""
SWEEP EVERY CACHED ROUTE'S CAVE RUNGS FOR ANSWERS NOBODY READ.

V105's cave rung b6 was `|gp-0x6b94| >= |gp-0x4f64|` -- cut to measure the governor clip duty, the
exact question I was about to build a new probe for.  It flew, its route was cached, and it had been
sitting unread.  Reading it took one line and killed the largest remaining candidate.

Every flown probe build cost a drive.  There are ~24 cached routes, each carrying up to five rungs in
0x14A byte4 bits 7:3.  That is on the order of a hundred measurements already paid for.  This reads
all of them and ranks by whether the answer is INFORMATIVE (duty strictly between 0 and 1) or
DEGENERATE (0.000000 or 1.000000 -- either a dead rung or a saturated one, both of which the record
has repeatedly mistaken for findings).
"""
import glob
import os
import sys

import numpy as np

sys.path.insert(0, 'analysis-2020accord/lib')
import route_build_registry as R                                          # noqa: E402

C = 'analysis-2020accord/_scratch/cache'
BITS = (7, 6, 5, 4, 3)

rows = []
for d in sorted(glob.glob(C + '/r*')):
    tag = os.path.basename(d)[1:]
    f = glob.glob(os.path.join(d, '*.npz'))
    f = [x for x in f if os.path.basename(x) == 'r%s.npz' % tag]
    if not f:
        continue
    try:
        z = np.load(f[0], allow_pickle=True)
    except Exception:
        continue
    if 'probe' not in z or 'cc_lat' not in z:
        continue
    pr = np.asarray(z['probe']).astype(float)
    eng = np.asarray(z['cc_lat']).astype(float) > 0.5
    n = min(len(pr), len(eng))
    pr, eng = pr[:n], eng[:n]
    if eng.sum() < 500:
        continue
    p = pr[eng].astype(int)
    duties = {b: float(((p >> b) & 1).mean()) for b in BITS}
    rec = R.BY_ROUTE.get(tag)
    rows.append((tag, int(eng.sum()), duties, rec))

print('=' * 112)
print('  UNREAD RUNG SWEEP -- %d cached routes with >= 500 engaged frames' % len(rows))
print('  duty in (0,1) = INFORMATIVE.  0.000000 / 1.000000 = degenerate (dead rung or saturated).')
print('=' * 112)
informative = 0
degenerate = 0
for tag, neng, duties, rec in rows:
    build = rec.build if rec else '?'
    meaning = rec.probe if rec else '(not in registry)'
    print('\n  r%-4s  %-10s  n_eng %6d   %s' % (tag, build, neng, meaning))
    line = []
    for b in BITS:
        d = duties[b]
        if d in (0.0, 1.0):
            degenerate += 1
            line.append('b%d %.6f DEGEN' % (b, d))
        else:
            informative += 1
            line.append('b%d %.4f' % (b, d))
    print('        ' + '  '.join(line))
    if rec and rec.evidence:
        ev = ' '.join(rec.evidence)
        print('        recorded: %s' % (ev[:150] + ('...' if len(ev) > 150 else '')))
    else:
        print('        recorded: ** NOTHING IN THE REGISTRY EVIDENCE FIELD **')

print()
print('=' * 112)
print('  %d informative rung-readings, %d degenerate, across %d routes.'
      % (informative, degenerate, len(rows)))
print('  A DEGENERATE rung is not a null result -- it is an uninterpretable one, and the record has')
print('  repeatedly mistaken the two.  An INFORMATIVE rung with nothing in its evidence field is an')
print('  answer that was paid for with a drive and never read.')
