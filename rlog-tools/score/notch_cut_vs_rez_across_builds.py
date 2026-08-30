#!/usr/bin/env python3
r"""CAN THE 6-15 Hz RULE BE SETTLED WITHOUT NEW FIRMWARE?

The rule -- "never notch 6-15 Hz on this lane, it DAMPS there" -- blocks the only band the torque
spectrum says is worth filtering.  It was measured on `mag427`, and the frame builder clamps that field
to [0, 0x3ff], so its phase carries no reliable sign.  A sign probe needs a cave or a clamp change,
which is the operator's call, not something to cut onto a shelf about to be flown.

So ask it a different way, from data that already exists.

THE IDEA.  The biquad sits IN this lane.  Different builds place it differently, so each build applies
a different amount of cut at 6-15 Hz.  The aggregate `Re(Z)` at 6-15 Hz is measurable on every route
from `tq` and `rate_f` -- both signed, both on the same 0x18F frame, which is the record's own
estimator convention.  Then:

  * if the lane DAMPS at 6-15 Hz (the rule), cutting it there REMOVES damping
    => more notch cut  ->  Re(Z) MORE negative (worse anti-damping)
  * if the lane PUMPS there, cutting it there REMOVES pumping
    => more notch cut  ->  Re(Z) LESS negative (better)

**A positive correlation between cut and Re(Z) refutes the rule; a negative one confirms it.**

WHAT THIS CANNOT DO.  Builds differ in more than their notch, and there are few of them, so this is a
correlation across a handful of confounded points -- a screen, not a proof.  It is worth running
because a clear result in EITHER direction is more than the rule currently rests on, and because it
costs no firmware and no drive.

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

import cmath
import glob
import os
import struct
import sys

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    'C:/Users/dudei/Desktop/Projects/accord-firmwares')
FS_CTRL = 1000.0
BAND = (6.0, 15.0)
NPERSEG = 1024
MIN_ENG = 2000

# route -> build, the kit's canonical map (rlog-tools/lib/v95_rez_lib.py BUILD)
BUILD = {"r5e": "v75", "r61": "v74", "r65": "v76", "r66": "v80", "r67": "v81",
         "r68": "v83a", "r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b",
         "r71": "v87", "r73": "v88", "r75": "v89", "r76": "v89", "r77": "v90",
         "r78": "v91", "r79": "v92", "r95": "v101", "r96": "v102", "r9e": "v103",
         "ra4": "v104", "ra5": "v105", "ra6": "v106"}


def notch_cut(img):
    """mean |H| of the build's biquad over the band, and whether it is ARMED.

    An UNARMED biquad applies no cut at all, whatever its coefficients say -- 0xC649B is the arm.
    """
    a1, a2, b1, c4 = struct.unpack_from('<ffff', img, 0xC60A8)
    armed = img[0xC649B] == 1
    if not armed:
        return 1.0, False
    f = np.arange(BAND[0], BAND[1] + 0.01, 0.25)
    z = np.exp(-2j * np.pi * f / FS_CTRL)
    H = np.abs(c4 * (1 + b1 * z + z * z) / (1 + a1 * z + a2 * z * z))
    return float(H.mean()), True


def rez(route):
    """aggregate Re(Z) over the band, from tq and rate_f -- both signed, same 0x18F frame"""
    best = None
    for pat in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
                os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route,
                             route + '.npz')):
        if os.path.exists(pat):
            best = pat
            break
    if best is None:
        return None, 0
    z = np.load(best, allow_pickle=True)
    if not {'tq', 'rate_f', 'cc_lat', 't'} <= set(z.files):
        return None, 0
    eng = np.asarray(z['cc_lat'], float) > 0.5
    tq = np.asarray(z['tq'], float)
    rt = np.asarray(z['rate_f'], float)
    n = min(len(eng), len(tq), len(rt))
    eng, tq, rt = eng[:n], tq[:n], rt[:n]
    if eng.sum() < MIN_ENG:
        return None, int(eng.sum())
    t = np.asarray(z['t'], float)[:n]
    fs = 1.0 / np.median(np.diff(t))
    f, Pxy = signal.csd(rt[eng], tq[eng], fs, nperseg=NPERSEG)   # Z = torque / rate
    m = (f >= BAND[0]) & (f <= BAND[1])
    # normalise by |Z| so a loud route is not a big Re(Z) by loudness alone
    return float(np.sum(np.real(Pxy[m])) / max(np.sum(np.abs(Pxy[m])), 1e-30)), int(eng.sum())


def main():
    print('=' * 92)
    print('  NOTCH CUT AT %.0f-%.0f Hz  vs  AGGREGATE Re(Z) THERE, across builds'
          % BAND)
    print('=' * 92)
    print('  %-6s %-7s %8s %8s %10s %9s' %
          ('route', 'build', 'armed', '|H| band', 'cut(1-|H|)', 'Re(Z)'))
    print('  ' + '-' * 60)
    rows = []
    for route, b in sorted(BUILD.items(), key=lambda kv: kv[1]):
        g = [p for p in glob.glob(os.path.join(FW, 'analysis-2020accord', '*plain_image.bin'))
             if '_%s_' % b in p.lower() and 'SUPERSEDED' not in p]
        if not g:
            continue
        H, armed = notch_cut(open(g[0], 'rb').read())
        r, neng = rez(route)
        if r is None:
            continue
        print('  %-6s %-7s %8s %8.4f %10.4f %9.4f'
              % (route, b.upper(), 'yes' if armed else 'NO', H, 1 - H, r))
        rows.append((route, b, 1 - H, r, armed))
    print('  ' + '-' * 60)
    if len(rows) < 4:
        print('  only %d usable points -- too few to correlate.' % len(rows))
        return
    cut = np.array([x[2] for x in rows])
    rz = np.array([x[3] for x in rows])
    armed_any = any(x[4] for x in rows)
    print('  %d builds.  cut range %.4f .. %.4f   Re(Z) range %.4f .. %.4f'
          % (len(rows), cut.min(), cut.max(), rz.min(), rz.max()))
    if cut.max() - cut.min() < 1e-6:
        print()
        print('  \U0001f6d1 EVERY BUILD APPLIES THE SAME CUT (usually because the biquad is UNARMED on')
        print('     all of them). There is no contrast to correlate -- this cannot answer the')
        print('     question, and a correlation computed anyway would be meaningless.')
        print('     armed on at least one build: %s' % armed_any)
        return
    pr = stats.pearsonr(cut, rz)
    sp = stats.spearmanr(cut, rz)
    print('  cut vs Re(Z):  pearson r=%+.3f p=%.4f   spearman rho=%+.3f p=%.4f'
          % (pr[0], pr[1], sp[0], sp[1]))
    print()
    print('  READING IT:')
    print('   * POSITIVE (more cut -> Re(Z) less negative) => the lane PUMPS at %.0f-%.0f Hz'
          % BAND)
    print('     and the "never notch here" rule is REFUTED -- the strongest lever in the kit opens.')
    print('   * NEGATIVE (more cut -> Re(Z) more negative) => the lane DAMPS, the rule stands,')
    print('     and the ratchet stays out of reach by calibration.')
    print('   * NULL => this screen cannot separate them either.')
    print()
    print('  \U0001f6d1 builds differ in more than their notch and n is small: a SCREEN, not a proof.')


if __name__ == '__main__':
    main()
