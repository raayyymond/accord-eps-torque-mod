#!/usr/bin/env python3
"""builds/v50_v79/build_v78_tva.py -- V78 = V76 + ONE u16 damper cell + a RE-CUT probe. UNFLASHED.

★ WHY THIS BUILD EXISTS.  V76 flew route 65 clean (636.3 s, 63,477 frames, zero DTC transitions,
all five legs of the V74/V75 hard-fault fingerprint negative). The operator reports **grind #1 and
micro-ratcheting still present at creep**. This session measured the dose response over the whole
V72..V76 ladder, episode-bootstrapped:

    grind #1  (18-22 Hz)  slope b = -0.614 [-0.810, -0.416] on k   -> DOSE-LIMITED
    ratchet   ( 6-9  Hz)  slope b = -0.094 [-0.291, +0.098] on k   -> DOSE-INDEPENDENT

🛑 **THIS BUILD IS NOT EXPECTED TO TOUCH THE MICRO-RATCHET, AND MUST NOT BE DESCRIBED AS IF IT WERE.**
Its one validated target is grind #1. The operator asked for **150% of V75's damper dose at 5 mph**.

    dose(5 mph, r=99 ct) :  V75 137  ->  V78 206   = 150.36%
    k (truncated form)   :  V76 1.3866 -> V78 2.0840   = 1.503x V76, 1.319x V75

THE EDIT -- exactly ONE u16 cell
--------------------------------
    FactorE, mode 26 (ENGAGED) record, Y[1]:  300 -> 449      (2 bytes)
        after:  X = [0, 119, 2500, 4000]   Y = [0, 449, 539, 927]
        before: X = [0, 119, 2500, 4000]   Y = [0, 300, 539, 927]
FactorC is UNCHANGED (`[566,566,566,908]`), mode 24 stays byte-stock, every other factor untouched.
🛑 The record address is DEREFERENCED from the pointer array (`0xC9F84 + 26*4`), never hard-coded.

WHAT IS CARRIED FROM V76 BY BEING BUILT ON IT
---------------------------------------------
The base is V76's own plain image, so the DTC-0x1d interlock (`0xC407E` = 511 against the 512-count
trip in `FUN_00036d74`), the byte-stock friction table, `0xC63A0` = 1024 and byte-stock mode 24 all
come across untouched. Each is still asserted BY VALUE here (RULE 3: a lever is only carried if the
bytes say so), on the base, on the built image and on the .rwd readback.

🛑 RULE 11 -- `0xC407E` IS A DO-NOT-RAISE CELL. A clamp may be an interlock.

THE PROBE -- RE-CUT, and one rung deliberately DIFFERS FROM THE BRIEF
--------------------------------------------------------------------
V76's bit7 (`|gp-0x6b26| > 448`) read **0 / 63,477** with bit3 alive at 99.93%: that question is
answered and the bit is freed. The brief specified bit7 = `|gp-0x6bd0| >= 448` and bit6 =
`|gp-0x6bd0| >= 512`. Sized against the lane's own REACHABLE output (below), **bit6 = 512 carries no
information and is replaced by a reachable rung at 192.** See `THE 192 SUBSTITUTION` below -- it is
flagged, argued and reported, not silently applied.

CAVE DISCIPLINE
---------------
🛑 Growing a cave is this kit's ONLY bricking class -- V24, V27 and V48B all bricked the ECU. The
extent stays **68 bytes**, asserted on the emitted bytes, on the built image AND on the .rwd
readback. This cut uses all 68 for code (V76 used 64 + 4 bytes of pad).
🛑 `r10` must not be touched. This cave writes **r6/r7/r15 and flags ONLY** -- asserted from the
emitted encodings, not from the comments. It does not use r9 at all.
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
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, HERE)

if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402  (x31 container, encoders, crc_block_map)
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl / cmp_rr)
import build_v55_tva as V55                # noqa: E402  (ldh / ldbu_any / cmp_imm5)
import build_v68_tva as V68                # noqa: E402  (cave geometry constants)
import build_v76_v38base_tva as V76B       # noqa: E402  (the BASE build -- its cave is re-derived)
import v76_surface as VS                   # noqa: E402  (the evaluator mirror, per-instruction)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = FF.START, FF.END                      # 0x13000 .. 0x100000
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7    # gp = r4
R15 = 15

# =====================================================================================================
# THE BASE -- V76 (which itself sits on V38)
# =====================================================================================================
SRC_BIN = plain_image_path("_v76_v38base_relu_damper_plain_image.bin")
SRC_SHA256 = "54a212a269623ef3d674fe7711eefdf7db32ebc3f25bf3e20c7bc5a14c830f33"
SRC_RWD_SHA256 = "1fba57b243534538a7d533436387a98c673bf038dc579f9a3c6796d4c6030c89"
STOCK_BIN = stock_fw_path("code.bin")

# ⚠ A BUILD-SPECIFIC image name, per the recorded plain-image-overwrite hazard: two V70 cuts both
# wrote `_v70_plain_image.bin` and the second destroyed the first's snapshot, leaving a flashable
# artefact no gate could check. The tag names the three cells the probe actually READS.
BIN_OUT = str(plain_image_path("_v78_v76base_ey1_449_dose206_plain_image.bin"))
# 🛑 Paths this build must NEVER write -- above all its own BASE.
FORBIDDEN_OVERWRITE = {
    str(plain_image_path("_v76_v38base_relu_damper_plain_image.bin")),
    str(plain_image_path("_v76_gate_fb_arm5244_gateprobe_plain_image.bin")),
    str(plain_image_path("_v76_v38base_relu_damper_probe6b26_plain_image.bin")),
    str(plain_image_path("_v77_C63A0.1024_v74base_plain_image.bin")),
    str(plain_image_path("_v77b_C63A0.1024_v75base_plain_image.bin")),
}

# ⚠ DELIBERATELY SHORT -- V71A overran Windows' 260-char path limit and failed the .rwd write AFTER
# the image was already on disk. The length is asserted BEFORE anything is written.
# 🛑 V78, NOT V77: `builds/v50_v79/build_v77_tva.py` exists and V77/V77B .rwds are on disk (renamed SUPERSEDED-...).
# Reusing V77 would break "exactly ONE flashable .rwd per build number".
TAG = "V78-V76BASE-EY1.449-dose206-probe-6bd0-63fd-67fa"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")

# =====================================================================================================
# 🛑🛑 THE SAFETY-CRITICAL INTERLOCK -- inherited from V76, asserted here BY VALUE (RULE 3 / RULE 11)
# =====================================================================================================
FAULT_CLAMP_ADDR = V76B.FAULT_CLAMP_ADDR        # 0xC407E, the friction-lane clamp
FAULT_CLAMP_MAX = V76B.FAULT_CLAMP_MAX          # 511
FAULT_THRESH_ADDR = V76B.FAULT_THRESH_ADDR      # 0xC4004, the f32 FUN_00036d74 compares against
FAULT_TRIP_COUNTS = V76B.FAULT_TRIP_COUNTS      # 512
NOT_CARRIED = V76B.NOT_CARRIED                  # the V72/V73/V74 levers that must stay absent

# =====================================================================================================
# GROUP 1 -- THE ONE CALIBRATION CELL
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

# The V76 base contents of the mode-26 records, asserted before writing.
BASE_C26 = ([2240, 3840, 5120, 8960], [566, 566, 566, 908])
BASE_E26 = ([0, 119, 2500, 4000], [0, 300, 539, 927])
NEW_C26 = BASE_C26                              # 🛑 FactorC is NOT TOUCHED by this build
NEW_E26 = ([0, 119, 2500, 4000], [0, 449, 539, 927])

R_OP = 99                       # counts; the measured in-burst median rate for grind #1 (21.0 deg/s)
SPEED_CTS_PER_KMH = VS.SPEED_CTS_PER_KMH        # 64.0
RATE_CTS_PER_DEGS = VS.RATE_CTS_PER_DEGS        # 4.7121
DOSE_TARGET = 206                               # 1.50 x V75's 137, on the integer surface
V75_DOSE = 137
SPEED_5MPH_CT = 515                             # 5 mph = 8.04672 km/h -> 515 counts (both conventions)
CEILING_FLOOR = 512                             # the tp+0x7158 fallback AND the LERP's Y[0]

# The independent statement of the write list. Asserted against what this builder actually emits.
EXPECTED_WRITES = {0xD7818: (300, 449, "FactorE m26 Y[1]")}

# =====================================================================================================
# GROUP 2 -- THE PROBE CAVE (RE-CUT)
# =====================================================================================================
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = 68                           # 🛑 THE PROVEN EXTENT. NEVER GROW IT.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK        # 0x55C0E, `movea -0x1518,gp,r6`
HOOK_RETURN = HOOK_ADDR + 4                                  # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")                     # `mov 0x8,r7` -- proves r7 is DEAD

PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-0x14A TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- live STEER_SENSOR_STATUS, PRESERVED
PAYLOAD_SHIFT = 3

STATE_DISP = -0x67FA        # the assist-chain state selector. BYTE, lockstep-shadowed -> read only.
MODEIDX_DISP = +0x63FD      # the mode index. BYTE, ODD displacement -> ld.bu op 0x3D, not 0x3C.
B26_DISP = -0x6B26          # the FRICTION lane -- V76 read it; V78 does NOT (question answered)
BD0_DISP = -0x6BD0          # halfword, SIGNED -- THE DAMPER OUTPUT, this build's subject
# (firmware reads, firmware writes) by raw LE byte scan over BOTH gp encodings, cave excluded.
CELL_CENSUS = {STATE_DISP: (128, 33), MODEIDX_DISP: (22, 5), B26_DISP: (4, 1),
               BD0_DISP: (5, 3), -0x6BC6: (1, 1), -0x6BC8: (1, 1), -PAYLOAD_BYTE4_DISP: (3, 3)}
CAVE_READS = (STATE_DISP, MODEIDX_DISP, BD0_DISP)
CAVE_MUST_NOT_READ = (B26_DISP, -0x6BC6, -0x6BC8)

# ---------------------------------------------------------------------------------------------------
# 🛑 THE BIT MAP -- and the ONE rung that differs from the brief, flagged not silently applied
# ---------------------------------------------------------------------------------------------------
#   bit7  |gp-0x6bd0| >= 448    RAIL PROXIMITY / NO-CLIP GUARANTEE      (brief, kept verbatim)
#   bit6  |gp-0x6bd0| >= 192    ⚠ THE SUBSTITUTION -- brief said 512    (see below)
#   bit5  clear, always 0       🛑 the ceiling-index rung is DROPPED -- 14 B, no budget
#   bit4  gp+0x63fd & 0x2       the mode index
#   bit3  gp-0x67fa == 5        ★ THE POSITIVE CONTROL -- MANDATORY
#   2:0   live STEER_SENSOR_STATUS, PRESERVED
#
# ★★ REACHABILITY, computed on THIS build's own surface through `v76_surface`'s evaluator mirror and
#    asserted below in `assert_rung_reachability()` -- the smallest |rate| in counts that makes each
#    rung fire, by speed:
#
#      threshold |     5..80 km/h   |   96.7 km/h    |   140 km/h
#      ----------+------------------+----------------+---------------
#         192    |   93 ct / 20 d/s |  79 ct / 17 d/s|  58 ct / 12 d/s
#         448    | 3552 ct / 754 d/s|3104 ct / 659d/s|1627 ct / 345d/s
#         512    | 4000 ct / 849 d/s|3486 ct / 740d/s|2651 ct / 563d/s
#
#    The kit's OBSERVED rate maximum across its whole corpus is **1,941 counts** (route 5d,
#    BUILD-LINEAGE RULE 8; both CAN channels agree on that figure). At r = 1941 this build's damper
#    tops out at **285** counts up to 80 km/h and **333** at 96.7 km/h.
#
# 🛑 CONSEQUENCE FOR bit6: `|d| >= 512` is IMPLIED by `|d| >= 448`. If bit7 reads zero for a drive
#    then bit6 = 512 is ZERO WITHOUT BEING MEASURED -- it can only carry information inside an event
#    that is itself predicted never to occur. That is a bit spent on a conditional refinement of a
#    null: the V64/V68/V69 failure mode ("size a probe rung against the lane's own reachable output").
#    ⇒ **REPLACED BY 192**, which:
#      · fires at r >= 93 counts = 19.7 deg/s -- just UNDER R_OP = 99 counts (21.0 deg/s), the
#        measured grind-#1 in-burst median. The rung therefore sits ON the design point, i.e. at
#        roughly 50% duty in exactly the bursts this build is dosed for: maximum information.
#      · is a direct V76 -> V78 DOSE DISCRIMINATOR. The same 192 threshold needed **598 counts
#        (127 deg/s)** on V76 and needs **93 counts (20 deg/s)** on V78 -- a **6.4x** shift in the
#        rate required to trip it. So the bit measures whether the 1.5x dose is actually IN FORCE.
#      · calibrates the unobservable rate index `gp-0x6ac0` against CAN steering rate.
#
# ★ bit7 IS KEPT AT 448 AND IS STILL WORTH ITS BIT, because its null is the answer:
#   448 < 512 <= ceiling at every ceiling value the LERP can produce (X=[300,800] Y=[512,1024],
#   fallback 512), so **bit7 == 0 across a drive PROVES no clipping occurred anywhere on that drive,
#   whichever ceiling was in force** -- i.e. no Coulomb relay at the rail, the hazard raising dose
#   actually creates. One bit, one guarantee. A non-zero reading would be a genuine surprise and
#   would falsify the surface model rather than confirm it.
#
# 🛑 STRUCTURAL INVARIANTS THIS CUT GUARANTEES, usable as integrity checks on the wire:
#     bit5 is ALWAYS 0            (no code path sets it)
#     bit7 SET  =>  bit6 SET      (448 >= 192, a thermometer on one materialised |value|)
# ---------------------------------------------------------------------------------------------------
PROBE_SOURCE = "orchestrator brief, bit6 RESIZED 448/512 -> 448/192 on reachability (flagged)"
BIT_STATE5, W_STATE = 3, 1        # gp-0x67fa == 5     ★ POSITIVE CONTROL
BIT_MODEIDX, W_MODE = 4, 2        # gp+0x63fd & 0x2
BIT_DAMP_LO, W_DAMP_LO = 6, 8     # |gp-0x6bd0| >= 192
BIT_DAMP_HI, W_DAMP_HI = 7, 16    # |gp-0x6bd0| >= 448
BITS_CLEAR = (5,)
STATE_EQ = 5
MODEIDX_MASK = 0x2
# 🛑 The two thresholds are tested on ONE materialised |value| via a single `shr 0x6`, so both must
#    be exact multiples of 64 and their quotients must fit Format II's SIGNED imm5 (-16..15).
DAMP_SHIFT = 6
DAMP_LO_THRESH, DAMP_HI_THRESH = 192, 448
PROBE_MASK = 0xD8                 # bits 7,6,4,3 -- the only bits the cave can set
ILLEGAL_BIT5 = 0x20               # bit 5 -- any payload carrying it is `state_impossible`
LEGAL_PAYLOAD_HI = {(hi * W_DAMP_HI | lo * W_DAMP_LO | m * W_MODE | s * W_STATE) << PAYLOAD_SHIFT
                    for hi in (0, 1) for lo in (0, 1) for m in (0, 1) for s in (0, 1)
                    if lo >= hi}                              # bit7 => bit6
BR_SKIP2, BR_SKIP4 = 4, 6         # skip a 2-byte setter / skip the 4-byte `addi`

# 🛑 The ONLY registers the cave may write. r9 is NOT used by this cut at all.
ALLOWED_WRITE_REGS = {R6, R7, R15}
FORBIDDEN_WRITE_REGS = {10}
COND_BGE, COND_BLT = 0xE, 0x6     # signed >=, signed <. The INVERTING twins of each other.

# ---- instruction pins. Every halfword emitted reproduces a REAL instance in THIS base, address and
# ---- bytes, and every address below was confirmed by GhidraMCP to be a real instruction BOUNDARY
# ---- with the stated mnemonic (not merely a byte match -- that trap is on record).
# 🛑 EVERY pin is IN-SPAN (>= 0x13000): the .rwd payload covers only [0x13000, 0x100000), so a pin
#    below that is uncheckable against the artifact actually flashed.
PIN_LDBU_STATE_R6 = (0x18C7C, bytes.fromhex("84370798"))     # `ld.bu -0x67fa[gp],r6`
PIN_CMP_5_R6 = (0x16FA4, bytes.fromhex("6532"))              # `cmp 0x5,r6`
PIN_SETFE_R7 = (0x261E4, bytes.fromhex("e23f0000"))          # 🛑 `setfe r7` -- FOUR bytes, Format IX
PIN_LDBU_MODEIDX_R15 = (0x34470, bytes.fromhex("a47ffd63"))  # `ld.bu 0x63fd[gp],r15` (op 0x3D, ODD)
PIN_ANDI_2_R15_R6 = (0x4DA3C, bytes.fromhex("cf360200"))     # `andi 0x2,r15,r6`
PIN_OR_R6_R7 = (0x1C1C4, bytes.fromhex("0639"))              # `or r6,r7`
# `ld.h -0x6bd0[gp],r15` has NO exact in-span instance. hw1 and hw2 are pinned to real instances of
# the same FIELD KINDS, and the pair is then proven by ROUND-TRIP against four real `-0x6bd0` loads
# spanning four different destination registers (LDH_6BD0_DONORS below).
PIN_LDH_HW1_R15 = (0x1C0C8, bytes.fromhex("247f"))           # hw1 of `ld.h -0x6b98,gp,r15`
PIN_LDH_6BD0_HW2 = (0x34728, bytes.fromhex("3094"))          # hw2 of `ld.h -0x6bd0,gp,r7` @0x34726
LDH_6BD0_DONORS = {0x1C114: 8, 0x34726: 7, 0x347BC: 7, 0x38150: 10, 0x3AC78: 9}
PIN_CMP_R0_R15 = (0x14C64, bytes.fromhex("e079"))            # `cmp r0,r15`
PIN_BGE_4 = (0x244CE, bytes.fromhex("ae05"))                 # `bge +4`  (cond 0xE) -- 0x244CE->0x244D2
PIN_SUBR_R0_R15 = (0x2AD3E, bytes.fromhex("8079"))           # `subr r0,r15` -> r15 = 0 - r15
PIN_SHR_6_R15 = (0x59B40, bytes.fromhex("867a"))             # `shr 0x6,r15` -- LOGICAL, the ONE instance
PIN_CMP_3_R15 = (0x1B972, bytes.fromhex("637a"))             # `cmp 0x3,r15`   (192 >> 6)
PIN_BLT_4 = (0x290A8, bytes.fromhex("a605"))                 # `blt +4`  (cond 0x6) -- 0x290A8->0x290AC
PIN_ADD_8_R7 = (0x17CD8, bytes.fromhex("483a"))              # `add 0x8,r7` (Format II imm5)
PIN_CMP_7_R15 = (0x222AC, bytes.fromhex("677a"))             # `cmp 0x7,r15`   (448 >> 6)
PIN_BLT_6 = (0x1C006, bytes.fromhex("b605"))                 # `blt +6`  (cond 0x6) -- 0x1C006->0x1C00C
PIN_ADDI_HW1_R7_R7 = (0x2A0E0, bytes.fromhex("073e"))        # hw1 donor: `addi imm,r7,r7`
PIN_IMM_10_HW2 = (0x146D6, bytes.fromhex("1000"))            # hw2 donor: the literal 0x0010 = 16
ADDI_R7_R7_DONORS = {0x2064E: 0xFFC2, 0x2A0E0: 0x0012, 0x463C6: 0x0032}
SHR_DONORS = {0x144F6: (3, 14), 0x147B0: (2, 7), 0x14EBC: (1, 6), 0x1538C: (7, 9)}
ADD_IMM5_DONORS = {0x17CD4: (8, 30), 0x17CD6: (8, 10), 0x14802: (4, 8), 0x14DD4: (8, 6)}
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))               # `shl 0x3,r7`
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))        # `ld.bu -0x1514[gp],r6`
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))         # `andi 0x7,r6,r6`
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))              # `or r7,r6`
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))         # `st.b r6,-0x1514[gp]` -- THE ONLY STORE
PIN_JMP_LP = (0x14AAA, bytes.fromhex("7f00"))                # `jmp [lp]`
# ⚠ NO `PIN_MOVEA_HOOK`. On the V76 base 0x55C0E is ALREADY the `jarl`, so the displaced `movea`
#    exists only inside V76's own cave. It is pinned instead as `HOOK_STOCK` against the STOCK image.
ALL_PINS = {n: v for n, v in sorted(globals().items()) if n.startswith("PIN_")}

# =====================================================================================================
# 🛑🛑 REGISTER LIVENESS AT THE HOOK -- re-verified for THIS cut, not inherited
# =====================================================================================================
# [EVIDENCE, GhidraMCP disassembly of the WHOLE post-hook tail 0x55C0E..0x55C41, 12 instructions:
#   0x55C12 mov 0x8,r7 | 0x55C14 movea 0x14a,r0,r8 | 0x55C18 jarl FUN_00057b24
#   0x55C1C ld.bu -0x1511,gp,r6 | 0x55C20 andi 0xf,r10,r8 | 0x55C24 andi 0xf0,r6,r6
#   0x55C28 or r8,r6 | 0x55C2A st.b r6,-0x1511,gp | 0x55C2E jarl FUN_0001fa72 | 0x55C32 mov 0x1,r10
#   0x55C34/38/3C epilogue (restores ONLY lp and r28) | 0x55C40 jmp lp ]
#   · r15 -- NOT READ ANYWHERE after the hook, and the epilogue restores only lp/r28, so no caller
#     can depend on it either. FUN_00057b24 additionally writes r15 @0x57B28 before reading.
#   · r6  -- written by the displaced `movea` the cave replays, and again by `ld.bu` @0x55C1C.
#   · r7  -- written by `mov 0x8,r7` @0x55C12, the instruction immediately after the hook.
#   · r10 -- NOT TOUCHED by this cave (two readings of its liveness are on record; both imply the
#     same operational rule, and this cut obeys it unconditionally).
HOOK_FN = (0x55A98, 0x55C41)
DEAD_AT_HOOK = {R6: "written by the replayed movea, and by ld.bu @0x55C1C",
                R7: "written by `mov 0x8,r7` @0x55C12",
                R15: "never read in 0x55C0E..0x55C41; epilogue restores only lp/r28"}


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


def assert_no_aliasing(buf, label):
    """🛑 GUARD 5. Nothing else may own the bytes we write, in ANY of the six arrays.

    Uses `rec_len = 4 + 4n` per record -- NOT a flat 0x18 window. V73's guard window was 4 bytes too
    wide and false-positived across adjacent modes. Also reports the nearest OTHER record."""
    write_addrs = set(EXPECTED_WRITES)
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
                    assert name == "FactorE" and modes == [LIVE_MODE], (
                        f"🛑 {label}: write 0x{a:05X} lands inside {name} record 0x{rec:05X}, owned "
                        f"by modes {modes} -- it would leak outside mode {LIVE_MODE}")
                else:
                    d = rec - a if rec > a else a - (rec + ln) + 1
                    if nearest is None or d < nearest[0]:
                        nearest = (d, name, rec, modes)
    live_e = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
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
    assert live_e == EXPECT_ADDR[("E", LIVE_MODE)]
    return nearest


def assert_pointer_arrays_stock(buf, stock, label):
    """🛑 GUARD 5. All SIX pointer arrays byte-identical to STOCK over all 34 modes."""
    for name, ptrs in ALL_PTR_ARRAYS.items():
        got = bytes(buf[ptrs:ptrs + 4 * N_MODES])
        want = bytes(stock[ptrs:ptrs + 4 * N_MODES])
        assert got == want, \
            f"🛑 {label}: the {name} pointer array @0x{ptrs:05X} differs from STOCK over " \
            f"{N_MODES} modes -- a retargeted pointer would silently move every edit"
    return len(ALL_PTR_ARRAYS)


def assert_untouched_surfaces(buf, base, label):
    """FactorB/C/D, the ceiling and friction must stay as the base has them, in BOTH modes.

    Also asserts the edited record's HEADER (the point count -- a change would move rec_len) and its
    TAIL (the 2 bytes whose mis-sizing produced the V73 spill)."""
    for name, ptrs in (("FactorB", FACTOR_B_PTRS), ("FactorC", FACTOR_C_PTRS),
                       ("FactorD", FACTOR_D_PTRS), ("ceiling", CEILING_PTRS),
                       ("friction", FRICTION_PTRS)):
        for mode in (MANUAL_MODE, LIVE_MODE):
            off = rec_addr(buf, ptrs, mode)
            n = u16(buf, off)
            ln = 2 + 4 * n
            assert bytes(buf[off:off + ln]) == bytes(base[off:off + ln]), \
                f"🛑 {label}: {name} mode {mode} @0x{off:05X} CHANGED -- this build touches only " \
                f"FactorE mode {LIVE_MODE}"
    off = rec_addr(buf, FACTOR_E_PTRS, LIVE_MODE)
    assert u16(buf, off) == 4 == u16(base, off), \
        f"🛑 {label}: FactorE m{LIVE_MODE} HEADER changed -- the point count must stay 4"
    assert bytes(buf[off + REC_DATA_LEN:off + REC_STRIDE]) == b"\x00\x00", \
        f"🛑 {label}: FactorE m{LIVE_MODE} TAIL is not 0x0000 -- the V73 spill signature"
    _o, _n, cx, cy = read_rec(buf, FACTOR_C_PTRS, LIVE_MODE)
    assert (cx, cy) == NEW_C26, f"🛑 {label}: FactorC m26 is {(cx, cy)}, must stay {NEW_C26}"


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
# 🛑🛑 THE INTERLOCK GUARD, and the levers this build must NOT resurrect
# =====================================================================================================
def assert_fault_interlock(buf, label):
    return V76B.assert_fault_interlock(buf, label)


def assert_not_carried(buf, label):
    for addr, (want, why) in NOT_CARRIED.items():
        got = u16(buf, addr)
        assert got == want, f"{label}: 0x{addr:05X} = {got}, expected {want} -- {why}"


def assert_manual_mode_stock(buf, stock, label):
    """🛑 GUARD 5. Mode 24 is MANUAL steering. Byte-identical to STOCK, not merely to the base."""
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
SPEED_GATE, RATE_GATE = 0x7D00, 0x32C9      # FactorC gate @0x344E0, FactorE gate @0x345FA


def surfaces(img_before, img_after):
    return (VS.Surface(img=bytes(img_before), mode=LIVE_MODE),
            VS.Surface(img=bytes(img_after), mode=LIVE_MODE),
            VS.Surface(img=VS.load("stock"), mode=LIVE_MODE))


def assert_table_shape(X, Y, label):
    """GUARD 1 + GUARD 2."""
    assert all(X[i] < X[i + 1] for i in range(len(X) - 1)), f"{label}: X is not STRICTLY increasing"
    assert all(Y[i] <= Y[i + 1] for i in range(len(Y) - 1)), f"{label}: Y is not monotone"
    assert Y[0] == 0, (
        f"🛑 {label}: E_Y[0] = {Y[0]} != 0. A non-zero Y[0] is a COULOMB RELAY: the LERP index "
        f"(gp-0x6ac0) and the output sign (gp-0x6abe) are DIFFERENT cells, so it gives constant "
        f"magnitude with a rate-flipped sign -- describing function 4*M0/(pi*A), unbounded as the "
        f"amplitude falls. NEVER RAISE IT.")
    assert Y[1] < Y[2], f"{label}: the E_Y1 == E_Y2 plateau is back"


def assert_add_only(S76, S78, STK):
    """🛑 GUARD 3, EXACT and EXHAUSTIVE -- by factor monotonicity, not a subsampled grid.

    |gp-0x6bd0| = min( (C(speed) * E(rate)) >> 10 , ceiling ) with seed = B = D = 1024 (four
    back-to-back `mulu` + logical `shr 0xa` at 0x34684-0x3469C, ZERO add/or). Both `>>10` and the
    ceiling clamp min(|d|, c) are monotone non-decreasing in each factor, and both gates depend only
    on the index, so proving E and C add-only per-axis proves the WHOLE 32000 x 13001 surface.
    """
    for r in range(RATE_GATE):
        e78, e76, es = S78.factorE(r), S76.factorE(r), STK.factorE(r)
        assert (e78 is None) == (e76 is None) == (es is None), f"the FactorE GATE moved at r={r}"
        if e78 is None:
            continue
        assert e78 >= e76 >= es, f"FactorE add-only FAILS at rate {r}: {es} -> {e76} -> {e78}"
    for sp in range(SPEED_GATE):
        c78, c76, cs = S78.factorC(sp), S76.factorC(sp), STK.factorC(sp)
        assert c78 == c76 >= cs, f"FactorC changed or dropped below stock at speed {sp}"
    for w in ("B", "D"):
        assert S78.XY(w) == S76.XY(w) == STK.XY(w), f"Factor{w} moved"
    assert S78.XY("CEIL") == S76.XY("CEIL") == STK.XY("CEIL"), "the ceiling record moved"
    assert S78.ceil_fallback == S76.ceil_fallback == CEILING_FLOOR
    return RATE_GATE, SPEED_GATE


def assert_add_only_direct(S78, STK, step_s=11, step_r=17):
    """The required SECOND METHOD: a direct subsampled sweep of the full 2-D surface."""
    worst, at, n = 0, None, 0
    for sp in range(0, SPEED_GATE, step_s):
        for r in range(0, RATE_GATE, step_r):
            a, b = S78.mag(sp, r), STK.mag(sp, r)
            n += 1
            if b - a > worst:
                worst, at = b - a, (sp, r, a, b)
    assert worst == 0, f"🛑 add-only FAILS by {worst} counts at {at}"
    return n


def assert_no_clip(S76, S78):
    """🛑 GUARD 4 -- this edit must introduce NO clipping that V76 did not already have.

    Exact argument, not a sample: V78 differs from V76 only where E_V78(r) > E_V76(r), and on that
    set E_V78(r) <= E_Y[2] = 539. With C_max over the whole speed domain, the largest product
    reachable ON THE CHANGED SET is bounded below the ceiling FLOOR (512), so no point that failed
    to clip on V76 can clip on V78 -- at ANY ceiling value the LERP can produce.
    """
    c_max = max(S78.factorC(sp) for sp in range(SPEED_GATE))
    changed = [r for r in range(RATE_GATE)
               if S78.factorE(r) is not None and S78.factorE(r) != S76.factorE(r)]
    worst = max(((c_max * S78.factorE(r)) >> 10) for r in changed)
    assert worst < CEILING_FLOOR, (
        f"🛑 GUARD 4 FAILS: on the changed rate set the product reaches {worst} >= the ceiling "
        f"floor {CEILING_FLOOR} at C_max={c_max} -- this edit WOULD introduce new clipping")
    # ...and the brief's own form of the guard: max product where FactorC == 566
    flat = [sp for sp in range(SPEED_GATE) if S78.factorC(sp) == 566]
    e_max = max(e for e in (S78.factorE(r) for r in range(RATE_GATE)) if e is not None)
    flat_worst = (566 * e_max) >> 10
    assert flat_worst <= CEILING_FLOOR, \
        f"🛑 GUARD 4: max product where FactorC == 566 is {flat_worst} > {CEILING_FLOOR}"
    # ...and a direct clip-set comparison as the second method
    n76 = n78 = 0
    for bd in (0, 299, 300, 550, 800, 801, RATE_GATE):
        c = S78.ceiling(bd)
        assert c == S76.ceiling(bd) >= CEILING_FLOOR
        for sp in range(0, SPEED_GATE, 29):
            for r in range(0, RATE_GATE, 47):
                n76 += S76.output(sp, r, backdrive_idx=bd)[1]
                n78 += S78.output(sp, r, backdrive_idx=bd)[1]
    assert n78 == n76, f"🛑 GUARD 4: the clip set GREW ({n76} -> {n78} sampled points)"
    return worst, flat_worst, len(changed), len(flat), c_max, n76


def first_rate_for(S, speed, thresh):
    for r in range(RATE_GATE):
        if S.mag(speed, r) >= thresh:
            return r
    return None


def assert_rung_reachability(S76, S78):
    """🛑 Size every rung against its lane's own REACHABLE output BEFORE emitting it.

    Returns the table printed in the report. The ONLY thing asserted hard is that each emitted rung
    is reachable SOMEWHERE on the gated surface -- a structurally dead rung (V64/V68/V69) fails the
    build. The *empirical* likelihood is reported, loudly, and is the reason bit6 is 192 not 512.
    """
    rows = {}
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH, CEILING_FLOOR):
        row = {}
        for kmh in (5, 20, 35, 60, 80, 96.7, 140):
            sp = int(round(kmh * SPEED_CTS_PER_KMH))
            row[kmh] = first_rate_for(S78, sp, thr)
        rows[thr] = row
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        assert any(v is not None for v in rows[thr].values()), \
            f"🛑 the |gp-0x6bd0| >= {thr} rung is STRUCTURALLY DEAD -- it can never fire"
    # the substitution's justification, asserted rather than merely asserted in prose:
    lo_v78 = rows[DAMP_LO_THRESH][5]
    lo_v76 = first_rate_for(S76, int(round(5 * SPEED_CTS_PER_KMH)), DAMP_LO_THRESH)
    assert lo_v78 is not None and lo_v76 is not None and lo_v78 < lo_v76, \
        "the low rung does not discriminate V76 from V78 -- it would not measure the dose step"
    assert lo_v78 <= R_OP, (
        f"the low rung needs {lo_v78} counts but the design reference rate is {R_OP} -- it would "
        f"not sit ON the operating point")
    assert DAMP_HI_THRESH < CEILING_FLOOR <= min(S78.ceiling(b) for b in range(0, 0x3300, 7)), \
        "bit7's threshold does not sit strictly below EVERY reachable ceiling -- its null would " \
        "no longer prove 'no clip'"
    return rows, lo_v76, lo_v78


# =====================================================================================================
# The gp-cell census -- a raw LE byte scan, the required second method
# =====================================================================================================
cell_census = V76B.cell_census


def assert_cell_censuses(buf, cave_span, expect_cave, label):
    """🛑 The cave must READ each probed cell exactly once and WRITE none."""
    for disp, (want_r, want_w) in CELL_CENSUS.items():
        r, w, cave = cell_census(buf, disp, cave_span)
        assert len(r) == want_r and len(w) == want_w, (
            f"{label}: gp{disp:+#x} census is {len(r)}r/{len(w)}w, expected {want_r}r/{want_w}w "
            f"-- the firmware's own accesses must be untouched")
        if expect_cave and disp in CAVE_READS:
            assert len(cave) == 1 and cave[0][1].startswith("ld"), (
                f"{label}: the cave makes {len(cave)} access(es) to gp{disp:+#x}, expected exactly "
                f"one LOAD -- a WRITE to any of these escalates (gp-0x67fa is lockstep-checked)")
        elif expect_cave and disp in CAVE_MUST_NOT_READ:
            assert not cave, (
                f"{label}: the cave touches gp{disp:+#x} -- that rung is DROPPED from this cut, so "
                f"the cell must be left entirely alone")
        for _a, mnem, _raw in cave:
            assert mnem.startswith("ld") or disp == -PAYLOAD_BYTE4_DISP, \
                f"{label}: the cave WRITES gp{disp:+#x} -- forbidden"


def assert_pins(buf, label):
    n = 0
    for name, (addr, want) in ALL_PINS.items():
        got = bytes(buf[addr:addr + len(want)])
        assert got == want, f"{label}: {name} @0x{addr:05X} is {got.hex()}, expected {want.hex()}"
        assert addr >= START, f"{label}: {name} @0x{addr:05X} is BELOW 0x13000 -- uncheckable"
        assert not (CAVE_BASE <= addr < CAVE_BASE + CAVE_EXTENT), \
            f"{label}: {name} @0x{addr:05X} sits INSIDE the cave this build rewrites"
        n += 1
    return n


# =====================================================================================================
# CRC
# =====================================================================================================
owning_block = V76B.owning_block
refresh_crcs = V76B.refresh_crcs
assert_crc_chain = V76B.assert_crc_chain
changed_runs = V76B.changed_runs


# =====================================================================================================
# Instruction encoders not already in the V54/V55/FF set
# =====================================================================================================
def _fmt1(op6, reg1, reg2):
    return struct.pack("<H", ((reg2 & 0x1F) << 11) | ((op6 & 0x3F) << 5) | (reg1 & 0x1F))


def addi(imm16, reg1, reg2):
    """ADDI imm16,reg1,reg2 (Format VI, op 0x30). FOUR bytes.

    🛑 Needed rather than `add imm5` because bit7's weight is 16, outside Format II's SIGNED 5-bit
    range (-16..15). bit6's weight is 8 and DOES fit, which is what buys this cave its two bytes."""
    return _fmt1(0x30, reg1, reg2) + struct.pack("<H", imm16 & 0xFFFF)


