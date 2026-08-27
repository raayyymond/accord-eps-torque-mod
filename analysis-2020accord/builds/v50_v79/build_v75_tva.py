#!/usr/bin/env python3
"""builds/v50_v79/build_v75_tva.py -- V75 = V74 CARRIED, with the dose cranked 2.74x and a MAGNITUDE probe.

🛑🛑 STATUS: **BUILT, UNFLASHED, FLIGHT CONDITIONAL.** This artefact is NOT cleared to fly and
nothing in this file should be read as clearance. The route-5d abort check puts V74's own 5x-f0
prominence at **2.884 [2.301, 3.575]** against a 3.0 abort line -- the highest median in the corpus,
CI straddling the line -- and its **creep-only arm at 5.844** against a pooled creep baseline of
0.632. Creep is exactly where LEVER CY0 acts. A harmonic tracking test has since come back clean,
but **the flight decision is the operator's**, there is a competing lever under evaluation, and this
file does not make that call. Building an unflashed artefact costs nothing; flashing one does.

★★★★ THE ONE-LINE REASON THIS BUILD EXISTS. V74 put the damper in force for the first time (bit7
fired) but at only ~50 counts on the live mode 26, and its four state bits measured a **constant 5**
in 101,117 of 101,118 frames -- four bits spent on a cell that never moved. V75 does two things:
it **raises the delivered dose to 137 counts at the measured burst rate** (2.74x), and it **replaces
the wasted state field with a THERMOMETER on the damper's own magnitude** so the next flight can say
how big the dose actually got, not merely that it was non-zero.

🛑 V75 IS V74 PLUS ADDITIONS ONLY. Every cell either rises or stays. Nothing is reverted, nothing is
lowered, and the disengaged column stays byte-stock. Asserted cell by cell, not asserted in prose.

THE DOSE CRANK -- TWO INDEPENDENTLY TOGGLEABLE LEVERS, on the ENGAGED COLUMN of all 16 rows.
-----------------------------------------------------------------------------------------------
    LEVER CY0  FactorC (0xC9E9C[mode*4]) Y[0] := 566   -- raises the CREEP end of the speed axis
    LEVER EX1  FactorE (0xC9F84[mode*4]) X[1] := 200   -- steepens the LOW-RATE ramp
★ `LEVERS = {"CY0": ..., "EX1": ...}` -- separate derive functions, separate assertions, separate
  byte-attribution buckets, and **BOTH output filenames encode the set** (`lever_token()`). If the
  creep elevation above turns out to be a relay harmonic, the re-spec "drop CY0, keep EX1" is a FLAG
  CHANGE, not a rewrite. ⚠ The toggle is independent; the ARITHMETIC is not -- CY0's no-clip cap is
  binary-searched against the E axis EX1 actually wrote, so EX1 is derived and applied FIRST.
🛑 FactorE's Y ROW IS NOT TOUCHED. `0xD7818` / `0xD781A` / `0xD781C` stay exactly as V74 left them --
  FactorE's Y axis has ZERO verified headroom, because Y[3] = 927 is what sets the surface maximum.

★ WHY THESE TWO AND NOTHING ELSE. `dose = (FactorC x FactorE) >> 10` with FactorB and FactorD FLAT
  1024 (asserted per mode, BY COUNT). Of the four cells that could be moved:
    · `C_Y0` raises only the low-speed end -- the plateau `C_Y3` that sets the surface max is untouched.
    · `E_X1` moves a BREAKPOINT left. E rises on `(X0, X1_old)` and is unchanged above it, so the
      PLATEAU `E_Y1 = E_Y2` and the maximum `E_Y3` are both untouched.
  ⇒ Neither edit can raise the global surface peak, which is why both are free under the no-clip rule.
  **Both facts are RE-DERIVED here on the grid, not asserted from this paragraph:** `assert_no_clip`
  requires the global peak to be byte-identical to V74's on every engaged mode.

🛑 THE PER-MODE CAP IS BINARY-SEARCHED, NOT HAND-COPIED. `derive_lever_f()` searches each mode's own
  largest admissible `C_Y0` against that mode's OWN `C_Y3`, `E_Y3` and `ceiling_floor()`, over the
  same 98,988-point grid, under the rule **"every point the edit RAISES must stay at or below that
  mode's own ceiling floor"**. V74's own build capped modes 29/32/33 by a closed-form that was
  conservative by one count; the search is the honest derivation and it is re-run per mode.

⚠ MODES 2 AND 3 ARE HELD AT V74's 1356, NOT LOWERED TO 566 -- AND THIS IS A DELIBERATE DEVIATION
  FROM A LITERAL READING OF THE SPEC. Their FactorC record is a different shape entirely
  (`Y = [1356, 950, 1356, 1606]`, because V74 set `Y[0] := Y[2] = 1356`). Writing 566 there would
  LOWER a live cell by 790 counts -- a SUBTRACTION, which "additions only" forbids. Their own no-clip
  cap is 2076, so the hold is not a safety cap; it is the add-only rule. Both are TWAA-chassis modes,
  inert on this car. **Reported, not silently applied** -- see `HELD_AT_BASE`.

    DELIVERED DOSE, live mode 26, at the measured in-burst rate 99:   **50 -> 137 counts (2.74x)**
                                  at the 6-9 Hz arm's rate 127:       **66 -> 181 counts**
    🛑 Every number recomputed from the bytes actually written, and printed by the builder.

✅ NO-CLIP, TWO INDEPENDENT WAYS, both re-run here:
   1. the 98,988-point (speed, rate) grid: 0 points where `new > old AND new > floor`;
   2. the GLOBAL PEAK per mode must equal V74's exactly -- which is the structural claim above.
   ⊕ ALL ELEVEN modes written to 566 TOUCH the floor -- exactly 512, at the grid corner (speed 0,
   rate 4000, where `E = E_Y3 = 927` and `(566 * 927) >> 10 = 512`). That is BY CONSTRUCTION: 566 is
   the largest `C_Y0` for which that corner lands at or below 512, which is what the binary search
   returns. It is not clipping -- the clamp is `if |v| > ceiling`, so a value AT the ceiling passes
   through unchanged.
   ⚠ MODE 11 IS THE ONE THAT IS DIFFERENT, and for a separate reason: its FactorE is V72's flat
   `[927]*4`, so it sits at 512 across its WHOLE rate axis at creep speed -- including at rate 0.
   That is a pre-existing property of V72's edit to that record, not something V75 created, and mode
   11 is inert on this car (it is row 2's engaged mode, not row 11's).

★★ THE 512 FLOOR IS UNCONDITIONAL -- [EVIDENCE], and it closes an [OPEN] raised against this build.
   The ceiling's own reader is `ld.hu -0x6ac2,gp,r12` @**0x346A4** (UNSIGNED -- pinned in Ghidra, not
   inferred from `FUN_00041464`'s lockstep reads), followed by `addi -0x32c9,r12,r0` / `bnc` -- an
   UNSIGNED compare. So the `0xFFFF` sentinel that `0x41B44` can write is **65535 >= 0x32C9** and
   therefore skips the LERP entirely, taking the `ld.hu 0x7158,tp,r6` FALLBACK at 0x346AE.
   🛑 That fallback cell `tp+0x7158` = **0xC6158 = 512** -- byte-identical to the LERP's own `Y[0]`,
   on stock, on V74 and on V75. ⇒ **Both branches yield 512**, so the floor this build's whole
   no-clip argument rests on cannot be evaded by the sentinel path. (The competing reading -- that a
   u16 sentinel would RAIL the ceiling to 1024 -- is wrong: the u16 path never reaches the LERP.)

EDIT 3 -- THE PROBE, REDESIGNED. 68 of the proven 68 B, ZERO padding.
----------------------------------------------------------------------
🛑 THIS IS NOT OPTIONAL: V74's PROBE CANNOT DISTINGUISH V75 FROM V74. Its `bits 6:3` read
`gp-0x67fa`, which measured a constant 5, and its `bit7` is a *liveness* bit that reads broadly the
same on both builds. V75 spends the same five bits on MAGNITUDE:

    bit7 = (gp-0x6bd0 != 0)        ★ UNCHANGED FROM V74 -- the positive control AND the cross-build
                                     anchor. Same cell, same test; only the instruction path differs.
    bit6 = (|gp-0x6bd0| >= 128)
    bit5 = (|gp-0x6bd0| >= 288)
    bit4 = (|gp-0x6bd0| >= 448)    the near-ceiling indicator; the ceiling FLOOR is 512
    bit3 = (gp-0x6ac2  != 0)       ★★ THE BACK-DRIVE GATE. Never measured in this kit.
    bits 2:0 = live STEER_SENSOR_STATUS, preserved exactly as V74 does.

★★ THE THERMOMETER IS A STRUCTURAL INVARIANT, AND IT BUYS BUILD IDENTITY -- WHICH V74 DID NOT HAVE.
   bit4 => bit5 => bit6 => bit7 by construction, so only **10 of the 32** payloads in bits 7:3 are
   reachable: `{0x00,0x08,0x80,0x88,0xC0,0xC8,0xE0,0xE8,0xF0,0xF8}`. V74's own on-car payload was
   `0x28`/`0xA8` (state 5) and V73's was `0xC0`/`0xD0` -- **`0x28`, `0xA8` and `0xD0` are all ILLEGAL
   here**, so a V74 or V73 log is REJECTED by the payload alphabet alone. V74's guard could only ever
   reject on behavioural discriminators; this one rejects structurally.

★ THE THRESHOLDS ARE ALL MULTIPLES OF 32, WHICH IS WHY THIS FITS IN 68 BYTES. 128 = 4*32,
  288 = 9*32, 448 = 14*32, so ONE `shr 0x5,r6` turns all three into `cmp imm5` compares whose
  immediates (4, 9, 14) sit inside Format II's signed 5-bit range. A threshold that was not a
  multiple of 32 would need a `movea` per rung and would not fit.
★ THE ACCUMULATOR IS SHIFTED TWICE, ON PURPOSE. bits 7:4 are accumulated at weights 8/4/2/1 and then
  `shl 0x4`; bit3 is added AFTER the shift at weight 8. Accumulating bit7 at its natural pre-shift
  weight of 16 is impossible -- `add imm5` tops out at +15 -- and would have cost a 4-byte `movea`,
  putting the cave 2 bytes over the proven extent. **Growing the cave is this kit's ONLY bricking
  class (V24, V27, V48B).**

🛑 THE ONE-BIT TRAPS, EACH PINNED AND EACH DECODED BY FIELD
------------------------------------------------------------
  · `ld.h` op 0x39 vs `st.h` op 0x3B -- and `st.h r6,-0x6bd0,gp` IS a real instruction at 0x34730
    writing this very cell. The wrong bit makes the cave OVERWRITE the damper.
  · `ld.hu` op 0x3F is `ld.w` when hw2's LSB is CLEAR. `-0x6AC2` is halfword- but NOT word-aligned,
    so a `ld.w` there is a misaligned 32-bit read spanning `gp-0x6ac2` AND `gp-0x6ac0`. hw2's LSB is
    asserted SET.
  · `be` cond 0x2 vs `bne` 0xA, and `bge` 0xE vs `blt` 0x6 -- every displacement is decoded from the
    Format III field split and matched to an emitted instruction BOUNDARY, never to `addr + imm`.
  · `or r6,r7` vs `or r7,r6` -- same opcode, register fields swapped, BOTH real in this image. The
    fields are decoded. (V75 uses only the MERGE form `or r7,r6`; there is no accumulate `or`.)
  · `add 0x8,r7` appears TWICE with different meanings (bit7 pre-shift, bit3 post-shift). Their
    ORDER relative to `shl 0x4,r7` is asserted, because swapping them silently relabels two bits.

★★ TWO LOCKSTEP SHADOWS THAT V74 DID NOT GUARD, FOUND BY DECOMPILING FUN_00034350 AND FUN_00041464:
   `gp-0x6bd0` is shadowed at **`gp-0x4cf2`** and `gp-0x6ac2` at **`gp-0x4cc6`**; both writers compare
   the pair and escalate to `FUN_0006b9fa` on disagreement. The cave only READS, so the blast radius
   is zero -- but all three shadows (incl. `gp-0x4c39`) are asserted untouched.

★ `gp-0x6ac2` IS THE CEILING TABLE'S OWN LERP INDEX -- [EVIDENCE], from the decompile of
  FUN_00034350: `if (gp-0x6ac2 < 0x32c9) { LERP(gp-0x6ac2, 0xC77A0[mode]) } else { tp+0x7158 }`, and
  that result is the +/- clamp applied to `gp-0x6bd0`. Its producer (FUN_00041464) is
  `gp-0x6ac2 = |rate| >> 10 when sign(rate) != sign(gp-0x6b98), else 0` -- exactly the stated
  back-drive gate. ⚠ THE HONEST CAVEAT, stated here and in the decoder: the ceiling only RISES above
  512 once `gp-0x6ac2` exceeds X[0] = 300, and the cell is forced to the sentinel 0xFFFF when
  `|gp-0x6b98| >= 0x2000`. So `bit3 = 1` means "the index is not zero", which is NECESSARY but NOT
  SUFFICIENT for a lifted ceiling. A 300-count threshold does not fit in the remaining bytes.

🛑 MUST NOT CHANGE -- asserted byte-identical to V74 on the input, the output AND the .rwd readback
-----------------------------------------------------------------------------------------------------
  The friction records (V74's x1.5) · `0xC407E` = 850 · the whole r24/r26 rate lane incl. V72's r26
  cut · BOTH `sar` sites at STOCK (**reintroducing V62's `a9` causes grind #2 -- the fix is an
  ABSENCE**) · the gate · both scalar arms · `0x454FE` · `0xC77A0` (the ceiling table -- explicitly
  NOT this build's lever) · FactorE's whole Y row · every DISENGAGED-column record.

Usage:  python builds/v50_v79/build_v75_tva.py
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
import build_v54_tva as V54                # noqa: E402  (andi / or_rr / shl / cmp_rr encoders)
import build_v55_tva as V55                # noqa: E402  (ldbu_any / ldh / cmp_imm5)
import build_v57_tva as V57                # noqa: E402
import build_v64_tva as V64                # noqa: E402  (gp_access_census -- the raw byte scan)
import build_v68_tva as V68                # noqa: E402  (cave machinery)
import build_v71a_tva as A                 # noqa: E402
import build_v72_tva as V72                # noqa: E402
import build_v74_tva as V74                # noqa: E402  (THE BASE -- its levers, guards and readers)
import v72_lane_model as LM                # noqa: E402  (lerp_int)
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
# THE BASE -- V74, carried
# =====================================================================================================
SRC_BIN = plain_image_path("_v74_engagedcols_x0_12_addonly_plain_image.bin")
SRC_SHA256 = "8ae58cb8f41d0486a72454608835e399276bfdcfad464c6c9b52bc7107bfa959"
STOCK_BIN = stock_fw_path("code.bin")
# 🛑 A SAME-NUMBER RE-CUT ONCE OVERWROTE A PREDECESSOR'S PLAIN IMAGE and produced an artefact NO gate
# could check. The recorded FIX is `_v<NN><tag>_plain_image.bin`, and the tag carries the parameters
# that distinguish this cut. `build()` additionally REFUSES to overwrite a DIFFERING existing file.
# 🛑 BOTH OUTPUT NAMES ENCODE THE LEVER SET and are computed at build time from `LEVERS` -- see
# `lever_token()` / `bin_out()` / `out_rwd()` below. They are NOT module constants, precisely so a
# lever toggle cannot leave a stale name pointing at different bytes.

# 🛑 V74's / V72's own levers, re-declared HERE as literals (not imported) so a drift in either fails.
V72_GAIN_A = {0xC6A68: [512] * 4, 0xC6A7C: [512] * 4}
V72_LEVER_C = (0xC63A0, 2048)
V72_CARRIED = (0x454FE, 0xB5)
V72_GATE = (0x3AA96, 0xC5)
SAR_SITES = {0x3AB76: bytes.fromhex("aa32"), 0x3AC20: bytes.fromhex("aa42")}
ARMS_STOCK = {0xC643E: 1536, 0xC6444: 512, 0xC6446: 512}
GAIN_B_M10_KEEP = {0xD2A74: [5244] * 4, 0xD2AB0: [5244] * 4}
REC_STRIDE = 0x14

# =====================================================================================================
# THE MODE COLUMNS -- derived from the config table, never hand-listed
# =====================================================================================================
VARIANT_KEY_TABLE, VARIANT_IDX_TABLE, VARIANT_STRIDE = 0xCD000, 0xCD012, 0x24
VARIANT_ROWS = 16
ENGAGED_EXPECTED = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_EXPECTED = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
THIS_CAR_ROW, THIS_CAR_KEY = 11, "TVCA4"
THIS_CAR_MODES = [24, 25, 26, 27]
LIVE_MODE = 26

# =====================================================================================================
# EDIT 1 + EDIT 2 -- THE DOSE CRANK
# =====================================================================================================
FACTOR_B_PTRS, FACTOR_C_PTRS = 0xC9CCC, 0xC9E9C
FACTOR_D_PTRS, FACTOR_E_PTRS = 0xC9DB4, 0xC9F84
CEILING_PTRS = 0xC77A0
FRICTION_PTR_ARRAY = 0xCBE74
REC4_X_OFF, REC4_Y_OFF = 0x02, 0x0A
CEILING_X, CEILING_Y = [300, 800], [512, 1024]
CEILING_FLOOR = CEILING_Y[0]               # 512 -- 🛑 VERIFIED PER MODE, never assumed from one

TARGET_C_Y0 = 566                          # LEVER CY0 -- the creep end of FactorC's speed axis
TARGET_E_X1 = 200                          # LEVER EX1 -- FactorE's low-rate breakpoint, moved LEFT

# =====================================================================================================
# ★★ THE TWO LEVERS ARE INDEPENDENTLY TOGGLEABLE. A re-cut is a FLAG, not a rewrite.
# =====================================================================================================
# 🛑 WHY THIS MATTERS RIGHT NOW: the route-5d abort check puts V74's own 5x-f0 prominence at
# 2.884 [2.301, 3.575] against a 3.0 abort line, and its CREEP-ONLY arm at 5.844 against a 0.632
# baseline -- and creep is exactly where LEVER CY0 acts (`FactorC Y[0]` IS the creep cell). If that
# elevation turns out to be a relay harmonic rather than grind #1's pre-existing 42.19 Hz second
# harmonic, the re-spec is "drop CY0, keep EX1". So the two edits derive in SEPARATE functions, carry
# SEPARATE assertions, land in SEPARATE byte-attribution buckets, and BOTH FILENAMES encode the set.
#
# ⚠ THE DEPENDENCE IS ONE-WAY AND IT IS REAL. As a *toggle* the levers are independent, but CY0's
# no-clip CAP is derived against whatever EX1 actually wrote, because the two multiply. EX1 is
# therefore derived and applied FIRST, and `derive_lever_cy0` reads the E axis off the image. Turning
# EX1 off and leaving CY0 on re-runs the search against the stock E axis and may return a different
# cap -- which is correct behaviour, not a bug. It is never hand-copied.
LEVERS = {"CY0": True, "EX1": True}

# ⊕ 2026-08-06, AFTER V75 FLEW AND HARD-FAULTED: the re-spec anticipated above is now REAL, but for a
# reason the header did not foresee -- not a relay harmonic, a GATE 2 loop-gain overshoot. The ramp-regime
# incremental gain k = (C_Y0*Y[1]>>10)/(X[1]-X[0]) is a FREQUENCY-INDEPENDENT scalar on the whole damper
# path, so it scales loop gain equally at every frequency and no plant model is needed to compare builds:
#     stock k = 0.0000 (no loop through this path)  |  V74 k = 0.5799, flew 1,011 s CLEAN
#     V75   k = 1.5798 = +8.70 dB over V74          |  FAULTED (latched loss of assist, stoplight launch)
# => the critical gain is bracketed k* in (0.580, 1.580]; V74's margin here is >0 dB and <8.70 dB.
# Dropping EX1 alone gives k = 0.7655 = +2.41 dB over V74 while keeping the plateau (M = 297) and thus
# ~99% of V75's grind-band and ~88% of its ratchet damping. That cut is SINGLE-VARIABLE against BOTH
# flown builds (V74 + CY0 ; V75 - EX1), which no other candidate is.
# 🛑 Do NOT hand-edit the dict for a re-cut -- set ACCORD_V75_LEVERS instead, so this file keeps
# reproducing the FLOWN V75 byte-for-byte. The cap search still re-derives against whatever E axis is
# actually written (see the one-way dependence note above); it is never hand-copied.
#     ACCORD_V75_LEVERS=CY0        -> drop EX1, keep CY0   (the post-fault re-cut)
#     ACCORD_V75_LEVERS=CY0,EX1    -> the flown V75
#     ACCORD_V75_LEVERS=EX1        -> EX1 only
if os.environ.get("ACCORD_V75_LEVERS"):
    _sel = {t.strip().upper() for t in os.environ["ACCORD_V75_LEVERS"].split(",") if t.strip()}
    assert _sel <= {"CY0", "EX1"}, f"unknown lever(s): {_sel - {'CY0', 'EX1'}}"
    LEVERS = {"CY0": "CY0" in _sel, "EX1": "EX1" in _sel}
    print(f"[LEVERS] overridden from ACCORD_V75_LEVERS -> {LEVERS}")


def lever_token():
    """The lever set as a filename-safe token. 🛑 The ONLY pre-drive discriminator between cuts.

    A recorded hazard: two V70 cuts both wrote `_v70_plain_image.bin`, so the second OVERWROTE the
    first's snapshot while the first's `.rwd` stayed flashable -- an artefact NO gate could check.
    The cave is byte-identical across every V75 lever set, so the PAYLOAD cannot tell two cuts
    apart either. The filename is it.

    🛑 THE SEPARATOR IS `-`, NOT `+`, AND THAT IS NOT COSMETIC. The first cut used `+` and the
    Ghidra MCP layer silently URL-decoded it to a SPACE, so `program:` lookups by filename failed to
    resolve -- on the one file whose NAME is the only pre-drive discriminator. Any `+` in an artefact
    name is a wrong-file hazard. Dots and hyphens only.
    """
    parts = [t for t in (f"CY0.{TARGET_C_Y0}" if LEVERS["CY0"] else None,
                         f"EX1.{TARGET_E_X1}" if LEVERS["EX1"] else None) if t]
    token = "-".join(parts) if parts else "NONE"
    assert all(c.isalnum() or c in ".-" for c in token), \
        f"the lever token {token!r} carries a character that tooling may mangle -- `+` was already " \
        "URL-decoded to a space by the Ghidra MCP layer once"
    return token
E_X0_CARRIED = 12                          # V74's, NOT re-written. Asserted per mode.
CAP_SEARCH_HI = 4096                       # the binary search's upper bound (>> any admissible value)

BURST_RATE = 99                            # measured |gp-0x6ac0| p50 IN-BURST, [94.2, 113.0]
BURST_RATE_69HZ = 127                      # the 6-9 Hz arm's p50
OUT_OF_BURST_RATE = 9                      # 🛑 the OUT-of-burst p50 -- NOT the sizing input
OBSERVED_PEAK_V74 = 225                    # |gp-0x6bd0| peak actually driven on V74
PREDICTED_PEAK_V75 = 354                   # 69% of the 512 floor -- the basis for the bit4 threshold

# ⊕ The expected outcome for THE LIVE MODE, stated independently and asserted after dereferencing.
LIVE_EXPECT = {"factor_c": 0xD77D0, "factor_c_y0": 0xD77DA,
               "factor_e": 0xD780C, "factor_e_x1": 0xD7810,
               "factor_c_y0_old": 429, "factor_c_y0_new": 566,
               "factor_e_x1_old": 400, "factor_e_x1_new": 200,
               "dose_old": 50, "dose": 137, "dose_69hz": 181}
DOSE_RATIO_LIVE = 2.74                     # 137 / 50, to 2 dp

# ⚠ THE DELIBERATE DEVIATION, declared as data so the build must print it.
HELD_AT_BASE = (2, 3)                      # C_Y0 stays at V74's 1356: writing 566 would SUBTRACT
# 🛑 FactorE's Y ROW HAS ZERO VERIFIED HEADROOM -- named so the guard below is unmissable.
FACTOR_E_Y_FROZEN = True

# =====================================================================================================
# EDIT 3 -- THE PROBE
# =====================================================================================================
PAYLOAD_BYTE4_DISP = V68.PAYLOAD_BYTE4_DISP     # 0x1514 -- the CAN-330 TX buffer byte
PAYLOAD_KEEP_MASK = V68.PAYLOAD_KEEP_MASK       # 0x7 -- stock STEER_SENSOR_STATUS, preserved
HOOK_ADDR, HOOK_STOCK = V68.HOOK_ADDR, V68.HOOK_STOCK
HOOK_RETURN = HOOK_ADDR + 4                     # 0x55C12
HOOK_RETURN_INSN = bytes.fromhex("083a")        # `mov 0x8,r7` -- proves r7 is DEAD across the hook

DAMP_DISP = 0x6BD0              # gp-0x6bd0 -- the damper output.  ld.h, SIGNED
BACKDRIVE_DISP = 0x6AC2         # gp-0x6ac2 -- the ceiling LERP index. ld.hu, UNSIGNED
STATE_DISP = 0x67FA             # ⚠ V74's state cell. V75 does NOT read it -- asserted, see below.

MAG_SHIFT = 5                   # |x| >> 5, so every threshold becomes a multiple of 32
MAG_THRESHOLDS = (128, 288, 448)                # -> bits 6, 5, 4
MAG_IMM5 = tuple(t >> MAG_SHIFT for t in MAG_THRESHOLDS)        # (4, 9, 14) -- inside `cmp imm5`
W_B7, W_B6, W_B5, W_B4 = 8, 4, 2, 1             # PRE-`shl 0x4` weights
W_B3_POST = 8                                   # bit3 is added AFTER the shift
HI_SHIFT = 4                                    # `shl 0x4,r7` -- puts the 4-bit thermometer at 7:4
BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288 = 0x80, 0x40, 0x20
BIT_MAG448, BIT_BACKDRIVE = 0x10, 0x08
PROBE_MASK = 0xF8
BE_SKIP_ZERO = 8                # `be +8`  -- skips bge + subr + the bit7 setter
BGE_SKIP_NEG = 4                # `bge +4` -- skips the 2-byte `subr`
BLT_SKIP = 4                    # `blt +4` -- skips one 2-byte `add`
BE_SKIP_BD = 4                  # `be +4`  -- skips the 2-byte bit3 `add`

# The probed cells' firmware censuses, on the V74 base. (reads, writes, read mnemonics, write mnem.)
DAMP_CENSUS = (5, 3, {"ld.h"}, {"st.h"})
DAMP_WRITERS = [0x34730, 0x34744, 0x34752]      # all inside FUN_00034350
BACKDRIVE_CENSUS = (8, 4, {"ld.hu"}, {"st.h"})
BACKDRIVE_WRITERS = [0x418CE, 0x418E0, 0x41B30, 0x41B44]        # all inside FUN_00041464
# 🛑 ALL THREE LOCKSTEP SHADOWS. gp-0x4cf2 and gp-0x4cc6 were found by decompiling FUN_00034350 and
# FUN_00041464 for THIS build; V74 guarded only gp-0x4c39. A stray write to either half escalates.
SHADOW_DISPS = {0x4C39: "gp-0x67fa's", 0x4CF2: "gp-0x6bd0's", 0x4CC6: "gp-0x6ac2's"}

# ---- instruction pins. Every halfword we emit reproduces a REAL instance in the STOCK image, and
# ---- every one below was rendered by Ghidra's own disassembler at that address before being used.
PIN_MOVI5_0_R7 = (0x34114, bytes.fromhex("003a"))          # `mov 0x0,r7`
PIN_LDH_HW1 = (0x3ACA8, bytes.fromhex("24372c95"))         # hw1 donor: a real `ld.h ...,gp,r6`
PIN_LDH_6BD0_DISP = (0x34726, bytes.fromhex("243f3094"))   # hw2 donor: `ld.h -0x6bd0[gp],r7`
PIN_STH_6BD0 = (0x34730, bytes.fromhex("64373094"))        # 🛑 THE ONE-BIT TWIN: st.h, SAME reg/disp
PIN_CMP_R0_R6 = (0x3401E, bytes.fromhex("e031"))           # `cmp r0,r6`
PIN_BE8 = (0x00C02, bytes.fromhex("c205"))                 # `be 0xC0A`  = +8   Ghidra-confirmed
PIN_BGE4 = (0x244CE, bytes.fromhex("ae05"))                # `bge 0x244D2` = +4 Ghidra-confirmed
PIN_BLT4 = (0x290A8, bytes.fromhex("a605"))                # `blt 0x290AC` = +4 Ghidra-confirmed
PIN_BE4 = (0x02998, bytes.fromhex("a205"))                 # `be +4`
PIN_SUBR_R0_R6 = (0x2A150, bytes.fromhex("8031"))          # `subr r0,r6` -> r6 = -r6
PIN_SHR5_R6 = (0x18264, bytes.fromhex("8532"))             # `shr 0x5,r6` (LOGICAL; r6 >= 0 here)
PIN_CMP4_R6 = (0x027CA, bytes.fromhex("6432"))             # `cmp 0x4,r6`
PIN_CMP9_R6 = (0x0D398, bytes.fromhex("6932"))             # `cmp 0x9,r6`
PIN_CMP14_R6 = (0x07396, bytes.fromhex("6e32"))            # `cmp 0xe,r6`
PIN_ADD8_R7 = (0x0370C, bytes.fromhex("483a"))             # `add 0x8,r7`
PIN_ADD4_R7 = (0x038C4, bytes.fromhex("443a"))             # `add 0x4,r7`
PIN_ADD2_R7 = (0x27EF0, bytes.fromhex("423a"))             # `add 0x2,r7`
PIN_ADD1_R7 = (0x0EEE4, bytes.fromhex("413a"))             # `add 0x1,r7`
PIN_SHL4_R7 = (0x1C1C2, bytes.fromhex("c43a"))             # `shl 0x4,r7`
PIN_LDHU_HW1 = (0x14F30, bytes.fromhex("e437"))            # hw1 donor: a real `ld.hu ...,gp,r6`
PIN_LDHU_6AC2_DISP = (0x346A4, bytes.fromhex("e4673f95"))  # hw2 donor: `ld.hu -0x6ac2,gp,r12`
PIN_LDBU_BYTE4 = (0x55AD4, bytes.fromhex("8437edea"))      # `ld.bu -0x1514,gp,r6`
PIN_ANDI_7_R6 = (0x1FEA0, bytes.fromhex("c6360700"))       # `andi 0x7,r6,r6`
PIN_OR_R7_R6 = (0x68728, bytes.fromhex("0731"))            # `or r7,r6`   -> r6 |= r7   (THE MERGE)
PIN_OR_R6_R7 = (0x1C1C4, bytes.fromhex("0639"))            # 🛑 the SWAPPED twin -- asserted away
PIN_STB_BYTE4 = (0x55AE8, bytes.fromhex("4437ecea"))       # `st.b r6,-0x1514,gp` -- THE ONLY STORE
PIN_MOVEA_HOOK = (0x55C0E, bytes.fromhex("2436e8ea"))      # the displaced `movea -0x1518,gp,r6`
PIN_JMP_LP = (0x1E4, bytes.fromhex("7f00"))                # `jmp lp`

COND_BE, COND_BNE = FF.COND_BE, FF.COND_BNE                # 0x2 / 0xA -- the INVERTING twin
COND_BLT, COND_BGE = 0x6, 0xE                              # the OTHER inverting pair

# ⚠ DELIBERATELY SHORT and asserted BEFORE anything is written -- V71A's note records an over-long
# tag that overran Windows' 260-char path limit and failed the .rwd write AFTER the image was on disk.
DECODER = os.path.join(HERE, "..", "rlog-tools", "probe/decode_v75_probe.py")


def bin_out():
    """The plain-image path. 🛑 CARRIES THE LEVER SET -- a re-cut must not reuse a sibling's name."""
    return str(plain_image_path(f"_v75_{lever_token()}_magprobe_plain_image.bin"))


