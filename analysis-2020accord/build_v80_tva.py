#!/usr/bin/env python3
"""build_v80_tva.py -- V80 = V79 + the V42 macro-ratchet fix + a FLAT FactorC. UNFLASHED.

★ WHY THIS BUILD EXISTS -- three edits, of which TWO ARE NEW and ONE IS INHERITED

  EDIT 1 (CODE, ONE BYTE)  0x454FE  0xBA -> 0xB5      `bne 0x455C4` -> `br 0x455C4`
      🛑 RESTORES V42's MACRO-RATCHET FIX, which has been OFF THE CAR SINCE V53.
      Two prior builders were told to include it and shipped without it. It is asserted here on
      the base (must read 0xBA), on the built image (must read 0xB5), on the .rwd readback, and
      against the FLOWN `_v42_plain_image.bin` byte-for-byte.

  EDIT 2 (CAL, ONE u16 CELL)  FactorC m26 Y[3]  908 -> 566   =>  Y = [566, 566, 566, 566]
      Removes the rail V79 introduced. V79 clips 38.95% of the RULE-8 (speed, rate) envelope at
      ceiling floor 512; V78 and STOCK clip 0.00%. A railed damper takes its SIGN from gp-0x6abe
      and its INDEX from gp-0x6ac0 -- different cells -- so it degenerates into a Coulomb relay
      (RULE 12(b), the hazard that got an earlier ReLU plan overruled). Flat 566 makes the peak
      pre-clamp product (566*927)>>10 = 512 = the ceiling FLOOR exactly, so V80 NEVER clips, at
      ANY speed, ANY rate and ANY ceiling. Measured below: 0.00% at ceiling 512 AND 1024.

  EDIT 3 (CAL, INHERITED)  FactorE m26  X = [0, 119, 2500, 4000]  Y = [0, 897, 912, 927]
      Already in the V79 base. ASSERTED BY VALUE, NOT REWRITTEN. Zero bytes move.

THE ARITHMETIC, RE-DERIVED (not copied from the brief)
------------------------------------------------------
    dose(v, r) = min( (FactorC(v) * FactorE(r)) >> 10 , ceiling(gp-0x6ac2) )
    FactorC is now CONSTANT 566 over the whole gated speed domain [0, 0x7D00)  => the dose is
    SPEED-INDEPENDENT for the first time in this lineage.
        E(99) = 897*99//119 = 746        dose(99) = (566*746)>>10 = 412   at EVERY speed
        412 = 2.000x V78's 206 = 3.007x V75's 137
        k = ((566*897)>>10)/119 = 495/119 = 4.1597 counts of gp-0x6bd0 per count of rate

🛑🛑 `k` = 4.1597 IS UNCHANGED FROM V79 AND IS STILL THE HIGHEST LOOP GAIN THIS KIT HAS BUILT.
Edit 2 does NOT reduce it: with E_X0 = 0 the ramp passes through the origin, FactorC is 566 at
creep on both builds, and k depends only on those. Edit 2 removes the RAIL, not the GAIN.
2.000x V78 · 2.633x the V75 that hard-faulted · 3.000x the V76 that flew clean once.
GATE 2 (magnitude AND phase) is NOT satisfied by argument. **V80 IS NOT CLEARED TO FLY.**

🛑 WHAT EDIT 2 COSTS -- reported, not swallowed
----------------------------------------------
Flattening Y[3] 908 -> 566 CUTS engaged-mode damping above 80 km/h relative to V79, by up to
~310 counts. That is the POINT of the edit, but it also means:
  · V80 is NOT add-only vs V79. It is deliberately SUBTRACTIVE above 80 km/h. Quantified below.
  · Post-clamp vs STOCK it is add-only EXACTLY (worst drop 0) inside the RULE-8 observed envelope
    (rate <= 1941 ct) at BOTH ceiling 512 and ceiling 1024. **OUTSIDE that envelope it is not**:
    8 counts at ceiling 512 and 310 counts at ceiling 1024, both only above ~97 km/h AND above
    ~560 deg/s of column rate. Both figures are computed EXACTLY (closed form over C_max), not
    sampled -- and they are re-derived at run time, never printed as literals. The brief's
    "worst drop 0" is therefore TRUE as scoped and FALSE globally, and this file says so.
  · Mode 24 (MANUAL steering) stays BYTE-STOCK, which bounds the exposure to engaged driving.

🛑 WHAT THE PROBE CAN AND CANNOT SEE
------------------------------------
The 68-byte cave is byte-identical to V79/V78. Because FactorC at creep is unchanged, both rungs
trip at EXACTLY the same rate on V80 as on V79 below 80 km/h (bit6 at 47 ct = 10.0 deg/s, bit7 at
108 ct = 22.9 deg/s). **The probe CANNOT discriminate V80 from V79 below 80 km/h.** Above it, V80
trips LATER (it is speed-invariant now, where V79 got progressively earlier). A non-zero bit7 is
EXPECTED on V80 and is not evidence of a fault.

🛑 GRIND #1 ONLY. The micro-ratchet is dose-independent; the MACRO-ratchet is what edit 1 targets.

CAVE DISCIPLINE
---------------
🛑 Growing a cave is this kit's ONLY bricking class -- V24, V27 and V48B all bricked the ECU. This
build does not write the cave at all: it re-derives V78's 68 bytes from `build_v78_tva.build_cave()`,
asserts the base already carries them, re-disassembles them from the image and RE-EMULATES them.
"""
import hashlib
import os
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, encoders, crc_block_map)
import build_v68_tva as V68                # noqa: E402  (cave geometry constants)
import build_v76_v38base_tva as V76B       # noqa: E402  (interlock + CRC + census helpers)
import build_v78_tva as V78                # noqa: E402  (the CAVE -- pins + encoders + emulator)
import v76_surface as VS                   # noqa: E402  (the evaluator mirror, per-instruction)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000

# =====================================================================================================
# THE BASE -- V79 (which sits on V78 -> V76 -> V38)
# =====================================================================================================
SRC_BIN = plain_image_path("_v79_v78base_ey1_897_ey2_912_dose412_plain_image.bin")
SRC_SHA256 = "dc87ee1c8f43408061162567bc396b7a8660b30a9941793f3e1629401a468c86"
STOCK_BIN = stock_fw_path("code.bin")
# 🛑 The FLOWN artefact that carries edit 1. Used as an INDEPENDENT witness for the new byte.
V42_BIN = plain_image_path("_v42_plain_image.bin")

# ⚠ A BUILD-SPECIFIC image name, per the recorded plain-image-overwrite hazard: two V70 cuts both
# wrote `_v70_plain_image.bin` and the second destroyed the first's snapshot, leaving a flashable
# artefact no gate could check.
BIN_OUT = str(plain_image_path("_v80_v79base_flatC566_ratchet454FE_dose412_plain_image.bin"))
# 🛑 Paths this build must NEVER write -- above all its own BASE.
FORBIDDEN_OVERWRITE = {
    str(SRC_BIN),
    str(plain_image_path("_v78_v76base_ey1_449_dose206_plain_image.bin")),
    str(plain_image_path("_v76_v38base_relu_damper_plain_image.bin")),
    str(plain_image_path("_v76_gate_fb_arm5244_gateprobe_plain_image.bin")),
    str(plain_image_path("_v76_v38base_relu_damper_probe6b26_plain_image.bin")),
    str(plain_image_path("_v77_C63A0.1024_v74base_plain_image.bin")),
    str(plain_image_path("_v77b_C63A0.1024_v75base_plain_image.bin")),
    str(V42_BIN),
}

TAG = "V80-V79BASE-flatC566-ratchet454FE-dose412-probe-6bd0-63fd-67fa"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =====================================================================================================
# 🛑🛑 THE SAFETY-CRITICAL INTERLOCK -- inherited, asserted here BY VALUE (RULE 3 / RULE 11)
# =====================================================================================================
FAULT_CLAMP_ADDR = V76B.FAULT_CLAMP_ADDR        # 0xC407E, the friction-lane clamp
FAULT_CLAMP_MAX = V76B.FAULT_CLAMP_MAX          # 511
FAULT_THRESH_ADDR = V76B.FAULT_THRESH_ADDR      # 0xC4004, the f32 FUN_00036d74 compares against
FAULT_THRESH_BYTES = V76B.FAULT_THRESH_BYTES    # 0000003f
FAULT_TRIP_COUNTS = V76B.FAULT_TRIP_COUNTS      # 512
NOT_CARRIED = V76B.NOT_CARRIED                  # includes 0xC63A0 = 1024

# 🛑🛑 THE OPERATOR'S EXPLICIT MUST-NOT-CHANGE CELL, and its five siblings. 0xC63A0 flew at 2048 on
#     V74 and V75 ONLY, and BOTH hard-faulted. It is 1024 here and stays 1024.
C63A0_BLOCK = tuple(range(0xC63A0, 0xC63AC, 2))     # 0xC63A0 .. 0xC63AA
C63A0_VALUE = 1024

