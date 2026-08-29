# -*- coding: utf-8 -*-
"""What does the assist map's float second-order section actually DO at 8.64 Hz?

From FUN_000352b4, with s1 = gp-0x3814 and s2 = gp-0x3818 read BEFORE the update:

    w  = -(C_AC*s1 - -(s2*C_A8 - x*C_B4))      =  -C_AC*s1 - C_A8*s2 + C_B4*x
    y  = s1 + C_B0*s2 + w                      =  (1-C_AC)*s1 + (C_B0-C_A8)*s2 + C_B4*x
    s1 <- s2 ;  s2 <- w                        ;  y clamped to +/-12.0

Two states, two feedback coefficients -> a genuine biquad, running at 1 kHz, sitting in the
DOMINANT torque-fed lane.  It is Honda's (stock enable 0xC649B = 0) and the kit enabled it
from V104, so it is LIVE on the flying build.

This matters because it is the only FREQUENCY-SELECTIVE structure found anywhere in this
firmware, and a retune of it would attenuate the ratchet WITHOUT depending on the
real-positive P.L assumption that V168's lever rests on.  Simulate it directly rather than
deriving a transfer function by hand -- the operand order above is exactly what the
decompile shows and a sign slip would invert the answer.
"""
import sys
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

FS = 1000.0
STOCK = dict(C_A8=-1.5372, C_AC=0.63462001, C_B0=-1.8808, C_B4=0.81730998)
V106 = dict(C_A8=-1.88188, C_AC=0.9025, C_B0=-1.97438, C_B4=0.805095)


def run(x, c):
    s1 = s2 = 0.0
    y = np.empty_like(x)
    for i, xi in enumerate(x):
        w = -c['C_AC'] * s1 - c['C_A8'] * s2 + c['C_B4'] * xi
        yi = s1 + c['C_B0'] * s2 + w
        s1, s2 = s2, w
        y[i] = min(max(yi, -12.0), 12.0)
    return y


def resp(c, f, n=60000, amp=0.5):
    """Gain and phase at f, driven well inside the +/-12 clamp so it stays linear."""
    t = np.arange(n) / FS
    x = amp * np.sin(2 * np.pi * f * t)
    y = run(x, c)
    s = n // 3
    ref = np.exp(-2j * np.pi * f * t[s:])
    X = np.sum(x[s:] * ref)
    Y = np.sum(y[s:] * ref)
    return abs(Y / X), np.degrees(np.angle(Y / X))


print('assist-map second-order section, 1 kHz, driven at amplitude 0.5 (inside the +/-12 clamp)\n')
print('%-9s %-22s %-22s' % ('freq Hz', 'STOCK / flying coeffs', 'V106/V107 coeffs'))
for f in (1, 3, 5, 7, 8.64, 10, 12, 15, 20, 21, 25, 30, 40):
    g1, p1 = resp(STOCK, f)
    g2, p2 = resp(V106, f)
    mark = '   <- the ratchet' if abs(f - 8.64) < 0.01 else ('   <- the grind' if f == 21 else '')
    print('%-9.2f %-22s %-22s%s'
          % (f, '%.4f  %+7.1f deg' % (g1, p1), '%.4f  %+7.1f deg' % (g2, p2), mark))

# where is its own peak / trough?
fs = np.concatenate([np.arange(0.5, 40, 0.5)])
g = np.array([resp(STOCK, f, n=30000)[0] for f in fs])
print('\nSTOCK section: peak gain %.3f at %.1f Hz ; min gain %.3f at %.1f Hz'
      % (g.max(), fs[int(np.argmax(g))], g.min(), fs[int(np.argmin(g))]))
g2 = np.array([resp(V106, f, n=30000)[0] for f in fs])
print('V106  section: peak gain %.3f at %.1f Hz ; min gain %.3f at %.1f Hz'
      % (g2.max(), fs[int(np.argmax(g2))], g2.min(), fs[int(np.argmin(g2))]))

print("""
READING
  gain << 1 at 8.64 Hz  => the section already attenuates the ratchet band, and the lever is
                           to deepen or re-centre it.
  gain >~ 1 at 8.64 Hz  => the section PASSES or AMPLIFIES the ratchet, and retuning it to
                           attenuate there is an untried, frequency-selective lever that does
                           NOT rest on the P.L assumption.""")
