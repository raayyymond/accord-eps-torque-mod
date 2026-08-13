#!/usr/bin/env python3
r"""Extract routes `7e` and `7f` -- the two drives the operator delivered on 2026-08-12 -- into
`analysis-2020accord/_cache_r7e/` and `_cache_r7f/`.

🛑 THE INSTRUMENT IS NOT REIMPLEMENTED.  This file imports `extract_r7d`, which itself only adds
rows to `decode_v84_probe_r6d.ROUTES` and calls that module's `extract()`/`split()` -- the SAME
code that wrote every cache since `_cache_r6d/`.  Field names, ZOH/interp convention, IMU axis
pick, sentinel definition and `PASS_1D` are therefore bit-for-bit the ones every prior route was
scored with.  The 0x1AB full tap and the 0x14A byte-7 tap come along unchanged, including the
elementwise byte-4 assertion that kills the run rather than silently mispairing.

BUILD ON THE CAR IS NOT ASSUMED.  `WIRE_SCALE` / `WIRE_SOURCE` below are the V96 spec; if the
identity battery says otherwise, the 427 *counts* rescale but nothing else in the cache does
(the wire column itself is raw).

Usage:
    python extract_r7e_r7f.py            # extract both, then identity + census
    python extract_r7e_r7f.py extract 7e
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

import extract_r7d as X  # noqa: E402  -- installs the taps; brings D + rlog_parse with it

D = X.D

NEW = {
    "7e": ("75604b0a432fdc89_0000007e--e5f2d1465f", 14, "analysis-2020accord/_cache_r7e",
           "r7es", "r7e", "V96?"),
    "7f": ("75604b0a432fdc89_0000007f--2bb30756e7", 14, "analysis-2020accord/_cache_r7f",
           "r7fs", "r7f", "V96?"),
}
for _k, _v in NEW.items():
    D.ROUTES[_k] = _v

# V96 spec: 427 (0x1AB) <- gp-0x6b70, `sar 6`, magnitude + explicit sign bit.  LSB 12.8 counts.
for _k in NEW:
    X.WIRE_SCALE[_k] = 64.0 / 5.0
    X.WIRE_SOURCE[_k] = "gp-0x6b70 (PID reference lane), sar 6  [V96 spec, UNCONFIRMED]"


def main(argv):
    if not argv:
        for r in ("7e", "7f"):
            X.extract_route(r)
        for r in ("7e", "7f"):
            X.census(r)
        return
    fn = {"extract": X.extract_route, "census": X.census, "health": X.health}[argv[0]]
    for r in (argv[1:] or ["7e", "7f"]):
        fn(r)


if __name__ == "__main__":
    main(sys.argv[1:])
