# -*- coding: utf-8 -*-
"""Archive the OLDEST blockquote blocks out of STATE.md, with byte accounting.

STATE.md is at 145.1 KB against a ~150 KB working target and a hard 256 KB Read cap. The blocks are
blockquote groups, newest prepended at the top, so the oldest sit at the bottom of the BLOCKS section.
Move whole groups only -- a half-moved block is worse than a large file.
"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

P = 'docs/STATE.md'
lines = io.open(P, encoding='utf-8').read().split('\n')
orig_bytes = len('\n'.join(lines).encode('utf-8'))

# BLOCKS section runs from the INDEX header to the first "EARLIER STATE ... ARCHIVED" header
start = next(i for i, l in enumerate(lines) if l.startswith('## 🗂 INDEX TO THE BLOCKS BELOW'))
end = next(i for i, l in enumerate(lines) if 'EARLIER STATE' in l and 'ARCHIVED' in l)

# group boundaries: a line starting '> ' whose predecessor is blank
starts = [i for i in range(start + 1, end)
          if lines[i].startswith('> ') and (i == 0 or lines[i - 1].strip() == '')]
if len(starts) < 6:
    print('  only %d blocks found -- not archiving' % len(starts)); raise SystemExit
groups = [(starts[k], (starts[k + 1] if k + 1 < len(starts) else end)) for k in range(len(starts))]
print('  %d blocks between lines %d and %d' % (len(groups), start + 1, end + 1))

TARGET = 55 * 1024   # raised 2026-08-30: STATE hit 176 KB after a long analysis run
moved, acc = [], 0
for a, b in reversed(groups):                       # oldest first
    if acc >= TARGET:
        break
    seg = '\n'.join(lines[a:b])
    moved.append((a, b)); acc += len(seg.encode('utf-8'))
if not moved:
    print('  nothing to move'); raise SystemExit
moved.sort()
lo, hi = moved[0][0], moved[-1][1]
assert all(moved[k][1] == moved[k + 1][0] for k in range(len(moved) - 1)), 'blocks not contiguous'

# NEVER a fixed name: the first version of this script OVERWROTE its own earlier archive,
# silently discarding 20 blocks (recovered from git). Pick the next free suffix instead.
import string
for _sfx in [''] + list(string.ascii_lowercase):
    AR = 'docs/archive/STATE-ARCHIVE-2026-08-30%s-auto.md' % _sfx
    if not os.path.exists(AR):
        break
else:
    raise SystemExit('no free archive name')
io.open(AR, 'w', encoding='utf-8').write(
    '# STATE ARCHIVE — blocks moved out of `docs/STATE.md` on 2026-08-30\n\n'
    'These are a RECORD of what was believed when written, not an instruction. They were moved to keep\n'
    '`STATE.md` under its working target; nothing here was retracted by the move. %d blocks, %.1f KB.\n\n'
    '---\n\n' % (len(moved), acc / 1024) + '\n'.join(lines[lo:hi]) + '\n')

PTR = ['', '## 📁 **EARLIER BLOCKS (%d) ARCHIVED 2026-08-30**' % len(moved), '',
       'Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its',
       'working target. **A record of what was believed then, not an instruction.** Nothing was retracted',
       'by the move.', '']
out = lines[:lo] + PTR + lines[hi:]
txt = '\n'.join(out)
io.open(P, 'w', encoding='utf-8').write(txt)

new_bytes = len(txt.encode('utf-8'))
ar_bytes = os.path.getsize(AR)
print('  moved   %d blocks, %.1f KB' % (len(moved), acc / 1024))
print('  STATE   %.1f KB -> %.1f KB' % (orig_bytes / 1024, new_bytes / 1024))
print('  archive %.1f KB' % (ar_bytes / 1024))
# accounting: nothing lost
assert new_bytes < orig_bytes, 'STATE did not shrink'
assert acc > 0.9 * (orig_bytes - new_bytes) - 512, 'byte accounting does not balance'
print('  [OK] whole groups only, accounting balances, archive written.')
