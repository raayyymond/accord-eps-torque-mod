#!/usr/bin/env python3
"""Build `_cache_loop_op/` -- the batch-lattice cache the command<->response causality work runs on.

    python loop_op_extract.py                # all four routes
    python loop_op_extract.py V84/r6d        # one

See `loop_op_lib`'s docstring for why this cache exists rather than reusing `_cache_r6d` etc.:
the corpus caches build one row per 0x14A frame and carry the 0x18F payload forward by a whole
batch, and they resample `sendcan` onto that foreign lattice with `np.interp`.  Both are fatal to a
phase-slope measurement at 27 Hz.
"""
import sys

import numpy as np

import loop_op_lib as L

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main(routes):
    for r in routes:
        print(f"=== {r}", flush=True)
        segs = L.build_route(r)
        L.save_route(r, segs)
        t = sum(len(d["t"]) for d in segs)
        eng = sum(int((d["cc_lat"] > 0.5).sum()) for d in segs)
        fss = np.array([d["_fs"] for d in segs])
        print(f"    {len(segs)} segs  {t} batches  {t/100:.0f} s  engaged {eng/max(t,1)*100:.1f}%  "
              f"fs {fss.min():.4f}..{fss.max():.4f}")
        # instrument health: how close is the batch lattice to uniform?
        for d in segs[:2]:
            dt = np.diff(d["t"])
            print(f"      seg{d['_seg']} dt p1/p50/p99 = {np.percentile(dt,1)*1e3:.2f}/"
                  f"{np.median(dt)*1e3:.2f}/{np.percentile(dt,99)*1e3:.2f} ms  "
                  f"gaps>15ms: {(dt>0.015).sum()}")
    print(f"\ncache -> {L.CACHE}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a in L.ROUTES]
    main(args or list(L.ROUTES))
