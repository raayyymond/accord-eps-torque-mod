#!/usr/bin/env python3
"""Stage-2 LERP: build the exact 10-point table at creep and invert it.

Mirrors the decompiled integer arithmetic, address-annotated.
  FUN_000382d8 @0x382d8  speed-blend of two flash records -> gp-0x6350[] / gp-0x630c[]
  FUN_000389ec @0x389ec  rescale by K1/K2 (both PROVEN == 1024) -> gp-0x64b8[] / gp-0x641c[]
  FUN_00038148 @0x38148  gp-0x6b70 = sign(iVar6) * LERP(|iVar6| * 0xC63AE >> 10), clamp +-0xC6200
"""
import struct

B = open(r'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin','rb').read()
u16 = lambda a: struct.unpack_from('<H', B, a)[0]
s16 = lambda a: struct.unpack_from('<h', B, a)[0]
u32 = lambda a: struct.unpack_from('<I', B, a)[0]

BRK_PTRS = 0xCC9FC
REC_PTRS = [0xC7B40, 0xC7C28, 0xC7D10, 0xC7DF8, 0xC7EE0, 0xC7FC8, 0xC80B0]
K1 = K2 = 1024                       # gp-0x6982 / gp-0x6984, boot 1024, zero writers
X9_FLOOR = u16(0xC613C)              # 14490   tp+0x713C
Y_CEIL   = u16(0xC6200)              # 8192    tp+0x7200
IN_SCALE = u16(0xC63AE)              # 1024    tp+0x73AE

def cap_for_speed(sp):
    """FUN_000389ec 0x389ec-0x38a5c: speed-scheduled X-axis cap (uVar46)."""
    X = [u16(0xC669A + 2*i) for i in range(7)]
    Y = [u16(0xC66A8 + 2*i) for i in range(7)]
    if sp <= X[0]:  return Y[0]
    if sp >= X[6]:  return u16(0xC66B4)
    for i in range(1, 7):
        if X[i] > sp:
            return (Y[i] - Y[i-1]) * (sp - X[i-1]) // (X[i] - X[i-1]) + Y[i-1]
    return Y[6]

def records(mode):
    brk = u32(BRK_PTRS + mode*4)
    brks = [s16(brk + 2*i) for i in range(7)]
    recs = []
    for base in REC_PTRS:
        p = u32(base + mode*4)
        recs.append(dict(cnt=s16(p),
                         X=[s16(p + 2 + 2*i) for i in range(9)],
                         Y=[s16(p + 0x14 + 2*i) for i in range(9)]))
    return brks, recs

def build(mode, sp_counts):
    """Returns the 10-point (X, Y) table actually in gp-0x64b8[] / gp-0x641c[]."""
    brks, recs = records(mode)
    # 0x38590..0x385c8 : k = first index with brk[k] > speed
    k = 0
    while k < 7 and brks[k] <= sp_counts:
        k += 1
    if 1 <= k <= 6:                                   # 0x385ea..0x38648 integer blend
        lo, hi = recs[k-1], recs[k]
        num, den = sp_counts - brks[k-1], brks[k] - brks[k-1]
        Xs = [lo['X'][i] + ((hi['X'][i] - lo['X'][i]) * num) // den for i in range(9)]
        Ys = [lo['Y'][i] + ((hi['Y'][i] - lo['Y'][i]) * num) // den for i in range(9)]
    else:
        r = recs[0] if k == 0 else recs[6]
        Xs, Ys = list(r['X']), list(r['Y'])
    for i in range(1, 9):                             # 0x388c4+ : 8 unconditional rungs
        Ys[i] = max(Ys[i], Ys[i-1])
    # FUN_000389ec: K1/K2 are 1024 -> identity; X[0]=Y[0]=0 (0x38d1c/0x38d22)
    Xr = [(x << 10) // K1 for x in Xs]                # 0x38c64 shl / 0x38c6a divq
    Yr = [(y * K2) >> 10 for y in Ys]                 # 0x38c7e mul / 0x38c84 sar
    cap = cap_for_speed(sp_counts)
    X = [0]*10; Y = [0]*10
    trunc = None
    for i in range(1, 9):
        if Xr[i] < cap:
            X[i] = Xr[i]; Y[i] = min(max(Yr[i], Y[i-1]), Y_CEIL)
        else:
            X[i] = cap
            Y[i] = min(max(Yr[i-1] + (Yr[i]-Yr[i-1])*(cap-Xr[i-1])//(Xr[i]-Xr[i-1]), Y[i-1]), Y_CEIL)
            trunc = i
            for j in range(i+1, 9): X[j] = X[i]; Y[j] = Y[i]
            break
    X[9] = max(X9_FLOOR, X[8]); Y[9] = Y_CEIL
    return X, Y, cap, trunc

def lerp(X, Y, x):
    if x <= X[0]: return Y[0]
    if x >= X[9]: return Y[9]
    for i in range(1, 10):
        if X[i] > x:
            return (Y[i]-Y[i-1]) * (x - X[i-1]) // (X[i]-X[i-1]) + Y[i-1]
    return Y[9]

def invert(X, Y, y):
    """smallest |iVar6| producing LERP >= y (float, for readability)"""
    if y <= 0: return 0.0
    for i in range(1, 10):
        if Y[i] >= y:
            if Y[i] == Y[i-1]: return float(X[i-1])
            return X[i-1] + (y - Y[i-1]) * (X[i]-X[i-1]) / (Y[i]-Y[i-1])
    return float('inf')

MEAS = [('p50', 320), ('p90', 2534), ('p99', 3059), ('max', 3187)]

print('cals: X9_FLOOR(0xC613C)=%d  Y_CEIL(0xC6200)=%d  IN_SCALE(0xC63AE)=%d  K1=K2=%d' %
      (X9_FLOOR, Y_CEIL, IN_SCALE, K1))
print('LERP index = |iVar6| * %d >> 10 = |iVar6| exactly\n' % IN_SCALE)

for mode, tag in ((24, 'MANUAL'), (26, 'ENGAGED')):
    for kmh in (0.0, 3.0, 6.6):
        sp = int(round(kmh*64))
        X, Y, cap, tr = build(mode, sp)
        print('mode %d (%s)  %.1f km/h (%d counts)  Xcap=%d%s' %
              (mode, tag, kmh, sp, cap, '  TRUNC@k=%d' % tr if tr else ''))
        print('   X = %s' % X)
        print('   Y = %s' % Y)
        fp = [(Y[i]-Y[i-1])/(X[i]-X[i-1]) if X[i] != X[i-1] else float('nan') for i in range(1,10)]
        print("   f' = %s" % ' '.join('%.3f' % v for v in fp))
        print('   inverted: ' + '  '.join('%s |6b70|=%d -> |iVar6|=%.0f' % (n, v, invert(X, Y, v))
                                          for n, v in MEAS))
        print('   sanity: LERP(X[k])=Y[k] for all k: %s' %
              all(lerp(X, Y, X[k]) == Y[k] for k in range(10)))
        print()
