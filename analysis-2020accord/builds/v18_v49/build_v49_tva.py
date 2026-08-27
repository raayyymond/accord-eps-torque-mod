"""
builds/v18_v49/build_v49_tva.py -- V49 = V38 + the state-4 ratchet fix + a COLLOCATED TORQUE-RATE DAMPER made by
                     flipping FUN_0003a382's StageC derivative sign AND band-limiting it.

=======================================================================================================
🛑🛑🛑 FLASH GATE -- READ BEFORE EVEN THINKING ABOUT FLASHING 🛑🛑🛑
This build's DIRECTION (fixes the vibration vs makes it WORSE / bricks) depends on the runtime value of
the shared polarity byte gp-0x6752, which is EEPROM/NVM-resident and CANNOT be read from code.bin.
  * gp-0x6752 = +1  -> the flipped StageC term is DAMPING at 21.5 Hz  -> intended fix.
  * gp-0x6752 = -1  -> it is ANTI-DAMPING at 21.5 Hz -> WORSE, a V48B-class full-authority brick risk.
The default is +1 and a working power-steering car strongly implies +1, but that is an INFERENCE.
** DO NOT FLASH V49 until gp-0x6752 (abs 0xFEDF18AE) is confirmed = +1 by a read-only, at-rest RAM read. **
This script only BUILDS + verifies the artifact (study artifact). Flashing remains gated on an explicit
operator instruction naming the file + bus, AFTER the polarity confirmation.
=======================================================================================================

V49 IN ONE LINE
    Keep the 4x LKAS gain + the CONFIRMED state-4 ratchet fix. Turn FUN_0003a382's StageC term from a
    reinforcing (anti-damping) collocated torque-derivative into an OPPOSING (damping) one by flipping a
    single opcode bit (subr->sub @0x3a836), AND band-limit it to ~10 Hz (StageC pole 0xC644A 1024->64) so
    the flipped derivative adds damping at the ~21.5 Hz mode WITHOUT creating high-frequency anti-damping.

WHY (topology + closed-loop model, 2026-07-22; studies/models/eps_v49_a382_stagec_flip_model.py, disasm-exact)
    The 21.5 Hz vibration is a FIRMWARE/PLANT closed-loop mode (the openpilot bus command 0xE4 was proven
    to STRIP the resonance via its saturated slew limiter -> the comma is a passenger). The aggregator
    topology is COMPLETE (no missed dominant carrier). Every MAGNITUDE cut of a collocated carrier failed
    (V39 r24, V42 r26, V43/V46 a382 poles, V48A a382 uVar27 x0.25 -> all null): reducing a small
    anti-damping term toward zero does little. FUN_0003a382 StageC is a genuine collocated 1 kHz torque
    DERIVATIVE at UNITY gain (top-ranked 21.5 Hz carrier, never isolated). FLIPPING its sign is
    categorically different -- it ADDS damping (crosses past zero) instead of just shrinking anti-damping.
    Model (polarity +1): the flip moves the a382 loop factor Re from +0.63 (anti-damping) to damping,
    ~2-3.7x the change of the null V48A cut, in the correct direction.

WHY THE BAND-LIMIT IS PART OF THE EDIT (GATE 2 -- this is not optional)
    A derivative amplifies with frequency, so the BARE sign flip (pole left at unity 1024) helps at 21.5 Hz
    but CREATES new anti-damping at 55-140 Hz -- a GATE-2 failure, and given the unresolved 21.5-vs-78.6 Hz
    aliasing, a real brick risk. Lowering the StageC pole 0xC644A to 64 (corner ~10 Hz) rolls the derivative
    off above ~10 Hz: the closed-loop model is then DAMPING at 21.5 Hz AND has NO anti-damping at any swept
    frequency 1-140 Hz (GATE-2 CLEAN). Bonus: confining the effect to ~21.5 Hz means that IF the true mode
    is actually the 78.6 Hz alias, this edit is a NULL (safe), not a brick. (This is exactly V43's pole
    value, which alone -- without the flip -- was null; the flip is what makes the band-limit do something.)

THE THREE EDITS
    1. CODE, 1 byte, MAIN block:  0x454FE  0x65BA->0x65B5  (bne->br)  -- the CONFIRMED state-4 ratchet fix.
    2. CODE, 1 byte, MAIN block:  0x3a836  0x8E->0xAE (word 0x798E->0x79AE) -- subr r14,r15 -> sub r14,r15,
       i.e. StageC derivative (current-prev) -> (prev-current). V850 Format-I, no displacement/target: the
       ONLY change is the arithmetic sign. Verified against the stock word + re-decoded here.
    3. CAL, 1 halfword, CAL block: 0xC644A  1024->64  -- StageC EMA pole: unity -> ~10 Hz low-pass.

GATE 1 (RAM ownership): trivially clean -- no new RAM. Edit 2 reuses FUN_0003a382's own existing state
    (gp-0x3684 delay, gp-0x3680 accumulator); gp-0x6ad4 output has 1 writer + 1 reader and is NOT part of
    any int/float lockstep (no FUN_0006b9fa wrap) -- so nothing to desync. Edit 3 is a normal cal.
GATE 2 (closed-loop): PASSED for the flip+band-limit (pole 64) -- see studies/models/eps_v49_a382_stagec_flip_model.py.
    ⚠ CONDITIONAL on polarity +1 (the flash gate above) and on the single-resonance plant model; a second
    mechanical mode >50 Hz is not modeled (the band-limit is chosen partly to be robust to exactly that).

HONEST RESIDUAL: a382 is a MINORITY carrier (V48A's 75% cut was null), so even sign-correct + band-limited,
    V49 may be a PARTIAL cure, not a full one. It CANNOT brick at polarity +1 (sign-correct damping). If it
    is a partial cure with the mode confirmed at 21.5 Hz, the StageC pole can be raised (64->96->128) for
    more damping at the cost of re-checking the HF band.

CRC BLOCKS TOUCHED (2): MAIN 0xC4FFC (ratchet + StageC flip) + CAL 0xC6FFC (StageC pole). Same 2-block
    footprint as V43. Built on the exact on-car V38 baseline; cal+2-code-byte; study artifact, UNFLASHED.
=======================================================================================================
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

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V49 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks


START, END = 0x13000, 0x100000
V38_PLAIN = str(plain_image_path("_v38_plain_image.bin"))
V38_RWD = os.path.join(
    RWD_DIR,
    "39990-TVA,A160-V38-LKAS-4x-V37guards-softwall5120-float5-setpoint16384-0x13000-0x100000.rwd",
)
V38_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
V38_RWD_SHA256 = "c6fdb297635b43681d7692ebf86de2071bd687566bb96ff0ee06977cc4d4b990"
EXPECTED_HEADERS = [
    (b"#", [b"\x00"]),
    (b"?", [b"A1"]),
    (b"/", [b"39990-TVA-A110", b"39990-TVA,A160"]),
    (b"!", [b"001100121020", b"001100121020"]),
    (b"&", [b"BF109E"]),
    (b"%", [b"30"]),
]

V49_TAG = "LKAS-4x-V38base-ratchet-stageC-flip-damper-pole64-GATED-gp6752"
V49_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V49-{V49_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v49_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- EDIT 1: the CONFIRMED state-4 ratchet fix (V42 Change 1) -----------------------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA        # bne +198 -> 0x455c4
RATCHET_NEW_HW = 0x65B5          # br  +198 -> 0x455c4
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))    # ld.bu -0x67fa[gp],r12
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))        # cmp 0x4,r12

# ---- EDIT 2: flip StageC derivative sign -- subr r14,r15 -> sub r14,r15 -------------------------
# V850 Format-I reg-reg: word = (reg2<<11)|(opcode<<5)|reg1. SUBR opcode=0x0C, SUB opcode=0x0D.
#   subr r14,r15 = 0x798E : r15 = r14 - r15 = current - previous (forward derivative)
#   sub  r14,r15 = 0x79AE : r15 = r15 - r14 = previous - current (NEGATED derivative)
# Only opcode bit0 (word bit5 = byte0 bit5, 0x20) moves; reg1/reg2 unchanged. No displacement/target.
FLIP_ADDR = 0x3A836
FLIP_STOCK_HW = 0x798E
FLIP_NEW_HW = 0x79AE

# ---- EDIT 3: band-limit StageC (its EMA pole) -- unity -> ~10 Hz low-pass -----------------------
POLE_ADDR = 0xC644A
POLE_STOCK = 1024                # Q10 unity == pole disabled (unfiltered derivative)
POLE_NEW = 64                    # alpha 64/1024 = 0.0625, corner ~10 Hz -> GATE-2 clean (model)
POLE_SIBLING_ADDR = 0xC6450      # StageA pole -- MUST stay unity (we only band-limit StageC)
POLE_SIBLING_STOCK = 1024

MAIN_BLOCK = (0x13000, 0xC4FFC)  # ratchet + StageC flip; CRC @0xC4FFC
CAL_BLOCK = (0xC6000, 0xC6FFC)   # StageC pole; CRC @0xC6FFC

# FUN_0003a382's other gain tables MUST stay stock -- the flip + pole must be the ONLY change in the lane
# so a null (or a worse) result is attributable and not confounded by a second simultaneous edit.
FUN3A382_TABLES = {
    0xC6B26: ((256, 256, 225, 153), "L1 Stage-A gain Y row"),
    0xC6B12: ((98, 98, 98, 98), "L2/S3 accumulator gain Y row"),
    0xC6AE6: ((2048, 2048, 2048, 2048), "L3 Stage-C DERIVATIVE gain Y row"),
}
UVAR27_ADDR = 0xC67B8
UVAR27_STOCK = 1024

# Cal cells that MUST remain exactly as V38 left them.
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- forward authority untouched"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal"),
    0xC6206: (512, "governor slew step, fast"),
    0xC6208: (205, "governor slew step, slow"),
    0xC64A3: (1, "pre-gain deadband enable"),
    0xC61B8: (102, "pre-gain deadband threshold"),
    0xC6194: (3, "dead LKAS rate limiter"),
    UVAR27_ADDR: (UVAR27_STOCK, "FUN_0003a382 uVar27 post-sum gain -- stock (V48A cut it; V49 does NOT)"),
}
# The 21 Hz DTC-0x1d damping clamp trap -- byte-stock (V49 does not go near it).
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

EXPECTED_BLOCKS = 50


def full_image(window):
    image = bytearray(b"\xff" * 0x100000)
    image[START:END] = window
    return bytes(image)


def assert_x31_checksum(raw, label):
    stored = struct.unpack_from("<I", raw, len(raw) - 4)[0]
    calculated = sum(raw[:-4]) & 0xFFFFFFFF
    assert calculated == stored, f"{label} x31 checksum: 0x{calculated:08X} != 0x{stored:08X}"


def decode_bcond(code, address):
    halfword = struct.unpack_from("<H", code, address)[0]
    if (halfword >> 7) & 0xF != 0xB:
        return None
    cond = halfword & 0xF
    disp = (((halfword >> 11) & 0x1F) << 4) | (((halfword >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return cond, address + disp


def decode_fmt1(word):
    """V850 Format-I reg-reg -> (reg2, opcode, reg1)."""
    return (word >> 11) & 0x1F, (word >> 5) & 0x3F, word & 0x1F


def crc_block_map(code):
    start_page, num_pages = struct.unpack_from("<HH", code, END - 8)
    block_start, block_length = start_page << 12, (num_pages << 12) - 4
    blocks, visited = [], set()
    while True:
        assert block_start not in visited, f"CRC chain loop at 0x{block_start:X}"
        visited.add(block_start)
        assert block_start >= 8 and block_length >= 0, "invalid block geometry"
        trailer = block_start + block_length
        assert trailer + 4 <= len(code), f"block 0x{block_start:X} out of bounds"
        blocks.append((block_start, trailer))
        if block_start == START:
            break
        next_page, next_num_pages = struct.unpack_from("<HH", code, block_start - 8)
        next_start = next_page << 12
        assert next_start != block_start, f"CRC chain self-loop at 0x{block_start:X}"
        block_start, block_length = next_start, (next_num_pages << 12) - 4
        assert len(blocks) <= 200, "runaway CRC chain"
    return blocks


def assert_crc_chain(code, label):
    blocks = crc_block_map(code)
    for block_start, trailer in blocks:
        calculated = zlib.crc32(code[block_start:trailer]) & 0xFFFFFFFF
        stored = struct.unpack_from("<I", code, trailer)[0]
        assert calculated == stored, \
            f"{label}: CRC mismatch block 0x{block_start:X}: 0x{calculated:08X} != 0x{stored:08X}"
    assert len(blocks) == EXPECTED_BLOCKS, \
        f"{label}: expected {EXPECTED_BLOCKS} CRC blocks, traversed {len(blocks)}"
    return len(blocks)


def owning_block(code, address):
    inside = [(s, e) for s, e in crc_block_map(code) if s <= address < e]
    assert len(inside) == 1, f"0x{address:05X} lies in {len(inside)} CRC blocks ({inside})"
    return inside[0]


def changed_runs(before, after):
    diffs = [i for i in range(START, END) if before[i] != after[i]]
    runs = []
    for address in diffs:
        if runs and address == runs[-1][1] + 1:
            runs[-1][1] = address
        else:
            runs.append([address, address])
    return diffs, runs


def u16(code, addr):
    return struct.unpack_from("<H", code, addr)[0]


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39/V48B cave present; baseline must be V38"

    # ratchet at stock bne (V49 APPLIES the fix, like V42/V45/V46/V47/V48A)
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, "0x454FE is not the stock `bne` halfword"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET), \
        "0x454FE does not decode as (BNE, 0x455C4) in the V38 baseline"
    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR):
        assert bytes(code[address:address + len(expected)]) == expected, \
            f"instruction context at 0x{address:05X} does not match expected V38 bytes"

    # StageC derivative must be the stock `subr r14,r15` before we flip it.
    assert u16(code, FLIP_ADDR) == FLIP_STOCK_HW, \
        f"0x{FLIP_ADDR:05X} is 0x{u16(code, FLIP_ADDR):04X}, expected stock subr 0x{FLIP_STOCK_HW:04X}"
    r2, op, r1 = decode_fmt1(FLIP_STOCK_HW)
    assert (r2, op, r1) == (15, 0x0C, 14), f"stock 0x{FLIP_ADDR:05X} is not subr r14,r15: {(r2, op, r1)}"

    # StageC pole must be at stock unity; StageA sibling pole must be unity too.
    assert u16(code, POLE_ADDR) == POLE_STOCK, f"0x{POLE_ADDR:05X} StageC pole is not stock {POLE_STOCK}"
    assert u16(code, POLE_SIBLING_ADDR) == POLE_SIBLING_STOCK, "StageA sibling pole not at unity"

    # a382's other gain tables + uVar27 must be stock.
    for address, (values, note) in FUN3A382_TABLES.items():
        assert struct.unpack_from("<4h", code, address) == values, f"0x{address:05X} ({note}) not stock"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else u16(code, address)
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"clamp {note} 0x{addr:05X} not stock"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, "clamp float mirror moved"


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)
    assert_crc_chain(baseline, "V38 baseline")
    assert walk(bytes(baseline), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V38 baseline") == 0

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    assert decode is not None
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)

    # ---- EDIT 1: state-4 ratchet fix ------------------------------------------------------------
    print("  EDIT 1 (CODE, 1 byte) -- CONFIRMED state-4 ratchet fix:")
    before = decode_bcond(code, RATCHET_ADDR)
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    after = decode_bcond(code, RATCHET_ADDR)
    assert before == (COND_BNE, RATCHET_TARGET) and after == (COND_BR, RATCHET_TARGET), \
        "ratchet branch target moved"
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1], "high byte of the branch changed"
    print(f"    0x{RATCHET_ADDR:05X}: 0x{RATCHET_STOCK_HW:04X} -> 0x{RATCHET_NEW_HW:04X}  bne -> br 0x{RATCHET_TARGET:05X}")

    # ---- EDIT 2: flip StageC derivative sign ----------------------------------------------------
    print("  EDIT 2 (CODE, 1 byte) -- flip FUN_0003a382 StageC derivative: subr -> sub:")
    struct.pack_into("<H", code, FLIP_ADDR, FLIP_NEW_HW)
    r2, op, r1 = decode_fmt1(u16(code, FLIP_ADDR))
    assert (r2, op, r1) == (15, 0x0D, 14), f"flipped 0x{FLIP_ADDR:05X} is not sub r14,r15: {(r2, op, r1)}"
    assert code[FLIP_ADDR + 1] == baseline[FLIP_ADDR + 1], "high byte of the StageC instruction changed"
    assert code[FLIP_ADDR] == (baseline[FLIP_ADDR] | 0x20), "flip is not the single opcode bit (0x20)"
    print(f"    0x{FLIP_ADDR:05X}: 0x{FLIP_STOCK_HW:04X} -> 0x{FLIP_NEW_HW:04X}  subr r14,r15 -> sub r14,r15")
    print(f"                (StageC derivative current-previous -> previous-current; single opcode bit 0x20)")

    # ---- EDIT 3: band-limit StageC (pole) -------------------------------------------------------
    print("  EDIT 3 (CAL, 1 halfword) -- band-limit StageC to ~10 Hz (GATE-2: kills the HF anti-damping):")
    struct.pack_into("<H", code, POLE_ADDR, POLE_NEW)
    assert u16(code, POLE_ADDR) == POLE_NEW
    assert u16(code, POLE_SIBLING_ADDR) == POLE_SIBLING_STOCK, "StageA sibling pole must stay unity"
    print(f"    0x{POLE_ADDR:05X}: {POLE_STOCK} -> {POLE_NEW}  (alpha {POLE_STOCK/1024:.4f} -> {POLE_NEW/1024:.4f}, corner ~10 Hz)")

    # nothing else in the lane or the trap may move
    for address, (values, note) in FUN3A382_TABLES.items():
        assert struct.unpack_from("<4h", code, address) == values, f"0x{address:05X} ({note}) moved"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"clamp {note} moved"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, "clamp float mirror moved"

    # ---- CRC coverage ---------------------------------------------------------------------------
    assert owning_block(code, RATCHET_ADDR) == MAIN_BLOCK, "ratchet not in MAIN_BLOCK"
    assert owning_block(code, FLIP_ADDR) == MAIN_BLOCK, "StageC flip not in MAIN_BLOCK"
    assert owning_block(code, POLE_ADDR) == CAL_BLOCK, "StageC pole not in CAL_BLOCK"
    print(f"  CRC coverage: ratchet + StageC flip -> MAIN [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}); "
          f"pole -> CAL [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X})")
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ----------------------------------------------------------------------
    allowed = {RATCHET_ADDR, FLIP_ADDR, POLE_ADDR, POLE_ADDR + 1}
    for block in (MAIN_BLOCK, CAL_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V49-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # 1 ratchet + 1 flip + 2 pole (0x0400 -> 0x0040 moves both bytes) + up to 8 CRC-trailer bytes.
    non_crc = set(diffs) - {p for b in (MAIN_BLOCK, CAL_BLOCK) for p in range(b[1], b[1] + 4)}
    assert non_crc == {RATCHET_ADDR, FLIP_ADDR, POLE_ADDR, POLE_ADDR + 1}, \
        f"non-CRC diffs {sorted(non_crc)} != the 4 intended edit bytes"

    # everything else byte-identical to V38
    # address order: StageC flip 0x3A836 comes BEFORE the ratchet 0x454FE.
    assert bytes(code[START:FLIP_ADDR]) == bytes(baseline[START:FLIP_ADDR]), "code before StageC flip moved"
    assert bytes(code[FLIP_ADDR + 1:RATCHET_ADDR]) == bytes(baseline[FLIP_ADDR + 1:RATCHET_ADDR]), \
        "code between StageC flip and ratchet moved"
    assert bytes(code[RATCHET_ADDR + 1:0xBF000]) == bytes(baseline[RATCHET_ADDR + 1:0xBF000]), \
        "code after the ratchet (through end of app) moved"
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "cal edit in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    cal_diffs = {i for i in range(0xC6000, 0xC7000) if code[i] != baseline[i]}
    assert cal_diffs <= allowed, f"unexpected 0xC6000-block bytes: {sorted(cal_diffs - allowed)}"
    assert bytes(code[0xC7000:0x100000]) == bytes(baseline[0xC7000:0x100000]), "0xC7000-end moved"

    assert_crc_chain(code, "V49 plain")
    assert walk(bytes(code), label="V49") == 0
    assert walk_all_blocks(bytes(code), label="V49") == 0

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V49 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V49 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V49 RWD readback")
    assert walk(readback, label="V49 RWD readback") == 0
    assert walk_all_blocks(readback, label="V49 RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), "ratchet lost in RWD"
    assert decode_fmt1(u16(readback, FLIP_ADDR)) == (15, 0x0D, 14), "StageC flip lost in RWD (not sub r14,r15)"
    assert u16(readback, POLE_ADDR) == POLE_NEW, "StageC pole lost in RWD"
    assert u16(readback, POLE_SIBLING_ADDR) == POLE_SIBLING_STOCK, "StageA sibling pole moved in RWD"
    assert u16(readback, 0xC646C) == 3564, "4x forward gain not preserved in RWD"
    assert bytes(readback[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, "clamp trap moved in RWD"

    print(f"\n  V49-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "EDIT 1: state-4 ratchet branch nibble (confirmed)"
        elif first == FLIP_ADDR:
            kind = "EDIT 2: StageC derivative sign flip (subr->sub)"
        elif first == POLE_ADDR:
            kind = "EDIT 3: StageC pole 0xC644A 1024->64 (band-limit)"
        elif first in (MAIN_BLOCK[1], CAL_BLOCK[1]):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V49 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V49 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V49-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V49_OUT)]
    for path in stale + [V49_OUT, BIN_OUT, V49_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V49 = V38 + ratchet fix + StageC collocated damper (sign flip + band-limit).")
    print("  EDIT 1 (CODE, 1 byte)   0x454FE  bne -> br              (confirmed ratchet fix)")
    print("  EDIT 2 (CODE, 1 byte)   0x3A836  subr r14,r15 -> sub    (StageC derivative sign flip)")
    print("  EDIT 3 (CAL, 1 halfword) 0xC644A  1024 -> 64            (band-limit StageC to ~10 Hz, GATE-2)")
    print("  🛑 FLASH GATE: direction depends on polarity gp-0x6752 (0xFEDF18AE). +1 = fix, -1 = brick.")
    print("     CONFIRM gp-0x6752 == +1 via a read-only at-rest RAM read BEFORE any flash.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V49_OUT), exist_ok=True)
    with open(V49_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V49_OUT + ".tmp", V49_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V49_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. 🛑 Flash ONLY after (1) gp-0x6752 confirmed +1 AND (2) an explicit operator")
    print("  instruction naming the file + bus. Direction bricks at gp-0x6752 = -1.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
