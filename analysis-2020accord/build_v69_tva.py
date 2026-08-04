#!/usr/bin/env python3
"""V69 -- revert the LKAS gate, shape Honda's own low-speed rate-gain surface.

Full rationale, evidence and both gates: `docs/V69-DESIGN.md`. This file is the executable
version of that spec and re-derives every load-bearing number from the image.

THE PROBLEM
-----------
Routes `4c`/`4e` (V68) captured the operator's highway lane-change vibration: `4e` seg 33
t = 51.3 s, an openpilot ALC right lane change at 25.93 m/s -- bar **1468 counts p-p**, 26-30 Hz
envelope 614 (20x the route median), lines at 28.12/28.51 Hz at prominence 100-107, while
**40-49 Hz reads 69 in the same window**. Not wheel order 2 (24.93 Hz) or 3 (37.40), not engine
order 1 (26.10) or 2 (52.20).

V67/V68's rate-lane arm is a FLAT scalar taken whenever the LKAS gate is open. Honda's stock
surface rolls off with speed (3072 -> 2151); the flat arm does not follow it, so the delivered
multiplier RISES with speed and peaks at highway -- 2.4383x, exactly where the symptom is:

    stock LERP  grind #1 (7.2 km/h) = 2622        arm 5244 => 2.000x
    stock LERP  highway  (110 km/h) = 2151        arm 5244 => 2.4383x

One scalar cannot serve both ends: 1.00x at highway needs 2172, which is 0.83x at grind #1 --
BELOW stock, i.e. V61 territory, and V61 made grind #1 WORSE.

THE DESIGN, AND WHY IT IS FORCED
--------------------------------
The gate branch at `0x3AC04-0x3AC0C` is `cmp`(2) + `be`(2) + `ld.hu`(4) + `br`(2) = **10 bytes,
fully packed between two other arms -- zero slack**, and it REPLACES the LERP rather than scaling
it. So speed shaping can only reach the engaged path if the gate is off. Composing "gated AND
speed-shaped" needs new instructions on the 1 kHz path -- a code cave, this kit's ONLY bricking
class (V24, V27, V48B all bricked the ECU). Rejected.

    V69 = V66's control path (gate reverted to the dead gp-0x683c, arm back to stock)
        + rec0/rec1 Y[0..1] doubled
        + two in-place probe immediates for build identity

★ THE HIGHWAY 1.000x IS STRUCTURAL, NOT TUNED. The lane-change point is 93.35 km/h = 5980 counts,
inside the cross-axis [3200, 6400] segment, so the interpolation there reads ONLY rec2 and rec3.
**Any edit confined to rec0/rec1 is exactly 1.000x at every speed >= 50 km/h, every rate, on every
axis scale.** It cannot drift with a re-tune. Asserted below by sweep, not by argument.

★ AND IT DOES NOT BET ON THE OPEN AXIS SCALE. The inner axis's counts-per-deg/s is [OPEN] (repo
runs 4.7121; the chain-direct alternative is 0.58901). V69 doubles the WHOLE flat [0,400] segment
instead of leaning on where a breakpoint falls, so its creep dose is 2.000x on BOTH scales.
"Design A" (`0xD2ABC` alone -> 7051) swings 2.00x -> 1.22x at grind #1 and is a bet on one scale;
it also peaks at **2.753x** at 10 km/h / 86 deg/s, and delivers only 1.1-1.5x at |rate| 16-32 deg/s
where V62's measured fix was LARGEST. Rejected on all three counts.
⚠ The price of scale-independence, stated: grind #1 and manual creep share the same speed cells, so
on scale B nothing separates them and manual creep is also 2.000x -- exactly the dose V62/V65 flew.

🛑🛑 THE EDIT-ORDER INVARIANT -- this one can make the car WORSE THAN STOCK.
Edits 1 and 2 are jointly safe and individually dangerous in one direction: writing
`0xC6446 = 512` while the gate stays repointed leaves the arm LIVE at 512, which is ~5x BELOW the
stock LERP, degrading engaged steering everywhere. Asserted as `arm == 512 => gate byte == 0xc5`.

🛑 THE NEIGHBOUR TRAP. Modes 10/11/12 interleave at stride 0x14 and **mode 11's and mode 12's
0 km/h records are BYTE-IDENTICAL to mode 10's**, with their 10 km/h records one count below. The
target byte pattern occurs THREE times within 40 bytes. Every cell here is addressed absolutely and
the neighbours are asserted unchanged; `diff_build_vs_stock.py` is span-based and would NOT catch a
stray hit.

Usage:  python build_v69_tva.py
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v66_tva as V66                # noqa: E402
import build_v67_tva as V67                # noqa: E402
import build_v68_tva as V68                # noqa: E402  (cave machinery + census helpers)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                               # noqa: E402

START, END = V68.START, V68.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
MAIN_BLOCK, CAL_BLOCK = V68.MAIN_BLOCK, V68.CAL_BLOCK
D2000_BLOCK = V68.D2000_BLOCK              # (0xD2000, 0xD2010) -- V60's falsified cells, must not move

# ---- the control-path reverts ------------------------------------------------------------------
REPOINT_ADDR = V67.REPOINT_ADDR            # 0x3AA94  ld.bu -0x????[gp],r15
REPOINT_BYTE = V67.REPOINT_BYTE            # 0x3AA96  the one byte V67 moved
GATE_V68, GATE_STOCK = 0xFB, 0xC5          # gp-0x6806 (live)  vs  gp-0x683c (DEAD, 0 writers)
ARM_ADDR = V67.ARM_ADDR                    # 0xC6446
ARM_V68, ARM_STOCK = 5244, 512

# ---- the surface edit: rec0 and rec1, Y[0] and Y[1], each EXACTLY doubled -----------------------
# Y lives at record+0x0A (count @+0x00, X @+0x02) -- from the firmware's own accessor arithmetic.
REC0, REC1 = 0xD2A74, 0xD2AB0              # 0 km/h and 10 km/h, mode 10
SURFACE = (
    (REC0 + 0x0A, 3072, 6144, "rec0 (0 km/h)  Y[0]"),
    (REC0 + 0x0C, 3072, 6144, "rec0 (0 km/h)  Y[1]"),
    (REC1 + 0x0A, 2561, 5122, "rec1 (10 km/h) Y[0]"),
    (REC1 + 0x0C, 2561, 5122, "rec1 (10 km/h) Y[1]"),
)
# Records that MUST NOT move. mode 11/12 rec0 are byte-identical to mode 10's -- the neighbour trap.
NEIGHBOURS = (0xD2A88, 0xD2A9C, 0xD2AC4, 0xD2AD8, 0xD2B00, 0xD2B14, 0xD2B3C, 0xD2B50)
UNTOUCHED_RECS = (0xD2AEC, 0xD2B28)        # mode-10 50 and 100 km/h -- the structural highway 1.000x

CROSS_X_ADDR = 0xC6010                     # (0, 640, 3200, 6400) counts, 64.0625 counts/km/h

# ---- the probe: two in-place immediates, no new instruction -------------------------------------
LIVE_IMM_V69 = 0x80                        # bit7 liveness, bit3 CLEAR   (V68 emits 0x88)
DETECT_LVL_V69 = 0                         # bit4 rung `cmp 0x0,r6` => blt never taken => bit4 == 1

TAG = ("LKAS-4x-mss0-decouple0xC646C-ratelane-SPEEDSHAPED-gateREVERTED-"
       "gainB-rec0rec1-x2-can330byte4")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V69-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v69_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def rec_of(buf, addr):
    return (list(struct.unpack_from("<4H", buf, addr + 0x02)),
            list(struct.unpack_from("<4H", buf, addr + 0x0A)))


# ---- the LERP, mirroring the decompiled integer arithmetic --------------------------------------
def _lerp(x, xs, ys):
    """FUN_0003ad74 / the inline LERP at 0x3ABB2-0x3ABF8. FLAT outside; `divq` truncates to zero."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(len(xs) - 1):
        if x < xs[i + 1]:
            num = (ys[i + 1] - ys[i]) * (x - xs[i])
            q = abs(num) // (xs[i + 1] - xs[i])
            return ys[i] + (q if num >= 0 else -q)
    return ys[-1]


