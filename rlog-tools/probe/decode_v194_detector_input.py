#!/usr/bin/env python3
"""Decode V194's CAN 427 probe: gp-0x6c2c, the oscillation detector's own input.

WHAT THIS ANSWERS
-----------------
Honda's reversal detector (FUN_000428d4) increments its counter only when |gp-0x6c2c| exceeds
T = cal(0xC620A) = 12800.  Nothing in this kit has ever measured gp-0x6c2c, so it is unknown whether
the ratchet's acceleration reaches T at all.  If it does not, then V191, V192 AND V193 -- every
lever gated on that counter -- are inert, and the next build lowers T instead.

THE ENCODING (set by V194, and it is not the same as V183's)
------------------------------------------------------------
The packer does `andi 0xffff` (ZERO-extend), then `sar N`, then masks to 10 bits.  gp-0x6ac0 was
unsigned so N=4 was fine; gp-0x6c2c is SIGNED, so N was moved to 6 to make the 10-bit field carry
the sign cleanly:

    positive x -> raw    0 ..  511
    negative x -> raw  512 .. 1023
    decode:  x = (raw < 512 ? raw : raw - 1024) * 64
    resolution 64 counts, range +-32704, and T = 12800 lands at raw 200.

A smaller shift wraps negatives into the positive range and makes the channel unreadable.

VERDICTS
--------
    |x| peaks well past 12800 during the ratchet -> amplitude fine; the detector route is live and
                                                    V193's frequency fix is the operative change
    peaks below 12800                            -> T is the blocker; V191/V192/V193 all inert
    peaks near 12800                             -> marginal; T needs a modest reduction
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

SAR = 6
LSB = 1 << SAR
T = 12800


def decode(raw):
    """raw: the 10-bit field from CAN 427.  Returns gp-0x6c2c in firmware counts."""
    r = np.asarray(raw).astype(int) & 0x3FF
    return np.where(r < 512, r, r - 1024) * LSB


def main(tag):
    p = Path('analysis-2020accord/_scratch/cache') / tag / f'{tag}.npz'
    if not p.exists():
        print(f'no cache for {tag} at {p}')
        print('the probe field is the 10-bit value the 427 decoder already extracts;')
        print('pair it with the SAFE time base -- (t, probe) or (raw14_t, raw14_b4), never mixed')
        print('(raw14 off-by-one: t == raw14_t[1:] in every cache).')
        return 1
    z = np.load(p, allow_pickle=True)
    key = next((k for k in ('probe', 'raw14_b4') if k in z.files), None)
    if key is None:
        print(f'{tag}: no probe channel in cache (have: {list(z.files)[:12]})')
        return 1
    x = decode(z[key])
    lat = np.asarray(z['cc_lat']).astype(float) if 'cc_lat' in z.files else None
    n = len(x)
    if lat is not None:
        m = lat[:n] > 0.5
    else:
        m = np.ones(n, bool)
    eng = x[m[:len(x)]]
    print(f'route {tag}: {n} frames, {m.sum()} engaged')
    for nm, v in (('ALL', x), ('ENGAGED', eng)):
        if len(v) == 0:
            continue
        a = np.abs(v)
        print(f'  {nm:8s} |x|  p50 {np.percentile(a, 50):8.0f}   p95 {np.percentile(a, 95):8.0f}'
              f'   p99 {np.percentile(a, 99):8.0f}   max {a.max():8.0f}')
        print(f'           frames past T={T}: {(a > T).sum()} ({100.0 * (a > T).mean():.3f} %)')
    a = np.abs(eng if len(eng) else x)
    print('')
    if a.max() > 1.5 * T:
        print(f'=> VERDICT: amplitude is NOT the blocker (max {a.max():.0f} vs T={T}).')
        print('   The detector route is live; V193\'s frequency fix is the operative change.')
    elif a.max() < T:
        print(f'=> VERDICT: T IS THE BLOCKER (max {a.max():.0f} < T={T}).')
        print('   V191/V192/V193 are ALL inert. The next build lowers T at 0xC620A.')
    else:
        print(f'=> VERDICT: MARGINAL (max {a.max():.0f} vs T={T}). T needs a modest reduction.')
    return 0


if __name__ == '__main__':
    os.chdir(str(_d.parent) if (_d / 'rlog-tools').exists() else '.')
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'r24'))
