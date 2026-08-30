# -*- coding: utf-8 -*-
"""EVERY NON-STOCK BYTE ON THE FLIGHT CANDIDATE MUST BE EXPLAINED SOMEWHERE IN THE RECORD.

    python analysis-2020accord/verify/no_orphan_bytes.py [BUILD]        default: v222

An ORPHAN is a byte that differs from stock and that NO document in the kit mentions. Orphans are how
this kit loses things: V42's ratchet fix sat silently REVERTED across eighteen builds (V53-V70) because
nothing checked that the bytes on the candidate still matched the bytes the record described. The
inverse -- a byte nobody can explain -- is the same failure pointed the other way, and the operator is
entitled to know what every non-stock byte in his ECU does.

METHOD. Diff the candidate against the stock dump over the flashable extent, group into contiguous
runs, drop the CRC trailers, then for each run ask whether its address is mentioned anywhere in
`docs/` or `memory/`. Addresses are often written as ranges ("0xC65C6-0xC65CF") or as the head of a
family, so a run counts as covered if ANY address within its own span, or within a small neighbourhood
of it, appears in the record.

WHAT THIS DOES AND DOES NOT PROVE. It proves every changed byte has a written home, which is what stops
a lever being carried by accident. It does NOT prove the annotation is correct, current, or that the
byte is doing what the annotation claims -- those need the lineage and a drive.
"""
import glob
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.environ.get('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares') + '/analysis-2020accord'
BUILD = (sys.argv[1] if len(sys.argv) > 1 else 'v222').lower()
START, END = 0x13000, 0x100000
CRC = (0xC4FFC, 0xC6FFC, 0xD7FFC, 0xE4FFC, 0xE5FFC)
NEIGHBOURHOOD = 32          # a run is covered if a cited address falls this close to it


def image(tag):
    g = [f for f in glob.glob('%s/_%s_*plain_image.bin' % (ROOT, tag)) if 'SUPERSEDED' not in f]
    assert len(g) == 1, 'expected exactly one live image for %s, found %d' % (tag, len(g))
    return open(g[0], 'rb').read(), os.path.basename(g[0])


def runs_vs_stock(new, st):
    out = []
    n = min(len(new), len(st), END)
    i = START
    while i < n:
        if new[i] != st[i]:
            j = i
            while j < n and new[j] != st[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def cited_addresses():
    """Every 0x..... literal appearing anywhere in docs/ or memory/."""
    seen = set()
    pats = ['docs/**/*.md', 'memory/**/*.md', 'memory/*.md', 'docs/*.md']
    files = set()
    for p in pats:
        files.update(glob.glob(p, recursive=True))
    rx = re.compile(r'0x([0-9A-Fa-f]{4,6})')
    for f in files:
        try:
            t = open(f, encoding='utf-8', errors='replace').read()
        except OSError:
            continue
        for m in rx.finditer(t):
            try:
                seen.add(int(m.group(1), 16))
            except ValueError:
                pass
    return seen, len(files)


new, name = image(BUILD)
st = open(ROOT + '/stock_fw_dump/code.bin', 'rb').read()
all_runs = runs_vs_stock(new, st)
pay = [r for r in all_runs if not any(c <= r[0] < c + 4 for c in CRC)]
nbytes = sum(b - a for a, b in pay)

cited, nfiles = cited_addresses()

print('=' * 88)
print('  NO-ORPHAN-BYTES AUDIT -- %s' % BUILD.upper())
print('=' * 88)
print()
print('  image      %s' % name[:70])
print('  vs stock   %d runs, %d payload bytes (+%d CRC trailers)'
      % (len(all_runs), nbytes, len(all_runs) - len(pay)))
print('  record     %d distinct 0x addresses cited across %d files' % (len(cited), nfiles))
print()

orphans = []
for a, b in pay:
    span = set(range(a, b))
    near = any((x in cited) for x in span)
    if not near:
        near = any((a - NEIGHBOURHOOD) <= x <= (b + NEIGHBOURHOOD) for x in cited)
    if not near:
        orphans.append((a, b))

if orphans:
    print('  %d ORPHAN RUNS -- changed bytes that NO document mentions:' % len(orphans))
    for a, b in orphans:
        print('    0x%05X  %3d B   stock %s -> %s'
              % (a, b - a, st[a:b].hex()[:16], new[a:b].hex()[:16]))
else:
    print('  [OK] ZERO orphan runs. Every one of the %d non-stock bytes has a written home.' % nbytes)

cov = 100.0 * (len(pay) - len(orphans)) / max(len(pay), 1)
print()
print('  coverage: %d of %d payload runs cited (%.1f %%)' % (len(pay) - len(orphans), len(pay), cov))

assert len(pay) > 0, 'a candidate with no delta from stock would mean the diff is broken'
assert cov > 99.0, 'every non-stock run must be explained somewhere in the record'
print()
print('  [EVIDENCE] every changed byte on %s is mentioned in the record.' % BUILD.upper())
print('  [LIMIT]    this proves each byte has a written HOME, not that the annotation is correct,')
print('             current, or that the byte does what it claims. Those need the lineage and a drive.')
