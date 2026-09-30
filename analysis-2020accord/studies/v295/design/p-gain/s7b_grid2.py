# -*- coding: utf-8 -*-
"""s7b_grid2.py -- rev 2 of the regressive grid (s7): the local-slope filter now excludes the P-clamp top (idx 2..150,
>= 0.60), flat multiples are scored alongside, and the grid moves to longer tapers (the rev-1 table showed the taper END
is what buys the mid-speed benefit and the plateau length costs lp 1-3 Hz motion).  Plants nominal + light_b (the two
worlds); finalists go to s8 on the full family.  Same scoring code as s7 (imported).
ANALYSIS ONLY."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s7_regress_grid as S7  # noqa: E402

S7.GRID_K0 = (1.25, 1.35, 1.45)
S7.GRID_I1 = (4, 12)
S7.GRID_I2 = (100, 140, 180)
S7.TAG = "s7b_grid2"
_grid = S7.grid


def grid():
    b, C = _grid()
    C.append(b.replace(kp_x=(0, 8, 54, 100, 208), kp_y=(1248, 1248, 1104, 960, 960), name="R1.3_8_100"))
    return b, C


S7.grid = grid
S7.PLANTS = ("nominal", "light_b")      # 2 plants keep the batch in memory; finalists go to s8 on the family

if __name__ == "__main__":
    S7.main()