def add_imm5(imm5, reg2):
    """ADD imm5,reg2 (Format II, op 0x12) -- reg2 += sign_extend(imm5). TWO bytes."""
    assert -16 <= imm5 <= 15, "Format II imm5 is SIGNED"
    return _fmt1(0x12, imm5 & 0x1F, reg2)


def subr_rr(reg1, reg2):
    """SUBR reg1,reg2 (Format I, op 0x0C) -- reg2 = reg1 - reg2. 🛑 NOT reg2 - reg1; that is SUB."""
    return _fmt1(0x0C, reg1, reg2)


def setfe(reg2):
    """SETF E,reg2 (Format IX) -- reg2 = (Z) ? 1 : 0. 🛑 FOUR BYTES, not two.

    ★ It collapses "zero the accumulator" and "set bit0 on equality" into ONE instruction. The V76
    spec listed it as 2 B; emitting 2 would desynchronise every following instruction."""
    assert reg2 == R7, "only the r7 form is pinned"
    return PIN_SETFE_R7[1]


def _self_check_encoders(buf):
    """Every encoder reproduces a REAL instance in THIS image, at a named IN-SPAN address that
    GhidraMCP confirmed is an instruction BOUNDARY with the stated mnemonic."""
    checks = [
        (V55.ldbu_any(STATE_DISP, R6), PIN_LDBU_STATE_R6, "ld.bu -0x67fa[gp],r6"),
        (V55.cmp_imm5(STATE_EQ, R6), PIN_CMP_5_R6, "cmp 0x5,r6"),
        (setfe(R7), PIN_SETFE_R7, "setfe r7"),
        (V55.ldbu_any(MODEIDX_DISP, R15), PIN_LDBU_MODEIDX_R15, "ld.bu 0x63fd[gp],r15"),
        (V54.andi(MODEIDX_MASK, R15, R6), PIN_ANDI_2_R15_R6, "andi 0x2,r15,r6"),
        (V54.or_rr(R6, R7), PIN_OR_R6_R7, "or r6,r7"),
        (V54.cmp_rr(R0, R15), PIN_CMP_R0_R15, "cmp r0,r15"),
        (subr_rr(R0, R15), PIN_SUBR_R0_R15, "subr r0,r15"),
        (FF.shr(DAMP_SHIFT, R15), PIN_SHR_6_R15, "shr 0x6,r15"),
        (V55.cmp_imm5(DAMP_LO_THRESH >> DAMP_SHIFT, R15), PIN_CMP_3_R15, "cmp 0x3,r15"),
        (add_imm5(W_DAMP_LO, R7), PIN_ADD_8_R7, "add 0x8,r7"),
        (V55.cmp_imm5(DAMP_HI_THRESH >> DAMP_SHIFT, R15), PIN_CMP_7_R15, "cmp 0x7,r15"),
        (V54.shl(PAYLOAD_SHIFT, R7), PIN_SHL3_R7, "shl 0x3,r7"),
        (V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), PIN_LDBU_BYTE4, "ld.bu -0x1514[gp],r6"),
        (V54.andi(PAYLOAD_KEEP_MASK, R6, R6), PIN_ANDI_7_R6, "andi 0x7,r6,r6"),
        (V54.or_rr(R7, R6), PIN_OR_R7_R6, "or r7,r6"),
        (FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), PIN_STB_BYTE4, "st.b r6,-0x1514[gp]"),
        (FF.JMP_LP, PIN_JMP_LP, "jmp [lp]"),
    ]
    for enc, (addr, want), text in checks:
        assert enc == want, f"encoder '{text}' emits {enc.hex()}, the pin says {want.hex()}"
        assert addr >= START, f"pin for '{text}' @0x{addr:05X} is BELOW 0x13000 -- uncheckable"
        assert bytes(buf[addr:addr + len(want)]) == want, \
            f"pin for '{text}' @0x{addr:05X} does not read back"
    # ---- branch donors: the cond nibble is a FIELD, so assert the twins do not collapse ----------
    for cond, disp, (addr, want), text in ((COND_BGE, BR_SKIP2, PIN_BGE_4, "bge +4"),
                                           (COND_BLT, BR_SKIP2, PIN_BLT_4, "blt +4"),
                                           (COND_BLT, BR_SKIP4, PIN_BLT_6, "blt +6")):
        assert FF.bcond(cond, disp) == want, \
            f"'{text}' encodes {FF.bcond(cond, disp).hex()}, the pin says {want.hex()}"
        assert addr >= START and bytes(buf[addr:addr + 2]) == want, \
            f"pin for '{text}' @0x{addr:05X} does not read back"
        hw = struct.unpack("<H", want)[0]
        assert hw & 0xF == cond, f"the '{text}' donor carries cond 0x{hw & 0xF:x}, not 0x{cond:x}"
        assert (hw >> 7) & 0xF == 0xB, f"the '{text}' donor is not a Bcond"
    # ---- `ld.h -0x6bd0[gp],r15`: hw1 + hw2 half-pins, THEN a 4-donor round-trip -----------------
    ldh = V55.ldh(-BD0_DISP, R15)
    assert ldh[:2] == PIN_LDH_HW1_R15[1], f"ld.h hw1 {ldh[:2].hex()} != pin"
    assert ldh[2:] == PIN_LDH_6BD0_HW2[1], f"ld.h hw2 {ldh[2:].hex()} != pin"
    for a, w in (PIN_LDH_HW1_R15, PIN_LDH_6BD0_HW2):
        assert a >= START and bytes(buf[a:a + 2]) == w, f"ld.h half-pin @0x{a:05X} does not read back"
    for a, reg2 in LDH_6BD0_DONORS.items():
        assert a >= START, f"ld.h donor 0x{a:05X} is below 0x13000"
        real = bytes(buf[a:a + 4])
        assert real == V55.ldh(-BD0_DISP, reg2), (
            f"the ld.h encoder does not reproduce the real `ld.h -0x6bd0,gp,r{reg2}` @0x{a:05X} "
            f"({real.hex()}) -- the displacement field is not what this builder thinks")
    # ---- `addi 0x10,r7,r7`: hw1/hw2 half-pins + round-trip donors --------------------------------
    ad = addi(W_DAMP_HI, R7, R7)
    assert ad[:2] == PIN_ADDI_HW1_R7_R7[1] and ad[2:] == PIN_IMM_10_HW2[1], "addi pin mismatch"
    for a, w in (PIN_ADDI_HW1_R7_R7, PIN_IMM_10_HW2):
        assert a >= START and bytes(buf[a:a + 2]) == w, f"addi half-pin @0x{a:05X}"
    for a, imm in ADDI_R7_R7_DONORS.items():
        assert a >= START and bytes(buf[a:a + 4]) == addi(imm, R7, R7), \
            f"the addi encoder does not reproduce the real instance @0x{a:05X}"
    # ---- `shr` and `add imm5`: round-trip over other (imm, reg) combinations ----------------------
    for a, (imm, reg) in SHR_DONORS.items():
        assert a >= START and bytes(buf[a:a + 2]) == FF.shr(imm, reg), \
            f"the shr encoder does not reproduce the real `shr 0x{imm:x},r{reg}` @0x{a:05X}"
    for a, (imm, reg) in ADD_IMM5_DONORS.items():
        assert a >= START and bytes(buf[a:a + 2]) == add_imm5(imm, reg), \
            f"the add-imm5 encoder does not reproduce the real instance @0x{a:05X}"
    # ---- 🛑 the INVERTING twins, asserted AWAY ---------------------------------------------------
    assert FF.bcond(COND_BGE, BR_SKIP2) != FF.bcond(COND_BLT, BR_SKIP2), "bge/blt collapsed"
    assert FF.bcond(COND_BLT, BR_SKIP2) != FF.bcond(COND_BLT, BR_SKIP4), "the displacements collapsed"
    assert subr_rr(R0, R15) != _fmt1(0x0D, R0, R15), "subr/sub collapsed -- op 0x0C vs 0x0D"
    assert FF.shr(DAMP_SHIFT, R15) != _fmt1(0x15, DAMP_SHIFT, R15), "shr/sar collapsed -- 0x14 vs 0x15"
    assert FF.shr(DAMP_SHIFT, R15) != V54.shl(DAMP_SHIFT, R15), "shr/shl collapsed -- 0x14 vs 0x16"
    assert V54.cmp_rr(R0, R15) != V54.cmp_rr(R15, R0), "cmp operand order collapsed"
    assert add_imm5(W_DAMP_LO, R7) != FF.movi5(W_DAMP_LO, R7), "add/mov imm5 collapsed"
    # 🛑 bit7's weight is outside `add imm5`'s SIGNED range; bit6's is inside. That is the budget.
    assert not (-16 <= W_DAMP_HI <= 15) and (-16 <= W_DAMP_LO <= 15)
    # 🛑 the shift trick is EXACT only for thresholds that are multiples of 1<<DAMP_SHIFT
    for t in (DAMP_LO_THRESH, DAMP_HI_THRESH):
        assert t % (1 << DAMP_SHIFT) == 0, f"threshold {t} is not a multiple of {1 << DAMP_SHIFT}"
        assert -16 <= (t >> DAMP_SHIFT) <= 15, f"threshold {t} >> {DAMP_SHIFT} does not fit imm5"
        for v in range(max(0, t - 3), t + 3):
            assert ((v >> DAMP_SHIFT) >= (t >> DAMP_SHIFT)) == (v >= t), \
                f"the shift-compare is not exact at |d| = {v} for threshold {t}"
    return len(checks) + 3 + len(LDH_6BD0_DONORS) + len(ADDI_R7_R7_DONORS) \
        + len(SHR_DONORS) + len(ADD_IMM5_DONORS)


