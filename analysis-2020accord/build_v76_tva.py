#!/usr/bin/env python3
"""build_v76_tva.py -- V76 = V74 + V67/V68's RATE-LANE RESTORE, and a probe that watches THE GATE.

🛑🛑 V76 IS A **SIBLING** OF V75, NOT A SUCCESSOR. Both branch from the SAME V74 base. V75 cranks the
DAMPER dose 2.74x; V76 restores the RATE LANE. They are independent single-variable candidates and
**the operator chooses one to fly.** V76 is built on `_v74_engagedcols_x0_12_addonly_plain_image.bin`
and contains NONE of V75's FactorC/FactorE edits -- asserted cell by cell below, not asserted in prose.

★★★★ THE ONE-LINE REASON THIS BUILD EXISTS. The two best grind-#1 results in this kit's history are
rate-lane configs and NEITHER is on the car: V62/V65 (median e_18-22 = 168) causes grind #2, and
V67/V68 (109) does not. V67/V68's entire mechanism is **ONE BYTE plus ONE 16-bit cal**, and -- unlike
every mode-indexed lever this kit ever flew -- it is **MODE-PROOF**, which is why RULE 7 voided
V69/V70 but not V67/V68.

THE LEVER -- two cells, reproduced EXACTLY from V67/V68 (byte-verified against both images)
--------------------------------------------------------------------------------------------------
    0x3AA96   0xC5 -> 0xFB    repoints `ld.bu -0x683c[gp],r15` @0x3AA94 to `ld.bu -0x6806[gp],r15`.
                              ONE in-place branch-operand byte. `gp-0x683c` is a DEAD cell (1 reader,
                              0 writers, so it reads 0 forever ⇒ V72..V75 are UNGATED); `gp-0x6806`
                              is the LKAS-applying flag, validated on-car by V57's probe at 99.983%
                              agreement with `carControl.latActive`.
    0xC6446   512  -> 5244    r24's gate-active arm.
    0xC6444   512  -> 512     ⊕ ALREADY EQUAL to V67/V68's value. ASSERTED, NEVER WRITTEN.

★★ WHY THE REPOINT IS ONE BYTE AND NOT FOUR [EVIDENCE, Ghidra-rendered at 0x3AA94 = `847fc597`]:
   `-0x683c` encodes as hw2 = 0x97C4|1 = 0x97C5 and `-0x6806` as hw2 = 0x97FA|1 = 0x97FB. **BOTH
   displacements are EVEN**, so `ld.bu`'s displacement-bit-0 (which lives in hw1 bit 5, NOT hw2)
   stays 0, the opcode field stays 0x3C, and **hw1 is byte-identical**. Only hw2's LOW byte moves,
   `c5 -> fb`. V67 and V68 carry exactly `fb` at 0x3AA96 -- read out of both images by this builder.

★★★★ WHY IT IS MODE-PROOF -- RE-CONFIRMED IN GHIDRA FOR THIS BUILD, not quoted from the ledger.
   `FUN_0003aa2c` decompiled + disassembled; the crux traced end to end:
       0x3AA94  ld.bu -0x683c,gp,r15      the gate cell
       0x3AAA6  cmp   r0,r15
       0x3AAA8  setfne lp                 ⇒ lp = (gate != 0), and BOTH ladders branch on `lp`
     r26 / gain_A ladder:
       0x3AB56  cmp   r0,lp
       0x3AB5C  be    +8   -> 0x3AB64     gate == 0: fall through to the `gp-0x671a` arm / the LERP
       0x3AB5E  ld.hu 0x7444,tp,r8        gate != 0: **0xC6444 = 512, UNCONDITIONAL**
       0x3AB68  ld.hu 0x743e,tp,r8        (the `gp-0x671a >= 5` arm, 0xC643E = 1536)
     r24 / gain_B ladder:
       0x3ABFA  cmp   r0,r6               r6 = gp-0x671d, THE MASK
       0x3ABFC  be    +8   -> 0x3AC04
       0x3ABFE  ld.hu 0x7442,tp,r10       mask != 0: **0xC6442 = 1024, OUTRANKS EVERYTHING**
       0x3AC06  be    +8   -> 0x3AC0E
       0x3AC08  ld.hu 0x7446,tp,r10       gate != 0: **0xC6446, UNCONDITIONAL**
       0x3AC12  ld.hu 0x7440,tp,r10       else `gp-0x671a >= 5`: 0xC6440 = 2048
       (else)                             the **mode*4-indexed gain_B LERP** -- the FALLBACK
   ⇒ When the gate fires, both arms are plain `ld.hu <disp>[tp]` scalars that **override the register
   unconditionally** and the mode-indexed LERP is **bypassed entirely**. That is exactly why RULE 7
   voided V69/V70 (which edited the mode-10 fallback surface on a mode-24/26 car) but NOT V67/V68.

⚠ WHAT THE GATE DOES TO **BOTH** LANES, stated because it is a two-lane lever and always was:
   r24 -> 5244 against the gain_B creep LERP of 3072 = **x1.707**, and r26 -> 512 against gain_A's own
   creep LERP of 3072 = **/6.00**. Net delivered vs stock = `(5244 + 512a) / (3072 + 3072a)` with
   `a = gp-0x69a4/1024`; parity at a = 0.848. V67/V68 measured the kit's best grind-#1 result at this
   setting. **This build does not claim to know which lane did it** -- it reproduces the config.

THE PROBE -- watch THE GATE and its MASKING RISK, not just the output
--------------------------------------------------------------------------------------------------
    bit7 = (gp-0x6bd0 != 0)   ★ UNCHANGED from V74/V75 -- the cross-build anchor. Same cell, same
                                test, same bit position, so the three builds' duty cycles compare.
    bit6 = (gp-0x6806 != 0)   ★★★★ **THE GATE.** If this is CONSTANT the build is INERT and nothing
                                else in the log is interpretable.
    bit5 = (gp-0x671d != 0)   🛑 **THE MASKING RISK, and it OUTRANKS the arm.** When set, r24 is
                                pinned to 0xC6442 = 1024, BELOW the stock creep LERP of 3072 -- and
                                the gate's r26 /6 cut still applies ⇒ **V76 is BELOW STOCK in that
                                state.** V64 read this cell 0 across 14,980 frames of one short
                                route; a long mixed drive is its first real test.
    bit4 = (gp-0x671a >= 5)   the third arm (0xC6440 = 2048 / 0xC643E = 1536), below the gate.
                                ⚠ `>=`, not `>`; 0xC64FA is a **BYTE** cal = 5 (u16 reads 517 -- the
                                V63 trap). The threshold is asserted against the byte, and the cal is
                                on the keep-list so the hard-coded imm5 cannot drift.
    bits 2:0 = live STEER_SENSOR_STATUS, preserved exactly as V74/V75 do.
    bit3     = **STRUCTURALLY ZERO** -- see the byte budget below.

🛑🛑 THE BYTE BUDGET, AND THE ONE DELIBERATE DEVIATION FROM THE SPEC. The spec asked for a FIFTH rung,
`bit3 = (gp-0x6ac2 != 0)` (the back-drive detector). **IT DOES NOT FIT, and the arithmetic is not
close.** V75 fits five bits because three of them are `cmp imm5` rungs sharing ONE load (6 B each).
V76's bits read **four DIFFERENT cells**, so every rung costs `load(4) + cmp(2) + branch(2) + add(2)
= 10 B`:
      mov(2) + 5x10 + shl(2) + ld.bu byte4(4) + andi(4) + or(2) + st.b(4) + movea(4) + jmp(2) = 74 B
against the **68 B proven extent**. The cheaper encodings were checked and none exists:
  · `gp-0x671d` (0xFEDF18E3) and `gp-0x671a` (0xFEDF18E6) sit in **different 4-aligned words**, so no
    shared load can serve both -- computed from gp = 0xFEDF8000, not assumed.
  · `andi 0x7,r6,r6` (4 B) has no 2-byte equivalent with only r6/r7 provably dead across the hook;
    `shl 0x1d`/`shr 0x1d` is also 4 B. Recruiting a third register would be an unproven GATE 1 claim.
  · `setf` saves 2 B at best (only on the weight-1 rung) and would need a new, unpinned encoding.
  ⇒ **74 B is the floor for five rungs.** V76 therefore ships **FOUR** rungs in **64 B of code**,
  zero-padded to the same **68 B region** V74 used (V74's own cave is 46 B of code + 22 B of zero
  pad), so the edited span is byte-for-byte the same extent every build since V72 has carried.
⊕ WHAT IS LOST, AND WHY IT IS THE RIGHT BIT TO LOSE: `gp-0x6ac2` is the DAMPER CEILING's LERP index --
  a V74 property that V76 does not touch, orthogonal to the rate lane. **V75 carries that identical
  rung**, so whichever sibling flies, the kit does not lose the measurement.

★ BUILD IDENTITY, both ends. bit3 is emitted by NO instruction ⇒ **it is 0 on every V76 frame, by
  construction.** V74's own on-car payload was 0x28/0xA8 (state 5 ⇒ bits 6:3 = 0b0101 ⇒ **bit3 SET on
  every frame**), so a V74 log is rejected by one frame. V75's alphabet is the 10 thermometer values
  and its bits obey bit4=>bit5=>bit6=>bit7; V76's four bits are INDEPENDENT, so payloads such as 0x10,
  0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x90, 0xA0, 0xB0, 0xD0 are legal here and ILLEGAL on V75.

★★ THE STRUCTURAL PROOF OF THE REPOINT IS A **CENSUS**, and it is TWO-SIDED [EVIDENCE, raw byte scan]:
      gp-0x683c   1 firmware reader on V74  ->  **0** on V76      (the dead cell is abandoned)
      gp-0x6806  13 firmware readers on V74 -> **14** on V76, the new one at **exactly 0x3AA94**
   A one-byte edit that failed to land, or landed on the wrong cell, cannot produce that pair.

🛑 MUST NOT CHANGE -- asserted by VALUE on the input, the output AND the .rwd readback
--------------------------------------------------------------------------------------------------
  BOTH `sar` sites at STOCK (0x3AB76 = aa32, 0x3AC20 = aa42 -- **reintroducing V62's `a9` causes
  grind #2, and the fix is an ABSENCE**) · V72's gain_A r26 cut (0xC6A68/0xC6A7C flat 512;
  0xC6A90/0xC6AA4 byte-stock) · 0xC643E = 1536 · 0xC6440 = 2048 · 0xC6442 = 1024 · **0xC6444 = 512
  (V67/V68's value already; asserted, never written)** · 0xC64FA byte = 5 · 0xC407E = 850 ·
  0x454FE = 0xB5 (carried inertly since V71) · **the ENTIRE FactorB/C/D/E + ceiling + friction damper
  lane on ALL 34 modes -- i.e. V75's levers must NOT appear here** · the six pointer arrays · the
  config table · every DISENGAGED-column record.

Usage:  python build_v76_tva.py
"""
import hashlib
import os
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl / cmp_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldbu_any / ldh / cmp_imm5)
import build_v57_tva as V57                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the raw byte scan)
import build_v68_tva as V68                # noqa: E402  (cave machinery)
import build_v71a_tva as A                 # noqa: E402
import build_v72_tva as V72                # noqa: E402
import build_v74_tva as V74                # noqa: E402  (THE BASE -- its levers, guards and readers)
import v72_lane_model as LM                # noqa: E402
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = V72.START, V72.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT              # 68 -- the PROVEN REGION. Never grow it.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT      # 0xC4FF0
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
TP = LM.TP                                 # 0xBF000

# =====================================================================================================
# THE BASE -- V74, carried. 🛑 THE SIBLING V75 IS **NOT** IN THIS CHAIN.
# =====================================================================================================
SRC_BIN = plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin")
SRC_SHA256 = "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959"
STOCK_BIN = stock_fw_path("code.bin")

# 🛑 V67 / V68 -- the images this build REPRODUCES. Read, not quoted: the two lever values below are
# cross-checked against BOTH of them, so a typo here fails instead of shipping.
V67_BIN = plain_image_path("_v67_plain_image.bin")
V68_BIN = plain_image_path("_v68_plain_image.bin")