# =====================================================================================================
# EDIT 1 -- THE MACRO-RATCHET FIX.  ONE BYTE.  V850 Format III condition nibble only.
# =====================================================================================================
# [EVIDENCE] GhidraMCP decompile of FUN_0004503c (the function that owns 0x454FE) shows the guard:
#     if (*(char *)(gp + -0x67fa) == '\x04') {          <- 0x454F8 ld.bu / 0x454FC cmp / 0x454FE bne
#         uVar9  = |gp-0x6ace|            (via FUN_00049a5a + FUN_00049a78, twice)
#         uVar13 = |gp-0x138a|
#         if (uVar13 < uVar9) sVar5 = *(short *)(gp + -0x138a);   <- THE SUBSTITUTION
#     }
#     *(short *)(gp + -0x138a) = sVar5;
# i.e. in state 4 the governor FORBIDS the command magnitude from rising, cumulatively. Making the
# branch unconditional deletes the whole `if` body, so the freshly-computed value survives.
#
# [EVIDENCE] GhidraMCP disassemble_bytes on STOCK code.bin, 0x454F8..0x4550F:
#     000454f8  84670798  ld.bu -0x67fa, gp, r12
#     000454fc  6462      cmp   0x4, r12
#     000454fe  ba65      bne   0x000455c4
#     00045500  80ff5a45  jarl  0x00049a5a, lp
# [EVIDENCE] the cond nibble 0x5 = BR is validated against a REAL instance in this same image, not
#     hand-decoded: GhidraMCP reports `000450ea  a515  br 0x0004510e`, and `decode_bcond` below
#     independently returns (5, 0x4510E) for those bytes. Two methods, same answer.
EDIT_ADDR = 0x454FE
EDIT_BASE_HW = 0x65BA           # `bne  +198 -> 0x455C4`   (low byte 0xBA)
EDIT_NEW_HW = 0x65B5            # `br   +198 -> 0x455C4`   (low byte 0xB5)
EDIT_BASE_BYTE, EDIT_NEW_BYTE = 0xBA, 0xB5
COND_BNE, COND_BR = 0xA, 0x5
CTX_LD_STATE = (0x454F8, bytes.fromhex("84670798"))    # ld.bu -0x67fa[gp],r12
CTX_CMP_FOUR = (0x454FC, bytes.fromhex("6462"))        # cmp 0x4,r12
CTX_JARL_SUB = (0x45500, bytes.fromhex("80ff5a45"))    # jarl 0x00049A5A,lp -- first insn of the block
SUBST_BLOCK = (0x45500, 0x455C4)                       # the block the edit makes unreachable
# The brief's window: this range must differ from STOCK in EXACTLY the one edited byte.
RATCHET_WINDOW = (0x454C0, 0x45540)
# A real `br` in this image, used to validate the cond nibble empirically rather than by assertion.
BR_WITNESS = (0x450EA, bytes.fromhex("a515"), 0x4510E)

# =====================================================================================================
# EDIT 2 / EDIT 3 -- THE CALIBRATION CELLS
# =====================================================================================================
FACTOR_C_PTRS, FACTOR_E_PTRS = V76B.FACTOR_C_PTRS, V76B.FACTOR_E_PTRS      # 0xC9E9C / 0xC9F84
FACTOR_B_PTRS, FACTOR_D_PTRS = V76B.FACTOR_B_PTRS, V76B.FACTOR_D_PTRS
CEILING_PTRS, FRICTION_PTRS = V76B.CEILING_PTRS, V76B.FRICTION_PTR_ARRAY
# 🛑 SIX arrays, not five -- the friction records are the sixth, and V74's x1.5 lived there.
ALL_PTR_ARRAYS = {"FactorB": FACTOR_B_PTRS, "FactorC": FACTOR_C_PTRS, "FactorD": FACTOR_D_PTRS,
                  "FactorE": FACTOR_E_PTRS, "ceiling": CEILING_PTRS, "friction": FRICTION_PTRS}
N_SLOTS_SCAN = V76B.N_SLOTS_SCAN                # 58 -- the FactorC array's true extent
N_MODES = V76B.N_MODES                          # 34
LIVE_MODE, MANUAL_MODE = V76B.LIVE_MODE, V76B.MANUAL_MODE      # 26 engaged / 24 manual
rec_len = V76B.rec_len                          # 4 + 4*count  -- NOT a flat 0x18 window
REC_STRIDE, REC_DATA_LEN = V76B.REC_STRIDE, V76B.REC_DATA_LEN  # 0x14 / 18
EXPECT_ADDR = V76B.EXPECT_ADDR                  # {("C",24):0xD67E4, ("C",26):0xD77D0, ...}

# The V79 base contents of the mode-26 records, asserted before writing.
BASE_C26 = ([2240, 3840, 5120, 8960], [566, 566, 566, 908])
NEW_C26 = ([2240, 3840, 5120, 8960], [566, 566, 566, 566])      # ★ EDIT 2 -- Y[3] only
BASE_E26 = ([0, 119, 2500, 4000], [0, 897, 912, 927])
NEW_E26 = BASE_E26                              # 🛑 EDIT 3 is INHERITED. FactorE is NOT written.

R_OP = 99                       # counts; the measured in-burst median rate for grind #1 (21.0 deg/s)
SPEED_CTS_PER_KMH = VS.SPEED_CTS_PER_KMH        # 64.0
RATE_CTS_PER_DEGS = VS.RATE_CTS_PER_DEGS        # 4.7121
DOSE_TARGET = 412                               # EXACTLY 2x V78's 206, on the integer surface
V79_DOSE, V78_DOSE, V76_DOSE, V75_DOSE = 412, 206, 137, 137
SPEED_5MPH_CT = 515                             # 5 mph = 8.04672 km/h -> 515 counts
SPEED_140_CT = 8960                             # 140 km/h -- FactorC's X[3] knot
CEILING_FLOOR = 512                             # the tp+0x7158 fallback AND the ceiling LERP's Y[0]
CEILING_TOP = 1024                              # the ceiling LERP's Y[1] (backdrive idx >= 800)
FLAT_C = 566                                    # FactorC's value -- now at EVERY speed
OBS_RATE_MAX = 1941                             # RULE 8: route 5d maximum, 412 deg/s
SPEED_GATE, RATE_GATE = 0x7D00, 0x32C9          # FactorC gate @0x344E0, FactorE gate @0x345FA

# The independent statement of the write list. Asserted against what this builder actually emits.
# 🛑 Y[i] lives at rec + 2 + 2*n + 2*i with n = 4  =>  Y[3] = 0xD77D0 + 2 + 8 + 6 = 0xD77E0.
FACTOR_C_Y3_ADDR = 0xD77E0
EXPECTED_CELL_WRITES = {FACTOR_C_Y3_ADDR: (908, 566, "FactorC m26 Y[3]")}
EXPECTED_BYTE_WRITES = {EDIT_ADDR: (EDIT_BASE_BYTE, EDIT_NEW_BYTE, "state-4 branch cond nibble")}

# =====================================================================================================
# THE PROBE CAVE (CARRIED, NOT REWRITTEN)
# =====================================================================================================
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V78.CAVE_EXTENT              # 🛑 68. THE PROVEN EXTENT. NEVER GROW IT.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK        # 0x55C0E, `movea -0x1518,gp,r6`
HOOK_RETURN, HOOK_RETURN_INSN = V78.HOOK_RETURN, V78.HOOK_RETURN_INSN
BIT_DAMP_LO, BIT_DAMP_HI = V78.BIT_DAMP_LO, V78.BIT_DAMP_HI
DAMP_LO_THRESH, DAMP_HI_THRESH = V78.DAMP_LO_THRESH, V78.DAMP_HI_THRESH      # 192 / 448
LEGAL_PAYLOAD_HI = V78.LEGAL_PAYLOAD_HI


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


# =====================================================================================================
# EDIT 1's decoder -- V850 Format III, and the guards around it
# =====================================================================================================
def decode_bcond(buf, address):
    """Decode a V850 Bcond halfword -> (cond, absolute_target). None if it is not a Bcond.

    Format III is ONE halfword:
        bits[15:11] = disp[8:4] | bits[10:7] = 0b1011 | bits[6:4] = disp[3:1] | bits[3:0] = cond
    Only the LOW NIBBLE moves in this edit, so the displacement -- and therefore the branch TARGET
    -- is provably unchanged. Both sides are decoded and compared, never assumed.
    """
    hw = struct.unpack_from("<H", buf, address)[0]
    if (hw >> 7) & 0xF != 0xB:
        return None
    cond = hw & 0xF
    disp = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
    if disp & 0x100:
        disp -= 0x200
    return cond, address + disp


def assert_br_witness(buf):
    """🛑 Validate cond nibble 0x5 == BR against a REAL instruction in THIS image, not by assertion.

    GhidraMCP independently disassembles 0x450EA as `br 0x0004510e` (bytes a515). If our decoder
    agrees on that instance, its verdict on 0x454FE is a measurement, not a hand-decode.
    """
    addr, want_bytes, want_target = BR_WITNESS
    assert bytes(buf[addr:addr + 2]) == want_bytes, \
        f"the `br` witness at 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
        f"{want_bytes.hex()} -- the encoding cross-check has lost its anchor"
    got = decode_bcond(buf, addr)
    assert got == (COND_BR, want_target), \
        f"the `br` witness decodes as {got}, but GhidraMCP reports br -> 0x{want_target:05X}"
    return got


def assert_ratchet_context(buf, label):
    """The exact instruction context around the edit, byte-for-byte."""
    for address, expected in (CTX_LD_STATE, CTX_CMP_FOUR, CTX_JARL_SUB):
        assert bytes(buf[address:address + len(expected)]) == expected, \
            f"🛑 {label}: instruction context at 0x{address:05X} is " \
            f"{bytes(buf[address:address + len(expected)]).hex()}, expected {expected.hex()}"


def assert_ratchet_base(buf, label):
    """🛑 THE EDIT TWO BUILDERS DROPPED. Assert the base is STOCK here before touching it."""
    assert_ratchet_context(buf, label)
    assert u16(buf, EDIT_ADDR) == EDIT_BASE_HW, \
        f"🛑 {label}: 0x{EDIT_ADDR:05X} is 0x{u16(buf, EDIT_ADDR):04X}, expected the stock `bne` " \
        f"0x{EDIT_BASE_HW:04X} -- the ratchet fix is either already present or the base is wrong"
    assert buf[EDIT_ADDR] == EDIT_BASE_BYTE, f"{label}: low byte is 0x{buf[EDIT_ADDR]:02X}"
    got = decode_bcond(buf, EDIT_ADDR)
    assert got == (COND_BNE, SUBST_BLOCK[1]), \
        f"🛑 {label}: 0x{EDIT_ADDR:05X} decodes as {got}, expected (BNE, 0x{SUBST_BLOCK[1]:05X})"
    return got


def assert_ratchet_present(buf, label):
    """🛑🛑 THE ASSERTION THIS BUILD EXISTS TO MAKE. Run on the image AND on the .rwd readback."""
    assert_ratchet_context(buf, label)
    assert buf[EDIT_ADDR] == EDIT_NEW_BYTE, (
        f"🛑🛑 {label}: 0x{EDIT_ADDR:05X} = 0x{buf[EDIT_ADDR]:02X}, MUST be 0x{EDIT_NEW_BYTE:02X}. "
        f"THE MACRO-RATCHET FIX IS MISSING. Two prior builders shipped without it.")
    assert u16(buf, EDIT_ADDR) == EDIT_NEW_HW, \
        f"🛑 {label}: halfword is 0x{u16(buf, EDIT_ADDR):04X}, expected 0x{EDIT_NEW_HW:04X}"
    got = decode_bcond(buf, EDIT_ADDR)
    assert got == (COND_BR, SUBST_BLOCK[1]), \
        f"🛑 {label}: 0x{EDIT_ADDR:05X} decodes as {got}, expected (BR, 0x{SUBST_BLOCK[1]:05X})"
    return got


