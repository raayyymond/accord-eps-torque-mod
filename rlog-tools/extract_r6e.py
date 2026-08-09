#!/usr/bin/env python3
"""Extract route `6e` (V85) into `_cache_r6e/`, using the corpus's OWN extractor unchanged.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  This file adds one row to `decode_v84_probe_r6d.ROUTES`
and calls that module's `extract()` / `split()` -- the SAME code that actually wrote `_cache_r6d/`
(and `_cache_r68x/`, `_cache_r67x/`).  So the field names, the ZOH/interp convention, the IMU
vertical+lateral axis pick, the sentinel definition and the `PASS_1D` list are bit-for-bit the ones
route `6d` (V84) was scored with, and every `_r*_lib` / `_grind2_lib` harness loads `_cache_r6e/`
unchanged.  A copy would drift; a rebind cannot.

⚠ `extract_r6d_r68.py` drives `compare_v75_v76_v80_grind.extract66` instead, which writes a
STRICTLY SMALLER schema (no `cs_rate` / `cs_yaw` / `cs_brake` / `cc_curv` / `ct_*` / `imu_lat` /
`sentinels`).  `_cache_r6d/` on disk is the RICHER one, so this file follows `_cache_r6d/`.

After extraction the V85 probe decode is stamped into the same columns V84's routes carry, under
`v85_*` names.  V84's own `v84_*` / `thermo_*` columns are still written by the shared extractor and
are RETAINED DELIBERATELY: the identity battery needs the V84 reading of a V85 log side by side
with the V85 one.  🛑 They are NOT meaningful as V85 measurements -- read `v85_*`.

Usage:
    python extract_r6e.py
"""
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import decode_v84_probe_r6d as D  # noqa: E402  -- THE extractor that wrote _cache_r6d/
import rlog_parse                 # noqa: E402

from build_v85_tva import (BIT_FINGERPRINT, BIT_FRIC_HI, BIT_FRIC_LO,  # noqa: E402
                           BIT_RATE_HI, BIT_RATE_LO)

# route key -> (route stem, n segs, cache dir, per-seg prefix, npz stem, label)
D.ROUTES["6e"] = ("75604b0a432fdc89_0000006e--649c462a6e", 8, "_cache_r6e", "r6es", "r6e", "V85")

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
    cache = ROOT / "_cache_r6e"
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
    (ROOT / "_cache_r6e" / "r6e_truncation.json").write_text(json.dumps(
        {k: {"complete_messages": n, "error": why} for k, (n, why) in TRUNCATED.items()}, indent=1))
    if TRUNCATED:
        print("\n🛑 TRUNCATED SEGMENTS (declare these in any census):")
        for k, (n, why) in TRUNCATED.items():
            print(f"   {k}: {n:,} messages then {why}")
