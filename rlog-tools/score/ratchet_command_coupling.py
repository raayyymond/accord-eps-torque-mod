# -*- coding: utf-8 -*-
"""Band-SPECIFIC command->torque coupling: ratchet-band coherence minus control-band.

Raw coherence was inconclusive because command->torque coupling is broadband -- the
30-40 Hz control band scored as high as the ratchet band on most routes.  The specificity
contrast removes that: only excess coherence AT the ratchet frequency counts.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
BAND, CTRL = (7.0, 10.5), (30.0, 40.0)
R = [('r78','V91'),('r7e','V96'),('r7f','V96'),('r96','V102'),('ra4','V104'),
     ('ra6','V106'),('r1e','V107'),('r22','V112'),('r24','V122')]

def segs(tag, chans):
    p = 'analysis-2020accord/_scratch/cache/%s/%s.npz' % (tag, tag)
    if not os.path.exists(p): return []
    z = np.load(p, allow_pickle=True)
    if any(c not in z.files for c in chans): return []
    lat = np.asarray(z['cc_lat']).astype(float); v = np.asarray(z['cs_v']).astype(float)
    A = [np.asarray(z[c]).astype(float) for c in chans]
    n = min([len(lat), len(v)] + [len(a) for a in A])
    lat, kmh = lat[:n], v[:n]*3.6; A = [a[:n] for a in A]
    ok = (lat > 0.5) & (kmh >= 1.0) & (kmh < 24.0)
    for a in A: ok &= np.isfinite(a)
    d = np.diff(np.concatenate(([0], ok.view(np.int8), [0])))
    st, en = np.where(d == 1)[0], np.where(d == -1)[0]
    return [tuple(a[i:j] for a in A) for i, j in zip(st, en)
            if (j-i) >= NPS and all(np.std(a[i:j]) > 0 for a in A)]

def spec(pairs):
    acc, f = [], None
    for x, y in pairs:
        f, C = signal.coherence(x-x.mean(), y-y.mean(), FS, nperseg=NPS//2, noverlap=NPS//4)
        acc.append(C)
    M = np.median(np.asarray(acc), 0)
    return float(np.max(M[(f>=BAND[0])&(f<=BAND[1])]) - np.max(M[(f>=CTRL[0])&(f<=CTRL[1])]))

def shuf(a, rng):
    F = np.fft.rfft(a - a.mean()); ph = rng.uniform(0, 2*np.pi, len(F)); ph[0] = 0
    return np.fft.irfft(np.abs(F)*np.exp(1j*ph), len(a))

print('%-6s %-6s %-5s %-10s %-11s %s' % ('route','build','nseg','specificity','shuf p95','verdict'))
vals = []
for tag, bld in R:
    s = segs(tag, ('co_tqcan', 'cs_tq'))
    if len(s) < 4:
        print('%-6s %-6s %-5d  -- too few' % (tag, bld, len(s))); continue
    v = spec(s)
    rng = np.random.default_rng(0)
    null = [spec([(shuf(x, rng), y) for x, y in s]) for _ in range(40)]
    p95 = float(np.percentile(null, 95))
    print('%-6s %-6s %-5d %-+10.3f %-+11.3f %s'
          % (tag, bld, len(s), v, p95, 'SPECIFIC' if v > p95 else 'not specific'))
    vals.append(v)
vals = np.asarray(vals)
b = [np.median(np.random.default_rng(s).choice(vals, len(vals))) for s in range(4000)]
print('\nacross routes: median %+.3f  95%% CI [%+.3f, %+.3f]  (zero = no ratchet-specific coupling)'
      % (np.median(vals), np.percentile(b, 2.5), np.percentile(b, 97.5)))
