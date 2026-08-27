#!/usr/bin/env python3
"""builds/v50_v79/build_v73_tva.py -- V73 = V72 CARRIED BYTE-IDENTICALLY, plus three additions and a new probe.

    V73  ==  V72  +  GRIND #1 (the friction lane: 0xD2A44 Y x1.5 and 0xC407E 511 -> 850)
                  +  RATCHET  (FactorC/E Y[0] on the no-match fallback modes 0 and 2)
                  +  a new 68-byte probe that reads ONE thing: the damper's MODE BYTE.

★★ THE OBJECTIVE, IN ONE LINE: V72's `bit4` rung (|gp-0x6bd0| >= 64) read 0 in 87,940 frames --
including 0 of 34,275 ABOVE 35 km/h, where STOCK already damps -- which is arithmetically impossible
if the car were running mode 10 or 11. **V73 stops inferring the mode and MEASURES it**, while paying
for both outcomes: the friction lever is mode-10-indexed (a bet on 10/11), the ratchet rows are
mode-0/2 (a bet on the blank-HW-ID fallback), and the probe says which bet was right in one drive.

🛑 EVERY V72 BYTE IS CARRIED. This build is ADD-ONLY on top of `_v72_plain_image.bin`, so the diff
against V72 is small and fully auditable. Lever A / Lever B / Lever C / the carried 0x454FE / the
gate are asserted AT THEIR V72 VALUES on the input AND on the output AND on the .rwd readback.

EDIT 1 -- GRIND #1, the friction lane (`gp-0x6b26`, FUN_00036c12).   8 bytes
--------------------------------------------------------------------------
    0xD2A4C/4E/50  the 3-point record @0xD2A44's Y[0..2]:
                   -9830 -> -14745,  -5734 -> -8601,  -1966 -> -2949      (x1.5, exact)
    0xC407E        tp+0x507e, the lane's OWN symmetric self-clamp:  511 -> 850
✅ [EVIDENCE, decompile of FUN_00036c12 @0x36c12 + byte reads on the image being built]
   `iVar11 = *(int *)(0xCBE74 + (byte)(gp+0x63fd) * 4)` -- the record is MODE-INDEXED, mode 10
   dereferences to 0xD2A44, asserted here from the pointer array rather than quoted. The axis is
   `gp-0x6a5e` (voted vehicle speed): X = [0, 1280, 5760] counts = [0, 20, 90] km/h at 64 counts/km/h.
   The lane's arithmetic is `((gate(gp-0x6c2c) * Y_speed) >> 6) * 273 >> 18`, then clamped
   SYMMETRICALLY to +/- *(short *)(tp+0x507e) -- the two halves of the lever are the LERP gain and
   that clamp, and raising the gain alone would just clip harder.
🛑 THE CLAMP IS THE HALF THAT SURVIVES A WRONG MODE. `0xC407E` is a scalar tp cell read by
   FUN_00036c12 unconditionally; it is NOT mode-indexed. `0xD2A44` IS. See the DISCLOSED RISKS.
⚠ `0xC407C` (= 461) IS NOT TOUCHED -- adjacent, unread by this lane (its only access image-wide is
   `ld.hu 0x507c[tp],r18` @0x56914, a different subsystem), owner unidentified. Asserted unchanged.
★ RULE 4: `0xD2A44` / `0xCBE74` / `0xC407E` are virgin across all 67 prior built images (byte diff,
   not a source grep). No lineage result exists for or against this lane.

EDIT 2 -- THE RATCHET, on EVERY candidate mode: 0,1,2,3,4,5,12,14.   16 cells / 32 bytes
-----------------------------------------------------------------------------------------
**THE EDIT IS `Y[0] := that record's OWN Y[1]`, and every address is DERIVED from the pointer arrays
`0xC9E9C` (FactorC) / `0xC9F84` (FactorE) at `mode * 4` on the image being built.** Nothing is
hand-listed; the derivation is cross-checked against an independently stated value table, so a
derivation bug cannot pass silently. Each record is asserted to parse as a **4-point form with
`Y[0] == 0`** BEFORE it is touched -- if either fails the build STOPS rather than guessing a layout.

WHY THIS MODE SET. The ROW->mode table @`0xCD012` (stride `0x24`) gives each HW-ID key FOUR mode
values (`e012..e015`):  row 0 `"00000"` (blank) -> 0,1,2,3 · rows 1/4/5 `TVAA0/2/4` -> 4,4,5,5 ·
rows 2/3/6/7 `TVAA1/TVAC1/TVAA6/TVAC4` -> 10,10,11,11 · row 8 `TVAA7` -> 12,13,14,15.
Route 59's highway telemetry graded the candidates against each mode's own `bit4` trip threshold:
**modes 4/5 and 12 are fully consistent** with V72's `bit4` null (their thresholds were never
reached), **0-3 are marginally disfavoured** (11 of 34,277 frames should have tripped -- within
100 Hz sampling slop), and **10/11 are decisively excluded** (they trip unconditionally). The data
cannot pick between the survivors, so the lever covers all of them. **The ECU runs exactly ONE mode,
so every other edited mode is inert** -- corrective if it hits, costing nothing if it misses.
🛑 10 and 11 are EXCLUDED from the loop (V72 owns them) and asserted at V72's LEVER B values.

★ `Y[0] := Y[1]` is the largest value that keeps the row MONOTONE and it PRESERVES the rate/speed
  proportionality -- the shape is unchanged, only the dead first segment is lifted to meet the
  second. 🛑 V72 flattened mode 10's FactorE to [927,927,927,927], turning a proportional damper
  into a near-bang-bang relay -- a limit-cycle hazard. **Deliberately NOT repeated; asserted against.**
🛑 THE DOSE IS NOT UNIFORM: modes 0-3 deliver **106** counts at creep, modes 4/5 **33**, modes 12/14
  **31** -- a 3.4x spread, because each family's own Y[1] is what is being lifted to. ⇒ **if the
  probe reads 4/5/12/14 the delivered dose was small and a null must NOT be read as falsifying the
  lever**; V74 raises it against whichever mode turns out to be live.
  ⚠ 12/14 deliver **31**, not 32: `(234 * 140) >> 10 = 32760 >> 10 = 31`. Recomputed, not quoted.
✅ NO-CLIP, PER MODE, against that mode's OWN ceiling floor re-read from `0xC77A0[mode*4]` (all 8 are
  X=[300,800] Y=[512,1024] ⇒ floor 512 -- **verified per mode, not assumed from one**). FactorB and
  FactorD are FLAT 1024 on every mode, so the Q10 chain reduces to `(C * E) >> 10`.
  ⚠ THE CLAIM IS SCOPED, exactly as V72 scoped its own: raising `Y[0]` changes the surface ONLY
  where an axis sits at or below its own `X[1]`, so the guarantee is asserted over that NEWLY
  AFFECTED region (max 234 / 219 / 211 by family, all < 512) plus `peak == peak_base`. **A blanket
  "max < 512 everywhere" is FALSE on modes 4/5/12/14 (peaks 792/821) -- and EQUALLY false on the
  base, where the ceiling LERP has itself risen to 1024 -- so it is not a V73 requirement.**
⚠ MODES 13 AND 15 ARE NOT COVERED. They are `TVAA7`'s `e013`/`e015` arms, reachable exactly as 1 and
  3 are from the blank row, and they are not in the specified mode set. FactorC `0xD37BC`/`0xD37E4`,
  FactorE `0xD37F8`/`0xD3820`; asserted UNTOUCHED. A follow-up is a one-line change to RATCHET_MODES.

EDIT 3 -- THE PROBE. 36 of the proven 68 bytes, zero-padded, extent UNCHANGED.
-------------------------------------------------------------------------------
    bit7      = 1                              LIVENESS. field == 0 ⇒ the cave did not fire ⇒ VOID.
    bits 6:3  = (*(byte *)(gp + 0x63fd)) & 0xF ★★★★ **THE MODE.** The single quantity that decides
                                               which calibration records this car actually reads --
                                               it has never been measured, it is what V72's damper
                                               null hangs on, and it is inferred (not known) in
                                               every "mode 10" statement this kit has ever made.
    bits 2:0  = stock STEER_SENSOR_STATUS       preserved, untouched.
★ 4 BITS ARE LOSSLESS FOR THIS CAR: every mode value reachable from a `TVA*` row (rows 0-8:
  0,1,2,3,4,5,10,11,12,13,14,15) is < 16. Rows 9-15 are TVC/TWA chassis and WOULD alias -- asserted
  and reported, not assumed away.
🛑 ONE RUNG, BY DESIGN. V72 spent five rungs and the decisive one (bit4) returned an uninterpretable
  null because the LAYER BELOW it -- which records were live at all -- was unmeasured. This build
  measures that layer and nothing else.
⚠ THE COST, DECLARED: unlike V72 there is NO structural invariant among the 16 payload values, so
  the payload stream can only prove "some bit7-setting cave ran". **The .rwd FILENAME is the
  pre-drive discriminator**, and CAVE_HEX in the decoder is the post-hoc one.

🛑 THE DISCLOSED RISKS -- stated, not bounded away
---------------------------------------------------
  🛑 RISK 1 -- THE TWO LEVERS BET ON OPPOSITE ANSWERS, AND THAT IS INTENTIONAL, NOT A CONTRADICTION.
     `0xD2A44` is `0xCBE74[mode * 4]` at **mode 10 only**; EDIT 2 covers 0-5, 12 and 14 and excludes
     10/11. **They are disjoint, so exactly one of them can have acted on any given drive**, and the
     probe says which. Neither can regress the other, and `0xC407E` acts either way.
     ⚠ Note the asymmetry is deliberate but real: the telemetry that motivated EDIT 2's wide mode set
     ALSO argues mode 10 is excluded -- so EDIT 1's LERP half is, on that reading, the less likely of
     the two to be live. ⊕ Every non-10 mode's friction record is BYTE-IDENTICAL to mode 10's, so
     widening EDIT 1 later is six bytes per mode at `0xCBE74[mode*4] + 8`.
  🛑 RISK 2 -- MODES 13 AND 15 ARE NOT COVERED BY EDIT 2, and 1/3's analogue for row 8 is exactly
     what they are. FactorC 0xD37BC / 0xD37E4, FactorE 0xD37F8 / 0xD3820. If the probe reads 13 or
     15, EDIT 2 was inert too. A one-line change to RATCHET_MODES closes it.
  🛑 RISK 2b -- THE DOSE VARIES 3.4x ACROSS THE COVERED MODES (106 / 33 / 31 counts at creep). A null
     on a 4/5/12/14 reading is NOT evidence against the lever; it is a small dose. Do not score it
     as a falsification.
  ⚠ RISK 3 -- GATE 2 for the friction lane is inherited, not re-derived here: the sizing work
     reported 45 Hz suppressed 1.5-2.9x HARDER than 20.9 Hz at every rung with no sign flips, and
     1.5x is the rung whose whole p50-p99 range clears the clamp at 850. 2.0x clips at p90. This
     build takes the clean rung. The manual-feel cost is a transient catch on FAST low-speed inputs
     (the lane's speed gain peaks at 0 km/h and falls ~5x by 90 km/h), not a steady weight change.
  ⚠ RISK 4 -- V73 inherits V72's UNGATED rate lane and every one of V72's disclosed risks unchanged.
     Nothing here narrows them; see `builds/v50_v79/build_v72_tva.py`'s docstring.

CAVE DISCIPLINE
---------------
Base 0xC4B34, hook 0x55C0E, extent 68 of the proven 68 B -- unchanged, flown 10x
(V55/V57/V58/V59/V64/V65/V66/V67/V70/V71, all clean). Only 36 B are code; the remaining 32 are 0x00
(`nop`) and sit AFTER `jmp [lp]`, so they are unreachable. 🛑 Growing a cave is this kit's ONLY
bricking class (V24, V27 and V48B all bricked the ECU); shrinking the CODE inside a proven extent is
not the same operation and the extent is asserted at 68 either way.
★ r7 IS PROVABLY DEAD ACROSS THE HOOK: the instruction at 0x55C12 -- where the cave returns -- is
`mov 0x8,r7` (083a), which overwrites it. Asserted by value. r6 is restored by re-executing the
displaced `movea -0x1518,gp,r6` as the penultimate instruction, exactly as every prior cave does.

Usage:  python builds/v50_v79/build_v73_tva.py
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
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> build.log` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  (owning_block)
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl encoders)
import build_v55_tva as V55                # noqa: E402  (ldbu_any -- the ODD-displacement form)
import build_v57_tva as V57                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the two-decoder scan)
import build_v68_tva as V68                # noqa: E402  (cave machinery)
import build_v71a_tva as A                 # noqa: E402  (ratchet byte + governor monitor safety)
import build_v72_tva as V72                # noqa: E402  (THE BASE -- its levers and its guards)
import v72_lane_model as LM                # noqa: E402  (lerp_int, the delivered multiplier)
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table  # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR, stock_fw_path            # noqa: E402
from verify_bootloader_crc import walk_all_blocks                              # noqa: E402

START, END = V72.START, V72.END
CAVE_BASE = V68.CAVE_BASE                  # 0xC4B34
CAVE_EXTENT = V72.CAVE_EXTENT              # 68 -- the PROVEN extent. Never grow it.
CAVE_HARD_LIMIT = V68.CAVE_HARD_LIMIT
GP, R0, R6, R7 = V68.GP, V68.R0, V68.R6, V68.R7
TP = LM.TP                                 # 0xBF000
Q10 = 1024

# =====================================================================================================
# THE BASE -- V72, carried byte-identically
# =====================================================================================================
SRC_BIN = plain_image_path("_v72_plain_image.bin")
SRC_SHA256 = "466b5f2983167ed1599969eaf1165b570c34ff900012853c6fdb050deebaca58"
STOCK_BIN = stock_fw_path("code.bin")
BIN_OUT = str(plain_image_path("_v73_plain_image.bin"))

# 🛑 V72's own levers, re-declared HERE as literals (not imported) so a drift in either file fails.
V72_LEVER_A = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4,      # gain_B mode-10 rec0/rec1   r24
               0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}        # gain_A       rec0/rec1     r26
V72_LEVER_B = {0xD27BC: [430, 430, 430, 877], 0xD27D0: [431, 431, 431, 877],   # FactorC m10/m11
               0xD27F8: [927] * 4, 0xD280C: [927] * 4}                          # FactorE m10/m11
V72_LEVER_C = (0xC63A0, 2048)
V72_CARRIED = (0x454FE, 0xB5)              # the low byte -- `bne 0x455C4` -> `br 0x455C4`
V72_GATE = (0x3AA96, 0xC5)                 # gp-0x683c, ZERO writers ⇒ V72/V73 are UNGATED

# =====================================================================================================
# EDIT 1 -- GRIND #1: the friction lane
# =====================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74               # ptr[mode * 4]; mode 10 -> 0xD2A44
FRICTION_MODE = 10
FRICTION_REC = 0xD2A44
FRICTION_NPT = 3                           # count@+0, X[0..2]@+2, Y[0..2]@+8, terminator@+0x0E
FRICTION_Y_OFF = 0x08
FRICTION_X = [0, 1280, 5760]               # counts of voted vehicle speed = [0, 20, 90] km/h
FRICTION_Y_STOCK = [-9830, -5734, -1966]
FRICTION_SCALE_NUM, FRICTION_SCALE_DEN = 3, 2                       # x1.5, EXACT in integers
FRICTION_Y_NEW = [-14745, -8601, -2949]
FRICTION_MODE_TWINS = {0: 0xCE6D8, 1: 0xCE6E8, 2: 0xCF6D8, 3: 0xCF6E8, 4: 0xD0A44,
                       11: 0xD2A54, 12: 0xD2A64}                     # left BYTE-STOCK -- see RISK 1
SPEED_COUNTS_PER_KMH = 64

CLAMP_ADDR, CLAMP_STOCK, CLAMP_NEW = 0xC407E, 511, 850              # tp+0x507e, the self-clamp
CLAMP_TP_DISP = 0x507E
CLAMP_READERS = [0x36C34, 0x36CD0, 0x36CDC]                          # all `ld.h`, all in FUN_00036c12
CLAMP_NEIGHBOUR = (0xC407C, 461)                                     # ⚠ NOT TOUCHED, owner unknown
CLAMP_NEIGHBOUR_ACCESS = (0x56914, "ld.hu", 18)                      # its only access image-wide
FRICTION_FN = 0x36C12
AGGREGATOR_GATE = 1024                                               # the aggregator's own +/-0x400

# =====================================================================================================
# EDIT 2 -- THE RATCHET, on EVERY candidate mode. Addresses are DERIVED, never hand-listed.
# =====================================================================================================
# ★★ THE MODE SET, and where it comes from. The ROW->mode table @0xCD012 (stride 0x24) maps each
# 5-byte HW-ID key to FOUR mode values (e012..e015 = branch A arm 1/2, branch B arm 1/2):
#     row 0 "00000" (BLANK/no match) -> 0, 1, 2, 3        row 8 TVAA7          -> 12, 13, 14, 15
#     rows 1/4/5 TVAA0/TVAA2/TVAA4   -> 4, 4, 5, 5        rows 2/3/6/7 TVAA1.. -> 10, 10, 11, 11
# The ECU runs EXACTLY ONE mode, so every mode that is not the live one is inert: the lever is
# corrective if it hits and costs nothing if it misses. 10 and 11 are EXCLUDED because V72 owns them
# and they are decisively excluded by V72's own bit4 null (they trip unconditionally).
RATCHET_MODES = (0, 1, 2, 3, 4, 5, 12, 14)
EXCLUDED_MODES = (10, 11)          # V72's LEVER B -- must stay EXACTLY at V72's values
# ⚠ 13 and 15 are TVAA7's e013/e015 arms -- reachable exactly as 1 and 3 are from the blank row, and
# NOT in the specified mode set. Named with their real addresses so a follow-up needs no analysis.
UNCOVERED_MODES = (13, 15)

FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
FACTOR_B_PTRS, FACTOR_D_PTRS = 0xC9CCC, 0xC9DB4
CEILING_PTRS = 0xC77A0
REC4_X_OFF, REC4_Y_OFF, REC4_STRIDE = 0x02, 0x0A, 0x14              # 4-point record layout
CEILING_X, CEILING_Y = [300, 800], [512, 1024]
CEILING_FLOOR = CEILING_Y[0]        # 512 -- 🛑 VERIFIED PER MODE below, never assumed from one mode
# ⊕ THE CROSS-CHECK. Every address and value below is DERIVED from the pointer arrays on the image
# being built; this table is the independent second statement, so a derivation bug cannot pass
# silently. (mode -> FactorC Y[1], FactorE Y[1], delivered (C*E)>>10 at creep)
# ⚠ modes 12/14 deliver 31, not 32 -- (234 * 140) >> 10 = 32760 >> 10 = 31. Recomputed, not quoted.
RATCHET_CROSSCHECK = {0: (950, 115, 106), 1: (950, 115, 106), 2: (950, 115, 106), 3: (950, 115, 106),
                      4: (242, 142, 33), 5: (242, 142, 33), 12: (234, 140, 31), 14: (234, 140, 31)}

# The ROW -> mode table: 16 five-byte ASCII keys @0xCD000 stride 0x24, modes at +0x12..+0x15.
VARIANT_KEY_TABLE, VARIANT_IDX_TABLE, VARIANT_STRIDE = 0xCD000, 0xCD012, 0x24
BLANK_ROW, BLANK_ROW_KEY = 0, "00000"
THIS_CAR_ROW_KEY = "TVAA1"

# =====================================================================================================
# EDIT 3 -- THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
HOOK_RETURN = HOOK_ADDR + 4                     # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")        # `mov 0x8,r7` -- proves r7 is DEAD across the hook

MODE_DISP = 0x63FD              # 🛑 a POSITIVE gp displacement. gp+0x63fd, NOT gp-0x63fd.
MODE_MASK = 0xF                 # 4 bits; lossless for every TVA-family row (asserted)
W_LIVE = 0x10                   # -> bit7 LIVENESS, in PRE-SHIFT weights
PAYLOAD_SHIFT = 3
BIT_LIVE = W_LIVE << PAYLOAD_SHIFT              # 0x80
MODE_FIELD = MODE_MASK << PAYLOAD_SHIFT         # 0x78 -- bits 6:3
PROBE_MASK = BIT_LIVE | MODE_FIELD              # 0xF8

# gp+0x63fd's census on the V72 base: 22 ld.bu readers, 5 st.b writers, all inside FUN_00042746.
MODE_CENSUS_READS = 22
MODE_CENSUS_WRITERS = [0x426AE, 0x4279E, 0x427C4, 0x427FC, 0x42822]
MODE_READ_PINS = {0x34470: ("a47ffd63", 15, "FUN_00034350's FactorB read"),
                  0x34502: ("a46ffd63", 13, "FUN_00034350's FactorC read"),
                  0x346B4: ("a437fd63", 6, "★ BYTE-IDENTICAL to what this cave emits"),
                  0x36C4A: ("a47ffd63", 15, "FUN_00036c12's -- the friction lane's own read")}
# 🛑 V72's three probed cells. V73 retires all three; the cave must not touch them and the
# FIRMWARE's own reader/writer sets must be unchanged.
RETIRED_CELLS = {d: v for d, v in V72.PROBE_CENSUS.items()}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance in the STOCK image, and
# ---- every one below was rendered by Ghidra's own disassembler at that address before being used.
PIN_MOVEA_10_R7 = (0x49256, bytes.fromhex("203e1000"))     # `movea 0x10,r0,r7`
PIN_LDBU_MODE_R6 = (0x346B4, bytes.fromhex("a437fd63"))    # ★ `ld.bu 0x63fd,gp,r6` -- IDENTICAL
PIN_LDBU_MODE_R15 = (0x34470, bytes.fromhex("a47ffd63"))   # `ld.bu 0x63fd,gp,r15`
PIN_LDBU_MODE_R13 = (0x34502, bytes.fromhex("a46ffd63"))   # `ld.bu 0x63fd,gp,r13`
PIN_ANDI_F_R6 = (0x45EBC, bytes.fromhex("c6360f00"))       # `andi 0xf,r6,r6`
PIN_OR_R6_R7 = (0x1C1C4, bytes.fromhex("0639"))            # `or r6,r7`   -> r7 |= r6
PIN_SHL3_R7 = (0x4FB82, bytes.fromhex("c33a"))             # `shl 0x3,r7` -- V31P FLASHED it 4x
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))      # `ld.bu -0x1514,gp,r6`
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))       # `andi 0x7,r6,r6`
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))            # `or r7,r6`   -> r6 |= r7
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))       # `st.b r6,-0x1514,gp` -- THE ONLY STORE
PIN_MOVEA_HOOK = (0x55C0E, bytes.fromhex("2436e8ea"))      # the displaced `movea -0x1518,gp,r6`
PIN_JMP_LP = (0x1E4, bytes.fromhex("7f00"))                # `jmp lp`
# 🛑 THE ONE-BIT TRAP ON THE MODE LOAD: ld.bu is op 0x3C|(disp&1) = 0x3D here; st.b is 0x3A. The
# firmware's own `st.b r8,0x63fd,gp` @0x426AE is 4447fd63 against our a437fd63.
PIN_STB_MODE = (0x426AE, bytes.fromhex("4447fd63"))

# ⚠ DELIBERATELY SHORT and asserted BEFORE anything is written -- V71A's note records an over-long
# tag that overran Windows' 260-char path limit and failed the .rwd write AFTER the image was on disk.
TAG = "V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V73-{TAG}-0x{START:X}-0x{END:X}.rwd")
DECODER = os.path.join(HERE, "..", "rlog-tools", "probe/decode_v73_probe.py")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


def rec4_x(buf, base):
    return list(struct.unpack_from("<4h", buf, base + REC4_X_OFF))


def rec4_y(buf, base):
    return list(struct.unpack_from("<4h", buf, base + REC4_Y_OFF))


def rec3_x(buf, base):
    return list(struct.unpack_from("<3h", buf, base + 0x02))


def rec3_y(buf, base):
    return list(struct.unpack_from("<3h", buf, base + FRICTION_Y_OFF))


def rec_any(buf, base):
    """(count, X, Y) for a record of ANY point count, driven by the count word at +0.

    🛑 THIS EXISTS BECAUSE A FIXED-OFFSET READER GAVE A WRONG ANSWER DURING THIS BUILD. Y lives at
    `base + 2 + 2 * count`, so the 4-point reader (Y at +0x0A) applied to FactorD -- which is a
    5-POINT record -- returns [X[4], Y[0], Y[1], Y[2]] and reads as "not flat". The count is read,
    never assumed.
    """
    n = u16(buf, base)
    assert 1 <= n <= 16, f"the record @0x{base:05X} declares count {n}"
    xs = list(struct.unpack_from(f"<{n}h", buf, base + 2))
    ys = list(struct.unpack_from(f"<{n}h", buf, base + 2 + 2 * n))
    return n, xs, ys


def decode_fmt2(hw):
    """V850 Format-II field split: imm5 = bits[4:0], opcode = bits[10:5], reg2 = bits[15:11]."""
    return {"imm5": hw & 0x1F, "opcode": (hw >> 5) & 0x3F, "reg2": (hw >> 11) & 0x1F}


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(mode_byte, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the instructions, not a paraphrase."""
    r7 = W_LIVE                                     # movea 0x10,r0,r7
    r6 = mode_byte & 0xFF                           # ld.bu 0x63fd[gp],r6   (ZERO-extends a BYTE)
    r6 &= MODE_MASK                                 # andi 0xf,r6,r6
    r7 |= r6                                        # or   r6,r7           -> r7 |= r6
    r7 <<= PAYLOAD_SHIFT                            # shl  0x3,r7
    return (r7 & 0xFF) | (status_bits & PAYLOAD_KEEP_MASK)


