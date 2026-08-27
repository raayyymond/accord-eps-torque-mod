#!/usr/bin/env python3
"""D4 -- the manual-feel change, RATE-MATCHED.

§2 of studies/sessions/r59/d4_r59_channels_feel.py found route 59's manual creep carries the corpus's highest median bar
torque (1,968 counts) AND its highest median column rate (101 deg/s). A raw |tq|-on-|rate| slope
therefore cannot separate "the firmware got heavier" from "he steered faster that day". This file
bins on |rate| and compares the median |tq| WITHIN each bin, which holds the driver's own input
fixed. A velocity-opposing damper (V72's Lever B/C) must show up as extra torque that GROWS with
the rate bin; a route-wide effort offset must not.

Writes `_scratch/out/_d4_r59_feelmatch.json`.
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
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

CREEP_R = 4.0
RBINS = [(0, 20), (20, 50), (50, 100), (100, 200), (200, 400), (400, 1e9)]
RNAMES = ["0-20", "20-50", "50-100", "100-200", "200-400", "400+"]
ROUTES = {
    "V59 r2c":  ("_scratch/cache/r2c", "r2cs", [0, 1, 3, 4, 8, 9, 10, 11, 12], []),
    "V62 r37":  ("_scratch/cache/r37", "r37s", list(range(15)), []),
    "V67 r47":  ("_scratch/cache/r47", "r47s", list(range(26)), []),
    "V69 r4f":  ("_scratch/cache/r4f", "r4fs", list(range(8)), []),
    "V70 r50":  ("_scratch/cache/r50", "r50s", [0, 1, 2], [0]),
    "V71B r54": ("_scratch/cache/r54", "r54s", list(range(21)), [10, 11]),
    "V71C r58": ("_scratch/cache/r58", "r58s", list(range(16)), [12, 13, 14, 15]),
    "V72 r59":  ("_scratch/cache/r59", "r59s", list(range(15)), [12, 13, 14]),
}
OUT = {}


def hdr(s):
    print("\n" + "=" * 124 + f"\n{s}\n" + "=" * 124)


def gather(cache, pfx, segs, skip, engaged):
    TQ, RT, ANG, SEG = [], [], [], []
    for s in segs:
        if s in skip:
            continue
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C.load(s, ROOT / cache, pfx)
        v = np.abs(np.asarray(d["cs_v"], float))
        lat = np.asarray(d["cc_lat"], float) > 0.5
        m = (v >= 0.3) & (v < CREEP_R) & (lat if engaged else ~lat)
        if not m.any():
            continue
        TQ.append(np.abs(np.asarray(d["tq"], float))[m])
        RT.append(np.abs(np.asarray(d["rate_c"], float))[m])
        ANG.append(np.abs(np.asarray(d["ang"], float))[m])
        SEG.append(np.full(int(m.sum()), s, float))
    if not TQ:
        return None
    return (np.concatenate(TQ), np.concatenate(RT), np.concatenate(ANG), np.concatenate(SEG))


def boot_med(v, seg, nb=2000, rng=None):
    """Median with a SEGMENT bootstrap -- frames inside one segment are not independent."""
    rng = rng or np.random.default_rng(20260805)
    u = np.unique(seg)
    if len(u) < 2:
        return float(np.median(v)), np.nan, np.nan
    per = [v[seg == s] for s in u]
    dr = np.empty(nb)
    for i in range(nb):
        dr[i] = np.median(np.concatenate([per[k] for k in rng.integers(0, len(per), len(per))]))
    return (float(np.median(v)), float(np.percentile(dr, 2.5)), float(np.percentile(dr, 97.5)))


for arm, engaged in (("MANUAL", False), ("ENGAGED", True)):
    hdr(f"{arm} CREEP (0.3-4 m/s): median |bar torque| WITHIN each |column rate| bin (deg/s).\n"
        f"    Segment bootstrap. A velocity-opposing damper must GROW across the bins.")
    print(f"   {'route':10s} {'n':>7s} | " + " ".join(f"{n:>16s}" for n in RNAMES))
    tab = {}
    for tag, (cache, pfx, segs, skip) in ROUTES.items():
        g = gather(cache, pfx, segs, skip, engaged)
        if g is None:
            continue
        tq, rt, ang, seg = g
        cells = []
        for lo, hi in RBINS:
            m = (rt >= lo) & (rt < hi)
            if m.sum() < 60:
                cells.append((np.nan, np.nan, np.nan, int(m.sum())))
                continue
            a, b, c = boot_med(tq[m], seg[m])
            cells.append((a, b, c, int(m.sum())))
        tab[tag] = [list(x) for x in cells]
        print(f"   {tag:10s} {len(tq):>7d} | " +
              " ".join(f"{c[0]:>7.0f}[{c[3]:>6d}]" if np.isfinite(c[0]) else f"{'--':>16s}"
                       for c in cells))
    OUT[arm] = tab
    if arm == "MANUAL":
        print(f"\n   RATIO V72 / reference, per rate bin (median |tq|):")
        print(f"   {'reference':10s} | " + " ".join(f"{n:>10s}" for n in RNAMES))
        for ref in ("V71C r58", "V71B r54", "V62 r37", "V59 r2c", "V69 r4f", "V67 r47"):
            if ref not in tab:
                continue
            print(f"   {ref:10s} | " + " ".join(
                f"{tab['V72 r59'][i][0] / tab[ref][i][0]:>10.3f}"
                if (np.isfinite(tab["V72 r59"][i][0]) and np.isfinite(tab[ref][i][0])
                    and tab[ref][i][0] > 0) else f"{'--':>10s}" for i in range(len(RBINS))))

(ROOT / "_scratch/out/_d4_r59_feelmatch.json").write_text(json.dumps(OUT, indent=1, default=float))
print(f"\nwrote {ROOT / '_scratch/out/_d4_r59_feelmatch.json'}")
