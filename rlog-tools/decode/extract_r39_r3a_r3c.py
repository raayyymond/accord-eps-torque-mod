#!/usr/bin/env python3
r"""Extract the V282 routes 39 / 3a / 3c into `analysis-2020accord/_scratch/cache/r{39,3a,3c}/`
using the corpus's OWN extractor and the corpus's OWN 0x1AB + byte-7 taps, unchanged.

THIS FILE CLOSES A DEFECT: `analysis-2020accord/_scratch/cache/r39/` (r39.npz, 91 fields, plus
`r39_events.json`, `r39_segments.json`, `r39_1ab.json`, `r39_census_seg.json`) has been on disk
since 2026-09-04 with **no producer in the repo** -- subagent "dec39" built it from an ad-hoc
driver that was never committed, so the cache was unreproducible.  This is that driver, rebuilt
from the same two modules dec39 must have used, and extended to routes 3a and 3c.

THE INSTRUMENT IS NOT REIMPLEMENTED.  Exactly as `decode/extract_r6e.py` .. `decode/extract_r7d.py`
do, this file adds rows to `decode_v84_probe_r6d.ROUTES` and calls that module's `extract()` /
`split()`, and it imports `decode/extract_r7d.py` to get the 0x1AB full-payload tap, the 0x14A
byte-7 tap and the `row2raw14` index map -- the same code that wrote every `ab_*` / `raw14_b7` /
`row2raw14` column in the corpus.  Field names, ZOH/interp convention, IMU axis pick, sentinel
definition and `PASS_1D` are therefore bit-for-bit the ones every prior route was scored with.
A copy would drift; a rebind cannot.

===================================================================================================
THE 427 DESCRIPTOR IS CORRECTED HERE.  DO NOT RE-DERIVE THE OLD ONE.
===================================================================================================
The existing `r39_1ab.json` says `wire_source = "gp-0x6B38 sar0 (V282 tap, decoded from image)"`
and `wire_scale_counts_per_lsb = 0.2`.  **That is WRONG** -- STATE.md defect #4, adjudicated by
the operator 2026-09-04, and independently confirmed on the wire:

  * `0x1AB` byte 0 takes only {128, 130} on r39 and r3a (and {128, 130, 136} on r3c, the 136 being
    a 45-frame power-up transient at vEgo 0).  So bit 9 of the 10-bit MOTOR_TORQUE field is a
    SIGN bit and the magnitude is the low 9 bits.
  * Magnitude maxes at 207 (r39) / 209 (r3a) / 213 (r3c) against a 1023 ceiling.  A sar-0 /
    0.2-per-LSB decode would cap |T| near 207 * 0.2 = 41 counts; the chain and every prior route
    put |T| at 400-2500 counts.  The kit's **sar-3 (x8)** decode is the one that matches:
        |T| counts = 8 * (field & 511),   sign = (field >> 9) & 1
    giving |T| max 1656 / 1672 / 1704 counts on r39 / r3a / r3c.

`WIRE_SCALE` below is therefore **8.0**, not 0.2, and `WIRE_SOURCE` names the sar-3 packer.
Re-running this file on route 39 REWRITES `r39_1ab.json` with the corrected descriptor.

===================================================================================================
ROUTE-NUMBER COLLISION, and route 3a's MISSING SEGMENT
===================================================================================================
The dongle's route counter RESET.  `analysis-2020accord/rlogs/` holds an OLD 2026-08-01 V65-era
`0000003a--4e55c1e0f4` (7 seg) as well as the NEW 2026-09-04 V282 `0000003a--283a39a1d6` (13 seg).
Every row below carries the FULL route id.  Never match on the counter alone.

Route 3a is **missing segment 10** on disk (indices 0..9, 11, 12, 13).  `decode_v84_probe_r6d.extract`
was changed 2026-09-04 to enumerate the segment files that EXIST rather than `range(nseg)`, and to
carry the REAL segment number into the `seg` column -- so `split()` writes `r3as11.npz` from
segment 11, not from the 11th file.  The hole is a genuine ~60 s gap in the concatenated `t` axis:
it shows in `seg_bounds` as a jump between segment 9's end and segment 11's start.  Time-indexed
code is fine; anything that assumes a uniform grid will bridge it invisibly.

Usage:
    python rlog-tools/decode/extract_r39_r3a_r3c.py 3a 3c        # the two new routes
    python rlog-tools/decode/extract_r39_r3a_r3c.py 39           # rebuild/verify route 39
    python rlog-tools/decode/extract_r39_r3a_r3c.py              # all three
    R39_R3X_CACHE_SUFFIX=_verify python ... 39                   # write to r39_verify/ instead
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  Put EVERY kit root, and every code subfolder under each, on
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
# --- END PATH BOOTSTRAP ---------------------------------------------------

import os
import sys

import decode_v84_probe_r6d as D      # noqa: E402  the extractor that wrote every cache since r6d
import extract_r7d as T               # noqa: E402  the 0x1AB / byte-7 taps + row2raw14, unchanged

# Optional suffix so a VERIFICATION run can write beside the real cache instead of over it.
SUF = os.environ.get("R39_R3X_CACHE_SUFFIX", "")

# route key -> (full route id, nominal n segs, cache dir, per-seg prefix, npz stem, label)
ROUTE_DEF = {
    "39": ("75604b0a432fdc89_00000039--f56039af87", 16,
           f"analysis-2020accord/_scratch/cache/r39{SUF}", "r39s", "r39", "V282"),
    # 🛑 13 files on disk, indices 0..9, 11, 12, 13 -- segment 10 is ABSENT.  nseg is the NOMINAL
    #    count so the extractor can report what is missing.
    "3a": ("75604b0a432fdc89_0000003a--283a39a1d6", 14,
           f"analysis-2020accord/_scratch/cache/r3a{SUF}", "r3as", "r3a", "V282"),
    "3c": ("75604b0a432fdc89_0000003c--927965c2b4", 13,
           f"analysis-2020accord/_scratch/cache/r3c{SUF}", "r3cs", "r3c", "V282"),
}
for _k, _v in ROUTE_DEF.items():
    D.ROUTES[_k] = _v

# ---- 427 (0x1AB) descriptor.  CORRECTED -- see the module docstring.  V282's tap is gp-0x6B38,
#      the delivered LKAS-lane torque, packed by the sar-3 packer: counts = 8 * (field & 511).
_SRC = ("gp-0x6B38 (delivered LKAS-lane torque, the V282 427 tap), sar 3; "
        "counts = 8 * (MOTOR_TORQUE & 511), bit 9 = sign. "
        "SUPERSEDES the 'sar0 / 0.2 counts per LSB' descriptor in the pre-2026-09-04 r39_1ab.json, "
        "which was WRONG (STATE.md defect #4).")
for _k in ROUTE_DEF:
    T.WIRE_SCALE[_k] = 8.0
    T.WIRE_SOURCE[_k] = _SRC


def main(routes):
    for r in routes:
        if r not in ROUTE_DEF:
            raise SystemExit(f"unknown route {r!r}; known: {sorted(ROUTE_DEF)}")
        print("=" * 100, flush=True)
        print(f"ROUTE {r}  {ROUTE_DEF[r][0]}  ->  {ROUTE_DEF[r][2]}", flush=True)
        print("=" * 100, flush=True)
        T.extract_route(r)


if __name__ == "__main__":
    main(sys.argv[1:] or ["39", "3a", "3c"])
