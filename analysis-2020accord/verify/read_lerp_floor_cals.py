# -*- coding: utf-8 -*-
"""Do the LERP Y-floors act at SMALL signal (a real amplitude-selective lever) or large?

From FUN_000389ec's per-knot loop:
    if cal[tp+0x713e] <= X_knot  and  X_prev < cal[tp+0x713e]:   Y = max(Y, cal[tp+0x717a])
    elif X_prev < cal[tp+0x7140]:                                 Y = max(Y, cal[tp+0x717c])
  both only armed when  uVar48 > cal[tp+0x72d8]   (uVar48 derives from gp-0x6a64)
tp = 0xBF000 -- guard the recurring off-by-0x1000: tp+0x713e is 0xC613E, NOT 0xC713E.
Also check whether these cells are VIRGIN across the flown builds.
"""
import io, os, struct, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
TP = 0xBF000
imgs = [('stock', os.path.join(R, 'stock_fw_dump', 'code.bin'))]
for v in ('v122', 'v158', 'v173', 'v175'):
    g = [x for x in glob.glob(os.path.join(R, '*%s*plain_image.bin' % v)) if 'SUPERSEDED' not in x]
    if g:
        imgs.append((v.upper(), sorted(g)[0]))
blobs = [(n, io.open(p, 'rb').read()) for n, p in imgs]
u16 = lambda b, a: struct.unpack_from('<H', b, a)[0]
s16 = lambda b, a: struct.unpack_from('<h', b, a)[0]

CELLS = [(0x713e, 'X threshold A  (arms floor A)'),
         (0x7140, 'X threshold B  (arms floor B)'),
         (0x717a, 'Y FLOOR A'),
         (0x717c, 'Y FLOOR B'),
         (0x72d8, 'arm gate on gp-0x6a64'),
         (0x7178, 'per-knot output clamp')]
print('tp = 0x%05X   (tp+0x713e = 0x%05X -- NOT 0xC713E)' % (TP, TP + 0x713e))
print('\n%-8s %-30s %s' % ('addr', 'what', '  '.join('%-8s' % n for n, _ in blobs)))
for off, what in CELLS:
    a = TP + off
    vals = [u16(b, a) for _, b in blobs]
    virgin = len(set(vals)) == 1
    print('0x%05X %-30s %s   %s' % (a, what, '  '.join('%-8d' % v for v in vals),
                                    'VIRGIN' if virgin else '*** MOVED ***'))

b = blobs[0][1]
tA, tB = u16(b, TP + 0x713e), u16(b, TP + 0x7140)
fA, fB = u16(b, TP + 0x717a), u16(b, TP + 0x717c)
print('\nINTERPRETATION')
print('  The X axis of this LERP is the |residual|, and the knots are built as')
print('  X[i] = (raw << 10) / scale, with scale = 1024 (unity) if the inputs are constant.')
print('  So the thresholds are directly comparable to the residual clamp of 8192 (0xC6200):')
for nm, t in (('A', tA), ('B', tB)):
    print('    threshold %s = %-6d  = %.1f %% of the +-8192 residual clamp' % (nm, t, 100.0 * t / 8192))
print('  floors:  A = %d   B = %d   (clamp on gp-0x6b70 is +-8192)' % (fA, fB))
print('\n  => %s' % ('SMALL-SIGNAL: the floors arm low on the residual axis, so lowering them cuts '
                     'small-signal gain -- the amplitude-selective lever EXISTS'
                     if max(tA, tB) < 0.25 * 8192 else
                     'NOT small-signal: the thresholds sit high on the residual axis, so these floors '
                     'shape LARGE-signal response -- NOT the amplitude-selective lever'))
