#!/usr/bin/env python3
"""V97 VIRGINITY CENSUS — for ANY address, how many images on disk ever left stock.

Why this exists: `ledger_v94_cells.py` hand-lists MATRIX_SCALARS, so a cell that no build ever
touched is INVISIBLE to it — and virgin cells are exactly what we are hunting.  This walks the whole
corpus and answers, per address: stock value, current value on the target build, and the set of build
tags that ever differed from stock.  A cell with an EMPTY set is virgin.

Also fixes two defects in ledger_v94_cells.py (REPORTED, not patched there):
  1. Its BUILDS list stops at V94, so `LEDGER_TARGET=V96` KeyErrors in `matrix` and is SILENTLY
     IGNORED by `grid` (grid never reads TARGET — it prints a V94 grid that looks retargeted).
  2. The _v95_* plain images its Ghidra sessions reference are no longer on disk.

Usage:
    python ledger_v97_virginity.py cells 0xC63A6 0xC64DE ...   # named cells, full history
    python ledger_v97_virginity.py sweep 0xC6300 0xC6500       # every halfword in a range
    python ledger_v97_virginity.py virgins 0xC6000 0xC7000     # only the never-moved halfwords
"""
import struct
import sys
from pathlib import Path

ROOT = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
STOCK = ROOT / "stock_fw_dump" / "code.bin"

# Every plain image on disk, in build order.  Globbed so a freshly-cut build is picked up without
# editing this file; the sort key parses the numeric build index out of the filename.
def build_list():
    out = [("STOCK", STOCK)]
    hits = []
    for p in ROOT.glob("_v*_plain_image.bin"):
        stem = p.name[2:].split("_")[0]          # "_v76g_foo_plain_image.bin" -> "v76g"
        num = "".join(c for c in stem if c.isdigit())
        if not num:
            continue                              # _vcantxtest, _vfourframe: not numbered builds
        hits.append((int(num), stem, p))
    for _, tag, p in sorted(hits, key=lambda t: (t[0], t[1])):
        out.append((tag.upper(), p))
    return out


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def load():
    builds = build_list()
    imgs, order = {}, []
    for tag, p in builds:
        if not p.exists():
            print(f"### MISSING {tag}: {p}", file=sys.stderr)
            continue
        imgs[tag] = p.read_bytes()
        order.append(tag)
    st = imgs["STOCK"]
    assert len(st) == 0x100000, len(st)
    # tp-relative anchors: guards the recurring off-by-0x1000.  tp=0xBF000 => tp+0x746C == 0xC646C.
    assert s16(st, 0xC646C) == 891, s16(st, 0xC646C)
    assert st[0x454FE] == 0xBA, hex(st[0x454FE])
    return imgs, order


# Addresses that are 0xFF in EVERY non-stock image => plain-image packaging, not a real edit.
def packaging_mask(imgs, order):
    st = imgs["STOCK"]
    tags = [t for t in order if t != "STOCK"]
    mask = set()
    for i in range(len(st)):
        if st[i] == 0xFF:
            continue
        if all(imgs[t][i] == 0xFF for t in tags):
            mask.add(i)
    return mask


def movers(imgs, order, addr, width, mask):
    """Build tags whose bytes at [addr, addr+width) differ from stock, packaging excluded."""
    st = imgs["STOCK"]
    if all(a in mask for a in range(addr, addr + width)):
        return []
    sv = st[addr:addr + width]
    return [t for t in order if t != "STOCK" and imgs[t][addr:addr + width] != sv]


def fmt(b, addr, width, signed=True):
    if width == 1:
        return f"0x{b[addr]:02X}"
    return str(s16(b, addr) if signed else u16(b, addr))


def cmd_cells(imgs, order, args):
    mask = packaging_mask(imgs, order)
    st = imgs["STOCK"]
    target = order[-1]
    print(f"corpus: {len(order) - 1} non-stock images, newest = {target}\n")
    for a in args:
        addr = int(a, 0)
        mv = movers(imgs, order, addr, 2, mask)
        print(f"0x{addr:05X}  stock={fmt(st, addr, 2)}  {target}={fmt(imgs[target], addr, 2)}")
        print(f"    moved by {len(mv)} / {len(order) - 1} images"
              + (f": {' '.join(mv)}" if mv else "   <== VIRGIN"))
        if mv:
            prev = None
            for t in order:
                v = fmt(imgs[t], addr, 2)
                if v != prev:
                    print(f"      {t:<8} {v}")
                    prev = v
        print()


def cmd_sweep(imgs, order, args, virgins_only=False):
    lo, hi = int(args[0], 0), int(args[1], 0)
    mask = packaging_mask(imgs, order)
    st = imgs["STOCK"]
    target = order[-1]
    n = len(order) - 1
    print(f"corpus: {n} non-stock images, newest = {target}")
    print(f"sweep 0x{lo:05X}-0x{hi:05X} halfwords"
          + ("  [VIRGIN ONLY]" if virgins_only else "") + "\n")
    print(f"{'addr':<10}{'stock':>8}{'target':>8}  movers")
    for addr in range(lo, hi, 2):
        mv = movers(imgs, order, addr, 2, mask)
        if virgins_only and mv:
            continue
        if not virgins_only and not mv:
            continue
        print(f"0x{addr:05X}  {fmt(st, addr, 2):>8}{fmt(imgs[target], addr, 2):>8}  "
              + (f"{len(mv):>2}x {' '.join(mv)}" if mv else "VIRGIN"))


def main():
    imgs, order = load()
    cmd = sys.argv[1]
    if cmd == "cells":
        cmd_cells(imgs, order, sys.argv[2:])
    elif cmd == "sweep":
        cmd_sweep(imgs, order, sys.argv[2:])
    elif cmd == "virgins":
        cmd_sweep(imgs, order, sys.argv[2:], virgins_only=True)


if __name__ == "__main__":
    main()
