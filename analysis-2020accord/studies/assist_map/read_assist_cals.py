# -*- coding: utf-8 -*-
"""The base-assist map's output LAG -- and whether its pole differs engaged vs manual.

FUN_000352b4 ends with a first-order lag on the map output:

    iVar24 += (iVar20 - iVar24) * k >> 11        # gp-0x381c is the 32-bit state, 1 kHz
    where iVar20 = out * 0x80  and  k = clamp(uVar40, 2, 0xCC)

and k is SELECTED:

    bVar3  = (gp-0x6b62 return-centre != 0)
    uVar40 = cal(0xC6382)                 if (iVar14 != 0 && bVar3)      <- manual branch
           = LERP(0xC68FE.. -> 0xC6906..) otherwise                      <- engaged branch

Memory: return-centre is DEAD ENGAGED (0.0000 duty over 75,227 engaged frames) and live in
manual.  So the two arms can take different poles.  A pole that lands near 8.64 Hz in one
arm and not the other is exactly what an engaged-only torque resonance needs.

alpha = k/2048 per 1 kHz tick  =>  fc = -ln(1-alpha) * 1000 / (2*pi)
"""
import glob
import os
import re
import sys

import numpy as np

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
STOCK = os.path.join(ROOT, 'stock_fw_dump/code.bin')
FS = 1000.0


def u16(a, off):
    return int(a[off]) | (int(a[off + 1]) << 8)


def s16(a, off):
    v = u16(a, off)
    return v - 0x10000 if v >= 0x8000 else v


def fc_of(k):
    """Corner frequency of y += (x-y)*k/2048 sampled at 1 kHz."""
    al = k / 2048.0
    if al <= 0 or al >= 1:
        return float('nan')
    return -np.log(1 - al) * FS / (2 * np.pi)


def img(v):
    for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
        m = re.search(r'_v(\d+)', os.path.basename(p).lower())
        if m and int(m.group(1)) == v:
            return np.fromfile(p, dtype=np.uint8)
    return None


a = np.fromfile(STOCK, dtype=np.uint8)
print('STOCK  %s  (%d bytes)\n' % (os.path.basename(STOCK), len(a)))

print('slope cap   0xC6384 = %-6d  (Q10 => %.3f x)' % (u16(a, 0xC6384), u16(a, 0xC6384) / 1024.0))
k382 = u16(a, 0xC6382)
print('manual-arm lag coeff 0xC6382 = %-6d' % k382)
print('   clamped to [2,204] => k = %d   corner = %.2f Hz'
      % (min(max(k382, 2), 204), fc_of(min(max(k382, 2), 204))))

print('\nengaged-arm lag coeff: LERP  axis 0xC68FE.. -> values 0xC6906..')
print('%-8s %-10s %-10s %-8s %s' % ('i', 'axis', 'value', 'k clamp', 'corner Hz'))
for i in range(8):
    ax = u16(a, 0xC68FE + 2 * i)
    vl = u16(a, 0xC6906 + 2 * i)
    kk = min(max(vl, 2), 204)
    print('%-8d %-10d %-10d %-8d %.2f' % (i, ax, vl, kk, fc_of(kk)))

print('\nfull reachable corner range of the lag:')
print('  k=2   -> %.3f Hz      k=204 -> %.2f Hz' % (fc_of(2), fc_of(204)))
print('  the ratchet sits at 8.64 Hz; k for exactly that corner:')
al = 1 - np.exp(-2 * np.pi * 8.64 / FS)
print('  alpha = %.5f  =>  k = %.1f' % (al, al * 2048))

print('\nhas either cell ever moved?  (stock vs every build image)')
for addr, nm in ((0xC6384, 'slope cap'), (0xC6382, 'manual lag'), (0xC6200, 'input clamp')):
    vals = {}
    for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
        m = re.search(r'_v(\d+)', os.path.basename(p).lower())
        if not m:
            continue
        b = np.fromfile(p, dtype=np.uint8)
        if len(b) > addr + 1:
            vals.setdefault(u16(b, addr), []).append(int(m.group(1)))
    st = u16(a, addr)
    print('  0x%05X %-12s stock %-6d  values across %d images: %s'
          % (addr, nm, st, sum(len(v) for v in vals.values()),
             ', '.join('%d(x%d)' % (k, len(v)) for k, v in sorted(vals.items()))))

print('\nthe 10-knot map itself (X from gp-0x641e.., Y from gp-0x6444..) is built in RAM at')
print('runtime, so its knots are RAM-resident, not directly image-readable here.')
