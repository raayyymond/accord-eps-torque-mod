#!/usr/bin/env python3
"""verify/verify_v79.py -- verify the V79 ARTIFACTS ON DISK, independently of builds/v50_v79/build_v79_tva.py.

🛑 The builder's own readback is not evidence for the FILES: it checks the buffer it just made. This
script opens the two artifacts, re-hashes them, decodes the .rwd back to bytes, and re-derives every
decision-bearing claim from the DISK image with raw little-endian struct reads -- no Surface object,
no shared record helper, no build-script constant that is not restated here.
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
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF                                              # noqa: E402
from encode_eps import parse_x31, build_decode_table                           # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

V78_IMG = plain_image_path("_v78_v76base_ey1_449_dose206_plain_image.bin")
V79_IMG = plain_image_path("_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin")
V79_RWD = Path(RWD_DIR) / ("39990-TVA,A160-V79-V78BASE-EY1.897-EY2.912-dose412-"
                           "probe-6bd0-63fd-67fa-0x13000-0x100000.rwd")
V78_SHA = "c8d8e5e1c606dd920ccec8d41ea6398c73dbe473f58912092770e700ffd50ab1"
V79_IMG_SHA = "dc87ee1c8f43408061162567bc396b7a8660b30a9941793f3e1629401a468c86"
V79_RWD_SHA = "4adc88e2e91578cf4d445d045e6bc6f02d5de8b554b364334b4ba7235b8592e8"

START, END = 0x13000, 0x100000
FACTOR_PTRS = {"B": 0xC9CCC, "C": 0xC9E9C, "D": 0xC9DB4, "E": 0xC9F84,
               "CEIL": 0xC77A0, "FRIC": 0xCBE74}
NPTS = {"B": 4, "C": 4, "D": 5, "E": 4, "CEIL": 2, "FRIC": 3}
CAVE = (0xC4B34, 68)
FAILS = []


def chk(label, got, want, note=""):
    ok = got == want
    if not ok:
        FAILS.append(label)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label:<62} got {str(got):<22} want {str(want)} {note}")
    return ok


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def s16(b, a):
    return struct.unpack_from("<h", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


def rec(img, which, mode):
    """Dereference and parse, from scratch. Layout: n | n*X | n*Y | terminator. X at base+2."""
    base = u32(img, FACTOR_PTRS[which] + 4 * mode)
    n = u16(img, base)
    X = [s16(img, base + 2 + 2 * i) for i in range(n)]
    Y = [s16(img, base + 2 + 2 * n + 2 * i) for i in range(n)]
    return base, n, X, Y


def lerp(X, Y, idx):
    """FUN_00034350's LERP: UNSIGNED strict compares, `divq` truncates toward ZERO."""
    n = len(X)
    if not idx > X[0]:
        return Y[0] & 0xFFFF
    if not idx < X[n - 1]:
        return Y[n - 1] & 0xFFFF
    k = 1
    while X[k] <= idx:
        k += 1
    return (int((Y[k] - Y[k - 1]) * (idx - X[k - 1]) / (X[k] - X[k - 1])) + Y[k - 1]) & 0xFFFF


def dose(img, mode, speed, rate):
    """(C(speed) * E(rate)) >> 10 with B = D = seed = 1024, then the ceiling clamp at its FLOOR."""
    _b, _n, cx, cy = rec(img, "C", mode)
    _b, _n, ex, ey = rec(img, "E", mode)
    if not (speed < 0x7D00) or not (rate < 0x32C9):
        return None
    d = (1024 * lerp(cx, cy, speed)) >> 10
    d = (d * lerp(ex, ey, rate)) >> 10
    return d


