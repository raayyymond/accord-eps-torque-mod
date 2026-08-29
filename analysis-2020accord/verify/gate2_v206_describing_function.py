# -*- coding: utf-8 -*-
"""
GATE 2 FOR V206 -- and it is NOT the trivial check it looks like.

V206 halves cal(0xC63AE), which scales the INPUT of a memoryless nonlinearity:

    gp-0x6b70 = sgn(resid) * LERP( (|resid| * cal) >> 10 )

"Halving a gain must reduce loop gain" is FALSE here.  Scaling the input by k moves the operating
point DOWN a CONCAVE curve, onto a STEEPER part.  The curve's slope ratio between small and mid
signal is 6.7-10.7x, so the steepening is large.  The correct instrument for a memoryless
nonlinearity in a loop is the DESCRIBING FUNCTION:

    f(x) = sgn(x) * LERP(|x|)            the stage at unity scale
    g(x) = f(k*x)                        the stage with the dose
    N(A) = first-harmonic gain at input amplitude A
    => N_g(A) = k * N_f(k*A)             NOT k * N_f(A)

Since N_f DECREASES with amplitude (concave), N_f(kA) > N_f(A) for k < 1, so the two effects fight.
The dose only reduces loop gain if  k * N_f(k*A) < N_f(A)  at EVERY amplitude the loop can reach.
This checks that, and it is the difference between a GATE 2 pass and a build that raises the very
gain it was cut to lower.

PHASE: the stage is memoryless, so it contributes ZERO phase at every frequency and every amplitude.
The dose therefore scales the Nyquist locus radially with no rotation -- which is why the magnitude
test above is sufficient, and why it must be done properly.
"""
import math
import os
import sys

sys.path.insert(0, 'analysis-2020accord/studies/models')
os.environ.setdefault('ACCORD_FIRMWARE_ROOT',
                      'C:/Users/dudei/Desktop/Projects/accord-firmwares')
import assist_map_mirror as M                                            # noqa: E402

SPEEDS = (320, 640, 1280, 2560, 5120)
K_UNITY, K_DOSE = 1024, 512
CLAMP = M.CAL_7200            # 8192, the gp-0x6b70 output clamp


def curve(speed_cnt, mode=26, angle=150):
    A, B = M.stage_382d8(mode, speed_cnt)
    M.stage_389ec(A, B, speed_cnt, angle)
    st = M._LAST_STAGING
    return list(st['Xi']), list(st['Yi'])


def f_stage(x, X, Y, k):
    """The stage exactly: scale the input by k/1024, LERP, re-sign, clamp.  0x38242 / 0x381xx."""
    u = (abs(int(x)) * k) >> 10
    y = M._lerp_u16(u, X, Y)
    y = min(y, CLAMP)
    return y if x >= 0 else -y


def describing(A, X, Y, k, n=512):
    """First-harmonic gain N(A) = (2/(pi*A)) * integral f(A sin t) sin t dt, over a quarter period."""
    if A <= 0:
        return float('nan')
    s = 0.0
    for i in range(n):
        t = (i + 0.5) * (math.pi / 2) / n
        s += f_stage(A * math.sin(t), X, Y, k) * math.sin(t)
    s *= (math.pi / 2) / n
    return (4.0 / (math.pi * A)) * s


print('=' * 98)
print('  GATE 2 -- V206 (0xC63AE 1024 -> 512).  Describing function, not a naive gain.')
print('  PASS requires  N_dose(A) < N_unity(A)  at EVERY amplitude the loop can reach.')
print('=' * 98)
AMPS = (25, 50, 100, 200, 400, 800, 1600, 3200, 6400, 12800)
worst = None
for sp in SPEEDS:
    X, Y = curve(sp)
    print('\n  speed %d   (curve X[1]=%d Y[1]=%d, small-signal %.2fx)'
          % (sp, X[1], Y[1], Y[1] / X[1]))
    print('     A      N unity    N dose    ratio    verdict')
    for A in AMPS:
        nu = describing(A, X, Y, K_UNITY)
        nd = describing(A, X, Y, K_DOSE)
        r = nd / nu if nu else float('nan')
        ok = nd < nu
        if worst is None or r > worst[0]:
            worst = (r, sp, A, nu, nd)
        print('   %6d   %8.4f  %8.4f   %6.3f    %s'
              % (A, nu, nd, r, 'ok' if ok else '** RAISES LOOP GAIN **'))

print()
print('=' * 98)
r, sp, A, nu, nd = worst
if r < 1.0:
    print('  GATE 2 PASS -- worst case is speed %d at A=%d: N %.4f -> %.4f, ratio %.3f < 1.'
          % (sp, A, nu, nd, r))
    print('  The dose reduces first-harmonic loop gain at EVERY amplitude and EVERY speed tested,')
    print('  and adds no phase (memoryless).  The Nyquist locus contracts radially toward the')
    print('  origin with no rotation, so it cannot create an encirclement of -1 that did not')
    print('  already exist: a stable loop stays stable.')
else:
    print('  GATE 2 FAIL -- speed %d at A=%d: N %.4f -> %.4f, ratio %.3f >= 1.' % (sp, A, nu, nd, r))
    print('  The concave curve steepens faster than the dose shrinks. DO NOT FLY V206.')
print('=' * 98)
