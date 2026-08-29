# -*- coding: utf-8 -*-
"""The ratchet/lag frontier for the assist section, and GATE 2 at V173's point.

The section's slow real pole couples ratchet attenuation to added phase lag inseparably
(one real pole = 20 dB/decade, and its lag is set by the same time constant).  A NOTCH
would decouple them, but (a) the lineage forbids re-centring this biquad without new
evidence -- V105 flew a 25.5 Hz notch and failed -- and (b) the mode WANDERS +-0.71 Hz, so
a unit-circle zero gives ~0 dB worst case anyway.  So price the frontier honestly and see
where V173 sits.
"""
import io, os, struct, sys, glob
import numpy as np
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 1000.0
ROOT = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'

def load(p):
    b = io.open(p, 'rb').read()
    return dict(zip(('C_A8','C_AC','C_B0','C_B4'),
                    [struct.unpack('<f', b[a:a+4])[0] for a in (0xC60A8,0xC60AC,0xC60B0,0xC60B4)]))
S = load(os.path.join(ROOT, 'stock_fw_dump', 'code.bin'))
V = load(glob.glob(os.path.join(ROOT, '*v173*plain_image.bin'))[0])

def H(c, f):
    z = np.exp(2j*np.pi*np.atleast_1d(f)/FS)
    return c['C_B4']*(z*z+c['C_B0']*z+1.0)/(z*z+c['C_A8']*z+c['C_AC'])
def gd(c, f):
    h = 1e-3
    return -np.gradient(np.unwrap(np.angle(H(c, np.array([f-h,f,f+h])))), 2*np.pi*h)[1]*1000.0

def mk(p_slow, p_fast=0.475):
    c = dict(S)
    c['C_A8'] = -(p_slow + p_fast); c['C_AC'] = p_slow*p_fast
    c['C_B4'] = (1.0 + c['C_A8'] + c['C_AC'])/(2.0 + c['C_B0'])
    return c

print('FRONTIER: slow real pole (fast pole fixed 0.475, notch KEPT at 55.23 Hz)')
print('%7s %8s   %8s %8s %8s   %9s %8s' % (
      'p_slow','corner','ratchet','grind','LKAS','lag@1Hz','lag@8Hz'))
print('%7s %8s   %8s %8s %8s   %9s %8s' % (
      '','Hz','dB@8.17','dB 15-25','dB 0.5-3','added ms','added ms'))
rows = []
for p in (0.7966, 0.90, 0.94, 0.955, 0.970, 0.980, 0.985, 0.990):
    c = mk(p)
    corner = FS*(-np.log(p))/(2*np.pi)
    r8 = 20*np.log10(abs(H(c,8.17)[0])/abs(H(S,8.17)[0]))
    g = np.linspace(15,25,120); rg = 20*np.log10(np.mean(np.abs(H(c,g))/np.abs(H(S,g))))
    l = np.linspace(0.5,3,80);  rl = 20*np.log10(np.mean(np.abs(H(c,l))/np.abs(H(S,l))))
    d1, d8 = gd(c,1.0)-gd(S,1.0), gd(c,8.17)-gd(S,8.17)
    tag = '   <== V173' if abs(p-0.970) < 1e-6 else ('   (stock)' if abs(p-0.7966) < 1e-3 else '')
    print('%7.4f %8.2f   %+8.2f %+8.2f %+8.2f   %+9.1f %+8.1f%s'
          % (p, corner, r8, rg, rl, d1, d8, tag))
    rows.append((p, r8, d1))

print('\nCOST OF EACH EXTRA dB OF RATCHET ATTENUATION, from V173:')
base = [r for r in rows if abs(r[0]-0.970) < 1e-6][0]
for p, r8, d1 in rows:
    if p <= 0.970: continue
    print('  p=%.3f : %+.2f dB more ratchet  for  %+.1f ms more lag at 1 Hz  (%.1f ms per dB)'
          % (p, r8-base[1], d1-base[2], (d1-base[2])/max(base[1]-r8, 1e-9)))

print('\nGATE 2 at V173 -- the section can only REMOVE loop gain if |H_V173| <= |H_stock|')
f = np.geomspace(0.1, 499.0, 6000)
ratio = np.abs(H(V, f))/np.abs(H(S, f))
print('  max |H_V173/H_stock| over 0.1-499 Hz = %.6f at %.2f Hz  -> %s'
      % (ratio.max(), f[np.argmax(ratio)],
         'PASS (never adds gain)' if ratio.max() <= 1.0 + 1e-6 else 'FAIL -- adds gain'))
print('  max |H_V173| absolute            = %.6f  (stock %.6f)'
      % (np.abs(H(V,f)).max(), np.abs(H(S,f)).max()))
mono = np.all(np.diff(np.abs(H(V, np.linspace(0.1,200,4000)))) <= 1e-9)
print('  |H_V173| monotone decreasing 0.1-200 Hz -> %s (no new resonance)' % mono)
print('\n  phase lag added at the frequencies the outer loop closes on:')
for f0 in (0.5, 1.0, 2.0, 3.0):
    dph = np.degrees(np.angle(H(V,f0)[0]) - np.angle(H(S,f0)[0]))
    print('    %.1f Hz : %+6.2f deg   (%+.1f ms)' % (f0, dph, gd(V,f0)-gd(S,f0)))