def assert_ratchet_witness(buf, v42, label):
    """🛑 An INDEPENDENT witness: the FLOWN V42 image carries exactly the bytes we emit.

    V42 fixed the ratchet on-car (kit record). If our edited window is byte-identical to V42's over
    the whole [0x454C0, 0x45540) window, the edit is not a re-derivation -- it is a replication of a
    build that has already run on the car.
    """
    lo, hi = RATCHET_WINDOW
    assert bytes(buf[lo:hi]) == bytes(v42[lo:hi]), (
        f"🛑 {label}: [0x{lo:05X},0x{hi:05X}) does not match the FLOWN _v42_plain_image.bin -- "
        f"diff at {[hex(a) for a in range(lo, hi) if buf[a] != v42[a]][:8]}")
    assert v42[EDIT_ADDR] == EDIT_NEW_BYTE, "the V42 witness image does not carry 0xB5 -- STOP"
    return hi - lo


def assert_ratchet_window_vs_stock(buf, stock, label):
    """🛑 THE BRIEF'S WINDOW GUARD: [0x454C0, 0x45540) differs from STOCK in EXACTLY one byte."""
    lo, hi = RATCHET_WINDOW
    diff = [a for a in range(lo, hi) if buf[a] != stock[a]]
    assert diff == [EDIT_ADDR], (
        f"🛑 {label}: [0x{lo:05X},0x{hi:05X}) differs from STOCK at {[hex(a) for a in diff]}, "
        f"expected exactly [0x{EDIT_ADDR:05X}]")
    return len(diff)


def assert_no_external_entry(buf, label):
    """🛑 The substitution block must be reachable ONLY by falling through the edited branch.

    Scans the whole owning function FUN_0004503c (0x4503C..0x45607) for any Bcond or jr/jarl whose
    target lands inside [0x45500, 0x455C4). If one existed, the edit would not fully disable it.
    """
    low, high = SUBST_BLOCK
    for address in range(0x4503C, 0x45608, 2):
        if low <= address < high:
            continue
        got = decode_bcond(buf, address)
        if got and low <= got[1] < high:
            raise AssertionError(
                f"🛑 {label}: external Bcond at 0x{address:05X} enters the substitution block at "
                f"0x{got[1]:05X} -- the edit would not fully disable it")
        hw = u16(buf, address)
        if (hw & 0xFFC0) == 0x0780:                      # jr / jarl disp22
            disp = ((hw & 0x3F) << 16) | u16(buf, address + 2)
            if disp & 0x200000:
                disp -= 0x400000
            if low <= address + disp < high:
                raise AssertionError(
                    f"🛑 {label}: external jr/jarl at 0x{address:05X} enters the substitution block")
    return high - low


# =====================================================================================================
# Record helpers -- every address is DEREFERENCED, never hard-coded into a write
# =====================================================================================================
def rec_addr(buf, ptrs, mode):
    return u32(buf, ptrs + 4 * mode)


def read_rec(buf, ptrs, mode):
    """-> (addr, count, X, Y). Reads the count from the record itself; never assumes 4.

    🛑 Layout: base+0 u16 count | base+2 n x i16 X | base+2+2n n x i16 Y | base+2+4n u16 terminator.
    X starts at base+2, NOT base+4 -- getting that wrong silently reads [X1,X2,X3,Y0]."""
    off = rec_addr(buf, ptrs, mode)
    n = u16(buf, off)
    assert 1 <= n <= 16, f"record @0x{off:05X} claims count={n} -- refusing to parse"
    X = [s16(buf, off + 2 + 2 * i) for i in range(n)]
    Y = [s16(buf, off + 2 + 2 * n + 2 * i) for i in range(n)]
    return off, n, X, Y


def write_rec(buf, ptrs, mode, X, Y):
    """Write a record IN PLACE. 🛑 Writes exactly 2+4*count bytes; never the full 0x14 stride."""
    off = rec_addr(buf, ptrs, mode)
    n = u16(buf, off)
    assert len(X) == len(Y) == n, \
        f"record @0x{off:05X} has count={n} but {len(X)} points were supplied -- changing the " \
        f"count would change rec_len ({rec_len(n)} -> {rec_len(len(X))}) and could spill"
    for i, v in enumerate(X):
        struct.pack_into("<h", buf, off + 2 + 2 * i, v)
    for i, v in enumerate(Y):
        struct.pack_into("<h", buf, off + 2 + 2 * n + 2 * i, v)
    return off, 2 + 4 * n


def assert_write_addresses(buf, label):
    """🛑 The cal write address is DERIVED from the dereferenced record, then compared with the
    independently-stated `EXPECTED_CELL_WRITES`. A pointer-array misread cannot silently retarget."""
    off = rec_addr(buf, FACTOR_C_PTRS, LIVE_MODE)
    n = u16(buf, off)
    derived = {off + 2 + 2 * n + 2 * 3}
    assert derived == set(EXPECTED_CELL_WRITES), (
        f"🛑 {label}: FactorC Y[3] derives to {sorted(map(hex, derived))} but the spec says "
        f"{sorted(map(hex, EXPECTED_CELL_WRITES))}")
    return off


