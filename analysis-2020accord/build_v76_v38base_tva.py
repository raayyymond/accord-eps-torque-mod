#!/usr/bin/env python3
"""build_v76_v38base_tva.py -- V76 RE-CUT ON A **V38 BASE**. Supersedes V76/V77/V77B.

★★★★ THE ONE-LINE REASON THIS FILE EXISTS. Two hard faults in two days -- a latched total loss of
power steering requiring an engine restart -- one ENGAGED (V75) and one **MANUAL** (V74, over a
bump). The mechanism was found and orchestrator-verified: `FUN_00036d74`, called UNCONDITIONALLY
from the 1 kHz task `FUN_0002214a` @0x2290a, tests `|gp-0x6b26| / 1024 > cal(0xC4004)` and faults
straight to DTC 0x1d. `0xC4004` is **0.5 = 512 raw counts**; `gp-0x6b26` is clamped to +/-`0xC407E`,
which is **511 in stock and in V38** -- exactly ONE count under the ceiling. That is an INTERLOCK,
not a coincidence. **V73 raised `0xC407E` to 850 (338 counts past the ceiling) and V74's x1.5
friction table then made the crossing easy.** Every build from V73 onward carried the breach.

⇒ This build abandons the V73/V74/V75 lineage entirely and re-cuts from **V38**, the last base whose
friction lane is provably inside the interlock. It carries THREE edit groups and nothing else.

    GROUP 1  the mode-26 damper surface (FactorC + FactorE). Mode 24 stays BYTE-STOCK.
    GROUP 2  a 68-byte probe cave at 0xC4B34, hooked at 0x55C0E.
    GROUP 3  -- there is no group 3. Nothing else changes.

🛑 DELIBERATELY **NOT** CARRIED FORWARD, and asserted absent cell by cell below:
    0xC63A0 = 2048     (V72's LEVER C -- the Path-2 damper weight; stays STOCK 1024)
    0xC407E = 850      (V73's friction clamp -- stays STOCK 511, INSIDE the fault interlock)
    the x1.5 friction table  (V74's LEVER D' -- mode-26 friction record stays byte-stock)
    V73's mode-0..17 FactorC/FactorE edits  (this build touches mode 26 and nothing else)
Their absence is the POINT of the build, so each one is an assertion here, not a comment.

CAVE DISCIPLINE
---------------
🛑 Growing a cave is this kit's ONLY bricking class -- V24, V27 and V48B all bricked the ECU. The
extent is 68 bytes, asserted on the emitted bytes, on the built image AND on the .rwd readback.
Padding sits AFTER `jmp [lp]` and is proven unreachable by the branch-geometry assertions.
🛑 `r10` is LIVE across the hook. The cave writes r6/r7/r11/r15 and flags ONLY -- asserted from the
   emitted encodings, not from the comments.

WHY A NEW FILENAME AND NOT `build_v76_tva.py`
---------------------------------------------
`build_v76_tva.py` builds the SUPERSEDED V76 (`…_v76_gate_fb_arm5244_gateprobe_…`), whose .rwd is
still on disk as `SUPERSEDED-2026-08-07-BY-V76-V38BASE-…`. Overwriting the script would leave that
artefact unreproducible -- the same class of hazard as the recorded same-number re-cut that
destroyed a predecessor's plain image and produced an artefact no gate could check. Distinct file,
distinct image tag, distinct .rwd name.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, encoders, crc_block_map)
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl / cmp_rr)
import build_v55_tva as V55                # noqa: E402  (ldh / ldbu_any / cmp_imm5)
import build_v68_tva as V68                # noqa: E402  (cave geometry constants)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7    # gp = r4
R11, R15 = 11, 15

# =====================================================================================================
# THE BASE -- V38
# =====================================================================================================
SRC_BIN = plain_image_path("_v38_plain_image.bin")
SRC_SHA256 = "a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8"
STOCK_BIN = stock_fw_path("code.bin")

# ⚠ A DISTINCT tag. It must not collide with `_v76_gate_fb_arm5244_gateprobe_plain_image.bin`, the
# superseded V76's snapshot -- a same-number re-cut has destroyed a predecessor's snapshot before.
BIN_OUT = str(plain_image_path("_v76_v38base_relu_damper_plain_image.bin"))
FORBIDDEN_OVERWRITE = str(plain_image_path("_v76_gate_fb_arm5244_gateprobe_plain_image.bin"))

# ⚠ DELIBERATELY SHORT -- V71A overran Windows' 260-char path limit and failed the .rwd write AFTER
# the image was already on disk. The length is asserted BEFORE anything is written.
TAG = "V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =====================================================================================================
# 🛑🛑 THE SAFETY-CRITICAL INTERLOCK THIS BUILD EXISTS TO RESTORE
# =====================================================================================================
# `FUN_00036d74` <- called UNCONDITIONALLY from the 1 kHz task `FUN_0002214a` @0x2290a.
# It computes `|gp-0x6b26| / 1024` and faults to DTC 0x1d when that exceeds `cal(0xC4004)`.
#   0xC4004 = f32 0.5  ⇒  the trip point is 0.5 * 1024 = 512 raw counts.
#   gp-0x6b26 is clamped to +/- cal(0xC407E).
#   STOCK / V38: 0xC407E = 511  ⇒  the clamp sits ONE count under the trip point. AN INTERLOCK.
#   V73:         0xC407E = 850  ⇒  338 counts PAST the ceiling. V74's x1.5 friction made the
#                                  crossing easy. BOTH V74 AND V75 HARD-FAULTED.
# ⇒ These three assertions are the single most important guard in this file. They are checked on the
#   base, on the built image and on the .rwd readback. If any fails: STOP. Do not relax them.
FAULT_CLAMP_ADDR = 0xC407E          # the friction-lane clamp
FAULT_CLAMP_MAX = 511               # 🛑 <= 511. NEVER raise this without re-deriving 0xC4004.
FAULT_THRESH_ADDR = 0xC4004         # the f32 threshold FUN_00036d74 compares against
FAULT_THRESH_VALUE = 0.5
FAULT_THRESH_BYTES = bytes.fromhex("0000003f")
FAULT_SCALE = 1024                  # the divisor in FUN_00036d74
FAULT_TRIP_COUNTS = 512             # 0.5 * 1024
FAULT_CELL_DISP = 0x6B26            # gp-0x6b26, the monitored signal
FRICTION_PTR_ARRAY = 0xCBE74
FRICTION_M26_EXPECT = 0xD7A54       # asserted, then re-derived from the pointer array
FRICTION_M26_STOCK_XY = ([0, 1280, 5760], [-9830, -5734, -1966])

# The cells V73/V74/V75 moved and this build must NOT. Value = what V38/STOCK carries.
NOT_CARRIED = {
    0xC63A0: (1024, "V72 LEVER C raised this to 2048 -- the Path-2 damper weight. STAYS STOCK."),
    0xC407E: (511, "V73 raised this to 850 and breached the DTC-0x1d interlock. STAYS STOCK."),
    0xC407C: (461, "the clamp's neighbour, owner unidentified. Untouched."),
    0xC6444: (512, "gain_A arm. Untouched on this base."),
    0xC6446: (512, "gain_B arm. Untouched on this base."),
    0xC643E: (1536, "untouched on this base."),
}

# =====================================================================================================
# GROUP 1 -- THE MODE-26 DAMPER SURFACE
# =====================================================================================================
# Records are `[u16 count][count x int16 X][count x int16 Y]`, little-endian, resolved through a
# pointer array of u32s, stride 4, indexed by mode.
FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
N_MODES = 34
LIVE_MODE = 26                      # engaged. V73's on-car probe, not an inference.
MANUAL_MODE = 24                    # 🛑 must stay BYTE-STOCK -- manual steering
THIS_CAR_KEY = "TVCA4"

# 🛑 rec_len = 4 + 4*count -- a 4-point record occupies 0x14 bytes (2 count + 16 data + 2 slack), and
# consecutive records are 0x14 apart. V73 used a FLAT 0x18 window and **spilled into the next mode's
# record**. That bug is on record. This builder writes exactly `2 + 4*count` bytes and asserts the
# 2 slack bytes are untouched.
def rec_len(count):
    return 4 + 4 * count

REC_STRIDE = 0x14                   # == rec_len(4)
REC_DATA_LEN = 18                   # == 2 + 4*4 -- what we actually write

# The expected geometry, stated independently and asserted after dereferencing, so a pointer-array
# misread cannot silently retarget the write.
EXPECT_ADDR = {("C", 24): 0xD67E4, ("C", 26): 0xD77D0,
               ("E", 24): 0xD6820, ("E", 26): 0xD780C}

# The V38 base contents of the two records we edit, asserted before writing.
BASE_C26 = ([2240, 3840, 5120, 8960], [0, 234, 429, 908])
BASE_E26 = ([60, 400, 2500, 4000], [0, 140, 539, 927])

# ---------------------------------------------------------------------------------------------------
# ✅ TableDesign's VALIDATED arrays, taken from `v76_cut_spec.py` (which asserts the same V38 sha256
# and re-derives the same record addresses). Re-run that file to reproduce the design evidence:
#   · add-only vs stock at all 182,027,001 (speed, rate) points, 0 violations
#   · dose 137 at the measured burst rate r=99, plateau REMOVED (E_Y1 300 < E_Y2 539)
#   · k = 1.3866 vs V75-flown 1.5798 -- a 12.4% REDUCTION on the build that faulted
#   · 🛑 G3 OVERRIDE: `build_v74_tva.E_X0_MIN_SAFE = 12`, this build sets E_X0 = 0. Authorised by
#     the operator. The guard exists to stop a steep ramp starting near zero, but 12 -> 0 LOWERS
#     the slope (2.867 -> 2.521 per count), and E_Y[0] = 0 is retained so there is no torque at
#     zero rate and no Coulomb relay. The guard's rationale points opposite to its effect here.
# ---------------------------------------------------------------------------------------------------
TABLE_SOURCE = "TableDesign-validated (v76_cut_spec.py)"
NEW_C26 = ([2240, 3840, 5120, 8960], [566, 566, 566, 908])
NEW_E26 = ([0, 119, 2500, 4000], [0, 300, 539, 927])
E_X0_MIN_SAFE_OVERRIDDEN = (12, 0)      # (the V74 guard, what this build sets) -- FLAGGED, not silent

# The independent statement of the write list, from TableDesign's spec. Asserted against what this
# builder actually emits, so a derivation bug in either one fails the build.
EXPECTED_WRITES = {
    0xD77DA: (0, 566, "FactorC Y[0]"), 0xD77DC: (234, 566, "FactorC Y[1]"),
    0xD77DE: (429, 566, "FactorC Y[2]"),
    0xD780E: (60, 0, "FactorE X[0]"), 0xD7810: (400, 119, "FactorE X[1]"),
    0xD7818: (140, 300, "FactorE Y[1]"),
}

# =====================================================================================================
# GROUP 2 -- THE PROBE CAVE
# =====================================================================================================
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V72_CAVE_EXTENT = 68         # 🛑 THE PROVEN EXTENT. NEVER GROW IT.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK        # 0x55C0E, `movea -0x1518,gp,r6`
HOOK_RETURN = HOOK_ADDR + 4                                  # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")                     # `mov 0x8,r7` -- proves r7 is DEAD

PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- live STEER_SENSOR_STATUS, PRESERVED
PAYLOAD_SHIFT = 3

# The probed cells and their firmware censuses on the V38 base -- (reads, writes), by raw LE byte
# scan covering BOTH gp encodings. 🛑 The cave must READ each and write NONE.
STATE_DISP = -0x67FA        # the assist-chain state selector. BYTE. lockstep-shadowed -> read only.
MODEIDX_DISP = +0x63FD      # the mode index. BYTE, ODD displacement -> ld.bu op 0x3D, not 0x3C.
BC6_DISP = -0x6BC6          # halfword, SIGNED
BC8_DISP = -0x6BC8          # halfword, SIGNED
B26_DISP = -0x6B26          # halfword, SIGNED -- THE MONITORED SIGNAL (see the interlock above)
CELL_CENSUS = {STATE_DISP: (128, 33), MODEIDX_DISP: (22, 5), BC6_DISP: (1, 1),
               BC8_DISP: (1, 1), B26_DISP: (4, 1), -PAYLOAD_BYTE4_DISP: (3, 3)}
# The cells the cave actually READS -- exactly one load each, no stores. 🛑 `gp-0x6b26` is censused
# but NOT read: its thermometer (bits 6/7) is HELD and did not fit in 68 bytes. It stays in the
# census so the FIRMWARE's own 4r/1w on the fault-monitor cell is still asserted untouched.
CAVE_READS = (STATE_DISP, MODEIDX_DISP, BC6_DISP, BC8_DISP)

# ---- instruction pins. Every halfword emitted reproduces a REAL instance in the V38 image, address
# ---- and bytes. Verified here by a raw byte read, not by a cached Ghidra database.
PIN_LDBU_STATE_R6 = (0x18C7C, bytes.fromhex("84370798"))   # `ld.bu -0x67fa[gp],r6`
PIN_LDBU_MODEIDX_R6 = (0x346B4, bytes.fromhex("a437fd63"))  # `ld.bu 0x63fd[gp],r6`  (op 0x3D, ODD)
PIN_LDH_BC6_R15 = (0x3435C, bytes.fromhex("247f3a94"))     # `ld.h -0x6bc6[gp],r15`
PIN_LDH_BC8_R11 = (0x34358, bytes.fromhex("245f3894"))     # `ld.h -0x6bc8[gp],r11`
PIN_LDH_B26_R6 = (0x3815C, bytes.fromhex("2437da94"))      # `ld.h -0x6b26[gp],r6`
PIN_LDH_B26_R11 = (0x3AC98, bytes.fromhex("245fda94"))     # `ld.h -0x6b26[gp],r11`
PIN_MOVI5_0_R7 = (0x14BD4, bytes.fromhex("003a"))          # `mov 0x0,r7`
PIN_MOVI5_1_R7 = (0x14D40, bytes.fromhex("013a"))          # `mov 0x1,r7`
PIN_CMP_5_R6 = (0x16FA4, bytes.fromhex("6532"))            # `cmp 0x5,r6`
PIN_CMP_10_R15 = (0x22FFC, bytes.fromhex("6a7a"))          # `cmp 0xa,r15`
PIN_ANDI_HW1_R6_R6 = (0x1FEA0, bytes.fromhex("c636"))      # hw1 donor: `andi imm,r6,r6`
# hw2 donor: the immediate half of the real `andi 0x2,r22,r15` @0x164F4 (`d67e0200`), so hw2 is +2.
PIN_ANDI_IMM2_HW2 = (0x164F6, bytes.fromhex("0200"))
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))       # `andi 0x7,r6,r6`
PIN_ADD_2_R7 = (0x27EF0, bytes.fromhex("423a"))            # `add 0x2,r7`
PIN_ADD_4_R7 = (0x2688E, bytes.fromhex("443a"))            # `add 0x4,r7`
PIN_ADD_5_R15 = (0x43494, bytes.fromhex("457a"))           # `add 0x5,r15`
PIN_SUB_R11_R15 = (0x34364, bytes.fromhex("ab79"))         # ★ `sub r11,r15` -- see LOCKSTEP_TRIPLE
PIN_BNE_4 = (0x1A8A6, bytes.fromhex("aa05"))               # `bne +4`
PIN_BE_4 = (0x1AFD0, bytes.fromhex("a205"))                # `be +4`
PIN_BNH_4 = (0x2784E, bytes.fromhex("a305"))               # `bnh +4` (unsigned <=; cond 0x3)
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))            # `or r7,r6`
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))             # `shl 0x3,r7`
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))      # `ld.bu -0x1514[gp],r6`
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))       # `st.b r6,-0x1514[gp]` -- THE ONLY STORE
PIN_MOVEA_HOOK = (0x55C0E, bytes.fromhex("2436e8ea"))      # the displaced `movea -0x1518,gp,r6`
# ⚠ NOT V74's 0x1E4. The plain image carries ONLY the flashable span and is all-0xFF below
# 0x13000, so a bootloader-region pin cannot be checked against the artifact we actually build.
# 0x14AAA is in-span, identical in STOCK and V38, and Ghidra renders it `jmp lp` on a real
# instruction boundary (between a 6-byte `st.w r6,-0x6e20,gp` and a `prepare`).
PIN_JMP_LP = (0x14AAA, bytes.fromhex("7f00"))              # `jmp [lp]`

ALL_PINS = {n: v for n, v in sorted(globals().items()) if n.startswith("PIN_")}

# 🛑 The ONLY registers the cave may write. r10 is LIVE across the hook.
ALLOWED_WRITE_REGS = {R6, R7, R11, R15}
FORBIDDEN_WRITE_REGS = {10}

COND_BE, COND_BNE = FF.COND_BE, FF.COND_BNE

# =====================================================================================================
# 🛑🛑 REGISTER LIVENESS AT THE HOOK -- the bricking-class question, resolved by DISASSEMBLY
# =====================================================================================================
# The hook 0x55C0E sits in FUN_00055a98 (0x55A98..0x55C41), inside the argument setup for
# `FUN_00057b24(gp-0x1518, 8, 0x14a)` -- the CAN-0x14A checksum call.
#
# [EVIDENCE] r11 and r15 are DEAD at 0x55C0E. Three independent legs:
#   1. LAST READS ARE BEFORE THE HOOK. r15's last read is 0x55B82 `cmp r15,r10`; r11's is
#      0x55BBE `andi 0x3,r11,r9`. Exhaustive over the tail -- every instruction from 0x55C0E to
#      `jmp [lp]` @0x55C40 was enumerated and NONE reads r11 or r15.
#   2. THE ONLY CALL AFTER THE HOOK DOES NOT TAKE THEM. FUN_00057b24 writes before reading:
#      0x57B28 `mov r8,r15`, 0x57B58 `sld.bu 0x0[ep],r11`. Its inputs are r6/r7/r8 only.
#   3. NO CALLER CAN DEPEND ON THEM. FUN_00055a98's prologue saves r7/r28/lp/r8/r6 and its
#      epilogue restores ONLY lp and r28 -- it clobbers r11/r15 freely.
#   r6 is written by the displaced `movea` itself; r7 by `mov 0x8,r7` @0x55C12. Both dead.
#
# ⚠ [EVIDENCE] r10 is the ABI RETURN register, not a value carried across the hook: FUN_00057b24
#   ends `andi 0xf,r12,r10 ; jmp [lp]`, and 0x55C20 `andi 0xf,r10,r8` consumes THAT return.
#   An earlier analysis called r10 "live across the hook"; that is not what the code does. It makes
#   NO difference to this build -- the cave writes no r10 and that is asserted -- but the record
#   should be right.
HOOK_FN = (0x55A98, 0x55C41)
DEAD_AT_HOOK = {R6: "written by the displaced movea @0x55C0E",
                R7: "written by `mov 0x8,r7` @0x55C12",
                R11: "last read 0x55BBE; FUN_00057b24 writes it @0x57B58 before reading",
                R15: "last read 0x55B82; FUN_00057b24 writes it @0x57B28 before reading"}

# ★ The firmware computes bit5's quantity ITSELF, with these very registers, at FUN_00034350's
# entry -- our three halfwords are BYTE-IDENTICAL to the firmware's own:
#     0x34358  ld.h -0x6bc8,gp,r11    245f3894
#     0x3435C  ld.h -0x6bc6,gp,r15    247f3a94
#     0x34364  sub  r11,r15           ab79
# It then compares that difference against gp-0x6bc4 and gp-0x6bca -- the "entry lockstep quad"
# corridor. bit5 reports whether the corridor's own input has moved more than +/-5.
LOCKSTEP_TRIPLE = (0x34358, 0x3435C, 0x34364)

# ---------------------------------------------------------------------------------------------------
# ProbeDesign's APPROVED core: bits 3/4/5. Bits 6/7 (the |gp-0x6b26| thermometer) are HELD.
# 🛑 [EVIDENCE] The thermometer does not fit and was never a live option. Budget, in bytes:
#     fixed overhead (accumulator init, shl 0x3, payload read/mask/or/store, replayed movea,
#     jmp [lp]) = 24  =>  44 available.
#     bit3 10 + bit4 12 + bit5 18 = 40  =>  4 spare.
#     A |gp-0x6b26| thermometer needs a materialised absolute value (mov/sar/xor/sub = 8 B) plus a
#     4-byte `movea` per threshold, because 256 and 448 are outside imm5 range: ~30 B against 4.
#   Growing the cave to fit is NOT an option -- V24, V27 and V48B bricked the ECU that way.
# ⇒ bits 6 and 7 are ZERO BY CONSTRUCTION in this build. The decoder must not read them as a
#   measurement. This coincides with ProbeDesign holding them pending the SlewFix work.
# ---------------------------------------------------------------------------------------------------
PROBE_SOURCE = "ProbeDesign-core-3 (bits 6/7 held; see the budget note)"
BIT_STATE5 = 3       # gp-0x67fa == 5              ★ THE POSITIVE CONTROL
BIT_MODEIDX = 4      # gp+0x63fd & 0x2             the mode index -- closes the mode-lag question
BIT_BCDIFF = 5       # |gp-0x6bc6 - gp-0x6bc8| > 5 the Surface-A corridor, pre-registered null
BITS_HELD = (6, 7)   # the |gp-0x6b26| thermometer -- HELD, emitted as constant 0
STATE_EQ = 5
MODEIDX_MASK = 0x2
BCDIFF_THRESH = 5
PROBE_MASK = 0x38    # bits 5:3 only -- bits 7:6 are constant 0, bits 2:0 the live status
PAYLOAD_SHIFT = 3
BR_SKIP = 4          # every skip jumps the 2-byte setter that follows it


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


# =====================================================================================================
# Record helpers -- every address is DEREFERENCED, never hard-coded into a write
# =====================================================================================================
def rec_addr(buf, ptrs, mode):
    return u32(buf, ptrs + 4 * mode)


def read_rec(buf, ptrs, mode):
    """-> (addr, count, X, Y). Reads the count from the record itself; never assumes 4."""
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


def assert_no_aliasing(buf):
    """🛑 A record shared by two modes would make a mode-26 edit leak into another mode."""
    for name, ptrs in (("FactorC", FACTOR_C_PTRS), ("FactorE", FACTOR_E_PTRS)):
        owners = {}
        for m in range(N_MODES):
            owners.setdefault(rec_addr(buf, ptrs, m), []).append(m)
        live = rec_addr(buf, ptrs, LIVE_MODE)
        assert owners[live] == [LIVE_MODE], \
            f"{name} mode-{LIVE_MODE} record 0x{live:05X} is ALSO used by modes " \
            f"{[m for m in owners[live] if m != LIVE_MODE]} -- the edit would leak"
        manual = rec_addr(buf, ptrs, MANUAL_MODE)
        assert manual != live, f"{name}: mode {MANUAL_MODE} and {LIVE_MODE} share a record"


def assert_record_geometry(buf, label):
    """The dereferenced addresses must match the independently-stated expectation."""
    for (kind, mode), want in EXPECT_ADDR.items():
        ptrs = FACTOR_C_PTRS if kind == "C" else FACTOR_E_PTRS
        got = rec_addr(buf, ptrs, mode)
        assert got == want, \
            f"{label}: Factor{kind} mode {mode} dereferences to 0x{got:05X}, expected 0x{want:05X}"
        n = u16(buf, got)
        assert n == 4 and rec_len(n) == REC_STRIDE == 0x14, \
            f"{label}: Factor{kind} m{mode} count={n}, rec_len=0x{rec_len(n):X} (expected 4 / 0x14)"


# =====================================================================================================
# 🛑🛑 THE INTERLOCK GUARD -- the single most important assertion in this file
# =====================================================================================================
def assert_fault_interlock(buf, label):
    """`FUN_00036d74` faults to DTC 0x1d when |gp-0x6b26|/1024 > cal(0xC4004).

    The clamp on gp-0x6b26 lives at 0xC407E and MUST stay strictly below the trip point. V73 raised
    it to 850 against a 512-count ceiling; V74 and V75 both hard-faulted with a total loss of power
    steering, one of them in MANUAL. Do not relax any of these three checks.
    """
    clamp = u16(buf, FAULT_CLAMP_ADDR)
    assert clamp <= FAULT_CLAMP_MAX, (
        f"🛑🛑 {label}: FRICTION CLAMP 0x{FAULT_CLAMP_ADDR:05X} = {clamp} > {FAULT_CLAMP_MAX}. "
        f"FUN_00036d74 faults to DTC 0x1d above {FAULT_TRIP_COUNTS} counts. THIS IS THE V74/V75 "
        f"HARD-FAULT MECHANISM -- total loss of power steering. STOP.")
    assert clamp < FAULT_TRIP_COUNTS, (
        f"🛑🛑 {label}: clamp {clamp} is not strictly below the {FAULT_TRIP_COUNTS}-count trip "
        f"point -- the interlock margin is gone.")

    raw = bytes(buf[FAULT_THRESH_ADDR:FAULT_THRESH_ADDR + 4])
    thresh = struct.unpack("<f", raw)[0]
    assert raw == FAULT_THRESH_BYTES and thresh == FAULT_THRESH_VALUE, (
        f"🛑🛑 {label}: 0x{FAULT_THRESH_ADDR:05X} reads {thresh!r} ({raw.hex()}), expected "
        f"{FAULT_THRESH_VALUE} ({FAULT_THRESH_BYTES.hex()}). The trip point moved -- the {clamp} "
        f"clamp is no longer provably safe. STOP.")
    assert int(thresh * FAULT_SCALE) == FAULT_TRIP_COUNTS, "the trip-point arithmetic drifted"

    off = rec_addr(buf, FRICTION_PTR_ARRAY, LIVE_MODE)
    assert off == FRICTION_M26_EXPECT, \
        f"{label}: friction m{LIVE_MODE} dereferences to 0x{off:05X}, expected " \
        f"0x{FRICTION_M26_EXPECT:05X}"
    n = u16(buf, off)
    X = [s16(buf, off + 2 + 2 * i) for i in range(n)]
    Y = [s16(buf, off + 2 + 2 * n + 2 * i) for i in range(n)]
    assert (X, Y) == FRICTION_M26_STOCK_XY, (
        f"🛑🛑 {label}: friction m{LIVE_MODE} @0x{off:05X} is X={X} Y={Y}, not stock "
        f"{FRICTION_M26_STOCK_XY}. V74's x1.5 friction is what drove gp-0x6b26 into the ceiling. "
        f"THIS BUILD MUST NOT CARRY IT. STOP.")
    return clamp, thresh, off


def assert_not_carried(buf, label):
    """Every V72/V73/V74 lever this build deliberately drops, asserted ABSENT by value."""
    for addr, (want, why) in NOT_CARRIED.items():
        got = u16(buf, addr)
        assert got == want, f"{label}: 0x{addr:05X} = {got}, expected {want} -- {why}"


def assert_manual_mode_stock(buf, base, label):
    """🛑 Mode 24 is MANUAL steering. It must be byte-identical to the base, everywhere."""
    for kind, ptrs in (("C", FACTOR_C_PTRS), ("E", FACTOR_E_PTRS)):
        off = rec_addr(buf, ptrs, MANUAL_MODE)
        assert off == EXPECT_ADDR[(kind, MANUAL_MODE)]
        got, want = bytes(buf[off:off + REC_STRIDE]), bytes(base[off:off + REC_STRIDE])
        assert got == want, (
            f"🛑 {label}: Factor{kind} mode {MANUAL_MODE} @0x{off:05X} CHANGED "
            f"({want.hex()} -> {got.hex()}) -- manual steering must stay byte-stock")
    off = rec_addr(buf, FRICTION_PTR_ARRAY, MANUAL_MODE)
    assert bytes(buf[off:off + 14]) == bytes(base[off:off + 14]), \
        f"🛑 {label}: friction mode {MANUAL_MODE} @0x{off:05X} changed"


# =====================================================================================================
# The gp-cell census -- a raw LE byte scan, the required second method
# =====================================================================================================
_OPS = {0x38: "ld.b", 0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h",
        0x3C: "ld.bu", 0x3D: "ld.bu", 0x3F: "ld.hu/ld.w"}


def cell_census(buf, disp, cave_span=range(0, 0)):
    """(firmware reads, firmware writes, cave hits) for a gp displacement, by raw byte scan.

    Covers BOTH gp encodings' 4-byte form and takes ld.bu's displacement bit 0 from the OPCODE
    field, which a naive disp16 scan gets wrong for odd displacements such as gp+0x63fd.
    """
    fw_r, fw_w, cave = [], [], []
    for a in range(START, END - 4, 2):
        hw = u16(buf, a)
        op6 = (hw >> 5) & 0x3F
        if op6 not in _OPS or (hw & 0x1F) != GP:
            continue
        hw2 = u16(buf, a + 2)
        d = hw2 - 0x10000 if hw2 & 0x8000 else hw2
        if op6 in (0x3C, 0x3D):
            eff = (d & ~1) | (op6 & 1)
        elif op6 == 0x3F:
            eff = d & ~1
        else:
            eff = d
        if eff != disp:
            continue
        entry = (a, _OPS[op6], bytes(buf[a:a + 4]))
        if a in cave_span:
            cave.append(entry)
        elif _OPS[op6].startswith("ld"):
            fw_r.append(entry)
        else:
            fw_w.append(entry)
    return fw_r, fw_w, cave


def assert_cell_censuses(buf, cave_span, expect_cave, label):
    """🛑 The cave must READ each probed cell and WRITE none. gp-0x67fa is lockstep-shadowed."""
    for disp, (want_r, want_w) in CELL_CENSUS.items():
        r, w, cave = cell_census(buf, disp, cave_span)
        assert len(r) == want_r and len(w) == want_w, (
            f"{label}: gp{disp:+#x} census is {len(r)}r/{len(w)}w, expected {want_r}r/{want_w}w "
            f"-- the firmware's own accesses must be untouched")
        if expect_cave and disp in CAVE_READS:
            assert len(cave) == 1 and cave[0][1].startswith("ld"), (
                f"{label}: the cave makes {len(cave)} access(es) to gp{disp:+#x}, expected exactly "
                f"one LOAD -- a WRITE to any of these escalates (gp-0x67fa is lockstep-checked)")
        elif expect_cave and disp == B26_DISP:
            assert not cave, (
                f"{label}: the cave touches gp-0x6b26 -- bits 6/7 are HELD in this build, so the "
                f"fault-monitor cell must be left entirely alone")
        for _a, mnem, _raw in cave:
            assert mnem.startswith("ld") or disp == -PAYLOAD_BYTE4_DISP, \
                f"{label}: the cave WRITES gp{disp:+#x} -- forbidden"


def assert_pins(buf, label, skip=()):
    """Every pin must still read exactly as recorded, in THIS image.

    ⚠ `PIN_MOVEA_HOOK` is the ONE pin whose site this build overwrites (0x55C0E becomes the
    `jarl`). On the built image it is skipped here and checked instead by its two real successors:
    the hook is the jarl, and the displaced `movea` is replayed inside the cave.
    """
    n = 0
    for name, (addr, want) in ALL_PINS.items():
        if name in skip:
            continue
        got = bytes(buf[addr:addr + len(want)])
        assert got == want, f"{label}: {name} @0x{addr:05X} is {got.hex()}, expected {want.hex()}"
        n += 1
    return n


# =====================================================================================================
# CRC
# =====================================================================================================
def owning_block(buf, address):
    inside = [(s, e) for s, e in FF.crc_block_map(buf) if s <= address < e]
    assert len(inside) == 1, f"0x{address:05X} lies in {len(inside)} CRC blocks ({inside})"
    return inside[0]


def refresh_crcs(buf, touched_addrs):
    """Recompute the trailer of every block that owns a touched address. Returns {trailer: (old,new)}."""
    blocks = FF.crc_block_map(buf)
    assert len(blocks) == FF.EXPECTED_BLOCKS, f"{len(blocks)} CRC blocks, expected {FF.EXPECTED_BLOCKS}"
    need = set()
    for a in touched_addrs:
        need.add(owning_block(buf, a))
    changed = {}
    for bstart, trailer in sorted(need):
        old = u32(buf, trailer)
        new = zlib.crc32(bytes(buf[bstart:trailer])) & 0xFFFFFFFF
        struct.pack_into("<I", buf, trailer, new)
        changed[trailer] = (old, new, bstart)
    return changed


def assert_crc_chain(buf, label):
    blocks = FF.crc_block_map(buf)
    assert len(blocks) == FF.EXPECTED_BLOCKS, f"{label}: {len(blocks)} blocks"
    for bstart, trailer in blocks:
        calc = zlib.crc32(bytes(buf[bstart:trailer])) & 0xFFFFFFFF
        stored = u32(buf, trailer)
        assert calc == stored, \
            f"{label}: CRC mismatch at block 0x{bstart:05X}: 0x{calc:08X} != 0x{stored:08X}"
    assert walk_all_blocks(bytes(buf)) == 0, f"{label}: walk_all_blocks FAILED"
    return len(blocks)


def changed_runs(before, after, lo=START, hi=END):
    runs, i = [], lo
    while i < hi:
        if before[i] != after[i]:
            j = i
            while j < hi and before[j] != after[j]:
                j += 1
            runs.append((i, j - i))
            i = j
        else:
            i += 1
    return runs


# =====================================================================================================
# Instruction encoders not already in the V54/V55/FF set. Each is validated in _self_check_encoders()
# against a REAL instance in this image, by address -- never against a hand-decode.
# =====================================================================================================
def _fmt1(op6, reg1, reg2):
    return struct.pack("<H", ((reg2 & 0x1F) << 11) | ((op6 & 0x3F) << 5) | (reg1 & 0x1F))


def add_imm5(imm5, reg2):
    """ADD imm5,reg2 (Format II, op 0x12) -- reg2 += sign_extend(imm5)."""
    assert -16 <= imm5 <= 15, "Format II imm5 is SIGNED"
    return _fmt1(0x12, imm5 & 0x1F, reg2)


def sub_rr(reg1, reg2):
    """SUB reg1,reg2 (Format I, op 0x0D) -- reg2 = reg2 - reg1. 🛑 NOT reg1 - reg2."""
    return _fmt1(0x0D, reg1, reg2)


COND_BNH = 0x3          # unsigned <= : CY or Z. The INVERTING twin `bh` is 0xB, asserted away.


def _self_check_encoders(buf):
    """Every encoder reproduces a REAL instance in THIS image, at a named address."""
    checks = [
        (FF.movi5(0, R7), PIN_MOVI5_0_R7, "mov 0x0,r7"),
        (FF.movi5(1, R7), PIN_MOVI5_1_R7, "mov 0x1,r7"),
        (V55.cmp_imm5(STATE_EQ, R6), PIN_CMP_5_R6, "cmp 0x5,r6"),
        (V55.cmp_imm5(2 * BCDIFF_THRESH, R15), PIN_CMP_10_R15, "cmp 0xa,r15"),
        (V54.andi(PAYLOAD_KEEP_MASK, R6, R6), PIN_ANDI_7_R6, "andi 0x7,r6,r6"),
        (add_imm5(2, R7), PIN_ADD_2_R7, "add 0x2,r7"),
        (add_imm5(4, R7), PIN_ADD_4_R7, "add 0x4,r7"),
        (add_imm5(BCDIFF_THRESH, R15), PIN_ADD_5_R15, "add 0x5,r15"),
        (sub_rr(R11, R15), PIN_SUB_R11_R15, "sub r11,r15"),
        (FF.bcond(COND_BNE, BR_SKIP), PIN_BNE_4, "bne +4"),
        (FF.bcond(COND_BE, BR_SKIP), PIN_BE_4, "be +4"),
        (FF.bcond(COND_BNH, BR_SKIP), PIN_BNH_4, "bnh +4"),
        (V54.or_rr(R7, R6), PIN_OR_R7_R6, "or r7,r6"),
        (V54.shl(PAYLOAD_SHIFT, R7), PIN_SHL3_R7, "shl 0x3,r7"),
        (V55.ldbu_any(STATE_DISP, R6), PIN_LDBU_STATE_R6, "ld.bu -0x67fa[gp],r6"),
        (V55.ldbu_any(MODEIDX_DISP, R6), PIN_LDBU_MODEIDX_R6, "ld.bu 0x63fd[gp],r6"),
        (V55.ldh(-BC6_DISP, R15), PIN_LDH_BC6_R15, "ld.h -0x6bc6[gp],r15"),
        (V55.ldh(-BC8_DISP, R11), PIN_LDH_BC8_R11, "ld.h -0x6bc8[gp],r11"),
        (V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), PIN_LDBU_BYTE4, "ld.bu -0x1514[gp],r6"),
        (FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), PIN_STB_BYTE4, "st.b r6,-0x1514[gp]"),
        (FF.JMP_LP, PIN_JMP_LP, "jmp [lp]"),
    ]
    for enc, (addr, want), text in checks:
        assert enc == want, f"encoder '{text}' emits {enc.hex()}, the pin says {want.hex()}"
        assert bytes(buf[addr:addr + len(want)]) == want, \
            f"pin for '{text}' @0x{addr:05X} does not read back"
    # `andi 0x2,r6,r6` has no exact instance: pin hw1 and hw2 to separate real donors, as V74 does.
    a2 = V54.andi(MODEIDX_MASK, R6, R6)
    assert a2[:2] == PIN_ANDI_HW1_R6_R6[1] and a2[2:] == PIN_ANDI_IMM2_HW2[1], \
        f"`andi 0x2,r6,r6` = {a2.hex()} does not match its two half-pins"
    assert bytes(buf[PIN_ANDI_HW1_R6_R6[0]:PIN_ANDI_HW1_R6_R6[0] + 2]) == PIN_ANDI_HW1_R6_R6[1]
    assert bytes(buf[PIN_ANDI_IMM2_HW2[0]:PIN_ANDI_IMM2_HW2[0] + 2]) == PIN_ANDI_IMM2_HW2[1]
    # 🛑 the inverting twins, asserted AWAY -- each of these has flipped a probe rung's meaning before
    assert FF.bcond(COND_BNE, BR_SKIP) != FF.bcond(COND_BE, BR_SKIP), "bne/be collapsed"
    assert FF.bcond(COND_BNH, BR_SKIP) != FF.bcond(0xB, BR_SKIP), "bnh/bh collapsed"
    assert sub_rr(R11, R15) != sub_rr(R15, R11), "sub operand order collapsed"
    # ★ the firmware's own three instructions, byte-identical to ours
    a11, a15, asub = LOCKSTEP_TRIPLE
    assert bytes(buf[a11:a11 + 4]) == V55.ldh(-BC8_DISP, R11)
    assert bytes(buf[a15:a15 + 4]) == V55.ldh(-BC6_DISP, R15)
    assert bytes(buf[asub:asub + 2]) == sub_rr(R11, R15)
    return len(checks) + 1


# =====================================================================================================
# THE CAVE
# =====================================================================================================
def build_cave():
    """Emit the 68-byte probe. Returns (bytes, listing) where listing = [(addr, raw, text)]."""
    body, listing, writes = bytearray(), [], []

    def emit(raw, text, wreg=None):
        listing.append((CAVE_BASE + len(body), bytes(raw), text))
        if wreg is not None:
            writes.append((CAVE_BASE + len(body), wreg))
        body.extend(raw)

    emit(FF.movi5(0, R7), "mov 0x0,r7           ; r7 = the 5-bit field accumulator", R7)

    # ---- bit3: gp-0x67fa == 5. ★ THE POSITIVE CONTROL ------------------------------------------
    emit(V55.ldbu_any(STATE_DISP, R6), "ld.bu -0x67fa[gp],r6 ; THE STATE (byte, neg disp)", R6)
    c1 = len(listing)
    emit(V55.cmp_imm5(STATE_EQ, R6), "cmp 0x5,r6           ; Z iff state == 5")
    b1 = len(listing)
    emit(FF.bcond(COND_BNE, BR_SKIP), "bne +4               ; not 5 -> skip the setter")
    emit(FF.movi5(1, R7), f"mov 0x1,r7           ; bit{BIT_STATE5} <- (state == 5)", R7)
    l1 = CAVE_BASE + len(body)   # the branch target: AFTER the setter

    # ---- bit4: gp+0x63fd & 0x2 -- the mode index ------------------------------------------------
    emit(V55.ldbu_any(MODEIDX_DISP, R6), "ld.bu 0x63fd[gp],r6  ; MODE INDEX (ODD disp, op 0x3D)", R6)
    c2 = len(listing)
    emit(V54.andi(MODEIDX_MASK, R6, R6), "andi 0x2,r6,r6       ; Z iff bit1 clear", R6)
    b2 = len(listing)
    emit(FF.bcond(COND_BE, BR_SKIP), "be +4                ; bit1 clear -> skip")
    emit(add_imm5(2, R7), f"add 0x2,r7           ; bit{BIT_MODEIDX} <- (mode & 2)", R7)
    l2 = CAVE_BASE + len(body)   # the branch target: AFTER the setter

    # ---- bit5: |gp-0x6bc6 - gp-0x6bc8| > 5 -- the Surface-A corridor ----------------------------
    # ★ the loads and the sub are BYTE-IDENTICAL to FUN_00034350's own entry (LOCKSTEP_TRIPLE).
    # ★ the range trick: |d| > 5  <=>  (unsigned)(d + 5) > 10. Saves 6 B over a materialised abs,
    #   which is what makes three rungs fit in 68 bytes at all.
    emit(V55.ldh(-BC6_DISP, R15), "ld.h -0x6bc6[gp],r15 ; corridor A (SIGNED, op 0x39)", R15)
    emit(V55.ldh(-BC8_DISP, R11), "ld.h -0x6bc8[gp],r11 ; corridor B (SIGNED, op 0x39)", R11)
    emit(sub_rr(R11, R15), "sub r11,r15          ; r15 = A - B   🛑 NOT `sub r15,r11`", R15)
    emit(add_imm5(BCDIFF_THRESH, R15), "add 0x5,r15          ; r15 = d + 5", R15)
    c3 = len(listing)
    emit(V55.cmp_imm5(2 * BCDIFF_THRESH, R15), "cmp 0xa,r15          ; UNSIGNED compare vs 10")
    b3 = len(listing)
    emit(FF.bcond(COND_BNH, BR_SKIP), "bnh +4               ; (u)(d+5) <= 10 <=> |d| <= 5 -> skip")
    emit(add_imm5(4, R7), f"add 0x4,r7           ; bit{BIT_BCDIFF} <- (|A-B| > 5)", R7)
    l3 = CAVE_BASE + len(body)   # the branch target: AFTER the setter

    # ---- pack into the CAN-330 payload byte, preserving bits 2:0 --------------------------------
    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7           ; the field -> bits 5:3", R7)
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4", R6)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6       ; keep live status bits 2:0", R6)
    emit(V54.or_rr(R7, R6), "or r7,r6             ; 🛑 NOT `or r6,r7`", R6)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]  ; ★ THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6  ; re-exec the displaced instruction", R6)
    ret_addr = CAVE_BASE + len(body)
    emit(FF.JMP_LP, f"jmp [lp]             ; -> 0x{HOOK_RETURN:05X}")

    code_len = len(body)
    pad = CAVE_EXTENT - code_len
    assert pad >= 0, f"the cave code is {code_len}B, over the PROVEN {CAVE_EXTENT}B extent"
    assert pad % 2 == 0, "the padding is not halfword-aligned"
    if pad:
        emit(bytes(pad), f"<{pad} x 0x00, AFTER `jmp [lp]` => UNREACHABLE; extent stays 68>")

    # ---- 🛑 FLAG LIVENESS: each test must be IMMEDIATELY followed by its branch -----------------
    for ci, bi, name in ((c1, b1, "bit3 cmp/bne"), (c2, b2, "bit4 andi/be"), (c3, b3, "bit5 cmp/bnh")):
        assert bi == ci + 1, \
            f"{name}: {bi - ci - 1} instruction(s) sit between the test and its branch -- the " \
            f"branch would read STALE flags, a silent and plausible-looking wrong answer"
        ca, craw, _ = listing[ci]
        ba, braw, _ = listing[bi]
        assert ca + len(craw) == ba, f"{name}: the test/branch pair is not adjacent"

    # ---- 🛑 the INVERTING twins, on the EMITTED bytes -------------------------------------------
    assert struct.unpack("<H", listing[b1][1])[0] & 0xF == COND_BNE, \
        "bit3's branch is not `bne` -- `be` would invert it: bit3 would read HIGH off state 5"
    assert struct.unpack("<H", listing[b2][1])[0] & 0xF == COND_BE, \
        "bit4's branch is not `be` -- `bne` would invert the mode-index rung"
    assert struct.unpack("<H", listing[b3][1])[0] & 0xF == COND_BNH, \
        "bit5's branch is not `bnh` -- `bh` would invert the corridor rung"

    # ---- GATE 2a: every branch lands EXACTLY on an emitted instruction boundary -----------------
    bounds = {a for a, _r, _t in listing}
    for bi, label, name in ((b1, l1, "bit3"), (b2, l2, "bit4"), (b3, l3, "bit5")):
        ba, braw, _ = listing[bi]
        assert ba + BR_SKIP == label, f"{name}: `b* +{BR_SKIP}` @0x{ba:05X} does not target 0x{label:05X}"
        assert label in bounds, f"{name}: branch target 0x{label:05X} is not an instruction boundary"
        assert label == listing[bi + 2][0], f"{name}: the branch does not skip exactly the setter"
        assert len(listing[bi + 1][1]) == 2, f"{name}: the skipped setter is not 2 bytes"
        assert ba < label <= ret_addr, f"{name}: the branch is not a forward jump before the return"
    branches = [i for i, (_a, r, _t) in enumerate(listing)
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    assert branches == [b1, b2, b3], f"the cave has branches at {branches}, expected {[b1, b2, b3]}"

    # ---- SINGLE EXIT: no jr/jarl anywhere ------------------------------------------------------
    for _a, raw, text in listing:
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert raw == FF.JMP_LP or ((hw >> 5) & 0x3F) not in (0x1E, 0x1B), \
            f"'{text}' is a jr/jarl -- the cave must have a SINGLE exit"

    # ---- GATE 1 as a property of the EMITTED CODE: EXACTLY ONE store ---------------------------
    stores = [i for i, (_a, raw, _t) in enumerate(listing)
              if len(raw) == 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert len(stores) == 1, f"the cave must contain EXACTLY ONE store, found {stores}"
    assert listing[stores[0]][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the CAN-330 payload byte"
    for idx, (_a, raw, text) in enumerate(listing):
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- 🛑🛑 REGISTER DISCIPLINE, read off the EMITTED ENCODINGS ------------------------------
    # Every instruction that writes a GPR must write r6/r7/r11/r15, and NEVER r10.
    for addr, raw, text in listing:
        # the trailing pad is all-zero and sits AFTER `jmp [lp]` -- unreachable, not an instruction
        if len(raw) > 4 or raw == FF.JMP_LP or raw == HOOK_STOCK or raw == bytes(len(raw)):
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        op6 = (hw >> 5) & 0x3F
        if (hw >> 7) & 0xF == 0xB:                       # Bcond writes no GPR
            continue
        if op6 in (0x13, 0x0F):                          # cmp -- flags only
            continue
        if op6 in (0x3A, 0x3B):                          # a store's reg2 is the SOURCE
            continue
        dest = hw >> 11
        assert dest in ALLOWED_WRITE_REGS, \
            f"'{text}' @0x{addr:05X} writes r{dest} -- only r6/r7/r11/r15 are proven dead here"
        assert dest not in FORBIDDEN_WRITE_REGS, f"'{text}' writes r{dest} -- FORBIDDEN"
    dests = {(hw := struct.unpack_from("<H", r, 0)[0]) >> 11
             for _a, r, _t in listing
             if len(r) in (2, 4) and r not in (FF.JMP_LP, HOOK_STOCK) and r != bytes(len(r))
             and (hw >> 7) & 0xF != 0xB and ((hw >> 5) & 0x3F) not in (0x13, 0x0F, 0x3A, 0x3B)}
    assert dests <= ALLOWED_WRITE_REGS, f"the cave writes {sorted(dests)}"
    assert 10 not in dests, "🛑 the cave writes r10"

    # ---- geometry ------------------------------------------------------------------------------
    assert code_len == 2 + 4 + 2 + 2 + 2 + 4 + 4 + 2 + 2 + 4 + 4 + 2 + 2 + 2 + 2 + 2 \
        + 2 + 4 + 4 + 2 + 4 + 4 + 2 == 64, f"the cave code is {code_len}B, the budget says 64"
    assert bytes(body[code_len:]) == bytes(pad), "the padding is not all zero"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == CAVE_EXTENT == 68, \
        f"cave {len(body)}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def wire_model(state, mode_idx, bc6, bc8, status_bits=0x7):
    """A Python mirror of EXACTLY what the cave computes -- instruction for instruction."""
    r7 = 0
    if (state & 0xFF) == STATE_EQ:                       # ld.bu is UNSIGNED; cmp is on the byte
        r7 = 1
    if (mode_idx & 0xFF) & MODEIDX_MASK:
        r7 += 2
    d = bc6 - bc8                                        # both ld.h -> SIGNED
    if ((d + BCDIFF_THRESH) & 0xFFFFFFFF) > 2 * BCDIFF_THRESH:   # UNSIGNED compare
        r7 += 4
    return ((r7 << PAYLOAD_SHIFT) | (status_bits & PAYLOAD_KEEP_MASK)) & 0xFF


def _check_wire_model():
    """The mirror's truth table, including the sign cases the range trick exists to handle."""
    assert wire_model(5, 0, 0, 0, 0) == 0x08
    assert wire_model(4, 0, 0, 0, 0) == 0x00
    assert wire_model(5, 0x02, 0, 0, 0) == 0x18
    assert wire_model(5, 0xFD, 0, 0, 0) == 0x08          # bit1 clear in 0xFD
    for d in (6, 7, 100, 32767):
        assert wire_model(0, 0, d, 0, 0) == 0x20, f"+{d} should set bit5"
        assert wire_model(0, 0, -d, 0, 0) == 0x20, f"-{d} should set bit5"   # the SIGNED case
    for d in (-5, -1, 0, 1, 5):
        assert wire_model(0, 0, d, 0, 0) == 0x00, f"{d} must NOT set bit5"
    assert wire_model(5, 0x02, 0, -6, 0b101) == 0x3D     # all three + preserved status
    assert wire_model(0, 0, 0, 0, 0xFF) == 0x07, "bits 2:0 must be preserved and masked to 3"


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, from raw bytes, in Python.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. This is the independent second method for the cave's contents.
    """
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        imm5 = hw & 0x1F
        if hw == 0x0000:
            n, m = 2, "nop"
        elif (hw >> 7) & 0xF == 0xB:
            n = 2
            m = {0x2: "be", 0x3: "bnh", 0xA: "bne", 0xB: "bh", 0x6: "blt", 0xE: "bge"}.get(
                hw & 0xF, f"b?{hw & 0xF:x}")
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            m = f"{m} {d:+d}"
        elif op6 in (0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F, 0x31, 0x36):
            n = 4
            hw2 = struct.unpack_from("<H", raw, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            m = {0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h", 0x3C: "ld.bu", 0x3D: "ld.bu",
                 0x3F: "ld.hu" if hw2 & 1 else "ld.w", 0x31: "movea", 0x36: "andi"}[op6]
            if op6 in (0x31, 0x36):
                m = f"{m} 0x{hw2:04x},r{reg1},r{reg2}"
            else:
                eff = ((disp & ~1) | (op6 & 1)) if op6 in (0x3C, 0x3D) else disp
                m = (f"{m} r{reg2},{eff}[r{reg1}]" if op6 in (0x3A, 0x3B)
                     else f"{m} {eff}[r{reg1}],r{reg2}")
        elif op6 == 0x10:
            n, m = 2, f"mov 0x{imm5:x},r{reg2}"
        elif op6 == 0x12:
            n, m = 2, f"add 0x{imm5:x},r{reg2}"
        elif op6 == 0x13:
            n, m = 2, f"cmp 0x{imm5:x},r{reg2}"
        elif op6 == 0x16:
            n, m = 2, f"shl 0x{imm5:x},r{reg2}"
        elif op6 == 0x0D:
            n, m = 2, f"sub r{reg1},r{reg2}"
        elif op6 == 0x08:
            n, m = 2, f"or r{reg1},r{reg2}"
        elif hw == 0x007F:
            n, m = 2, "jmp [lp]"
        else:
            n, m = 2, f"?? {hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


def main():
    print("=" * 102)
    print("  V76 -- RE-CUT ON THE V38 BASE. Supersedes V76 / V77 / V77B.")
    print("=" * 102)
    assert TABLE_SOURCE.startswith("TableDesign-validated"), TABLE_SOURCE
    assert PROBE_SOURCE.startswith("ProbeDesign-core-3"), PROBE_SOURCE
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it"

    base = bytes(SRC_BIN.read_bytes())
    assert len(base) == 0x100000, f"the base must be 1 MiB, got 0x{len(base):X}"
    assert hashlib.sha256(base).hexdigest() == SRC_SHA256, "the base is NOT the V38 plain image"
    stock = bytes(STOCK_BIN.read_bytes())
    print(f"\n  base  {SRC_BIN.name}\n        sha256 {SRC_SHA256}  VERIFIED")

    # ---- everything checkable BEFORE a byte is written -----------------------------------------
    n_enc = _self_check_encoders(base)
    _check_wire_model()
    n_pins = assert_pins(base, "V38 base")
    assert_no_aliasing(base)
    assert_record_geometry(base, "V38 base")
    clamp, thresh, fric = assert_fault_interlock(base, "V38 base")
    assert_not_carried(base, "V38 base")
    assert_cell_censuses(base, range(0, 0), False, "V38 base")
    assert bytes(base[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "the hook site is not the stock movea"
    assert bytes(base[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "0x55C12 is not `mov 0x8,r7` -- the proof that r7 is dead across the hook"
    assert bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == b"\xff" * CAVE_EXTENT, \
        "the cave target is not all 0xFF -- refusing to overwrite"
    assert bytes(base[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the cave tail is not 0xFF"
    assert_crc_chain(base, "V38 base")
    print(f"  base OK: {n_enc} encoders self-checked, {n_pins} pins, record geometry, "
          f"no aliasing, censuses, CRC chain 50/50")
    print(f"  🛑 INTERLOCK on the base: 0xC407E = {clamp} (<= {FAULT_CLAMP_MAX}), "
          f"0xC4004 = {thresh} => trip at {FAULT_TRIP_COUNTS} counts, friction m26 @0x{fric:05X} STOCK")

    code = bytearray(base)
    touched = []

    # ---- GROUP 1 -- the mode-26 damper surface -------------------------------------------------
    print("\n" + "-" * 102)
    print("  GROUP 1 -- mode-26 FactorC / FactorE   (mode 24 BYTE-STOCK)")
    print("-" * 102)
    for kind, ptrs, (nx, ny) in (("C", FACTOR_C_PTRS, NEW_C26), ("E", FACTOR_E_PTRS, NEW_E26)):
        off, n, ox, oy = read_rec(code, ptrs, LIVE_MODE)
        expect = BASE_C26 if kind == "C" else BASE_E26
        assert (ox, oy) == expect, f"Factor{kind} m26 base is X={ox} Y={oy}, expected {expect}"
        slack_before = bytes(code[off + REC_DATA_LEN:off + REC_STRIDE])
        woff, wlen = write_rec(code, ptrs, LIVE_MODE, nx, ny)
        assert wlen == REC_DATA_LEN, f"wrote {wlen}B, expected {REC_DATA_LEN}"
        assert bytes(code[off + REC_DATA_LEN:off + REC_STRIDE]) == slack_before, \
            f"🛑 Factor{kind} m26: the 2 slack bytes changed -- this is the V73 spill"
        touched.extend(range(off, off + REC_DATA_LEN))
        print(f"    Factor{kind} m26 @0x{woff:05X}  X {ox} -> {nx}\n"
              f"    {'':>18s}  Y {oy} -> {ny}")

    runs1 = changed_runs(base, code)
    got_writes = {}
    for a, ln in runs1:
        for w in range(a, a + ln, 2):
            got_writes[w] = (u16(base, w), u16(code, w))
    assert set(got_writes) == set(EXPECTED_WRITES), \
        f"the write set differs from TableDesign's spec: {sorted(map(hex, set(got_writes) ^ set(EXPECTED_WRITES)))}"
    for a, (old, new, lbl) in EXPECTED_WRITES.items():
        assert got_writes[a] == (old, new), f"0x{a:05X} ({lbl}): got {got_writes[a]}, spec says {(old, new)}"
        assert u16(stock, a) == old, f"0x{a:05X}: the base value is not the STOCK value"
    print(f"    {len(EXPECTED_WRITES)} halfword writes, {2 * len(EXPECTED_WRITES)} bytes, "
          f"all matching v76_cut_spec.py and all old-values == STOCK")
    assert_manual_mode_stock(code, base, "after group 1")
    assert_fault_interlock(code, "after group 1")

    # ---- GROUP 2 -- the probe cave --------------------------------------------------------------
    print("\n" + "-" * 102)
    print(f"  GROUP 2 -- the {CAVE_EXTENT}-byte probe cave @0x{CAVE_BASE:05X}, hook 0x{HOOK_ADDR:05X}")
    print("-" * 102)
    cave, listing = build_cave()
    for addr, raw, text in listing:
        print(f"    0x{addr:05X}  {raw.hex():<8s}  {text}")
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave
    touched.extend(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))

    # the hook: `movea -0x1518,gp,r6` -> `jarl CAVE_BASE,lp`, in place, 4 bytes for 4 bytes
    hook_patch = FF.jarl_lp(CAVE_BASE, HOOK_ADDR)
    assert len(hook_patch) == 4 and len(HOOK_STOCK) == 4, "the hook patch must be 4-for-4 bytes"
    # 🛑 the cave returns via `jmp [lp]`, so the hook MUST link lp -- `jr` would never come back.
    assert hook_patch[:2] != FF.jr(CAVE_BASE, HOOK_ADDR)[:2], \
        "the hook patch is a `jr`, not a `jarl` -- the cave would never return"
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_patch
    touched.extend(range(HOOK_ADDR, HOOK_ADDR + 4))
    print(f"\n    hook  0x{HOOK_ADDR:05X}  {HOOK_STOCK.hex()} -> {hook_patch.hex()}  "
          f"`jarl 0x{CAVE_BASE:05X},lp`, returns to 0x{HOOK_RETURN:05X}")

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_cell_censuses(code, cave_span, True, "after group 2")
    assert_fault_interlock(code, "after group 2")
    assert_not_carried(code, "after group 2")
    assert_manual_mode_stock(code, base, "after group 2")

    # ---- CRC ------------------------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  CRC")
    print("-" * 102)
    changed = refresh_crcs(code, touched)
    for trailer, (old, new, bstart) in sorted(changed.items()):
        touched.extend(range(trailer, trailer + 4))
        print(f"    block [0x{bstart:05X}, 0x{trailer:05X})  trailer 0x{old:08X} -> 0x{new:08X}")
    n_blocks = assert_crc_chain(code, "V76")
    print(f"    {len(changed)} trailer(s) rewritten; full chain re-verified: {n_blocks}/50 blocks PASS")

    # ---- the full attributed diff ---------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  FULL BYTE DIFF  V38 -> V76")
    print("-" * 102)
    groups = {}
    for a, ln in changed_runs(base, code):
        if any(a >= r and a + ln <= r + REC_STRIDE for r in
               (rec_addr(code, FACTOR_C_PTRS, LIVE_MODE), rec_addr(code, FACTOR_E_PTRS, LIVE_MODE))):
            g = "1 damper surface m26"
        elif CAVE_BASE <= a < CAVE_BASE + CAVE_EXTENT:
            g = "2 probe cave"
        elif HOOK_ADDR <= a < HOOK_ADDR + 4:
            g = "2 probe hook"
        elif any(t <= a < t + 4 for t in changed):
            g = "3 CRC trailer"
        else:
            g = "UNATTRIBUTED"
        groups.setdefault(g, []).append((a, ln))
    total = 0
    for g in sorted(groups):
        n = sum(ln for _a, ln in groups[g])
        total += n
        print(f"    {g:22s} {len(groups[g]):3d} run(s) {n:4d} byte(s)   "
              f"{', '.join(f'0x{a:05X}+{ln}' for a, ln in groups[g][:4])}"
              f"{' ...' if len(groups[g]) > 4 else ''}")
    assert "UNATTRIBUTED" not in groups, f"UNATTRIBUTED bytes: {groups.get('UNATTRIBUTED')}"
    print(f"    TOTAL {sum(len(v) for v in groups.values())} runs, {total} bytes, ALL ATTRIBUTED")

    # ---- write + .rwd ---------------------------------------------------------------------------
    assert BIN_OUT != FORBIDDEN_OVERWRITE, "refusing to write the superseded V76's snapshot path"
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image is already there (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). A same-number re-cut destroyed a "
            "predecessor's snapshot once already. Rename it deliberately, then re-run.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n        SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "the V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V76 output")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    # ---- 🛑 EVERYTHING re-derived FROM THE READBACK --------------------------------------------
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec[START:END]) == bytes(code[START:END]), "the decoded payload != the built image"

    assert_pins(dec, "readback", skip={"PIN_MOVEA_HOOK"})
    # ...and the two facts that REPLACE that pin on the built image:
    assert bytes(dec[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "readback: the hook is not our `jarl` to the cave"
    assert bytes(dec[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "readback: the hook's return site 0x55C12 was disturbed"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]).count(HOOK_STOCK) == 1, \
        "readback: the displaced `movea` is not replayed EXACTLY once in the cave"
    assert_no_aliasing(dec)
    assert_record_geometry(dec, "readback")
    rb_clamp, rb_thresh, rb_fric = assert_fault_interlock(dec, "readback")
    assert_not_carried(dec, "readback")
    assert_manual_mode_stock(dec, base, "readback")
    assert_cell_censuses(dec, cave_span, True, "readback")
    assert_crc_chain(dec, "readback")
    for kind, ptrs, want in (("C", FACTOR_C_PTRS, NEW_C26), ("E", FACTOR_E_PTRS, NEW_E26)):
        _o, _n, x, y = read_rec(dec, ptrs, LIVE_MODE)
        assert (x, y) == want, f"readback Factor{kind} m26 is X={x} Y={y}, expected {want}"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave, "the readback cave differs"
    assert bytes(dec[HOOK_ADDR:HOOK_ADDR + 4]) == hook_patch, "the readback hook differs"
    # 🛑 Re-disassembled FROM THE DECODED .rwd BYTES in Python -- a stale Ghidra import defeats
    # hash-checking, so the cave's contents get an independent second method.
    redis = redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    assert b"".join(r for _a, r, _t in redis) == cave, \
        "the re-disassembly does not reconstruct the cave's bytes"
    ncode = len(listing) - 1                      # every entry except the trailing pad blob
    assert [(a, r) for a, r, _t in redis[:ncode]] == [(a, r) for a, r, _t in listing[:ncode]], \
        "the readback cave does not re-disassemble to the emitted listing"
    # the pad decodes as 2-byte `nop`s rather than one 4-byte blob -- the more faithful reading
    assert all(t == "nop" and r == b"\x00\x00" for _a, r, t in redis[ncode:]), \
        "the cave tail is not pure `nop` padding"
    assert sum(len(r) for _a, r, _t in redis[ncode:]) == CAVE_EXTENT - 64, "the pad length moved"
    assert len(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])) == CAVE_EXTENT == 68
    assert bytes(dec[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the readback cave tail is not 0xFF"
    rb_runs = changed_runs(base, dec)
    assert sum(ln for _a, ln in rb_runs) == total, "the readback diff size differs"

    print("\n  READBACK -- re-derived FROM THE DECODED .rwd BYTES: both records via the pointer")
    print("     arrays, mode-24 identity, the DTC-0x1d interlock, the dropped levers, all "
          f"{n_pins} pins,")
    print("     every probed cell's census, the whole 68-byte cave AND its re-disassembly, the")
    print("     cave tail, and the full 50-block CRC chain. ALL PASS.")
    print(f"\n  wrote {OUT}\n        SHA256 {rwd_sha}")

    print("\n" + "=" * 102)
    print("  V76 BUILT on the V38 base.")
    print(f"  🛑 INTERLOCK RESTORED: 0xC407E = {rb_clamp} against a {FAULT_TRIP_COUNTS}-count trip "
          f"(0xC4004 = {rb_thresh}); friction m26 @0x{rb_fric:05X} byte-stock.")
    print("     V73/V74/V75 carried 850 here. That is the mechanism that took the steering out.")
    print(f"  ★ mode 26 damper: FactorC Y -> {NEW_C26[1]}, FactorE X -> {NEW_E26[0]}, "
          f"Y -> {NEW_E26[1]}")
    print("  🛑 MODE 24 (manual) IS BYTE-STOCK -- asserted from the pointer arrays, twice.")
    print(f"  ★ probe: bit{BIT_STATE5} state==5 (POSITIVE CONTROL) · bit{BIT_MODEIDX} mode&2 · "
          f"bit{BIT_BCDIFF} |6bc6-6bc8|>5 · bits {BITS_HELD} ZERO BY CONSTRUCTION")
    print("     Read bit3 FIRST: all-zero on bits 5:3 for a whole drive = the cave never fired.")
    print("  🛑 Flash ONLY on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    main()
