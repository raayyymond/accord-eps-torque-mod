#!/usr/bin/env python3
"""D5 ss13-14 -- what the HAND actually feels, and the audibility contrast done properly.

  ss13  🛑 ss12 returned all-NaN because `_grind2_lib`'s `cell` is (eng, VSPEED, eff, rate) -- speed
        is INSIDE the stratification key, so a creep cell and a highway cell can never overlap and
        the estimator has nothing to average. Restratify on (eff, rate) only, via `N.recell`, which
        is what a speed contrast needs.
  ss14  THE FELT AMPLITUDE. The hand feels ANGULAR MOTION, not spectral prominence. For a given
        torque amplitude a 7.8 Hz oscillation moves the rim (21/7.8)^2 ~ 7x further than a 21 Hz one.
        So measure the p99 band envelope of the ANGLE channel in both bands: if 6-9 Hz dominates the
        motion at BOTH creep and cruise, then the operator feels 7.8 Hz in both cases and the only
        difference between "grind #1" and "micro ratchet" is whether the co-occurring 18-22 Hz
        component is large enough to be HEARD. That is the whole reconciliation, in one table.
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import _r31_common as C  # noqa: E402
import _r59_lib as L  # noqa: E402
from d5_identity_coupling import segs_of  # noqa: E402

OUT = ROOT / "_scratch/out/_d5_felt.json"
RNG = np.random.default_rng(13142026)
VB = [(0.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 15.0), (15.0, 25.0), (25.0, 1e9)]
VN = ["0-2", "2-4", "4-8", "8-15", "15-25", "25+"]


def vbin(v):
    for i, (lo, hi) in enumerate(VB):
        if lo <= v < hi:
            return i
    return len(VB) - 1


def main():
    L.install_fs()
    res = {}
    store = N.records()
    eng = [r for b in N.LADDER for r in store.get(b, []) if r["eng"] == 1]

    # ---------------------------------------------------------------- ss13 ----------------------
    L.hdr("ss13  AUDIBILITY CONTRAST, restratified on (effort, rate) only -- speed is the CONTRAST")
    cells = {"creep 1.5-3 m/s": [r for r in eng if 1.5 <= r["v"] < 3.0],
             "0-4 m/s": [r for r in eng if r["v"] < 4.0],
             "4-8 m/s": [r for r in eng if 4.0 <= r["v"] < 8.0],
             "8-15 m/s": [r for r in eng if 8.0 <= r["v"] < 15.0],
             "25+ m/s": [r for r in eng if r["v"] >= 25.0]}
    key = lambda r: (G.binof(r["eff"], G.E_BINS), G.binof(r["rate"], G.R_BINS))  # noqa: E731
    ref = N.recell([r for r in eng if 15.0 <= r["v"] < 25.0], key)
    print(f"  reference cell = 15-25 m/s engaged (n={len(ref)}).  matched on driver effort and "
          f"steering rate.\n")
    print(f"  {'cell':<18}{'n':>6}{'cells':>7}   {'e_18-22 ratio':>26}{'e_6-9 ratio':>26}")
    for nm, rs in cells.items():
        if len(rs) < 20:
            continue
        A = N.recell(rs, key)
        s = f"  {nm:<18}{len(rs):>6}"
        first = True
        for k in ("e_18-22", "e_6-9"):
            r_, l_, h_, nc = G.boot_cellwise(A, ref, k, RNG, nboot=800, min_ep=2, min_win=4)[:4]
            if first:
                s += f"{nc:>7}   "
                first = False
            s += f"{r_:>12.2f}x [{l_:>5.2f},{h_:>5.2f}]"
            res.setdefault("audibility", {})[f"{nm}|{k}"] = dict(r=r_, lo=l_, hi=h_, ncell=nc)
        print(s)
    n18 = G.split_half_null(N.recell(eng, key), "e_18-22", RNG, nrep=120, min_ep=2, min_win=4)
    n69 = G.split_half_null(N.recell(eng, key), "e_6-9", RNG, nrep=120, min_ep=2, min_win=4)
    print(f"\n  split-half null, same estimator:  e_18-22 {n18[0]:.2f} [{n18[1]:.2f},{n18[2]:.2f}]"
          f"    e_6-9 {n69[0]:.2f} [{n69[1]:.2f},{n69[2]:.2f}]")
    res["null"] = dict(e18=list(n18), e69=list(n69))

    # ---------------------------------------------------------------- ss14 ----------------------
    L.hdr("ss14  WHAT THE HAND FEELS -- p99 band envelope of the ANGLE channel (deg) and `tq`")
    print("  engaged. `ang` is the raw 0x18F steering angle, deg. `tq` is the torsion-bar sensor.\n")
    nfft = 256
    taper = np.hanning(nfft) + 1e-3
    cw = slice(int(0.2 * nfft), int(0.8 * nfft))
    acc = {i: {k: [] for k in ("a69", "a1822", "t69", "t1822")} for i in range(len(VB))}
    for b in N.LADDER:
        for s, d in segs_of(b):
            fs = G.fs_of(d)
            xa = np.asarray(d["ang"], float)
            xt = np.asarray(d["tq"], float)
            v = np.abs(np.asarray(d["cs_v"], float))
            m = np.asarray(d["cc_lat"], float) > 0.5
            for a, e in C.runs_of(m, d["t"], nfft):
                for i in range(a, e - nfft + 1, nfft):
                    wa, wt = xa[i:i + nfft], xt[i:i + nfft]
                    if not (np.all(np.isfinite(wa)) and np.all(np.isfinite(wt))):
                        continue
                    j = vbin(float(np.mean(v[i:i + nfft])))
                    acc[j]["a69"].append(G.win_env(wa, fs, 6, 9, taper, cw))
                    acc[j]["a1822"].append(G.win_env(wa, fs, 18, 22, taper, cw))
                    acc[j]["t69"].append(G.win_env(wt, fs, 6, 9, taper, cw))
                    acc[j]["t1822"].append(G.win_env(wt, fs, 18, 22, taper, cw))
    print(f"  {'v (m/s)':<9}{'n':>6}   {'ANGLE 6-9':>12}{'ANGLE 18-22':>13}{'ratio':>8}   "
          f"{'TQ 6-9':>10}{'TQ 18-22':>10}{'ratio':>8}")
    for i, nm in enumerate(VN):
        A = acc[i]
        if len(A["a69"]) < 10:
            print(f"  {nm:<9}{len(A['a69']):>6}   -- underpowered")
            continue
        a69, a18 = np.median(A["a69"]), np.median(A["a1822"])
        t69, t18 = np.median(A["t69"]), np.median(A["t1822"])
        print(f"  {nm:<9}{len(A['a69']):>6}   {a69:>12.4f}{a18:>13.4f}{a69/a18:>8.2f}   "
              f"{t69:>10.0f}{t18:>10.0f}{t69/t18:>8.2f}")
        res.setdefault("felt", {})[nm] = dict(n=len(A["a69"]), a69=float(a69), a1822=float(a18),
                                              t69=float(t69), t1822=float(t18))
    print("\n  ANGLE units are degrees (p99 of the analytic band envelope, i.e. the amplitude;")
    print("  peak-to-peak is 2x). ratio > 1 means that band dominates the MOTION of the rim.")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=float)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
