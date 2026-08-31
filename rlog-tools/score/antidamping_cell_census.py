#!/usr/bin/env python3
r"""EVERY CELL THAT VARIES ACROSS THE FLOWN CORPUS, TESTED AGAINST THE 6-9 Hz ANTI-DAMPING.

WHY.  Lever B was found OPPORTUNISTICALLY -- by noticing it happened to correlate.  This is the
systematic version: enumerate every byte that differs between any two flown images, group into u16
cells, and regress each against the coherence-gated Re(Z) at 6-9 Hz.  It either finds more levers that
move the ratchet WITHOUT spending forward authority, or it establishes that Lever B is the only one.

THE CONTROLS THAT MAKE IT READABLE, and they matter more than the ranking:

  * Re(Z) is coherence-gated (>= 0.60).  Pooling low-coherence windows imports regression dilution,
    which already produced one retracted mechanism in this arc.
  * The anti-damping is AMPLITUDE-INDEPENDENT, which is what makes a cross-build comparison of it
    legitimate at all; the 22-30 Hz band is NOT, and cannot be compared this way.
  * \U0001f6d1 MULTIPLICITY.  Hundreds of cells against 17 builds will throw up "significant" hits by
    chance alone.  A Benjamini-Hochberg FDR is reported alongside the raw p, and NOTHING here should be
    built on without an independent reason -- the point is to generate candidates, not verdicts.
  * \U0001f6d1 COLLINEARITY.  Cells that moved together across builds are INDISTINGUISHABLE, exactly as
    the gain and its tracking clamp are (clamp = gain*512//891).  Cells are therefore grouped into
    identical-pattern classes and the class is reported, never a single member as "the" cause.

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

import collections
import glob
import os
import re
import struct
import sys

import numpy as np
from scipy import stats

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from friction_dose_vs_antidamping import rez, BUILD, IMGDIR   # noqa: E402

CAL_LO, CAL_HI = 0xC4000, 0xCC000     # the calibration region; code edits are not doses
# 🛑 TWO CLASSES OF BYTE VARY ACROSS BUILDS WITHOUT BEING LEVERS, AND BOTH SCORE HIGHLY IF
# LEFT IN. The 164-byte CAVE at 0xC4B34 holds per-build PROBE payloads -- it differs by instrument
# design, not by any damping mechanism -- and each CRC-block TRAILER is a DERIVED checksum that moves
# whenever anything in its block moves. Excluding both is what separates a lever from an artefact.
CAVE = (0xC4B34, 0xC4B34 + 164)
TRAILERS = {0xC4FFC, 0xC5FFC, 0xC6FFC, 0xC7FFC, 0xC8FFC, 0xC9FFC, 0xCAFFC, 0xCBFFC}


def is_artefact(a):
    if CAVE[0] <= a < CAVE[1]:
        return 'cave/probe payload'
    for t in TRAILERS:
        if t <= a < t + 4:
            return 'CRC trailer'
    return None


KNOWN = {0xC6CD0: 'GAIN (forward LKAS)', 0xC61B2: 'clamp+ (tracks gain)',
         0xC61B4: 'clamp- (tracks gain)', 0xC6446: 'Lever B', 0xC646C: 'shared sensor scale',
         0xC674E: 'soft-EME interlock', 0xC67C4: 'resonance-PID knee', 0xC6906: 'engaged lag pole'}


def image_for(build):
    p = [q for q in glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
         if 'DO-NOT-FLASH' not in os.path.basename(q)]
    p = p or glob.glob(os.path.join(IMGDIR, '_%s_*_plain_image.bin' % build.lower()))
    if not p:
        return None
    im = open(p[0], 'rb').read()
    return im if struct.unpack_from('<H', im, 0xC646C)[0] == 891 else None


def main():
    print('=' * 90)
    print('  CELL CENSUS AGAINST THE 6-9 Hz ANTI-DAMPING -- every cell that varies across flown builds')
    print('=' * 90)

    builds, imgs, vals = [], {}, {}
    for r in sorted(BUILD, key=lambda k: int(re.sub(r'\D', '', BUILD[k]))):
        b = BUILD[r]
        if b in imgs:
            continue
        im, z = image_for(b), rez(r)
        if im is None or z is None:
            continue
        imgs[b], vals[b] = im, z[0]
        builds.append(b)
    print('\n  %d flown builds with both an image and a measured Re(Z): %s'
          % (len(builds), ', '.join(builds)))
    if len(builds) < 6:
        print('  too few to census.')
        return

    ref = imgs[builds[0]]
    n = min(len(imgs[b]) for b in builds)
    varying = []
    for a in range(CAL_LO, min(CAL_HI, n - 1), 2):
        if is_artefact(a):
            continue
        vs = [struct.unpack_from('<H', imgs[b], a)[0] for b in builds]
        if len(set(vs)) > 1:
            varying.append((a, tuple(vs)))
    print('  %d u16 cells in [0x%05X,0x%05X) vary (cave and CRC trailers excluded)' % (len(varying), CAL_LO, CAL_HI))

    y = np.array([vals[b] for b in builds])
    rows = []
    for a, vs in varying:
        x = np.array(vs, float)
        if len(set(vs)) < 2:
            continue
        rho = stats.spearmanr(x, y)
        if not np.isfinite(rho.correlation):
            continue
        rows.append((a, vs, rho.correlation, rho.pvalue))
    if not rows:
        print('\n  nothing testable.')
        return

    # Benjamini-Hochberg
    rows.sort(key=lambda t: t[3])
    m = len(rows)
    qs = []
    prev = 1.0
    for i in range(m - 1, -1, -1):
        prev = min(prev, rows[i][3] * m / (i + 1))
        qs.append(prev)
    qs = qs[::-1]

    # group collinear cells by their value-pattern signature
    sig = collections.defaultdict(list)
    for (a, vs, r_, p_), q_ in zip(rows, qs):
        sig[tuple(sorted(set(vs)))+ (tuple(np.argsort(vs)),)].append((a, vs, r_, p_, q_))

    print('\n  TOP COLLINEARITY CLASSES BY |rho| -- a class is indistinguishable within itself')
    print('  %-11s %8s %9s %9s %s' % ('cells', 'rho', 'p', 'q (FDR)', 'members'))
    print('  ' + '-' * 84)
    classes = sorted(sig.values(), key=lambda g: -abs(g[0][2]))
    shown = 0
    for g in classes:
        a, vs, r_, p_, q_ = g[0]
        if abs(r_) < 0.5:
            continue
        names = []
        for aa, _, _, _, _ in g[:6]:
            names.append(KNOWN.get(aa, '0x%05X' % aa))
        more = '' if len(g) <= 6 else ' +%d more' % (len(g) - 6)
        print('  %-11d %+8.3f %9.4f %9.4f %s%s' % (len(g), r_, p_, q_, ', '.join(names), more))
        shown += 1
        if shown >= 12:
            break
    print('  ' + '-' * 84)

    sig_hits = [g for g in classes if g[0][4] < 0.10]
    print('\n  classes surviving FDR q < 0.10: %d' % len(sig_hits))
    if not sig_hits:
        print('  => NO cell survives multiplicity correction. Lever B and the gain are the only')
        print('     candidates this corpus supports, and no further one is hiding in the cal region.')
    else:
        for g in sig_hits[:6]:
            a, vs, r_, p_, q_ = g[0]
            print('     %-28s rho %+.3f  q %.4f  (%d collinear cells)'
                  % (KNOWN.get(a, '0x%05X' % a), r_, q_, len(g)))
    print('\n  \U0001f6d1 CANDIDATES, NOT VERDICTS. Cells within a class are indistinguishable, builds')
    print('     differ in many cells at once, and there is one route per build.')


if __name__ == '__main__':
    main()