def tag():
    return f"V74BASE-ENGCOLS13-levers-{lever_token()}-magprobe-6bd0-thermo-6ac2"


def out_rwd():
    """The .rwd path -- SELF-DESCRIBING: the lever set is in the filename, not only in this file."""
    return os.path.join(RWD_DIR, f"39990-TVA,A160-V75-{tag()}-0x{START:X}-0x{END:X}.rwd")


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def s16(buf, a):
    return struct.unpack_from("<h", buf, a)[0]


def u32(buf, a):
    return struct.unpack_from("<I", buf, a)[0]


rec_any = V74.rec_any                   # (count, X, Y), driven by the record's OWN count word
rec_len = V74.rec_len                   # 4 + 4n -- 🛑 NOT a flat 0x18 window
rec4_y = V74.rec4_y
factor_rec = V74.factor_rec             # DEREFERENCED from the pointer array, never quoted
ceiling_floor = V74.ceiling_floor       # that mode's OWN floor, re-read per mode
damper_authority = V74.damper_authority  # FUN_00034350's Q10 chain, mirrored EXACTLY


# =====================================================================================================
# Encoders this build adds. Each is pinned to a REAL instruction and Ghidra-confirmed at that address.
# =====================================================================================================

def addi5(imm5, reg2):
    """Format II `add imm5,reg2`, opcode 0x12. imm5 is SIGN-extended: the range is -16..+15."""
    assert -16 <= imm5 <= 15, f"add imm5 {imm5} is outside Format II's signed 5-bit range"
    assert 0 <= reg2 < 32
    return struct.pack("<H", (reg2 << 11) | (0x12 << 5) | (imm5 & 0x1F))


