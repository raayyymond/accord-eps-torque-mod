#!/usr/bin/env python3
r"""score/score_v102_ancova.py -- the peak triple with the SPEED SLOPE removed, and the ratchet band.

WHY: `score/score_v102_peak_cave.py` s3C measured a REAL, non-tyre speed slope on the resonance --
V102 +0.1594 [+0.1362, +0.1844] Hz/(m/s), V100 +0.161, V101 +0.110, all excluding the order-1 tyre
slope +0.489.  The arms' mean speeds differ by up to 10 km/h, so a raw f0 comparison confounds
gain with speed.  Here f0 is regressed on speed per build and evaluated at a COMMON reference
speed, with the slope pooled across builds (they agree within error).
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26) -------------------------------
# This file imports sibling modules by bare name.  It used to sit flat in the
# kit directory; now that it is nested, put the kit root and every code
# subfolder on sys.path so those imports still resolve from anywhere.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_p = [_r]
for _b, _ds, _fs in _os.walk(_r):
    _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
              ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
    _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
del _os, _sys, _r, _p, _b, _ds, _fs
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import score_v102_peak_cave as K  # noqa: E402
import score_v102_full as F  # noqa: E402
import score_v102_matched as M  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

VREF_KMH = 40.0                       # a speed all four builds actually drove engaged


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


if __name__ == "__main__":
    hdr("3D -- 🛑 PEAK FREQUENCY AT A COMMON SPEED (%.0f km/h).  Per-window local-max f0 regressed\n"
        "      on speed; slope POOLED across builds (they agree); intercepts compared.\n"
        "      This removes the +0.16 Hz/(m/s) speed slope that confounds the raw triple."
        % VREF_KMH)
    rng = np.random.default_rng(77)
    DAT = {}
    for r, lab, gl, _g in K.ARMS:
        P, vs, ep = K.collect(r, 5, 115)
        fw = np.array([K.peak_of(p)[0] for p in P])
        ok = np.array([K.peak_of(p)[2] for p in P])
        prom = np.array([K.peak_of(p)[1] for p in P])
        DAT[r] = dict(lab=lab, gl=gl, f=fw[ok], v=vs[ok] / 3.6, prom=prom[ok], ep=ep[ok])
        print("      %-11s %-4s  %3d local-max windows   v mean %5.1f km/h   median prominence %.2f"
              % (lab, gl, len(DAT[r]["f"]), DAT[r]["v"].mean() * 3.6,
                 float(np.median(DAT[r]["prom"]))))

    # pooled slope, excluding STOCK (it has no line -- its "peaks" are noise argmaxes)
    LIVE = ["85", "96", "95"]
    X = np.concatenate([DAT[r]["v"] for r in LIVE])
    Y = np.concatenate([DAT[r]["f"] for r in LIVE])
    G = np.concatenate([np.full(len(DAT[r]["f"]), i) for i, r in enumerate(LIVE)])
    A = np.column_stack([X] + [(G == i).astype(float) for i in range(len(LIVE))])
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    slope = coef[0]
    print("\n      pooled slope (V100+V102+V101, STOCK excluded -- it has no line) = "
          "%+.4f Hz/(m/s)" % slope)
    print("\n      %-11s %-4s %12s %12s   %s" % ("build", "gain", "f0 @%.0f km/h" % VREF_KMH,
                                                 "95%% CI", "n"))
    ref = VREF_KMH / 3.6
    res = {}
    for i, r in enumerate(LIVE):
        f0 = coef[1 + i] + slope * ref
        bs = []
        for _ in range(3000):
            sel = {rr: rng.integers(0, len(DAT[rr]["f"]), len(DAT[rr]["f"])) for rr in LIVE}
            Xb = np.concatenate([DAT[rr]["v"][sel[rr]] for rr in LIVE])
            Yb = np.concatenate([DAT[rr]["f"][sel[rr]] for rr in LIVE])
            Gb = np.concatenate([np.full(len(sel[rr]), j) for j, rr in enumerate(LIVE)])
            Ab = np.column_stack([Xb] + [(Gb == j).astype(float) for j in range(len(LIVE))])
            cb, *_ = np.linalg.lstsq(Ab, Yb, rcond=None)
            bs.append(cb[1 + i] + cb[0] * ref)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        res[r] = (f0, lo, hi)
        print("      %-11s %-4s %12.2f  [%5.2f, %5.2f]   %d"
              % (DAT[r]["lab"], DAT[r]["gl"], f0, lo, hi, len(DAT[r]["f"])))
    print("\n      pairwise differences at %.0f km/h (bootstrapped):" % VREF_KMH)
    for a, b in (("85", "96"), ("96", "95"), ("85", "95")):
        bs = []
        for _ in range(3000):
            sel = {rr: rng.integers(0, len(DAT[rr]["f"]), len(DAT[rr]["f"])) for rr in LIVE}
            Xb = np.concatenate([DAT[rr]["v"][sel[rr]] for rr in LIVE])
            Yb = np.concatenate([DAT[rr]["f"][sel[rr]] for rr in LIVE])
            Gb = np.concatenate([np.full(len(sel[rr]), j) for j, rr in enumerate(LIVE)])
            Ab = np.column_stack([Xb] + [(Gb == j).astype(float) for j in range(len(LIVE))])
            cb, *_ = np.linalg.lstsq(Ab, Yb, rcond=None)
            bs.append(cb[1 + LIVE.index(b)] - cb[1 + LIVE.index(a)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        print("        %-5s -> %-5s   %+6.2f Hz  [%+.2f, %+.2f]   %s"
              % (DAT[a]["gl"], DAT[b]["gl"], np.mean(bs), lo, hi,
                 "SEPARATED" if lo > 0 or hi < 0 else "NOT separated"))

    hdr("7 -- THE OPERATOR'S OTHER SYMPTOM: the 7.3-9.3 Hz ratchet band, matched speed.\n"
        "     His words -- V102: \"Ratcheting was bad, similar to 4x torque mod.\"\n"
        "                  STOCK: \"barely perceptible ratcheting.\"")
    TAB = {r: F.build_table(r) for r, _, _, _ in K.ARMS}
    VE = (5, 20, 35, 50, 65, 80, 95, 115)
    for c in ("tq", "rate_f", "cs_ang"):
        for A, B, nm in (("97", "96", "V102 / STOCK"), ("97", "85", "V100 / STOCK"),
                         ("85", "96", "V102 / V100")):
            d, cen = M.matched_ratio(TAB[A], TAB[B], c, "B8", "CTRL", vedges=VE)
            if d:
                print("      %-7s %-16s = %6.3f  EPISODE [%5.3f, %6.3f]  cells=%d"
                      % (c, nm, d["r"], d["lo"], d["hi"], d["cells"]))
        d, cen = M.matched_ratio(TAB["95"], TAB["96"], c, "B8", "CTRL")
        if d:
            print("      %-7s %-16s = %6.3f  EPISODE [%5.3f, %6.3f]  cells=%d  (5-65 km/h overlap)"
                  % (c, "V102 / V101", d["r"], d["lo"], d["hi"], d["cells"]))
