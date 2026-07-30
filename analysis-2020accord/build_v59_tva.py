#!/usr/bin/env python3
"""build_v59_tva.py -- V59 = V58 with the cave payload replaced by the BOOST-INDEX DEPTH probe.

WHAT V59 IS
-----------
A POST-PROCESSOR over `_v58_plain_image.bin`. It transcribes nothing from V58 -- not the cave, not the
hook, not the calibration. Same principle V58 used over V57 and V56 used over V55.

*** V59 CHANGES NOTHING BUT THE CAVE PAYLOAD. *** V57's calibration (the 0xC646C decoupling) is on the
car, fault-free through V58's 14-segment drive, and stays byte-identical. Same cave base 0xC4B34, same
hook 0x55C0E, same 68-byte extent. Only the MAIN CRC block moves; the CAL CRC must NOT.

WHY THIS PROBE -- what V58's drive established, and the one thing it could not
-----------------------------------------------------------------------------
V58 flew clean (route `2b`, 14 segments, 83,959 frames; ST==4 = 0; no steerUnavailable/canError/
controlsMismatch). Its rlogs settled a lot and left exactly one gap:

  * The grinding is a FIXED ~20.9 Hz, CREEP-ONLY, closed-loop mode requiring APPLIED LKAS torque.
    Speed-matched engaged/disengaged (the collinearity confound is finally broken -- seg 13 gives 60 s
    of moving-but-disengaged at 0.5-4.8 m/s): prominence median 122.7x vs 3.6x, i.e. the resonance is
    ABSENT disengaged, not merely smaller. Dies ~20x above 6 m/s. Order ~20 vs wheel order 1 => not the
    tyre. `f = a*v + b` fits a = 0 within 0.12-1.48 sigma; a = 0.177 REJECTED at 3.2-7.1 sigma.
  * bit5 = 0 in all 35,964 frames => `gp-0x6bbe` NEVER reaches its +-512 ceiling. The ceiling
    `0xD20C0` is ELIMINATED as a lever; `K1` @`0xD200C` = 43 keeps its headroom.
  * bit6 was VOID BY CONSTRUCTION. `gp-0x6bbe` is DC-dominated during a turn -- it crosses zero
    0.00-1.10 /s where a 22 Hz sign flip needs ~44/s. A sign comparator can only carry phase for a
    signal that actually crosses zero. The damping-sign question is STILL OPEN. (Pooling runs to force
    an answer manufactures a splice artifact: within the four low-speed engaged runs bit6 has 5/0/0/1
    transitions, so a concatenated coherence of ~0.5 at 25 Hz is step discontinuities at the joins.)
  * bit4 DID fire: `sign(gp-0x6b9a)` toggles at 20.93 Hz, per-run coherence 0.649/0.970/0.769/0.881
    against the bus angle-rate, own-spectrum peak 10.8x median, and -- decisively -- 13.69 toggles/s
    ENGAGED vs 0.61 DISENGAGED at matched creep speed, with the 20.9 Hz line present in one arm and
    absent in the other. The disengaged arm has MORE driver angle and effort, so this is not the wheel
    merely being shaken.

THE MECHANISM V59 TESTS -- byte-verified 2026-07-30, and it corrects build_v58's own docstring
----------------------------------------------------------------------------------------------
build_v58_tva.py says `gp-0x6b9a` "indexes boost's NON-flat table (0xD28DC)". *** THAT IS WRONG. ***
Resolved from image bytes, little-endian, all 34 modes:

    0xca4f4[mode]  -> ... 0xD08DC 0xD18DC 0xD28DC ...     0xD28DC PRESENT   (LERP1)
    0xca23c[mode]  -> ... 0xD0888 0xD1888 0xD2888 ...     0xD28DC ABSENT    (LERP4)
    0xca154 / 0xc7970 / 0xca06c / 0xca40c / 0xca324       0xD28DC ABSENT

`0xD28DC` is real (count=6, X=(0,512,1490,2529,3645,5120), Y=(16384,14657,11672,9365,8244,8187)) but it
hangs off `0xca4f4`, not `0xca23c`. And BOTH LERPs are indexed by **`gp-0x6ba6`**, not `gp-0x6b9a`
(r9 loaded @0x34b6e, relayed via `gp-0x6bba` because the 4-state FSM clobbers r9).

`gp-0x6b9a`'s ONLY live consumer in FUN_00034a72 is a 5-input plausibility gate: `|gp-0x6b9a| <= 25600`
(`addi 0x6400 / ori 0xc801 / cmp / bnc` @0x34c9c-cb4) ANDed with four sibling range checks into r21,
which zeroes r24 @0x34fc8. Its SIGN has no effect on the output at all. Two of its three reads in that
function (@0x34b5e, @0x34b68) are DEAD -- `tp+0x7499 = 1` (byte-verified) takes the branch @0x34b3c.

*** THE KEY FACT: `gp-0x6ba6 == |gp-0x6b9a|`. *** Both are written by FUN_0003b66a from the same r28:

    0x3b874  cmp   r0,r28
    0x3b876  mov   r28,r13
    0x3b878  bge   0x3b886        ; r28 >= 0 -> r13 = r28
    0x3b87a  subr  r0,r13         ; else     -> r13 = -r28          r13 = |r28|
    0x3b87e  ori   0xffff,r0,r13  ; FAULT path: r13 = 0xFFFF
    0x3b882  movea 0x7fff,r0,r28  ; FAULT path: r28 = 0x7FFF
    0x3b892  st.h  r13,-0x6ba6[gp]    ; SOLE writer (byte-scan: 1 st.h image-wide)
    0x3b8b0  st.h  r28,-0x6b9a[gp]    ; SOLE writer (byte-scan: 1 st.h image-wide)

So the table index is the FULL-WAVE RECTIFICATION of the signal V58 watched cross zero at 20.93 Hz.
It therefore has a MINIMUM at every zero crossing and sweeps the boost amplitude curve at **2x the mode
frequency (~41.9 Hz)**, on the main assist path, with a 2:1 authority range (16384 -> 8187).

*** BUT THE DEPTH IS UNKNOWN, AND DEPTH IS EVERYTHING. *** A sign bit carries no amplitude. The swing
the mechanism actually delivers is set by how far up the curve the index climbs:

    index stays < 512   ->  Y in 16384..14657,  swing <= 1.12x   (weak)
    index reaches 1024  ->  Y in 16384..12938,  swing ~  1.27x
    index reaches 2048  ->  Y in 16384..10360,  swing ~  1.58x
    index reaches 2529  ->  Y in 16384.. 9365,  swing ~  1.75x   (X3, near the steepest part)
    index >= 5120       ->  Y in 16384.. 8187,  swing ~  2.00x   (the full range)

⚠ NOT "inert below 512": the LERP interpolates from X = 0, so the coefficient is pinned at 16384 only
at exactly zero. A 12% gain modulation at ~2x the mode frequency is still a parametric drive, just a
modest one -- and it has to be weighed against GATE 2, since both curves sit on the BASE ASSIST path
and moving them changes manual feel. V59 measures which regime we are in.

WHAT IT MEASURES -- CAN 0x14A byte4, 100 Hz
-------------------------------------------
    bit 7 = 1                        LIVENESS (constant; field==0 => the cave did not fire => VOID)
    bit 6 = (gp-0x6ba6 <  0)         the 0xFFFF FAULT SENTINEL from FUN_0003b66a's input gates
    bit 5 = ((gp-0x6ba6 >>  9) == 0) index < 512   -- BELOW X1: no modulation at all
    bit 4 = ((gp-0x6ba6 >> 10) == 0) index < 1024
    bit 3 = ((gp-0x6ba6 >> 11) == 0) index < 2048
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

A THERMOMETER, not four independent flags. Thresholds are nested, so bit5 => bit4 => bit3 always; any
frame violating that monotonicity is a DECODE ERROR, not a reading. That self-check is free and it is
the reason the bits are "below" rather than "at or above": the inverted sense is what lets the whole
cave run on BNE and BGE, the only two condition codes PINNED to real instruction instances in this
image. Introducing an unpinned cond field into a cave is not worth a polarity convenience.

Thresholds are powers of two so each level is one `sar` of the SAME register -- no second register, no
16-bit immediate, no `cmp` against a constant. 512 is X1 exactly; 1024 and 2048 bracket X2 = 1490 and
X3 = 2529, which is where Y falls fastest (16384 -> 14657 -> 11672 -> 9365). Above X4 = 3645 the curve
is essentially flat (8244 -> 8187), so resolution up there would buy nothing.

Reading `gp-0x6ba6` SIGNED is deliberate: the cell is a magnitude, so it is non-negative in normal
operation and the only way bit6 can set is the 0xFFFF sentinel. That both tests the fault hypothesis
for free AND disambiguates an all-clear thermometer (huge value) from a fault (bit6 set).

CAVE DISCIPLINE
---------------
Read-only. One ld.h, three arithmetic shifts, four compares against r0, no arithmetic on any signal, no
new RAM, two scratch registers only (r6 = value, r7 = accumulator) -- exactly V58's register budget.
66 bytes against the 68-byte extent that V55/V57/V58 have all flown. *** Every encoder and both
condition codes are already pinned; V59 introduces NONE. *** Code caves are this kit's only bricking
class (V24, V27, V48B all bricked the ECU), which is why the base/hook/extent are reused, not moved.

DELIBERATELY NOT PROBED: `gp-0x6bbe`'s damping sign. V58 showed a sign bit cannot answer it, and the
fix (a thermometer on |gp-0x6bbe|) does not fit alongside this one. The mechanism question is the
higher-value measurement -- the damping sign only decides which way to move K1, and K1 is only worth
moving once we know what is actually modulating. That is V60.

Decoder: rlog-tools/decode_v59_boostindex.py
"""
import hashlib
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF
import build_v53_tva as V53
import build_v54_tva as V54
import build_v55_tva as V55
import build_v57_tva as V57
import build_v58_tva as V58

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from firmware_paths import plain_image_path, RWD_DIR
from verify_bootloader_crc import walk, walk_all_blocks
from build_vfourframe_tva import GP, R0, R6, R7

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged from V55/V57/V58
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- the probe ------------------------------------------------------------------------------------
INDEX_DISP = 0x6ba6         # gp-0x6ba6 == |gp-0x6b9a|, the LERP1/LERP4 index. Read SIGNED on purpose.

