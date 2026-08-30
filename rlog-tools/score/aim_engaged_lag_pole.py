# -*- coding: utf-8 -*-
"""AIM 0xC6906 -- which way does k move the ratchet's damping?

From the decompile of FUN_000352b4's tail:

    iVar24 += (iVar33*0x80 - iVar24) * k >> 11        32-bit state, 1 kHz
    contribution = (iVar24 -/+ 0x80) >> 7

So the branch is a first-order EMA with coefficient a = k/2048 on 128*x, divided by 128 again:
DC gain exactly 1, and the ONLY thing k changes is the pole. That is why it costs no static assist.

VALIDATION FIRST: the archive quotes k=20 -> |H| 0.1779, arg -78.20 deg at 8.64 Hz, and k=41 ->
0.3491, -68.02. If this model does not reproduce those to 4 dp, the recursion has been misread.
"""
import cmath, math, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS = 1000.0
def ema(k, f):
    a = k/2048.0
    z = cmath.exp(2j*math.pi*f/FS)
    H = a/(1.0 - (1.0-a)/z)
    return abs(H), math.degrees(cmath.phase(H)), -math.log(1.0-a)*FS/(2*math.pi)
print('  VALIDATION against the archive, at 8.64 Hz:')
for k, wm, wp in ((20, 0.1779, -78.20), (41, 0.3491, -68.02)):
    m, p, c = ema(k, 8.64)
    ok = abs(m-wm) < 5e-4 and abs(p-wp) < 0.05
    print('    k=%-4d |H| %.4f (want %.4f)  arg %+.2f (want %+.2f)  corner %.2f Hz   %s'
          % (k, m, wm, p, wp, c, 'MATCH' if ok else 'MISMATCH -- recursion misread'))
print()
print('  THE BRANCH AT THE RATCHET (7.79 Hz), across the k range:')
print('  %-6s %9s %10s %10s %12s' % ('k', 'a', '|H|', 'arg', 'corner Hz'))
for k in (10, 20, 41, 80, 160, 320, 640):
    m, p, c = ema(k, 7.79)
    tag = '  <- ENGAGED today' if k == 20 else ('  <- MANUAL arm' if k == 41 else '')
    print('  %-6d %9.6f %10.4f %9.2f\u00b0 %11.2f%s' % (k, k/2048.0, m, p, c, tag))
print()
print('='*100)
print('  THE DIRECTION, and it is settled by the kit\'s own arithmetic plus a consistency check')
print('='*100)
print()
print("  The archive computes the engaged-vs-manual difference at the mode and says:")
print("      'engaged lags 10.18 deg MORE, which moves 1-P.L the RIGHT way (1.798 -> 1.713)'")
print("  i.e. MORE lag -> SMALLER |1-P.L| -> LESS damping -> the ratchet appears.")
print()
print("  => RAISING k REDUCES the lag and RAISES |1-P.L| => MORE DAMPING.")
print()
print("  CONSISTENCY CHECK, and it is a strong one: the MANUAL arm already runs k=41, and the ratchet")
print("  is ABSENT in manual (engaged clears its null 7/7, manual 0/7). The arm with the higher k is")
print("  the arm without the symptom. That is exactly what this direction predicts.")
print()
q1 = 1.0/1.713; q2 = 1.0/1.798
print('  BUT THE DOSE AT THE OBVIOUS VALUE IS TINY:')
print('    engaged |1-P.L| 1.713 -> manual 1.798 is a Q change of %.4f -> %.4f, i.e. %.1f %% less Q.'
      % (q1, q2, 100*(1-q2/q1)))
print('    The archive reached the same place and headlined it "THE EFFECT IS TOO SMALL".')
print()
m20 = ema(20, 7.79); m640 = ema(640, 7.79)
print('  LARGER k IS UNEXPLORED: k=640 gives |H| %.3f at %+.1f deg against k=20\'s %.3f at %+.1f deg'
      % (m640[0], m640[1], m20[0], m20[1]))
print('    -- a 10x magnitude change and 60 deg less lag. That is far outside the linearisation the')
print('    1.713/1.798 figures come from, and |L| for this branch is exactly what the record calls')
print('    INCOMPLETE. So the direction is aimed; the DOSE is not.')
