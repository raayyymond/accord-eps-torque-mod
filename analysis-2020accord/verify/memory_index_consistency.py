# -*- coding: utf-8 -*-
"""MEMORY INDEX CONSISTENCY -- an index line must not sound more confident than the file it points at.

    python analysis-2020accord/verify/memory_index_consistency.py

WHY THIS EXISTS. `memory/MEMORY.md` and its seven continuation pages are loaded into context at the
START of every session. A wrong line there is read FIRST, and the retraction -- which usually lives in
STATE.md or in the memory file's own banner -- may never be reached. That is not hypothetical: on
2026-08-30 two index entries were found asserting claims that had been withdrawn, one of them added
earlier the same session by the agent that then withdrew it.

Hand-fixing works only when someone happens to look. This makes it mechanical.

THE CHECK. For every `[title](path)` pointer in the index pages:

  1. does the TARGET file carry a caution banner?      (DISPUTED / SUPERSEDED / RETRACTED / WITHDRAWN /
                                                        REFUTED / FALSIFIED / DO NOT SIZE A BUILD)
  2. does the INDEX LINE carry a caution marker?        (the same words, or a warning glyph)
  3. if (1) and not (2) -> MISMATCH. The index sounds confident about a file that is not.

It deliberately does NOT flag the reverse (cautious line, confident file): over-caution in an index is
harmless, and a line may be cautious for reasons the target does not state.

WHAT IT CANNOT DO. It compares TONE, not CONTENT. An index line can be perfectly worded and still
describe the wrong fact. This catches the mechanical failure -- a banner nobody propagated -- not a
wrong claim that everyone believed.
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BANNERS = ('DISPUTED', 'SUPERSEDED', 'RETRACTED', 'WITHDRAWN', 'REFUTED',
           'DO NOT SIZE A BUILD', 'STRUCK')
MARKERS = BANNERS + ('⚠', '\U0001f6d1', 'UNRESOLVED', 'OPEN', 'CORRECTION', 'NOT settled',
                     'weaker', 'do not', 'DO NOT')
LINK = re.compile(r'\[([^\]]{3,140})\]\(([^)]+\.md)\)')


def index_pages():
    out = []
    for p in ['memory/MEMORY.md'] + sorted(glob.glob('memory/MEMORY-PART*.md')):
        if os.path.exists(p):
            out.append(p)
    return out


def banner_of(path):
    """The first caution banner in the target's frontmatter or opening block, if any."""
    try:
        t = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    head = t[:1800]                      # frontmatter + opening banner region
    for b in BANNERS:
        if b in head.upper():
            return b
    return None


pages = index_pages()
print('=' * 92)
print('  MEMORY INDEX CONSISTENCY')
print('=' * 92)
print()
print('  index pages: %s' % ', '.join(os.path.basename(p) for p in pages))

checked = missing = mismatch = 0
problems = []
for page in pages:
    base = os.path.dirname(page)
    for line in io.open(page, encoding='utf-8', errors='replace').read().split('\n'):
        for title, rel in LINK.findall(line):
            if rel.startswith('http'):
                continue
            # the memory-writing instructions contain a literal template example
            if rel == 'file.md':
                continue
            # cross-links BETWEEN index pages are navigation, not claims: a continuation page
            # naturally contains the word SUPERSEDED because it holds superseded entries
            if os.path.basename(rel).upper().startswith('MEMORY'):
                continue
            tgt = os.path.normpath(os.path.join(base, rel))
            if not os.path.exists(tgt):
                missing += 1
                problems.append(('MISSING', os.path.basename(page), rel, ''))
                continue
            checked += 1
            b = banner_of(tgt)
            if not b:
                continue
            if not any(m.upper() in line.upper() for m in MARKERS):
                mismatch += 1
                problems.append(('TONE', os.path.basename(page), os.path.basename(tgt), b))

print('  pointers checked: %d   (targets missing: %d)' % (checked, missing))
print()
if problems:
    print('  %-9s %-18s %-52s %s' % ('kind', 'index page', 'target', 'banner'))
    for kind, page, tgt, b in problems:
        print('  %-9s %-18s %-52s %s' % (kind, page, tgt[:52], b))
else:
    print('  [OK] every pointer resolves, and no confident index line points at a bannered file.')

print()
assert missing == 0, '%d index pointers do not resolve' % missing
assert mismatch == 0, ('%d index lines sound confident about a file carrying a caution banner'
                       % mismatch)
print('  [EVIDENCE] %d pointers, all resolving, none over-confident.' % checked)
print('  [LIMIT]    this compares TONE, not CONTENT. A well-worded line can still state a wrong fact;')
print('             this catches an unpropagated banner, not a claim everyone believed.')