def subr_rr(reg1, reg2):
    """Format I `subr reg1,reg2`, opcode 0x0C -> reg2 = reg1 - reg2.

    🛑 NOT `sub` (0x0D), whose operand order is the other way round. With reg1 = r0 this negates.
    """
    assert 0 <= reg1 < 32 and 0 <= reg2 < 32
    return struct.pack("<H", (reg2 << 11) | (0x0C << 5) | reg1)


def ldhu_gp(disp, reg2):
    """`ld.hu -disp[gp],reg2`, opcode 0x3F.

    🛑 THE FORMAT SELECTOR IS hw2's LSB: SET = ld.hu, CLEAR = ld.w. `-0x6AC2` is halfword- but not
    word-aligned, so the ld.w form would be a MISALIGNED 32-bit read spanning gp-0x6ac2 AND
    gp-0x6ac0 -- a different cell and a possible alignment fault. The bit is asserted below.
    """
    assert 0 < disp <= 0x8000 and disp % 2 == 0, f"gp-0x{disp:04X} is not an even displacement"
    hw2 = ((0x10000 - disp) & 0xFFFE) | 1
    return struct.pack("<HH", (reg2 << 11) | (0x3F << 5) | GP, hw2)


# =====================================================================================================
# The wire model -- a Python mirror of the cave, instruction for instruction
# =====================================================================================================

def wire_byte4(v6bd0, v6ac2, status_bits=0x7):
    """EXACTLY what the emitted cave computes. Mirrors the instructions, not a paraphrase."""
    r7 = 0                                              # mov 0x0,r7
    r6 = v6bd0 - 0x10000 if v6bd0 & 0x8000 else v6bd0   # ld.h   (SIGN-extends a halfword)
    if r6 != 0:                                         # cmp r0,r6 ; be +8
        if r6 < 0:                                      # bge +4
            r6 = -r6                                    # subr r0,r6
        r7 += W_B7                                      # add 0x8,r7   -> bit7
    r6 >>= MAG_SHIFT                                    # shr 0x5,r6   (r6 >= 0, so logical == arith)
    if r6 >= MAG_IMM5[0]:                               # cmp 0x4,r6 ; blt +4
        r7 += W_B6                                      # add 0x4,r7   -> bit6
    if r6 >= MAG_IMM5[1]:                               # cmp 0x9,r6 ; blt +4
        r7 += W_B5                                      # add 0x2,r7   -> bit5
    if r6 >= MAG_IMM5[2]:                               # cmp 0xe,r6 ; blt +4
        r7 += W_B4                                      # add 0x1,r7   -> bit4
    r7 <<= HI_SHIFT                                     # shl 0x4,r7
    if (v6ac2 & 0xFFFF) != 0:                           # ld.hu (ZERO-extends) ; cmp r0,r6 ; be +4
        r7 += W_B3_POST                                 # add 0x8,r7   -> bit3
    r6 = status_bits & PAYLOAD_KEEP_MASK                # ld.bu -0x1514[gp],r6 ; andi 0x7,r6,r6
    r6 |= r7                                            # or r7,r6
    return r6 & 0xFF                                    # st.b stores the LOW BYTE


def _thermo(v):
    """The reference thermometer, written from the SPEC rather than from the wire model."""
    a = abs(v - 0x10000 if v & 0x8000 else v)
    return ((BIT_DAMP_NZ if a != 0 else 0) | (BIT_MAG128 if a >= MAG_THRESHOLDS[0] else 0)
            | (BIT_MAG288 if a >= MAG_THRESHOLDS[1] else 0)
            | (BIT_MAG448 if a >= MAG_THRESHOLDS[2] else 0))


# ★ ONLY 10 of the 32 payloads are reachable, BECAUSE the four damper bits are a thermometer.
LEGAL_PAYLOADS = sorted({_thermo(v) | b for v in range(0x10000) for b in (0, BIT_BACKDRIVE)})


def _wire_model():
    """The rung's semantics, checked over the FULL 16-bit input range -- not a sample."""
    # 🛑 EXHAUSTIVE over every possible `gp-0x6bd0`, against a spec-derived reference.
    for v in range(0x10000):
        b = wire_byte4(v, 0)
        assert (b & PROBE_MASK) == _thermo(v), \
            f"the wire model disagrees with the spec thermometer at 0x{v:04X}"
    # the thresholds land EXACTLY where the spec says, from both sides, in both signs
    for t, bit in zip(MAG_THRESHOLDS, (BIT_MAG128, BIT_MAG288, BIT_MAG448)):
        for sign in (1, -1):
            assert wire_byte4((sign * t) & 0xFFFF, 0) & bit, f"|x| = {t} does not set 0x{bit:02X}"
            assert not (wire_byte4((sign * (t - 1)) & 0xFFFF, 0) & bit), \
                f"|x| = {t - 1} DOES set 0x{bit:02X} -- the threshold is off by one"
    # 🛑 bit7 must be TWO-SIDED and must be EXACTLY the V74 test, so the two builds are comparable.
    assert wire_byte4(0xFFFF, 0) & BIT_DAMP_NZ and wire_byte4(0x0001, 0) & BIT_DAMP_NZ, \
        "bit7 is not two-sided -- a negative damper output must set it"
    assert not (wire_byte4(0x0000, 0) & BIT_DAMP_NZ), "bit7 sets on a ZERO damper output"
    assert not (wire_byte4(0x0000, 0) & (BIT_MAG128 | BIT_MAG288 | BIT_MAG448)), \
        "a magnitude bit sets on a ZERO damper output"
    # ★ THE THERMOMETER INVARIANT -- the whole basis of the build-identity guard.
    for v in range(0x10000):
        b = wire_byte4(v, 0)
        assert not (b & BIT_MAG128) or (b & BIT_DAMP_NZ), "bit6 without bit7"
        assert not (b & BIT_MAG288) or (b & BIT_MAG128), "bit5 without bit6"
        assert not (b & BIT_MAG448) or (b & BIT_MAG288), "bit4 without bit5"
    assert len(LEGAL_PAYLOADS) == 10, f"{len(LEGAL_PAYLOADS)} legal payloads, expected 10"
    assert LEGAL_PAYLOADS == [0x00, 0x08, 0x80, 0x88, 0xC0, 0xC8, 0xE0, 0xE8, 0xF0, 0xF8], \
        f"the legal payload set moved: {[hex(p) for p in LEGAL_PAYLOADS]}"
    # 🛑 V74's and V73's own on-car payloads must be ILLEGAL here -- that is the identity guard.
    for stale, who in ((0x28, "V74 state 5, bit7 clear"), (0xA8, "V74 state 5, bit7 set"),
                       (0xD0, "V73 mode 26 -> field 10, bit7 set")):
        assert stale not in LEGAL_PAYLOADS, f"0x{stale:02X} ({who}) is LEGAL on V75 -- no identity"
    # bit3 is INDEPENDENT of the damper and must never disturb the thermometer
    for v in (0, 1, 127, 128, 287, 288, 447, 448, 0x7FFF, 0x8000, 0xFFFF):
        for bd in (0, 1, 0x7FFF, 0x8000, 0xFFFF):
            b = wire_byte4(v, bd)
            assert bool(b & BIT_BACKDRIVE) == (bd != 0), f"bit3 is not `gp-0x6ac2 != 0` at {bd}"
            assert (b & (PROBE_MASK ^ BIT_BACKDRIVE)) == _thermo(v), "bit3 disturbed the thermometer"
            assert (b & PROBE_MASK) in LEGAL_PAYLOADS, f"payload 0x{b:02X} is outside LEGAL"
    # the preserved status bits, and the field's confinement to bits 7:3
    for status in range(8):
        for v in (0, 0x0100, 0xFF00):
            for bd in (0, 1):
                b = wire_byte4(v, bd, status_bits=status)
                assert b & PAYLOAD_KEEP_MASK == status, \
                    "the preserved STEER_SENSOR_STATUS bits 2:0 are not passed through untouched"
                assert (b & PROBE_MASK) | status == b, "the field escaped bits 7:3"
    assert PROBE_MASK & PAYLOAD_KEEP_MASK == 0 and \
        BIT_DAMP_NZ | BIT_MAG128 | BIT_MAG288 | BIT_MAG448 | BIT_BACKDRIVE == PROBE_MASK == 0xF8, \
        "the probe bits do not cover exactly 7:3"
    # 🛑 THE ACCUMULATOR CANNOT OVERFLOW THE BYTE: max r7 before the merge is 0xF8.
    assert ((W_B7 + W_B6 + W_B5 + W_B4) << HI_SHIFT) + W_B3_POST == 0xF8, \
        "the accumulator's maximum is not 0xF8 -- the weights or the shift are wrong"
    assert (W_B7 << HI_SHIFT) == BIT_DAMP_NZ and (W_B6 << HI_SHIFT) == BIT_MAG128 and \
        (W_B5 << HI_SHIFT) == BIT_MAG288 and (W_B4 << HI_SHIFT) == BIT_MAG448 and \
        W_B3_POST == BIT_BACKDRIVE, "a weight does not land on its declared bit"
    # 🛑 EVERY weight must be inside `add imm5`'s range -- this is WHY the shift is split in two.
    for w in (W_B7, W_B6, W_B5, W_B4, W_B3_POST):
        assert -16 <= w <= 15, f"weight {w} does not fit `add imm5`"
    assert not (-16 <= (BIT_DAMP_NZ >> 3) <= 15), \
        "bit7's natural pre-shl3 weight would have fitted add imm5 -- the two-shift design is moot"
    # the thresholds are multiples of the shift, which is why `cmp imm5` suffices
    for t, i in zip(MAG_THRESHOLDS, MAG_IMM5):
        assert t == i << MAG_SHIFT and 0 <= i <= 15, \
            f"threshold {t} is not {i} << {MAG_SHIFT} -- it would not fit `cmp imm5`"


