# -*- coding: utf-8 -*-
"""SCORE V127 -- the RAIL DUTY of gp-0x6b26, the one quantity this kit has measured wrong.

V127 puts gp-0x6B26 on CAN 427 (0x1AB) with the packer at sar 2:
    wire = min((|gp-0x6b26| * 5) >> 2, 0x3FF)
so the +-511 clamp maps to wire 638 of 1023 -- no clipping, LSB 0.8 counts, and the rail is
directly countable.  Inverse: |gp-0x6b26| = wire * 4/5.

WHY THIS ENDPOINT
-----------------
V107 predicted a rail duty of <=1.05 % and MEASURED 33.49 % -- a 32x miss -- because
gp-0x6b26 -> aggregator -> motor -> motor rate -> gp-0x6c2c is a CLOSED LOOP and the prediction
was open-loop.  No open-loop duty prediction on this lane can be trusted, so V127 measures it.

A railed acceleration term is sign(alpha)*511: a bang-bang Coulomb relay, which is
accord-v80-damper-relay-and-grind1-inert's measured mechanism.  A relay ratchets; it does not
damp.  De-railing is the whole point of the build.

WHAT IS AND IS NOT MEASURABLE ON THIS WIRE
-------------------------------------------
427 arrives at 49.9 Hz => Nyquist 24.95 Hz, and the lane's -3 dB band is 25-153 Hz.  So this
wire CANNOT measure the lane's SPECTRUM -- exactly the blindness that voided V107's safety case.
RAIL DUTY is a LEVEL statistic, and undersampling an ergodic signal leaves the duty estimate
unbiased.  This script reports duty and distribution ONLY, and refuses to report a spectrum.

PRE-REGISTERED, BEFORE THE DRIVE (see docs/scoring/SCORING-V127-preregistered.md)
---------------------------------------------------------------------------------
Primary endpoint: engaged rail duty, stratified by speed on V107's own bins.
    <= 2 %  in every bin        -> DE-RAILED.  The term is linear; the fix is in force.
    2-10 %  in any bin          -> PARTIAL.  Consider the next rung, the mode record 0xCBE74 (the NORMAL LERP rails at mid speed too).
    > 10 %  in any bin          -> STILL RAILING.  Go to -1966.
Interpretable from ONE drive with no matched control, which is the kit's build-design law.

Bootstrap is over EPISODES, never windows (feedback-episodes-not-windows).

USAGE:  python rlog-tools/score/score_v126_rail.py <route> [--control r24]
"""
import os, sys, glob
import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))      # rlog-tools
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
RLOGS = os.path.join(ROOT, 'analysis-2020accord', 'rlogs')
CACHE = os.path.join(ROOT, 'analysis-2020accord', '_scratch', 'cache')

FS = 50.0                    # the 427 channel's own rate -- NOT 100
# 🛑 THESE MUST MATCH THE IMAGE THAT FLEW.
#   V127 / V129 / V130 / V131 : clamp 511, sar 2  -> rail wire 638
#   V133                      : clamp 1023, sar 3 -> rail wire 639
# V132 shipped clamp 1023 with sar 2, which CLIPS at |x| = 819 BELOW its own clamp; it was
# superseded before flight and its artifacts deleted.  If a cache ever comes from it, the
# wrong-build guard below fires because the wire reaches 1023.
import os as _os
_V133 = _os.environ.get('ACCORD_RAIL_V133', '').strip() not in ('', '0', 'no')
CLAMP = 1023 if _V133 else 511      # cal(0xC407E)
SAR = 3 if _V133 else 2
RAIL_WIRE = min((CLAMP * 5) >> SAR, 0x3FF)          # 638
LSB = (1 << SAR) / 5.0                              # 0.8 counts per wire step
BINS = [(0, 10), (10, 25), (25, 40), (40, 64), (64, 200)]
V107_MEASURED = {(0, 10): 0.0168, (10, 25): 0.3232, (25, 40): 0.2127,
                 (40, 64): 0.0427, (64, 200): 0.0023}
PREFIX = {'r24': '75604b0a432fdc89_00000024--6f4943e0a6'}


def read_427(tag):
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
    for k, n in (('cs_rate', 'rate'), ('cc_lat', 'lat'), ('cs_v', 'v')):
        out[n] = np.interp(tg, t, g(k)) if k in z.files else np.zeros_like(tg)
    print('  %s: %d 0x1AB frames at %.1f Hz -> %d samples on a %.0f Hz grid'
          % (tag, len(wire), len(wire) / (at.max() - at.min()), len(tg), FS))
    return out


