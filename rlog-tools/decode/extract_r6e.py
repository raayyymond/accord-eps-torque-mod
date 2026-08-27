#!/usr/bin/env python3
"""Extract route `6e` (V85) into `_scratch/cache/r6e/`, using the corpus's OWN extractor unchanged.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  This file adds one row to `decode_v84_probe_r6d.ROUTES`
and calls that module's `extract()` / `split()` -- the SAME code that actually wrote `_scratch/cache/r6d/`
(and `_scratch/cache/r68x/`, `_scratch/cache/r67x/`).  So the field names, the ZOH/interp convention, the IMU
vertical+lateral axis pick, the sentinel definition and the `PASS_1D` list are bit-for-bit the ones
route `6d` (V84) was scored with, and every `_r*_lib` / `_grind2_lib` harness loads `_scratch/cache/r6e/`
unchanged.  A copy would drift; a rebind cannot.

⚠ `decode/extract_r6d_r68.py` drives `compare_v75_v76_v80_grind.extract66` instead, which writes a
STRICTLY SMALLER schema (no `cs_rate` / `cs_yaw` / `cs_brake` / `cc_curv` / `ct_*` / `imu_lat` /
`sentinels`).  `_scratch/cache/r6d/` on disk is the RICHER one, so this file follows `_scratch/cache/r6d/`.

After extraction the V85 probe decode is stamped into the same columns V84's routes carry, under
`v85_*` names.  V84's own `v84_*` / `thermo_*` columns are still written by the shared extractor and
are RETAINED DELIBERATELY: the identity battery needs the V84 reading of a V85 log side by side
with the V85 one.  🛑 They are NOT meaningful as V85 measurements -- read `v85_*`.

Usage:
    python decode/extract_r6e.py
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

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote _scratch/cache/r6d/
import rlog_parse                 # noqa: E402

from build_v85_tva import (BIT_FINGERPRINT, BIT_FRIC_HI, BIT_FRIC_LO,  # noqa: E402
                           BIT_RATE_HI, BIT_RATE_LO)

# route key -> (route stem, n segs, cache dir, per-seg prefix, npz stem, label)
D.ROUTES["6e"] = ("75604b0a432fdc89_0000006e--649c462a6e", 8, "_scratch/cache/r6e", "r6es", "r6e", "V85")

# the V85 cave's five bits, stamped alongside the shared extractor's v84_*/thermo_* columns
V85_COLS = (("v85_rate_lo", BIT_RATE_LO),    # b7  |gp-0x6abc| >= 64   (> OLD saturation 50)
            ("v85_rate_hi", BIT_RATE_HI),    # b6  |gp-0x6abc| >= 512  (> NEW saturation 500)
            ("v85_fric_hi", BIT_FRIC_HI),    # b5  |gp-0x6ae2| >= 8
            ("v85_fric_lo", BIT_FRIC_LO),    # b4  |gp-0x6ae2| >= 2
            ("v85_fingerprint", BIT_FINGERPRINT))   # b3  constant 1
D.PASS_1D = list(D.PASS_1D) + [c for c, _ in V85_COLS]

# =====================================================================================================
# 🛑 ONE DEVIATION FROM THE r6d RUN, AND IT IS DECLARED.
# Route `6e`'s FINAL segment (`--7--`, 3.3 MB) is TRUNCATED mid-capnp-message -- the drive ended
# while the segment was still being written.  Stock `read_messages` raises
# `KjException: Message ends prematurely` and loses the WHOLE route.  This wrapper yields every
# COMPLETE message and stops at the tear, printing what it lost.  capnp's `read_multiple_bytes` is
# strictly sequential, so everything yielded before the exception is a fully-formed message -- no
# partial record can enter the cache.  Route `6d`'s last segment parsed clean, so this path was
# never needed before.
# =====================================================================================================
_ORIG_READ = rlog_parse.read_messages
TRUNCATED = {}


def _read_messages_tolerant(path):
    n = 0
    try:
        for evt in _ORIG_READ(path):
            n += 1
            yield evt
    except Exception as exc:                       # capnp KjException on a torn tail
        TRUNCATED[Path(path).name] = (n, str(exc).splitlines()[0])
        print(f"  ⚠ TRUNCATED rlog {Path(path).name}: {n:,} complete messages read, then "
              f"{str(exc).splitlines()[0]}", flush=True)


rlog_parse.read_messages = _read_messages_tolerant


def stamp_v85():
    """Add the `v85_*` decode columns to the route-global npz, then re-split so segments carry them."""
    cache = ROOT / "_scratch/cache/r6e"
    z = dict(np.load(cache / "r6e.npz"))
    p = z["probe"].astype(int)
    for col, bit in V85_COLS:
        z[col] = ((p & bit) != 0).astype(float)
    np.savez_compressed(cache / "r6e.npz", **z)
    print(f"  stamped {[c for c, _ in V85_COLS]} onto r6e.npz")


if __name__ == "__main__":
    D.extract("6e")
    stamp_v85()
    D.split("6e")
    (ROOT / "_scratch/cache/r6e" / "r6e_truncation.json").write_text(json.dumps(
        {k: {"complete_messages": n, "error": why} for k, (n, why) in TRUNCATED.items()}, indent=1))
    if TRUNCATED:
        print("\n🛑 TRUNCATED SEGMENTS (declare these in any census):")
        for k, (n, why) in TRUNCATED.items():
            print(f"   {k}: {n:,} messages then {why}")
