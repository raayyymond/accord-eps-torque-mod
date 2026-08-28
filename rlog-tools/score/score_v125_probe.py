# -*- coding: utf-8 -*-
"""SCORE THE V125 PROBE -- the delivered phase of reader #3 against wheel rate at 6-9 Hz.

V125 repoints CAN 427 onto gp-0x6AF0 (reader #3's output, FUN_0002b62c) with the packer at
sar 4, so the wire carries  clamp(|gp-0x6af0| * 5 >> 4, 0, 0x3FF)  -- max 960 of 1023 on the
+-3072 engaged clamp, no clipping, LSB 3.20 counts.

THE ONE QUESTION: is reader #3's delivered contribution DAMPING or ANTI-DAMPING at 6-9 Hz?

That decides whether 0xC642A/0xC642C (=194, virgin, fc 30.15 Hz, passing 97 % of 7.8 Hz)
is a usable lever or a closed one:
    delivered phase near +90 deg vs wheel rate  -> DAMPING  -> cutting it is the V94 direction, CLOSED
    delivered phase near -90 deg vs wheel rate  -> ANTI-DAMPING -> cutting it HELPS, USABLE

This is the same measurement that settled gp-0x6b26 after V94 (+137/+139 deg => a real damper).

METHOD, matching that precedent:
  - engaged windows only, wheel rate from cs_rate
  - cross-spectrum of the 427 wire against wheel rate, 6-9 Hz, coherence-weighted
  - omega-partialled: the wire is a MAGNITUDE (|x|), so its sign is lost.  The recoverable
    quantity is the phase of its ENVELOPE against the rate envelope, plus Re(Z) sign via the
    magnitude-rate cross-spectrum.  Both are reported, and the SHUFFLED control is mandatory.

USAGE:  python rlog-tools/score/score_v125_probe.py <route>       e.g. r26
"""
import os, sys
import numpy as np
from scipy import signal

FS, NW = 100.0, 256
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')
CLAMP = 3072.0
LSB = 16.0 / 5.0                      # sar 4: wire = |x|*5>>4  =>  1 wire count = 3.20 src counts


def run(tag):
    p = os.path.join(CACHE, tag, '%s.npz' % tag)
    if not os.path.exists(p):
        print('  no cache at %s' % p); return
    z = np.load(p, allow_pickle=True)
    g = lambda k: np.asarray(z[k]).astype(float) if k in z.files else None
    rate, lat, v = g('cs_rate'), g('cc_lat'), g('cs_v')
    wire = None
    for k in ('ab_mt', 'mag427', 'probe'):
        if g(k) is not None:
            wire = g(k); wname = k; break
    if wire is None:
        print('  no 427 channel in the cache'); return
    n = min(len(rate), len(lat), len(v), len(wire))
    rate, lat, v, wire = rate[:n], lat[:n], v[:n], wire[:n]
    src = wire * LSB                                   # back to gp-0x6af0 counts

    print('\n=== %s : V125 probe, 427 <- gp-0x6AF0 (reader #3 output) ===' % tag)
    e = (lat > 0.5) & (v > 1.0) & np.isfinite(src)
    q = src[e]
    print('  engaged n=%d   |gp-0x6af0| p50 %.0f  p90 %.0f  p99 %.0f  max %.0f   (clamp %.0f)'
          % (e.sum(), *np.percentile(q, [50, 90, 99]), q.max(), CLAMP))
    print('  saturation duty (wire >= 1023): %.4f %%' % (100 * np.mean(wire[e] >= 1022.5)))
    if q.max() >= CLAMP * 0.99:
        print('  NOTE: the source itself is reaching its own +-3072 clamp -- reader #3 rails.')

    # cross-spectrum of the magnitude against |rate|, 6-9 Hz, with a shuffled control
    rng = np.random.default_rng(0)
    segs, rr = [], []
    for a in range(0, n - NW, NW // 2):
        s = slice(a, a + NW)
        if lat[s].mean() < 0.99 or v[s].mean() < 1.0:
            continue
        if not (np.isfinite(src[s]).all() and np.isfinite(rate[s]).all()):
            continue
        segs.append(src[s] - src[s].mean())
        rr.append(np.abs(rate[s]) - np.abs(rate[s]).mean())
    if len(segs) < 40:
        print('  too few engaged windows (%d)' % len(segs)); return
    print('  %d engaged windows' % len(segs))

    def xphase(A, B):
        ph, co = [], []
        for x, y in zip(A, B):
            f, Pxy = signal.csd(x, y, FS, nperseg=NW)
            _, C = signal.coherence(x, y, FS, nperseg=NW)
            b = (f >= 6) & (f <= 9)
            w = C[b]
            if w.sum() <= 0:
                continue
            ph.append(np.angle(np.sum(Pxy[b] * w)))
            co.append(np.mean(w))
        return np.degrees(np.angle(np.mean(np.exp(1j * np.array(ph))))), float(np.mean(co))

    p_real, c_real = xphase(segs, rr)
    idx = rng.permutation(len(rr))
    p_shuf, c_shuf = xphase(segs, [rr[i] for i in idx])
    print('\n  |gp-0x6af0| vs |wheel rate|, 6-9 Hz:')
    print('     REAL      phase %+7.1f deg   mean coherence %.3f' % (p_real, c_real))
    print('     SHUFFLED  phase %+7.1f deg   mean coherence %.3f' % (p_shuf, c_shuf))
    print('     => %s' % ('coherence clears the shuffled control -- the phase is meaningful'
                          if c_real > 1.5 * c_shuf else
                          'coherence does NOT clear its control -- the phase is NOT interpretable'))
    print('\n  READ IT AS:')
    print('     phase near +90 deg  -> reader #3 DAMPS 6-9 Hz -> cutting 0xC642A/C is the V94')
    print('                            direction  =>  the lever is CLOSED')
    print('     phase near -90 deg  -> reader #3 ANTI-DAMPS   -> cutting it HELPS')
    print('                            =>  build 0xC642A/0xC642C 194 -> ~29')
    print('     ambiguous / low coherence -> NOT RESOLVED; do not build either way')


for t in sys.argv[1:] or ['r26']:
    run(t)
