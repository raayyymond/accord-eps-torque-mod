# -*- coding: utf-8 -*-
"""PRE-REGISTRATION: the exact numbers the scorer will print after the drive.

"V184 cuts the grind 16 dB" is not a prediction the scorer can check.  The scorer reports a
SLOPE-CORRECTED EXCESS -- band power divided by a power law fitted OUTSIDE the band -- and the
assist-section filter attenuates the fit region too, so the excess does NOT fall by the raw power
ratio.  Compute the actual predicted excess by applying each build's |H|^2 to the REAL flying
spectrum and re-running the same estimator.

Written BEFORE the drive so the result can falsify it.
"""
import io, os, struct, sys, glob, cmath, math
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
SEC_FS = 1000.0                     # the assist section runs at 1 kHz
A = 'C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'


def coeffs(b):
    return dict(zip(('A8', 'AC', 'B0', 'B4'),
                    [struct.unpack_from('<f', b, o)[0]
                     for o in (0xC60A8, 0xC60AC, 0xC60B0, 0xC60B4)]))


def img(v):
    g = [x for x in glob.glob(A + '/*_' + v + '_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0], 'rb').read() if g else None


def H(c, f):
    z = cmath.exp(2j * math.pi * f / SEC_FS)
    return abs(c['B4'] * (z * z + c['B0'] * z + 1.0) / (z * z + c['A8'] * z + c['AC']))


fly = coeffs(img('v122'))
BUILDS = [('V185 (poles at Honda)', coeffs(img('v185'))),
          ('V184 (poles 0.980)', coeffs(img('v184')))]

# ---- the REAL flying spectrum, from the reference route the scorer itself cites -------------
TAG = 'r24'
p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (TAG, TAG)
z = np.load(p, allow_pickle=True)
lat = np.asarray(z['cc_lat']).astype(float)
kmh = np.asarray(z['cs_v']).astype(float) * 3.6
tq = np.asarray(z['cs_tq']).astype(float)
n = min(len(lat), len(kmh), len(tq))
lat, kmh, tq = lat[:n], kmh[:n], tq[:n]
ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(tq)
d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
acc = []
for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
    if (j - i) < NPS:
        continue
    for k in range(i, j - NPS, NPS // 2):
        s = tq[k:k + NPS]
        if np.std(s) <= 0:
            continue
        f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        acc.append(P)
print('%s: %d engaged-creep windows' % (TAG, len(acc)))
Pf = np.median(np.asarray(acc), 0)

BANDS = [((15.0, 25.0), 'GRIND  15-25 Hz'), ((5.0, 12.0), 'RATCHET 5-12 Hz')]
FIT = [(3.0, 6.0), (12.0, 40.0)]
fitm = np.zeros_like(f, bool)
for lo, hi in FIT:
    fitm |= (f >= lo) & (f <= hi)


def excess(P, lo, hi):
    good = fitm & (P > 0) & (f > 0)
    b, a = np.polyfit(np.log10(f[good]), np.log10(P[good]), 1)
    m = (f >= lo) & (f <= hi)
    pred = 10 ** (a + b * np.log10(f[m]))
    r = P[m] / pred
    k = int(np.argmax(r))
    return float(r[k]), float(f[m][k])


print('')
print('%-24s %-18s %-18s' % ('build', BANDS[0][1], BANDS[1][1]))
print('-' * 64)
base = []
for (lo, hi), nm in BANDS:
    e, pk = excess(Pf, lo, hi)
    base.append(e)
print('%-24s %-18s %-18s' % ('FLYING (V122) measured',
                             '%.1fx' % base[0], '%.1fx' % base[1]))
print('   scorer prints for r24:  grind 14.0x  ratchet 33.2x   (null ~3.9)')
print('')
for nm, c in BUILDS:
    gain2 = np.array([(H(c, x) / max(H(fly, x), 1e-12)) ** 2 if x > 0 else 1.0 for x in f])
    Pn = Pf * gain2
    out = []
    for (lo, hi), _ in BANDS:
        e, pk = excess(Pn, lo, hi)
        out.append(e)
    print('%-24s %-18s %-18s' % (nm, '%.1fx' % out[0], '%.1fx' % out[1]))
print('')
print('NULL for both bands on this route is about 3.9x -- below it the scorer says "not real".')
print('')
print('=> PRE-REGISTERED, before the drive:')
for nm, c in BUILDS:
    gain2 = np.array([(H(c, x) / max(H(fly, x), 1e-12)) ** 2 if x > 0 else 1.0 for x in f])
    Pn = Pf * gain2
    g = excess(Pn, 15.0, 25.0)[0]
    r = excess(Pn, 5.0, 12.0)[0]
    print('   %-24s grind %s   ratchet %s'
          % (nm,
             'GONE (%.1fx < null)' % g if g < 3.9 else 'still real (%.1fx)' % g,
             'GONE (%.1fx < null)' % r if r < 3.9 else 'still real (%.1fx)' % r))
print('')
print('NOTE: this is the ASSIST-SECTION filter only. The inertia-dose revert acts in a')
print('different lane and is NOT in these numbers -- so the ratchet column is a LOWER bound')
print('on what the builds do to it.')
