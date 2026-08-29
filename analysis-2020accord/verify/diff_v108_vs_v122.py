# -*- coding: utf-8 -*-
"""The COMPLETE undocumented delta: V122 (flying) vs V108 (last build with a lineage row).

Four of V122's changes were found by inspecting cells I happened to look at. This enumerates
ALL of them, so nothing else is hiding. Decode each run as u16 / float32 / bytes and flag the
ones that look like SHAPE changes (a graduated series replaced by a constant), which is the
class that produced both of today's levers and that linear analysis cannot see.
"""
import io, os, struct, sys, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'


def img(v):
    g = [x for x in glob.glob(os.path.join(R, '*_' + v + '_*plain_image.bin'))
         if 'SUPERSEDED' not in x]
    if not g:
        return None
    return io.open(sorted(g)[0], 'rb').read()


a, b = img('v108'), img('v122')
stock = io.open(os.path.join(R, 'stock_fw_dump', 'code.bin'), 'rb').read()
START, END = 0x13000, 0x100000
diff = [x for x in range(START, END) if a[x] != b[x]]
runs = []
for x in diff:
    if runs and x <= runs[-1][1] + 3:          # coalesce runs separated by <=3 bytes
        runs[-1][1] = x + 1
    else:
        runs.append([x, x + 1])
crc = lambda lo: (lo & 0xFFF) >= 0xFFC
pay = [r for r in runs if not crc(r[0])]
print('V122 vs V108: %d differing bytes, %d runs (%d payload, %d CRC)'
      % (len(diff), len(runs), len(pay), len(runs) - len(pay)))
print('')
print('%-20s %4s  %s' % ('range', 'B', 'decode  (V108 -> V122, with stock for reference)'))
print('-' * 100)
f32 = lambda x, o: struct.unpack_from('<f', x, o)[0]
u16 = lambda x, o: struct.unpack_from('<H', x, o)[0]
for lo, hi in pay:
    n = hi - lo
    print('0x%05X..0x%05X %4d' % (lo, hi - 1, n))
    # float32 view when 4-aligned and the values look like sane floats
    if lo % 4 == 0 and n % 4 == 0 and n <= 64:
        vals = []
        for o in range(lo, hi, 4):
            try:
                va, vb, vs = f32(a, o), f32(b, o), f32(stock, o)
                vals.append((o, vs, va, vb))
            except Exception:
                vals = None
                break
        if vals and all(abs(v[2]) < 1e12 and abs(v[3]) < 1e12 for v in vals):
            for o, vs, va, vb in vals:
                print('        f32 0x%05X  stock %+11.4f   V108 %+11.4f -> V122 %+11.4f'
                      % (o, vs, va, vb))
            continue
    if n <= 8 and lo % 2 == 0:
        for o in range(lo, hi, 2):
            print('        u16 0x%05X  stock %6d   V108 %6d -> V122 %6d'
                  % (o, u16(stock, o), u16(a, o), u16(b, o)))
    else:
        print('        bytes  V108 %s' % a[lo:hi].hex())
        print('               V122 %s' % b[lo:hi].hex())
        print('               stk  %s' % stock[lo:hi].hex())
