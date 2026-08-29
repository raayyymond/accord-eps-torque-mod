#!/usr/bin/env python3
"""Decode V201's CAN 427 probe: gp-0x6b7e, the r24 RATE LANE -- the biggest 8 Hz exciter.

WHAT THIS ANSWERS
-----------------
The ratchet is a PLANT resonance, so firmware can only reduce its EXCITERS.  Only four aggregator
terms are live, and V196 halves the one with the SMALLEST clamp:

    gp-0x6b86  12288   biquad output -- LKAS command, 1-5 Hz
    gp-0x6b4c  10240   11-slot assist sum -- low frequency
    gp-0x6b7e   2048   VISCOUS, rate-derived (omega^1)      <-- this probe
    gp-0x6b26   1024   INERTIA, acceleration-derived (omega^2)   <-- what V196 halves

The inertia term is the only omega^2 one, so it can still dominate the 8 Hz sum despite the small
clamp -- but constants cannot settle that.  This measures gp-0x6b7e's actual 8 Hz content.

    its 8 Hz content is LARGE  -> V196 aims at a minor exciter; the viscous path is where a lever
                                  should go, and it is BYTE-STOCK (0xC6370/0xC6372/0xC615A all
                                  identical on stock, V122 and V196) so it is entirely unexplored
    small or comparable        -> V196 is aimed correctly; the omega^2 weighting does the work

THE ENCODING (V201: sar 3, NOT V194's sar 6)
--------------------------------------------
gp-0x6b7e is SIGNED and the aggregator clamps it to +-12288, so sar 5 fits it with 2x headroom:

    positive x (0..12288)    -> raw    0 ..  256
    negative x (-12288..-1)  -> raw  768 .. 1023
    decode:  x = (raw < 512 ? raw : raw - 1024) * 32
    resolution 32 counts, unambiguous for |x| <= 16352

The shift is a property of the SOURCE, not of the channel.  V194 used sar 6 because gp-0x6c2c spans
the full int16; the shift must match the source: too small wraps the sign, too large discards resolution.
"""
import os
import sys
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np  # noqa: E402
from scipy import signal  # noqa: E402

FS = 100.0
SAR = 5
LSB = 1 << SAR
CLAMP = 12288


def decode(raw):
    r = np.asarray(raw).astype(int) & 0x3FF
    return np.where(r < 512, r, r - 1024) * LSB


def main(tag, confirmed=False):
    if not confirmed:
        print('=' * 78)
        print('REFUSING TO DECODE -- this channel is only meaningful on a V201 route.')
        print('')
        print('  The 427 field carries a DIFFERENT signal on every other build:')
        print('    V102..V182  gp-0x6b4c            V183..V196  gp-0x6ac0 at sar 4')
        print('    V194        gp-0x6c2c at sar 6   V201        gp-0x6b7e at sar 3  <- this one')
        print('')
        print('  Decoding another build here yields a PLAUSIBLE, SPECIFIC, WRONG number.')
        print(f'  Re-run with --v201 once the route is genuinely a V201 capture:')
        print(f'    python {Path(__file__).name} <route-tag> --v203')
        print('=' * 78)
        return 2
    p = Path('analysis-2020accord/_scratch/cache') / tag / f'{tag}.npz'
    if not p.exists():
        print(f'no cache for {tag} at {p}')
        return 1
    z = np.load(p, allow_pickle=True)
    key = next((k for k in ('probe', 'raw14_b4') if k in z.files), None)
    if key is None:
        print(f'{tag}: no probe channel (have: {list(z.files)[:12]})')
        return 1
    x = decode(z[key])
    lat = np.asarray(z['cc_lat']).astype(float) if 'cc_lat' in z.files else None
    n = len(x)
    m = (lat[:n] > 0.5) if lat is not None else np.ones(n, bool)
    eng = x[m[:n]]
    print(f'route {tag}: {n} frames, {m.sum()} engaged')
    a = np.abs(eng if len(eng) else x)
    print(f'  |gp-0x6b7e|  p50 {np.percentile(a, 50):7.0f}  p95 {np.percentile(a, 95):7.0f}'
          f'  max {a.max():7.0f}   (writer clamp {CLAMP})')
    print(f'  frames AT the clamp: {(a >= CLAMP - LSB).sum()} '
          f'({100.0 * (a >= CLAMP - LSB).mean():.2f} %)')
    if len(eng) > 512:
        f, P = signal.welch(eng - eng.mean(), FS, nperseg=512, noverlap=256)
        tr = np.trapezoid if hasattr(np, 'trapezoid') else np.trapz
        b8 = (f >= 5) & (f <= 12)
        bc = (f >= 30) & (f <= 45)
        print(f'  5-12 Hz band power {float(tr(P[b8], f[b8])):10.1f}'
              f'   30-45 Hz control {float(tr(P[bc], f[bc])):10.1f}'
              f'   ratio {float(tr(P[b8], f[b8]) / max(tr(P[bc], f[bc]), 1e-30)):7.2f}')
        print('')
        print('  Compare this 5-12 Hz band power against the same statistic for the inertia term.')
        print('  If the pedestal dominates, V196 is aimed at a minor exciter and the')
        print('  rate lanes are where a bigger lever belongs -- and unlike every other')
        print('  candidate they have a MEASURED on-car dose-response history:')
        print('    V62 sar x2  "18-22 Hz down 8-42x"   V88 Lever B  "grinding FIXED on-car"')
    return 0


if __name__ == '__main__':
    os.chdir(str(_d))
    _a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(main(_a[0] if _a else 'r24', any(f in sys.argv for f in ('--v201','--v202','--v203'))))
