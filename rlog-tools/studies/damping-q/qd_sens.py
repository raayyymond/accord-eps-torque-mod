#!/usr/bin/env python3
"""SENSITIVITY: does the V86-vs-V86B linewidth-Q verdict survive the estimator choices?

Four knobs, swept independently at the only well-populated design point (T = 10.1 s):
  * search band          5-11 Hz  vs  6.5-9.5 Hz (tight around the recorded 7.79 Hz)
  * floor subtraction    on / off (off = `catA_linewidth.py`'s convention)
  * wheel-order veto     targeted 0.8 Hz guard / none
  * statistic            median / mean

Usage:  python studies/damping-q/qd_sens.py
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import qd_lib as Q                                                       # noqa: E402
import qd_win as W                                                       # noqa: E402

RNG = np.random.default_rng(515)
NW = 1024
rows = []
print(f"{'band':>12s} {'floor':>6s} {'order':>7s} {'stat':>7s} | "
      f"{'Q V86':>7s} {'Q V86B':>7s} {'Q V85':>7s} | {'NULL V86B/V85':>26s} | "
      f"{'EFF V86/V86B':>26s} | {'DiD':>26s}")
print("-" * 150)
for band, blab in [((5.0, 11.0), "5-11 Hz"), ((6.5, 9.5), "6.5-9.5 Hz")]:
    for fsub in (True, False):
        for oc in (True, False):
            for stat, slab in ((np.median, "median"), (np.mean, "mean")):
                arms = {}
                for b in W.ROUTES:
                    rs = W.windows(b, NW)
                    for r in rs:
                        r.update(Q.linewidth(r["x"], r["fs"], flo=band[0], fhi=band[1],
                                             floor_sub=fsub))
                    rs = [r for r in rs if np.isfinite(r.get("f0", np.nan))]
                    arms[b] = W.order_clean(rs) if oc else rs
                w, _ = W.shared_weights([arms[b] for b in ("V86", "V86B", "V85")])
                qs = {b: float(stat([r["q_app"] for r in arms[b]
                                     if np.isfinite(r["q_app"])])) for b in W.ROUTES}
                null = Q.boot_ratio(arms["V86B"], arms["V85"], "q_app", rng=RNG, stat=stat,
                                    weights=w, vbins=W.VBINS)
                eff = Q.boot_ratio(arms["V86"], arms["V86B"], "q_app", rng=RNG, stat=stat,
                                   weights=w, vbins=W.VBINS)
                dd = Q.did(arms["V86"], arms["V86B"], arms["V85"], "q_app", rng=RNG, stat=stat,
                           weights=w, vbins=W.VBINS)
                rows.append(dict(band=blab, floor_sub=fsub, order_clean=oc, stat=slab,
                                 q=qs, null=null, eff=eff, did=dd))
                print(f"{blab:>12s} {str(fsub):>6s} {str(oc):>7s} {slab:>7s} | "
                      f"{qs['V86']:7.1f} {qs['V86B']:7.1f} {qs['V85']:7.1f} | "
                      f"{null['ratio']:7.3f} [{null['lo']:6.3f},{null['hi']:7.3f}] | "
                      f"{eff['ratio']:7.3f} [{eff['lo']:6.3f},{eff['hi']:7.3f}] | "
                      f"{dd['did']:7.3f} [{dd['lo']:6.3f},{dd['hi']:7.3f}]")

effs = [r["eff"]["ratio"] for r in rows if np.isfinite(r["eff"]["ratio"])]
excl = sum(1 for r in rows if np.isfinite(r["eff"]["lo"]) and
           (r["eff"]["lo"] > 1.0 or r["eff"]["hi"] < 1.0))
print(f"\n  EFF V86/V86B across all {len(rows)} estimator variants: "
      f"min {min(effs):.3f}  median {np.median(effs):.3f}  max {max(effs):.3f}")
print(f"  variants whose EFFECT CI excludes 1.00: {excl} / {len(rows)}")
json.dump(rows, open(ROOT / "_scratch/cache/r6f" / "qd_sens.json", "w"), indent=1, default=float)
print("wrote _scratch/cache/r6f/qd_sens.json")
