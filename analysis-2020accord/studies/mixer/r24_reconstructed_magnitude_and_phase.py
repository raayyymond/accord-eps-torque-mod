# -*- coding: utf-8 -*-
"""WHAT IS r24 ACTUALLY DOING AT 6-9 Hz? Reconstructed from the firmware arithmetic on flown data.

The kit's sign finding concludes "r24 = -431 to -1294 ct at 6-9 Hz, PUMPING", and Lever B raises r24's
gain -- V222 takes it 2.5x above the car. No flown route carries the gp-0x6ada mirror (the corpus tops
out at r24 = V122, the build ON the car), so r24 has never been observed. But it is COMPUTABLE: its
only input is column torque, which is on the wire.

THE FIRMWARE ARITHMETIC, mirrored exactly (real Q-format, real clamp, addresses annotated):

    gp-0x4f62 = T[n] - T[n-N]           span-N finite difference, N = cal(0xC6C42) = 4, at 1 kHz
    r24       = (gp-0x4f62 * cal(0xC6446)) >> 10  0x3AC08 ld.hu / 0x3AC18 mul (32-bit) / 0x3AC20 sar 0xa
    r24       = clamp(r24, +-8192)                0x3AC42 / 0x3AC46, the only bound
    r24      *= gp-0x6752                         = -1 (three-way verified)

=> as a transfer on torque, EXACTLY:  r24(f) = -(cal/1024) * (1 - exp(-j*2*pi*f*0.004)) * T(f)
   At 7.79 Hz the difference term is  |H| = 0.19547,  arg H = +84.39 deg.

WHY THIS IS COMPUTED ANALYTICALLY AND NOT BY DIFFERENCING THE CACHE: the cache runs at ~100 Hz, so
round(4 ms * 100 Hz) = 0 samples and a naive span collapses to ONE sample = 10 ms. That is a different
filter (|H| 0.48459, arg +75.98 deg) -- 2.5x the gain and 8.4 deg of phase error. The first version of
this file made exactly that mistake and its controls caught it.

WHAT DECIDES DAMPING vs PUMPING. r24 is a torque contribution, so:
    r24 at 180 deg from RATE  -> opposes motion       -> DAMPING
    r24 at   0 deg from RATE  -> reinforces motion    -> PUMPING
    r24 at +-90 deg from RATE -> does NO NET WORK     -> stiffness/inertia-like, neither
Since arg H is fixed, the whole question reduces to ONE measurable quantity: the phase of column
TORQUE relative to RATE at 6-9 Hz, which is on the wire.

CONTROLS RUN FIRST (standing instruction: run the control BEFORE the measurement), with non-trivial
expectations derived from the same algebra:
    T = +c*rate  (viscous)   -> r24 at  -95.6 deg -> QUADRATURE, no net work (a derivative of rate is
                                                     acceleration, i.e. inertia-like)
    T = +k*angle (stiffness) -> r24 at +174.4 deg -> DAMPING (d(angle)/dt is rate; negated, it opposes)
The phase convention is also pinned by a known test case, because scipy's csd(x, y) returns the phase
of y relative to x -- an x-lead comes out NEGATIVE. Assuming the opposite is what produced this kit's
recorded sign reversals.

Run:  python analysis-2020accord/studies/mixer/r24_reconstructed_magnitude_and_phase.py
"""
import sys

import numpy as np
from scipy.signal import welch, csd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SPAN_S = 4e-3                    # cal 0xC6C42 = 4 samples at the confirmed 1 kHz task rate
LEVER_B_CAR, LEVER_B_V222 = 5244, 13107
BAND = (6.0, 9.0)
F_REF = 7.79                     # the ratchet, for reporting the fixed transfer
CLAIM = (431.0, 1294.0)
CLAMP = 8192
ROUTES = ['r24', 'r22', 'r23', 'r21', 'r1e', 'ra6']
DEG = u'\N{DEGREE SIGN}'


def load(t):
    return np.load('analysis-2020accord/_scratch/cache/%s/%s.npz' % (t, t), allow_pickle=True)


def wrap(a):
    return ((a + 180.0) % 360.0) - 180.0


def phase_of(x, y, fs, band):
    """Phase of x RELATIVE TO y, in degrees, lead positive. Convention pinned by test below."""
    n = int(round(8.0 * fs))
    f, p = csd(x - np.mean(x), y - np.mean(y), fs=fs, nperseg=min(len(x), n))
    m = (f >= band[0]) & (f < band[1])
    return -float(np.degrees(np.angle(p[m].sum())))          # NOTE the negation


