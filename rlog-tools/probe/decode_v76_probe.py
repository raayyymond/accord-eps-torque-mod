#!/usr/bin/env python3
"""probe/decode_v76_probe.py -- read V76's probe: THE GATE, its MASKING RISK, and the r24 arm ladder.

🛑🛑 STATUS: V76 is **BUILT, UNFLASHED**, and it is a **SIBLING** of V75, not a successor. Both
branch from the same V74 base; the operator chooses ONE to fly. If you are running this decoder on a
log, someone made a flight decision -- confirm the .rwd filename in `RWD_NAME` below before reading a
single number out of it.

WHAT V76 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
V76 = V74's damper, byte for byte, **plus V67/V68's rate-lane configuration**, which is the best
grind-#1 result in this kit's history (median `e_18-22` = 109) and has been OFF THE CAR since V68.
Two cells, and they are MODE-PROOF -- reached by plain `ld.hu <disp>[tp]` scalars with no `mode*4`
index, which is exactly why RULE 7 voided V69/V70 but not V67/V68:

  LEVER 1  `0x3AA96`  `0xC5 -> 0xFB`  -- repoints `ld.bu -0x683c[gp],r15` @0x3AA94 to
           `ld.bu -0x6806[gp],r15`. ONE in-place branch-operand byte. `gp-0x683c` is a DEAD cell
           (1 reader, 0 writers) so V72..V75 run UNGATED; `gp-0x6806` is the LKAS-applying flag,
           validated on-car by V57's probe at 99.983% agreement with `carControl.latActive`.
           ★ The crux, Ghidra-read: `0x3AAA6 cmp r0,r15` ; `0x3AAA8 setfne lp` -- and BOTH selector
           ladders branch on `lp`, so repointing the LOAD is sufficient.
  LEVER 2  `0xC6446`  `512 -> 5244`   -- r24's gate-active arm.
  ⊕ `0xC6444` already holds 512 (V67/V68's value) on every image in this kit. V76 ASSERTS it and
    never writes it.

⚠ THIS IS A TWO-LANE LEVER AND ALWAYS WAS. Firing the gate raises r24 to `5244 / 3072 = 1.70703x`
  the gain_B creep LERP **and simultaneously cuts r26 to `512 / 3072 = /6.00 EXACTLY`** against
  gain_A's own creep LERP. Net vs stock = `(5244 + 512a) / (3072 + 3072a)` with `a = gp-0x69a4/1024`;
  parity at `a = 0.848`. V76 reproduces the CONFIGURATION -- it does not claim to know which lane did
  the work, and the corpus cannot separate them (see BUILD-LINEAGE, "TWO SELECTORS, ONE GATE").

THE r24 PRIORITY LADDER -- read it TOP-DOWN, it is what this probe measures
--------------------------------------------------------------------------
    bit5 set  ->  0xC6442 = 1024   🛑 **BELOW** the stock creep LERP of 3072, and the gate's r26 /6
                                   cut still applies ⇒ **V76 IS WORSE THAN STOCK IN THIS STATE.**
    else bit6 ->  0xC6446 = 5244   ★★★★ the lever. r24 x1.707, r26 /6.00.
    else bit4 ->  0xC6440 = 2048   the third arm (r26 side: 0xC643E = 1536)
    else      ->  the mode*4-indexed gain_B LERP -- stock behaviour
  🛑 The mask OUTRANKS the gate. That is why `bit5` is on this probe at all, and why its duty is the
  first number to read: a build that spends its engaged time in the masked state is not the lever
  anyone specified.

THE FIVE-BIT FIELD, CAN 0x14A byte 4
--------------------------------------
    bit7  (gp-0x6bd0 != 0)   ★ THE CROSS-BUILD ANCHOR. Same cell, same test, same bit position as
                               V74 and V75, so the three builds' duty cycles compare directly. It is
                               the base-assist damper's own output and belongs to the V74 lever set
                               that V76 carries UNCHANGED -- do not re-credit it to this build.
    bit6  (gp-0x6806 != 0)   ★★★★ **THE GATE.** If this is CONSTANT the build is INERT and nothing
                               else in the log is interpretable.
    bit5  (gp-0x671d != 0)   🛑 **THE MASKING RISK**, and it OUTRANKS the arm.
    bit4  (gp-0x671a >= 5)   the third arm's index vs the BYTE cal 0xC64FA = 5.
                               ⚠ `>=`, not `>`. Reading 0xC64FA as u16 gives 517 -- the V63 trap.
    bit3  🛑 **STRUCTURALLY ZERO.** No instruction in V76's cave sets it. See below.
    bits 2:0  live STEER_SENSOR_STATUS, preserved.

🛑 WHY THERE ARE FOUR RUNGS AND NOT FIVE. The spec asked for a fifth, `bit3 = (gp-0x6ac2 != 0)`.
It does not fit and the arithmetic is not close. V75 fits five bits because three of them are
`cmp imm5` rungs sharing ONE load (6 B each); V76's bits read FOUR DIFFERENT cells, so every rung is
`load(4) + cmp(2) + branch(2) + add(2) = 10 B` and the cave would need **74 B against the 68 B proven
extent**. `gp-0x671d` (0xFEDF18E3) and `gp-0x671a` (0xFEDF18E6) sit in different 4-aligned words so
no shared load exists; `andi 0x7` has no 2-byte equivalent with only r6/r7 provably dead. V76 ships
FOUR rungs in 64 B plus 4 B of zero pad -- the same 68 B region, V74's own idiom (46 B code + 22 B
pad). **`gp-0x6ac2` is the DAMPER CEILING's index, orthogonal to the rate lane, and V75 carries that
identical rung** -- so whichever sibling flies, the kit does not lose the measurement.

★ BIT3 IS THE BUILD-IDENTITY GUARD, and it is structural in ONE direction. V74's on-car payload was
`0x28`/`0xA8` (state 5 ⇒ bits 6:3 = 0b0101 ⇒ **bit3 SET on every frame**), so ONE frame rejects a V74
log. V75's bit3 is the back-drive gate and its four damper bits obey `bit4 => bit5 => bit6 => bit7`;
V76's four bits are INDEPENDENT, so `0x10 0x20 0x30 0x40 0x50 0x60 0x70 0x90 0xA0 0xB0 0xD0` are
legal here and ILLEGAL there. ⚠ **The converse does not hold**: a V75 log whose back-drive never
fired carries only `{0x00, 0x80, 0xC0, 0xE0, 0xF0}`, every one of which is legal here too -- so a
quiet V75 log CANNOT be excluded from the payload alone. That case is reported as UNPOWERED, never as
a pass, and the FILENAME remains the pre-drive discriminator.

Usage:  python probe/decode_v76_probe.py <rlog-or-segment-dir> [...]
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
import os
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decode_v67_gate import collect                                        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES                                 # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v76_tva.assert_decoder_matches() FAILS THE BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "003a24373094e031a205483a8437fb97e031a205443aa437e398e031a205423a8437e7986532a605413ac43a8437edeac636070007314437ecea2436e8ea7f0000000000"  # noqa: E501
#
#   0xC4B34  003a      mov   0x0,r7           r7 = 0                       (real instance @0x34114)
#   0xC4B36  24373094  ld.h  -0x6bd0[gp],r6   ★ THE DAMPER'S OWN OUTPUT. **SIGNED** -- op field
#                                             0x39. Its one-bit twin `st.h` (0x3B) is a REAL
#                                             instruction at 0x34730 writing this very cell.
#   0xC4B3A  e031      cmp   r0,r6            Z set <=> the output is exactly 0
#   0xC4B3C  a205      be    +4               skip the setter               (real `be +4` @0x2998)
#   0xC4B3E  483a      add   0x8,r7           bit7 = (gp-0x6bd0 != 0)   THE CROSS-BUILD ANCHOR
#   0xC4B40  8437fb97  ld.bu -0x6806[gp],r6   ★★★★ THE GATE -- the same cell the repointed
#                                             instruction @0x3AA94 now reads. Displacement 0x97FA is
#                                             **EVEN**, so the opcode field is 0x3C. (EXACT real
#                                             instance @0x2A8C0)
#   0xC4B44  e031      cmp   r0,r6
#   0xC4B46  a205      be    +4
#   0xC4B48  443a      add   0x4,r7           bit6 = (gp-0x6806 != 0)
#   0xC4B4A  a437e398  ld.bu -0x671d[gp],r6   🛑 THE MASK. Displacement 0x98E3 is **ODD**, and
#                                             `ld.bu` carries the displacement's bit 0 in the
#                                             OPCODE FIELD (0x3D, not 0x3C) -- NOT in hw2. An
#                                             encoder assuming one parity would silently address
#                                             the NEIGHBOURING cell with every other field perfect.
#                                             ⊕ EXACT real instance @0x3AB98 -- and that instance is
#                                             the FIRMWARE'S OWN mask read inside FUN_0003aa2c.
#   0xC4B4E  e031      cmp   r0,r6
#   0xC4B50  a205      be    +4
#   0xC4B52  423a      add   0x2,r7           bit5 = (gp-0x671d != 0)   THE MASKING RISK
#   0xC4B54  8437e798  ld.bu -0x671a[gp],r6   the third arm's index. Displacement 0x98E6 EVEN -> 0x3C.
#                                             (hw1 donor @0x55AD4, hw2 donor @0x3AA70)
#   0xC4B58  6532      cmp   0x5,r6           🛑 the **BYTE** cal 0xC64FA = 5. Its u16 is 517 -- the
#                                             V63 trap. The cal is on the build's keep-list so this
#                                             hard-coded imm5 cannot drift.  (real @0x7380)
#   0xC4B5A  a605      blt   +4               `blt`, NOT `bge`: the test is `>=`, so the SKIP is the
#                                             `<` case.                     (real @0x290A8)
#   0xC4B5C  413a      add   0x1,r7           bit4 = (gp-0x671a >= 5)
#   0xC4B5E  c43a      shl   0x4,r7           the 4-bit field -> bits 7:4.  (real @0x1C1C2)
#                                             🛑 NOTHING is added after this shift, which is why
#                                             BIT3 IS STRUCTURALLY ZERO.
#   0xC4B60  8437edea  ld.bu -0x1514[gp],r6   CAN-330 payload byte4 (r6 is free: the field is in r7)
#   0xC4B64  c6360700  andi  0x7,r6,r6        preserve live STEER_SENSOR_STATUS bits 2:0
#   0xC4B68  0731      or    r7,r6            THE MERGE. 🛑 **NOT** `or r6,r7` (0639) -- same
#                                             opcode, register fields SWAPPED, and both are real
#                                             instructions in this image.
#   0xC4B6A  4437ecea  st.b  r6,-0x1514[gp]   THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B6E  2436e8ea  movea -0x1518,gp,r6    the displaced hook instruction, re-executed LAST
#   0xC4B72  7f00      jmp   [lp]             -> 0x55C12, which is `mov 0x8,r7` (083a) ⇒ r7 is
#                                             PROVABLY DEAD across the hook
#   0xC4B74  00000000  <4 B zero pad>         closes the 68 B region. V74's own cave is 46 B of code
#                                             + 22 B of pad in this same region.

BIT_DAMP_NZ = 0x80            # bit7   the damper is non-zero      ★ THE CROSS-BUILD ANCHOR
BIT_GATE = 0x40               # bit6   gp-0x6806 != 0              ★★★★ THE GATE
BIT_MASK = 0x20               # bit5   gp-0x671d != 0              🛑 THE MASKING RISK
BIT_ARM3 = 0x10               # bit4   gp-0x671a >= 5              the third arm
BIT_UNUSED = 0x08             # bit3   🛑 STRUCTURALLY ZERO -- emitted by no instruction
PROBE_MASK = 0xF0
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

ARM_THRESHOLD = 5             # the BYTE cal 0xC64FA. ⚠ its u16 reads 517 -- the V63 trap.
# ★ The complete reachable alphabet of bits 7:4. All SIXTEEN, because the four bits are INDEPENDENT
# -- there is no thermometer invariant here. builds/v50_v79/build_v76_tva.py asserts this tuple against its own
# exhaustive wire model. 🛑 A weaker structural guard than V75's, and it is stated as such.
LEGAL_PAYLOADS = (0x00, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70,
                  0x80, 0x90, 0xA0, 0xB0, 0xC0, 0xD0, 0xE0, 0xF0)
# 🛑 Payloads that PROVE a foreign log: every one has BIT3 set, and V76 emits no instruction for it.
FOREIGN_PAYLOADS = {0x08: "V75 (back-drive alone) or V74 (state 8/9, damper zero)",
                    0x28: "V74 (state 5, damper zero)", 0xA8: "V74 (state 5, damper non-zero)",
                    0x88: "V75 (damper non-zero + back-drive)",
                    0xC8: "V75 (thermometer >=128 + back-drive)",
                    0xE8: "V75 (thermometer >=288 + back-drive)",
                    0xF8: "V75 (full thermometer + back-drive)",
                    0x18: "V74 (state 3, damper zero)", 0x38: "V74 (state 7, damper zero)",
                    0x48: "V74 (state 9, damper zero)", 0x58: "V74 (state 11, damper zero)"}
# ⚠ The payloads V75 can ALSO produce. A log confined to these cannot be separated from a quiet V75.
V75_QUIET_ALPHABET = (0x00, 0x80, 0xC0, 0xE0, 0xF0)
# ★ The payloads that are legal here and IMPOSSIBLE on V75 (they break bit4=>bit5=>bit6=>bit7) and on
# V74 (whose bits 6:3 are a 4-bit state field, so bit3 tracks the state's parity, not these).
V76_ONLY_PAYLOADS = (0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x90, 0xA0, 0xB0, 0xD0)

DAMP_DISP = 0x6BD0            # the base-assist damper output   -- SIGNED, ld.h
GATE_DISP = 0x6806            # THE GATE, the LKAS-applying flag -- ld.bu, EVEN disp -> op 0x3C
MASK_DISP = 0x671D            # the mask                        -- ld.bu, **ODD** disp -> op 0x3D
ARM3_DISP = 0x671A            # the third arm's index           -- ld.bu, EVEN disp -> op 0x3C
DEAD_DISP = 0x683C            # ⚠ the cell V72..V75's gate read: 1 reader, 0 writers, always 0

# The r24 ladder's arms, in PRIORITY ORDER. Read top-down; the FIRST match wins.
ARM_MASK_VALUE = 1024         # 0xC6442, taken when bit5 -- BELOW the stock creep LERP
ARM_GATE_VALUE = 5244         # 0xC6446, taken when bit6 and not bit5   ★ THE LEVER
ARM_THIRD_VALUE = 2048        # 0xC6440, taken when bit4 and neither above
GAIN_B_CREEP_LERP = 3072      # the mode-indexed fallback surface at creep -- the "stock" reference
# The r26 side. 🛑 There is NO mask arm on gain_A -- it is 2 arms + default, not 3.
ARM_A_GATE_VALUE = 512        # 0xC6444, taken when the gate fires   -> /6.00 EXACTLY
ARM_A_THIRD_VALUE = 1536      # 0xC643E, taken when bit4 and the gate is clear
GAIN_A_CREEP_LERP = 3072
PARITY_A = 0.848              # `a` = gp-0x69a4/1024 at which the net lands ON stock

ENGAGED_MODES = (2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33)
DISENGAGED_MODES = (0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31)
LIVE_MODE = 26                # row 11 TVCA4, e014 -- V73's on-car probe, not an inference
MANUAL_MODE = 24
GATE_LATACTIVE_AGREEMENT = 99.983     # V57's on-car measurement of gp-0x6806 vs carControl.latActive
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)

# 🛑 ONE LINE, deliberately. builds/v50_v79/build_v76_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V76-V74BASE-GATE-FB-ARM5244-gateprobe-6806-671d-671a-0x13000-0x100000.rwd"  # noqa: E501
PLAIN_IMAGE = "_v76_gate_fb_arm5244_gateprobe_plain_image.bin"
PLAIN_SHA256 = "f27e1fd8540c52c753e9513f6ab9db4599f3d65400dd400cd393b91322cd2b5e"
RWD_SHA256 = "5ea4f75825964897d6e0e18b721e4b759fe74b5bd8aea115d9dadccf4790eca9"


def arm(b4):
    """Which r24 arm each frame occupied. 0 = mask (1024), 1 = gate (5244), 2 = third (2048),
    3 = the mode-indexed LERP. 🛑 The ladder is a PRIORITY chain, so the order here is the code's."""
    out = np.full(len(b4), 3, dtype=np.int8)
    third = (b4 & BIT_ARM3) != 0
    gate = (b4 & BIT_GATE) != 0
    mask = (b4 & BIT_MASK) != 0
    out[third] = 2
    out[gate & ~mask] = 1
    out[mask] = 0
    return out


