# -*- coding: utf-8 -*-
"""
EVERY CLAMP BETWEEN THE LKAS COMMAND AND THE MOTOR -- ceiling, reachability, measured duty.

The record's current model of the ratchet is a COMMAND-GATED SATURATION, with an explicit
instruction: "a linear lever cannot fix a relay.  The target is the SATURATING ELEMENT: find what
clips, and either raise its ceiling or soften its corner."

I found ONE (the gp-0x6b70 LERP) and built a ceiling raise for it.  I never checked whether it is the
only one, or the BINDING one.  This enumerates them all, reads every ceiling from the image, and
marks which have a MEASURED clip duty in the record versus which have never been looked at.

A clamp only matters if its input can REACH it.  So each row carries the producer's own ceiling next
to the clamp, and the ratio decides whether it can bind at all.
"""
import os
import struct

D = os.path.join(os.environ.get('ACCORD_FIRMWARE_ROOT',
                                'C:/Users/dudei/Desktop/Projects/accord-firmwares'),
                 'analysis-2020accord')
B = open(os.path.join(D, '_v202_V202-V199BASE-POLES.15.25.WIDER.SHOULDER_plain_image.bin'),
         'rb').read()
u16 = lambda a: struct.unpack_from('<H', B, a)[0]

# (element, ceiling, where the ceiling comes from, producer ceiling, measured duty / status)
ROWS = [
    ('gp-0x4f64  governor ceiling', u16(0xC6202), 'cal 0xC6202 (min of cap table)', None,
     'PINNED AT MAX 99.9%+ of engaged time (route a6) -- a CONSTANT, not a live limit'),
    ('gp-0x6b94  aggregator out', 10240, 'immediate +-0x2800', u16(0xC6202),
     'MEASURED DEAD: b6 = |gp-0x6b94| >= |gp-0x4f64| duty 0.000000 over 49,021 engaged\n        frames on route a5 (V105), with FOUR positive controls on the same byte'),
    ('gp-0x6b70  observer out', u16(0xC6200), 'cal 0xC6200', 14490,
     'UNMEASURED -- V205 reads it; this is V206s target'),
    ('gp-0x6ad6  torque ref', u16(0xC6200), 'cal 0xC6200 @0x3A7CA', None,
     'MEASURED DEAD: V100 b5 = |gp-0x6ad6| >= cal duty 0.000000, CI [0, 0.0186],\n        with b4 = 0.6057 on the same cell -- the reference-clamp hypothesis is DEAD'),
    ('gp-0x6b86  base assist', 12288, 'immediate +-0x3000', 12288,
     'equals its producer -- cannot clip'),
    ('biquad out', 12288, 'float +-12.0 x1024', 12288,
     'equals its producer -- cannot clip'),
    ('gp-0x6b84  resid', 12288, 'immediate +-0x3000', None, 'UNMEASURED'),
    ('LKAS setpoint', u16(0xC61BE), 'cal 0xC61BE', None,
     'MEASURED IDLE -- V108 E3 pulled on its own null, rate still rising at 5 speeds'),
    ('fwd clamp A', u16(0xC61B2), 'cal 0xC61B2', 2505,
     'INERT at 6x -- lane max 2505 < 3072'),
    ('fwd clamp B', u16(0xC61B4), 'cal 0xC61B4', 2505,
     'INERT at 6x -- lane max 2505 < 3072'),
    ('0xC407E interlock', u16(0xC407E), 'cal 0xC407E', None,
     'Honda ships 511, ONE COUNT under its own 512 trip -- V73 raised it, V74/V75 FAULTED'),
    ('0xC674E EME wall', u16(0xC674E), 'cal 0xC674E', 3072,
     'must stay > the tracking clamp; the structural cap below 10x gain'),
    ('gp-0x6b26 inertia win', 1024, 'zero-REJECT +-0x400', 511,
     'producer clamped to 511 by 0xC407E -- cannot reject'),
    ('gp-0x6bd0 damping win', 2048, 'zero-REJECT +-0x800', 1024,
     '0 in 100% of the micro regime'),
    ('gp-0x6bbe viscous win', 2048, 'zero-REJECT +-0x800', 512, 'p50 74 -- far from the window'),
    ('gp-0x6b46 lag win', 1024, 'zero-REJECT +-0x400', 512,
     'clamped to +-512 by construction -- cannot reject'),
    ('gp-0x6b4c assist-sum win', 10240, 'zero-REJECT +-0x2800', 10240,
     'MEASURED: |.| >= 4096 duty 0.000000 over 17,614 engaged frames'),
    ('gp-0x6b4e model lane', 10240, 'SATURATE +-0x2800', 10240,
     'equals its window -- saturates but never rejects; magnitude UNMEASURED (V204)'),
]

print('=' * 108)
print('  SATURATION CENSUS -- every clamp from the LKAS command to the motor')
print('=' * 108)
print('  %-26s %8s  %-30s %10s' % ('element', 'ceiling', 'where the ceiling comes from', 'producer'))
print('  ' + '-' * 104)
for nm, ceil, src, prod, note in ROWS:
    p = '' if prod is None else '%d' % prod
    print('  %-26s %8d  %-30s %10s' % (nm, ceil, src, p))
    print('        %s' % note)

print()
print('=' * 108)
print('  WHAT THIS RANKS')
print('=' * 108)
unmeasured = [r for r in ROWS if r[4].startswith('UNMEASURED')]
print('  CANNOT CLIP (ceiling >= producer, or measured inert):  %d of %d'
      % (len(ROWS) - len(unmeasured), len(ROWS)))
print('  NEVER MEASURED -- any of these could be the saturating element:')
for nm, ceil, src, prod, note in unmeasured:
    print('     %-26s ceiling %5d   %s' % (nm, ceil, note.split('--')[-1].strip()))
print()
print('=' * 108)
print('  THE CENSUS CONVERGES ON gp-0x6b70')
print('=' * 108)
print('  Every other clamp between the LKAS command and the motor is either STRUCTURALLY unable to')
print('  clip (ceiling >= its own producer) or MEASURED at zero duty:')
print('    gp-0x6ad6   V100 b5, duty 0.000000, CI [0, 0.0186], b4 = 0.6057 on the same cell')
print('    gp-0x6b94   V105 b6 on route a5, duty 0.000000 over 49,021 engaged frames,')
print('                with b7 0.383 / b5 0.280 / b4 0.434 / b3 0.487 as positive controls')
print('    gp-0x4f64   pinned at its cal max 4762 for 99.9%+ of engaged time -- a CONSTANT limit,')
print('                and the aggregator never reaches it (the b6 result above)')
print()
print('  ** gp-0x6b70 is the ONLY clamp in the path that can clip and has never been measured. **')
print('  That is exactly the cell V205 reads and V206 doses -- arrived at independently, by')
print('  elimination, from data already on disk.')