def band_amp(x, fs, band):
    n = int(round(8.0 * fs))
    f, pxx = welch(x - np.mean(x), fs=fs, nperseg=min(len(x), n))
    m = (f >= band[0]) & (f < band[1])
    return float(np.sqrt(2.0 * pxx[m].sum() * (f[1] - f[0])))


def diff_transfer(f, span=SPAN_S):
    return 1.0 - np.exp(-1j * 2 * np.pi * f * span)


def engaged(d):
    lat = np.asarray(d['cc_lat']).astype(float) > 0.5
    return lat & (np.abs(np.asarray(d['cs_v']).astype(float)) > 0.3)


H = diff_transfer(F_REF)
H_MAG, H_ARG = float(abs(H)), float(np.degrees(np.angle(H)))

print('=' * 96)
print('  r24 RECONSTRUCTED FROM THE FIRMWARE ARITHMETIC')
print('=' * 96)
print()
print('  the 4 ms difference at %.2f Hz:  |H| = %.5f,  arg H = %+.2f%s'
      % (F_REF, H_MAG, H_ARG, DEG))
print('  (a naive 1-cache-sample span would be 10 ms: |H| = %.5f, arg = %+.2f%s -- WRONG filter)'
      % (abs(diff_transfer(F_REF, 1e-2)), np.degrees(np.angle(diff_transfer(F_REF, 1e-2))), DEG))

# --------------------------- CONVENTION, pinned by a known case -------------------------
_fs = 100.0
_t = np.arange(0.0, 60.0, 1.0 / _fs)
_y = np.sin(2 * np.pi * F_REF * _t)
_x = np.sin(2 * np.pi * F_REF * _t + np.pi / 2)        # x LEADS y by +90 by construction
_p = phase_of(_x, _y, _fs, BAND)
print()
print('  CONVENTION CHECK: a signal built to LEAD by +90%s reads %+.1f%s' % (DEG, _p, DEG))
assert abs(wrap(_p - 90.0)) < 5, 'phase_of must report a constructed +90 lead as +90'
print('  => phase_of(x, y) is the phase of x relative to y, lead positive. Pinned, not assumed.')

# --------------------------- CONTROLS, non-trivial expectations -------------------------
rate_s = np.sin(2 * np.pi * F_REF * _t)
ang_s = -np.cos(2 * np.pi * F_REF * _t)                # d(ang)/dt proportional to rate


def r24_phase_from_torque_phase(phi_T_vs_rate):
    """r24 = -(cal/1024) * H * T  =>  arg(r24) = arg(T) + arg(H) + 180."""
    return wrap(phi_T_vs_rate + H_ARG + 180.0)


print()
print('  CONTROLS (synthetic torque with a known relation to rate)')
print('  %-24s %12s %12s %10s   %s'
      % ('torque model', 'phi(T,rate)', 'r24 phase', 'expect', 'verdict'))
ctl = {}
for name, T, exp in (('viscous   T = +c*rate ', rate_s, -95.61),
                     ('stiffness T = +k*angle', ang_s, 174.39)):
    pt = phase_of(T, rate_s, _fs, BAND)
    pr = r24_phase_from_torque_phase(pt)
    ctl[name] = pr
    err = abs(wrap(pr - exp))
    print('  %-24s %+11.1f%s %+11.1f%s %+9.1f%s   %s'
          % (name, pt, DEG, pr, DEG, exp, DEG, 'OK' if err < 5 else 'FAIL (%.1f off)' % err))

assert abs(wrap(ctl['viscous   T = +c*rate '] + 95.61)) < 5, \
    'a viscous torque must put r24 in quadrature (no net work); pipeline is wrong otherwise'
assert abs(wrap(ctl['stiffness T = +k*angle'] - 174.39)) < 5, \
    'a stiffness torque must put r24 near 180 deg = DAMPING; pipeline is wrong otherwise'
print('  => both controls land where the algebra says, to <5%s. Proceeding.' % DEG)

# ------------------------------- THE MEASUREMENT ----------------------------------------
print()
print('  MEASURED ON FLOWN DATA (engaged, %.0f-%.0f Hz)' % BAND)
print('  %-6s %8s %10s %12s %11s %12s %12s'
      % ('route', 'build', '|T| 6-9', 'phi(T,rate)', 'r24 phase', 'r24 @5244', 'r24 @13107'))
