# -*- coding: utf-8 -*-
"""IS THE 50-72 Hz AUDIO THE SECOND HARMONIC OF THE 22-40 Hz MECHANICAL PUMPING?

22-40 Hz doubled is 44-80 Hz, which is almost exactly the band where the audio shows licensed
LKAS excess. If that is a harmonic relationship rather than a coincidence, then cutting the pumping
(V232) also removes the audible grinding, and the one-biquad trade between V231 and V232 dissolves.

TEST: per engaged window, find the dominant MECHANICAL frequency in 22-40 Hz (wheel rate, CAN) and the
dominant AUDIO frequency in 44-80 Hz. If harmonic, audio_peak / mech_peak clusters at 2.00.

CONTROL, and it is the point of the design: the same ratio computed on SHUFFLED window pairings. A
harmonic lock must beat its own shuffled null, otherwise the clustering is just an artifact of two
bounded ranges whose quotient is mechanically confined near 2.
"""
import glob, os, sys
import numpy as np
from scipy.signal import welch
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
RNG = np.random.default_rng(20260830)

rows = []
for ap in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*_grind.npz')):
    tag = os.path.basename(ap).split('_grind')[0]
    cp = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(cp):
        continue
    g = np.load(ap, allow_pickle=True); c = np.load(cp, allow_pickle=True)
    if not {'cc_lat', 'cs_v', 'cs_rate', 't'} <= set(c.files):
        continue
    f_a = np.asarray(g['sp_f']).astype(float)
    sp = np.asarray(g['sp']).astype(float)
    ts = np.asarray(g['t_sp']).astype(float)
    tc = np.asarray(c['t']).astype(float)
    fs = 1.0 / np.median(np.diff(tc))
    rate = np.asarray(c['cs_rate']).astype(float)
    eng = np.asarray(c['cc_lat']).astype(float) > 0.5
    mov = np.abs(np.asarray(c['cs_v']).astype(float)) > 0.3
    m = eng & mov
    n = int(round(8 * fs))
    idx = np.flatnonzero(m)
    mech, aud = [], []
    for run in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
        for k in range(0, len(run) - n + 1, n):
            w = run[k:k + n]
            x = rate[w] - rate[w].mean()
            fm, pm = welch(x, fs=fs, nperseg=min(len(w), int(round(4 * fs))))
            b = (fm >= 22) & (fm < 40)
            if not b.any() or pm[b].max() <= 0:
                continue
            fpk = fm[b][np.argmax(pm[b])]
            t0, t1 = tc[w[0]], tc[w[-1]]
            sel = (ts >= t0) & (ts <= t1)
            if sel.sum() < 3:
                continue
            aband = (f_a >= 44) & (f_a < 80)
            spa = sp[sel][:, aband].mean(axis=0)
            if spa.max() <= 0:
                continue
            apk = f_a[aband][np.argmax(spa)]
            mech.append(fpk); aud.append(apk)
    if len(mech) >= 20:
        rows.append((tag, np.array(mech), np.array(aud)))

print('=' * 96)
print('  IS THE 50-72 Hz AUDIO THE 2nd HARMONIC OF THE 22-40 Hz PUMPING?')
print('=' * 96)
print()
if not rows:
    print('  no route yields enough paired windows.'); raise SystemExit
allm = np.concatenate([r[1] for r in rows]); alla = np.concatenate([r[2] for r in rows])
print('  %-6s %6s %12s %12s %14s %14s' % ('route', 'n', 'mech peak', 'audio peak', 'ratio med', 'shuffled'))
per = []
for tag, mm, aa in rows:
    r = aa / mm
    sh = aa[RNG.permutation(len(aa))] / mm
    per.append((np.median(r), np.median(sh)))
    print('  %-6s %6d %11.1f %11.1f %13.3f %13.3f'
          % (tag, len(mm), np.median(mm), np.median(aa), np.median(r), np.median(sh)))
print()
r_all = alla / allm
sh_all = alla[RNG.permutation(len(alla))] / allm
print('  pooled n=%d   ratio median %.3f   shuffled median %.3f' % (len(r_all), np.median(r_all), np.median(sh_all)))
# how tightly does the ratio sit at 2.00, vs the shuffled null?
tol = 0.10
hit = np.mean(np.abs(r_all - 2.0) < tol); hit_s = np.mean(np.abs(sh_all - 2.0) < tol)
print('  P(|ratio - 2.00| < %.2f)  real %.3f   shuffled %.3f   lift %.2fx'
      % (tol, hit, hit_s, hit / max(hit_s, 1e-9)))
bs = np.array([np.mean(np.abs((alla[RNG.integers(0, len(alla), len(alla))] / allm) - 2.0) < tol)
               for _ in range(2000)])
lo, hi = np.percentile(bs, [2.5, 97.5])
print('  shuffled-null 95%% band for that probability: [%.3f, %.3f]' % (lo, hi))
print()
if hit > hi:
    print('  => the ratio locks at 2.00 ABOVE its own shuffled null: HARMONIC relationship supported.')
else:
    print('  => the ratio does NOT beat its shuffled null. NO harmonic lock is demonstrated;')
    print('     the 44-80 Hz audio is not shown to be the second harmonic of the pumping, and the')
    print('     V231-vs-V232 trade does NOT dissolve.')