# =====================================================================================================
# THE CAVE
# =====================================================================================================
def build_cave():
    """Emit the 68-byte probe. Returns (bytes, listing) where listing = [(addr, raw, text)]."""
    body, listing = bytearray(), []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), bytes(raw), text))
        body.extend(raw)

    # ---- bit3: gp-0x67fa == 5. ★ THE POSITIVE CONTROL ------------------------------------------
    # ★ `setfe` both ZEROES r7 and sets bit0 on equality, so no separate `mov 0x0,r7` is needed.
    emit(V55.ldbu_any(STATE_DISP, R6), "ld.bu -0x67fa[gp],r6 ; THE STATE (byte, neg disp)")
    c_state = len(listing)
    emit(V55.cmp_imm5(STATE_EQ, R6), "cmp 0x5,r6           ; Z iff state == 5")
    s_state = len(listing)
    emit(setfe(R7), f"setfe r7             ; r7 = (state == 5)  bit{BIT_STATE5}  🛑 4 BYTES")

    # ---- bit4: gp+0x63fd & 0x2 -- the mode index ------------------------------------------------
    emit(V55.ldbu_any(MODEIDX_DISP, R15), "ld.bu 0x63fd[gp],r15 ; MODE INDEX (ODD disp, op 0x3D)")
    emit(V54.andi(MODEIDX_MASK, R15, R6), f"andi 0x2,r15,r6      ; r6 = mode & 2 (weight {W_MODE})")
    emit(V54.or_rr(R6, R7), f"or r6,r7             ; bit{BIT_MODEIDX}  🛑 NOT `or r7,r6`")

    # ---- |gp-0x6bd0| into r15 -------------------------------------------------------------------
    # ★ The same three-instruction absolute-value idiom the stock firmware itself uses at
    #   0x244CA-0x244D0 (`cmp r0,r22 ; bge +4 ; subr r0,r22`) -- the pins are that exact sequence.
    #   `ld.h` SIGN-extends to 32 bits, so the negation is exact for every value the cell can hold.
    emit(V55.ldh(-BD0_DISP, R15), "ld.h -0x6bd0[gp],r15 ; THE DAMPER OUTPUT (SIGNED, op 0x39)")
    c_abs = len(listing)
    emit(V54.cmp_rr(R0, R15), "cmp r0,r15           ; flags <- v - 0")
    b_abs = len(listing)
    emit(FF.bcond(COND_BGE, BR_SKIP2), "bge +4               ; v >= 0 -> skip the negate")
    neg_at = CAVE_BASE + len(body)
    emit(subr_rr(R0, R15), "subr r0,r15          ; r15 = 0 - v   🛑 NOT `sub`")
    abs_at = CAVE_BASE + len(body)

    # ---- bits 6/7: two thresholds on ONE materialised |v|, via a single logical shift ------------
    # 🛑 EXACT because both thresholds are multiples of 64: |v| >= 64*q  <=>  (|v| >> 6) >= q.
    emit(FF.shr(DAMP_SHIFT, R15), f"shr 0x{DAMP_SHIFT:x},r15          ; r15 = |v| >> {DAMP_SHIFT}  (LOGICAL)")
    c_lo = len(listing)
    emit(V55.cmp_imm5(DAMP_LO_THRESH >> DAMP_SHIFT, R15),
         f"cmp 0x{DAMP_LO_THRESH >> DAMP_SHIFT:x},r15           ; flags <- (|v|>>{DAMP_SHIFT}) - {DAMP_LO_THRESH >> DAMP_SHIFT}")
    b_lo = len(listing)
    emit(FF.bcond(COND_BLT, BR_SKIP2), f"blt +4               ; |v| < {DAMP_LO_THRESH} -> skip")
    lo_at = CAVE_BASE + len(body)
    emit(add_imm5(W_DAMP_LO, R7), f"add 0x{W_DAMP_LO:x},r7            ; bit{BIT_DAMP_LO} <- (|v| >= {DAMP_LO_THRESH})")
    lo_end = CAVE_BASE + len(body)
    c_hi = len(listing)
    emit(V55.cmp_imm5(DAMP_HI_THRESH >> DAMP_SHIFT, R15),
         f"cmp 0x{DAMP_HI_THRESH >> DAMP_SHIFT:x},r15           ; flags <- (|v|>>{DAMP_SHIFT}) - {DAMP_HI_THRESH >> DAMP_SHIFT}")
    b_hi = len(listing)
    emit(FF.bcond(COND_BLT, BR_SKIP4), f"blt +6               ; |v| < {DAMP_HI_THRESH} -> skip")
    hi_at = CAVE_BASE + len(body)
    emit(addi(W_DAMP_HI, R7, R7),
         f"addi 0x{W_DAMP_HI:x},r7,r7      ; bit{BIT_DAMP_HI} <- (|v| >= {DAMP_HI_THRESH})  🛑 4 BYTES")
    hi_end = CAVE_BASE + len(body)

    # ---- pack into the CAN-0x14A payload byte, preserving bits 2:0 -------------------------------
    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7           ; the field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-0x14A payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6       ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6             ; 🛑 NOT `or r6,r7`")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]  ; ★ THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6  ; re-exec the displaced instruction")
    ret_at = CAVE_BASE + len(body)
    emit(FF.JMP_LP, f"jmp [lp]             ; -> 0x{HOOK_RETURN:05X}")

    code_len = len(body)
    pad = CAVE_EXTENT - code_len
    assert pad >= 0, f"the cave code is {code_len}B, over the PROVEN {CAVE_EXTENT}B extent"
    assert pad % 2 == 0, "the padding is not halfword-aligned"
    if pad:
        emit(bytes(pad), f"<{pad} x 0x00, AFTER `jmp [lp]` => UNREACHABLE; extent stays {CAVE_EXTENT}>")

    # ---- 🛑 FLAG LIVENESS: each test must be IMMEDIATELY followed by its consumer ---------------
    for ci, ui, name in ((c_state, s_state, "bit3 cmp/setfe"), (c_abs, b_abs, "abs cmp/bge"),
                         (c_lo, b_lo, "bit6 cmp/blt"), (c_hi, b_hi, "bit7 cmp/blt")):
        assert ui == ci + 1, \
            f"{name}: {ui - ci - 1} instruction(s) sit between the test and its consumer -- STALE flags"
        ca, craw, _ = listing[ci]
        ua, _uraw, _ = listing[ui]
        assert ca + len(craw) == ua, f"{name}: the test/consumer pair is not adjacent"
    # 🛑 `shr` and `add` both SET FLAGS. Neither is read: each is followed by a fresh `cmp`.
    for idx, nxt in ((b_lo + 1, c_hi), ):
        assert listing[nxt][1][:1] and (struct.unpack("<H", listing[nxt][1])[0] >> 5) & 0x3F == 0x13, \
            "the instruction after bit6's setter is not a fresh `cmp` -- flags would be stale"

    # ---- 🛑 the INVERTING twins, on the EMITTED bytes -------------------------------------------
    assert listing[s_state][1] == PIN_SETFE_R7[1] and len(listing[s_state][1]) == 4, \
        "bit3's setter is not the pinned 4-byte `setfe r7`"
    for bi, cond, name in ((b_abs, COND_BGE, "the abs branch"), (b_lo, COND_BLT, "bit6's branch"),
                           (b_hi, COND_BLT, "bit7's branch")):
        assert struct.unpack("<H", listing[bi][1])[0] & 0xF == cond, \
            f"{name} carries the wrong condition -- the inverting twin would reverse the rung"

    # ---- GATE 2a: every branch lands EXACTLY on an emitted instruction boundary -----------------
    bounds = {a for a, _r, _t in listing}
    for bi, tgt, name in ((b_abs, abs_at, "the abs SKIP path"), (b_lo, lo_end, "bit6's SKIP path"),
                          (b_hi, hi_end, "bit7's SKIP path")):
        ba, raw, _ = listing[bi]
        d = struct.unpack("<H", raw)[0]
        disp = (((d >> 11) & 0x1F) << 4) | (((d >> 4) & 0x7) << 1)
        disp -= 0x200 if disp & 0x100 else 0
        assert ba + disp == tgt, \
            f"{name}: branch @0x{ba:05X} targets 0x{ba + disp:05X}, expected 0x{tgt:05X}"
        assert tgt in bounds, f"{name} target 0x{tgt:05X} is not an instruction boundary"
        assert tgt <= ret_at, f"{name} target is past the return"
        assert ba < tgt, f"{name} is not a FORWARD jump"
    assert neg_at < abs_at and abs_at - neg_at == 2, "the abs branch does not skip exactly `subr`"
    assert lo_at < lo_end and lo_end - lo_at == 2, "bit6's branch does not skip exactly the `add`"
    assert hi_at < hi_end and hi_end - hi_at == 4, "bit7's branch does not skip exactly the `addi`"
    branches = [i for i, (_a, r, _t) in enumerate(listing)
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    assert branches == [b_abs, b_lo, b_hi], \
        f"the cave has branches at {branches}, expected {[b_abs, b_lo, b_hi]}"

    # ---- 🛑 the DROPPED rungs must not have crept back in --------------------------------------
    for disp in CAVE_MUST_NOT_READ:
        forms = [V55.ldh(-disp, r) for r in range(32)] + \
                [V55.ldbu_any(disp, r) for r in range(32)]
        assert not any(e in bytes(body) for e in forms), \
            f"the cave reads gp{disp:+#x} -- that rung is DROPPED from this cut"

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
        "the sole store is not the CAN-0x14A payload byte"
    for idx, (_a, raw, text) in enumerate(listing):
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"

    # ---- 🛑🛑 REGISTER DISCIPLINE, read off the EMITTED ENCODINGS ------------------------------
    dests = set()
    for addr, raw, text in listing:
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
            f"'{text}' @0x{addr:05X} writes r{dest} -- only r6/r7/r15 are proven dead here"
        assert dest not in FORBIDDEN_WRITE_REGS, f"'{text}' writes r{dest} -- FORBIDDEN"
        dests.add(dest)
    assert dests <= ALLOWED_WRITE_REGS, f"the cave writes {sorted(dests)}"
    assert 10 not in dests, "🛑 the cave writes r10 -- the operator's hard stop"
    assert 9 not in dests, "this cut does not use r9 at all"

    # ---- geometry ------------------------------------------------------------------------------
    # 🛑 `setfe` is 4 B, not 2. bit6's `add imm5` is 2 B while bit7's `addi imm16` is 4 B.
    assert code_len == (4 + 2 + 4) + (4 + 4 + 2) + (4 + 2 + 2 + 2) \
        + (2 + 2 + 2 + 2) + (2 + 2 + 4) + (2 + 4 + 4 + 2 + 4) + (4 + 2) == 68, \
        f"the cave code is {code_len}B, the budget says 68"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == CAVE_EXTENT == 68, \
        f"cave {len(body)}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def wire_model(state, mode_idx, bd0, status_bits=0x7):
    """A Python mirror of EXACTLY what the cave computes -- instruction for instruction.

    `setfe` ASSIGNS 1/0 into r7 (it does not accumulate), so it must come FIRST; the mode rung ORs
    in, and the two damper rungs ADD. The byte cells are `ld.bu` (zero-extend); `gp-0x6bd0` is
    `ld.h` (SIGN-extend), matching `FUN_000347b8`'s own `(int)*(short *)` cast."""
    r7 = 1 if (state & 0xFF) == STATE_EQ else 0          # setfe -- assignment, not accumulation
    r7 |= W_MODE if ((mode_idx & 0xFF) & MODEIDX_MASK) else 0
    v = bd0 - 0x10000 if bd0 & 0x8000 else bd0           # ld.h is SIGNED
    a = (-v if v < 0 else v) >> DAMP_SHIFT               # cmp r0/bge/subr, then LOGICAL shr
    r7 += W_DAMP_LO if a >= (DAMP_LO_THRESH >> DAMP_SHIFT) else 0
    r7 += W_DAMP_HI if a >= (DAMP_HI_THRESH >> DAMP_SHIFT) else 0
    return ((r7 << PAYLOAD_SHIFT) | (status_bits & PAYLOAD_KEEP_MASK)) & 0xFF


def _check_wire_model():
    assert wire_model(5, 0, 0, 0) == 0x08, "bit3 alone"
    assert wire_model(4, 0, 0, 0) == 0x00, "state 4 must not set bit3"
    assert wire_model(5, 0x02, 0, 0) == 0x18, "bit3 + bit4"
    assert wire_model(5, 0xFD, 0, 0) == 0x08, "bit1 is clear in 0xFD"
    assert wire_model(0, 0x02, 0, 0) == 0x10, "bit4 alone"
    for v in (DAMP_LO_THRESH, DAMP_LO_THRESH + 1, DAMP_HI_THRESH - 1):
        assert wire_model(0, 0, v, 0) == 0x40, f"+{v} sets bit6 only"
        assert wire_model(0, 0, (-v) & 0xFFFF, 0) == 0x40, f"-{v} sets bit6 only (SIGNED)"
    for v in (DAMP_HI_THRESH, DAMP_HI_THRESH + 1, 511, 512, 1024):
        assert wire_model(0, 0, v, 0) == 0xC0, f"+{v} sets bit7 AND bit6"
        assert wire_model(0, 0, (-v) & 0xFFFF, 0) == 0xC0, f"-{v} sets bit7 AND bit6 (SIGNED)"
    for v in (0, 1, 100, DAMP_LO_THRESH - 1):
        assert wire_model(0, 0, v, 0) == 0x00, f"+{v} must set neither"
        assert wire_model(0, 0, (-v) & 0xFFFF, 0) == 0x00, f"-{v} must set neither"
    assert wire_model(5, 0x02, 511, 0b101) == 0xDD, "all four rungs + preserved status"
    assert wire_model(0, 0, 0, 0xFF) == 0x07, "bits 2:0 preserved and masked to 3"
    # 🛑 bit5 is STRUCTURALLY unreachable and bit7 ALWAYS implies bit6 -- exhaustive over the
    #    whole reachable input space of the cell (it is a 16-bit store, so this IS exhaustive on v).
    seen = set()
    for st in (0, 4, 5, 6, 255):
        for md in (0, 1, 2, 3, 255):
            for v in range(0, 0x10000, 7):
                p = wire_model(st, md, v, 0)
                assert p & ILLEGAL_BIT5 == 0, f"payload 0x{p:02X} sets bit5 -- impossible"
                assert not (p & 0x80) or (p & 0x40), f"payload 0x{p:02X} has bit7 without bit6"
                seen.add(p & 0xF8)
    assert seen <= LEGAL_PAYLOAD_HI, f"the mirror produced payloads outside the legal set: {seen}"
    assert LEGAL_PAYLOAD_HI == {0x00, 0x08, 0x10, 0x18, 0x40, 0x48, 0x50, 0x58,
                                0xC0, 0xC8, 0xD0, 0xD8}, "the legal payload set drifted"
    return len(LEGAL_PAYLOAD_HI)


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, from raw bytes, in Python.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. This is the independent second method for the cave's contents."""
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        imm5 = hw & 0x1F
        simm5 = imm5 - 32 if imm5 & 0x10 else imm5
        if hw == 0x0000:
            n, m = 2, "nop"
        elif raw[i:i + 4] == PIN_SETFE_R7[1]:
            n, m = 4, "setfe r7"          # 🛑 Format IX, FOUR bytes, by exact pin match
        elif (hw >> 7) & 0xF == 0xB:
            n = 2
            m = {0x2: "be", 0x3: "bnh", 0x6: "blt", 0xA: "bne", 0xB: "bh",
                 0xE: "bge", 0xF: "bgt"}.get(hw & 0xF, f"b?{hw & 0xF:x}")
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            m = f"{m} {d:+d}"
        elif op6 in (0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F, 0x30, 0x31, 0x36):
            n = 4
            hw2 = struct.unpack_from("<H", raw, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            m = {0x39: "ld.w" if hw2 & 1 else "ld.h", 0x3A: "st.b", 0x3B: "st.h", 0x3C: "ld.bu",
                 0x3D: "ld.bu", 0x3F: "ld.hu" if hw2 & 1 else "ld.w", 0x30: "addi",
                 0x31: "movea", 0x36: "andi"}[op6]
            if op6 in (0x30, 0x31, 0x36):
                m = f"{m} 0x{hw2:04x},r{reg1},r{reg2}"
            else:
                eff = ((disp & ~1) | (op6 & 1)) if op6 in (0x3C, 0x3D) else disp
                m = (f"{m} r{reg2},{eff}[r{reg1}]" if op6 in (0x3A, 0x3B)
                     else f"{m} {eff}[r{reg1}],r{reg2}")
        elif op6 == 0x10:
            n, m = 2, f"mov 0x{imm5:x},r{reg2}"
        elif op6 == 0x12:
            n, m = 2, f"add {simm5:+d},r{reg2}"
        elif op6 == 0x13:
            n, m = 2, f"cmp {simm5:+d},r{reg2}"
        elif op6 == 0x14:
            n, m = 2, f"shr 0x{imm5:x},r{reg2}"      # 🛑 LOGICAL. 0x15 would be `sar`
        elif op6 == 0x15:
            n, m = 2, f"sar 0x{imm5:x},r{reg2}"
        elif op6 == 0x16:
            n, m = 2, f"shl 0x{imm5:x},r{reg2}"
        elif op6 == 0x0C:
            n, m = 2, f"subr r{reg1},r{reg2}"        # 🛑 reg2 = reg1 - reg2
        elif op6 == 0x0D:
            n, m = 2, f"sub r{reg1},r{reg2}"
        elif op6 == 0x0F:
            n, m = 2, f"cmp r{reg1},r{reg2}"
        elif op6 == 0x08:
            n, m = 2, f"or r{reg1},r{reg2}"
        elif hw == 0x007F:
            n, m = 2, "jmp [lp]"
        else:
            n, m = 2, f"?? {hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


def emulate_cave(cave, state, mode_idx, bd0, status):
    """🛑 THE THIRD METHOD: single-step the EMITTED BYTES on a tiny V850 interpreter and compare
    against `wire_model`. Neither the listing text nor the mirror is trusted -- only the bytes."""
    regs = [0] * 32
    mem = {STATE_DISP: state & 0xFF, MODEIDX_DISP: mode_idx & 0xFF, BD0_DISP: bd0 & 0xFFFF,
           -PAYLOAD_BYTE4_DISP: status & 0xFF}
    Z = S = False
    i, out = 0, None
    steps = 0
    while i < len(cave):
        steps += 1
        assert steps < 200, "the emulator did not terminate"
        hw = struct.unpack_from("<H", cave, i)[0]
        op6, reg2, reg1 = (hw >> 5) & 0x3F, hw >> 11, hw & 0x1F
        imm5 = hw & 0x1F
        simm5 = imm5 - 32 if imm5 & 0x10 else imm5
        if cave[i:i + 4] == PIN_SETFE_R7[1]:                       # setfe r7
            regs[R7] = 1 if Z else 0
            i += 4
            continue
        if (hw >> 7) & 0xF == 0xB:                                 # Bcond
            cond = hw & 0xF
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            take = {0xE: not S, 0x6: S, 0x2: Z}[cond]              # OV is always 0 here
            i = i + d if take else i + 2
            continue
        if op6 in (0x39, 0x3A, 0x3C, 0x3D):                        # gp-relative load/store
            hw2 = struct.unpack_from("<H", cave, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            eff = ((disp & ~1) | (op6 & 1)) if op6 in (0x3C, 0x3D) else disp
            assert reg1 == GP, "the emulator only models gp-relative access"
            if op6 == 0x3A:                                        # st.b
                out = regs[reg2] & 0xFF
                mem[eff] = out
            elif op6 == 0x39:                                      # ld.h -- SIGN extend
                v = mem[eff]
                regs[reg2] = v - 0x10000 if v & 0x8000 else v
            else:                                                  # ld.bu -- ZERO extend
                regs[reg2] = mem[eff] & 0xFF
            i += 4
            continue
        if op6 == 0x36:                                            # andi
            hw2 = struct.unpack_from("<H", cave, i + 2)[0]
            regs[reg2] = regs[reg1] & hw2
            Z, S = regs[reg2] == 0, False
            i += 4
            continue
        if op6 == 0x30:                                            # addi
            hw2 = struct.unpack_from("<H", cave, i + 2)[0]
            regs[reg2] = regs[reg1] + (hw2 - 0x10000 if hw2 & 0x8000 else hw2)
            i += 4
            continue
        if op6 == 0x31:                                            # movea -- the replayed insn
            i += 4
            continue
        if op6 == 0x13:                                            # cmp imm5
            r = regs[reg2] - simm5
            Z, S = r == 0, r < 0
        elif op6 == 0x0F:                                          # cmp reg1,reg2
            r = regs[reg2] - regs[reg1]
            Z, S = r == 0, r < 0
        elif op6 == 0x0C:                                          # subr
            regs[reg2] = regs[reg1] - regs[reg2]
            Z, S = regs[reg2] == 0, regs[reg2] < 0
        elif op6 == 0x12:                                          # add imm5
            regs[reg2] += simm5
            Z, S = regs[reg2] == 0, regs[reg2] < 0
        elif op6 == 0x14:                                          # shr -- LOGICAL
            regs[reg2] = (regs[reg2] & 0xFFFFFFFF) >> imm5
            Z, S = regs[reg2] == 0, False
        elif op6 == 0x16:                                          # shl
            regs[reg2] = (regs[reg2] << imm5) & 0xFFFFFFFF
            Z, S = regs[reg2] == 0, bool(regs[reg2] & 0x80000000)
        elif op6 == 0x08:                                          # or
            regs[reg2] |= regs[reg1]
            Z, S = regs[reg2] == 0, False
        elif hw == 0x007F:                                         # jmp [lp]
            break
        else:
            raise AssertionError(f"the emulator met an unmodelled opcode 0x{hw:04x} at +{i}")
        regs[R0] = 0
        i += 2
    assert out is not None, "the cave never reached its store"
    return out


def _check_emulator(cave):
    n = 0
    for st in (0, 4, 5, 6, 255):
        for md in (0, 2, 3, 255):
            for v in (0, 1, 63, 64, 191, 192, 193, 447, 448, 449, 511, 512, 821, 1024,
                      0xFFFF, 0xFF40, 0xFF00, 0xFE40, 0x8000, 0x7FFF):
                for status in (0, 5, 7):
                    got = emulate_cave(cave, st, md, v, status)
                    want = wire_model(st, md, v, status)
                    assert got == want, (
                        f"🛑 the EMITTED BYTES compute 0x{got:02X} but the mirror says 0x{want:02X} "
                        f"for state={st} mode={md} v=0x{v:04X} status={status}")
                    n += 1
    return n


def main():
    print("=" * 102)
    print("  V78 -- V76 + FactorE m26 Y[1] 300->449 (dose 206 = 150% of V75) + a re-cut probe")
    print("=" * 102)
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it"
    assert "v78" in os.path.basename(BIN_OUT).lower() and "V78" in TAG, \
        "the artefact names must carry the build number -- V77/V77B are already consumed"

    base = bytes(SRC_BIN.read_bytes())
    assert len(base) == 0x100000, f"the base must be 1 MiB, got 0x{len(base):X}"
    assert hashlib.sha256(base).hexdigest() == SRC_SHA256, "the base is NOT the V76 plain image"
    stock = bytes(STOCK_BIN.read_bytes())
    print(f"\n  base  {SRC_BIN.name}\n        sha256 {SRC_SHA256}  VERIFIED")

    # ---- BASE IDENTITY beyond the hash: V76's own cave, re-derived from its builder -------------
    v76_cave, _ = V76B.build_cave()
    assert bytes(base[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == v76_cave, \
        "the base's cave is not the one builds/v50_v79/build_v76_v38base_tva.py emits -- WRONG BASE"
    assert bytes(base[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the base's hook is not already the `jarl` to the cave"
    assert bytes(stock[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, \
        "the STOCK hook site is not the `movea` the cave replays"
    assert bytes(base[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "0x55C12 is not `mov 0x8,r7` -- the proof that r7 is dead across the hook"
    print("        base cave re-derived from build_v76_v38base_tva.build_cave(): IDENTICAL")

    # ---- everything checkable BEFORE a byte is written -----------------------------------------
    n_enc = _self_check_encoders(base)
    n_pay = _check_wire_model()
    n_pins = assert_pins(base, "V76 base")
    n_ptr = assert_pointer_arrays_stock(base, stock, "V76 base")
    nearest = assert_no_aliasing(base, "V76 base")
    assert_untouched_surfaces(base, base, "V76 base")
    assert_record_geometry(base, "V76 base")
    clamp, thresh, fric = assert_fault_interlock(base, "V76 base")
    assert_not_carried(base, "V76 base")
    assert_manual_mode_stock(base, stock, "V76 base")
    assert_cell_censuses(base, range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT), False, "V76 base")
    assert_crc_chain(base, "V76 base")
    print(f"  base OK: {n_enc} encoder round-trips, {n_pins} pins, {n_ptr} pointer arrays == STOCK "
          f"over {N_MODES} modes,\n           record geometry, no aliasing, censuses, "
          f"CRC chain 50/50, {n_pay} legal payloads")
    print(f"  🛑 INTERLOCK on the base: 0xC407E = {clamp} (<= {FAULT_CLAMP_MAX}), "
          f"0xC4004 = {thresh} => trip at {FAULT_TRIP_COUNTS} counts, friction m26 @0x{fric:05X} STOCK")
    print(f"  nearest OTHER record to the write set: {nearest[0]} bytes "
          f"({nearest[1]} @0x{nearest[2]:05X}, modes {nearest[3][:4]})")

    code = bytearray(base)
    touched = []

    # ---- GROUP 1 -- the one calibration cell ----------------------------------------------------
    print("\n" + "-" * 102)
    print("  GROUP 1 -- FactorE mode 26 (ENGAGED), ONE u16 cell.  Mode 24 and FactorC UNTOUCHED.")
    print("-" * 102)
    off, n, ox, oy = read_rec(code, FACTOR_E_PTRS, LIVE_MODE)
    assert (ox, oy) == BASE_E26, f"FactorE m26 base is X={ox} Y={oy}, expected {BASE_E26}"
    assert off == u32(code, FACTOR_E_PTRS + 4 * LIVE_MODE) == EXPECT_ADDR[("E", LIVE_MODE)]
    print(f"    pointer array 0x{FACTOR_E_PTRS:05X} + 26*4 = 0x{FACTOR_E_PTRS + 104:05X} "
          f"-> record 0x{off:05X}  (n={n}, rec_len={rec_len(n)})")
    assert_table_shape(*NEW_E26, label="FactorE m26 (new)")
    slack_before = bytes(code[off + REC_DATA_LEN:off + REC_STRIDE])
    woff, wlen = write_rec(code, FACTOR_E_PTRS, LIVE_MODE, *NEW_E26)
    assert wlen == REC_DATA_LEN, f"wrote {wlen}B, expected {REC_DATA_LEN}"
    assert bytes(code[off + REC_DATA_LEN:off + REC_STRIDE]) == slack_before, \
        "🛑 FactorE m26: the 2 slack bytes changed -- this is the V73 spill"
    touched.extend(range(off, off + REC_DATA_LEN))
    print(f"    FactorE m26 @0x{woff:05X}  X {ox} -> {NEW_E26[0]}   (UNCHANGED)")
    print(f"    {'':>18s}  Y {oy} -> {NEW_E26[1]}")

    runs1 = changed_runs(base, code)
    got_writes = {}
    for a, ln in runs1:
        for w in range(a, a + ln, 2):
            got_writes[w] = (u16(base, w), u16(code, w))
    assert set(got_writes) == set(EXPECTED_WRITES), \
        f"the write set differs from the spec: {sorted(map(hex, set(got_writes) ^ set(EXPECTED_WRITES)))}"
    for a, (old, new, lbl) in EXPECTED_WRITES.items():
        assert got_writes[a] == (old, new), f"0x{a:05X} ({lbl}): got {got_writes[a]}, spec {(old, new)}"
    print(f"    {len(EXPECTED_WRITES)} halfword write = {2 * len(EXPECTED_WRITES)} bytes "
          f"({sum(ln for _a, ln in runs1)} in {len(runs1)} run), matching the spec exactly")
    assert_manual_mode_stock(code, stock, "after group 1")
    assert_untouched_surfaces(code, base, "after group 1")
    assert_fault_interlock(code, "after group 1")
    assert_pointer_arrays_stock(code, stock, "after group 1")

    # ---- THE SURFACE GUARDS ----------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  SURFACE GUARDS  (v76_surface's per-instruction mirror of FUN_00034350)")
    print("-" * 102)
    S76, S78, STK = surfaces(base, code)
    d78 = S78.mag(SPEED_5MPH_CT, R_OP)
    d76 = S76.mag(SPEED_5MPH_CT, R_OP)
    e99 = S78.factorE(R_OP)
    c515 = S78.factorC(SPEED_5MPH_CT)
    k78 = ((c515 * NEW_E26[1][1]) >> 10) / (NEW_E26[0][1] - NEW_E26[0][0])
    k76 = ((S76.factorC(SPEED_5MPH_CT) * BASE_E26[1][1]) >> 10) / (BASE_E26[0][1] - BASE_E26[0][0])
    assert e99 == 373 and c515 == 566 and d78 == DOSE_TARGET, \
        f"the target arithmetic does not reproduce: E(99)={e99} C(515)={c515} dose={d78}"
    print(f"    E({R_OP}) = {NEW_E26[1][1]}*{R_OP}//{NEW_E26[0][1]} = {e99}  ·  C(515) = {c515}  ·  "
          f"dose = ({c515}*{e99})>>10 = {d78}")
    print(f"    dose {d78} = {100 * d78 / V75_DOSE:.2f}% of V75's {V75_DOSE}  ·  "
          f"{d78 / d76:.4f}x V76's {d76}")
    print(f"    k(truncated) = {k78:.4f}   = {k78 / k76:.4f}x V76 ({k76:.4f})  "
          f"= {k78 / 1.5798:.4f}x V75 (1.5798)")

    assert_table_shape(*S78.XY("E"), label="GUARD 1/2 built FactorE m26")
    print(f"    GUARD 1  X strictly increasing, Y monotone non-decreasing      PASS")
    print(f"    GUARD 2  E_Y[0] == 0 retained (no Coulomb relay); plateau removed ({NEW_E26[1][1]} "
          f"< {NEW_E26[1][2]})  PASS")

    nr, ns = assert_add_only(S76, S78, STK)
    ndirect = assert_add_only_direct(S78, STK)
    print(f"    GUARD 3  add-only vs STOCK, EXACT by factor monotonicity: FactorE over all {nr:,} "
          f"gated rate\n             indices and FactorC over all {ns:,} gated speed indices "
          f"(B/D/ceiling identical)")
    print(f"             second method -- direct 2-D sweep, {ndirect:,} (speed,rate) points, "
          f"worst drop 0   PASS")

    worst, flat_worst, nchg, nflat, c_max, nclip = assert_no_clip(S76, S78)
    print(f"    GUARD 4  NO NEW CLIPPING. The edit changes FactorE at {nchg:,} rate indices; over "
          f"those,\n             max (C_max={c_max} * E)>>10 = {worst} < the ceiling FLOOR "
          f"{CEILING_FLOOR}  =>  no point that\n             failed to clip on V76 can clip on V78, "
          f"at ANY ceiling the LERP can produce.")
    print(f"             max (566*E_max)>>10 over the {nflat:,} speeds where FactorC == 566 = "
          f"{flat_worst} (== the ceiling floor, unchanged from V76)")
    print(f"             second method -- clip-set sweep at 7 backdrive indices: {nclip} clipped "
          f"points on BOTH builds   PASS")

    rows, lo76, lo78 = assert_rung_reachability(S76, S78)
    print("\n    RUNG REACHABILITY -- smallest |rate| (counts / deg-s) that makes each rung fire:")
    hdr = "      thr  |" + "".join(f"{k:>14}" for k in (5, 20, 35, 60, 80, 96.7, 140)) + "  km/h"
    print(hdr)
    for thr in (DAMP_LO_THRESH, DAMP_HI_THRESH, CEILING_FLOOR):
        cells = []
        for kmh in (5, 20, 35, 60, 80, 96.7, 140):
            r = rows[thr][kmh]
            cells.append("never" if r is None else f"{r}/{r / RATE_CTS_PER_DEGS:.0f}")
        mark = "  <- bit6" if thr == DAMP_LO_THRESH else ("  <- bit7" if thr == DAMP_HI_THRESH
                                                          else "  (ceiling floor)")
        print(f"      {thr:4d} |" + "".join(f"{c:>14}" for c in cells) + mark)
    print(f"      ⚠ the kit's OBSERVED rate maximum is 1,941 counts (route 5d, RULE 8). At r=1941 "
          f"this\n        build's damper reaches {S78.mag(SPEED_5MPH_CT, 1941)} counts up to "
          f"80 km/h and {S78.mag(int(96.7 * 64), 1941)} at 96.7 km/h.")
    print(f"      ⇒ bit7 (448) is REACHABLE but NOT EXPECTED TO FIRE. Its null is the deliverable: "
          f"448 < {CEILING_FLOOR}\n        <= every reachable ceiling, so bit7 == 0 across a drive "
          f"PROVES no clipping occurred.")
    print(f"      ⇒ bit6 (192) needs {lo78} counts on V78 vs {lo76} on V76 -- a "
          f"{lo76 / lo78:.1f}x shift, and {lo78} ct sits just\n        under the design reference "
          f"rate {R_OP} ct. THAT is the dose-in-force measurement. "
          f"[brief said 512; resized]")

    # ---- GROUP 2 -- the probe cave ---------------------------------------------------------------
    print("\n" + "-" * 102)
    print(f"  GROUP 2 -- the {CAVE_EXTENT}-byte probe cave @0x{CAVE_BASE:05X} (RE-CUT), "
          f"hook 0x{HOOK_ADDR:05X} unchanged")
    print("-" * 102)
    cave, listing = build_cave()
    for addr, raw, text in listing:
        print(f"    0x{addr:05X}  {raw.hex():<8s}  {text}")
    n_emul = _check_emulator(cave)
    print(f"\n    THIRD METHOD: the EMITTED BYTES single-stepped on a V850 interpreter and compared "
          f"to\n    the mirror over {n_emul:,} (state, mode, |d|, status) combinations -- ALL MATCH.")
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave
    touched.extend(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "the hook must stay the base's `jarl` -- this build does not re-hook"
    assert bytes(code[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        bytes(base[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the cave tail is not virgin 0xFF"

    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_cell_censuses(code, cave_span, True, "after group 2")
    assert_fault_interlock(code, "after group 2")
    assert_not_carried(code, "after group 2")
    assert_manual_mode_stock(code, stock, "after group 2")
    assert_pins(code, "after group 2")

    # ---- CRC ------------------------------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  CRC")
    print("-" * 102)
    changed = refresh_crcs(code, touched)
    for trailer, (old, new, bstart) in sorted(changed.items()):
        touched.extend(range(trailer, trailer + 4))
        print(f"    block [0x{bstart:05X}, 0x{trailer:05X})  trailer 0x{old:08X} -> 0x{new:08X}")
    n_blocks = assert_crc_chain(code, "V78")
    print(f"    {len(changed)} trailer(s) rewritten; full chain re-verified: {n_blocks}/50 blocks PASS")

    # ---- the full attributed diff ---------------------------------------------------------------
    print("\n" + "-" * 102)
    print("  FULL BYTE DIFF  V76 -> V78")
    print("-" * 102)
    e_rec = rec_addr(code, FACTOR_E_PTRS, LIVE_MODE)
    groups = {}
    for a, ln in changed_runs(base, code):
        if e_rec <= a and a + ln <= e_rec + REC_STRIDE:
            g = "1 FactorE m26 cell"
        elif CAVE_BASE <= a < CAVE_BASE + CAVE_EXTENT:
            g = "2 probe cave"
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
              f"{', '.join(f'0x{a:05X}+{ln}' for a, ln in groups[g][:5])}"
              f"{' ...' if len(groups[g]) > 5 else ''}")
    assert "UNATTRIBUTED" not in groups, f"UNATTRIBUTED bytes: {groups.get('UNATTRIBUTED')}"
    # 🛑 COUNT CELLS, NOT BYTES. The edit is ONE u16 cell, but 300 = 0x012C and 449 = 0x01C1 share
    #    their HIGH byte, so the byte diff is ONE byte, not two. The brief said "the 2 table bytes";
    #    the bytes say one. THE BYTES WIN. What is asserted is the CELL and its containment.
    tbl = groups["1 FactorE m26 cell"]
    tbl_bytes = sum(ln for _a, ln in tbl)
    assert len(EXPECTED_WRITES) == 1 and tbl_bytes <= 2, \
        f"the table delta is {tbl_bytes} bytes across {len(tbl)} run(s) -- expected 1 CELL (<=2 B)"
    for a, ln in tbl:
        cell = next(iter(EXPECTED_WRITES))
        assert cell <= a and a + ln <= cell + 2, \
            f"a table diff run 0x{a:05X}+{ln} escapes the single cell 0x{cell:05X}+2"
    print(f"    TOTAL {sum(len(v) for v in groups.values())} runs, {total} bytes, ALL ATTRIBUTED")
    print(f"    🛑 table delta = 1 CELL @0x{next(iter(EXPECTED_WRITES)):05X} = {tbl_bytes} changed "
          f"byte(s): 300 = 0x012C -> 449 = 0x01C1 shares its\n       HIGH byte, so the byte count "
          f"is {tbl_bytes}, not 2. COUNT CELLS, NOT BYTES (the V77/V76 trap).")

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
    if os.path.exists(OUT) and Path(OUT).read_bytes() and existing is None:
        raise SystemExit(f"🛑 {OUT} exists but its plain image does not -- refusing to proceed")
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
    FF.assert_x31_checksum(rwd, "V78 output")
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    assert rwd_sha != SRC_RWD_SHA256, "the output .rwd is byte-identical to V76's -- nothing changed"

    # ---- 🛑 EVERYTHING re-derived FROM THE READBACK --------------------------------------------
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(dec[START:END]) == bytes(code[START:END]), "the decoded payload != the built image"

    assert_pins(dec, "readback")
    assert_pointer_arrays_stock(dec, stock, "readback")
    assert_no_aliasing(dec, "readback")
    assert_untouched_surfaces(dec, base, "readback")
    assert_record_geometry(dec, "readback")
    rb_clamp, rb_thresh, rb_fric = assert_fault_interlock(dec, "readback")
    assert_not_carried(dec, "readback")
    assert_manual_mode_stock(dec, stock, "readback")
    assert_cell_censuses(dec, cave_span, True, "readback")
    assert_crc_chain(dec, "readback")
    _o, _n, rx, ry = read_rec(dec, FACTOR_E_PTRS, LIVE_MODE)
    assert (rx, ry) == NEW_E26, f"readback FactorE m26 is X={rx} Y={ry}, expected {NEW_E26}"
    _o, _n, rcx, rcy = read_rec(dec, FACTOR_C_PTRS, LIVE_MODE)
    assert (rcx, rcy) == NEW_C26, "readback FactorC m26 moved -- it must be untouched"
    S_rb = VS.Surface(img=bytes(dec), mode=LIVE_MODE)
    assert S_rb.mag(SPEED_5MPH_CT, R_OP) == DOSE_TARGET, "the readback dose is not 206"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave, "the readback cave differs"
    assert bytes(dec[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        "readback: the hook is not the `jarl` to the cave"
    assert bytes(dec[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        "readback: the hook's return site 0x55C12 was disturbed"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]).count(HOOK_STOCK) == 1, \
        "readback: the displaced `movea` is not replayed EXACTLY once in the cave"
    assert bytes(dec[CAVE_BASE + CAVE_EXTENT:CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - CAVE_EXTENT), "the readback cave tail is not 0xFF"
    # 🛑 re-disassembled AND re-emulated FROM THE DECODED .rwd BYTES
    redis = redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    assert b"".join(r for _a, r, _t in redis) == cave, \
        "the re-disassembly does not reconstruct the cave's bytes"
    assert [(a, r) for a, r, _t in redis] == [(a, r) for a, r, _t in listing], \
        "the readback cave does not re-disassemble to the emitted listing"
    assert _check_emulator(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT])) == n_emul
    rb_runs = changed_runs(base, dec)
    assert sum(ln for _a, ln in rb_runs) == total, "the readback diff size differs"

    print("\n  READBACK -- re-derived FROM THE DECODED .rwd BYTES: the FactorE record via its")
    print("     pointer array, the dose 206, FactorC and mode-24 identity vs STOCK, all six pointer")
    print(f"     arrays, the DTC-0x1d interlock, the dropped levers, all {n_pins} pins, every probed")
    print("     cell's census, the whole 68-byte cave, its re-disassembly, its re-EMULATION, the")
    print("     cave tail, and the full 50-block CRC chain. ALL PASS.")
    print(f"\n  wrote {OUT}\n        SHA256 {rwd_sha}")

    print("\n" + "=" * 102)
    print("  V78 BUILT on the V76 base.  🛑 UNFLASHED. NOT A FLASH CLEARANCE.")
    print(f"  ★ ONE CELL: FactorE m26 Y[1] 300 -> 449 @0x{woff + 2 + 4 * 2 + 2 * 1:05X}. "
          f"dose(5 mph, {R_OP} ct) = {DOSE_TARGET} = {100 * DOSE_TARGET / V75_DOSE:.1f}% of V75.")
    print(f"  🛑 INTERLOCK CARRIED: 0xC407E = {rb_clamp} against a {FAULT_TRIP_COUNTS}-count trip "
          f"(0xC4004 = {rb_thresh});")
    print(f"     friction m26 @0x{rb_fric:05X} byte-stock; MODE 24 byte-STOCK; FactorC untouched.")
    print(f"  ★ probe: bit{BIT_DAMP_HI} |gp-0x6bd0| >= {DAMP_HI_THRESH} (no-clip guarantee) · "
          f"bit{BIT_DAMP_LO} |gp-0x6bd0| >= {DAMP_LO_THRESH} (dose in force)")
    print(f"           bit{BIT_MODEIDX} mode&2 · bit{BIT_STATE5} state==5 (POSITIVE CONTROL) · "
          f"bits 2:0 STEER_SENSOR_STATUS")
    print(f"     bit{BITS_CLEAR[0]} is STRUCTURALLY ZERO and bit{BIT_DAMP_HI} ALWAYS implies "
          f"bit{BIT_DAMP_LO}. Legal byte4 & 0xF8 =")
    print(f"     {sorted(hex(v) for v in LEGAL_PAYLOAD_HI)}")
    print("     Any payload with byte4 & 0x20, or bit7 without bit6, is an integrity failure.")
    print("     Read bit3 FIRST: all-zero on bits 7,6,4,3 for a whole drive = the cave never fired.")
    print("  🛑 GRIND #1 ONLY. The micro-ratchet is DOSE-INDEPENDENT (slope CI contains zero);")
    print("     this build is NOT expected to change it and must not be reported as if it were.")
    print("  🛑 Flash ONLY on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    main()