def _self_check_encoders():
    """Every halfword we emit is pinned to a REAL instruction in the STOCK image.

    🛑 Caves are this kit's ONLY bricking class (V24, V27 and V48B all bricked the ECU).
    Each pin below was ALSO rendered by Ghidra's own disassembler at that address before being
    written into this file -- the pin is the byte check, Ghidra is the semantic check.
    """
    V55._self_check_encoders()               # chains down through V54/FF
    src = Path(STOCK_BIN).read_bytes()

    pins = [PIN_MOVI5_0_R7, PIN_LDH_HW1, PIN_LDH_6BD0_DISP, PIN_STH_6BD0, PIN_CMP_R0_R6, PIN_BE8,
            PIN_BGE4, PIN_BLT4, PIN_BE4, PIN_SUBR_R0_R6, PIN_SHR5_R6, PIN_CMP4_R6, PIN_CMP9_R6,
            PIN_CMP14_R6, PIN_ADD8_R7, PIN_ADD4_R7, PIN_ADD2_R7, PIN_ADD1_R7, PIN_SHL4_R7,
            PIN_LDHU_HW1, PIN_LDHU_6AC2_DISP, PIN_LDBU_BYTE4, PIN_ANDI_7_R6, PIN_OR_R7_R6,
            PIN_OR_R6_R7, PIN_STB_BYTE4, PIN_MOVEA_HOOK, PIN_JMP_LP]
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

    # ---- the back-drive load. `ld.hu`, matching the firmware's OWN eight readers of this cell. ----
    ldhu = ldhu_gp(BACKDRIVE_DISP, R6)
    hw1, hw2 = struct.unpack("<HH", ldhu)
    assert ldhu[:2] == PIN_LDHU_HW1[1], "the ld.hu hw1 is not the real `ld.hu ...,gp,r6` form"
    assert ldhu[2:] == PIN_LDHU_6AC2_DISP[1][2:], \
        "the ld.hu displacement halfword is not the real -0x6ac2"
    assert ((hw1 >> 5) & 0x3F) == 0x3F, "the back-drive load's opcode field is not 0x3F"
    assert hw2 & 1 == 1, \
        "🛑 hw2's LSB is CLEAR -- opcode 0x3F with an even hw2 is `ld.w`, a MISALIGNED 32-bit read " \
        "spanning gp-0x6ac2 AND gp-0x6ac0. It would read a different quantity entirely."
    assert (hw2 & 0xFFFE) == ((0x10000 - BACKDRIVE_DISP) & 0xFFFE) == 0x953E, \
        "the ld.hu effective displacement is not -0x6ac2"
    assert (hw1 >> 11) == R6 and (hw1 & 0x1F) == GP == 4, "the back-drive load is not `... [gp],r6`"
    assert ldhu != FF.sth(R6, -BACKDRIVE_DISP, GP), "the back-drive load collapsed onto an st.h"
    assert ldhu != ldhu_gp(BACKDRIVE_DISP, R7), "the ld.hu register field is not r6"

    # ---- the abs sequence -------------------------------------------------------------------------
    assert subr_rr(R0, R6) == PIN_SUBR_R0_R6[1], "subr r0,r6 != the real one @0x2A150"
    hw = struct.unpack("<H", subr_rr(R0, R6))[0]
    assert ((hw >> 5) & 0x3F) == 0x0C and (hw >> 11) == R6 and (hw & 0x1F) == R0, \
        "🛑 `subr r0,r6` fields are wrong -- opcode 0x0D would be `sub`, whose operands are the " \
        "other way round, and r6 would become r6 - r0 = r6: the negate would VANISH"
    assert subr_rr(R0, R6) != struct.pack("<H", (R6 << 11) | (0x0D << 5) | R0), \
        "subr collapsed onto sub"
    assert FF.bcond(COND_BGE, BGE_SKIP_NEG) == PIN_BGE4[1], "bge +4 != the real one @0x244CE"
    assert FF.bcond(COND_BLT, BGE_SKIP_NEG) != FF.bcond(COND_BGE, BGE_SKIP_NEG), \
        "🛑 `bge +4` and `blt +4` collapsed -- the wrong one negates POSITIVE values instead"
    assert FF.bcond(COND_BLT, BLT_SKIP) == PIN_BLT4[1], "blt +4 != the real one @0x290A8"

    # ---- the branches ------------------------------------------------------------------------------
    assert FF.bcond(COND_BE, BE_SKIP_ZERO) == PIN_BE8[1], "be +8 != the real one @0xC02"
    assert FF.bcond(COND_BE, BE_SKIP_BD) == PIN_BE4[1], "be +4 != the real one @0x2998"
    assert FF.bcond(COND_BNE, BE_SKIP_ZERO) != FF.bcond(COND_BE, BE_SKIP_ZERO), \
        "🛑 `be +8` and `bne +8` collapsed -- the wrong one INVERTS the whole rung"
    assert FF.bcond(COND_BE, BE_SKIP_ZERO) != FF.bcond(COND_BE, BE_SKIP_BD), \
        "be +8 and be +4 collapsed -- +4 would land on the `subr`, negating a ZERO and setting bit7"

    # ---- the accumulator ---------------------------------------------------------------------------
    assert FF.movi5(0, R7) == PIN_MOVI5_0_R7[1], "mov 0x0,r7 != the real one @0x34114"
    assert FF.movi5(0, R7) != HOOK_RETURN_INSN, "mov 0x0,r7 collapsed onto the hook's `mov 0x8,r7`"
    assert V54.cmp_rr(R0, R6) == PIN_CMP_R0_R6[1], "cmp r0,r6 != the real one @0x3401E"
    assert V54.cmp_rr(R6, R0) != V54.cmp_rr(R0, R6), "cmp's two register fields collapsed"
    for imm, pin in zip(MAG_IMM5, (PIN_CMP4_R6, PIN_CMP9_R6, PIN_CMP14_R6)):
        assert V55.cmp_imm5(imm, R6) == pin[1], f"cmp 0x{imm:x},r6 != the real one @0x{pin[0]:05X}"
        hw = struct.unpack("<H", V55.cmp_imm5(imm, R6))[0]
        assert ((hw >> 5) & 0x3F) == 0x13 and (hw >> 11) == R6 and (hw & 0x1F) == imm, \
            f"`cmp 0x{imm:x},r6` fields are wrong"
    for w, pin in ((W_B7, PIN_ADD8_R7), (W_B6, PIN_ADD4_R7), (W_B5, PIN_ADD2_R7),
                   (W_B4, PIN_ADD1_R7)):
        assert addi5(w, R7) == pin[1], f"add 0x{w:x},r7 != the real one @0x{pin[0]:05X}"
        hw = struct.unpack("<H", addi5(w, R7))[0]
        assert ((hw >> 5) & 0x3F) == 0x12 and (hw >> 11) == R7 and (hw & 0x1F) == w, \
            f"`add 0x{w:x},r7` fields are wrong"
        assert addi5(w, R7) != V55.cmp_imm5(w, R7), \
            "🛑 `add imm5` and `cmp imm5` collapsed -- the accumulate would become a no-op compare"
        assert addi5(w, R7) != addi5(w, R6), "the add's register field is not r7"
    assert addi5(W_B3_POST, R7) == PIN_ADD8_R7[1] == addi5(W_B7, R7), \
        "the two `add 0x8,r7` (bit7 pre-shift / bit3 post-shift) are not the same encoding"
    assert FF.shr(MAG_SHIFT, R6) == PIN_SHR5_R6[1], "shr 0x5,r6 != the real one @0x18264"
    assert FF.shr(MAG_SHIFT, R6) != V55.sar(MAG_SHIFT, R6) and \
        FF.shr(MAG_SHIFT, R6) != V54.shl(MAG_SHIFT, R6), "shr collapsed onto sar or shl"
    assert V54.shl(HI_SHIFT, R7) == PIN_SHL4_R7[1], "shl 0x4,r7 != the real one @0x1C1C2"
    assert V54.shl(HI_SHIFT, R7) != V54.shl(3, R7), \
        "🛑 `shl 0x4` collapsed onto V74's `shl 0x3` -- every bit would land one position low"
    assert V54.shl(HI_SHIFT, R7) != FF.shr(HI_SHIFT, R7) and V54.shl(HI_SHIFT, R7) != \
        V55.sar(HI_SHIFT, R7), "shl collapsed onto a RIGHT shift"

    # ---- the merge and the store -------------------------------------------------------------------
    assert V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == PIN_LDBU_BYTE4[1], "the byte4 read changed"
    assert V54.andi(PAYLOAD_KEEP_MASK, R6, R6) == PIN_ANDI_7_R6[1], "andi 0x7,r6,r6 changed"
    # 🛑🛑 `or r7,r6` (0731) vs `or r6,r7` (0639) -- SAME opcode, register fields SWAPPED, and BOTH
    # are real instructions in this image, so a byte pin alone cannot catch the swap: the FIELDS are
    # decoded. V75's cave has only the MERGE form.
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


def build_cave():
    """pack_v75_probe -- entered by `jarl` from 0x55C0E, returns `jmp [lp]` to 0x55C12.

        mov   0x0,r7           ; r7 = 0
        ld.h  -0x6bd0[gp],r6   ; ★★★★ THE DAMPER'S OWN OUTPUT. SIGNED (op 0x39, NOT 0x3B = st.h)
        cmp   r0,r6            ; 🛑 Z set <=> the output is exactly 0. ONE cmp feeds TWO branches.
        be    +8               ;   -> the shr, with r6 = 0 and r7 = 0  (bit7 clear, no magnitude)
        bge   +4               ;   reads the SAME cmp's flags -- nothing between modifies them
        subr  r0,r6            ; r6 = -r6   (op 0x0C; 0x0D `sub` would leave r6 unchanged)
        add   0x8,r7           ; bit7 = (gp-0x6bd0 != 0)   ★ THE POSITIVE CONTROL, unchanged from V74
        shr   0x5,r6           ; q = |x| >> 5 -- turns every threshold into a `cmp imm5`
        cmp   0x4,r6           ; q >= 4  <=>  |x| >= 128
        blt   +4
        add   0x4,r7           ; bit6
        cmp   0x9,r6           ; q >= 9  <=>  |x| >= 288
        blt   +4
        add   0x2,r7           ; bit5
        cmp   0xe,r6           ; q >= 14 <=>  |x| >= 448   (the ceiling FLOOR is 512)
        blt   +4
        add   0x1,r7           ; bit4
        shl   0x4,r7           ; the 4-bit thermometer -> bits 7:4
        ld.hu -0x6ac2[gp],r6   ; ★★ THE BACK-DRIVE GATE / ceiling LERP index. UNSIGNED (hw2 LSB = 1,
                               ;    else the opcode is `ld.w` -- a MISALIGNED read of another cell)
        cmp   r0,r6
        be    +4
        add   0x8,r7           ; bit3 = (gp-0x6ac2 != 0)   -- weight 8 POST-shift
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4   (r6 is free again: the field is in r7)
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6            ; THE MERGE. 🛑 not `or r6,r7`
        st.b  r6,-0x1514[gp]   ; THE ONLY STORE
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
        <the full 68 bytes; there is NO padding this time>
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
    emit(V55.ldh(DAMP_DISP, R6),
         f"ld.h -0x{DAMP_DISP:04x}[gp],r6  ; ★★★★ THE DAMPER OUTPUT (SIGNED, op MUST be 0x39)",
         writes_r6=True)
    cmp0_idx = len(listing)
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6            ; 🛑 SETS Z iff the output is exactly 0")
    be0_idx = len(listing)
    emit(FF.bcond(COND_BE, BE_SKIP_ZERO), "be +8                ; Z => zero -> skip abs AND bit7")
    bge_idx = len(listing)
    emit(FF.bcond(COND_BGE, BGE_SKIP_NEG), "bge +4               ; SAME flags -- x > 0, skip negate")
    emit(subr_rr(R0, R6), "subr r0,r6           ; r6 = -r6   (op 0x0C, NOT 0x0D `sub`)",
         writes_r6=True)
    emit(addi5(W_B7, R7), f"add 0x{W_B7:x},r7            ; bit7 = (gp-0x{DAMP_DISP:04x} != 0)  "
                          "POSITIVE CONTROL")
    label_shr = CAVE_BASE + len(body)
    emit(FF.shr(MAG_SHIFT, R6),
         f"shr 0x{MAG_SHIFT:x},r6            ; q = |x| >> {MAG_SHIFT}", writes_r6=True)
    mag_idx = []
    for imm, w, thr in zip(MAG_IMM5, (W_B6, W_B5, W_B4), MAG_THRESHOLDS):
        mag_idx.append(len(listing))
        emit(V55.cmp_imm5(imm, R6), f"cmp 0x{imm:x},r6            ; q >= {imm} <=> |x| >= {thr}")
        emit(FF.bcond(COND_BLT, BLT_SKIP), "blt +4")
        emit(addi5(w, R7), f"add 0x{w:x},r7            ; |x| >= {thr}")
    shl_idx = len(listing)
    emit(V54.shl(HI_SHIFT, R7), f"shl 0x{HI_SHIFT:x},r7            ; the thermometer -> bits 7:4")
    emit(ldhu_gp(BACKDRIVE_DISP, R6),
         f"ld.hu -0x{BACKDRIVE_DISP:04x}[gp],r6 ; ★★ THE BACK-DRIVE GATE (UNSIGNED; hw2 LSB = 1)",
         writes_r6=True)
    cmp1_idx = len(listing)
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    be1_idx = len(listing)
    emit(FF.bcond(COND_BE, BE_SKIP_BD), "be +4")
    bd_idx = len(listing)
    emit(addi5(W_B3_POST, R7),
         f"add 0x{W_B3_POST:x},r7            ; bit3 = (gp-0x{BACKDRIVE_DISP:04x} != 0)  POST-shift")
    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4",
         writes_r6=True)
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6       ; keep live status bits 2:0",
         writes_r6=True)
    emit(V54.or_rr(R7, R6), "or r7,r6             ; THE MERGE  🛑 NOT `or r6,r7`", writes_r6=True)
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]  ; THE ONLY STORE")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6  ; re-exec displaced instruction", writes_r6=True)
    ret_addr = CAVE_BASE + len(body)
    emit(FF.JMP_LP, "jmp [lp]             ; -> 0x55C12")

    # ---- 🛑🛑 FLAG LIVENESS: every branch must read its OWN cmp's flags. --------------------------
    # The first `cmp` feeds TWO branches (be, then bge) -- legal ONLY because a Bcond does not touch
    # the PSW, which is asserted structurally here rather than remembered.
    assert be0_idx == cmp0_idx + 1 and bge_idx == be0_idx + 1, \
        "the `cmp r0,r6` / `be` / `bge` triple is not contiguous -- the `bge` would read STALE flags"
    assert be1_idx == cmp1_idx + 1 and bd_idx == be1_idx + 1, \
        "the back-drive `cmp`/`be` pair is not adjacent"
    for i in mag_idx:
        assert ((struct.unpack("<H", listing[i][1])[0] >> 5) & 0x3F) == 0x13, \
            f"listing[{i}] is not a `cmp imm5`"
        assert (struct.unpack("<H", listing[i + 1][1])[0] >> 7) & 0xF == 0xB, \
            f"listing[{i + 1}] is not a Bcond -- the compare would fall through unconditionally"
        assert struct.unpack("<H", listing[i + 1][1])[0] & 0xF == COND_BLT, \
            "a magnitude branch is not `blt` -- `bge` would INVERT the rung"
        assert listing[i][0] + 2 == listing[i + 1][0], "a cmp/blt pair is not adjacent"
    assert struct.unpack("<H", listing[be0_idx][1])[0] & 0xF == COND_BE and \
        struct.unpack("<H", listing[be1_idx][1])[0] & 0xF == COND_BE, \
        "a zero-test branch is not `be` -- `bne` would read the cell as live exactly when it is dead"
    assert struct.unpack("<H", listing[bge_idx][1])[0] & 0xF == COND_BGE, \
        "the sign branch is not `bge` -- `blt` would negate the POSITIVE values instead"

    # ---- GATE 2a: EVERY branch lands EXACTLY on an emitted instruction boundary -------------------
    bounds = {a for a, _r, _t in listing}
    branches = [(i, a, r) for i, (a, r, _t) in enumerate(listing)
                if len(r) == 2 and (struct.unpack("<H", r)[0] >> 7) & 0xF == 0xB]
    # be +8 · bge +4 · blt +4 x3 · be +4
    assert len(branches) == 6, f"the cave has {len(branches)} Bcond(s), expected exactly 6"
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
        assert tgt > listing[i + 1][0], \
            f"branch @0x{a:05X} targets the instruction immediately after it -- it skips NOTHING " \
            "and the rung it guards is dead"
    # the two named skips, checked against the LISTING rather than against arithmetic
    assert listing[be0_idx][0] + BE_SKIP_ZERO == label_shr, \
        f"`be +{BE_SKIP_ZERO}` does not land on the `shr` -- +4 would land on the `subr`, which " \
        "would negate a ZERO and then set bit7 on a dead damper"
    assert listing[bge_idx][0] + BGE_SKIP_NEG == listing[bge_idx + 2][0], \
        "`bge +4` does not skip exactly the 2-byte `subr`"

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
    # 🛑 THE TWO `add 0x8,r7` ARE THE SAME BYTES AND MEAN DIFFERENT BITS. Their position relative to
    # `shl 0x4,r7` is the ONLY thing that distinguishes bit7 from bit3; assert it explicitly.
    add8 = [i for i, (_a, r, _t) in enumerate(listing) if r == addi5(W_B7, R7)]
    assert len(add8) == 2 and add8[0] < shl_idx < add8[1], \
        f"the two `add 0x8,r7` are at {add8} around the `shl` at {shl_idx} -- swapping them " \
        "silently relabels bit7 as bit3 and vice versa"
    assert listing[shl_idx][1] == V54.shl(HI_SHIFT, R7), "listing[shl_idx] is not the `shl 0x4,r7`"
    assert [i for i, (_a, r, _t) in enumerate(listing) if r == V54.or_rr(R6, R7)] == [], \
        "the cave contains the ACCUMULATE `or r6,r7` -- V75 has only the MERGE `or r7,r6`"
    ret_idx = [i for i, (_a, r, _t) in enumerate(listing) if r == FF.JMP_LP]
    assert ret_idx == [len(listing) - 1] == [27], f"`jmp [lp]` is at {ret_idx}, expected index 27"
    assert listing[-2][1] == HOOK_STOCK, "the displaced movea must precede the return"
    assert body.count(HOOK_STOCK) == 1, "the displaced movea appears more than once"
    code_len = len(body)
    assert code_len == CAVE_EXTENT == 68, \
        f"the cave is {code_len}B != the PROVEN {CAVE_EXTENT}B extent -- caves brick ECUs"
    assert len(listing) == 28, f"{len(listing)} instructions, expected 28"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    return bytes(body), listing


def redisassemble_cave(raw, base=CAVE_BASE):
    """Decode the cave STRAIGHT OUT OF THE BUILT IMAGE, in Python, from raw bytes.

    🛑 A stale Ghidra import defeats hash-checking, so victory is never declared off a cached
    database. Extended from V74's decoder with `subr` (0x0C). Kept self-contained ON PURPOSE: this
    is the readback's independent witness, so it must not inherit the builder's assumptions.
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
        elif op6 == 0x0D:
            n, m = 2, f"sub r{reg1},r{reg2}"
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

