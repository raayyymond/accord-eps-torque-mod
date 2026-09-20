# -*- coding: utf-8 -*-
"""r5 -- what is actually ON the wire: band power of the measured wheel rate, per route.

The gate turns on r73 being labelled "flew clean".  The fork's own commit message for the NEXT
commit says r73 chattered at 4 Hz.  This measures it, with r72 (same commit, relay off) as control.
Band power of steeringRateDeg, engaged hands-off, >= 15 m/s, normalised by the 0.3-1.0 Hz power of
the same run so road/driving content divides out.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from r1_ident import grid, runs_of  # noqa: E402
import r2_stat as R  # noqa: E402

NW = 1024
BANDS = [(1.5, 2.0), (2.0, 2.6), (2.6, 3.2), (3.2, 4.0), (4.0, 5.0), (5.0, 6.5)]
REF = (0.3, 1.0)
ROUTES = ["00000071--f2c9d073a3", "00000072--8001fc3048", "00000073--79fd149dd8",
          "0000006c--68c6e94b17", "0000006e--6ca3e014fd", "00000075--6c8687d5bd",
          "00000076--d0b7ea7e4d", "00000070--717f5a7866",
          "00000064--ce6b0b0ebb", "00000065--b9f78988bd"]


def main():
    C = R.read_controllers()
    f = np.fft.rfftfreq(NW, 0.01)
    w = np.hanning(NW)
    print("normalised wheel-rate band power (band / 0.3-1.0 Hz), engaged hands-off >= 15 m/s")
    print(f"{'route':22s} {'label':24s} {'relay':>6s} {'nwin':>5s} "
          + "".join(f"{f'{a}-{b}':>10s}" for a, b in BANDS) + f"{'peak Hz':>9s}")
    for rt in ROUTES:
        g = grid(rt)
        m = (g["lat_active"] > 0.5) & (g["spress"] < 0.5) & (g["vego"] >= 15.0)
        S = np.zeros(len(f))
        n = 0
        for i, j in runs_of(m, NW):
            for s in range(i, j - NW + 1, NW // 2):
                X = np.fft.rfft((g["sr_deg"][s:s + NW] - g["sr_deg"][s:s + NW].mean()) * w)
                S += np.abs(X) ** 2
                n += 1
        if n == 0:
            continue
        S /= n
        ref = S[(f >= REF[0]) & (f < REF[1])].sum()
        p = C[rt]
        row = [S[(f >= a) & (f < b)].sum() / ref for a, b in BANDS]
        sel = (f >= 1.5) & (f <= 6.5)
        pk = f[sel][int(np.argmax(S[sel]))]
        print(f"{rt:22s} {p['lbl'][:24]:24s} {('LIVE' if p['relay'] else 'dead'):>6s} {n:5d} "
              + "".join(f"{x:10.4f}" for x in row) + f"{pk:9.2f}")
        del g


if __name__ == "__main__":
    main()
