# -*- coding: utf-8 -*-
"""What can ONE 15 s engaged pass actually answer? Power-check every endpoint on the card.

For each band, resample real 15 s engaged creep windows from the corpus, score them the way the
scorer does (band power normalised by a slope-matched control band), and ask: comparing ONE new
window against the historical distribution, how big a change is detectable at 95 %?

Then compare that floor to what V175/V173 actually PREDICT, so each endpoint is marked
ANSWERABLE or NOT from Stage 1 alone.  A null on a NOT-answerable endpoint means nothing and
must not be reported as evidence.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, WIN, NPS = 100.0, int(15 * 100), 512
CTRL = (30.0, 40.0)
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']

# band, name, predicted V175-vs-flying AMPLITUDE ratio (from the transfer functions)
ENDPOINTS = [
    ((6.5, 11.0), 'RATCHET 6.5-11 Hz', 0.51, 'V173 poles -5.9 dB; V175 adds the inertia revert'),
    ((15.0, 25.0), 'GRIND 15-25 Hz', 0.24, 'V173 poles -12.6 dB, the primary win'),
    ((0.5, 3.0), 'LKAS band 0.5-3 Hz', 0.92, 'should be UNCHANGED -- a null here must be meaningful'),
    ((26.0, 31.0), 'lane-change 26-31 Hz', 0.17, 'V173 poles -15.7 dB'),
]


def eng_windows():
    out = []
    for tag in ROUTES:
        p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
        if not os.path.exists(p):
            continue
        z = np.load(p, allow_pickle=True)
        if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq')):
            continue
        lat = np.asarray(z['cc_lat']).astype(float)
        v = np.asarray(z['cs_v']).astype(float)
        a = np.asarray(z['cs_tq']).astype(float)
        n = min(len(lat), len(v), len(a))
        lat, kmh, a = lat[:n], v[:n] * 3.6, a[:n]
        ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a)
        d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
        for i, j in zip(np.where(d == 1)[0], np.where(d == -1)[0]):
            if (j - i) >= WIN and np.std(a[i:j]) > 0:
                out.append(a[i:i + WIN])
    return out


def bp(x, lo, hi):
    f, P = signal.welch(x - x.mean(), FS, nperseg=NPS, noverlap=NPS // 2)
    m = (f >= lo) & (f <= hi)
    tr = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
    return float(tr(P[m], f[m]))


W = eng_windows()
print('engaged 15 s windows in the corpus: %d\n' % len(W))
print('%-22s %8s %9s %11s %9s   %s' % (
    'endpoint', 'log10 sd', 'detect@1', 'predicted', 'margin', 'verdict'))
print('-' * 92)
rows = []
for (lo, hi), nm, pred_amp, why in ENDPOINTS:
    v = np.array([bp(w, lo, hi) / max(bp(w, *CTRL), 1e-30) for w in W])
    v = v[np.isfinite(v) & (v > 0)]
    sd = float(np.std(np.log10(v), ddof=1))
    det_pow = 10 ** (1.96 * sd)              # detectable POWER ratio from one window
    pred_pow = pred_amp ** 2                 # transfer-function amplitude -> power
    margin = (1.0 / pred_pow) / det_pow      # >1 means the effect clears the floor
    ok = margin >= 1.0
    print('%-22s %8.3f %9.2fx %10.3fx %8.2fx   %s'
          % (nm, sd, det_pow, pred_pow, margin,
             'ANSWERABLE from ONE pass' if ok else 'NOT answerable -- a null means NOTHING'))
    rows.append((nm, sd, det_pow, pred_pow, margin, ok, why))

print('\nnotes')
for nm, sd, det, pp, mg, ok, why in rows:
    print('  %-22s %s' % (nm, why))

print('\nHOW MANY 15 s ENGAGED PASSES EACH ENDPOINT NEEDS')
print('%-22s %s' % ('endpoint', 'passes for the predicted effect to clear 95 %'))
for nm, sd, det, pp, mg, ok, why in rows:
    need = None
    for k in range(1, 13):
        if 10 ** (1.96 * sd / np.sqrt(k)) <= (1.0 / pp) if pp < 1 else True:
            need = k
            break
    if pp >= 1.0:
        print('  %-22s n/a (no change predicted -- see the equivalence note below)' % nm)
    else:
        print('  %-22s %s' % (nm, ('%d' % need) if need else '>12'))

print('\nEQUIVALENCE, for the LKAS band where we predict NO change:')
lo, hi = 0.5, 3.0
v = np.array([bp(w, lo, hi) / max(bp(w, *CTRL), 1e-30) for w in W])
v = v[np.isfinite(v) & (v > 0)]
sd = float(np.std(np.log10(v), ddof=1))
print('  one pass can only bound an LKAS-band change to within %.2fx.' % 10 ** (1.96 * sd))
print('  => "LKAS authority looks unchanged" from ONE pass is NOT evidence of no change.')
print('     Report it as unmeasured, or take %d passes to bound it to 1.5x.'
      % max(1, int(np.ceil((1.96 * sd / np.log10(1.5)) ** 2))))
