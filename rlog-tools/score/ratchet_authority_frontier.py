#!/usr/bin/env python3
r"""THE RATCHET-vs-AUTHORITY FRONTIER.  The central tension of the project, priced.

WHY THIS IS THE RIGHT QUESTION.  The operator asks for two things that the measurements say are in
conflict: more LKAS torque, and no ratcheting.  The 6-9 Hz anti-damping tracks the forward gain
(rho -0.819 over 17 flown builds, ~ -4.4 of Re(Z) per 1x of gain), and the gain is exactly what buys
torque.  Every other lever is small next to it -- the damper lane maxes at 29 % of the requirement and
costs 15 % of authority to get there.

BUT THE TRADE IS NOT AS BRUTAL AS IT LOOKS, FOR TWO REASONS THIS SCRIPT QUANTIFIES:

  1. PEAK delivered torque is set by the CLAMP, not the gain.  `delivered = min(cmd*gain/891, clamp)`,
     so at the rail both a 4x and a 6x build deliver exactly `clamp`.  Lowering the gain does not lower
     the ceiling -- it lowers the SLOPE to it.

  2. openpilot is a FEEDBACK controller.  If the plant gain drops it winds up further to hold the same
     lane error, up to saturation.  Since the rail duty is only 13-25 %, there is headroom to
     compensate most of the time.  So the authority actually LOST is far less than the gain ratio
     suggests -- it is only the part that pushes into the rail.

WHAT THIS COMPUTES.  For each candidate gain, using the flown command distribution:
    * anti-damping, from the measured gain relation
    * mean delivered torque assuming openpilot compensates up to the rail
    * the fraction of time it is pinned at the rail (where it can no longer compensate)

\U0001f6d1 THE COMPENSATION MODEL IS THE WEAK POINT and is stated as BELIEF.  Assuming openpilot
recovers the full gain ratio below the rail is optimistic -- it holds only while its own authority and
rate limits are not binding.  The rail duty column is the honest bound on how often that fails.

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
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

STOCK = 891.0
CAR_GAIN = 5346.0          # 6x
CAR_REZ = -64.77
SLOPE_PER_X = -4.4         # measured Re(Z) per 1x of gain, from the era-free contrast
SOFT_EME = 5120


def commands():
    out = []
    seen = set()
    for p in (sorted(glob.glob('_scratch/cache/*/*.npz')) +
              sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz'))):
        r = os.path.basename(p)[:-4]
        if r in seen or 's' in r[1:]:
            continue
        seen.add(r)
        try:
            z = np.load(p, allow_pickle=True)
        except Exception:
            continue
        if not {'co_tqcan', 'cc_lat'} <= set(z.files):
            continue
        c = np.abs(np.asarray(z['co_tqcan'], float))
        e = np.asarray(z['cc_lat'], float) > 0.5
        n = min(len(c), len(e))
        out.append(c[:n][e[:n]])
    return np.concatenate(out) if out else None


def main():
    print('=' * 90)
    print('  THE RATCHET-vs-AUTHORITY FRONTIER   -- the two things asked for, in conflict, priced')
    print('=' * 90)
    cmd = commands()
    if cmd is None or len(cmd) < 1000:
        print('  no command data.')
        return
    print('\n  %d engaged frames of openpilot command.\n' % len(cmd))
    print('  peak delivered torque IS the clamp, so the clamp column is the real ceiling.')
    print('  "compensated" assumes openpilot winds up to hold the same lane error below the rail.\n')
    print('  %-9s %7s %8s %11s %12s %11s %10s'
          % ('gain', 'clamp', 'rail@cmd', 'rail duty', 'mean deliv', 'Re(Z) est', 'vs car'))
    print('  ' + '-' * 76)
    base_ref = None
    for mult in (2.0, 4.0, 6.0, 8.0, 10.0):
        g = STOCK * mult
        clamp = int(g * 512 // STOCK)
        clamp = min(clamp, 4096)                    # keep under the soft-EME interlock
        thr = clamp * STOCK / g
        rail = float((cmd >= thr).mean())
        deliv = float(np.mean(np.minimum(cmd * g / STOCK, clamp)))
        # compensated: below the rail openpilot recovers the same torque; only rail-clipped frames lose
        comp = float(np.mean(np.minimum(cmd * CAR_GAIN / STOCK, clamp)))
        rez = CAR_REZ + SLOPE_PER_X * (6.0 - mult) * -1
        rez = CAR_REZ - SLOPE_PER_X * (mult - 6.0) * -1
        rez = CAR_REZ + (mult - 6.0) * SLOPE_PER_X
        if base_ref is None and mult == 6.0:
            base_ref = comp
        print('  %7.1fx %7d %8.0f %10.1f%% %12.0f %11.1f %9s'
              % (mult, clamp, thr, 100 * rail, comp, rez,
                 '--' if mult == 6.0 else '%+.1f%%' % (100 * (comp / (base_ref or comp) - 1))))
    print('  ' + '-' * 76)
    print('\n  READING')
    print('  * Re(Z) improves ~4.4 per 1x of gain REMOVED -- the biggest single ratchet lever there is,')
    print('    bigger than the whole damper lane (which maxes at 29 % = ~19 units).')
    print('  * but "mean deliv" barely moves once the clamp is held at 4096, because peak torque is the')
    print('    CLAMP and openpilot compensates below the rail. The cost is concentrated in rail duty.')
    print('\n  \U0001f6d1 [BELIEF] the compensation model is the weak point: it assumes openpilot recovers')
    print('     the full gain ratio below the rail, which holds only while its own authority and rate')
    print('     limits are not binding. The rail-duty column bounds how often that fails.')
    print('  \U0001f6d1 and the gain->ratchet slope is itself confounded with build era -- one era-free')
    print('     contrast supports it (V101->V102 with Lever B held), not a controlled experiment.')


if __name__ == '__main__':
    main()