def gain_q10(buf, speed_counts, axis_counts):
    recs = [rec_of(buf, a) for a in (REC0, REC1, 0xD2AEC, 0xD2B28)]
    cross = list(struct.unpack_from("<4h", buf, CROSS_X_ADDR))
    k = max(cross[0], min(speed_counts, cross[-1]))
    xs = [_lerp(k, cross, [recs[i][0][j] for i in range(4)]) for j in range(4)]
    ys = [_lerp(k, cross, [recs[i][1][j] for i in range(4)]) for j in range(4)]
    idx = axis_counts if 0 <= axis_counts < 13001 else 0     # the fold @0x3AAC8/0x3AACC
    return _lerp(idx, xs, ys)


def build():
    print(__doc__)
    src = Path(plain_image_path("_v68_plain_image.bin"))
    v68 = bytearray(src.read_bytes())
    print("=" * 102)
    print(f"SOURCE: {src}\n  SHA256 {hashlib.sha256(bytes(v68)).hexdigest()}")

    # ---- gate the SOURCE before touching it -----------------------------------------------------
    assert len(v68) == 0x100000, "source image is not 1 MiB"
    assert v68[REPOINT_BYTE] == GATE_V68, \
        f"source gate byte is 0x{v68[REPOINT_BYTE]:02X}, expected V68's 0x{GATE_V68:02X}"
    assert u16(v68, ARM_ADDR) == ARM_V68, f"source arm is {u16(v68, ARM_ADDR)}, expected {ARM_V68}"
    for addr, old, _new, name in SURFACE:
        assert u16(v68, addr) == old, f"{name} @0x{addr:05X} is {u16(v68, addr)}, expected {old}"
    role = list(v68[0xC4124:0xC4124 + 11])
    assert role == [0, 0, 5, 0, 5, 5, 0, 0, 0, 5, 0], f"role table drifted: {role}"
    assert not any(r in (6, 7) for r in role), \
        "a slot carries role 6 or 7 -- gp-0x67ac becomes LIVE and the rate lanes can drop out"
    assert bytes(v68[0xC6564:0xC6564 + 40]) == bytes(40), \
        "0xC6564 is no longer 40 zero bytes -- r26 may no longer be inert"
    print("  source gates: gate byte 0xFB, arm 5244, surface stock, role table "
          f"{role}, 0xC6564 = 40 zero bytes  ✅")

    code = bytearray(v68)

    # ---- EDIT 1+2: the control path reverts to V66's --------------------------------------------
    print("\n  EDIT 1-2 -- THE CONTROL PATH REVERTS (this is what lets speed shaping reach the "
          "engaged lane):")
    code[REPOINT_BYTE] = GATE_STOCK
    struct.pack_into("<H", code, ARM_ADDR, ARM_STOCK)
    print(f"    0x{REPOINT_BYTE:05X}  0x{GATE_V68:02X} -> 0x{GATE_STOCK:02X}   "
          f"ld.bu -0x6806[gp],r15 -> -0x683c   (the DEAD cell: 0 writers image-wide)")
    print(f"    0x{ARM_ADDR:05X}  {ARM_V68} -> {ARM_STOCK}       r24's LKAS arm, back to stock")
    # 🛑🛑 THE EDIT-ORDER INVARIANT. 512 is ~5x BELOW the stock LERP; live, it is worse than stock.
    assert not (u16(code, ARM_ADDR) == ARM_STOCK and code[REPOINT_BYTE] != GATE_STOCK), \
        "arm == 512 while the gate is STILL repointed -- that arm is LIVE and ~5x below the stock " \
        "LERP. Refusing to emit."
    print("    ✅ edit-order invariant asserted: arm == 512 ⟹ gate byte == 0xc5")
    assert bytes(code[REPOINT_ADDR:REPOINT_ADDR + 4]) == bytes.fromhex("847fc597"), \
        "the reverted gate load is not the stock `ld.bu -0x683c[gp],r15`"

    # ---- EDIT 3-6: the surface --------------------------------------------------------------
    print("\n  EDIT 3-6 -- THE SURFACE. Every halfword is EXACTLY 2x the one it replaces:")
    for addr, old, new, name in SURFACE:
        before = struct.pack("<H", old)
        struct.pack_into("<H", code, addr, new)
        print(f"    0x{addr:05X}  {old:5d} -> {new:5d}   bytes {before.hex(' ')} -> "
              f"{struct.pack('<H', new).hex(' ')}   {name}")
        assert new == 2 * old, f"{name} is not an exact doubling"

    # ---- EDIT 7-8: the probe immediates -----------------------------------------------------
    print("\n  EDIT 7-8 -- THE PROBE (two in-place immediates; NO new instruction, NO cave growth):")
    saved_imm, saved_cells = V68.LIVE_IMM, V68.CELLS
    try:
        V68.LIVE_IMM = LIVE_IMM_V69
        V68.CELLS = tuple(
            (d, b, n, k, (DETECT_LVL_V69 if d == V68.DETECT_DISP else lv), w)
            for d, b, n, k, lv, w in saved_cells)
        cave_bytes, cave_listing = V68.build_cave()
    finally:
        V68.LIVE_IMM, V68.CELLS = saved_imm, saved_cells
    assert len(cave_bytes) <= len(V55.CAVE_BYTES), "cave overruns the proven extent"
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        cave_bytes + b"\xff" * (len(V55.CAVE_BYTES) - len(cave_bytes))
    cave_listing = [
        (a, r, ("movea 0x80,r0,r7    ; bit7 LIVENESS, bit3 CLEAR  *** V69 BUILD CLASS ***"
                if a == CAVE_BASE else
                t.replace(">= 0", "always -> bit4 CONSTANT 1  *** V69 BUILD CLASS ***")))
        for a, r, t in cave_listing]
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    print(f"    cave {len(cave_bytes)}B of the proven {len(V55.CAVE_BYTES)}B "
          f"({len(V55.CAVE_BYTES) - len(cave_bytes)} spare)")
    assert code[CAVE_BASE + 2] == LIVE_IMM_V69, "the liveness immediate is not 0x80"
    assert bytes(code[V68.HOOK_ADDR:V68.HOOK_ADDR + 4]) == \
        bytes(v68[V68.HOOK_ADDR:V68.HOOK_ADDR + 4]), "the hook must stay byte-identical"

    # ---- STRUCTURAL GATES ------------------------------------------------------------------
    print("\n  GATES:")
    for a in NEIGHBOURS:
        assert bytes(code[a:a + 20]) == bytes(v68[a:a + 20]), \
            f"neighbour record 0x{a:05X} MOVED -- the byte-pattern trap fired"
    print(f"    ✅ all {len(NEIGHBOURS)} mode-11/12 neighbour records byte-identical "
          "(mode 11/12 rec0 are byte-IDENTICAL to mode 10's -- the pattern occurs 3x in 40 bytes)")
    for a in UNTOUCHED_RECS:
        assert bytes(code[a:a + 20]) == bytes(v68[a:a + 20]), f"mode-10 rec 0x{a:05X} moved"
    print("    ✅ mode-10 50 km/h and 100 km/h records byte-identical ⇒ the highway 1.000x is "
          "STRUCTURAL")
    assert bytes(code[D2000_BLOCK[0]:D2000_BLOCK[1]]) == \
        bytes(v68[D2000_BLOCK[0]:D2000_BLOCK[1]]), "V60's falsified slew-blend cells MOVED"
    print(f"    ✅ 0x{D2000_BLOCK[0]:05X}-0x{D2000_BLOCK[1]:05X} (V60's falsified cells) unchanged")
    assert u16(code, V57.PRIVATE_ADDR) == u16(v68, V57.PRIVATE_ADDR), "V57's private cell moved"
    for a, want in V68.SAR_SITES_STOCK:
        assert u16(code, a) == want, f"sar site 0x{a:05X} is not stock"
    print("    ✅ all three `sar` sites stock; V57's private gain cell carried")

    # ---- THE STRUCTURAL HIGHWAY CLAIM, PROVEN BY SWEEP -------------------------------------
    bad = [(v, r) for v in range(3200, 6401, 32) for r in range(0, 3001, 25)
           if gain_q10(code, v, r) != gain_q10(v68, v, r)]
    assert not bad, f"the surface edit changed a >=50 km/h operating point: {bad[:4]}"
    print(f"    ✅ SWEEP: {len(range(3200, 6401, 32)) * len(range(0, 3001, 25))} points at "
          "speed >= 50 km/h are byte-identical to stock ⇒ highway is EXACTLY 1.000x, all rates")

    # ---- THE DELIVERED MULTIPLIER ---------------------------------------------------------
    print("\n  DELIVERED MULTIPLIER (V69 vs stock LERP), low rate axis:")
    print("      km/h  " + "".join(f"{k:>8}" for k in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93)))
    row = []
    for kmh in (0, 5, 7.2, 10, 15, 20, 30, 40, 50, 93):
        sc = int(kmh * 64.0625)
        row.append(gain_q10(code, sc, 100) / gain_q10(v68, sc, 100))
    print("      mult  " + "".join(f"{x:8.3f}" for x in row))
    mx = max(gain_q10(code, v, r) / gain_q10(v68, v, r)
             for v in range(0, 6401, 64) for r in range(0, 3001, 25))
    assert mx <= 2.001, f"the surface exceeds 2.000x somewhere ({mx:.3f}) -- GATE 2 bracket broken"
    print(f"    ✅ MAX multiplier anywhere = {mx:.3f}x ⇒ inside [stock 1.00x, V62/V65 2.00x], "
          "both flown flight-clean")

    # ---- CRC: THREE blocks. Generic, per build_v60's template. ----------------------------
    blocks = sorted({tuple(V53.owning_block(code, a))
                     for a in (REPOINT_BYTE, ARM_ADDR, CAVE_BASE, SURFACE[0][0], SURFACE[-1][0])})
    print(f"\n  CRC -- {len(blocks)} blocks move:")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")

    # ---- EXACT DIFF vs V68 ----------------------------------------------------------------
    diffs = [i for i in range(len(code)) if code[i] != v68[i]]
    crc_words = {b[1] + k for b in blocks for k in range(4)}
    functional = [d for d in diffs if d not in crc_words]
    print(f"\n  EXACT DIFF vs V68: {len(diffs)} bytes "
          f"({len(functional)} functional + {len(diffs) - len(functional)} CRC bookkeeping)")
    expect = ({REPOINT_BYTE, ARM_ADDR, ARM_ADDR + 1}
              | {a + k for a, _, _, _ in SURFACE for k in (0, 1)}
              | set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES))))
    stray = [d for d in functional if d not in expect]
    assert not stray, f"UNATTRIBUTED functional bytes: {[hex(x) for x in stray]}"
    for d in functional:
        where = ("gate byte" if d == REPOINT_BYTE else
                 "arm 0xC6446" if d in (ARM_ADDR, ARM_ADDR + 1) else
                 "cave" if CAVE_BASE <= d < CAVE_BASE + len(V55.CAVE_BYTES) else "surface")
        print(f"    0x{d:05X}  {v68[d]:02X} -> {code[d]:02X}   {where}")
    print("    ✅ zero unattributed functional bytes")

    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    # ---- ENCODE, then RE-RUN every gate on the DECODED READBACK --------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)
    rwd = encode_x31(info["headers"], info["blocks"], [bytes(code[START:END]).translate(encode)])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V69 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v68)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    print("\n  READBACK -- decoded from the .rwd and re-gated:")
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    assert dec[REPOINT_BYTE] == GATE_STOCK, "readback gate byte wrong"
    assert u16(dec, ARM_ADDR) == ARM_STOCK, "readback arm wrong"
    for addr, _old, new, name in SURFACE:
        assert u16(dec, addr) == new, f"readback {name} wrong"
    assert dec[CAVE_BASE + 2] == LIVE_IMM_V69, "readback liveness immediate wrong"
    for a in NEIGHBOURS:
        assert bytes(dec[a:a + 20]) == bytes(v68[a:a + 20]), "readback neighbour moved"
    nbad2 = walk_all_blocks(bytes(dec))
    assert nbad2 == 0, f"readback CRC chain FAILED: {nbad2} mismatching block(s)"
    print("    ✅ payload, gate byte, arm, all four surface halfwords, cave immediate,")
    print("       every neighbour record, and the full CRC chain -- all verified ON THE READBACK")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n" + "=" * 102)
    print(f"  V69 BUILT. 8 edits / {len(functional)} changed bytes, 3 CRC blocks, "
          "no cave growth, GATE 1 vacuous.")
    print("  🛑 SPEC: docs/V69-DESIGN.md §6 (the manual-feel cost) and §9 (what falsifies this).")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, hashlib.sha256(rwd).hexdigest()


if __name__ == "__main__":
    build()
