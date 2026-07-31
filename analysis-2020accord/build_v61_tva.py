"""
build_v61_tva.py -- V61 = V59 + KILL THE TORSION-BAR RATE LANE, BOTH HALVES, AT ONCE.

THE POINT
---------
r24 and r26 are the aggregator's two torque-RATE lanes. They are NOT independent: both are gain-scalings
of ONE shared value -- `r1 = clamp(gp-0x4f62, +/-5120)`, produced once at 0x3AAAC-0x3AAC0 and tapped
twice. Disassembly-confirmed this session:

    0x3AA9C  ld.h -0x4f62[gp],r14        # the torque RATE (a 4-sample first difference of gp-0x4f60)
    0x3AAAC  addi -0x1400,r14,r0         # \
    0x3AAB0  ble 0x3AAB8                 #  |
    0x3AAB2  movea 0x1400,r0,r1          #  |  r1 = clamp(rate, -5120, +5120)
    0x3AAB6  br 0x3AAC4                  #  |     THE SHARED VALUE
    0x3AAB8  addi 0x1400,r14,r0          #  |
    0x3AABC  movea -0x1400,r0,r1         #  |
    0x3AAC0  cmovge r14,r1,r1            # /
    ...
    0x3AB6C  mul r1,r6,r0                # r26 lane taps r1 here
    0x3AC16  mov r1,r8                   # r24 lane taps r1 here

**Every prior test killed ONE tap and left the other carrying the signal:**
  - V39 suppressed r24 -- and only CONDITIONALLY, via a cave at 0x3AC78 that bypasses unless driver max
    torque < 320 AND |LKAS| >= 417. Not an unconditional lane removal.  -> NULL on-car.
  - V42 zeroed r26 (RATE_A gain tables + the two override cals).  -> NULL on-car.
    build_v42_tva.py says it outright: "WHY r26 AND NOT r24: r24 was already zeroed by V39".
Since both lanes scale the SAME r1 and carry the SAME sign (single shared polarity load @0x3AB78),
killing either alone leaves the other transmitting the rate. **Each null is therefore uninformative
about the lane as a whole.** V61 removes the lane. That test has never been run.

WHY THIS LANE
-------------
V52C low-passed the torque VALUE gp-0x4f60 (19 carriers repointed) and was NULL. It could never have
covered the RATE: gp-0x4f62 is a DIFFERENT CELL written by a DIFFERENT function (FUN_0007E74A), so
V52C's repoint mechanism -- which retargets instructions whose disp16 equals -0x4f60 -- is structurally
blind to it. Byte-verified: gp-0x4f62 has 9 access sites, NONE in V52C's 19.
A first difference is a differentiator: |H(f)| = (4*Fs/D)*|sin(pi*f*D/Fs)| -> ~4*pi*f, i.e. ~264x at
21 Hz and essentially Fs-independent above ~500 Hz. Delay D = 4, byte-verified at tp+0x7c42 = 0xC6C42.
Of the rate's three consumers only THIS one is a live magnitude path -- 0x02C4E8 (FUN_0002c478) and
0x03B6A8 (FUN_0003b66a) are validity gates, and 0x3B6A8's magnitude term is dead code because
tp+0x74be = 0xC64BE = 0 (byte-verified). See memory/accord-torque-rate-lane-v52c-structurally-blind.md.

THE EDIT -- two single-BIT register-field changes, no cave, no RAM, no new opcode
--------------------------------------------------------------------------------
    0x3AB6C  37E1 -> 37E0   mul r1,r6,r0 -> mul r0,r6,r0    reg1: r1 -> r0   => r6 = r6*0 = 0 => r26 = 0
    0x3AC16  4001 -> 4000   mov r1,r8    -> mov r0,r8       reg1: r1 -> r0   => r8 = 0        => r24 = 0
r0 is hardwired zero on V850 and both instructions keep their opcode, format and length. This is the
edit class the kit's own record prefers: "an encoder that changes a REGISTER FIELD of a verified
instruction over one introducing a new opcode value."

r24 reaching 0 is not an assumption -- the tail was traced with r8 = 0:
    0x3AC20 sar 0xa,r8      -> r8 = 0
    0x3AC22 mov 0x0,r6      -> r6 = 0                (the DEFAULT, taken when both deadzone arms skip)
    0x3AC24 cmp r12,r8 ; 0x3AC2A ble 0x3AC32         -> taken (0 <= deadzone 3)
    0x3AC32 subr r0,r11 ; 0x3AC34 cmp r11,r8 ; 0x3AC36 bge 0x3AC3E   -> taken (0 >= -3)
    0x3AC3E mul r14,r6,r0   -> 0 * polarity = 0      -> clamp +/-0x2000 -> r24 = 0
r26 likewise: r6=0 flows through 0x3AB70 sar / 0x3AB72 mul / 0x3AB7E mul polarity -> r26 = 0.
Both then enter the sum unchanged in structure at 0x3ACC8 `mov r26,r6` / 0x3ACCA `add r24,r6`.

WHY THIS IS LOW-RISK
--------------------
- No code cave. Caves are this kit's ONLY bricking class (V24, V27, V48B). GATE 1 is vacuous: no new
  RAM cell is claimed.
- r24/r26 are SATURATING CLIPS summed ungated -- per the golden model "the lowest discontinuity risk of
  the group" (eight sibling lanes are zero-range GATES, which do jump).
- Monitor risk: the aggregator output gp-0x6b94 is lockstep-shadowed at gp-0x4ce0, but both int paths
  are computed from this same code, so they move together. V42 already zeroed r26 by this route and
  flew fault-free, which is the empirical proof that the shadow tracks.
- Reversible, and 8 bytes off V59.

WHAT IT COSTS
-------------
The rate lanes are a phase-lead / responsiveness term in BASE ASSIST, so manual feel WILL change --
expect slightly less eager turn-in. There is no LKAS-only decoupling point in this chain (traced).
That is the price of the experiment and it is reversible by reflashing V59.

BASE = V59, NOT V60. V60's blend edit (0xD2006 102 -> 43) was FLASHED 2026-07-31 and returned NULL, so
it is reverted by construction: building on V59 means 0xD2006 is already back at stock 102 and V61
carries no falsified confound. V59's probe is UNCHANGED.
NOTE the probe is NOT a pure control here. It reads gp-0x6ba6, produced by FUN_0003b66a from the torque
VALUE -- upstream of this edit, so the edit cannot move it directly. But if the grinding actually
changes, the bar quietens and the index distribution moves with it. So treat the index as a SECONDARY
READOUT of whether the mode changed, not as a null control.

INTERPRETING THE DRIVE
----------------------
NULL  => the torque-rate feedback lane is closed for good, and with the value path (V52C), the boost
         amplitude index (V60), the resonance lane (V56) and the damper (V44/V47) already closed, the
         torque-feedback hypothesis is in serious trouble. What remains is base-assist LOOP GAIN
         (0xD2834 / 0xCA154[mode], zero build-script hits, never touched) -- a direct trade against
         steering weight, i.e. an operator decision.
MOVES => the lane is the carrier, and the next question is how much of it can be given back (the gain
         cals 0xC6440/42/46 and 0xC643E/44 are the graded knobs) rather than a binary kill.
"""

