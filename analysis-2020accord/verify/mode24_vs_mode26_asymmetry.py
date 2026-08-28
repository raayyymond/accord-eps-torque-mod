# -*- coding: utf-8 -*-
"""Is the engaged-only damper still a RELAY on the current builds?

In STOCK, mode 24 (manual) and mode 26 (engaged) are BYTE-IDENTICAL for all six factor
families -- Honda does not change the damper when LKAS engages. The entire engaged-only
damper is OUR edit, first armed at V74.

  STOCK..V73  m26 FactorC Y = [0, 234, 429, 908]     a RAMP starting at zero
  V74         [429, ...]
  V75/V81     [566, 234, 429, 908]
  V80         [566, 566, 566, 566]                   FLAT = a RELAY, not a ramp

accord-v80-damper-relay-and-grind1-inert: "The damper became a RELAY, grind #1 INERT to
dose. Restore the RAMP, don't merely lower k." That recommendation was made and, per the
memory, NOT applied. Check what V90..V121 actually carry.

Record layout: [u16 n][n * i16 X][n * i16 Y][u16 term], X at base+2, pointer array + mode*4.
"""
import glob, os, struct

FR = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord'
PTR = {'FactorC': 0xC9E9C, 'FactorE': 0xC9F84}
TAGS = ['_v90_', '_v96_', '_v100_', '_v103_', '_v104_', '_v107_', '_v108_', '_v111_',
        '_v112_', '_v116_', '_v120_', '_v121_']


def rec(d, ptr_arr, mode):
    base = int.from_bytes(d[ptr_arr + mode * 4: ptr_arr + mode * 4 + 4], 'little')
    if not (0 < base < len(d) - 64):
        return None
    n = int.from_bytes(d[base:base + 2], 'little')
    if not (1 <= n <= 16):
        return None
    X = [struct.unpack_from('<h', d, base + 2 + 2 * i)[0] for i in range(n)]
    Y = [struct.unpack_from('<h', d, base + 2 + 2 * n + 2 * i)[0] for i in range(n)]
    return X, Y


rows = [('STOCK', open(glob.glob(FR + '/**/code.bin', recursive=True)[0], 'rb').read())]
for t in TAGS:
    g = [x for x in glob.glob(os.path.join(FR, t + '*plain_image.bin')) if 'SUPERSEDED' not in x]
    if g:
        rows.append((t.strip('_').upper(), open(g[0], 'rb').read()))

for fam, ptr in PTR.items():
    print("\n%s  (ptr array 0x%05X)  --  mode 24 = MANUAL, mode 26 = ENGAGED" % (fam, ptr))
    print("  build     m24 Y                        m26 Y                        same?  flat?")
    for name, d in rows:
        a, b = rec(d, ptr, 24), rec(d, ptr, 26)
        if not a or not b:
            print("  %-8s  <unreadable>" % name)
            continue
        same = a[1] == b[1]
        flat = len(set(b[1])) == 1
        print("  %-8s  %-27s  %-27s  %-5s  %s"
              % (name, str(a[1]), str(b[1]), 'YES' if same else 'NO',
                 'RELAY' if flat else ('ramp' if b[1][0] == 0 else 'ramp+pedestal')))
print("\n  stock behaviour = m24 and m26 IDENTICAL and Y[0] == 0 (a ramp from zero).")
print("  'NO' + a non-zero Y[0] = an engaged-only damper that Honda does not ship.")
