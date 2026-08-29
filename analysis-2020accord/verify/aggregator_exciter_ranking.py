# -*- coding: utf-8 -*-
"""Rank every aggregator term by its AUTHORITY, to see whether V196 touches a big lever or a small one.

The ratchet is a PLANT resonance, so firmware can only reduce what EXCITES it.  The exciters are the
terms summed in FUN_0003aa2c into gp-0x6b94.  Each is gated by a clamp, and that clamp is a hard
upper bound on how much that term can contribute -- measurable from the decompiled constants without
needing a probe.

Clamp widths are read from the gate expressions in the decompile:  x * (x + H < 2H+1)  =>  |x| <= H.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# (cell, clamp, what it is, recorded status, expected 8 Hz character)
T = [
 ('gp-0x6b86', 12288, 'the BIQUAD output (boost path)',
  'LIVE - engagement-gated; V195/V196 reshape it', 'carries the LKAS command: mostly 1-5 Hz'),
 ('gp-0x6b4c', 10240, 'the 11-slot assist sum',
  'LIVE - 7 slots raw, 4 forced zero', 'assist-shaped, low frequency'),
 ('gp-0x6ad4', 10240, 'the unfiltered residual PID lane',
  'ELIMINATED as a cause by V56', 'n/a'),
 ('gp-0x6b62',  8192, 'return-centre / detent',
  'DEAD ENGAGED - 0.0000 over 75,227 frames', 'n/a'),
 ('gp-0x6adc',  8192, 'the r26 RATE LANE (decompiler iVar21)',
  'LIVE - V62/V88 levers act here', 'rate-derived: omega^1'),
 ('gp-0x6ada',  8192, 'the r24 RATE LANE (decompiler iVar16)',
  'LIVE - V62 sar x2, V88 Lever B', 'rate-derived: omega^1'),
 ('gp-0x6bbe',  2048, 'VISCOUS + a DC pedestal',
  'LIVE - flat ~90 ct/(rad/s), p50 73.6 ct', 'rate-derived: omega^1'),
 ('gp-0x6bd0',  2048, 'the base-assist damper',
  'DEAD in the micro regime - 100 % of it', 'n/a'),
 ('gp-0x6ade',  1024, 'a clamped input',
  'DEAD - read at 0x3AA48, NO WRITER in the image', 'n/a'),
 ('gp-0x6b26',  1024, 'the INERTIA term  <-- V196 halves this',
  'LIVE - clamped at 511 by 0xC407E', 'acceleration-derived: omega^2'),
]
print('AGGREGATOR TERMS (FUN_0003aa2c -> gp-0x6b94, itself clamped +-10240)')
print('')
print('%-11s %7s  %-34s %s' % ('cell', 'clamp', 'what it is', 'status'))
print('-' * 108)
for c, k, w, s, _ in sorted(T, key=lambda r: -r[1]):
    print('%-11s %7d  %-34s %s' % (c, k, w, s))
live = [r for r in T if r[3].startswith('LIVE')]
dead = [r for r in T if 'DEAD' in r[3] or 'ELIMINATED' in r[3]]
unk = [r for r in T if r[3] == 'unidentified']
print('')
print('%d LIVE - %d DEAD or eliminated - %d unidentified' % (len(live), len(dead), len(unk)))
print('')
print('=> AUTHORITY RANKING OF THE LIVE TERMS (clamp = hard upper bound on contribution)')
for c, k, w, s, ch in sorted(live, key=lambda r: -r[1]):
    print('     %-11s %6d   %s' % (c, k, ch))
print('')
b = max(r[1] for r in live)
i = [r[1] for r in T if r[0] == 'gp-0x6b26'][0]
print('   the INERTIA term has the SMALLEST clamp of any live term: %d vs %d for the biquad output'
      % (i, b))
print('   => %.0fx less authority in absolute terms, and V196 halves it again.' % (b / i))
print('')
print('!! BUT AUTHORITY IS NOT 8 Hz CONTENT.  The big terms carry the LKAS command, which the')
print('   record shows is a 1-5 Hz low-pass, so their energy sits well BELOW the ratchet.  The')
print('   inertia term is omega^2-weighted, i.e. concentrated exactly where the ratchet is.')
print('   A small clamp on a high-frequency term can still dominate the 8 Hz sum.')
print('')
print('   THIS CANNOT BE SETTLED FROM CONSTANTS.  What would settle it: repoint the 427 probe')
print('   onto each candidate in turn and measure its 8 Hz content directly.  gp-0x6bbe is the')
print('   first one worth measuring -- it is LIVE, rate-derived (omega^1, so also elevated at')
print('   8 Hz), and has 2x the inertia term\'s clamp.')
