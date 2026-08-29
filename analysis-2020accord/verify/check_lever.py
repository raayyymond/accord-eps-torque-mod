#!/usr/bin/env python3
r"""
check_lever.py -- ANSWER "what does this cell ACTUALLY hold on the car?" BEFORE proposing an edit.

    python check_lever.py 0xC6446 0xC40BC ...
    python check_lever.py --record 0xD780C          # dump a LERP record + validate its header

WHY THIS EXISTS
---------------
Two builds died this session to the same root cause, and CLAUDE.md already names it:
"Check build lineage before proposing a cal lever -- grep build_v*_tva.py + BUILD-LINEAGE.md before
naming any address; state its on-car result."

  V159  edited 0xC6728 -- an unrelated 8-knot table -- after an off-by-0x400 on a tp displacement.
  V166  was designed to raise the LKAS setpoint limit 15360 -> 16384, from the golden model's
        Calibration DEFAULT and a scan of the STOCK image.  V38 had already raised the record our
        car uses to 16384; the edit was a NO-OP.  Only the build's base assertion caught it.

=> a model's Calibration defaults are STOCK values, not the flying build's.  READ THE IMAGE.

WHAT IT PRINTS
--------------
For each address: the stock value, the value on the current flying base, and the full distribution
across every plain image in the artifact root -- so "virgin", "already applied" and "moved by an
earlier build" are all visible at a glance, with the build numbers that hold each value.

THE KNOT-COUNT HEADER
---------------------
--record also validates the invariant found 2026-08-28: every cal LERP carries its knot count --
a (0, N) pair immediately before X for inline tp-relative cals, or a bare N at +0 for pointer-table
records.  Validated 54 well-formed vs 8 false positives across 0xC6000-0xC7000.  A correct read must
satisfy hdr == len(X) with X STRICTLY ASCENDING, which catches a wrong address, a wrong knot count
and a wrong stride in one assertion.
"""
import glob
import os
import re
import struct
import sys

ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT",
                      "C:/Users/dudei/Desktop/Projects/accord-firmwares")
ART = os.path.join(ROOT, "analysis-2020accord")
STOCK = os.path.join(ART, "stock_fw_dump", "code.bin")
# the current flying base; update when a new build flies
FLYING = "_v122_V122-V112BASE-KNEE3000.K1.1020-ALPHA2.8-BEST_plain_image.bin"

u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]


def images():
    out = {}
    for f in sorted(glob.glob(os.path.join(ART, "*_plain_image.bin"))):
        base = os.path.basename(f)
        if "SUPERSEDED" in base:
            continue
        m = re.search(r"_v(\d+[a-z]?)_", base)
        out[m.group(1) if m else base[:10]] = f
    return out


def check(addrs):
    stock = open(STOCK, "rb").read()
    flying_path = os.path.join(ART, FLYING)
    flying = open(flying_path, "rb").read() if os.path.exists(flying_path) else None
    imgs = images()
    loaded = {v: open(p, "rb").read() for v, p in imgs.items()}

    for a in addrs:
        print("\n=== 0x%05X ===" % a)
        s = u16(stock, a)
        print("  stock            %d" % s)
        if flying:
            f = u16(flying, a)
            note = "SAME as stock" if f == s else "*** MOVED by an earlier build ***"
            print("  flying base      %d   %s" % (f, note))
        dist = {}
        for v, b in loaded.items():
            if len(b) > a + 1:
                dist.setdefault(u16(b, a), []).append(v)
        print("  across %d images:" % len(loaded))
        for val in sorted(dist):
            builds = " ".join(sorted(dist[val]))
            tag = "  <- VIRGIN (every build)" if len(dist) == 1 else ""
            print("     %-8d %3d builds%s  %s" % (val, len(dist[val]), tag, builds[:70]))


def record(addr):
    """Dump a LERP record at addr and validate the knot-count header both ways."""
    stock = open(STOCK, "rb").read()
    flying_path = os.path.join(ART, FLYING)
    img = open(flying_path, "rb").read() if os.path.exists(flying_path) else stock
    print("\n=== record 0x%05X (read from %s) ===" % (addr, os.path.basename(flying_path)))

    n_ptr = u16(img, addr)                       # pointer-record form: bare N at +0
    ok_ptr = 2 <= n_ptr <= 16
    if ok_ptr:
        X = [u16(img, addr + 2 + 2 * i) for i in range(n_ptr)]
        asc = all(X[i] < X[i + 1] for i in range(n_ptr - 1))
        print("  pointer-record form: hdr=%d  X=%s  %s"
              % (n_ptr, X, "ASCENDING -- VALID" if asc else "NOT ascending -- WRONG ADDRESS?"))
        if asc:
            for yo in sorted({2 + 2 * n_ptr, 0xA, 0xC, 0x16}):
                Y = [u16(img, addr + yo + 2 * i) for i in range(n_ptr)]
                print("     Y@+0x%02X = %s" % (yo, Y))
    if u16(img, addr - 4) == 0 and 2 <= u16(img, addr - 2) <= 16:
        n = u16(img, addr - 2)
        X = [u16(img, addr + 2 * i) for i in range(n)]
        Y = [u16(img, addr + 2 * n + 2 * i) for i in range(n)]
        asc = all(X[i] < X[i + 1] for i in range(n - 1))
        print("  inline (0,N) form:   hdr=(0,%d)  X=%s  %s" % (n, X, "ASCENDING -- VALID" if asc else "NOT ascending"))
        print("                       Y=%s" % Y)
    if not ok_ptr and u16(img, addr - 4) != 0:
        print("  no valid header either way -- this is probably NOT a record start.")


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if x != "--record"]
    if not args:
        print(__doc__)
        sys.exit(0)
    vals = [int(x, 16) if x.lower().startswith("0x") else int(x) for x in args]
    if "--record" in sys.argv:
        for v in vals:
            record(v)
    else:
        check(vals)