# =====================================================================================================
# THE LEVER -- exactly two cells
# =====================================================================================================
GATE_INSN_ADDR = 0x3AA94                        # `ld.bu -0x683c[gp],r15`
GATE_ADDR = 0x3AA96                             # hw2's LOW byte -- the ONLY byte that moves
GATE_BYTE_V74, GATE_BYTE_V76 = 0xC5, 0xFB
GATE_INSN_V74 = bytes.fromhex("847fc597")       # Ghidra-rendered at 0x3AA94 on the stock image
GATE_INSN_V76 = bytes.fromhex("847ffb97")
GATE_DISP_V74, GATE_DISP_V76 = 0x683C, 0x6806   # gp-relative, both POSITIVE offsets below gp
GATE_CONSUMER = (0x3AAA6, 0x3AAA8)              # `cmp r0,r15` ; `setfne lp` -- the crux, Ghidra-read

ARM_B_ADDR, ARM_B_V74, ARM_B_V76 = 0xC6446, 512, 5244     # r24's gate-active arm  (gain_B side)
ARM_A_ADDR, ARM_A_VALUE = 0xC6444, 512                    # r26's gate-active arm  -- ASSERT ONLY

# The rest of the two ladders. 🛑 Every one is on the keep-list; none is written.
LADDER_KEEP = {0xC643E: 1536,       # r26 third arm   (gp-0x671a >= 5)
               0xC6440: 2048,       # r24 third arm   (gp-0x671a >= 5)
               0xC6442: 1024,       # r24 MASK arm    (gp-0x671d != 0) -- outranks the gate
               ARM_A_ADDR: ARM_A_VALUE}
ARM_THRESHOLD_ADDR = 0xC64FA        # 🛑 a **BYTE** cal. u16 here reads 517 -- the V63 trap.
ARM_THRESHOLD = 5

# The two ladder code spans, asserted byte-identical to V74: the lever is the GATE, not the ladders.
LADDER_SPANS = {0x3AB56: 0x3AB6C,   # r26 / gain_A selector
                0x3ABFA: 0x3AC16}   # r24 / gain_B selector
SAR_SITES = {0x3AB76: bytes.fromhex("aa32"), 0x3AC20: bytes.fromhex("aa42")}
V72_GAIN_A = {0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}
V72_CARRIED = (0x454FE, 0xB5)
CLAMP_KEEP = (0xC407E, 850)
REC_STRIDE = 0x14

# The damper lane -- V75's territory. EVERY record on EVERY mode must be byte-identical to V74.
FACTOR_B_PTRS, FACTOR_C_PTRS = 0xC9CCC, 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = 0xC9DB4, 0xC9F84
CEILING_PTRS, FRICTION_PTR_ARRAY = 0xC77A0, 0xCBE74
ALL_MODES = range(34)
ENGAGED_EXPECTED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_EXPECTED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
THIS_CAR_ROW, THIS_CAR_KEY, LIVE_MODE = 11, "TVCA4", 26

# ⊕ The delivered multiplier, stated independently and re-derived from the bytes actually written.
GAIN_B_CREEP_LERP = 3072            # gain_B's own creep value on the mode-indexed fallback surface
GAIN_A_CREEP_LERP = 3072            # gain_A's own creep value on its (non-mode-indexed) surface
R24_RATIO_EXPECT = 1.70703125       # 5244 / 3072
R26_RATIO_EXPECT = 0.16666666666    # 512 / 3072  == 1/6.00 EXACTLY
PARITY_A = 0.848                    # `a` at which the net lands on stock; above it V76 is BELOW stock

# =====================================================================================================
# THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
HOOK_RETURN = HOOK_ADDR + 4                     # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")        # `mov 0x8,r7` -- proves r7 is DEAD across the hook

DAMP_DISP = 0x6BD0              # gp-0x6bd0  the damper output.       ld.h,   SIGNED
GATE_DISP = GATE_DISP_V76       # gp-0x6806  THE GATE.                ld.bu,  EVEN disp -> op 0x3C
MASK_DISP = 0x671D              # gp-0x671d  the mask.                ld.bu,  ODD  disp -> op 0x3D
ARM3_DISP = 0x671A              # gp-0x671a  the third arm's index.   ld.bu,  EVEN disp -> op 0x3C
DEAD_DISP = GATE_DISP_V74       # gp-0x683c  the abandoned dead cell
STATE_DISP = 0x67FA             # ⚠ V74's state cell -- V76 does NOT read it. Asserted both ways.
BACKDRIVE_DISP = 0x6AC2         # ⚠ V75's back-drive cell -- V76 does NOT read it. Asserted both ways.

W_B7, W_B6, W_B5, W_B4 = 8, 4, 2, 1             # PRE-`shl 0x4` weights
HI_SHIFT = 4                                    # `shl 0x4,r7` -- puts the 4-bit field at 7:4
BIT_DAMP_NZ, BIT_GATE, BIT_MASK, BIT_ARM3 = 0x80, 0x40, 0x20, 0x10
BIT_UNUSED = 0x08                               # 🛑 emitted by NO instruction ⇒ 0 on every frame
PROBE_MASK = 0xF0
BE_SKIP = 4                     # `be +4`  -- skips one 2-byte `add`
BLT_SKIP = 4                    # `blt +4` -- skips one 2-byte `add`
PAD_BYTES = 4                   # zero pad to the 68-byte region (V74's own precedent: 46 + 22)

# ★ THE PAYLOAD ALPHABET. Four INDEPENDENT bits ⇒ all 16 of {0x00..0xF0 step 0x10} are reachable and
# nothing else is. That is a weaker structural guard than V75's thermometer, so it is stated honestly.
LEGAL_PAYLOADS = tuple(v << 4 for v in range(16))
# 🛑 The stale payloads that MUST be illegal here, each from a real on-car log of this kit.
STALE_PAYLOADS = {0x28: "V74 state 5, bit7 clear", 0xA8: "V74 state 5, bit7 set",
                  0xC8: "V75 thermometer + back-drive", 0x08: "V75 back-drive alone",
                  0xE8: "V75 thermometer + back-drive", 0xF8: "V75 full thermometer + back-drive"}

# The probed cells' firmware censuses on the V74 BASE. (reads, writes, read mnemonics, write mnemonic)
CENSUS_BASE = {DAMP_DISP: (5, 3, {"ld.h"}, {"st.h"}),
               GATE_DISP: (13, 16, {"ld.bu"}, {"st.b"}),
               MASK_DISP: (14, 2, {"ld.bu"}, {"st.b"}),
               ARM3_DISP: (7, 1, {"ld.bu"}, {"st.b"}),
               DEAD_DISP: (1, 0, {"ld.bu"}, set())}
# ★★ ON THE OUTPUT the gate's reader moves: gp-0x683c 1 -> 0 and gp-0x6806 13 -> 14. TWO-SIDED.
CENSUS_OUT = {DAMP_DISP: (5, 3, {"ld.h"}, {"st.h"}),
              GATE_DISP: (14, 16, {"ld.bu"}, {"st.b"}),
              MASK_DISP: (14, 2, {"ld.bu"}, {"st.b"}),
              ARM3_DISP: (7, 1, {"ld.bu"}, {"st.b"}),
              DEAD_DISP: (0, 0, {"ld.bu"}, set())}
DAMP_WRITERS = [0x34730, 0x34744, 0x34752]
MASK_WRITERS = [0x3BD2A, 0x41EC6]
ARM3_WRITERS = [0x42A12]
GATE_WRITER_COUNT = 16
# How many times the CAVE touches each cell, on the input (a V74 cave) and the output (a V76 one).
CAVE_ACCESS_ON_BASE = {DAMP_DISP: 1, GATE_DISP: 0, MASK_DISP: 0, ARM3_DISP: 0,
                       DEAD_DISP: 0, STATE_DISP: 1, BACKDRIVE_DISP: 0}
CAVE_ACCESS_ON_OUTPUT = {DAMP_DISP: 1, GATE_DISP: 1, MASK_DISP: 1, ARM3_DISP: 1,
                         DEAD_DISP: 0, STATE_DISP: 0, BACKDRIVE_DISP: 0}
# 🛑 All three known lockstep shadows -- a stray write to either half escalates via FUN_0006b9fa.
SHADOW_DISPS = {0x4C39: "gp-0x67fa's", 0x4CF2: "gp-0x6bd0's", 0x4CC6: "gp-0x6ac2's"}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance in the STOCK image, and
# ---- every one below was rendered by Ghidra's own disassembler at that address before being used.
PIN_MOVI5_0_R7 = (0x34114, bytes.fromhex("003a"))          # `mov 0x0,r7`
PIN_LDH_HW1 = (0x3ACA8, bytes.fromhex("24372c95"))         # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_6BD0_DISP = (0x34726, bytes.fromhex("243f3094"))   # hw2 donor: `ld.h -0x6bd0[gp],r7`
PIN_STH_6BD0 = (0x34730, bytes.fromhex("64373094"))        # 🛑 THE ONE-BIT TWIN: st.h, SAME reg/disp
PIN_LDBU_6806_R6 = (0x2A8C0, bytes.fromhex("8437fb97"))    # ★ EXACT: `ld.bu -0x6806[gp],r6`
PIN_LDBU_671D_R6 = (0x3AB98, bytes.fromhex("a437e398"))    # ★ EXACT, and it is the FIRMWARE'S OWN
                                                           #   mask read inside FUN_0003aa2c. op 0x3D.
PIN_LDBU_HW1_R6 = (0x55AD4, bytes.fromhex("8437edea"))     # hw1 donor: a real `ld.bu ...,gp,r6`
PIN_LDBU_671A_DISP = (0x3AA70, bytes.fromhex("8467e798"))  # hw2 donor: `ld.bu -0x671a[gp],r12`
PIN_CMP_R0_R6 = (0x3401E, bytes.fromhex("e031"))           # `cmp r0,r6`
PIN_CMP5_R6 = (0x07380, bytes.fromhex("6532"))             # `cmp 0x5,r6`
PIN_BE4 = (0x02998, bytes.fromhex("a205"))                 # `be +4`
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))                # `blt +4`
PIN_ADD8_R7 = (0x0370C, bytes.fromhex("483a"))             # `add 0x8,r7`
PIN_ADD4_R7 = (0x038C4, bytes.fromhex("443a"))             # `add 0x4,r7`
PIN_ADD2_R7 = (0x27EF0, bytes.fromhex("423a"))             # `add 0x2,r7`
PIN_ADD1_R7 = (0x0EEE4, bytes.fromhex("413a"))             # `add 0x1,r7`
PIN_SHL4_R7 = (0x1C1C2, bytes.fromhex("c43a"))             # `shl 0x4,r7`
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))      # `ld.bu -0x1514,gp,r6`
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))       # `andi 0x7,r6,r6`
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))            # `or r7,r6`   -> r6 |= r7   (THE MERGE)
PIN_OR_R6_R7 = (0x1C1C4, bytes.fromhex("0639"))            # 🛑 the SWAPPED twin -- asserted away
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))       # `st.b r6,-0x1514,gp` -- THE ONLY STORE
PIN_MOVEA_HOOK = (0x55C0E, bytes.fromhex("2436e8ea"))      # the displaced `movea -0x1518,gp,r6`
PIN_JMP_LP = (0x1E4, bytes.fromhex("7f00"))                # `jmp lp`
# 🛑 the two ladder branches whose polarity the whole build rests on, Ghidra-rendered.
PIN_LADDER_BE8_A = (0x3AB5C, bytes.fromhex("c205"))        # `be 0x3AB64` = +8   (r26 lane)
PIN_LADDER_BE8_B = (0x3AC06, bytes.fromhex("c205"))        # `be 0x3AC0E` = +8   (r24 lane)

COND_BE, COND_BNE = FF.COND_BE, FF.COND_BNE                # 0x2 / 0xA -- the INVERTING twin
COND_BLT, COND_BGE = 0x6, 0xE                              # the OTHER inverting pair

DECODER = os.path.join(HERE, "..", "rlog-tools", "decode_v76_probe.py")

LEVER_TOKEN = f"gate.{GATE_BYTE_V76:02X}+arm{ARM_B_ADDR:05X}.{ARM_B_V76}"
BIN_OUT = str(plain_image_path("_v76_gate_fb_arm5244_gateprobe_plain_image.bin"))
TAG = "V74BASE-GATE-FB-ARM5244-gateprobe-6806-671d-671a"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V76-{TAG}-0x{START:X}-0x{END:X}.rwd")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


rec_len = V74.rec_len                   # 4 + 4n -- 🛑 NOT a flat 0x18 window
rec4_y = V74.rec4_y
factor_rec = V74.factor_rec             # DEREFERENCED from the pointer array, never quoted


# =====================================================================================================
# Encoders this build adds
# =====================================================================================================

