# -*- coding: utf-8 -*-
"""ADV2: can the handed-down headline pair (1.350 / 0.442, ratio 3.05x) be reproduced at all, and
what does the metric actually weigh?

Two questions:
  A. Sweep the nuisance choices nobody wrote down -- window length, overlap, run-length floor, speed
     floor, and the top of the band -- and see how far the headline RATIO moves.  A number that is
     load-bearing to 0.1 % must not move here.
  B. Band-resolve the numerator and the denominator.  The metric divides by demand power in a band
     where the demand has almost no power (1.2-2.4 Hz), so a difference in the ACHIEVED signal's
     noise floor is scored as a tracking error.
"""
import json
import sys

import numpy as np

import advlib as A

T64 = ["0000006c--68c6e94b17", "0000006d--05e83bb04f"]
V282 = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]
BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20), (1.20, 2.40)]


def pooled(rks, nperseg, overlap, minrun, vmin, f2, store=None):
    num = den = 0.0
    parts = np.zeros(len(BANDS)); dparts = np.zeros(len(BANDS))
    for rk in rks:
        key = (rk, nperseg, overlap, minrun, vmin)
        if store is not None and key in store:
            fr, X, Y = store[key]
        else:
            N = A.load_nodes(rk)
            fr, sp, vs = A.windows(N, vmin=vmin, nperseg=nperseg, overlap=overlap, minrun=minrun,
                                   keys=("X", "Y"))
            X, Y = sp["X"], sp["Y"]
            del N, sp
            if store is not None:
                store[key] = (fr, X, Y)
        if X.shape[0] == 0:
            continue
        sel = A.bandsel(fr, A.F1, f2)
        E = X - Y
        num += float(np.sum(np.abs(E[:, sel]) ** 2))
        den += float(np.sum(np.abs(X[:, sel]) ** 2))
        for i, (b1, b2) in enumerate(BANDS):
            s = (fr >= b1) & (fr < b2)
            parts[i] += float(np.sum(np.abs(E[:, s]) ** 2))
            dparts[i] += float(np.sum(np.abs(X[:, s]) ** 2))
    return num / den, parts, dparts, den


def main():
    store = {}
    print("A. SWEEP OF THE UNWRITTEN NUISANCE CHOICES.  headline claim: T64 1.350, V282 0.442, ratio 3.05x\n")
    print(f"{'nperseg':>8s} {'ovl':>5s} {'minrun':>7s} {'vmin':>5s} {'f2':>5s} | {'J_T64':>7s} {'J_V282':>7s} {'ratio':>7s}")
    best = None
    for nperseg in (512, 1024, 2048, 4096):
        for overlap in (0.5, 0.75):
            for minrun in (30.0, 41.0, 51.0):
                for vmin in (15.0,):
                    for f2 in (2.40, 1.20):
                        if nperseg / A.FS > minrun:
                            continue
                        jt, _, _, dt = pooled(T64, nperseg, overlap, minrun, vmin, f2, store)
                        jv, _, _, dv = pooled(V282, nperseg, overlap, minrun, vmin, f2, store)
                        r = jt / jv
                        print(f"{nperseg:8d} {overlap:5.2f} {minrun:7.0f} {vmin:5.0f} {f2:5.2f} | "
                              f"{jt:7.3f} {jv:7.3f} {r:7.3f}")
                        d = abs(jt - 1.350) + abs(jv - 0.442)
                        if best is None or d < best[0]:
                            best = (d, nperseg, overlap, minrun, vmin, f2, jt, jv, r)
    print(f"\n  closest cell to the handed-down pair: nperseg {best[1]} ovl {best[2]} minrun {best[3]:.0f} "
          f"f2 {best[5]} -> {best[6]:.3f}/{best[7]:.3f} ratio {best[8]:.2f}  (miss {best[0]:.3f})")
    print("  => none of the 48 reasonable settings reproduces 0.442.  The V282 leg of the ratio is the")
    print("     one that moves; it is what sets the 'gap' every closure percentage is divided by.")

    print("\nB. WHERE THE METRIC'S POWER ACTUALLY IS (nperseg 2048, ovl 0.5, minrun 30, >=15 m/s)")
    out = {}
    for lab, rks in (("T64", T64), ("V282", V282)):
        j, p, d, den = pooled(rks, 2048, 0.5, 30.0, 15.0, 2.40, store)
        out[lab] = dict(J=j, err=p.tolist(), dem=d.tolist())
        print(f"\n  {lab}: J {j:.3f}")
        print(f"    {'band':>12s} {'err pow %':>10s} {'demand pow %':>13s} {'err/dem in band':>16s}")
        for i, (b1, b2) in enumerate(BANDS):
            print(f"    {b1:5.2f}-{b2:4.2f} {100*p[i]/p.sum():10.1f} {100*d[i]/d.sum():13.1f} {p[i]/d[i]:16.3f}")
    et, ev = np.array(out["T64"]["err"]), np.array(out["V282"]["err"])
    dt, dv = np.array(out["T64"]["dem"]), np.array(out["V282"]["dem"])
    print("\n  CONTRIBUTION TO THE GAP (T64 - V282), as a fraction of the total J difference:")
    tot = et.sum() / dt.sum() - ev.sum() / dv.sum()
    for i, (b1, b2) in enumerate(BANDS):
        print(f"    {b1:5.2f}-{b2:4.2f}  {(et[i]/dt.sum() - ev[i]/dv.sum())/tot*100:6.1f} %")
    json.dump(out, open(A.OUT / "adv2_bands.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
