"""
builds/v18_v49/build_v48a_tva.py -- V48A = V38 + the state-4 ratchet fix + COMBINED CARRIER MUTE (cal-only).

=======================================================================================================
V48A IN ONE LINE
    Keep the 4x LKAS gain and the CONFIRMED state-4 ratchet fix. Attack the ~21 Hz vibration by
    attenuating the two strongest 21 Hz feedback carriers, cal-only, without touching the 4x forward
    authority: (1) MUTE the "type-8" command-derivative carrier (mixer slot-8 sum gate 0xC4120 -> 0),
    and (2) attenuate the FUN_0003a382 reinforcing residual lane 4x via its post-sum gain uVar27
    (0xC67B8/BA/BC 1024 -> 256). Cut from V38 (stock damper) -- V47's motor-rate damper opening is NOT
    carried (it is non-collocated w.r.t. the wheel-side mode and did nothing in motion; dropping it
    isolates the two mutes cleanly).

WHY THESE TWO CARRIERS  [loop-gain model + six-agent audit, docs/research/VIBRATION-DOSSIER.md]
    The vibration is a two-inertia torsional mode (~21.4 Hz, Q=13.6) whose closed-loop Q is dominated by
    POSITIVE-FEEDBACK (anti-damping) base-assist lanes that read the torsion-bar torque at 1 kHz and
    bypass the LKAS ~5 Hz low-pass. The loop-gain model puts |L(21Hz)| at 0.875 (1.16 dB margin) at 4x;
    the two carriers below are the strongest identified:
      - "type-8" (gp-0x6b12): an envelope-shaped cycle-DELTA of the delivered motor command, latched into
        mixer slot 8 -> gp-0x6b4c. A command-derivative feedback = classic anti-damping at a resonance.
        Removed cleanly by zeroing its per-slot SUM gate; forward authority (0xC646C) untouched.
      - FUN_0003a382 -> gp-0x6ad4: an UNFILTERED model-vs-reality residual (parallel prop + derivative +
        accumulator), added with reinforcing sign. V43/V46 each muted one of three parallel branches and
        failed; uVar27 sits AFTER the 3-way sum, so 1024->256 attenuates all three (incl. the pole-less
        accumulator) by 4x at once.
    Model: muting BOTH -> |L| ~0.25-0.32, margin ~10-12 dB IF these two dominate the loop gain. If null,
    the anti-damping is distributed and the next step is the designed 21.4 Hz notch (V48B).

WHY IT IS SAFE  [pre-build adversarial verification, GhidraMCP, this session]
    EDIT 1 (0xC4120, type-8 mute). The gate array tp+0x5118 has exactly TWO readers image-wide:
      FUN_00026c80 (the int mixer producer) and FUN_00027b0a (a FLOAT int/float LOCKSTEP MONITOR that
      re-derives the same gated sum and DTC-faults on mismatch vs gp-0x6b4c/gp-0x6b4a). BOTH read the SAME
      live cal byte, so muting slot 8 drops it from the int producer AND the float monitor in lockstep ->
      no divergence -> the monitor cannot trip (the matched-symmetric discipline; cf. V27's asymmetric
      brick). The shadow pair gp-0x62b0[8]/gp-0x4b40[8] is written UNCONDITIONALLY (gate-independent),
      before the gate is read, so the FUN_00028d22 shadow comparator cannot trip either.
    EDIT 2 (uVar27, FUN_0003a382 output). FUN_0003a382 is a PURE LEAF (0 jarl, 154 instrs) -> no DTC /
      monitor reachable from within it. The uVar27 table (0xC67B0) is read only at 0x3a4ae. gp-0x6ad4 has
      exactly one producer (0x3a8a0) and one consumer (0x3aca8); shrinking it moves the aggregate FURTHER
      from its clamp/lockstep boundary. No float mirror exists for this lane.
    Neither edit touches the damping OUTPUT CLAMP BOUND (0xD209C/0xD20A8) or its float mirror
      (0xC6554) -- the no-debounce DTC-0x1d trap -- which stay byte-stock (asserted).

CRC BLOCKS TOUCHED  (2)
    MAIN 0xC4FFC (ratchet 0x454FE + type-8 mute 0xC4120) + CAL 0xC6FFC (uVar27 0xC67B8/BA/BC).
    This is the first build in this lineage to write the MAIN block's 0xC4xxx cal sub-region.
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
    raise RuntimeError("V48A builder requires assertions; do not run with python -O")

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

V48A_TAG = "LKAS-4x-V38base-ratchet-mute-type8-a382-uVar27x256"
V48A_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V48A-{V48A_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v48a_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA        # bne +198 -> 0x455c4
RATCHET_NEW_HW = 0x65B5          # br  +198 -> 0x455c4
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))

# ---- EDIT 1 (CAL, 1 byte): mute the type-8 carrier -- mixer slot-8 SUM gate --------------------------
# tp+0x5118[8] = 0xC4120. 1 -> 0 removes slot 8 from the sum that becomes gp-0x6b4c. Read by exactly two
# functions (FUN_00026c80 int producer + FUN_00027b0a float lockstep monitor), both off the SAME cal
# byte -> matched-symmetric, monitor cannot trip. In the MAIN CRC block.
TYPE8_ADDR = 0xC4120
TYPE8_STOCK = 0x01
TYPE8_NEW = 0x00

# ---- EDIT 2 (CAL, 3 halfwords): attenuate FUN_0003a382's output lane 4x via post-sum gain uVar27 ---
# Table @0xC67B0: [count=3][X=5,10,15][Y=1024,1024,1024][pad]. Y cells are the only reachable values on
# the access path (flat), so 1024->256 is a uniform 4x (-12 dB) attenuation independent of the index. In
# the CAL CRC block. Single-reader (0x3a4ae), pure leaf, no float mirror.
UVAR27_EDITS = [
    (0xC67B8, 1024, 256, "FUN_0003a382 uVar27 Y0 (post-sum gain, -12 dB)"),
    (0xC67BA, 1024, 256, "FUN_0003a382 uVar27 Y1"),
    (0xC67BC, 1024, 256, "FUN_0003a382 uVar27 Y2"),
]

MAIN_BLOCK = (0x13000, 0xC4FFC)  # ratchet 0x454FE + type-8 mute 0xC4120; CRC @0xC4FFC
CAL_BLOCK = (0xC6000, 0xC6FFC)   # uVar27; CRC @0xC6FFC

# ---- SAFETY: the damping OUTPUT CLAMP BOUND + its float mirror MUST stay byte-stock ---------------
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD209E: (300, "clamp m10 X0"), 0xD20A0: (800, "clamp m10 X1"),
    0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"), 0xD20AC: (800, "clamp m11 X1"),
    0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

# V44/V47 damper Y0 cells: MUST remain STOCK (V48A is cut from V38 -- does NOT carry the damper opening).
DAMP_STOCK = {
    0xD27C6: 0, 0xD27DA: 0,                              # Factor C Y0 (stock)
    0xD2802: 0, 0xD2804: 140, 0xD2806: 539,              # Factor E m10 Y0/Y1/Y2 (stock)
    0xD2816: 0, 0xD2818: 140, 0xD281A: 539,              # Factor E m11 Y0/Y1/Y2 (stock)
}

# r26 adaptive-gain Y rows: MUST remain STOCK.
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)
RATE_A_Y_OFFSET = 0xA
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))

# Cal cells that MUST remain exactly as V38 left them (forward authority + everything not under test).
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- UNTOUCHED, forward authority preserved"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal ceiling"),
    0xC6206: (512, "governor slew step, HANDS-OFF"),
    0xC6208: (205, "governor slew step, HANDS-ON"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole -- untouched (uVar27 is the lever, not the poles)"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- untouched"),
    0xC64A3: (1, "pre-gain deadband enable"),
    0xC61B8: (102, "pre-gain deadband threshold"),
    0xC6194: (3, "dead LKAS rate limiter"),
}

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
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"{label}: clamp bound 0x{addr:05X} moved ({note})"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, \
        f"{label}: clamp float mirror 0x{CLAMP_FLOAT_ADDR:05X} moved (DTC-0x1d hard-fault trap)"


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"

    # Ratchet at stock bne (V48A APPLIES the fix, like V42/V45/V47).
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, \
        f"0x{RATCHET_ADDR:05X} is not the stock `bne` halfword 0x{RATCHET_STOCK_HW:04X}"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET), \
        "0x454FE does not decode as (BNE, 0x455C4) in the V38 baseline"
    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR):
        assert bytes(code[address:address + len(expected)]) == expected, \
            f"instruction context at 0x{address:05X} does not match expected V38 bytes"

    # The two mute targets must be at their documented stock values first.
    assert code[TYPE8_ADDR] == TYPE8_STOCK, \
        f"0x{TYPE8_ADDR:05X} type-8 gate is 0x{code[TYPE8_ADDR]:02X}, expected stock 0x{TYPE8_STOCK:02X}"
    for addr, stock, _new, label in UVAR27_EDITS:
        assert u16(code, addr) == stock, f"0x{addr:05X} ({label}) stock is {u16(code, addr)}, expected {stock}"

    # Damper (stock -- NOT carrying V47), clamp trap, r26, and every tracked cal must be stock.
    for addr, stock in DAMP_STOCK.items():
        assert u16(code, addr) == stock, f"0x{addr:05X} damper cell is {u16(code, addr)}, expected stock {stock}"
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

    # ---- CHANGE 2 (CAL, 1 byte): mute the type-8 carrier ----------------------------------------
    print("  CHANGE 2 (CAL, 1 byte) -- mute type-8 carrier (mixer slot-8 sum gate):")
    code[TYPE8_ADDR] = TYPE8_NEW
    assert code[TYPE8_ADDR] == TYPE8_NEW
    print(f"    0x{TYPE8_ADDR:05X}: 0x{TYPE8_STOCK:02X} -> 0x{TYPE8_NEW:02X}   "
          f"(slot 8 dropped from gp-0x6b4c; int+float monitors matched off the same byte)")

    # ---- CHANGE 3 (CAL, 3 halfwords): attenuate FUN_0003a382 output lane 4x ----------------------
    print("  CHANGE 3 (CAL, 3 halfwords) -- FUN_0003a382 uVar27 post-sum gain 1024 -> 256:")
    for addr, stock, new, label in UVAR27_EDITS:
        struct.pack_into("<H", code, addr, new)
        assert u16(code, addr) == new
        print(f"    0x{addr:05X}: {stock:>4} -> {new:>4}   {label}")

    # Nothing else may move.
    for addr, stock in DAMP_STOCK.items():
        assert u16(code, addr) == stock, f"0x{addr:05X} damper cell drifted from stock"
    assert_clamp_stock(code, "V48A")
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], "r26 moved"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"

    # ---- CRC coverage (MAIN + CAL) --------------------------------------------------------------
    assert owning_block(code, RATCHET_ADDR) == MAIN_BLOCK, "ratchet not in MAIN_BLOCK"
    assert owning_block(code, TYPE8_ADDR) == MAIN_BLOCK, "type-8 mute not in MAIN_BLOCK"
    for addr, _s, _n, label in UVAR27_EDITS:
        assert owning_block(code, addr) == CAL_BLOCK, f"0x{addr:05X} ({label}) not in CAL_BLOCK"
    print(f"  CRC coverage: ratchet + type-8 -> MAIN [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}); "
          f"uVar27 -> CAL [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X})")

    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ----------------------------------------------------------------------
    allowed = {RATCHET_ADDR, TYPE8_ADDR}
    for addr, _s, _n, _l in UVAR27_EDITS:
        allowed.update({addr, addr + 1})            # full halfword for each uVar27 Y cell
    for block in (MAIN_BLOCK, CAL_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V48A-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # The load-bearing invariant is the exact set of NON-CRC edits (a hard count is brittle: a recomputed
    # CRC trailer can coincidentally share a byte with the stock trailer -- e.g. the MAIN CRC keeps its
    # 0x21 byte here, so the total is 12 not 13). Verify the intended edit bytes exactly, then allow the
    # CRC trailers to change however many of their bytes actually differ.
    crc_bytes = set()
    for block in (MAIN_BLOCK, CAL_BLOCK):
        crc_bytes.update(range(block[1], block[1] + 4))
    intended_edit_bytes = {RATCHET_ADDR, TYPE8_ADDR}
    for addr, _s, _n, _l in UVAR27_EDITS:
        for byte_addr in (addr, addr + 1):
            if baseline[byte_addr] != code[byte_addr]:
                intended_edit_bytes.add(byte_addr)
    non_crc_diffs = set(diffs) - crc_bytes
    assert non_crc_diffs == intended_edit_bytes, \
        f"non-CRC diffs {sorted(non_crc_diffs)} != intended {sorted(intended_edit_bytes)}"
    assert len(intended_edit_bytes) == 5, f"expected 5 intended edit bytes, got {len(intended_edit_bytes)}"

    # ---- everything else byte-identical to V38 --------------------------------------------------
    assert bytes(code[START:RATCHET_ADDR]) == bytes(baseline[START:RATCHET_ADDR]), "code before ratchet moved"
    assert bytes(code[RATCHET_ADDR + 1:0xBF000]) == bytes(baseline[RATCHET_ADDR + 1:0xBF000]), \
        "code after ratchet moved"
    # 0xBF000..0xC4FFC: identical except the type-8 mute byte at 0xC4120 (+ the MAIN CRC trailer).
    assert bytes(code[0xBF000:TYPE8_ADDR]) == bytes(baseline[0xBF000:TYPE8_ADDR]), "edit before 0xC4120"
    assert bytes(code[TYPE8_ADDR + 1:0xC4FFC]) == bytes(baseline[TYPE8_ADDR + 1:0xC4FFC]), \
        "edit in 0xBF000-0xC4FFC other than the type-8 mute"
    # cap block untouched.
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    # CAL block: identical except the three uVar27 halfwords (+ the CAL CRC trailer).
    cal_diffs = {i for i in range(0xC6000, 0xC7000) if code[i] != baseline[i]}
    assert cal_diffs <= allowed, f"unexpected 0xC6000-block bytes: {sorted(cal_diffs - allowed)}"
    # everything after the CAL block -- including the 0xD2xxx damper tables -- is stock.
    assert bytes(code[0xC7000:0x100000]) == bytes(baseline[0xC7000:0x100000]), "0xC7000-end moved"

    assert_crc_chain(code, "V48A plain")
    assert walk(bytes(code), label="V48A") == 0
    assert walk_all_blocks(bytes(code), label="V48A") == 0

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V48A emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V48A RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V48A RWD readback")
    assert walk(readback, label="V48A RWD readback") == 0
    assert walk_all_blocks(readback, label="V48A RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "ratchet fix did not survive the RWD round-trip"
    assert readback[TYPE8_ADDR] == TYPE8_NEW, "type-8 mute did not survive the RWD round-trip"
    for addr, _s, new, label in UVAR27_EDITS:
        assert u16(readback, addr) == new, f"0x{addr:05X} ({label}) did not survive RWD round-trip"
    assert_clamp_stock(readback, "V48A RWD readback")
    for addr, stock in DAMP_STOCK.items():
        assert u16(readback, addr) == stock, f"0x{addr:05X} damper cell not stock in RWD readback"
    assert u16(readback, 0xC646C) == 3564, "4x forward gain not preserved in RWD readback"

    print(f"\n  V48A-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "CHANGE 1: state-4 ratchet branch nibble"
        elif first == TYPE8_ADDR:
            kind = "CHANGE 2: type-8 carrier mute (slot-8 sum gate)"
        elif any(a <= first <= a + 1 for a, _s, _n, _l in UVAR27_EDITS):
            kind = "CHANGE 3: FUN_0003a382 uVar27 4x attenuation"
        elif any(block[1] <= first < block[1] + 4 for block in (MAIN_BLOCK, CAL_BLOCK)):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:  {V38_SHA256}")
    print(f"  V48A SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V48A RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V48A-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V48A_OUT)]
    for path in stale + [V48A_OUT, BIN_OUT, V48A_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V48A = V38 + ratchet fix + COMBINED CARRIER MUTE (cal-only, keeps 4x).")
    print("  CHANGE 1 (CODE, 1 byte)   0x454FE  bne -> br        (ratchet fix, carried)")
    print("  CHANGE 2 (CAL, 1 byte)    0xC4120  0x01 -> 0x00     (mute type-8 carrier)")
    print("  CHANGE 3 (CAL, 3 halfwords) 0xC67B8/BA/BC 1024->256 (FUN_0003a382 uVar27 -12 dB)")
    print("  NOT carried: V47 damper opening (cut from V38; motor-rate damper is non-collocated).")
    print("  UNTOUCHED: 0xC646C=3564 (4x forward), clamp trap 0xD209C/0xC6554 (DTC-0x1d).\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V48A_OUT), exist_ok=True)
    with open(V48A_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V48A_OUT + ".tmp", V48A_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V48A_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
