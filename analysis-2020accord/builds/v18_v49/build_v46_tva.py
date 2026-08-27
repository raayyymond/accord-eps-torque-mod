"""
builds/v18_v49/build_v46_tva.py -- V46 = V38 + the KEPT state-4 ratchet fix + LEVER A (the Stage A carrier filter).

=======================================================================================================
V46 IN ONE LINE
    Keep the 4x LKAS gain and the CONFIRMED state-4 ratchet fix. Add ONE calibration halfword that
    turns FUN_0003a382's Stage A from an exact unity passthrough into a ~4.8 Hz first-order low-pass,
    cutting the 21 Hz self-oscillation loop gain ~12 dB while preserving low-frequency road feel.
    DROP V45's failed hands-off governor-slew lever entirely (0xC6206 stays STOCK 512).

WHY THIS LEVER  [the vibration is a self-excited base-assist limit cycle, NOT a command-path symptom]
    The ~21.4 Hz vibration is command-independent (present at near-zero LKAS command, gone with OP off,
    peaks ~5 mph) -- the signature of a self-excited limit cycle in the base-assist torque-sensor
    feedback loop, not a forced response to the LKAS command. Every prior vibration lever (V39 r24,
    V42 r26, V43 Stage-C pole, V44 hands-off damping floor, V45 hands-off slew) lived on the command
    path or was too weak; none reduced the loop's 21 Hz gain.

    FUN_0003a382 Stage A is a feed-forward torque-tracking residual: errorterm = sensed Sensor-B torque
    (gp-0x4f60) - modeled torque (gp-0x6ad6), passed to the motor command at UNITY GAIN, ZERO LAG
    (pole cal 0xC6450 = 1024 = 2^10 divides out exactly => output == input every cycle, flat at ALL
    frequencies including 21 Hz), then summed into the aggregator gp-0x6b94 with ASSIST (positive)
    polarity -- confirmed reinforcing, not opposing (contrasted vs friction's all-negative table and
    damping's velocity-keyed conditional negation; Stage A has NEITHER). At the plant's 21 Hz
    resonance (Q~=13.6, ~180 deg phase flip) this unity in-phase feedback closes a positive-feedback
    loop that sustains the ring. Lowering 0xC6450 1024 -> 32 makes Stage A a first-order low-pass with
    corner ~= 32/1024 * 1000/(2*pi) ~= 4.8 Hz: everything below a few Hz (the useful torque-tracking /
    road feel) passes essentially unchanged; 21 Hz is cut ~12-13 dB, pulling the loop gain back under 1.

    Directly mirrors V43's already-FLASHED, fault-free pole edit on the SIBLING constant 0xC644A
    (Stage C) in the SAME function -- but Stage A is the untouched, exact-unity, ZERO-LAG (in-phase)
    stage, where V43's Stage C was a 90-deg-shifted derivative branch (which fixed nothing -> phase,
    not gain, is why Stage A is the suspect).

HONEST CAVEATS  [stated, not hidden]
    - Stage A is NOT engagement-gated (RoadFeel, disasm-verified): it computes every cycle in MANUAL
      driving too. Expect a road-feel effect -- a frequency-NARROW one: >~5 Hz road texture / kickback
      is attenuated; driver inputs, effort, on-center, and assist accuracy (all <5 Hz) are preserved.
      It adds no heaviness and no lag. Comparable-or-milder than V43's already-driven sibling edit.
    - Efficacy is control-theory inference, not a measurement: it rests on Stage A carrying significant
      21 Hz content and on gp-0x6ad6 (the model) NOT already carrying a 21 Hz component (no evidence it
      does -- it is DC/slow by construction). Stage B (a window-clamped accumulator) is an unruled-out
      wildcard. Worst case is a NULL (like V43's sibling), not a backfire -- filtering a reinforcing
      term cannot destabilize.

WHY IT IS SAFE  [blast radius byte-verified, RoadFeel this session]
    - 0xC6450 (tp+0x7450) has exactly ONE real reader: 0x3a7f0 inside FUN_0003a382. The other two
      "7450" operand hits are branch-target-text false positives (same class this kit has hit before).
    - Stage A's RAM state gp-0x367c: exactly one reader + one writer, both inside FUN_0003a382. NO
      shadow-lockstep pair, NO float mirror, NO external consumer -- a clean single-site scalar.
    - The lane's sole caller is FUN_0002214a (the confirmed ~1 kHz control task).
    - This is the OPPOSITE risk class from V40 (which bricked by REMOVING a rate limit): lowering a
      pole only ADDS filtering; it cannot snap-to-target or remove a guard.

WHAT V46 IS NOT
    - NOT V45's governor-slew lever. 0xC6206 stays STOCK 512 (asserted). V45 was FLASHED and fixed
      nothing; dropped entirely.
    - NOT the dampers. Factor C (0xD27C6/0xD27DA) and Factor E stay STOCK -- that is V47.
    - NOT r24 (V39) / r26 (V42) / Stage-C pole 0xC644A (V43). All stay stock (V46 is cut from V38).

    A SINGLE vibration variable, cleanly attributable, independently backable-out -- this kit's only
    reliably-successful change class (V29, V31, V37, V42-change-1 were all cal-only).
=======================================================================================================
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

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V46 builder requires assertions; do not run with python -O")

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

V46_TAG = "LKAS-4x-V38base-state4-ratchet-off-stageA-carrier-pole32"
V46_OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V46-{V46_TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v46_plain_image.bin"))

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]))

# ---- CARRIED THROUGH: the state-4 ratchet fix (V42 Change 1, CONFIRMED on-car) -------------------
# 0x454fe: `bne 0x455c4` -> `br 0x455c4`. Only the low condition nibble moves; the displacement and
# therefore the target are provably unchanged (decoded both, asserted below).
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA        # bne +198 -> 0x455c4   (V38 stock, ratchet NOT yet fixed)
RATCHET_NEW_HW = 0x65B5          # br  +198 -> 0x455c4
RATCHET_TARGET = 0x455C4
COND_BNE, COND_BR = 0xA, 0x5
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))    # ld.bu -0x67fa[gp],r12
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))        # cmp 0x4,r12

# ---- THE VIBRATION LEVER (LEVER A): Stage A carrier pole 1024 -> 32 -------------------------------
# FUN_0003a382 Stage A pole cal (tp+0x7450). 1024 = 2^10 = exact unity passthrough; 32 = first-order
# low-pass, corner ~4.8 Hz. Stored little-endian: 0x0400 -> 0x0020 (both bytes move).
STAGEA_ADDR = 0xC6450
STAGEA_STOCK = 1024              # exact unity (output == input every cycle)
STAGEA_NEW = 32                  # ~4.8 Hz first-order low-pass (cuts 21 Hz ~12 dB)

MAIN_BLOCK = (0x13000, 0xC4FFC)  # holds the ratchet byte; CRC @0xC4FFC
CAL_BLOCK = (0xC6000, 0xC6FFC)   # holds the Stage A pole edit; CRC @0xC6FFC

# Damping-floor cells: MUST remain STOCK 0 -- V46 does NOT carry the dampers (that is V47).
DAMP_Y0_CELLS = (0xD27C6, 0xD27DA)

# r26 adaptive-gain Y rows (V42's falsified target): MUST remain STOCK (V46 is cut from V38).
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)
RATE_A_Y_OFFSET = 0xA
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))

# Cal cells that MUST remain exactly as V38 left them (V46 touches ONLY 0xC6450 in this block).
STOCK_CALS = {
    0xC646C: (3564, "LKAS output gain (V38 4x)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC6202: (4762, "governor nominal ceiling"),
    0xC6206: (512, "governor slew step, HANDS-OFF -- untouched (V45's failed lever, dropped)"),
    0xC6208: (205, "governor slew step, HANDS-ON -- untouched"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- left at unity (V43 reverted; V46 edits SIBLING)"),
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
    """Decode a V850 Bcond halfword -> (cond, absolute_target). Returns None if not a Bcond."""
    halfword = struct.unpack_from("<H", code, address)[0]
    if (halfword >> 7) & 0xF != 0xB:
        return None
    cond = halfword & 0xF
    disp = (((halfword >> 11) & 0x1F) << 4) | (((halfword >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return cond, address + disp


def crc_block_map(code):
    """Follow the block linked list EXACTLY as stored (all 50 blocks, no bridge)."""
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


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[0xC4B34:0xC4B60]) == b"\xff" * 0x2C, "V39 cave present; baseline must be V38"

    # Ratchet must be at STOCK bne -- V46 is the build that APPLIES the fix (like V42), not one that
    # inherits it. Decodes as (BNE, 0x455c4).
    assert struct.unpack_from("<H", code, RATCHET_ADDR)[0] == RATCHET_STOCK_HW, \
        f"0x{RATCHET_ADDR:05X} is not the stock `bne` halfword 0x{RATCHET_STOCK_HW:04X}"
    assert decode_bcond(code, RATCHET_ADDR) == (COND_BNE, RATCHET_TARGET), \
        "0x454FE does not decode as (BNE, 0x455C4) in the V38 baseline"
    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR):
        assert bytes(code[address:address + len(expected)]) == expected, \
            f"instruction context at 0x{address:05X} does not match expected V38 bytes"

    # Stage A pole must be at stock 1024 (exact unity) -- proving the edit is real, not a no-op.
    assert struct.unpack_from("<H", code, STAGEA_ADDR)[0] == STAGEA_STOCK, \
        f"0x{STAGEA_ADDR:05X} is {struct.unpack_from('<H', code, STAGEA_ADDR)[0]}, expected stock {STAGEA_STOCK}"

    # No dampers (V47's territory): Factor C floor still 0.
    for cell in DAMP_Y0_CELLS:
        assert struct.unpack_from("<H", code, cell)[0] == 0, \
            f"0x{cell:05X} damping Y[0] is nonzero -- baseline must be pre-V44 (V38)"
    # r26 gain surface is stock.
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], \
            f"r26 record 0x{base:05X} Y row is not stock -- baseline must be V38"

    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else struct.unpack_from("<H", code, address)[0]
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
    print("  CHANGE 1 (CODE, 1 byte) -- the CONFIRMED state-4 ratchet fix:")
    before_cond, before_target = decode_bcond(code, RATCHET_ADDR)
    struct.pack_into("<H", code, RATCHET_ADDR, RATCHET_NEW_HW)
    after_cond, after_target = decode_bcond(code, RATCHET_ADDR)
    print(f"    0x{RATCHET_ADDR:05X}: 0x{RATCHET_STOCK_HW:04X} -> 0x{RATCHET_NEW_HW:04X}   "
          f"bne 0x{before_target:05X} -> br 0x{after_target:05X}")
    assert (before_cond, after_cond) == (COND_BNE, COND_BR)
    assert before_target == after_target == RATCHET_TARGET, "branch target moved"
    assert code[RATCHET_ADDR + 1] == baseline[RATCHET_ADDR + 1], "high byte of the branch changed"

    # ---- CHANGE 2 (CAL, 1 halfword): Stage A carrier pole 1024 -> 32 -----------------------------
    print("  CHANGE 2 (CAL, 1 halfword) -- Stage A carrier pole (LEVER A):")
    struct.pack_into("<H", code, STAGEA_ADDR, STAGEA_NEW)
    print(f"    0x{STAGEA_ADDR:05X}: {STAGEA_STOCK} -> {STAGEA_NEW}   "
          f"(FUN_0003a382 Stage A: exact unity -> ~4.8 Hz low-pass; cuts 21 Hz ~12 dB)")
    assert struct.unpack_from("<H", code, STAGEA_ADDR)[0] == STAGEA_NEW

    # Nothing else may move: dampers still stock, r26 still stock, all tracked cals still stock.
    for cell in DAMP_Y0_CELLS:
        assert struct.unpack_from("<H", code, cell)[0] == 0, "damping floor crept in (that is V47)"
    for i, base in enumerate(RATE_A_RECORDS):
        assert struct.unpack_from("<4h", code, base + RATE_A_Y_OFFSET) == RATE_A_Y_STOCK[i], "r26 moved"
    for address, (value, note) in STOCK_CALS.items():
        got = code[address] if address == 0xC64A3 else struct.unpack_from("<H", code, address)[0]
        assert got == value, f"0x{address:05X} moved ({note})"

    # ---- CRC coverage ---------------------------------------------------------------------------
    ratchet_block = owning_block(code, RATCHET_ADDR)
    assert ratchet_block == MAIN_BLOCK, f"ratchet lands in {ratchet_block}, expected {MAIN_BLOCK}"
    stagea_block = owning_block(code, STAGEA_ADDR)
    assert stagea_block == CAL_BLOCK, f"Stage A edit lands in {stagea_block}, expected {CAL_BLOCK}"
    print(f"  CRC coverage: ratchet 0x{RATCHET_ADDR:05X} -> [0x{MAIN_BLOCK[0]:X},0x{MAIN_BLOCK[1]:X})")
    print(f"  CRC coverage: StageA  0x{STAGEA_ADDR:05X} -> [0x{CAL_BLOCK[0]:X},0x{CAL_BLOCK[1]:X})")

    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ----------------------------------------------------------------------
    allowed = {RATCHET_ADDR, STAGEA_ADDR, STAGEA_ADDR + 1}
    for block in (MAIN_BLOCK, CAL_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V46-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    # 1 ratchet + 2 Stage A (1024=0x0400 -> 32=0x0020, both bytes move) + two 4-byte CRC trailers = 11.
    assert len(diffs) == 11, f"expected exactly 11 changed bytes vs V38, got {len(diffs)}"

    # ---- everything else byte-identical to V38 --------------------------------------------------
    assert bytes(code[START:RATCHET_ADDR]) == bytes(baseline[START:RATCHET_ADDR]), "code before ratchet moved"
    assert bytes(code[RATCHET_ADDR + 1:0xBF000]) == bytes(baseline[RATCHET_ADDR + 1:0xBF000]), \
        "code after ratchet moved"
    assert bytes(code[0xBF000:0xC4FFC]) == bytes(baseline[0xBF000:0xC4FFC]), "cal edit in 0xBF000-0xC4FFC"
    assert bytes(code[0xC5000:0xC6000]) == bytes(baseline[0xC5000:0xC6000]), "cap tables moved"
    cal_diffs = {i for i in range(0xC6000, 0xC7000) if code[i] != baseline[i]}
    assert cal_diffs <= allowed, f"unexpected 0xC6000-block bytes: {sorted(cal_diffs - allowed)}"
    assert bytes(code[0xC7000:0xE4000]) == bytes(baseline[0xC7000:0xE4000]), \
        "0xC7000-0xE4000 moved (incl. 0xD2xxx damping -- V46 must NOT touch it)"
    assert bytes(code[0xE4000:0xE6000]) == bytes(baseline[0xE4000:0xE6000]), "setpoint records moved"
    assert bytes(code[0xE6000:0x100000]) == bytes(baseline[0xE6000:0x100000]), "tail moved"

    assert_crc_chain(code, "V46 plain")
    assert walk(bytes(code), label="V46") == 0
    assert walk_all_blocks(bytes(code), label="V46") == 0

    # ---- RWD round-trip -------------------------------------------------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    assert_x31_checksum(rwd, "V46 emitted")
    emitted = parse_x31(rwd)
    assert emitted["headers"] == source_info["headers"]
    assert emitted["blocks"] == source_info["blocks"]
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V46 RWD does not decode back to the built image"
    readback = full_image(decoded)
    assert_crc_chain(readback, "V46 RWD readback")
    assert walk(readback, label="V46 RWD readback") == 0
    assert walk_all_blocks(readback, label="V46 RWD readback") == 0
    assert decode_bcond(readback, RATCHET_ADDR) == (COND_BR, RATCHET_TARGET), \
        "the ratchet fix did not survive the RWD round-trip"
    assert struct.unpack_from("<H", readback, STAGEA_ADDR)[0] == STAGEA_NEW, \
        "the Stage A pole edit did not survive the RWD round-trip"
    for cell in DAMP_Y0_CELLS:
        assert struct.unpack_from("<H", readback, cell)[0] == 0, "damping floor in RWD readback"

    print(f"\n  V46-vs-V38: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        if first == RATCHET_ADDR:
            kind = "CHANGE 1: state-4 ratchet branch nibble"
        elif first == STAGEA_ADDR:
            kind = "CHANGE 2: Stage A carrier pole 1024 -> 32 (LEVER A)"
        elif first in (MAIN_BLOCK[1], CAL_BLOCK[1]):
            kind = "CRC trailer"
        else:
            kind = "UNEXPECTED"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256: {V38_SHA256}")
    print(f"  V46 SHA-256: {hashlib.sha256(code).hexdigest()}")
    print(f"  V46 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V46-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(V46_OUT)]
    for path in stale + [V46_OUT, BIN_OUT, V46_OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V46 = V38 + KEPT ratchet fix + LEVER A (Stage A carrier pole 1024 -> 32).")
    print("  CHANGE 1 (CODE, 1 byte)  0x454FE  bne 0x455C4 -> br 0x455C4   (confirmed ratchet fix)")
    print("  CHANGE 2 (CAL, 1 halfword) 0xC6450  1024 -> 32   (Stage A: unity -> ~4.8 Hz low-pass)")
    print("  DROPPED: V45's hands-off governor slew (0xC6206 stays STOCK 512).")
    print("  KEPT: 4x LKAS gain 0xC646C=3564. r24/r26/Stage-C/dampers all stock.\n")
    code, rwd = build()

    os.makedirs(os.path.dirname(V46_OUT), exist_ok=True)
    with open(V46_OUT + ".tmp", "wb") as handle:
        handle.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as handle:
        handle.write(code)
    os.replace(V46_OUT + ".tmp", V46_OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(V46_OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  NOT FLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
