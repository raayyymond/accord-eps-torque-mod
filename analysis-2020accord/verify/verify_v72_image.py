#!/usr/bin/env python3
"""verify/verify_v72_image.py -- VALUE-ANCHORED verification of a built V72 image.

🛑 WHY THIS EXISTS AND WHY IT IS NOT `verify/diff_build_vs_stock.py`.
That tool is SPAN-based: it asks "which byte ranges moved?" A span check passes on the WRONG BUILD --
two images that edit the same addresses to different values are indistinguishable to it, and the kit
has a recorded case where a re-cut under the same number produced an artefact no gate could check.
This file asserts the ACTUAL VALUES at every site, including every MUST-REMAIN-STOCK one, so it
fails on any image that is not V72.

🛑 IT DOES NOT SIMPLY IMPORT THE BUILDER'S NUMBERS AND COMPARE THEM TO THEMSELVES. Every expected
value below is re-declared here as a LITERAL, from `docs/specs/design/V72-DESIGN.md`, and then CROSS-CHECKED
against `builds/v50_v79/build_v72_tva.py`'s own tables. A divergence between the two independent statements is a
failure -- so a typo in either file is caught, which importing alone could never do.

Usage:  python verify/verify_v72_image.py [IMAGE]        (default: _v72_plain_image.bin)
        python verify/verify_v72_image.py --rwd PATH     (decode a .rwd and verify the payload)
"""
from __future__ import annotations
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

import argparse
import hashlib
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_v72_tva as V72                                                    # noqa: E402
import build_vfourframe_tva as FF                                             # noqa: E402
import build_v64_tva as V64                                                   # noqa: E402
import v72_lane_model as LM                                                   # noqa: E402
from encode_eps import parse_x31, build_decode_table                          # noqa: E402
from firmware_paths import plain_image_path, stock_fw_path                    # noqa: E402
from verify_bootloader_crc import walk_all_blocks                             # noqa: E402

# =====================================================================================================
# THE EXPECTATION, RE-DECLARED AS LITERALS FROM docs/specs/design/V72-DESIGN.md -- not imported
# =====================================================================================================
EXPECT_LEVER_A = {                       # record base -> the FULL final Y row. FLAT = whole axis.
    0xD2A74: [5244, 5244, 5244, 5244],   # gain_B mode-10 rec0,  0 km/h   r24
    0xD2AB0: [5244, 5244, 5244, 5244],   # gain_B mode-10 rec1, 10 km/h   r24
    0xC6A68: [512, 512, 512, 512],       # gain_A rec0,          0 km/h   r26
    0xC6A7C: [512, 512, 512, 512],       # gain_A rec1,         10 km/h   r26
}
EXPECT_LEVER_B = {                       # 10 cells = 20 bytes
    0xD27C6: 430, 0xD27C8: 430,          # FactorC m10 Y[0], Y[1]  -> [430, 430, 430, 877]
    0xD27DA: 431, 0xD27DC: 431,          # FactorC m11 Y[0], Y[1]  -> [431, 431, 431, 877]
    0xD2802: 927, 0xD2804: 927, 0xD2806: 927,     # FactorE m10 -> [927, 927, 927, 927]
    0xD2816: 927, 0xD2818: 927, 0xD281A: 927,     # FactorE m11 -> [927, 927, 927, 927]
}
EXPECT_FACTOR_RECORDS = {                # base -> the FULL final Y row, which must be MONOTONE
    0xD27BC: [430, 430, 430, 877], 0xD27D0: [431, 431, 431, 877],
    0xD27F8: [927, 927, 927, 927], 0xD280C: [927, 927, 927, 927],
}
EXPECT_LEVER_C = (0xC63A0, 2048)
EXPECT_CARRIED = (0x454FE, 0x65B5)       # `br 0x455C4` -- the cond nibble only