# ★ THE CAVE'S OWN ACCESS COUNTS, stated per cell for BOTH images. The V74 base's cave ALREADY reads
# gp-0x6bd0 (its bit7 is the same test) and gp-0x67fa (its wasted state field); V75's reads gp-0x6bd0
# and gp-0x6ac2 and must NOT read gp-0x67fa. Making this a count rather than a boolean is what turns
# the check into a BUILD-IDENTITY test on both ends: it fails if the input is not a V74 cave, and it
# fails if the output is still one.
CAVE_ACCESS_ON_BASE = {DAMP_DISP: 1, BACKDRIVE_DISP: 0, STATE_DISP: 1}
CAVE_ACCESS_ON_OUTPUT = {DAMP_DISP: 1, BACKDRIVE_DISP: 1, STATE_DISP: 0}


def assert_probe_censuses(buf, cave_span, expect):
    """GATE 1 (RAM ownership) for BOTH probed cells, as a MEASUREMENT from raw bytes.

    🛑 The cave must READ each cell and write NEITHER. `gp-0x6bd0` is the damper's own output and
    `gp-0x6ac2` is the ceiling's LERP index; BOTH are lockstep-shadowed (gp-0x4cf2 / gp-0x4cc6) and a
    stray write to either half escalates through FUN_0006b9fa.

    `expect` maps each displacement to the number of accesses the CAVE should make, so the same
    function gates the input (a V74 cave) and the output (a V75 one).
    """
    out = {}
    for disp, (n_read, n_write, rmn, wmn), writers in (
            (DAMP_DISP, DAMP_CENSUS, DAMP_WRITERS),
            (BACKDRIVE_DISP, BACKDRIVE_CENSUS, BACKDRIVE_WRITERS)):
        reads, writes, cave = V74.cell_census(buf, disp, cave_span)
        assert all(m in rmn for _a, m, _r in reads), \
            f"gp-0x{disp:04x}: unexpected read WIDTH/SIGN -- {sorted({m for _a, m, _r in reads})}"
        assert all(m in wmn for _a, m, _r in writes), f"gp-0x{disp:04x}: unexpected write WIDTH"
        assert len(reads) == n_read, \
            f"gp-0x{disp:04x} has {len(reads)} firmware readers, expected {n_read}"
        assert len(writes) == n_write, \
            f"gp-0x{disp:04x} has {len(writes)} firmware writers, expected {n_write}"
        assert [a for a, _m, _r in writes] == writers, \
            f"gp-0x{disp:04x} writers moved: {[hex(a) for a, _m, _r in writes]}"
        assert len(cave) == expect[disp], \
            f"gp-0x{disp:04x}: the cave makes {len(cave)} access(es) " \
            f"{[(hex(a), m, r) for a, m, r in cave]}, expected {expect[disp]}"
        assert all(m.startswith("ld.") and r == R6 for _a, m, r in cave), \
            f"gp-0x{disp:04x}: a cave access is not a load into r{R6} -- a STORE here would CORRUPT " \
            "the cell, and both cells are lockstep-checked"
        out[disp] = (len(reads), len(writes))
    # 🛑 ALL THREE lockstep shadows must be untouched by the cave, on BOTH images.
    for disp, whose in SHADOW_DISPS.items():
        _r, _w, scave = V74.cell_census(buf, disp, cave_span)
        assert not scave, f"the cave touches {whose} lockstep shadow gp-0x{disp:04x}"
    # ⊕ V74's state cell: the BASE's cave reads it, V75's must NOT. Both directions are asserted.
    _r, _w, stale = V74.cell_census(buf, STATE_DISP, cave_span)
    assert len(stale) == expect[STATE_DISP], \
        f"🛑 the cave makes {len(stale)} access(es) to V74's state cell gp-0x{STATE_DISP:04x}, " \
        f"expected {expect[STATE_DISP]} -- on the INPUT that means the base is not a V74 cave; on " \
        "the OUTPUT it means the V74 cave survived and its four wasted bits are still there"
    return out


# =====================================================================================================
# EDIT 1 + EDIT 2 -- the dose crank, derived
# =====================================================================================================

def _surface_axes(buf, mode, speeds, rates, c_y0=None):
    """(C over `speeds`, E over `rates`) for `mode`, C_Y[0] optionally overridden for the cap search.

    ⊕ There is deliberately NO `e_x1` override: LEVER EX1 is APPLIED TO THE IMAGE before LEVER CY0
    derives, so the E axis read here is already the one that will ship. An override would let the
    cap be searched against an E axis that never gets built.
    """
    _n, cx, cy = rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))
    _n, ex, ey = rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))
    if c_y0 is not None:
        cy = [c_y0] + cy[1:]
    return ([LM.lerp_int(v, cx, cy) for v in speeds], [LM.lerp_int(r, ex, ey) for r in rates])


def _grid_axes(n_speed=14001, n_rate=4501, dv=32, dr=20):
    return list(range(0, n_speed, dv)), list(range(0, n_rate, dr))


def _raised_max_bound(cs, es, base_c, base_e):
    """An O(n) UPPER BOUND on the surface over the raised set. Sound in the SAFE direction only.

    The raised set is contained in `(A x all_E) U (all_C x B)` where A / B are the speed / rate
    indices at which C / E actually rose. Since `(c*e)>>10` is monotone non-decreasing in both
    non-negative arguments, the maximum over each rectangle is at its own corner. The containment
    is one-way -- a point where C rose but the product truncates back to the same value is inside
    the bound's set and outside the true raised set -- so `bound <= floor` PROVES no clip, while
    `bound > floor` proves nothing and falls through to the exact scan.
    """
    best = 0
    a = [c for c, cb in zip(cs, base_c) if c > cb]
    b = [e for e, eb in zip(es, base_e) if e > eb]
    if a:
        best = max(best, (max(a) * max(es)) >> 10)
    if b:
        best = max(best, (max(cs) * max(b)) >> 10)
    return best


def _no_clip_ok(buf, mode, speeds, rates, floor, c_y0, base_c, base_e):
    """(passes, peak) for a candidate `c_y0` over the whole grid, on `buf` AS IT STANDS.

    🛑 `buf` must ALREADY carry whatever LEVER EX1 is going to write, because the two levers are
    multiplicative and the admissible `C_Y0` depends on the E axis it will actually meet. Deriving
    the cap against a lever set other than the one being built is exactly the "hand-picked corner"
    error the kit has already made twice on this table family.

    The rule, unchanged from V74: **every point the edit RAISES must stay at or below that mode's
    OWN ceiling floor.** Points that were already above it and did NOT move are legal -- that is
    stock behaviour and V75 is not entitled to change it either way.
    ⊕ `dose = (C * E) >> 10` exactly, because FactorB and FactorD are FLAT 1024 (asserted by the
    caller, BY COUNT). The scalar mirror `damper_authority()` is cross-checked against this on a
    sample in `assert_no_clip`, so the fast path can never drift from the decompiled arithmetic.
    ⊕ The O(n) bound is tried first; the EXACT O(n^2) scan runs only when the bound cannot settle
    it, which during the binary search is a handful of candidates near the boundary. The verdict is
    identical either way -- the bound is an optimisation, never a relaxation.
    """
    cs, es = _surface_axes(buf, mode, speeds, rates, c_y0=c_y0)
    peak = (max(cs) * max(es)) >> 10        # exact: the product is monotone in both, both >= 0
    if _raised_max_bound(cs, es, base_c, base_e) <= floor:
        return True, peak
    for ci, cb in zip(cs, base_c):
        for ei, eb in zip(es, base_e):
            now = (ci * ei) >> 10
            if now > ((cb * eb) >> 10) and now > floor:
                return False, None
    return True, peak


def _assert_mode_shape(buf, mode, seen):
    """The record geometry every lever depends on. Run once per mode, before any lever derives."""
    cb = factor_rec(buf, FACTOR_C_PTRS, mode)
    eb = factor_rec(buf, FACTOR_E_PTRS, mode)
    for base, name in ((cb, "FactorC"), (eb, "FactorE")):
        assert seen.get(base, mode) == mode, \
            f"mode {mode}'s {name} @0x{base:05X} is ALSO mode {seen[base]}'s -- two modes alias " \
            "onto one record and the second edit would read a mutated 'old' value"
        seen[base] = mode
        n, xs, ys = rec_any(buf, base)
        assert n == 4, \
            f"🛑 {name} mode {mode} @0x{base:05X} declares count {n}, not 4. STOP: do not guess."
        assert all(b > a for a, b in zip(xs, xs[1:])), \
            f"{name} mode {mode} X = {xs} is not strictly increasing"
        assert all(0 <= y < 0x8000 for y in ys), f"{name} mode {mode}: a Y is not a positive short"
    # FactorB / FactorD must be FLAT 1024 -- otherwise `(C*E)>>10` is not the whole chain.
    for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD")):
        n, _xs, ys = rec_any(buf, factor_rec(buf, ptrs, mode))
        assert set(ys) == {Q10}, f"{name} m{mode} ({n}-point) is not FLAT {Q10}: {ys}"
    return cb, eb


# =====================================================================================================
# LEVER EX1 -- FactorE X[1] := 200.  INDEPENDENT of LEVER CY0.
# =====================================================================================================

def derive_lever_ex1(buf, modes, verbose=True):
    """Move FactorE's low-rate breakpoint LEFT. Returns {cell: (old, new, label, mode, "EX1")}.

    ★ WHY THIS IS FREE, structurally: `X[1]` moves a BREAKPOINT, it does not raise a VALUE. E rises
    only on the open interval `(X[0], X[1]_old)` and is bit-identical everywhere else, so the
    plateau `Y[1] = Y[2]` and the maximum `Y[3]` -- the two things the no-clip rule binds on -- are
    untouched. That is why this lever exists at all: a recorded full-grid search found FactorE's *Y*
    axis has ZERO remaining headroom, and it is still right. This lever never touches Y.
    🛑 ADD-ONLY: `new = min(old, TARGET)`, so X[1] can only move LEFT. Moving it right would LOWER E.
    """
    edits, seen = {}, {}
    for mode in modes:
        _cb, eb = _assert_mode_shape(buf, mode, seen)
        _n, ex, ey = rec_any(buf, eb)
        assert ex[0] == E_X0_CARRIED, \
            f"🛑 FactorE m{mode} X[0] is {ex[0]}, not V74's {E_X0_CARRIED} -- the base is not V74"
        x1_new = min(ex[1], TARGET_E_X1) if LEVERS["EX1"] else ex[1]
        assert ex[0] < x1_new < ex[2], \
            f"m{mode}: the new X[1] {x1_new} does not sit strictly between X[0] {ex[0]} and " \
            f"X[2] {ex[2]} -- the axis would stop being strictly increasing"
        assert x1_new <= ex[1], f"🛑 m{mode}: X[1] {ex[1]} -> {x1_new} moves RIGHT -- a SUBTRACTION"
        assert ey[1] >= ey[0], \
            f"m{mode}: FactorE Y[1] {ey[1]} < Y[0] {ey[0]} -- moving X[1] left would LOWER E, " \
            "which would make this lever a subtraction rather than an addition"
        edits[eb + REC4_X_OFF + 2] = (ex[1], x1_new, f"FactorE mode {mode:2d} X[1]", mode, "EX1")
        if verbose:
            print(f"      m{mode:2d}  E_X {ex} -> {[ex[0], x1_new] + ex[2:]}"
                  f"{'   (lever OFF -- no-op)' if not LEVERS['EX1'] else ''}")
    assert len(edits) == len(modes) == 13, f"{len(edits)} EX1 cells, expected 13"
    return edits


# =====================================================================================================
# LEVER CY0 -- FactorC Y[0] := 566, capped PER MODE.  INDEPENDENT of LEVER EX1 as a TOGGLE,
# but its CAP is derived against whatever EX1 has already written -- see the docstring.
# =====================================================================================================

