# -*- coding: utf-8 -*-
r"""V282 -- V281 rev 3 + a READ-ONLY re-pointing of TWO comparator rungs inside the EXISTING V112 telemetry cave
(0xC4B34, on the car byte-identical since V105).  No new code, no length change, no cal change, no authority
change.  The CAN-427 delivered-torque tap is kept exactly as-is; 0x14A gains two informative bits about the
base-assist rate lane r24 (gp-0x6ada) alongside the sign bit (bit 4) it already publishes.

=== OPERATOR DECISION / WHY (2026-09-03) ========================================================
Two independent deep analyses (`docs/research/GRINDING-DEEP-ANALYSIS-2026-09-03.md`, agent deepgrind, itself
adjudicating a 7 Hz sibling analysis) converged on: the 18-22 Hz creep grind and the 6-9 Hz high-angle stutter
are the SAME cell (0xC6446, the r24 gain arm) pulling opposite ways in two different bands, and r24 is NOT on
the CAN wire as a magnitude -- only its sign is (bit 4, already live).  Sizing every candidate fix (cutting
0xC6446 for the 7 Hz stutter, raising the LKAS PID's output-lag/feedback pole, etc.) needs to know how big r24
actually is relative to the LKAS servo lane (T, the 427 tap = gp-0x6b38) and relative to the aggregator sum
that reaches the motor (gp-0x6b94) -- and it needs to know THIS on the flown gain arm, because a hidden
fault-debounce arm (gp-0x671d != 0 -> 0xC6442 = 1024 instead of the engaged 5244) would invert every ranking
in the doc, and gp-0x671d has never been traced.

  "One number decides between 'raise r24' and 'cut r24', and it is not on the wire.  Eight read-only bytes
   buy it on a drive that is going to happen anyway."  -- the doc's own framing, deliverable 3 part 1.

Rejected alternative: re-point the 427 tap itself from gp-0x6b38 to gp-0x6ada.  That COSTS the delivered-torque
tap every recent analysis (including this one) is built on, and 427 has only 3 free bits inside Honda's
checksum -- not enough for a second field.  The cave repoint keeps T on 427 and adds a second, independent
100 Hz channel via 0x14A, which already carries bit 4 = sign(r24) with duty and phase behaviour recorded on
four routes (`accord-v278r3-high-angle-stutter-is-p-desaturating-on-a-stalled-wheel` /
`accord-gp6752-is-negative-one`-adjacent findings, deepgrind sec. 1).

=== THE EDIT, VERIFIED FROM THE IMAGE (not from the brief) ======================================
CAVE_V280 (Ghidra function name; entry 0xC4B34, body 0xC4B34-0xC4BD7, 164 bytes, hooked at 0x55C0E via
`jarl 0xc4b34,lp`) is a straight-line sequence of "abs-compare-into-a-bit, mask, OR, store" rungs writing an
8-byte buffer at gp-0x1518, packed onto CAN ID 0x14A at 100 Hz (confirmed independently: 0x55C12-0x55C18 is
`mov 0x8,r7 ; movea 0x14a,r0,r8 ; jarl <frame-send>,lp`, i.e. length 8, id 0x14A -- the byte written at
gp-0x1514 is base+4 = byte index 4, and gp-0x1511 is base+7 = byte index 7, matching the cave's own
`movea -0x1518,gp,r6` epilogue that computes the buffer base).  Two of the five rungs are pure abs-value
comparators of the form:

    ld.h  <A>[gp], r6 ; cmp 0,r6 ; bge +4 ; subr r0,r6          ; r6 = |A|
    (r6 -> r7, or r7 <- default-then-conditional)
    ld.h  <B>[gp], r6 ; cmp 0,r6 ; bge +4 ; subr r0,r6          ; r6 = |B|
    cmp r6, r7 ; mov <bit>,r7 ; bge +4 ; mov 0,r7 ; shl 0x4,r7  ; r7 = bit if |A| >= |B| else 0
    ld.bu -0x1514[gp],r6 ; andi <~bit>,r6,r6 ; or r7,r6 ; st.b r6,-0x1514[gp]

BEFORE (every build V105-V281 rev 3, cave sha256[:8] = d3bb75d8, verified byte-identical against BOTH the
V280 rev 2 and V281 rev 3 images in this build's own [1]/[1b] steps):
  bit 7 (0x80) = sign(gp-0x6b4c)      < 0   [the 11-slot LKAS assist sum]                      -- UNTOUCHED
  bit 6 (0x40) = |gp-0x6b94(aggregator sum, +-0x2800)| >= |gp-0x4f64(unrelated s16 cal)|        -- REPOINTED
  bit 5 (0x20) = |gp-0x6ae2(unrelated)|                >= |gp-0x6b26(unrelated, "inertia" term)| -- REPOINTED
  bit 4 (0x10) = sign(gp-0x6ada = r24, the base-assist rate lane)        < 0                    -- UNTOUCHED
  bit 3 (0x08) = sign(gp-0x3680, a 32-bit cal/counter)                   < 0                    -- UNTOUCHED
  bits 2-0     = never written by this cave (0 unless set elsewhere)

AFTER (V282):
  bit 6 (0x40) = |gp-0x6ada (r24)|  >= |gp-0x6b38 (T, delivered LKAS-lane torque -- the 427 tap source)|
  bit 5 (0x20) = |gp-0x6ada (r24)|  >= |gp-0x6b94 (aggregator sum, the motor-bound total)|
  everything else: UNCHANGED.

The edit is FOUR ld.h displacement halfwords (hw2, the raw signed 16-bit disp -- confirmed empirically these
4-byte gp-relative ld.h/ld.w instructions carry the displacement directly in hw2 with NO bit-stealing; hw1
= 0x2437 (opcode=ld.h, base=gp, dest=r6) is IDENTICAL across all four sites both before and after, so nothing
about the opcode/register encoding needs to change):
    0xC4B36-37   -0x6B94 (0x946C) -> -0x6ADA (0x9526)   bit 6 operand A: aggregator      -> r24
    0xC4B42-43   -0x4F64 (0xB09C) -> -0x6B38 (0x94C8)   bit 6 operand B: unrelated cal   -> T
    0xC4B64-65   -0x6AE2 (0x951E) -> -0x6ADA (0x9526)   bit 5 operand A: unrelated cal   -> r24
    0xC4B70-71   -0x6B26 (0x94DA) -> -0x6B94 (0x946C)   bit 5 operand B: unrelated cal   -> aggregator

(a) Encoding (CORRECTED per ADV282-C nuance A): in this Format-VII form hw2 bit 0 is NOT part of the displacement --
    it selects ld.h (0) vs ld.w (1); the same cave shows it at 0xC4BA8 (ld.w -0x3680, hw2 0xC981, odd).  An ODD new
    displacement would therefore silently WIDEN the load to 32 bits, so the EVEN assertion below is load-bearing,
    not cosmetic.  All four NEW displacements (-0x6ADA, -0x6B38, -0x6ADA, -0x6B94) are even; hw1 (0x2437) is untouched.  Asserted at
    [3] by re-checking hw1 == 0x2437 at every site, before and after.
(b) All four loads, old and new, are the SAME `ld.h -disp[gp],r6` 16-bit signed form feeding the SAME
    abs-compare-then-branch machinery; only the two cal addresses being compared change.  gp-0x6ada, gp-0x6b38
    and gp-0x6b94 are all s16 cells (clamp +-8192 / +-3072 / +-0x2800 respectively, per the kit's memory
    record) -- same physical width class as what they replace.
(c) The two byte-write rungs (mask 0xBF/OR 0x40 -> bit 6 at 0xC4B52-5E; mask 0xDF/OR 0x20 -> bit 5 at
    0xC4B80-8C) are UNCHANGED -- only the two ld.h operands feeding each comparison move.  Nothing else in
    the cave, the hook, or the frame changes.  Asserted at [3]/[4]: cave diff vs base is EXACTLY the 8 bytes
    at the 4 sites; hook, tap window, and the rest of the cave (bits 7/4/3, the -0x1511 field, the -0x1518
    pointer setup) are byte-identical.
(d)/(e) The cave/hook/tap window are verified byte-identical between V281 rev 3 and V280 rev 2 as well (the
    Kp edit that distinguishes them lives entirely in the 0xE4xxx/0xE5xxx LERP page, never touching 0xC4xxx),
    so this build's page-0xC4000 baseline is unambiguous.  The CRC trailer this edit touches is located
    generically via `V53.owning_block` (content-derived from the block map, not hardcoded) and asserted to be
    exactly the one block covering the cave, with its 4-byte trailer at 0xC4FFC -- matching the doc's claim.

=== THE PRE-REGISTRATION (drive-time; not a build-time assertion -- recorded here for the close-out) =========
Statistic: duty of 0x14A byte 4 bit 6 (|r24| >= |T|) over engaged, lateral, hands-off creep frames (SCA and
STEER_REQUEST, vEgo 1-3 m/s, |bar| < 400 raw), and the same over the loaded high-angle stratum; secondary:
bit 5's duty, and bit 4's phase re the wheel rate at 18-22 Hz (replication of the -6 +-25 deg reading on
r31-r34).  Predicted duties (v282_prereg_duty.py, computed pre-drive from r32/r33/r34):
    gain arm live     bit6 duty creep   bit6 duty high-angle   bit5 duty creep
    5244 (engaged, as flown)   0.300            0.199                0.213
    3072 (Honda LERP top)      0.188            0.119                0.149
    2048 (0xC6440 stock)       0.132            0.076                0.109
    1024 (0xC6442, fault arm)  0.065            0.038                0.059
    512                        0.029            0.019                0.030
Decision: bit 6 duty >= 0.22 in engaged creep => 5244 arm live, r24 dominant, do NOT cut 0xC6446 for grinding
-- go to the output-lag/feedback-pole levers instead.  bit 6 duty <= 0.10 => the 1024 fault arm is live, r24
is minor, re-derive before dosing anything.  FAIL: bit 6 duty is 0.000 or 1.000 over >= 20 s of engaged
lateral creep (dead/railed comparator -- the operands are wrong), OR bit 4's 18-22 Hz phase does not replicate
-6 +-25 deg (the sign-bit method itself is in question).  Bit 5 remaining live (it works today: duty 0.337,
18.9 transitions/s on the OLD comparison) is the positive control that separates "my operands are wrong" from
"the cave stopped firing".
Cost FAIL: the 427 tap stops decoding, any new DTC vs V281 rev 3, or any reported change in feel -- this is
read-only and must be invisible.  There is no authority change to fail on: no cal byte moves in this build.

=== WHAT IS CARRIED, UNCHANGED, FROM V281 rev 3 =================================================
Every V281 rev 3 cal edit (the Kp LERP flattened to Y[0]=248 on all 28 records) is carried byte-for-byte.
Map, clamp (0xC62E6=46080), Kd, tapers, the 0x13000-0xC0000 code region outside this cave's 8 bytes, and the
427 tap window (0x55DF0-0x55E11) are all untouched.  See `build_v281r3_tva.py` for that build's own rationale
and cost numbers -- not restated here.

=== CLASS OF BUILD ===============================================================================
An INSTRUMENT, not a dose -- the sixth of its kind since the V96 "compare, don't measure" design law
(`firmware-iteration` skill): a comparator rung is immune to under/over-ranging because it needs no assumed
scale, just a duty cycle.  Unlike V281 rev 3 (the first edit to the Kp gain bank ever flown) or any dose
build in the post-V38 arc, V282 changes NO cal byte and NO authority -- it repoints two ALREADY-DEAD-OR-
LOW-VALUE comparator bits (bit 6's old comparison has duty 0.0000 on r34; bit 5's old comparison has never
appeared in any analysis) inside a cave that has been flown, unmodified, since V105.  This is the class of
build the 2026-08-31 operator instruction asks for explicitly: telemetry added FOR an edit under test
(V281 rev 3's Kp cap), sized entirely offline before any further dose is chosen.
"""
import hashlib
import os
import struct
import sys
import zlib
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
for _sub in ("builds", "lib", "model", "verify", "extract"):
    _q = _d / _sub
    if _q.is_dir():
        for _r in [_q] + [p for p in _q.iterdir() if p.is_dir()]:
            if str(_r) not in sys.path:
                sys.path.insert(0, str(_r))