# 🛑 MUST REMAIN BYTE-STOCK. Asserted BY VALUE, which is the whole point of this file.
EXPECT_STOCK_HALFWORDS = {
    0xC643E: 1536, 0xC6440: 2048, 0xC6442: 1024, 0xC6444: 512, 0xC6446: 512,   # all five arms
    0xC6158: 512,                                                              # ceiling fallback
}
EXPECT_STOCK_BYTES = {0x3AA96: 0xC5}     # the gate: gp-0x683c, ZERO writers ⇒ V72 is UNGATED
EXPECT_STOCK_RECORDS = {                 # base -> full Y row, must equal STOCK
    0xD2AEC: [2305, 2304, 2149, 1948],   # gain_B mode-10  50 km/h
    0xD2B28: [2151, 2151, 2049, 1947],   # gain_B mode-10 100 km/h
    0xC6A90: [2664, 2664, 2243, 1436],   # gain_A          50 km/h
    0xC6AA4: [2560, 2560, 2145, 1331],   # gain_A         100 km/h
    0xD2A88: [3072, 3072, 2322, 1536],   # 🛑 gain_B MODE 11 rec0 -- NOT a speed record
    0xD2A9C: [3072, 3072, 2322, 1536],   # 🛑 gain_B MODE 12 rec0 -- NOT a speed record
    0xD27E4: [0, 234, 429, 908],         # FactorC mode 12
    0xD2820: [0, 140, 539, 927],         # FactorE mode 12
}
EXPECT_SAR_SITES = {0x3AB76: 0x32AA, 0x3AC20: 0x42AA}       # both `sar 0xa` -- V62's lever, NOT here
EXPECT_CEILING = (0xD209C, [2, 300, 800, 512, 1024, 0])     # count, X[0..1], Y[0..1], terminator
EXPECT_CEILING_FLOAT = (0xC6554, "0000964300004844")        # 300.0f, 800.0f -- the lockstep twin
EXPECT_ROLE_TABLE = (0xC4124, [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0])
EXPECT_CAVE = (0xC4B34, "203e1000e4375d96a932a205483a6232a605443a24373094a6326132be057f32ae05423a"
                        "e4374195a932a205413ac33a8437edeac636070007314437ecea2436e8ea7f00")
EXPECT_CAVE_HOOK = (0x55C0E, 4)
# The three probed cells: (firmware readers, firmware writers, writer addresses, the cave's mnemonic)
EXPECT_PROBE_CENSUS = {
    0x69A4: (3, 1, [0x355C6], "ld.hu"),
    0x6BD0: (5, 3, [0x34730, 0x34744, 0x34752], "ld.h"),
    0x6AC0: (26, 4, [0x41820, 0x41832, 0x41A8C, 0x41AAC], "ld.hu"),
}
EXPECT_LEVER_C_READER = 0x381AC
CRC_BLOCKS_MOVED = [0xC4FFC, 0xC6FFC, 0xD2FFC]
CRC_SKIPPED_BLOCK = (0xC5000, 0xC5FFC)   # the V40 ignition-brick precedent -- nothing may land here

FAILS: list[str] = []


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def rec_y(b, base):
    return list(struct.unpack_from("<4h", b, base + 0x0A))


def check(ok, msg, detail=""):
    if ok:
        print(f"    ✅ {msg}")
    else:
        FAILS.append(f"{msg}  {detail}")
        print(f"    🛑 FAIL: {msg}  {detail}")
    return ok