def addi5(imm5, reg2):
    """Format II `add imm5,reg2`, opcode 0x12. imm5 is SIGN-extended: the range is -16..+15."""
    assert -16 <= imm5 <= 15, f"add imm5 {imm5} is outside Format II's signed 5-bit range"
    assert 0 <= reg2 < 32
    return struct.pack("<H", (reg2 << 11) | (0x12 << 5) | (imm5 & 0x1F))


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v6bd0, v6806, v671d, v671a, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the instructions, not a paraphrase."""
    r7 = 0                                              # mov 0x0,r7
    r6 = v6bd0 - 0x10000 if v6bd0 & 0x8000 else v6bd0   # ld.h   (SIGN-extends a halfword)
    if r6 != 0:                                         # cmp r0,r6 ; be +4
        r7 += W_B7                                      # add 0x8,r7   -> bit7
    r6 = v6806 & 0xFF                                   # ld.bu  (ZERO-extends a byte)
    if r6 != 0:                                         # cmp r0,r6 ; be +4
        r7 += W_B6                                      # add 0x4,r7   -> bit6  THE GATE
    r6 = v671d & 0xFF                                   # ld.bu  (op 0x3D -- ODD displacement)
    if r6 != 0:                                         # cmp r0,r6 ; be +4
        r7 += W_B5                                      # add 0x2,r7   -> bit5  THE MASK
    r6 = v671a & 0xFF                                   # ld.bu
    if r6 >= ARM_THRESHOLD:                             # cmp 0x5,r6 ; blt +4   (SIGNED, r6 in 0..255)
        r7 += W_B4                                      # add 0x1,r7   -> bit4
    r7 <<= HI_SHIFT                                     # shl 0x4,r7
    r6 = status_bits & PAYLOAD_KEEP_MASK                # ld.bu -0x1514[gp],r6 ; andi 0x7,r6,r6
    r6 |= r7                                            # or r7,r6
    return r6 & 0xFF                                    # st.b stores the LOW BYTE


def _spec(v6bd0, v6806, v671d, v671a):
    """The reference payload, written from the SPEC rather than from the wire model."""
    a = v6bd0 - 0x10000 if v6bd0 & 0x8000 else v6bd0
    return ((BIT_DAMP_NZ if a != 0 else 0)
            | (BIT_GATE if (v6806 & 0xFF) != 0 else 0)
            | (BIT_MASK if (v671d & 0xFF) != 0 else 0)
            | (BIT_ARM3 if (v671a & 0xFF) >= ARM_THRESHOLD else 0))


def _wire_model():
    """The rungs' semantics, checked EXHAUSTIVELY where the domain allows, not by sampling."""
    # 🛑 the three byte cells are checked over their FULL 0..255 domain, jointly.
    for g in range(256):
        for m in (0, 1, 255):
            for a3 in range(256):
                b = wire_byte4(0, g, m, a3)
                assert (b & PROBE_MASK) == _spec(0, g, m, a3), \
                    f"the wire model disagrees with the spec at gate={g} mask={m} arm3={a3}"
    # 🛑 bit7 EXHAUSTIVELY over every possible `gp-0x6bd0`, and it must be TWO-SIDED.
    for v in range(0x10000):
        b = wire_byte4(v, 0, 0, 0)
        assert bool(b & BIT_DAMP_NZ) == (v != 0), f"bit7 is wrong at 0x{v:04X}"
        assert (b & (PROBE_MASK ^ BIT_DAMP_NZ)) == 0, "a damper value disturbed another bit"
    assert wire_byte4(0xFFFF, 0, 0, 0) & BIT_DAMP_NZ and wire_byte4(0x0001, 0, 0, 0) & BIT_DAMP_NZ, \
        "bit7 is not two-sided -- a negative damper output must set it"
    assert not (wire_byte4(0x0000, 0, 0, 0) & BIT_DAMP_NZ), "bit7 sets on a ZERO damper output"
    # 🛑 bit4's threshold is `>=` and lands EXACTLY on the BYTE cal, from both sides.
    assert wire_byte4(0, 0, 0, ARM_THRESHOLD) & BIT_ARM3, f"|arm3| = {ARM_THRESHOLD} does not set bit4"
    assert not (wire_byte4(0, 0, 0, ARM_THRESHOLD - 1) & BIT_ARM3), \
        "bit4 sets one count BELOW the threshold -- `>` was encoded where `>=` was specified"
    assert wire_byte4(0, 0, 0, 255) & BIT_ARM3, \
        "bit4 is CLEAR at 255 -- the compare was signed against a sign-extended byte"
    # ★ THE FOUR BITS ARE INDEPENDENT -- every one of the 16 payloads is reachable, and only those.
    reachable = {wire_byte4(d, g, m, a) & PROBE_MASK
                 for d in (0, 1) for g in (0, 1) for m in (0, 1) for a in (0, 5)}
    assert reachable == set(LEGAL_PAYLOADS), \
        f"the reachable payload set is {sorted(hex(x) for x in reachable)}, expected all 16"
    assert len(LEGAL_PAYLOADS) == 16, "LEGAL_PAYLOADS is not the full 16-value alphabet"
    # 🛑🛑 bit3 IS STRUCTURALLY ZERO -- the whole build-identity guard against V74 and V75.
    for d in (0, 1, 0xFFFF, 0x7FFF, 0x8000):
        for g in (0, 1, 255):
            for m in (0, 1, 255):
                for a in (0, 4, 5, 255):
                    assert not (wire_byte4(d, g, m, a) & BIT_UNUSED), \
                        "🛑 bit3 is SET -- V76 emits no instruction for it, so this is impossible " \
                        "and the identity guard against V74 (bits 6:3 = state) would be void"
    for stale, who in STALE_PAYLOADS.items():
        assert stale not in LEGAL_PAYLOADS, f"0x{stale:02X} ({who}) is LEGAL on V76 -- no identity"
    # the preserved status bits, and the field's confinement to bits 7:4
    for status in range(8):
        for d in (0, 0x0100, 0xFF00):
            for g in (0, 1):
                b = wire_byte4(d, g, 0, 0, status_bits=status)
                assert b & PAYLOAD_KEEP_MASK == status, \
                    "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
                assert (b & PROBE_MASK) | status == b, "the field escaped bits 7:4"
    assert PROBE_MASK & PAYLOAD_KEEP_MASK == 0 and PROBE_MASK & BIT_UNUSED == 0 and \
        BIT_DAMP_NZ | BIT_GATE | BIT_MASK | BIT_ARM3 == PROBE_MASK == 0xF0, \
        "the probe bits do not cover exactly 7:4"
    # 🛑 THE ACCUMULATOR CANNOT OVERFLOW THE BYTE: max r7 after the shift is 0xF0.
    assert ((W_B7 + W_B6 + W_B5 + W_B4) << HI_SHIFT) == PROBE_MASK, \
        "the accumulator's maximum is not 0xF0 -- the weights or the shift are wrong"
    assert (W_B7 << HI_SHIFT) == BIT_DAMP_NZ and (W_B6 << HI_SHIFT) == BIT_GATE and \
        (W_B5 << HI_SHIFT) == BIT_MASK and (W_B4 << HI_SHIFT) == BIT_ARM3, \
        "a weight does not land on its declared bit"
    for w in (W_B7, W_B6, W_B5, W_B4):
        assert -16 <= w <= 15, f"weight {w} does not fit `add imm5`"
    assert -16 <= ARM_THRESHOLD <= 15, "the arm threshold does not fit `cmp imm5`"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    Each pin below was ALSO rendered by Ghidra's own disassembler at that address before being
    written into this file -- the pin is the byte check, Ghidra is the semantic check.
    """
    V55._self_check_encoders()               # chains down through V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVI5_0_R7, PIN_LDH_HW1, PIN_LDH_6BD0_DISP, PIN_STH_6BD0, PIN_LDBU_6806_R6,
            PIN_LDBU_671D_R6, PIN_LDBU_HW1_R6, PIN_LDBU_671A_DISP, PIN_CMP_R0_R6, PIN_CMP5_R6,
            PIN_BE4, PIN_BLT4, PIN_ADD8_R7, PIN_ADD4_R7, PIN_ADD2_R7, PIN_ADD1_R7, PIN_SHL4_R7,
            PIN_LDBU_BYTE4, PIN_ANDI_7_R6, PIN_OR_R7_R6, PIN_OR_R6_R7, PIN_STB_BYTE4,
            PIN_MOVEA_HOOK, PIN_JMP_LP, PIN_LADDER_BE8_A, PIN_LADDER_BE8_B,
            (GATE_INSN_ADDR, GATE_INSN_V74)]
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # ---- the damper load. SIGNED `ld.h`; its one-bit twin `st.h` is a real instruction. ----------
    ldh = V55.ldh(DAMP_DISP, R6)
    assert ldh[:2] == PIN_LDH_HW1[1][:2], "the ld.h hw1 is not the real `ld.h ...,gp,r6` form"
    assert ldh[2:] == PIN_LDH_6BD0_DISP[1][2:] == PIN_STH_6BD0[1][2:], \
        "the ld.h displacement halfword is not the real -0x6bd0"
    assert ((struct.unpack("<H", ldh[:2])[0] >> 5) & 0x3F) == 0x39, \
        "the damper load's opcode field is not 0x39 -- 0x3B would be an st.h, a WRITE"
    assert ldh != PIN_STH_6BD0[1] and ldh[:2] != PIN_STH_6BD0[1][:2], \
        f"the damper load matches the real `st.h r6,-0x6bd0,gp` @0x{PIN_STH_6BD0[0]:05X} -- the cave " \
        "would OVERWRITE the damper's own output"

    # ---- the three byte loads. 🛑 THE PARITY TRAP, decoded by FIELD on every one. -----------------
    # `ld.bu` carries the displacement's bit 0 in the OPCODE FIELD (0x3C even / 0x3D odd), NOT in hw2.
    # gp-0x671d's displacement 0x98E3 is ODD; the other two are EVEN. An encoder that assumed one
    # parity would silently address the NEIGHBOURING cell with every other field perfect.
    for disp, want_op, pin, why in ((GATE_DISP, 0x3C, PIN_LDBU_6806_R6, "THE GATE"),
                                    (MASK_DISP, 0x3D, PIN_LDBU_671D_R6, "THE MASK (ODD disp)"),
                                    (ARM3_DISP, 0x3C, None, "the third arm's index")):
        raw = V55.ldbu_any(-disp, R6)
        hw1, hw2 = struct.unpack("<HH", raw)
        d16 = (0x10000 - disp) & 0xFFFF
        assert ((hw1 >> 5) & 0x3F) == want_op, \
            f"gp-0x{disp:04x} ({why}): opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, expected " \
            f"0x{want_op:02X} -- displacement 0x{d16:04X} is " \
            f"{'ODD' if d16 & 1 else 'EVEN'} and `ld.bu` carries that bit in hw1 bit 5"
        assert ((hw1 >> 5) & 1) == (d16 & 1), "hw1's displacement bit 0 disagrees with the address"
        assert (hw2 & 0xFFFE) == (d16 & 0xFFFE) and hw2 & 1 == 1, \
            f"gp-0x{disp:04x}: hw2 is 0x{hw2:04X}, expected 0x{(d16 & 0xFFFE) | 1:04X}"
        assert (hw1 >> 11) == R6 and (hw1 & 0x1F) == GP == 4, \
            f"gp-0x{disp:04x}: the load is not `... [gp],r6`"
        assert raw != FF.stb(R6, -disp, GP), f"gp-0x{disp:04x}: the load collapsed onto an st.b"
        assert V55.ldbu_any(-disp, R6) != V55.ldbu_any(-(disp ^ 1), R6), \
            f"gp-0x{disp:04x} and its ODD/EVEN neighbour encode identically -- the parity trap is live"
        if pin is not None:
            assert raw == pin[1], f"gp-0x{disp:04x} ({why}) != the real one @0x{pin[0]:05X}"
    # the arm3 load has no exact donor; it is composed from a REAL hw1 and a REAL hw2, both pinned.
    arm3 = V55.ldbu_any(-ARM3_DISP, R6)
    assert arm3[:2] == PIN_LDBU_HW1_R6[1][:2], "the arm3 hw1 is not the real `ld.bu ...,gp,r6` form"
    assert arm3[2:] == PIN_LDBU_671A_DISP[1][2:], "the arm3 hw2 is not the real -0x671a displacement"

    # ---- the branches ------------------------------------------------------------------------------
    assert FF.bcond(COND_BE, BE_SKIP) == PIN_BE4[1], "be +4 != the real one @0x2998"
    assert FF.bcond(COND_BLT, BLT_SKIP) == PIN_BLT4[1], "blt +4 != the real one @0x290A8"
    assert FF.bcond(COND_BNE, BE_SKIP) != FF.bcond(COND_BE, BE_SKIP), \
        "🛑 `be +4` and `bne +4` collapsed -- the wrong one INVERTS every zero-test rung"
    assert FF.bcond(COND_BGE, BLT_SKIP) != FF.bcond(COND_BLT, BLT_SKIP), \
        "🛑 `blt +4` and `bge +4` collapsed -- the wrong one inverts bit4"
    assert FF.bcond(COND_BE, BE_SKIP) != FF.bcond(COND_BLT, BLT_SKIP), \
        "the zero-test and threshold branches encode identically"

    # ---- the accumulator ---------------------------------------------------------------------------
    assert FF.movi5(0, R7) == PIN_MOVI5_0_R7[1], "mov 0x0,r7 != the real one @0x34114"
    assert FF.movi5(0, R7) != HOOK_RETURN_INSN, "mov 0x0,r7 collapsed onto the hook's `mov 0x8,r7`"
    assert V54.cmp_rr(R0, R6) == PIN_CMP_R0_R6[1], "cmp r0,r6 != the real one @0x3401E"
    assert V54.cmp_rr(R6, R0) != V54.cmp_rr(R0, R6), "cmp's two register fields collapsed"
    assert V55.cmp_imm5(ARM_THRESHOLD, R6) == PIN_CMP5_R6[1], \
        f"cmp 0x{ARM_THRESHOLD:x},r6 != the real one @0x{PIN_CMP5_R6[0]:05X}"
    hw = struct.unpack("<H", V55.cmp_imm5(ARM_THRESHOLD, R6))[0]
    assert ((hw >> 5) & 0x3F) == 0x13 and (hw >> 11) == R6 and (hw & 0x1F) == ARM_THRESHOLD, \
        "`cmp 0x5,r6` fields are wrong"
    assert V55.cmp_imm5(ARM_THRESHOLD, R6) != addi5(ARM_THRESHOLD, R6), \
        "🛑 `cmp imm5` and `add imm5` collapsed -- the threshold test would become an ADD"
    for w, pin in ((W_B7, PIN_ADD8_R7), (W_B6, PIN_ADD4_R7), (W_B5, PIN_ADD2_R7),
                   (W_B4, PIN_ADD1_R7)):
        assert addi5(w, R7) == pin[1], f"add 0x{w:x},r7 != the real one @0x{pin[0]:05X}"
        hw = struct.unpack("<H", addi5(w, R7))[0]
        assert ((hw >> 5) & 0x3F) == 0x12 and (hw >> 11) == R7 and (hw & 0x1F) == w, \
            f"`add 0x{w:x},r7` fields are wrong"
        assert addi5(w, R7) != V55.cmp_imm5(w, R7), \
            "🛑 `add imm5` and `cmp imm5` collapsed -- the accumulate would become a no-op compare"
        assert addi5(w, R7) != addi5(w, R6), "the add's register field is not r7"
    assert len({addi5(w, R7) for w in (W_B7, W_B6, W_B5, W_B4)}) == 4, \
        "🛑 two accumulate weights encode identically -- two bits would be silently merged"
    assert V54.shl(HI_SHIFT, R7) == PIN_SHL4_R7[1], "shl 0x4,r7 != the real one @0x1C1C2"
    assert V54.shl(HI_SHIFT, R7) != V54.shl(3, R7), \
        "🛑 `shl 0x4` collapsed onto V74's `shl 0x3` -- every bit would land one position low"
    assert V54.shl(HI_SHIFT, R7) != FF.shr(HI_SHIFT, R7) and \
        V54.shl(HI_SHIFT, R7) != V55.sar(HI_SHIFT, R7), "shl collapsed onto a RIGHT shift"

    # ---- the merge and the store -------------------------------------------------------------------
    assert V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == PIN_LDBU_BYTE4[1], "the byte4 read changed"
    assert V54.andi(PAYLOAD_KEEP_MASK, R6, R6) == PIN_ANDI_7_R6[1], "andi 0x7,r6,r6 changed"
    # 🛑🛑 `or r7,r6` (0731) vs `or r6,r7` (0639) -- SAME opcode, register fields SWAPPED, and BOTH
    # are real instructions in this image, so a byte pin alone cannot catch the swap: the FIELDS are
    # decoded. V76's cave has only the MERGE form.
    ours = V54.or_rr(R7, R6)
    assert ours == PIN_OR_R7_R6[1], "or r7,r6 != the real one @0x68728"
    assert ours != V54.or_rr(R6, R7) == PIN_OR_R6_R7[1], \
        "or r7,r6 collapsed onto `or r6,r7` -- the payload would be OR'd into the SCRATCH register " \
        "and the stored byte would carry only the live status bits, reading as an all-zero probe"
    hw = struct.unpack("<H", ours)[0]
    assert ((hw >> 5) & 0x3F) == 0x08 and (hw >> 11) == R6 and (hw & 0x1F) == R7, \
        f"`or r7,r6` fields are wrong: op 0x{(hw >> 5) & 0x3F:02X} reg2 r{hw >> 11} reg1 r{hw & 0x1F}"
    assert FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP) == PIN_STB_BYTE4[1], "the byte4 store changed"
    assert HOOK_STOCK == PIN_MOVEA_HOOK[1], "the displaced hook instruction changed"
    assert FF.JMP_LP == PIN_JMP_LP[1], "jmp [lp] changed"
    _wire_model()


# =====================================================================================================
# THE LEVER -- derived, and its encoding re-derived from the FIELDS
# =====================================================================================================

def derive_gate_edit(buf):
    """The one-byte repoint, DERIVED from the two displacements -- never hand-copied.

    🛑 Returns the full 4-byte instruction both ways so the caller can assert that hw1 and hw2's HIGH
    byte are untouched. If either moved, the edit is not a displacement repoint and the claim
    "one in-place branch-operand byte" is false.
    """
    old = bytes(buf[GATE_INSN_ADDR:GATE_INSN_ADDR + 4])
    assert old == GATE_INSN_V74, \
        f"0x{GATE_INSN_ADDR:05X} is {old.hex()}, expected the V74/stock {GATE_INSN_V74.hex()}"
    new = V55.ldbu_any(-GATE_DISP_V76, 15)              # r15 -- the instruction's OWN register
    assert new == GATE_INSN_V76, \
        f"the derived repoint is {new.hex()}, the spec says {GATE_INSN_V76.hex()}"
    assert V55.ldbu_any(-GATE_DISP_V74, 15) == old, \
        "the encoder does not reproduce the STOCK gate instruction -- it cannot be trusted for the new"
    # decode BOTH by field and assert only the displacement's low byte moved
    (h1o, h2o), (h1n, h2n) = struct.unpack("<HH", old), struct.unpack("<HH", new)
    assert h1o == h1n, f"hw1 moved 0x{h1o:04X} -> 0x{h1n:04X}: this is not a displacement-only edit"
    assert (h1n >> 11) == 15 and (h1n & 0x1F) == GP, "the repointed load is not `... [gp],r15`"
    assert ((h1n >> 5) & 0x3F) == 0x3C, \
        "🛑 the opcode field is not 0x3C -- both displacements are EVEN so it MUST stay 0x3C; 0x3D " \
        "would address the neighbouring cell with every other field perfect"
    assert (h2o >> 8) == (h2n >> 8), "hw2's HIGH byte moved -- more than one byte would change"
    assert (h2o & 0xFF, h2n & 0xFF) == (GATE_BYTE_V74, GATE_BYTE_V76), \
        f"the moving byte is 0x{h2o & 0xFF:02X} -> 0x{h2n & 0xFF:02X}, spec " \
        f"0x{GATE_BYTE_V74:02X} -> 0x{GATE_BYTE_V76:02X}"
    assert (h2o & 0xFFFE) == ((0x10000 - GATE_DISP_V74) & 0xFFFE), "the old displacement is not -0x683c"
    assert (h2n & 0xFFFE) == ((0x10000 - GATE_DISP_V76) & 0xFFFE), "the new displacement is not -0x6806"
    return old, new


def assert_ladders_untouched(buf, base_img, label):
    """🛑 THE LEVER IS THE GATE, NOT THE LADDERS. Both selector spans stay byte-identical to V74."""
    for lo, hi in LADDER_SPANS.items():
        assert bytes(buf[lo:hi + 4]) == bytes(base_img[lo:hi + 4]), \
            f"{label}: the selector span 0x{lo:05X}-0x{hi:05X} MOVED -- V76 repoints the GATE'S " \
            "OPERAND, it does not rewrite the arms' selection logic"
    # the two `be +8` that route to the gate arms, decoded from the Format III field split
    for addr, raw in (PIN_LADDER_BE8_A, PIN_LADDER_BE8_B):
        got = bytes(buf[addr:addr + 2])
        assert got == raw, f"{label}: the ladder branch @0x{addr:05X} is {got.hex()}, expected {raw.hex()}"
        hw = struct.unpack("<H", got)[0]
        assert hw & 0xF == COND_BE, \
            f"{label}: the ladder branch @0x{addr:05X} is not `be` -- `bne` (0xA) would INVERT which " \
            "arm the gate selects and the whole lever would run backwards"
        d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
        d -= 0x200 if d & 0x100 else 0
        assert d == 8, f"{label}: the ladder branch @0x{addr:05X} is `be {d:+d}`, expected `be +8`"


def assert_damper_lane_frozen(buf, base_img, label):
    """🛑 V75's LEVERS MUST NOT APPEAR HERE. Every damper record on every one of the 34 modes."""
    seen = 0
    for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_C_PTRS, "FactorC"),
                       (FACTOR_D_PTRS, "FactorD"), (FACTOR_E_PTRS, "FactorE"),
                       (CEILING_PTRS, "ceiling"), (FRICTION_PTR_ARRAY, "friction")):
        for mode in ALL_MODES:
            base = factor_rec(buf, ptrs, mode)
            n = rec_len(buf, base)                      # 🛑 the record's OWN length, not a flat 0x18
            assert bytes(buf[base:base + n]) == bytes(base_img[base:base + n]), \
                f"🛑 {label}: {name} mode {mode} @0x{base:05X} MOVED. V76 is a RATE-LANE build -- " \
                "the damper lane is V75's territory and the two siblings must stay single-variable."
            seen += 1
    assert seen == 6 * len(ALL_MODES) == 204, f"{label}: only {seen} damper records checked"
    return seen


