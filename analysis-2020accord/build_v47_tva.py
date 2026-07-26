"""
build_v47_tva.py -- V47 = V38 + the state-4 ratchet fix + DAMPING RESTORE ONLY (both deadzones).

=======================================================================================================
V47 IN ONE LINE
    Keep the 4x LKAS gain and the CONFIRMED state-4 ratchet fix. Restore the base-assist viscous
    damper hands-off by opening BOTH of its motor-side deadzones -- Factor C (driver torque) AND
    Factor E (motor rate). NO Stage A carrier filter: lever A was FLASHED as V46 and did NOT move the
    vibration on-car, so it is DROPPED -- V47 is a clean dampers-only test (0xC6450 stays STOCK 1024).

WHY THE DAMPING RESTORE  [the operator's manual-rotation cure, turned into firmware]
    The ~21 Hz vibration VANISHES the moment the driver manually ROTATES the wheel (motion, not force).
    Rotation spins up motor rate gp-0x6ac0, which engages the base-assist viscous damper
    (FUN_00034350 -> gp-0x6bd0). That damper is a PRODUCT of 5 Q10 factors; two are gated to zero
    hands-off:
      - Factor C (voted driver torque gp-0x6a5e): Y0=0 below 2240 counts. V44 opened this (0xD27C6/DA).
      - Factor E (|motor rate| gp-0x6ac0): Y0=0 below 60 counts, only 14% at 400 -- a hard low-rate
        deadzone. V44 did NOT open this, which is WHY V44 failed: Factor C alone still left Factor E
        zeroing the whole product hands-off.
    V47 opens BOTH. Factor C uses V44's proven cells (copy Y1 into Y0). Factor E is reshaped so the
    damper carries REAL authority at the low motor rates present during a hands-off resonance --
    ~160-213 counts, matched to the authority the manual-rotation cure demonstrably applies.

SIZING = AGGRESSIVE (deliberate)  [stated, not hidden]
    Factor E Y-row 10/11: (0,140,539,927) -> (700,750,800,927). Delivers 68-78% of peak damping across
    the ENTIRE rate domain instead of only above 2500 counts. A CONSERVATIVE Y0-only bump to 140 (exact
    V44 pattern) yields only ~32 counts -- the same too-weak magnitude V44 already failed with -- so it
    is not used here. TRADE-OFF: removing Factor E's low-rate deadzone adds viscous resistance during
    ANY slow/deliberate steering, so expect some low-speed steering HEAVINESS (parking, maneuvers).
    Fully reversible (cal-only, unflashed). A middle-ground Y0~=350 is available if it feels too heavy.

WHY IT IS SAFE  [byte-verified this session, DampFactors]
    - Factor E tables 0xD27F8(m10)/0xD280C(m11): read ONLY by FUN_00034350's own LERP; no other
      reader, NO float mirror, NO monitor. FUN_00034350 is int-only end to end. GO.
    - The damping output gp-0x6bd0's shadow pair (gp-0x4cf2) is REPORT-ONLY on mismatch.
    - Factor C cells are V44's already-verified, road-carried edits.
    - ⚠ The damping OUTPUT CLAMP BOUND (0xD209C/0xD20A8) has a float mirror (0xC6554/58/5C/60) guarded
      by a NO-DEBOUNCE DTC-0x1d hard shutdown (FUN_000347b8 -> FUN_000462e6 -> FUN_00016de6(0x1d)).
      V47 does NOT touch it and does NOT need to: even aggressive damping (~213 counts) stays under the
      clamp's 512 low floor, so it never binds. This builder ASSERTS the int clamp tables and the float
      mirror remain byte-stock (baseline, built image, and RWD readback).

CRC BLOCKS TOUCHED  (2, down from V46's re-defined 3)
    MAIN 0xC4FFC (ratchet) + DAMP 0xD2FFC (Factor C + Factor E). The CAL block 0xC6000 is NOT touched
    (Stage A reverted), so its CRC @0xC6FFC stays stock.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V47 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
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

V47_TAG = "LKAS-4x-V38base-ratchet-dampers-C235-Eaggr"
V47_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V47-{V47_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v47_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA        # bne +198 -> 0x455c4
RATCHET_NEW_HW = 0x65B5          # br  +198 -> 0x455c4
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))

# ---- THE VIBRATION LEVER: DAMPING RESTORE (both deadzones) ---------------------------------------
# Each entry: (address, stock_halfword, new_halfword, label). All are u16 LERP-Y cells in DAMP_BLOCK.
DAMP_EDITS = [
    # Factor C (voted driver torque) Y0 -- V44's proven cells (copy that table's own Y1 into Y0).
    (0xD27C6, 0, 235, "FactorC m10 Y0 (driver-torque deadzone; V44 value)"),
    (0xD27DA, 0, 234, "FactorC m11 Y0 (driver-torque deadzone; V44 value)"),
    # Factor E (|motor rate|) Y0/Y1/Y2 -- AGGRESSIVE reshape (0,140,539,927) -> (700,750,800,927).
    (0xD2802, 0, 700, "FactorE m10 Y0 (motor-rate deadzone)"),
    (0xD2804, 140, 750, "FactorE m10 Y1"),
    (0xD2806, 539, 800, "FactorE m10 Y2"),
    (0xD2816, 0, 700, "FactorE m11 Y0 (motor-rate deadzone)"),
    (0xD2818, 140, 750, "FactorE m11 Y1"),
    (0xD281A, 539, 800, "FactorE m11 Y2"),
]

# ---- SAFETY: the damping OUTPUT CLAMP BOUND + its float mirror MUST stay byte-stock ---------------
# (int clamp tables in DAMP_BLOCK; float mirror in the untouched CAL block; guarded by no-debounce
#  DTC 0x1d.)
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD209E: (300, "clamp m10 X0"), 0xD20A0: (800, "clamp m10 X1"),
    0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"), 0xD20AC: (800, "clamp m11 X1"),
    0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

# r26 adaptive-gain Y rows (V42's falsified target): MUST remain STOCK (V47 is cut from V38).
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)
RATE_A_Y_OFFSET = 0xA
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))

# Cal cells that MUST remain exactly as V38 left them. V47 touches NOTHING in the 0xC6000 block.
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal ceiling"),
    0xC6206: (512, "governor slew step, HANDS-OFF -- untouched"),
    0xC6208: (205, "governor slew step, HANDS-ON -- untouched"),
    0xC6450: (1024, "Stage A pole -- lever A REVERTED (falsified on-car in V46)"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- untouched"),
    0xC64A3: (1, "pre-gain deadband enable"),
    0xC61B8: (102, "pre-gain deadband threshold"),
    0xC6194: (3, "dead LKAS rate limiter"),
}

MAIN_BLOCK = (0x13000, 0xC4FFC)  # ratchet; CRC @0xC4FFC
DAMP_BLOCK = (0xD2000, 0xD2FFC)  # Factor C + Factor E; CRC @0xD2FFC (same block V44 used)

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


def assert_clamp_stock(code, label):
    """The damping output clamp bound + its float mirror -- the DTC-0x1d hard-fault trap -- stay stock."""
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"{label}: clamp bound 0x{addr:05X} moved ({note})"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, \
        f"{label}: clamp float mirror 0x{CLAMP_FLOAT_ADDR:05X} moved (DTC-0x1d hard-fault trap)"


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"

    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, \
        f"0x{RATCHET_ADDR:05X} is not the stock `bne` halfword 0x{RATCHET_STOCK_HW:04X}"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET), \
        "0x454FE does not decode as (BNE, 0x455C4) in the V38 baseline"
    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR):
        assert bytes(code[address:address + len(expected)]) == expected, \
            f"instruction context at 0x{address:05X} does not match expected V38 bytes"

    # Every damping cell V47 will edit must be at its documented STOCK value first.
    for addr, stock, _new, label in DAMP_EDITS:
        assert u16(code, addr) == stock, f"0x{addr:05X} ({label}) stock is {u16(code, addr)}, expected {stock}"

    # The clamp bound + float mirror (the hard-fault trap) must be stock, and stay stock.
    assert_clamp_stock(code, "V38 baseline")

    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], \
            f"r26 record 0x{base:05X} Y row is not stock -- baseline must be V38"

    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else u16(code, address)
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"


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

    # ---- CHANGE 1 (CODE, 1 byte): the state-4 ratchet fix ---------------------------------------
    print("  CHANGE 1 (CODE, 1 byte) -- state-4 ratchet fix:")
    before_cond, before_target = decode_bcond(code, RATCHET_ADDR)
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    after_cond, after_target = decode_bcond(code, RATCHET_ADDR)
    print(f"    0x{RATCHET_ADDR:05X}: 0x{RATCHET_STOCK_HW:04X} -> 0x{RATCHET_NEW_HW:04X}   "
          f"bne 0x{before_target:05X} -> br 0x{after_target:05X}")
    assert (before_cond, after_cond) == (COND_BNE, COND_BR)
    assert before_target == after_target == RATCHET_TARGET, "branch target moved"
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1], "high byte of the branch changed"

    # ---- CHANGE 2 (CAL, 8 halfwords): damping restore -- open both deadzones ---------------------
    print("  CHANGE 2 (CAL, 8 halfwords) -- damping restore (Factor C + Factor E):")
    for addr, stock, new, label in DAMP_EDITS:
        struct.pack_into("<H", code, addr, new)
        assert u16(code, addr) == new
        print(f"    0x{addr:05X}: {stock:>4} -> {new:>4}   {label}")

    # Stage A stays stock (lever A dropped); clamp trap + r26 + tracked cals UNTOUCHED.
    assert u16(code, 0xC6450) == 1024, "Stage A pole moved -- V47 must NOT carry lever A"
    assert_clamp_stock(code, "V47")
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], "r26 moved"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"

    # ---- CRC coverage (MAIN + DAMP only; CAL block untouched) -----------------------------------
    assert owning_block(code, RATCHET_ADDR) == MAIN_BLOCK, "ratchet not in MAIN_BLOCK"
    for addr, _s, _n, label in DAMP_EDITS:
        assert owning_block(code, addr) == DAMP_BLOCK, f"0x{addr:05X} ({label}) not in DAMP_BLOCK"
    print(f"  CRC coverage: ratchet -> MAIN [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}); "
          f"dampers -> DAMP [0x{DAMP_BLOCK[0]:X},0x{DAMP_BLOCK[1]:X})")

    for block in sorted({MAIN_BLOCK, DAMP_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ----------------------------------------------------------------------
    allowed = {RATCHET_ADDR}
    for addr, _s, _n, _l in DAMP_EDITS:
        allowed.update({addr, addr + 1})            # full halfword for each damping cell
    for block in (MAIN_BLOCK, DAMP_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V47-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # 1 ratchet + 2 FactorC (1B each) + 12 FactorE (6 halfwords, both bytes) + 8 CRC (2 trailers) = 23.
    assert len(diffs) == 23, f"expected exactly 23 changed bytes vs V38, got {len(diffs)}"

    # ---- everything else byte-identical to V38 --------------------------------------------------
    assert bytes(code[START:RATCHET_ADDR]) == bytes(baseline[START:RATCHET_ADDR]), "code before ratchet moved"
    assert bytes(code[RATCHET_ADDR + 1:0xBF000]) == bytes(baseline[RATCHET_ADDR + 1:0xBF000]), \
        "code after ratchet moved"
    # Nothing changes in 0xBF000..0xD2000 EXCEPT the MAIN CRC trailer at 0xC4FFC. The entire 0xC6000
    # CAL block is byte-stock (lever A reverted), covered by the 0xC5000:0xD2000 span.
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "edit in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xD2000]) == bytes(baseline[0xC5000:0xD2000]), \
        "unexpected edit in 0xC5000-0xD2000 (incl. the entire 0xC6000 CAL block -- lever A reverted)"
    damp_diffs = {i for i in range(0xD2000, 0xD3000) if code[i] != baseline[i]}
    assert damp_diffs <= allowed, f"unexpected 0xD2000-block bytes: {sorted(damp_diffs - allowed)}"
    assert bytes(code[0xD3000:0x100000]) == bytes(baseline[0xD3000:0x100000]), "0xD3000-end moved"

    assert_crc_chain(code, "V47 plain")
    assert walk(bytes(code), label="V47") == 0
    assert walk_all_blocks(bytes(code), label="V47") == 0

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V47 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V47 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V47 RWD readback")
    assert walk(readback, label="V47 RWD readback") == 0
    assert walk_all_blocks(readback, label="V47 RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "ratchet fix did not survive the RWD round-trip"
    assert u16(readback, 0xC6450) == 1024, "Stage A pole not stock in RWD readback"
    for addr, _s, new, label in DAMP_EDITS:
        assert u16(readback, addr) == new, f"0x{addr:05X} ({label}) did not survive RWD round-trip"
    assert_clamp_stock(readback, "V47 RWD readback")

    print(f"\n  V47-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "ratchet branch nibble"
        elif any(first == a for a, _s, _n, _l in DAMP_EDITS):
            kind = "damping restore (Factor C / Factor E)"
        elif first in (MAIN_BLOCK[1], DAMP_BLOCK[1]):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V47 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V47 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V47-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V47_OUT)]
    for path in stale + [V47_OUT, BIN_OUT, V47_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V47 = V38 + ratchet fix + DAMPING RESTORE ONLY (Factor C + Factor E, aggressive).")
    print("  CHANGE 1 (CODE, 1 byte)  0x454FE  bne -> br   (ratchet fix)")
    print("  CHANGE 2 (CAL, 8 halfwords) Factor C 0xD27C6/DA=235/234; Factor E Y0-2 -> 700/750/800")
    print("  DROPPED: lever A (Stage A pole 0xC6450 stays STOCK 1024 -- falsified on-car as V46).")
    print("  UNTOUCHED: clamp bound 0xD209C/0xD20A8 + float mirror 0xC6554 (DTC-0x1d trap).\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V47_OUT), exist_ok=True)
    with open(V47_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V47_OUT + ".tmp", V47_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V47_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