def cross_check_against_builder():
    """🛑 The two independent statements of the spec must agree. A typo in EITHER file fails here."""
    print("\n  CROSS-CHECK -- this file's literals vs builds/v50_v79/build_v72_tva.py's tables:")
    ok = True
    ok &= check({b: y for b, (y, _l) in V72.LEVER_A_FINAL_Y.items()} == EXPECT_LEVER_A,
                "LEVER A: the builder's final Y rows equal this file's literals")
    ok &= check({a: n for a, (_o, n, _l) in V72.LEVER_B.items()} == EXPECT_LEVER_B,
                "LEVER B: the builder's cells equal this file's literals",
                f"builder={ {hex(a): n for a, (_o, n, _l) in V72.LEVER_B.items()} }")
    ok &= check((V72.DAMP_WEIGHT_ADDR, V72.DAMP_WEIGHT_NEW) == EXPECT_LEVER_C,
                "LEVER C: address and value agree")
    ok &= check(len(V72.LEVER_B) == 10, "LEVER B is 10 cells = 20 bytes",
                f"{len(V72.LEVER_B)} cells")
    ok &= check(bytes.fromhex(EXPECT_CAVE[1]) == V72.build_cave()[0],
                "the cave hex equals the one the builder emits, byte for byte")
    ok &= check((V72.A_THRESHOLD, V72.A2_THRESHOLD, V72.D_THRESHOLD, V72.D_NEG_THRESHOLD,
                 V72.R_THRESHOLD) == (512, 1024, 64, -65, 512),
                "the probe thresholds are (512, 1024, 64, -65, 512)")
    ok &= check(all(len(set(y)) == 1 for y in EXPECT_LEVER_A.values()),
                "LEVER A is FLAT on all four records ⇒ it doses the WHOLE rate axis")
    return ok


