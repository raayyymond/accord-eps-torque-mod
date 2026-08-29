# -*- coding: utf-8 -*-
"""Generate a MEASURED address index for V122 onward, straight from the images.

The lineage's critical function is `grep <address>` -> which build moved it.  V122-V196 have no
rows, so that grep silently returns nothing for every cell those builds touched -- which is how the
10x K1 and the 72 dead bytes stayed invisible.  Narrative rows cannot be reconstructed for builds
whose reasoning was never written down, but the ADDRESS INDEX can be measured exactly.
"""
import io, glob, os, re, struct, sys, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
st = io.open(A + '/stock_fw_dump/code.bin', 'rb').read()

imgs = {}
for p in glob.glob(A + '/*plain_image.bin'):
    if 'SUPERSEDED' in p:
        continue
    m = re.search(r'_v(\d+)_', os.path.basename(p))
    if m:
        imgs[int(m.group(1))] = p
vs = sorted(k for k in imgs if k >= 122)

# cell -> list of (build, prev_value, new_value)
hist = collections.defaultdict(list)
prev = None
for v in vs:
    b = io.open(imgs[v], 'rb').read()
    if prev is not None:
        pb, pv = prev
        d = [a for a in range(0x13000, 0x100000) if b[a] != pb[a] and (a & 0xFFF) < 0xFFC]
        runs = []
        for a in d:
            if runs and a == runs[-1][1]:
                runs[-1][1] = a + 1
            else:
                runs.append([a, a + 1])
        for lo, hi in runs:
            n = hi - lo
            if n <= 2:
                f = lambda x: struct.unpack_from('<h', x, lo)[0] if n == 2 else x[lo]
            elif n == 4:
                f = lambda x: round(struct.unpack_from('<f', x, lo)[0], 7)
            else:
                f = lambda x: ' '.join('%02x' % y for y in x[lo:min(hi, lo + 8)])
            hist[lo].append((v, f(pb), f(b), n, pv))
    prev = (b, v)

out = []
out.append('# BUILD LINEAGE — PART 5: V122 ONWARD, MEASURED FROM THE IMAGES')
out.append('')
out.append('🛑 **GENERATED, NOT NARRATED.** Every row below is a byte diff between two images on')
out.append('disk. It carries no reasoning — that lives in `docs/STATE.md` and the handoffs. What it')
out.append('restores is the lineage\'s ONE critical function: **`grep <address>` tells you which')
out.append('build moved a cell.** That grep silently returned nothing for V122–V196, which is how')
out.append('the 10× K1 dose and 72 dead bytes stayed invisible.')
out.append('')
out.append('⚠ **Not every build number has an image.** Gaps mean a row attributes a change to the')
out.append('next build that HAS an image, not necessarily the one that made it. Gaps in this range:')
out.append('122→124, 125→127, 127→129, 129→131, 131→137, 142→147, 161→164, 165→167, 177→179,')
out.append('181→183. Treat an attribution across a gap as "at or before this build".')
out.append('')
out.append('⚠ **Values shown are int16 for 2-byte cells, float32 for 4-byte, hex otherwise.**')
out.append('CRC trailers (offset ≥ 0xFFC in a page) are excluded.')
out.append('')
out.append('## Address index')
out.append('')
out.append('| cell | stock | changes (build: from → to) |')
out.append('|---|---|---|')
for lo in sorted(hist):
    ev = hist[lo]
    n = ev[0][3]
    if n <= 2:
        sv = struct.unpack_from('<h', st, lo)[0] if n == 2 else st[lo]
    elif n == 4:
        sv = round(struct.unpack_from('<f', st, lo)[0], 7)
    else:
        sv = ' '.join('%02x' % y for y in st[lo:min(lo + n, lo + 8)])
    ch = ' · '.join('**V%d**: %s → %s' % (v, a, b) for v, a, b, _, _ in ev)
    out.append('| `0x%05X` | `%s` | %s |' % (lo, sv, ch))
out.append('')
out.append('## Builds covered')
out.append('')
out.append('`' + '` `'.join('V%d' % v for v in vs) + '`')
out.append('')
out.append('%d distinct cells moved across %d builds.' % (len(hist), len(vs)))
io.open('docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md', 'w',
        encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('%d cells indexed across %d builds' % (len(hist), len(vs)))
print('%.1f KB' % (os.path.getsize('docs/BUILD-LINEAGE-PART5-V122-ONWARD-MEASURED.md') / 1024))