LEGAL_PAYLOADS = {BIT_LIVE | (m << PAYLOAD_SHIFT) for m in range(MODE_MASK + 1)}


def _wire_model():
    """The rung's semantics, exhaustively: every one of the 256 byte values the cell can hold."""
    for raw in range(256):
        b = wire_byte4(raw)
        assert b & BIT_LIVE, f"the liveness bit is clear at mode byte {raw}"
        assert (b & MODE_FIELD) >> PAYLOAD_SHIFT == (raw & MODE_MASK), \
            f"bits 6:3 are not `(gp+0x63fd) & 0xF` at {raw}"
        assert (b & PROBE_MASK) in LEGAL_PAYLOADS, f"payload 0x{b:02X} is outside LEGAL at {raw}"
    # 🛑 the field must never reach the preserved status bits, and the seed must land on bit7.
    for m in range(MODE_MASK + 1):
        r7 = W_LIVE | m
        assert (r7 << PAYLOAD_SHIFT) <= 0xF8, f"r7 = 0x{r7:02X} shifts past the byte"
        assert (r7 << PAYLOAD_SHIFT) & PAYLOAD_KEEP_MASK == 0, \
            f"r7 = 0x{r7:02X} shifts INTO the preserved status bits -- the wire would be corrupted"
    assert (W_LIVE << PAYLOAD_SHIFT) == BIT_LIVE == 0x80, \
        "the seed does NOT land on bit7 after the shift -- the VOID sentinel would be broken"
    assert BIT_LIVE | MODE_FIELD == PROBE_MASK == 0xF8 and PROBE_MASK & PAYLOAD_KEEP_MASK == 0, \
        "the probe bits do not cover exactly 7:3"
    for status in range(8):
        for raw in (0, 10, 11, 0xFF):
            assert wire_byte4(raw, status_bits=status) & PAYLOAD_KEEP_MASK == status, \
                "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
    assert len(LEGAL_PAYLOADS) == 16, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 16"
    # ⚠ THE COST OF ONE RUNG, STATED AS AN ASSERTION so it cannot be forgotten in the write-up:
    # every legal payload differs only in the mode field, so the value SET carries no build identity
    # beyond "bit7 was set". V72's bit5 => bit6 invariant has no analogue here.
    assert {p & MODE_FIELD for p in LEGAL_PAYLOADS} == {m << PAYLOAD_SHIFT for m in range(16)}, \
        "the payload set is not the full 16-value mode field"
    # 🛑 the 4-bit field ALIASES for mode >= 16. Named explicitly; the TVA rows are checked on the
    # image in assert_mode_field_lossless().
    assert wire_byte4(16) == wire_byte4(0) and wire_byte4(26) == wire_byte4(10), \
        "the 4-bit field does not alias mod 16 -- the aliasing statement in the docs is wrong"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    Each pin below was ALSO rendered by Ghidra's own disassembler at that address (dry run) before
    being written into this file -- the pin is the byte check, Ghidra is the semantic check.
    """
    V55._self_check_encoders()               # chains down through V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVEA_10_R7, PIN_LDBU_MODE_R6, PIN_LDBU_MODE_R15, PIN_LDBU_MODE_R13, PIN_ANDI_F_R6,
            PIN_OR_R6_R7, PIN_SHL3_R7, PIN_LDBU_BYTE4, PIN_ANDI_7_R6, PIN_OR_R7_R6, PIN_STB_BYTE4,
            PIN_MOVEA_HOOK, PIN_JMP_LP, PIN_STB_MODE]
    for addr, raw in pins:
        assert bytes(src[addr:addr + len(raw)]) == raw, \
            f"the donor @0x{addr:05X} is not {raw.hex()} on the STOCK image -- re-pin"

    # ---- the mode load. ★ BYTE-IDENTICAL to a real `ld.bu 0x63fd,gp,r6` @0x346B4 --------------------
    ours = V55.ldbu_any(MODE_DISP, R6)
    assert ours == PIN_LDBU_MODE_R6[1], \
        f"the mode load is not byte-identical to the real one @0x{PIN_LDBU_MODE_R6[0]:05X}"
    hw1, hw2 = struct.unpack("<HH", ours)
    # 🛑 THE ODD-DISPLACEMENT TRAP: ld.bu carries disp bit 0 in the OPCODE FIELD (0x3C | (disp & 1))
    # and ALSO sets hw2's LSB. 0x63FD is ODD, so op MUST be 0x3D. V54's helper only ever emitted 0x3C.
    assert ((hw1 >> 5) & 0x3F) == 0x3D, \
        f"the mode load's opcode field is 0x{(hw1 >> 5) & 0x3F:02X}, MUST be 0x3D for an ODD disp"
    assert hw2 == ((MODE_DISP & 0xFFFE) | 1) == 0x63FD, "ld.bu hw2 must be (disp & ~1) | 1"
    assert (hw1 >> 11) == R6 and (hw1 & 0x1F) == GP == 4, "the mode load is not `... [gp],r6`"
    # 🛑 THE ONE-BIT TRAP: st.b is op 0x3A. The firmware's own store to this very cell is 4447fd63.
    assert ours != PIN_STB_MODE[1] and ours[:2] != PIN_STB_MODE[1][:2], \
        f"the mode load IS/matches the real `st.b r8,0x63fd,gp` @0x{PIN_STB_MODE[0]:05X} -- the cave " \
        "would WRITE the mode byte that FIVE damper factor tables and the friction lane index on"
    assert ours != FF.stb(R6, MODE_DISP, GP), "the mode load collapsed onto an st.b -- a WRITE"
    assert ours != V55.ldbu_any(-MODE_DISP, R6), \
        "the POSITIVE and NEGATIVE displacement forms collapsed -- gp+0x63fd is not gp-0x63fd"
    assert V55.ldbu_any(MODE_DISP, 15) == PIN_LDBU_MODE_R15[1] and \
        V55.ldbu_any(MODE_DISP, 13) == PIN_LDBU_MODE_R13[1], \
        "the mode-load encoder disagrees with the r15/r13 instances in FUN_00034350"

    # ---- the rest -----------------------------------------------------------------------------------
    assert FF.movea(W_LIVE, R0, R7) == PIN_MOVEA_10_R7[1], "movea 0x10,r0,r7 != the real one @0x49256"
    assert V54.andi(MODE_MASK, R6, R6) == PIN_ANDI_F_R6[1], "andi 0xf,r6,r6 != the real one @0x45EBC"
    assert V54.andi(PAYLOAD_KEEP_MASK, R6, R6) == PIN_ANDI_7_R6[1], "andi 0x7,r6,r6 encoding changed"
    assert V54.andi(MODE_MASK, R6, R6) != V54.andi(PAYLOAD_KEEP_MASK, R6, R6), \
        "the 0xF and 0x7 masks collapsed -- the mode's top bit would be lost"
    # 🛑🛑 `or r6,r7` (0639) vs `or r7,r6` (0731) -- SAME opcode, the two register fields SWAPPED, and
    # the wrong one accumulates into the scratch register instead of the payload. Both are real
    # instructions in this image, so a byte pin alone cannot catch the swap: the FIELDS are decoded.
    ours = V54.or_rr(R6, R7)
    assert ours == PIN_OR_R6_R7[1], "or r6,r7 != the real one @0x1C1C4"
    assert ours != V54.or_rr(R7, R6) == PIN_OR_R7_R6[1], \
        "or r6,r7 collapsed onto `or r7,r6` -- the mode would be OR'd into the SCRATCH register and " \
        "the payload would carry the liveness bit alone, reading as `mode 0` on every frame"
    hw = struct.unpack("<H", ours)[0]
    assert ((hw >> 5) & 0x3F) == 0x08 and (hw >> 11) == R7 and (hw & 0x1F) == R6, \
        f"`or r6,r7` fields are wrong: op 0x{(hw >> 5) & 0x3F:02X} reg2 r{hw >> 11} reg1 r{hw & 0x1F}"
    assert V54.shl(PAYLOAD_SHIFT, R7) == PIN_SHL3_R7[1] == V54.V31P_SHL3_R7, \
        "shl 0x3,r7 != the real one @0x4FB82 / V31P's FLASHED byte sequence"
    assert V54.shl(PAYLOAD_SHIFT, R7) != V55.sar(PAYLOAD_SHIFT, R7) and \
        V54.shl(PAYLOAD_SHIFT, R7) != FF.shr(PAYLOAD_SHIFT, R7), \
        "shl collapsed onto a RIGHT shift -- the payload would land in the wrong bits"
    assert V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == PIN_LDBU_BYTE4[1], "the byte4 read changed"
    assert FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP) == PIN_STB_BYTE4[1], "the byte4 store changed"
    assert HOOK_STOCK == PIN_MOVEA_HOOK[1], "the displaced hook instruction changed"
    assert FF.JMP_LP == PIN_JMP_LP[1], "jmp [lp] changed"
    _wire_model()


def build_cave():
    """pack_v73_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        movea 0x10,r0,r7       ; r7 = 0x10   bit7 LIVENESS, in PRE-SHIFT weights
        ld.bu 0x63fd[gp],r6    ; ★★★★ THE MODE BYTE. POSITIVE gp displacement; op 0x3D (ODD disp).
        andi  0xf,r6,r6        ; 4 bits -- lossless for every TVA-family row (asserted on the image)
        or    r6,r7            ; r7 |= mode      🛑 NOT `or r7,r6` -- the fields are decoded, not
                               ;                  merely byte-pinned, because both forms are real
        shl   0x3,r7           ; the 5-bit field -> bits 7:3 (V31P's FLASHED idiom; Honda's @0x4FB82)
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4   (r6 is free again: the mode is in r7)
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        <32 bytes of 0x00 = `nop`, AFTER the return ⇒ unreachable; the extent stays 68>
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

    emit(FF.movea(W_LIVE, R0, R7), "movea 0x10,r0,r7    ; bit7 LIVENESS (pre-shift weight 0x10)")
    emit(V55.ldbu_any(MODE_DISP, R6),
         f"ld.bu 0x{MODE_DISP:04x}[gp],r6  ; ★★★★ THE MODE BYTE (POSITIVE disp, op 0x3D)",
         writes_r6=True)
    emit(V54.andi(MODE_MASK, R6, R6), "andi 0xf,r6,r6      ; 4 bits", writes_r6=True)
    emit(V54.or_rr(R6, R7), "or r6,r7            ; r7 |= mode   🛑 NOT `or r7,r6`")
    emit(V54.shl(PAYLOAD_SHIFT, R7), "shl 0x3,r7          ; the 5-bit field -> bits 7:3")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4",
         writes_r6=True)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0",
         writes_r6=True)
    emit(V54.or_rr(R7, R6), "or r7,r6", writes_r6=True)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp] ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction", writes_r6=True)
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    code_len = len(body)
    pad = CAVE_EXTENT - code_len
    assert pad >= 0, f"the cave code is {code_len}B, over the PROVEN {CAVE_EXTENT}B extent"
    assert pad % 2 == 0, "the padding is not halfword-aligned"
    if pad:
        emit(bytes(pad), f"<{pad} x 0x00 = nop, AFTER `jmp [lp]` ⇒ UNREACHABLE; extent stays 68>")

    # ---- GATE 2 restated on the EMITTED CODE ------------------------------------------------------
    # 🛑 the mode must be OR'd into r7, not r6. Located BY POSITION, and the register fields are
    # decoded -- a byte pin alone cannot catch a field swap when BOTH forms exist in the image.
    or_idx = [i for i, (_a, r, _t) in enumerate(listing) if r == V54.or_rr(R6, R7)]
    assert len(or_idx) == 1, f"`or r6,r7` appears {len(or_idx)} times, expected exactly once"
    assert or_idx[0] == 3, f"`or r6,r7` is at index {or_idx[0]}, expected 3 (after the andi mask)"
    assert listing[or_idx[0] - 1][1] == V54.andi(MODE_MASK, R6, R6), \
        "the accumulate is not immediately preceded by the 0xF mask -- an unmasked mode >= 16 would " \
        "carry into the liveness bit and, after the shift, past the byte"
    assert listing[or_idx[0] + 1][1] == V54.shl(PAYLOAD_SHIFT, R7), \
        "the accumulate is not immediately followed by `shl 0x3,r7`"
    # ---- GATE 2b: r6/r7 liveness. Only the mode/payload loads may write r6; only r7 accumulates.
    for idx, (addr, raw, text) in enumerate(listing):
        if len(raw) > 4:                                          # the padding pseudo-entry
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        if raw == FF.JMP_LP:
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
    # ---- 🛑 STRAIGHT-LINE, SINGLE EXIT. The zero padding's unreachability rests on this: there is
    # no Bcond, no jr and no second jarl anywhere in the cave, so control cannot reach past the
    # `jmp [lp]`. V72's cave had five branches; V73's has NONE.
    for idx, (_a, raw, text) in enumerate(listing):
        if len(raw) > 4 or raw == FF.JMP_LP:
            continue
        hw = struct.unpack_from("<H", raw, 0)[0]
        assert (hw >> 7) & 0xF != 0xB, f"listing[{idx}] '{text}' is a Bcond -- the cave must be " \
            "straight-line code with a SINGLE exit"
        assert ((hw >> 5) & 0x3F) not in (0x1E, 0x1B), \
            f"listing[{idx}] '{text}' is a jr/jarl -- the cave must have a SINGLE exit"
    # ---- geometry ---------------------------------------------------------------------------------
    ret_idx = [i for i, (_a, r, _t) in enumerate(listing) if r == FF.JMP_LP]
    assert ret_idx == [10], f"`jmp [lp]` is at {ret_idx}, expected exactly index 10"
    assert listing[9][1] == HOOK_STOCK, "displaced movea must precede the return"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert bytes(body[code_len:]) == bytes(pad), "the padding is not all zero"
    assert code_len == 4 + 4 + 4 + 2 + 2 + 4 + 4 + 2 + 4 + 4 + 2 == 36, \
        f"the cave code is {code_len}B, the budget says 36"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) == CAVE_EXTENT == 68, \
        f"cave {len(body)}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    return bytes(body), listing


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, in Python, from raw bytes.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. This walks the emitted bytes with a minimal V850 length/format decoder and returns
    (address, bytes, mnemonic) triples, which the caller compares against the build-time listing.
    Extended from V72's decoder with the `nop` (0x0000) case the zero padding needs.
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
        elif op6 == 0x12:
            n, m = 2, f"add {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 == 0x13:
            n, m = 2, f"cmp {(hw & 0x1F) - 32 if hw & 0x10 else hw & 0x1F},r{reg2}"
        elif op6 in (0x14, 0x15, 0x16):
            n, m = 2, f"{ {0x14: 'shr', 0x15: 'sar', 0x16: 'shl'}[op6] } 0x{hw & 0x1F:x},r{reg2}"
        elif op6 == 0x0F:
            n, m = 2, f"cmp r{reg1},r{reg2}"
        elif op6 == 0x08:
            n, m = 2, f"or r{reg1},r{reg2}"
        elif hw == 0x007F or (op6 == 0x03 and reg2 == 0):
            n, m = 2, "jmp [lp]"
        else:
            n, m = 2, f"?? 0x{hw:04x}"
        out.append((base + i, bytes(raw[i:i + n]), m))
        i += n
    return out


