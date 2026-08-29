# -*- coding: utf-8 -*-
"""
IS gp-0x6b70 A RELAY?  ANSWERED FROM THE IMAGE, after all.

Last tick concluded the LERP behind gp-0x6b70 could not be read statically, because FUN_00038148's
X (gp-0x64b6..) and Y (gp-0x641c..) are filled from RAM staging that FUN_000389ec COMPUTES by float
arithmetic from four live cells.  That was right about the mechanism and wrong about the conclusion:
the kit ALREADY mirrors FUN_000389ec integer-exactly (assist_map_mirror.py, validated 200/200 against
V72's flown probe), and the two arrays the LERP copies are exactly its internal staging:

    0x39548  st.h r9,  -0x64b8, gp   <- gp-0x373c   == mirror's Xi   (torque axis)
    0x39522  st.h r11, -0x641c, gp   <- gp-0x3714   == mirror's Yi   (assist axis)

So gp-0x6b70 = sgn(resid) * LERP_Xi_Yi(|resid|) -- ** the observer re-uses the POWER-ASSIST CURVE **,
applied to the residual instead of to driver torque.  The curve is a function of (speed, angle), so
it is computable for every operating point without a drive.

RELAY TEST: a relay saturates.  Report the fraction of the input span 0..8192 (the gp-0x6b70 clamp,
cal 0xC6200) that already sits within 5 % of the curve's own maximum.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import assist_map_mirror as M                                          # noqa: E402

MODES = (24, 26)              # the car is TVCA4 -- modes 24 (manual) and 26 (engaged)
SPEEDS = (0, 320, 640, 1280, 2560, 5120)      # counts; 0xC62EA = 320 ct is the ~5 km/h lockout
ANGLES = (0, 50, 150, 400, 900, 1800)         # 0.1 deg units


def curve(mode, speed_cnt, angle_10deg):
    A, B = M.stage_382d8(mode, speed_cnt)
    M.stage_389ec(A, B, speed_cnt, angle_10deg)
    st = M._LAST_STAGING
    return list(st['Xi']), list(st['Yi'])


def lerp(x, X, Y):
    return M._lerp_u16(x, X, Y)


CLAMP = M.CAL_7200            # 0xC6200 = 8192, the gp-0x6b70 clamp AND the input span


def relay_fraction(X, Y, span=None, tol=0.05):
    span = span or CLAMP
    ymax = max(Y)
    if ymax <= 0:
        return float('nan'), 0
    n, hit = 400, 0
    for k in range(n + 1):
        x = span * k // n
        if lerp(x, X, Y) >= ymax * (1 - tol):
            hit += 1
    return hit / (n + 1.0), ymax


print('=' * 100)
print('  gp-0x6b70 = sgn(resid) * ASSIST_CURVE(|resid|)   -- the observer re-uses the assist map')
print('  relay-fraction = share of the 0..%d input span already within 5 %% of the curve max' % CLAMP)
print('=' * 100)
for mode in MODES:
    print('\n  MODE %d' % mode)
    print('    speed  angle    X knots (torque axis)                       Ymax   relay-frac')
    for sp in SPEEDS:
        for an in (ANGLES if sp else ANGLES[:1]):
            try:
                X, Y = curve(mode, sp, an)
            except Exception as e:
                print('    %5d %6d   ERROR %s' % (sp, an, e))
                continue
            f, ymax = relay_fraction(X, Y)
            xs = ' '.join('%5d' % v for v in X[:6])
            print('    %5d %6d   %s   %5d   %6.1f %%' % (sp, an, xs, ymax, 100 * f))
        if sp == 0:
            break_inner = True
print()
print('  A relay would read near 100 %%: the curve reaches its ceiling almost immediately and the')
print('  stage becomes a signed constant.  A graded assist curve reads low.')