import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
import build_v55_tva as V55                # noqa: E402
import build_v57_tva as V57                # noqa: E402
import build_v59_tva as V59                # noqa: E402

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                          # noqa: E402

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

# ---- THE TWO EDITS -----------------------------------------------------------------------------
R26_TAP = 0x3AB6C            # mul r1,r6,r0   -- the r26 lane's read of the shared clamped rate
R26_STOCK_HW = 0x37E1
R26_NEW_HW = 0x37E0
R26_TAP_HW2 = 0x0220         # reg3 field; must NOT move

R24_TAP = 0x3AC16            # mov r1,r8      -- the r24 lane's read of the same shared value
R24_STOCK_HW = 0x4001
R24_NEW_HW = 0x4000

EDITS = ((R26_TAP, R26_STOCK_HW, R26_NEW_HW, "r26 lane: mul r1,r6,r0 -> mul r0,r6,r0"),
         (R24_TAP, R24_STOCK_HW, R24_NEW_HW, "r24 lane: mov r1,r8 -> mov r0,r8"))

# The shared clamp that PRODUCES r1. Untouched, and asserted so, or the edit means something else.
CLAMP_CTX = ((0x3AA9C, struct.pack("<2H", 0x7724, 0xB09E), "ld.h -0x4f62[gp],r14"),
             (0x3AAAC, struct.pack("<2H", 0x060E, 0xEC00), "addi -0x1400,r14,r0"),
             (0x3AAB2, struct.pack("<2H", 0x0E20, 0x1400), "movea 0x1400,r0,r1"),
             (0x3AABC, struct.pack("<2H", 0x0E20, 0xEC00), "movea -0x1400,r0,r1"),
             (0x3AAC0, struct.pack("<2H", 0x0FEE, 0x0B3C), "cmovge r14,r1,r1"))

