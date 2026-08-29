# -*- coding: utf-8 -*-
"""Does the ratchet frequency actually VARY between routes, or is 0.80 Hz estimator noise?

A firmware divider at 100/12 must give the SAME frequency on every route to within
measurement error.  The observed between-route sd is 0.80 Hz.  Two readings:
  (a) the frequency genuinely varies  -> a firmware divider is EXCLUDED
  (b) the estimator is just noisy     -> the question stays open
These are separated by a WITHIN-route split-half control plus a SYNTHETIC fixed-frequency
control that calibrates how much scatter the estimator manufactures on its own.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
rng = np.random.default_rng(11803)
FS = 100.0
ROUTES = ['r77','r21','ra6','r1e','ra4','r7e','r7f','r95','r81','r82',
          'r78','r79','r85','r96','r9e','ra5','r22','r24','r97']

def runs(tag, minlen):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p): return []
    z = np.load(p, allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): return []
    lat = np.asarray(z['cc_lat']).astype(float); v = np.asarray(z['cs_v']).astype(float)
    a = np.asarray(z['cs_tq']).astype(float)
    n = min(len(lat), len(v), len(a)); lat, kmh, a = lat[:n], v[:n]*3.6, a[:n]
    ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0) & np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return [a[i:j] for i, j in zip(st, en) if (j-i) >= minlen and np.std(a[i:j]) > 0]

def est(segs, NPS, lo=6.5, hi=10.5):
    acc = []
    for s in segs:
        f, P = signal.welch(s - s.mean(), FS, nperseg=NPS, noverlap=NPS//2)
        acc.append(P)
    M = np.median(np.asarray(acc), 0)
    m = (f >= lo) & (f <= hi); idx = np.where(m)[0]
    k = idx[int(np.argmax(M[idx]))]
    if k <= 0 or k >= len(M)-1: return f[k]
    a_, b_, c_ = (np.log(M[k-1]+1e-30), np.log(M[k]+1e-30), np.log(M[k+1]+1e-30))
    den = a_ - 2*b_ + c_
    return f[k] + (0.5*(a_-c_)/den if den != 0 else 0.0)*(f[1]-f[0])

for NPS in (512, 1024):
    print('=' * 78)
    print('nperseg=%d   df = %.4f Hz' % (NPS, FS/NPS))
    full, halves = [], []
    for tag in ROUTES:
        segs = runs(tag, NPS)
        if len(segs) < 6: continue          # need >=3 per half
        A, B = segs[0::2], segs[1::2]
        fa, fb, ff = est(A, NPS), est(B, NPS), est(segs, NPS)
        full.append(ff); halves.append((tag, fa, fb, abs(fa-fb)))
    if len(full) < 4:
        print('  too few routes with >=6 segments'); continue
    full = np.asarray(full)
    dif = np.asarray([h[3] for h in halves])
    # sd of a single estimate implied by the split-half differences:
    #   each half uses ~n/2 segments, so sd(half-diff) = sqrt(2)*sd_half, and
    #   sd_full = sd_half/sqrt(2)  =>  sd_full = sd(diff)/2
    sd_within = float(np.std(dif, ddof=1)) / 2.0
    sd_between = float(np.std(full, ddof=1))
    print('  routes usable: %d' % len(full))
    print('  BETWEEN-route sd of the peak      : %.4f Hz' % sd_between)
    print('  WITHIN-route sd implied by split  : %.4f Hz  (median |A-B| = %.4f)'
          % (sd_within, float(np.median(dif))))
    ex = sd_between**2 - sd_within**2
    print('  excess (true route-to-route) sd   : %s'
          % ('%.4f Hz' % np.sqrt(ex) if ex > 0 else 'NONE -- within >= between'))
    print('  per route:  tag   halfA    halfB    |diff|')
    for tag, fa, fb, d in halves:
        print('              %-5s %7.4f %8.4f %8.4f' % (tag, fa, fb, d))

    # ---- synthetic control: a TRULY fixed 8.3333 Hz mode in 1/f^1.5 noise --------
    print('  --- CONTROL: synthetic FIXED 8.3333 Hz line, matched segment counts ---')
    nseg = int(np.median([len(runs(t, NPS)) for t in ROUTES if len(runs(t, NPS)) >= 6]))
    for snr in (0.5, 1.0, 2.0):
        outs = []
        for _ in range(40):
            segs = []
            for _ in range(nseg):
                L = NPS + int(rng.integers(0, NPS))
                w = rng.standard_normal(L)
                W = np.fft.rfft(w); fr = np.fft.rfftfreq(L, 1/FS); fr[0] = fr[1]
                w = np.fft.irfft(W / fr**0.75, n=L)
                w /= (np.std(w) + 1e-12)
                t = np.arange(L)/FS
                segs.append(w + snr*np.sin(2*np.pi*(100.0/12.0)*t + rng.uniform(0, 6.28)))
            outs.append(est(segs, NPS))
        outs = np.asarray(outs)
        print('    SNR %.1f : mean %.4f Hz  sd %.4f Hz  (truth 8.3333)'
              % (snr, outs.mean(), outs.std(ddof=1)))
