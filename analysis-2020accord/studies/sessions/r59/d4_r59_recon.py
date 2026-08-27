#!/usr/bin/env python3
"""D4 recon: what regimes does route 59 (V72) actually contain, in SECONDS?

No verdicts here -- this establishes the EXPOSURE that every P(0) later depends on. Frames are
counted on each segment's own lattice (fs from `_r4f_lib.fs_lattice`, never 1/median(dt)).
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

HERE = Path(__file__).resolve().parents[3]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _r31_common as C  # noqa: E402
import _r4f_lib as R4F  # noqa: E402

CACHE = ROOT / "_scratch/cache/r59"
PFX = "r59s"
SEGS = list(range(15))
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

print(f"{'seg':>4s} {'fs':>8s} {'n':>7s} {'secs':>7s} {'v max':>6s} {'lat%':>6s} {'gear':>28s} "
      f"{'|ang|max':>8s} {'|tq|p99':>8s} {'b4damp%':>8s} {'b3rate%':>8s} {'b6a512%':>8s}")
tot = 0.0
for s in SEGS:
    p = CACHE / f"{PFX}{s}.npz"
    if not p.exists():
        continue
    d = C.load(s, CACHE, PFX)
    fs = R4F.fs_lattice(d)
    n = len(d["t"])
    secs = n / fs
    tot += secs
    g = {GEAR[int(k)]: int((d["cs_gear"] == k).sum()) for k in np.unique(d["cs_gear"])}
    print(f"{s:>4d} {fs:>8.3f} {n:>7d} {secs:>7.1f} {np.abs(d['cs_v']).max():>6.2f} "
          f"{100 * (d['cc_lat'] > 0.5).mean():>6.1f} {str(g):>28s} "
          f"{np.abs(d['ang']).max():>8.1f} {np.percentile(np.abs(d['tq']), 99):>8.0f} "
          f"{100 * d['b4_damp'].mean():>8.4f} {100 * d['b3_rate'].mean():>8.3f} "
          f"{100 * d['b6_a512'].mean():>8.3f}")
print(f"  route total {tot:.1f} s")

# --------------------------------------------------------------- regime census, seconds ----------
print("\nREGIME CENSUS (seconds).  eff = |lowpass(tq,3Hz)| on the whole segment.")
acc = {}
for s in SEGS:
    p = CACHE / f"{PFX}{s}.npz"
    if not p.exists():
        continue
    d = C.load(s, CACHE, PFX)
    fs = R4F.fs_lattice(d)
    dt = 1.0 / fs
    v = np.abs(np.asarray(d["cs_v"], float))
    ang = np.abs(np.asarray(d["ang"], float))
    eff = np.abs(C.sustained(np.asarray(d["tq"], float), fs))
    eng = np.asarray(d["cc_lat"], float) > 0.5
    park = np.asarray(d["cs_gear"], float) == 1.0
    rate = np.abs(np.asarray(d["rate_c"], float))
    creep = (v >= 0.3) & (v < 4.0)
    cells = {
        "total": np.ones(len(v), bool),
        "driving (not park)": ~park,
        "creep 0.3-4 m/s": creep,
        "  eng creep": creep & eng,
        "  man creep": creep & ~eng,
        "corner-lite creep&|ang|>=100": creep & (ang >= 100),
        "  eng": creep & (ang >= 100) & eng,
        "  man": creep & (ang >= 100) & ~eng,
        "HARD corner creep |ang|>=150 & eff>=1600": creep & (ang >= 150) & (eff >= 1600),
        "  eng": creep & (ang >= 150) & (eff >= 1600) & eng,
        "  man": creep & (ang >= 150) & (eff >= 1600) & ~eng,
        "rate>=1400cts (297 deg/s)": rate * 4.7121 >= 1400,
        "  creep & rate>=1400": creep & (rate * 4.7121 >= 1400),
        "hands-off eff<=300": eff <= 300,
        "  eng hands-off creep": creep & (eff <= 300) & eng,
        "  man hands-off creep": creep & (eff <= 300) & ~eng,
        "highway >=14 m/s": v >= 14,
        "  eng hwy": (v >= 14) & eng,
        "  man hwy": (v >= 14) & ~eng,
    }
    for k, m in cells.items():
        acc[k] = acc.get(k, 0.0) + m.sum() * dt
for k, sec in acc.items():
    print(f"   {k:44s} {sec:9.1f} s")
