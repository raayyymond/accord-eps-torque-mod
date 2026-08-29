# -*- coding: utf-8 -*-
"""With Honda's notch FIXED, what is the best ratchet attenuation per ms of added lag?

Now that the structure is known to separate -- C_B0 sets the notch, C_A8/C_AC set the poles,
C_B4 sets DC -- the design reduces to choosing ONE real pole pair.  Sweep it and find the
efficient frontier of 8.64 Hz attenuation against added group delay, which is the felt cost.

V173 picked poles (0.97, 0.475) because they were V172's.  That was inherited, not chosen.
This asks whether a better pair exists at the same or lower lag.
"""
import sys, struct
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 1000.0
FLY = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
B0 = FLY['C_B0']

def f32(x): return struct.unpack('<f', struct.pack('<f', float(x)))[0]
def mk(p1, p2):
    A8 = f32(-(p1+p2)); AC = f32(p1*p2)
    return dict(C_A8=A8, C_AC=AC, C_B0=f32(B0), C_B4=f32((1+A8+AC)/(2+B0)))
def H(c, f):
    z = np.exp(2j*np.pi*np.asarray(f, float)/FS)
    return c['C_B4']*(z**2 + c['C_B0']*z + 1)/(z**2 + c['C_A8']*z + c['C_AC'])
def gd(c, f=0.5, df=0.05):
    p = np.unwrap(np.angle(H(c, np.array([f-df, f, f+df]))))
    return -(p[2]-p[0])/(2*np.pi*2*df)*1000.0

gd0 = gd(FLY)
fs = np.arange(0.5, 499.5, 0.5)
rows = []
for p1 in np.arange(0.90, 0.995, 0.005):
    for p2 in np.arange(0.0, 0.96, 0.05):
        c = mk(p1, p2)
        lag = gd(c) - gd0
        if lag > 60: continue
        g864 = abs(H(c, 8.64)); g3 = abs(H(c, 3.0)); dc = abs(H(c, 0.5))
        if dc < 0.97 or dc > 1.02: continue
        if np.abs(H(c, fs)).max() > 1.005: continue
        rows.append((lag, g864, g3, dc, p1, p2, abs(H(c, 21.0))))
rows.sort()
# efficient frontier: best (lowest) g864 seen so far as lag increases
print('EFFICIENT FRONTIER -- best 8.64 Hz attenuation at each lag budget')
print('%-9s %-10s %-9s %-8s %-14s %s' % ('lag ms', '8.64 Hz', '3 Hz', 'DC', 'poles', '21 Hz'))
best = 9e9
front = []
for lag, g, g3, dc, p1, p2, g21 in rows:
    if g < best - 1e-4:
        best = g; front.append((lag, g, g3, dc, p1, p2, g21))
for lag, g, g3, dc, p1, p2, g21 in front:
    mark = '   <- V173 is here' if abs(p1-0.97) < 0.003 and abs(p2-0.475) < 0.03 else ''
    print('%-9.1f %-10.4f %-9.4f %-8.4f %-14s %.4f%s'
          % (lag, g, g3, dc, '%.3f/%.2f' % (p1, p2), g21, mark))
v173 = mk(0.97, 0.475)
print('\nV173 as built: lag %+.1f ms  8.64 Hz %.4f  3 Hz %.4f  21 Hz %.4f'
      % (gd(v173)-gd0, abs(H(v173, 8.64)), abs(H(v173, 3.0)), abs(H(v173, 21.0))))
same = [r for r in front if abs(r[0] - (gd(v173)-gd0)) < 3.0]
if same:
    b = min(same, key=lambda r: r[1])
    print('best on the frontier at the SAME lag: 8.64 Hz %.4f with poles %.3f/%.2f'
          % (b[1], b[4], b[5]))
    print('  => V173 %s' % ('is at/near the frontier' if b[1] >= abs(H(v173,8.64))-0.02
                            else 'is BEATEN by %.4f vs %.4f' % (b[1], abs(H(v173,8.64)))))
