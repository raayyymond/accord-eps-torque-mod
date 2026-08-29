# -*- coding: utf-8 -*-
"""Is the gp-0x6b26 lane's gate in FUN_00038148 ever CLOSED?

FUN_00038148 admits the term only while (gp-0x6b26 + 0x400) < 0x801, i.e. |x| <= 1024, and
ZEROES it otherwise (store-zero, not clamp).  But FUN_00036c12 clamps gp-0x6b26 to
+-cal[0xC407E] when it writes it.  If that clamp is inside +-1024 the gate can NEVER close
and w[3] is an unconditional multiplier.  Read both from stock AND from the flight image.
"""
import io, os, struct, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
imgs = {'stock': os.path.join(R, 'stock_fw_dump', 'code.bin'),
        'V173 ': glob.glob(os.path.join(R, '*v173*plain_image.bin'))[0],
        'V174 ': glob.glob(os.path.join(R, '*v174*plain_image.bin'))[0]}
u16 = lambda b, a: struct.unpack_from('<H', b, a)[0]
s16 = lambda b, a: struct.unpack_from('<h', b, a)[0]

CELLS = [(0xC407E, 'clamp on gp-0x6b26      (tp+0x507E)'),
         (0xC63A0, 'w[0] gp-0x6bd0  damper  (FLOWN V72=2048, V77=1024)'),
         (0xC63A2, 'w[1] gp-0x6bbe  viscous'),
         (0xC63A4, 'w[2] gp-0x6b46'),
         (0xC63A6, 'w[3] gp-0x6b26  INERTIA  <== THE VIRGIN LEVER'),
         (0xC63A8, 'w[4] gp-0x6b4e'),
         (0xC63AA, 'w[5] gp-0x6b4c'),
         (0xC63AC, 'EMA alpha on the sum'),
         (0xC63AE, 'scale into the residual LERP')]
print('%-9s %-46s %s' % ('addr', 'what', '  '.join('%-7s' % k for k in imgs)))
blobs = {k: io.open(v, 'rb').read() for k, v in imgs.items()}
for a, w in CELLS:
    print('0x%05X  %-46s %s' % (a, w, '  '.join('%-7d' % u16(b, a) for b in blobs.values())))

print('\nTHE GATE TEST')
for k, b in blobs.items():
    clamp = u16(b, 0xC407E)
    print('  %-6s clamp |gp-0x6b26| <= %-5d   gate admits |x| <= 1024   -> gate %s'
          % (k, clamp, 'ALWAYS OPEN (clamp is inside the window)' if clamp <= 1024
             else 'CAN CLOSE -- w[3] is conditionally inert'))

print('\nTHE INERTIA GAIN K, from the 0xCBE74 mode records (Y rows), stock vs flight')
for k, b in blobs.items():
    ptr = struct.unpack_from('<I', b, 0xCBE74)[0]
    print('  %-6s 0xCBE74[0] -> 0x%06X' % (k, ptr))
for nm, a in (('m24 MANUAL ', 0xD6A6C), ('m26 ENGAGED', 0xD7A5C), ('m27 ENGAGED', 0xD7A6C)):
    print('  %s Y = %s' % (nm, '   '.join(
        '%-7s[%s]' % (k, ','.join('%6d' % s16(b, a + 2 * i) for i in range(3)))
        for k, b in blobs.items())))

print('\nWHY w[3] IS FREQUENCY-SELECTIVE  (gp-0x6b26 = K * acceleration)')
print('  a sinusoid at f has |alpha| = (2*pi*f)^2 * |theta|, so the term scales as f^2:')
for f in (0.5, 1.0, 3.0, 8.17, 21.0):
    print('    %5.2f Hz   relative contribution %8.2fx   (vs 1 Hz)' % (f, (f / 1.0) ** 2))
print('  => cutting w[3] removes loop gain at 8.17 Hz %.1fx harder than at 1 Hz,'
      % ((8.17 / 1.0) ** 2))
print('     with NO filter and NO added phase lag anywhere.')
