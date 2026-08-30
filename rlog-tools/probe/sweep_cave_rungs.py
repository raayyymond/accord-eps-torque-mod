# -*- coding: utf-8 -*-
"""SWEEP EVERY CACHED ROUTE'S CAVE RUNGS AND FLAG THE ONES NOBODY HAS READ.

    python rlog-tools/probe/sweep_cave_rungs.py [--all]

WHY THIS EXISTS. The record already names the failure it prevents: V105's `b6` sat unread because
nothing pointed at it, and `lib/route_build_registry.py` stops at r77, so the whole V90-V106 arc has
its rung meanings only in lineage prose. This session hit the same thing again from the other side --
route r85's `b5`/`b6` had been EXTRACTED in an earlier sweep but never connected to the question they
answer ("can the ratchet lever be gated off?"), and answering it took one afternoon and no drive.

So the sweep itself is now a tool rather than an ad-hoc pass, and it reports THREE things per rung:

    duty        the fraction of ENGAGED frames the rung reads 1
    verdict     DEGENERATE (0.000 / 1.000, carries no information) or INFORMATIVE
    identity    whether the cave was present at all -- a raw probe byte stuck at 0x07 is the stock
                STEER_SENSOR_STATUS with NO probe bits, i.e. an instrument that was never there

🛑 A DEGENERATE RUNG IS NOT A FINDING. It is either a real always/never, or a dead rung; those are
told apart by the build's own identity bit, not by the duty. Where a cache carries a decoded
`vNNN_bK` field the sweep uses it; otherwise it decodes bits 7:3 of the raw probe byte.
"""
import glob
import os
import re
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

STOCK_PROBE_BYTE = 0x07          # stock STEER_SENSOR_STATUS, i.e. no cave
DEGEN = 0.001                    # within this of 0 or 1 -> carries no information

# ---- route -> build, for caches whose own probe_build label is missing or unresolved ----------
# The record names the gap this fills: lib/route_build_registry.py stops at r77, so the whole
# V90-V106 arc (and later) has its build attribution only in prose. That gap is *why* rungs go
# unread. This map is CACHE-FIRST on purpose -- it carries no rlog hashes, because those are not in
# the caches and inventing them was the blocker that stopped the registry being extended.
# 🛑 EVERY ENTRY CITES ITS SOURCE. Do not add one without a citation.
ROUTE_BUILD = {
    # r21's cache says "UNKNOWN-V108-or-V111". V108 and V111 differ in only 3 payload cells and the
    # cave is BYTE-IDENTICAL, so the rungs cannot discriminate them. Resolved from the record:
    'r21': ('V111', 'docs/handoffs/2026-08/HANDOFF-2026-08-28-v112-flew-two-symptoms-separated.md '
                    'line 11 tabulates "r21  V111"; written by the session that flew r22 as V112, '
                    'whose own base is V111, so the flight order is consistent'),
}


def _lbl(k, rs):
    """Bit name, prefixed by its build only when the cache carries more than one decoded set."""
    return k if len({x.split('_')[0] for x in rs}) > 1 else k.split('_')[-1]


def rungs(d):
    """(name -> array) for every rung this cache exposes, decoded or raw.

    🛑 THE NO-CAVE CHECK RUNS FIRST, BEFORE ANY DECODED FIELD. A cache can carry decoded `vNNN_bK`
    columns that are all zero simply because the build had NO CAVE -- r97 is exactly that: 68,883
    engaged frames with the probe byte stuck at the stock 0x07. Preferring the decoded fields there
    reports "five rungs that never fire", which reads like a result and is not one. (My first version
    of this tool did precisely that.)
    """
    out = {}
    for cand in ('probe', 'field'):
        if cand in d.files:
            u = np.unique(d[cand].astype(int))
            if len(u) <= 1 and int(u[0]) == STOCK_PROBE_BYTE:
                return {}, 'NO CAVE (probe byte stuck at 0x07)'
            break
    dec = sorted(set(k for k in d.files if re.fullmatch(r'v\d+_b[3-7]', k)))
    if dec:
        for k in dec:
            out[k] = d[k].astype(float)
        return out, 'decoded (%s)' % ','.join(sorted({k.split('_')[0] for k in dec}))
    for cand in ('probe', 'field'):
        if cand in d.files:
            raw = d[cand].astype(int)
            for b in range(3, 8):
                out['%s_b%d' % (cand, b)] = ((raw >> b) & 1).astype(float)
            return out, 'raw %s byte, bits 7:3' % cand
    return {}, 'no probe channel'


def main(argv):
    show_all = '--all' in argv
    rows = []
    for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/r*.npz')):
        base = os.path.basename(p)
        if re.search(r's\d+\.npz$', base):        # per-segment caches duplicate the parent
            continue
        try:
            d = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if 'cc_lat' not in d.files:
            continue
        lat = d['cc_lat'] > 0.5
        if lat.sum() < 500:
            continue
        tag = base[:-4]
        build = str(d['probe_build'][0]) if 'probe_build' in d.files else '?'
        if tag in ROUTE_BUILD and ('UNKNOWN' in build.upper() or build in ('?', '')):
            build = ROUTE_BUILD[tag][0] + '*'      # * = resolved from the record, not the cache
        rs, how = rungs(d)
        rows.append((tag, build, int(lat.sum()), rs, how, lat))

    print('=' * 100)
    print('  CAVE RUNG SWEEP -- %d cached routes with >=500 engaged frames' % len(rows))
    print('=' * 100)
    print()
    n_inf = n_deg = n_nocave = 0
    for tag, build, n, rs, how, lat in rows:
        if not rs:
            n_nocave += 1
            print('  %-6s %-6s %7d eng   !! %s' % (tag, build, n, how))
            continue
        cells = []
        for k in sorted(rs):
            duty = float((rs[k][lat] > 0.5).mean())
            deg = duty < DEGEN or duty > 1 - DEGEN
            n_deg += deg
            n_inf += not deg
            if deg and not show_all:
                cells.append('%s=%s' % (_lbl(k, rs), 'always' if duty > 0.5 else 'never'))
            else:
                cells.append('%s=%.4f' % (_lbl(k, rs), duty))
        print('  %-6s %-6s %7d eng   %-22s %s' % (tag, build, n, how, '  '.join(cells)))

    print()
    print('  %d informative rungs, %d degenerate, %d routes with NO cave at all'
          % (n_inf, n_deg, n_nocave))
    if ROUTE_BUILD:
        print()
        print('  * = build resolved from the record because the cache label is missing or unresolved:')
        for t, (b, why) in sorted(ROUTE_BUILD.items()):
            print('      %-5s -> %-5s  %s' % (t, b, why))
    print()
    print('  🛑 A DEGENERATE RUNG IS NOT A FINDING -- "always" and "never" are only meaningful once')
    print('  the build\'s own identity bit says the cave was running. Check the lineage row before')
    print('  quoting any of these, and prefer the decoded vNNN_bK fields where a cache has them.')
    print('  ⚠ lib/route_build_registry.py stops at r77, so for newer routes the MEANING of each bit')
    print('  lives only in BUILD-LINEAGE prose. That gap is why rungs go unread; this tool shows the')
    print('  VALUES, not the meanings.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