# The aggregator's add order, which must not move: 0x3ACC8 mov r26,r6 / 0x3ACCA add r24,r6.
SUM_CTX = ((0x3ACC8, 0x301A, "mov r26,r6"), (0x3ACCA, 0x31D8, "add r24,r6"))

# 🛑 Every r24/r26 GAIN cal must be STOCK. V39 (r24) and V42 (r26) edited these; V61 must be a clean
# INDEPENDENT test of the lane, not an accidental re-run of either build layered on top.
RATE_GAIN_CALS = ((0xC6440, 2048, "r24 gain, default arm (V39 territory)"),
                  (0xC6442, 1024, "r24 gain, arm 2 (V39 territory)"),
                  (0xC6446, 512, "r24 gain, arm 3 (V39 territory)"),
                  (0xC61F6, 3, "r24 deadzone (V39 territory)"),
                  (0xC6444, 512, "r26 override, gp-0x683c != 0 (V42 territory)"),
                  (0xC643E, 1536, "r26 override, assist_state arm (V42 territory)"))
# V42's r26 gain_A records -- 4 records, u16 count + s16 X[4] + s16 Y[4]. Y must be stock.
RATE_A_RECORDS = (0xC6A68, 0xC6A7C, 0xC6A90, 0xC6AA4)
RATE_A_Y_STOCK = ((3072, 3072, 2434, 2048), (3072, 3072, 2488, 1536),
                  (2664, 2664, 2243, 1436), (2560, 2560, 2145, 1331))

TAG = "LKAS-4x-mss0-decouple0xC646C-boostindexdepth-ratelane0-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V61-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v61_plain_image.bin"))
V59_BIN = str(plain_image_path("_v59_plain_image.bin"))

