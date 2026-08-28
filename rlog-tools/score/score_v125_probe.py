# -*- coding: utf-8 -*-
"""SCORE THE V125 PROBE -- the delivered phase of reader #3 against wheel rate at 6-9 Hz.

V125 repoints CAN 427 (0x1AB) onto gp-0x6AF0 (reader #3's output) with the packer at sar 4:
    wire = min((abs(raw) * 5) >> 4, 0x3FF)

THE ONE QUESTION: is reader #3's delivered contribution DAMPING or ANTI-DAMPING at 6-9 Hz?
That decides whether 0xC642A/0xC642C (=194, virgin, fc 30.15 Hz, passing 97 % of 7.8 Hz) is a
usable lever or a closed one.

THREE TRAPS THIS SCRIPT EXISTS TO AVOID -- all three bit an earlier version of it, 2026-08-28:

  1. 427 IS A 50 Hz CHANNEL.  It arrives at 49.9 Hz; cs_rate arrives at 99.8 Hz.  Truncating
     both to a common INDEX misaligns them by 2x and destroys the measurement -- it took
     coherence from 0.512 to 0.049.  ALWAYS regrid on TIME.
  2. NYQUIST IS 24.95 Hz.  The 21-26 Hz grind band STRADDLES it, so this wire CANNOT measure
     grind #1.  It is a 6-9 Hz instrument only.
  3. raw14_b4 IS NOT THIS WIRE.  It is CAN 0x14A byte 4 -- a legacy 5-bit field (bits 7:3) that
     post-V106 builds do NOT write.  On r24 its low 3 bits are constant and its content is
     Honda's, yet the extractor still labels it "probe".  The 427 wire is ((b0 & 3) << 8) | b1.

POSITIVE CONTROL, MEASURED ON r24 (V122), whose tap is gp-0x6ABC = wheel rate x 4.7121:
    corr(|rate|, wire)        = +0.9832
    corr(packer model, wire)  = +0.9832   (p50 2 vs 3, p99 319 vs 321 -- byte-accurate)
    coherence 6-9 Hz 0.335, permutation null 0.074 +- 0.004  =>  EXCESS 0.261, z ~ +60
=> the instrument is sound.  Run "--control r24" any time this script is changed; if the
   EXCESS moves, the script broke, not the car.

THE BAR IS THE EXCESS, NOT THE RAW COHERENCE.  Welch coherence from n segments is biased up
by ~1/n even for independent signals, so a raw number means nothing on its own -- and a RATIO
against the floor is equally arbitrary.  The permutation null measures the floor directly;
what has to clear zero is (real - null), in units of the null's own spread.

USAGE:  python rlog-tools/score/score_v125_probe.py <route> [--control r24]
"""
import os, sys, glob
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # rlog-tools
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
RLOGS = os.path.join(ROOT, 'analysis-2020accord', 'rlogs')
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS = 50.0                 # the 427 channel's own rate -- NOT 100
NW = 512                  # 10.24 s windows at 50 Hz -- LONG ON PURPOSE, see below
NP = 64                   # 1.28 s Welch segments => ~15 per window
# COHERENCE BIAS: a magnitude-squared coherence estimated from n Welch segments is biased
# upward by ~1/n even for INDEPENDENT signals.  At NW=128/NP=64 that is only ~3 segments and
# the shuffled control read 0.347 -- nearly the 0.510 of the real pairing, i.e. almost all
# "coherence" was bias.  NW=512 gives ~15 segments and a ~0.07 floor.  If you shorten NW,
# re-run --control r24 and check the SHUFFLED number, not just the real one.
RATE_SCALE = 4.7121       # ct/(deg/s), for the r24 control only
PREFIX = {'r24': '75604b0a432fdc89_00000024--6f4943e0a6'}


