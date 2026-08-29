# -*- coding: utf-8 -*-
"""Does V172's lag land where the DRIVER feels it?

"130 ms settling" is a step-response figure and is the wrong metric for feel.  What a driver
feels on ordinary inputs is GROUP DELAY in the band they actually steer in (roughly 0-3 Hz);
settling time is dominated by the slowest pole regardless of whether any energy is there.

Compute group delay vs frequency for the flying tuning and for V172, and then ask whether a
real-pole variant can hold 3-5 Hz closer to unity while still attenuating 8.64 Hz.
"""
import struct, sys
import numpy as np
from scipy import optimize
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FS = 1000.0
FLY  = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
V172 = dict(C_A8=-1.44508553, C_AC=0.460833013, C_B0=-1.97093439, C_B4=0.548481286)

def H(c, f):
    z = np.exp(2j*np.pi*np.asarray(f, float)/FS)
    return c['C_B4']*((1-c['C_AC']) + (c['C_B0']-c['C_A8'])*z)/(z**2 + c['C_A8']*z + c['C_AC']) + c['C_B4']
def poles(c): return np.roots([1.0, c['C_A8'], c['C_AC']])
def as_c(v):  return dict(C_A8=v[0], C_AC=v[1], C_B0=v[2], C_B4=v[3])
def f32(x):   return struct.unpack('<f', struct.pack('<f', float(x)))[0]

def gdelay(c, f, df=0.05):
    """Group delay in ms: -dphase/domega."""
    p1 = np.unwrap(np.angle(H(c, np.array([f-df, f, f+df]))))
    return -(p1[2]-p1[0])/(2*np.pi*2*df) * 1000.0

print('GROUP DELAY -- what a driver actually feels, by frequency')
print('%-9s %-14s %-14s %s' % ('freq Hz', 'FLYING ms', 'V172 ms', 'added lag ms'))
for f in (0.5, 1, 2, 3, 4, 5, 7, 8.64, 12):
    a, b = gdelay(FLY, f), gdelay(V172, f)
    print('%-9.2f %-14.1f %-14.1f %+.1f%s' % (f, a, b, b-a,
          '   <- driver band' if f <= 3 else ('   <- RATCHET' if abs(f-8.64)<.01 else '')))

# a real-pole variant that protects 3-5 Hz
BAND = np.linspace(7.0, 11.0, 13); FULL = np.arange(0.5, 49.0, 1.0)
G0 = np.abs(H(FLY, FULL))
def solve():
    def cost(v):
        c = as_c(v); p = poles(c)
        if np.max(np.abs(np.imag(p))) > 1e-9: return 1e5
        r = np.max(np.abs(p))
        if r >= 0.97: return 1e6 + (r-0.97)*1e3
        gb = np.abs(H(c, BAND)); gf = np.abs(H(c, FULL))
        return (np.max(gb)**2*40 + (abs(H(c,0.5))-1)**2*500
                + max(0, 0.95-abs(H(c,3.0)))**2*900          # protect 3 Hz
                + max(0, 0.85-abs(H(c,5.0)))**2*500          # protect 5 Hz
                + np.sum(np.maximum(0, gf/G0 - 1.02)**2)*40)
    best, bv = None, None
    for s in range(30):
        rng = np.random.default_rng(s)
        x0 = np.array([-1.4, 0.45, -1.95, 0.55]) + rng.normal(0, 0.2, 4)
        r = optimize.minimize(cost, x0, method='Nelder-Mead', options=dict(maxiter=3000))
        if best is None or r.fun < best: best, bv = r.fun, r.x
    return as_c([f32(x) for x in bv])

P = solve(); pp = poles(P)
print('\nPROTECTED real-pole variant: poles %s  real %s  r %.5f'
      % (np.round(pp,5), bool(np.max(np.abs(np.imag(pp)))<1e-9), float(np.max(np.abs(pp)))))
print('%-9s %-11s %-11s %-11s %s' % ('freq Hz','FLYING','V172','PROTECTED','protected gdelay'))
for f in (0.5, 1, 3, 5, 7, 8.64, 11, 21):
    print('%-9.2f %-11.4f %-11.4f %-11.4f %+.1f ms'
          % (f, abs(H(FLY,f)), abs(H(V172,f)), abs(H(P,f)), gdelay(P,f)))
gb = np.abs(H(P, BAND)).max()
g864 = abs(H(P, 8.64))
Pc = 0.9300/2.825; L = 0.825 + 2.0*g864
print('\n  protected: 8.64 Hz %.4f (V172 %.4f) => loop Q ratio %.2f = %.1fx more damped'
      % (g864, abs(H(V172,8.64)), 1/abs(1-Pc*L), 14.29/(1/abs(1-Pc*L))))
print('  coefficients: %s' % '  '.join('%s=%+0.9g' % (k, P[k]) for k in ('C_A8','C_AC','C_B0','C_B4')))
print('  raw: %s' % ' '.join('%08X' % struct.unpack('<I', struct.pack('<f', P[k]))[0]
                             for k in ('C_A8','C_AC','C_B0','C_B4')))