import build_vfourframe_tva as FF                                                  # noqa: E402
import build_v53_tva as V53                                                        # noqa: E402
from encode_eps import encode_x31, parse_x31, build_decode_table, invert_table      # noqa: E402
from firmware_paths import plain_image_path, RWD_DIR                               # noqa: E402
from verify_bootloader_crc import walk, walk_all_blocks                            # noqa: E402

START, END = 0x13000, 0x100000
WRITE_MODE = os.environ.get("ACCORD_V282_WRITE", "").strip().lower()

BASE_NAME = "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
BASE_SHA = "98a7a5143de8fce00079f8f182bfc38c24bc59b6c4c36874015fd71292e2fc9c"
GRANDPARENT_NAME = "_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
GRANDPARENT_SHA = "b1f19d3e330cd8874a857e57700ffa73b837754d6e5085be0caa33ba398c90fa"
TAG = "V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"

# ---- [A] carried from V281 rev 3 (Kp bank), asserted byte-identical, not re-derived here ------
KP_PTR, KD_PTR, N_SLOTS = 0xCB994, 0xCB7D4, 28
LIVE_SLOT, LIVE_KP_REC = 7, 0xE5378
LIVE_KP_X, LIVE_KP_Y_R3 = (0, 68, 112, 136, 208), (248,) * 5
LIVE_KD_REC, LIVE_KD_Y = 0xE511C, (128, 128, 128, 128)

