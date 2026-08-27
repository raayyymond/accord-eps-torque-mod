#!/usr/bin/env python3
"""Order-track the ratchet, and test whether V62 MOVED its frequency.

Deliverables 2 and 3 of the ratchet brief.

🛑 THE CONTAMINATION BOUNDARY. Wheel order 1 is f = v / circumference, circumference 2.073-2.090 m
(kit-measured, V56/V57), i.e. f ~= 0.479*v .. 0.482*v. Using the conservative 0.489*v the brief
quotes, order 1 enters the 6-9 Hz ratchet band at

    v = 6.0 / 0.489 = 12.3 m/s   and leaves it at   v = 9.0 / 0.489 = 18.4 m/s

so ANY ratchet statistic taken above ~12 m/s is tyre-contaminated, and any taken above ~11 m/s is
within one 0.39 Hz FFT bin of contamination. The ratchet claim is therefore restricted to
v < 11 m/s, and everything above is reported separately and labelled.

Two discriminators are applied, not one:
  (a) f0 vs speed        -- a road line is proportional to v; a structural mode is not.
  (b) CV(hertz) vs CV(order) -- whichever domain has the smaller relative scatter is the domain
      the line is fixed in.
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
# --- end path bootstrap ---------------------------------------------------
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import _r31_common as C  # noqa: E402
import _r37_ratchet_lib as L  # noqa: E402

CIRC = 2.080
VBINS = [(0.3, 1.5), (1.5, 2.5), (2.5, 4.0), (4.0, 6.0), (6.0, 8.0), (8.0, 11.0),
         (11.0, 14.0), (14.0, 18.0), (18.0, 23.0), (23.0, 30.0)]


def eng_mask(d):
    lat = d["cc_lat"] > 0.5
    g = (d["cs_gear"] == 2.0) if "cs_gear" in d else np.ones(len(d["t"]), bool)
    return lat & g & (d["cs_v"] > 0.3)


def main():
    print("RATCHET FREQUENCY vs SPEED, engaged, drive gear. Free locator 5-12 Hz "
          "(prominence spectrum).")
    print("Order-1 column is 0.489*v at the bin's median speed; ** marks bins where order 1 is "
          "inside 6-9 Hz.\n")
    store = {}
    for nm, ca, pf, sg in L.ROUTES:
        rs = L.collect(ca, pf, sg, mask_fn=eng_mask)
        store[nm] = rs
        print(f"  === {nm} ===")
        print(f"    {'v bin':>12s} {'nwin':>5s} {'nep':>4s} | {'f0 med':>7s} {'sd':>5s} | "
              f"{'RMS':>7s} {'env99':>8s} | {'prom p50':>9s} | {'order1':>7s} {'f0/order1':>10s}")
        for lo, hi in VBINS:
            c = [r for r in rs if lo <= r["v"] < hi]
            if len(c) < 3:
                continue
            f0 = np.array([r["fr"] for r in c])
            vm = np.median([r["v"] for r in c])
            o1 = 0.489 * vm
            flag = "**" if 6.0 <= o1 <= 9.0 else "  "
            print(f"    {lo:5.1f}-{hi:5.1f} {len(c):5d} {len(L.episodes(c)):4d} | "
                  f"{np.nanmedian(f0):7.2f} {np.nanstd(f0):5.2f} | "
                  f"{np.nanmedian([r['rms_r'] for r in c]):7.1f} "
                  f"{np.nanmedian([r['env_r'] for r in c]):8.1f} | "
                  f"{np.nanmedian([r['pr'] for r in c]):9.1f} | {o1:7.2f}{flag} "
                  f"{np.nanmedian(f0)/max(o1,1e-6):10.2f}")
        print()

    # ---- (a) speed dependence, split at the contamination boundary ---------------------------
    print("SPEED DEPENDENCE of the ratchet f0 (Spearman rho of f0 vs vEgo):")
    print(f"  {'route':14s} {'v<11 m/s':>26s} | {'v>=11 m/s':>26s}")
    for nm, rs in store.items():
        out = ""
        for lo, hi in ((0.3, 11.0), (11.0, 40.0)):
            c = [r for r in rs if lo <= r["v"] < hi and np.isfinite(r["fr"])]
            if len(c) < 8:
                out += f" {'n<8':>26s} |"
                continue
            rho, p = spearmanr([r["v"] for r in c], [r["fr"] for r in c])
            out += f" rho={rho:+.3f} p={p:.1e} n={len(c):<4d} |"
        print(f"  {nm:14s}{out}")

    # ---- (b) CV(hertz) vs CV(order), restricted to the clean speed range ----------------------
    print("\nDOMAIN TEST, engaged, 0.3-11 m/s (order 1 well clear of the band):")
    print(f"  {'route':14s} {'n':>4s} | {'f0 med':>7s} {'CV(Hz)':>7s} | {'order med':>9s} "
          f"{'CV(order)':>9s} | verdict")
    for nm, rs in store.items():
        c = [r for r in rs if 0.3 <= r["v"] < 11.0 and np.isfinite(r["fr"])]
        if len(c) < 8:
            print(f"  {nm:14s} {len(c):4d} | (n<8)")
            continue
        f0 = np.array([r["fr"] for r in c])
        od = np.array([r["fr"] * CIRC / r["v"] for r in c])
        cvf, cvo = f0.std(ddof=1) / np.median(f0), od.std(ddof=1) / np.median(od)
        print(f"  {nm:14s} {len(c):4d} | {np.median(f0):7.2f} {cvf:7.3f} | {np.median(od):9.2f} "
              f"{cvo:9.3f} | {'FIXED IN HERTZ (structural)' if cvf < cvo else 'FIXED IN ORDER (tyre)'}")

    # ---- did V62 move f0? speed-matched, clean speeds only ------------------------------------
    print("\nDID V62 MOVE THE RATCHET? Speed-matched, engaged, drive, CLEAN speeds only.")
    print(f"  {'v bin':>12s} | " + " | ".join(f"{nm:>13s}" for nm in store))
    for lo, hi in [(0.3, 1.5), (1.5, 2.5), (2.5, 4.0), (4.0, 6.0), (6.0, 8.0), (8.0, 11.0)]:
        row = f"  {lo:5.1f}-{hi:5.1f} | "
        for nm, rs in store.items():
            c = [r for r in rs if lo <= r["v"] < hi and np.isfinite(r["fr"])]
            row += (f"{np.median([r['fr'] for r in c]):6.2f} n={len(c):<4d}" if len(c) >= 3
                    else f"{'--':>13s}") + " | "
        print(row)

    print("\n  Reference: V61 lowered the torsion-bar RATE lane (Kd down); V62 doubled it "
          "(Kd up).\n  If omega_n^2 rises with Kd, V61 should sit BELOW V59 and V62 ABOVE it.")


if __name__ == "__main__":
    main()
