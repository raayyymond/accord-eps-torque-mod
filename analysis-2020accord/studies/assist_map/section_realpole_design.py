# -*- coding: utf-8 -*-
"""Re-examine the r<=0.97 design: REAL poles mean overdamped, not ringing.

The frontier table printed a "ring Q" for every row, but that figure only means anything for
a COMPLEX pole pair.  Rows at r = 0.85, 0.90 and 0.97 printed ring f = 0.00 Hz, i.e. the
poles are REAL -- an overdamped cascade with no oscillation at all.  I nearly discarded a
viable design by reading Q off real poles.

Check the r<=0.97 solution properly: pole type, step response, pulse response, and what its
7-11 Hz attenuation does to the loop under the same anchoring used for the slope cap.
"""
import struct, sys
import numpy as np
from scipy import optimize
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FS = 1000.0
STOCK = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
BAND = np.linspace(7.0, 11.0, 13); FULL = np.arange(0.5, 49.0, 1.0)

def H(c, f):
    z = np.exp(2j*np.pi*np.asarray(f, float)/FS)
    return c['C_B4']*((1-c['C_AC']) + (c['C_B0']-c['C_A8'])*z)/(z**2 + c['C_A8']*z + c['C_AC']) + c['C_B4']
def poles(c): return np.roots([1.0, c['C_A8'], c['C_AC']])
def as_c(v):  return dict(C_A8=v[0], C_AC=v[1], C_B0=v[2], C_B4=v[3])
def f32(x):   return struct.unpack('<f', struct.pack('<f', float(x)))[0]
G0 = np.abs(H(STOCK, FULL))

def solve(rmax, force_real=True):
    def cost(v):
        c = as_c(v); p = poles(c); r = np.max(np.abs(p))
        if r >= rmax: return 1e6 + (r-rmax)*1e3
        if force_real and np.max(np.abs(np.imag(p))) > 1e-9: return 1e5
        gb = np.abs(H(c, BAND)); gf = np.abs(H(c, FULL))
        return (np.max(gb)**2*40 + (abs(H(c,0.5))-1)**2*500 + (abs(H(c,3.0))-1)**2*120
                + np.sum(np.maximum(0, gf/G0 - 1.02)**2)*40)
    best, bv = None, None
    for s in range(24):
        rng = np.random.default_rng(s)
        x0 = np.array([-1.5, 0.55, -1.9, 0.8]) + rng.normal(0, 0.25, 4)
        r = optimize.minimize(cost, x0, method='Nelder-Mead', options=dict(maxiter=2500))
        if best is None or r.fun < best: best, bv = r.fun, r.x
    return as_c([f32(v) for v in bv])

def tdom(c, kind='step', n=3000):
    x = np.ones(n); x[:200] = 0.0
    if kind == 'pulse':
        x = np.zeros(n); x[500:540] = 1.0
    s1 = s2 = 0.0; y = np.empty(n)
    a8, ac, b0, b4 = c['C_A8'], c['C_AC'], c['C_B0'], c['C_B4']
    for i in range(n):
        w = -ac*s1 - a8*s2 + b4*x[i]
        y[i] = min(max(s1 + b0*s2 + w, -12.0), 12.0)
        s1, s2 = s2, w
    return y

c = solve(0.97)
p = poles(c)
print('REAL-POLE design, r <= 0.97')
for k in ('C_A8','C_AC','C_B0','C_B4'):
    print('  %-5s %+0.9g   raw %08X' % (k, c[k], struct.unpack('<I', struct.pack('<f', c[k]))[0]))
print('  poles %s   real: %s   radius %.5f'
      % (np.round(p,5), bool(np.max(np.abs(np.imag(p))) < 1e-9), float(np.max(np.abs(p)))))

print('\n%-9s %-11s %-11s %s' % ('freq Hz','FLYING','DESIGN','ratio'))
for f in (0.5, 1, 2, 3, 5, 7, 8.64, 11, 15, 21, 30, 40):
    g0, g1 = abs(H(STOCK,f)), abs(H(c,f))
    print('%-9.2f %-11.4f %-11.4f %.3f%s' % (f, g0, g1, g1/g0,
          '   <- RATCHET' if abs(f-8.64)<.01 else ('   <- driver band' if f in (3,5) else '')))

for kind in ('step','pulse'):
    y0, y1 = tdom(STOCK, kind), tdom(c, kind)
    for nm, y in (('FLYING', y0), ('DESIGN', y1)):
        ss = float(np.mean(y[-200:])) if kind=='step' else 0.0
        e = y[200:] - ss
        zc = int(np.sum(np.diff(np.sign(e)) != 0))//2
        idx = np.where(np.abs(e) > 0.02*max(abs(ss),0.02))[0]
        print('  %-6s %-7s overshoot %6.1f%%  osc cycles %2d  settle %4.0f ms'
              % (kind, nm, 100*(y[200:].max()-ss)/max(abs(ss),1e-9) if kind=='step' else 0,
                 zc, (idx[-1]/FS*1000) if len(idx) else 0))

gb = np.abs(H(c, BAND)).max(); g864 = abs(H(c, 8.64))
s_eff = 2.000 * g864
L = 0.825 + s_eff; P = 0.9300/2.825
print('\nLOOP EFFECT, same anchoring as the slope cap (P.L real-positive, Q_eff/Q_pass=14.3)')
print('  filter at 8.64 Hz: %.4f -> effective map s = %.3f (was %.3f)'
      % (g864, s_eff, 2.000*abs(H(STOCK,8.64))))
print('  |L| %.3f -> P.L %.4f -> |1-P.L| %.4f -> Q ratio %.2f  = %.1fx MORE DAMPED than stock'
      % (L, P*L, abs(1-P*L), 1/abs(1-P*L), 14.29/(1/abs(1-P*L))))
print('  DC gain %.4f   worst 7-11 Hz %.4f' % (abs(H(c,0.5)), gb))