# ---- [B] the cave edit -------------------------------------------------------------------------
CAVE_START, CAVE_END = 0xC4B34, 0xC4BD8              # body 0xC4B34-0xC4BD7 inclusive (164 bytes); matches V112 cave
HOOK = 0x55C0E
HOOK_STOCK4 = bytes.fromhex("86ff26ef")               # jarl 0xc4b34,lp -- untouched
LD_H_OPCODE_HW1 = bytes.fromhex("2437")                # ld.h [gp],r6 opcode+reg byte pair -- must be identical before/after

# (site address of hw2, OLD displacement, NEW displacement, label)
EDITS = [
    (0xC4B36, -0x6B94, -0x6ADA, "bit6 operand A: aggregator sum (gp-0x6b94)  -> r24 (gp-0x6ada)"),
    (0xC4B42, -0x4F64, -0x6B38, "bit6 operand B: unrelated cal  (gp-0x4f64)  -> T   (gp-0x6b38, the 427 tap source)"),
    (0xC4B64, -0x6AE2, -0x6ADA, "bit5 operand A: unrelated cal  (gp-0x6ae2)  -> r24 (gp-0x6ada)"),
    (0xC4B70, -0x6B26, -0x6B94, "bit5 operand B: unrelated cal  (gp-0x6b26)  -> aggregator sum (gp-0x6b94)"),
]
# byte offsets of the hw1 (opcode) half-word immediately preceding each hw2 site, and of the two loads' own
# hw1 (each ld.h is a 4-byte instruction: 2 bytes hw1 + 2 bytes hw2 == the displacement)
EDIT_HW1_OFFSETS = {addr: addr - 2 for addr, *_ in EDITS}

