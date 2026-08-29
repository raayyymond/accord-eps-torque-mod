# -*- coding: utf-8 -*-
"""The second-order float section inside the base-assist map, across builds.

FUN_000352b4 ends with, gated on cal(0xC649B)==1 AND cal(0xC64FA) <= gp-0x671a:

    s2 = gp-0x3818
    w  = -(C_AC*gp-0x3814 - -(s2*C_A8 - (iVar34/1024)*C_B4))
    y  = gp-0x3814 + s2*C_B0 + w
    gp-0x3814 = s2 ;  gp-0x3818 = w ;  clamp y to +/-12.0 ;  iVar34 = y*1024

Two states, two feedback coefficients -> a genuine second-order recursive section, in
float, on the DOMINANT torque-fed lane.  Both its coefficients (0xC60A8..0xC60B4) and its
enable byte (0xC649B) are inside the 278 bytes this kit changed across V91-V122, so they
can be scored directly against the measured ratchet.
"""
import glob
import os
import re
import struct
import sys

import numpy as np
from scipy import stats

os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
COEF = {'C_A8 0xC60A8': 0xC60A8, 'C_AC 0xC60AC': 0xC60AC,
        'C_B0 0xC60B0': 0xC60B0, 'C_B4 0xC60B4': 0xC60B4}
ENABLE = 0xC649B
GATE = 0xC64FA
# measured cs_tq excess from the validated estimator
ROUTES = [('r78', 91, 9.8, 6.1), ('r7e', 96, 16.5, 28.9), ('r7f', 96, 32.9, 14.3),
          ('r96', 102, 49.4, 248.2), ('ra4', 104, 15.8, 54.7), ('ra6', 106, 67.8, 25.3),
          ('r1e', 107, 28.8, 27.7), ('r22', 112, 35.8, 15.0), ('r24', 122, 33.2, 14.0)]


def f32(a, off):
    return struct.unpack('<f', a[off:off + 4].tobytes())[0]


def img(v):
    for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
        m = re.search(r'_v(\d+)', os.path.basename(p).lower())
        if m and int(m.group(1)) == v:
            return np.fromfile(p, dtype=np.uint8)
    return None


st = np.fromfile(os.path.join(ROOT, 'stock_fw_dump/code.bin'), dtype=np.uint8)
print('STOCK values')
for nm, off in COEF.items():
    print('  %-14s = %-14.8g  (raw %08X)' % (nm, f32(st, off), int.from_bytes(st[off:off+4].tobytes(), 'little')))
print('  enable 0xC649B = %d      gate 0xC64FA = %d' % (st[ENABLE], st[GATE]))

print('\nacross the nine scored builds:')
print('%-6s %-6s %-8s %-6s %-12s %-12s %-12s %-12s %s'
      % ('route', 'build', 'enable', 'gate', 'C_A8', 'C_AC', 'C_B0', 'C_B4', 'RATCHET'))
rows = []
for tag, v, er, eg in ROUTES:
    a = img(v)
    if a is None:
        print('%-6s V%-5d -- no image' % (tag, v))
        continue
    c = [f32(a, COEF[k]) for k in COEF]
    print('%-6s V%-5d %-8d %-6d %-12.6g %-12.6g %-12.6g %-12.6g %.1f'
          % (tag, v, a[ENABLE], a[GATE], c[0], c[1], c[2], c[3], er))
    rows.append((a[ENABLE], a[GATE], c, er, eg))

en = np.array([r[0] for r in rows], float)
ga = np.array([r[1] for r in rows], float)
er = np.array([r[3] for r in rows], float)
eg = np.array([r[4] for r in rows], float)
print('\ncorrelations with the measured symptoms:')
for nm, x in (('enable 0xC649B', en), ('gate 0xC64FA', ga)):
    if len(set(x)) < 2:
        print('  %-16s constant at %g across all nine -- cannot correlate' % (nm, x[0]))
        continue
    r1, p1 = stats.spearmanr(x, er)
    r2, p2 = stats.spearmanr(x, eg)
    print('  %-16s vs RATCHET rho %+.2f p %.3f   vs GRIND rho %+.2f p %.3f' % (nm, r1, p1, r2, p2))
for i, k in enumerate(COEF):
    x = np.array([r[2][i] for r in rows], float)
    if len(set(np.round(x, 10))) < 2:
        print('  %-16s constant at %.8g across all nine' % (k, x[0]))
        continue
    r1, p1 = stats.spearmanr(x, er)
    print('  %-16s vs RATCHET rho %+.2f p %.3f' % (k, r1, p1))

print('\nfull history of the enable byte and the coefficients over every image:')
for nm, off, w in (('enable 0xC649B', ENABLE, 1), ('gate 0xC64FA', GATE, 1)):
    vals = {}
    for p in glob.glob(os.path.join(ROOT, '*plain_image*.bin')):
        m = re.search(r'_v(\d+)', os.path.basename(p).lower())
        if not m:
            continue
        b = np.fromfile(p, dtype=np.uint8)
        vals.setdefault(int(b[off]), []).append(int(m.group(1)))
    print('  %-16s stock %-4d  %s' % (nm, st[off],
          ' · '.join('%d on %d builds' % (k, len(v)) for k, v in sorted(vals.items()))))
