#!/usr/bin/env python3
r"""=================================================================================================
V103 -- Honda's dormant biquad armed engaged-only (Part A) + the comparator probe (Part B).
         🛑 b3/byte7 IDENTITY IS STILL UNRESOLVED -- this build will not write a file until it is.
=================================================================================================

BASE: **V102** (`_v102_V101BASE-GAIN6X.C6CD0.5346-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6_plain_image.bin`)
      sha256 61197f8ceffc401f9396e9023d07995820e17bb957007a6cd48d227dbfe32455 -- **BUILT, NOT FLASHED**
      as of this build (V101 remains on the car).  team-lead's spec explicitly bases V103 on V102.

    🛑 GAIN DOES NOT MOVE.  0xC6CD0 stays 5346 (6x).  0xC61B2/0xC61B4 stay 3072 (tracking).
       These were the toggle cells in V102's script; here they are permanently FROZEN.

-------------------------------------------------------------------------------------------------
PART A -- ARM HONDA'S DORMANT BIQUAD, ENGAGED-ONLY.  Spec from `pole-hunt`, verified independently
          by this builder against the actual V102 image before being applied here.
-------------------------------------------------------------------------------------------------
`FUN_000352b4` (0x352b4-0x35b1f) contains a genuine 2-state recursive (DF-style) float filter that
Honda ships DISARMED.  Its two state cells, `gp-0x3814`/`gp-0x3818` (abs 0xFEDF47EC/0xFEDF47E8), are
Honda's own -- already allocated, already read+written by Honda's own code every time this path runs,
and boot to a `.data` initializer that is exactly 0.0f for both (verified twice: read flash
0x89898-0x8989F on stock AND on this exact V102 base, byte-identical, all zero). **ZERO NEW RAM
CLAIM.** GATE-1 footprint scan (disp16 + register-indirect + disp23-style text + LE32 literal-table
+ get_xrefs_to, all against the current fully-analysed program) found both cells' only accesses
anywhere in the image are the two pairs already inside `FUN_000352b4` itself.

Stock arm condition (measured DEAD across 255,292 engaged frames on three builds -- V64 0/14,980,
V67 0/186,321, V68 0/53,991):
    r9  = gp-0x671a               ; the reversal-counter
    r12 = tp+0x74fa = 0xC64FA     ; a threshold cal
    r6  = (r9 >= r12 unsigned)    ; setfnc -- "NC" = no-carry = unsigned >=

New arm condition -- engaged-only, repointing the SOURCE, not just the threshold:
    r9  = gp-0x6806               ; the LKAS engagement flag (this kit's own established ID)
    r6  = (r9 != 0)                ; setfne -- "NE" = not-equal

| # | address | current (verified against V102) | new | what changes |
|---|---------|-----------------------------------|-----|---------------|
| 1 | 0xC649B  cal, 1 B | `00` | `01` | arms Honda's dormant biquad (was disarmed) |
| 2 | 0x35A06  code, 4 B | `84 4F E7 98` = `ld.bu -0x671a[gp],r9` | `84 4F FB 97` = `ld.bu -0x6806[gp],r9` | arm SOURCE: reversal-counter -> LKAS engaged flag |
| 3 | 0x35A12  code, 2 B | `EC 49` = `cmp r12,r9` | `E0 49` = `cmp r0,r9` | compares the new r9 against literal 0 |
| 4 | 0x35A18  code, 4 B | `E9 37 00 00` = `setfnc r6` | `EA 37 00 00` = `setfne r6` | condition: unsigned->= becomes !=0 |

All four bytes were read directly off `_v102_..._plain_image.bin` by this builder (not taken from the
spec) and matched exactly before this script was written. The new encodings were independently
re-derived from the raw bits (register-field and condition-code-nibble decode), not just diffed
against the spec string.

**GATE 1 -- no new RAM, no new code region.** All four sites are IN-PLACE edits to bytes Honda's own
compiler already emitted -- not a cave, not a trampoline. Same risk class as V62/V67 (a 2-4 byte
in-place displacement/condition edit), the lowest-risk edit class this kit has, and far below a new
cave.

**GATE 2 -- closed-loop placement is `pole-hunt`'s call, not re-litigated here.** This builder's job
is byte-exact, verified construction of the edit `pole-hunt` specified; the biquad's own output
already flows into an existing shadow/plausibility check (`gp-0x6b86` vs `gp-0x4cde`, `FUN_0006b9fa`
on mismatch) -- noted for the record, not claimed as a substitute for real closed-loop verification.

**CRC -- TWO trailers, not one.** `0x35A06`/`0x35A12`/`0x35A18` sit in the main app block
`[0x13000,0xC4FFC)` -> trailer `0xC4FFC`. `0xC649B` sits in the cal block `[0xC6000,0xC6FFC)` ->
trailer `0xC6FFC`. Both are recomputed automatically below via the existing `owning_block`/
`walk_all_blocks` machinery -- no new CRC path written.

-------------------------------------------------------------------------------------------------
PART B -- THE COMPARATOR PROBE.  🛑 FINAL MAP, team-lead's third and last word (supersedes both an
          earlier pump-hunt spec AND team-lead's own first revision, which this builder already
          built once and is now replacing): **EXACTLY ONE BIT CHANGES.**
-------------------------------------------------------------------------------------------------
    | bit | V102 today                        | V103           | role |
    |-----|------------------------------------|-----------------|------|
    | b7  | gp-0x6b4c < 0                      | UNCHANGED       | wiring control -- expect duty ~0.27, rising 0.148->0.417 with wheel rate |
    | b6  | \|gp-0x6ada\| >= \|gp-0x6adc\|      | UNCHANGED       | r24 vs r26 -- expect duty 0.8991, rising 0.836(<1 deg/s)->0.981(13-25)->0.992(25-50) with wheel rate |
    | b5  | \|gp-0x6ae2\| >= \|gp-0x6b26\|      | UNCHANGED       | friction vs inertia -- expect duty 0.2481.  **NOT sacrificed -- Decision 1 (repurpose b5) is MOOT** |
    | b4  | gp-0x6ada < 0                      | UNCHANGED       | r24 sign -- expect duty 0.4091 |
    | **b3** | forced 0                        | **sign(gp-0x3680) < 0 -- NEW** | **D_state's own sign -- the new measurand, AND the identity mechanism (see below)** |

`gp-0x3680` = D_state, the PID's own D-term accumulator (`FUN_0003a382`). **32-bit** (`ld.w`/`st.w`),
unlike every other cell this cave has ever touched (all 16-bit `ld.h`). GATE-1, independently
re-verified by this builder (not taken from the spec): exactly TWO gp-relative accesses to
`gp-0x3680` anywhere in the 183,569-instruction analysed image -- `ld.w -0x3680,gp,r9` @`0x3a85c`
and `st.w r14,-0x3680,gp` @`0x3a87a`, BOTH inside `FUN_0003a382`. Zero LE32 literal-table references
to its absolute address (`0xFEDF4980`) anywhere in the 1 MB image -- not part of any table-dispatched
registry (the class that makes `gp-0x1500`/`gp-0x14E0` unsafe). The rung only READS it -- zero new RAM
claim, same as every prior cave in this kit. `0xC64FA` (the shared oscillation-detector ceil Part A
deliberately avoids) stays at 5, untouched, asserted -- unrelated to this bit.

🛑 **THE `ld.w ...,gp,r6` ENCODING -- DERIVED AND GHIDRA-VERIFIED, NOT HAND-DECODED.** `pump-hunt`
found real `ld.w` instructions at r9 (`24 4f 81 c9`) and r15 (`24 7f 7d c9`) but none at r6, and
declined to hand-derive the register field -- correctly, per this kit's own repeated hand-decode
failures (`hw2=disp|1`, the `jarl` Format-V mask, `ba05`/`b205` inversions, V90's big-endian cave).
This builder derived `reg2=(byte1>>3)&0x1F` from BOTH real examples (agreeing: 0x4F->9, 0x7F->15),
noted hw1 (byte0/byte1) is IDENTICAL between `ld.h` and `ld.w` for the same destination register
(differ only in hw2 bit0), and predicted `ld.w -0x3680,gp,r6` = `24 37 81 c9` (byte1=0x37 is the SAME
byte already used in dozens of proven `ld.h ...,gp,r6` instructions across V90-V102's caves).
**Verified independently**: imported a throwaway 4-instruction scratch binary (both real examples +
a known-good V102 `ld.h` anchor + the candidate) into a fresh Ghidra program and ran
`disassemble_bytes(dry_run=true)` -- Ghidra's own SLEIGH decoder confirms `ld.w -0x3680, gp, r6` for
the candidate bytes. Scratch program closed after; nothing touched the shared project.

**WHY b3, NOT A SHIFT-COMPATIBLE BIT.** b6/b5/b4/b7 all reach byte4 bits 7:4 via a 4-bit accumulator
then `shl 0x4` -- structurally that scheme can only ever reach bits 4-7. b3 (0x08) sits below the
shift, so D's sign is ADDED DIRECTLY (`add 0x8,r7`, unshifted) immediately AFTER PASS 3's `shl 0x4`
has already placed b7/b4 -- reusing the exact SAME two-byte `483a` sequence PASS 3 already uses for
b7's own pre-shift contribution (0x8 pre-shift becomes bit7 after the shift; the identical 0x8 used
AFTER the shift IS bit3 directly -- one proven byte pattern, two positions, no new encoding). PASS 3
grows from V102's 38 B (b7+b4) to 48 B (b7+b4+b3); PASS 1's mask changes (0xB7->0xBF: it no longer
forces bit3, PASS 3 now owns it exclusively); PASS 2 (b5) is BYTE-IDENTICAL to V102's, unedited.
New cave total: 46(PASS1)+46(PASS2)+48(PASS3)+18(BYTE7)+6(RET) = **164 B** (up from V102's 154 --
GROWTH IS STATED, NOT CLAIMED AWAY: +10 B, one full sign-check sequence, 13.5% of the 1,212 B extent).

⭐ **IDENTITY -- team-lead's ruling, quoted verbatim, and it must travel with the scorer:**
> *"V103 is the first build since V85 without a single-frame identity witness. Both axes are
> numerically exhausted: `byte7[7:6]` has all 4 codes allocated (0=<=V91, 1=V96/97, 2=V98-V100,
> 3=V101/V102), and `b3` is one bit with both its values already claimed (V101=1, V102=0) --
> forcing it to either value on V103 collides with an existing build's signature, not a new one.
> Neither a second CAN ID nor sacrificing a data bit was judged worth it. Route identity for V103
> must be established from `b5`'s statistics [sic -- superseded by the final map: from `b3`'s own
> behaviour] (duty and wheel-rate correlation, visibly different from V102's old friction-vs-inertia
> comparator within a handful of frames) plus the flash record -- not from a constant bit."*
🛑 **CONCRETE RULE FOR THE SCORER: `b3` MUST VARY.** No predecessor has a varying b3 -- V101 pins it
constant 1, V102 pins it constant 0 -- so observing b3 take BOTH values within a drive is a
categorical distinction (a toggling bit vs a bit that structurally cannot toggle), not a statistical
one. **A constant `b3` on this build means it is not V103, or the rung is dead -- either way, stop
and report, do not score further.** The ~50-build "byte4 is always odd" convention died at V98; the
byte7-plus-b3 single-frame-identity convention dies here.

=================================================================================================
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import build_vfourframe_tva as FF          # noqa: E402
import build_v53_tva as V53                # noqa: E402  -- owning_block, the REAL block map
from encode_eps import encode_x31, invert_table, parse_x31, build_decode_table   # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                             # noqa: E402
from verify_bootloader_crc import walk_all_blocks                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V103_WRITE", "").strip().lower()

GP, TP = 0xFEDF8000, 0xBF000

BASE_NAME = "_v102_V101BASE-GAIN6X.C6CD0.5346-CAVE.CMP.6ADA.6AE2-SIGNS-427.6B4C-ID.ID3.6_plain_image.bin"
BASE_BIN = str(plain_image_path(BASE_NAME))
BASE_SHA = "61197f8ceffc401f9396e9023d07995820e17bb957007a6cd48d227dbfe32455"
STOCK_BIN = str(plain_image_path("stock_fw_dump/code.bin"))
STOCK_SHA = "3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822"

# =================================================================================================
# PART A -- the four edit sites.  Byte-exact, independently re-verified against the V102 image
# by this builder before this table was written (see the docstring table above).
# =================================================================================================
A_CAL_ADDR = 0xC649B
A_CAL_PRE, A_CAL_POST = bytes([0x00]), bytes([0x01])

A_ARMSRC_ADDR = 0x35A06
A_ARMSRC_PRE = bytes.fromhex("844fe798")     # ld.bu -0x671a[gp],r9   (the reversal counter)
A_ARMSRC_POST = bytes.fromhex("844ffb97")    # ld.bu -0x6806[gp],r9   (the LKAS engagement flag)

A_CMP_ADDR = 0x35A12
A_CMP_PRE = bytes.fromhex("ec49")            # cmp r12,r9   (r12 = tp+0x74fa threshold cal)
A_CMP_POST = bytes.fromhex("e049")           # cmp r0,r9

A_SETF_ADDR = 0x35A18
A_SETF_PRE = bytes.fromhex("e9370000")       # setfnc r6   (cond 0x9 = NC = unsigned >=)
A_SETF_POST = bytes.fromhex("ea370000")      # setfne r6   (cond 0xA = NE = not-equal)

# the biquad's own two state cells -- NOT touched by Part A, asserted untouched below.
BIQUAD_X1, BIQUAD_X2 = 0x3818, 0x3814        # gp-0x3818 / gp-0x3814, abs 0xFEDF47E8 / 0xFEDF47EC
BIQUAD_FUNC_LO, BIQUAD_FUNC_HI = 0x352B4, 0x35B1F    # FUN_000352b4 body bounds, for locality checks

FUNC_ARM_ADDR = 0x35A02        # ld.bu 0x74fa[tp],r12 -- the OLD threshold load. Dead code after Part A
                                # (r12 is still loaded but no longer read meaningfully by the new
                                # `cmp r0,r9`) -- NOT edited; harmless, asserted present and unchanged.
FUNC_ARM_PRE = bytes.fromhex("8567fb74")       # anchor: confirms we are looking at the right region
                                                # = ld.bu 0x74fa[tp],r12 (the old threshold load)

# =================================================================================================
# PART B -- the comparator probe.  🛑 FINAL MAP: b7/b6/b5/b4 byte-identical to V102.  b3 -- ONLY
# b3 -- becomes the new measurand (D_state's sign) AND the identity mechanism.  See docstring.
# =================================================================================================
CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V102_CAVE_LEN = 154
V103_CAVE_LEN = 164
HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")   # jarl 0xC4B34,lp -- inherited, unedited

SRC_DSTATE = 0x3680      # gp-0x3680  D_state, the PID D-term accumulator.  32-bit.  b3 operand (NEW).
DSTATE_LDW_ADDR_R9 = 0x3A85C     # pump-hunt's real anchor: ld.w -0x3680,gp,r9  = 24 4f 81 c9
DSTATE_LDW_BYTES_R9 = bytes.fromhex("244f81c9")
DSTATE_STW_ADDR = 0x3A87A        # the sole writer: st.w r14,-0x3680,gp = 64 77 81 c9  (NOT edited)
DSTATE_LDW_BYTES_R6 = bytes.fromhex("243781c9")   # derived + Ghidra-verified, see docstring

# ---- PASS 1 (b6) -- instructions BYTE-IDENTICAL to V102; MASK CHANGES (no longer forces b3=0) --
PASS1 = bytes.fromhex(
    "24372695"      # +0x00  ld.h  -0x6ada[gp],r6    A = r24 lane mirror
    "6032" "ae05"   # +0x04  cmp 0x0,r6 / bge +4
    "8031"          # +0x08  subr  r0,r6            r6 = |A|
    "0638"          # +0x0A  mov   r6,r7            r7 = |A|
    "24372495"      # +0x0C  ld.h  -0x6adc[gp],r6   B = r26 lane mirror
    "6032" "ae05"   # +0x10  cmp 0x0,r6 / bge +4
    "8031"          # +0x14  subr  r0,r6            r6 = |B|
    "e639"          # +0x16  cmp   r6,r7           flags = |A| - |B|
    "043a"          # +0x18  mov   0x4,r7          ASSUME SET (pre-shift bit2 -> b6)
    "ae05"          # +0x1A  bge   +4              taken iff |A| >= |B|
    "003a"          # +0x1C  mov   0x0,r7          else CLEAR
    "c43a"          # +0x1E  shl   0x4,r7          -> byte4 bit 6
    "8437edea"      # +0x20  ld.bu -0x1514[gp],r6
    "c636" "bf00"   # +0x24  andi  0xbf,r6,r6      clear bit 6 ONLY -- b3 no longer owned here
    "0731"          # +0x28  or    r7,r6
    "4437ecea")     # +0x2A  st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 1

# ---- PASS 2 (b5) -- BYTE-IDENTICAL to V102's ORIGINAL friction-vs-inertia comparator, unedited -
PASS2 = bytes.fromhex(
    "24371e95"      # +0x2E  ld.h  -0x6ae2[gp],r6   A = modelled Coulomb friction x1024 (K1 output)
    "6032" "ae05"   # +0x32  cmp 0x0,r6 / bge +4
    "8031"          # +0x36  subr  r0,r6            r6 = |A|
    "0638"          # +0x38  mov   r6,r7            r7 = |A|
    "2437da94"      # +0x3A  ld.h  -0x6b26[gp],r6   B = the INERTIA term
    "6032" "ae05"   # +0x3E  cmp 0x0,r6 / bge +4
    "8031"          # +0x42  subr  r0,r6            r6 = |B|
    "e639"          # +0x44  cmp   r6,r7           flags = |A| - |B|
    "023a"          # +0x46  mov   0x2,r7          ASSUME SET (pre-shift bit1 -> b5)
    "ae05"          # +0x48  bge   +4              taken iff |A| >= |B|
    "003a"          # +0x4A  mov   0x0,r7          else CLEAR
    "c43a"          # +0x4C  shl   0x4,r7          -> byte4 bit 5
    "8437edea"      # +0x4E  ld.bu -0x1514[gp],r6
    "c636" "df00"   # +0x52  andi  0xdf,r6,r6      clear bit 5 only
    "0731"          # +0x56  or    r7,r6
    "4437ecea")     # +0x58  st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 2

# ---- PASS 3 (b7 + b4 + b3) -- b7/b4 BYTE-IDENTICAL to V102; b3 (D_state's sign) ADDED after the
#      shl, unshifted -- reuses the SAME `483a` (add 0x8,r7) byte pattern PASS 3 already uses for
#      b7's pre-shift value, now applied directly to bit3 (0x08 IS bit3, no further shift needed).
#      48 B (V102's 38 + 10 for the new ld.w/cmp/bge/add sequence).
# -------------------------------------------------------------------------------------------------
PASS3 = bytes.fromhex(
    "003a"          #        mov   0x0,r7          init accumulator
    "2437b494"      #        ld.h  -0x6b4c[gp],r6   LKAS command
    "6032" "ae05"   #        cmp 0x0,r6 / bge +4
    "483a"          #        add   0x8,r7          b7 = (gp-0x6b4c < 0), pre-shift bit3 -> bit7
    "24372695"      #        ld.h  -0x6ada[gp],r6   r24 lane mirror
    "6032" "ae05"   #        cmp 0x0,r6 / bge +4
    "413a"          #        add   0x1,r7          b4 = (gp-0x6ada < 0), pre-shift bit0 -> bit4
    "c43a"          #        shl   0x4,r7          -> byte4 bits {7,4} PLACED
    ) + DSTATE_LDW_BYTES_R6 + bytes.fromhex(
    "6032" "ae05"   #        cmp 0x0,r6 / bge +4    skip iff D_state >= 0 (D_state now in r6)
    "483a"          #        add   0x8,r7          b3 = (D_state < 0), DIRECT bit3 -- NO shift;
                     #                              same 2 bytes as b7's pre-shift value above,
                     #                              reused past the shift point (0x8 == bit3 itself)
    "8437edea"      #        ld.bu -0x1514[gp],r6
    "c636" "6700"   #        andi  0x67,r6,r6      clear bits 7, 4 and 3
    "0731"          #        or    r7,r6
    "4437ecea")     #        st.b  r6,-0x1514[gp]  CAN 0x14A byte 4, pass 3 (b7+b4+b3)

# ---- byte7 identity block -- BYTE-IDENTICAL to V102, unchanged, 18 B --------------------------
BYTE7 = bytes.fromhex(
    "033a"          #        mov   0x3,r7          byte7[7:6] == 3   -- SAME code as V101/V102
    "c63a"          #        shl   0x6,r7          -> 0xC0
    "a437efea"      #        ld.bu -0x1511[gp],r6
    "c636" "3f00"   #        andi  0x3f,r6,r6      keep Honda's bits 5:0
    "0731"          #        or    r7,r6
    "4437efea")     #        st.b  r6,-0x1511[gp]  CAN 0x14A byte 7

# ---- return -- BYTE-IDENTICAL to V102, unchanged, 6 B ------------------------------------------
RET = bytes.fromhex(
    "2436e8ea"      #        movea -0x1518,gp,r6   restore the hooked instruction
    "7f00")         #        jmp   [lp]

PAYLOAD = PASS1 + PASS2 + PASS3 + BYTE7 + RET
MASK_PASS1 = 0x00BF      # writes bit 6 ONLY -- no longer forces b3
MASK_PASS2 = 0x00DF      # writes bit 5 -- byte-identical to V102's original
MASK_PASS3 = 0x0067      # writes bits 7, 4 AND 3 (D_state's sign, the new measurand)
MASK_B7 = 0x003F         # byte7 writes bits 7:6

INSN_HW1_2B = {
    "003a": "mov 0x0,r7", "023a": "mov 0x2,r7", "043a": "mov 0x4,r7", "033a": "mov 0x3,r7",
    "413a": "add 0x1,r7", "423a": "add 0x2,r7", "483a": "add 0x8,r7",
    "c43a": "shl 0x4,r7", "c63a": "shl 0x6,r7",
    "0638": "mov r6,r7", "8031": "subr r0,r6", "6032": "cmp 0x0,r6", "e639": "cmp r6,r7",
    "0731": "or r7,r6", "7f00": "jmp [lp]", "ae05": "bge +4",
}
INSN_HW1_4B = {
    "2437": "ld.h  disp[gp],r6", "8437": "ld.bu disp[gp],r6", "a437": "ld.bu disp[gp],r6",
    "4437": "st.b  r6,disp[gp]", "2436": "movea disp,gp,r6", "c636": "andi  imm,r6,r6",
}
BRANCH_MNEM, BRANCH_SPAN = "bge +4", 4
ST_B4_INSN = bytes.fromhex("4437ecea")      # st.b r6,-0x1514[gp]
ST_B7_INSN = bytes.fromhex("4437efea")      # st.b r6,-0x1511[gp]


def decode_cave(payload, name):
    """Linear sweep.  Raises if any byte is not covered by a known instruction form."""
    i, out = 0, []
    while i < len(payload):
        hw1 = payload[i:i + 2].hex()
        if hw1 in INSN_HW1_2B:
            out.append((i, 2, INSN_HW1_2B[hw1]))
            i += 2
        elif hw1 in INSN_HW1_4B:
            if i + 4 > len(payload):
                raise SystemExit(f"{name}: truncated 32-bit instruction at +0x{i:02X}")
            out.append((i, 4, INSN_HW1_4B[hw1]))
            i += 4
        else:
            raise SystemExit(f"{name}: UNKNOWN instruction hw1 {hw1} at +0x{i:02X}")
    return out


TOKEN = "V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA-ID.B3VARIES"
BIN_OUT = str(plain_image_path(f"_v103_{TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V103-{TOKEN}-0x{START:X}-0x{END:X}.rwd")

# =================================================================================================
# EVERYTHING THAT MUST NOT MOVE.  Carried from V102's own ledger.  0xC649B is REMOVED from here --
# it is now an EDIT TARGET (Part A #1), not a frozen cell.  The three gain cells, toggled in V102,
# are now PERMANENTLY FROZEN (team-lead: "Gain stays 6x. Do not change it.").
# =================================================================================================
FROZEN = {
    0x3AA96: (1, 0xC5, "LEVER B GATE -- HONDA STOCK / DEAD. Carried from V102. DO NOT RESTORE."),
    0xC6446: (2, 512, "LEVER B ARM -- HONDA STOCK. Carried from V102. DO NOT RESTORE."),
    0xC407E: (2, 511, "HARD-FAULT INTERLOCK -- Honda's 511, one under its own 512 trip"),
    0xC4080: (2, 0, "K0 -- NEVER RAISE (latent pure Coulomb relay)"),
    0xC40BC: (2, 300, "Coulomb ramp knee (V99's lever, carried)"),
    0xC40D0: (2, 408, "friction EMA alpha = 408/4096 -- matches 0xC63AC=102/1024"),
    0xC40D2: (2, 204, "K1 -- HELD AT 204. Instrumented by V102's b5, NOT dosed. Carried."),
    0xC40D4: (2, 573, "command-branch EMA -- VIRGIN"),
    0xC40D6: (2, 246, "accel/inertia EMA -- VIRGIN"),
    0xC40D8: (2, 3686, "gp-0x4f60 EMA -- a NO-OP"),
    0xC63AC: (2, 102, "accumulator pole -- Honda's own value (V99's revert)"),
    0xC63A0: (2, 1024, "w[0] gp-0x6bd0"),
    0xC63A2: (2, 1024, "w[1] gp-0x6bbe VISCOUS -- VIRGIN"),
    0xC63A4: (2, 1024, "w[2] gp-0x6b46 -- VIRGIN"),
    0xC63A6: (2, 1024, "w[3] gp-0x6b26 INERTIA -- VIRGIN (V102 b5's operand B)"),
    0xC63A8: (2, 1024, "w[4] gp-0x6b4e"),
    0xC63AA: (2, 1024, "w[5] gp-0x6b4c -- LKAS command lane (V102 b7 / 427 source)"),
    0xC63AE: (2, 1024, "Stage-2 LERP index scale"),
    0xC6200: (2, 8192, "PID reference clamp -- DEAD (V100 measured 0.000000)"),
    0xC6444: (2, 512, "r24 lane companion cal -- VIRGIN, and NOT Lever B's arm"),
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
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- V62's fix, half. Carried"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- carried"),
    0xC64A1: (1, 1, "READ-ONLY"),
    0xC63D2: (2, 6, "FUN_00036682 pole"),
    0xC640A: (2, 0xE000, "FALLBACK-2 STOCK"),
    0xC640C: (2, 0xF333, "FALLBACK-1 STOCK"),
    # -- the three cells V102 toggled; here they are permanent --
    0xC6CD0: (2, 5346, "🛑 LKAS GAIN -- 6x, THE OPERATOR'S RULING. DOES NOT MOVE in V103."),
    0xC61B2: (2, 3072, "fwd-path clamp -- tracks the gain, frozen with it"),
    0xC61B4: (2, 3072, "arb output clamp -- tracks the gain, frozen with it"),
    # -- team-lead's explicit addition: the cell Part A deliberately does NOT touch --
    0xC64FA: (1, 5, "🛑 SHARED OSCILLATION-DETECTOR CEIL -- ~18 in-code readers incl. "
                    "FUN_000428d4's own latch and the r24/r26 rate-lane arms. Part A arms the "
                    "biquad by patching the COMPARISON privately at 0x35A12, NOT by raising this "
                    "widely-shared cell -- this assertion makes that choice explicit."),
}

# =================================================================================================
# THE FRICTION DOSE FAMILY.  Car is TVCA4: 24/25 = MANUAL, 26/27 = ENGAGED.  Carried from V102.
# =================================================================================================
FRICTION_PTR_ARRAY = 0xCBE74
REC_X_OFF, REC_Y_OFF = 0x02, 0x08
MANUAL_MODES, ENGAGED_MODES = (24, 25), (26, 27)
FRICTION_Y_STOCK = (-9830, -5734, -1966)
FRICTION_Y_V92 = (-14745, -8601, -2949)

# =================================================================================================
# THE EME AUDIT -- every V25 -> V37 EME-prevention fix, re-run against the BUILT image.  Carried
# verbatim from V102 -- Part A touches none of these cells or ranges.
# =================================================================================================
EME_RANGES = [
    (0xC64B4, 0xC64BA, "V36/V37", "STEER_STATUS debounce disable + DTC-0x49 (0xC64B8 -> 0xFF)"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals maxed to 0xFFFF"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f (and -1.0f -> -5.0f)"),
    (0xC65C6, 0xC65D0, "V31->V38", "soft-EME boost floor FLOAT 0.0f/1.5f/2.0f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC64DE, 0xC64E0, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384, bank 1"),
    (0xE5180, 0xE5260, "V38", "same taper surface, bank 2"),
]
EME_SCALARS = [
    (0xC64B8, 1, 0xFF, 0x70, "DTC-0x49 counter-B gate -- 112 -> 0xFF, can never increment (V37)"),
    (0xC61C0, 2, 0xFFFF, 1600, "debounce cal 0 (V36)"),
    (0xC61C2, 2, 0xFFFF, 896, "debounce cal 1 (V36)"),
    (0xC61C4, 2, 0xFFFF, 1280, "debounce cal 2 (V36)"),
    (0xC64DE, 1, 27, 17, "re-engage ramp (pre-V38)"),
    (0xC674E, 2, 5120, 1024, "soft-EME boost floor INT -- THE AUTHORITY FLOOR"),
]
EME_FLOATS = [
    (0xC6598, 5.0, 1.0, "soft-EME boost floor FLOAT #1 (V29->V38)"),
    (0xC659C, 5.0, 1.0, "soft-EME boost floor FLOAT #2 (V29->V38)"),
    (0xC65AC, -5.0, -1.0, "soft-EME boost floor FLOAT #3, negative rail (V29->V38)"),
    (0xC65B0, -5.0, -1.0, "soft-EME boost floor FLOAT #4, negative rail (V29->V38)"),
    (0xC65C4, 5.0, 0.0, "soft-EME boost floor FLOAT #5 (V31->V38)"),
    (0xC65C8, 5.0, 1.5, "soft-EME boost floor FLOAT #6 (V31->V38)"),
    (0xC65CC, 5.0, 2.0, "soft-EME boost floor FLOAT #7 (V31->V38)"),
]

# the non-stock ledger vs HONDA STOCK.  Carried from V102 + Part A's four new ranges.
VS_STOCK = [
    (0x13109, 0x1310A, "pre-V38", "part-number '-' -> ','"),
    (0x14120, 0x14121, "pre-V38", "part-number 2nd copy"),
    (0x2A1F0, 0x2A1F2, "V57", "forward-LKAS reader repointed tp+0x746C -> tp+0x7CD0"),
    (0x454FE, 0x454FF, "V42", "state-4 governor bne -> br (INERT, carried)"),
    (0x55C0E, 0x55C12, "V53+", "THE CAVE HOOK -- jarl 0xC4B34,lp"),
    (0x55DF2, 0x55DF4, "V102", "CAN 427 source gp-0x6c18 (stock) -> gp-0x6b4c"),
    (0x55E10, 0x55E11, "V96", "CAN 427 scaler sar 0x3 -> sar 0x6"),
    (0xC40BC, 0xC40BE, "V99", "Coulomb ramp knee 600 -> 300"),
    (0xC40D2, 0xC40D3, "V89", "K1 Coulomb gain 102 -> 204 -- HELD, instrumented not dosed"),
    (0xC4B34, 0xC4B34 + V103_CAVE_LEN, "CAVE", "the code cave -- 164 B (b7/b6/b5/b4 unchanged, "
                                                "b3 -> D_state sign, the new measurand and identity)"),
    (0xC61B2, 0xC61B6, "V101", "LKAS forward-path clamps -- now FROZEN at the tracking value"),
    (0xC61C0, 0xC61C6, "V36", "STEER_STATUS debounce cals"),
    (0xC62EA, 0xC62EC, "V53", "low-speed steer lockout 320 -> 0"),
    (0xC64B4, 0xC64B9, "V36/V37", "STEER_STATUS debounce + DTC-0x49"),
    (0xC64DE, 0xC64DF, "pre-V38", "re-engage ramp 17 -> 27"),
    (0xC6598, 0xC65B4, "V29->V38", "soft-EME boost floor FLOAT 1.0f -> 5.0f"),
    (0xC65C6, 0xC65CF, "V31->V38", "soft-EME boost floor FLOAT 1.5f -> 5.0f"),
    (0xC674E, 0xC676E, "V25->V38", "soft-EME boost floor INT 1024 -> 5120"),
    (0xC6CD0, 0xC6CD2, "V101", "the PRIVATE forward-LKAS gain -- now FROZEN at 6x"),
    (0xD7A5C, 0xD7A62, "V92", "friction dose x1.5 engaged mode 26 -- MEASURED INERT"),
    (0xD7A6C, 0xD7A72, "V92", "friction dose x1.5 engaged mode 27 -- MEASURED INERT"),
    (0xE4180, 0xE4260, "V38", "LKAS command clamp taper 15360 -> 16384"),
    (0xE5180, 0xE5260, "V38", "same taper surface, second bank"),
    # -- Part A, new this build --
    (0xC649B, 0xC649C, "V103", "PART A: arm Honda's dormant biquad, 0 -> 1"),
    (0x35A06, 0x35A0A, "V103", "PART A: arm source, reversal-counter -> gp-0x6806 engagement flag"),
    (0x35A12, 0x35A14, "V103", "PART A: cmp r12,r9 -> cmp r0,r9"),
    (0x35A18, 0x35A1C, "V103", "PART A: setfnc -> setfne (unsigned>= -> !=0)"),
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


def f32(buf, a):
    return struct.unpack_from("<f", buf, a)[0]


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def rdw(buf, a, w):
    return u16(buf, a) if w == 2 else (buf[a] if w == 1 else rd(buf, a, w))


def rec_addr(buf, mode):
    return struct.unpack_from("<I", buf, FRICTION_PTR_ARRAY + mode * 4)[0]


def rec_y(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_Y_OFF)


def rec_x(buf, mode):
    return struct.unpack_from("<3h", buf, rec_addr(buf, mode) + REC_X_OFF)


def assert_frozen(buf, label):
    bad = []
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = rdw(buf, a, w)
        if got != want:
            bad.append((a, got, want, why))
    for a, got, exp, why in bad:
        print(f"    {BAD} 0x{a:05X} is {got}, expected {exp} -- {why}")
    check(not bad, f"{label}: all {len(FROZEN)} FROZEN cells at their expected values")


def assert_friction_family(buf, label):
    print(f"\n    friction dose family 0x{FRICTION_PTR_ARRAY:05X} ({label}) -- "
          f"CAR IS TVCA4: 24/25 MANUAL, 26/27 ENGAGED")
    bad = []
    for m in MANUAL_MODES + ENGAGED_MODES:
        ra = rec_addr(buf, m)
        want = FRICTION_Y_STOCK if m in MANUAL_MODES else FRICTION_Y_V92
        got = rec_y(buf, m)
        role = "MANUAL " if m in MANUAL_MODES else "ENGAGED"
        if got != want:
            bad.append(m)
        print(f"      {OK if got == want else BAD} mode {m:2d} {role}  record 0x{ra:05X}  "
              f"Y@0x{ra + REC_Y_OFF:05X} = {got}  X = {rec_x(buf, m)}")
    check(not bad, f"{label}: all 4 friction records at their expected Y "
                   f"(manual STOCK, engaged V92 x1.5 -- MEASURED INERT, carried unchanged)")


def eme_audit(img, base, stock, label):
    print(f"\n  ---- EME AUDIT ({label}) ----")
    print(f"    {'range':<21} {'B':>4} {'!=stock':>8}  {'==base':>7}  origin      what")
    allok = True
    for lo, hi, origin, what in EME_RANGES:
        same_as_base = bytes(img[lo:hi]) == bytes(base[lo:hi])
        n_vs_stock = sum(1 for i in range(lo, hi) if img[i] != stock[i])
        allok &= same_as_base and n_vs_stock > 0
        print(f"    {'0x%05X-0x%05X' % (lo, hi - 1):<21} {hi - lo:>4} {n_vs_stock:>8}  "
              f"{'YES' if same_as_base else 'NO!':>7}  {origin:<10}  {what}")
    check(allok, f"{label}: all {len(EME_RANGES)} EME ranges carried "
                 f"(identical to the audited V102 base AND non-stock)")

    print(f"\n    scalar cells:")
    bad = []
    for a, w, want, stk, why in EME_SCALARS:
        got = rdw(img, a, w)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_SCALARS)} EME scalar cells at their fixed values")

    print(f"\n    float cells:")
    bad = []
    for a, want, stk, why in EME_FLOATS:
        got = f32(img, a)
        print(f"      {OK if got == want else BAD} 0x{a:05X}  = {got:<7} (stock {stk:<7})  {why}")
        if got != want:
            bad.append(a)
    check(not bad, f"{label}: all {len(EME_FLOATS)} EME float cells at their fixed values")

    floor, clamp = u16(img, 0xC674E), u16(img, 0xC61B2)
    check(floor == 5120 and floor > clamp,
          f"{label}: soft-EME boost floor INT = {floor} > {clamp} (the fwd-path clamp) "
          f"=> authority sufficient")
    check(u16(img, 0xC407E) == 511,
          f"{label}: hard-fault interlock 0xC407E = 511 (Honda's own, one under its 512 trip)")
    check(u16(img, 0xC4080) == 0, f"{label}: 0xC4080 (K0) = 0 -- NEVER-RAISE, untouched")


def build():
    print("=" * 102)
    print("  V103 -- Honda's dormant biquad armed engaged-only (Part A) + the comparator probe (Part B).")
    print("          FINAL MAP: exactly one bit changes -- b3 -> sign(gp-0x3680), D's delivered sign.")
    print("=" * 102)

    # ==============================================================================================
    print("\n  [1] THE BASE -- V102 (BUILT, NOT FLASHED -- V101 remains on the car)")
    base = bytearray(Path(BASE_BIN).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA,
          f"base is V102, sha256 {BASE_SHA[:24]}...")
    check(len(base) == 0x100000, f"base is {len(base)} bytes")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50")
    stock = bytearray(Path(STOCK_BIN).read_bytes())
    check(hashlib.sha256(bytes(stock)).hexdigest() == STOCK_SHA and len(stock) == 0x100000,
          f"stock reference loaded, sha256 {STOCK_SHA[:24]}...")

    # ==============================================================================================
    print("\n  [2] FROZEN CELLS -- every one at its expected value BEFORE the edit")
    assert_frozen(base, "V102 base")
    assert_friction_family(base, "V102 base")

    # ==============================================================================================
    print("\n  [3] PART A -- PRE-EDIT VERIFICATION, independently against the base image")
    check(rd(base, A_CAL_ADDR, 1) == A_CAL_PRE, f"0x{A_CAL_ADDR:05X} = {A_CAL_PRE.hex()} (disarmed)")
    check(rd(base, A_ARMSRC_ADDR, 4) == A_ARMSRC_PRE,
          f"0x{A_ARMSRC_ADDR:05X} = {A_ARMSRC_PRE.hex()} = ld.bu -0x671a[gp],r9")
    check(rd(base, A_CMP_ADDR, 2) == A_CMP_PRE,
          f"0x{A_CMP_ADDR:05X} = {A_CMP_PRE.hex()} = cmp r12,r9")
    check(rd(base, A_SETF_ADDR, 4) == A_SETF_PRE,
          f"0x{A_SETF_ADDR:05X} = {A_SETF_PRE.hex()} = setfnc r6")
    check(rd(base, FUNC_ARM_ADDR, 4) == FUNC_ARM_PRE,
          f"0x{FUNC_ARM_ADDR:05X} anchor confirms this is the right FUN_000352b4 region")
    check(BIQUAD_FUNC_LO <= A_ARMSRC_ADDR < BIQUAD_FUNC_HI
          and BIQUAD_FUNC_LO <= A_CMP_ADDR < BIQUAD_FUNC_HI
          and BIQUAD_FUNC_LO <= A_SETF_ADDR < BIQUAD_FUNC_HI,
          f"all three code edits lie inside FUN_000352b4 [0x{BIQUAD_FUNC_LO:05X},0x{BIQUAD_FUNC_HI:05X})")

    print("\n  [3b] PART A -- FIELD-LEVEL DECODE, both sides, independently re-derived (not diffed)")
    old_reg1 = A_CMP_PRE[0] & 0x1F
    new_reg1 = A_CMP_POST[0] & 0x1F
    check(old_reg1 == 12 and new_reg1 == 0,
          f"  cmp: byte0 {A_CMP_PRE[0]:02X}->{A_CMP_POST[0]:02X}, reg1 field {old_reg1}(r12) -> "
          f"{new_reg1}(r0); byte1 {A_CMP_PRE[1]:02X} unchanged (reg2 = r9)")
    old_cc, new_cc = A_SETF_PRE[0] & 0x0F, A_SETF_POST[0] & 0x0F
    check(old_cc == 0x9 and new_cc == 0xA,
          f"  setf: byte0 {A_SETF_PRE[0]:02X}->{A_SETF_POST[0]:02X}, cond nibble "
          f"0x{old_cc:X}(NC=unsigned>=) -> 0x{new_cc:X}(NE=not-equal)")
    hw2_old = struct.unpack_from("<H", A_ARMSRC_PRE, 2)[0]
    hw2_new = struct.unpack_from("<H", A_ARMSRC_POST, 2)[0]
    disp_old = struct.unpack_from("<h", struct.pack("<H", hw2_old & 0xFFFE))[0]
    disp_new = struct.unpack_from("<h", struct.pack("<H", hw2_new & 0xFFFE))[0]
    check(A_ARMSRC_PRE[:2] == A_ARMSRC_POST[:2],
          f"  ld.bu: byte0/1 {A_ARMSRC_PRE[:2].hex()} unchanged -- same opcode family (ld.bu/gp), "
          f"same dest reg (r9), same displacement PARITY (bit0 unchanged)")
    check(disp_old == -0x671A and disp_new == -0x6806,
          f"  ld.bu: displacement (masked hw2, sign-extended) {disp_old} (-0x671A, the reversal "
          f"counter) -> {disp_new} (-0x6806, this kit's own established LKAS-engagement-flag cell)")

    # ==============================================================================================
    code = bytearray(base)
    attributed = set()

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
        print(f"    0x{addr:05X}  {len(post):2d} B   {label}")

    print(f"\n  [4] THE EDITS -- Part A (four sites) + Part B (the cave)")
    apply(A_CAL_ADDR, A_CAL_PRE, A_CAL_POST,
          f"EDIT 1  ARM CAL       0xC649B  0 -> 1  (arms Honda's dormant biquad)")
    apply(A_ARMSRC_ADDR, A_ARMSRC_PRE, A_ARMSRC_POST,
          f"EDIT 2  ARM SOURCE    0x35A06  ld.bu -0x671a[gp],r9 -> ld.bu -0x6806[gp],r9")
    apply(A_CMP_ADDR, A_CMP_PRE, A_CMP_POST,
          f"EDIT 3  COMPARE       0x35A12  cmp r12,r9 -> cmp r0,r9")
    apply(A_SETF_ADDR, A_SETF_PRE, A_SETF_POST,
          f"EDIT 4  CONDITION     0x35A18  setfnc r6 -> setfne r6")
    # cave GROWS (154 -> 164): "pre" must cover the full 164 B this edit writes, not just V102's
    # 154 real bytes -- the extra 10 B are read directly from the base image's virgin 0xFF tail
    # (already asserted virgin in [5c] below) so the apply() assertion genuinely checks them too.
    cave_pre = rd(base, CAVE_BASE, V103_CAVE_LEN)                                   # 154 B real + 10 B 0xFF
    cave_post = PAYLOAD                                                            # 164 B, no padding needed
    apply(CAVE_BASE, cave_pre, cave_post,
          f"EDIT 5  CAVE           0x{CAVE_BASE:05X}  {V102_CAVE_LEN} -> {V103_CAVE_LEN} B "
          f"(b7/b6/b5/b4 unchanged, b3 -> D_state sign -- the new measurand and identity)")

    # ==============================================================================================
    print("\n  [5] POST-EDIT VERIFICATION -- read back out of the image being built")
    check(rd(code, A_CAL_ADDR, 1) == A_CAL_POST, "arm cal reads 1")
    check(rd(code, A_ARMSRC_ADDR, 4) == A_ARMSRC_POST, "arm source reads -0x6806[gp]")
    check(rd(code, A_CMP_ADDR, 2) == A_CMP_POST, "compare reads cmp r0,r9")
    check(rd(code, A_SETF_ADDR, 4) == A_SETF_POST, "condition reads setfne")

    print("\n  [5b] GATE 1 -- the biquad's own RAM is UNTOUCHED by these edits")
    biquad_span = bytes.fromhex("2437") + struct.pack("<h", -BIQUAD_X1)   # ld.h -0x3818[gp],r? twin
    check(rd(code, 0x35A2C, 4) == rd(base, 0x35A2C, 4)
          and rd(code, 0x35A64, 4) == rd(base, 0x35A64, 4)
          and rd(code, 0x35A4C, 4) == rd(base, 0x35A4C, 4)
          and rd(code, 0x35A6A, 4) == rd(base, 0x35A6A, 4),
          f"the four gp-0x{BIQUAD_X1:04X}/gp-0x{BIQUAD_X2:04X} load/store instructions "
          f"(0x35A2C, 0x35A4C, 0x35A64, 0x35A6A) are byte-identical to the base -- "
          f"Part A edits the ARM condition only, never the filter's own state access")
    check(not any(a in attributed for a in (0x35A2C, 0x35A2D, 0x35A4C, 0x35A4D, 0x35A64, 0x35A65,
                                             0x35A6A, 0x35A6B)),
          "none of the four biquad state instructions are in this build's attributed-byte set")

    print("\n  [5c] PART B -- PRE-EDIT: hook unchanged, cave currently V102's 154 B")
    V102_CAVE = rd(base, CAVE_BASE, V102_CAVE_LEN)
    check(all(b == 0xFF for b in base[CAVE_BASE + V102_CAVE_LEN:CAVE_FREE_END]),
          f"V102's cave tail is virgin 0xFF to 0x{CAVE_FREE_END:05X}")
    check(rd(base, HOOK_ADDR, 4) == HOOK_BYTES, f"hook 0x{HOOK_ADDR:05X} unchanged")

    print("\n  [5d] PART B -- LINEAR DECODE of the new payload, every byte on an instruction boundary")
    dec_ins = decode_cave(PAYLOAD, "V103")
    bounds = {o for o, _, _ in dec_ins}
    branches = [(o, o + BRANCH_SPAN) for o, _, m in dec_ins if m == BRANCH_MNEM]
    check(sum(ln for _, ln, _ in dec_ins) == len(PAYLOAD) == V103_CAVE_LEN,
          f"{len(PAYLOAD)} B decode to {len(dec_ins)} instructions, full coverage, "
          f"matches declared V103_CAVE_LEN")
    check(all(hi in bounds for _, hi in branches), "all `bge +4` targets land on instruction boundaries")
    check(bytes.fromhex("ba05") not in PAYLOAD and bytes.fromhex("b205") not in PAYLOAD,
          "the payload contains NO `bne`/`be` -- every branch is `ae05` = signed GE")
    check(dec_ins[-1][2] == "jmp [lp]" and dec_ins[-2][2] == "movea disp,gp,r6",
          "stream ends movea -0x1518,gp,r6 / jmp [lp] -- the hooked instruction is restored")

    print("\n  [5e] PART B -- b5/BYTE7/RET are BYTE-IDENTICAL to V102's; PASS1's MASK moves; PASS3 grows")
    check(PASS2 == V102_CAVE[0x2E:0x5C],
          "PASS 2 (b5, friction-vs-inertia) byte-identical to V102's ORIGINAL -- unedited, not sacrificed")
    check(BYTE7 == V102_CAVE[0x82:0x94], "byte7 identity block byte-identical to V102's (and V101's)")
    check(RET == V102_CAVE[0x94:0x9A], "return sequence byte-identical to V102's")
    check(PASS1[:0x26] == V102_CAVE[0x00:0x26] and PASS1[0x28:] == V102_CAVE[0x28:0x2E],
          "PASS 1's comparator logic AND the andi opcode (everything except the mask immediate "
          "byte at +0x26) are byte-identical to V102's")
    check(PASS1[0x26:0x28] == bytes.fromhex("bf00") and V102_CAVE[0x26:0x28] == bytes.fromhex("b700"),
          "PASS 1's mask immediate moves 0xB7 (clears bits 6,3) -> 0xBF (clears bit 6 ONLY) -- "
          "b3 is no longer forced here, PASS 3 owns it exclusively now")
    check(len(PASS3) == 48 and len(V102_CAVE[0x5C:0x82]) == 38,
          "PASS 3 grows 38 B (b7+b4) -> 48 B (b7+b4+b3) -- +10 B, one new sign-check sequence")

    print("\n  [5f] PART B -- b3's NEW semantics, field-by-field, and the ld.w derivation")
    # PASS 3 layout: 0x00 mov / 0x02 ld.h(b7 src) / 0x06 cmp / 0x08 bge / 0x0A add(b7) /
    #                0x0C ld.h(b4 src) / 0x10 cmp / 0x12 bge / 0x14 add(b4) / 0x16 shl /
    #                0x18 ld.w(b3 src, NEW) / 0x1C cmp / 0x1E bge / 0x20 add(b3, NEW) /
    #                0x22 ld.bu / 0x26 andi / 0x2A or / 0x2C st.b
    check(PASS3[0x16:0x18] == bytes.fromhex("c43a"),
          "PASS 3: shl 0x4,r7 places b7/b4 BEFORE D_state's load -- confirms b3 is added post-shift")
    check(PASS3[0x18:0x1C] == DSTATE_LDW_BYTES_R6,
          f"b3 loads gp-0x{SRC_DSTATE:04X} (D_state) via {DSTATE_LDW_BYTES_R6.hex()} = "
          f"ld.w -0x{SRC_DSTATE:X}[gp],r6 -- Ghidra-verified, not hand-decoded")
    check(PASS3[0x1C:0x1E] == bytes.fromhex("6032") and PASS3[0x1E:0x20] == bytes.fromhex("ae05"),
          "b3: cmp 0x0,r6 / bge +4 -- skips the add iff D_state >= 0 (same polarity idiom as b4/b7)")
    check(PASS3[0x20:0x22] == bytes.fromhex("483a"),
          "b3: add 0x8,r7 -- DIRECT bit3 contribution (no further shift), the EXACT SAME 2-byte "
          "sequence PASS 3 already uses for b7's pre-shift value (0x8 pre-shift -> bit7 after shl4; "
          "the identical 0x8 used AFTER the shl IS bit3 itself) -- one proven pattern, reused, not "
          "a new encoding")
    check(PASS3[0x28:0x2A] == bytes.fromhex("6700"),
          "PASS 3's final mask is 0x67 (clears bits 7,4,3) -- matches MASK_PASS3")

    print("\n  [5g] PART B -- MASK COVERAGE, the bit-partition after the final map")
    cleared = set()
    for lbl, m, bits in (("PASS1 b6", MASK_PASS1, {6}), ("PASS2 b5 (unedited)", MASK_PASS2, {5}),
                         ("PASS3 b7+b4+b3 (b3 NEW)", MASK_PASS3, {7, 4, 3})):
        got = {b for b in range(8) if not (m >> b) & 1}
        check(got == bits and (m & 0x07) == 0x07,
              f"  {lbl:<28} andi 0x{m:02X} clears {sorted(bits, reverse=True)}, preserves Honda 2:0")
        check(not (cleared & bits), f"  {lbl:<28} touches no bit an earlier pass already wrote")
        cleared |= bits
    check(cleared == {7, 6, 5, 4, 3}, f"passes cover exactly byte4 bits 7:3 = {sorted(cleared, reverse=True)}")

    print("\n  [5h] PART B -- GATE 1, RAM ownership.  Same store SET as V102, zero new RAM claim")
    n_b4 = sum(1 for i in range(len(PAYLOAD) - 3) if PAYLOAD[i:i + 4] == ST_B4_INSN)
    n_b7 = sum(1 for i in range(len(PAYLOAD) - 3) if PAYLOAD[i:i + 4] == ST_B7_INSN)
    check((n_b4, n_b7) == (3, 1),
          f"stores: {n_b4}x gp-0x1514 + {n_b7}x gp-0x1511 -- SAME as V102, no new RAM claimed")
    check(not (CAVE_BASE <= DSTATE_STW_ADDR < CAVE_BASE + V103_CAVE_LEN),
          f"D_state's sole writer (0x{DSTATE_STW_ADDR:05X}, Honda's own FUN_0003a382) is nowhere "
          f"near this cave -- b3 reads it, never writes it")
    check(code[0xC64FA] == 5,
          "0xC64FA (the shared oscillation-detector ceil Part A deliberately avoids) still 5 -- "
          "Part B does not touch it either, confirmed directly here in addition to the FROZEN dict")
    regs = set()
    for _, _, m in dec_ins:
        regs |= {t.strip("[],") for t in m.replace(",", " ").split()
                 if t.strip("[],").startswith(("r", "gp", "lp"))}
    check(regs <= {"r0", "r6", "r7", "gp", "lp"},
          f"every register the payload names is in {{r0, r6, r7, gp, lp}} -- got {sorted(regs)}")

    print("\n  [6] FROZEN + the friction dose family, AFTER the edit")
    assert_frozen(code, "built image (pre-CRC)")
    assert_friction_family(code, "built image (pre-CRC)")

    print("\n  [6b] Everything outside Part A's four sites and the cave is bit-for-bit V102's")
    diffs = [i for i in range(START, END) if code[i] != base[i]
             and i not in attributed]
    check(not diffs, f"ZERO bytes differ from the V102 base outside Part A's four sites and the cave "
                     f"-- the control law is otherwise UNCHANGED from V102")

    # ==============================================================================================
    eme_audit(code, base, stock, "built image, pre-CRC")

    # ==============================================================================================
    print("\n  [7] CRC RECOMPUTATION -- reusing the existing owning_block/walk_all_blocks machinery")
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    check(len(blocks) == 2,
          f"Part A + the cave span exactly {len(blocks)} CRC block(s) "
          f"(expected 2: the main app block 0xC4FFC covers Part A's 3 code edits AND the cave -- "
          f"same block, since the cave sits inside [0x13000,0xC4FFC) -- and the 0xC6xxx cal block "
          f"0xC6FFC covers Part A's arm byte) -- {[hex(b[1]) for b in blocks]}")
    for blk in blocks:
        check(not any(blk[1] <= a < blk[1] + 4 for a in touched),
              f"no edit on trailer 0x{blk[1]:06X}")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        n_in = len([a for a in touched if blk[0] <= a < blk[1]])
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X})  0x{old_crc:08X} -> 0x{new_crc:08X}  "
              f"{n_in} of {len(touched)} edited bytes  (trailer 0x{blk[1]:06X})")
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
        sattr |= {i for i in sruns if lo <= i < hi}
    sun = sorted(set(sruns) - sattr - scrc)
    print(f"       {len(sruns)} bytes differ from STOCK total, {len(sattr)} attributed, "
          f"{len(set(sruns) & scrc)} CRC")
    check(not sun, "ZERO unattributed bytes vs stock"
                   + ("" if not sun else "  -- " + str([hex(x) for x in sun[:16]])))

    print("\n  [8b] FULL BYTE DIFF vs THE V102 BASE -- what THIS build changed")
    bruns = [i for i in range(START, END) if code[i] != base[i]]
    runs = []
    for i in bruns:
        if runs and i == runs[-1][1]:
            runs[-1][1] = i + 1
        else:
            runs.append([i, i + 1])
    named = [(A_CAL_ADDR, 1, "PART A: arm cal"), (A_ARMSRC_ADDR, 4, "PART A: arm source"),
             (A_CMP_ADDR, 2, "PART A: compare"), (A_SETF_ADDR, 4, "PART A: condition"),
             (CAVE_BASE, V103_CAVE_LEN, "PART B: cave (b3 new -- D_state sign)")]
    unnamed = []
    for lo, hi in runs:
        span = set(range(lo, hi))
        if (lo & 0xFFF) >= 0xFFC:
            tag = "CRC trailer"
        else:
            hits = [w for a, n, w in named if span & set(range(a, a + n))]
            tag = " + ".join(hits) if hits else "?? UNATTRIBUTED"
            if not hits or not span <= (attributed | {a for a_, n_, _ in named
                                                      for a in range(a_, a_ + n_)}):
                unnamed.append((lo, hi))
        print(f"       0x{lo:05X}..0x{hi - 1:05X}  {hi - lo:4d} B   {tag}")
    check(not unnamed,
          f"every one of the {len(runs)} changed runs vs V102 lies inside a named edit or a "
          f"CRC trailer" + ("" if not unnamed else f"  -- STRAY: {[(hex(a), hex(b)) for a, b in unnamed]}"))
    print(f"       ({len(runs)} changed runs vs V102 total: Part A's 4 sites + the cave's changed "
          f"span + 2 CRC trailers -- count not asserted exact, byte-run boundaries inside the cave "
          f"depend on incidental old/new content matches)")

    # ==============================================================================================
    print("\n  [9] .rwd ENCODE + READBACK (pipeline check -- WRITE_MODE gates whether files land)")
    source_rwd = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 OK")
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V103 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to built image")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  DRY RUN -- NOTHING WRITTEN. Both parts are built and verified and the identity")
        print("  question is RULED (see docstring). Re-run with ACCORD_V103_WRITE=rwd to cut.")
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

            # ======================================================================================
            # EVERYTHING BELOW READS THE SHIPPED FILE BACK OFF DISK.  No script claims.
            # ======================================================================================
            print("\n  [10] FROM-DISK VERIFICATION -- the shipped .rwd, decoded")
            shipped = Path(OUT).read_bytes()
            check(hashlib.sha256(shipped).hexdigest() == rwd_sha, "shipped .rwd sha256 OK")
            FF.assert_x31_checksum(shipped, "V103 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            check(bytes(sd) == bytes(code), "shipped .rwd decodes to the built image")
            check(walk_all_blocks(bytes(sd)) == 0, "shipped CRC 50/50")
            disk_img = bytearray(Path(BIN_OUT).read_bytes())
            check(hashlib.sha256(bytes(disk_img)).hexdigest() == img_sha,
                  "plain image re-read from disk, sha256 OK")
            check(bytes(disk_img) == bytes(sd), "plain image on disk == decoded shipped .rwd")
            check(disk_img[A_CAL_ADDR] == 1 and rd(disk_img, A_ARMSRC_ADDR, 4) == A_ARMSRC_POST
                  and rd(disk_img, A_CMP_ADDR, 2) == A_CMP_POST
                  and rd(disk_img, A_SETF_ADDR, 4) == A_SETF_POST,
                  "shipped: Part A's four edits present, re-read from disk")
            check(rd(disk_img, CAVE_BASE, V103_CAVE_LEN) == PAYLOAD,
                  f"shipped: {V103_CAVE_LEN}-byte cave payload byte-identical, re-read from disk")
            check(disk_img[0xC64FA] == 5, "shipped: 0xC64FA still 5")
            assert_frozen(disk_img, "SHIPPED image")
            assert_friction_family(disk_img, "SHIPPED image")
            eme_audit(disk_img, base, stock, "SHIPPED image, from disk")

    print("\n" + "=" * 102)
    print(f"  V103 [{TOKEN}]")
    print(f"    {_checks[1]}/{_checks[0]} assertions PASSED")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  ({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print(f"  PART A: arms Honda's dormant biquad in FUN_000352b4, engaged-only "
          f"(gp-0x6806 != 0), zero new RAM, zero new code region.")
    print(f"  PART B: comparator probe -- b7/b6/b5/b4 byte-identical to V102, b5 NOT sacrificed. "
          f"b3 -> sign(gp-0x3680) D_state -- the new measurand AND the identity mechanism. "
          f"Cave 154 -> 164 B (+10 B, one new sign-check sequence).")
    print(f"  CRC: two trailers, 0xC4FFC (Part A code + the cave) and 0xC6FFC (Part A's arm cal).")
    print(f"  IDENTITY: no single-frame witness -- both axes exhausted (byte7[7:6] all 4 codes "
          f"spent; b3's 2 states both claimed by V101/V102). RULED: b3 MUST VARY -- V101 pins it "
          f"1, V102 pins it 0, no predecessor has a toggling b3, so route identity for V103 comes "
          f"from observing b3 take both values (plus the flash record), not from a constant bit. "
          f"A constant b3 on this build means it is not V103, or the rung is dead.")
    print(f"  EXPECTED PATTERN (for the scorer): b7 duty ~0.27 rising 0.148->0.417 with wheel rate "
          f"* b6 duty 0.8991 rising 0.836->0.981->0.992 * b5 duty 0.2481 * b4 duty 0.4091 * "
          f"b3 MUST VARY.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