def derive_lever_cy0(buf, base_img, modes, verbose=True):
    """Raise FactorC's creep end. Returns ({cell: (old, new, label, mode, "CY0")}, report).

    🛑 `buf` MUST ALREADY CARRY LEVER EX1'S BYTES and `base_img` must be the untouched V74. The two
    levers multiply, so the admissible `C_Y0` is a function of the E axis it will actually meet;
    deriving it against a different lever set is the exact "hand-picked corner" error this table
    family has already produced twice. The dependency is one-way -- CY0's cap depends on EX1, EX1
    depends on nothing -- which is why EX1 is derived and applied FIRST.
    🛑 THE CAP IS BINARY-SEARCHED against that mode's OWN `C_Y3`, `E_Y3` and `ceiling_floor()` over
    the 98,988-point grid. Nothing is hand-copied from mode 26.
    🛑 ADD-ONLY: `new = max(old, min(TARGET, cap))`, so a mode whose base value already EXCEEDS the
    target is HELD, never lowered. Modes 2/3 hit that branch (1356 > 566) and are reported.
    """
    speeds, rates = _grid_axes()
    edits, report, seen = {}, {}, {}
    for mode in modes:
        cb, _eb = _assert_mode_shape(buf, mode, seen)
        _n, _cx, cy = rec_any(buf, cb)
        floor = ceiling_floor(buf, mode)
        base_c, base_e = _surface_axes(base_img, mode, speeds, rates)
        # the state `buf` is already in must itself be admissible, or the premise is wrong
        ok0, _pk = _no_clip_ok(buf, mode, speeds, rates, floor, cy[0], base_c, base_e)
        assert ok0, \
            f"🛑 m{mode}: the image ALREADY raises the surface above the floor {floor} before " \
            "LEVER CY0 is applied. STOP -- LEVER EX1 is not free on this mode."
        if LEVERS["CY0"]:
            lo, hi = cy[0], CAP_SEARCH_HI
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if _no_clip_ok(buf, mode, speeds, rates, floor, mid, base_c, base_e)[0]:
                    lo = mid
                else:
                    hi = mid - 1
            cap = lo
            assert cap >= cy[0], f"m{mode}: the search returned a cap below the base value"
            c_new = max(cy[0], min(TARGET_C_Y0, cap))
        else:
            cap, c_new = cy[0], cy[0]
        held = LEVERS["CY0"] and c_new == cy[0] and cy[0] > TARGET_C_Y0
        capped = LEVERS["CY0"] and cap < TARGET_C_Y0
        ok, peak = _no_clip_ok(buf, mode, speeds, rates, floor, c_new, base_c, base_e)
        assert ok, f"m{mode}: the chosen C_Y0 {c_new} fails the no-clip rule after all"
        assert c_new >= cy[0], f"🛑 m{mode}: C_Y0 {cy[0]} -> {c_new} is a SUBTRACTION"
        edits[cb + REC4_Y_OFF] = (cy[0], c_new, f"FactorC mode {mode:2d} Y[0]", mode, "CY0")
        report[mode] = (cap, peak, held, capped, floor)
        if verbose:
            note = ("   ⚠ HELD at the base (add-only: base > target)" if held else
                    f"   ⚠ CAPPED to {cap} by no-clip" if capped else
                    "   (lever OFF -- no-op)" if not LEVERS["CY0"] else "")
            print(f"      m{mode:2d}  C_Y {cy} -> {[c_new] + cy[1:]}   cap {cap:5d} "
                  f"floor {floor}{note}")
    assert len(edits) == len(modes) == 13, f"{len(edits)} CY0 cells, expected 13"
    if LEVERS["CY0"]:
        assert set(m for m, r in report.items() if r[2]) == set(HELD_AT_BASE), \
            f"the HELD set is {sorted(m for m, r in report.items() if r[2])}, the spec says " \
            f"{list(HELD_AT_BASE)} -- an undeclared mode is being held, or a declared one is not"
    return edits, report