BLEND_ADDR, BLEND_STOCK = 0xD2006, 102     # V60's falsified lever -- must be back at stock here


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def decode_fields(halfword):
    """V850 Format-I/reg-reg field split: reg1 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"reg1": halfword & 0x1F, "opcode": (halfword >> 5) & 0x3F, "reg2": (halfword >> 11) & 0x1F}


def assert_rate_lane(code, label, expect_killed):
    """Both taps read r0 (killed) or r1 (stock), and NOTHING else about them may differ."""
    for addr, stock_hw, new_hw, what in EDITS:
        want = new_hw if expect_killed else stock_hw
        got = u16(code, addr)
        assert got == want, f"{label}: 0x{addr:05X} is 0x{got:04X}, expected 0x{want:04X} ({what})"
        f_got, f_stock = decode_fields(got), decode_fields(stock_hw)
        assert f_got["opcode"] == f_stock["opcode"] and f_got["reg2"] == f_stock["reg2"], \
            f"{label}: 0x{addr:05X} changed more than reg1 -- opcode/reg2 moved"
        assert f_got["reg1"] == (0 if expect_killed else 1), \
            f"{label}: 0x{addr:05X} reg1 is r{f_got['reg1']}"
    assert u16(code, R26_TAP + 2) == R26_TAP_HW2, f"{label}: the mul's reg3 halfword moved"


def assert_untouched_context(code, label):
    for addr, want, what in CLAMP_CTX:
        got = bytes(code[addr:addr + len(want)])
        assert got == want, f"{label}: shared-clamp context at 0x{addr:05X} ({what}) is {got.hex()}"
    for addr, want, what in SUM_CTX:
        assert u16(code, addr) == want, f"{label}: aggregator sum at 0x{addr:05X} ({what}) moved"
    for addr, want, what in RATE_GAIN_CALS:
        assert u16(code, addr) == want, \
            f"{label}: rate gain cal 0x{addr:05X} ({what}) is {u16(code, addr)}, expected {want} -- " \
            "V61 must be an INDEPENDENT lane test, not V39/V42 layered underneath"
    for base, ys in zip(RATE_A_RECORDS, RATE_A_Y_STOCK):
        assert struct.unpack_from("<4h", code, base + 0xA) == ys, \
            f"{label}: r26 gain_A record 0x{base:05X} Y row moved -- V42's edit must NOT be present"


def build():
    if not os.path.exists(V59_BIN):
        print(f"  {V59_BIN} missing -- running the V59 builder first\n")
        V59.build()
    v59 = bytearray(open(V59_BIN, "rb").read())
    print(f"  V59 source {V59_BIN}\n    SHA256 {hashlib.sha256(bytes(v59)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v59, "V59 source")
    assert walk(bytes(v59), label="V59 source") == 0
    assert walk_all_blocks(bytes(v59), label="V59 source") == 0
    V59.assert_probe_sites(v59, "V59 source")
    V59.assert_index_chain(v59, "V59 source")
    V55.assert_variant_tables(v59)
    V57.assert_decoupled(v59, "V59 source")
    assert u16(v59, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V59 source lost the lockout edit"
    assert u16(v59, BLEND_ADDR) == BLEND_STOCK, \
        "0xD2006 is not stock 102 -- V61 must NOT carry V60's falsified blend edit"
    assert_rate_lane(v59, "V59 source", expect_killed=False)
    assert_untouched_context(v59, "V59 source")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)
    assert_rate_lane(baseline, "V38 baseline", expect_killed=False)
    assert_untouched_context(baseline, "V38 baseline")

    code = bytearray(v59)

    # ---- the two edits ---------------------------------------------------------------------------
    print("\n  THE EDIT -- remove the torsion-bar RATE lane at BOTH taps of its shared value r1:")
    for addr, stock_hw, new_hw, what in EDITS:
        struct.pack_into("<H", code, addr, new_hw)
        print(f"    0x{addr:05X}  0x{stock_hw:04X} -> 0x{new_hw:04X}   {what}")
    print("    r1 = clamp(gp-0x4f62, +/-5120) is left INTACT and simply stops being read.")
    assert_rate_lane(code, "V61", expect_killed=True)
    assert_untouched_context(code, "V61")

    # ---- everything else must be byte-identical to V59 -------------------------------------------
    assert bytes(code[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]) == \
        bytes(v59[V59.CAVE_BASE:V59.CAVE_BASE + len(V55.CAVE_BYTES)]), "the cave moved"
    assert bytes(code[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]) == \
        bytes(v59[V59.HOOK_ADDR:V59.HOOK_ADDR + 4]), "the hook moved"
    V59.assert_probe_sites(code, "V61")
    V59.assert_index_chain(code, "V61")
    V57.assert_decoupled(code, "V61")
    V55.assert_variant_tables(code)
    assert u16(code, BLEND_ADDR) == BLEND_STOCK, "V61 must leave 0xD2006 at stock"
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC6424, "shaper deadband"),
                    (0xC646C, "shared sensor scale"), (0xC6CD0, "private LKAS gain"),
                    (0xC62EA, "low-speed lockout"),
                    (0xC63BA, "FUN_3b66a EMA alpha -- pre-falsified by V60, NOT a lever")):
        assert u16(code, a) == u16(v59, a), f"{name} 0x{a:05X} moved -- V61 edits TWO code halfwords"
    assert code[0xC64DE] == 27 and code[0xC64A3] == 1
    assert struct.unpack_from("<9H", code, 0xD27BC) == \
        struct.unpack_from("<9H", baseline, 0xD27BC), "FactorC 0xD27BC moved (V44 is falsified)"
    for addr, n in ((V59.LERP1_ADDR, 13), (V59.LERP4_ADDR, 13)):
        assert struct.unpack_from(f"<{n}H", code, addr) == \
            struct.unpack_from(f"<{n}H", baseline, addr), f"amplitude curve 0x{addr:05X} moved"

    # ---- CRC -------------------------------------------------------------------------------------
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")
        if block == CAL_BLOCK:
            assert old_crc == new_crc, "CAL CRC moved -- V61 changes NO 0xC6xxx calibration"

    # ---- exact diff ------------------------------------------------------------------------------
    # 🛑 NEVER whole-file diff against a full_image(): 0xFF filler below 0x13000 reports ~51,000 bogus
    # bytes. Restricted to [0x13000,0x100000).
    d59 = [i for i in range(0x13000, 0x100000) if code[i] != v59[i]]
    permitted = set()
    for addr, _s, _n, _w in EDITS:
        permitted |= set(range(addr, addr + 2))
    permitted |= set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    stray = [i for i in d59 if i not in permitted]
    assert not stray, f"V61 vs V59 touches bytes outside the two taps + MAIN CRC: {[hex(x) for x in stray]}"
    # 0x37E1->0x37E0 and 0x4001->0x4000 each flip ONE bit in the LOW byte, so exactly 2 code bytes move.
    # ⚠ Do NOT assert a fixed TOTAL byte count -- that silently encodes which CRC bytes happened to
    # differ (here the new MAIN CRC shares its low byte with the old, so only 3 of 4 trailer bytes move).
    # Assert the two code bytes exactly, and tie the rest to the CRC word actually changing.
    crc_range = range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)
    code_changed = sorted(i for i in d59 if i not in crc_range)
    crc_changed = sorted(i for i in d59 if i in crc_range)
    assert code_changed == [R26_TAP, R24_TAP], \
        f"expected exactly the two low bytes 0x{R26_TAP:05X}/0x{R24_TAP:05X}, got {[hex(x) for x in code_changed]}"
    assert crc_changed, "the MAIN block CRC did not move, but two code bytes did"
    assert len(d59) == 2 + len(crc_changed), f"unexpected extra bytes in the diff: {len(d59)}"
    print(f"\n  V61 vs V59: {len(d59)} bytes  "
          f"(2 register-field bytes + {len(crc_changed)} MAIN block CRC bytes ONLY)")
    print("    => CAL CRC unchanged = machine proof no 0xC6xxx calibration moved")
    print("    => 0xD2000-block CRC unchanged = machine proof V60's falsified blend is reverted/absent")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V61 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V61")
    assert walk(bytes(code), label="V61") == 0
    assert walk_all_blocks(bytes(code), label="V61") == 0
    V59.assert_probe_sites(code, "V61")
    V55.assert_variant_tables(code)
    assert_rate_lane(code, "V61", expect_killed=True)
    assert_untouched_context(code, "V61")

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback -----------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == FF.EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(source_info["headers"], source_info["blocks"],
                     [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V61 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V61 readback")
    assert walk(bytes(readback), label="V61 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V61 readback") == 0
    V59.assert_probe_sites(readback, "V61 readback")
    V59.assert_index_chain(readback, "V61 readback")
    V57.assert_decoupled(readback, "V61 readback")
    V55.assert_variant_tables(readback)
    assert_rate_lane(readback, "V61 readback", expect_killed=True)
    assert_untouched_context(readback, "V61 readback")

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  🛑 UNFLASHED. Flash only on explicit operator instruction naming the file and the bus.")
    print("     Kill openpilot/pandad first (tmux kill-server on the comma device).")
    print("\n  THE DRIVE -- same route shape as V59 (route 2c):")
    print("     parking-lot creep, v <= 5 m/s, LKAS applying, SUSTAINED hands-off stretches >= 3 s,")
    print("     deliberate LKAS on/off passes at matched speed and angle, plus a 10-13 m/s under-load")
    print("     pass. Decode with rlog-tools/decode_v59_boostindex.py.")
    print("     ⚠ The probe is NOT a null control this time: it reads gp-0x6ba6, which is upstream of")
    print("     the edit, so the edit cannot move it DIRECTLY -- but if the grinding actually quietens,")
    print("     the bar quietens and the index distribution moves with it. Treat it as a SECONDARY")
    print("     READOUT (V59 gave 76.9/18.5/4.6/0.04 at engaged+creep+hands-off).")
    print("\n     ⚠ EXPECT A MANUAL-FEEL CHANGE: the rate lanes are a phase-lead term in BASE assist")
    print("     and there is no LKAS-only decoupling point in this chain. Reversible by reflashing V59.")
    return code


if __name__ == "__main__":
    print(__doc__)
    build()