# =====================================================================================================
# Censuses -- raw byte scans, because `search_instructions` silently undercounts
# =====================================================================================================

def gp_pos_census(buf, disp_pos):
    """Every 4-byte gp-relative access to a POSITIVE displacement, by raw LE byte scan.

    🛑 Written out here rather than reused blindly: V64's helper takes a NEGATIVE magnitude. The two
    are cross-checked against each other below -- `gp_access_census(0x10000 - d)` must produce the
    identical hit list, which is the required second method for a load-bearing count.
    """
    d16 = disp_pos & 0xFFFF
    out = []
    for mnem, op, kind in V64._FORMS:
        hw2 = d16 if kind == "disp" else (d16 & 0xFFFE) | (1 if kind == "odd" else 0)
        for o in ([0x3C | (d16 & 1)] if op is None else [op]):
            for reg2 in range(32):
                pat = struct.pack("<HH", (reg2 << 11) | (o << 5) | GP, hw2)
                i = buf.find(pat)
                while i >= 0:
                    if i % 2 == 0:
                        out.append((i, mnem, reg2))
                    i = buf.find(pat, i + 1)
    return sorted(out)


def assert_mode_census(buf, cave_span, expect_cave):
    """gp+0x63fd: the firmware's readers/writers, plus THIS cave's single read. Two decoders."""
    hits = gp_pos_census(buf, MODE_DISP)
    assert hits == V64.gp_access_census(buf, 0x10000 - MODE_DISP), \
        "the two independent census decoders disagree on gp+0x63fd -- one of them is wrong"
    assert all(m in ("ld.bu", "st.b") for _a, m, _r in hits), \
        "gp+0x63fd has a non-BYTE access -- the cell is not a byte after all"
    fw = [h for h in hits if h[0] not in cave_span]
    reads = [h for h in fw if h[1] == "ld.bu"]
    writes = [h for h in fw if h[1] == "st.b"]
    assert len(reads) == MODE_CENSUS_READS, \
        f"gp+0x63fd has {len(reads)} firmware readers, expected {MODE_CENSUS_READS}"
    assert [a for a, _m, _r in writes] == MODE_CENSUS_WRITERS, \
        f"gp+0x63fd writers are {[hex(a) for a, _m, _r in writes]}, expected " \
        f"{[hex(w) for w in MODE_CENSUS_WRITERS]} (all inside FUN_00042746)"
    for addr, (raw, reg, _what) in MODE_READ_PINS.items():
        assert bytes(buf[addr:addr + 4]) == bytes.fromhex(raw), \
            f"the mode read @0x{addr:05X} is not {raw} -- the cell's identity claim is void"
        assert (addr, "ld.bu", reg) in reads, f"0x{addr:05X} is missing from the reader census"
    cave = [h for h in hits if h[0] in cave_span]
    if expect_cave:
        assert len(cave) == 1 and cave[0][1] == "ld.bu" and cave[0][2] == R6, \
            f"gp+0x63fd: cave accesses are {[(hex(a), m, r) for a, m, r in cave]}, expected exactly " \
            "one `ld.bu ...,r6` -- an st.b here would REWRITE the damper's own mode selector"
    else:
        assert not cave, "the source image's cave already touches gp+0x63fd"
    return len(reads), len(writes)


