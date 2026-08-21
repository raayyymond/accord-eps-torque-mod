#!/usr/bin/env python3
"""Guard against the 427-alias trap in the route caches.

WHAT THE TRAP IS
----------------
CAN 427 (0x1AB) carries ONE firmware cell, and which cell depends on the BUILD:

    V100 (route 0x85), V101 (route 0x95)   ->  427 packs gp-0x6b94, the AGGREGATOR SUM
    V102 (route 0x96), V103 (route 0x9e)   ->  427 packs gp-0x6b4c, the 11-slot LANE
    stock            (route 0x97)          ->  427 packs gp-0x6b4c, the LANE

The extractors write BOTH `x6b94` and `x6b4c` keys regardless, so on any route where 427
carried the LANE, `x6b94` is a MISLABELLED ALIAS of `x6b4c` -- byte-identical, not the sum.

WHY IT MATTERS
--------------
Reading `x6b94` off r96/r97/r9e and calling it the aggregator sum is EXACTLY the error that
produced GATE2's original notch verdict: `0.2075 angle +39.7 deg` was quoted as the sum when it
was the lane, which made the priced correction 4x too large. At 6-9 Hz the aggregator is a 4:1
near-cancellation, so lane-vs-sum is not a labelling nicety -- it is a factor of ~4 on every
dose computed from it.

USE
---
Call `assert_is_sum(tag)` before using `x6b94` as the aggregator sum. Run this file directly to
audit every cache on disk.
"""
import glob
import os
import sys

import numpy as np

# Routes where 427 is KNOWN to pack the aggregator sum gp-0x6b94. Everything else is the lane.
SUM_ROUTES = {"r85", "r95"}


def _load(tag):
    hits = sorted(glob.glob("_cache_%s/%s.npz" % (tag, tag))) or sorted(
        glob.glob("_cache_%s/*.npz" % tag)
    )
    if not hits:
        return None, None
    return hits[0], np.load(hits[0], allow_pickle=True)


def is_aliased(tag):
    """True if `x6b94` in this cache is a byte-identical alias of `x6b4c` (i.e. NOT the sum)."""
    path, d = _load(tag)
    if d is None:
        return None
    ks = set(d.files)
    if not ("x6b94" in ks and "x6b4c" in ks):
        return False
    a, b = d["x6b94"], d["x6b4c"]
    return a.shape == b.shape and bool(np.array_equal(a, b))


def assert_is_sum(tag):
    """Raise unless `x6b94` on this route really is the aggregator sum."""
    if tag not in SUM_ROUTES:
        raise AssertionError(
            "route %s did NOT pack gp-0x6b94 on 427 -- its `x6b94` key is an alias of the "
            "gp-0x6b4c LANE, not the aggregator sum. Only %s carry the sum."
            % (tag, sorted(SUM_ROUTES))
        )
    if is_aliased(tag):
        raise AssertionError(
            "route %s is listed as a SUM route but its `x6b94` is byte-identical to `x6b4c` "
            "-- the extractor or SUM_ROUTES is wrong." % tag
        )
    return True


def main():
    tags = sorted(
        os.path.basename(p)[len("_cache_") :] for p in glob.glob("_cache_*") if os.path.isdir(p)
    )
    bad = []
    print("%-6s %-10s %-8s %s" % ("route", "expected", "aliased", "verdict"))
    for tag in tags:
        al = is_aliased(tag)
        if al is None:
            continue
        expected = "SUM" if tag in SUM_ROUTES else "lane"
        if al and tag in SUM_ROUTES:
            verdict, ok = "*** CONTRADICTION ***", False
        elif al:
            verdict, ok = "x6b94 IS AN ALIAS -- do not use as sum", False
        else:
            verdict, ok = "ok", True
        if not ok:
            bad.append(tag)
        print("%-6s %-10s %-8s %s" % (tag, expected, al, verdict))
    if bad:
        print("\nAFFECTED: %s" % ", ".join(bad))
        print("Use `x6b4c` on these routes and do not read `x6b94` as the aggregator sum.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
