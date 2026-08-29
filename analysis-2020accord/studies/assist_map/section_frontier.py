# -*- coding: utf-8 -*-
"""Attenuation-vs-ringing frontier, all analytic so it actually finishes.

Settling is computed from the pole radius rather than simulated: |r|^n = 0.02 at 1 kHz
gives t_2% = ln(0.02)/ln(r) ms.  Ring Q = 1/(2(1-r)), ring freq = angle(p)*FS/2pi.
"""
import struct, sys
import numpy as np
from scipy import optimize
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FS = 1000.0
STOCK = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
BAND = np.linspace(7.0, 11.0, 13)
FULL = np.arange(0.5, 49.0, 1.0)

def H(c, f):
    z = np.exp(2j*np.pi*np.asarray(f, float)/FS)
    return c['C_B4']*((1-c['C_AC']) + (c['C_B0']-c['C_A8'])*z)/(z**2 + c['C_A8']*z + c['C_AC']) + c['C_B4']
def poles(c): return np.roots([1.0, c['C_A8'], c['C_AC']])
def as_c(v):  return dict(C_A8=v[0], C_AC=v[1], C_B0=v[2], C_B4=v[3])
def f32(x):   return struct.unpack('<f', struct.pack('<f', float(x)))[0]
G0 = np.abs(H(STOCK, FULL))

def solve(rmax, seeds=10, it=1200):
    def cost(v):
        c = as_c(v)
        r = np.max(np.abs(poles(c)))
        if r >= rmax: return 1e6 + (r-rmax)*1e3
        gb = np.abs(H(c, BAND)); gf = np.abs(H(c, FULL))
        return (np.max(gb)**2*40 + (abs(H(c,0.5))-1)**2*500 + (abs(H(c,3.0))-1)**2*120
                + np.sum(np.maximum(0, gf/G0 - 1.02)**2)*40)
    best, bv = None, None
    for s in range(seeds):
        rng = np.random.default_rng(s)
        x0 = np.array([-1.5, 0.7, -1.9, 0.8]) + rng.normal(0, 0.3, 4)
        r = optimize.minimize(cost, x0, method='Nelder-Mead', options=dict(maxiter=it))
        if best is None or r.fun < best: best, bv = r.fun, r.x
    return as_c([f32(v) for v in bv])

gf0 = np.abs(H(STOCK, BAND)).max()
print('%-9s %-13s %-12s %-11s %-9s %-11s %s'
      % ('r limit', 'best 7-11 Hz', 'attenuation', 'ring f Hz', 'ring Q', 'settle ms', 'DC'))
for rmax in (0.85, 0.90, 0.94, 0.97, 0.985, 0.995):
    c = solve(rmax)
    p = poles(c); r = float(np.max(np.abs(p)))
    gb = np.abs(H(c, BAND)).max()
    fr = float(abs(np.angle(p[0])))*FS/(2*np.pi)
    st = np.log(0.02)/np.log(max(r, 1e-9))
    print('%-9.3f %-13.4f %-12s %-11.2f %-9.1f %-11.0f %.4f'
          % (rmax, gb, '%.2fx' % (gf0/max(gb,1e-9)), fr, 1.0/(2*max(1-r,1e-9)), st, abs(H(c,0.5))))
pr = float(np.max(np.abs(poles(STOCK))))
print('\nFLYING today: 7-11 Hz gain %.4f, pole r %.4f, ring Q %.1f, settle %.0f ms'
      % (gf0, pr, 1.0/(2*(1-pr)), np.log(0.02)/np.log(pr)))