ARM_BANDS = (f"MASK   r24 = {ARM_MASK_VALUE}  🛑 BELOW the stock LERP of {GAIN_B_CREEP_LERP}",
             f"GATE   r24 = {ARM_GATE_VALUE}  ★ THE LEVER (and r26 -> {ARM_A_GATE_VALUE}, /6.00)",
             f"THIRD  r24 = {ARM_THIRD_VALUE}  (r26 -> {ARM_A_THIRD_VALUE})",
             f"LERP   r24 = the mode-indexed surface  (stock behaviour)")


def identify(b4, engaged=None, speed_ms=None, override=False):
    """Is this a V76 payload? 🛑 THE GUARD CAN REJECT STRUCTURALLY, BUT IT CANNOT CONFIRM.

    T1 [DECISIVE, STRUCTURAL] **BIT3.** V76's cave adds nothing after the `shl 0x4,r7`, so bit3 is
       0 on every frame it produces. V74's field is a 4-bit STATE at bits 6:3 (its on-car state was
       a constant 5 ⇒ bit3 set on every frame) and V75's bit3 is the back-drive gate. Any frame with
       bit3 set proves the bytes did not come from this cave.
    T2 [DECISIVE, STRUCTURAL] **THE V74 STATE SIGNATURE.** V74 spends bits 6:3 on `gp-0x67fa`, whose
       complete value set is {1,3,4,5,6,7,8,9,10,11}. If bits 6:3 are CONSTANT across the whole drive
       AND that constant is in the state set, the log is V74-shaped -- V76's bits 6:4 are three
       independent live signals and cannot all be frozen while bit7 moves.
    T3 [UNPOWERED, and it is reported as such] **SEPARATION FROM V75.** A V75 log whose back-drive
       never fired carries only {0x00, 0x80, 0xC0, 0xE0, 0xF0}, all of which are legal here. If this
       log contains no V76-only payload, the two builds are NOT separable from the bytes.

    🛑 AN UNPOWERED CHECK IS REPORTED AS **UNPOWERED**, NEVER AS A PASS. That distinction is the
    whole lesson of V64/V68's five uninterpretable nulls.
    """
    decisive, corroborating, unpowered = [], [], []
    field = b4 & (PROBE_MASK | BIT_UNUSED)
    seen = Counter(int(f) for f in field)
    nz = (b4 & BIT_DAMP_NZ) != 0

    # ---- T1: bit3 -- STRUCTURAL, needs no covariate ----------------------------------------------
    bad3 = {p: n for p, n in seen.items() if p & BIT_UNUSED}
    if bad3:
        who = {hex(p): FOREIGN_PAYLOADS.get(p, "unknown schema") for p in bad3}
        decisive.append(
            f"T1 BIT3: {sum(bad3.values())} frame(s) carry bit3 SET -- {[(hex(p), n) for p, n in bad3.items()]}. "
            f"Attribution: {who}. V76's cave adds NOTHING after the `shl 0x4,r7`, so bit3 is 0 by "
            "construction. These bytes did not come from V76.")
    else:
        corroborating.append(f"T1 passes: bit3 is CLEAR on all {len(b4)} frames "
                             f"(payloads {sorted(hex(p) for p in seen)})")

    # ---- T2: the V74 constant-state signature ------------------------------------------------------
    mid = {int(x) for x in ((b4 & 0x78) >> 3)}          # bits 6:3, V74's state field
    if len(mid) == 1 and next(iter(mid)) in (1, 3, 4, 5, 6, 7, 8, 9, 10, 11) and nz.any() and \
            not nz.all():
        s = next(iter(mid))
        decisive.append(
            f"T2 V74 STATE SIGNATURE: bits 6:3 are CONSTANT at {s} across all {len(b4)} frames while "
            "bit7 moves. On V76 those three bits are the gate, the mask and the arm index -- three "
            "independent live signals -- and cannot all be frozen. This is V74's `gp-0x67fa` field.")
    else:
        corroborating.append(f"T2 passes: bits 6:3 take {len(mid)} distinct value(s) "
                             f"{sorted(mid)} -- not a frozen V74 state field")

    # ---- T3: separation from a QUIET V75 -- honestly UNPOWERED when it cannot separate ------------
    v76_only = {p: n for p, n in seen.items() if p in V76_ONLY_PAYLOADS}
    if v76_only:
        corroborating.append(
            f"T3 POSITIVE: {sum(v76_only.values())} frame(s) carry a payload that is legal on V76 and "
            f"IMPOSSIBLE on V75 -- {[(hex(p), n) for p, n in v76_only.items()]}. V75's four damper "
            "bits are a thermometer (bit4=>bit5=>bit6=>bit7); these break it.")
    elif set(seen) <= set(V75_QUIET_ALPHABET):
        unpowered.append(
            f"T3 (separation from V75): every payload seen {sorted(hex(p) for p in seen)} is inside "
            f"the alphabet a QUIET V75 (back-drive never fired) also produces. The two builds are "
            "NOT separable from these bytes -- this is UNPOWERED, NOT a pass. The FILENAME is the "
            "discriminator.")
    else:
        corroborating.append(f"T3: payload set {sorted(hex(p) for p in seen)} is outside the quiet-V75 "
                             "alphabet, but carries no V76-only value either -- weak evidence only")

    # ---- verdict ---------------------------------------------------------------------------------
    if unpowered:
        print("  ⚠ UNPOWERED CHECKS (these are NOT passes):")
        for u in unpowered:
            print(f"     · {u}")
    if decisive:
        print("\n  " + "=" * 92)
        print("  🛑🛑 REFUSING TO DECODE -- THESE BYTES ARE NOT A V76 PAYLOAD.")
        print("  " + "=" * 92)
        for w in decisive:
            print(f"     · [DECISIVE] {w}")
        for w in corroborating:
            print(f"     · [corroborating] {w}")
        print("     ⇒ Every V7x cave writes the SAME cell (gp-0x1514, CAN 0x14A byte4) in the SAME")
        print("       bit positions, so another build's log decodes here silently and produces a")
        print("       CONFIDENT WRONG answer. That has already happened once in this kit.")
        print(f"     🛑 Confirm the flashed .rwd is {RWD_NAME}")
        print("     Re-run with --i-confirm-v76 to override AFTER checking the filename.")
        if not override:
            return False
        print("  ⚠ --i-confirm-v76 given: proceeding under protest. Every number below is suspect.")
    elif corroborating:
        print("  ⊕ build-identity checks that ran clean:")
        for w in corroborating:
            print(f"     · {w}")
    if set(seen) == {0x00}:
        print("  🛑🛑 VOID-SHAPED: bits 7:3 are IDENTICALLY 0 across the whole drive.")
        print("     ⚠ 0x00 is a LEGAL V76 payload (damper zero, gate clear, mask clear, arm3 below")
        print("       threshold), so this does NOT prove the cave never fired. But it DOES mean the")
        print("       GATE never fired, which makes the lever INERT and every downstream number")
        print("       uninterpretable. Check the .rwd filename, then read it as a gate null.")
    print(f"  ✅ not excluded as V76: {len(seen)} distinct payload(s) "
          f"{sorted(hex(p) for p in seen)}, bit7 duty {100.0 * np.mean(nz):.3f}%")
    print("     🛑 'not excluded' is NOT 'confirmed' -- the FILENAME remains the pre-drive")
    print(f"        discriminator. Plain image SHA256 {PLAIN_SHA256}")
    return True


