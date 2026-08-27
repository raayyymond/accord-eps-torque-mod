#!/usr/bin/env python3
r"""studies/v102-crossbuild/v102_wire_and_427.py -- two short sub-reports on routes 96 (V102) and 97 (STOCK).

  Q1  DID CAN 427 ACTUALLY GET REPOINTED TO gp-0x6b4c ON V102?  A yes/no, on ENGAGED frames,
      where the lane is non-zero.  (My earlier "identical alphabet" flag was a segment-0 parked
      artefact; this settles it properly.)  The discriminator is WHICH CELL the lane tracks:
      `gp-0x6b94` is the AGGREGATOR OUTPUT (post-governor, drives the motor) and `gp-0x6b4c` is
      the 11-SLOT ASSIST SUM (the LKAS command's own summing node).  So the repointed lane must
      track openpilot's command `e4tq` MORE than V101's lane does, and track delivered wheel
      motion LESS.

  Q2  HOW DENSELY DOES OPENPILOT FILL ITS OWN +-4096 WIRE RANGE?
      `e4tq` in the caches is taken from **src == 129** (0x81 = openpilot's own sendcan TX flag,
      `probe/decode_v84_probe_r6d.py:117`), NOT a gateway echo -- so the cached value SET is the
      transmitted set.  BUT it is zero-order-held onto the ~100 Hz row grid, which duplicates
      frames and therefore CORRUPTS the |delta| distribution.  The lattice and the rail duty come
      from the cache (ZOH-invariant); the |delta| distribution is re-read from RAW sendcan on a
      subset of 100 %-engaged segments.
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
import sys
from collections import Counter
from math import gcd
from functools import reduce
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import v102_xb_lib as L      # noqa: E402
import rlog_parse            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RLOGS = ROOT / "analysis-2020accord" / "rlogs"
PFX = {"96": "75604b0a432fdc89_00000096--57f5183b32",
       "97": "75604b0a432fdc89_00000097--489d7896b3"}
RAW_SEGS = {"96": (7, 8, 9, 10), "97": (5, 6, 7, 8)}       # 100 %-engaged segments
LAB = {"96": "V102 6x", "97": "STOCK 1x", "95": "V101 8x", "85": "V100 4x"}

for _r, _lab in (("96", "V102"), ("97", "V9b-STOCK")):
    if _r not in L.ROUTES:
        L.ROUTES[_r] = L._mk(_r, _lab, gain=0, clamp=0, leverB=False, idcode=0, bits="v102")


def hdr(s):
    print("\n" + "=" * 100)
    print(s)
    print("=" * 100)


def load(route, keys):
    acc = {}
    for s in L.ROUTES[route]["segs"]:
        d = L.load_seg(route, s)
        for k in keys:
            if k in d:
                acc.setdefault(k, []).append(d[k])
    return {k: np.concatenate(v) for k, v in acc.items()}


# =====================================================================================================
if __name__ == "__main__":
    hdr("Q1 -- DID 427 GET REPOINTED TO gp-0x6b4c ON V102?  Engaged frames only.")
    K = ("cc_lat", "e4tq", "rate_c", "mag427", "x6b94", "tq", "cs_tq", "v_rear")
    for r in ("96", "95", "85", "97"):
        d = load(r, K)
        if "mag427" not in d:
            print("   r%-3s %-9s  no mag427 column" % (r, LAB[r]))
            continue
        eng = d["cc_lat"] > 0.5
        man = ~eng
        mg = np.asarray(d["mag427"], float)
        e4 = np.abs(np.asarray(d["e4tq"], float))
        ar = np.abs(np.asarray(d["rate_c"], float))
        n = min(len(mg), len(eng), len(e4), len(ar))
        mg, e4, ar, eng, man = mg[:n], e4[:n], ar[:n], eng[:n], man[:n]

        def sp(a, b, m):
            """Spearman rank correlation on the masked subset (robust, no scale assumption)."""
            x, y = a[m], b[m]
            if len(x) < 100:
                return float("nan")
            rx = np.argsort(np.argsort(x)).astype(float)
            ry = np.argsort(np.argsort(y)).astype(float)
            return float(np.corrcoef(rx, ry)[0, 1])
        print("   r%-3s %-9s  427 nonzero: engaged %.4f  manual %.4f   |  "
              "rank-corr(|427|, |openpilot cmd|) = %+.3f   rank-corr(|427|, |wheel rate|) = %+.3f"
              % (r, LAB[r], float((mg[eng] > 0).mean()), float((mg[man] > 0).mean()),
                 sp(mg, e4, eng), sp(mg, ar, eng)))
    print("""
   READING:  `gp-0x6b94` is the aggregator OUTPUT -- it drives the motor, so on V100/V101 the lane
   should track delivered WHEEL MOTION at least as well as it tracks openpilot's command.
   `gp-0x6b4c` is the 11-slot ASSIST SUM -- the command's own summing node -- so a repointed lane
   should track the COMMAND much more tightly and the wheel much more loosely.""")

    hdr("Q2 -- OPENPILOT'S OWN WIRE DENSITY.  `e4tq` is src==129 (sendcan TX), not a bus echo.")
    print("   (a) VALUE SET + RAIL DUTY, from the cache -- ZOH-invariant, so these are exact.")
    for r in ("96", "97", "95", "85"):
        d = load(r, ("cc_lat", "e4tq"))
        eng = d["cc_lat"] > 0.5
        e = np.asarray(d["e4tq"], float)[:len(eng)].astype(int)
        ee = e[eng]
        u = np.unique(ee)
        nz = u[u != 0]
        g = reduce(gcd, [int(abs(x)) for x in nz]) if len(nz) else 0
        print("\n      r%-3s %-9s  engaged frames %d" % (r, LAB[r], len(ee)))
        print("         distinct codes %d   min %d  max %d   p1 %d  p50 %d  p99 %d"
              % (len(u), ee.min(), ee.max(), *np.percentile(ee, [1, 50, 99]).astype(int)))
        print("         GCD of nonzero codes = %d  =>  %s"
              % (g, "COARSE LATTICE, step %d" % g if g > 1 else
                 "CONTIGUOUS INTEGERS -- no lattice, 1-LSB resolution"))
        for rail in (4096, int(np.abs(ee).max())):
            print("         |code| >= %-5d duty %.4f" % (rail, float((np.abs(ee) >= rail).mean())))
        # occupancy: how much of the reachable range is actually used
        span = int(ee.max() - ee.min()) + 1
        print("         occupancy: %d distinct of %d integers in [%d, %d] = %.1f %%"
              % (len(u), span, ee.min(), ee.max(), 100.0 * len(u) / span))

    print("\n   (b) |DELTA code| BETWEEN SUCCESSIVE TRANSMITTED FRAMES -- from RAW sendcan,")
    print("       because the cache's ZOH duplicates frames and would fabricate zero deltas.")
    for r in ("96", "97"):
        codes, ts = [], []
        for s in RAW_SEGS[r]:
            p = RLOGS / ("%s--%d--rlog.zst" % (PFX[r], s))
            if not p.exists():
                continue
            # 🛑 src == 129 (0x81) inside the `can` stream is openpilot's own TX -- EXACTLY the
            # filter `probe/decode_v84_probe_r6d.py:117` uses.  A per-event try/except is mandatory:
            # every rlog here has at least one event whose `.which()` raises on a torn union, and
            # a try around the whole loop throws the rest of the segment away.
            try:
                for evt in rlog_parse.read_messages(str(p)):
                    try:
                        if evt.which() != "can":
                            continue
                        tm = evt.logMonoTime * 1e-9
                        for m in evt.can:
                            if int(m.src) == 129 and int(m.address) == 0x0E4:
                                dd = bytes(m.dat)
                                if len(dd) >= 2:
                                    v = (dd[0] << 8) | dd[1]
                                    codes.append(v - 65536 if v >= 32768 else v)
                                    ts.append(tm)
                    except Exception:
                        continue
            except Exception as exc:
                print("        (rlog ended early %s: %s)" % (p.name, str(exc).splitlines()[0]))
        if len(codes) < 500:
            print("      r%-3s only %d raw TX frames -- not quoted" % (r, len(codes)))
            continue
        c = np.array(codes, int)
        t = np.array(ts, float)
        dt = np.diff(t)
        ok = (dt > 0) & (dt < 0.05)
        dc = np.abs(np.diff(c))[ok]
        u = np.unique(c)
        nz = u[u != 0]
        g = reduce(gcd, [int(abs(x)) for x in nz]) if len(nz) else 0
        print("\n      r%-3s %-9s  %d raw sendcan 0x0E4 frames over %d segments, TX rate %.1f Hz"
              % (r, LAB[r], len(c), len(RAW_SEGS[r]), 1.0 / np.median(dt)))
        print("         distinct codes %d  range [%d, %d]  GCD %d  =>  %s"
              % (len(u), c.min(), c.max(), g,
                 "step %d lattice" % g if g > 1 else "CONTIGUOUS -- 1-LSB steps available"))
        print("         |delta| per TX frame:  p10 %.0f  p50 %.0f  p90 %.0f  p99 %.0f  max %.0f"
              % tuple(np.percentile(dc, [10, 50, 90, 99, 100])))
        print("         fraction of frames with |delta| == 0: %.4f   |delta| >= 4: %.4f   "
              ">= 16: %.4f" % (float((dc == 0).mean()), float((dc >= 4).mean()),
                               float((dc >= 16).mean())))
        print("         |code| >= 4096 duty (raw TX) %.4f" % float((np.abs(c) >= 4096).mean()))