def read_427(tag):
    """0x1AB frames straight from the rlogs -- the cache carries no 427 timebase."""
    import zstandard
    from cereal import log as clog
    pre = PREFIX.get(tag)
    if pre is None:
        cands = sorted(glob.glob(os.path.join(RLOGS, '*_000000%s--*--rlog.zst' % tag[1:])))
        if not cands:
            return None, None
        pre = '--'.join(os.path.basename(cands[0]).split('--')[:2])
    segs = sorted(glob.glob(os.path.join(RLOGS, '%s--*--rlog.zst' % pre)),
                  key=lambda p: int(os.path.basename(p).split('--')[2]))
    T, B = [], []
    for p in segs:
        with open(p, 'rb') as fh:
            data = zstandard.ZstdDecompressor().stream_reader(fh).read()
        for evt in clog.Event.read_multiple_bytes(data):
            try:
                if evt.which() != 'can':
                    continue
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            for m in evt.can:
                if int(m.address) == 0x1AB:
                    d = bytes(m.dat)
                    T.append(tm)
                    B.append((d[0] if len(d) > 0 else 0, d[1] if len(d) > 1 else 0))
    if not T:
        return None, None
    B = np.array(B, int)
    return np.array(T), (((B[:, 0] & 0x03) << 8) | B[:, 1]).astype(float)


def grid(tag):
    at, wire = read_427(tag)
    if at is None:
        print('  no 0x1AB frames for %s' % tag)
        return None
    z = np.load(os.path.join(CACHE, tag, '%s.npz' % tag), allow_pickle=True)
    g = lambda k: np.asarray(z[k]).astype(float)
    t = g('t')
    at = at - float(np.asarray(z['t0_mono']).ravel()[0])
    a, b = max(t.min(), at.min()), min(t.max(), at.max())
    tg = np.arange(a, b, 1.0 / FS)
    out = dict(t=tg, wire=np.interp(tg, at, wire))
    for k, n in (('cs_rate', 'rate'), ('cc_lat', 'lat'), ('cs_v', 'v'), ('ang', 'ang')):
        out[n] = np.interp(tg, t, g(k)) if k in z.files else np.zeros_like(tg)
    print('  %s: %d 0x1AB frames at %.1f Hz -> %d samples on a %.0f Hz grid'
          % (tag, len(wire), len(wire) / (at.max() - at.min()), len(tg), FS))
    return out