def assert_retired_cells(buf, cave_span):
    """🛑 V73 retires V72's three probed cells: the cave must not touch them, and the FIRMWARE's own
    reader/writer sets must be exactly what V72 measured -- a probe change must not move a lane."""
    out = {}
    for disp, (n_read, n_write, writers, mnems, _want, _what) in RETIRED_CELLS.items():
        hits = V64.gp_access_census(buf, disp)
        assert not [h for h in hits if h[0] in cave_span], \
            f"the V73 cave still touches gp-0x{disp:04x} -- V73 retired it"
        fw = [h for h in hits if h[0] not in cave_span]
        assert all(m in mnems for _a, m, _r in fw), f"gp-0x{disp:04x}: unexpected access WIDTH/SIGN"
        reads = [h for h in fw if h[1].startswith("ld.")]
        writes = [h for h in fw if not h[1].startswith("ld.")]
        assert len(reads) == n_read and [a for a, _m, _r in writes] == writers, \
            f"gp-0x{disp:04x} firmware census moved: {len(reads)}r / " \
            f"{[hex(a) for a, _m, _r in writes]}w, expected {n_read}r / {[hex(w) for w in writers]}w"
        out[disp] = (len(reads), len(writes))
    return out


def assert_clamp_census(buf):
    """tp+0x507e (0xC407E): the friction lane's own clamp. THREE readers, ZERO writers, all `ld.h`.

    Raw byte scan over every 4-byte tp-relative form, both parities -- the same method that settled
    LEVER C on V72. Zero writers ⇒ no lockstep monitor can be checking it against a shadow.
    """
    d = CLAMP_ADDR - TP
    assert d == CLAMP_TP_DISP, f"0x{CLAMP_ADDR:05X} is not tp+0x{CLAMP_TP_DISP:04X}"
    out = []
    for mnem, op, kind in V64._FORMS:
        hw2 = d if kind == "disp" else (d & 0xFFFE) | (1 if kind == "odd" else 0)
        for o in ([0x3C | (d & 1)] if op is None else [op]):
            for reg2 in range(32):
                pat = struct.pack("<HH", (reg2 << 11) | (o << 5) | 5, hw2)     # reg1 = 5 = tp
                i = buf.find(pat)
                while i >= 0:
                    if i % 2 == 0:
                        out.append((i, mnem, reg2))
                    i = buf.find(pat, i + 1)
    out.sort()
    reads = [h for h in out if h[1].startswith("ld.")]
    writes = [h for h in out if not h[1].startswith("ld.")]
    assert [a for a, _m, _r in reads] == CLAMP_READERS, \
        f"tp+0x{d:04X} readers are {[hex(a) for a, _m, _r in reads]}, expected " \
        f"{[hex(r) for r in CLAMP_READERS]} -- all three inside FUN_00036c12"
    assert all(m == "ld.h" for _a, m, _r in reads), \
        "a tp+0x507e read is not `ld.h` -- the clamp is SIGNED and a `ld.hu` would break the sign"
    assert not writes, \
        f"🛑 tp+0x{d:04X} HAS WRITERS at {[hex(a) for a, _m, _r in writes]} -- it is not a pure cal"
    return reads


