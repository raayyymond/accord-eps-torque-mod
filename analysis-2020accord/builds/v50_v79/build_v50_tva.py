"""
builds/v50_v79/build_v50_tva.py -- V50 = V38 + the state-4 ratchet fix + a first-order EMA LOW-PASS on Sensor-B torque
                    gp-0x4f60 (code cave). "V48B done right."

=======================================================================================================
V50 IN ONE LINE
    Keep the 4x LKAS gain and the CONFIRMED state-4 ratchet fix. Attack the ~21 Hz (low-speed) vibration
    with a first-order EMA LOW-PASS (fc~=12 Hz, alpha=74/1024) on a FILTERED COPY of gp-0x4f60, chosen
    over V48B's notch because the mode is SPEED-DEPENDENT (~21.7 Hz low-speed -> ~8-12 Hz highway; fresh
    manual-drive data) and the 21.5-vs-78.6 Hz aliasing is unresolved -- a low-pass covers the whole band
    and rolls off 78.6 Hz even harder (-16 dB) than 21.4 (-6 dB), a notch would miss both.

WHY V50 IS SAFER THAN THE BRICKED V48B  (both mandatory gates, applied without being asked)
    * GATE 2 (closed-loop stability): studies/models/eps_v50_gate2_lowpass.py -- the EMA is STABLE under both the
      pessimistic (Q_cl=13.6) and the realistic broad-shelf (Q_cl~4.8) loop calibrations, hard-edge
      4.66x -> ~21x, and has NO resonant pole (robust by construction; V48B's notch was an r=0.979
      resonator). Polarity-independent (no sign term -> sidesteps the V49 gate).
    * GATE 1 (RAM ownership): a first-order EMA has ONE state word, not V48B's 4-cell biquad whose x2 cell
      gp-0x14FA aliased a live status byte and bricked. The state (4-byte) + output (2-byte) are placed in
      the vetted-clean "Cell C" region near 0xFEDF0000, AWAY from the gp-0x14xx/0x15xx CAN/DTC status
      cluster and the 0xbb640/0xb7260 address tables (whose unknown consumer is the V48B register-indirect
      blind-spot). D_STATE/D_OUT come from the Gate-1 RAM-ownership trace and are asserted 4-aligned + free.

THE FILTER  [studies/caves/v50_cave_asm.py -- all encoders cross-verified vs real code.bin instructions]
    32-bit state S = filtered<<8 (deadband-free). Each 1 kHz cycle:
      diff = (x<<8) - S ; S += (74*diff)>>10 ; y = S>>8 ; carriers ld.h y.
    74*diff is done by shift-add (74=64+8+2) -- NOT mulhi (which truncates to 16 bits). Overflow-proof:
    |diff|<=13.1M, 74*diff<=0.97e9 < 2^31.

THE CAVE + REPOINTS: identical mechanics to V48B (trampoline jr at 0x7FEAC displacing cmp r0,r8 +
    mov r8,r14, re-executed last; 7 live carrier repoints; 2 dormant reads left raw). Only the cave body
    (EMA, not biquad) and the output cell address differ.

CRC BLOCKS TOUCHED (1): MAIN 0xC4FFC only (ratchet + trampoline + cave + 7 repoints). The fc corner is
    baked into the cave (alpha=74 shift-add), NOT a cal -> no CAL-block edit. 0xC646C=3564 (4x) untouched.

STATUS: STUDY ARTIFACT, UNFLASHED. Code cave = the kit's only bricking class (V24/V27/V48B). Both gates
    pass, but the ultimate check is first-minutes on-car observation. Flash ONLY on explicit operator
    instruction naming the file + bus, after a Ghidra re-disassembly of the built image.
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
    raise RuntimeError("V50 builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks
from v50_cave_asm import CAVE_BASE, HOOK, RETURN, D_CELL, assemble_cave, gp_field, jr

# =====================================================================================================
# GATE-1 RESULT -- the single 16-bit EMA cell is gp-0x1500 (0xFEDF6B00). Evidence: V48B wrote it every
# cycle and drove (its brick was gp-0x14FA, a DIFFERENT cell); the Gate-1 RAM-ownership trace found bytes
# 0-1 direct-clean by two methods; the CAN-0xE4 handler FUN_00052676 paired with it in the 0xbb640 table
# does NOT write it (lead-decompiled + verified). RESIDUAL (irreducible cave risk; pre-flash review must
# close it): 0xFEDF6B00 also appears in the 0xbb640/0xb7260 address tables whose walker is unidentified,
# so a register-indirect writer is not PROVEN absent. Single 16-bit cell = state AND output (imported).
# =====================================================================================================

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

V50_TAG = "LKAS-4x-V38base-ratchet-lowpass-fc12hz-ema-gp1500"
V50_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V50-{V50_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v50_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA
RATCHET_NEW_HW = 0x65B5
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5

HOOK_STOCK = bytes.fromhex("e0410870")   # cmp r0,r8 ; mov r8,r14

# ---- the 7 LIVE carrier repoint sites (Gate-1 reconfirmed on stock): ld.h -0x4f60[gp],rX ----------
# stock word1 = 0x24 | (byte1<<8); disp16 = 0xB0A0 (-0x4f60) -> D_OUT.
REPOINT_SITES = [
    (0x2C480, 0x24 | (0x7F << 8), "FUN_0002c478 type-8 (r15)"),
    (0x354D2, 0x24 | (0x87 << 8), "FUN_000352b4 magnitude (r16)"),
    (0x35AA4, 0x24 | (0x77 << 8), "FUN_000352b4 magnitude (r14)"),
    (0x3A6CA, 0x24 | (0x57 << 8), "FUN_0003a382 resonance (r10)"),
    (0x3A7CA, 0x24 | (0x47 << 8), "FUN_0003a382 resonance (r8)"),
    (0x3B4A8, 0x24 | (0x6F << 8), "FUN_0003b49a -> FUN_0003a382 (r13)"),
    (0x3B672, 0x24 | (0x4F << 8), "FUN_0003b66a -> damping+boost Factor-A (r9)"),
]
DISP_4F60 = (-0x4F60) & 0xFFFF   # 0xB0A0

# ---- SAFETY: the damping OUTPUT CLAMP BOUND + float mirror (DTC-0x1d no-debounce trap) stay stock --
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD209E: (300, "clamp m10 X0"), 0xD20A0: (800, "clamp m10 X1"),
    0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"), 0xD20AC: (800, "clamp m11 X1"),
    0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- UNTOUCHED"),
    0xC4120: (0x01, "type-8 slot-8 sum gate -- stock"),
    0xC6498: (0x01, "damping mode byte -- stock (0x34392 read dormant)"),
    0xC6499: (0x01, "boost mode byte -- stock (0x34ace read dormant)"),
    0xC67B8: (1024, "FUN_0003a382 uVar27 Y0 -- stock"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole -- stock"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- stock"),
}
DORMANT_SITES = {0x34392: "FUN_00034350 damping (dormant)", 0x34ACE: "FUN_00034a72 boost (dormant)"}

MAIN_BLOCK = (0x13000, 0xC4FFC)
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


def assert_cell_ok():
    """The single 16-bit EMA cell must be halfword-aligned and in disp16 range."""
    assert D_CELL % 2 == 0, f"D_CELL gp-0x{D_CELL:04X} must be halfword-aligned for ld.h/st.h"
    assert 0 < D_CELL <= 0x8000, "gp displacement out of disp16 range"
    assert D_CELL == 0x1500, "V50 uses the V48B-proven gp-0x1500 cell; change deliberately if ever moved"


def assert_clamp_stock(code, label):
    for addr, (value, note) in CLAMP_INT_STOCK.items():
        assert u16(code, addr) == value, f"{label}: clamp bound 0x{addr:05X} moved ({note})"
    assert bytes(code[CLAMP_FLOAT_ADDR:CLAMP_FLOAT_ADDR + 16]) == CLAMP_FLOAT_STOCK, \
        f"{label}: clamp float mirror moved (DTC-0x1d trap)"


def assert_repoint_sites_stock(code):
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1, f"repoint site 0x{addr:05X} opcode/reg word moved ({note})"
        assert u16(code, addr + 2) == DISP_4F60, f"repoint site 0x{addr:05X} disp not stock ({note})"
    for addr, note in DORMANT_SITES.items():
        assert u16(code, addr + 2) == DISP_4F60, f"dormant site 0x{addr:05X} disp moved ({note})"


def assert_v38_baseline(code, cave_bytes):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, "0x454FE is not the stock bne"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET)
    assert bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK, "0x7FEAC not stock cmp/mov"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == b"\xff" * len(cave_bytes), \
        "cave region not all-0xFF -- baseline must be V38"
    assert bytes(code[CAVE_BASE + len(cave_bytes):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(cave_bytes)), "cave tail not 0xFF"
    assert_repoint_sites_stock(code)
    assert_clamp_stock(code, "V38 baseline")
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
        assert got == value, f"0x{address:05X}: expected {value} got {got} ({note})"


def build():
    assert_cell_ok()
    disp_out = gp_field(D_CELL)

    baseline = bytearray(open(V38_PLAIN, "rb").read())
    cave_bytes, cave_ann = assemble_cave(d_cell=D_CELL)
    assert_v38_baseline(baseline, cave_bytes)
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
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    code = bytearray(baseline)

    print("  CHANGE 1 (CODE, 1 byte) -- state-4 ratchet fix:")
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET)
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1]
    print(f"    0x{RATCHET_ADDR:05X}: bne -> br 0x{RATCHET_TARGET:05X}")

    print(f"  CHANGE 2 (CODE, {len(cave_bytes)} bytes) -- EMA low-pass cave @0x{CAVE_BASE:05X}:")
    code[CAVE_BASE:CAVE_BASE + len(cave_bytes)] = cave_bytes
    print(f"    [0x{CAVE_BASE:05X},0x{CAVE_BASE + len(cave_bytes):05X})  {len(cave_ann)} instrs  "
          f"(single 16-bit cell gp-0x{D_CELL:04X})")

    print(f"  CHANGE 3 (CODE, 4 bytes) -- trampoline @0x{HOOK:05X}:")
    tramp = jr(CAVE_BASE, HOOK)
    code[HOOK:HOOK + 4] = tramp
    print(f"    0x{HOOK:05X}: {HOOK_STOCK.hex()} -> {tramp.hex()}   jr 0x{CAVE_BASE:05X}")

    print("  CHANGE 4 (CODE, 7 x 2 bytes) -- repoint live carriers gp-0x4f60 -> gp-0x{:04X}:".format(D_CELL))
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1 and u16(code, addr + 2) == DISP_4F60
        struct.pack_into("<H", code, addr + 2, disp_out)
        assert u16(code, addr + 2) == disp_out and u16(code, addr) == w1
        print(f"    0x{addr:05X}: disp {DISP_4F60:#06x} -> {disp_out:#06x}   {note}")

    assert_clamp_stock(code, "V50")
    for addr, note in DORMANT_SITES.items():
        assert u16(code, addr + 2) == DISP_4F60, f"dormant site 0x{addr:05X} must stay raw ({note})"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"

    for addr in (RATCHET_ADDR, CAVE_BASE, CAVE_BASE + len(cave_bytes) - 1, HOOK):
        assert owning_block(code, addr) == MAIN_BLOCK
    for addr, _w, _n in REPOINT_SITES:
        assert owning_block(code, addr) == MAIN_BLOCK
    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    diffs, runs = changed_runs(baseline, code)
    allowed = {RATCHET_ADDR}
    allowed.update(range(CAVE_BASE, CAVE_BASE + len(cave_bytes)))
    allowed.update(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        allowed.update({addr + 2, addr + 3})
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    assert set(diffs) <= allowed, f"unexpected V50-vs-V38 bytes: {sorted(set(diffs) - allowed)}"

    crc_bytes = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    intended = {RATCHET_ADDR} | set(range(CAVE_BASE, CAVE_BASE + len(cave_bytes))) | set(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        intended.update({addr + 2, addr + 3})
    non_crc = set(diffs) - crc_bytes
    assert non_crc <= intended, f"unexpected non-CRC diffs: {sorted(non_crc - intended)}"
    for b in intended - non_crc:
        assert CAVE_BASE <= b < CAVE_BASE + len(cave_bytes) and cave_bytes[b - CAVE_BASE] == 0xFF, \
            f"intended edit at 0x{b:05X} did not land and is not a 0xFF cave byte"

    assert_crc_chain(code, "V50 plain")
    assert walk(bytes(code), label="V50") == 0
    assert walk_all_blocks(bytes(code), label="V50") == 0

    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V50 emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V50 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V50 RWD readback")
    assert walk(readback, label="V50 RWD readback") == 0
    assert walk_all_blocks(readback, label="V50 RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), "ratchet lost in RWD"
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == cave_bytes, "cave lost in RWD"
    assert bytes(readback[HOOK:HOOK + 4]) == tramp, "trampoline lost in RWD"
    for addr, w1, _n in REPOINT_SITES:
        assert u16(readback, addr) == w1 and u16(readback, addr + 2) == disp_out, "repoint lost in RWD"
    for addr, _n in DORMANT_SITES.items():
        assert u16(readback, addr + 2) == DISP_4F60, "dormant site changed in RWD"
    assert_clamp_stock(readback, "V50 RWD readback")
    assert u16(readback, 0xC646C) == 3564, "4x forward gain not preserved in RWD readback"

    print(f"\n  V50-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "CHANGE 1: state-4 ratchet branch nibble"
        elif first == HOOK:
            kind = "CHANGE 3: trampoline jr -> cave"
        elif CAVE_BASE <= first < CAVE_BASE + len(cave_bytes):
            kind = "CHANGE 2: EMA low-pass cave"
        elif any(first == a + 2 for a, _w, _n in REPOINT_SITES):
            kind = "CHANGE 4: carrier repoint (disp16)"
        elif MAIN_BLOCK[1] <= first < MAIN_BLOCK[1] + 4:
            kind = "CRC trailer (MAIN)"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:  {V38_SHA256}")
    print(f"  V50 SHA-256:  {hashlib.sha256(code).hexdigest()}")
    print(f"  V50 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd, cave_ann


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V50-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V50_OUT)]
    for path in stale + [V50_OUT, BIN_OUT, V50_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V50 = V38 + ratchet fix + first-order EMA LOW-PASS (fc~12 Hz) on gp-0x4f60 (code cave, keeps 4x).")
    print("  CHANGE 1 (CODE, 1 byte)     0x454FE  bne -> br            (ratchet fix, carried)")
    print(f"  CHANGE 2 (CODE, EMA cave)   0x{CAVE_BASE:05X}  low-pass biquad-free (alpha=74/1024)")
    print(f"  CHANGE 3 (CODE, 4 bytes)    0x{HOOK:05X}  jr -> cave           (trampoline)")
    print("  CHANGE 4 (CODE, 7x2 bytes)  repoint live carriers gp-0x4f60 -> filtered copy")
    print("  UNTOUCHED: raw gp-0x4f60/shadow, monitors, CAN, 0xC646C=3564 (4x), clamp trap.\n")
    code, rwd, cave_ann = build()

    os.makedirs(os.path.dirname(V50_OUT), exist_ok=True)
    with open(V50_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V50_OUT + ".tmp", V50_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V50_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  *** CODE CAVE -- NOT FLASHED. *** Ghidra-re-disassemble the built image (cave+hook+repoints),")
    print("  run the adversarial pre-flash review, then flash only on explicit operator file+bus instruction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
