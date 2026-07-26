"""
build_v48b_tva.py -- V48B = V38 + the state-4 ratchet fix + a 21.4 Hz NOTCH on Sensor-B torque (code cave).

=======================================================================================================
V48B IN ONE LINE
    Keep the 4x LKAS gain and the CONFIRMED state-4 ratchet fix. Attack the ~21.4 Hz two-inertia
    torsional vibration with the OEM-standard, split-independent lever: a 2nd-order NOTCH biquad on a
    FILTERED COPY of Sensor-B/TAS torque gp-0x4f60. The raw gp-0x4f60 is left untouched (it is
    shadow-lockstep fault-0x17 + feeds 2 no-debounce hard-shutdown monitors + 2 CAN broadcasts). A code
    cave computes the notch once per 1 kHz cycle and stores it to a new RAM cell (gp-0x1500); the 7 LIVE
    base-assist carrier reads of gp-0x4f60 are repointed to that cell. Monitors / CAN / diagnostics keep
    the raw value.

WHY A NOTCH  [docs/VIBRATION-DOSSIER.md, eps_loop_gain_model.py, eps_v48b_notch_design.py]
    V48A muted the two strongest identified carriers (type-8 + FUN_0003a382 uVar27) and did NOTHING ->
    the anti-damping is DISTRIBUTED across several collocated torsion-bar-reading lanes. The notch
    attenuates the SHARED input ahead of ALL of them at once (split-independent), is the least
    feel-affecting option (surgical at 21.4 Hz, exactly unity at DC), and the loop is characterized so it
    is a designed filter, not a guess. Model: |L(21Hz)| 0.875 -> 0.348, margin 1.16 dB -> ~9 dB.

THE FILTER  [eps_v48b_notch_design.py + eps_v48b_cave_model.py, both runnable + validated]
    RBJ peaking-dip, f0=21.4 Hz, Q=5, -8 dB, fs=1000 Hz. Direct-Form I, Q12, int16 coeffs
    b0=4045 b1=-7949 b2=3977 a1=-7949 a2=3926. Measured (cave-exact integer sim): -7.9 dB at 21.4 Hz,
    +0.000 dB at DC (73/73 = exact unity -> zero steady torque offset), pole r=0.979 stable, int32
    accumulator >=2x margin even at full +/-32767 input, states fit int16. y = clamp(acc>>12, +/-25600).

THE CAVE  [v48b_cave_asm.py -- every encoding cross-validated vs >=2 real code.bin instructions]
    Trampoline `jr CAVE` at 0x7FEAC displaces `cmp r0,r8`+`mov r8,r14` (the front of an abs(gp-0x4f60)
    idiom). The cave saves r10/r11/r12, runs the biquad on a FRESH gp-0x4f60 read (independent of r8),
    stores to gp-0x1500, restores r10/r11/r12 + sp, then RE-EXECUTES cmp+mov LAST (so PSW flags are
    correct for the `bge 0x7feb4` at the return) and `jr 0x7FEB0`. Net: register/flag state at 0x7FEB0
    is byte-identical to the original two instructions plus the notch RAM write -- fully transparent.
    Producer FUN_0007f3f8 runs (via FUN_0006bb08) BEFORE all 5 carrier lanes in the 1 kHz task, so the
    filtered copy is same-cycle fresh.

REPOINTS  (7 LIVE carriers; patch only the disp16 field, opcode+dest register unchanged)
    gp-0x4f60 (a0 b0) -> gp-0x1500 (00 eb) at:
      FUN_0002c478 @0x2c480 (type-8),  FUN_000352b4 @0x354d2 & @0x35aa4 (magnitude),
      FUN_0003a382 @0x3a6ca & @0x3a7ca (resonance), FUN_0003b49a @0x3b4a8 (-> FUN_0003a382),
      FUN_0003b66a @0x3b672 (-> damping+boost Factor-A).
    NOT repointed: the 2 mode-gated DORMANT reads (FUN_00034350 @0x34392, FUN_00034a72 @0x34ace) --
    bypassed in stock cal (0xC6498/0xC6499=1), so repointing them buys nothing live and only adds
    surface. Available as an operator option (see V48B handoff). The 6 previously-unclassified readers
    are all classifier / return-center / UDS-diagnostic consumers (subagent-confirmed) -> correctly keep
    the RAW value; none feed the aggregator.

WHY IT IS SAFE  [pre-build; a dedicated adversarial review still gates any flash -- this is a CODE CAVE]
    * Raw gp-0x4f60 / its shadow gp-0x4486 are NEVER touched -> zero interaction with the shadow-lockstep
      (fault 0x17), the 2 hard-shutdown monitors (FUN_00042af8 0x1c, FUN_00043e44 0x1d), or the 2 CAN
      broadcasts. All of them structurally want the raw value and still get it.
    * The cave is register/flag/sp transparent (save+restore r10/r11/r12; re-exec cmp/mov last).
    * Output clamped to +/-25600 -> states stay int16 -> accumulator provably < 2^31 (no overflow).
    * The damping OUTPUT CLAMP BOUND (0xD209C/0xD20A8) + float mirror (0xC6554) -- the no-debounce
      DTC-0x1d trap -- are byte-stock (asserted).
    * Cave region [0xC4B34, 0xC4BBE) asserted all-0xFF before write; trampoline site + all 7 repoint
      sites asserted at their exact stock bytes before patch. The trampoline/CRC/cave mechanics are the
      SAME class flashed on-car in V31P (jr/jarl into 0xC4B34) -- proven plumbing; the NEW risk is the
      cave arithmetic, which is why the assembled image must be Ghidra-re-disassembled before flash.

CRC BLOCKS TOUCHED  (1)
    MAIN 0xC4FFC only -- ratchet 0x454FE + trampoline 0x7FEAC + cave 0xC4B34 + all 7 repoints are inside
    [0x13000, 0xC4FFC). No CAL block edit (unlike V48A). 0xC646C=3564 (4x) untouched.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V48B builder requires assertions; do not run with python -O")

from firmware_paths import FLASHING_ROOT, REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for path in (HERE, FLASHING):
    if path not in sys.path:
        sys.path.insert(0, path)

from encode_eps import OPS, build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks
from v48b_cave_asm import (
    CAVE_BASE, HOOK, RETURN, D_OUT, assemble_cave, gp_field, jr,
)

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

V48B_TAG = "LKAS-4x-V38base-ratchet-notch21p4hz-Q12-DFI-gp1500"
V48B_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V48B-{V48B_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v48b_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA        # bne +198 -> 0x455c4
RATCHET_NEW_HW = 0x65B5          # br  +198 -> 0x455c4
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5

# ---- the trampoline hook: displaces cmp r0,r8 (e0 41) + mov r8,r14 (08 70) -----------------------
HOOK_STOCK = bytes.fromhex("e0410870")   # cmp r0,r8 ; mov r8,r14

# ---- the 7 LIVE carrier repoint sites: ld.h -0x4f60[gp],rX -> ld.h -0x1500[gp],rX ----------------
# stock = 24 XX a0 b0 ; patched = 24 XX 00 eb  (only bytes [site+2:site+4] change).
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
DISP_1500 = gp_field(D_OUT)      # 0xEB00, the filtered-copy output cell

# ---- SAFETY: the damping OUTPUT CLAMP BOUND + its float mirror MUST stay byte-stock ---------------
CLAMP_INT_STOCK = {
    0xD209C: (2, "clamp m10 header"), 0xD209E: (300, "clamp m10 X0"), 0xD20A0: (800, "clamp m10 X1"),
    0xD20A2: (512, "clamp m10 Y0"), 0xD20A4: (1024, "clamp m10 Y1"),
    0xD20A8: (2, "clamp m11 header"), 0xD20AA: (300, "clamp m11 X0"), 0xD20AC: (800, "clamp m11 X1"),
    0xD20AE: (512, "clamp m11 Y0"), 0xD20B0: (1024, "clamp m11 Y1"),
}
CLAMP_FLOAT_ADDR = 0xC6554
CLAMP_FLOAT_STOCK = struct.pack("<ffff", 300.0, 800.0, 0.5, 1.0)

# Cal cells that MUST remain exactly as V38 left them (nothing under test here is cal).
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x) -- UNTOUCHED, forward authority preserved"),
    0xC4120: (0x01, "type-8 slot-8 sum gate -- stock (V48A muted it; V48B does NOT)"),
    0xC6498: (0x01, "damping mode byte -- stock (keeps 0x34392 read dormant/bypassed)"),
    0xC6499: (0x01, "boost mode byte -- stock (keeps 0x34ace read dormant/bypassed)"),
    0xC67B8: (1024, "FUN_0003a382 uVar27 Y0 -- stock (V48A cut it; V48B does NOT)"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole -- stock"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- stock"),
}
# The 2 dormant reads MUST stay at stock -0x4f60 (we deliberately do NOT repoint them).
DORMANT_SITES = {0x34392: "FUN_00034350 damping (dormant)", 0x34ACE: "FUN_00034a72 boost (dormant)"}

MAIN_BLOCK = (0x13000, 0xC4FFC)  # every V48B edit lives here; CRC @0xC4FFC
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


def assert_repoint_sites_stock(code):
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1, f"repoint site 0x{addr:05X} opcode/reg word moved ({note})"
        assert u16(code, addr + 2) == DISP_4F60, \
            f"repoint site 0x{addr:05X} disp is not stock -0x4f60 ({note})"
    for addr, note in DORMANT_SITES.items():
        assert u16(code, addr + 2) == DISP_4F60, f"dormant site 0x{addr:05X} disp moved ({note})"


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    # ratchet at stock bne; V48B APPLIES the fix like V42/V45/V47/V48A.
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, "0x454FE is not the stock bne halfword"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET), \
        "0x454FE does not decode as (BNE, 0x455C4) in V38"
    # trampoline site holds the exact stock displaced instructions.
    assert bytes(code[HOOK:HOOK + 4]) == HOOK_STOCK, \
        f"0x{HOOK:05X} is not stock `cmp r0,r8; mov r8,r14` ({bytes(code[HOOK:HOOK+4]).hex()})"
    # cave region is entirely 0xFF (V38, not V39-cave).
    cave_bytes, _ = assemble_cave()
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == b"\xff" * len(cave_bytes), \
        "cave region is not all-0xFF -- baseline must be V38 (no V39 cave)"
    assert bytes(code[CAVE_BASE + len(cave_bytes):0xC4FF0]) == \
        b"\xff" * (0xC4FF0 - CAVE_BASE - len(cave_bytes)), "cave tail not 0xFF"
    assert_repoint_sites_stock(code)
    assert_clamp_stock(code, "V38 baseline")
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
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
    cave_bytes, cave_ann = assemble_cave()

    # ---- CHANGE 1 (CODE, 1 byte): the state-4 ratchet fix ---------------------------------------
    print("  CHANGE 1 (CODE, 1 byte) -- state-4 ratchet fix:")
    before_cond, before_target = decode_bcond(code, RATCHET_ADDR)
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    after_cond, after_target = decode_bcond(code, RATCHET_ADDR)
    assert (before_cond, after_cond) == (COND_BNE, COND_BR)
    assert before_target == after_target == RATCHET_TARGET, "branch target moved"
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1], "high byte of the branch changed"
    print(f"    0x{RATCHET_ADDR:05X}: bne -> br 0x{after_target:05X}")

    # ---- CHANGE 2 (CODE, 138 bytes): write the notch cave ---------------------------------------
    print(f"  CHANGE 2 (CODE, {len(cave_bytes)} bytes) -- notch biquad cave @0x{CAVE_BASE:05X}:")
    code[CAVE_BASE:CAVE_BASE + len(cave_bytes)] = cave_bytes
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == cave_bytes
    print(f"    [0x{CAVE_BASE:05X},0x{CAVE_BASE + len(cave_bytes):05X})  {len(cave_ann)} instrs")

    # ---- CHANGE 3 (CODE, 4 bytes): plant the trampoline -----------------------------------------
    print(f"  CHANGE 3 (CODE, 4 bytes) -- trampoline @0x{HOOK:05X}:")
    tramp = jr(CAVE_BASE, HOOK)
    code[HOOK:HOOK + 4] = tramp
    assert bytes(code[HOOK:HOOK + 4]) == tramp
    print(f"    0x{HOOK:05X}: {HOOK_STOCK.hex()} -> {tramp.hex()}   jr 0x{CAVE_BASE:05X}")

    # ---- CHANGE 4 (CODE, 7x2 bytes): repoint the live carriers -----------------------------------
    print("  CHANGE 4 (CODE, 7 x 2 bytes) -- repoint live carriers gp-0x4f60 -> gp-0x1500:")
    for addr, w1, note in REPOINT_SITES:
        assert u16(code, addr) == w1 and u16(code, addr + 2) == DISP_4F60
        struct.pack_into("<H", code, addr + 2, DISP_1500)
        assert u16(code, addr + 2) == DISP_1500
        assert u16(code, addr) == w1, "opcode/register word must not change on repoint"
        print(f"    0x{addr:05X}: disp {DISP_4F60:#06x} -> {DISP_1500:#06x}   {note}")

    # ---- nothing else may move ------------------------------------------------------------------
    assert_clamp_stock(code, "V48B")
    for addr, note in DORMANT_SITES.items():
        assert u16(code, addr + 2) == DISP_4F60, f"dormant site 0x{addr:05X} must stay raw ({note})"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address in (0xC4120, 0xC6498, 0xC6499) else u16(code, address)
        assert got == value, f"0x{address:05X} moved ({note})"

    # ---- CRC coverage: everything is in the single MAIN block ------------------------------------
    for addr in (RATCHET_ADDR, CAVE_BASE, CAVE_BASE + len(cave_bytes) - 1, HOOK):
        assert owning_block(code, addr) == MAIN_BLOCK, f"0x{addr:05X} not in MAIN_BLOCK"
    for addr, _w, _n in REPOINT_SITES:
        assert owning_block(code, addr) == MAIN_BLOCK, f"repoint 0x{addr:05X} not in MAIN_BLOCK"
    old_crc = struct.unpack_from("<I", code, MAIN_BLOCK[1])[0]
    new_crc = zlib.crc32(code[MAIN_BLOCK[0]:MAIN_BLOCK[1]]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_BLOCK[1], new_crc)
    print(f"  CRC [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X}) @0x{MAIN_BLOCK[1]:X}: "
          f"0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ----------------------------------------------------------------------
    diffs, runs = changed_runs(baseline, code)
    allowed = {RATCHET_ADDR}
    allowed.update(range(CAVE_BASE, CAVE_BASE + len(cave_bytes)))
    allowed.update(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        allowed.update({addr + 2, addr + 3})
    allowed.update(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    assert set(diffs) <= allowed, f"unexpected V48B-vs-V38 bytes: {sorted(set(diffs) - allowed)}"

    crc_bytes = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    intended = {RATCHET_ADDR} | set(range(CAVE_BASE, CAVE_BASE + len(cave_bytes))) \
        | set(range(HOOK, HOOK + 4))
    for addr, _w, _n in REPOINT_SITES:
        intended.update({addr + 2, addr + 3})
    non_crc = set(diffs) - crc_bytes
    # Every non-CRC changed byte must be an intended edit...
    assert non_crc <= intended, f"unexpected non-CRC diffs: {sorted(non_crc - intended)}"
    # ...and the only intended bytes that legitimately did NOT change are cave bytes whose assembled
    # value equals the pre-existing 0xFF fill (e.g. the 0xFF in `addi -16,sp,sp`'s immediate).
    for b in intended - non_crc:
        assert CAVE_BASE <= b < CAVE_BASE + len(cave_bytes) and cave_bytes[b - CAVE_BASE] == 0xFF, \
            f"intended edit at 0x{b:05X} did not land and is not a 0xFF cave byte"
    assert len(intended) == 1 + len(cave_bytes) + 4 + 2 * len(REPOINT_SITES), "intended byte count"

    assert_crc_chain(code, "V48B plain")
    assert walk(bytes(code), label="V48B") == 0
    assert walk_all_blocks(bytes(code), label="V48B") == 0

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V48B emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V48B RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V48B RWD readback")
    assert walk(readback, label="V48B RWD readback") == 0
    assert walk_all_blocks(readback, label="V48B RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), "ratchet lost in RWD"
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(cave_bytes)]) == cave_bytes, "cave lost in RWD"
    assert bytes(readback[HOOK:HOOK + 4]) == tramp, "trampoline lost in RWD"
    for addr, w1, _n in REPOINT_SITES:
        assert u16(readback, addr) == w1 and u16(readback, addr + 2) == DISP_1500, "repoint lost in RWD"
    for addr, _n in DORMANT_SITES.items():
        assert u16(readback, addr + 2) == DISP_4F60, "dormant site changed in RWD"
    assert_clamp_stock(readback, "V48B RWD readback")
    assert u16(readback, 0xC646C) == 3564, "4x forward gain not preserved in RWD readback"

    print(f"\n  V48B-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "CHANGE 1: state-4 ratchet branch nibble"
        elif first == HOOK:
            kind = "CHANGE 3: trampoline jr -> cave"
        elif CAVE_BASE <= first < CAVE_BASE + len(cave_bytes):
            kind = "CHANGE 2: notch biquad cave"
        elif any(first == a + 2 for a, _w, _n in REPOINT_SITES):
            kind = "CHANGE 4: carrier repoint (disp16)"
        elif MAIN_BLOCK[1] <= first < MAIN_BLOCK[1] + 4:
            kind = "CRC trailer (MAIN)"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:  {V38_SHA256}")
    print(f"  V48B SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V48B RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd, cave_ann


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V48B-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V48B_OUT)]
    for path in stale + [V48B_OUT, BIN_OUT, V48B_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V48B = V38 + ratchet fix + 21.4 Hz NOTCH (code cave, keeps 4x). CODE-CAVE build.")
    print("  CHANGE 1 (CODE, 1 byte)     0x454FE  bne -> br            (ratchet fix, carried)")
    print(f"  CHANGE 2 (CODE, 138 bytes)  0x{CAVE_BASE:05X}  notch biquad cave    (DF-I Q12, 21.4 Hz)")
    print(f"  CHANGE 3 (CODE, 4 bytes)    0x{HOOK:05X}  jr -> cave           (trampoline)")
    print("  CHANGE 4 (CODE, 7x2 bytes)  repoint live carriers gp-0x4f60 -> gp-0x1500 (filtered copy)")
    print("  UNTOUCHED: raw gp-0x4f60/shadow, monitors, CAN, 0xC646C=3564 (4x), clamp trap 0xD209C/0xC6554.")
    print("  NOT repointed: 2 dormant reads 0x34392/0x34ace (operator option).\n")
    code, rwd, cave_ann = build()

    os.makedirs(os.path.dirname(V48B_OUT), exist_ok=True)
    with open(V48B_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V48B_OUT + ".tmp", V48B_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V48B_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  *** CODE CAVE -- NOT FLASHED, NOT YET SAFETY-SIGNED-OFF. ***")
    print("  Before any flash: Ghidra-re-disassemble the built image at the cave + hook + repoints,")
    print("  and run a dedicated adversarial pre-flash review. Flash only on explicit operator")
    print("  instruction naming the file and the bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
