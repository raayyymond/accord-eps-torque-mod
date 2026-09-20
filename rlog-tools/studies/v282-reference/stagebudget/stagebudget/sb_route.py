# -*- coding: utf-8 -*-
"""Stage 5: PER ROUTE.  The loop leg L34 (setpoint -> wheel angle) route by route, because the group
pooling hides both the route/road confound and the fact that two routes inside `T2` flew very
different fork configurations.

Flown fork configuration, EVIDENCE (each route's own initData via hsurface/surface/params_all.json,
plus `git show <commit>` for the constants that are NOT toggles):

  route  grp      EPS   ff  Kp    LAF   Kp/LAF  Ki    RF    D      in-loop extras          G table
  r64/65 V282     V282  on  0.9   6.0   0.150   0.30  --    0.200  none                    120/95/85/70
  r6c    V282     V282  on  0.9   6.0   0.150   0.30  --    0.200  none                    120/95/85/70
  r70    T2       V293  OFF 0.3   6.0   0.050   0.15  --    0.200  none                    (FF not run)
  r71    T2       V293  on  0.85  14.0  0.061   0.30  --    0.200  none                    550/271/246/167
  r72/73 T3       V293  on  0.85  14.0  0.061   0.60  0.12  0.274  notch, hyst, rate-meas  550/271/246/167
  r75    T4       V293  on  0.85  14.0  0.061   0.60  0.12  0.280  notch, hyst, rate-meas  550/271/246/167
  r76    T5       V293  on  1.0   14.0  0.071   0.30  0.12  0.286  + disturbance observer  550/271/246/167
  r6c/6d T64      V293  on  1.0   14.0  0.071   0.30  0.06  0.299  + hold level, jerk 4 Hz 550/271/246/167
  r6e    T64B     V293  on  1.0   14.0  0.071   0.30  0.06  0.302  + hold level, HL off    550/271/246/167

  Kp/LAF is the P gain from lateral-accel error to commanded torque.  EVERY torque rev ran it 2.1-3.0x
  LOWER than V282 -- that is a fork parameter difference and a live confound on any "the EPS is slower"
  reading of the loop leg, and it is stated here rather than divided out.

ANALYSIS ONLY, read-only.  usage: python sb_route.py > out/ROUTE-OUT.txt
"""
import sys

import numpy as np

import sb_lib as L
from sb_budget import Spec, cell
from sb_budget2 import C4, gate

TAG = {"00000064--ce6b0b0ebb": "r64 V282", "00000065--b9f78988bd": "r65 V282",
       "0000006c--2bc842dbac": "r6c V282", "00000039--f56039af87": "r39 V282old",
       "0000003a--283a39a1d6": "r3a V282old", "0000003c--927965c2b4": "r3c V282old",
       "00000070--717f5a7866": "r70 T2 FFoff", "00000071--f2c9d073a3": "r71 T2",
       "00000072--8001fc3048": "r72 T3", "00000073--79fd149dd8": "r73 T3",
       "00000075--6c8687d5bd": "r75 T4", "00000074--2bf17ca67d": "r74 T4",
       "00000076--d0b7ea7e4d": "r76 T5", "0000006c--68c6e94b17": "r6c' T64",
       "0000006d--05e83bb04f": "r6d T64", "0000006e--6ca3e014fd": "r6e T64B"}
ORDER = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
         "00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4",
         "00000070--717f5a7866", "00000071--f2c9d073a3",
         "00000072--8001fc3048", "00000073--79fd149dd8", "00000075--6c8687d5bd",
         "00000076--d0b7ea7e4d", "0000006c--68c6e94b17", "0000006d--05e83bb04f",
         "0000006e--6ca3e014fd"]


def main():
    for f1, f2, W in L.BANDS[1:3]:
        S = Spec(W)
        print("=" * 140)
        print(f"BAND {f1:.2f}-{f2:.2f} Hz -- every route's own four legs, per speed bin.")
        print("  The two software legs L1/L2 are a PER-ROUTE CONTROL: they are linear filters whose")
        print("  constants are known, so any route-to-route spread in them is the estimator's noise floor.")
        print("=" * 140)
        for sb in range(4):
            hdr = False
            for rk in ORDER:
                idx = np.where((S.route == rk) & (S.sbin == sb))[0]
                c = cell(S, idx, f1, f2, C4)
                if c is None or c["n"] < 6:
                    continue
                if not hdr:
                    print(f"\n-- speed {L.SPDN[sb]} --")
                    print(f"  {'route':14s} {'n':>4s} {'v':>5s} {'medA':>7s} | {'L1 lag':>7s} {'L2 lag':>7s} "
                          f"{'L34 g':>7s} {'L34 lag':>8s} {'L5 g':>6s} {'L5 lag':>7s} | {'TOT g':>6s} "
                          f"{'TOT lag':>8s} | {'cohM':>5s}")
                    hdr = True
                print(f"  {TAG[rk]:14s} {c['n']:>4d} {c['v']:>5.1f} {c['am']:>7.4f} | "
                      f"{c['tau'][0]*1e3:>+7.0f} {c['tau'][1]*1e3:>+7.0f} "
                      f"{c['g'][2]:>7.3f} {c['tau'][2]*1e3:>+8.0f} {c['g'][3]:>6.3f} {c['tau'][3]*1e3:>+7.0f} | "
                      f"{c['g_end']:>6.3f} {c['t_end']*1e3:>+8.0f} | {c['coh']['M']:>5.2f}"
                      + ("" if gate(c, C4) else "  WEAK"))
        print()
        del S
    return 0


if __name__ == "__main__":
    sys.exit(main())
