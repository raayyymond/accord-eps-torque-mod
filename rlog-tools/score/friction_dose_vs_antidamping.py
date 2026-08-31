#!/usr/bin/env python3
r"""DOES THE ENGAGED FRICTION DOSE PREDICT THE 6-9 Hz ANTI-DAMPING?  A cross-build dose-response.

THE SETUP.  Engagement swaps the friction record (pointer array 0xCBE74) from mode 24 to mode 26, and
Honda's engaged record is 3x the manual one:

    mode 24 (manual)   Y = ( -9830,  -5734,  -1966)
    mode 26 (engaged)  Y = (-29490, -17202, -16000)      3.00x  3.00x  8.14x

That is the ONLY lane of the several the mode swap is said to re-index whose table actually differs --
the five base-assist damper records (FactorB/C/D/E + ceiling) and all three boost tables are BYTE
IDENTICAL between the two modes.  So of everything the 24 -> 26 re-index touches, friction is the whole
of it, and friction in a loop is the textbook stick-slip / ratchet mechanism.

THE TEST.  The engaged record has been dosed across the corpus -- 0.25x, 0.5x, 1.0x (= the manual
values), 1.5x and Honda's 3x -- so several FLOWN builds carry different friction and each has measured
Re(Z) at 6-9 Hz.  Regress one on the other.

    friction dose predicts Re(Z)   =>  the engagement-caused anti-damping is the friction lane, and
                                       that lane is cal-only, mode-scoped and already proven flyable.
    no relation                    =>  friction is ELIMINATED, and the last lane the mode swap touches
                                       is gone with it.

\U0001f6d1 CONFOUNDED like every cross-build comparison here: builds differ in more than friction, and
mostly one route each.  A SCREEN.  The Re(Z) side is coherence-gated (>= 0.60) because pooling
low-coherence windows imports regression dilution -- that artefact already produced one retracted
mechanism in this arc.

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
import os
import re
import struct
import sys

import numpy as np
from scipy import signal, stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FW = os.environ.get('ACCORD_FIRMWARE_ROOT',
                    r'C:\Users\dudei\Desktop\Projects\accord-firmwares')
IMGDIR = os.path.join(FW, 'analysis-2020accord')

BUILD = {'r77': 'V90', 'r78': 'V91', 'r7d': 'V94', 'r7e': 'V96', 'r7f': 'V96',
         'r80': 'V97', 'r81': 'V98', 'r82': 'V99', 'r85': 'V100', 'r95': 'V101',
         'r96': 'V102', 'r9e': 'V103', 'ra4': 'V104', 'ra5': 'V105', 'ra6': 'V106',
         'r1e': 'V107', 'r21': 'V111', 'r22': 'V112', 'r24': 'V122'}
PTR, NPT = 0xCBE74, 3
MANUAL_Y0 = -9830.0          # Honda's manual Y[0]; doses are quoted as multiples of this
BAND = (6.0, 9.5)
MIN_COH = 0.60


def friction_engaged(build):
    """Engaged (mode 26) friction Y from that build's plain image."""
    pats = glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
    pats = [p for p in pats if 'DO-NOT-FLASH' not in os.path.basename(p)] or pats
    if not pats:
        return None
    img = open(pats[0], 'rb').read()
    if struct.unpack_from('<H', img, 0xC646C)[0] != 891:
        return None
    b = struct.unpack_from('<I', img, PTR + 26 * 4)[0]
    if not (0 < b < len(img) - 2 - 4 * NPT):
        return None
    return tuple(struct.unpack_from('<h', img, b + 2 + 2 * NPT + 2 * i)[0] for i in range(NPT))


def cache_for(route):
    for p in (os.path.join(REPO, '_scratch', 'cache', route, route + '.npz'),
              os.path.join(REPO, 'analysis-2020accord', '_scratch', 'cache', route, route + '.npz')):
        if os.path.exists(p):
            return p
    return None