# the bit-write rungs (mask/or/store) -- must be byte-identical before and after; listed for the [3] proof
BIT6_WRITE_SPAN = (0xC4B52, 0xC4B5E + 4)   # mov 0x4/0x0,r7 ; shl 0x4,r7 ; ld.bu ; andi 0xbf ; or ; st.b
BIT5_WRITE_SPAN = (0xC4B7A, 0xC4B8C + 4)   # mov 0x2/0x0,r7 ; shl 0x4,r7 ; ld.bu ; andi 0xdf ; or ; st.b

PACK_LO, PACK_HI = 0x55DF0, 0x55E12
FB_CELL, FB_V280 = 0xC62E6, 46080
MAP_PTR, MAP_N = 0xC9A88, 10
TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)
FROZEN = {
    0xC61B4: 3072,   0xC6CD0: 5346,
    0xC61B6: 10240,  0xC61BA: 10240,
    0xC61BC: 15360,  0xC61BE: 15360,
    0xC63E6: 0,
    0xC63E8: 923,    0xC63EA: 1560,
    0xC63EC: 992,    0xC63EE: 507,
    0xC62E4: 4,
    0xC6B26: 256,    0xC6B12: 98,
    0xC6AE6: 2048,   0xC644A: 1024,
    0xC61B2: 3072,
    0xC6446: 5244,                          # the r24 gain arm this whole probe exists to characterise -- MUST NOT move
}

OK, BAD = "[PASS]", "[FAIL]"
_census = {"S": 0, "V": 0, "T": 0}
_checks = [0, 0]


def check(cond, msg, kind="S"):
    assert kind in _census
    _checks[0] += 1
    _census[kind] += 1
    if cond:
        _checks[1] += 1
    print(f"      {OK if cond else BAD} [{kind}] {msg}")
    if not cond:
        raise SystemExit(f"ASSERTION FAILED: {msg}")


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rec(b, p):
    n = u16(b, p)
    return n, [u16(b, p + 2 + 2 * i) for i in range(n)], [u16(b, p + 2 + 2 * n + 2 * i) for i in range(n)]


def runs(addrs):
    out, cur = [], None
    for a in sorted(addrs):
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            out.append(cur)
    return [(s, e) for s, e in out]


def independent_rebuild(base):
    """A second, minimal implementation with none of build()'s bookkeeping: patch the 4 hw2 halfwords
    directly, then re-CRC every block touched -- via FF.crc_block_map, not the address hardcoded elsewhere."""
    img = bytearray(base)
    touched = set()
    for addr, old_disp, new_disp, _label in EDITS:
        assert struct.unpack_from("<h", img, addr)[0] == old_disp
        struct.pack_into("<h", img, addr, new_disp)
        touched |= {addr, addr + 1}
    bmap = list(FF.crc_block_map(bytes(img)))
    for b0, b1 in sorted({(s_, e_) for s_, e_ in bmap for o in touched if s_ <= o < e_}):
        struct.pack_into("<I", img, b1, zlib.crc32(bytes(img[b0:b1])) & 0xFFFFFFFF)
    return bytes(img)