def assert_mode_field_lossless(buf):
    """★ 4 bits are LOSSLESS for this car: every mode a TVA-family row can select is < 16."""
    rows, aliasing = [], []
    for n in range(16):
        o = VARIANT_KEY_TABLE + n * VARIANT_STRIDE
        key = bytes(buf[o:o + 5]).decode("ascii", "replace")
        modes = list(buf[VARIANT_IDX_TABLE + n * VARIANT_STRIDE:
                         VARIANT_IDX_TABLE + n * VARIANT_STRIDE + 4])
        rows.append((n, key, modes))
        if key.startswith("TVA") or key == BLANK_ROW_KEY:
            assert all(m < 16 for m in modes), \
                f"row {n} ({key}) can select mode {max(modes)} >= 16 -- the 4-bit field would ALIAS " \
                "on this car's own chassis family, and the probe would be ambiguous"
        elif any(m >= 16 for m in modes):
            aliasing.append((n, key, modes))
    blank = rows[BLANK_ROW]
    assert blank[1] == BLANK_ROW_KEY, f"row 0's key is {blank[1]!r}, expected {BLANK_ROW_KEY!r}"
    assert blank[2] == [0, 1, 2, 3], \
        f"the BLANK row selects {blank[2]}, not [0, 1, 2, 3] -- EDIT 2's mode choice rests on this"
    this_car = [r for r in rows if r[1] == THIS_CAR_ROW_KEY]
    assert len(this_car) == 1 and this_car[0][2] == [10, 10, 11, 11], \
        f"{THIS_CAR_ROW_KEY} does not select [10, 10, 11, 11] -- EDIT 1's mode choice rests on this"
    return rows, aliasing


# =====================================================================================================
# The delivered damper authority on modes 0 and 2 -- FUN_00034350's Q10 chain, mirrored EXACTLY
# =====================================================================================================

def factor_rec(buf, ptr_array, mode):
    """The record a given factor's pointer array selects for `mode`. DEREFERENCED, never quoted."""
    return u32(buf, ptr_array + mode * 4)


def ceiling_floor(buf, mode):
    """That mode's OWN ceiling floor, re-read per mode. 🛑 NOT assumed constant across modes."""
    n, xs, ys = rec_any(buf, factor_rec(buf, CEILING_PTRS, mode))
    assert (n, xs, ys) == (2, CEILING_X, CEILING_Y), \
        f"mode {mode}'s ceiling @0x{factor_rec(buf, CEILING_PTRS, mode):05X} is ({n}, {xs}, {ys}), " \
        f"expected (2, {CEILING_X}, {CEILING_Y}) -- the no-clip floor rests on it and it is VERIFIED " \
        "per mode, not inherited from mode 0"
    return ys[0]


def damper_authority(buf, mode, speed_counts=0, rate=0, seed=Q10):
    """|gp-0x6bd0| for ANY mode, mirroring FUN_00034350's Q10 chain EXACTLY.

        gp-0x6bd0 = sign * ((((seed*B)>>10)*C)>>10)*D)>>10)*E)>>10, clamped to +/- ceiling

    Every record is DEREFERENCED from its pointer array at `mode`, so this cannot be pointed at the
    wrong table by a stale literal. FactorB and FactorD are FLAT 1024 on every mode (asserted by the
    caller), so they drop out; FactorC is keyed on VOTED SPEED and FactorE on |motor rate|.
    """
    # 🛑 rec_any, not rec4_*: FactorD is a FIVE-point record and a 4-point reader mis-reads its Y.
    c = LM.lerp_int(speed_counts, *rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))[1:])
    e = LM.lerp_int(rate, *rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))[1:])
    b = LM.lerp_int(speed_counts, *rec_any(buf, factor_rec(buf, FACTOR_B_PTRS, mode))[1:])
    d = LM.lerp_int(rate, *rec_any(buf, factor_rec(buf, FACTOR_D_PTRS, mode))[1:])
    v = (seed * b) >> 10
    v = (v * c) >> 10
    v = (v * d) >> 10
    return (v * e) >> 10


def derive_ratchet_edits(buf):
    """THE EDIT, derived: for every candidate mode, `Y[0] := that record's OWN Y[1]`.

    ★ Y[1] is the largest value that keeps the row MONOTONE, and it preserves the rate/speed
    PROPORTIONALITY -- the shape is unchanged, only the dead first segment is lifted to meet the
    second. 🛑 It deliberately does NOT flatten the row the way V72 did to mode 10's FactorE
    (Y[0..2] -> 927), which turned a proportional damper into a near-bang-bang relay.

    Returns {cell_address: (old, new, label, mode, factor, record_base)}. Raises if ANY record fails
    to parse as a 4-point `Y[0] == 0` form -- 🛑 the layout is never guessed.
    """
    edits = {}
    for mode in RATCHET_MODES:
        for ptrs, name in ((FACTOR_C_PTRS, "FactorC"), (FACTOR_E_PTRS, "FactorE")):
            base = factor_rec(buf, ptrs, mode)
            n, xs, ys = rec_any(buf, base)
            assert n == 4, \
                f"🛑 {name} mode {mode} @0x{base:05X} declares count {n}, not 4 -- the record does " \
                "NOT parse as the 4-point form. STOP: do not guess the layout."
            assert ys[0] == 0, \
                f"🛑 {name} mode {mode} @0x{base:05X} has Y[0] = {ys[0]}, not 0 -- this is not the " \
                f"dead cell V73 fixes. STOP and report. (Y = {ys})"
            assert ys[1] > 0, f"{name} mode {mode}: Y[1] = {ys[1]} is not a positive dose"
            assert all(b_ >= a_ for a_, b_ in zip(ys, ys[1:])), \
                f"{name} mode {mode} is not monotone BEFORE the edit: {ys}"
            assert len(set(xs)) == 4 and all(x > 0 for x in xs), f"{name} mode {mode} X = {xs}"
            edits[base + REC4_Y_OFF] = (0, ys[1], f"{name} mode {mode:2d} Y[0]", mode, name, base)
    # ⊕ THE CROSS-CHECK -- the derived values against the independently-stated table.
    for mode, (cy1, ey1, prod) in RATCHET_CROSSCHECK.items():
        got = {f: n for _a, (_o, n, _l, m, f, _b) in edits.items() if m == mode for f in (f,)}
        assert got == {"FactorC": cy1, "FactorE": ey1}, \
            f"mode {mode}: derived {got}, cross-check table says FactorC {cy1} / FactorE {ey1}"
        assert (cy1 * ey1) >> 10 == prod, f"mode {mode}: (C*E)>>10 is {(cy1 * ey1) >> 10}, not {prod}"
    assert set(RATCHET_CROSSCHECK) == set(RATCHET_MODES), "the cross-check table and mode set differ"
    assert len(edits) == 2 * len(RATCHET_MODES) == 16, f"{len(edits)} cells, expected 16"
    return edits


def friction_authority(buf, mode_rec, speed_counts, drive):
    """|gp-0x6b26| for the friction lane, mirroring FUN_00036c12's arithmetic EXACTLY.

        sVar7 = LERP(gp-0x6a5e voted speed, record)          <- Y is NEGATIVE throughout
        iVar4 = ((short)(drive) * sVar7 >> 6) * 0x111        <- 273
        iVar5 = iVar4 >> 0x12                                <- 18
        clamp SYMMETRICALLY to +/- *(short *)(tp+0x507e)
    """
    y = LM.lerp_int(speed_counts, rec3_x(buf, mode_rec), rec3_y(buf, mode_rec))
    v = ((drive * y) >> 6) * 0x111
    v >>= 0x12
    lim = s16(buf, CLAMP_ADDR)
    return max(-lim, min(lim, v))


# =====================================================================================================
# The MUST-REMAIN sites
# =====================================================================================================

def assert_v72_intact(buf, label, stock):
    """🛑 Every V72 lever, at its V72 value. V73 is ADD-ONLY; a moved V72 byte is a build failure."""
    # 🛑 THE ONE RELAXATION, MADE EXPLICIT. V72.assert_untouched asserts FactorC/E **mode 12** are
    # byte-stock (0xD27E4 / 0xD2820) -- and mode 12 is now inside V73's candidate set. Rather than
    # drop the check, restore those two Y[0] cells on a COPY, run the FULL inherited guard against
    # it, and assert the exception set is exactly those two cells. Same idiom as V72's own 0x454FE
    # relaxation. On the V72 SOURCE the cells are already 0, so the copy is identical and this is a
    # no-op -- the guard is never weakened for the input.
    probe = bytearray(buf)
    m12 = [factor_rec(buf, p, 12) + REC4_Y_OFF for p in (FACTOR_C_PTRS, FACTOR_E_PTRS)]
    for cell in m12:
        struct.pack_into("<H", probe, cell, 0)
    V72.assert_untouched(probe, label, stock)        # gate, sar sites, arms, hwy recs, ceiling, roles
    exc = [i for i in range(START, END) if probe[i] != buf[i]]
    allowed = {c + k for c in m12 for k in (0, 1)}
    assert set(exc) <= allowed, \
        f"{label}: the V72-guard relaxation reaches {[hex(x) for x in exc if x not in allowed][:8]}, " \
        f"outside mode 12's two Y[0] cells {[hex(c) for c in m12]}"
    for base, want in V72_LEVER_A.items():
        got = list(struct.unpack_from("<4h", buf, base + REC4_Y_OFF))
        assert got == want, f"{label}: V72 LEVER A record 0x{base:05X} Y is {got}, expected {want}"
    for base, want in V72_LEVER_B.items():
        got = list(struct.unpack_from("<4h", buf, base + REC4_Y_OFF))
        assert got == want, f"{label}: V72 LEVER B record 0x{base:05X} Y is {got}, expected {want}"
    assert u16(buf, V72_LEVER_C[0]) == V72_LEVER_C[1], \
        f"{label}: V72 LEVER C 0x{V72_LEVER_C[0]:05X} is {u16(buf, V72_LEVER_C[0])}, expected " \
        f"{V72_LEVER_C[1]}"
    assert buf[V72_CARRIED[0]] == V72_CARRIED[1], \
        f"{label}: the carried 0x{V72_CARRIED[0]:05X} is 0x{buf[V72_CARRIED[0]]:02X}, expected " \
        f"0x{V72_CARRIED[1]:02X}"
    assert buf[V72_GATE[0]] == V72_GATE[1], \
        f"{label}: the gate 0x{V72_GATE[0]:05X} is 0x{buf[V72_GATE[0]]:02X}, expected " \
        f"0x{V72_GATE[1]:02X}"
    V72.assert_lever_c_single_reader(bytes(buf))
    A.assert_ratchet_edit(buf, label, expect_edited=True)
    A.assert_no_external_entry(buf)
    A.assert_governor_monitor_safety(buf, label)
    V55.assert_variant_tables(buf)
    # 🛑 the pointer arrays THEMSELVES must not move -- an edited table is only reachable through them
    # 🛑 the pointer arrays THEMSELVES must be byte-identical to STOCK -- every edited table is only
    # reachable through them, and a moved pointer would silently redirect the whole lever.
    for arr in (FRICTION_PTR_ARRAY, FACTOR_C_PTRS, FACTOR_E_PTRS, FACTOR_B_PTRS, FACTOR_D_PTRS,
                CEILING_PTRS):
        for mode in range(16):
            got = u32(buf, arr + mode * 4)
            assert got == u32(stock, arr + mode * 4), \
                f"{label}: 0x{arr:05X}[{mode}] -> 0x{got:05X} but STOCK says " \
                f"0x{u32(stock, arr + mode * 4):05X}"
    assert u32(buf, FRICTION_PTR_ARRAY + FRICTION_MODE * 4) == FRICTION_REC, \
        f"{label}: 0x{FRICTION_PTR_ARRAY:05X}[{FRICTION_MODE}] no longer selects 0x{FRICTION_REC:05X}"