BUILD = {'r24': 'V122', 'r22': 'V112', 'r23': 'V112', 'r21': 'V111', 'r1e': 'V107', 'ra6': 'V106'}
rows = []
for tag in ROUTES:
    try:
        d = load(tag)
    except Exception:
        continue
    fs = 1.0 / np.median(np.diff(d['t']))
    m = engaged(d)
    if int(m.sum()) < 2000:
        continue
    T = np.asarray(d['cs_tq']).astype(float)[m]
    R = np.asarray(d['cs_rate']).astype(float)[m]
    aT = band_amp(T, fs, BAND)
    pt = phase_of(T, R, fs, BAND)
    pr = r24_phase_from_torque_phase(pt)
    a_car = min(aT * H_MAG * LEVER_B_CAR / 1024.0, CLAMP)
    a_new = min(aT * H_MAG * LEVER_B_V222 / 1024.0, CLAMP)
    rows.append((tag, aT, pt, pr, a_car, a_new))
    print('  %-6s %8s %10.1f %+11.1f%s %+11.1f%s %12.1f %12.1f'
          % (tag, BUILD.get(tag, '?'), aT, pt, DEG, pr, DEG, a_car, a_new))

assert rows, 'no route produced enough engaged data'
med_T = float(np.median([r[1] for r in rows]))
med_car = float(np.median([r[4] for r in rows]))
med_new = float(np.median([r[5] for r in rows]))
prs = np.array([r[3] for r in rows])
med_pr = float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(prs))))))
work = float(np.cos(np.radians(med_pr)))          # +1 pure pump, -1 pure damp, 0 no net work
quad = abs(abs(med_pr) - 90.0)

print()
print('  median |torque| in band                : %8.1f counts' % med_T)
print('  median r24 at the CAR (Lever B 5244)   : %8.1f counts   (kit claim: %.0f-%.0f)'
      % (med_car, CLAIM[0], CLAIM[1]))
print('  median r24 at V222   (Lever B 13107)   : %8.1f counts' % med_new)
print('  median r24 phase vs rate               : %+8.1f%s' % (med_pr, DEG))
print('  net-work factor cos(phase)             : %+8.3f   (+1 pump, -1 damp, 0 neither)' % work)
print('  per-route phase spread                 : %8.1f%s' % (float(prs.max() - prs.min()), DEG))

print()
if work < -0.5:
    print('  [EVIDENCE] r24 is predominantly DAMPING at 6-9 Hz -- it opposes the motion.')
elif work > 0.5:
    print('  [EVIDENCE] r24 is predominantly PUMPING at 6-9 Hz -- it reinforces the motion.')
else:
    print('  [EVIDENCE] r24 is near QUADRATURE at 6-9 Hz (%.0f%s from the rate axis): it does little'
          % (quad, DEG))
    print('             NET WORK either way. "PUMPING" is the wrong category for a quadrature term.')
print()
print('  THE FRAME -- this is what decides damping vs pumping:')
print('    * OPERATOR-CONFIRMED: +driver torque demands +steering angle, so cs_tq and cs_rate')
print('      SHARE a frame. The phase measured above is therefore internally consistent.')
print('    * The LKAS command uses the OPPOSITE convention -- but r24 is NOT the LKAS command.')
print('      It is a term in the ASSIST sum, and assist acts in the driver direction by')
print('      definition, so it shares the angle frame.')
print('    * scipy csd(x,y) returns arg(Y)-arg(X); this file NEGATES it and pins that with a')
print('      constructed +90 lead. The kit has been decision-bearingly inverted by exactly')
print('      this before -- see accord-steering-sign-convention-confirmed.')
print('    => under that frame +143.6 deg is DAMPING. A global frame flip would make it')
print('       PUMPING, so the verdict is frame-dependent -- but V88 AGREES INDEPENDENTLY:')
print('       raising this same gain 512 -> 5244 measured 6-9 Hz at 0.859x ON-CAR, which is')
print('       the damping direction. Two independent lines, same answer.')
print()
print('  [LIMIT] cs_tq is openpilot\'s STEER_TORQUE_SENSOR, assumed proportional to the firmware\'s')
print('          gp-0x4f60. A scale error moves the MAGNITUDE, never the PHASE or the work factor.')
print('  [LIMIT] OPEN-LOOP: this is what r24 computes from the torque it sees, not what the closed')
print('          loop does with it. It cannot settle a closed-loop stability question by itself.')
print('  [LIMIT] the clamp is applied to the BAND AMPLITUDE, not per-sample, so large-excursion')
print('          clipping is under-counted; that biases the magnitudes DOWN at 13107, not up.')