def assert_must_not_change(buf, label, stock, base_img):
    """V74's FULL keep-list, with V76's TWO edits relaxed on a COPY -- the guard is never weakened.

    🛑 The idiom (V73's, then V74's): restore the edited cells on a scratch copy, run the INHERITED
    guard unmodified, then assert the exception set is EXACTLY the bytes this build claims to move.
    A relaxation that reached one byte further would fail here.
    """
    probe = bytearray(buf)
    probe[GATE_ADDR] = GATE_BYTE_V74
    struct.pack_into("<H", probe, ARM_B_ADDR, ARM_B_V74)
    V74.assert_must_not_change(probe, label, stock, base_img)
    exc = sorted(i for i in range(START, END) if probe[i] != buf[i])
    allowed = [GATE_ADDR, ARM_B_ADDR, ARM_B_ADDR + 1]
    assert exc == allowed, \
        f"{label}: the V74-guard relaxation covers {[hex(x) for x in exc]}, expected exactly " \
        f"{[hex(x) for x in allowed]} -- V76 moves ONE gate byte and ONE 16-bit arm, nothing else"
    # ---- V76's OWN keep-list, by VALUE, on the real buffer -----------------------------------------
    for addr, raw in SAR_SITES.items():
        assert bytes(buf[addr:addr + 2]) == raw == bytes(stock[addr:addr + 2]), \
            f"{label}: the `sar` site 0x{addr:05X} is {bytes(buf[addr:addr + 2]).hex()}, expected " \
            f"the STOCK {raw.hex()} -- 🛑 reintroducing V62's `a9` CAUSES GRIND #2 and the fix is " \
            "an ABSENCE"
    for addr, want in LADDER_KEEP.items():
        assert u16(buf, addr) == want, \
            f"{label}: 0x{addr:05X} is {u16(buf, addr)}, expected {want}"
    assert u16(buf, ARM_A_ADDR) == ARM_A_VALUE, \
        f"{label}: 0xC6444 is {u16(buf, ARM_A_ADDR)} -- it ALREADY equals V67/V68's value and this " \
        "build must ASSERT it, never write it"
    assert buf[ARM_THRESHOLD_ADDR] == ARM_THRESHOLD, \
        f"{label}: the arm threshold cal 0x{ARM_THRESHOLD_ADDR:05X} is a BYTE = " \
        f"{buf[ARM_THRESHOLD_ADDR]}, expected {ARM_THRESHOLD} -- the probe's `cmp 0x5,r6` is " \
        "hard-coded against it (⚠ reading it as u16 gives 517: the V63 trap)"
    assert u16(buf, ARM_THRESHOLD_ADDR) == 517, \
        f"{label}: the u16 at 0x{ARM_THRESHOLD_ADDR:05X} is not 517 -- the byte/u16 pair is the " \
        "documented V63 trap and both halves are asserted so a widened read is caught"
    for base, want in V72_GAIN_A.items():
        assert rec4_y(buf, base) == want, \
            f"{label}: gain_A 0x{base:05X} Y is {rec4_y(buf, base)}, expected V72's {want}"
    assert buf[V72_CARRIED[0]] == V72_CARRIED[1], \
        f"{label}: the carried 0x{V72_CARRIED[0]:05X} is 0x{buf[V72_CARRIED[0]]:02X}"
    assert u16(buf, CLAMP_KEEP[0]) == CLAMP_KEEP[1], \
        f"{label}: 0x{CLAMP_KEEP[0]:05X} is {u16(buf, CLAMP_KEEP[0])}, expected {CLAMP_KEEP[1]}"
    assert_ladders_untouched(buf, stock, f"{label} (vs STOCK)")
    if base_img is not None:
        assert_damper_lane_frozen(buf, base_img, label)


