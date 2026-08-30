# -*- coding: utf-8 -*-
"""Is the Re(Z)-vs-amplitude trend just REGRESSION DILUTION?

At small A the SNR is low, and Re(Z)=CSD/PSD is biased toward zero when noisy. That alone would
produce a -23 -> -65 shape with no mechanism. The discriminator is COHERENCE per decile:

  coherence RISES with A  -> dilution is live, the trend may be an artefact
  coherence FLAT with A   -> dilution is not available as an explanation

Also reports the trend restricted to HIGH-COHERENCE windows only, where dilution is weakest.
"""
import glob
import os
import sys

import numpy as np
from scipy import signal, stats

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WIN_S = 2.0


def wins(t, q, r, eng, fs, band):
    lo, hi = band[0] / (fs / 2), band[1] / (fs / 2)
    if hi >= 1.0:
        return []
    b, a = signal.butter(3, [lo, hi], btype='band')
    qf = signal.filtfilt(b, a, q - q.mean())
    rf = signal.filtfilt(b, a, r - r.mean())
    qa, ra = signal.hilbert(qf), signal.hilbert(rf)
    n = int(WIN_S * fs)
    out = []
    for i in range(0, len(t) - n, n):
        sl = slice(i, i + n)
        if eng[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        # magnitude-squared coherence of the two analytic signals in this window
        cxy = np.mean(qq * np.conj(rr))
        coh = float(np.abs(cxy) ** 2 / max(den * float(np.mean(np.abs(qq) ** 2)), 1e-30))
        out.append((float(np.sqrt(den)), float((cxy / den).real), coh))
    return out


def show(rows, label):
    if len(rows) < 200:
        print('  %s: too few (%d)' % (label, len(rows)))
        return
    A = np.array([a for a, _, _ in rows])
    Z = np.array([z for _, z, _ in rows])
    C = np.array([c for _, _, c in rows])
    q = np.quantile(A, np.linspace(0, 1, 11))
    print('\n  %s   %d windows' % (label, len(rows)))
    print('  %-6s %10s %11s %11s %8s' % ('decile', 'A median', 'Re(Z) med', 'coherence', 'n'))
    print('  ' + '-' * 50)
    for i in range(10):
        m = (A >= q[i]) & ((A <= q[i + 1]) if i == 9 else (A < q[i + 1]))
        if m.sum() < 5:
            continue
        print('  %-6d %10.4f %11.2f %11.3f %8d'
              % (i + 1, np.median(A[m]), np.median(Z[m]), np.median(C[m]), m.sum()))
    print('  ' + '-' * 50)
    print('  rho(A, coherence) = %+.3f  p %.1e' % stats.spearmanr(A, C)[:2])
    hi = C >= np.quantile(C, 0.5)
    print('  rho(A, Re(Z)) all windows          = %+.3f' % stats.spearmanr(A, Z).correlation)
    print('  rho(A, Re(Z)) HIGH-COHERENCE half  = %+.3f  (n=%d)'
          % (stats.spearmanr(A[hi], Z[hi]).correlation, hi.sum()))
    if hi.sum() > 100:
        qq = np.quantile(A[hi], [0.1, 0.9])
        lo_m = A[hi] <= qq[0]
        hi_m = A[hi] >= qq[1]
        print('  within HIGH-COHERENCE: Re(Z) low-A %+.1f  vs  high-A %+.1f'
              % (np.median(Z[hi][lo_m]), np.median(Z[hi][hi_m])))


def main():
    print('=' * 84)
    print('  IS THE Re(Z)-vs-AMPLITUDE TREND JUST REGRESSION DILUTION?')
    print('=' * 84)
    band, ctl = [], []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
            continue
        seen.add(r)
        t = np.asarray(z['t'], float)
        n = len(t)
        q = np.asarray(z['tq'], float)[:n]
        ra = np.asarray(z['cs_rate'], float)[:n]
        e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
        if len(q) < n or len(ra) < n:
            continue
        fs = 1.0 / np.median(np.diff(t))
        band += wins(t, q, ra, e, fs, (6.0, 9.5))
        ctl += wins(t, q, ra, e, fs, (22.0, 30.0))
    show(band, '6-9.5 Hz')
    show(ctl, '22-30 Hz control')


if __name__ == '__main__':
    main()