def assert_no_aliasing(buf, label):
    """🛑 GUARD 7. Nothing else may own the byte we write, in ANY of the six arrays.

    Uses `rec_len = 4 + 4n` per record -- NOT a flat 0x18 window. V73's guard window was 4 bytes too
    wide and false-positived across adjacent modes. Also reports the nearest OTHER record."""
    write_addrs = set(EXPECTED_CELL_WRITES)
    nearest = None
    for name, ptrs in ALL_PTR_ARRAYS.items():
        owners = {}
        for m in range(N_SLOTS_SCAN):
            r = rec_addr(buf, ptrs, m)
            n = u16(buf, r)
            if 1 <= n <= 16:
                owners.setdefault((r, rec_len(n)), []).append(m)
        for a in write_addrs:
            for (rec, ln), modes in owners.items():
                if rec <= a < rec + ln:
                    assert name == "FactorC" and modes == [LIVE_MODE], (
                        f"🛑 {label}: write 0x{a:05X} lands inside {name} record 0x{rec:05X}, owned "
                        f"by modes {modes} -- it would leak outside mode {LIVE_MODE}")
                else:
                    d = rec - a if rec > a else a - (rec + ln) + 1
                    if nearest is None or d < nearest[0]:
                        nearest = (d, name, rec, modes)
    for name, ptrs in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
        owners = {}
        for m in range(N_SLOTS_SCAN):
            owners.setdefault(rec_addr(buf, ptrs, m), []).append(m)
        live = rec_addr(buf, ptrs, LIVE_MODE)
        assert owners[live] == [LIVE_MODE], \
            f"{label}: {name} m{LIVE_MODE} record 0x{live:05X} is ALSO used by modes " \
            f"{[m for m in owners[live] if m != LIVE_MODE]} -- the edit would leak"
        assert rec_addr(buf, ptrs, MANUAL_MODE) != live, \
            f"{label}: {name}: modes {MANUAL_MODE} and {LIVE_MODE} share a record"
    assert rec_addr(buf, FACTOR_C_PTRS, LIVE_MODE) == EXPECT_ADDR[("C", LIVE_MODE)]
    return nearest


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 GUARD 7. All SIX pointer arrays byte-identical to STOCK over all 34 modes."""
    for name, ptrs in ALL_PTR_ARRAYS.items():
        got = bytes(buf[ptrs:ptrs + 4 * N_MODES])
        want = bytes(stock[ptrs:ptrs + 4 * N_MODES])
        assert got == want, \
            f"🛑 {label}: the {name} pointer array @0x{ptrs:05X} differs from STOCK over " \
            f"{N_MODES} modes -- a retargeted pointer would silently move every edit"
    return len(ALL_PTR_ARRAYS)


def assert_untouched_surfaces(buf, base, label):
    """FactorB/D, the ceiling and friction must stay as the base has them, in BOTH modes.
    FactorE m26 must be IDENTICAL to the base -- edit 3 is INHERITED, never rewritten.

    Also asserts the edited record's HEADER (the point count -- a change would move rec_len) and its
    TAIL (the 2 bytes whose mis-sizing produced the V73 spill)."""
    for name, ptrs in (("FactorB", FACTOR_B_PTRS), ("FactorD", FACTOR_D_PTRS),
                       ("ceiling", CEILING_PTRS), ("friction", FRICTION_PTRS)):
        for mode in (MANUAL_MODE, LIVE_MODE):
            off = rec_addr(buf, ptrs, mode)
            n = u16(buf, off)
            ln = 2 + 4 * n
            assert bytes(buf[off:off + ln]) == bytes(base[off:off + ln]), \
                f"🛑 {label}: {name} mode {mode} @0x{off:05X} CHANGED -- this build touches only " \
                f"FactorC mode {LIVE_MODE} and one code byte"
    # 🛑 FactorE is EDIT 3 and is INHERITED. Not one byte of it may move.
    eoff = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert bytes(buf[eoff:eoff + REC_STRIDE]) == bytes(base[eoff:eoff + REC_STRIDE]), \
        f"🛑 {label}: FactorE m26 @0x{eoff:05X} MOVED -- edit 3 is inherited, never rewritten"
    _o, _n, ex, ey = read_rec(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert (ex, ey) == BASE_E26 == NEW_E26, \
        f"🛑 {label}: FactorE m26 is X={ex} Y={ey}, expected the inherited {BASE_E26}"
    # the edited FactorC record: header, tail, X, and Y all pinned by value
    coff = rec_addr(buf, FACTOR_C_PTRS, LIVE_MODE)
    assert u16(buf, coff) == 4 == u16(base, coff), \
        f"🛑 {label}: FactorC m{LIVE_MODE} HEADER changed -- the point count must stay 4"
    assert bytes(buf[coff + REC_DATA_LEN:coff + REC_STRIDE]) == b"\x00\x00", \
        f"🛑 {label}: FactorC m{LIVE_MODE} TAIL is not 0x0000 -- the V73 spill signature"
    _o, _n, cx, _cy = read_rec(buf, FACTOR_C_PTRS, LIVE_MODE)
    assert cx == BASE_C26[0] == NEW_C26[0], \
        f"🛑 {label}: FactorC m26 X is {cx} -- this build changes Y[3] ONLY"


def assert_record_geometry(buf, label):
    for (kind, mode), want in EXPECT_ADDR.items():
        ptrs = FACTOR_C_PTRS if kind == "C" else FACTOR_E_PTRS
        got = rec_addr(buf, ptrs, mode)
        assert got == want, \
            f"{label}: Factor{kind} mode {mode} dereferences to 0x{got:05X}, expected 0x{want:05X}"
        n = u16(buf, got)
        assert n == 4 and rec_len(n) == REC_STRIDE == 0x14, \
            f"{label}: Factor{kind} m{mode} count={n}, rec_len=0x{rec_len(n):X} (expected 4 / 0x14)"


# =====================================================================================================
# 🛑🛑 THE INTERLOCK GUARD, the operator's DO-NOT-DOUBLE cell, and the levers not to resurrect
# =====================================================================================================
def assert_fault_interlock(buf, label):
    return V76B.assert_fault_interlock(buf, label)


def assert_not_carried(buf, label):
    for addr, (want, why) in NOT_CARRIED.items():
        got = u16(buf, addr)
        assert got == want, f"{label}: 0x{addr:05X} = {got}, expected {want} -- {why}"


def assert_c63a0_block(buf, stock, label):
    """🛑🛑 GUARD 5 -- THE OPERATOR'S EXPLICIT DIRECTIVE, 2026-08-07:
       "Do not double 0xC63A0, that is what was causing hard faults."

    0xC63A0 was V72's LEVER C. It flew at 2048 on V74 and V75 ONLY and BOTH hard-faulted. It is
    1024 (stock) on this base and stays 1024, together with its five siblings 0xC63A2..0xC63AA."""
    for a in C63A0_BLOCK:
        got, want = u16(buf, a), u16(stock, a)
        assert got == C63A0_VALUE, (
            f"🛑🛑 {label}: 0x{a:05X} = {got}, MUST be {C63A0_VALUE}. The operator's directive is "
            f"explicit: do not raise 0xC63A0. It flew at 2048 on V74/V75 and both hard-faulted.")
        assert got == want, f"🛑 {label}: 0x{a:05X} = {got} but STOCK carries {want}"
    return len(C63A0_BLOCK)


def assert_manual_mode_stock(buf, stock, label):
    """🛑 GUARD 7. Mode 24 is MANUAL steering. Byte-identical to STOCK, not merely to the base."""
    for kind, ptrs in (("C", FACTOR_C_PTRS), ("E", FACTOR_E_PTRS)):
        off = rec_addr(buf, ptrs, MANUAL_MODE)
        assert off == EXPECT_ADDR[(kind, MANUAL_MODE)]
        got, want = bytes(buf[off:off + REC_STRIDE]), bytes(stock[off:off + REC_STRIDE])
        assert got == want, (
            f"🛑 {label}: Factor{kind} mode {MANUAL_MODE} @0x{off:05X} differs from STOCK "
            f"({want.hex()} -> {got.hex()}) -- manual steering must stay byte-stock")
    for name, ptrs in (("FactorB", FACTOR_B_PTRS), ("FactorD", FACTOR_D_PTRS),
                       ("ceiling", CEILING_PTRS), ("friction", FRICTION_PTRS)):
        off = rec_addr(buf, ptrs, MANUAL_MODE)
        n = u16(buf, off)
        assert bytes(buf[off:off + 2 + 4 * n]) == bytes(stock[off:off + 2 + 4 * n]), \
            f"🛑 {label}: {name} mode {MANUAL_MODE} @0x{off:05X} differs from STOCK"


# =====================================================================================================
# THE SURFACE GUARDS -- through `v76_surface`'s per-instruction evaluator mirror
# =====================================================================================================
def surfaces(img_before, img_after):
    return (VS.Surface(img=bytes(img_before), mode=LIVE_MODE),
            VS.Surface(img=bytes(img_after), mode=LIVE_MODE),
            VS.Surface(img=VS.load("stock"), mode=LIVE_MODE))


def assert_table_shape(X, Y, label):
    """GUARD 1 + GUARD 2 applied to FactorE -- inherited, but re-asserted on the built image."""
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1)), f"{label}: X is not STRICTLY increasing"
    assert all(Y[i] < Y[i + 1] for i in range(len(Y) - 1)), (
        f"🛑 {label}: Y = {Y} is not STRICTLY increasing. The operator asked for 'relu like or "
        f"monotone increasing'; a flat or descending segment is neither.")
    assert Y[0] == 0, (
        f"🛑 {label}: E_Y[0] = {Y[0]} != 0. A non-zero Y[0] is a COULOMB RELAY: the LERP index "
        f"(gp-0x6ac0) and the output sign (gp-0x6abe) are DIFFERENT cells, so it gives constant "
        f"magnitude with a rate-flipped sign -- describing function 4*M0/(pi*A), unbounded as the "
        f"amplitude falls. NEVER RAISE IT.")


def assert_factorC_flat(S, label):
    """★ EDIT 2's own guard: FactorC is monotone non-decreasing AND constant, EXHAUSTIVELY.

    With Y = [566,566,566,566] every LERP segment has a ZERO numerator, so the `divq` at 0x34560
    returns 0 at every index and both hard clamps return 566. This is checked over the WHOLE gated
    speed domain rather than at the four knots -- 32,000 evaluations of the real evaluator."""
    X, Y = S.XY("C")
    assert X == NEW_C26[0], f"🛑 {label}: FactorC X is {X}, must stay {NEW_C26[0]}"
    assert Y == NEW_C26[1] == [FLAT_C] * 4, f"🛑 {label}: FactorC Y is {Y}, expected {NEW_C26[1]}"
    assert all(X[i] < X[i + 1] for i in range(3)), f"{label}: FactorC X not strictly increasing"
    assert all(Y[i] <= Y[i + 1] for i in range(3)), f"{label}: FactorC Y not monotone"
    vals = {S.factorC(sp) for sp in range(SPEED_GATE)}
    assert vals == {FLAT_C}, \
        f"🛑 {label}: FactorC takes values {sorted(vals)} over the gated speed domain, expected " \
        f"only {{{FLAT_C}}} -- the flatness claim is the whole basis of the no-clip guard"
    return SPEED_GATE


def assert_never_clips(S, label):
    """🛑🛑 EDIT 2's PURPOSE, stated as an exact supremum and then measured a second way.

    FactorC is constant 566, so the pre-clamp product is (566 * E(r)) >> 10 at EVERY speed and its
    supremum over all gated rates is (566 * E_max) >> 10 with E_max = 927. That evaluates to 512 =
    the ceiling FLOOR exactly, so `d > c` at 0x34724 is NEVER true, at ANY ceiling the LERP can
    produce (its own Y[0] is 512 and it only rises). => V80 can never rail. RULE 12(b) closed."""
    e_max = max(e for e in (S.factorE(r) for r in range(RATE_GATE)) if e is not None)
    peak = (FLAT_C * e_max) >> 10
    assert e_max == 927, f"{label}: E_max is {e_max}, expected 927"
    assert peak == CEILING_FLOOR, (
        f"🛑🛑 {label}: max (566*E)>>10 = {peak}, MUST be exactly the ceiling floor "
        f"{CEILING_FLOOR}. Edit 2's entire purpose is that the damper never reaches the rail.")
    # second method: the evaluator's own clip flag, at BOTH ceilings, over the RULE-8 envelope
    n = clipped = 0
    for bd, _c in ((0, CEILING_FLOOR), (800, CEILING_TOP)):
        for sp in range(0, 9001, 29):
            for r in range(0, OBS_RATE_MAX + 1, 7):
                n += 1
                clipped += S.output(sp, r, backdrive_idx=bd)[1]
    assert clipped == 0, f"🛑 {label}: {clipped} of {n} sampled points CLIP -- edit 2 failed"
    # third method: the supremum of |gp-0x6bd0| itself, both ceilings, whole domain, coarse
    sup = max(S.mag(sp, r, backdrive_idx=bd)
              for bd in (0, 800)
              for sp in range(0, SPEED_GATE, 53)
              for r in range(0, RATE_GATE, 29))
    assert sup <= CEILING_FLOOR, f"🛑 {label}: |gp-0x6bd0| reaches {sup} > {CEILING_FLOOR}"
    return peak, e_max, n, sup


def clip_fraction(S, ceil_bd, rmax=OBS_RATE_MAX, step_s=29, step_r=7):
    n = c = 0
    for sp in range(0, 9001, step_s):
        for r in range(0, rmax + 1, step_r):
            n += 1
            c += S.output(sp, r, backdrive_idx=ceil_bd)[1]
    return c, n


def worst_drop_exact(S_ref, S80, ceil, rmax):
    """🛑 The EXACT supremum of (reference - V80) AFTER the ceiling clamp, over ALL speeds.

    Closed form, not a sample. V80's FactorC is CONSTANT, so its output does not depend on speed at
    all. The reference's output at a fixed rate is monotone non-decreasing in its FactorC, so the
    worst case over speed is attained at the reference's MAXIMUM FactorC -- which is reached (both
    references hard-clamp to Y[3] at speed >= 8960). One pass over the rate axis therefore gives the
    exact answer over the whole 2-D domain. Returns (worst_drop, at_rate, ref_value, v80_value)."""
    c_ref = max(S_ref.factorC(sp) for sp in range(SPEED_GATE))
    worst, at = 0, None
    for r in range(rmax + 1):
        e_ref, e_80 = S_ref.factorE(r), S80.factorE(r)
        if e_ref is None or e_80 is None:
            continue
        a = min((c_ref * e_ref) >> 10, ceil)
        b = min((FLAT_C * e_80) >> 10, ceil)
        if a - b > worst:
            worst, at = a - b, (r, a, b)
    return (worst,) + (at if at else (None, None, None))


def assert_add_only_postclamp(S80, STK, label):
    """🛑 GUARD 4, AS SCOPED. Post-clamp add-only vs STOCK inside the RULE-8 observed envelope.

    Evaluated AFTER the ceiling clamp: STOCK itself exceeds 512 at high speed and rate, so a
    pre-clamp comparison would report a drop that the hardware never delivers.
    ⚠ This is asserted ONLY inside the observed envelope (rate <= 1,941 ct, RULE 8). The full-domain
    figure is COMPUTED and REPORTED by `main`, and it is NOT zero."""
    for ceil in (CEILING_FLOOR, CEILING_TOP):
        worst, at_r, a, b = worst_drop_exact(STK, S80, ceil, OBS_RATE_MAX)
        assert worst == 0, (
            f"🛑 {label}: post-clamp add-only vs STOCK FAILS by {worst} counts at ceiling {ceil}, "
            f"rate {at_r} ct (stock {a}, V80 {b}) -- inside the RULE-8 envelope")
    # required SECOND METHOD: a direct subsampled 2-D sweep through the evaluator itself
    worst = 0
    at = None
    n = 0
    for bd, ceil in ((0, CEILING_FLOOR), (800, CEILING_TOP)):
        for sp in range(0, 9001, 29):
            for r in range(0, OBS_RATE_MAX + 1, 7):
                n += 1
                a = S80.mag(sp, r, backdrive_idx=bd)
                b = STK.mag(sp, r, backdrive_idx=bd)
                if b - a > worst:
                    worst, at = b - a, (ceil, sp, r, a, b)
    assert worst == 0, f"🛑 {label}: second method finds a {worst}-count drop vs STOCK at {at}"
    return n


def assert_factorE_untouched_vs_base(S80, S79):
    """FactorE, FactorB, FactorD and the ceiling are IDENTICAL to the base, per-index."""
    for r in range(RATE_GATE):
        a, b = S80.factorE(r), S79.factorE(r)
        assert a == b, f"FactorE moved at rate {r}: {b} -> {a}"
    for w in ("B", "D", "CEIL"):
        assert S80.XY(w) == S79.XY(w), f"Factor{w} moved"
    assert S80.ceil_fallback == S79.ceil_fallback == CEILING_FLOOR
    return RATE_GATE


def factorC_delta_vs_base(S80, S79):
    """★ Where edit 2 actually bites: FactorC is identical to V79 up to X[2] and lower above it."""
    same = [sp for sp in range(SPEED_GATE) if S80.factorC(sp) == S79.factorC(sp)]
    lower = [sp for sp in range(SPEED_GATE) if S80.factorC(sp) < S79.factorC(sp)]
    higher = [sp for sp in range(SPEED_GATE) if S80.factorC(sp) > S79.factorC(sp)]
    assert not higher, "edit 2 RAISES FactorC somewhere -- it must only lower it"
    assert same and same == list(range(len(same))), "the unchanged speed set is not a prefix"
    assert lower and min(lower) == len(same), "the changed set does not start where the same set ends"
    return len(same) - 1, min(lower), max(lower)


def first_rate_for(S, speed, thresh):
    for r in range(RATE_GATE):
        if S.mag(speed, r) >= thresh:
            return r
    return None


def probe_trip_rates(S79, S80):
    """🛑 The probe is byte-identical to V79, and the surface moved under it ONLY above 80 km/h."""
    rows = {}
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        rows[thr] = {}
        for kmh in (5, 8.05, 20, 35, 60, 80, 96.7, 120, 140):
            sp = int(round(kmh * SPEED_CTS_PER_KMH))
            rows[thr][kmh] = (first_rate_for(S79, sp, thr), first_rate_for(S80, sp, thr))
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        assert all(v[1] is not None for v in rows[thr].values()), \
            f"🛑 the |gp-0x6bd0| >= {thr} rung is STRUCTURALLY DEAD on V80 at some speed"
    # ★ speed-invariance: FactorC is flat, so both rungs must trip at the SAME rate at every speed
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        got = {v[1] for v in rows[thr].values()}
        assert len(got) == 1, \
            f"🛑 the >={thr} rung is not speed-invariant on V80 ({sorted(got)}) -- FactorC is flat, " \
            f"so it must be"
    assert DAMP_HI_THRESH < CEILING_FLOOR, "bit7's threshold no longer sits below the ceiling floor"
    lo, hi = rows[DAMP_LO_THRESH][5][1], rows[DAMP_HI_THRESH][5][1]
    assert hi > R_OP, "bit7 fires at or below R_OP -- it would be saturated, not a ~50% duty rung"
    # 🛑 the rung CANNOT discriminate V80 from V79 at creep -- state it as an assertion, not prose
    assert rows[DAMP_LO_THRESH][5][0] == lo and rows[DAMP_HI_THRESH][5][0] == hi, \
        "the creep trip rates differ between V79 and V80 -- they must not; the creep dose is equal"
    return rows, lo, hi


# =====================================================================================================
# The gp-cell census / CRC / cave -- shared, unchanged
# =====================================================================================================
cell_census = V76B.cell_census
assert_cell_censuses = V78.assert_cell_censuses
assert_pins = V78.assert_pins
owning_block = V76B.owning_block
refresh_crcs = V76B.refresh_crcs
assert_crc_chain = V76B.assert_crc_chain
changed_runs = V76B.changed_runs


def main():
    print("=" * 102)
    print("  V80 -- V79 + the V42 macro-ratchet fix (0x454FE) + FactorC m26 Y[3] 908 -> 566 (FLAT)")
    print("=" * 102)
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it"
    assert "v80" in os.path.basename(BIN_OUT).lower() and "V80" in TAG, \
        "the artefact names must carry the build number"
    for token in ("flatC566", "ratchet454FE"):
        assert token in TAG and token.lower() in os.path.basename(BIN_OUT).lower(), \
            f"the TAG and image name must both carry '{token}'"

    base = bytes(SRC_BIN.read_bytes())
    assert len(base) == 0x100000, f"the base must be 1 MiB, got 0x{len(base):X}"
    assert hashlib.sha256(base).hexdigest() == SRC_SHA256, "the base is NOT the V79 plain image"
    stock = bytes(STOCK_BIN.read_bytes())
    v42 = bytes(V42_BIN.read_bytes())
    print(f"\n  base  {SRC_BIN.name}\n        sha256 {SRC_SHA256}  VERIFIED")

    # ---- BASE IDENTITY beyond the hash: V78's own cave, re-derived from its builder ------------
    v78_cave, v78_listing = V78.build_cave()
    assert bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, \
        "the base's cave is not the one build_v78_tva.py emits -- WRONG BASE"
    assert bytes(base[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the base's hook is not already the `jarl` to the cave"
    assert bytes(stock[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, \
        "the STOCK hook site is not the `movea` the cave replays"
    assert bytes(base[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "0x55C12 is not `mov 0x8,r7` -- the proof that r7 is dead across the hook"
    print("        base cave re-derived from build_v78_tva.build_cave(): IDENTICAL (68 B)")

    # ---- everything checkable BEFORE a byte is written -----------------------------------------
    n_enc = V78._self_check_encoders(base)
    n_pay = V78._check_wire_model()
    n_pins = assert_pins(base, "V79 base")
    n_ptr = assert_pointer_arrays_stock(base, stock, "V79 base")
    nearest = assert_no_aliasing(base, "V79 base")
    assert_untouched_surfaces(base, base, "V79 base")
    assert_record_geometry(base, "V79 base")
    assert_write_addresses(base, "V79 base")
    clamp, thresh, fric = assert_fault_interlock(base, "V79 base")
    assert_not_carried(base, "V79 base")
    n_c63 = assert_c63a0_block(base, stock, "V79 base")
    assert_manual_mode_stock(base, stock, "V79 base")
    assert_cell_censuses(base, range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT), True, "V79 base")
    assert_crc_chain(base, "V79 base")
    _o, _n, bcx, bcy = read_rec(base, FACTOR_C_PTRS, LIVE_MODE)
    assert (bcx, bcy) == BASE_C26, f"FactorC m26 base is X={bcx} Y={bcy}, expected {BASE_C26}"
    br_wit = assert_br_witness(base)
    base_bcond = assert_ratchet_base(base, "V79 base")
    assert bytes(base[RATCHET_WINDOW[0]:RATCHET_WINDOW[1]]) == \
        bytes(stock[RATCHET_WINDOW[0]:RATCHET_WINDOW[1]]), \
        "the base's governor window is not byte-stock -- the one-byte claim would be false"
    n_span = assert_no_external_entry(base, "V79 base")
    print(f"  base OK: {n_enc} encoder round-trips, {n_pins} pins, {n_ptr} pointer arrays == STOCK "
          f"over {N_MODES} modes,\n           record geometry, write addresses, no aliasing, "
          f"censuses, CRC chain 50/50, {n_pay} legal payloads")
    print(f"  🛑 INTERLOCK on the base: 0xC407E = {clamp} (<= {FAULT_CLAMP_MAX}), "
          f"0xC4004 = {thresh} => trip at {FAULT_TRIP_COUNTS} counts, friction m26 @0x{fric:05X} STOCK")
    print(f"  🛑🛑 OPERATOR DIRECTIVE: 0xC63A0 = {u16(base, 0xC63A0)} on the base "
          f"({n_c63} cells 0xC63A0..0xC63AA all == {C63A0_VALUE} == STOCK). NOT RAISED, NOT TOUCHED.")
    print(f"  nearest OTHER record to the write set: {nearest[0]} bytes "
          f"({nearest[1]} @0x{nearest[2]:05X}, modes {nearest[3][:4]})")
    print(f"  🛑 RATCHET SITE ON THE BASE: 0x{EDIT_ADDR:05X} = 0x{base[EDIT_ADDR]:02X}, halfword "
          f"0x{EDIT_BASE_HW:04X}, decodes (cond 0x{base_bcond[0]:X} = BNE, target "
          f"0x{base_bcond[1]:05X}) -- STOCK, the fix is ABSENT, as expected")
    print(f"     `br` encoding validated against a REAL instance: 0x{BR_WITNESS[0]:05X} "
          f"{BR_WITNESS[1].hex()} decodes (cond 0x{br_wit[0]:X}, target 0x{br_wit[1]:05X}); "
          f"GhidraMCP reads it `br 0x{BR_WITNESS[2]:05X}`")
    print(f"     substitution block [0x{SUBST_BLOCK[0]:05X},0x{SUBST_BLOCK[1]:05X}) = {n_span} bytes: "
          f"NO external Bcond or jr/jarl enters it across FUN_0004503c")

    code = bytearray(base)
    touched = []

    # ---- EDIT 1 -- THE MACRO-RATCHET FIX ---------------------------------------------------------
    print("\n" + "-" * 102)
    print("  EDIT 1 -- 0x454FE  `bne 0x455C4` -> `br 0x455C4`.  ONE BYTE. V42's fix, restored.")
    print("-" * 102)
    before_cond, before_target = decode_bcond(code, EDIT_ADDR)
    struct.pack_into("<H", code, EDIT_ADDR, EDIT_NEW_HW)
    after_cond, after_target = decode_bcond(code, EDIT_ADDR)
    assert (before_cond, after_cond) == (COND_BNE, COND_BR)
    assert before_target == after_target == SUBST_BLOCK[1], (
        f"🛑 the branch TARGET moved: 0x{before_target:05X} -> 0x{after_target:05X}. Only the "
        f"condition nibble may change.")
    assert code[EDIT_ADDR + 1] == base[EDIT_ADDR + 1] == 0x65, \
        "the HIGH byte of the branch halfword moved -- the displacement would change"
    assert code[EDIT_ADDR] == EDIT_NEW_BYTE
    touched.append(EDIT_ADDR)
    print(f"    0x{EDIT_ADDR:05X}  0x{EDIT_BASE_BYTE:02X} -> 0x{EDIT_NEW_BYTE:02X}   halfword "
          f"0x{EDIT_BASE_HW:04X} -> 0x{EDIT_NEW_HW:04X}   (0x{EDIT_ADDR + 1:05X} stays "
          f"0x{code[EDIT_ADDR + 1]:02X})")
    print(f"    cond nibble 0x{before_cond:X} (BNE) -> 0x{after_cond:X} (BR); target UNCHANGED at "
          f"0x{after_target:05X}, decoded BOTH sides")
    n_wit = assert_ratchet_witness(code, v42, "after edit 1")
    print(f"    ★ [EVIDENCE] the whole {n_wit}-byte window [0x{RATCHET_WINDOW[0]:05X},"
          f"0x{RATCHET_WINDOW[1]:05X}) is now BYTE-IDENTICAL to the FLOWN _v42_plain_image.bin")
    n_diff = assert_ratchet_window_vs_stock(code, stock, "after edit 1")
    print(f"    ★ the same window differs from STOCK in EXACTLY {n_diff} byte: 0x{EDIT_ADDR:05X}")
    assert_ratchet_present(code, "after edit 1")
    assert_no_external_entry(code, "after edit 1")

    # ---- EDIT 2 -- FactorC m26 Y[3] --------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  EDIT 2 -- FactorC mode 26 (ENGAGED) Y[3] 908 -> 566.  ONE u16 CELL.  X, mode 24, "
          "FactorE UNTOUCHED.")
    print("-" * 102)
    off, n, ox, oy = read_rec(code, FACTOR_C_PTRS, LIVE_MODE)
    assert (ox, oy) == BASE_C26, f"FactorC m26 base is X={ox} Y={oy}, expected {BASE_C26}"
    assert off == u32(code, FACTOR_C_PTRS + 4 * LIVE_MODE) == EXPECT_ADDR[("C", LIVE_MODE)]
    print(f"    pointer array 0x{FACTOR_C_PTRS:05X} + 26*4 = 0x{FACTOR_C_PTRS + 104:05X} "
          f"-> record 0x{off:05X}  (n={n}, rec_len={rec_len(n)})")
    slack_before = bytes(code[off + REC_DATA_LEN:off + REC_STRIDE])
    woff, wlen = write_rec(code, FACTOR_C_PTRS, LIVE_MODE, *NEW_C26)
    assert wlen == REC_DATA_LEN, f"wrote {wlen}B, expected {REC_DATA_LEN}"
    assert bytes(code[off + REC_DATA_LEN:off + REC_STRIDE]) == slack_before, \
        "🛑 FactorC m26: the 2 slack bytes changed -- this is the V73 spill"
    touched.extend(range(off, off + REC_DATA_LEN))
    print(f"    FactorC m26 @0x{woff:05X}  X {ox} -> {NEW_C26[0]}   (UNCHANGED)")
    print(f"    {'':>18s}  Y {oy} -> {NEW_C26[1]}")
    for a, (old, new, lbl) in sorted(EXPECTED_CELL_WRITES.items()):
        print(f"      0x{a:05X}  {lbl:<20s} {old:5d} = 0x{old:04X}  ->  {new:5d} = 0x{new:04X}   "
              f"bytes {old.to_bytes(2, 'little').hex()} -> {new.to_bytes(2, 'little').hex()}")

    # ---- EDIT 3 -- INHERITED, ASSERTED ----------------------------------------------------------
    _o, _n, ex, ey = read_rec(code, FACTOR_E_PTRS, LIVE_MODE)
    assert (ex, ey) == BASE_E26, f"🛑 EDIT 3 MISSING: FactorE m26 is X={ex} Y={ey}"
    assert bytes(code[_o:_o + REC_STRIDE]) == bytes(base[_o:_o + REC_STRIDE]), \
        "FactorE m26 bytes moved -- edit 3 is inherited, not written"
    print(f"\n  EDIT 3 (INHERITED, NOT REWRITTEN) -- FactorE m26 @0x{_o:05X}  X {ex}  Y {ey}")
    print(f"    0 bytes written. Asserted BY VALUE on the base, the built image and the readback.")

    # ---- the write set, derived from the image, checked against the spec ------------------------
    runs1 = changed_runs(base, code)
    got = {}
    for a, ln in runs1:
        for w in range(a, a + ln):
            got[w] = (base[w], code[w])
    want = {EDIT_ADDR: (EDIT_BASE_BYTE, EDIT_NEW_BYTE)}
    for a, (old, new, _l) in EXPECTED_CELL_WRITES.items():
        for i in range(2):
            ob, nb = old.to_bytes(2, "little")[i], new.to_bytes(2, "little")[i]
            if ob != nb:
                want[a + i] = (ob, nb)
    assert got == want, (
        f"the write set differs from the spec: got {sorted(map(hex, got))}, "
        f"spec {sorted(map(hex, want))}")
    print(f"\n    write set VERIFIED against the spec: {len(got)} changed byte(s) in "
          f"{len(runs1)} run(s) -- {', '.join(f'0x{a:05X}' for a in sorted(got))}")

    assert_manual_mode_stock(code, stock, "after edits")
    assert_untouched_surfaces(code, base, "after edits")
    assert_fault_interlock(code, "after edits")
    assert_not_carried(code, "after edits")
    assert_c63a0_block(code, stock, "after edits")
    assert_pointer_arrays_stock(code, stock, "after edits")
    assert_write_addresses(code, "after edits")
    assert_ratchet_present(code, "after edits")

    # ---- THE SURFACE GUARDS ----------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  SURFACE GUARDS  (v76_surface's per-instruction mirror of FUN_00034350)")
    print("-" * 102)
    S79, S80, STK = surfaces(base, code)
    n_flat = assert_factorC_flat(S80, "GUARD 1 built FactorC m26")
    assert_table_shape(*S80.XY("E"), label="GUARD 2 built FactorE m26")
    print(f"    GUARD 1  FactorC Y {S80.XY('C')[1]} -- CONSTANT {FLAT_C} at ALL {n_flat:,} gated "
          f"speed indices\n             (exhaustive through the real LERP, not the four knots); "
          f"X {S80.XY('C')[0]} strictly increasing")
    print(f"    GUARD 2  FactorE Y {S80.XY('E')[1]} STRICTLY increasing, E_Y[0] == 0 retained "
          f"(no Coulomb relay)")

    n_e = assert_factorE_untouched_vs_base(S80, S79)
    print(f"    GUARD 3  FactorE identical to V79 at all {n_e:,} gated rate indices; "
          f"FactorB/D/ceiling identical")

    peak, e_max, n_clip, sup = assert_never_clips(S80, "GUARD 4 built")
    print(f"    GUARD 4  🛑 V80 NEVER CLIPS. max ({FLAT_C}*E)>>10 over EVERY gated rate = {peak} "
          f"== the ceiling FLOOR {CEILING_FLOOR}\n             (E_max = {e_max}); second method -- "
          f"the evaluator's own clip flag, 0 of {n_clip:,} points at\n             ceiling "
          f"{CEILING_FLOOR} AND {CEILING_TOP}; third -- sup|gp-0x6bd0| over the whole domain = {sup}")

    n_add = assert_add_only_postclamp(S80, STK, "GUARD 5")
    print(f"    GUARD 5  POST-CLAMP ADD-ONLY vs STOCK inside the RULE-8 envelope (rate <= "
          f"{OBS_RATE_MAX:,} ct):\n             worst drop 0 at ceiling {CEILING_FLOOR} AND "
          f"{CEILING_TOP}, EXACT (closed form over C_max, all speeds);\n             second method "
          f"-- direct 2-D sweep through the evaluator, {n_add:,} points, worst drop 0")

    # ---- the dose arithmetic ---------------------------------------------------------------------
    d80 = S80.mag(SPEED_5MPH_CT, R_OP)
    d79 = S79.mag(SPEED_5MPH_CT, R_OP)
    e99 = S80.factorE(R_OP)
    c515 = S80.factorC(SPEED_5MPH_CT)
    k80 = ((c515 * NEW_E26[1][1]) >> 10) / (NEW_E26[0][1] - NEW_E26[0][0])
    assert c515 == FLAT_C and d80 == DOSE_TARGET == d79 == V79_DOSE, \
        f"the target arithmetic does not reproduce: E(99)={e99} C(515)={c515} dose={d80}"
    doses = {kmh: S80.mag(int(round(kmh * SPEED_CTS_PER_KMH)), R_OP)
             for kmh in (5, 8.05, 20, 35, 60, 80, 96.7, 120, 140)}
    assert set(doses.values()) == {DOSE_TARGET}, \
        f"🛑 the dose is NOT flat in speed: {doses} -- FactorC's flatness did not carry through"
    print(f"\n    E({R_OP}) = {NEW_E26[1][1]}*{R_OP}//{NEW_E26[0][1]} = {e99}  ·  "
          f"C = {c515} at EVERY speed  ·  dose = ({c515}*{e99})>>10 = {d80}")
    print(f"    ★ dose({R_OP} ct) = {DOSE_TARGET} at EVERY speed 5 -> 140 km/h "
          f"{sorted(set(doses.values()))} -- FLAT, a first in this lineage")
    print(f"    dose {d80} = {d80 / V78_DOSE:.3f}x V78's {V78_DOSE}  ·  "
          f"{d80 / V75_DOSE:.3f}x V75's {V75_DOSE}  ·  {d80 / V79_DOSE:.3f}x V79's {V79_DOSE}")
    print(f"    k = (({FLAT_C}*{NEW_E26[1][1]})>>10)/{NEW_E26[0][1]} = "
          f"{(FLAT_C * NEW_E26[1][1]) >> 10}/{NEW_E26[0][1]} = {k80:.4f}")
    print(f"    🛑 k IS UNCHANGED FROM V79 AND IS THE HIGHEST THIS KIT HAS BUILT: {k80 / 2.0798:.3f}x "
          f"V78, {k80 / 1.5798:.3f}x V75,\n       {k80 / 1.3866:.3f}x V76. Edit 2 removes the RAIL, "
          f"not the GAIN. GATE 2 is NOT satisfied by argument.")

    # ---- 🛑 WHAT EDIT 2 COSTS -- reported, not swallowed -----------------------------------------
    print("\n    🛑🛑 WHAT GUARD 5 DOES **NOT** COVER -- the drops OUTSIDE the RULE-8 envelope")
    top_same, first_lower, last_lower = factorC_delta_vs_base(S80, S79)
    print(f"       edit 2 leaves FactorC IDENTICAL to V79 up to {top_same} ct = "
          f"{top_same / SPEED_CTS_PER_KMH:.2f} km/h and LOWERS it\n       from {first_lower} ct "
          f"({first_lower / SPEED_CTS_PER_KMH:.2f} km/h) upward. It never raises it.")
    print(f"       {'reference':>9} {'ceiling':>8} {'rate cap':>10} {'worst drop':>11} "
          f"{'at rate':>22}")
    for ceil in (CEILING_FLOOR, CEILING_TOP):
        for rmax, tag in ((OBS_RATE_MAX, "RULE 8 observed"), (RATE_GATE - 1, "whole gated domain")):
            w, at_r, a, b = worst_drop_exact(STK, S80, ceil, rmax)
            loc = "--" if at_r is None else f"{at_r} ct = {at_r / RATE_CTS_PER_DEGS:.0f} deg/s"
            print(f"       {'STOCK':>9} {ceil:>8} {tag:>18} {w:>11} {loc:>22}")
    for ceil in (CEILING_FLOOR, CEILING_TOP):
        w, at_r, a, b = worst_drop_exact(S79, S80, ceil, RATE_GATE - 1)
        loc = "--" if at_r is None else f"{at_r} ct = {at_r / RATE_CTS_PER_DEGS:.0f} deg/s"
        print(f"       {'V79':>9} {ceil:>8} {'whole gated domain':>18} {w:>11} {loc:>22}")
    # 🛑 every number in this sentence is COMPUTED, never a literal -- the prose cannot drift from
    #    the table above it (an earlier draft of this file said 309 where the exact figure is 310).
    w512 = worst_drop_exact(STK, S80, CEILING_FLOOR, RATE_GATE - 1)[0]
    w1024 = worst_drop_exact(STK, S80, CEILING_TOP, RATE_GATE - 1)[0]
    first_drop = next(((sp, r) for sp in range(0, SPEED_GATE, 7) for r in range(0, RATE_GATE, 13)
                       if STK.mag(sp, r) > S80.mag(sp, r)), None)
    print("       ⇒ vs STOCK the post-clamp add-only claim is TRUE inside the observed envelope and")
    print(f"         FALSE outside it, by {w512} counts at ceiling {CEILING_FLOOR} and {w1024} at "
          f"ceiling {CEILING_TOP} -- the FIRST\n         drop anywhere (ceiling {CEILING_FLOOR}) is "
          f"at {first_drop[0] / SPEED_CTS_PER_KMH:.0f} km/h AND "
          f"{first_drop[1] / RATE_CTS_PER_DEGS:.0f} deg/s of column rate, and it is 1 count.\n"
          f"         **Reported, not asserted.**")
    print("       ⇒ vs V79 this build is DELIBERATELY SUBTRACTIVE above 80 km/h. That IS edit 2.")
    print("         Mode 24 (MANUAL) stays byte-stock, which bounds the exposure to engaged driving.")

    # ---- the clip census, both builds -------------------------------------------------------------
    print("\n    THE RAIL EDIT 2 REMOVES -- clip fraction over the RULE-8 (speed, rate) envelope")
    print(f"       {'ceiling':>8} | {'V79':>18} | {'V80':>18} | {'STOCK':>18}")
    for bd, ceil in ((0, CEILING_FLOOR), (800, CEILING_TOP)):
        cells = []
        for S in (S79, S80, STK):
            c, n = clip_fraction(S, bd)
            cells.append(f"{c:,}/{n:,} = {100 * c / n:.2f}%")
        print(f"       {ceil:>8} | {cells[0]:>18} | {cells[1]:>18} | {cells[2]:>18}")
    print("       ⇒ RULE 12(b): a railed damper takes its SIGN from gp-0x6abe and its INDEX from")
    print("         gp-0x6ac0 -- different cells -- so it IS a Coulomb relay. V80 closes that")
    print("         provably and unconditionally, at every ceiling the LERP can produce.")

    # ---- THE PROBE'S TRIP RATES ------------------------------------------------------------------
    trip, lo80, hi80 = probe_trip_rates(S79, S80)
    print("\n    PROBE TRIP RATES -- the cave is byte-identical to V79; the surface moved only >80 km/h")
    print(f"       {'km/h':>7} | {'bit6 >=192  V79':>18} {'V80':>18} | "
          f"{'bit7 >=448  V79':>18} {'V80':>18}")
    for kmh in (5, 8.05, 20, 35, 60, 80, 96.7, 120, 140):
        cells = []
        for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
            for r in trip[thr][kmh]:
                cells.append("never" if r is None
                             else f"{r} ct = {r / RATE_CTS_PER_DEGS:.1f} d/s")
        print(f"       {kmh:>7} | {cells[0]:>18} {cells[1]:>18} | {cells[2]:>18} {cells[3]:>18}")
    print(f"       🛑 BOTH RUNGS ARE NOW SPEED-INVARIANT: bit6 at {lo80} ct "
          f"({lo80 / RATE_CTS_PER_DEGS:.1f} deg/s) and bit7 at {hi80} ct\n          "
          f"({hi80 / RATE_CTS_PER_DEGS:.1f} deg/s) at EVERY speed, because FactorC is flat.")
    print(f"       🛑 THE PROBE CANNOT DISCRIMINATE V80 FROM V79 BELOW 80 km/h -- the creep dose is")
    print(f"          identical by construction. Above it V80 trips LATER. A non-zero bit7 is")
    print(f"          EXPECTED (it fires just above R_OP = {R_OP} ct = "
          f"{R_OP / RATE_CTS_PER_DEGS:.1f} deg/s) and is NOT evidence of a fault.")

    # ---- THE PROBE CAVE, CARRIED UNCHANGED --------------------------------------------------------
    print("\n" + "-" * 102)
    print(f"  THE {CAVE_EXTENT}-BYTE PROBE CAVE @0x{CAVE_BASE:05X}: CARRIED FROM V79/V78, NOT REWRITTEN")
    print("-" * 102)
    redis = V78.redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    for addr, raw, text in redis:
        print(f"    0x{addr:05X}  {raw.hex():<8s}  {text}")
    assert b"".join(r for _a, r, _t in redis) == v78_cave, \
        "the re-disassembly does not reconstruct the base's cave bytes"
    assert [(a, r) for a, r, _t in redis] == [(a, r) for a, r, _t in v78_listing], \
        "the base's cave does not re-disassemble to build_v78_tva's emitted listing"
    n_emul = V78._check_emulator(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    print(f"\n    RE-EMULATED from the image bytes on a V850 interpreter, compared to the mirror "
          f"over\n    {n_emul:,} (state, mode, |d|, status) combinations -- ALL MATCH. "
          f"ZERO cave bytes changed.")
    assert bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == \
        bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, "the cave moved"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the hook must stay the base's `jarl` -- this build does not re-hook"
    assert bytes(code[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        bytes(base[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the cave tail is not virgin 0xFF"

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_cell_censuses(code, cave_span, True, "after the cave check")
    assert_pins(code, "after the cave check")

    # ---- CRC ------------------------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  CRC")
    print("-" * 102)
    changed = refresh_crcs(code, touched)
    assert len(changed) == 2, \
        f"{len(changed)} CRC trailer(s) rewritten -- the two edits live in two DIFFERENT blocks " \
        f"(0x454FE in [0x13000,0xC4FFC), 0xD77E0 in [0xD7000,0xD7FFC)), so exactly 2 are expected"
    for trailer, (old, new, bstart) in sorted(changed.items()):
        touched.extend(range(trailer, trailer + 4))
        print(f"    block [0x{bstart:05X}, 0x{trailer:05X})  trailer 0x{old:08X} -> 0x{new:08X}")
    n_blocks = assert_crc_chain(code, "V80")
    print(f"    {len(changed)} trailers rewritten; full chain re-verified: {n_blocks}/50 blocks PASS")

    # ---- the full attributed diff ---------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  FULL BYTE DIFF  V79 -> V80")
    print("-" * 102)
    c_rec = rec_addr(code, FACTOR_C_PTRS, LIVE_MODE)
    groups = {}
    for a, ln in changed_runs(base, code):
        if c_rec <= a and a + ln <= c_rec + REC_STRIDE:
            g = "1 FactorC m26 Y[3]"
        elif a == EDIT_ADDR and ln == 1:
            g = "2 governor branch 0x454FE"
        elif CAVE_BASE <= a < CAVE_BASE + CAVE_EXTENT:
            g = "3 probe cave (MUST BE ABSENT)"
        elif any(t <= a < t + 4 for t in changed):
            g = "4 CRC trailer"
        else:
            g = "UNATTRIBUTED"
        groups.setdefault(g, []).append((a, ln))
    total = 0
    for g in sorted(groups):
        n = sum(ln for _a, ln in groups[g])
        total += n
        print(f"    {g:30s} {len(groups[g]):3d} run(s) {n:4d} byte(s)   "
              f"{', '.join(f'0x{a:05X}+{ln}' for a, ln in groups[g][:5])}"
              f"{' ...' if len(groups[g]) > 5 else ''}")
    assert "UNATTRIBUTED" not in groups, f"UNATTRIBUTED bytes: {groups.get('UNATTRIBUTED')}"
    assert "3 probe cave (MUST BE ABSENT)" not in groups, "the cave changed -- it must not"
    assert groups["2 governor branch 0x454FE"] == [(EDIT_ADDR, 1)], \
        "the governor edit is not exactly one byte at 0x454FE"
    tbl = groups["1 FactorC m26 Y[3]"]
    tbl_bytes = sum(ln for _a, ln in tbl)
    assert tbl_bytes == 2 and len(tbl) == 1, \
        f"the table delta is {tbl_bytes} bytes across {len(tbl)} run(s) -- expected ONE cell (2 B)"
    assert tbl[0][0] == FACTOR_C_Y3_ADDR, \
        f"the table diff run starts at 0x{tbl[0][0]:05X}, expected 0x{FACTOR_C_Y3_ADDR:05X}"
    print(f"    TOTAL {sum(len(v) for v in groups.values())} runs, {total} bytes, ALL ATTRIBUTED")
    print(f"    🛑 the delta is 1 CODE BYTE (0x{EDIT_ADDR:05X}) + 1 CAL CELL "
          f"(0x{FACTOR_C_Y3_ADDR:05X}, both bytes move:\n       908 = 0x038C -> 566 = 0x0236) + "
          f"{len(changed)} CRC trailers. Nothing else.")

    # ---- write + .rwd ---------------------------------------------------------------------------
    assert BIN_OUT not in FORBIDDEN_OVERWRITE, \
        f"🛑 {BIN_OUT} is a retired or BASE snapshot path -- a same-number re-cut has destroyed a " \
        "predecessor's snapshot before and produced an artefact no gate could check"
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image is already there (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). Rename it deliberately, then re-run.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n        SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "the source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "container source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V80 output")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # ---- 🛑 EVERYTHING re-derived FROM THE READBACK --------------------------------------------
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec[START:END]) == bytes(code[START:END]), "the decoded payload != the built image"

    rb_bcond = assert_ratchet_present(dec, "readback")          # 🛑 EDIT 1, from the .rwd bytes
    assert_ratchet_witness(dec, v42, "readback")
    assert_ratchet_window_vs_stock(dec, stock, "readback")
    assert_no_external_entry(dec, "readback")
    assert_pins(dec, "readback")
    assert_pointer_arrays_stock(dec, stock, "readback")
    assert_no_aliasing(dec, "readback")
    assert_untouched_surfaces(dec, base, "readback")
    assert_record_geometry(dec, "readback")
    assert_write_addresses(dec, "readback")
    rb_clamp, rb_thresh, rb_fric = assert_fault_interlock(dec, "readback")
    assert_not_carried(dec, "readback")
    rb_c63 = assert_c63a0_block(dec, stock, "readback")
    assert_manual_mode_stock(dec, stock, "readback")
    assert_cell_censuses(dec, cave_span, True, "readback")
    assert_crc_chain(dec, "readback")
    _o, _n, rcx, rcy = read_rec(dec, FACTOR_C_PTRS, LIVE_MODE)
    assert (rcx, rcy) == NEW_C26, f"readback FactorC m26 is X={rcx} Y={rcy}, expected {NEW_C26}"
    _o, _n, rex, rey = read_rec(dec, FACTOR_E_PTRS, LIVE_MODE)
    assert (rex, rey) == NEW_E26, f"readback FactorE m26 is X={rex} Y={rey}, expected {NEW_E26}"
    S_rb = VS.Surface(img=bytes(dec), mode=LIVE_MODE)
    assert S_rb.mag(SPEED_5MPH_CT, R_OP) == DOSE_TARGET, "the readback dose is not 412"
    assert {S_rb.mag(int(round(k * SPEED_CTS_PER_KMH)), R_OP)
            for k in (5, 20, 60, 100, 140)} == {DOSE_TARGET}, "the readback dose is not FLAT"
    assert_factorC_flat(S_rb, "readback FactorC m26")
    assert_table_shape(*S_rb.XY("E"), label="readback FactorE m26")
    assert_never_clips(S_rb, "readback")
    assert_add_only_postclamp(S_rb, STK, "readback")
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v78_cave, \
        "the readback cave is not V78's"
    assert bytes(dec[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "readback: the hook is not the `jarl` to the cave"
    assert bytes(dec[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "readback: the hook's return site 0x55C12 was disturbed"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]).count(HOOK_STOCK) == 1, \
        "readback: the displaced `movea` is not replayed EXACTLY once in the cave"
    assert bytes(dec[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the readback cave tail is not 0xFF"
    redis_rb = V78.redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    assert [(a, r) for a, r, _t in redis_rb] == [(a, r) for a, r, _t in v78_listing], \
        "the readback cave does not re-disassemble to V78's emitted listing"
    assert V78._check_emulator(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])) == n_emul
    assert sum(ln for _a, ln in changed_runs(base, dec)) == total, "the readback diff size differs"

    print("\n  READBACK -- re-derived FROM THE DECODED .rwd BYTES: the 0x454FE branch decoded to")
    print(f"     (BR, 0x{rb_bcond[1]:05X}) and matched against the FLOWN V42 image; the FactorC and")
    print("     FactorE records via their pointer arrays; the flat dose 412; the never-clips guard;")
    print("     post-clamp add-only vs STOCK; mode-24 identity vs STOCK; all six pointer arrays; the")
    print(f"     DTC-0x1d interlock; 0xC63A0 ({rb_c63} cells) = 1024; the dropped levers; all "
          f"{n_pins} pins;\n     every probed cell's census; the whole 68-byte cave, its "
          f"re-disassembly, its re-EMULATION,\n     its tail; and the full 50-block CRC chain. "
          f"ALL PASS.")
    print(f"\n  wrote {OUT}\n        SHA256 {rwd_sha}")

    print("\n" + "=" * 102)
    print("  V80 BUILT on the V79 base.  🛑 UNFLASHED. NOT A FLASH CLEARANCE. NOT CLEARED TO FLY.")
    print(f"  ★ EDIT 1  0x{EDIT_ADDR:05X}  0x{EDIT_BASE_BYTE:02X} -> 0x{EDIT_NEW_BYTE:02X}  "
          f"`bne 0x{SUBST_BLOCK[1]:05X}` -> `br 0x{SUBST_BLOCK[1]:05X}`.  V42's MACRO-RATCHET FIX,")
    print("            off the car since V53, RESTORED. Window byte-identical to the flown V42 image.")
    print(f"  ★ EDIT 2  FactorC m26 Y[3] 908 -> 566 @0x{FACTOR_C_Y3_ADDR:05X}. FactorC is now FLAT "
          f"{FLAT_C} at every speed,")
    print(f"            so max|gp-0x6bd0| = {peak} == the ceiling floor: V80 clips 0.00% where V79 "
          f"clips 38.95%.")
    print(f"  ★ EDIT 3  FactorE m26 X {NEW_E26[0]} Y {NEW_E26[1]} -- INHERITED, 0 bytes written.")
    print(f"     dose({R_OP} ct) = {DOSE_TARGET} at EVERY speed = {DOSE_TARGET / V78_DOSE:.3f}x V78, "
          f"{DOSE_TARGET / V75_DOSE:.3f}x V75, {DOSE_TARGET / V79_DOSE:.3f}x V79.")
    print(f"  🛑 k = {k80:.4f} -- UNCHANGED from V79 and still the HIGHEST LOOP GAIN THIS KIT HAS "
          f"BUILT.\n     Edit 2 removes the RAIL, not the GAIN. GATE 2 (magnitude AND phase) is NOT "
          f"satisfied by argument.\n     The damper's forward path to the motor is still NOT FOUND, "
          f"so the 2x is PREDICTED, not PROVEN.")
    print(f"  🛑 INTERLOCK CARRIED: 0xC407E = {rb_clamp} against a {FAULT_TRIP_COUNTS}-count trip "
          f"(0xC4004 = {rb_thresh});")
    print(f"     friction m26 @0x{rb_fric:05X} byte-stock; MODE 24 byte-STOCK; FactorE untouched;")
    print(f"     🛑🛑 0xC63A0 = {u16(dec, 0xC63A0)} (STOCK, NOT RAISED) -- the operator's explicit "
          f"directive.")
    print("  🛑 EDIT 2 IS SUBTRACTIVE ABOVE 80 km/h vs V79, and vs STOCK the post-clamp add-only")
    print("     claim holds only inside the RULE-8 envelope. Both quantified above. Engaged mode only.")
    print(f"  ★ probe UNCHANGED (0 cave bytes moved); both rungs now SPEED-INVARIANT -- bit6 at "
          f"{lo80} ct\n     ({lo80 / RATE_CTS_PER_DEGS:.1f} deg/s), bit7 at {hi80} ct "
          f"({hi80 / RATE_CTS_PER_DEGS:.1f} deg/s). It CANNOT tell V80 from V79 below 80 km/h.")
    print(f"     bit{V78.BITS_CLEAR[0]} is STRUCTURALLY ZERO and bit{BIT_DAMP_HI} ALWAYS implies "
          f"bit{BIT_DAMP_LO}. Legal byte4 & 0xF8 =")
    print(f"     {sorted(hex(v) for v in LEGAL_PAYLOAD_HI)}")
    print("     Any payload with byte4 & 0x20, or bit7 without bit6, is an integrity failure.")
    print("     Read bit3 FIRST: all-zero on bits 7,6,4,3 for a whole drive = the cave never fired.")
    print("  🛑 GRIND #1 ONLY for edits 2/3. Edit 1 targets the MACRO-ratchet; the MICRO-ratchet is")
    print("     DOSE-INDEPENDENT (slope CI contains zero) and must not be scored against this build.")
    print("  🛑 Flash ONLY on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    main()
