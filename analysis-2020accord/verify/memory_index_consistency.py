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


# The AUTO-MEMORY index lives outside the repo and is loaded into context at session start, exactly
# like the project index -- so it needs the same check. It was NOT scanned until 2026-08-30, when 89
# of its entries had their descriptive tails trimmed to get the file under its load limit; any
# caution marker living in a trimmed tail would have vanished silently.
AUTO = os.path.expanduser(
    '~/.claude/projects/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/memory/MEMORY.md')


def index_pages():
    out = []
    for p in ['memory/MEMORY.md'] + sorted(glob.glob('memory/MEMORY-PART*.md')):
        if os.path.exists(p):
            out.append(p)
    if os.path.exists(AUTO):
        out.append(AUTO)
    return out


def banner_of(path):
    """The first caution banner in the target's opening BODY block, if any.

    TWO THINGS THIS DELIBERATELY DOES NOT MATCH, both found on 2026-08-30 when the auto-memory index
    was first scanned:

      1. YAML FRONTMATTER. A `description:` that REPORTS a refutation ("the belief is refuted") is
         describing a finding, not flagging the file. Frontmatter is stripped before scanning.
      2. LOWERCASE PROSE. The kit's banners are written UPPERCASE ("SUPERSEDED", "REFUTED"), usually
         after a glyph. Matching case-insensitively turns every ordinary sentence containing the word
         "corrected" or "disputed" into a banner. The match is now case-SENSITIVE.

    Both produced the same false positive: a correct, confident index line reported as over-confident.
    """
    try:
        t = io.open(path, encoding='utf-8', errors='replace').read()
    except OSError:
        return None
    if t.startswith('---'):              # strip YAML frontmatter
        end = t.find('\n---', 3)
        if end != -1:
            t = t[end + 4:]
    # A banner sits ABOVE the first section heading. Scanning a fixed 1800-char window instead
    # caught '## A HYPOTHESIS OF MINE THAT WAS REFUTED, AND WHY' -- a section documenting a refuted
    # hypothesis inside a file whose own result stands (V88). Cut at the first section heading.
    cut = t.find('\n## ')
    head = (t if cut == -1 else t[:cut])[:1200]
    for b in BANNERS:
        if b in head:                    # case-SENSITIVE: banners are uppercase by convention
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
