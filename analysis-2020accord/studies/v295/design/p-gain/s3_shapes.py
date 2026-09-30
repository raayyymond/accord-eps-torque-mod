# -*- coding: utf-8 -*-
"""s3_shapes.py -- the candidate SHAPES of the p-gain lens, as delivered surfaces read from the golden model:
static ratio T_c/T_V294 and local slope (T per wire count) at the operating points the r71b census found
(straights idx 5-7 at >= 10 m/s and 7-14 below; turn holds idx 18 / 34 / 36 / 50 at 22+ / 15-22 / 10-15 / 5-10 m/s;
hard turns idx 43-75), monotonicity, rail, trim cap at the operating points (C*Kp(idx)/256 through the chain).
ANALYSIS ONLY."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H

OPS = [0, 1, 3, 6, 10, 14, 18, 25, 34, 50, 65, 75, 100, 150, 200]


def cands():
    b = H.Cells.v294()
    my = b.map_y
    C = [b]
    for g in (1.2, 1.3, 1.4):
        C.append(b.replace(kp_y=(int(round(960 * g)),) * 5, name="g%.1f" % g))
    # Kp schedules (5 knots; X moved into the busy zone)
    C.append(b.replace(kp_x=(0, 12, 32, 96, 208), kp_y=(1248, 1248, 1104, 1008, 960), name="K-regress"))
    C.append(b.replace(kp_x=(0, 20, 40, 64, 208), kp_y=(1152, 1248, 1248, 1152, 1008), name="K-mid"))
    C.append(b.replace(kp_x=(0, 24, 48, 96, 208), kp_y=(1248, 1248, 1248, 1104, 1008), name="K-1.3taper"))
    # demand-map shapes (FF only, Kp 960, trim untouched): same X knots as V294
    C.append(b.replace(map_y=(0, 83, 117, 134, 169, 306, 444, 581, 719, 1032), name="M-regress"))
    C.append(b.replace(map_y=tuple(int(round(y * 1.3)) for y in my[:6]) + (440, 550, 688, 1032), name="M-mid"))
    C.append(b.replace(map_y=tuple(min(int(round(y * 1.3)), 1032) for y in my), name="M-x1.3"))
    return C


def main():
    base = H.Cells.v294()
    kp_tab = lambda c: H.lerp_table(c.kp_x, c.kp_y)  # noqa: E731
    for c in cands():
        mono, dmin = G.monotone(c)
        S = G.surface_table(c)
        rail_idx = int(np.argmax(S >= S.max()))
        print("\n%-11s Kp X %s Y %s | map Y %s" % (c.name, c.kp_x, c.kp_y, c.map_y))
        print("   monotone %s (min step %d)  rail %d first at idx %d  problems %s" % (mono, dmin, S.max(), rail_idx, c.problems()))
        print("   idx      " + " ".join("%6d" % i for i in OPS))
        print("   T        " + " ".join("%6.0f" % S[i] for i in OPS))
        print("   ratio    " + " ".join("%6.2f" % (S[i] / G.surface_table(base)[i] if G.surface_table(base)[i] else np.nan) for i in OPS))
        print("   slope/V294 " + " ".join("%5.2f" % (G.local_slope(c, i) / G.local_slope(base, i)) for i in OPS))
        print("   Kp(idx)  " + " ".join("%6d" % kp_tab(c)[i] for i in OPS))
        print("   trim cap T at idx (C*Kp/256 through the chain, T counts): " +
              " ".join("%d" % round(c.fb_clamp * kp_tab(c)[i] / 256 * 254 / 256 * 0.990234 * c.gain / 32768) for i in (0, 6, 18, 50)))


if __name__ == "__main__":
    main()
