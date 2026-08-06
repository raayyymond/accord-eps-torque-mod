#!/usr/bin/env python3
"""decode_v73_probe.py -- read V73's probe: the base-assist damper's MODE BYTE, `gp+0x63fd`.

WHAT V73 IS -- so a reader of this file cannot mistake the artefact
--------------------------------------------------------------------
V73 = **V72, carried byte-identically**, plus three additions and a new probe. Everything V72 does --
LEVER A (both rate lanes dosed across the whole rate axis at the 0 and 10 km/h records, UNGATED,
exactly 1.000x at and above 50 km/h), LEVER B (mode-10/11 FactorC/E), LEVER C (`0xC63A0` = 2048) and
the carried-but-inert `0x454FE` -- is unchanged and is asserted at its V72 value by the builder.

  EDIT 1  **GRIND #1, the friction lane** (`gp-0x6b26`, FUN_00036c12). The 3-point record `0xD2A44`
          Y[0..2] x1.5 (-9830/-5734/-1966 -> -14745/-8601/-2949) **paired with** the lane's own
          symmetric self-clamp `0xC407E` (tp+0x507e) 511 -> 850. Raising the gain without the clamp
          just clips harder; the sizing work put grind #1's whole p50-p99 range inside 850 at 1.5x.
          🛑 The record is **MODE-INDEXED** (`0xCBE74[mode * 4]`, mode 10 -> `0xD2A44`).
          **`0xC407E` is NOT** -- it is a scalar tp cell read unconditionally, so it acts in any mode.
  EDIT 2  **THE RATCHET, on every candidate mode: 0, 1, 2, 3, 4, 5, 12, 14** (16 cells / 32 bytes).
          The edit is **`Y[0] := that record's OWN Y[1]`**, with every address DERIVED from the
          pointer arrays `0xC9E9C` (FactorC) / `0xC9F84` (FactorE) at `mode * 4`. ★ Y[1] is the
          largest value that keeps the row MONOTONE and it preserves the rate/speed PROPORTIONALITY
          -- only the dead first segment is lifted to meet the second. V72 flattened mode 10's
          FactorE to [927,927,927,927], turning a proportional damper into a near-bang-bang relay,
          and V73 deliberately does not repeat that.
          🛑 **10 and 11 are EXCLUDED** (V72 owns them, and V72's own `bit4` null excludes them
          decisively -- on those values the rung had to fire ~100% of the time and fired 0/87,940).
  EDIT 3  this probe.

🛑🛑 **THE TWO LEVERS ARE DISJOINT IN MODE, AND THIS PROBE SETTLES WHICH ACTED.** EDIT 1's LERP half
is mode-**10**-indexed; EDIT 2 covers 0-5, 12 and 14. **At most one of them can have acted on any
drive**, and the mode field says which. Neither can regress the other, and `0xC407E` acts either way.

🛑 **THE DOSE IS NOT UNIFORM ACROSS FAMILIES.** Delivered `|gp-0x6bd0|` at creep, `(C*E)>>10` with
FactorB/D flat 1024:  **modes 0-3 -> 106 counts · modes 4/5 -> 33 · modes 12/14 -> 31** -- a 3.4x
spread, because each family's own Y[1] is the value being lifted to. ⇒ **if this reads 4, 5, 12 or
14, the dose V73 delivered was SMALL and a null result must NOT be scored as falsifying the lever.**
V74 raises it against whichever mode turns out to be live.

THE PAYLOAD -- CAN 0x14A byte4, bits 7:3
-----------------------------------------
    bit7      = 1                                LIVENESS. field == 0 ⇒ the cave did not fire ⇒ VOID.
    bits 6:3  = (*(byte *)(gp + 0x63FD)) & 0xF   ★★★★ **THE MODE.**
    bits 2:0  = stock STEER_SENSOR_STATUS         preserved, untouched.

WHY THIS ONE MEASUREMENT
-------------------------
`gp+0x63FD` is the byte **every** FactorB/C/D/E lookup in `FUN_00034350` indexes on, the byte the
friction lane indexes on (`0x36c4a`), and the byte r24's gain_B selector indexes on (`0x3ad88`).
Every "mode 10" statement this kit has ever made is an INFERENCE from the part number
(39990-TVA-A160 -> key `TVAA1` -> row 2 -> modes 10/11); the actual coded row lives in EEPROM
(UDS variant coding), **not in the flash image**, and has never been read back.

V72's `bit4` rung (`|gp-0x6bd0| >= 64`) is what forced the issue: on modes 10/11 V72's own FactorC/E
give `|gp-0x6bd0| = 1024 * (430/1024) * (927/1024) = 389` **unconditionally, on every frame**, so the
rung had to fire ~100% of the time. It fired **0 / 87,940 frames, including 0 / 34,275 above 35 km/h**
where even STOCK damps. There is no amplitude, speed or rate regime in which mode 10/11 is silent.
⇒ either the car is not in mode 10/11, or something below the cal layer is wrong. **This rung reads
the selector itself and does not need either story to be true.**

HOW TO READ THE ANSWER
-----------------------
| mode        | what it means | which V73 edit was LIVE |
|-------------|---------------|-------------------------|
| **0**       | `.bss` boot default AND `e012` of the blank row | **EDIT 2**, dose **106** |
| **1 / 2 / 3** | `e013`/`e014`/`e015` of the blank row | **EDIT 2**, dose **106** |
| **4 / 5**   | `TVAA0`/`TVAA2`/`TVAA4` coding | **EDIT 2**, dose **33** ⚠ small |
| **12 / 14** | `TVAA7` coding, `e012`/`e014` arms | **EDIT 2**, dose **31** ⚠ small |
| **13 / 15** | `TVAA7`'s `e013`/`e015` arms | ⚠ **NEITHER.** `0xD37BC`/`0xD37F8` and
                `0xD37E4`/`0xD3820` are untouched -- a one-line follow-up, no new analysis needed |
| **10 / 11** | `TVAA1`/`TVAC1`/`TVAA6`/`TVAC4` -- the part-number inference was RIGHT |
                **EDIT 1's LERP** (mode 10 only) and V72's LEVER B, which means the `bit4` null needs
                a different explanation |
⊕ In EVERY case `0xC407E` (511 -> 850) was live, because it is not mode-indexed.

⚠ **THE 4-BIT FIELD ALIASES MOD 16.** Modes 16-33 exist in the ROM table but only on TVC/TWA chassis
rows (9-15). Every mode a `TVA*` or blank row can select is < 16, which the builder asserts against
the 0xCD000 table on the image being built, so the field is **lossless for this car** -- but a value
read here is `mode & 0xF`, and if this ECU were somehow coded to a TVC/TWA row the reading would be
ambiguous (e.g. 16 reads as 0, 26 reads as 10). Report it as `mode & 0xF`, not as `mode`.

⚠ **WEAK BUILD IDENTITY, STATED UP FRONT.** All 16 payload values are legal here, so unlike V72
(whose `bit5 => bit6` invariant made 4 of 16 payloads structurally impossible) **the value set proves
only that SOME bit7-setting cave ran.** The `.rwd` **FILENAME** is the pre-drive discriminator and
`CAVE_HEX` below is the post-hoc one. Do not claim more from the stream than that.

CAVE DISCIPLINE -- 36 code bytes inside the proven 68-byte extent; the remaining 32 are 0x00 (`nop`)
and sit AFTER `jmp [lp]`, so they are unreachable. Caves are this kit's only bricking class (V24, V27
and V48B all bricked the ECU) and the extent is asserted at 68 either way.
⚠ The role table at 0xC4124 is asserted unchanged by the builder ([0,0,5,0,5,5,0,0,0,5,0]); a slot
carrying role 6 or 7 makes gp-0x67ac live and the aggregator drops r24, r26 AND the damping lane --
which would make every lever on this build vacuous at once.

Usage:  python decode_v73_probe.py <rlog-or-route-dir> [...]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

# 🛑 WINDOWS REDIRECT FIX -- cp1252 on a redirected stdout raises UnicodeEncodeError on the first
# 🛑/★/⚠ glyph, so `> out.txt` would crash before emitting a line.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
# ⚠ The NUMERIC MACHINERY is shared on purpose -- collect/runs_of are instrument code, not semantics,
# and two copies would drift. The 128-sample floor was FIXED on 2026-08-04; do not regress it.
from decode_v67_gate import collect                                        # noqa: E402
from decode_v69_ratchet import MIN_SAMPLES                                  # noqa: E402

# 🛑 THE MECHANICAL LINK TO THE IMAGE. build_v73_tva.assert_decoder_matches() FAILS THE BUILD if this
# hex does not equal the cave it just emitted, so this decoder cannot silently describe a different
# build. Do not hand-edit it.
CAVE_HEX = "203e1000a437fd63c6360f000639c33a8437edeac636070007314437ecea2436e8ea7f000000000000000000000000000000000000000000000000000000000000000000"  # noqa: E501
#
#   0xC4B34  203e1000  movea 0x10,r0,r7      bit7 LIVENESS, in PRE-SHIFT weights
#   0xC4B38  a437fd63  ld.bu 0x63fd[gp],r6   ★★★★ THE MODE BYTE. **POSITIVE** gp displacement.
#                                            🛑 op field 0x3D, not 0x3C: ld.bu carries the
#                                            displacement's own bit 0 IN THE OPCODE, and 0x63FD is
#                                            ODD. Byte-identical to the real `ld.bu 0x63fd,gp,r6`
#                                            @0x346B4. The st.b twin @0x426AE is 4447fd63.
#   0xC4B3C  c6360f00  andi 0xf,r6,r6        4 bits (real instance @0x45EBC)
#   0xC4B40  0639      or    r6,r7           r7 |= mode.  🛑 **NOT** `or r7,r6` (0731) -- SAME opcode,
#                                            register fields SWAPPED, and both forms are real
#                                            instructions in this image, so a byte pin alone cannot
#                                            catch the swap. The wrong one would OR the mode into the
#                                            SCRATCH register and every frame would read "mode 0".
#   0xC4B42  c33a      shl   0x3,r7          the 5-bit field -> bits 7:3 (Honda's own @0x4FB82)
#   0xC4B44  8437edea  ld.bu -0x1514[gp],r6  CAN-330 payload byte4 (r6 is free: the mode is in r7)
#   0xC4B48  c6360700  andi  0x7,r6,r6       preserve live STEER_SENSOR_STATUS bits 2:0
#   0xC4B4C  0731      or    r7,r6           the MERGE -- this one IS `or r7,r6`
#   0xC4B4E  4437ecea  st.b  r6,-0x1514[gp]  THE ONLY STORE. GATE 1 is vacuous.
#   0xC4B52  2436e8ea  movea -0x1518,gp,r6   the displaced hook instruction, re-executed LAST
#   0xC4B56  7f00      jmp   [lp]            -> 0x55C12, which is `mov 0x8,r7` (083a) ⇒ r7 is
#                                            PROVABLY DEAD across the hook
#   0xC4B58  00 x 32   nop                   padding, AFTER the return ⇒ unreachable

BIT_LIVE = 0x80               # bit7  the cave ran
MODE_FIELD = 0x78             # bits 6:3  (gp+0x63FD) & 0xF
MODE_SHIFT = 3
MODE_MASK = 0xF
PROBE_MASK = 0xF8
STATUS_MASK = 0x07            # STEER_SENSOR_STATUS, preserved

MODE_DISP = 0x63FD            # 🛑 a POSITIVE gp displacement. gp+0x63FD, NOT gp-0x63FD.
FRICTION_PTR_ARRAY = 0xCBE74  # ptr[mode * 4] -> the friction record; mode 10 -> 0xD2A44
FACTOR_C_PTRS, FACTOR_E_PTRS = 0xC9E9C, 0xC9F84
FACTORC_ONSET_KMH = 35.0      # below this, mode-10/11 STOCK base-assist damping is a HARD ZERO
CREEP_MAX_MS = 4.0            # the ratchet and grind #1 are creep symptoms (1-4 m/s)

# 🛑 ONE LINE, deliberately. build_v73_tva.py asserts this exact basename appears in this file;
# splitting it across a concatenation makes the substring vanish and the check silently harder.
RWD_NAME = "39990-TVA,A160-V73-V72BASE-frictionx1.5-C407E850-ratchet-modes0_5_12_14-Y0eqY1-probe-MODEBYTE-0x13000-0x100000.rwd"  # noqa: E501

# Which modes EDIT 2 covers, which V72 owns, and which are reachable but uncovered.
RATCHET_MODES = (0, 1, 2, 3, 4, 5, 12, 14)
EXCLUDED_MODES = (10, 11)          # V72's LEVER B
UNCOVERED_MODES = (13, 15)         # ⚠ TVAA7's e013/e015 arms
DOSE = {0: 106, 1: 106, 2: 106, 3: 106, 4: 33, 5: 33, 12: 31, 14: 31}   # counts at creep
SMALL_DOSE_MODES = (4, 5, 12, 14)  # 🛑 a null here is a SMALL DOSE, not a falsification

# What each mode value implies. (label, which V73 edit was live, the records that mode actually reads)
MODE_MEANING = {
    0: ("BLANK HW-ID, e012 -- and the .bss BOOT DEFAULT", "EDIT 2, dose 106",
        "FactorC 0xCE528, FactorE 0xCE550, friction 0xCE6D8"),
    1: ("BLANK HW-ID, e013", "EDIT 2, dose 106",
        "FactorC 0xCE53C, FactorE 0xCE564, friction 0xCE6E8"),
    2: ("BLANK HW-ID, e014", "EDIT 2, dose 106",
        "FactorC 0xCF528, FactorE 0xCF550, friction 0xCF6D8"),
    3: ("BLANK HW-ID, e015", "EDIT 2, dose 106",
        "FactorC 0xCF53C, FactorE 0xCF564, friction 0xCF6E8"),
    4: ("TVAA0 / TVAA2 / TVAA4 coding, e012/e013", "EDIT 2, dose 33 ⚠ SMALL",
        "FactorC 0xD07BC, FactorE 0xD07F8, friction 0xD0A44"),
    5: ("TVAA0 / TVAA2 / TVAA4 coding, e014/e015", "EDIT 2, dose 33 ⚠ SMALL",
        "FactorC 0xD07D0, FactorE 0xD080C, friction 0xD0A54"),
    10: ("TVAA1 / TVAC1 / TVAA6 / TVAC4 -- THE INFERRED ONE",
         "EDIT 1's LERP (0xD2A44) + V72's LEVER B", "FactorC 0xD27BC, FactorE 0xD27F8, fric 0xD2A44"),
    11: ("TVAA1 family, failover branch", "V72's LEVER B (mode 11); EDIT 1's LERP is mode 10 ONLY",
         "FactorC 0xD27D0, FactorE 0xD280C, friction 0xD2A54"),
    12: ("TVAA7 coding, e012", "EDIT 2, dose 31 ⚠ SMALL",
         "FactorC 0xD27E4, FactorE 0xD2820, friction 0xD2A64"),
    13: ("TVAA7 coding, e013", "⚠ NEITHER -- follow-up: 0xD37BC / 0xD37F8",
         "FactorC 0xD37BC, FactorE 0xD37F8"),
    14: ("TVAA7 coding, e014", "EDIT 2, dose 31 ⚠ SMALL",
         "FactorC 0xD37D0, FactorE 0xD380C"),
    15: ("TVAA7 coding, e015", "⚠ NEITHER -- follow-up: 0xD37E4 / 0xD3820",
         "FactorC 0xD37E4, FactorE 0xD3820"),
}
# ⚠ ALIASING: a reading of N could also be N+16 or N+32 on a TVC/TWA-coded ECU (rows 9-15).
ALIAS_NOTE = {0: (16, 32), 1: (17, 33), 6: (22,), 7: (23,), 8: (24,), 9: (25,), 10: (26,), 11: (27,),
              12: (28,), 13: (29,), 14: (30,), 15: (31,)}


def wire_byte4(mode_byte, status_bits=0x7):
    """EXACTLY what the cave computes -- the same instructions, in the same order."""
    r7 = 0x10                                       # movea 0x10,r0,r7
    r6 = mode_byte & 0xFF                           # ld.bu 0x63fd[gp],r6   (a BYTE, zero-extended)
    r6 &= MODE_MASK                                 # andi  0xf,r6,r6
    r7 |= r6                                        # or    r6,r7
    return ((r7 << MODE_SHIFT) & 0xFF) | (status_bits & STATUS_MASK)


LEGAL = {BIT_LIVE | (m << MODE_SHIFT) for m in range(MODE_MASK + 1)}
ON_WIRE = {b | STATUS_MASK for b in LEGAL}          # as transmitted, with all three status bits set

STRUCTURALLY_DISJOINT = {
    "V53 (emits only 0x07 -- bit7 CLEAR)": {0x07},
    "V54 (emits only 0x0F -- bit7 CLEAR)": {0x0F},
}
# 🛑 A COLLISION THIS KIT HAS ALREADY BEEN BITTEN BY: on V73 `mode 0` transmits as 0x87 with all
# three status bits set -- the SAME byte V64's probe emitted, constant, for 14,980 frames, when its
# detector never armed. A constant-0x87 stream is a legitimate V73 answer AND a known failure
# signature of a different build, and the payload cannot tell them apart. Filename + CAVE_HEX only.
V64_STUCK_VALUE = 0x87

# The cave's REAL instruction boundaries, as (offset, length). Every byte-level check below is made
# on these rather than on "every even offset" -- a displacement halfword decoded as an opcode is how
# a store gets invented or missed.
BOUNDARIES = ((0, 4), (4, 4), (8, 4), (12, 2), (14, 2),              # seed + mode + mask + or + shl
              (16, 4), (20, 4), (24, 2), (26, 4), (30, 4), (34, 2))  # tail
PAD_OFF = 36


def _self_check():
    """The payload claims, as executable assertions rather than a paragraph."""
    assert len(LEGAL) == 16, f"{len(LEGAL)} legal payloads, expected 16"
    assert all(b & BIT_LIVE for b in LEGAL), "a legal payload has bit7 clear"
    assert BIT_LIVE | MODE_FIELD == PROBE_MASK, "the probe bits do not cover exactly 7:3"
    assert PROBE_MASK & STATUS_MASK == 0, "the probe bits collide with STEER_SENSOR_STATUS"
    assert MODE_FIELD == MODE_MASK << MODE_SHIFT == 0x78, "the mode field is not bits 6:3"
    # ---- the rung, EXHAUSTIVELY over all 256 values the byte can hold ----------------------------
    for raw in range(256):
        b = wire_byte4(raw)
        assert b & BIT_LIVE, f"the liveness bit is clear at mode byte {raw}"
        assert (b & MODE_FIELD) >> MODE_SHIFT == (raw & MODE_MASK), \
            f"bits 6:3 are not `(gp+0x63FD) & 0xF` at {raw}"
        assert (b & PROBE_MASK) in LEGAL, f"payload 0x{b:02X} is outside LEGAL at {raw}"
    # 🛑 the ALIASING is a property of the rung, not a caveat bolted on afterwards.
    assert wire_byte4(16) == wire_byte4(0) and wire_byte4(26) == wire_byte4(10), \
        "the 4-bit field does not ALIAS mod 16 -- the aliasing note in the docstring is wrong"
    for status in range(8):
        assert wire_byte4(0xFF, status) == 0xF8 | status, \
            "the preserved STEER_SENSOR_STATUS bits are not passed through untouched"
        assert wire_byte4(0, status) == 0x80 | status, "an all-zero mode is not bare liveness"
    # ---- the cave hex, field by field ------------------------------------------------------------
    raw = bytes.fromhex(CAVE_HEX)
    assert len(raw) == 68, f"CAVE_HEX is {len(raw)} bytes, not the proven 68"
    assert sum(n for _o, n in BOUNDARIES) == PAD_OFF, "the boundary table does not tile the code"
    for prev, nxt in zip(BOUNDARIES, BOUNDARIES[1:]):
        assert prev[0] + prev[1] == nxt[0], f"the boundary table is not contiguous at {prev}"
    assert raw[PAD_OFF:] == bytes(68 - PAD_OFF), \
        "the bytes after `jmp [lp]` are not all 0x00 -- the padding claim is wrong"
    assert raw[0:4] == bytes.fromhex("203e1000"), "offset 0 is not `movea 0x10,r0,r7`"
    assert raw[34:36] == bytes.fromhex("7f00"), "offset 34 is not `jmp [lp]`"
    # 🛑 Offsets are (address - 0xC4B34), DERIVED from the listing above, not guessed -- an off-by-4
    # checks the wrong halfword and the guard silently passes on a cave that WRITES.
    # 🛑🛑 THE MODE LOAD'S ONE-BIT TRAP: ld.bu (odd disp) is op 0x3D; st.b is 0x3A, and the
    # firmware's own `st.b r8,0x63fd,gp` @0x426AE is 4447fd63 against our a437fd63.
    assert raw[4:8] == bytes.fromhex("a437fd63"), "offset 4 is not `ld.bu 0x63fd[gp],r6`"
    assert raw[4:8] != bytes.fromhex("4447fd63"), \
        "the mode load IS the real `st.b r8,0x63fd,gp` @0x426AE -- the cave would REWRITE the byte " \
        "that every damper factor table, the friction lane and r24's gain_B all index on. DO NOT FLASH."
    _hw1 = int.from_bytes(raw[4:6], "little")
    assert (_hw1 >> 5) & 0x3F == 0x3D, \
        f"the mode load's opcode field is 0x{(_hw1 >> 5) & 0x3F:02X}, MUST be 0x3D (ld.bu, ODD " \
        "displacement); 0x3C is the EVEN form and 0x3A is st.b"
    assert (_hw1 >> 11) == 6 and (_hw1 & 0x1F) == 4, "the mode load is not `... [gp],r6`"
    assert int.from_bytes(raw[6:8], "little") == (MODE_DISP & 0xFFFE) | 1 == 0x63FD, \
        "the mode load does not carry the displacement +0x63FD"
    for off, want, what in ((8, "c6360f00", "andi 0xf,r6,r6   -- the 4-bit mask"),
                            (12, "0639", "or r6,r7         -- mode INTO the payload"),
                            (14, "c33a", "shl 0x3,r7       -- field -> bits 7:3"),
                            (16, "8437edea", "ld.bu -0x1514[gp],r6"),
                            (20, "c6360700", "andi 0x7,r6,r6   -- keep the status bits"),
                            (24, "0731", "or r7,r6         -- the MERGE"),
                            (26, "4437ecea", "st.b r6,-0x1514[gp] -- THE ONLY STORE"),
                            (30, "2436e8ea", "movea -0x1518,gp,r6 -- the displaced instruction")):
        assert raw[off:off + len(want) // 2] == bytes.fromhex(want), \
            f"CAVE_HEX offset {off} is not {want} ({what})"
    # 🛑🛑 `or r6,r7` vs `or r7,r6`: SAME opcode, register fields SWAPPED, BOTH real in this image.
    # Decode the FIELDS -- a byte comparison alone is not a proof here.
    assert raw[12:14] != bytes.fromhex("0731"), \
        "offset 12 is `or r7,r6`, not `or r6,r7` -- the mode would be OR'd into the SCRATCH register " \
        "and EVERY frame would read mode 0. This is the exact false-negative the probe exists to avoid."
    _or = int.from_bytes(raw[12:14], "little")
    assert (_or >> 5) & 0x3F == 0x08 and (_or >> 11) == 7 and (_or & 0x1F) == 6, \
        f"the accumulate's fields are wrong: op 0x{(_or >> 5) & 0x3F:02X}, dest r{_or >> 11}, " \
        f"src r{_or & 0x1F} -- must be op 0x08, dest r7, src r6"
    assert raw[8:12] != raw[20:24], "the 0xF and 0x7 masks collapsed -- the mode's top bit is lost"
    assert int.from_bytes(raw[10:12], "little") == MODE_MASK and \
        int.from_bytes(raw[22:24], "little") == STATUS_MASK, \
        "the two andi immediates are not 0xF (the mode) and 0x7 (the preserved status bits)"
    # 🛑 EXACTLY ONE STORE, on the REAL instruction boundaries.
    stores = [o for o, n in BOUNDARIES
              if n >= 4 and ((int.from_bytes(raw[o:o + 2], "little") >> 5) & 0x3F) in (0x3A, 0x3B)]
    assert stores == [26], f"the cave's store set is {stores}, expected exactly [26]"


_self_check()


def identify(b4):
    """Which build produced this payload stream? Reported at its REAL strength, not more."""
    vals = set(int(v) for v in b4)
    print(f"\n  distinct byte4 values: {sorted(hex(v) for v in vals)}")
    void = int(np.count_nonzero((b4 & BIT_LIVE) == 0))
    print(f"  VOID (bit7 clear, the cave did not fire): {void} / {len(b4)}")
    if void:
        print("  🛑 HARD FAIL. A VOID frame means the cave did not run. Nothing below may be")
        print(f"     interpreted. Check the .rwd filename against:\n       {RWD_NAME}")
        # ⊕ THE REVERSE GUARD, AND IT IS FREE. On **V74** this same bit is `gp-0x6bd0 != 0` -- the
        # damper's own output -- which reads 0 whenever the motor rate is 0. So a V74 log fed to
        # THIS decoder trips the line above and is refused, without a dedicated test. ⚠ The residual:
        # a V74 log whose damper never read zero would decode here as a mode reading. That is
        # implausible (FactorE's Y[0] is preserved at 0, so zero rate forces zero output), but it is
        # not impossible, so the FILENAME remains the discriminator in both directions.
        # 🛑 The forward direction is NOT free and needed a real guard: see decode_v74_probe.py's
        # identify(), added after this decoder's own flight was certified as a V74 success.
        return False
    for name in STRUCTURALLY_DISJOINT:
        print(f"  ✅ EXCLUDED ABSOLUTELY: {name}")
    print("  ⚠ WEAK IDENTITY, BY CONSTRUCTION: all 16 payload values are legal on V73, so the value")
    print("    SET proves only that SOME bit7-setting cave ran. V72's `bit5 => bit6` invariant has no")
    print("    analogue here. **The .rwd FILENAME is the pre-drive discriminator**; CAVE_HEX in this")
    print("    file is the post-hoc one. Do not claim a build identity from the stream alone.")
    if vals == {V64_STUCK_VALUE}:
        print(f"  🛑🛑 THE STREAM IS CONSTANT 0x{V64_STUCK_VALUE:02X}, WHICH IS **ALSO** THE VALUE "
              "V64's PROBE EMITTED")
        print("     for 14,980 frames when its detector never armed. On V73 that byte reads as")
        print("     `mode 0`, which is a real and expected answer -- but the two are indistinguishable")
        print("     from the payload alone. 🛑 CONFIRM THE ARTEFACT BY FILENAME AND CAVE_HEX BEFORE")
        print(f"     reporting a mode-0 result:\n       {RWD_NAME}")
    return True


def report_mode(b4, engaged, speed_ms, warn_alias=True):
    """★★★★ THE MEASUREMENT: which calibration records this car actually reads."""
    modes = (b4 & MODE_FIELD) >> MODE_SHIFT
    n = len(modes)
    print("\n  ★★★★ bits 6:3 -- (gp+0x63FD) & 0xF, THE BASE-ASSIST DAMPER'S MODE SELECTOR")
    counts = Counter(int(m) for m in modes)
    for m, c in counts.most_common():
        label, live, recs = MODE_MEANING.get(m, ("UNKNOWN -- not in the ROM table for any row",
                                                 "unknown", "—"))
        print(f"     mode {m:2d}: {100.0 * c / n:7.3f}%  ({c} / {n})   {label}")
        print(f"               V73 edit live: {live}")
        print(f"               reads: {recs}")
        if warn_alias and m in ALIAS_NOTE:
            print(f"               ⚠ ALIAS: a TVC/TWA-coded ECU reading {ALIAS_NOTE[m]} would also "
                  f"show {m}. Report as `mode & 0xF`.")
    dom, dom_n = counts.most_common(1)[0]
    print(f"     ⇒ DOMINANT: mode {dom} on {100.0 * dom_n / n:.3f}% of frames; "
          f"{len(counts)} distinct value(s) seen.")

    # ---- the BOOT-WINDOW question: does the HW-ID confirm sequence fire, and how fast? ------------
    first = int(modes[0])
    changed = np.nonzero(modes != modes[0])[0]
    print(f"\n     THE BOOT-WINDOW QUESTION (`gp+0x63FD` is .bss and boots to 0; FUN_00042746 writes")
    print(f"     it from the HW-ID table). First frame reads mode {first}.")
    if not len(changed):
        print(f"     ⇒ the mode NEVER changed across all {n} frames. If that value is 0, the")
        print("       confirm sequence did not fire on this drive -- which is exactly the reading")
        print("       V72's bit4 null implies, and it makes EDIT 2 the live lever.")
    else:
        i = int(changed[0])
        print(f"     ⇒ it FIRST changed at frame {i} ({100.0 * i / n:.2f}% into the log), "
              f"{first} -> {int(modes[i])}.")
        trans = int(np.count_nonzero(modes[1:] != modes[:-1]))
        print(f"       {trans} transition(s) in total. A mode that flips during a drive means the")
        print("       failover selector `gp-0x67e2` / `gp-0x67f6` is moving, which is itself news.")

    # ---- conditioning: engagement and speed ------------------------------------------------------
    if engaged is not None and engaged.any():
        for lab, m in (("engaged", engaged), ("manual ", ~engaged)):
            if m.sum() >= MIN_SAMPLES:
                c = Counter(int(x) for x in modes[m])
                print(f"     {lab}: {dict(c.most_common(4))}   ({int(m.sum())} frames)")
        print("     ⚠ the mode selector is HW-ID-keyed, not engagement-keyed -- a split here would")
        print("       CONTRADICT the traced structure and should be reported as such, not smoothed.")
    if speed_ms is not None:
        kmh = np.asarray(speed_ms) * 3.6
        for lab, m in ((f"creep (< {CREEP_MAX_MS * 3.6:.0f} km/h)", kmh < CREEP_MAX_MS * 3.6),
                       (f"below {FACTORC_ONSET_KMH:.0f} km/h    ", kmh < FACTORC_ONSET_KMH),
                       (f"at/above {FACTORC_ONSET_KMH:.0f} km/h ", kmh >= FACTORC_ONSET_KMH)):
            if m.sum() >= MIN_SAMPLES:
                c = Counter(int(x) for x in modes[m])
                print(f"     {lab}: {dict(c.most_common(4))}   ({int(m.sum())} frames)")
            else:
                print(f"     {lab}: only {int(m.sum())} frames (< {MIN_SAMPLES}) -- not reportable")
    return counts


def report_verdict(counts):
    """What the reading licenses, and what it does not."""
    dom = counts.most_common(1)[0][0]
    print("\n  THE VERDICT THIS DRIVE LICENSES:")
    if dom in RATCHET_MODES:
        print(f"     mode {dom} ⇒ **EDIT 2 WAS LIVE** at a delivered creep dose of "
              f"**{DOSE[dom]} counts**, and")
        print("       EDIT 1's friction LERP at 0xD2A44 was **INERT** (it is mode-10-indexed) --")
        print("       only its clamp 0xC407E acted. Score the ratchet against EDIT 2 and grind #1")
        print("       against the CLAMP ALONE.")
        if dom in SMALL_DOSE_MODES:
            print(f"     🛑🛑 THE DOSE WAS SMALL ({DOSE[dom]} counts vs 106 on modes 0-3). **A NULL "
                  "RESULT HERE IS NOT A")
            print("        FALSIFICATION OF THE LEVER** -- it is an under-dose. V74 should raise")
            print(f"        mode {dom}'s FactorC/E Y[0] above its own Y[1] before anything is")
            print("        concluded about whether base-assist damping helps the ratchet.")
        print("     ⊕ It ALSO explains V72's bit4 null WITHOUT a fifth hypothesis: V72's LEVER B")
        print("       edited mode 10/11's FactorC/E, which this car never read.")
        print("     ⇒ the follow-up that widens EDIT 1 writes the same friction Y row into")
        print(f"       0xCBE74[{dom}*4]'s record + 8 (6 bytes).")
    elif dom in EXCLUDED_MODES:
        print(f"     mode {dom} ⇒ the part-number inference was RIGHT. **EDIT 1's LERP was LIVE**")
        print("       (mode 10 only) and V72's LEVER B was live all along -- which means the bit4")
        print("       null (0 / 87,940 frames, including 0 / 34,275 above 35 km/h) is NOT explained")
        print("       by the mode and needs a different account. 🛑 Treat that as an OPEN")
        print("       contradiction, not a detail: on those FactorC/E values bit4 had to fire on")
        print("       ~100% of frames. EDIT 2 was inert and cannot have regressed anything.")
    elif dom in UNCOVERED_MODES:
        print(f"     mode {dom} ⇒ the TVAA7 branch fired, but on the arm V73 did NOT cover.")
        print("       **NEITHER EDIT 1's LERP NOR EDIT 2 was live**; only the clamp 0xC407E acted.")
        print("       The one-line follow-up is named in MODE_MEANING above -- no new analysis needed.")
    else:
        print(f"     mode {dom} ⇒ outside every modelled set. 🛑 STOP and re-derive: the ROW->mode")
        print("       table reaches only 0-5 and 10-15 on TVA-family rows, so this is either a")
        print("       TVC/TWA-coded ECU (and the 4-bit field ALIASED) or the reading is wrong.")
    print("     ⊕ IN EVERY CASE: 0xC407E (511 -> 850) WAS LIVE -- it is a scalar tp cell, not")
    print("       mode-indexed. Any grind-#1 change on this drive is attributable to it at minimum.")


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    for target in argv[1:]:
        print("=" * 100)
        print(f"  {target}")
        # 🛑 GLUE, fixed 2026-08-04 while extracting route 59: `collect()` takes a LIST of paths and
        # returns `b4` / `lat` / `v`. Passing the bare string made it iterate the path's CHARACTERS.
        data = collect([target])
        b4 = np.asarray(data["b4"], dtype=np.uint8)
        if not len(b4):
            print("  🛑 no 0x14A frames found.")
            continue
        engaged = np.asarray(data["lat"], dtype=bool) if data.get("has_lat") else None
        speed_ms = data.get("v")
        print(f"  frames: {len(b4)}")
        print(f"  payload histogram: {dict(Counter(hex(int(v)) for v in b4).most_common(12))}")
        if not identify(b4):
            continue
        counts = report_mode(b4, engaged, speed_ms)
        report_verdict(counts)
        print("\n  🛑 REMINDER: V73 carries every V72 lever unchanged, including the UNGATED rate")
        print("     lane -- the dose applies in MANUAL below ~30 km/h too. Score manual separately.")
        print("  🛑 `0x454FE` is CARRIED but INERT and UNTESTED (V71 measured `gp-0x67fa == 4` at")
        print("     0/123,277 and 8/92,826 frames, all eight in park). Do not score the 7.79 Hz")
        print("     ratchet against it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