def main():
    print("=" * 104)
    print("  VERIFY V79 -- from the artifacts on disk, independently of the builder")
    print("=" * 104)

    for p in (V78_IMG, V79_IMG, V79_RWD):
        assert os.path.exists(p), f"missing artifact {p}"
    v78 = Path(V78_IMG).read_bytes()
    v79 = Path(V79_IMG).read_bytes()
    rwd = Path(V79_RWD).read_bytes()
    stock = Path(stock_fw_path("code.bin")).read_bytes()

    print("\n-- 1. HASHES AND SIZES --------------------------------------------------------------")
    chk("V78 base image sha256", hashlib.sha256(v78).hexdigest(), V78_SHA)
    chk("V79 plain image sha256", hashlib.sha256(v79).hexdigest(), V79_IMG_SHA)
    chk("V79 .rwd sha256", hashlib.sha256(rwd).hexdigest(), V79_RWD_SHA)
    chk("V79 image size", len(v79), 0x100000)
    chk("V79 image name", os.path.basename(V79_IMG),
        "_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin")

    print("\n-- 2. THE .rwd DECODES TO THE IMAGE --------------------------------------------------")
    FF.assert_x31_checksum(rwd, "V79 on disk")
    info = parse_x31(rwd)
    chk("x31 headers", info["headers"] == FF.EXPECTED_HEADERS, True)
    chk("x31 payload block", info["blocks"], [{"start": START, "length": END - START}])
    decoded = bytes(info["encs"][0]).translate(build_decode_table(FF.V9B["keys"], FF.V9B["ops"]))
    chk("decoded .rwd payload == image[0x13000:0x100000]", decoded == v79[START:END], True)

    print("\n-- 3. BYTE DIFF V78 -> V79 -----------------------------------------------------------")
    runs, i = [], START
    while i < END:
        if v78[i] != v79[i]:
            j = i
            while j < END and v78[j] != v79[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    for a, ln in runs:
        print(f"        0x{a:05X} +{ln}   {v78[a:a + ln].hex()} -> {v79[a:a + ln].hex()}")
    chk("changed runs", runs, [(0xD7818, 4), (0xD7FFC, 4)],
        "= the two FactorE cells + the CRC trailer of block [0xD7000,0xD7FFC)")
    chk("total changed bytes", sum(ln for _a, ln in runs), 8)
    chk("cave 0xC4B34+68 unchanged vs V78",
        v79[CAVE[0]:CAVE[0] + CAVE[1]] == v78[CAVE[0]:CAVE[0] + CAVE[1]], True)
    chk("cave tail still virgin 0xFF", v79[CAVE[0] + CAVE[1]:0xC4B80],
        b"\xff" * (0xC4B80 - CAVE[0] - CAVE[1]))

    print("\n-- 4. THE EDIT, RE-DERIVED THROUGH THE POINTER ARRAY ---------------------------------")
    for mode in (24, 26):
        for w in ("C", "E"):
            b, n, X, Y = rec(v79, w, mode)
            print(f"        Factor{w} m{mode} @0x{b:05X} n={n}  X={X}  Y={Y}")
    b, n, ex, ey = rec(v79, "E", 26)
    chk("FactorE m26 record address (deref 0xC9F84+26*4)", hex(b), hex(0xD780C))
    chk("FactorE m26 X (UNCHANGED)", ex, [0, 119, 2500, 4000])
    chk("FactorE m26 Y", ey, [0, 897, 912, 927])
    chk("  Y[1] address", hex(b + 2 + 2 * n + 2), hex(0xD7818))
    chk("  Y[2] address", hex(b + 2 + 2 * n + 4), hex(0xD781A))
    chk("FactorE m26 Y strictly INCREASING", all(ey[i] < ey[i + 1] for i in range(3)), True)
    chk("FactorE m26 Y[0] == 0 (no Coulomb relay)", ey[0], 0)
    chk("FactorE m26 point count unchanged", n, 4)
    chk("FactorE m26 terminator (V73 spill signature)", v79[b + 18:b + 20], b"\x00\x00")
    _b, _n, cx, cy = rec(v79, "C", 26)
    chk("FactorC m26 UNTOUCHED", (cx, cy), ([2240, 3840, 5120, 8960], [566, 566, 566, 908]))
    chk("FactorC m26 Y monotone non-decreasing", all(cy[i] <= cy[i + 1] for i in range(3)), True)

    print("\n-- 5. MODE 24 AND THE OTHER FACTORS, BYTE-STOCK --------------------------------------")
    for w in ("B", "C", "D", "E", "CEIL", "FRIC"):
        base = u32(v79, FACTOR_PTRS[w] + 4 * 24)
        ln = 2 + 4 * NPTS[w]
        chk(f"Factor{w} mode 24 byte-identical to STOCK", v79[base:base + ln] == stock[base:base + ln],
            True, f"@0x{base:05X}")
    for w in ("B", "C", "D", "CEIL", "FRIC"):
        base = u32(v79, FACTOR_PTRS[w] + 4 * 26)
        ln = 2 + 4 * NPTS[w]
        chk(f"Factor{w} mode 26 unchanged vs V78", v79[base:base + ln] == v78[base:base + ln],
            True, f"@0x{base:05X}")
    fb = u32(v79, FACTOR_PTRS["FRIC"] + 4 * 26)
    chk("friction m26 record address", hex(fb), hex(0xD7A54))
    chk("friction m26 byte-identical to STOCK", v79[fb:fb + 14] == stock[fb:fb + 14], True)
    for w, ptrs in FACTOR_PTRS.items():
        chk(f"{w} pointer array == STOCK over 34 modes",
            v79[ptrs:ptrs + 136] == stock[ptrs:ptrs + 136], True, f"@0x{ptrs:05X}")

    print("\n-- 6. 🛑 THE MUST-NOT-CHANGE CELLS ---------------------------------------------------")
    for a in range(0xC63A0, 0xC63AC, 2):
        chk(f"0xC63A0 block: 0x{a:05X} (operator: DO NOT DOUBLE)", u16(v79, a), 1024,
            f"stock {u16(stock, a)}")
    chk("0xC407E friction clamp (RULE 11 interlock)", u16(v79, 0xC407E), 511,
        f"stock {u16(stock, 0xC407E)}")
    chk("0xC4004 monitor threshold bytes", v79[0xC4004:0xC4008].hex(), "0000003f",
        f"= float {struct.unpack_from('<f', v79, 0xC4004)[0]} -> {int(0.5 * 1024)} counts")
    chk("clamp sits strictly UNDER the trip", u16(v79, 0xC407E) < int(0.5 * 1024), True)
    for a, want in ((0xC407C, 461), (0xC6444, 512), (0xC6446, 512), (0xC643E, 1536)):
        chk(f"0x{a:05X} not carried forward", u16(v79, a), want)

    print("\n-- 7. CRC CHAIN ----------------------------------------------------------------------")
    blocks = FF.crc_block_map(v79)
    chk("block count", len(blocks), 50)
    bad = [(s, t) for s, t in blocks if zlib.crc32(v79[s:t]) & 0xFFFFFFFF != u32(v79, t)]
    chk("blocks with a CRC mismatch", bad, [])
    chk("verify_bootloader_crc.walk_all_blocks", walk_all_blocks(v79), 0)

    print("\n-- 8. THE ARITHMETIC, RE-DERIVED FROM THE DISK IMAGE ---------------------------------")
    d79 = dose(v79, 26, 515, 99)
    d78 = dose(v78, 26, 515, 99)
    chk("dose(5 mph = 515 ct, r = 99 ct) on V79", d79, 412)
    chk("dose on V78", d78, 206)
    chk("V79 / V78 dose ratio", d79 / d78, 2.0)
    k79 = ((lerp(cx, cy, 515) * ey[1]) >> 10) / (ex[1] - ex[0])
    print(f"        k = ((C(515)={lerp(cx, cy, 515)} * E_Y1={ey[1]}) >> 10) / (E_X1-E_X0={ex[1]}) "
          f"= {k79:.4f}")
    chk("k = 4.1597", round(k79, 4), 4.1597)
    print("        V79/V78 dose ratio at 5 mph, by steering rate:")
    for r in (25, 50, 99, 118, 200, 400, 1200, 2500):
        a, b_ = dose(v79, 26, 515, r), dose(v78, 26, 515, r)
        print(f"          r={r:5d} ct = {r / 4.7121:6.1f} deg/s   V78 {b_:4d}  V79 {a:4d}   "
              f"{a / b_:.3f}x")
    emax = max(lerp(ex, ey, r) for r in range(0x32C9))
    chk("max (566 * E) >> 10 at creep <= ceiling floor 512", (566 * emax) >> 10, 512,
        f"E_max = {emax}")
    print("        first CLIPPING rate at the ceiling floor (512), by speed:")
    for kmh in (80, 85, 96.7, 140):
        sp = int(round(kmh * 64.0))
        f = lambda img: next((r for r in range(0x32C9) if dose(img, 26, sp, r) > 512), None)
        a, b_ = f(v78), f(v79)
        print(f"          {kmh:>5} km/h  C={lerp(cx, cy, sp):3d}   V78 "
              f"{'never' if a is None else str(a) + ' ct':>10}   V79 "
              f"{'never' if b_ is None else str(b_) + ' ct':>10}")
    print("        probe trip rates at 5 mph (cave byte-identical to V78):")
    for thr, bit in ((192, 6), (448, 7)):
        f = lambda img: next((r for r in range(0x32C9) if min(dose(img, 26, 515, r), 512) >= thr),
                             None)
        a, b_ = f(v78), f(v79)
        print(f"          bit{bit} |gp-0x6bd0| >= {thr:3d}   V78 {a:5d} ct = {a / 4.7121:5.1f} d/s"
              f"   V79 {b_:5d} ct = {b_ / 4.7121:5.1f} d/s")

    print("\n" + "=" * 104)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED: {FAILS}")
        return 1
    print("  ALL CHECKS PASS -- verified from the artifacts on disk.")
    print("  🛑 THIS IS NOT A FLASH CLEARANCE. V79 IS NOT CLEARED TO FLY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