def assert_no_clip(buf, base_img, modes, label):
    """★ THE SURFACE RULE, re-run on the FINISHED image against the V74 base.

    Two independent statements, both required:
      1. no swept point is both RAISED and above that mode's own ceiling floor;
      2. the GLOBAL PEAK is byte-identical to V74's -- the structural claim that `C_Y0` and `E_X1`
         cannot move the maximum, re-derived rather than argued.
    ⊕ The fast (C x E) path is cross-checked against `damper_authority()` -- the exact mirror of
    FUN_00034350's Q10 chain -- on a deterministic sample, so it cannot drift from the decompilation.
    """
    speeds, rates = _grid_axes()
    report = {}
    for mode in modes:
        fl = ceiling_floor(buf, mode)
        cs, es = _surface_axes(buf, mode, speeds, rates)
        cb_, eb_ = _surface_axes(base_img, mode, speeds, rates)
        bad, raised, aff, peak, peak_b = [], 0, 0, 0, 0
        for si, (ci, cbv) in enumerate(zip(cs, cb_)):
            for ri, (ei, ebv) in enumerate(zip(es, eb_)):
                now, was = (ci * ei) >> 10, (cbv * ebv) >> 10
                if now > peak:
                    peak = now
                if was > peak_b:
                    peak_b = was
                if now > was:
                    raised += 1
                    aff = max(aff, now)
                    if now > fl:
                        bad.append((speeds[si], rates[ri], was, now))
        assert not bad, \
            f"🛑 {label}: mode {mode} RAISES the surface above its own ceiling floor {fl} at " \
            f"{len(bad)} point(s), e.g. {bad[:3]} ⇒ the damper would SATURATE there. That puts a " \
            "hard-clipping element inside a feedback loop and CREATES limit cycles."
        assert peak == peak_b, \
            f"🛑 {label}: mode {mode}'s GLOBAL peak moved {peak_b} -> {peak}. `C_Y0` raises only the " \
            "creep end and `E_X1` moves a breakpoint, so neither may touch the maximum."
        # 🛑 the fast path must equal the EXACT decompiled mirror.
        for v, r in ((0, BURST_RATE), (0, BURST_RATE_69HZ), (speeds[-1], rates[-1]),
                     (speeds[len(speeds) // 3], rates[len(rates) // 3]), (0, 0)):
            fast = (LM.lerp_int(v, *rec_any(buf, factor_rec(buf, FACTOR_C_PTRS, mode))[1:])
                    * LM.lerp_int(r, *rec_any(buf, factor_rec(buf, FACTOR_E_PTRS, mode))[1:])) >> 10
            assert fast == damper_authority(buf, mode, v, r), \
                f"{label}: m{mode} the (C*E)>>10 fast path disagrees with FUN_00034350's mirror at " \
                f"(speed {v}, rate {r}) -- FactorB/D are not flat and the sweep is INVALID"
        report[mode] = (fl, raised, aff, peak)
    return report, len(speeds) * len(rates)


def assert_v75_shape(buf, label, base_img, modes, lever_f):
    """The post-edit shape: only the two intended cells moved, in the intended direction."""
    for mode in modes:
        cb, eb = factor_rec(buf, FACTOR_C_PTRS, mode), factor_rec(buf, FACTOR_E_PTRS, mode)
        n_c, cx, cy = rec_any(buf, cb)
        n_e, ex, ey = rec_any(buf, eb)
        bn_c, bcx, bcy = rec_any(base_img, cb)
        bn_e, bex, bey = rec_any(base_img, eb)
        assert (n_c, n_e) == (bn_c, bn_e) == (4, 4), f"{label}: a record's point count moved"
        # ---- FactorC: ONLY Y[0], and only UPWARD -------------------------------------------------
        assert cx == bcx, f"{label}: FactorC m{mode}: the X axis moved"
        assert cy[1:] == bcy[1:], f"{label}: FactorC m{mode}: only Y[0] may move, got {cy}"
        assert cy[0] >= bcy[0], f"{label}: FactorC m{mode} Y[0] {bcy[0]} -> {cy[0]} is a SUBTRACTION"
        # ---- FactorE: ONLY X[1], and only LEFTWARD. 🛑 THE Y ROW IS FROZEN. -----------------------
        assert ey == bey, \
            f"🛑 {label}: FactorE m{mode} Y moved {bey} -> {ey}. FactorE's Y axis has ZERO verified " \
            "headroom -- Y[3] is what sets the surface maximum. It is FROZEN in this build."
        assert ex[0] == bex[0] == E_X0_CARRIED and ex[2:] == bex[2:], \
            f"{label}: FactorE m{mode}: only X[1] may move, got {ex}"
        assert ex[1] <= bex[1], f"{label}: FactorE m{mode} X[1] {bex[1]} -> {ex[1]} is a SUBTRACTION"
        assert all(b > a for a, b in zip(ex, ex[1:])), \
            f"{label}: FactorE m{mode} X = {ex} is not strictly increasing"
        assert all(b >= a for a, b in zip(ey, ey[1:])), \
            f"🛑 {label}: FactorE m{mode} Y = {ey} is NOT monotone non-decreasing"
        # ---- everything else about the mode is byte-frozen ----------------------------------------
        for ptrs, name in ((FACTOR_B_PTRS, "FactorB"), (FACTOR_D_PTRS, "FactorD"),
                           (CEILING_PTRS, "ceiling"), (FRICTION_PTR_ARRAY, "friction")):
            base = factor_rec(buf, ptrs, mode)
            ln = rec_len(buf, base)
            assert bytes(buf[base:base + ln]) == bytes(base_img[base:base + ln]), \
                f"🛑 {label}: {name} m{mode} @0x{base:05X} MOVED -- it is not this build's lever " \
                "(the ceiling table especially: 0xC77A0 is explicitly NOT V75's lever)"
    for addr, (_old, new, lbl, _m, _f) in lever_f.items():
        assert u16(buf, addr) == new, f"{label}: {lbl} @0x{addr:05X} is {u16(buf, addr)}, want {new}"
    for base, want in GAIN_B_M10_KEEP.items():
        got = rec4_y(buf, base)
        assert got == want and \
            bytes(buf[base:base + REC_STRIDE]) == bytes(base_img[base:base + REC_STRIDE]), \
            f"{label}: gain_B mode-10 0x{base:05X} Y is {got}, expected V74's {want} byte-for-byte"


def assert_decoder_matches(cave_bytes):
    """🛑 The decoder's CAVE_HEX must equal the cave just emitted, so it cannot drift."""
    if not os.path.exists(DECODER):
        print(f"    ⚠ {DECODER} not found -- the decoder/image link is NOT verified")
        return False
    txt = open(DECODER, encoding="utf-8").read()
    m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
    assert m, "V75: the decoder carries no CAVE_HEX -- it cannot be checked against the image"
    assert m.group(1) == cave_bytes.hex(), \
        f"V75: the decoder's CAVE_HEX is STALE.\n  decoder: {m.group(1)}\n  image:   {cave_bytes.hex()}"
    # 🛑 THE DECODER MUST NAME THE EXACT .rwd OF *THIS* LEVER SET. The cave is byte-identical across
    # every V75 cut, so the payload cannot distinguish them -- the filename is the only pre-drive
    # discriminator, and a decoder naming a sibling's .rwd would send the operator to the wrong file.
    # A re-cut with a lever toggled MUST update `RWD_NAME` in the decoder; that is deliberate.
    assert os.path.basename(out_rwd()) in txt, \
        f"V75: the decoder's RWD_NAME does not match THIS lever set. Set it to:\n" \
        f"      {os.path.basename(out_rwd())}\n" \
        "      (the cave is identical across lever sets, so the FILENAME is the only discriminator)"
    for token in ("V75", "0x6BD0", "0x6AC2"):
        assert token in txt, f"V75: the decoder does not carry '{token}'"
    for name, val in (("BIT_DAMP_NZ", BIT_DAMP_NZ), ("BIT_MAG128", BIT_MAG128),
                      ("BIT_MAG288", BIT_MAG288), ("BIT_MAG448", BIT_MAG448),
                      ("BIT_BACKDRIVE", BIT_BACKDRIVE), ("PROBE_MASK", PROBE_MASK)):
        mm = re.search(rf"^{name}\s*=\s*(0x[0-9a-fA-F]+|\d+)\b", txt, re.M)
        assert mm and int(mm.group(1), 0) == val, \
            f"V75: the decoder's {name} is {mm and mm.group(1)}, not 0x{val:02X}"
    mm = re.search(r"^LEGAL_PAYLOADS\s*=\s*\(([^)]*)\)", txt, re.M)
    assert mm and [int(x, 0) for x in mm.group(1).replace(",", " ").split()] == LEGAL_PAYLOADS, \
        "V75: the decoder's LEGAL_PAYLOADS does not match the 10 reachable thermometer payloads"
    mm = re.search(r"^MAG_THRESHOLDS\s*=\s*\(([^)]*)\)", txt, re.M)
    assert mm and tuple(int(x, 0) for x in mm.group(1).replace(",", " ").split()) == MAG_THRESHOLDS, \
        "V75: the decoder's MAG_THRESHOLDS differ from the emitted ones"
    for claim in ("THERMOMETER", "POSITIVE CONTROL", "BACK-DRIVE"):
        assert claim in txt.upper(), f"V75: the decoder never states '{claim}'"
    for stale in ("0x67FA", "0x69A4", "0x6AC0", "0x63FD"):
        assert not re.search(rf"^BIT_\w+\s*=.*{stale}", txt, re.M | re.I), \
            f"V75: {stale} is still a LIVE RUNG in the decoder"
    return True


def build():
    print(__doc__)

    # ---- 🛑 A SAME-NUMBER RE-CUT ONCE DESTROYED ITS PREDECESSOR'S PLAIN IMAGE. Never overwrite. ----
    BIN_OUT, OUT = bin_out(), out_rwd()
    existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
    if existing is not None:
        print(f"  ⚠ {BIN_OUT} already exists ({hashlib.sha256(existing).hexdigest()[:16]}...). "
              "It will be COMPARED, not blindly overwritten.")
    assert len(OUT) < 250, \
        f"the .rwd path is {len(OUT)} chars -- Windows' 260 limit would truncate it. Shorten the " \
        "tag BEFORE building; nothing has been written yet."
    assert lever_token() in os.path.basename(BIN_OUT) and lever_token() in os.path.basename(OUT), \
        "🛑 the lever set is not in BOTH filenames -- a re-cut would be indistinguishable from its " \
        "sibling, and the cave is byte-identical across lever sets so the payload cannot tell them " \
        "apart either"
    assert any(LEVERS.values()), \
        "🛑 BOTH LEVERS ARE OFF. That build is byte-identical to V74 outside the cave; it is a " \
        "probe-only re-cut, not V75. Set at least one lever or build it deliberately under another " \
        "number."

    v74 = bytearray(Path(SRC_BIN).read_bytes())
    stock = Path(STOCK_BIN).read_bytes()
    print("=" * 102)
    print(f"SOURCE (V74): {SRC_BIN}\n  SHA256 {hashlib.sha256(bytes(v74)).hexdigest()}")
    print(f"STOCK:        {STOCK_BIN}")
    for name, img in (("V74", v74), ("stock", stock)):
        assert len(img) == 0x100000, f"the {name} image is not 1 MiB"
    assert hashlib.sha256(bytes(v74)).hexdigest() == SRC_SHA256, \
        f"🛑 THE BASE IS NOT V74. SHA256 is {hashlib.sha256(bytes(v74)).hexdigest()}, expected " \
        f"{SRC_SHA256}. V75 is defined as V74 + these edits; any other base voids every claim."
    print("  ✅ the base SHA256 matches the recorded V74 image exactly.")

    # ---- gate the SOURCE ---------------------------------------------------------------------------
    cave_span = range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)
    V74.assert_must_not_change(v74, "V74 source", stock, None)
    assert walk_all_blocks(bytes(v74)) == 0, "the V74 source's own CRC chain does not verify"
    assert_probe_censuses(bytes(v74), cave_span, CAVE_ACCESS_ON_BASE)
    print("  ✅ every MUST-NOT-CHANGE site, the six pointer arrays over all 34 modes, the config")
    print("     table, V72's LEVER C, the carried 0x454FE, the UNGATED gate byte, V57's decoupling,")
    print("     V53's eleven STOCK_CALS and the full CRC chain: all verified ON THE INPUT.")

    # ---- THE MODE COLUMNS --------------------------------------------------------------------------
    rows, ENGAGED, DISENGAGED = V74.derive_mode_columns(bytes(v74))
    assert tuple(ENGAGED) == ENGAGED_EXPECTED and tuple(DISENGAGED) == DISENGAGED_EXPECTED, \
        "V75's own independent statement of the mode columns disagrees with the derivation"
    assert not (set(ENGAGED) & set(DISENGAGED)), \
        "🛑 THE COLUMNS ARE NOT DISJOINT -- the whole safety argument collapses"
    print(f"\n  🛑 THE CONFIG TABLE 0x{VARIANT_KEY_TABLE:05X} -- DERIVED on the image being built:")
    print(f"     ENGAGED    (e014,e015) = {list(ENGAGED)}   <- V75 writes these 13")
    print(f"     DISENGAGED (e012,e013) = {list(DISENGAGED)}   <- byte-stock")
    print(f"     ★★ row {THIS_CAR_ROW} {THIS_CAR_KEY!r}: manual {THIS_CAR_MODES[0]}, ENGAGED "
          f"{LIVE_MODE} (V73's on-car probe, not an inference)")

    code = bytearray(v74)

    # ---- LEVER EX1, then LEVER CY0 -- derived and applied SEPARATELY, in dependency order ---------
    print(f"\n  THE LEVER SET: {lever_token()}   "
          f"(CY0 {'ON' if LEVERS['CY0'] else 'OFF'} · EX1 {'ON' if LEVERS['EX1'] else 'OFF'})")
    print("    🛑 Every address is DEREFERENCED from the pointer arrays on the image being built.")
    print(f"\n  LEVER EX1 -- FactorE X[1] := {TARGET_E_X1} on the {len(ENGAGED)} engaged modes "
          "(moves a BREAKPOINT; touches no Y):")
    lever_ex1 = derive_lever_ex1(code, ENGAGED)
    for addr, (old, new, lbl, _m, _f) in sorted(lever_ex1.items()):
        assert u16(code, addr) == old, f"{lbl} @0x{addr:05X} is {u16(code, addr)}, expected {old}"
        struct.pack_into("<H", code, addr, new)
    print(f"\n  LEVER CY0 -- FactorC Y[0] := {TARGET_C_Y0}, cap BINARY-SEARCHED per mode against "
          "that mode's own C_Y3 / E_Y3 / floor,")
    print("    🛑 and against the E axis LEVER EX1 has ALREADY written -- the two levers multiply:")
    lever_cy0, cap_report = derive_lever_cy0(code, v74, ENGAGED)
    lever_f = {**lever_ex1, **lever_cy0}
    # ⊕ the LIVE mode's geometry, against the independently stated expectation
    assert factor_rec(code, FACTOR_C_PTRS, LIVE_MODE) == LIVE_EXPECT["factor_c"], "live FactorC moved"
    assert factor_rec(code, FACTOR_E_PTRS, LIVE_MODE) == LIVE_EXPECT["factor_e"], "live FactorE moved"
    for key, addr in (("factor_c_y0", LIVE_EXPECT["factor_c"] + REC4_Y_OFF),
                      ("factor_e_x1", LIVE_EXPECT["factor_e"] + REC4_X_OFF + 2)):
        assert addr == LIVE_EXPECT[key], \
            f"the LIVE mode's {key} derives to 0x{addr:05X}, the spec says 0x{LIVE_EXPECT[key]:05X}"
    print(f"    ✅ THE LIVE MODE {LIVE_MODE} derives to exactly the specified cells: "
          f"C_Y[0] @0x{LIVE_EXPECT['factor_c_y0']:05X}, E_X[1] @0x{LIVE_EXPECT['factor_e_x1']:05X}")

    for addr, (old, new, lbl, _m, _f) in sorted(lever_cy0.items()):
        assert u16(code, addr) == old, f"{lbl} @0x{addr:05X} is {u16(code, addr)}, expected {old}"
        struct.pack_into("<H", code, addr, new)
    print(f"\n    THE {len(lever_f)} DERIVED CELLS ({len(lever_cy0)} CY0 + {len(lever_ex1)} EX1):")
    for addr, (old, new, lbl, mode, fam) in sorted(lever_f.items()):
        why = ("" if old != new else
               "   ⚠ NO-OP (lever OFF)" if not LEVERS[fam] else
               "   ⚠ NO-OP (HELD; see below)")
        print(f"      0x{addr:05X}  [{fam}] {old:5d} -> {new:5d}   {lbl}{why}")
    # 🛑 the LIVE-mode expectations are stated for the FULL lever set only; a re-cut with a lever
    # off must print its own numbers rather than fail against a spec written for a different build.
    full_set = LEVERS["CY0"] and LEVERS["EX1"]
    want_c = LIVE_EXPECT["factor_c_y0_new"] if LEVERS["CY0"] else LIVE_EXPECT["factor_c_y0_old"]
    want_x = LIVE_EXPECT["factor_e_x1_new"] if LEVERS["EX1"] else LIVE_EXPECT["factor_e_x1_old"]
    assert u16(code, LIVE_EXPECT["factor_c_y0"]) == want_c, \
        f"live C_Y0 is {u16(code, LIVE_EXPECT['factor_c_y0'])}, expected {want_c} for this lever set"
    assert u16(code, LIVE_EXPECT["factor_e_x1"]) == want_x, \
        f"live E_X1 is {u16(code, LIVE_EXPECT['factor_e_x1'])}, expected {want_x} for this lever set"
    if LEVERS["CY0"]:
        print(f"\n    ⚠ THE DELIBERATE DEVIATION -- modes {list(HELD_AT_BASE)} are HELD, not written "
              f"to {TARGET_C_Y0}:")
        for mode in HELD_AT_BASE:
            cy0 = rec_any(v74, factor_rec(v74, FACTOR_C_PTRS, mode))[2][0]
            cap = cap_report[mode][0]
            print(f"      mode {mode:2d}: V74 already carries C_Y[0] = {cy0} (V74 set it to that "
                  f"record's own Y[2]). Writing {TARGET_C_Y0}")
            print(f"               would LOWER it by {cy0 - TARGET_C_Y0} counts -- a SUBTRACTION, "
                  "which 'additions only' forbids. Its own")
            print(f"               no-clip cap is {cap}, so this is the ADD-ONLY rule, not a safety "
                  "cap. TWAA chassis; inert here.")
    else:
        print("\n    ⊕ LEVER CY0 is OFF -- every FactorC Y[0] is byte-identical to V74, and the "
              "HELD-mode question does not arise.")
    capped = [(m, r[0]) for m, r in cap_report.items() if r[3]]
    if capped:
        print(f"\n    ⚠ {len(capped)} MODE(S) NEEDED THE NO-CLIP CAP: "
              f"{[(m, c) for m, c in capped]}")
    else:
        print(f"\n    ✅ NO engaged mode needed a no-clip cap below the target {TARGET_C_Y0}: every")
        print(f"       one binary-searched to a cap >= {TARGET_C_Y0} against its OWN C_Y3, E_Y3 and")
        print("       ceiling floor. (⊕ V74's closed-form cap was conservative by exactly one count:")
        print("       floor(512*1024/927) = 565, while (566*927)>>10 = 512 <= 512 is admissible.)")

    # ---- THE SURFACE ------------------------------------------------------------------------------
    print(f"\n  ✅ DELIVERED DAMPING AUTHORITY (FactorB/D FLAT {Q10} ⇒ the chain reduces to "
          f"(C * E) >> 10, seed {Q10}):")
    surf, npts = assert_no_clip(code, v74, ENGAGED, "V75")
    print(f"    🛑 RECOMPUTED FROM THE BYTES JUST WRITTEN over {npts:,} grid points, not from the "
          "design note.")
    print(f"      {'mode':>4} {'E@r99':>6} {'dose@99':>8} {'V74@99':>7} {'x':>5} {'dose@127':>9} "
          f"{'V74@127':>8} {'dose@9':>7} {'floor':>6} {'raisedMax':>10} {'ptsRaised':>10} "
          f"{'peak':>6}")
    doses = {}
    for mode in ENGAGED:
        fl, raised, aff, peak = surf[mode]
        d_now = damper_authority(code, mode, 0, BURST_RATE)
        d_was = damper_authority(v74, mode, 0, BURST_RATE)
        e_at_99 = LM.lerp_int(BURST_RATE, *rec_any(code, factor_rec(code, FACTOR_E_PTRS, mode))[1:])
        d_69 = damper_authority(code, mode, 0, BURST_RATE_69HZ)
        d_69_was = damper_authority(v74, mode, 0, BURST_RATE_69HZ)
        d_oob = damper_authority(code, mode, 0, OUT_OF_BURST_RATE)
        doses[mode] = d_now
        star = "  ★★ LIVE" if mode == LIVE_MODE else ("  (touches floor)" if aff == fl else "")
        print(f"      {mode:4d} {e_at_99:6d} {d_now:8d} {d_was:7d} {d_now / max(d_was, 1):5.2f} "
              f"{d_69:9d} {d_69_was:8d} {d_oob:7d} {fl:6d} {aff:10d} {raised:10d} {peak:6d}{star}")
    assert damper_authority(v74, LIVE_MODE, 0, BURST_RATE) == LIVE_EXPECT["dose_old"], \
        "the V74 base's own live dose is not the recorded 50 -- the base is wrong"
    ratio = doses[LIVE_MODE] / LIVE_EXPECT["dose_old"]
    if full_set:
        # 🛑 the spec's numbers apply to the FULL lever set. A re-cut asserts its own arithmetic
        # (add-only + no-clip, above) and REPORTS its dose rather than being held to this one.
        assert doses[LIVE_MODE] == LIVE_EXPECT["dose"], \
            f"the LIVE mode's dose at rate {BURST_RATE} is {doses[LIVE_MODE]}, the spec says " \
            f"{LIVE_EXPECT['dose']}"
        assert damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ) == LIVE_EXPECT["dose_69hz"], \
            f"the LIVE mode's dose at rate {BURST_RATE_69HZ} is " \
            f"{damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ)}, spec " \
            f"{LIVE_EXPECT['dose_69hz']}"
        assert abs(ratio - DOSE_RATIO_LIVE) < 0.005, f"the live dose ratio is {ratio:.3f}"
    else:
        print(f"    ⚠ PARTIAL LEVER SET {lever_token()}: the spec's dose numbers "
              f"({LIVE_EXPECT['dose']} @ {BURST_RATE}) describe the FULL set and are NOT asserted.")
        print(f"      This cut delivers {doses[LIVE_MODE]} at rate {BURST_RATE} "
              f"({ratio:.2f}x V74's {LIVE_EXPECT['dose_old']}) and "
              f"{damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ)} at {BURST_RATE_69HZ}.")
        print("      The add-only and no-clip rules above ARE asserted, unchanged.")
    print(f"      ✅ every engaged mode: wherever V75 RAISES the surface it stays at or below that")
    print("         mode's own ceiling FLOOR, and the GLOBAL peak is byte-identical to V74's ⇒ the")
    print("         claim that C_Y0 and E_X1 cannot move the maximum is RE-DERIVED, not argued.")
    print(f"      ★★ THE LIVE MODE {LIVE_MODE}: {LIVE_EXPECT['dose_old']} -> {doses[LIVE_MODE]} "
          f"counts at the measured burst rate {BURST_RATE} = **{ratio:.2f}x**, and "
          f"{damper_authority(v74, LIVE_MODE, 0, BURST_RATE_69HZ)} -> "
          f"{damper_authority(code, LIVE_MODE, 0, BURST_RATE_69HZ)} at the 6-9 Hz rate "
          f"{BURST_RATE_69HZ}.")
    touch = [m for m in ENGAGED if surf[m][2] == surf[m][0]]
    if touch and LEVERS["CY0"]:
        print(f"      ⊕ mode(s) {touch}")
        print(f"        raise the surface exactly TO the floor {CEILING_FLOOR} -- BY CONSTRUCTION, "
              "at the grid corner (speed 0, max rate),")
        print(f"        because {TARGET_C_Y0} is the LARGEST C_Y0 whose (C * E_Y3) >> 10 lands at or "
              "below the floor. That is NOT")
        print("        clipping: the clamp is `if |v| > ceiling`, so a value AT the ceiling passes "
              "through unchanged.")
        print(f"        ⊕ AND THE CEILING IS 512 ON BOTH BRANCHES: the reader @0x346A4 is `ld.hu` "
              "(UNSIGNED, pinned), so the")
        print(f"        0xFFFF sentinel is >= 0x32C9 and takes the tp+0x7158 FALLBACK -- which is "
              "itself 512, byte-identical")
        print("        to the LERP's Y[0]. There is no reachable path to a different ceiling.")
    flat_e = [m for m in ENGAGED
              if len(set(rec_any(code, factor_rec(code, FACTOR_E_PTRS, m))[2])) == 1]
    if flat_e:
        print(f"      ⚠ mode(s) {flat_e} are DIFFERENT and for a separate reason: FactorE is V72's "
              "flat [927]*4,")
        print(f"        so they sit at {CEILING_FLOOR} across the WHOLE rate axis at creep speed, "
              "rate 0 included (see dose@9).")
        print("        That is a pre-existing property of V72's edit to that record, not something "
              "V75 created, and")
        print("        mode 11 is row 2's engaged mode -- inert on this car.")

    # ---- EDIT 3 -- the probe -----------------------------------------------------------------------
    print("\n  EDIT 3 -- THE PROBE (68 code bytes of the proven 68-byte extent; NO padding):")
    cave_bytes, cave_listing = build_cave()
    code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT] = cave_bytes
    for addr, raw, text in cave_listing:
        print(f"    0x{addr:05X}  {raw.hex():<10s} {text}")
    # 🛑 The HOOK SITE already carries the `jarl` on every cave build -- HOOK_STOCK is the DISPLACED
    # original that the cave re-executes, NOT what sits at 0x55C0E. Both are asserted, separately.
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
    cens = assert_probe_censuses(bytes(code), cave_span, CAVE_ACCESS_ON_OUTPUT)
    print("\n    ✅ GATE 1 (RAM ownership), asserted as a MEASUREMENT from raw bytes:")
    for disp, (r, w) in cens.items():
        print(f"       gp-0x{disp:04x}  {r}r / {w}w firmware -- the cave adds EXACTLY ONE load and "
              "writes it NEVER.")
    print(f"       🛑 The one-bit traps: `st.h r6,-0x{DAMP_DISP:04x},gp` @0x{PIN_STH_6BD0[0]:05X} is "
          f"{PIN_STH_6BD0[1].hex()} against our {V55.ldh(DAMP_DISP, R6).hex()};")
    print(f"          the ld.hu hw2 is 0x{struct.unpack('<H', ldhu_gp(BACKDRIVE_DISP, R6)[2:])[0]:04X}"
          " -- LSB SET, so the opcode is ld.hu and NOT the misaligned ld.w.")
    print(f"       All three lockstep shadows are untouched by the cave: "
          f"{', '.join(f'gp-0x{d:04x} ({w})' for d, w in SHADOW_DISPS.items())}.")
    print(f"       ⊕ The cave does NOT read V74's gp-0x{STATE_DISP:04x} -- asserted, so a stale V74 "
          "cave cannot masquerade as V75.")
    print(f"\n    ★★ THE THERMOMETER: bit4 => bit5 => bit6 => bit7 by construction, so only "
          f"{len(LEGAL_PAYLOADS)} of 32 payloads in")
    print(f"       bits 7:3 are reachable: {[hex(p) for p in LEGAL_PAYLOADS]}.")
    print("       V74's own on-car payload (0x28/0xA8) and V73's 0xD0 are ILLEGAL here ⇒ this build "
          "has a")
    print("       STRUCTURAL identity guard, which V74 did not.")

    if assert_decoder_matches(cave_bytes):
        print("    ✅ rlog-tools/probe/decode_v75_probe.py CAVE_HEX matches the built cave byte-for-byte.")

    # ---- 🛑 RE-DISASSEMBLE THE CAVE FROM THE BUILT BYTES, IN PYTHON -------------------------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE (raw Python decoder, NOT a Ghidra database):")
    redis = redisassemble_cave(bytes(code[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))
    for (a, raw, m) in redis:
        print(f"    0x{a:05X}  {raw.hex():<10s} {m}")
    assert [r for _a, r, _m in redis] == [r for _a, r, _t in cave_listing], \
        "the re-disassembly's bytes differ from the emitted listing"
    assert [a for a, _r, _m in redis] == [a for a, _r, _t in cave_listing], \
        "the re-disassembly does not land on the same instruction boundaries as the build listing"
    assert not [m for _a, _r, m in redis if m == "nop" or m.startswith("??")], \
        "the re-disassembly contains a nop or an undecoded halfword -- V75's cave is FULL"
    stores = [(a, m) for a, _r, m in redis if m.startswith(("st.b", "st.h"))]
    assert len(stores) == 1 and stores[0][1] == f"st.b r{R6},{-PAYLOAD_BYTE4_DISP}[r{GP}]", \
        f"the re-disassembly finds stores {stores} -- expected exactly ONE st.b to the CAN payload"
    loads = [m for _a, _r, m in redis if m.startswith(("ld.bu ", "ld.h ", "ld.hu ", "ld.w "))]
    assert loads == [f"ld.h {-DAMP_DISP}[r{GP}],r{R6}",
                     f"ld.hu {-BACKDRIVE_DISP}[r{GP}],r{R6}",
                     f"ld.bu {-PAYLOAD_BYTE4_DISP}[r{GP}],r{R6}"], \
        f"the re-disassembled load sequence is {loads} -- a `ld.w` here would be the MISALIGNED form"
    ors = [m for _a, _r, m in redis if m.startswith("or ")]
    assert ors == [f"or r{R7},r{R6}"], \
        f"the re-disassembled `or` sequence is {ors} -- V75 has ONLY the merge `or r7,r6`"
    assert [m for _a, _r, m in redis if m.startswith("subr ")] == [f"subr r{R0},r{R6}"], \
        "the re-disassembly does not find exactly one `subr r0,r6` -- a `sub` would not negate"
    brs = [(a, m) for a, _r, m in redis if m.startswith(("be ", "bne ", "blt ", "bge ", "b?"))]
    assert [m for _a, m in brs] == [f"be +{BE_SKIP_ZERO}", f"bge +{BGE_SKIP_NEG}"] + \
        [f"blt +{BLT_SKIP}"] * 3 + [f"be +{BE_SKIP_BD}"], \
        f"the re-disassembled branch sequence is {[m for _a, m in brs]}"
    bounds = [a for a, _r, _m in redis]
    for a, m in brs:
        assert a + int(m.split("+")[1]) in bounds, \
            f"the branch `{m}` @0x{a:05X} does not target an instruction boundary in the readback"
    mags = [m for _a, _r, m in redis if m.startswith("cmp 0x") or m.startswith("cmp ")]
    assert [m for m in mags if not m.startswith("cmp r")] == [f"cmp {i},r{R6}" for i in MAG_IMM5], \
        f"the re-disassembled magnitude compares are {mags}, expected {MAG_IMM5}"
    adds = [(a, m) for a, _r, m in redis if m.startswith("add ")]
    assert [m for _a, m in adds] == [f"add {w},r{R7}" for w in (W_B7, W_B6, W_B5, W_B4, W_B3_POST)], \
        f"the re-disassembled accumulate sequence is {[m for _a, m in adds]}"
    shl_a = [a for a, _r, m in redis if m == f"shl 0x{HI_SHIFT:x},r{R7}"]
    assert len(shl_a) == 1 and adds[3][0] < shl_a[0] < adds[4][0], \
        "🛑 the `shl 0x4,r7` does not sit between the fourth and fifth `add` -- bit7 and bit3 would " \
        "be silently relabelled"
    print(f"    ✅ ONE `ld.h` (the damper, SIGNED) + ONE `ld.hu` (the back-drive gate, UNSIGNED and "
          "NOT ld.w) + ONE `ld.bu`,")
    print("       exactly ONE store, ONE `subr` (not `sub`), five branches all landing on emitted")
    print(f"       BOUNDARIES, and the `shl 0x{HI_SHIFT:x}` correctly between the 4th and 5th `add`. "
          "Re-derived from the BUILT bytes.")

    # ---- the untouched sites, re-asserted on the finished image ------------------------------------
    V74.assert_must_not_change(code, "V75", stock, v74)
    assert_v75_shape(code, "V75", v74, ENGAGED, lever_f)
    print("\n  ✅ THE FULL KEEP-LIST RE-ASSERTED ON THE FINISHED IMAGE: both `sar` sites at stock,")
    print("     the gate, all three arms, V72's gain_A r26 cut EXACTLY, LEVER C, the carried")
    print("     0x454FE, the clamp at 850, the six pointer arrays, the config table, V57's")
    print("     decoupling, V53's STOCK_CALS, EVERY friction record, EVERY ceiling record, FactorE's")
    print("     WHOLE Y ROW, and EVERY DISENGAGED-COLUMN RECORD byte-identical to V74.")

    # ---- CRC ---------------------------------------------------------------------------------------
    touched = [CAVE_BASE] + list(lever_f)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    expect_trailers = [0xC4FFC, 0xCFFFC, 0xD0FFC, 0xD2FFC, 0xD3FFC, 0xD4FFC, 0xD6FFC, 0xD7FFC,
                       0xD8FFC, 0xD9FFC]
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
    all_edit_bytes = set(range(CAVE_BASE, CAVE_BASE + CAVE_EXTENT)) | \
        {a + k for a in lever_f for k in (0, 1)}
    assert not [a for a in all_edit_bytes if 0xC5000 <= a < 0xC5FFC], \
        "an edit landed in [0xC5000,0xC5FFC) -- the CRC-SKIPPED block with the V40 ignition precedent"
    print(f"    ✅ NOTHING of the {len(all_edit_bytes)} edited bytes lands in [0xC5000,0xC5FFC) -- "
          "the CRC-skipped block, V40 ignition precedent.")

    # ---- the attributed diff -- ONE BUCKET PER LEVER, so a re-cut's diff reads directly ----------
    c_cells = {a + k for a in lever_cy0 for k in (0, 1)}
    e_cells = {a + k for a in lever_ex1 for k in (0, 1)}
    assert not (c_cells & e_cells), "the two levers' cells overlap -- the buckets are not separable"

    def attribute(d):
        return ("PROBE cave (6bd0 thermometer / 6ac2)" if d in cave_span else
                f"LEVER CY0 FactorC Y[0] := {TARGET_C_Y0}" if d in c_cells else
                f"LEVER EX1 FactorE X[1] := {TARGET_E_X1}" if d in e_cells else None)

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
        print(f"    0x{a:05X}-0x{b:05X} ({b - a + 1:2d} B)  {bytes(v74[a:b + 1]).hex():<20s} -> "
              f"{bytes(code[a:b + 1]).hex():<20s} {attribute(a)}")
    counts = {}
    for d in f74:
        counts[attribute(d)] = counts.get(attribute(d), 0) + 1
    print(f"    by lever: {counts}")
    # 🛑 COUNT CELLS, NOT BYTES. Modes 29/32/33 move 565 -> 566, which changes only the LOW byte
    # (0x35 -> 0x36), so a byte count would be 19 and not 22 -- and asserting 22 would fail a
    # correct build. The cell-level statement is the one that means what it says.
    moved_c = [a for a in lever_cy0 if code[a:a + 2] != v74[a:a + 2]]
    moved_e = [a for a in lever_ex1 if code[a:a + 2] != v74[a:a + 2]]
    want_c = (len(ENGAGED) - len(HELD_AT_BASE)) if LEVERS["CY0"] else 0
    want_e = len(ENGAGED) if LEVERS["EX1"] else 0
    assert len(moved_c) == want_c, \
        f"{len(moved_c)} FactorC cells moved, expected {want_c} " \
        f"(lever CY0 {'ON' if LEVERS['CY0'] else 'OFF'}" \
        f"{f'; {len(ENGAGED)} engaged minus {len(HELD_AT_BASE)} HELD' if LEVERS['CY0'] else ''})"
    assert len(moved_e) == want_e, \
        f"{len(moved_e)} FactorE cells moved, expected {want_e} " \
        f"(lever EX1 {'ON' if LEVERS['EX1'] else 'OFF'})"
    if LEVERS["EX1"]:
        assert counts.get(f"LEVER EX1 FactorE X[1] := {TARGET_E_X1}") == 2 * len(ENGAGED), \
            "the FactorE byte count does not match 13 modes x 2 bytes (400 -> 200 moves both bytes)"
    # every DERIVED cell that did not move must be an explained no-op: lever off, or a HELD mode.
    for a, v in lever_f.items():
        if a in moved_c or a in moved_e:
            continue
        assert v[0] == v[1], f"cell 0x{a:05X} claims {v[0]} -> {v[1]} but the bytes did not move"
        assert not LEVERS[v[4]] or v[3] in HELD_AT_BASE, \
            f"cell 0x{a:05X} did not move, its lever {v[4]} is ON, and mode {v[3]} is not a " \
            "declared HELD mode -- an edit silently did nothing"

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
    FF.assert_x31_checksum(rwd, "V75 output")

    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    dec = bytearray(v74)
    dec[START:END] = bytes(back["encs"][0]).translate(decode)
    assert dec[START:END] == code[START:END], "decoded payload != built image"

    # 🛑 EVERYTHING re-derived FROM THE READBACK, not from the in-memory build.
    V74.assert_must_not_change(dec, "V75 readback", stock, v74)
    assert_v75_shape(dec, "V75 readback", v74, ENGAGED, lever_f)
    _rows, eng_rb, dis_rb = V74.derive_mode_columns(bytes(dec))
    assert (eng_rb, dis_rb) == (ENGAGED, DISENGAGED), "the readback's mode columns differ"
    # 🛑 REPRODUCIBILITY, re-derived in the SAME dependency order as the build: EX1 from the pristine
    # base, applied to a scratch copy, then CY0's cap searched against that scratch. Re-deriving CY0
    # against the untouched base would search a lever set that was never built.
    scratch = bytearray(v74)
    rb_ex1 = derive_lever_ex1(scratch, ENGAGED, verbose=False)
    for addr, (_o, new, _l, _m, _f) in rb_ex1.items():
        struct.pack_into("<H", scratch, addr, new)
    rb_cy0, _rep = derive_lever_cy0(scratch, v74, ENGAGED, verbose=False)
    assert rb_ex1 == lever_ex1 and rb_cy0 == lever_cy0, \
        "the lever derivation is not reproducible from the base image"
    for addr, (_o, new, lbl, _m, _f) in lever_f.items():
        assert u16(dec, addr) == new, f"readback {lbl} @0x{addr:05X} is {u16(dec, addr)}"
    V74.assert_clamp_census(bytes(dec))
    surf_rb, _n = assert_no_clip(dec, v74, ENGAGED, "V75 readback")
    doses_rb = {m: damper_authority(dec, m, 0, BURST_RATE) for m in ENGAGED}
    assert doses_rb == doses, f"the readback dose table differs: {doses_rb} vs {doses}"
    assert surf_rb == surf, "the readback surface report differs"
    assert bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]) == cave_bytes, "readback cave differs"
    assert_probe_censuses(bytes(dec), cave_span, CAVE_ACCESS_ON_OUTPUT)
    assert [r for _a, r, _m in redisassemble_cave(bytes(dec[CAVE_BASE:CAVE_BASE + CAVE_EXTENT]))] == \
        [r for _a, r, _m in redis], "the readback cave does not re-disassemble identically"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    rb_stray = [i for i in range(START, END)
                if dec[i] != v74[i] and i not in crc_only and attribute(i) is None]
    assert not rb_stray, f"readback differs from V74 outside the attributed set: {rb_stray[:8]}"
    print("\n  READBACK -- the config table and BOTH mode columns re-derived, all 26 dose-crank")
    print("     cells, the no-clip surface rule and the DOSE TABLE recomputed FROM THE READ-BACK")
    print("     BYTES, the whole 68-byte cave AND its re-disassembly, both probe-cell censuses, all")
    print("     three lockstep shadows, the full keep-list, identity to V74 outside the attributed")
    print("     set, and the full CRC chain: ALL re-verified ON THE READBACK.")

    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print(f"\n  wrote {OUT}\n    SHA256 {rwd_sha}")
    print("\n" + "=" * 102)
    print(f"  V75 BUILT -- UNFLASHED, FLIGHT CONDITIONAL. Lever set: {lever_token()}")
    print("  🛑 THIS IS NOT CLEARANCE TO FLY. The route-5d abort check put V74's own 5x-f0")
    print("     prominence at 2.884 [2.301, 3.575] against a 3.0 line, and its CREEP-ONLY arm at")
    print("     5.844 against a 0.632 baseline -- and creep is exactly where LEVER CY0 acts.")
    print("     The flight decision is the operator's; this build does not make it.")
    print(f"  ★★ THE LIVE MODE {LIVE_MODE} delivers {doses[LIVE_MODE]} counts at the measured burst "
          f"rate {BURST_RATE} -- **{ratio:.2f}x** V74's {LIVE_EXPECT['dose_old']}.")
    print("  ★★ The probe is now a MAGNITUDE THERMOMETER on gp-0x6bd0 plus the back-drive gate")
    print("     gp-0x6ac2, and only 10 of 32 payloads are reachable ⇒ a V73 or V74 log is REJECTED")
    print("     structurally, which no previous probe in this kit could do.")
    print("  🛑 The DISENGAGED column is byte-stock ⇒ manual and parking steering are untouched.")
    print("  🛑 Read the probe FIRST: an ILLEGAL payload means this is not a V75 log.")
    print("  🛑 Flash only on the operator's explicit instruction, naming the file and the bus.")
    return img_sha, rwd_sha


def _self_check():
    """Everything checkable without an image."""
    _self_check_encoders()
    assert (BIT_DAMP_NZ, BIT_MAG128, BIT_MAG288, BIT_MAG448, BIT_BACKDRIVE) == \
        (0x80, 0x40, 0x20, 0x10, 0x08)
    assert not (set(ENGAGED_EXPECTED) & set(DISENGAGED_EXPECTED)), "the mode columns overlap"
    assert len(ENGAGED_EXPECTED) == len(DISENGAGED_EXPECTED) == 13
    assert LIVE_MODE in ENGAGED_EXPECTED and 10 in DISENGAGED_EXPECTED
    assert set(HELD_AT_BASE) < set(ENGAGED_EXPECTED)
    cave, listing = build_cave()
    assert len(cave) == 68 and len(listing) == 28, f"{len(cave)}B / {len(listing)} entries"
    assert cave.hex().startswith("003a24373094e031c205ae058031483a8532")


if __name__ == "__main__":
    build()