def assert_v73_untouched(buf, label, base_img):
    """The sites V73 must NOT move, by value, on top of V72's own set."""
    assert u16(buf, CLAMP_NEIGHBOUR[0]) == CLAMP_NEIGHBOUR[1], \
        f"{label}: 0x{CLAMP_NEIGHBOUR[0]:05X} is {u16(buf, CLAMP_NEIGHBOUR[0])}, expected the " \
        f"untouched {CLAMP_NEIGHBOUR[1]} -- adjacent to the clamp, unread by this lane, owner UNKNOWN"
    for mode, addr in sorted(FRICTION_MODE_TWINS.items()):
        assert bytes(buf[addr:addr + 0x10]) == bytes(base_img[addr:addr + 0x10]), \
            f"{label}: the mode-{mode} friction record 0x{addr:05X} moved -- V73 edits mode " \
            f"{FRICTION_MODE} ONLY"
    # ⚠ modes 13/15 (TVAA7's e013/e015) are reachable and are NOT in the specified mode set.
    for mode in UNCOVERED_MODES:
        for ptrs in (FACTOR_C_PTRS, FACTOR_E_PTRS):
            addr = factor_rec(buf, ptrs, mode)
            assert bytes(buf[addr:addr + REC4_STRIDE]) == bytes(base_img[addr:addr + REC4_STRIDE]), \
                f"{label}: the mode-{mode} record 0x{addr:05X} moved -- V73's mode set is " \
                f"{RATCHET_MODES} and {UNCOVERED_MODES} are deliberately NOT in it"
    # 🛑 V72 owns modes 10 and 11; they must be EXACTLY at V72's values, not merely 'unedited'.
    for mode in EXCLUDED_MODES:
        for ptrs, table in ((FACTOR_C_PTRS, V72_LEVER_B), (FACTOR_E_PTRS, V72_LEVER_B)):
            addr = factor_rec(buf, ptrs, mode)
            assert addr in table, f"{label}: mode {mode}'s 0x{addr:05X} is not a V72 LEVER B record"
            assert rec4_y(buf, addr) == table[addr], \
                f"{label}: mode-{mode} record 0x{addr:05X} is {rec4_y(buf, addr)}, expected V72's " \
                f"{table[addr]} -- modes 10/11 are EXCLUDED from V73's loop by design"
    # every edited mode: only Y[0] may move. FactorB/D and the ceiling must be byte-identical.
    # 0x18 covers the LONGEST record (FactorD is 5-point = 24 B) and deliberately spills into the
    # following record for the shorter ones -- a superset, which is the safe direction.
    for mode in RATCHET_MODES:
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD"),
                           (CEILING_PTRS, "the ceiling")):
            base = factor_rec(buf, ptrs, mode)
            assert bytes(buf[base:base + 0x18]) == bytes(base_img[base:base + 0x18]), \
                f"{label}: mode-{mode} {name} @0x{base:05X} moved"
        for ptrs, name in ((FACTOR_C_PTRS, "FactorC"), (FACTOR_E_PTRS, "FactorE")):
            base = factor_rec(buf, ptrs, mode)
            n, xs, _ys = rec_any(buf, base)
            assert n == 4 and xs == rec_any(base_img, base)[1], \
                f"{label}: mode-{mode} {name} count or X row moved -- only Y[0] may change"
            assert bytes(buf[base + REC4_Y_OFF + 2:base + REC4_STRIDE]) == \
                bytes(base_img[base + REC4_Y_OFF + 2:base + REC4_STRIDE]), \
                f"{label}: mode-{mode} {name} Y[1..3] moved -- only Y[0] may change"
    assert rec3_x(buf, FRICTION_REC) == FRICTION_X, f"{label}: the friction X row moved"
    assert u16(buf, FRICTION_REC) == FRICTION_NPT, f"{label}: the friction record's count moved"


