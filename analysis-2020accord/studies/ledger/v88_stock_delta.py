#!/usr/bin/env python3
"""V88's CUMULATIVE delta vs STOCK, read from the PLAIN IMAGES ON DISK -- not from build scripts.

Two outputs:
  1. Every byte run in `_v88_..._plain_image.bin` that differs from stock, with CRC trailers
     separated from real edits, and each real run attributed to the build that introduced it by
     walking the image chain V38 -> V88 and reporting the FIRST build whose byte matches V88's.
  2. The cross-build matrix of the kit's standing cell list, V38 -> V88, so it is visible at a
     glance which cells have moved and which have been frozen for N builds.

Plain images are flat 1 MiB code images: file offset == firmware address.  V850 is LITTLE-ENDIAN.
Anchors asserted before anything is reported (stock 0xC646C == 891, 0x454FE == 0xBA).

Usage:  python studies/ledger/v88_stock_delta.py            # both tables
        python studies/ledger/v88_stock_delta.py runs       # just the stock delta
        python studies/ledger/v88_stock_delta.py matrix     # just the cross-build matrix
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
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
# --- end path bootstrap ---------------------------------------------------
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ledger_v38_to_v84_bytes as L  # noqa: E402  -- the established reader; SITES/PTRS reused

ROOT = L.ROOT
STOCK = L.STOCK

# The chain in flight order, V38 -> V88.  Attribution walks this list.
CHAIN = list(L.BUILDS) + [
    ("V85",  "_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin"),
    ("V86",  "_v86_CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V86B", "_v86b_FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB_plain_image.bin"),
    ("V87",  "_v87_V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98_plain_image.bin"),
    ("V88",  "_v88_V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256"
             "_plain_image.bin"),
]

# Builds that actually FLEW, newest last.  Used only to label the matrix.
FLOWN = {"V38", "V39", "V41", "V42", "V53", "V54", "V55", "V56", "V57", "V58", "V59", "V60",
         "V61", "V62", "V64", "V65", "V66", "V67", "V68", "V69", "V70", "V71a", "V71b", "V71c",
         "V72", "V73", "V74", "V75", "V76", "V80", "V81", "V83a", "V84", "V85", "V86", "V86B",
         "V87", "V88"}

# CRC trailer geometry.  The bootloader walks 50 blocks and every block END is 0x?????FFC, with the
# checksum occupying that word.  `verify_bootloader_crc.walk_all_blocks` prints all 50 and is used as
# the SECOND method (below) rather than as the classifier, so this stays quiet and byte-exact.
def is_crc_word(addr):
    return (addr & 0xFFF) >= 0xFFC


def load(stem):
    p = stem if isinstance(stem, Path) else ROOT / stem
    return p.read_bytes()


def crc_word_addrs(img):
    """Addresses covered by a CRC trailer word.  Block ends are 0x?????FFC across all 50 blocks."""
    return {a for a in range(0x13000, 0x100000) if is_crc_word(a)}


START, END = 0x13000, 0x100000          # the flashed region; anything outside it is not shipped


def runs(a, b, gap=4):
    """Differing byte runs inside the FLASHED region, merging runs closer than `gap`.

    🛑 Restricted to [0x13000, 0x100000).  Below START the plain images carry an undumped
    bootloader area that differs wholesale and is NOT part of any build's delta.
    """
    assert len(a) == len(b)
    diff = [i for i in range(START, END) if a[i] != b[i]]
    if not diff:
        return []
    out, s, p = [], diff[0], diff[0]
    for i in diff[1:]:
        if i - p <= gap:
            p = i
            continue
        out.append((s, p))
        s = p = i
    out.append((s, p))
    return out


def attribute(imgs, order, addr, v88_byte, stock_byte):
    """First build in `order` whose byte at `addr` equals V88's and differs from stock."""
    for n in order:
        if n in ("STOCK",):
            continue
        b = imgs.get(n)
        if b is None:
            continue
        if b[addr] == v88_byte and v88_byte != stock_byte:
            return n
    return "?"


