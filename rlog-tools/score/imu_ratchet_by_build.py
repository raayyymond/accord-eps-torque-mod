#!/usr/bin/env python3
r"""HAS ANY BUILD EVER MOVED THE RATCHET?  Asked of the IMU, which no build could have gamed.

The kit has thirty-plus builds and no measured ratchet improvement.  But every ratchet score in the
record was computed from the EPS's own CAN channels -- the same subsystem the builds modify -- so a
build that changed how the EPS *reports* torque would move the score without moving the car.  The
comma's LSM6DS3TR-C is physically independent: its gyro cannot be altered by any calibration.

This ranks the flown builds by the engagement-gated gyro excess at the ratchet, speed-matched, each
against its own road control on vertical acceleration.

  ratio = gyro local excess / road-control local excess

so a route that was simply driven on rougher roads cannot rank as a worse build.  A build that
genuinely reduced the ratchet must show a LOWER ratio than its neighbours in the arc.

READING IT
  * a build clearly below the corpus spread  => the first off-EPS evidence that anything ever worked.
  * all builds within the spread             => nothing has moved it, confirmed on an instrument no
    build could have influenced, and the arc's null is real rather than an artefact of CAN scoring.

WHAT THIS IS NOT.  One route per build, so build and route (road, weather, traffic) are perfectly
confounded -- this cannot attribute a difference TO the build.  It is a screen: if every build sits in
the same spread, that is informative; if one stands out, it is a lead to chase, not a result.

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

import os
import sys

import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ratchet_in_the_imu_pooled as P                                   # noqa: E402

# the kit's canonical route -> build map (rlog-tools/lib/v95_rez_lib.py BUILD)
BUILD = {"r5e": "V75", "r61": "V74", "r65": "V76", "r66": "V80", "r66x": "V80",
         "r67x": "V81", "r67": "V81", "r68x": "V83a", "r68": "V83a", "r6d": "V84",
         "r6e": "V85", "r6f": "V86", "r70": "V86B", "r71": "V87", "r73": "V88",
         "r75": "V89", "r76": "V89", "r77": "V90", "r78": "V91", "r79": "V92",
         "r7d": "V94"}
# arc order, so a dose-response would be visible as a trend rather than a scatter
ORDER = ["V74", "V75", "V76", "V80", "V81", "V83a", "V84", "V85", "V86", "V86B",
         "V87", "V88", "V89", "V90", "V91", "V92", "V94"]


def main():
    rows = P.collect() if hasattr(P, 'collect') else None
    if rows is None:
        print('  the pooled module exposes no collect(); run it directly for the per-route table.')
        return
    byb = {}
    for r in rows:
        b = BUILD.get(r[0])
        if b is None:
            continue
        byb.setdefault(b, []).append(r)

    print('=' * 92)
    print('  HAS ANY BUILD MOVED THE RATCHET?   IMU gyro excess / road control, speed-matched')
    print('=' * 92)
    print('  %-6s %-8s %6s %7s %7s %9s %9s %8s' %
          ('build', 'route', 'segs', 'eng s', 'man s', 'gyro exc', 'road ctl', 'ratio'))
    print('  ' + '-' * 74)
    seen = []
    for b in ORDER:
        for r in byb.get(b, []):
            print('  %-6s %-8s %6d %7.1f %7.1f %9.3f %9.3f %8.3f'
                  % (b, r[0], r[1], r[2], r[3], r[5], r[6], r[7]))
            seen.append((b, r[7]))
    for b in sorted(set(byb) - set(ORDER)):
        for r in byb[b]:
            print('  %-6s %-8s %6d %7.1f %7.1f %9.3f %9.3f %8.3f  (not in arc order)'
                  % (b, r[0], r[1], r[2], r[3], r[5], r[6], r[7]))
            seen.append((b, r[7]))
    unmapped = [r for r in rows if BUILD.get(r[0]) is None]
    if unmapped:
        print('  ' + '-' * 74)
        for r in unmapped:
            print('  %-6s %-8s %6d %7.1f %7.1f %9.3f %9.3f %8.3f  (route not in BUILD map)'
                  % ('?', r[0], r[1], r[2], r[3], r[5], r[6], r[7]))
    if not seen:
        print('  no flown build had a pooled speed-matched IMU arm.')
        print('  \U0001f6d1 EMPTY INPUT, not a null result.')
        return
    v = np.array([x[1] for x in seen], float)
    print('  ' + '-' * 74)
    print('  %d builds with an IMU arm.  median ratio %.3f   spread %.3f .. %.3f'
          % (len(seen), np.median(v), v.min(), v.max()))
    lo = sorted(seen, key=lambda x: x[1])[:3]
    print('  lowest three: ' + ', '.join('%s %.3f' % t for t in lo))
    print()
    print('  READING IT:')
    print('   * a build clearly BELOW the spread => the first off-EPS sign anything ever worked.')
    print('   * all inside the spread           => nothing has moved it, on an instrument no build')
    print('     could have influenced, and the arc\'s null is real rather than a CAN-scoring artefact.')
    print()
    print('  \U0001f6d1 ONE ROUTE PER BUILD: build and road are perfectly confounded. This is a SCREEN,')
    print('     not an attribution -- a standout is a lead to chase, not a result.')


if __name__ == '__main__':
    main()