def assert_decoder_matches(cave_bytes):
    """🛑 The decoder's CAVE_HEX must equal the cave just emitted, so it cannot drift."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, "V73: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"V73: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    for token in ("V73", os.path.basename(OUT), "0x63FD", "0xC4124"):
        assert token in txt, f"V73: the decoder does not carry '{token}'"
    for name, val in (("BIT_LIVE", BIT_LIVE), ("MODE_FIELD", MODE_FIELD),
                      ("MODE_SHIFT", PAYLOAD_SHIFT), ("PROBE_MASK", PROBE_MASK)):
        assert re.search(rf"^{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", txt, re.M), \
            f"V73: the decoder does not declare {name}"
        got = re.search(rf"^{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", txt, re.M).group(1)
        assert int(got, 0) == val, f"V73: the decoder's {name} is {got}, not {val}"
    # 🛑 the decoder must state the ALIASING and the WEAK-IDENTITY costs, and must NOT repeat the
    # retracted harmonic claim or V72's retired rungs.
    for claim in ("ALIAS", "FILENAME"):
        assert claim in txt.upper(), f"V73: the decoder never states '{claim}'"
    assert "2nd harmonic" not in txt, \
        "V73: the decoder repeats the RETRACTED 'grind #2 is grind #1's 2nd harmonic' claim"
    for stale in ("0x69A4", "0x6BD0", "0x6AC0"):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale}", txt, re.M | re.I), \
            f"V73: {stale} is still a LIVE RUNG in the decoder"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it. Shorten TAG " \
        "BEFORE building; nothing has been written yet."

    v72 = bytearray(Path(SRC_BIN).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V72): {SRC_BIN}\n  SHA256 {hashlib.sha256(bytes(v72)).hexdigest()}")
    print(f"STOCK:        {STOCK_BIN}")
    for name, img in (("V72", v72), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert hashlib.sha256(bytes(v72)).hexdigest() == SRC_SHA256, \
        f"🛑 THE BASE IS NOT V72. SHA256 is {hashlib.sha256(bytes(v72)).hexdigest()}, expected " \
        f"{SRC_SHA256}. V73 is defined as V72 + additions; any other base voids every carried claim."
    print(f"  ✅ the base SHA256 matches the recorded V72 image exactly.")

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    assert_v72_intact(v72, "V72 source", stock)
    assert walk_all_blocks(bytes(v72)) == 0, "the V72 source's own CRC chain does not verify"
    print("  ✅ V72's LEVER A / B / C, the carried 0x454FE, the UNGATED gate byte, every")
    print("     MUST-REMAIN-STOCK site, the four pointer arrays and the full CRC chain: all verified")
    print("     ON THE INPUT before a single byte was changed.")
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    assert_mode_census(bytes(v72), cave_span, expect_cave=False)

    rows, aliasing = assert_mode_field_lossless(bytes(v72))
    print("\n  🛑 THE HW-ID ROW -> MODE TABLE (0xCD000, 16 keys, stride 0x24, modes at +0x12..+0x15):")
    for n, key, modes in rows[:9]:
        mark = "  <- BLANK / no match" if n == BLANK_ROW else \
               f"  <- this car's part number ({THIS_CAR_ROW_KEY})" if key == THIS_CAR_ROW_KEY else ""
        print(f"     row {n:2d}  {key:6s}  modes {modes}{mark}")
    print(f"     rows 9-15 are TVC/TWA chassis (modes 16-33) -- {len(aliasing)} of them WOULD alias "
          "in a 4-bit field.")
    print("     ★ every mode a TVA-family or blank row can select is < 16 ⇒ the 4-bit field is "
          "LOSSLESS for this car.")

    code = bytearray(v72)

    # ---- EDIT 1 -- GRIND #1, the friction lane -----------------------------------------------------
    print("\n  EDIT 1 -- GRIND #1: the friction lane (gp-0x6b26, FUN_00036c12). 8 bytes:")
    ptr = u32(code, FRICTION_PTR_ARRAY + FRICTION_MODE * 4)
    assert ptr == FRICTION_REC, \
        f"0x{FRICTION_PTR_ARRAY:05X}[{FRICTION_MODE}] -> 0x{ptr:05X}, expected 0x{FRICTION_REC:05X}"
    assert u16(code, FRICTION_REC) == FRICTION_NPT, \
        f"the record @0x{FRICTION_REC:05X} does not declare count = {FRICTION_NPT}"
    assert rec3_x(code, FRICTION_REC) == FRICTION_X, \
        f"the record's X row is {rec3_x(code, FRICTION_REC)}, expected {FRICTION_X}"
    assert rec3_y(code, FRICTION_REC) == FRICTION_Y_STOCK, \
        f"the record's Y row is {rec3_y(code, FRICTION_REC)}, expected the stock {FRICTION_Y_STOCK}"
    print(f"    ✅ 0x{FRICTION_PTR_ARRAY:05X}[{FRICTION_MODE}] -> 0x{ptr:05X}   count = "
          f"{FRICTION_NPT}, X = {FRICTION_X} counts = "
          f"{[x // SPEED_COUNTS_PER_KMH for x in FRICTION_X]} km/h, Y = {FRICTION_Y_STOCK}")
    # ★ x1.5 EXACTLY, in integers, derived rather than quoted -- and it must not overflow int16.
    want_y = [(y * FRICTION_SCALE_NUM) // FRICTION_SCALE_DEN for y in FRICTION_Y_STOCK]
    assert want_y == FRICTION_Y_NEW, f"x1.5 gives {want_y}, not the declared {FRICTION_Y_NEW}"
    assert all(y * FRICTION_SCALE_NUM % FRICTION_SCALE_DEN == 0 for y in FRICTION_Y_STOCK), \
        "x1.5 is not exact on one of the Y values -- the multiplier would be silently rounded"
    assert all(-0x8000 <= y < 0x8000 for y in want_y), "a scaled Y does not fit in int16"
    assert all(a < b <= 0 for a, b in zip(want_y, want_y[1:])), \
        "the scaled Y row is not monotone increasing toward zero -- the stock shape must be preserved"
    struct.pack_into("<3h", code, FRICTION_REC + FRICTION_Y_OFF, *want_y)
    assert rec3_y(code, FRICTION_REC) == want_y, "the friction record did not take its final Y"
    for k, (old, new) in enumerate(zip(FRICTION_Y_STOCK, want_y)):
        print(f"    0x{FRICTION_REC + FRICTION_Y_OFF + 2 * k:05X}  {old:7d} -> {new:7d}   "
              f"friction Y[{k}] @ {FRICTION_X[k] // SPEED_COUNTS_PER_KMH} km/h  (x1.5, exact)")
    assert u16(code, CLAMP_ADDR) == CLAMP_STOCK, \
        f"0x{CLAMP_ADDR:05X} is {u16(code, CLAMP_ADDR)}, expected the stock {CLAMP_STOCK}"
    struct.pack_into("<H", code, CLAMP_ADDR, CLAMP_NEW)
    print(f"    0x{CLAMP_ADDR:05X}  {CLAMP_STOCK:7d} -> {CLAMP_NEW:7d}   tp+0x{CLAMP_TP_DISP:04X}, "
          "the lane's OWN symmetric self-clamp")
    assert CLAMP_NEW < AGGREGATOR_GATE, \
        f"the clamp {CLAMP_NEW} is at or above the aggregator's own +/-{AGGREGATOR_GATE} gate, which " \
        "would bind first and make the edit meaningless"
    creaders = assert_clamp_census(bytes(code))
    print(f"    ✅ [EVIDENCE, raw both-parity tp-relative byte scan on THIS image] tp+0x"
          f"{CLAMP_TP_DISP:04X} has {len(creaders)} readers, ALL `ld.h`, ALL inside FUN_000"
          f"{FRICTION_FN:05x}:")
    print(f"       {[hex(a) for a, _m, _r in creaders]}, and ZERO writers ⇒ no lockstep monitor can "
          "be checking it.")
    print(f"    ⚠ 0x{CLAMP_NEIGHBOUR[0]:05X} (= {CLAMP_NEIGHBOUR[1]}) IS NOT TOUCHED -- adjacent, its "
          f"only access image-wide is")
    print(f"      `{CLAMP_NEIGHBOUR_ACCESS[1]} 0x507c[tp],r{CLAMP_NEIGHBOUR_ACCESS[2]}` "
          f"@0x{CLAMP_NEIGHBOUR_ACCESS[0]:05X}, a different subsystem; owner UNIDENTIFIED.")
    print("\n    THE DELIVERED FRICTION AUTHORITY, mirroring FUN_00036c12 "
          "(`(drive * Y >> 6) * 273 >> 18`, clamped):")
    print("      drive |gp-0x6c2c|      0 km/h            20 km/h           90 km/h    "
          "(V72 -> V73, counts)")
    for drive in (2000, 5000, 10000, 20000):
        row = []
        for vc in (0, 1280, 5760):
            was = friction_authority(v72, FRICTION_REC, vc, drive)
            now = friction_authority(code, FRICTION_REC, vc, drive)
            row.append(f"{was:6d} -> {now:6d}")
        print(f"      {drive:12d}   " + "   ".join(row))
    clipped = [(d, v) for d in range(0, 30001, 250) for v in range(0, 5761, 64)
               if abs(friction_authority(code, FRICTION_REC, v, d)) >= CLAMP_NEW]
    print(f"      ⚠ the new clamp binds at {len(clipped)} of "
          f"{len(range(0, 30001, 250)) * len(range(0, 5761, 64))} swept (drive, speed) points -- "
          "clipping is NOT eliminated,")
    print("        only pushed out; the sizing work put grind #1's p50-p99 range inside it at 1.5x.")

    # ---- EDIT 2 -- THE RATCHET, every candidate mode -----------------------------------------------
    print(f"\n  EDIT 2 -- THE RATCHET: `Y[0] := that record's OWN Y[1]` on modes {RATCHET_MODES}.")
    print("    🛑 Every address below is DEREFERENCED from the pointer arrays on the image being")
    print("       built -- nothing is hand-listed -- and cross-checked against an independently")
    print("       stated value table, so a derivation bug cannot pass silently.")
    ratchet_edits = derive_ratchet_edits(code)
    print(f"\n    {'mode':>4} {'FactorC rec':>12} {'Y before':<22} {'FactorE rec':>12} "
          f"{'Y before':<22} {'ceilFloor':>9}")
    for mode in RATCHET_MODES:
        cb, eb = factor_rec(code, FACTOR_C_PTRS, mode), factor_rec(code, FACTOR_E_PTRS, mode)
        fl = ceiling_floor(code, mode)
        print(f"    {mode:4d}      0x{cb:05X} {str(rec_any(code, cb)[2]):<22}      0x{eb:05X} "
              f"{str(rec_any(code, eb)[2]):<22} {fl:9d}")
        # FactorB/D must be FLAT 1024, or the Q10 reduction is wrong. Read by COUNT: FactorB is
        # 4-point and FactorD is 5-point, and a fixed 4-point reader mis-reads the latter.
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
            base = factor_rec(code, ptrs, mode)
            n, _xs, ys = rec_any(code, base)
            assert set(ys) == {Q10}, f"{name} mode {mode} ({n}-point) is not FLAT {Q10}: {ys}"
    print(f"    ✅ all {len(RATCHET_MODES)} modes: count 4, Y[0] == 0, monotone, FactorB/D FLAT "
          f"{Q10}, ceiling X = {CEILING_X} Y = {CEILING_Y}")
    print(f"       ⇒ FLOOR {CEILING_FLOOR}, VERIFIED PER MODE (not inherited from one mode).")

    print(f"\n    THE {len(ratchet_edits)} EDITED CELLS:")
    for addr, (old, new, label, _m, _f, _b) in sorted(ratchet_edits.items()):
        assert u16(code, addr) == old, \
            f"{label} @0x{addr:05X} is {u16(code, addr)}, expected {old}"
        struct.pack_into("<H", code, addr, new)
        print(f"      0x{addr:05X}  {old:5d} -> {new:5d}   {label}")

    print("\n    RESULTING RECORDS -- MONOTONE and still RATE/SPEED-PROPORTIONAL "
          "(🛑 NOT flattened, unlike V72's mode-10 FactorE):")
    grid_vr = [(v, r) for v in range(0, 14001, 64) for r in range(0, 4501, 25)]
    for mode in RATCHET_MODES:
        for ptrs, name in ((FACTOR_C_PTRS, "FactorC"), (FACTOR_E_PTRS, "FactorE")):
            base = factor_rec(code, ptrs, mode)
            was, ys = rec_any(v72, base)[2], rec_any(code, base)[2]
            assert ys[0] == was[1], f"{name} m{mode}: Y[0] is {ys[0]}, the spec says its OWN Y[1] " \
                                    f"= {was[1]}"
            assert ys[1:] == was[1:], f"{name} m{mode}: only Y[0] may change, got {ys}"
            assert all(b >= a for a, b in zip(ys, ys[1:])), \
                f"🛑 {name} m{mode} Y = {ys} is NOT monotone non-decreasing"
            assert len(set(ys)) > 1, \
                f"🛑 {name} m{mode} Y = {ys} is FLAT -- that is the near-bang-bang relay shape V72 " \
                "produced on mode 10 and this build must NOT repeat"
            assert all(0 <= y < 0x8000 for y in ys), f"{name} m{mode}: a Y is not a positive short"
            print(f"      mode {mode:2d}  {name}  {str(was):<22} -> {ys}   monotone ✅ "
                  " proportional ✅")

    print(f"\n    DELIVERED DAMPING AUTHORITY (FactorB/D FLAT {Q10} ⇒ the chain reduces to "
          f"(C * E) >> 10, seed {Q10}):")
    print(f"      {'mode':>4} {'creep':>6} {'floor':>6} {'affectedMax':>12} {'peak base':>10} "
          f"{'peak V73':>9}")
    doses = {}
    for mode in RATCHET_MODES:
        fl = ceiling_floor(code, mode)
        creep = damper_authority(code, mode, 0, 0)
        cx = rec_any(code, factor_rec(code, FACTOR_C_PTRS, mode))[1]
        ex = rec_any(code, factor_rec(code, FACTOR_E_PTRS, mode))[1]
        # ★ THE CORRECTLY-SCOPED NO-CLIP CLAIM. Raising Y[0] changes the surface ONLY where an axis
        # sits at or below its own X[1]; above that the curve is byte-identical. So the region V73
        # newly affects is {v <= C.X[1]} UNION {r <= E.X[1]}, and THAT is where the guarantee must
        # hold. 🛑 A blanket "max < floor everywhere" is FALSE on modes 4/5/12/14 (peaks 792/821) --
        # and EQUALLY false on the base, where the ceiling LERP has itself risen to 1024 -- so it
        # cannot be a V73 requirement. Same discipline V72 used for its own opened region.
        aff = max(damper_authority(code, mode, v, r) for v, r in grid_vr
                  if v <= cx[1] or r <= ex[1])
        peak = max(damper_authority(code, mode, v, r) for v, r in grid_vr)
        peak_b = max(damper_authority(v72, mode, v, r) for v, r in grid_vr)
        doses[mode] = creep
        print(f"      {mode:4d} {creep:6d} {fl:6d} {aff:12d} {peak_b:10d} {peak:9d}")
        assert creep == RATCHET_CROSSCHECK[mode][2], \
            f"mode {mode}: creep authority is {creep}, cross-check says {RATCHET_CROSSCHECK[mode][2]}"
        assert creep < fl, f"🛑 mode {mode}: creep {creep} is at or above its own ceiling FLOOR {fl}"
        assert aff < fl, \
            f"🛑 mode {mode}: the NEWLY AFFECTED region delivers {aff}, at or above its own ceiling " \
            f"FLOOR {fl} ⇒ the damper would SATURATE there, putting a hard-clipping element inside " \
            "a feedback loop at the frequency of a high-Q resonance. That CREATES limit cycles."
        assert peak == peak_b, \
            f"mode {mode}: the GLOBAL peak moved {peak_b} -> {peak}; only Y[0] changed, so it must not"
    print(f"      ✅ every mode: creep < its own floor, the NEWLY AFFECTED region's max < its own")
    print("         floor, and the GLOBAL peak is byte-identical to the base (only Y[0] moved and")
    print("         the peak lives at Y[3]).")
    print("      ⚠ SCOPE, STATED: a blanket 'max < 512 everywhere' is FALSE on modes 4/5/12/14 "
          "(peaks 792/821) --")
    print("        and EQUALLY false on the BASE, where the ceiling LERP has itself risen to 1024, "
          "so it is not a")
    print("        V73 requirement. The correctly-scoped claim is the one asserted above.")
    print(f"\n    🛑 THE DOSE IS NOT UNIFORM ACROSS FAMILIES: {doses}")
    print("       modes 0-3 deliver 106 counts, modes 4/5 deliver 33, modes 12/14 deliver 31 -- a")
    print("       3.2-3.4x spread, because each family's own Y[1] is the value being lifted to.")
    print("       ⇒ IF THE PROBE READS 4, 5, 12 OR 14, THE DOSE THIS BUILD DELIVERED IS SMALL and a")
    print("       null result must NOT be read as falsifying the lever. V74 should raise it against")
    print("       whichever mode is actually live -- that is what edit #3 exists to tell you.")
    print(f"\n    ⚠ MODES {UNCOVERED_MODES} ARE NOT COVERED. They are TVAA7's e013/e015 arms, "
          "reachable exactly as 1")
    print("      and 3 are from the blank row. Asserted UNTOUCHED; their records are:")
    for mode in UNCOVERED_MODES:
        cb, eb = factor_rec(code, FACTOR_C_PTRS, mode), factor_rec(code, FACTOR_E_PTRS, mode)
        print(f"        mode {mode}: FactorC 0x{cb:05X} {rec_any(code, cb)[2]}   "
              f"FactorE 0x{eb:05X} {rec_any(code, eb)[2]}")
    print(f"    🛑 MODES {EXCLUDED_MODES} ARE EXCLUDED BY DESIGN and asserted at V72's LEVER B values.")

    # ---- EDIT 3 -- the probe -----------------------------------------------------------------------
    print("\n  EDIT 3 -- THE PROBE (36 code bytes + 32 pad = the proven 68-byte extent):")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex()[:24]:<24s} {text}")
    assert code[CAVE_BASE + 2] == W_LIVE, "the liveness immediate is not the pre-shift weight 0x10"
    # 🛑 The HOOK SITE already carries the `jarl` on every cave build -- HOOK_STOCK is the DISPLACED
    # original that the cave re-executes, NOT what sits at 0x55C0E. Both are asserted, separately.
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v72[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must stay byte-identical to the base"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"the hook is not `jarl 0x{CAVE_BASE:05X}` -- the cave would never be entered"
    # ⚠ the offset is DERIVED from the emitted listing, never hardcoded -- V72's was 0x32 and V73's
    # is 0x1E, and a stale literal here would assert the wrong halfword.
    disp_off = cave_listing[9][0] - CAVE_BASE
    assert bytes(code[CAVE_BASE + disp_off:CAVE_BASE + disp_off + 4]) == HOOK_STOCK, \
        f"the displaced original is not at cave offset 0x{disp_off:02X}"
    assert bytes(code[HOOK_RETURN:HOOK_RETURN + 2]) == HOOK_RETURN_INSN, \
        f"0x{HOOK_RETURN:05X} is not `mov 0x8,r7` -- the proof that r7 is DEAD across the hook is void"
    print(f"    ★ r7 IS PROVABLY DEAD ACROSS THE HOOK: 0x{HOOK_RETURN:05X} (where the cave returns) "
          f"is `mov 0x8,r7` = {HOOK_RETURN_INSN.hex()},")
    print("      which overwrites it immediately. r6 is restored by re-executing the displaced movea.")
    nr, nw = assert_mode_census(bytes(code), cave_span, expect_cave=True)
    print(f"\n    ✅ GATE 1 (RAM ownership), asserted as a MEASUREMENT from raw bytes, TWO decoders:")
    print(f"       gp+0x{MODE_DISP:04x}  {nr}r / {nw}w -- readers are the damper's five factor lookups, the "
          "friction lane, the")
    print(f"       r24 gain_B selector and the diagnostics; the {nw} writers are ALL inside "
          "FUN_00042746 (the HW-ID failover).")
    print(f"       The cave adds EXACTLY ONE `ld.bu 0x{MODE_DISP:04x}[gp],r6` and writes it NEVER. "
          "🛑 The one-bit trap: the")
    print(f"       firmware's own `st.b r8,0x{MODE_DISP:04x},gp` @0x{PIN_STB_MODE[0]:05X} is "
          f"{PIN_STB_MODE[1].hex()} against our {V55.ldbu_any(MODE_DISP, R6).hex()}.")
    retired = assert_retired_cells(bytes(code), cave_span)
    print("    ✅ V72's three probed cells are RETIRED and their FIRMWARE censuses are unchanged: " +
          ", ".join(f"gp-0x{d:04x} {r}r/{w}w" for d, (r, w) in retired.items()))
    print("       the cave's ONLY store is st.b r6,-0x1514[gp] (the CAN-330 payload byte, bits 2:0")
    print("       preserved) -- identical RAM ownership to V67..V72, all flown clean.")
    print("    ⚠ WEAK BUILD IDENTITY, STATED: all 16 payload values are legal, so the value SET "
          "proves only that")
    print("      SOME bit7-setting cave ran. V72's bit5 => bit6 invariant has no analogue here. "
          "The .rwd FILENAME")
    print("      is the pre-drive discriminator and CAVE_HEX is the post-hoc one.")

    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/probe/decode_v73_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 RE-DISASSEMBLE THE CAVE FROM THE BUILT BYTES, IN PYTHON -------------------------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE (raw Python decoder, NOT a Ghidra database):")
    redis = redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    for (a, raw, m) in redis[:11]:
        print(f"    0x{a:05X}  {raw.hex():<12s} {m}")
    print(f"    0x{redis[11][0]:05X}..0x{redis[-1][0]:05X}  {len(redis) - 11} x `nop` (0x0000) -- "
          "the zero padding, AFTER `jmp [lp]` ⇒ unreachable")
    assert [r for _a, r, _m in redis[:11]] == [r for _a, r, _t in cave_listing[:11]], \
        "the re-disassembly's bytes differ from the emitted listing"
    assert [a for a, _r, _m in redis[:11]] == [a for a, _r, _t in cave_listing[:11]], \
        "the re-disassembly does not land on the same instruction boundaries as the build listing"
    assert all(m == "nop" for _a, _r, m in redis[11:]), "the padding does not decode as nop"
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    assert len(stores) == 1 and stores[0][1] == f"st.b r{R6},{-PAYLOAD_BYTE4_DISP}[r{GP}]", \
        f"the re-disassembly finds stores {stores} -- expected exactly ONE st.b to the CAN payload"
    ldbu = [(a, m) for a, _r, m in redis if m.startswith("ld.bu ")]
    assert len(ldbu) == 2, f"the re-disassembly finds {len(ldbu)} ld.bu, expected 2"
    assert ldbu[0][1] == f"ld.bu {MODE_DISP}[r{GP}],r{R6}", \
        f"the first ld.bu is {ldbu[0][1]}, expected the POSITIVE-displacement mode read"
    assert ldbu[1][1] == f"ld.bu {-PAYLOAD_BYTE4_DISP}[r{GP}],r{R6}", \
        f"the second ld.bu is {ldbu[1][1]}, expected the CAN payload byte read"
    ors = [(a, m) for a, _r, m in redis if m.startswith("or ")]
    assert [m for _a, m in ors] == [f"or r{R6},r{R7}", f"or r{R7},r{R6}"], \
        f"the re-disassembled `or` sequence is {[m for _a, m in ors]} -- the ACCUMULATE must be " \
        f"`or r{R6},r{R7}` (mode INTO the payload) and the MERGE `or r{R7},r{R6}`"
    print(f"    ✅ exactly TWO `ld.bu` (the mode at +0x{MODE_DISP:04x}, the CAN byte at "
          f"-0x{PAYLOAD_BYTE4_DISP:04x}), exactly ONE store, and the")
    print(f"       `or` pair in the right ORDER (`or r6,r7` then `or r7,r6`). Re-derived from the "
          "BUILT bytes.")

    # ---- the untouched sites, re-asserted on the finished image ------------------------------------
    assert_v72_intact(code, "V73", stock)
    assert_v73_untouched(code, "V73", v72)
    probe_copy = bytearray(code)
    struct.pack_into("<H", probe_copy, A.RATCHET_ADDR, A.RATCHET_STOCK_HW)
    V57.assert_decoupled(probe_copy, "V73 (with 0x454FE restored for the inherited guard)")
    exception_set = [i for i in range(START, END) if probe_copy[i] != code[i]]
    assert exception_set == [A.RATCHET_ADDR], \
        f"the guard relaxation covers {[hex(x) for x in exception_set]}, expected " \
        f"exactly [0x{A.RATCHET_ADDR:05X}]"
    print("\n  ✅ V53's eleven STOCK_CALS re-checked through V57's inherited guard (the ONLY relaxation")
    print(f"     is 0x{A.RATCHET_ADDR:05X}, asserted as a one-byte exception set); V57's decoupling "
          "carried; variant")
    print("     tables intact; V72's LEVER A / B / C unchanged at their V72 values.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = [CAVE_BASE, CLAMP_ADDR, FRICTION_REC + FRICTION_Y_OFF] + list(ratchet_edits)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    assert [b[1] for b in blocks] == [0xC4FFC, 0xCEFFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC], \
        f"expected the MAIN/0xCE000/0xCF000/0xD0000/0xD2000/0xD3000 trailers, got " \
        f"{[hex(b[1]) for b in blocks]}"
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
    all_edit_bytes = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)) | \
        {CLAMP_ADDR, CLAMP_ADDR + 1} | \
        {FRICTION_REC + FRICTION_Y_OFF + k for k in range(6)} | \
        {a + k for a in ratchet_edits for k in (0, 1)}
    assert not [a for a in all_edit_bytes if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"
    print(f"    ✅ NOTHING of the {len(all_edit_bytes)} edited bytes lands in [0xC5000,0xC5FFC) -- "
          "the CRC-skipped block, V40 ignition precedent.")

    # ---- the attributed diff -----------------------------------------------------------------------
    def attribute(d):
        return ("PROBE cave (mode byte)" if d in range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT) else
                "EDIT 1 friction LERP 0xD2A44 x1.5"
                if d in {FRICTION_REC + FRICTION_Y_OFF + k for k in range(6)} else
                "EDIT 1 friction clamp 0xC407E" if d in (CLAMP_ADDR, CLAMP_ADDR + 1) else
                f"EDIT 2 ratchet FactorC/E Y[0] (modes {RATCHET_MODES})"
                if d in {a + k for a in ratchet_edits for k in (0, 1)} else None)

    d72 = [i for i in range(START, END) if code[i] != v72[i]]
    f72 = [d for d in d72 if d not in crc_only]
    stray = [d for d in f72 if attribute(d) is None]
    assert not stray, f"UNATTRIBUTED functional bytes vs V72: {[hex(x) for x in stray]}"
    print(f"\n  EXACT DIFF vs V72 (the base): {len(d72)} bytes = {len(f72)} functional + "
          f"{len(d72) - len(f72)} CRC")
    for d in sorted(f72):
        print(f"    0x{d:05X}  {v72[d]:02X} -> {code[d]:02X}   {attribute(d)}")

    inherited = {i for i in range(START, END) if v72[i] != stock[i]}
    d_stock = [i for i in range(START, END) if code[i] != stock[i]]
    fs = [d for d in d_stock if d not in crc_only]
    stray_s = [d for d in fs if attribute(d) is None and d not in inherited]
    assert not stray_s, f"UNATTRIBUTED functional bytes vs STOCK: {[hex(x) for x in stray_s[:16]]}"
    print(f"\n  EXACT DIFF vs STOCK: {len(d_stock)} bytes = {len(fs)} functional + "
          f"{len(d_stock) - len(fs)} CRC (the V38->V72 lineage is carried)")

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
    FF.assert_x31_checksum(rwd, "V73 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v72)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"
    assert_v72_intact(dec, "V73 readback", stock)
    assert_v73_untouched(dec, "V73 readback", v72)
    assert rec3_y(dec, FRICTION_REC) == FRICTION_Y_NEW, \
        f"readback friction Y is {rec3_y(dec, FRICTION_REC)}"
    assert u16(dec, CLAMP_ADDR) == CLAMP_NEW, f"readback 0x{CLAMP_ADDR:05X} is {u16(dec, CLAMP_ADDR)}"
    assert_clamp_census(bytes(dec))
    for addr, (_o, new, label, _m, _f, _b) in ratchet_edits.items():
        assert u16(dec, addr) == new, f"readback {label} @0x{addr:05X} is {u16(dec, addr)}"
    assert derive_ratchet_edits(v72) == ratchet_edits, "the derivation is not reproducible"
    for mode in RATCHET_MODES:
        fl = ceiling_floor(dec, mode)
        cx = rec_any(dec, factor_rec(dec, FACTOR_C_PTRS, mode))[1]
        ex = rec_any(dec, factor_rec(dec, FACTOR_E_PTRS, mode))[1]
        for ptrs in (FACTOR_C_PTRS, FACTOR_E_PTRS):
            ys = rec_any(dec, factor_rec(dec, ptrs, mode))[2]
            assert all(b >= a for a, b in zip(ys, ys[1:])) and len(set(ys)) > 1, \
                f"readback mode {mode} Y = {ys} is not monotone-and-proportional"
        assert max(damper_authority(dec, mode, v, r) for v, r in grid_vr
                   if v <= cx[1] or r <= ex[1]) < fl, \
            f"readback: mode {mode}'s newly affected region clips against its floor {fl}"
        assert damper_authority(dec, mode, 0, 0) == RATCHET_CROSSCHECK[mode][2], \
            f"readback: mode {mode}'s creep dose moved"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_mode_census(bytes(dec), cave_span, expect_cave=True)
    assert_retired_cells(bytes(dec), cave_span)
    assert_mode_field_lossless(bytes(dec))
    assert [r for _a, r, _m in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))] == \
        [r for _a, r, _m in redis], "the readback cave does not re-disassemble identically"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v72[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V72 outside the attributed set: {rb_stray[:8]}"
    print("\n  READBACK -- payload, the friction record and its clamp (with the clamp's reader")
    print("     census), all four ratchet cells AND their monotone/proportional/no-clip properties,")
    print("     every V72 lever at its V72 value, the carried ratchet byte, the governor-monitor")
    print("     safety, the whole 68-byte cave AND its re-disassembly, the gp+0x63fd census through")
    print("     two independent decoders, the ROW->mode table, identity to V72 outside the")
    print("     attributed set, and the full CRC chain: ALL re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print("  V73 BUILT. Every V72 byte carried; three additions and one probe rung.")
    print("  🛑 THE TWO LEVERS ARE DISJOINT IN MODE AND THE PROBE SETTLES WHICH ACTED: the friction")
    print(f"     LERP is mode-{FRICTION_MODE}-indexed; the ratchet covers {RATCHET_MODES}. The clamp")
    print("     0xC407E is mode-independent and acts either way.")
    print(f"  🛑 DOSE BY FAMILY: {doses} counts at creep -- a 3.4x spread. If the probe reads 4/5/12/14")
    print("     the delivered dose was SMALL; a null must not be scored as falsifying the lever, and")
    print("     V74 should raise it against whichever mode is live.")
    print(f"  ⚠ NOT COVERED: modes {UNCOVERED_MODES} (TVAA7's e013/e015) -- FactorC 0xD37BC/0xD37E4,")
    print("     FactorE 0xD37F8/0xD3820. A one-line change to RATCHET_MODES closes it.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without an image."""
    _self_check_encoders()
    assert (BIT_LIVE, MODE_FIELD, PROBE_MASK) == (0x80, 0x78, 0xF8)
    assert len(FRICTION_Y_NEW) == 3
    assert set(RATCHET_MODES) == set(RATCHET_CROSSCHECK) and len(RATCHET_MODES) == 8
    assert not (set(RATCHET_MODES) & set(EXCLUDED_MODES)), "an excluded mode is in the edit loop"
    assert not (set(RATCHET_MODES) & set(UNCOVERED_MODES)), "an uncovered mode is in the edit loop"
    assert FRICTION_MODE in EXCLUDED_MODES, \
        "EDIT 1's mode is inside EDIT 2's set -- the two levers must be DISJOINT in mode"
    cave, listing = build_cave()
    assert len(cave) == 68 and len(listing) == 12


if __name__ == "__main__":
    build()
