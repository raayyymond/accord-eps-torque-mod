# -*- coding: utf-8 -*-
"""WHERE DOES MORE LEVER B STOP BUYING DAMPING? The describing function answers it exactly.

Only two dose points for Lever B exist on-car (512 and 5244), and V62's lesson is explicit -- "2x is
approximately the OPTIMUM, not a point on a ramp". So the dose cannot be chosen from the record. It
CAN be chosen from the arithmetic, because the lane's nonlinearity is known exactly:

    scaled = (clamp(gp-0x4f62, +-5120) * k) >> 10        0x3AC18 / 0x3AC20   -- 32-bit throughout
    shaped = deadzone(scaled, +-3)                        0x3AC24            -- cal 0xC61F6
    out    = clamp(polarity * shaped, +-8192)             0x3AC42 / 0x3AC46  -- immediates

Raising k moves ONLY where the lane stops being linear: the onset is A_sat = 8192*1024/k. Past that
it is a saturating element, and for a sinusoid of amplitude A the SINUSOIDAL-INPUT DESCRIBING
FUNCTION of a saturation with linear slope k and rail L = 8192 is

    N(A)/k = 1                                                        for k*A <= L
    N(A)/k = (2/pi) * [ asin(1/rho) + (1/rho)*sqrt(1 - 1/rho^2) ]     for rho = k*A/L > 1

The EFFECTIVE DAMPING the loop sees is N(A), not k. It is unit-free in rho, which sidesteps the open
question of what gp-0x4f62's counts physically are.

THE CONSEQUENCE, AND IT IS THE WHOLE POINT: as k -> infinity, N(A) -> 4L/(pi*A), a CONSTANT
INDEPENDENT OF k. So the damping this lane can deliver at a given oscillation amplitude is BOUNDED,
and past the knee more gain buys essentially nothing while making the lane progressively more of a
relay on every larger excursion. That bound is the real ceiling -- not the cal's range (65535), and
not the int16 argument V160 made, which does not exist at all.

Run:  python analysis-2020accord/studies/mixer/lever_b_describing_function_optimum.py
"""
import numpy as np

L = 8192.0                 # the +-8192 output rail, immediates at 0x3AC42/46
Q = 1024.0                 # the >>10
CAR_K, SHELF_K = 5244, 13107
# engaged |d(column torque)/dt| on the car's own route r24 -- shape, not absolute scale
AMPS = {'p50 (27)': 27.0, 'p90 (146)': 146.0, 'p99 (610)': 610.0, 'max (1669)': 1669.0}
KS = [512, 5244, 6553, 13107, 19660, 26214, 39321, 52428, 65535]


def n_over_k(k, A):
    rho = k * A / (L * Q)
    if rho <= 1.0:
        return 1.0
    r = 1.0 / rho
    return (2.0 / np.pi) * (np.arcsin(r) + r * np.sqrt(max(0.0, 1.0 - r * r)))


def eff(k, A):
    """Effective damping N(A), in the same units as k."""
    return k * n_over_k(k, A)


print('=' * 96)
print('  LEVER B -- EFFECTIVE DAMPING N(A) vs GAIN, by oscillation amplitude')
print('=' * 96)
print()
print('  %8s %9s   %s' % ('gain k', 'onset', '   '.join('%12s' % a for a in AMPS)))
rows = {}
for k in KS:
    cells = []
    for nm, A in AMPS.items():
        e = eff(k, A)
        rows.setdefault(nm, []).append(e)
        cells.append('%12.0f' % e)
    tag = ''
    if k == CAR_K:
        tag = '  <- THE CAR'
    elif k == SHELF_K:
        tag = '  <- V221/V222'
    print('  %8d %9.0f   %s%s' % (k, L * Q / k, '   '.join(cells), tag))

print()
print('  the asymptote 4L/(pi*A), which NO gain can exceed:')
print('  %8s %9s   %s' % ('', '', '   '.join('%12.0f' % (4 * L * Q / (np.pi * A)) for A in AMPS.values())))
print()
print('  --- what each further doubling actually buys, relative to the car ---')
print('  %8s   %s' % ('gain k', '   '.join('%12s' % a for a in AMPS)))
base = {nm: eff(CAR_K, A) for nm, A in AMPS.items()}
for k in KS:
    print('  %8d   %s' % (k, '   '.join('%11.2fx' % (eff(k, A) / base[nm])
                                        for nm, A in AMPS.items())))

print()
print('  --- the knee: the gain past which one more doubling buys under 20 % ---')
for nm, A in AMPS.items():
    knee = None
    for k in range(512, 65536, 64):
        if eff(2 * k, A) / eff(k, A) < 1.20:
            knee = k
            break
    print('    %-12s knee at k = %5s   (onset %s counts)'
          % (nm, knee if knee else '>65535',
             '%.0f' % (L * Q / knee) if knee else '--'))

# --------------------------------- assertions -----------------------------------------
for nm, A in AMPS.items():
    asym = 4 * L * Q / (np.pi * A)
    assert eff(65535, A) <= asym * 1.001, 'N(A) must never exceed its own asymptote for %s' % nm
    assert eff(65535, A) >= eff(13107, A), 'N(A) must be monotone non-decreasing in k'
assert abs(n_over_k(512, 27.0) - 1.0) < 1e-12, 'at the stock gain the small amplitudes are LINEAR'
assert n_over_k(SHELF_K, 27.0) == 1.0, 'V221/V222 must keep the p50 amplitude fully linear'
assert n_over_k(SHELF_K, 1669.0) < 1.0, 'and the largest measured excursion must be saturating'
assert eff(2 * SHELF_K, 146.0) / eff(SHELF_K, 146.0) > 1.5, \
    'at the p90 amplitude a further doubling must still buy real damping -- if not, V222 is at the knee'
print()
print('  all assertions hold.')
print()
print('  [EVIDENCE] the ceiling on this lane is 4L/(pi*A), not the cal range and not an int16 bound.')
print('  [NOTE]     this is an OPEN-LOOP gain calculation. It says what the lane can deliver, NOT')
print('             that delivering more improves the car -- phase and the rest of the loop decide')
print('             that, and only a drive scores the symptom.')