def band(x, y, lo=6.0, hi=9.0):
    """coherence-weighted cross-phase and mean coherence over [lo, hi]."""
    ph, co = [], []
    for a in range(0, len(x) - NW, NW // 2):
        s = slice(a, a + NW)
        u, w = x[s] - x[s].mean(), y[s] - y[s].mean()
        if not (np.isfinite(u).all() and np.isfinite(w).all()) or u.std() == 0 or w.std() == 0:
            continue
        f, Pxy = signal.csd(u, w, FS, nperseg=NP, noverlap=NP // 2)
        _, C = signal.coherence(u, w, FS, nperseg=NP, noverlap=NP // 2)
        m = (f >= lo) & (f <= hi)
        if C[m].sum() <= 0:
            continue
        ph.append(np.angle(np.sum(Pxy[m] * C[m])))
        co.append(C[m].mean())
    if len(ph) < 30:
        return None, None, len(ph)
    return (np.degrees(np.angle(np.mean(np.exp(1j * np.array(ph))))),
            float(np.mean(co)), len(ph))


def null(x, y, k=20):
    """Permutation null for the coherence floor: k shuffles, mean and sd of the estimate."""
    rng = np.random.default_rng(0)
    v = []
    for _ in range(k):
        _, c, _ = band(x, y[rng.permutation(len(y))])
        if c is not None:
            v.append(c)
    return (float(np.mean(v)), float(np.std(v))) if v else (0.0, 1.0)


def control(tag='r24'):
    d = grid(tag)
    if d is None:
        return
    e = (d['lat'] > 0.99) & (d['v'] > 1.0)
    r, w = np.abs(d['rate'])[e], d['wire'][e]
    pred = np.minimum((np.minimum(np.abs(d['rate'][e]) * RATE_SCALE, 65535) * 5).astype(np.int64) >> 3,
                      0x3FF)
    print('\n  POSITIVE CONTROL (%s taps gp-0x6ABC = wheel rate x %.4f)' % (tag, RATE_SCALE))
    print('     corr(|rate|, wire)       %+.4f    EXPECT +0.98' % np.corrcoef(r, w)[0, 1])
    print('     corr(packer model, wire) %+.4f    EXPECT +0.98'
          % np.corrcoef(pred.astype(float), w)[0, 1])
    p, c, n = band(w, r)
    mu, sd = null(w, r)
    print('     coherence 6-9 Hz  %.3f REAL vs null %.3f +- %.3f  over %d windows' % (c, mu, sd, n))
    print('     EXCESS %.3f   z = %+.1f      EXPECT excess ~0.26' % (c - mu, (c - mu) / max(sd, 1e-6)))
    print('     => %s' % ('INSTRUMENT OK' if (c - mu) > 0.10 and (c - mu) > 4 * sd else
                          'INSTRUMENT BROKEN -- fix this script before trusting any probe'))


def run(tag):
    d = grid(tag)
    if d is None:
        return
    e = (d['lat'] > 0.99) & (d['v'] > 1.0)
    w, r = d['wire'][e], np.abs(d['rate'])[e]
    print('\n=== %s : V125 probe, 427 <- gp-0x6AF0 (reader #3 output), sar 4 ===' % tag)
    print('  engaged n=%d   wire p50 %.0f  p90 %.0f  p99 %.0f  max %.0f   (field max 1023)'
          % (e.sum(), *np.percentile(w, [50, 90, 99]), w.max()))
    sat = float(np.mean(w >= 1022.5))
    print('  saturation duty (wire >= 1023): %.4f %%' % (100 * sat))
    if sat > 0.01:
        print('  RAILING -- the phase is measured on a clipped signal; downgrade the verdict')
    p, c, n = band(w, r)
    if p is None:
        print('  too few engaged windows (%d)' % n)
        return
    rng = np.random.default_rng(0)
    ps, cs, _ = band(w, r[rng.permutation(len(r))])
    print('\n  |gp-0x6af0| vs |wheel rate|, 6-9 Hz, over %d windows:' % n)
    print('     REAL      phase %+7.1f deg   mean coherence %.3f' % (p, c))
    print('     SHUFFLED  phase %+7.1f deg   mean coherence %.3f' % (ps, cs))
    ok = c > 0.30 and c > 5 * cs
    print('     => %s' % ('coherence clears its control AND the 0.30 floor -- phase is meaningful'
                          if ok else
                          'coherence FAILS the bar (>0.30 and >5x shuffled) -- NOT interpretable'))
    print('\n  READ IT AS:')
    print('     phase near +90 deg -> reader #3 DAMPS 6-9 Hz -> cutting 0xC642A/C is the V94')
    print('                           direction  =>  the lever is CLOSED')
    print('     phase near -90 deg -> reader #3 ANTI-DAMPS   -> cutting it HELPS')
    print('                           =>  build 0xC642A/0xC642C 194 -> ~29')
    print('     ambiguous / low coherence -> NOT RESOLVED; do not build either way')
    if ok:
        print('\n  VERDICT: %s' % ('DAMPS -> 0xC642A/C CLOSED' if 30 < p < 150 else
                                   'ANTI-DAMPS -> 0xC642A/C USABLE' if -150 < p < -30 else
                                   'phase is not near +-90 deg -> NOT RESOLVED'))


args = sys.argv[1:]
if '--control' in args:
    i = args.index('--control')
    control(args[i + 1] if i + 1 < len(args) else 'r24')
else:
    for t in args or ['r26']:
        run(t)
