#!/usr/bin/env python3
r"""Extract the FIRST V288 route -- `75604b0a432fdc89_0000005e--03a9714d78` (15 segs, pulled
2026-09-08) -- into `analysis-2020accord/_scratch/cache/r5e_v288/` with the corpus's own extractor
and taps, exactly as `extract_r39_r3a_r3c.py` does, plus the operator's BOOKMARKS.

ROUTE-NUMBER COLLISION: the dongle counter has reset; `_scratch/cache/r5e/` is a 2026-08-06 V65-era
route.  This route is keyed `5e2` and cached under `r5e_v288`.  Never match on the counter alone.

BOOKMARKS: the fork's `feedbackd` publishes a `userBookmark` event for every wheel-button /
UI bookmark; the corpus extractor only keeps `onroadEvents`.  This file scans the raw rlogs a
second time for `userBookmark` and `bookmarkButton` and writes `r5e_v288_bookmarks.json`
(mono time, route-relative t, and segment).  The operator's instruction for this route: each
bookmark was pressed IMMEDIATELY AFTER a grinding episode was felt.

DECODER NOTE (V288): 0x14A byte 4 bit 5 = sign(filtered setpoint y), NOT V282's r24 comparator.
Bits 3/4/7 = the three-sign rung, bit 6 = |r24| >= |T|, bits 0-2 stock.  The 0x1AB tap is V282's
(gp-0x6B38, sar-3 packer): counts = 8 * (field & 511), bit 9 = sign.

Usage:
    python rlog-tools/decode/extract_r5e_v288.py            # extract + bookmarks
    python rlog-tools/decode/extract_r5e_v288.py bookmarks  # bookmarks only (fast)
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
import numpy as np

import decode_v84_probe_r6d as D      # noqa: E402
import extract_r7d as T               # noqa: E402
from rlog_parse import read_messages  # noqa: E402

KEY = "5e2"
RID = "75604b0a432fdc89_0000005e--03a9714d78"
CDIR = "analysis-2020accord/_scratch/cache/r5e_v288"
STEM = "r5e_v288"
D.ROUTES[KEY] = (RID, 15, CDIR, STEM + "s", STEM, "V288r2")
T.WIRE_SCALE[KEY] = 8.0
T.WIRE_SOURCE[KEY] = ("gp-0x6B38 (delivered LKAS-lane torque, the V282/V288 427 tap), sar 3; "
                      "counts = 8 * (MOTOR_TORQUE & 511), bit 9 = sign.")

RLOGS = Path(_repo) / "analysis-2020accord" / "rlogs"


def bookmarks():
    out = []
    files = sorted(RLOGS.glob(f"{RID}--*--rlog.zst"), key=lambda p: int(p.name.split("--")[2]))
    t0 = None
    for p in files:
        seg = int(p.name.split("--")[2])
        first = None
        for evt in read_messages(p):
            try:
                w = evt.which()
            except Exception:
                continue
            tm = evt.logMonoTime * 1e-9
            if first is None:
                first = tm
            if t0 is None:
                t0 = tm
            if w in ("userBookmark", "bookmarkButton"):
                out.append({"mono": tm, "t": tm - t0, "seg": seg, "which": w})
        print(f"  seg {seg}: {sum(1 for o in out if o['seg']==seg)} bookmark events", flush=True)
    dst = Path(_repo) / CDIR
    dst.mkdir(parents=True, exist_ok=True)
    (dst / f"{STEM}_bookmarks.json").write_text(json.dumps({"route": RID, "t0_mono_first_msg": t0,
                                                            "events": out}, indent=1))
    print(f"{len(out)} bookmark events -> {dst / (STEM + '_bookmarks.json')}")
    for o in out:
        print(f"  {o['which']:14s} seg {o['seg']:2d}  t={o['t']:9.3f}")
    return out


if __name__ == "__main__":
    if sys.argv[1:] == ["bookmarks"]:
        bookmarks()
    else:
        T.extract_route(KEY)
        bookmarks()
