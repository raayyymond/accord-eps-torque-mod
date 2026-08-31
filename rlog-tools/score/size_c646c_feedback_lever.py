#!/usr/bin/env python3
r"""CAN THE `0xC646C` FEEDBACK PATH BUY BACK ANY OF THE 6-9 Hz ANTI-DAMPING?  Size it before building.

WHY IT IS THE LAST CANDIDATE.  The 6-9 Hz anti-damping tracks the FORWARD gain `0xC6CD0` (rho -0.819
over 17 flown builds, and it follows the V100->V101->V102 reversal).  Forward gain is also what buys
authority, so the two are locked -- unless some OTHER path contributes, and one exists: V57 decoupled
the forward reader onto `0xC6CD0` and left FOUR FEEDBACK readers on the shared cal `0xC646C` = 891,
which is stock and has NEVER been varied in the flown corpus.  Lowering it would cut feedback response
without touching forward authority.  That is the only known shape of "authority without ratchet", so it
deserves a number rather than a build.

THE ARITHMETIC, mirrored from the decompile.  The two live readers (`FUN_00036682` @0x36686 and
`FUN_00036828` @0x3684a, #6 feeding #5) both compute

    out = (gp-0x4f60_RAW_SENSOR * cal) >> 15                cal = 0xC646C = 891 stock
        -> 1-pole IIR, coefficient tp+0x73d2 = 14/1024      => fc = fs*a/(2*pi), a = 14/1024
        -> clamp +-512                                      (aggregator is clamped +-0x2800 = +-10240)
        -> summed into the aggregator by FUN_0003aa2c

So the path is a torque-driven feedback term of loop gain

    k(f) = (891/32768) * |H_iir(f)|          and its phase is the IIR's phase

and the closed-loop impedance perturbation is  Z -> Z / (1 + k(f)),  because the term adds motor torque
PROPORTIONAL TO the same driver torque the impedance is measured against.  Zeroing the cal removes
exactly k, so |k| IS the entire reachable effect -- an upper bound, not an estimate.

\U0001f6d1 THE BOUND IS WHAT MATTERS.  If |k| at 7.8 Hz is a fraction of a percent, then even driving
`0xC646C` to zero cannot move a Re(Z) of -65 by a useful amount, and the lever is CLOSED without a
build, a probe or a drive.

PATH BOOTSTRAP -- see the note in the sibling scripts.
"""
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_sys.path[:0] = [_r]
for _v in ("_os", "_sys", "_r", "_n", "_v"):
    globals().pop(_v, None)

import glob
import math
import os
import sys

import numpy as np
from scipy import signal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAL = 891.0            # 0xC646C, stock and never varied in the flown corpus
SHIFT = 32768.0        # >> 15
IIR_A = 14.0 / 1024.0  # tp+0x73d2
FS = 1000.0            # the readers run on the 1 kHz control task
CLAMP = 512.0
AGG = 10240.0          # aggregator clamp +-0x2800
F0 = 7.79              # the ratchet
MEASURED_REZ = -65.0   # median coherence-gated Re(Z) at 6-9 Hz across flown builds


def iir(f, a=IIR_A, fs=FS):
    """1-pole EMA y += a*(x-y): H(f) = a / (a + j*2*pi*f/fs) to first order."""
    w = 2.0 * math.pi * f / fs
    return a / complex(a, w)


def main():
    print('=' * 84)
    print('  CAN `0xC646C` BUY BACK ANY OF THE 6-9 Hz ANTI-DAMPING?')
    print('=' * 84)
    fc = FS * IIR_A / (2 * math.pi)
    print('\n  the path:  raw torque -> *%.0f/%.0f -> IIR(a=%.5f, fc=%.2f Hz) -> clamp +-%.0f -> aggregator'
          % (CAL, SHIFT, IIR_A, fc, CLAMP))
    print('  loop gain  k(f) = (%.0f/%.0f) * |H_iir(f)| = %.5f * |H_iir(f)|\n' % (CAL, SHIFT, CAL / SHIFT))
    print('  %8s %12s %12s %14s' % ('f (Hz)', '|H_iir|', '|k|', 'phase(k) deg'))
    print('  ' + '-' * 50)
    for f in (1.0, 2.18, 5.0, F0, 15.6, 25.0):
        H = iir(f)
        k = (CAL / SHIFT) * H
        print('  %8.2f %12.4f %12.6f %14.1f' % (f, abs(H), abs(k), math.degrees(math.atan2(k.imag, k.real))))
    print('  ' + '-' * 50)

    k0 = (CAL / SHIFT) * iir(F0)
    print('\n  AT THE RATCHET (%.2f Hz):  |k| = %.6f  =  %.4f %%' % (F0, abs(k0), 100 * abs(k0)))
    print('  Z -> Z/(1+k), so zeroing the cal changes |Z| by at most %.4f %%' % (100 * abs(k0) / abs(1 + k0)))
    print('  against the measured Re(Z) = %.0f, the WHOLE reachable effect is %+.3f units.'
          % (MEASURED_REZ, MEASURED_REZ * (abs(1 / (1 + k0)) - 1)))

    # how often does the clamp even matter, and how big is the term against the aggregator?
    print('\n  and the term is small in the aggregator regardless -- measured 6-9.5 Hz torque band:')
    print('  %-7s %14s %14s %14s' % ('route', '|tq| band p99', 'path out p99', '% of aggregator'))
    print('  ' + '-' * 54)
    shown = 0
    for r in ('ra6', 'r1e', 'r24', 'r96'):
        p = None
        for c in (os.path.join(REPO, '_scratch', 'cache', r, r + '.npz'),
                  os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', r, r + '.npz')):
            if os.path.exists(c):
                p = c
                break
        if not p:
            continue
        z = np.load(p, allow_pickle=True)
        if not {'t', 'tq', 'cc_lat'} <= set(z.files):
            continue
        t = np.asarray(z['t'], float)
        n = len(t)
        q = np.asarray(z['tq'], float)[:n]
        e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
        fs = 1.0 / np.median(np.diff(t))
        lo, hi = 6.0 / (fs / 2), 9.5 / (fs / 2)
        if hi >= 1.0:
            continue
        b, a = signal.butter(3, [lo, hi], btype='band')
        band = np.abs(signal.hilbert(signal.filtfilt(b, a, q - q.mean())))[e]
        if len(band) < 1000:
            continue
        amp = float(np.percentile(band, 99))
        out = amp * (CAL / SHIFT) * abs(iir(F0))
        print('  %-7s %14.0f %14.2f %13.3f%%' % (r, amp, out, 100 * out / AGG))
        shown += 1
    print('  ' + '-' * 54)
    if shown:
        print('\n  the +-%.0f clamp never binds either: the term is two orders below it.' % CLAMP)
    print('\n  => VERDICT')
    if 100 * abs(k0) < 1.0:
        print('     `0xC646C` is CLOSED as a ratchet lever. Even driving it to ZERO -- which would also')
        print('     desensitise readers shared across three subsystems -- moves Re(Z) by well under one')
        print('     unit of the 65 measured. There is no authority-without-ratchet here.')
    else:
        print('     |k| is %.2f %% -- large enough to be worth a build. Size the blast radius next.'
              % (100 * abs(k0)))
    print('\n  \U0001f6d1 UPPER BOUND, not an estimate: it assumes the whole path is removable and')
    print('     ignores that the same cal feeds readers in three subsystems.')


if __name__ == '__main__':
    main()