def episodes(mask, tg, min_s=3.0):
    """contiguous engaged runs, so the bootstrap resamples EPISODES not windows."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if (tg[j - 1] - tg[i]) >= min_s:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def boot(eps, hit, tot, k=4000, seed=0):
    """episode bootstrap of a duty; returns (point, lo, hi) or None if too few episodes."""
    if len(eps) < 4 or tot.sum() == 0:
        return None
    rng = np.random.default_rng(seed)
    h = np.array([hit[a:b].sum() for a, b in eps], float)
    m = np.array([tot[a:b].sum() for a, b in eps], float)
    if m.sum() == 0:
        return None
    pt = h.sum() / m.sum()
    idx = rng.integers(0, len(eps), size=(k, len(eps)))
    num, den = h[idx].sum(1), m[idx].sum(1)
    ok = den > 0
    if ok.sum() < 100:
        return None
    d = num[ok] / den[ok]
    return pt, float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def run(tag):
    d = grid(tag)
    if d is None:
        return
    w, v, lat = d['wire'], d['v'] * 3.6, d['lat']
    eng = (lat > 0.99) & (v > 1.0)
    b26 = w * LSB
    print('\n=== %s : V127, 427 <- gp-0x6B26, sar %d ===' % (tag, SAR))
    print('  engaged n=%d   |gp-0x6b26| p50 %.0f  p90 %.0f  p99 %.0f  max %.0f   (clamp %d)'
          % (eng.sum(), *np.percentile(b26[eng], [50, 90, 99]), b26[eng].max(), CLAMP))
    if w[eng].max() > RAIL_WIRE + 1:
        print('  WIRE EXCEEDS THE EXPECTED RAIL (%d) -- the packer sar or the source is not what'
              ' this script assumes.  STOP and re-check before interpreting.' % RAIL_WIRE)
        return
    railed = (w >= RAIL_WIRE - 0.5).astype(float)
    eps = episodes(eng, d['t'])
    print('  %d engaged episodes >= 3 s' % len(eps))

    print('\n  RAIL DUTY (|gp-0x6b26| == 511), engaged, episode-bootstrapped 95 %% CI:')
    print('     %-12s %8s %-22s %10s' % ('speed km/h', 'n', 'V127 duty [CI]', 'V107 meas'))
    worst = 0.0
    for lo, hi in BINS:
        m = eng & (v >= lo) & (v < hi)
        if m.sum() < 200:
            print('     %-12s %8d  (too few samples)' % ('%d-%d' % (lo, hi), m.sum()))
            continue
        r = boot(episodes(m, d['t']), railed * m, m.astype(float))
        ref = V107_MEASURED.get((lo, hi))
        if r is None:
            print('     %-12s %8d  %-22s %9.2f%%'
                  % ('%d-%d' % (lo, hi), m.sum(), 'too few episodes', 100 * ref if ref else 0))
            continue
        pt, l, h2 = r
        worst = max(worst, pt)
        print('     %-12s %8d  %6.2f%% [%5.2f, %5.2f]   %9.2f%%'
              % ('%d-%d' % (lo, hi), m.sum(), 100 * pt, 100 * l, 100 * h2,
                 100 * ref if ref is not None else float('nan')))

    print('\n  PRE-REGISTERED VERDICT (worst bin = %.2f %%):' % (100 * worst))
    if worst <= 0.02:
        print('     DE-RAILED -- the term is linear; the fix is in force.')
    elif worst <= 0.10:
        print('     PARTIAL -- consider the next rung, the mode record 0xCBE74 (the NORMAL LERP rails at mid speed too).')
    else:
        print('     STILL RAILING -- go to the mode record 0xCBE74 (the NORMAL LERP rails at mid speed too).')
    print('\n  NOT REPORTED, DELIBERATELY: any spectrum of this wire.  427 is 49.9 Hz (Nyquist')
    print('  24.95 Hz) and the lane lives at 25-153 Hz.  Duty is a level statistic and survives')
    print('  undersampling; a spectrum does not.  That confusion is what voided V107.')


def control(tag='r24'):
    """r24 is V122, whose 427 tap is gp-0x6ABC at sar 3 -- NOT this build's wire.
    The control here is a NEGATIVE one: the script must REFUSE to score it."""
    d = grid(tag)
    if d is None:
        return
    w = d['wire']
    print('\n  NEGATIVE CONTROL on %s (tap is gp-0x6ABC at sar 3, not gp-0x6B26 at sar 2)' % tag)
    print('     wire max %.0f vs this build\'s expected rail %d' % (w.max(), RAIL_WIRE))
    print('     => %s' % ('CORRECTLY REFUSED -- the guard catches a wrong-build cache'
                          if w.max() > RAIL_WIRE + 1 else
                          'WARNING: the guard did NOT fire; check the sar before trusting a score'))


args = sys.argv[1:]
if '--control' in args:
    i = args.index('--control')
    control(args[i + 1] if i + 1 < len(args) else 'r24')
else:
    for t in args or ['r25']:
        run(t)