def verify(img: bytes, stock: bytes, v70: bytes, label: str):
    print(f"\n{'=' * 100}\n  VERIFYING {label}\n  SHA256 {hashlib.sha256(img).hexdigest()}")
    check(len(img) == 0x100000, "the image is exactly 1 MiB", f"len={len(img)}")

    print("\n  LEVER A -- both rate lanes, PLATEAU ONLY (Y[0]/Y[1]; Y[2]/Y[3] must be STOCK):")
    for base, want in EXPECT_LEVER_A.items():
        got = rec_y(img, base)
        check(got == want, f"0x{base:05X} Y row == {want}", f"got {got}")
        check(len(set(got)) == 1,
              f"0x{base:05X} Y row is FLAT ⇒ the WHOLE rate axis is dosed, which is what reproduces "
              "a scalar arm", f"got {got}")
        check(list(struct.unpack_from("<4h", img, base + 0x02)) ==
              list(struct.unpack_from("<4h", stock, base + 0x02)),
              f"0x{base:05X} X row is STOCK -- only Y values may move")

    print("\n  LEVER B -- the base-assist damper opened at creep (V47's exact bytes):")
    for addr, want in EXPECT_LEVER_B.items():
        check(u16(img, addr) == want, f"0x{addr:05X} == {want}", f"got {u16(img, addr)}")
    for base, want in EXPECT_FACTOR_RECORDS.items():
        got = rec_y(img, base)
        check(got == want, f"0x{base:05X} Y row == {want}", f"got {got}")
        check(all(b >= a for a, b in zip(got, got[1:])),
              f"0x{base:05X} Y row is MONOTONE non-decreasing -- a mid-schedule dip is a defect",
              f"got {got}")
    # 🛑 SCOPED: the region V72 NEWLY OPENS is speed < FactorC's X[0] = 35 km/h, where stock is a
    # HARD ZERO. That is where the no-clip guarantee must hold. A blanket "max < 512" is false above
    # ~110 km/h -- and false on STOCK too -- so it cannot be a V72 requirement.
    creep = V72.damper_authority(img, 10, 0, 0)
    opened = max(V72.damper_authority(img, m, v, r) for m in (10, 11)
                 for v in range(0, V72.FACTORC_ONSET_COUNTS + 1, 32) for r in range(0, 4001, 25))
    grid_all = [(m, v, r) for m in (10, 11) for v in range(0, 9001, 64) for r in range(0, 4001, 50)]
    peak = max(V72.damper_authority(img, m, v, r) for m, v, r in grid_all)
    peak_stock = max(V72.damper_authority(stock, m, v, r) for m, v, r in grid_all)
    check(opened < EXPECT_CEILING[1][3],
          f"delivered authority {creep} at creep / {opened} max over the OPENED region (< 35 km/h) "
          f"stays under the ceiling FLOOR {EXPECT_CEILING[1][3]} => no saturation, no hard "
          "nonlinearity inside the loop")
    check(peak == peak_stock,
          f"V72 does not raise the GLOBAL peak authority ({peak} == stock's {peak_stock}) -- it "
          "opens the low-speed region without adding authority anywhere else")

    print("\n  LEVER C -- the damper's own weight:")
    check(u16(img, EXPECT_LEVER_C[0]) == EXPECT_LEVER_C[1],
          f"0x{EXPECT_LEVER_C[0]:05X} == {EXPECT_LEVER_C[1]}", f"got {u16(img, EXPECT_LEVER_C[0])}")
    try:
        _n, readers = V72.assert_lever_c_single_reader(img)
        check([a for a, _r in readers] == [EXPECT_LEVER_C_READER],
              f"tp+0x73A0 has EXACTLY ONE reader, 0x{EXPECT_LEVER_C_READER:05X}, and ZERO writers "
              "⇒ no monitor can be checking it")
    except AssertionError as exc:
        check(False, "LEVER C single-reader census", str(exc))

    print("\n  CARRIED -- 0x454FE (🛑 FALSIFIED for the 7.79 Hz ratchet; carried for V42's symptom):")
    check(u16(img, EXPECT_CARRIED[0]) == EXPECT_CARRIED[1],
          f"0x{EXPECT_CARRIED[0]:05X} == 0x{EXPECT_CARRIED[1]:04X} (`br 0x455C4`)",
          f"got 0x{u16(img, EXPECT_CARRIED[0]):04X}")
    check(img[EXPECT_CARRIED[0] + 1] == 0x65,
          "the branch's HIGH byte is untouched ⇒ the DISPLACEMENT is provably unchanged")

    print("\n  🛑 MUST REMAIN BYTE-STOCK -- asserted BY VALUE, not by span:")
    for addr, want in EXPECT_STOCK_HALFWORDS.items():
        check(u16(img, addr) == want == u16(stock, addr),
              f"0x{addr:05X} == {want} (stock)", f"got {u16(img, addr)}")
    for addr, want in EXPECT_STOCK_BYTES.items():
        check(img[addr] == want == stock[addr],
              f"0x{addr:05X} == 0x{want:02X} (stock) -- the gate is the DEAD cell ⇒ V72 is UNGATED",
              f"got 0x{img[addr]:02X}")
    for addr, want in EXPECT_SAR_SITES.items():
        check(u16(img, addr) == want == u16(stock, addr),
              f"0x{addr:05X} == 0x{want:04X} -- `sar 0xa`, V62's lever is NOT carried",
              f"got 0x{u16(img, addr):04X}")
    for base, want in EXPECT_STOCK_RECORDS.items():
        got = rec_y(img, base)
        check(got == want == rec_y(stock, base), f"0x{base:05X} Y row == {want} (stock)", f"got {got}")
    cbase, cwant = EXPECT_CEILING
    cgot = [u16(img, cbase + 2 * j) for j in range(6)]
    check(cgot == cwant,
          f"0x{cbase:05X} damper ceiling == {cwant} -- LOCKSTEP-checked, DTC 0x1d on mismatch",
          f"got {cgot}")
    fbase, fhex = EXPECT_CEILING_FLOAT
    check(img[fbase:fbase + 8].hex() == fhex,
          f"0x{fbase:05X} the ceiling's FLOAT twin is stock (300.0f, 800.0f)")
    rbase, rwant = EXPECT_ROLE_TABLE
    rgot = list(img[rbase:rbase + len(rwant)])
    check(rgot == rwant,
          f"0x{rbase:05X} role table == {rwant}", f"got {rgot}")
    check(not any(r in (6, 7) for r in rgot),
          "no slot carries role 6 or 7 ⇒ gp-0x67ac cannot read 1 ⇒ the aggregator's FULL 11-lane "
          "branch is the only reachable one and NO lever on this build is vacuous")

    print("\n  THE PROBE -- the cave, its re-disassembly, and RAM ownership:")
    base, want_hex = EXPECT_CAVE
    got = bytes(img[base:base + 68])
    check(got.hex() == want_hex, "the 68-byte cave matches, byte for byte", f"got {got.hex()}")
    check(img[EXPECT_CAVE_HOOK[0]:EXPECT_CAVE_HOOK[0] + 4] ==
          v70[EXPECT_CAVE_HOOK[0]:EXPECT_CAVE_HOOK[0] + 4],
          f"the hook @0x{EXPECT_CAVE_HOOK[0]:05X} is byte-identical to the base")
    redis = V72.redisassemble_cave(got, base)
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    check(len(stores) == 1 and stores[0][1].startswith("st.b"),
          "the cave contains EXACTLY ONE store, and it is an st.b to the CAN-330 payload byte",
          f"got {stores}")
    ldh = [(a, m) for a, _r, m in redis if m.startswith("ld.h ")]
    check(len(ldh) == 1 and ldh[0][1] == "ld.h -27600[r4],r6",
          "the damper rung is `ld.h -0x6bd0[gp],r6` -- opcode 0x39, NOT the st.h twin 0x3B",
          f"got {ldh}")
    hw1 = u16(img, base + 20)          # ⚠ offset 20, not 16: bit5's rung shifted the damper load
    check((hw1 >> 5) & 0x3F == 0x39,
          f"the damper rung's opcode field is 0x39; the real st.h @0x34730 is 0x3B and carries the "
          "SAME register and displacement",
          f"got 0x{(hw1 >> 5) & 0x3F:02X}")
    check(got[18:20] == bytes.fromhex("443a"),
          "offset 18 is `add 0x4,r7` ⇒ bit5 (`a` >= 1024) IS present, and bit5 => bit6 is structural",
          f"got {got[18:20].hex()}")
    for sar_off in (8, 40):
        check(got[sar_off:sar_off + 2] == bytes.fromhex("a932") and
              got[sar_off + 2:sar_off + 4] == bytes.fromhex("a205"),
              f"offset {sar_off}: `sar 0x9,r6` is IMMEDIATELY followed by its `be +4` -- flag "
              "liveness is load-bearing, and anything between them would read STALE flags",
              f"got {got[sar_off:sar_off + 4].hex()}")
    cave_span = range(base, base + 68)
    for disp, (nr, nw, writers, want_mnem) in EXPECT_PROBE_CENSUS.items():
        hits = V64.gp_access_census(img, disp)
        rd = [h for h in hits if h[0] not in cave_span and h[1].startswith("ld.")]
        wr = [h for h in hits if h[0] not in cave_span and not h[1].startswith("ld.")]
        cave = [h for h in hits if h[0] in cave_span]
        check(len(rd) == nr and [a for a, _m, _r in wr] == writers,
              f"gp-0x{disp:04x} firmware census is {nr}r / {nw}w at {[hex(w) for w in writers]}",
              f"got {len(rd)}r / {len(wr)}w at {[hex(a) for a, _m, _r in wr]}")
        check(len(cave) == 1 and cave[0][1] == want_mnem and cave[0][2] == 6,
              f"gp-0x{disp:04x}: the cave READS it exactly once (`{want_mnem} ...,r6`) and WRITES "
              "it never", f"got {[(hex(a), m, r) for a, m, r in cave]}")
    for stale in (0x6ADA, 0x6ADC, 0x671D, 0x67FA):
        check(not [h for h in V64.gp_access_census(img, stale) if h[0] in cave_span],
              f"the cave does not touch gp-0x{stale:04x} (retired by V72)")

    print("\n  THE DELIVERED MULTIPLIERS, re-derived from THIS image:")
    grid = [(v, r) for v in range(0, 6401, 64) for r in range(0, 3001, 50)]
    # 🛑 NO POINTWISE BOUND IS ASSERTED. `V72 <= V62` and `V72 <= V70` are BOTH FALSE for this
    # spec (V72's r24 reaches 3.414x at rate 3000 where V62 is 2.000x). Earlier cuts of this file
    # asserted them; they are removed deliberately, and the grind-#2 exposure is carried as a
    # STATED RISK in the build note instead of as an arithmetic bound.
    hi24 = LM.effective(img, "r24", 0, 3000, False) / LM.effective(stock, "r24", 0, 3000, False)
    hi26 = LM.effective(img, "r26", 0, 3000, False) / LM.effective(stock, "r26", 0, 3000, False)
    check(hi24 > 2.0 and abs(hi26 - 0.25) < 0.01,
          f"the two-lane rule row: r24 high-rate {hi24:.3f}x AND r26 high-rate {hi26:.3f}x -- "
          "V67/V68's exact row, the only 3.4x-r24 row with no creep grind #2 in six builds",
          f"got ({hi24:.3f}, {hi26:.3f})")
    hwy = [(v, r, ln) for v, r in grid if v >= 3200 for ln in ("r24", "r26")
           if LM.effective(img, ln, v, r, False) != LM.effective(stock, ln, v, r, False)]
    check(not hwy, "EXACTLY 1.000000x on BOTH lanes at every rate, at and above 50 km/h", f"{hwy[:4]}")
    ungated = [(v, r, ln) for v, r in grid for ln in ("r24", "r26")
               if LM.effective(img, ln, v, r, True) != LM.effective(img, ln, v, r, False)]
    check(not ungated, "ENGAGED == MANUAL exactly ⇒ V72 is UNGATED (the disclosed cost)", f"{ungated[:4]}")
    # ★★ THE ASSERTION THAT MATTERS: V67/V68's ENGAGED multipliers reproduced at 0 and 10 km/h, at
    # EVERY rate index. A FLAT record is exactly what a scalar arm delivers.
    v67_path = plain_image_path("_v67_plain_image.bin")
    if v67_path.exists():
        v67 = v67_path.read_bytes()
        for kmh, vc in ((0, 0), (10, 640)):
            for lane in ("r24", "r26"):
                bad = []
                for r in range(0, 3001, 5):
                    g = LM.effective(img, lane, vc, r, False) / LM.effective(stock, lane, vc, r, False)
                    w = LM.effective(v67, lane, vc, r, True) / LM.effective(stock, lane, vc, r, True)
                    if abs(g - w) > 1e-12:
                        bad.append((r, round(g, 6), round(w, 6)))
                show = [LM.effective(img, lane, vc, r, False) /
                        LM.effective(stock, lane, vc, r, False) for r in (0, 400, 1400, 3000)]
                check(not bad,
                      f"{kmh:>2} km/h {lane} == V67/V68 ENGAGED at ALL 601 rate indices "
                      f"({' / '.join(f'{x:.3f}' for x in show)})", f"mismatches {bad[:4]}")
    else:
        check(False, "the V67 reference image is present", "MISSING -- cannot verify the reproduction")

    print("\n  CRC:")
    nbad = walk_all_blocks(img, verbose=False) if _accepts_verbose() else walk_all_blocks(img)
    check(nbad == 0, "the full bootloader CRC chain: 50/50 blocks PASS", f"{nbad} mismatch(es)")
    # 🛑 EXACTLY these three trailers, and no others. Enumerated over EVERY trailer the chain walks,
    # so a fourth block moving behind a recomputed checksum cannot pass unnoticed.
    all_trailers = sorted({t for t in range(V72.START, 0x100000, 0x1000) if (t & 0xFFF) == 0}
                          | set(CRC_BLOCKS_MOVED))
    moved = sorted(t for t in range(V72.START, 0x100000 - 3)
                   if (t & 0xFFF) == 0xFFC and img[t:t + 4] != v70[t:t + 4])
    check(moved == sorted(CRC_BLOCKS_MOVED),
          f"EXACTLY the MAIN/CAL/0xD2000 trailers moved: {[hex(t) for t in CRC_BLOCKS_MOVED]}",
          f"got {[hex(t) for t in moved]} (scanned {len(all_trailers)} candidate offsets)")
    check(all(not (CRC_SKIPPED_BLOCK[0] <= a < CRC_SKIPPED_BLOCK[1])
              for a in list(EXPECT_LEVER_B) + list(EXPECT_LEVER_A) +
              [EXPECT_LEVER_C[0], EXPECT_CARRIED[0], EXPECT_CAVE[0]]),
          f"no edit lands in [0x{CRC_SKIPPED_BLOCK[0]:05X},0x{CRC_SKIPPED_BLOCK[1]:05X}) -- the "
          "CRC-SKIPPED block with the V40 ignition-brick precedent")

    print("\n  DIFF ACCOUNTING vs the base:")
    d = [i for i in range(V72.START, V72.END) if img[i] != v70[i]]
    crc_only = {t + k for t in CRC_BLOCKS_MOVED for k in range(4)}
    f = [i for i in d if i not in crc_only]
    owned = set(range(*(EXPECT_CAVE[0], EXPECT_CAVE[0] + 68))) | \
        {b + 0x0A + k for b in EXPECT_LEVER_A for k in range(8)} | \
        {a + k for a in EXPECT_LEVER_B for k in (0, 1)} | \
        {EXPECT_LEVER_C[0], EXPECT_LEVER_C[0] + 1} | {EXPECT_CARRIED[0]}
    stray = [i for i in f if i not in owned]
    check(not stray, f"all {len(f)} functional bytes vs the base are attributable to V72's own "
                     f"edits ({len(d) - len(f)} CRC bytes)", f"stray {[hex(x) for x in stray[:8]]}")