# =====================================================================================================
# THE CAVE
# =====================================================================================================

def build_cave():
    """pack_v76_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        mov   0x0,r7           ; r7 = 0
        ld.h  -0x6bd0[gp],r6   ; ★ THE DAMPER OUTPUT. SIGNED (op 0x39, NOT 0x3B = st.h)
        cmp   r0,r6            ; 🛑 Z set <=> the output is exactly 0
        be    +4
        add   0x8,r7           ; bit7 = (gp-0x6bd0 != 0)   THE CROSS-BUILD ANCHOR (V74/V75 identical)
        ld.bu -0x6806[gp],r6   ; ★★★★ THE GATE. EVEN displacement -> opcode field 0x3C
        cmp   r0,r6
        be    +4
        add   0x4,r7           ; bit6 = (gp-0x6806 != 0)
        ld.bu -0x671d[gp],r6   ; 🛑 THE MASK. **ODD** displacement 0x98E3 -> opcode field 0x3D
        cmp   r0,r6
        be    +4
        add   0x2,r7           ; bit5 = (gp-0x671d != 0)   OUTRANKS the arm; sets r24 to 1024
        ld.bu -0x671a[gp],r6   ; the third arm's index. EVEN displacement -> 0x3C
        cmp   0x5,r6           ; 🛑 the BYTE cal 0xC64FA, not its u16 517
        blt   +4               ; `blt` not `bge` -- the test is `>=`, so the SKIP is on `<`
        add   0x1,r7           ; bit4 = (gp-0x671a >= 5)
        shl   0x4,r7           ; the 4-bit field -> bits 7:4.  🛑 bit3 is emitted by NOTHING.
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4   (r6 is free again: the field is in r7)
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6            ; THE MERGE. 🛑 not `or r6,r7`
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        <64 B of code + 4 B of zero pad = the same 68 B region V72..V75 carry>
    """
    _self_check_encoders()
    body = bytearray()
    listing = []
    r6_writers = []

    def emit(raw, text, writes_r6=False):
        if writes_r6:
            r6_writers.append(CAVE_BASE + len(body))
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movi5(0, R7), "mov 0x0,r7           ; r7 = 0")
    rung_idx = []

    def rung(load, cond, skip, weight, text, note):
        rung_idx.append(len(listing))
        emit(load, text, writes_r6=True)
        emit(V54.cmp_rr(R0, R6) if cond == COND_BE else V55.cmp_imm5(ARM_THRESHOLD, R6),
             "cmp r0,r6" if cond == COND_BE else f"cmp 0x{ARM_THRESHOLD:x},r6            ; the BYTE cal")
        emit(FF.bcond(cond, skip), f"b{'e' if cond == COND_BE else 'lt'} +{skip}")
        emit(addi5(weight, R7), f"add 0x{weight:x},r7            ; {note}")

    rung(V55.ldh(DAMP_DISP, R6), COND_BE, BE_SKIP, W_B7,
         f"ld.h -0x{DAMP_DISP:04x}[gp],r6  ; ★ THE DAMPER OUTPUT (SIGNED, op MUST be 0x39)",
         f"bit7 = (gp-0x{DAMP_DISP:04x} != 0)  CROSS-BUILD ANCHOR")
    rung(V55.ldbu_any(-GATE_DISP, R6), COND_BE, BE_SKIP, W_B6,
         f"ld.bu -0x{GATE_DISP:04x}[gp],r6 ; ★★★★ THE GATE (EVEN disp -> op 0x3C)",
         f"bit6 = (gp-0x{GATE_DISP:04x} != 0)  THE GATE")
    rung(V55.ldbu_any(-MASK_DISP, R6), COND_BE, BE_SKIP, W_B5,
         f"ld.bu -0x{MASK_DISP:04x}[gp],r6 ; 🛑 THE MASK (**ODD** disp -> op 0x3D)",
         f"bit5 = (gp-0x{MASK_DISP:04x} != 0)  MASKING RISK")
    rung(V55.ldbu_any(-ARM3_DISP, R6), COND_BLT, BLT_SKIP, W_B4,
         f"ld.bu -0x{ARM3_DISP:04x}[gp],r6 ; the third arm's index",
         f"bit4 = (gp-0x{ARM3_DISP:04x} >= {ARM_THRESHOLD})")
    shl_idx = len(listing)
    emit(V54.shl(HI_SHIFT, R7),
         f"shl 0x{HI_SHIFT:x},r7            ; the 4-bit field -> 7:4  (bit3 emitted by NOTHING)")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4",
         writes_r6=True)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6       ; keep live status bits 2:0",
         writes_r6=True)
    emit(V54.or_rr(R7, R6), "or r7,r6             ; THE MERGE  🛑 NOT `or r6,r7`", writes_r6=True)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]  ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6  ; re-exec displaced instruction", writes_r6=True)
    ret_addr = CAVE_BASE + len(body)
    emit(FF.JMP_LP, "jmp [lp]             ; -> 0x55C12")
    code_len = len(body)

    # ---- 🛑🛑 FLAG LIVENESS: every branch must read its OWN cmp's flags. --------------------------
    for i in rung_idx:
        ld, cm, br, ad = listing[i], listing[i + 1], listing[i + 2], listing[i + 3]
        assert ld[0] + len(ld[1]) == cm[0] and cm[0] + 2 == br[0] and br[0] + 2 == ad[0], \
            f"rung at listing[{i}] is not contiguous load/cmp/branch/add -- the branch would read " \
            "STALE flags from an earlier compare"
        assert ((struct.unpack("<H", cm[1])[0] >> 5) & 0x3F) in (0x0F, 0x13), \
            f"listing[{i + 1}] is not a `cmp`"
        assert (struct.unpack("<H", br[1])[0] >> 7) & 0xF == 0xB, \
            f"listing[{i + 2}] is not a Bcond -- the compare would fall through unconditionally"
        assert ((struct.unpack("<H", ad[1])[0] >> 5) & 0x3F) == 0x12, \
            f"listing[{i + 3}] is not an `add imm5`"
    conds = [struct.unpack("<H", listing[i + 2][1])[0] & 0xF for i in rung_idx]
    assert conds == [COND_BE, COND_BE, COND_BE, COND_BLT], \
        f"the rung conditions are {[hex(c) for c in conds]} -- expected three `be` (zero tests) and " \
        "one `blt` (the >= threshold). `bne`/`bge` would invert the rung it guards."

    # ---- GATE 2a: EVERY branch lands EXACTLY on an emitted instruction boundary -------------------
    bounds = {a for a, _r, _t in listing}
    branches = [(i, a, r) for i, (a, r, _t) in enumerate(listing)
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    assert len(branches) == 4, f"the cave has {len(branches)} Bcond(s), expected exactly 4"
    for i, a, raw in branches:
        hw = struct.unpack("<H", raw)[0]
        # 🛑 the displacement is DECODED from the Format III field split, never taken from the
        # constant we meant to encode -- that form would pass on any displacement.
        d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
        d -= 0x200 if d & 0x100 else 0
        tgt = a + d
        assert d > 0, f"branch @0x{a:05X} is BACKWARD (d = {d}) -- the cave must be straight-line"
        assert tgt in bounds, \
            f"`b{hw & 0xF:x} {d:+d}` @0x{a:05X} targets 0x{tgt:05X}, NOT an instruction boundary"
        assert a < tgt <= ret_addr, f"branch @0x{a:05X} escapes the cave body"
        assert tgt == listing[i + 2][0], \
            f"branch @0x{a:05X} does not skip exactly the 2-byte `add` it guards"

    # ---- GATE 2b: r6/r7 liveness. Only the loads/masks may write r6; only r7 accumulates. --------
    for idx, (addr, raw, text) in enumerate(listing):
        if len(raw) > 4 or raw == FF.JMP_LP:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        if (hw >> 7) & 0xF == 0xB:                                # a Bcond writes no GPR
            continue
        if ((hw >> 5) & 0x3F) in (0x13, 0x0F):                    # cmp -- flags only
            continue
        if raw == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP):            # a store's reg2 is the SOURCE
            continue
        want = R6 if addr in r6_writers else R7
        assert (hw >> 11) == want, \
            f"r6/r7 liveness: listing[{idx}] '{text}' writes r{hw >> 11}, not r{want}"
    # ---- GATE 1 as a property of the EMITTED CODE: EXACTLY ONE store ------------------------------
    store_idx = [i for i, (_a, raw, _t) in enumerate(listing)
                 if len(raw) == 4 and ((struct.unpack_from("<H", raw, 0)[0] >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert len(store_idx) == 1, f"the cave must contain EXACTLY ONE store, found {store_idx}"
    assert listing[store_idx[0]][1] == FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), \
        "the sole store is not the CAN-330 payload byte"
    for idx, (_a, raw, text) in enumerate(listing):
        if len(raw) > 4:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0b0111 or len(raw) >= 4, \
            f"listing[{idx}] '{text}' looks like a Format-IV sst -- an unaccounted store"
        assert raw == FF.JMP_LP or ((hw >> 5) & 0x3F) not in (0x1E, 0x1B), \
            f"'{text}' is a jr/jarl -- the cave must have a SINGLE exit"

    # ---- geometry ---------------------------------------------------------------------------------
    assert all(i + 3 < shl_idx for i in rung_idx), \
        "🛑 a rung sits AFTER the `shl 0x4,r7` -- its weight would land 4 bits low and the bit would " \
        "be silently relabelled"
    assert listing[shl_idx][1] == V54.shl(HI_SHIFT, R7), "listing[shl_idx] is not the `shl 0x4,r7`"
    assert [i for i, (_a, r, _t) in enumerate(listing) if r == V54.or_rr(R6, R7)] == [], \
        "the cave contains the ACCUMULATE `or r6,r7` -- V76 has only the MERGE `or r7,r6`"
    assert len({listing[i][1] for i in rung_idx}) == 4, \
        "🛑 two rungs load the SAME cell -- one of the four probed cells is not being read"
    ret_idx = [i for i, (_a, r, _t) in enumerate(listing) if r == FF.JMP_LP]
    # 1 seed + 4 rungs x 4 + shl + ld.bu + andi + or + st.b + movea + jmp = 24 instructions
    assert ret_idx == [len(listing) - 1] == [23], f"`jmp [lp]` is at {ret_idx}, expected index 23"
    assert listing[-2][1] == HOOK_STOCK, "the displaced movea must precede the return"
    assert body.count(HOOK_STOCK) == 1, "the displaced movea appears more than once"
    assert len(listing) == 1 + 4 * len(rung_idx) + 7 == 24, \
        f"{len(listing)} instructions, expected 24"
    assert code_len == 64, f"the cave code is {code_len}B, expected 64B (4 rungs x 10 + 24)"
    # ⊕ the zero pad -- V74's own precedent (46 B of code + 22 B of pad in the same 68 B region).
    body.extend(b"\x00" * PAD_BYTES)
    assert len(body) == CAVE_EXTENT == 68, \
        f"the cave region is {len(body)}B != the PROVEN {CAVE_EXTENT}B -- caves brick ECUs"
    assert code_len + PAD_BYTES == CAVE_EXTENT, "the pad does not close the region exactly"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    return bytes(body), listing, code_len


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, in Python, from raw bytes.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. Kept self-contained ON PURPOSE: this is the readback's independent witness, so it must
    not inherit the builder's assumptions.
    """
    out, i = [], 0
    while i < len(raw):
        hw = struct.unpack_from("<H", raw, i)[0]
        op6 = (hw >> 5) & 0x3F
        reg2, reg1 = hw >> 11, hw & 0x1F
        if hw == 0x0000:
            n, m = 2, "nop"
        elif (hw >> 7) & 0xF == 0xB:                                      # Format III Bcond
            n = 2
            m = {0x6: "blt", 0xE: "bge", 0xA: "bne", 0x2: "be"}.get(hw & 0xF, f"b?{hw & 0xF:x}")
            d = (((hw >> 11) & 0x1F) << 4) | (((hw >> 4) & 0x7) << 1)
            d -= 0x200 if d & 0x100 else 0
            m = f"{m} {d:+d}"
        elif op6 in (0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3F, 0x31, 0x36):     # 4-byte disp/imm forms
            n = 4
            hw2 = struct.unpack_from("<H", raw, i + 2)[0]
            disp = hw2 - 0x10000 if hw2 & 0x8000 else hw2
            # 🛑 op 0x3F is ld.hu when hw2's LSB is SET and ld.w when it is CLEAR; ld.bu (0x3C/0x3D)
            # carries the displacement's own bit 0 in the OPCODE FIELD and also sets hw2's LSB.
            m = {0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h", 0x3C: "ld.bu", 0x3D: "ld.bu",
                 0x3F: "ld.hu" if hw2 & 1 else "ld.w", 0x31: "movea", 0x36: "andi"}[op6]
            if op6 in (0x31, 0x36):
                m = f"{m} 0x{hw2:04x},r{reg1},r{reg2}"
            else:
                eff = (disp & ~1) | (op6 & 1 if op6 in (0x3C, 0x3D) else 0) \
                    if op6 in (0x3C, 0x3D, 0x3F) else disp
                # a STORE's reg2 field is the SOURCE, not the destination -- print it that way, so a
                # store can never be misread as a load in the readback evidence.
                m = (f"{m} r{reg2},{eff}[r{reg1}]" if op6 in (0x3A, 0x3B)
                     else f"{m} {eff}[r{reg1}],r{reg2}")
        elif hw == 0x007F or (op6 == 0x03 and reg2 == 0):
            n, m = 2, "jmp [lp]"
        elif op6 == 0x10:
            n, m = 2, f"mov {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 == 0x12:
            n, m = 2, f"add {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 == 0x13:
            n, m = 2, f"cmp {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 in (0x14, 0x15, 0x16):
            n, m = 2, f"{ {0x14: 'shr', 0x15: 'sar', 0x16: 'shl'}[op6] } 0x{hw & 0x1F:x},r{reg2}"
        elif op6 == 0x0C:
            n, m = 2, f"subr r{reg1},r{reg2}"
        elif op6 == 0x0F:
            n, m = 2, f"cmp r{reg1},r{reg2}"
        elif op6 == 0x08:
            n, m = 2, f"or r{reg1},r{reg2}"
        else:
            n, m = 2, f"?? 0x{hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


# =====================================================================================================
# Censuses -- raw byte scans, because `search_instructions` silently undercounts
# =====================================================================================================

def assert_probe_censuses(buf, cave_span, expect, label):
    """GATE 1 (RAM ownership) for every probed cell, as a MEASUREMENT from raw bytes.

    ★★ THIS IS ALSO THE STRUCTURAL PROOF OF THE REPOINT, and it is TWO-SIDED: `gp-0x683c` must go
    1 firmware reader -> 0 and `gp-0x6806` 13 -> 14, with the new reader at EXACTLY 0x3AA94.
    """
    out = {}
    for disp, (n_read, n_write, rmn, wmn) in CENSUS_BASE.items():
        want_r, want_w, _rm, _wm = expect[disp]
        reads, writes, cave = V74.cell_census(buf, disp, cave_span)
        assert all(m in rmn for _a, m, _r in reads), \
            f"{label} gp-0x{disp:04x}: unexpected read WIDTH/SIGN -- " \
            f"{sorted({m for _a, m, _r in reads})}"
        assert all(m in wmn for _a, m, _r in writes), f"{label} gp-0x{disp:04x}: unexpected write WIDTH"
        assert len(reads) == want_r, \
            f"{label} gp-0x{disp:04x} has {len(reads)} firmware readers, expected {want_r} " \
            f"({[hex(a) for a, _m, _r in reads]})"
        assert len(writes) == want_w, \
            f"{label} gp-0x{disp:04x} has {len(writes)} firmware writers, expected {want_w}"
        assert len(cave) == CAVE_ACCESS_ON_BASE[disp] if expect is CENSUS_BASE else True
        assert all(m.startswith("ld.") and r == R6 for _a, m, r in cave), \
            f"{label} gp-0x{disp:04x}: a cave access is not a load into r{R6} -- a STORE here would " \
            "CORRUPT the cell"
        out[disp] = (len(reads), len(writes), [a for a, _m, _r in reads])
    # the writer SETS, address by address
    for disp, writers in ((DAMP_DISP, DAMP_WRITERS), (MASK_DISP, MASK_WRITERS),
                          (ARM3_DISP, ARM3_WRITERS)):
        _r, w, _c = V74.cell_census(buf, disp, cave_span)
        assert [a for a, _m, _r in w] == writers, \
            f"{label} gp-0x{disp:04x} writers moved: {[hex(a) for a, _m, _r in w]}"
    # every cave access count, on BOTH the probed cells and the two cells V76 must NOT read
    want_cave = CAVE_ACCESS_ON_BASE if expect is CENSUS_BASE else CAVE_ACCESS_ON_OUTPUT
    for disp, n in want_cave.items():
        _r, _w, cave = V74.cell_census(buf, disp, cave_span)
        assert len(cave) == n, \
            f"🛑 {label}: the cave makes {len(cave)} access(es) to gp-0x{disp:04x} " \
            f"{[(hex(a), m, r) for a, m, r in cave]}, expected {n}. On the INPUT that means the base " \
            "is not a V74 cave; on the OUTPUT it means the V74 cave survived."
    # 🛑 ALL THREE lockstep shadows must be untouched by the cave, on BOTH images.
    for disp, whose in SHADOW_DISPS.items():
        _r, _w, scave = V74.cell_census(buf, disp, cave_span)
        assert not scave, f"{label}: the cave touches {whose} lockstep shadow gp-0x{disp:04x}"
    return out


def assert_repoint_census(before, after):
    """★★ THE TWO-SIDED STRUCTURAL PROOF. A one-byte edit that missed cannot produce this pair."""
    assert before[DEAD_DISP][0] == 1 and after[DEAD_DISP][0] == 0, \
        f"gp-0x{DEAD_DISP:04x} readers {before[DEAD_DISP][0]} -> {after[DEAD_DISP][0]}, expected " \
        "1 -> 0: the DEAD cell must be abandoned by the repoint"
    assert before[DEAD_DISP][2] == [GATE_INSN_ADDR], \
        f"the dead cell's single reader was at {[hex(a) for a in before[DEAD_DISP][2]]}, not " \
        f"0x{GATE_INSN_ADDR:05X} -- the base is not the image this build assumes"
    assert after[GATE_DISP][0] == before[GATE_DISP][0] + 1 == 14, \
        f"gp-0x{GATE_DISP:04x} readers {before[GATE_DISP][0]} -> {after[GATE_DISP][0]}, expected 13 -> 14"
    new = sorted(set(after[GATE_DISP][2]) - set(before[GATE_DISP][2]))
    assert new == [GATE_INSN_ADDR], \
        f"the NEW gp-0x{GATE_DISP:04x} reader is at {[hex(a) for a in new]}, expected exactly " \
        f"0x{GATE_INSN_ADDR:05X} -- the repointed byte landed somewhere else"
    assert set(before[GATE_DISP][2]) <= set(after[GATE_DISP][2]), \
        "the repoint REMOVED an existing gp-0x6806 reader"
    assert after[GATE_DISP][1] == before[GATE_DISP][1] == GATE_WRITER_COUNT, \
        "the gate cell's writer set moved -- V76 only adds a READER"


def assert_decoder_matches(cave_bytes):
    """🛑 The decoder's CAVE_HEX must equal the cave just emitted, so it cannot drift."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, "V76: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"V76: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    for token in ("V76", os.path.basename(BIN_OUT), "0x6806", "0x671D", "0x671A", "0x6BD0"):
        assert token in txt, f"V76: the decoder does not carry '{token}'"
    for name, val in (("BIT_DAMP_NZ", BIT_DAMP_NZ), ("BIT_GATE", BIT_GATE), ("BIT_MASK", BIT_MASK),
                      ("BIT_ARM3", BIT_ARM3), ("BIT_UNUSED", BIT_UNUSED), ("PROBE_MASK", PROBE_MASK),
                      ("ARM_THRESHOLD", ARM_THRESHOLD)):
        mm = re.search(rf"^{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", txt, re.M)
        assert mm and int(mm.group(1), 0) == val, \
            f"V76: the decoder's {name} is {mm and mm.group(1)}, not {val}"
    mm = re.search(r"^LEGAL_PAYLOADS\s*=\s*\(([^)]*)\)", txt, re.M)
    assert mm and tuple(int(x, 0) for x in mm.group(1).replace(",", " ").split()) == LEGAL_PAYLOADS, \
        "V76: the decoder's LEGAL_PAYLOADS does not match the 16 reachable payloads"
    for claim in ("THE GATE", "MASKING RISK", "CROSS-BUILD ANCHOR", "BIT3"):
        assert claim in txt.upper(), f"V76: the decoder never states '{claim}'"
    for stale in ("0x67FA", "0x6AC2", "0x69A4", "0x63FD"):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale}", txt, re.M | re.I), \
            f"V76: {stale} is still a LIVE RUNG in the decoder"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it."
    assert f"{GATE_BYTE_V76:02x}" in os.path.basename(BIN_OUT).lower() and \
        str(ARM_B_V76) in os.path.basename(BIN_OUT) and str(ARM_B_V76) in os.path.basename(OUT), \
        "🛑 the lever set is not in BOTH filenames -- the filename is the ONLY pre-drive " \
        "discriminator between cuts (two V70 cuts once shared a name and the second overwrote the " \
        "first's snapshot)"

    v74 = bytearray(Path(SRC_BIN).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V74): {SRC_BIN}\n  SHA256 {hashlib.sha256(bytes(v74)).hexdigest()}")
    print(f"STOCK:        {STOCK_BIN}")
    for name, img in (("V74", v74), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert hashlib.sha256(bytes(v74)).hexdigest() == SRC_SHA256, \
        f"🛑 THE BASE IS NOT V74. SHA256 is {hashlib.sha256(bytes(v74)).hexdigest()}, expected " \
        f"{SRC_SHA256}. V76 is defined as V74 + these edits; any other base voids every claim."
    print("  ✅ the base SHA256 matches the recorded V74 image exactly.")

    # ---- 🛑 THE LEVER VALUES ARE READ OUT OF V67 AND V68, NOT QUOTED FROM THIS FILE ---------------
    print("\n  🛑 THE TWO LEVER VALUES, CROSS-CHECKED AGAINST THE IMAGES V76 REPRODUCES:")
    for path, who in ((V67_BIN, "V67"), (V68_BIN, "V68")):
        ref = Path(path).read_bytes()
        assert ref[GATE_ADDR] == GATE_BYTE_V76, \
            f"{who} carries 0x{ref[GATE_ADDR]:02X} at 0x{GATE_ADDR:05X}, not 0x{GATE_BYTE_V76:02X}"
        assert u16(ref, ARM_B_ADDR) == ARM_B_V76, \
            f"{who} carries {u16(ref, ARM_B_ADDR)} at 0x{ARM_B_ADDR:05X}, not {ARM_B_V76}"
        assert u16(ref, ARM_A_ADDR) == ARM_A_VALUE, f"{who}'s 0xC6444 is not {ARM_A_VALUE}"
        assert bytes(ref[GATE_INSN_ADDR:GATE_INSN_ADDR + 4]) == GATE_INSN_V76, \
            f"{who}'s repointed instruction is not {GATE_INSN_V76.hex()}"
        print(f"     {who}: 0x{GATE_ADDR:05X} = 0x{ref[GATE_ADDR]:02X} · "
              f"0x{ARM_B_ADDR:05X} = {u16(ref, ARM_B_ADDR)} · 0x{ARM_A_ADDR:05X} = "
              f"{u16(ref, ARM_A_ADDR)} · insn @0x{GATE_INSN_ADDR:05X} = "
              f"{bytes(ref[GATE_INSN_ADDR:GATE_INSN_ADDR + 4]).hex()}   ✅ matches this build's spec")

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    V74.assert_must_not_change(v74, "V74 source", stock, None)
    assert v74[GATE_ADDR] == GATE_BYTE_V74 and u16(v74, ARM_B_ADDR) == ARM_B_V74, \
        "the V74 source is already gated or already armed -- it is not the recorded base"
    assert walk_all_blocks(bytes(v74)) == 0, "the V74 source's own CRC chain does not verify"
    cens_before = assert_probe_censuses(bytes(v74), cave_span, CENSUS_BASE, "V74 source")
    print("\n  ✅ every MUST-NOT-CHANGE site, the six pointer arrays over all 34 modes, the config")
    print("     table, V72's LEVER C, the carried 0x454FE, the UNGATED gate byte, V57's decoupling,")
    print("     V53's eleven STOCK_CALS and the full CRC chain: all verified ON THE INPUT.")

    rows, ENGAGED, DISENGAGED = V74.derive_mode_columns(bytes(v74))
    assert tuple(ENGAGED) == ENGAGED_EXPECTED and tuple(DISENGAGED) == DISENGAGED_EXPECTED, \
        "V76's own independent statement of the mode columns disagrees with the derivation"
    print(f"\n  ⊕ THE CONFIG TABLE, derived on the image being built: row {THIS_CAR_ROW} "
          f"{THIS_CAR_KEY!r}, live mode {LIVE_MODE}.")
    print("     🛑 V76's lever is MODE-PROOF -- it is reached by plain tp-relative scalars, so the")
    print(f"     mode columns are stated for the record only. NO mode-indexed table is written.")

    code = bytearray(v74)

    # ---- LEVER 1 -- the one-byte gate repoint ------------------------------------------------------
    print(f"\n  LEVER 1 -- THE GATE REPOINT @0x{GATE_INSN_ADDR:05X}:")
    old_insn, new_insn = derive_gate_edit(code)
    code[GATE_INSN_ADDR:GATE_INSN_ADDR + 4] = new_insn
    print(f"    0x{GATE_INSN_ADDR:05X}  {old_insn.hex()} -> {new_insn.hex()}   "
          f"`ld.bu -0x{GATE_DISP_V74:04x}[gp],r15` -> `ld.bu -0x{GATE_DISP_V76:04x}[gp],r15`")
    moved = [i for i in range(GATE_INSN_ADDR, GATE_INSN_ADDR + 4) if code[i] != v74[i]]
    assert moved == [GATE_ADDR], \
        f"the repoint moved {[hex(x) for x in moved]}, expected exactly [0x{GATE_ADDR:05X}] -- " \
        "'one in-place branch-operand byte' is the whole claim"
    print(f"    ✅ EXACTLY ONE BYTE MOVED: 0x{GATE_ADDR:05X} 0x{GATE_BYTE_V74:02X} -> "
          f"0x{GATE_BYTE_V76:02X}. hw1 and hw2's high byte are byte-identical.")
    print(f"    ★ THE CRUX, Ghidra-read on the stock image: 0x{GATE_CONSUMER[0]:05X} `cmp r0,r15` ; "
          f"0x{GATE_CONSUMER[1]:05X} `setfne lp`")
    print("      ⇒ lp = (the gate cell != 0), and BOTH selector ladders branch on `lp`. Repointing")
    print("      the LOAD is therefore sufficient; no other instruction needs to change.")

    # ---- LEVER 2 -- r24's gate-active arm ----------------------------------------------------------
    print(f"\n  LEVER 2 -- r24's GATE-ACTIVE ARM:")
    assert u16(code, ARM_B_ADDR) == ARM_B_V74, f"0x{ARM_B_ADDR:05X} is not {ARM_B_V74}"
    struct.pack_into("<H", code, ARM_B_ADDR, ARM_B_V76)
    print(f"    0x{ARM_B_ADDR:05X}  {ARM_B_V74:5d} -> {ARM_B_V76:5d}   read by "
          f"`ld.hu 0x7446,tp,r10` @0x3AC08 when the gate fires")
    print(f"    0x{ARM_A_ADDR:05X}  {ARM_A_VALUE:5d} -> {ARM_A_VALUE:5d}   ⊕ NOT WRITTEN -- it "
          f"already equals V67/V68's value. ASSERTED only.")
    r24 = ARM_B_V76 / GAIN_B_CREEP_LERP
    r26 = ARM_A_VALUE / GAIN_A_CREEP_LERP
    assert abs(r24 - R24_RATIO_EXPECT) < 1e-9 and abs(r26 - R26_RATIO_EXPECT) < 1e-9, \
        f"the derived ratios are r24 {r24}, r26 {r26} -- the spec says {R24_RATIO_EXPECT} / " \
        f"{R26_RATIO_EXPECT}"
    print(f"\n    ⚠ THIS IS A TWO-LANE LEVER AND ALWAYS WAS -- both numbers recomputed from the bytes:")
    print(f"       r24: {ARM_B_V76} / {GAIN_B_CREEP_LERP} (gain_B's creep LERP) = **{r24:.5f}x**")
    print(f"       r26: {ARM_A_VALUE} / {GAIN_A_CREEP_LERP} (gain_A's creep LERP) = "
          f"**{r26:.5f}x = /{1 / r26:.2f} EXACTLY**")
    print(f"       net vs stock = (5244 + 512a)/(3072 + 3072a), a = gp-0x69a4/1024; parity at "
          f"a = {PARITY_A}.")
    print("       ⇒ V76 REPRODUCES V67/V68's CONFIG. It does not claim to know which lane did the work.")

    # ---- THE PROBE ---------------------------------------------------------------------------------
    print(f"\n  THE PROBE (64 B of code + {PAD_BYTES} B zero pad = the {CAVE_EXTENT} B region):")
    cave_bytes, cave_listing, code_len = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<10s} {text}")
    print(f"    0x{CAVE_BASE + code_len:05X}  {'00' * PAD_BYTES:<10s} "
          f"<{PAD_BYTES} B zero pad -- closes the {CAVE_EXTENT} B region (V74: 46 B code + 22 B pad)>")
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v74[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical to the base"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"the hook is not `jarl 0x{CAVE_BASE:05X}` -- the cave would never be entered"
    disp_off = cave_listing[-2][0] - CAVE_BASE
    assert bytes(code[CAVE_BASE + disp_off:CAVE_BASE + disp_off + 4]) == HOOK_STOCK, \
        f"the displaced original is not at cave offset 0x{disp_off:02X}"
    assert bytes(code[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        f"0x{HOOK_RETURN:05X} is not `mov 0x8,r7` -- the proof that r7 is DEAD across the hook is void"
    print(f"    ★ r7 IS PROVABLY DEAD ACROSS THE HOOK: 0x{HOOK_RETURN:05X} (where the cave returns) "
          f"is `mov 0x8,r7` = {HOOK_RETURN_INSN.hex()},")
    print("      which overwrites it immediately. r6 is restored by re-executing the displaced movea.")

    cens_after = assert_probe_censuses(bytes(code), cave_span, CENSUS_OUT, "V76")
    assert_repoint_census(cens_before, cens_after)
    print("\n    ✅ GATE 1 (RAM ownership), asserted as a MEASUREMENT from raw bytes:")
    for disp, (r, w, _a) in cens_after.items():
        print(f"       gp-0x{disp:04x}  {r:2d}r / {w:2d}w firmware" +
              (f"  + EXACTLY ONE cave load, never a store." if CAVE_ACCESS_ON_OUTPUT[disp]
               else "   (no cave access)"))
    print(f"    ★★ THE TWO-SIDED PROOF OF THE REPOINT:")
    print(f"       gp-0x{DEAD_DISP:04x} (the DEAD cell)  {cens_before[DEAD_DISP][0]}r -> "
          f"{cens_after[DEAD_DISP][0]}r     -- abandoned")
    print(f"       gp-0x{GATE_DISP:04x} (THE GATE)       {cens_before[GATE_DISP][0]}r -> "
          f"{cens_after[GATE_DISP][0]}r    -- the NEW reader is at exactly 0x{GATE_INSN_ADDR:05X}")
    print(f"       A one-byte edit that missed, or landed on another cell, cannot produce that pair.")
    print(f"       ⊕ The cave reads gp-0x{STATE_DISP:04x} {CAVE_ACCESS_ON_OUTPUT[STATE_DISP]} times "
          f"(V74's state cell) and gp-0x{BACKDRIVE_DISP:04x} "
          f"{CAVE_ACCESS_ON_OUTPUT[BACKDRIVE_DISP]} times (V75's) -- asserted, so neither sibling's")
    print("       cave can masquerade as this one.")
    print(f"       All three lockstep shadows untouched: "
          f"{', '.join(f'gp-0x{d:04x} ({w})' for d, w in SHADOW_DISPS.items())}.")
    print(f"\n    ★ THE PAYLOAD ALPHABET: four INDEPENDENT bits ⇒ all {len(LEGAL_PAYLOADS)} of "
          f"{{0x00..0xF0 step 0x10}} are reachable and nothing else.")
    print("       🛑 bit3 is emitted by NO instruction ⇒ 0 on EVERY frame. V74's own on-car payload")
    print("       (0x28/0xA8, state 5 ⇒ bits 6:3 = 0b0101) has bit3 SET on every frame, so ONE frame")
    print("       rejects a V74 log. V75's alphabet is the 10 thermometer values with")
    print("       bit4=>bit5=>bit6=>bit7; V76's bits are independent, so 0x10/0x20/0x30/0x40/0x50/")
    print("       0x60/0x70/0x90/0xA0/0xB0/0xD0 are legal here and ILLEGAL there.")

    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/decode_v76_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 RE-DISASSEMBLE THE CAVE FROM THE BUILT BYTES, IN PYTHON -------------------------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE (raw Python decoder, NOT a Ghidra database):")
    redis = redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + code_len]))
    for (a, raw, m) in redis:
        print(f"    0x{a:05X}  {raw.hex():<10s} {m}")
    assert [r for _a, r, _m in redis] == [r for _a, r, _t in cave_listing], \
        "the re-disassembly's bytes differ from the emitted listing"
    assert [a for a, _r, _m in redis] == [a for a, _r, _t in cave_listing], \
        "the re-disassembly does not land on the same instruction boundaries as the build listing"
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        "the re-disassembly contains a nop or an undecoded halfword inside the CODE"
    assert bytes(code[CAVE_BASE + code_len:CAVE_BASE + CAVE_EXTENT]) == b"\x00" * PAD_BYTES, \
        "the pad is not zero"
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    assert len(stores) == 1 and stores[0][1] == f"st.b r{R6},{-PAYLOAD_BYTE4_DISP}[r{GP}]", \
        f"the re-disassembly finds stores {stores} -- expected exactly ONE st.b to the CAN payload"
    loads = [m for _a, _r, m in redis if m.startswith(("ld.bu ", "ld.h ", "ld.hu ", "ld.w "))]
    assert loads == [f"ld.h {-DAMP_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-GATE_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-MASK_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-ARM3_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-PAYLOAD_BYTE4_DISP}[r{GP}],r{R6}"], \
        f"the re-disassembled load sequence is {loads} -- the four probed cells, in order, then byte4"
    ors = [m for _a, _r, m in redis if m.startswith("or ")]
    assert ors == [f"or r{R7},r{R6}"], \
        f"the re-disassembled `or` sequence is {ors} -- V76 has ONLY the merge `or r7,r6`"
    brs = [(a, m) for a, _r, m in redis if m.startswith(("be ", "bne ", "blt ", "bge ", "b?"))]
    assert [m for _a, m in brs] == [f"be +{BE_SKIP}"] * 3 + [f"blt +{BLT_SKIP}"], \
        f"the re-disassembled branch sequence is {[m for _a, m in brs]} -- three `be` then one `blt`"
    bounds = [a for a, _r, _m in redis]
    for a, m in brs:
        assert a + int(m.split("+")[1]) in bounds, \
            f"the branch `{m}` @0x{a:05X} does not target an instruction boundary in the readback"
    cmps = [m for _a, _r, m in redis if m.startswith("cmp")]
    assert cmps == [f"cmp r{R0},r{R6}"] * 3 + [f"cmp {ARM_THRESHOLD},r{R6}"], \
        f"the re-disassembled compares are {cmps}"
    adds = [(a, m) for a, _r, m in redis if m.startswith("add ")]
    assert [m for _a, m in adds] == [f"add {w},r{R7}" for w in (W_B7, W_B6, W_B5, W_B4)], \
        f"the re-disassembled accumulate sequence is {[m for _a, m in adds]}"
    shl_a = [a for a, _r, m in redis if m == f"shl 0x{HI_SHIFT:x},r{R7}"]
    assert len(shl_a) == 1 and adds[-1][0] < shl_a[0], \
        "🛑 the `shl 0x4,r7` does not follow all four `add`s -- a bit would be relabelled"
    print("    ✅ ONE `ld.h` (the damper, SIGNED) + THREE `ld.bu` (gate / mask / arm3, with the ODD-")
    print("       displacement form 0x3D on gp-0x671d) + the byte4 read, exactly ONE store, four")
    print("       branches all landing on emitted BOUNDARIES, and the `shl 0x4` after all four adds.")

    # ---- the built gate instruction, re-decoded from the BUILT bytes -------------------------------
    got = bytes(code[GATE_INSN_ADDR:GATE_INSN_ADDR + 4])
    gh1, gh2 = struct.unpack("<HH", got)
    gdisp = (gh2 & 0xFFFE) | ((gh1 >> 5) & 1)
    gsigned = gdisp - 0x10000 if gdisp & 0x8000 else gdisp
    assert got == GATE_INSN_V76 and gsigned == -GATE_DISP_V76 and ((gh1 >> 5) & 0x3F) == 0x3C \
        and (gh1 >> 11) == 15 and (gh1 & 0x1F) == GP, \
        f"the BUILT gate instruction decodes to disp {gsigned:+#x} -- expected -0x{GATE_DISP_V76:04x}"
    print(f"\n  🛑 THE GATE INSTRUCTION, RE-DECODED FROM THE BUILT BYTES BY FIELD:")
    print(f"    0x{GATE_INSN_ADDR:05X}  {got.hex()}  hw1 0x{gh1:04X} (reg2 r{gh1 >> 11}, op "
          f"0x{(gh1 >> 5) & 0x3F:02X}, reg1 r{gh1 & 0x1F}) · hw2 0x{gh2:04X}")
    print(f"    ⇒ `ld.bu {gsigned:+#x}[gp],r15` = `ld.bu -0x{GATE_DISP_V76:04x}[gp],r15`  ✅ THE GATE")

    # ---- the untouched sites, re-asserted on the finished image ------------------------------------
    assert_must_not_change(code, "V76", stock, v74)
    assert_ladders_untouched(code, v74, "V76 (vs V74)")
    print("\n  ✅ THE FULL KEEP-LIST RE-ASSERTED ON THE FINISHED IMAGE: both `sar` sites at stock,")
    print("     0xC643E/0xC6440/0xC6442/0xC6444, the BYTE cal 0xC64FA = 5 (and its u16 = 517 twin),")
    print("     V72's gain_A r26 cut, the carried 0x454FE, the clamp at 850, BOTH selector spans,")
    print("     the six pointer arrays over all 34 modes, the config table, V57's decoupling, V53's")
    print("     STOCK_CALS, and ALL 204 damper records (FactorB/C/D/E + ceiling + friction x 34")
    print("     modes) byte-identical to V74 ⇒ V75's levers are provably ABSENT.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = [CAVE_BASE, GATE_ADDR, ARM_B_ADDR]
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC4FFC, 0xC6FFC]
    assert [b[1] for b in blocks] == expect_trailers, \
        f"expected trailers {[hex(t) for t in expect_trailers]}, got {[hex(b[1]) for b in blocks]}"
    print(f"\n  CRC -- EXACTLY {len(blocks)} blocks move (asserted, not observed):")
    for blk in blocks:
        old = struct.unpack_from("<I", code, blk[1])[0]
        new = zlib.crc32(code[blk[0]:blk[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new)
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old:08X} -> 0x{new:08X}")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    nbad = walk_all_blocks(bytes(code))
    assert nbad == 0, f"CRC chain FAILED: {nbad} mismatching block(s)"
    print("    ✅ full CRC chain re-walked: 50/50 blocks PASS (0 mismatches)")
    # 🛑 [0xC5000, 0xC5FFC) is CRC-SKIPPED by the bootloader and carries the V40 ignition-brick
    # precedent. Checked over the FULL byte extent of every edit, not just its base address.
    all_edit_bytes = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)) | {GATE_ADDR} | \
        {ARM_B_ADDR, ARM_B_ADDR + 1}
    assert not [a for a in all_edit_bytes if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"
    print(f"    ✅ NOTHING of the {len(all_edit_bytes)} edited bytes lands in [0xC5000,0xC5FFC) -- "
          "the CRC-skipped block, V40 ignition precedent.")

    # ---- the attributed diff -- ONE BUCKET PER LEVER ----------------------------------------------
    def attribute(d):
        return ("PROBE cave (6bd0 / 6806 gate / 671d mask / 671a arm3)" if d in cave_span else
                f"LEVER 1  gate repoint 0x{GATE_BYTE_V74:02X}->0x{GATE_BYTE_V76:02X} "
                f"(-0x683c => -0x6806)" if d == GATE_ADDR else
                f"LEVER 2  0xC6446 r24 arm {ARM_B_V74}->{ARM_B_V76}"
                if d in (ARM_B_ADDR, ARM_B_ADDR + 1) else None)

    d74 = [i for i in range(START, END) if code[i] != v74[i]]
    f74 = [d for d in d74 if d not in crc_only]
    stray = [d for d in f74 if attribute(d) is None]
    assert not stray, f"UNATTRIBUTED functional bytes vs V74: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V74 (the base): {len(d74)} bytes = {len(f74)} functional + "
          f"{len(d74) - len(f74)} CRC")
    runs, prev = [], None
    for d in sorted(f74):
        if prev is not None and d == prev[1] + 1 and attribute(d) == attribute(prev[0]):
            prev = (prev[0], d)
            runs[-1] = prev
        else:
            prev = (d, d)
            runs.append(prev)
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} ({b - a + 1:2d} B)  {bytes(v74[a:b + 1]).hex():<24s} -> "
              f"{bytes(code[a:b + 1]).hex():<24s} {attribute(a)}")
    counts = {}
    for d in f74:
        counts[attribute(d)] = counts.get(attribute(d), 0) + 1
    print(f"    by lever: {counts}")
    assert counts.get(f"LEVER 1  gate repoint 0x{GATE_BYTE_V74:02X}->0x{GATE_BYTE_V76:02X} "
                      f"(-0x683c => -0x6806)") == 1, "the gate lever is not exactly ONE byte"
    assert counts.get(f"LEVER 2  0xC6446 r24 arm {ARM_B_V74}->{ARM_B_V76}") == 2, \
        "the arm lever is not exactly TWO bytes"

    # ---- ⊕ THE DIFF vs V67 -- the config this build reproduces ------------------------------------
    v67 = Path(V67_BIN).read_bytes()
    lane_addrs = sorted({GATE_ADDR, ARM_B_ADDR, ARM_B_ADDR + 1, ARM_A_ADDR, ARM_A_ADDR + 1,
                         0xC643E, 0xC643F, 0xC6440, 0xC6441, 0xC6442, 0xC6443, 0xC64FA,
                         *range(0x3AB56, 0x3AB70), *range(0x3ABF8, 0x3AC18),
                         *range(GATE_INSN_ADDR, GATE_INSN_ADDR + 4),
                         *SAR_SITES, *(a + 1 for a in SAR_SITES)})
    lane_diff = [a for a in lane_addrs if code[a] != v67[a]]
    assert not lane_diff, \
        f"🛑 the RATE LANE differs from V67 at {[hex(x) for x in lane_diff]} -- V76's whole claim is " \
        "that it reproduces V67/V68's rate-lane configuration EXACTLY"
    print(f"\n  ★★ THE RATE LANE IS BYTE-IDENTICAL TO V67 across all {len(lane_addrs)} bytes of the")
    print("     gate instruction, both selector spans, all five arms, the threshold cal and both")
    print("     `sar` sites. V76 = V74's damper + V67/V68's rate lane, and nothing else.")

    inherited = {i for i in range(START, END) if v74[i] != stock[i]}
    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    fs = [d for d in d_stock if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None and d not in inherited]
    assert not stray_s, f"UNATTRIBUTED functional bytes vs STOCK: {[hex(x) for x in stray_s[:16]]}"
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes = {len(fs)} functional + "
          f"{len(d_stock) - len(fs)} CRC (the V38->V74 lineage is carried)")

    # ---- write + readback --------------------------------------------------------------------------
    if existing is not None and existing != bytes(code):
        raise SystemExit(
            f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists (on disk "
            f"{hashlib.sha256(existing).hexdigest()}, about to write "
            f"{hashlib.sha256(bytes(code)).hexdigest()}). A same-number re-cut destroyed a "
            "predecessor's snapshot once already and produced an artefact NO gate could check. "
            "Rename or delete the existing file deliberately, then re-run.")
    Path(BIN_OUT).write_bytes(bytes(code))
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {img_sha}")

    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    assert info["headers"] == FF.EXPECTED_HEADERS
    assert info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(decode))])
    Path(OUT).write_bytes(rwd)
    FF.assert_x31_checksum(rwd, "V76 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v74)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, not from the in-memory build.
    assert_must_not_change(dec, "V76 readback", stock, v74)
    assert_ladders_untouched(dec, v74, "V76 readback")
    _rows, eng_rb, dis_rb = V74.derive_mode_columns(bytes(dec))
    assert (eng_rb, dis_rb) == (ENGAGED, DISENGAGED), "the readback's mode columns differ"
    assert dec[GATE_ADDR] == GATE_BYTE_V76 and u16(dec, ARM_B_ADDR) == ARM_B_V76, \
        "the readback does not carry both levers"
    assert bytes(dec[GATE_INSN_ADDR:GATE_INSN_ADDR + 4]) == GATE_INSN_V76, \
        "the readback's gate instruction is not the repointed one"
    assert u16(dec, ARM_A_ADDR) == ARM_A_VALUE, "the readback's 0xC6444 moved"
    V74.assert_clamp_census(bytes(dec))
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    cens_rb = assert_probe_censuses(bytes(dec), cave_span, CENSUS_OUT, "V76 readback")
    assert_repoint_census(cens_before, cens_rb)
    assert [r for _a, r, _m in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + code_len]))] == \
        [r for _a, r, _m in redis], "the readback cave does not re-disassemble identically"
    assert assert_damper_lane_frozen(dec, v74, "V76 readback") == 204
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v74[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V74 outside the attributed set: {rb_stray[:8]}"
    assert not [a for a in lane_addrs if dec[a] != v67[a]], "the readback's rate lane differs from V67"
    print("\n  READBACK -- both levers, the gate instruction re-decoded, the whole 68-byte cave AND")
    print("     its re-disassembly, BOTH probe censuses INCLUDING the two-sided repoint proof, all")
    print("     three lockstep shadows, all 204 damper records, both selector spans, the full")
    print("     keep-list, the V67 rate-lane identity, identity to V74 outside the attributed set,")
    print("     and the full CRC chain: ALL re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("V76 -- BUILT, UNFLASHED. **A SIBLING CANDIDATE TO V75, NOT A SUCCESSOR.** Verification is")
    print("NOT clearance: both branch from V74 and the operator chooses ONE to fly. Nothing printed")
    print("here is a flight decision.")
    print(f"  plain image  {BIN_OUT}")
    print(f"    SHA256     {img_sha}")
    print(f"  rwd          {OUT}")
    print(f"    SHA256     {rwd_sha}")
    print("=" * 102)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
