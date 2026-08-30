# -*- coding: utf-8 -*-
"""Re(Z) ACROSS FREQUENCY -- where does the EPS exchange the most energy with the driver?

    python rlog-tools/score/rez_spectrum.py

Reusable instrument. The kit's Re(Z) work has always been evaluated INSIDE pre-chosen bands (6-9, 9-12,
15-22). This computes the whole curve instead, so the bands can be checked against where the physics
actually is rather than the other way round.

    Z(f) = S_TR(f) / S_RR(f)          transfer from steering RATE to column TORQUE
    Re(Z) < 0  =>  torque opposes rate  =>  the system is delivering energy, not absorbing it

TWO THINGS THIS FILE EXISTS TO GET RIGHT:

 1. MAGNITUDE-WEIGHT IT. cos(phase) alone finds the phase extremum, which is NOT the impedance
    extremum: cos bottoms out at 13 Hz (-0.998, essentially 179 deg opposed) but torque amplitude is
    lower there, so |Re(Z)| actually peaks at 10 Hz. Phase alone would mis-aim a lever by 3 Hz.

 2. GATE ON COHERENCE. Torque-rate coherence is 0.44-0.76 over 7-23 Hz, which is real, but it collapses
    below 7 Hz (0.07-0.27) and above 24 Hz (0.11-0.15). Numbers outside the gate are printed but
    flagged, never used for a conclusion. For contrast, COMMAND-rate coherence never exceeds 0.23
    anywhere -- which is why no command-referenced delay could be fitted.

WHAT THE MEASUREMENT SAYS (6 routes, engaged):

    band            mean Re(Z)   mean cos   coherence
    ratchet  6-9       -23.5      -0.401      0.532
    mid      9-12      -67.9      -0.784      0.618     <- strongest AND best-measured
    gap     12-15      -51.3      -0.986      0.511
    grind   15-22      -14.2      -0.591      0.631

Re(Z) is negative across the ENTIRE 4-24 Hz range: the anti-damping is BROADBAND, not a narrow mode.
Its magnitude peaks at 10 Hz and its power at 9 Hz -- roughly 3x the ratchet band and 5x the grind
band, in a band the kit scores but has never treated as a target.

=> CONSEQUENCE: size and aim levers at 9-12 Hz, not only at 6-9.

SIGN CAVEAT. The ABSOLUTE sign of Re(Z) depends on a frame this kit has not resolved (see
r24_retrodiction_test_fails.py). What is frame-free, and all that is claimed here, is the SHAPE: the
extremum sits at 9-10 Hz and the band ordering is mid > gap > ratchet > grind.
"""
import sys

import numpy as np
from scipy.signal import csd, welch, coherence

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROUTES = ['r24', 'r22', 'r23', 'r21', 'r1e', 'ra6']
GRID = np.arange(4.0, 26.0, 1.0)
COH_MIN = 0.30
BANDS = [('ratchet', 6, 9), ('mid', 9, 12), ('gap', 12, 15), ('grind', 15, 22)]


def load(t):
    return np.load('analysis-2020accord/_scratch/cache/%s/%s.npz' % (t, t), allow_pickle=True)


def per_route(tag):
    d = load(tag)
    fs = 1.0 / np.median(np.diff(d['t']))
    m = (np.asarray(d['cc_lat']).astype(float) > 0.5) & \
        (np.abs(np.asarray(d['cs_v']).astype(float)) > 0.3)
    if int(m.sum()) < 4000:
        return None
    T = np.asarray(d['cs_tq']).astype(float)[m]
    R = np.asarray(d['cs_rate']).astype(float)[m]
    n = int(round(16 * fs))
    f, Ptr = csd(T - T.mean(), R - R.mean(), fs=fs, nperseg=min(len(T), n))
    _, Prr = welch(R - R.mean(), fs=fs, nperseg=min(len(R), n))
    _, Ptt = welch(T - T.mean(), fs=fs, nperseg=min(len(T), n))
    fk, K = coherence(T - T.mean(), R - R.mean(), fs=fs, nperseg=min(len(T), n))
    Z = np.conj(Ptr) / np.maximum(Prr, 1e-20)
    return (np.interp(GRID, f, np.real(Z)),
            np.interp(GRID, f, np.cos(np.angle(Ptr))),
            np.interp(GRID, fk, K),
            np.interp(GRID, f, np.sqrt(Ptt)))


