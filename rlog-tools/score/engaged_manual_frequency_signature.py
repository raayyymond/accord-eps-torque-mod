# -*- coding: utf-8 -*-
"""Does the ENGAGED/MANUAL torque ratio rise like omega^2? That fingerprints the inertia lane.

The V184-vs-V185 fork is: is the ratchet driven by the INERTIA lane (gp-0x6b26 = K*alpha, whose
loop contribution scales omega^2) or by ASSIST-SECTION LOOP GAIN (a mild broadband filter on the
car)?  Both are engaged-only, so the engaged/manual CONTRAST cannot separate them -- but their
FREQUENCY SIGNATURES can:

    inertia lane      contribution ~ omega^2  ->  the engaged/manual ratio should RISE steeply
    assist section    |H| <= 1, mild          ->  ratio flat, or falling

Fit  log10(ratio) = a + b*log10(f)  over 3-30 Hz and read b.
    b ~ +2   -> inertia-like            -> V185 (which reverts the dose) is the right build
    b ~  0   -> broadband               -> V184 (which cuts loop gain) is the right build

CONTROLS, because a bare slope proves nothing:
  * SPEED-MATCHED sampling -- [[accord-averaged-spectrum-needs-matched-speed-distributions]] warns
    that an unmatched speed census manufactures spectral differences.
  * a PERMUTATION null on the engaged/manual labels, giving the slope's own null band.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
ROUTES = ['r77', 'r21', 'ra6', 'r1e', 'ra4', 'r7e', 'r7f', 'r95', 'r81', 'r82',
          'r78', 'r79', 'r85', 'r96', 'r9e', 'ra5', 'r22', 'r24', 'r97']


def windows(tag):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p):
        return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat', 'cs_v', 'cs_tq')):
        return []
    lat = np.asarray(z['cc_lat']).astype(float)
    kmh = np.asarray(z['cs_v']).astype(float) * 3.6
    tq = np.asarray(z['cs_tq']).astype(float)
    n = min(len(lat), len(kmh), len(tq))
    lat, kmh, tq = lat[:n], kmh[:n], tq[:n]
    ok = np.isfinite(tq) & (kmh >= 1.0) & (kmh < 60.0)
    out = []
    for i in range(0, n - NPS, NPS // 2):
        s = slice(i, i + NPS)
        if not ok[s].all() or np.std(tq[s]) <= 0:
            continue
        eng = lat[s].mean() > 0.5
        if not (lat[s] > 0.5).all() and not (lat[s] <= 0.5).all():
            continue                       # no mixed windows
        out.append((eng, float(np.mean(kmh[s])), tq[s]))
    return out


W = [w for t in ROUTES for w in windows(t)]
E = [w for w in W if w[0]]
M = [w for w in W if not w[0]]
print('windows: engaged %d   manual %d' % (len(E), len(M)))
if len(E) < 20 or len(M) < 20:
    print('too few'); sys.exit(0)

# ---- speed-matched sampling: bin by speed, draw equal counts per bin ----------
BINS = np.array([1, 5, 10, 15, 20, 30, 45, 60.0])
rng = np.random.default_rng(11)


def matched(E, M, rng):
    ei, mi = [], []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        e = [k for k, w in enumerate(E) if lo <= w[1] < hi]
        m = [k for k, w in enumerate(M) if lo <= w[1] < hi]
        n = min(len(e), len(m))
        if n == 0:
            continue
        ei += list(rng.choice(e, n, replace=False))
        mi += list(rng.choice(m, n, replace=False))
    return ei, mi


def psd(idx, pool):
    acc = []
    for k in idx:
        f, P = signal.welch(pool[k][2] - pool[k][2].mean(), FS, nperseg=NPS, noverlap=NPS // 2)
        acc.append(P)
    return f, np.median(np.asarray(acc), 0)


ei, mi = matched(E, M, rng)
print('speed-matched: %d engaged / %d manual windows' % (len(ei), len(mi)))
print('  engaged mean speed %.1f km/h   manual %.1f km/h'
      % (np.mean([E[k][1] for k in ei]), np.mean([M[k][1] for k in mi])))
f, Pe = psd(ei, E)
_, Pm = psd(mi, M)
band = (f >= 3.0) & (f <= 30.0)
ratio = Pe[band] / np.maximum(Pm[band], 1e-30)
lf = np.log10(f[band])
lr = np.log10(np.maximum(ratio, 1e-12))
b, a = np.polyfit(lf, lr, 1)
print('')
print('engaged/manual PSD ratio over 3-30 Hz:  log-log slope b = %+.3f' % b)
print('  (PSD ratio; a force term scaling as omega^2 gives b ~ +2 in AMPLITUDE, +4 in PSD)')
for fr in (4.0, 8.17, 15.0, 25.0):
    k = np.argmin(np.abs(f - fr))
    print('    %5.2f Hz  ratio %7.2f' % (f[k], Pe[k] / max(Pm[k], 1e-30)))

# ---- permutation null on the labels -----------------------------------------
pool = E + M
lab = np.array([1] * len(E) + [0] * len(M))
null = []
for s in range(200):
    r2 = np.random.default_rng(100 + s)
    p = r2.permutation(lab)
    Ep = [pool[k] for k in range(len(pool)) if p[k] == 1]
    Mp = [pool[k] for k in range(len(pool)) if p[k] == 0]
    if len(Ep) < 20 or len(Mp) < 20:
        continue
    e2, m2 = matched(Ep, Mp, r2)
    if len(e2) < 10:
        continue
    _, Pe2 = psd(e2, Ep)
    _, Pm2 = psd(m2, Mp)
    rr = np.log10(np.maximum(Pe2[band] / np.maximum(Pm2[band], 1e-30), 1e-12))
    null.append(np.polyfit(lf, rr, 1)[0])
null = np.asarray(null)
lo, hi = np.percentile(null, [2.5, 97.5])
print('')
print('permutation null for the slope: [%+.3f, %+.3f]  (n=%d shuffles)' % (lo, hi, len(null)))
print('')
# --- the verdict must test the SHAPE, not merely that the slope beats its null ---
pk = int(np.argmax(ratio))
peak_f, peak_r = f[band][pk], ratio[pk]
edges = np.mean([ratio[0], ratio[-1]])
peaked = peak_r > 4.0 * max(edges, 1e-9)
print("")
print("SHAPE TEST (a power law has no peak; a resonance does):")
print("   peak %.2fx at %.2f Hz   band edges mean %.2fx   peak/edges = %.1fx"
      % (peak_r, peak_f, edges, peak_r / max(edges, 1e-9)))
if peaked:
    print("   => the ratio is PEAKED, not a power law. A log-log slope is the WRONG model here,")
    print("      and its significance vs the null says nothing about omega^2.")
    print("   => an omega^2 force term would need b ~ +4 in PSD; observed %+.3f. NOT inertia-like." % b)
    print("")
    print("=> THE FREQUENCY SIGNATURE DOES NOT DISCRIMINATE. Both accounts predict a peak at the")
    print("   resonance. The V184/V185 fork stays OPEN and must be settled on the car.")
else:
    print("   => not peaked; the power-law reading is admissible.")
    if lo <= b <= hi:
        print("   => slope inside its null: no discrimination.")
    elif b > 3.0:
        print("   => slope near +4: INERTIA-like, V185 favoured.")
    else:
        print("   => slope positive but far below +4: not the omega^2 fingerprint.")
