#!/usr/bin/env python3
r"""studies/impedance/stock_r97_rez_matched.py -- Re(Z) on STOCK vs the modded arms, SPEED-MATCHED.

The unmatched R3 table is confounded: stock's engaged hands-off windows have a median speed of
21.2 m/s (76 km/h) while V100's are 12.8 m/s and V102's 15.5 m/s.  Re(Z) is a driving-point
impedance and the plant it measures depends on speed (tyre self-aligning torque, rack load), so an
unmatched stock-vs-modded ratio could be a speed contrast.  This file restricts EVERY arm to the
SAME speed band before averaging, and prints the per-band window census beside every number.

Estimator is unchanged and imported read-only: `decode_v90_probe._wins` / `._band_transfer`,
NW_Z = 512 (5.12 s), HOP_Z = 256, mask = latActive & ~steeringPressed & v > 0.5 m/s.
Both channels are fields of the SAME 0x18F frame, so staleness cancels exactly in S_Tw / S_ww.
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
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L          # noqa: E402
import decode_v90_probe as P     # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

L.ROUTES["97"] = L._mk("97", "V9b-STOCK", gain=891, clamp=512, leverB=False, idcode=0, bits="stock")
L.ROUTES["96"] = L._mk("96", "V102", gain=5346, clamp=3072, leverB=False, idcode=3, bits="v102")
ARMS = [("97", "V9b STOCK 1x"), ("85", "V100 4x"), ("95", "V101 8x"), ("96", "V102 6x")]
ARMS = [(r, l) for r, l in ARMS if L._segs(r)]

DEG2RAD = np.pi / 180.0
RNG = np.random.default_rng(97_2026)
BANDS = [("2-4", 2.0, 4.0), ("4-6", 4.0, 6.0), ("6-9", 6.0, 9.0), ("9-12", 9.0, 12.0),
         ("12-16", 12.0, 16.0), ("16-18", 16.0, 18.0), ("18-22", 18.0, 22.0),
         ("22-26", 22.0, 26.0), ("26-31", 26.0, 31.0), ("31-35", 31.0, 35.0)]
VBANDS = [(2.0, 8.0), (8.0, 16.0), (16.0, 24.0), (24.0, 32.0)]     # m/s
OUT = {}


def load(route):
    R = L.ROUTES[route]
    z = np.load(R["cache"] / ("r" + route + ".npz"), allow_pickle=True)
    t = np.asarray(z["t"], float)
    return dict(t=t, tq=np.asarray(z["tq"], float),
                rate=np.asarray(z["rate_f"], float) * DEG2RAD,
                lat=np.asarray(z["cc_lat"], float) > 0.5,
                press=np.asarray(z["cs_press"], float) > 0.5,
                v=np.abs(np.asarray(z["cs_v"], float)),
                rc=np.abs(np.asarray(z["rate_c"], float)),
                fs=1.0 / float(np.median(np.diff(t))))


def rez_of(W, fs, bn, lo, hi, nboot=200):
    pairs = [(w[0], w[1]) for w in W]
    r = P._band_transfer(pairs, fs, P.NW_Z, [(bn, lo, hi)])[bn]
    idx = RNG.permutation(len(pairs))
    rs = P._band_transfer([(pairs[i][0], pairs[(idx[i] + 1) % len(pairs)][1])
                           for i in range(len(pairs))], fs, P.NW_Z, [(bn, lo, hi)])[bn]
    bs = [P._band_transfer([pairs[k] for k in RNG.integers(0, len(pairs), len(pairs))],
                           fs, P.NW_Z, [(bn, lo, hi)])[bn]["re_over_sxx"] for _ in range(nboot)]
    blo, bhi = np.percentile(bs, [2.5, 97.5])
    return dict(re_z=float(r["re_over_sxx"]), phase=float(r["phase_deg"]),
                coh2=float(r["coh2"]), shuf=float(rs["coh2"]),
                lo=float(blo), hi=float(bhi), n=len(pairs),
                trust=bool(np.isfinite(r["coh2"]) and r["coh2"] >= 0.10
                           and r["coh2"] >= 5.0 * max(rs["coh2"], 1e-9)))


def main():
    D = {rt: load(rt) for rt, _ in ARMS}
    Wall = {}
    for rt, lab in ARMS:
        d = D[rt]
        mask = d["lat"] & (~d["press"]) & (d["v"] > 0.5)
        Wall[rt] = P._wins(mask, d["t"], P.NW_Z, P.HOP_Z,
                           (d["rate"], d["tq"], d["v"], d["rc"]))
    for vlo, vhi in VBANDS:
        arms = []
        for rt, lab in ARMS:
            sel = [w for w in Wall[rt] if vlo <= float(np.median(w[2])) < vhi]
            if len(sel) >= 8:
                arms.append((rt, lab, sel))
        if not arms:
            continue
        print("\n" + "=" * 108)
        print("SPEED %.0f-%.0f m/s  (%.0f-%.0f km/h)   arms: %s"
              % (vlo, vhi, vlo * 3.6, vhi * 3.6,
                 "  ".join("%s n=%d" % (lab.split()[0] + lab.split()[1], len(s))
                           for _, lab, s in arms)))
        print("=" * 108)
        print("  %-8s" % "band" + "".join("%30s" % lab for _, lab, _ in arms))
        for bn, lo, hi in BANDS:
            row = "  %-8s" % bn
            for rt, lab, sel in arms:
                r = rez_of(sel, D[rt]["fs"], bn, lo, hi)
                row += "%11.0f [%6.0f,%6.0f]%s" % (r["re_z"], r["lo"], r["hi"],
                                                   " " if r["trust"] else "?")
                OUT.setdefault("%.0f-%.0f" % (vlo, vhi), {}).setdefault(rt, {})[bn] = r
            print(row)
        print("  ('?' = coherence gate failed: coh2 < 0.10 or < 5x the shuffled control)")
        base = [a for a in arms if a[0] == "97"]
        if base and len(arms) > 1:
            print("\n  ratio to STOCK (>1 = MORE anti-damping than stock; sign shown separately):")
            for rt, lab, sel in arms:
                if rt == "97":
                    continue
                row = "    %-13s" % lab
                for bn, lo, hi in BANDS:
                    a = OUT["%.0f-%.0f" % (vlo, vhi)]["97"][bn]["re_z"]
                    b = OUT["%.0f-%.0f" % (vlo, vhi)][rt][bn]["re_z"]
                    row += "  %s%.2f" % (bn + ":", b / a if a else np.nan)
                print(row)


if __name__ == "__main__":
    main()
    Path(__file__).with_name("_scratch/out/_stock_r97_rez_matched.json").write_text(
        json.dumps(OUT, indent=1, default=float))
    print("\n  wrote _scratch/out/_stock_r97_rez_matched.json")
