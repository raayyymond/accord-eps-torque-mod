#!/usr/bin/env python3
"""v89_i1_can_order.py -- THE DEFINITIVE TEST for the 0x18F / 0x14A row-packing skew.

The dispute: does a cache ROW carry the 0x18F frame from its own instant, or the previous one?

`compare_v75_v76_v80_grind.py:extract66()` walks `for m in evt.can:` and holds `last18`, appending a
ROW when it reaches a 0x14A -- so **LIST ORDER INSIDE `evt.can` decides it**, and nothing else does.
`tm = evt.logMonoTime` is per-EVENT, so co-logged frames share a timestamp exactly.

    0x18F BEFORE 0x14A in evt.can  ->  last18 is already this instant's frame  ->  NO SKEW
    0x14A BEFORE 0x18F in evt.can  ->  the row carries the PREVIOUS 0x18F      ->  ~10 ms SKEW

Both prior discriminators were inadequate and both sides said so:
  * `sstat` is >99.87% constant and ties across 4 shifts -- pins nothing.
  * `raw18_b4 -> sca` has only 7-16 transitions of a 2-3 valued byte.
  * "payload age vs the most recent 0x18F" assumes the row carries the most recent frame, which
    is the question -- a control that cannot fail.
This test needs no statistics, no entropy and no assumption. It reads the order directly.

Also reported, because the orchestrator asked: what happens on events that carry only ONE of the
two messages, and whether the ordering is stable across a route.
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rlog_parse import read_messages  # noqa: E402

RLOGS = Path(__file__).resolve().parent.parent / "analysis-2020accord" / "rlogs"
ROUTES = {"r73": "75604b0a432fdc89_00000073--9380c74d52",
          "r75": "75604b0a432fdc89_00000075--",
          "r76": "75604b0a432fdc89_00000076--"}


def segs(prefix, nmax=3):
    hits = sorted(RLOGS.glob(prefix + "*rlog.zst"),
                  key=lambda p: int(p.name.split("--")[2]))
    return hits[:nmax]


def scan(path):
    c = Counter()
    first_seen = []
    for evt in read_messages(path):
        try:
            if evt.which() != "can":
                continue
        except Exception:
            continue
        i18 = i14 = None
        for k, m in enumerate(evt.can):
            if int(m.src) != 1:
                continue
            a = int(m.address)
            if a == 0x18F and i18 is None:
                i18 = k
            elif a == 0x14A and i14 is None:
                i14 = k
        if i18 is None and i14 is None:
            continue
        if i18 is None:
            c["only_14A"] += 1
        elif i14 is None:
            c["only_18F"] += 1
        else:
            c["both"] += 1
            if i18 < i14:
                c["18F_first"] += 1
            else:
                c["14A_first"] += 1
            if len(first_seen) < 8:
                first_seen.append((i18, i14))
    return c, first_seen


def main():
    print("=" * 100)
    print("WHICH COMES FIRST INSIDE evt.can:  0x18F (src 1)  or  0x14A (src 1)?")
    print("=" * 100)
    grand = Counter()
    for rt, pfx in ROUTES.items():
        files = segs(pfx)
        if not files:
            print("  {}: no rlogs found for prefix {}".format(rt, pfx))
            continue
        tot = Counter()
        for f in files:
            c, fs = scan(f)
            tot.update(c)
            print("   {} {:<52s} both {:6d}  18F_first {:6d}  14A_first {:6d}  "
                  "only18F {:5d}  only14A {:5d}".format(
                      rt, f.name.split("--")[2] + "  " + f.name[-30:], c["both"],
                      c["18F_first"], c["14A_first"], c["only_18F"], c["only_14A"]))
            if fs:
                print("        first shared events, (idx18F, idx14A): {}".format(fs[:6]))
        b = max(tot["both"], 1)
        print("   {} TOTAL: both {:7d}   **18F first {:7d} ({:.4%})   14A first {:7d} ({:.4%})**"
              "   only18F {:6d}   only14A {:6d}".format(
                  rt, tot["both"], tot["18F_first"], tot["18F_first"] / b,
                  tot["14A_first"], tot["14A_first"] / b, tot["only_18F"], tot["only_14A"]))
        print()
        grand.update(tot)
    b = max(grand["both"], 1)
    print("=" * 100)
    print("ALL ROUTES: both {}   18F first {} ({:.4%})   14A first {} ({:.4%})".format(
        grand["both"], grand["18F_first"], grand["18F_first"] / b,
        grand["14A_first"], grand["14A_first"] / b))
    print("  non-co-logged: only 0x18F {}   only 0x14A {}   "
          "(these are the ~4% where the hold genuinely ages)".format(
              grand["only_18F"], grand["only_14A"]))
    print()
    if grand["14A_first"] > grand["18F_first"]:
        print("  => 0x14A IS PROCESSED FIRST => the row carries the PREVIOUS 0x18F")
        print("     => the payload is ~10 ms OLDER than the row label => THE CORRECTION STANDS")
    else:
        print("  => 0x18F IS PROCESSED FIRST => last18 is already this instant's frame")
        print("     => NO SKEW => the correction must be REMOVED wherever it was applied")


if __name__ == "__main__":
    main()
