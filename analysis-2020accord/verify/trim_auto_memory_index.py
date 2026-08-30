# -*- coding: utf-8 -*-
"""Trim auto-memory MEMORY.md index lines to <=200 chars.

The file is loaded into context at session start and is over the 24.4 KB limit, so it loads TRUNCATED
-- entries at the bottom are silently invisible. Every line here is a POINTER; the detail already
lives in the topic file it points at. So the fix is to cut the trailing prose after the link, never
the link itself.

Cuts only the em-dash tail AFTER the closing paren of the markdown link, and only on lines over the
cap. The title, the link target, the glyphs and the star rating are all preserved exactly.
"""
import io, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

P = os.path.expanduser(
    '~/.claude/projects/C--Users-dudei-Desktop-Projects-accord-eps-torque-mod/memory/MEMORY.md')
CAP = 140

lines = io.open(P, encoding='utf-8').read().split('\n')
before = sum(len(l.encode('utf-8')) for l in lines)
LINK = re.compile(r'^(.*?\]\([^)]+\))(.*)$')

out, trimmed = [], 0
for ln in lines:
    if len(ln) <= CAP or '](' not in ln:
        out.append(ln)
        continue
    m = LINK.match(ln)
    if not m:
        out.append(ln)
        continue
    head, tail = m.group(1), m.group(2)
    if len(head) >= CAP:          # the title itself is already at/over the cap: leave it alone
        out.append(ln)
        continue
    room = CAP - len(head)
    # keep as much of the tail as fits, cutting at a word boundary
    t = tail[:room]
    if len(tail) > room:
        cut = t.rfind(' ')
        t = (t[:cut] if cut > 12 else t).rstrip(' —-,;:') + '…'
    out.append(head + t)
    trimmed += 1

txt = '\n'.join(out)
io.open(P, 'w', encoding='utf-8').write(txt)
after = len(txt.encode('utf-8'))
over = [l for l in out if len(l) > CAP]
print('  lines            %d' % len(out))
print('  trimmed          %d' % trimmed)
print('  size             %.1f KB -> %.1f KB  (limit 24.4 KB)' % (before / 1024.0, after / 1024.0))
print('  still over %d ch %d  (titles alone exceed the cap; links intact)' % (CAP, len(over)))
assert all('](' in l or not l.strip().startswith('- ') for l in out), 'a link was destroyed'
print('  [OK] every entry still carries its link.')
