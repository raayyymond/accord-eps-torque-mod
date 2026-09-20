# -*- coding: utf-8 -*-
"""a7 -- how far does the plant's amplitude dependence go, and is it amplitude or speed?

The shake-band loop gain is what any SteerKP case has to be bounded by, and it is 3x larger on
high-demand windows than on low-demand ones.  Two questions the study never asked:
  * does |P| in 1.8-3.5 Hz SATURATE with demand amplitude, or keep climbing past the top tercile?
  * is the trend amplitude, or is it speed / road leaking in through the tercile split?
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adv_core as A  # noqa: E402

FLOWN = dict(kp=1.0, laf=14.0, ki=0.30, q=1.0)


def main():
    Wt = A.cat([A.extract(r, nps=1024) for r in A.T64])
    f = Wt["f"]
    shk = (f >= A.SHAKE[0]) & (f <= A.SHAKE[1])
    lo6 = (f >= 0.15) & (f <= 0.60)
    print("=" * 108)
    print("1. |P| (command -> the controller's own measurement) by demand-amplitude QUINTILE")
    print(f"{'quintile':>9s} {'n':>4s} {'med |X| rms':>12s} {'med v':>7s} {'|P| 0.15-0.6':>13s} "
          f"{'|P| 1.8-3.5':>12s} {'|L|shk @KP1':>12s} {'|L|shk @KP3 Q0.6':>17s}")
    qs = np.quantile(Wt["amp"], [0.2, 0.4, 0.6, 0.8])
    edges = [-np.inf] + list(qs) + [np.inf]
    for k in range(5):
        sel = (Wt["amp"] > edges[k]) & (Wt["amp"] <= edges[k + 1])
        if sel.sum() < 4:
            continue
        idn = A.identify(Wt, inst="X", vsel=sel)
        C0 = A.C_fb(f, Wt["v"][sel], **FLOWN)
        C1 = A.C_fb(f, Wt["v"][sel], 3.0, 14.0, 0.30, 0.6)
        L0 = idn["P"][None, :] * C0
        L1 = idn["P"][None, :] * C1
        print(f"{k+1:9d} {int(sel.sum()):4d} {np.median(Wt['amp'][sel]):12.3f} {np.median(Wt['v'][sel]):7.1f} "
              f"{float(np.mean(np.abs(idn['P'][lo6]))):13.3f} {float(np.mean(np.abs(idn['P'][shk]))):12.3f} "
              f"{float(np.mean(np.abs(L0[:, shk]))):12.3f} {float(np.mean(np.abs(L1[:, shk]))):17.3f}")

    print()
    print("2. IS IT AMPLITUDE OR SPEED?  Split on amplitude INSIDE each speed bin.")
    print(f"{'speed':>8s} {'amp half':>9s} {'n':>4s} {'med |X|':>8s} {'|P| 1.8-3.5':>12s} {'|L|shk @KP3 Q0.6':>17s}")
    for lo, hi in ((15.0, 22.0), (22.0, 99.0)):
        vs = (Wt["v"] >= lo) & (Wt["v"] < hi)
        med = np.median(Wt["amp"][vs])
        for tag, sel in (("low", vs & (Wt["amp"] <= med)), ("high", vs & (Wt["amp"] > med))):
            if sel.sum() < 4:
                continue
            idn = A.identify(Wt, inst="X", vsel=sel)
            C1 = A.C_fb(f, Wt["v"][sel], 3.0, 14.0, 0.30, 0.6)
            L1 = idn["P"][None, :] * C1
            print(f"{f'{lo:.0f}-{hi:.0f}':>8s} {tag:>9s} {int(sel.sum()):4d} {np.median(Wt['amp'][sel]):8.3f} "
                  f"{float(np.mean(np.abs(idn['P'][shk]))):12.3f} {float(np.mean(np.abs(L1[:, shk]))):17.3f}")

    print()
    print("3. AND WHAT THE EXCLUDED WINDOWS LOOK LIKE.  The metric drops any window more than 2 %")
    print("   saturated and any run shorter than 30 s.  Re-extract with NO run-length floor and NO")
    print("   saturation filter and compare the demand amplitude that gets scored vs dropped.")
    Wall = A.cat([A.extract(r, nps=1024, run_s=0.0, satfilt=None) for r in A.T64])
    print(f"      scored set  : n {len(Wt['v']):4d}   |X| rms median {np.median(Wt['amp']):.3f}  "
          f"p90 {np.quantile(Wt['amp'],0.9):.3f}  max {Wt['amp'].max():.3f}")
    print(f"      everything  : n {len(Wall['v']):4d}   |X| rms median {np.median(Wall['amp']):.3f}  "
          f"p90 {np.quantile(Wall['amp'],0.9):.3f}  max {Wall['amp'].max():.3f}")
    drop = np.quantile(Wall["amp"], 0.9)
    selhi = Wall["amp"] > drop
    idn = A.identify(Wall, inst="X", vsel=selhi)
    C1 = A.C_fb(f, Wall["v"][selhi], 3.0, 14.0, 0.30, 0.6)
    C0 = A.C_fb(f, Wall["v"][selhi], **FLOWN)
    print(f"      top decile of ALL windows (n {int(selhi.sum())}): |P| 1.8-3.5 = "
          f"{float(np.mean(np.abs(idn['P'][shk]))):.3f}, |L|shk @KP1 = "
          f"{float(np.mean(np.abs((idn['P'][None,:]*C0)[:, shk]))):.3f}, @KP3 Q0.6 = "
          f"{float(np.mean(np.abs((idn['P'][None,:]*C1)[:, shk]))):.3f}")


if __name__ == "__main__":
    main()
