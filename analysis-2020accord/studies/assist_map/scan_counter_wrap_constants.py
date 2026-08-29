# -*- coding: utf-8 -*-
"""Enumerate counter-wrap constants N in the stock image, WITHOUT pre-selecting 12.

V850 Format II:  hw = (reg2 << 11) | (op << 5) | imm5
    op 0x12 = add imm5,reg2      op 0x13 = cmp imm5,reg2
A modulo-N counter idiom is an `add 1,rX` and a `cmp N,rX` on the SAME register
within a short window.  Report the histogram over ALL N so 12 is not privileged.
"""
import io, os, sys, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IMG = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin'
b = io.open(IMG, 'rb').read()
print('image %s  %d bytes' % (os.path.basename(IMG), len(b)))

def hw(i):
    return b[i] | (b[i + 1] << 8)

def fmt2(h):
    """-> (op, reg2, imm5) """
    return ((h >> 5) & 0x3F, (h >> 11) & 0x1F, h & 0x1F)

ADD, CMP = 0x12, 0x13
WIN = 32                       # bytes either side

# index every add-1 by register
adds = collections.defaultdict(list)
cmps = []
for i in range(0, len(b) - 1, 2):
    op, r2, im = fmt2(hw(i))
    if r2 == 0:                # r0 is hardwired zero; never a counter
        continue
    if op == ADD and im == 1:
        adds[r2].append(i)
    elif op == CMP and 2 <= im <= 15:
        cmps.append((i, r2, im))

print('add 1,rX sites: %d   cmp imm5(2..15),rX sites: %d' % (
    sum(len(v) for v in adds.values()), len(cmps)))

hist = collections.Counter()
pairs = collections.defaultdict(list)
for ci, r2, n in cmps:
    near = [a for a in adds.get(r2, ()) if abs(a - ci) <= WIN]
    if near:
        hist[n] += 1
        pairs[n].append((ci, r2, min(near, key=lambda a: abs(a - ci))))

print('\nCOUNTER-WRAP HISTOGRAM  (add 1,rX paired with cmp N,rX within %d B)' % WIN)
print('   N   sites   f = 100/N Hz')
for n in range(2, 16):
    c = hist.get(n, 0)
    star = '  <-- in the measured ratchet range 6.8-10.4 Hz' if 9 <= n <= 15 and 6.8 <= 100.0 / n <= 10.4 else ''
    print('  %2d   %5d   %8.4f%s' % (n, c, 100.0 / n, star))

print('\nSITES for every N whose 100/N lands in the measured range:')
for n in sorted(pairs):
    f = 100.0 / n
    if not (6.8 <= f <= 10.4):
        continue
    print('  N=%d  (%.4f Hz)  %d site(s)' % (n, f, len(pairs[n])))
    for ci, r2, ai in pairs[n][:12]:
        print('     cmp 0x%x,r%d @ 0x%05X   add 1,r%d @ 0x%05X   (delta %+d)'
              % (n, r2, ci, r2, ai, ai - ci))
