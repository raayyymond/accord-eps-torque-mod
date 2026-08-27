#!/usr/bin/env python3
r"""Extract route `80` -- the V97 flight (parking-lot creep, LKAS engaged, operator aborted after
2 segments) -- into `analysis-2020accord/_scratch/cache/r80/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  This file imports `extract_r7d`, which only adds rows to
`decode_v84_probe_r6d.ROUTES` and calls that module's `extract()`/`split()` -- the SAME code that
wrote every cache since `_scratch/cache/r6d/`, and the same path `decode/extract_r7e_r7f.py` used for V96.  Field
names, ZOH/interp convention, IMU axis pick, sentinel definition and `PASS_1D` are bit-for-bit the
ones every prior route was scored with.  The 0x1AB full tap and the 0x14A byte-7 tap come along
unchanged, including the elementwise byte-4 assertion that kills the run rather than silently
mispairing, and the `row2raw14` index map that fixes the raw14 off-by-one.

V97 = V96 BASE + ONE CALIBRATION BYTE (`0xC63AC` 102 -> 150).  The cave, the 427 repoint and the
427 packer scale are V96's, UNCHANGED.  So `WIRE_SCALE`/`WIRE_SOURCE` are V96's spec verbatim.

🛑 IDENTITY CAVEAT, STATED UP FRONT: because V97's *instrument* is V96's instrument byte-for-byte,
NO single-frame test can separate V97 from V96.  The single-frame legs separate {V96, V97} from
V94 and from every build before it.  V96-vs-V97 is a DYNAMICS question (the pole) and is handled
by the phase measurement, not here.

Usage:
    python decode/extract_r80.py            # extract, then identity + census
    python decode/extract_r80.py extract 80
    python decode/extract_r80.py identity 80
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

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import extract_r7d as X  # noqa: E402  -- installs the taps; brings D + rlog_parse with it

D = X.D

NEW = {
    "80": ("75604b0a432fdc89_00000080--6c8b103892", 2, "analysis-2020accord/_scratch/cache/r80",
           "r80s", "r80", "V97?"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v
# V96/V97 spec: 427 (0x1AB) <- gp-0x6b70, `sar 6`, magnitude + explicit sign bit on 0x14A b4 b7.
for _k in NEW:
    X.WIRE_SCALE[_k] = 64.0 / 5.0
    X.WIRE_SOURCE[_k] = "gp-0x6b70 (PID reference lane), sar 6  [V96/V97 spec]"

# The V96/V97 cave's byte-4 map (builds/v80_v107/build_v96_tva.py, THE PAYLOAD).
X.BITNAMES["80"] = {"b7_sign_6b70": 0x80, "b6_sign_374c": 0x40,
                    "b5_Mhi_bit1": 0x20, "b4_Mhi_bit0": 0x10, "b3_mode_674e_lt28": 0x08}


def main(argv):
    if not argv:
        X.extract_route("80")
        X.identity("80")
        return
    fn = {"extract": X.extract_route, "census": X.census, "identity": X.identity,
          "health": X.health}[argv[0]]
    for r in (argv[1:] or ["80"]):
        fn(r)


if __name__ == "__main__":
    main(sys.argv[1:])
