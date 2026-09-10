#!/usr/bin/env python3
r"""Extract the FIRST TWO V289 rev 1 routes (2026-09-09) into the corpus caches, exactly as
`extract_r5e_v288.py` does (same extractor `extract_r7d.extract_route`, same taps, same bookmark scan),
route-parametrised:

    r62_v289  75604b0a432fdc89_00000062--1c7daa54e8  (17 segs 00-16)  -> analysis-2020accord/_scratch/cache/r62_v289
    r63_v289  75604b0a432fdc89_00000063--1d4b188022  (12 segs 00-11)  -> analysis-2020accord/_scratch/cache/r63_v289

ROUTE-NUMBER COLLISION: the dongle counter reset; `_scratch/cache/r62/` `r63/` (if they exist) would be
older routes.  These routes are keyed `62b`/`63b` in D.ROUTES and cached under `r62_v289`/`r63_v289`.

DECODER NOTE (V289 rev 1): 0x14A byte 4 bit 5 = sign(S - y) (the notched-out component of the clamped
loop output; duty ~0.50 engaged = cave ALIVE), bit 7 = |S - y| >= |y| (reads 1 while DISENGAGED),
bits 4/6 = V282's r24 comparators, bit 3 as V282, bits 0-2 stock Honda.  The 0x1AB tap is V282's
(gp-0x6B38, sar-3 packer): counts = 8 * (field & 511), bit 9 = sign.  The build label stored in the
cache is the OPERATOR'S label; attribute the build from the tap (v289_qlive_r62_r63.py).

Usage:
    python rlog-tools/decode/extract_v289_routes.py r62_v289            # extract + bookmarks
    python rlog-tools/decode/extract_v289_routes.py r63_v289 bookmarks  # bookmarks only (fast)
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
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
        if _os.path.isfile(_os.path.join(_d, ".pkgroot")) and _d not in _roots:
            _roots.append(_d)
for _root in _roots:
    for _p in [_root] + [_os.path.join(_root, _e) for _e in sorted(_os.listdir(_root))
                         if _os.path.isdir(_os.path.join(_root, _e)) and not _e.startswith((".", "_"))]:
        if _p not in _sys.path:
            _sys.path.insert(0, _p)
# --- END BOOTSTRAP ---
import json, sys
from pathlib import Path

import decode_v84_probe_r6d as D      # noqa: E402
import extract_r7d as T               # noqa: E402
from rlog_parse import read_messages  # noqa: E402

ROUTES = {
    "r62_v289": ("62b", "75604b0a432fdc89_00000062--1c7daa54e8", 17),
    "r63_v289": ("63b", "75604b0a432fdc89_00000063--1d4b188022", 12),
}
RLOGS = Path(_repo) / "analysis-2020accord" / "rlogs"


def register(stem):
    key, rid, nseg = ROUTES[stem]
    cdir = f"analysis-2020accord/_scratch/cache/{stem}"
    D.ROUTES[key] = (rid, nseg, cdir, stem + "s", stem, "V289r1")
    T.WIRE_SCALE[key] = 8.0
    T.WIRE_SOURCE[key] = ("gp-0x6B38 (delivered LKAS-lane torque, the V282/V288/V289 427 tap), sar 3; "
                          "counts = 8 * (MOTOR_TORQUE & 511), bit 9 = sign.")
    return key, rid, cdir


def bookmarks(stem):
    key, rid, cdir = register(stem)
    out = []
    files = sorted(RLOGS.glob(f"{rid}--*--rlog.zst"), key=lambda p: int(p.name.split("--")[2]))
    t0 = None
    for p in files:
        seg = int(p.name.split("--")[2])
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if t0 is None:
                t0 = tm
            if w in ("userBookmark", "bookmarkButton"):
                out.append({"mono": tm, "t": tm - t0, "seg": seg, "which": w})
        print(f"  seg {seg}: {sum(1 for o in out if o['seg']==seg)} bookmark events", flush=True)
    dst = Path(_repo) / cdir
    dst.mkdir(parents=True, exist_ok=True)
    (dst / f"{stem}_bookmarks.json").write_text(json.dumps({"route": rid, "t0_mono_first_msg": t0,
                                                            "events": out}, indent=1))
    print(f"{len(out)} bookmark events -> {dst / (stem + '_bookmarks.json')}")
    for o in out:
        print(f"  {o['which']:14s} seg {o['seg']:2d}  t={o['t']:9.3f}")
    return out


if __name__ == "__main__":
    stem = sys.argv[1]
    key, rid, cdir = register(stem)
    if sys.argv[2:] == ["bookmarks"]:
        bookmarks(stem)
    else:
        T.extract_route(key)
        bookmarks(stem)
