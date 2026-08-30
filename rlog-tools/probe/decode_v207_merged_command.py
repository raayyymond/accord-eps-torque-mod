#!/usr/bin/env python3
"""
DOES THE DELIVERY-CHAIN GATE FIRE?  Decoder for V207.

The shaper zero-rejects the merged command outside +-8192 (0x431d0-0x431d8: addi 0x2000 /
addi -0x4001 / cmovc 0x0,r9,r11).  Outside the window the command is REPLACED BY ZERO, not clipped.
V207 taps gp-0x6acc, which is the exact quantity that branch reads.

    decode:  x = (raw < 512 ? raw : raw - 1024) * 32        sar 5, resolution 32
    the GATE boundary sits at |x| = 8192, i.e. raw 256 / 768
    aliasing only beyond |x| = 16352, which the report flags

The endpoint is a DUTY, not an amplitude: what fraction of engaged frames sit outside the window.
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
CLAMP = 8192


def decode(raw):
    r = np.asarray(raw).astype(int) & 0x3FF
    return np.where(r < 512, r, r - 1024) * LSB


def main(tag, confirmed=False):
    if not confirmed:
        print('=' * 78)
        print('REFUSING TO DECODE -- this channel is only meaningful on a V207 route.')
        print('')
        print('  The 427 field carries a DIFFERENT signal on every other build:')
        print('    V102..V182  gp-0x6b4c            V183..V196  gp-0x6ac0 at sar 4')
        print('    V194        gp-0x6c2c at sar 6   V207        gp-0x6acc at sar 5  <- this one')
        print('')
        print('  Decoding another build here yields a PLAUSIBLE, SPECIFIC, WRONG number.')
        print(f'  Re-run with --v207 once the route is genuinely a V207 capture:')
        print(f'    python {Path(__file__).name} <route-tag> --v203')
        print('=' * 78)
        return 2
    p = (_d.parent / 'analysis-2020accord' / '_scratch' / 'cache') / tag / f'{tag}.npz'
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
    print(f'  |gp-0x6acc|  p50 {np.percentile(a, 50):7.0f}  p95 {np.percentile(a, 95):7.0f}'
          f'  max {a.max():7.0f}   (writer clamp {CLAMP})')
    gate = (a > 8192)
    print(f'  GATE FIRES (|x| > 8192): {gate.sum()} frames ({100.0 * gate.mean():.4f} %)')
    alias = (a >= 16352)
    if alias.any():
        print(f'  !! {alias.sum()} frames at/over the aliasing bound 16352 -- magnitudes above that are NOT trustworthy')
    print(f'  margin to the gate: p99 {np.percentile(a, 99):.0f}, max {a.max():.0f}, window 8192')
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
        print('  If the merged command dominates, V196 is aimed at a minor exciter and the')
        print('  rate lanes are where a bigger lever belongs -- and unlike every other')
        print('  candidate they have a MEASURED on-car dose-response history:')
        print('    V62 sar x2  "18-22 Hz down 8-42x"   V88 Lever B  "grinding FIXED on-car"')
    return 0


if __name__ == '__main__':
    os.chdir(str(_d))
    _a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(main(_a[0] if _a else 'r24', any(f in sys.argv for f in ('--v207','--v202','--v203'))))
