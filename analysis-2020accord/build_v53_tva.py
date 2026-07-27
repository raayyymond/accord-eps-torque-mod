"""
build_v53_tva.py -- V53 = FOURFRAME2 (V38 + the fixed four-frame telemetry cave) + the low-speed steer
lockout dropped to ZERO.

=======================================================================================================
V53 IN ONE LINE
    Take FOURFRAME2 byte-for-byte -- V38 calibration, the four-frame passive read-only CAN telemetry
    cave with the STRB/SSAM defect fixed, authority + reference-model channels -- and add ONE
    calibration halfword: `0xC62EA` 320 -> 0, i.e. the EPS's minimum-steer-speed lockout goes from
    4.995 km/h (3.104 mph) to 0.

WHY THE TWO CHANGES BELONG IN THE SAME BUILD
    They are the two experiments the kit is blocked on, and they are not merely compatible -- the
    lockout edit CREATES the condition the telemetry needs to observe.

    - FOURFRAME2 answers "what is `gp-0x6966` (authority) doing at the moment of the vibration", which
      decides the DIRECTION of the candidate `0xC6AF0` edit. Two analysis passes reached OPPOSITE
      conclusions from the same static data one turn apart, because both hinged on a runtime value.
      It also captures all three terms of the `FUN_0003a382` loop (`gp-0x4f60` sensor, `gp-0x6ad6`
      model, `gp-0x6ad4` output) so the lane's transfer function can be IDENTIFIED, not inferred.
    - The `0xC62EA` edit populates the empty "engaged at low speed" cell of the route-13 A/B/C split.
      On route 13, `STEER_CONTROL_ACTIVE` is a deterministic function of speed (ST=3 *is* the sub-5
      km/h gate), so cells B and C have ZERO speed overlap and "needs applied torque" cannot be fully
      separated from "needs v > 1.4 m/s". Lowering the gate breaks that collinearity in a parking lot.

    Stacking them means ONE flash and ONE drive answers both. The risk classes do not interact: the
    cave is read-only and lives at `0xC4B34` in the MAIN CRC block; the cal is one halfword at
    `0xC62EA` in the `0xC6000` CAL block, with exactly one reader.

THE LOCKOUT LEVER  [located 2026-07-24, analysed, cal-only, never before built]
    `0xC62EA` (`tp+0x72EA`) = 320 = 4.995 km/h is the LO half of a two-sided speed window compared
    against VOTED vehicle speed `gp-0x6a5e`, at the top of `FUN_00028ea6` = the LIVE ~1 kHz steer
    torque arbitration:
        0x28EB6  ld.hu 0x72e8[tp],r2    ; r2 = 12800  (HI bound, 199.8 km/h)  -- UNTOUCHED
        0x28EBC  ld.hu 0x72ea[tp],lp    ; lp =   320  (LO bound)              <== THE LEVER
        0x290C8  cmp r2,r10  / setfnh r9   ; r9 = (speed <= 12800)
        0x290D2  cmp lp,r10  / setfnc r7   ; r7 = (speed >=   320)   <== unsigned >=
    Failing the window is the ONLY writer of `STEER_STATUS = 3` (`0x29192 mov 3,r6` /
    `0x29194 st.b r6,-0x6807[gp]`), and `STEER_STATUS <= 2` is a precondition on all four live
    `STEER_CONTROL_ACTIVE = 1` writes AND on the authority ramp `gp-0x69b0` -- so this is real
    authority, not a label. Setting the LO bound to 0 makes `speed >= 0` unconditionally true.

    WHY 0 AND NOT 64 (the previously-suggested 1 km/h): the standstill case is ALREADY unlocked --
    `gp-0x68b3` (the window bypass) is written in `FUN_0004d0d0` only when `gp-0x6a62 == 0`, i.e.
    EXACTLY at true standstill. So stock already permits 0 km/h and forbids 1-319 counts; 0 vs 64
    differ only in whether that 0-1 km/h sliver is covered, and 0 removes the discontinuity rather
    than moving it. Operator instruction, 2026-07-27: minimum steer speed 0.

WHY IT IS SAFE  [each point verified, not assumed]
    - EXACTLY ONE READER, re-confirmed this session by an independent Python scan of the whole code
      region `[0x13000,0xC4FFC)` covering BOTH V850E2 encodings: the halfword `0x72EB` (the `disp|1`
      form the `ld.hu` actually uses) occurs exactly once image-wide, at `0x28EBE` -- the disp field
      of `0x28EBC`. The single bare-`0x72EA` hit is at ODD address `0x21167`, so it cannot be an
      instruction operand. No `movea <base>,tp,rX` table base can reach it either: the nearest below
      is `0x7010`, a 4-point LERP record (X = 0/640/3200/6400) ending hundreds of bytes short.
    - NO float mirror and NO shadow-lockstep twin. Both window cals are plain u16 `ld.hu` in the
      compact `0xC6xxx` block that every build in this kit already edits. This is NOT the V27/`0x17`
      failure class (that was a shadowed pair written on one leg only).
    - SNA DETECTION IS NOT DEFEATED. The invalid-speed sentinel is `0x7FFF` = 32767, which still
      fails the UNTOUCHED HI bound (12800), so an implausible speed keeps failing the window exactly
      as it does at stock. Lowering the LO bound cannot mask a bad sensor.
    - The speed VALUE and its plausibility test are untouched. `KFC_WHEELSPD_PLAUSI` / `KFC_VSA_1D0`
      are hard-fault (motor-off) eligible; the `(cell + 0x1900) < 0x9601` voter test and the shadowed
      `gp-0x6a46`/`gp-0x4ca4` pair are NOT edited. Only the CONSUMER threshold moves.
    - `0xC62EE` (the OTHER 320-count gate, `0x2d84a`) IS LEFT STOCK, deliberately, and asserted below.
      It is not a lockout -- it is a speed PERMISSIVE inside a CAN-COMMANDED assist-shutdown task,
      unreachable without a remote request bit. Touching it (especially raising it) is off-limits.
    - It is the OPPOSITE risk class from V40. V40 wrote `0xFFFF` into a governor slew guard, which
      made the guard NEVER FIRE -> snap-to-target -> DTC 0x1d -> motor off. Here nothing is removed
      from a limiter: a comparison threshold is WIDENED at its low end, on a gate whose failing branch
      only reports a status and withholds assist. There is no path by which "assist permitted at
      2 mph" produces an unbounded command -- every clamp, governor, and derate downstream is stock.

WHAT V53 IS NOT
    - NOT a vibration lever. No filter, pole, gain, damper or authority LERP moves. `0xC6AF0` stays
      stock -- its edit direction is still UNRESOLVED and this build is what will resolve it.
    - It does NOT carry the V42 state-4 ratchet fix (`0x454FE` stays stock `0x65BA`), because
      FOURFRAME2 does not and the operator specified a V38 base. This matches the image on the car
      today, so V53 is not a regression -- but it is a KNOWN, CONFIRMED root-cause fix that is absent.
      One byte, already validated on-car. Say the word and it goes in.
    - NOT a change to `0xC646C` (still V38's 4x = 3564) or to the `0xC61B2`/`0xC61B4` clamps.

⚠ EXPECTED BEHAVIOUR CHANGE, STATED PLAINLY
    Below ~3 mph the EPS will now accept LKAS torque where it previously refused. openpilot is not
    the obstacle (`CP.minSteerSpeed = 0.0`), but the StarPilot fork on the car runs
    `steerAtStandstill = False`, so at a dead stop openpilot still will not command. The new
    behaviour window is roughly 0.1-3 mph -- creep, parking lots, stop-and-go. Static-friction steer
    effort at walking pace is high; expect the EPS to work harder there than it ever has on this car.

⚠ ALIASING LIMIT -- INHERITED FROM FOURFRAME2, UNCHANGED
    The cave still fires from the 100 Hz CAN-330 packer hook and samples instantaneously. A true
    mechanical mode at 78.91 Hz folds to EXACTLY 21.09 Hz at 100.000 Hz. FFT-ing this telemetry
    CANNOT distinguish 21.09 from 78.91. That is deliberate: the cave has never once transmitted, so
    changing the transmit rate in the same step would make a null uninterpretable. Prove TX first.

PROVENANCE OF THE CAVE  [why this file is thin]
    The 853-byte cave is NOT re-typed here -- it is IMPORTED from `build_vfourframe_tva.py`, the file
    that produced `_vfourframe2_plain_image.bin`, so there is no transcription surface at all. The
    build then asserts that V53 differs from that exact image by EXACTLY six bytes: the two halves of
    `0xC62EA` and the four-byte CAL-block CRC trailer at `0xC6FFC`. Every encoder self-check, both
    mailbox gates, and the STRB=0x01 fix come along unmodified.

BUILT, UNFLASHED. Do NOT flash. Do NOT send CAN. Flash only on explicit operator instruction naming
the file and the bus.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V53 builder requires assertions; do not run with python -O")

from firmware_paths import REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# ---- the cave, its encoders and its verified constants come from the FOURFRAME2 builder verbatim ----
import build_vfourframe_tva as FF

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks


START, END = FF.START, FF.END
V38_PLAIN = FF.V38_PLAIN
V38_RWD = FF.V38_RWD
V38_SHA256 = FF.V38_SHA256
V38_RWD_SHA256 = FF.V38_RWD_SHA256
EXPECTED_HEADERS = FF.EXPECTED_HEADERS
V9B = FF.V9B

CAVE_BASE = FF.CAVE_BASE
CAVE_BYTES = FF.CAVE_BYTES
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT
HOOK_ADDR = FF.HOOK_ADDR
HOOK_STOCK = FF.HOOK_STOCK

MAIN_BLOCK = FF.MAIN_BLOCK           # (0x13000, 0xC4FFC) -- holds the cave and the hook
CAL_BLOCK = (0xC6000, 0xC6FFC)       # holds the lockout cal; CRC @0xC6FFC
EXPECTED_BLOCKS = FF.EXPECTED_BLOCKS

# The image FOURFRAME2 produced -- V53 must equal it except for the lockout cal + the CAL CRC.
FF2_PLAIN = str(plain_image_path("_vfourframe2_plain_image.bin"))
FF2_SHA256 = "826809239588355ae3724565612083a8cd219fd456d4d0a548237b7933f2976c"

# ---- THE LEVER: minimum steer speed -> 0 ------------------------------------------------------------
# tp+0x72EA. Unit is 64.0625 counts per km/h (CAN path implements x41>>6 on a 0.01 km/h raw value).
LOCKOUT_ADDR = 0xC62EA
LOCKOUT_STOCK = 320                  # 4.995 km/h = 3.104 mph
LOCKOUT_NEW = 0                      # 0 km/h -- window LO bound removed
LOCKOUT_READER = 0x28EBC             # the ONLY reader image-wide: ld.hu 0x72ea[tp],lp
LOCKOUT_READER_BYTES = bytes.fromhex("e5ffeb72")   # op 0x3F, reg1=tp(5), reg2=lp(31), disp 0x72EA|1
SPEED_CMP_ADDR = 0x290D2
SPEED_CMP_BYTES = bytes.fromhex("ff51")            # cmp lp,r10  (r10 = voted speed gp-0x6a5e)

# Cal cells that MUST stay exactly as V38/FOURFRAME2 left them.
STOCK_CALS = {
    0xC62E8: (12800, "speed window HI bound -- UNTOUCHED (keeps the 0x7FFF SNA sentinel failing)"),
    0xC62EC: (80, "low-speed hysteresis companion -- untouched"),
    0xC62EE: (320, "CAN-commanded assist-shutdown permissive -- MUST stay stock, never raise"),
    0xC62F0: (640, "governor slew bypass speed (~10 km/h) -- untouched"),
    0xC646C: (3564, "the 4x LKAS/sensor scale (V38)"),
    0xC61B2: (2048, "pack output clamp (V38)"),
    0xC61B4: (2048, "arb output clamp (V38)"),
    0xC6206: (512, "governor slew step, hands-off -- V45's failed lever, stays stock"),
    0xC6450: (1024, "FUN_0003a382 Stage A pole -- V46, flashed, null; stays stock"),
    0xC644A: (1024, "FUN_0003a382 Stage C pole -- V43, flashed, null; stays stock"),
}
# FUN_0003a382 authority -> output-bound LERP. Its edit direction is UNRESOLVED; this build MEASURES
# the index (gp-0x6966) rather than guessing. Y-array must be stock.
# Record layout is [count][X[0..n-1]][Y[0..n-1]] as u16, byte-read and confirmed on the V38 image.
AUTHORITY_LERP_ADDR = 0xC6AF0
AUTHORITY_LERP_STOCK = (5, 0, 3277, 3604, 19661, 32768, 32768, 32768, 0, 0, 0)
# V42's confirmed ratchet fix is NOT carried (FOURFRAME2 does not carry it either) -- asserted, not implied.
RATCHET_ADDR = 0x454FE
RATCHET_STOCK_HW = 0x65BA

TAG = ("LKAS-4x-V38base-FOURFRAME2-telem-STRB01FIX-authority-refmodel"
       "-newid0x6a0-0x6a3-mbx16-19-100hz-minsteerspeed0-lockout0xC62EA-320to0")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V53-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v53_plain_image.bin"))


# -------------------------------------------------------------------------------------------------------
# Verification helpers (CRC-chain walking reused from the FOURFRAME2 builder)
# -------------------------------------------------------------------------------------------------------

def owning_block(code, address):
    inside = [(s, e) for s, e in FF.crc_block_map(code) if s <= address < e]
    assert len(inside) == 1, f"0x{address:05X} lies in {len(inside)} CRC blocks ({inside})"
    return inside[0]


def u16(code, address):
    return struct.unpack_from("<H", code, address)[0]


def assert_stock_cals(code, label):
    for address, (value, note) in STOCK_CALS.items():
        got = u16(code, address)
        assert got == value, f"{label}: 0x{address:05X} is {got}, expected {value} ({note})"
    assert struct.unpack_from("<11H", code, AUTHORITY_LERP_ADDR) == AUTHORITY_LERP_STOCK, \
        f"{label}: the 0xC6AF0 authority LERP moved -- its edit direction is UNRESOLVED, it must stay stock"
    assert u16(code, RATCHET_ADDR) == RATCHET_STOCK_HW, \
        f"{label}: 0x{RATCHET_ADDR:05X} is not the stock bne -- V53 is cut from V38 like FOURFRAME2"


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site is not stock movea"
    assert bytes(code[CAVE_BASE:CAVE_HARD_LIMIT]) == b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE), \
        "cave region is not all 0xFF -- refusing to overwrite"
    assert CAVE_BASE + len(CAVE_BYTES) <= CAVE_HARD_LIMIT, "cave overruns its free region"

    # The lever must be at its stock value -- proving the edit is real, not a no-op.
    assert u16(code, LOCKOUT_ADDR) == LOCKOUT_STOCK, \
        f"0x{LOCKOUT_ADDR:05X} is {u16(code, LOCKOUT_ADDR)}, expected stock {LOCKOUT_STOCK}"
    # ...and its single reader / the compare that consumes it must be the instructions we think they are.
    assert bytes(code[LOCKOUT_READER:LOCKOUT_READER + 4]) == LOCKOUT_READER_BYTES, \
        f"0x{LOCKOUT_READER:05X} is not `ld.hu 0x72ea[tp],lp` -- the lever's reader moved"
    assert bytes(code[SPEED_CMP_ADDR:SPEED_CMP_ADDR + 2]) == SPEED_CMP_BYTES, \
        f"0x{SPEED_CMP_ADDR:05X} is not `cmp lp,r10` -- the speed comparison moved"
    assert_stock_cals(code, "V38 baseline")


def assert_sole_reader(code):
    """Independent Python re-enumeration of every reader of tp+0x72EA, BOTH V850E2 encodings.

    `ld.hu`/`ld.w` put `disp|1` in the displacement halfword, so a scan for the bare displacement is
    blind to them -- both forms are searched here. The 6-byte extended-displacement form still carries
    the low 16 bits of the displacement as an aligned halfword, so it is covered by the same sweep.
    """
    hits = {0x72EA: [], 0x72EB: []}
    for address in range(START, MAIN_BLOCK[1] - 1):
        value = u16(code, address)
        if value in hits:
            hits[value].append(address)
    aligned = sorted(a for v in hits for a in hits[v] if a % 2 == 0)
    assert aligned == [LOCKOUT_READER + 2], \
        f"tp+0x72EA reader set changed: {[hex(a) for a in aligned]} (expected only 0x{LOCKOUT_READER + 2:05X})"
    unaligned = sorted(a for v in hits for a in hits[v] if a % 2 == 1)
    print(f"  sole-reader check: 1 aligned operand @0x{aligned[0]:05X} (the disp of 0x{LOCKOUT_READER:05X}); "
          f"{len(unaligned)} unaligned byte-pair coincidence(s) {[hex(a) for a in unaligned]} -- not operands")

    # No `movea <base>,tp,rX` table base below the lever can span it (a displacement scan cannot see
    # table-indexed reads, so this is the check that closes the LERP-masquerade trap).
    bases = []
    for address in range(START, MAIN_BLOCK[1] - 3, 2):
        if (u16(code, address) & 0x07FF) == ((0x31 << 5) | 5):     # movea imm16, tp, rX
            imm = u16(code, address + 2)
            if 0x7000 <= imm <= 0x72EA:
                bases.append((address, imm))
    assert all(imm <= 0x7010 for _, imm in bases), \
        f"a tp table base sits close under the lever: {[(hex(a), hex(i)) for a, i in bases]}"
    print(f"  LERP-masquerade check: nearest tp table bases below the lever are "
          f"{[(hex(a), hex(i)) for a, i in bases]} -- all >= 0x2DA bytes short of tp+0x72EA")


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)
    FF.assert_crc_chain(baseline, "V38 baseline")
    assert walk(bytes(baseline), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V38 baseline") == 0
    assert_sole_reader(baseline)

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    FF._self_check_encoders()

    code = bytearray(baseline)

    # ---- CHANGE 1 (CODE, 857 bytes): the FOURFRAME2 telemetry cave + its hook ---------------------
    hook_bytes = FF.jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"\n  CHANGE 1 (CODE) -- FOURFRAME2 four-frame passive read-only CAN telemetry cave:")
    print(f"    cave @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes "
          f"(limit {CAVE_HARD_LIMIT - CAVE_BASE}, headroom {CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)})")
    print(f"    hook @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  "
          f"(movea -> jarl 0x{CAVE_BASE:05X},lp)")
    for mbx in FF.MAILBOXES:
        print(f"      mailbox {mbx['n']:2d} -> ID 0x{mbx['can_id']:03X}: " +
              ", ".join(f"{name}({label})" for name, _, label in mbx["signals"]))
    print("    STRB = 0x01 (SSAM=1, 'message buffer used') -- the FOURFRAME defect, fixed")
    print("    gated on gp-0x1712 bit0 (TX-ready) AND DAT_ff48024c bit4 (real emitter's own arm gate)")

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave bytes not written"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"

    # ---- CHANGE 2 (CAL, 1 halfword): minimum steer speed 320 -> 0 --------------------------------
    print(f"\n  CHANGE 2 (CAL, 1 halfword) -- minimum steer speed:")
    struct.pack_into("<H", code, LOCKOUT_ADDR, LOCKOUT_NEW)
    print(f"    0x{LOCKOUT_ADDR:05X}: {LOCKOUT_STOCK} -> {LOCKOUT_NEW}   "
          f"({LOCKOUT_STOCK / 64.0625:.3f} km/h / {LOCKOUT_STOCK / 64.0625 * 0.621371:.3f} mph -> 0)")
    print(f"    sole reader 0x{LOCKOUT_READER:05X} `ld.hu 0x72ea[tp],lp` -> "
          f"0x{SPEED_CMP_ADDR:05X} `cmp lp,r10` / setfnc  =>  (voted speed >= 0) is now always true")
    print(f"    HI bound 0xC62E8 = {u16(code, 0xC62E8)} UNTOUCHED -> the 0x7FFF SNA sentinel still fails")
    assert u16(code, LOCKOUT_ADDR) == LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert_stock_cals(code, "V53")

    # ---- CRC coverage ----------------------------------------------------------------------------
    cave_block = owning_block(code, CAVE_BASE)
    hook_block = owning_block(code, HOOK_ADDR)
    lockout_block = owning_block(code, LOCKOUT_ADDR)
    assert cave_block == MAIN_BLOCK, f"cave lands in {cave_block}, expected {MAIN_BLOCK}"
    assert hook_block == MAIN_BLOCK, f"hook lands in {hook_block}, expected {MAIN_BLOCK}"
    assert lockout_block == CAL_BLOCK, f"lockout lands in {lockout_block}, expected {CAL_BLOCK}"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 -----------------------------------------------------------------------
    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update({LOCKOUT_ADDR, LOCKOUT_ADDR + 1})
    for block in (MAIN_BLOCK, CAL_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diffs, runs = FF.changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V53-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:LOCKOUT_ADDR]) == bytes(baseline[0xC5000:LOCKOUT_ADDR]), \
        "cal/data before the lockout moved"
    assert bytes(code[LOCKOUT_ADDR + 2:CAL_BLOCK[1]]) == bytes(baseline[LOCKOUT_ADDR + 2:CAL_BLOCK[1]]), \
        "cal/data between the lockout and the CAL CRC moved"
    assert bytes(code[CAL_BLOCK[1] + 4:0x100000]) == bytes(baseline[CAL_BLOCK[1] + 4:0x100000]), \
        "data above the CAL block moved"

    # ---- V53 vs FOURFRAME2: must differ by EXACTLY the cal + the CAL CRC -------------------------
    ff2 = bytearray(open(FF2_PLAIN, "rb").read())
    assert hashlib.sha256(bytes(ff2)).hexdigest() == FF2_SHA256, \
        "_vfourframe2_plain_image.bin is not the recorded FOURFRAME2 image"
    ff2_diffs = [i for i in range(START, END) if ff2[i] != code[i]]
    expected_ff2 = [LOCKOUT_ADDR, LOCKOUT_ADDR + 1] + list(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    assert ff2_diffs == expected_ff2, \
        f"V53 vs FOURFRAME2 differs at {[hex(a) for a in ff2_diffs]}, expected {[hex(a) for a in expected_ff2]}"
    assert struct.unpack_from("<I", ff2, MAIN_BLOCK[1])[0] == \
        struct.unpack_from("<I", code, MAIN_BLOCK[1])[0], "MAIN CRC must be identical to FOURFRAME2"
    print(f"\n  V53-vs-FOURFRAME2: exactly {len(ff2_diffs)} bytes "
          f"({[hex(a) for a in ff2_diffs]}) -- cave and hook byte-identical, MAIN CRC unchanged")

    # ---- CRC / bootloader gates ------------------------------------------------------------------
    FF.assert_crc_chain(code, "V53 plain")
    assert walk(bytes(code), label="V53") == 0
    assert walk_all_blocks(bytes(code), label="V53") == 0

    # ---- encode, then decode the emitted RWD back and re-run every gate on the readback ----------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    FF.assert_x31_checksum(rwd, "V53 emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V53 RWD does not decode back to the built image"
    readback = FF.full_image(decoded)
    FF.assert_crc_chain(readback, "V53 RWD readback")
    assert walk(readback, label="V53 RWD readback") == 0
    assert walk_all_blocks(readback, label="V53 RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert u16(readback, LOCKOUT_ADDR) == LOCKOUT_NEW, "lockout edit lost in RWD"
    assert u16(readback, 0xC646C) == 3564, "4x gain lost in RWD"
    assert_stock_cals(readback, "V53 RWD readback")

    cave_span = range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES))
    print(f"\n  V53-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave fourframe_program_and_fire" if first in cave_span else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else
                "CAL CRC trailer" if first == CAL_BLOCK[1] else
                "lockout 0xC62EA 320->0" if first == LOCKOUT_ADDR else "UNEXPECTED")
        assert kind != "UNEXPECTED", f"unexplained run 0x{first:05X}-0x{last:05X}"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:        {V38_SHA256}")
    print(f"  FOURFRAME2 SHA-256: {FF2_SHA256}")
    print(f"  V53 SHA-256:        {hashlib.sha256(code).hexdigest()}")
    print(f"  V53 RWD SHA-256:    {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V53-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V53 = FOURFRAME2 (V38 + the STRB-fixed four-frame telemetry cave) + minimum steer speed -> 0")
    print("  Change 1: passive read-only CAN telemetry, IDs 0x6A0-0x6A3, 16 signals @100 Hz")
    print("  Change 2: 0xC62EA 320 -> 0  (low-speed steer lockout 4.995 km/h -> 0)")
    print("  ELEVATED RISK class: the cave shares the physical bus carrying steering frames.")
    code, rwd = build()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "wb") as h:
        h.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as h:
        h.write(code)
    os.replace(OUT + ".tmp", OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  UNFLASHED. Do NOT flash. Do NOT send CAN. Flash only on explicit operator instruction")
    print("  naming the file + bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
