# -*- coding: utf-8 -*-
"""GATE 2 PHASE: what does V184's pole retune cost in phase, ENGAGED-ONLY, at the ratchet?

The biquad is engaged-gated (0xC649B=1, arm source = the LKAS flag), so the whole section --
magnitude AND phase -- appears only while engaged.  V184 retunes its poles.  The question the
correction exposed: does the added phase lag at ~8.2 Hz cost more stability margin than the
gain reduction buys?

For a lightly damped resonance inside a feedback loop, Z = (Z0 + P*F)/(1 - P*L).  Damping is
lost as P*L approaches +1.  What matters at the resonance is therefore the COMPLEX change in
L, i.e. Re(L) as well as |L|.  A filter that only shrinks |L| is unambiguously stabilising; one
that also rotates L toward +1 can give some of that back.

Compare, at the ratchet, the section as it flies (Honda coefficients, V122) against V184's.
"""
import io, os, struct, sys, glob, cmath, math
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 1000.0
A = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'


def coeffs(b):
    return dict(zip(('A8', 'AC', 'B0', 'B4'),
                    [struct.unpack_from('<f', b, o)[0]
                     for o in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]))


def img(v):
    g = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0], 'rb').read() if g else None


def H(c, f):
    z = cmath.exp(2j * math.pi * f / FS)
    return c['B4'] * (z * z + c['B0'] * z + 1.0) / (z * z + c['A8'] * z + c['AC'])


fly = coeffs(img('v122'))
new = coeffs(img('v184'))
print('flying (V122, Honda coefficients): %s' % {k: round(v, 6) for k, v in fly.items()})
print('V184  (poles 0.980/0.475)        : %s' % {k: round(v, 6) for k, v in new.items()})
print('')
print('%-9s %10s %9s   %10s %9s   %10s %9s' % (
    'f Hz', '|H| fly', 'ph fly', '|H| V184', 'ph V184', 'ratio', 'd-phase'))
for f in (0.5, 1.0, 3.0, 6.5, 8.17, 11.0, 15.0, 21.0, 28.0):
    a, b = H(fly, f), H(new, f)
    dph = math.degrees(cmath.phase(b) - cmath.phase(a))
    tag = '   <== RATCHET' if abs(f - 8.17) < .01 else ('   <== GRIND' if f == 21.0 else '')
    print('%9.2f %10.5f %8.2f\u00b0   %10.5f %8.2f\u00b0   %10.4f %8.2f\u00b0%s'
          % (f, abs(a), math.degrees(cmath.phase(a)), abs(b), math.degrees(cmath.phase(b)),
             abs(b) / abs(a), dph, tag))

print('')
print('THE QUESTION: at the ratchet, does the rotation give back what the shrink buys?')
f = 8.17
a, b = H(fly, f), H(new, f)
r = b / a                                   # the multiplicative change in the loop path
print('  multiplicative change in L at %.2f Hz : |r| = %.4f, arg(r) = %+.2f deg'
      % (f, abs(r), math.degrees(cmath.phase(r))))
print('')
print('  The destabilising direction is L -> +1 (real, positive).  Decompose r:')
print('    Re(r) = %+.4f   Im(r) = %+.4f' % (r.real, r.imag))
print('')
if abs(r) < 1.0 and r.real < 1.0:
    print('  => |L| SHRINKS by %.0f%% and Re(r) = %.4f < 1, so the change moves L AWAY from +1'
          % (100 * (1 - abs(r)), r.real))
    print('     on both the magnitude and the real axis. ** The phase rotation does NOT give back')
    print('     the gain reduction: GATE 2 passes in phase as well as magnitude at the ratchet. **')
else:
    print('  => the rotation is material; GATE 2 phase is NOT clean at the ratchet.')

print('')
print('WORST CASE over the whole band -- is there ANY frequency where V184 raises |L|?')
worst, wf = 0.0, None
for i in range(1, 5000):
    f = 0.1 * i
    if f >= 499:
        break
    q = abs(H(new, f)) / abs(H(fly, f))
    if q > worst:
        worst, wf = q, f
print('  max |H_V184 / H_fly| over 0.1-499 Hz = %.4f at %.1f Hz  -> %s'
      % (worst, wf, 'never amplifies' if worst <= 1.0001 else 'AMPLIFIES -- investigate'))
print('')
print('AND THE ENGAGED-ONLY PART: manual keeps the BYPASS (H = 1), so relative to MANUAL the')
print('engaged path already carries the flying section. V184 changes only the engaged side.')
for f in (1.0, 8.17, 21.0):
    print('   %5.2f Hz  engaged-vs-manual phase: flying %+7.2f deg -> V184 %+7.2f deg  (delta %+.2f)'
          % (f, math.degrees(cmath.phase(H(fly, f))), math.degrees(cmath.phase(H(new, f))),
             math.degrees(cmath.phase(H(new, f))) - math.degrees(cmath.phase(H(fly, f)))))
