# -*- coding: utf-8 -*-
"""
THE 0xC63AA DILUTION RATIO -- and a 41x error in the recorded sensitivity.

BUILD-LINEAGE.md parks 0xC63AA as "still the best structural lever, but it needs the dilution ratio
first", with the sensitivity recorded as

    d(iVar6)/d(0xC63AA) = -(1/16) * (gp-0x6b4c / 1024)

Mirroring FUN_00038148's decompiled arithmetic exactly -- integer >>, real Q-format, addresses
annotated -- that factor does not survive.

    0x38148  term_i  = (x_i * gate_i * w_i) >> 10          six lanes, zero-REJECT gates
             SUM     = sum(term_i)
             scaled  = (SUM * sgn(gp-0x6752) * cal(0xC6468)) >> 10      cal = 2639
             target  = scaled * 0x10                        <-- the x16 the record dropped
             model  += ((target - model) * cal(0xC63AC)) >> 10          alpha = 102/1024
             resid   = gp-0x6bfe - (model >> 4) + gp-0x6bfa             <-- the >>4 it kept

** The *0x10 and the >>4 CANCEL. **  The model is stored 16x oversampled so the EMA keeps precision;
it is not a divide-by-16 in the signal path.  So the true sensitivity is

    d(resid)/d(w) = -sgn * (gp-0x6b4c * gate) * cal(0xC6468) / (1024 * 1024)
                  = -sgn * (gp-0x6b4c / 1024) * 2.577

against the recorded -(1/16) = -0.0625.  ** 2.577 / 0.0625 = 41.2x understated. **
"""
import os
import struct

D = os.path.join(os.environ.get('ACCORD_FIRMWARE_ROOT',
                                'C:/Users/dudei/Desktop/Projects/accord-firmwares'),
                 'analysis-2020accord')
B = open(os.path.join(D, '_v202_V202-V199BASE-POLES.15.25.WIDER.SHOULDER_plain_image.bin'),
         'rb').read()
u16 = lambda a: struct.unpack_from('<H', B, a)[0]

W = {'gp-0x6bd0': (0xC63A0, 2048), 'gp-0x6bbe': (0xC63A2, 2048),
     'gp-0x6b46': (0xC63A4, 1024), 'gp-0x6b26': (0xC63A6, 1024),
     'gp-0x6b4e': (0xC63A8, 10240), 'gp-0x6b4c': (0xC63AA, 10240)}
POST, ALPHA = u16(0xC6468), u16(0xC63AC)


def sar(x, n):
    """V850 arithmetic shift right -- Python >> already floors toward -inf, which matches."""
    return x >> n


def model_scaled(x, pol=1):
    """0x38148, exactly: gated weighted sum -> post scale -> the x16 that the >>4 later undoes."""
    s = 0
    for lane, v in x.items():
        w, win = W[lane]
        gate = 1 if -win <= v <= win else 0          # ZERO-REJECT, not saturate
        s += sar(v * gate * u16(w), 10)
    return sar(s * pol * POST, 10)                   # == model >> 4 at EMA convergence


print('=' * 96)
print('  0xC63AA SENSITIVITY AND DILUTION -- mirrored from FUN_00038148')
print('=' * 96)
print('  weights: ' + '  '.join('%s=%d' % (k, u16(v[0])) for k, v in sorted(W.items())))
print('  cal(0xC6468) post-sum = %d    cal(0xC63AC) EMA alpha = %d/1024' % (POST, ALPHA))
print()
print('  SENSITIVITY, measured by perturbing the mirror (not by algebra):')
base = {'gp-0x6b4e': 0, 'gp-0x6b4c': 1000, 'gp-0x6b26': 0,
        'gp-0x6b46': 0, 'gp-0x6bd0': 0, 'gp-0x6bbe': 0}
m0 = model_scaled(base)
sv = u16(0xC63AA)
for wnew in (1024, 512, 256, 0):
    B = bytearray(B); struct.pack_into('<H', B, 0xC63AA, wnew); B = bytes(B)
    m = model_scaled(base)
    print('    w = %4d -> scaled = %7d   d(resid) vs unity = %+8d  (= %+.3f x gp-0x6b4c)'
          % (wnew, m, m0 - m, (m0 - m) / 1000.0))
B = bytearray(B); struct.pack_into('<H', B, 0xC63AA, sv); B = bytes(B)
print('    recorded formula would predict d(resid) = -(1/16)*(1000/1024) = %.3f for w -> 0'
      % (-(1 / 16) * (1000 / 1024)))
print()
print('  DILUTION -- the gp-0x6b4c term as a share of SUM, in the regime the ratchet lives in')
print('    measured lane values from the record: gp-0x6bd0 = 0 in 100 %% of the micro regime;')
print('    gp-0x6bbe p50 = 74; gp-0x6b26 producer clamped to 511 by 0xC407E; |gp-0x6b4c| < 4096')
print('    (duty 0.000000 for >= 4096 over 17,614 engaged frames).')
print()
print('    gp-0x6b4c   share of SUM assuming gp-0x6b4e = gp-0x6b46 = 0   and with them at 500 each')
for v in (250, 500, 1000, 2000, 4000):
    o = {'gp-0x6b4e': 0, 'gp-0x6b4c': v, 'gp-0x6b26': 511,
         'gp-0x6b46': 0, 'gp-0x6bd0': 0, 'gp-0x6bbe': 74}
    tot = model_scaled(o)
    only = model_scaled({**o, 'gp-0x6b4c': 0})
    o2 = {**o, 'gp-0x6b4e': 500, 'gp-0x6b46': 500}
    tot2 = model_scaled(o2)
    only2 = model_scaled({**o2, 'gp-0x6b4c': 0})
    f = lambda t, o_: (t - o_) / t if t else float('nan')
    print('    %5d            %5.1f %%                                    %5.1f %%'
          % (v, 100 * f(tot, only), 100 * f(tot2, only2)))
print()
print('  => the term is NOT diluted in the ratchet regime: it dominates the model sum.')
print('  => the blocker is now only gp-0x6b4e and gp-0x6b46, whose magnitudes are unknown.')