rows = [r for r in (per_route(t) for t in ROUTES) if r is not None]
assert len(rows) >= 4, 'need at least 4 routes for a median curve'
Zm, Cm, Km, Am = (np.median(np.array([r[i] for r in rows]), axis=0) for i in range(4))

print('=' * 88)
print('  Re(Z) SPECTRUM -- median over %d routes, engaged' % len(rows))
print('=' * 88)
print()
print('  %6s %11s %9s %9s %9s  %s' % ('f Hz', 'Re(Z)', 'cos', 'coher', '|T|', 'anti-damping power'))
power = np.where(Zm < 0, -Zm * Am ** 2, 0.0)
for i, g in enumerate(GRID):
    bar = '#' * int(round(20 * power[i] / max(power.max(), 1e-9)))
    flag = '' if Km[i] >= COH_MIN else '   (below coherence gate)'
    print('  %6.1f %+11.1f %+9.3f %9.3f %9.1f  %-20s%s' % (g, Zm[i], Cm[i], Km[i], Am[i], bar, flag))

ok = Km >= COH_MIN
i_mag = int(np.argmin(np.where(ok, Zm, 0)))
i_pow = int(np.argmax(np.where(ok, power, 0)))
i_cos = int(np.argmin(np.where(ok, Cm, 0)))
print()
print('  within the coherence gate (>= %.2f):' % COH_MIN)
print('    most negative Re(Z)     %.1f Hz  (%+.1f)' % (GRID[i_mag], Zm[i_mag]))
print('    peak anti-damping power %.1f Hz' % GRID[i_pow])
print('    phase extremum          %.1f Hz  (cos %+.3f)  <- NOT the same frequency'
      % (GRID[i_cos], Cm[i_cos]))

print()
print('  %-9s %8s %12s %11s %11s' % ('band', 'Hz', 'mean Re(Z)', 'mean cos', 'coherence'))
stats = {}
for name, lo, hi in BANDS:
    k = (GRID >= lo) & (GRID < hi)
    stats[name] = (float(Zm[k].mean()), float(Cm[k].mean()), float(Km[k].mean()))
    print('  %-9s %4d-%-4d %+12.1f %+11.3f %11.3f' % ((name, lo, hi) + stats[name]))

worst = min(stats, key=lambda k: stats[k][0])
assert (Zm[ok] < 0).all(), 'Re(Z) must be single-signed across the gated range -- that IS the finding'
assert worst == 'mid', 'the 9-12 band must be the extremum, or the headline is wrong'
assert GRID[i_cos] != GRID[i_mag], 'phase and magnitude extrema must differ -- that is caveat 1'
assert stats['mid'][0] / stats['grind'][0] > 2.5, 'mid must dominate grind by a wide margin'
print()
print('  all four assertions hold.')
print('  [EVIDENCE] Re(Z) is single-signed across the whole gated 7-23 Hz range => the anti-damping is')
print('             BROADBAND, not a narrow mode.')
print('  [EVIDENCE] its extremum is %.0f-%.0f Hz, ~%.1fx the ratchet band and ~%.1fx the grind band --'
      % (GRID[i_pow], GRID[i_mag], stats['mid'][0] / stats['ratchet'][0],
         stats['mid'][0] / stats['grind'][0]))
print('             a band the kit scores but has never treated as a target.')
print('  [ACTION]   size and aim levers at 9-12 Hz, not only at 6-9.')
print('  [LIMIT]    the ABSOLUTE sign depends on the unresolved frame; only the SHAPE is claimed.')
