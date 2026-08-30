#!/usr/bin/env python3
"""The two PARTIAL arms the corpus already holds, measured with the corpus instrument.

  * route `4c` (V68) -- 234.8 s DISENGAGED above 20 m/s, the cleanest "assist not acting" arm in
    the corpus, and the operator reported NO GRIND on it.  ⚠ It is NOT a stock baseline: it is
    modified firmware with LKAS off.
  * routes `2b` (V58) and `2c` (V59) -- byte-verified STOCK in the rate lane, the damper, Lever B
    and `0x454FE`.  Their only live assist-chain delta is the 4x forward gain + the V38-era
    clamps/walls.  If the ~7.79 Hz line is present here it PREDATES every lever from V61 onward.

🛑 Instrument is `ratchet_line_ladder_v87.load` -> `relay_fingerprint_r6e.windows/spectra`, imported
verbatim.  `blk` resampling, n_blocks stated for every CI.  Nothing numeric is redefined.
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
import re
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod")
# repo reorg 2026-08-26 moved rlog_parse into rlog-tools/lib/ -- the old single-dir insert
# stopped resolving it, which killed this whole extractor family silently (the caches were
# already on disk, so nothing surfaced it). Put the kit root AND every code subfolder on.
for _p in [ROOT / "rlog-tools"] + [d for d in (ROOT / "rlog-tools").iterdir() if d.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import ratchet_line_ladder_v87 as L  # noqa: E402
import relay_fingerprint_r6e as RF   # noqa: E402

MACRO = RF.MACRO
OUT = {}

# cache, prefix -- segments discovered from disk
ARMS = [("V68/4c", "_scratch/cache/v68", "4cs"),
        ("V68/4e", "_scratch/cache/v68", "4es"),
        ("V59/2c", "_scratch/cache/r2c", "r2cs"),
        ("V58/2b", "_scratch/cache/r2b", "r2bs"),
        ("V81/67", "_scratch/cache/r67x", "r67xs"),
        ("V85/6e", "_scratch/cache/r6e", "r6es")]


def segs_of(cache, pfx):
    out = []
    for p in (ROOT / cache).glob(f"{pfx}*.npz"):
        m = re.fullmatch(rf"{pfx}(\d+)\.npz", p.name)
        if m:
            out.append(int(m.group(1)))
    return sorted(out)


def row(label, recs):
    if len(recs) < 4:
        return dict(n=len(recs), blk=len({r["blk"] for r in recs}), note="too few windows")
    e = [r for r in recs if np.isfinite(r["f_free"])]
    u = [r["blk"] for r in e]
    fc = RF._boot_med([r["f_free"] for r in e], u)
    pr = RF._boot_med([r["p779"] for r in e], u)
    aa = RF._boot_med([r["a779"] for r in e], u)
    v = np.array([r["v"] for r in e], float)
    frac = float(np.mean([abs(r["f_free"] - MACRO) <= 0.6 for r in e]))
    print(f"{label:14s} {len(e):4d} {len(set(u)):4d} | {fc[0]:7.3f} [{fc[1]:6.3f},{fc[2]:6.3f}] | "
          f"{pr[0]:7.2f} [{pr[1]:6.2f},{pr[2]:6.2f}] | {aa[0]:7.1f} [{aa[1]:6.1f},{aa[2]:6.1f}] | "
          f"{100*frac:5.1f}% | {np.median(v):5.2f} [{np.percentile(v,10):5.2f},"
          f"{np.percentile(v,90):5.2f}]")
    return dict(n=len(e), blk=len(set(u)), f_c=list(fc), prom779=list(pr), a779=list(aa),
                frac_at_line=frac, v_med=float(np.median(v)),
                v_p10=float(np.percentile(v, 10)), v_p90=float(np.percentile(v, 90)))


def main():
    RF.hdr("THE PARTIAL ARMS -- the ~7.79 Hz line, corpus instrument, blk resampling\n"
           "  f_c = median free 5-12 Hz prominence argmax | prom = prominence at the FIXED 7.79 Hz\n"
           "  a779 = p99 envelope amplitude in 7.79+-1 Hz, counts | frac = windows within 0.6 Hz")
    print(f"\n{'arm':14s} {'n':>4s} {'blk':>4s} | {'centre f_c (Hz), 95% CI':>24s} | "
          f"{'prom at 7.79 Hz':>24s} | {'a779 (counts)':>24s} | {'@line':>6s} | "
          f"{'speed med [p10,p90]':>21s}")
    for label, cache, pfx in ARMS:
        segs = segs_of(cache, pfx)
        if not segs:
            print(f"{label:14s}  -- no segments on disk")
            continue
        for arm, eng in (("ENG", True), ("MAN", False)):
            recs = L.load(f"{label}/{arm}", cache, pfx, segs, eng)
            OUT[f"{label}/{arm}"] = row(f"{label} {arm}", recs)
            OUT[f"{label}/{arm}"]["segs"] = segs
        print()

    dst = ROOT / "_scratch/cache/r6f" / "stock_baseline_search.json"
    prev = json.loads(dst.read_text()) if dst.exists() else {}
    prev["partial_arms"] = OUT
    dst.write_text(json.dumps(prev, indent=1, default=float))
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