# LERP1 @0xD28DC (via pointer table 0xca4f4, mode 10) -- the curve the index actually walks.
LERP1_ADDR = 0xD28DC
LERP1_X = (0, 512, 1490, 2529, 3645, 5120)
LERP1_Y = (16384, 14657, 11672, 9365, 8244, 8187)
# LERP4 @0xD2888 (via 0xca23c, mode 10) -- the second consumer of the SAME index.
LERP4_ADDR = 0xD2888
LERP4_X = (0, 307, 1024, 1741, 3072, 6144)
LERP4_Y = (16384, 14392, 10265, 8997, 8176, 8176)

SHIFT_512, SHIFT_1024, SHIFT_2048 = 9, 10, 11   # emitted as sar 9, then sar 1, then sar 1

BIT_LIVE, BIT_FAULT, BIT_LT512, BIT_LT1024, BIT_LT2048 = 0x80, 0x40, 0x20, 0x10, 0x08

COND_BNE = V57.COND_BNE     # 0xA, Z == 0   -- pinned to the real `bne 0x2a246` @0x2a240
COND_BGE = V57.COND_BGE     # 0xE, signed >= -- pinned to the real `bge 0x2a222` @0x2a21a

TAG = "LKAS-4x-mss0-decouple0xC646C-boostindexdepth-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V59-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v59_plain_image.bin"))
V58_BIN = str(plain_image_path("_v58_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def _self_check_encoders():
    """Every encoder must reproduce a real instance, or an already-self-checked ancestor encoder."""
    V58._self_check_encoders()          # inherits V57/V55/V54/FF self-checks

    # sar: pinned in V55 to the real `sar 0xf,r11` @0x2a202 (bytes `af5a`). Decode OUR operands out
    # of the encoding rather than trusting the helper -- Format II packs (reg2<<11)|(op<<5)|imm5.
    for sh in (SHIFT_512, 1):
        hw = struct.unpack("<H", V55.sar(sh, R6))[0]
        assert (hw >> 11) == R6, f"sar reg2 field is {hw >> 11}, expected r{R6}"
        assert ((hw >> 5) & 0x3F) == 0x15, "sar opcode field is not 0x15"
        assert (hw & 0x1F) == sh, f"sar imm5 field is {hw & 0x1F}, expected {sh}"
    assert V55.sar(SHIFT_512, R6) != V55.sar(1, R6), "sar ignores its immediate"

    # ld.h displacement: second halfword must be the two's-complement of the gp offset, LSB CLEAR.
    # (LSB set would be the ld.hu/ld.w extended form -- the `hw2 = disp|1` trap this kit has hit.)
    raw = V55.ldh(INDEX_DISP, R6)
    assert len(raw) == 4, "ld.h must be 4 bytes"
    d = struct.unpack_from("<H", raw, 2)[0]
    assert d == (0x10000 - INDEX_DISP) & 0xFFFF, "ld.h displacement halfword is wrong"
    assert d & 1 == 0, "displacement LSB must be CLEAR -- LSB set is ld.hu/ld.w, not ld.h"

    # Only PINNED condition codes. V59 introduces none.
    assert FF.bcond(COND_BNE, +6).hex() == "ba05", "bne +6 fails the real instance @0x2a240"
    assert FF.bcond(COND_BGE, +6).hex() == "be05", "bge +6 drifted from V55/V57/V58"

    for bit in (BIT_FAULT, BIT_LT512, BIT_LT1024, BIT_LT2048):
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"movea 0x{bit:x},r7,r7 malformed"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"

    # The five bits must be distinct single bits in 7:3, leaving 2:0 for the stock status field.
    bits = (BIT_LIVE, BIT_FAULT, BIT_LT512, BIT_LT1024, BIT_LT2048)
    assert len(set(bits)) == 5 and all(b & (b - 1) == 0 for b in bits), "probe bits are not distinct"
    assert sum(bits) == 0xF8, f"probe bits must occupy exactly 7:3, got 0x{sum(bits):02X}"
    assert sum(bits) & PAYLOAD_KEEP_MASK == 0, "probe bits collide with the preserved status bits"


def build_cave():
    """pack_boost_index_depth -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.h  -0x6ba6[gp],r6   ; |gp-0x6b9a| = the LERP1/LERP4 index (signed read: -1 => sentinel)
        cmp   r0,r6
        bge   +6               ; >= 0 -> normal, leave bit6 clear
        movea 0x40,r7,r7       ; bit6 = 0xFFFF FAULT SENTINEL from FUN_0003b66a
      fault_done:
        sar   9,r6             ; r6 = index >> 9
        cmp   r0,r6
        bne   +6               ; != 0 -> index >= 512, leave bit5 clear
        movea 0x20,r7,r7       ; bit5 = index < 512   (BELOW X1 -- nothing modulates)
      lt512_done:
        sar   1,r6             ; r6 = index >> 10
        cmp   r0,r6
        bne   +6               ; != 0 -> index >= 1024
        movea 0x10,r7,r7       ; bit4 = index < 1024
      lt1024_done:
        sar   1,r6             ; r6 = index >> 11
        cmp   r0,r6
        bne   +6               ; != 0 -> index >= 2048
        movea 0x8,r7,r7        ; bit3 = index < 2048
      lt2048_done:
        ld.bu -0x1514[gp],r6   ; CAN-330 payload byte4
        andi  0x7,r6,r6        ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]
        movea -0x1518,gp,r6    ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.movea(BIT_LIVE, R0, R7), "movea 0x80,r0,r7    ; bit7 LIVENESS")

    emit(V55.ldh(INDEX_DISP, R6), f"ld.h -0x{INDEX_DISP:x}[gp],r6  ; |gp-0x6b9a| = the LERP index")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BGE, +6), "bge +6              ; >= 0 -> not the sentinel")
    emit(FF.movea(BIT_FAULT, R7, R7), "movea 0x40,r7,r7    ; bit6 = 0xFFFF FAULT SENTINEL")
    fault_done = CAVE_BASE + len(body)

    emit(V55.sar(SHIFT_512, R6), f"sar {SHIFT_512},r6             ; index >> {SHIFT_512}")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> index >= 512")
    emit(FF.movea(BIT_LT512, R7, R7), "movea 0x20,r7,r7    ; bit5 = index < 512  (BELOW X1)")
    lt512_done = CAVE_BASE + len(body)

    emit(V55.sar(1, R6), f"sar 1,r6             ; index >> {SHIFT_1024}")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> index >= 1024")
    emit(FF.movea(BIT_LT1024, R7, R7), "movea 0x10,r7,r7    ; bit4 = index < 1024")
    lt1024_done = CAVE_BASE + len(body)

    emit(V55.sar(1, R6), f"sar 1,r6             ; index >> {SHIFT_2048}")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> index >= 2048")
    emit(FF.movea(BIT_LT2048, R7, R7), "movea 0x8,r7,r7     ; bit3 = index < 2048")
    lt2048_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # Every branch must land exactly on its label. Located BY POSITION, not by content: this cave
    # reuses `bne +6` THREE times, so a content-based lookup would be ambiguous.
    for idx, label, name in [(3, fault_done, "bge->fault_done"),
                             (7, lt512_done, "bne->lt512_done"),
                             (11, lt1024_done, "bne->lt1024_done"),
                             (15, lt2048_done, "bne->lt2048_done")]:
        addr, raw, _ = listing[idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"

    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V59 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B)"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


def decode_field(byte4):
    """Decode 0x14A byte4 into V59's five bits. field == 0 => THE CAVE DID NOT FIRE (VOID).

    Returns `monotonic=False` when the thermometer is inconsistent -- that is a decode error (wrong
    build on the car, or a corrupt frame), never a physical reading.
    """
    field = (byte4 >> 3) & 0x1F
    if field == 0:
        return None
    lt512 = bool(byte4 & BIT_LT512)
    lt1024 = bool(byte4 & BIT_LT1024)
    lt2048 = bool(byte4 & BIT_LT2048)
    if lt512:
        lo, hi = 0, 512
    elif lt1024:
        lo, hi = 512, 1024
    elif lt2048:
        lo, hi = 1024, 2048
    else:
        lo, hi = 2048, None
    return {
        "live": bool(byte4 & BIT_LIVE),
        "fault_sentinel": bool(byte4 & BIT_FAULT),
        "index_lo": lo,
        "index_hi": hi,
        "monotonic": (not lt512 or lt1024) and (not lt1024 or lt2048),
    }


def assert_probe_sites(code, label="V59"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V58 cave remnants survive past our payload"


def assert_index_chain(code, label="V59"):
    """The probe is only interpretable if the tables it is calibrated against are still stock.

    Both LERPs are indexed by gp-0x6ba6, so BOTH must be verified -- and the pointer tables that
    resolve to them, because `0xD28DC` hangs off `0xca4f4` and `0xD2888` off `0xca23c` (getting these
    two the wrong way round is exactly the error in build_v58's docstring).
    """
    for addr, xs, ys, nm in ((LERP1_ADDR, LERP1_X, LERP1_Y, "LERP1"),
                             (LERP4_ADDR, LERP4_X, LERP4_Y, "LERP4")):
        n = u16(code, addr)
        assert n == len(xs), f"{label}: {nm} @0x{addr:05X} point count is {n}, expected {len(xs)}"
        got_x = struct.unpack_from(f"<{n}H", code, addr + 2)
        got_y = struct.unpack_from(f"<{n}H", code, addr + 2 + 2 * n)
        assert got_x == xs, f"{label}: {nm} X row moved: {got_x} != {xs}"
        assert got_y == ys, f"{label}: {nm} Y row moved: {got_y} != {ys}"
    # the pointer tables must still resolve to those two LERPs for the SAME mode
    m1 = [struct.unpack_from("<I", code, 0xca4f4 + 4 * m)[0] for m in range(34)]
    m4 = [struct.unpack_from("<I", code, 0xca23c + 4 * m)[0] for m in range(34)]
    assert LERP1_ADDR in m1, f"{label}: 0x{LERP1_ADDR:05X} not reachable from 0xca4f4"
    assert LERP1_ADDR not in m4, f"{label}: 0x{LERP1_ADDR:05X} unexpectedly reachable from 0xca23c"
    assert LERP4_ADDR in m4, f"{label}: 0x{LERP4_ADDR:05X} not reachable from 0xca23c"
    assert m1.index(LERP1_ADDR) == m4.index(LERP4_ADDR), \
        f"{label}: the two LERPs resolve at different modes -- they must share one index"
    # the dead-branch condition that makes gp-0x6ba6 (not the EMA fallback) the live index
    assert code[0xC6498] == 1 and code[0xC6499] == 1, \
        f"{label}: tp+0x7498/0x7499 are not both 1 -- the gp-0x6ba6 path is no longer the live one"


def build():
    if not os.path.exists(V58_BIN):
        print(f"  {V58_BIN} missing -- running the V58 builder first\n")
        V58.build()
    v58 = bytearray(open(V58_BIN, "rb").read())
    print(f"  V58 source {V58_BIN}\n    SHA256 {hashlib.sha256(bytes(v58)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v58, "V58 source")
    assert walk(bytes(v58), label="V58 source") == 0
    assert walk_all_blocks(bytes(v58), label="V58 source") == 0
    V58.assert_probe_sites(v58, "V58 source")        # V58's OWN cave must be intact first
    V55.assert_variant_tables(v58)
    V57.assert_decoupled(v58, "V58 source")
    assert u16(v58, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V58 source lost the lockout edit"
    assert_index_chain(v58, "V58 source")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v58)

    # ---- pre-flight: V57's calibration must be exactly what we expect to CARRY FORWARD ------------
    assert u16(code, V57.PRIVATE_ADDR) == V57.GAIN_4X, "the private LKAS gain is not 3564"
    assert u16(code, V57.GAIN_ADDR) == V57.GAIN_STOCK, "the shared sensor scale is not stock 891"
    assert u16(code, V57.DISP_OFF) == V57.DISP_NEW, "the retargeted displacement is missing"
    assert u16(code, V57.LOAD_ADDR) == V57.INSN_HW1, "the opcode/register halfword moved"

    assert 0 < INDEX_DISP <= 0x7FFF
    assert INDEX_DISP % 2 == 0, "ld.h needs an EVEN displacement"

    # ---- THE ONLY EDIT: replace the cave payload -------------------------------------------------
    print(f"\n  THE PROBE -- replace V58's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes, V58 was {len(V58.CAVE_BYTES)}):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v58[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V58's -- same cave base, same jarl"
    assert_probe_sites(code, "V59")

    # ---- everything V57/V58 established must still hold ------------------------------------------
    V57.assert_decoupled(code, "V59")
    V55.assert_variant_tables(code)
    assert_index_chain(code, "V59")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "0xC6AF0 must stay STOCK -- V56's mute is falsified"
    # V59 is a PROBE: not one calibration byte may move relative to V58.
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC61B2, "fwd clamp"), (0xC61B4, "fwd clamp"),
                    (0xC6440, "r24"), (0xC6442, "r24"), (0xC6446, "r24"), (0xC61F6, "r24 deadzone"),
                    (0xC643E, "r26"), (0xC61D6, "slew step -- V16 REJECTED, must stay 0"),
                    (0xC6424, "shaper deadband"), (0xC64C9, "2D-map mux"),
                    (0xC646C, "shared sensor scale"), (0xC6CD0, "private LKAS gain"),
                    (0xC63BA, "FUN_3b66a EMA alpha -- a V60 candidate, must NOT move here")):
        assert u16(code, a) == u16(v58, a), f"{name} 0x{a:05X} moved -- V59 changes NO calibration"
    assert code[0xC64DE] == v58[0xC64DE] == 27, "V18's re-engage ramp must stay at 27"
    assert code[0xC64A3] == v58[0xC64A3] == 1, "the deadband ENABLE byte must stay stock"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A,
              0xD200C, 0xD2000):
        assert u16(code, a) == u16(baseline, a), f"damper/rate cal 0x{a:05X} moved"
    # the ceiling V58 ELIMINATED, and the two FIR triples, must all stay stock
    assert struct.unpack_from("<11H", code, 0xD20C0) == \
        struct.unpack_from("<11H", baseline, 0xD20C0), "0xD20C0 ceiling moved"
    for a in (0xC4018, 0xC401C, 0xC4020, 0xC4048, 0xC404C, 0xC4050):
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v58, a), \
            f"FIR coefficient 0x{a:05X} moved -- V59 must not touch the FIR"

    # ---- CRC -------------------------------------------------------------------------------------
    assert V53.owning_block(code, CAVE_BASE) == MAIN_BLOCK
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        tag = "unchanged" if old_crc == new_crc else "RECOMPUTED"
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: "
              f"0x{old_crc:08X} -> 0x{new_crc:08X}  ({tag})")

    # ---- exact diff ------------------------------------------------------------------------------
    # NEVER whole-file diff against a build_*.full_image(): 0xFF filler below 0x13000 reports ~51,000
    # bogus bytes. Restricted to [0x13000,0x100000) throughout.
    d58 = [i for i in range(0x13000, 0x100000) if code[i] != v58[i]]
    permitted = (set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
                 | set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)))
    stray = [i for i in d58 if i not in permitted]
    assert not stray, f"V59 vs V58 touches bytes outside the cave + MAIN CRC: {[hex(x) for x in stray]}"
    assert set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)) <= set(d58), "MAIN CRC trailer did not move"
    cal_trailer = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    assert not (cal_trailer & set(d58)), \
        "the CAL CRC moved -- V59 changes no calibration, so it must not"
    print(f"\n  V59 vs V58: {len(d58)} bytes  (cave payload + MAIN CRC only; CAL block untouched)")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V59 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V59")
    assert walk(bytes(code), label="V59") == 0
    assert walk_all_blocks(bytes(code), label="V59") == 0
    assert_probe_sites(code, "V59")
    V55.assert_variant_tables(code)

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback ------------------------------
    source_rwd = open(FF.V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == FF.EXPECTED_HEADERS
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    encode = invert_table(decode)

    rwd = encode_x31(source_info["headers"], source_info["blocks"],
                     [bytes(code[START:END]).translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V59 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V59 readback")
    assert walk(bytes(readback), label="V59 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V59 readback") == 0
    assert_probe_sites(readback, "V59 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V59 readback")
    assert_index_chain(readback, "V59 readback")
    assert u16(readback, V57.PRIVATE_ADDR) == V57.GAIN_4X
    assert u16(readback, V57.GAIN_ADDR) == V57.GAIN_STOCK
    assert u16(readback, V57.DISP_OFF) == V57.DISP_NEW
    assert readback[0xC64A3] == 1 and readback[0xC64DE] == 27

    # re-decode the cave FROM THE BUILT IMAGE, instruction by instruction, and compare to the listing
    print("\n  cave re-decoded from the BUILT image:")
    off = CAVE_BASE
    for addr, raw, text in CAVE_LISTING:
        got = bytes(readback[off:off + len(raw)])
        assert got == raw, f"re-decode mismatch at 0x{off:05X}: {got.hex()} != {raw.hex()}"
        print(f"    0x{off:05X}  {got.hex():<12s} {text}")
        off += len(raw)
    assert off == CAVE_BASE + len(CAVE_BYTES)

    # the thermometer must be self-consistent for every byte4 the cave can emit
    for idx in (0, 1, 511, 512, 513, 1023, 1024, 2047, 2048, 32767):
        b4 = BIT_LIVE
        if idx >> 9 == 0:
            b4 |= BIT_LT512
        if idx >> 10 == 0:
            b4 |= BIT_LT1024
        if idx >> 11 == 0:
            b4 |= BIT_LT2048
        d = decode_field(b4 | 0x7)
        assert d["monotonic"], f"thermometer not monotonic for index {idx}"
        assert d["index_lo"] <= idx and (d["index_hi"] is None or idx < d["index_hi"]), \
            f"decode_field brackets {idx} as [{d['index_lo']},{d['index_hi']})"
    sentinel = decode_field(BIT_LIVE | BIT_FAULT | 0x7)
    assert sentinel["fault_sentinel"] and sentinel["index_lo"] == 2048, \
        "the 0xFFFF sentinel must read as fault + all-thresholds-cleared"

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  PROBE: 0x14A byte4  bit7=LIVENESS  bit6=(gp-0x6ba6<0, the 0xFFFF FAULT SENTINEL)")
    print("                      bit5=(index<512)  bit4=(index<1024)  bit3=(index<2048)")
    print("                      bits2:0 = stock status.  THERMOMETER: bit5=>bit4=>bit3 always.")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("  GATE 1 RAM ownership: INHERITED -- same cave base/hook/extent as V55/V57/V58, all three")
    print("          flew fault-free. Read-only, no new RAM, r6/r7 only (V58's exact budget).")
    print("  GATE 2 closed-loop stability: VACUOUS -- V59 writes nothing to any control path and")
    print("          changes NO calibration byte. Its only output is a TX payload byte no control")
    print("          path reads. *** Still CODE in the 1 kHz TX path: a higher risk class than")
    print("          cal-only, which is why the base/hook/extent are reused rather than moved.")
    print("\n  HOW TO READ IT: `index` is gp-0x6ba6 == |gp-0x6b9a|, which indexes BOTH boost amplitude")
    print("          LERPs (0xD28DC via 0xca4f4, and 0xD2888 via 0xca23c). V58 showed its SIGNED")
    print("          sibling crosses zero at 20.93 Hz only when LKAS applies, so this index is that")
    print("          signal rectified -- it sweeps the curve at ~2x the mode frequency. The question")
    print("          is DEPTH: if bit5 is set essentially always, the index never clears X1 = 512,")
    print("          the coefficient stays pinned at 16384, and the mechanism is INERT -- do not")
    print("          flatten 0xD28DC. If bit5 clears during the bursts, read how far the thermometer")
    print("          falls to get the swept Y range, and 0xD28DC/0xD2888 become live levers.")
    print("          Condition on LATERAL engagement (carControl.latActive / 0x18F byte4 bit3),")
    print("          NEVER carState.cruiseState.enabled, and use SUSTAINED effort")
    print("          |lowpass(tq,3Hz)|<=200 for hands-off. Compare ENGAGED vs DISENGAGED at matched")
    print("          creep speed -- route 2b proved that contrast is computable.")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