def rez(route):
    p = cache_for(route)
    if not p:
        return None
    z = np.load(p, allow_pickle=True)
    if not {'t', 'tq', 'cs_rate', 'cc_lat'} <= set(z.files):
        return None
    t = np.asarray(z['t'], float)
    n = len(t)
    q = np.asarray(z['tq'], float)[:n]
    r = np.asarray(z['cs_rate'], float)[:n]
    e = (np.asarray(z['cc_lat'], float) > 0.5)[:n]
    if len(q) < n or len(r) < n:
        return None
    fs = 1.0 / np.median(np.diff(t))
    lo, hi = BAND[0] / (fs / 2), BAND[1] / (fs / 2)
    if hi >= 1.0:
        return None
    b, a = signal.butter(3, [lo, hi], btype='band')
    qa = signal.hilbert(signal.filtfilt(b, a, q - q.mean()))
    ra = signal.hilbert(signal.filtfilt(b, a, r - r.mean()))
    w = int(2.0 * fs)
    vals = []
    for i in range(0, n - w, w):
        sl = slice(i, i + w)
        if e[sl].mean() < 0.98:
            continue
        rr, qq = ra[sl], qa[sl]
        den = float(np.mean(np.abs(rr) ** 2))
        if den < 1e-6:
            continue
        cxy = np.mean(qq * np.conj(rr))
        coh = float(np.abs(cxy) ** 2 / max(den * float(np.mean(np.abs(qq) ** 2)), 1e-30))
        if coh >= MIN_COH:
            vals.append(float((cxy / den).real))
    return (float(np.median(vals)), len(vals)) if len(vals) >= 15 else None


def main():
    print('=' * 86)
    print('  DOES THE ENGAGED FRICTION DOSE PREDICT THE 6-9 Hz ANTI-DAMPING?')
    print('=' * 86)
    print()
    print('  %-6s %-6s %26s %8s %11s %7s' %
          ('route', 'build', 'engaged friction Y', 'dose', 'Re(Z) 6-9', 'wins'))
    print('  ' + '-' * 74)
    rows = []
    for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
        b = BUILD[r]
        Y = friction_engaged(b)
        z = rez(r)
        if Y is None or z is None:
            print('  %-6s %-6s %26s %8s %11s %7s'
                  % (r, b, ('%s' % (Y,)) if Y else 'no image',
                     '--', '--' if z is None else '%.2f' % z[0], '--'))
            continue
        dose = Y[0] / MANUAL_Y0
        rows.append((r, b, dose, z[0]))
        print('  %-6s %-6s %26s %7.2fx %11.2f %7d' % (r, b, '%s' % (Y,), dose, z[0], z[1]))
    print('  ' + '-' * 74)
    if len(rows) < 4:
        print('\n  too few paired builds (%d) to regress.' % len(rows))
        return
    d = np.array([x[2] for x in rows])
    v = np.array([x[3] for x in rows])
    print('\n  doses present: %s' % sorted(set(np.round(d, 2))))
    if len(set(np.round(d, 2))) < 2:
        print('  \U0001f6d1 EVERY FLOWN BUILD CARRIES THE SAME DOSE -- there is no contrast, so this')
        print('     corpus CANNOT test the friction lane. Not a null: an untested lever.')
        return
    lr = stats.linregress(d, v)
    rho = stats.spearmanr(d, v)
    print('  linregress Re(Z) on dose : slope %+.2f   R2 %.3f   p %.4f'
          % (lr.slope, lr.rvalue ** 2, lr.pvalue))
    print('  Spearman rho             : %+.3f   p %.4f  (n=%d builds)'
          % (rho.correlation, rho.pvalue, len(rows)))
    print()
    if rho.pvalue < 0.05:
        print('  => FRICTION DOSE PREDICTS THE ANTI-DAMPING. The lane is cal-only and mode-scoped.')
    else:
        print('  => NO RELATION. The friction lane does not explain the 6-9 Hz anti-damping, and it')
        print('     was the LAST lane the mode swap touches -- every other table the 24 -> 26 index')
        print('     reaches is byte-identical. Engagement\'s effect must then come from the LKAS')
        print('     TORQUE ITSELF, not from any re-indexed calibration.')
    print('\n  \U0001f6d1 CONFOUNDED: builds differ in more than friction, mostly one route each. A SCREEN.')


if __name__ == '__main__':
    main()
