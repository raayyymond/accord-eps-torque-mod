# -*- coding: utf-8 -*-
"""EVERY CELL ON V234 THAT DIFFERS FROM STOCK -- the close-out contract, run as a check.

Finding the Lever B defect by hand-checking one cell means the others were never checked that way.
This enumerates every differing run against STOCK (not against the car), classifies it, and prints it
so each can be adjudicated against the record.
"""
import glob, os, struct, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = os.environ['ACCORD_FIRMWARE_ROOT'] + '/analysis-2020accord/'
def im(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
stock = open(R+'stock_fw_dump/code.bin','rb').read()
v234, car = im('_v235_'), im('_v122_')
print('  stock %d B   V234 %d B   car %d B' % (len(stock), len(v234), len(car)))
n = min(len(stock), len(v234))
d = [i for i in range(0x13000, min(n, 0x100000)) if stock[i] != v234[i]]
runs = []
for i in d:
    if runs and i == runs[-1][1]+1: runs[-1][1] = i
    else: runs.append([i, i])
print('  %d differing bytes vs STOCK in %d runs' % (len(d), len(runs)))
print()
def show(b, o, L):
    if L == 1: return '%d' % b[o]
    if L == 2: return '%d' % struct.unpack_from('<H', b, o)[0]
    if L == 4:
        f = struct.unpack_from('<f', b, o)[0]
        return ('%.6g' % f) if (f == f and abs(f) < 1e6) else ('0x%08x' % struct.unpack_from('<I', b, o)[0])
    return b[o:o+L].hex()[:16]
print('  %-10s %-4s %-14s %-14s %-14s %s' % ('addr','len','stock','CAR','V234','same as car?'))
CRC = lambda a: (a & 0xFFF) >= 0xFFC
for lo, hi in runs:
    L = hi-lo+1
    tag = 'CRC trailer' if CRC(lo) else ''
    same = 'yes' if bytes(car[lo:hi+1]) == bytes(v234[lo:hi+1]) else '** DIFFERS **'
    print('  0x%-8X %-4d %-14s %-14s %-14s %s %s'
          % (lo, L, show(stock,lo,L), show(car,lo,L), show(v234,lo,L), same, tag))
print()
nc = [r for r in runs if not CRC(r[0])]
diff_car = [r for r in nc if bytes(car[r[0]:r[1]+1]) != bytes(v234[r[0]:r[1]+1])]
print('  %d non-CRC runs differ from stock; %d of those ALSO differ from the car.' % (len(nc), len(diff_car)))
print('  The %d that match the car are what he already drives -- they need no new justification.' % (len(nc)-len(diff_car)))
