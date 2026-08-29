#!/usr/bin/env python3
"""Decode V197's CAN 427 probe: gp-0x6bbe, the VISCOUS exciter.

WHAT THIS ANSWERS
-----------------
The ratchet is a PLANT resonance, so firmware can only reduce its EXCITERS.  Only four aggregator
terms are live, and V196 halves the one with the SMALLEST clamp:

    gp-0x6b86  12288   biquad output -- LKAS command, 1-5 Hz
    gp-0x6b4c  10240   11-slot assist sum -- low frequency
    gp-0x6bbe   2048   VISCOUS, rate-derived (omega^1)      <-- this probe
    gp-0x6b26   1024   INERTIA, acceleration-derived (omega^2)   <-- what V196 halves

The inertia term is the only omega^2 one, so it can still dominate the 8 Hz sum despite the small
clamp -- but constants cannot settle that.  This measures gp-0x6bbe's actual 8 Hz content.

    its 8 Hz content is LARGE  -> V196 aims at a minor exciter; the viscous path is where a lever
                                  should go, and it is BYTE-STOCK (0xC6370/0xC6372/0xC615A all
                                  identical on stock, V122 and V196) so it is entirely unexplored
    small or comparable        -> V196 is aimed correctly; the omega^2 weighting does the work

THE ENCODING (V197: sar 3, NOT V194's sar 6)
--------------------------------------------
gp-0x6bbe is SIGNED and its writer clamps it to +-2048, so a smaller shift keeps resolution:

    positive x (0..2048)    -> raw    0 ..  256
    negative x (-2048..-1)  -> raw  768 .. 1023
    decode:  x = (raw < 512 ? raw : raw - 1024) * 8
    resolution 8 counts, unambiguous for |x| <= 4088

The shift is a property of the SOURCE, not of the channel.  V194 used sar 6 because gp-0x6c2c spans
the full int16; using sar 6 here would throw away three bits of a +-2048 signal.
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
SAR = 3
LSB = 1 << SAR
CLAMP = 2048


def decode(raw):
    r = np.asarray(raw).astype(int) & 0x3FF
    return np.where(r < 512, r, r - 1024) * LSB


def main(tag, confirmed=False):
    if not confirmed:
        print('=' * 78)
        print('REFUSING TO DECODE -- this channel is only meaningful on a V197 route.')
        print('')
        print('  The 427 field carries a DIFFERENT signal on every other build:')
        print('    V102..V182  gp-0x6b4c            V183..V196  gp-0x6ac0 at sar 4')
        print('    V194        gp-0x6c2c at sar 6   V197        gp-0x6bbe at sar 3  <- this one')
        print('')
        print('  Decoding another build here yields a PLAUSIBLE, SPECIFIC, WRONG number.')
        print(f'  Re-run with --v197 once the route is genuinely a V197 capture:')
        print(f'    python {Path(__file__).name} <route-tag> --v197')
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
    print(f'  |gp-0x6bbe|  p50 {np.percentile(a, 50):7.0f}  p95 {np.percentile(a, 95):7.0f}'
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
        print('  If the viscous term dominates, V196 is aimed at a minor exciter and the')
        print('  byte-stock viscous path (0xC6370 / 0xC6372 / 0xC615A) is the unexplored lever.')
    return 0


if __name__ == '__main__':
    os.chdir(str(_d))
    _a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(main(_a[0] if _a else 'r24', '--v197' in sys.argv))
