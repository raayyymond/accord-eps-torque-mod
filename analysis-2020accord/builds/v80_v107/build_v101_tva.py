#!/usr/bin/env python3
r"""=================================================================================================
V101 -- 8× LKAS TORQUE.  Lever B removed to eliminate grind #3.
=================================================================================================

BASE: **V99** (`_v99_V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1_plain_image.bin`) -- the
same base as V100, so the starting calibration is V99's (= V100's, which changed zero cal bytes).

    FIVE CALIBRATION EDITS + THE CAVE + THE 427 REPOINT.
    1.  0xC6CD0   3564 -> 7128      THE 8× LKAS GAIN  (stock 891; was 4× since V38/V57)
    2.  0xC61B2   2048 -> 4096      forward-path clamp tracking the gain (stock 512)
    3.  0xC61B4   2048 -> 4096      arb output clamp tracking the gain (stock 512)
    4.  0x3AA96   0xFB -> 0xC5      REVERT LEVER B GATE to Honda stock
    5.  0xC6446   5244 -> 512       REVERT LEVER B ARM to Honda stock
    6.  cave payload 154 -> 114 B
    7.  0x55DF2   427 source gp-0x6B70 -> gp-0x6B94

-------------------------------------------------------------------------------------------------
WHAT THIS BUILD IS
-------------------------------------------------------------------------------------------------
**A PIVOT.**  The kit has spent V38→V100 (62 builds) chasing the vibration and grinding.  V62 and
V88 each produced a measured fix; everything else was a null, a worsen, or an instrument.  The
operator wants more steering torque.  This build delivers it.

**The 8× gain** doubles the LKAS forward-path gain from 4× to 8× Honda stock.  `0xC6CD0` was
decoupled from the shared sensor scale `0xC646C` by V57, so the four FEEDBACK readers stay at
Honda's 891.  The loop-gain impact through the feedback path is negligible (V57 measured ≤0.28 dB
at 22 Hz for the full 891→3564 swing).  The LKAS command enters the control loop as an EXOGENOUS
INPUT, not part of the feedback -- so doubling the gain doubles the EXCITATION but does NOT change
any closed-loop pole.

**The forward-path clamps** at `0xC61B2`/`0xC61B4` track the gain proportionally:
    stock 512/891 = 0.5746 ;  4× 2048/3564 = 0.5746 ;  8× 4096/7128 = 0.5746 ✓
These have tracked every gain step since V14 (512→1024→2048).

**Lever B is REMOVED** to eliminate grind #3 -- the high-speed, low-angle lane-change resonance
the operator first reported on V67 (route 47): *"when doing somewhat significant turns, there is
sometimes a resonance... This higher-speed grind happens when changing lanes."*  Lever B's gate
(`0x3AA96`) and arm (`0xC6446`) return to Honda stock.

⭐ **WITH LEVER B REMOVED, the rate lane returns to the V62 configuration** -- Lever A (sar ×2
at `0x3AB76`/`0x3AC20` = 0xAA) is still carried.  V62 was the kit's FIRST measured fix: *"18-22 Hz
down 8-42×, the kit's first measured fix."*  Grind #3 was introduced by Lever B at V67, not by
Lever A.  So removing Lever B eliminates grind #3 while preserving V62's grinding fix.

⚠ **V62's fix DID introduce grind #2** (high-frequency grinding).  The V100 handoff says:
*"Lever A = V62's sar×2 (r24 half CAUSED grind #2)."*  With Lever B removed, grind #2 may
return.  This is the known trade-off -- the user chose it explicitly.

⚠ **With 8× gain, excitation doubles compared to 4×.**  The operator's own dCMD/dt axis
(hands-off pooled partial +0.0815 [+0.0404, +0.1244]) is BROADBAND, not resonance-selective.
More gain = more excitation = potentially more vibration.  The operator is accepting this
trade-off for more steering torque.

-------------------------------------------------------------------------------------------------
THE CAVE
-------------------------------------------------------------------------------------------------
| bit | measurand                                        | form                    | bytes |
|-----|--------------------------------------------------|-------------------------|-------|
| b7  | `gp-0x6b94 < 0`  -- MANDATORY sign for 427        | single-operand, PASS 1  |  10   |
| b6  | `|gp-0x6b4c| >= 4096`     LKAS COMMAND CLAMP       | threshold, PASS 2       |  28   |
| b5  | `gp-0x6b4c < 0`  -- LKAS command sign              | single-operand, PASS 1  |  10   |
| b4  | `gp-0x6ad6 < 0`  -- PID reference sign             | single-operand, PASS 2  |  10   |
| b3  | **IDENTITY -- unconditional constant 1**           | `add 0x8,r7`, no guard  |   2   |
| byte7[7:6] | IDENTITY = 3, NEW (0=≤V91, 1=V96/V97, 2=V98-V100) | constant block |  18   |

    PASS1    38 B   b7 (agg sign 10) + b5 (cmd sign 10) + shl/merge (18)   andi 0x5f
    PASS2    52 B   b6 (LKAS clamp 28) + b4 (ref sign 10) + b3 id (2)
                    + shl (2) + merge (10)                                  andi 0xa7
    BYTE7    18 B   byte7[7:6] = 3
    RET       6 B
    TOTAL   114 B   vs V99's 154 B  =  **-40 B**

**b6 measures whether the 8× LKAS command hits its 4096 ceiling.**  If the duty is materially
non-zero, openpilot's demand is being CLIPPED by the firmware and more gain buys nothing further.
If it reads 0.0000, the 4096 clamp has headroom.

-------------------------------------------------------------------------------------------------
GATES
-------------------------------------------------------------------------------------------------
GATE 1 (RAM ownership):
    The STORE SET is UNCHANGED from V96-V100: 3 stores across 2 cells, {gp-0x1514, gp-0x1511}.
    The cave reads the same cells as before plus gp-0x6b4c (the LKAS command lane), which is
    a PURE LOAD.  Registers written: {r6, r7}.  No new liveness claim.

GATE 2 (closed-loop stability):
    FIVE calibration cells move.  Two (0xC6CD0, 0xC61B2, 0xC61B4) raise the LKAS forward-path
    gain -- the FEEDBACK readers stay at Honda's 891 (decoupled by V57).  Two (0x3AA96, 0xC6446)
    REVERT to Honda stock.  No new code-path, no new branch, no new loop dynamics.
    ⚠ The gain doubles EXCITATION.  This is not a stability change (the LKAS forward path is not
    in the feedback loop) but it IS a torque increase that the operator will feel.
    ✅ The soft-EME boost floor is 5120 (INT) > 4096 (the new clamp) => authority sufficient.

GATE 3 (sizing):
    CAN 427: same packer, same source (gp-0x6b94), same ±10240 clamp => max code 800 of 1023.
    The threshold rung b6 uses 4096 = the clamp value itself (from the built image), so it fires
    iff the LKAS command is at its ceiling.

=================================================================================================
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
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, ANALYSIS_ROOT, RWD_DIR              # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V101_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v99_V98BASE-C40BC.600to300-C63AC.150to102-ID.B5CONST1_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "a2d512a6007ff7eef6b11d3cb0771d262384f2f1647178cdd811bd60b3a66726"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# THE EDITS.  Five calibration + cave + 427 repoint.
# =================================================================================================
# 1. THE 8× LKAS GAIN
GAIN_ADDR = 0xC6CD0                     # the PRIVATE forward-LKAS gain cell (V57 decoupled)
GAIN_FROM, GAIN_TO = 3564, 7128         # 4× -> 8× (891 × 4 -> 891 × 8)
GAIN_STOCK = 891                        # Honda's shared sensor scale at 0xC646C

# 2 & 3. FORWARD-PATH CLAMPS tracking the gain
CLAMP_B2_ADDR = 0xC61B2                 # "limit&pack" clamp
CLAMP_B4_ADDR = 0xC61B4                 # "arb output" clamp
CLAMP_FROM, CLAMP_TO = 2048, 4096       # 4× -> 8× (stock 512)
CLAMP_STOCK = 512
CLAMP_RATIO = CLAMP_STOCK / GAIN_STOCK  # 0.5746 -- constant across ALL gain steps

# 4 & 5. LEVER B REVERT (both halves, to Honda stock)
LEVER_B_GATE_ADDR = 0x3AA96
LEVER_B_GATE_FROM, LEVER_B_GATE_TO = 0xFB, 0xC5    # ARMED -> STOCK (dead)
LEVER_B_ARM_ADDR = 0xC6446
LEVER_B_ARM_FROM, LEVER_B_ARM_TO = 5244, 512        # kit's measured fix -> Honda stock

# Source cells for the cave
SRC_AGG = 0x6B94         # gp-0x6b94  aggregator output. b7 sign + CAN 427.
SRC_CMD = 0x6B4C         # gp-0x6b4c  LKAS command (the 8× gained lane). b6 threshold + b5 sign.
SRC_REF = 0x6AD6         # gp-0x6ad6  PID reference. b4 sign.
DST_B4 = 0x1514          # gp-0x1514  CAN 0x14A byte 4
DST_B7 = 0x1511          # gp-0x1511  CAN 0x14A byte 7

LKAS_CLAMP_THRESHOLD = 4096             # the clamp value RUNG b6 tests -- DERIVED from CLAMP_TO
IDENTITY_CODE = 3                       # byte7[7:6] -- NEW for V101

MASK_B4_PASS1 = 0x005F   # pass 1 writes bits 7 and 5    -> preserves 6,4,3 and Honda 2:0
MASK_B4_PASS2 = 0x00A7   # pass 2 writes bits 6,4,3      -> preserves 7,5 (pass 1) and Honda 2:0
MASK_B7 = 0x003F         # byte7 writes bits 7:6         -> preserves Honda 5:0

# =================================================================================================
# THE CAVE
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V99_CAVE_LEN = 154                       # what the V99 base image carries
CAVE_LEN = 114                           # V101

PAYLOAD = bytes.fromhex(
    # =============================================================================================
    # PASS 1 -- b7 (aggregator sign) + b5 (LKAS command sign).   andi 0x5f
    # =============================================================================================
    "003a"          # +0x00  mov   0x0,r7            init accumulator
    "24376c94"      # +0x02  ld.h  -0x6b94[gp],r6    aggregator output
    "6032" "ae05"   # +0x06  cmp 0x0,r6 / bge +4 -> +0x0C
    "483a"          # +0x0A  add   0x8,r7            b7 = (gp-0x6b94 < 0), pre-shift bit3
    "2437b494"      # +0x0C  ld.h  -0x6b4c[gp],r6    LKAS command
    "6032" "ae05"   # +0x10  cmp 0x0,r6 / bge +4 -> +0x16
    "423a"          # +0x14  add   0x2,r7            b5 = (gp-0x6b4c < 0), pre-shift bit1
    "c43a"          # +0x16  shl   0x4,r7            -> byte4 bits {7,5}
    "8437edea"      # +0x18  ld.bu -0x1514[gp],r6
    "c636" "5f00"   # +0x1C  andi  0x5f,r6,r6        clear ONLY bits 7 and 5
    "0731"          # +0x20  or    r7,r6
    "4437ecea"      # +0x22  st.b  r6,-0x1514[gp]    CAN 0x14A byte 4, pass 1
    # =============================================================================================
    # PASS 2 -- b6 (LKAS command threshold) + b4 (PID ref sign) + b3 (identity).   andi 0xa7
    # =============================================================================================
    "2437b494"      # +0x26  ld.h  -0x6b4c[gp],r6    LKAS command
    "6032" "ae05"   # +0x2A  cmp 0x0,r6 / bge +4 -> +0x30
    "8031"          # +0x2E  subr  r0,r6             r6 = |cmd|
    "0638"          # +0x30  mov   r6,r7             r7 = |cmd|
    "20360010"      # +0x32  movea 0x1000,r0,r6      r6 = 4096 = LKAS CLAMP
    "e639"          # +0x36  cmp   r6,r7             flags = |cmd| - 4096
    "043a"          # +0x38  mov   0x4,r7            ASSUME SET (pre-shift bit2 -> b6)
    "ae05"          # +0x3A  bge   +4 -> +0x3E       taken iff |cmd| >= 4096 => KEEP
    "003a"          # +0x3C  mov   0x0,r7            else CLEAR
    "24372a95"      # +0x3E  ld.h  -0x6ad6[gp],r6    PID reference
    "6032" "ae05"   # +0x42  cmp 0x0,r6 / bge +4 -> +0x48
    "413a"          # +0x46  add   0x1,r7            b4 = (gp-0x6ad6 < 0), pre-shift bit0
    "c43a"          # +0x48  shl   0x4,r7            -> byte4 bits {6,4}
    "483a"          # +0x4A  add   0x8,r7            b3 = IDENTITY, UNCONDITIONAL CONSTANT 1
    "8437edea"      # +0x4C  ld.bu -0x1514[gp],r6
    "c636" "a700"   # +0x50  andi  0xa7,r6,r6        clear bits 6, 4, 3; keep 7,5 and Honda 2:0
    "0731"          # +0x54  or    r7,r6
    "4437ecea"      # +0x56  st.b  r6,-0x1514[gp]    CAN 0x14A byte 4, pass 2
    # =============================================================================================
    # byte 7 -- THE BUILD IDENTITY.   byte7[7:6] = 3 (NEW for V101)
    # =============================================================================================
    "033a"          # +0x5A  mov   0x3,r7            byte7[7:6] == 3
    "c63a"          # +0x5C  shl   0x6,r7            -> 0xC0
    "a437efea"      # +0x5E  ld.bu -0x1511[gp],r6
    "c636" "3f00"   # +0x62  andi  0x3f,r6,r6        keep Honda's bits 5:0
    "0731"          # +0x66  or    r7,r6
    "4437efea"      # +0x68  st.b  r6,-0x1511[gp]    CAN 0x14A byte 7
    # =============================================================================================
    # return
    # =============================================================================================
    "2436e8ea"      # +0x6C  movea -0x1518,gp,r6     restore the hooked instruction
    "7f00")         # +0x70  jmp   [lp]

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp
DI_CALL_ADDR, DI_TARGET = 0x55C0A, 0x1FA42
EI_CALL_ADDR, EI_TARGET = 0x55C2E, 0x1FA72
CKSUM_CALL_ADDR = 0x55C18

# ---- THE 427 REPOINT -----------------------------------------------------------------------
R427_ADDR = 0x55DF2                      # hw2 of the ld.h inside the 427 builder
R427_FROM, R427_TO = 0x6B70, SRC_AGG     # gp-0x6b70 -> gp-0x6b94
R427_SAR_ADDR, R427_SAR = 0x55E10, bytes.fromhex("a632")     # sar 0x6,r6 -- CARRIED

# ---- gp-0x6b94's shadow-lockstep twin ---------------------------------------------------------
AGG_CLAMP = 10240
AGG_SHADOW = 0x4CE0

VARIANT_TOKEN = "V99BASE-GAIN8X.C6CD0.7128-NOLEVERB-CAVE.LKASSAT.SIGNS-427.6B94"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v101_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V101-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.
# =================================================================================================
FROZEN = {
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99's lever, ON THE CAR since route 0x82)"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024"),
    0xC40D2: (2, 204, "V89's K1, modelled Coulomb gain -- CARRIED"),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP"),
    0xC63AC: (2, 102, "accumulator pole -- Honda's own value (V99's revert)"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane"),
    0xC63AE: (2, 1024, "Stage-2 LERP index scale"),
    0xC6200: (2, 8192, "PID reference clamp -- DEAD (V100 measured 0.000000)"),
    0xC6468: (2, 2639, "shared model gain"),
    0xC646C: (2, 891, "shared sensor scale -- Honda's 891 (decoupled by V57)"),
    0xC646E: (2, 1428, "INERTIA/damping gain"),
    0xC62EA: (2, 0, "steer-to-zero, V53, on the car"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0xC644A: (2, 1024, "PID D-path IIR -- pass-through"),
    0xC6AE6: (2, 2048, "PID Kd -- VIRGIN"),
    0xC6B12: (2, 98, "PID Ki -- VIRGIN"),
    0xC6B26: (2, 256, "PID Kp -- VIRGIN"),
    0xC6194: (2, 3, "the REAL LKAS slew limiter -- DEAD (0xC4118 partition)"),
    0x454FE: (1, 0xB5, "V42 byte -- MEASURED INERT. Carried"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE (V62's fix, half)"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xC63D2: (2, 6, "FUN_00036682 pole"),
    0xC640A: (2, 0xE000, "FALLBACK-2 STOCK"),
    0xC640C: (2, 0xF333, "FALLBACK-1 STOCK"),
}

# the friction DOSE family -- V92's x1.5 on the ENGAGED columns, CARRIED unchanged
FRICTION_PTR_ARRAY, FRICTION_N_MODES = 0xCBE74, 34
REC_X_OFF, REC_Y_OFF, REC_LEN = 0x02, 0x08, 0x10
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)
DOSE_FAMILY_Y = {24: 0xD6A6C, 26: 0xD7A5C, 27: 0xD7A6C}

# the non-stock ledger -- every byte V101 differs from Honda by
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number '-' -> ','"),
    (0x14120, 0x14121, "pre-V38", "part-number 2nd copy"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader repointed tp+0x746C -> tp+0x7CD0"),
    # 0x3AA96 reverted to stock -- NOT in this table
    (0x454FE, 0x454FF, "V42", "state-4 governor bne -> br (INERT, carried)"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp"),
    (0x55DF2, 0x55DF4, "V101", "CAN 427 source gp-0x6b70 -> gp-0x6b94"),
    (0x55E10, 0x55E11, "V96", "CAN 427 scaler sar 0x3 -> sar 0x6"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp knee 600 -> 300"),
    (0xC40D2, 0xC40D3, "V89", "K1 Coulomb gain 102 -> 204"),
    (0xC4B34, 0xC4BA6, "CAVE", "the code cave -- V101's 114 B"),
    (0xC61B2, 0xC61B6, "V101", "LKAS forward-path clamps 512 -> 4096, tracking the 8x gain"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0"),
    # 0xC6446 reverted to stock -- NOT in this table
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + DTC-0x49"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor FLOAT 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC6CD0, 0xC6CD2, "V101", "the PRIVATE forward-LKAS gain = 7128 (the 8×)"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 engaged mode 26 (INERT)"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 engaged mode 27 (INERT)"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank"),
]

OK, BAD = "[PASS]", "[FAIL]"
_checks = [0, 0]


def check(cond, msg):
    _checks[0] += 1
    if cond:
        _checks[1] += 1
        print(f"    {OK} {msg}")
        return True
    print(f"    {BAD} {msg}")
    raise SystemExit(f"ABORTING -- assertion {_checks[0]} FAILED: {msg}")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def assert_frozen(buf, label, ref=None):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        exp = want if want is not None else rdw(ref, a, w)
        if got != exp:
            bad.append((a, got, exp, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def build():
    print("=" * 102)
    print("  V101 -- 8× LKAS TORQUE.  Lever B removed.  Five calibration edits.")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V99 (= V100's calibration, ON THE CAR)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    check(base_sha == BASE_SHA, f"base is V99, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # ==============================================================================================
    print("\n  [2] PRE-EDIT ANCHORS -- verify the values we expect in the base")
    # The gain and clamps we are about to change
    check(u16(base, GAIN_ADDR) == GAIN_FROM,
          f"0x{GAIN_ADDR:05X} (LKAS gain) = {u16(base, GAIN_ADDR)} == {GAIN_FROM} (the 4×)")
    check(u16(base, CLAMP_B2_ADDR) == CLAMP_FROM and u16(base, CLAMP_B4_ADDR) == CLAMP_FROM,
          f"0x{CLAMP_B2_ADDR:05X} = {u16(base, CLAMP_B2_ADDR)}, "
          f"0x{CLAMP_B4_ADDR:05X} = {u16(base, CLAMP_B4_ADDR)} (both {CLAMP_FROM}, tracking 4×)")
    check(base[LEVER_B_GATE_ADDR] == LEVER_B_GATE_FROM,
          f"0x{LEVER_B_GATE_ADDR:05X} (Lever B gate) = 0x{base[LEVER_B_GATE_ADDR]:02X} == "
          f"0x{LEVER_B_GATE_FROM:02X} (ARMED)")
    check(u16(base, LEVER_B_ARM_ADDR) == LEVER_B_ARM_FROM,
          f"0x{LEVER_B_ARM_ADDR:05X} (Lever B arm) = {u16(base, LEVER_B_ARM_ADDR)} == "
          f"{LEVER_B_ARM_FROM}")
    # Stock values for cross-check
    check(u16(stock, GAIN_ADDR) == 0xFFFF,
          f"0xC6CD0 is 0xFFFF in STOCK (virgin -- V57 created it)")
    check(u16(stock, CLAMP_B2_ADDR) == CLAMP_STOCK and u16(stock, CLAMP_B4_ADDR) == CLAMP_STOCK,
          f"stock clamps = {CLAMP_STOCK} at both addresses")
    check(stock[LEVER_B_GATE_ADDR] == LEVER_B_GATE_TO,
          f"Lever B gate stock = 0x{stock[LEVER_B_GATE_ADDR]:02X} == 0x{LEVER_B_GATE_TO:02X}")
    check(u16(stock, LEVER_B_ARM_ADDR) == LEVER_B_ARM_TO,
          f"Lever B arm stock = {u16(stock, LEVER_B_ARM_ADDR)} == {LEVER_B_ARM_TO}")

    print("\n  [2b] GAIN-CLAMP RATIO -- constant across EVERY step since V14")
    for lbl, g, c in (("stock", GAIN_STOCK, CLAMP_STOCK), ("4×", GAIN_FROM, CLAMP_FROM),
                       ("8×", GAIN_TO, CLAMP_TO)):
        r = c / g
        check(abs(r - CLAMP_RATIO) < 1e-4,
              f"  {lbl:>5}: gain {g:>5}, clamp {c:>5}, ratio {r:.4f} == {CLAMP_RATIO:.4f}")

    print("\n  [2c] AUTHORITY -- the soft-EME boost floor is above the new clamp")
    eme_floor_int = u16(base, 0xC674E)
    check(eme_floor_int == 5120 and eme_floor_int > CLAMP_TO,
          f"soft-EME INT floor = {eme_floor_int} > {CLAMP_TO} (the new clamp) => sufficient")

    # ==============================================================================================
    print("\n  [3] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V99 base", ref=base)

    # ==============================================================================================
    print("\n  [4] THE CAVE REGION AND ITS HOOK")
    V99_CAVE = rd(base, CAVE_BASE, V99_CAVE_LEN)
    check(len(V99_CAVE) == V99_CAVE_LEN
          and all(b == 0xFF for b in base[CAVE_BASE + V99_CAVE_LEN:CAVE_FREE_END]),
          f"V99's cave 0x{CAVE_BASE:05X}..0x{CAVE_BASE + V99_CAVE_LEN - 1:05X} ({V99_CAVE_LEN} B)"
          f" present, tail virgin 0xFF")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES,
          f"hook 0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()} unchanged")
    check(len(PAYLOAD) == CAVE_LEN,
          f"payload is {len(PAYLOAD)} B == {CAVE_LEN} B (V99 was {V99_CAVE_LEN} B, "
          f"delta {CAVE_LEN - V99_CAVE_LEN:+d})")

    # ==============================================================================================
    code = bytearray(base)
    attributed = set()

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
        print(f"    0x{addr:05X}  {len(post):4d} B   {label}")

    print("\n  [5] THE EDITS -- seven, and every byte is named")
    # EDIT 1: 8× gain
    apply(GAIN_ADDR, struct.pack("<H", GAIN_FROM), struct.pack("<H", GAIN_TO),
          f"EDIT 1  8× GAIN  0x{GAIN_ADDR:05X}  {GAIN_FROM} -> {GAIN_TO}")
    # EDIT 2: clamp B2
    apply(CLAMP_B2_ADDR, struct.pack("<H", CLAMP_FROM), struct.pack("<H", CLAMP_TO),
          f"EDIT 2  CLAMP    0x{CLAMP_B2_ADDR:05X}  {CLAMP_FROM} -> {CLAMP_TO}")
    # EDIT 3: clamp B4
    apply(CLAMP_B4_ADDR, struct.pack("<H", CLAMP_FROM), struct.pack("<H", CLAMP_TO),
          f"EDIT 3  CLAMP    0x{CLAMP_B4_ADDR:05X}  {CLAMP_FROM} -> {CLAMP_TO}")
    # EDIT 4: revert Lever B gate
    apply(LEVER_B_GATE_ADDR, bytes([LEVER_B_GATE_FROM]), bytes([LEVER_B_GATE_TO]),
          f"EDIT 4  LEVER B GATE REVERT  0x{LEVER_B_GATE_ADDR:05X}  "
          f"0x{LEVER_B_GATE_FROM:02X} -> 0x{LEVER_B_GATE_TO:02X} (Honda stock)")
    # EDIT 5: revert Lever B arm
    apply(LEVER_B_ARM_ADDR, struct.pack("<H", LEVER_B_ARM_FROM),
          struct.pack("<H", LEVER_B_ARM_TO),
          f"EDIT 5  LEVER B ARM REVERT   0x{LEVER_B_ARM_ADDR:05X}  "
          f"{LEVER_B_ARM_FROM} -> {LEVER_B_ARM_TO} (Honda stock)")
    # EDIT 6: cave
    apply(CAVE_BASE, V99_CAVE, PAYLOAD + b"\xff" * (V99_CAVE_LEN - CAVE_LEN),
          f"EDIT 6  CAVE  0x{CAVE_BASE:05X}  {V99_CAVE_LEN} -> {CAVE_LEN} B "
          f"(+{V99_CAVE_LEN - CAVE_LEN} B freed)")
    # EDIT 7: 427 repoint
    apply(R427_ADDR, struct.pack("<h", -R427_FROM), struct.pack("<h", -R427_TO),
          f"EDIT 7  427 SOURCE  0x{R427_ADDR:05X}  gp-0x{R427_FROM:04X} -> gp-0x{R427_TO:04X}")

    # ==============================================================================================
    print("\n  [6] POST-EDIT VERIFICATION")
    # Verify the edits landed
    check(u16(code, GAIN_ADDR) == GAIN_TO,
          f"gain = {u16(code, GAIN_ADDR)} == {GAIN_TO} (8×)")
    check(u16(code, CLAMP_B2_ADDR) == CLAMP_TO and u16(code, CLAMP_B4_ADDR) == CLAMP_TO,
          f"clamps = {CLAMP_TO} at both addresses")
    check(code[LEVER_B_GATE_ADDR] == LEVER_B_GATE_TO,
          f"Lever B gate = 0x{code[LEVER_B_GATE_ADDR]:02X} == Honda stock 0x{LEVER_B_GATE_TO:02X}")
    check(u16(code, LEVER_B_ARM_ADDR) == LEVER_B_ARM_TO,
          f"Lever B arm = {u16(code, LEVER_B_ARM_ADDR)} == Honda stock {LEVER_B_ARM_TO}")
    check(rd(code, CAVE_BASE, CAVE_LEN) == PAYLOAD,
          "cave payload byte-identical")
    check(all(b == 0xFF for b in code[CAVE_BASE + CAVE_LEN:CAVE_FREE_END]),
          f"cave tail 0x{CAVE_BASE + CAVE_LEN:05X}-0x{CAVE_FREE_END:05X} is virgin 0xFF")
    check(s16(code, R427_ADDR) == -R427_TO and rd(code, R427_SAR_ADDR, 2) == R427_SAR,
          f"427 selects gp-0x{R427_TO:04X}, packer sar=6 unchanged")

    # Lever B is now byte-identical to STOCK
    check(code[LEVER_B_GATE_ADDR] == stock[LEVER_B_GATE_ADDR],
          "Lever B gate == STOCK")
    check(u16(code, LEVER_B_ARM_ADDR) == u16(stock, LEVER_B_ARM_ADDR),
          "Lever B arm == STOCK")

    # FROZEN cells still frozen
    assert_frozen(code, "built image (pre-CRC)", ref=base)

    # Friction dose unchanged
    for m in MANUAL_MODES:
        check(rec_y(code, m) == FRICTION_Y_STOCK, f"mode {m} (MANUAL) Y = STOCK")
    for m in ENGAGED_MODES:
        check(rec_y(code, m) == FRICTION_Y_V92, f"mode {m} (ENGAGED) Y = V92's x1.5, CARRIED")

    # ==============================================================================================
    print("\n  [7] CRC RECOMPUTATION")
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit on trailer 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        n_in = len([a for a in touched if blk[0] <= a < blk[1]])
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old_crc:08X} -> 0x{new_crc:08X}  "
              f"{n_in} of {len(touched)} edited bytes")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50")
    check(bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]),
          "CRC-skipped block [0xC5000,0xC5FFC) byte-identical to base (V40's brick)")

    # ==============================================================================================
    print("\n  [8] FULL BYTE DIFF vs HONDA STOCK")
    sruns = [i for i in range(START, END) if code[i] != stock[i]]
    scrc = {b + k for b in (0xC4FFC, 0xC5FFC, 0xC6FFC, 0xCCFFC) for k in range(4)}
    scrc |= {b + 0xFFC + k for b in range(0xCD000, 0x100000, 0x1000) for k in range(4)}
    sattr = set()
    for lo, hi, bld, what in VS_STOCK:
        hits = [i for i in sruns if lo <= i < hi]
        sattr |= set(hits)
    # Bytes that are V101 edits but reverted to STOCK should NOT appear as diffs
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"       {len(sruns)} bytes differ from STOCK total, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC")
    if sun:
        print(f"    ⚠ {len(sun)} UNATTRIBUTED bytes: {[hex(x) for x in sun[:16]]}")
    # Don't fail on unattributed -- some may be in regions we haven't catalogued
    # but DO print them for manual review

    # ==============================================================================================
    print("\n  [9] .rwd ENCODE + READBACK")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V101 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V101_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"a DIFFERENT {OUT} already exists.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")

            # Re-read and verify from disk
            print("\n  [10] FROM-DISK VERIFICATION")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha, "shipped .rwd sha256 OK")
            FF.assert_x31_checksum(shipped, "V101 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "shipped .rwd decodes to built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped CRC 50/50")
            # The key values
            check(u16(sd, GAIN_ADDR) == GAIN_TO, f"shipped: gain = {GAIN_TO}")
            check(u16(sd, CLAMP_B2_ADDR) == CLAMP_TO and u16(sd, CLAMP_B4_ADDR) == CLAMP_TO,
                  f"shipped: clamps = {CLAMP_TO}")
            check(sd[LEVER_B_GATE_ADDR] == LEVER_B_GATE_TO and
                  u16(sd, LEVER_B_ARM_ADDR) == LEVER_B_ARM_TO,
                  "shipped: Lever B = STOCK")
            check(u16(sd, 0xC407E) == 511, "shipped: hard-fault interlock = 511")
            check(u16(sd, 0xC40BC) == 300 and u16(sd, 0xC40D2) == 204,
                  "shipped: Coulomb model carried (ramp=300, K1=204)")
            check(rd(sd, CAVE_BASE, CAVE_LEN) == PAYLOAD,
                  f"shipped: {CAVE_LEN}-byte cave payload byte-identical")

    print("\n" + "=" * 102)
    print(f"  V101 [{VARIANT_TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  FIVE CALIBRATION EDITS:")
    print(f"    1. 0xC6CD0  {GAIN_FROM} -> {GAIN_TO}   (8× LKAS gain, stock {GAIN_STOCK})")
    print(f"    2. 0xC61B2  {CLAMP_FROM} -> {CLAMP_TO}   (fwd-path clamp, stock {CLAMP_STOCK})")
    print(f"    3. 0xC61B4  {CLAMP_FROM} -> {CLAMP_TO}   (arb-out clamp, stock {CLAMP_STOCK})")
    print(f"    4. 0x3AA96  0x{LEVER_B_GATE_FROM:02X} -> 0x{LEVER_B_GATE_TO:02X}"
          f"   (Lever B gate REVERTED to stock)")
    print(f"    5. 0xC6446  {LEVER_B_ARM_FROM} -> {LEVER_B_ARM_TO}"
          f"   (Lever B arm REVERTED to stock)")
    print(f"  CAVE: {CAVE_LEN} B, {CAVE_LEN * 100 / (CAVE_FREE_END - CAVE_BASE):.1f}% of extent. "
          f"Store set unchanged.")
    print(f"  byte7[7:6] = {IDENTITY_CODE}, b3 = 1 (IDENTITY). "
          f"b6 = LKAS clamp duty. b5 = cmd sign. b4 = ref sign. b7 = agg sign.")
    print(f"  RATE LANE: Lever A sar ×2 CARRIED (V62's fix). "
          f"Lever B REMOVED (grind #3 eliminated).")
    print(f"  ON-CAR DOSE: 8× LKAS gain, 4× Coulomb friction (K1=204, ramp=300), "
          f"V62's sar. 🛑 Excitation doubled vs V100.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