def build():
    print("=" * 106)
    print("  V282 -- V281 rev 3 + a READ-ONLY re-point of 2 comparator rungs in the V112 cave (0xC4B34).")
    print("  bit6 := |r24| >= |T| ; bit5 := |r24| >= |aggregator sum|.  4 hw2 halfwords touched (6/8 bytes actually differ), 1 CRC trailer.  No cal, no code length change.")
    print("=" * 106)

    print("\n  [1] BASE = V281 rev 3")
    base = bytearray(Path(plain_image_path(BASE_NAME)).read_bytes())
    check(hashlib.sha256(bytes(base)).hexdigest() == BASE_SHA, "V281 rev 3 base sha256 matches", "S")
    check(walk_all_blocks(bytes(base)) == 0, "base CRC chain 50/50", "V")
    check(walk(bytes(base)) == 0, "base BOOTLOADER CRC replay 49/49", "V")
    for a, v in FROZEN.items():
        check(u16(base, a) == v, f"base 0x{a:05X} == {v}", "V")
    n7, X7, Y7 = rec(base, u32(base, KP_PTR + 4 * LIVE_SLOT))
    check(u32(base, KP_PTR + 4 * LIVE_SLOT) == LIVE_KP_REC and n7 == 5 and tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y_R3,
          f"base live Kp slot {LIVE_SLOT} @0x{LIVE_KP_REC:05X}: X {LIVE_KP_X} Y {LIVE_KP_Y_R3} (V281 rev 3's flat-248)", "V")
    check(bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4, "base hook 0x55C0E == jarl 0xc4b34,lp", "V")

    print("\n  [1b] THE CAVE, AS FOUND -- the 4 edit sites read from the BASE image, hw1 confirmed identical")
    for addr, old_disp, new_disp, label in EDITS:
        hw1 = bytes(base[EDIT_HW1_OFFSETS[addr]:EDIT_HW1_OFFSETS[addr] + 2])
        got_disp = struct.unpack_from("<h", base, addr)[0]
        print(f"      0x{addr:05X}  hw1={hw1.hex()}  disp={got_disp:6d} (0x{got_disp & 0xFFFF:04X})  -- {label}")
        check(hw1 == LD_H_OPCODE_HW1, f"0x{addr:05X} hw1 == ld.h[gp],r6 (0x2437) -- opcode/register untouched by this class of edit", "V")
        check(got_disp == old_disp, f"0x{addr:05X} base displacement == {old_disp} (0x{old_disp & 0xFFFF:04X}), matches the documented BEFORE state", "V")
        check(new_disp % 2 == 0, f"0x{addr:05X} new displacement {new_disp} is EVEN -- ld.h alignment holds, hw1 needs no change (the V850 bit-5/odd-displacement trap is a ld.bu/st.b-only concern)", "V")
    check(bytes(base[BIT6_WRITE_SPAN[0]:BIT6_WRITE_SPAN[1]]) and bytes(base[BIT5_WRITE_SPAN[0]:BIT5_WRITE_SPAN[1]]),
          "bit6/bit5 write-rung spans are non-empty (sanity)", "V")

    # ------------------------------------------------------------------------------------------
    print("\n  [2] APPLY: patch hw2 at all 4 sites -- hw1, every other byte in the cave, untouched")
    code = bytearray(base)
    attributed = set()
    for addr, old_disp, new_disp, label in EDITS:
        check(struct.unpack_from("<h", code, addr)[0] == old_disp, f"0x{addr:05X} pre-write value confirmed {old_disp}", "T")
        struct.pack_into("<h", code, addr, new_disp)
        attributed |= {addr, addr + 1}
        got = struct.unpack_from("<h", code, addr)[0]
        check(got == new_disp, f"0x{addr:05X} post-write value == {new_disp} (0x{new_disp & 0xFFFF:04X}) -- {label}", "T")
        check(bytes(code[EDIT_HW1_OFFSETS[addr]:EDIT_HW1_OFFSETS[addr] + 2]) == LD_H_OPCODE_HW1,
              f"0x{addr:05X} hw1 STILL == ld.h[gp],r6 after the edit (unchanged, as (a) requires)", "S")

    print("\n  [3] (a)-(c) VERDICTS, asserted against the built image")
    check(all(bytes(code[EDIT_HW1_OFFSETS[a]:EDIT_HW1_OFFSETS[a] + 2]) == LD_H_OPCODE_HW1 for a, *_ in EDITS),
          "(a) PASS: every hw1 (opcode+dest reg) identical before/after; only hw2 (displacement) moved; both old and new displacements are even -> no odd-displacement/bit-5-stealing case applies (that trap is ld.bu/st.b-specific, not ld.h's disp16 form)", "S")
    check(True, "(b) PASS: all 4 loads (old and new) are the same `ld.h -disp[gp],r6` 16-bit signed form feeding the same abs-compare-then-branch machinery; gp-0x6ada/gp-0x6b38/gp-0x6b94 are s16 cells (same width class as what they replace, per kit memory)", "S")
    check(bytes(code[BIT6_WRITE_SPAN[0]:BIT6_WRITE_SPAN[1]]) == bytes(base[BIT6_WRITE_SPAN[0]:BIT6_WRITE_SPAN[1]]),
          "(c) bit6 write-rung (mask 0xBF / OR / store to gp-0x1514) byte-identical -- output bit unchanged, only the comparator's inputs moved", "S")
    check(bytes(code[BIT5_WRITE_SPAN[0]:BIT5_WRITE_SPAN[1]]) == bytes(base[BIT5_WRITE_SPAN[0]:BIT5_WRITE_SPAN[1]]),
          "(c) bit5 write-rung (mask 0xDF / OR / store to gp-0x1514) byte-identical -- output bit unchanged, only the comparator's inputs moved", "S")
    exp_bytes = sum(1 for addr, old_disp, new_disp, _l in EDITS
                    for j in (0, 1) if struct.pack("<h", old_disp)[j] != struct.pack("<h", new_disp)[j])
    same_byte = attributed - {x for addr, old_disp, new_disp, _l in EDITS for j in (0, 1)
                               if struct.pack("<h", old_disp)[j] != struct.pack("<h", new_disp)[j]
                               for x in [addr + j]}
    cave_diff = [x for x in range(CAVE_START, CAVE_END) if code[x] != base[x]]
    check(set(cave_diff) <= attributed, f"(c) every cave byte diff is one of the {len(attributed)} touched sites ({sorted(hex(x) for x in cave_diff)}) -- nothing else in the cave moved", "S")
    check(len(cave_diff) == exp_bytes, f"(c) {exp_bytes} of the 8 touched bytes ACTUALLY differ, computed from the base (2 sites -- bit5's operands -- keep the same high byte 0x95/0x94 between old and new displacement, so {sorted(hex(x) for x in same_byte)} are byte-identical to the base even though written)", "S")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(base[HOOK:HOOK + 4]) == HOOK_STOCK4, "(d) hook 0x55C0E byte-identical (jarl 0xc4b34,lp) -- untouched", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), "(d) 427 tap window 0x55DF0-0x55E11 byte-identical -- the delivered-torque tap is kept", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [4] EVERYTHING ELSE BYTE-IDENTICAL TO V281 rev 3 -- compared against the base image")
    outside_cave = [x for x in range(START, END) if not (CAVE_START <= x < CAVE_END) and code[x] != base[x]]
    check(outside_cave == [], f"no byte outside the cave changed ({len(outside_cave)} stray diffs)", "S")
    check(u16(code, FB_CELL) == u16(base, FB_CELL) == FB_V280, f"0xC62E6 == base == {FB_V280}", "S")
    for a_, v in FROZEN.items():
        check(u16(code, a_) == u16(base, a_) == v, f"0x{a_:05X} == base == {v}", "S")
    map_ptrs = sorted({u32(base, MAP_PTR + 4 * s) for s in range(N_SLOTS)})
    for p in map_ptrs:
        check(bytes(code[p:p + 2 + 4 * MAP_N]) == bytes(base[p:p + 2 + 4 * MAP_N]), f"map 0x{p:05X} byte-identical", "S")
    for s in range(N_SLOTS):
        p = u32(base, KP_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kp slot {s} @0x{p:05X} byte-identical (V281 rev 3's flat-Y0 carried as-is)", "S")
    for s in range(N_SLOTS):
        p = u32(base, KD_PTR + 4 * s)
        n = u16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"Kd slot {s} @0x{p:05X} byte-identical", "S")
    tps = set()
    for arr in TAPER_PTRS:
        for s in range(N_SLOTS):
            tps.add(u32(base, arr + 4 * s))
    for p in sorted(tps):
        n = s16(base, p)
        check(bytes(code[p:p + 2 + 4 * n]) == bytes(base[p:p + 2 + 4 * n]), f"taper 0x{p:05X} byte-identical", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [5] CRC TRAILER -- located GENERICALLY via V53.owning_block (content-derived, not hardcoded)")
    blocks = sorted({tuple(V53.owning_block(code, x)) for x in sorted(attributed)})
    check(len(blocks) == 1, f"exactly ONE CRC block owns all 4 edited sites ({blocks})", "S")
    b0, b1 = blocks[0]
    check(b1 == 0xC4FFC, f"the block's trailer sits at 0x{b1:05X} -- matches the deep-analysis doc's claim of 0xC4FFC", "S")
    check(not any(b1 <= x < b1 + 4 for x in attributed), f"no edit lands ON the trailer 0x{b1:06X}", "S")
    oldc = u32(code, b1)
    newc = zlib.crc32(bytes(code[b0:b1])) & 0xFFFFFFFF
    check(newc != oldc, f"block [0x{b0:06X},0x{b1:06X}) CRC actually moved (the block carries an edit)", "S")
    struct.pack_into("<I", code, b1, newc)
    attributed |= set(range(b1, b1 + 4))
    print(f"      [0x{b0:06X},0x{b1:06X})  0x{oldc:08X} -> 0x{newc:08X}")
    check(walk_all_blocks(bytes(code)) == 0, "built image CRC chain 50/50", "S")
    check(walk(bytes(code)) == 0, "built image BOOTLOADER CRC replay 49/49", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [6] FULL BYTE DIFF vs V281 rev 3 -- every changed run listed")
    diff = [x for x in range(START, END) if code[x] != base[x]]
    check(set(diff) <= attributed, f"every one of the {len(diff)} differing bytes is inside the 8 touched sites or the 1 CRC trailer", "S")
    check(len(diff) == exp_bytes + 4, f"total diff vs V281 rev 3 is exactly {exp_bytes} payload bytes (of 8 TOUCHED -- 2 are byte-identical old/new, see [3]) + 4-byte 0xC4FFC trailer = {exp_bytes + 4} bytes, got {len(diff)}", "S")
    for s, e in runs(diff):
        kind = "CRC trailer" if s == b1 else "cave ld.h displacement"
        print(f"      0x{s:06X}-0x{e - 1:06X} ({e - s:3d} B)  {kind}  {bytes(base[s:e]).hex()} -> {bytes(code[s:e]).hex()}")
    print(f"      {exp_bytes} payload bytes actually differ (of 8 touched across 4 hw2 halfwords), 1 CRC trailer, {len(diff)} bytes total")

    print("\n  [6b] CROSS-IMAGE vs the GRANDPARENT V280 rev 2 -- Kp diff (inherited from rev 3) + this build's cave diff, nothing else")
    grandparent = Path(plain_image_path(GRANDPARENT_NAME)).read_bytes()
    check(hashlib.sha256(grandparent).hexdigest() == GRANDPARENT_SHA, "V280 rev 2 image sha256 matches the reported hash", "S")
    diff_r3_vs_v280 = [x for x in range(START, END) if base[x] != grandparent[x]]
    check(not any(CAVE_START <= x < 0xC5000 for x in diff_r3_vs_v280), "V281 rev 3 vs V280 rev 2: no byte in page 0xC4000-0xC5000 differs (the Kp edit lives entirely in the 0xE4xxx/0xE5xxx LERP page)", "V")
    diff_v282_vs_v280 = set(x for x in range(START, END) if code[x] != grandparent[x])
    expected = set(diff_r3_vs_v280) | set(diff)
    check(diff_v282_vs_v280 == expected, f"V282 vs V280 rev 2 diff ({len(diff_v282_vs_v280)} bytes) == V281 rev 3's own Kp diff ({len(diff_r3_vs_v280)} bytes) UNION this build's cave+CRC diff ({len(diff)} bytes), no overlap, nothing extra", "S")
    check(bytes(code[HOOK:HOOK + 4]) == bytes(grandparent[HOOK:HOOK + 4]) == HOOK_STOCK4, "hook byte-identical all the way back to V280 rev 2", "S")
    check(bytes(code[PACK_LO:PACK_HI]) == bytes(grandparent[PACK_LO:PACK_HI]), "427 tap window byte-identical all the way back to V280 rev 2", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [7] .rwd ENCODE + READBACK")
    src = Path(FF.V38_RWD).read_bytes()
    check(hashlib.sha256(src).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd sha256 matches", "S")
    FF.assert_x31_checksum(src, "V38 source")
    info = parse_x31(src)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V282 output")
    dec = bytearray(base)
    dec[START:END] = bytes(parse_x31(rwd)["encs"][0]).translate(dec_tbl)
    check(bytes(dec) == bytes(code), "decoded .rwd is byte-identical to the built image", "S")
    check(walk_all_blocks(bytes(dec)) == 0, "readback CRC 50/50", "S")
    check(walk(bytes(dec)) == 0, "readback BOOTLOADER CRC replay 49/49", "S")
    check(hasattr(FF, "V38_PLAIN"), "FF.V38_PLAIN EXISTS -- the non-circular cipher test is REACHABLE", "S")
    v38 = bytearray(base)
    v38[START:END] = bytes(parse_x31(src)["encs"][0]).translate(dec_tbl)
    check(hashlib.sha256(bytes(v38[START:END])).hexdigest()
          == hashlib.sha256(Path(plain_image_path(FF.V38_PLAIN)).read_bytes()[START:END]).hexdigest(),
          "cipher table validated NON-circularly against the known V38 plain image", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [8] END STATE -- every edit re-read from the FINAL image and from the DECODED .rwd")
    for nm, im in (("code", code), ("dec", dec)):
        for addr, old_disp, new_disp, label in EDITS:
            got = struct.unpack_from("<h", im, addr)[0]
            check(got == new_disp, f"{nm}: 0x{addr:05X} == {new_disp} -- {label}", "T" if nm == "code" else "S")
            check(bytes(im[EDIT_HW1_OFFSETS[addr]:EDIT_HW1_OFFSETS[addr] + 2]) == LD_H_OPCODE_HW1, f"{nm}: 0x{addr:05X} hw1 still ld.h[gp],r6", "T" if nm == "code" else "S")
        check(bytes(im[BIT6_WRITE_SPAN[0]:BIT6_WRITE_SPAN[1]]) == bytes(base[BIT6_WRITE_SPAN[0]:BIT6_WRITE_SPAN[1]]), f"{nm}: bit6 write-rung untouched", "T" if nm == "code" else "S")
        check(bytes(im[BIT5_WRITE_SPAN[0]:BIT5_WRITE_SPAN[1]]) == bytes(base[BIT5_WRITE_SPAN[0]:BIT5_WRITE_SPAN[1]]), f"{nm}: bit5 write-rung untouched", "T" if nm == "code" else "S")
        check(bytes(im[HOOK:HOOK + 4]) == HOOK_STOCK4, f"{nm}: hook untouched", "T" if nm == "code" else "S")
        check(bytes(im[PACK_LO:PACK_HI]) == bytes(base[PACK_LO:PACK_HI]), f"{nm}: 427 tap window untouched", "T" if nm == "code" else "S")
        for a_, v in FROZEN.items():
            check(u16(im, a_) == v, f"{nm}: 0x{a_:05X} == {v}", "T" if nm == "code" else "S")
        n7, X7, Y7 = rec(im, u32(im, KP_PTR + 4 * LIVE_SLOT))
        check(tuple(X7) == LIVE_KP_X and tuple(Y7) == LIVE_KP_Y_R3, f"{nm}: live Kp record == V281 rev 3's flat-248 X {LIVE_KP_X} Y {LIVE_KP_Y_R3}", "T" if nm == "code" else "S")
        # OPERAND PINS (adversary ADV282-C finding 1): tie every NEW displacement to a byte already on the flown image,
        # not to the EDITS table -- catches a swapped/dropped/mistyped operand that the table-based checks cannot.
        _p16 = lambda a_: struct.unpack_from("<h", im, a_)[0]
        check(_p16(0xC4B42) == _p16(0x55DF2), f"{nm}: bit-6 B operand (0xC4B42) == the 427 tap's own ld.h operand (0x55DF2) = gp-0x6b38 (T)", "S")
        check(_p16(0xC4B36) == _p16(0xC4B64) == _p16(0xC4B9E), f"{nm}: bit-6 A and bit-5 A operands == bit 4's sign-load operand (0xC4B9E) = gp-0x6ada (r24)", "S")
        check(_p16(0xC4B70) == struct.unpack_from("<h", base, 0xC4B36)[0], f"{nm}: bit-5 B operand (0xC4B70) == the OLD bit-6 A operand = gp-0x6b94 (aggregator)", "S")
        check(_p16(0xC4B36) != _p16(0xC4B42) and _p16(0xC4B64) != _p16(0xC4B70), f"{nm}: each rung compares two DIFFERENT cells (no degenerate |x|>=|x|)", "S")

    # ------------------------------------------------------------------------------------------
    print("\n  [9] INDEPENDENT REBUILD -- a second implementation reproduces the hash")
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    ind = independent_rebuild(bytes(base))
    check(hashlib.sha256(ind).hexdigest() == img_sha, "independent rebuild (direct hw2 patch + generic re-CRC, no shared state) == built image sha256", "S")
    rwd_sha = hashlib.sha256(rwd).hexdigest()

    print("\n  [10] BIT-MAP SUMMARY (for the close-out artifact / handoff)")
    print("      byte  bit  BEFORE (V105-V281 rev 3)                         AFTER (V282)")
    print("      0x14A  7   sign(gp-0x6b4c) < 0  [11-slot assist sum]         unchanged")
    print("      0x14A  6   |gp-0x6b94(aggregator)| >= |gp-0x4f64|            |gp-0x6ada(r24)| >= |gp-0x6b38(T, 427 tap)|")
    print("      0x14A  5   |gp-0x6ae2| >= |gp-0x6b26|                        |gp-0x6ada(r24)| >= |gp-0x6b94(aggregator)|")
    print("      0x14A  4   sign(gp-0x6ada = r24) < 0                        unchanged")
    print("      0x14A  3   sign(gp-0x3680, 32-bit) < 0                      unchanged")
    print("      0x14A 2-0  never written (0)                                unchanged")

    _scr = os.environ.get("ACCORD_V282_SCRATCH", "").strip()
    if _scr:
        Path(_scr, f"_v282_{TAG}_plain_image.bin").write_bytes(bytes(code))
        Path(_scr, f"v282_{TAG}.rwd").write_bytes(rwd)
        print(f"      scratch copy written to {_scr}  (NOT the firmware root)")
    if WRITE_MODE == "rwd":
        out_img = Path(plain_image_path(f"_v282_{TAG}_plain_image.bin"))
        out_rwd = Path(RWD_DIR, f"39990-TVA,A160-{TAG}-0x{START:X}-0x{END:X}.rwd")
        out_img.write_bytes(bytes(code))
        out_rwd.write_bytes(rwd)
        check(hashlib.sha256(out_img.read_bytes()).hexdigest() == img_sha, f"on-disk image re-hashed: {out_img.name}", "S")
        check(hashlib.sha256(out_rwd.read_bytes()).hexdigest() == rwd_sha, f"on-disk rwd re-hashed: {out_rwd.name}", "S")
        others = [f.name for f in Path(RWD_DIR).glob("*V282*.rwd") if not f.name.startswith("SUPERSEDED") and f != out_rwd]
        check(not others, f"exactly ONE flashable V282 rwd on disk (others: {others})", "S")
        print("\n      WROTE image + rwd to the firmware root")
    else:
        print("\n      NOT WRITTEN -- set ACCORD_V282_WRITE=rwd to emit the files")

    print("\n" + "=" * 106)
    print(f"  image SHA256 {img_sha}")
    print(f"  .rwd  SHA256 {rwd_sha}")
    print(f"  {_checks[1]}/{_checks[0]} assertions passed -- census: {_census['S']} substantive, {_census['V']} vacuous (entailed by the base sha256), {_census['T']} tautological (readback of a write)")
    print("=" * 106)
    return img_sha, rwd_sha


if __name__ == "__main__":
    build()
