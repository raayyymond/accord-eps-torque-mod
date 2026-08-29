# -*- coding: utf-8 -*-
"""Do the grind and ratchet appear in channels OTHER than cs_tq?

Every prediction in this session rests on cs_tq, the DRIVER TORQUE SENSOR.  If the grind is really a
closed-loop instability it must also be visible in the steering ANGLE and, if it is command-driven,
in the LKAS COMMAND.  If it lives only in cs_tq it is a torque-path or sensor-local effect and the
notch's predicted benefit is overstated.

Report the slope-corrected excess per band per channel, on engaged creep windows, pooled over routes.
"""
import os, sys, glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
BANDS = [((5.0, 12.0), 'RATCHET 5-12'), ((15.0, 25.0), 'GRIND 15-25')]
FIT = [(3.0, 6.0), (12.0, 40.0)]

caches = sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))
z0 = np.load(caches[0], allow_pickle=True)
print('channels available in a cache:')
print('   ' + '  '.join(sorted(z0.files)))
print('')

CAND = [('cs_tq', 'driver torque sensor  (what every prediction used)'),
        ('cs_angle', 'steering ANGLE'),
        ('cs_rate', 'steering RATE'),
        ('cc_tq', 'the LKAS COMMAND'),
        ('sc_tq', 'sendcan LKAS command'),
        ('probe', 'the cave probe channel'),
        ('cs_press', 'hands-on pressure')]
have = [(k, d) for k, d in CAND if k in z0.files]
print('using: ' + ', '.join(k for k, _ in have))
print('')

acc = {k: [] for k, _ in have}
nwin = 0
for p in caches:
    try:
        z = np.load(p, allow_pickle=True)
    except Exception:
        continue
    if any(k not in z.files for k in ('cc_lat', 'cs_v')):
        continue
    lat = np.asarray(z['cc_lat']).astype(float)
    kmh = np.asarray(z['cs_v']).astype(float) * 3.6
    n = min(len(lat), len(kmh))
    ok = (lat[:n] > 0.5) & (kmh[:n] >= 1.0) & (kmh[:n] < 24.0)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
        if (j - i) < NPS:
            continue
        for kst in range(i, j - NPS, NPS // 2):
            got = False
            for key, _ in have:
                v = np.asarray(z[key]).astype(float)
                if len(v) < kst + NPS:
                    continue
                s = v[kst:kst + NPS]
                if not np.isfinite(s).all() or np.std(s) <= 0:
                    continue
                f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
                acc[key].append(P)
                got = True
            if got:
                nwin += 1
print('pooled %d engaged-creep windows across %d caches' % (nwin, len(caches)))
print('')
f = signal.welch(np.zeros(NPS), FS, nperseg=NPS, noverlap=NPS // 2)[0]
fitm = np.zeros_like(f, bool)
for lo, hi in FIT:
    fitm |= (f >= lo) & (f <= hi)


def excess(P, lo, hi):
    g = fitm & (P > 0) & (f > 0)
    if g.sum() < 8:
        return float('nan'), float('nan')
    b, a = np.polyfit(np.log10(f[g]), np.log10(P[g]), 1)
    m = (f >= lo) & (f <= hi)
    r = P[m] / (10 ** (a + b * np.log10(f[m])))
    k = int(np.argmax(r))
    return float(r[k]), float(f[m][k])


print('%-10s %6s   %-22s %-22s  %s' % ('channel', 'n', BANDS[0][1], BANDS[1][1], 'what it is'))
print('-' * 104)
for key, desc in have:
    if len(acc[key]) < 4:
        print('%-10s %6d   %s' % (key, len(acc[key]), 'too few windows'))
        continue
    M = np.median(np.asarray(acc[key]), 0)
    out = []
    for (lo, hi), _ in BANDS:
        e, pk = excess(M, lo, hi)
        out.append('%6.1fx @ %5.2f Hz' % (e, pk))
    print('%-10s %6d   %-22s %-22s  %s' % (key, len(acc[key]), out[0], out[1], desc))
print('')
print('null for the excess statistic is ~3.9x on these routes.')
print('=> a band that is real ONLY in cs_tq is a torque-path effect;')
print('   one that also shows in ANGLE is a genuine plant/loop oscillation.')