def report(b4, engaged, speed_ms):
    """The gate, the masking risk, and the arm ladder -- in that order of importance."""
    gate = (b4 & BIT_GATE) != 0
    mask = (b4 & BIT_MASK) != 0
    third = (b4 & BIT_ARM3) != 0
    nz = (b4 & BIT_DAMP_NZ) != 0
    a = arm(b4)
    eng = np.asarray(engaged, bool) if engaged is not None and len(engaged) == len(b4) else None

    # ---- 1. THE GATE. If this is constant, stop reading. -------------------------------------------
    print(f"\n  ★★★★ bit6 -- THE GATE (gp-0x{GATE_DISP:04X} != 0). READ THIS FIRST:")
    print(f"     duty {100.0 * gate.mean():.3f}% of {len(b4)} frames")
    if not gate.any():
        print("     🛑🛑 THE GATE NEVER FIRED. V76's ENTIRE lever is conditional on it, so the build")
        print("       delivered STOCK rate-lane behaviour and NOTHING below is interpretable as a")
        print("       dose result. ⚠ Before concluding the hypothesis is dead, note that V57")
        print(f"       measured this cell at {GATE_LATACTIVE_AGREEMENT}% agreement with latActive --")
        print("       so a null here is a BUILD-IDENTITY problem first and a mechanism problem")
        print("       second. Check the .rwd filename.")
    elif gate.all():
        print("     🛑 THE GATE IS CONSTANT-1. That contradicts V57's on-car measurement of this")
        print("       cell and means the arm applied in MANUAL steering too. Treat as a build-")
        print("       identity failure until the filename is confirmed.")
    elif eng is not None:
        agree = 100.0 * float((gate == eng).mean())
        print(f"     ⊕ agreement with latActive: {agree:.3f}%  "
              f"(V57 measured {GATE_LATACTIVE_AGREEMENT}% for this cell)")
        print(f"     engaged {100.0 * gate[eng].mean():.3f}%  ·  manual {100.0 * gate[~eng].mean():.3f}%")
        if agree > 95.0:
            print("     ✅ THE GATE TRACKS ENGAGEMENT ⇒ the repoint landed and the lever is LIVE on")
            print("        engaged frames only. Score the rate-lane result on ENGAGED frames.")
    else:
        print("     ⚠ no latActive in this log -- the gate's duty cannot be checked against")
        print("       engagement, which is the whole point of the repoint. UNPOWERED.")

    # ---- 2. THE MASKING RISK. It outranks the arm. -------------------------------------------------
    print(f"\n  🛑 bit5 -- THE MASKING RISK (gp-0x{MASK_DISP:04X} != 0). IT OUTRANKS THE ARM:")
    print(f"     duty {100.0 * mask.mean():.3f}% of {len(b4)} frames")
    both = gate & mask
    print(f"     ⚠ gate AND mask together: {100.0 * both.mean():.3f}% "
          f"({int(both.sum())} frames) -- 🛑 **THE BELOW-STOCK STATE**")
    if not mask.any():
        print("     ✅ the mask NEVER fired ⇒ whenever the gate was up, r24 really did take the")
        print(f"       {ARM_GATE_VALUE} arm. V64 read this cell 0 across 14,980 frames of one short")
        print("       route; this is its first test on a long mixed drive.")
    elif both.any():
        print(f"     🛑🛑 ON {int(both.sum())} FRAMES THE BUILD WAS **BELOW STOCK**: the mask pins r24")
        print(f"       to {ARM_MASK_VALUE} (vs the stock creep LERP of {GAIN_B_CREEP_LERP}) while the")
        print(f"       gate's r26 cut to {ARM_A_GATE_VALUE} (/6.00) STILL APPLIES. Any symptom")
        print("       measured on those frames is a DIFFERENT condition from the one V67/V68 flew --")
        print("       exclude them, or report the two arms separately. Do not pool.")
    else:
        print("     ⊕ the mask fired, but never while the gate was up ⇒ no below-stock frames.")

    # ---- 3. THE ARM LADDER -------------------------------------------------------------------------
    print(f"\n  ★ THE r24 PRIORITY LADDER -- which arm each frame actually took:")
    for i, band in enumerate(ARM_BANDS):
        n = int((a == i).sum())
        print(f"     {i}  {band:<70s} {n:8d}  {100.0 * n / len(b4):6.2f}%")
    if eng is not None:
        n_eng = int(eng.sum())
        if n_eng >= MIN_SAMPLES:
            print(f"     ENGAGED only ({n_eng} frames):")
            for i, band in enumerate(ARM_BANDS):
                n = int((a[eng] == i).sum())
                print(f"       {i}  {band.split('  ')[0]:<12s} {n:8d}  {100.0 * n / n_eng:6.2f}%")

    print(f"\n  ⊕ bit4 -- the third arm's index (gp-0x{ARM3_DISP:04X} >= {ARM_THRESHOLD}): "
          f"duty {100.0 * third.mean():.3f}%")
    print("     ⚠ It only DECIDES anything on frames where BOTH the mask and the gate are clear --")
    print(f"       {100.0 * float(((~mask) & (~gate)).mean()):.3f}% of this drive. Elsewhere it is "
          "measured but overruled.")

    # ---- 4. THE CROSS-BUILD ANCHOR -----------------------------------------------------------------
    print("\n  ★ bit7 -- THE CROSS-BUILD ANCHOR (unchanged from V74/V75, so the builds compare):")
    slices = [("all frames", np.ones(len(b4), dtype=bool))]
    if eng is not None:
        slices += [("ENGAGED", eng), ("manual", ~eng)]
        if speed_ms is not None and len(speed_ms) == len(b4):
            v = np.asarray(speed_ms, dtype=float)
            slices += [("ENGAGED creep (<= 4 m/s)", eng & (v <= CREEP_MAX_MS)),
                       ("ENGAGED cruise (> 4 m/s)", eng & (v > CREEP_MAX_MS))]
    print(f"     {'slice':26s} {'bit7':>8s} {'bit6':>8s} {'bit5':>8s} {'bit4':>8s}  n")
    for lab, m in slices:
        n = int(m.sum())
        if n < MIN_SAMPLES:
            print(f"     {lab:26s}: only {n} frames (< {MIN_SAMPLES}) -- not reportable")
            continue
        cols = [100.0 * ((b4[m] & bit) != 0).mean()
                for bit in (BIT_DAMP_NZ, BIT_GATE, BIT_MASK, BIT_ARM3)]
        print(f"     {lab:26s} " + " ".join(f"{c:7.3f}%" for c in cols) + f"  {n}")
    print(f"     🛑 bit7 is V74's damper, CARRIED UNCHANGED by V76. Compare its duty to V74's 39.93%")
    print("       engaged / 67.44% engaged-creep as a SANITY CHECK on the artefact -- do NOT credit")
    print("       any change in it to the rate-lane lever, which does not touch that cell.")

    # ---- 5. WHAT THIS DRIVE LICENSES ---------------------------------------------------------------
    print("\n  THE VERDICT THIS DRIVE LICENSES:")
    if not gate.any():
        print("     🛑 GATE NULL ⇒ the lever was never in force. This is RULE 5 territory: a null is")
        print("       only a null if the lever was in force, and it was not. Do not record the")
        print("       rate-lane hypothesis as falsified on this drive.")
    elif both.mean() > 0.5:
        print("     🛑 THE MASK DOMINATED. More than half of this drive sat in the below-stock state.")
        print("       The flown condition is NOT V67/V68's, and the grind-#1 comparison against them")
        print("       is invalid as pooled. Re-cut the analysis on mask-clear frames only.")
    else:
        clean = gate & ~mask
        print(f"     ✅ THE LEVER WAS IN FORCE ON {int(clean.sum())} FRAMES "
              f"({100.0 * clean.mean():.2f}%): gate up, mask clear ⇒ r24 = {ARM_GATE_VALUE} "
              f"(x{ARM_GATE_VALUE / GAIN_B_CREEP_LERP:.3f}) and")
        print(f"       r26 = {ARM_A_GATE_VALUE} (/{GAIN_A_CREEP_LERP / ARM_A_GATE_VALUE:.2f}). Score "
              "grind #1 (18-22 Hz) and the 6-9 Hz ratchet on THOSE frames.")
        print(f"       ⚠ Net vs stock = (5244 + 512a)/(3072 + 3072a); parity at a = {PARITY_A}. The")
        print("       corpus cannot separate the two lanes -- report the CONFIGURATION's result, and")
        print("       do not attribute it to r24 or r26 without a decoupled build.")
    print("     ⊕ V74's damper lever set (FactorC/FactorE engaged columns, friction x1.5, the")
    print("       X[0] = 12 gate, 0xC407E = 850) is CARRIED BYTE-FOR-BYTE and is NOT this build's")
    print("       variable. V75 is the sibling that moves it; do not compare V76 to V75 as a ladder.")
    return Counter(int(x) for x in a)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    override = "--i-confirm-v76" in argv[1:]
    if not args:
        print(__doc__)
        return 2
    refused = 0
    for target in args:
        print("=" * 100)
        print(f"  {target}")
        # 🛑 GLUE: `collect()` takes a LIST of paths and returns `b4` / `lat` / `v`. Passing the bare
        # string makes it iterate the path's CHARACTERS.
        data = collect([target])
        b4 = np.asarray(data["b4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            refused += 1
            continue
        engaged = np.asarray(data["lat"], dtype=bool) if data.get("has_lat") else None
        speed_ms = data.get("v")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: {dict(Counter(hex(int(x)) for x in b4).most_common(12))}")
        if not identify(b4, engaged, speed_ms, override=override):
            refused += 1
            continue
        report(b4, engaged, speed_ms)
        print(f"\n  🛑 REMINDER: V76's lever is MODE-PROOF -- both arms are plain tp-relative scalars")
        print(f"     with no mode*4 index, so this car's mode {LIVE_MODE} (engaged) / {MANUAL_MODE}")
        print("     (manual) is irrelevant to whether it is in force. That is the whole reason RULE 7")
        print("     voided V69/V70 and not V67/V68.")
        print("  🛑 The gate applies in MANUAL too whenever gp-0x6806 is set -- V57 measured that as")
        print("     essentially never, but the arm ladder above reports manual separately so the")
        print("     claim is checked on THIS drive rather than inherited.")
    # 🛑 EXIT NON-ZERO ON ANY REFUSAL. A guard that returns success is only half a guard: the loud
    # banner is for a human, this is for anything that pipes, wraps or CI-checks the decoder.
    if refused:
        print(f"\n🛑 {refused} of {len(args)} target(s) REFUSED or empty -- exiting non-zero.")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