def hexs(bs):
    return "".join(f"{x:02x}" for x in bs)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"

    imgs, order = {}, []
    for name, f in CHAIN:
        p = f if isinstance(f, Path) else ROOT / f
        if not p.exists():
            print(f"### MISSING {name}: {p}", file=sys.stderr)
            continue
        imgs[name] = load(p)
        order.append(name)

    st, v88 = imgs["STOCK"], imgs["V88"]
    assert len(st) == 0x100000 and len(v88) == 0x100000
    assert L.s16(st, 0xC646C) == 891 and st[0x454FE] == 0xBA
    assert L.s16(v88, 0xC6446) == 5244, L.s16(v88, 0xC6446)      # Lever B arm, from the IMAGE
    assert v88[0x3AA96] == 0xFB, hex(v88[0x3AA96])               # Lever B gate, from the IMAGE
    print("ANCHORS OK  stock 0xC646C=891 / 0x454FE=0xBA ; V88 0xC6446=5244 / 0x3AA96=0xFB\n")

    if what in ("all", "runs"):
        crc = crc_word_addrs(st)
        rr = runs(st, v88)
        real = [(s, e) for s, e in rr if not all(i in crc for i in range(s, e + 1))]
        trail = len(rr) - len(real)
        print(f"V88 vs STOCK: {len(rr)} differing runs "
              f"({len(real)} real edits, {trail} CRC trailers), "
              f"{sum(e - s + 1 for s, e in rr):,} bytes total\n")
        print(f"{'addr':>9} {'w':>3}  {'stock':<22} {'V88':<22} introduced")
        print("-" * 86)
        for s, e in real:
            w = e - s + 1
            src = attribute(imgs, order, s, v88[s], st[s])
            print(f"0x{s:05X} {w:>3}  {hexs(st[s:e+1]):<22} {hexs(v88[s:e+1]):<22} {src}")
        print()

    if what in ("all", "matrix"):
        cols = [n for n in order if n not in ("STOCK",)]
        # show only cells that MOVE somewhere in the chain, plus the frozen headline cells
        print("CROSS-BUILD MATRIX  (cells that move somewhere V38..V88; STOCK first)\n")
        for addr, w, label in L.SITES:
            vals = {}
            for n in ["STOCK"] + cols:
                b = imgs[n]
                vals[n] = b[addr] if w == 1 else L.s16(b, addr)
            moved = len({vals[n] for n in cols}) > 1 or vals["V88"] != vals["STOCK"]
            frozen = sum(1 for n in cols if vals[n] == vals["STOCK"])
            tag = "" if moved else f"   [FROZEN at stock in {frozen}/{len(cols)} builds]"
            if not moved:
                continue
            fmt = (lambda v: f"{v:02X}") if w == 1 else (lambda v: f"{v}")
            print(f"0x{addr:05X}  {label}{tag}")
            print(f"    STOCK={fmt(vals['STOCK'])}   V87={fmt(vals['V87'])}   "
                  f"V88={fmt(vals['V88'])}")
            seq, last = [], None
            for n in cols:
                if vals[n] != last:
                    seq.append(f"{n}:{fmt(vals[n])}")
                    last = vals[n]
            print("    " + " -> ".join(seq))
            print()

        print("FROZEN AT STOCK ACROSS THE WHOLE V38..V88 CHAIN:")
        for addr, w, label in L.SITES:
            vals = {n: (imgs[n][addr] if w == 1 else L.s16(imgs[n], addr))
                    for n in ["STOCK"] + cols}
            if all(vals[n] == vals["STOCK"] for n in cols):
                print(f"    0x{addr:05X}  {label}  = {vals['STOCK']}   "
                      f"({len(cols)} builds, never moved)")


if __name__ == "__main__":
    main()