def _accepts_verbose():
    import inspect
    return "verbose" in inspect.signature(walk_all_blocks).parameters


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?", default=None)
    ap.add_argument("--rwd", default=None)
    args = ap.parse_args()

    stock = Path(stock_fw_path("code.bin")).read_bytes()
    v70 = Path(plain_image_path("_v70_plain_image.bin")).read_bytes()

    if not cross_check_against_builder():
        print("\n🛑 THE TWO STATEMENTS OF THE SPEC DISAGREE. Nothing below can be trusted.")
        return 1

    if args.rwd:
        rwd = Path(args.rwd).read_bytes()
        FF.assert_x31_checksum(rwd, "the .rwd under test")
        info = parse_x31(rwd)
        decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
        img = bytearray(v70)
        img[V72.START:V72.END] = bytes(info["encs"][0]).translate(decode)
        verify(bytes(img), stock, v70, f"{args.rwd} (decoded payload)")
    else:
        p = Path(args.image) if args.image else Path(plain_image_path("_v72_plain_image.bin"))
        verify(p.read_bytes(), stock, v70, str(p))

    print("\n" + "=" * 100)
    if FAILS:
        print(f"  🛑 {len(FAILS)} CHECK(S) FAILED:")
        for f in FAILS:
            print(f"     - {f}")
        return 1
    print("  ✅ V72 VERIFIED. Every lever, every MUST-REMAIN-STOCK site, the cave and its")
    print("     re-disassembly, the probe census, the delivered multipliers and the CRC chain.")
    print("  🛑 Verification is not authorisation. Flash only on the operator's explicit")
    print("     instruction, naming the file and the bus.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
