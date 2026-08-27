#!/usr/bin/env python3
r"""builds/v80_v107/build_v90_tva.py -- V90 = the FLOWN V89, PROBE-ONLY. Not one calibration cell moves.

    base   _v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin
           sha256 6eae6826881cb5fd737ab433919f64a556ed027126e3f056ed8f03c13206f159

    0xC4B34  cave payload 62 B -> 74 B   four INDEPENDENT rungs on CAN 0x14A byte 4 bits 7:4
    0x55DF2  6894 -> da94                CAN 427 MOTOR_TORQUE: gp-0x6b98 -> gp-0x6b26

Two edits. **ZERO calibration cells change** -- V89's friction lever (0xC40D2 = 204) is carried
forward untouched, so the control surface on the car is bit-identical to the one that flew as V89.

===================================================================================================
WHAT CLASS OF BUILD THIS IS -- and how it differs from the whole arc since V38
===================================================================================================
The arc: V38-V52 authority/filters/poles/caves - V53-V61 telemetry + lane mutes - V62-V73 the rate
lane (r24/r26) - V74-V83a the base-assist damper - V84-V86B damper reverts and phase - V87 a
subtractive measurement build - V88 Lever B restored - V89 the FIRST build to touch the plant model.

**V90 is the first PURE-INSTRUMENT build since V54.** Every build in that arc moved at least one
calibration cell; V90 moves none. It changes only WHAT IS OBSERVED, so a V89-vs-V90 comparison is a
measurement-invariance check by construction: the delivered torque surface is identical and any
difference the operator reports is not attributable to a control edit.

Its instrument is also structurally different from every previous cave. V86B/V87/V88/V89 all put
three rungs on ONE cell, so b6 => b5 and b7 => b5 held identically and the support collapsed to
{3,7,15,23,31} on all four -- they were mutually indistinguishable from the wire. V90 puts FOUR
INDEPENDENT cells on b7/b6/b5/b4, every implication breaks, and all 16 odd codewords open up.

===================================================================================================
WHAT IS MEASURED
===================================================================================================
    b7  gp-0x6b26 < 0            SIGN of the damping lane        ~0.50 duty by construction
    b6  |gp-0x6bf6| >= 512       |MODEL| (= 2639 x model)        0.10-0.50  [BELIEF, the one guess]
    b5  gp-0x6ae2 != 0           FRICTION relay active           0.49-0.54  [E, V89's own rung]
    b4  gp-0x6c00 < 0            OBSERVER GATE FAILED            ~0.000, a one-shot question
    b3  1                        FINGERPRINT                     1.000 => every wire value is ODD
    CAN 427 MOTOR_TORQUE = clamp(|gp-0x6b26| * 5 >> 3, 0, 0x3FF) at 50 Hz, ~9 bits, never clips
      (|gp-0x6b26| <= 511 by the 0xC407E clamp => 511*5>>3 = 319 in a 10-bit field)

(b6, b5) is the point of the build: gp-0x6ae2 ~ 0.0773 * |gp-0x6bf6| * relay, so frames with
b6 = 1 AND b5 = 0 are *large model, zero friction* => relay ~ 0. That separates |model| from the
ratio's relay-ness -- the confound V89's single conflated bit could not resolve.

b7 is not optional: 427 runs at 50 Hz (Nyquist 24.9 Hz) and is RECTIFIED, so it cannot see the
18-28 Hz band at all and carries no phase. The 100 Hz sign bit is the only channel that reaches
that band, and with 427 it reconstructs the signed value -- V88's proven design on the new cell.

===================================================================================================
GATE 1 -- RAM ownership
===================================================================================================
All four new cells are READ-ONLY from the cave; a load has no side effects. Three of the four are
pure write-only diagnostic taps (0 firmware readers). No new RAM is claimed; the only cell WRITTEN
is gp-0x1514 bits 7:3, the same byte ~50 flown builds have written. Scratch is r6 and r7 only.
The hook at 0x55C0E is unchanged and already sits inside Honda's own di/ei critical section.

GATE 2 -- closed-loop stability: vacuous. No control cell moves and the cave is a leaf with no
loop, no divide, no call and no float; 29 straight-line instructions at 100 Hz.

===================================================================================================
🛑 CRC -- ONE TRAILER, NOT TWO. The blocks are NOT uniform 0x1000 below 0xC4000.
===================================================================================================
Block 50 is the single MAIN block spanning [0x013000, 0x0C4FFC) -- 0xB1FFC bytes -- so 0x055DF2
and 0xC4B34 share ONE trailer, 0xC4FFC. 0x055FFC is NOT a trailer: on this image it reads
`6477b8f0`, live code. Writing a CRC word there would silently overwrite 4 bytes of executable
code and the enclosing recompute would HIDE it -- the chain would still walk 50/50 clean.

Empirical, from two flown builds (full byte diffs over [0x13000,0x100000)):
    V38 -> V87  edits 0x02A1F0, 0x0454FE, 0x055C0E, 0x055DF2, 0x0C4B34
                trailers changed: 0x0C4FFC ONLY (+0x0C6FFC for the 0xC6000-block cals)
    V87 -> V88  edits 0x03AA96, 0x0C4B38, 0x0C4B46, 0x0C6446
                trailers changed: 0x0C4FFC (+0x0C6FFC)   -- no 0x03AFFC
V87 is a FLOWN build that edited 0x055DF2 with 0xC4FFC as its only low trailer. That is V90's
precedent. The trailer set here is DERIVED from the image's own block map, never hard-coded.

===================================================================================================
PRE-REGISTRATION
===================================================================================================
IDENTITY (single-frame, parameter-free): b4 == 0 is impossible on V86B/V87/V88/V89 across 254,085
    measured frames and is the ~100 % case on V90. ANY frame with (byte4>>3)&0x1F in
    {1,5,9,13,17,21,25,29} proves V90 flew. One frame, no thresholds, no control route.
MAP VALIDATOR: b3 == 1 => every observed value must be ODD. An even value means the cave did not
    run or the field is being read at the wrong bit offset.
H1  b5 must reproduce V89's 0.536/0.495 engaged duty -- it is V89's rung UNCHANGED, so a
    disagreement indicts the instrument, not the car.
H2  b6's threshold is the ONE guessed parameter. Railed or dead => move the single byte at
    0xC4B4A (0xA0|shift): sar 8 = 256, sar 9 = 512, sar 10 = 1024, sar 11 = 2048. The (b6,b5)
    2x2 table says which way.
H3  Score b4 and b5 conditioned on WHEEL RATE, not as route averages -- b5 ran 0.16 to 0.99 across
    the rate range on V89.
H4  427 now carries gp-0x6b26, a baseline that exists on NO build. Pair it to the cave stream by
    timestamp: 50 Hz vs 100 Hz, do not assume alignment.
H5  🛑 THE OPERATOR SCORES THE SYMPTOMS, IN HIS WORDS. Bands are the instrument, never the verdict.

⚠ COST: 427 stops carrying gp-0x6b98. Acknowledged and accepted -- gp-0x6b26 has never been
   measured, gp-0x6b98 has (V87/V88).
🛑 The failure mode b4 does NOT catch: at (char)gp-0x6752 == 0 the command branch zeroes and model,
   friction and inertia collapse together while the observer still emits a valid output, and
   polarity 0 PASSES the gate. b6 = 0 AND b5 = 0 is the signature, degenerate with "genuinely
   small". A future friction probe should carry gp-0x6752 itself.
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
WRITE_MODE = os.environ.get("ACCORD_V90_WRITE", "").strip().lower()

BASE_BIN = str(plain_image_path(
    "_v89_V88BASE-FRICTION.C40D2.204-CAVE.6AE2.SIGN.MAG64_plain_image.bin"))
BASE_SHA = "6eae6826881cb5fd737ab433919f64a556ed027126e3f056ed8f03c13206f159"

CAVE_BASE, CAVE_FREE_END = 0xC4B34, 0xC4FF0
V89_CAVE = bytes.fromhex(
    "003a24371e956032a305423a6032ae05483aa63241326132a305443aa43755986232a905"
    "413ac43a483a8437edeac636070007314437ecea2436e8ea7f00")
PAYLOAD = bytes.fromhex(
    "003a2437da946032ae05483a24370a946032ae058031a9326032a305443a24371e956032a305"
    "423a243700946032ae05413ac43a483a8437edeac636070007314437ecea2436e8ea7f00")

HOOK_ADDR, HOOK_BYTES = 0x55C0E, bytes.fromhex("86ff26ef")
R427_ADDR = 0x55DF2                          # hw2 of `ld.h ..[gp],r6` inside the 0x1AB builder
R427_OLD, R427_NEW = 0x6B98, 0x6B26          # gp-relative, both negative, both even => ld.h form

# Every halfword in PAYLOAD that is not already flying in V89's cave, and the address it is
# copied from IN THE BASE IMAGE. 🛑 Nothing here is hand-encoded: `subr r0,r6` is `8031`, and the
# hand-derived `3080` would have been `satsubr`, saturating instead of negating and corrupting b6
# on negative models only -- a defect that would have survived a flight.
TWINS = [
    (0x02, 4, 0x3815C, "ld.h -0x6b26[gp],r6   -- all four bytes, same dest register"),
    (0x0C, 2, 0x3815C, "ld.h hw1 `2437`"),
    (0x0E, 2, 0x3BAC2, "hw2 -0x6bf6           -- from `st.h r12,-0x6bf6[gp]` @0x3BAC0"),
    (0x14, 2, 0x2A150, "subr r0,r6  `8031`    -- NOT satsubr `3080`"),
    (0x16, 2, 0x3E60C, "sar 0x9,r6  `a932`    -- the THRESHOLD byte lives here, 0xA0|shift"),
    (0x28, 2, 0x3815C, "ld.h hw1 `2437`"),
    (0x2A, 2, 0x3BC18, "hw2 -0x6c00           -- from `st.h r9,-0x6c00[gp]` @0x3BC16"),
]
# These two come from V89's OWN flown cave rather than from Honda code.
CAVE_SELF_TWINS = [
    (0x1E, 4, CAVE_BASE + 0x02, "ld.h -0x6ae2[gp],r6 -- byte-identical to V89's cave +0x02"),
    (0x36, 0x14, CAVE_BASE + 0x2A, "the 20-byte epilogue -- identical to V89's"),
]

VARIANT_TOKEN = "V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26"
TAG = VARIANT_TOKEN
BIN_OUT = str(plain_image_path(f"_v90_{VARIANT_TOKEN}_plain_image.bin"))
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V90-{TAG}-0x{START:X}-0x{END:X}.rwd")

# 🛑 ZERO calibration cells change. Named explicitly so the claim is checkable, not merely implied
# by the diff. Every one is asserted on the base AND re-asserted on the built image.
FROZEN = {
    0xC40D2: (2, 204, "K1 modelled Coulomb friction -- V89's lever, CARRIED FORWARD unchanged"),
    0xC4080: (2, 0, "K0 pure-Coulomb arm -- the recorded NEVER-RAISE relay hazard, stays 0"),
    0xC407E: (2, 511, "hard-fault interlock clamp -- Honda's 511, one under its own 512 trip"),
    0xC40BC: (2, 600, "friction relay gate -- 600. 6000 measured 2.3x WORSE; DO NOT restore it"),
    0xC40D0: (2, 408, "friction EMA alpha (16.7 Hz)"),
    0xC40D4: (2, 573, "command-branch EMA -- V86's FALSIFIED lever"),
    0xC40D8: (2, 3686, "friction-family constant"),
    0xC646E: (2, 1428, "INERTIA/damping gain -- unmeasured sizing figure"),
    0xC63A0: (2, 1024, "INERT, no mechanism"),
    0xC63A2: (2, 1024, "loop-gain family"),
    0xC63A4: (2, 1024, "loop-gain family"),
    0xC63A6: (2, 1024, "loop-gain family"),
    0xC63A8: (2, 1024, "loop-gain family"),
    0xC63AA: (2, 1024, "loop-gain family"),
    0xC63AC: (2, 102, "loop-gain family"),
    0xC63AE: (2, 1024, "loop-gain family"),
    0xC6200: (2, 8192, "loop-gain family"),
    0xC6446: (2, 5244, "Lever B arm -- V88's 5244"),
    0xC6468: (2, 2639, "model output gain -- SHARED, 5 readers"),
    0xC646C: (2, 891, "shared sensor scale -- Honda 891"),
    0xC6CD0: (2, 3564, "private forward LKAS gain = 4.000x, NEVER lower"),
    0xC62EA: (2, 0, "steer-to-zero"),
    0xC61F6: (2, 3, "r24 deadzone"),
    0x3AA96: (1, 0xFB, "Lever B gate -- V88's"),
    0x454FE: (1, 0xB5, "V42's ratchet fix -- restored at V80, carried by V87/V88/V89"),
    0x3AB76: (1, 0xAA, "Lever A r26 sar -- DO NOT RESTORE"),
    0x3AC20: (1, 0xAA, "Lever A r24 sar -- DO NOT RESTORE"),
}

# The friction-comp LERP. 🛑 An address is not a mode: 0xD6A5C is mode 23, not mode 24. The Y row
# is at record base + 8, and writing Y values at the record base lands them in the X breakpoints,
# which the LERP compares UNSIGNED -- a flat Y[0] at all speeds that LOOKS like a working cal.
LERP_MODES = (24, 26)
LERP_TABLE, LERP_X, LERP_Y = 0xCBE74, (0, 1280, 5760), (-9830, -5734, -1966)


def rd(buf, a, w):
    return bytes(buf[a:a + w])


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


# ---------------------------------------------------------------------------------------------
# A V850E2 decoder covering exactly the eight formats this cave uses. It exists so the script
# re-disassembles the payload FROM THE BUILT IMAGE and checks the RUNG TABLE, rather than checking
# the bytes against the string it was handed. Confirmed independently in GhidraMCP.
# ---------------------------------------------------------------------------------------------
COND = {0x3: "bnh", 0xE: "bge"}
RN = {3: "sp", 4: "gp", 5: "tp", 30: "ep", 31: "lp"}


def rn(i):
    return RN.get(i, f"r{i}")


def decode(img, addr):
    """Return (text, length, kind, operand) for one instruction at `addr`."""
    hw1 = struct.unpack_from("<H", img, addr)[0]
    reg2, op, reg1 = (hw1 >> 11) & 0x1F, (hw1 >> 5) & 0x3F, hw1 & 0x1F
    imm5 = hw1 & 0x1F
    if op == 0x10:
        return f"mov   0x{imm5:x},{rn(reg2)}", 2, "alu", None
    if op == 0x12:
        return f"add   0x{imm5:x},{rn(reg2)}", 2, "add", imm5
    if op == 0x13:
        return f"cmp   0x{imm5:x},{rn(reg2)}", 2, "cmp", imm5
    if op == 0x15:
        return f"sar   0x{imm5:x},{rn(reg2)}", 2, "sar", imm5
    if op == 0x16:
        return f"shl   0x{imm5:x},{rn(reg2)}", 2, "shl", imm5
    if op == 0x0C:
        return f"subr  {rn(reg1)},{rn(reg2)}", 2, "subr", None
    if op == 0x08:
        return f"or    {rn(reg1)},{rn(reg2)}", 2, "or", None
    if op == 0x03 and reg2 == 0:
        return f"jmp   [{rn(reg1)}]", 2, "jmp", None
    if (hw1 >> 7) & 0xF == 0xB:                                  # Format III  bcond disp9
        disp = (((hw1 >> 11) & 0x1F) << 4) | (((hw1 >> 4) & 0x7) << 1)
        disp -= 0x200 if disp & 0x100 else 0
        c = hw1 & 0xF
        return f"{COND.get(c, f'b?{c:x}'):5s} +{disp}", 2, "branch", disp
    hw2 = struct.unpack_from("<H", img, addr + 2)[0]
    sdisp = struct.unpack("<h", struct.pack("<H", hw2))[0]
    names = {0x38: "ld.b", 0x39: "ld.h", 0x3A: "st.b", 0x3B: "st.h",
             0x3C: "ld.bu", 0x31: "movea", 0x36: "andi"}
    if op in (0x31, 0x36):
        return (f"andi  0x{hw2:x},{rn(reg1)},{rn(reg2)}" if op == 0x36 else
                f"movea {sdisp:#x},{rn(reg1)},{rn(reg2)}"), 4, names[op], (reg1, sdisp, hw2)
    if op == 0x3C:                                # ld.bu carries disp bit0 in hw1 bit5
        sdisp = (sdisp & ~1) | ((hw1 >> 5) & 1)
        sdisp -= 0x10000 if sdisp >= 0x8000 else 0
    if op in (0x3A, 0x3B):
        return f"{names[op]} {rn(reg2)},{sdisp:#x}[{rn(reg1)}]", 4, names[op], (reg1, sdisp)
    return f"{names.get(op, f'op{op:02x}')} {sdisp:#x}[{rn(reg1)}],{rn(reg2)}", 4, \
           names.get(op, f"op{op:02x}"), (reg1, sdisp)


def disassemble_cave(img, base, length):
    out, off = [], 0
    while off < length:
        text, n, kind, operand = decode(img, base + off)
        out.append((off, base + off, rd(img, base + off, n).hex(), text, kind, operand))
        off += n
    assert off == length, f"the last instruction overruns the payload by {off - length} byte(s)"
    return out


# The rung table, as INTENT. The built image is checked against this, not against the spec string.
EXPECTED = [
    (0x00, "mov   0x0,r7", None),
    (0x02, "ld.h  -0x6b26[gp],r6", "the damping lane"),
    (0x06, "cmp   0x0,r6", None), (0x08, "bge   +4", "-> 0x0C"),
    (0x0A, "add   0x8,r7", "b7 = SIGN(gp-0x6b26) < 0"),
    (0x0C, "ld.h  -0x6bf6[gp],r6", "2639 x model"),
    (0x10, "cmp   0x0,r6", None), (0x12, "bge   +4", "-> 0x16, skip the negate"),
    (0x14, "subr  r0,r6", "r6 = |2639 x model|"),
    (0x16, "sar   0x9,r6", "THRESHOLD 512"),
    (0x18, "cmp   0x0,r6", None), (0x1A, "bnh   +4", "-> 0x1E"),
    (0x1C, "add   0x4,r7", "b6 = |2639 x model| >= 512"),
    (0x1E, "ld.h  -0x6ae2[gp],r6", "friction x 1024"),
    (0x22, "cmp   0x0,r6", None), (0x24, "bnh   +4", "-> 0x28, unsigned: skip iff == 0"),
    (0x26, "add   0x2,r7", "b5 = FRICTION != 0   (V89's rung, unchanged)"),
    (0x28, "ld.h  -0x6c00[gp],r6", "observer status"),
    (0x2C, "cmp   0x0,r6", None), (0x2E, "bge   +4", "-> 0x32, success writes 0..20000"),
    (0x30, "add   0x1,r7", "b4 = OBSERVER GATE FAILED"),
    (0x32, "shl   0x4,r7", None),
    (0x34, "add   0x8,r7", "b3 = FINGERPRINT, always 1"),
    (0x36, "ld.bu -0x1514[gp],r6", None),
    (0x3A, "andi  0x7,r6,r6", "keep Honda's bits 2:0"),
    (0x3E, "or    r7,r6", None),
    (0x40, "st.b  r6,-0x1514[gp]", "0x14A byte 4"),
    (0x44, "movea -0x1518,gp,r6", "restore the hooked instruction"),
    (0x48, "jmp   [lp]", None),
]

M32 = 0xFFFFFFFF


def wire_byte4(x6b26, x6bf6, x6ae2, x6c00, honda_bits=0x7):
    """Mirrors the cave's integer arithmetic exactly, one line per instruction address."""
    r7 = 0
    r6 = x6b26                                   # 0xC4B36 ld.h  (SIGN-EXTENDS)
    if not r6 >= 0:         r7 += 8              # 0xC4B3A cmp / 0xC4B3C bge   b7 SIGN
    r6 = x6bf6                                   # 0xC4B40 ld.h
    if not r6 >= 0: r6 = 0 - r6                  # 0xC4B44 cmp / 46 bge / 48 subr  r6 = |x|
    r6 = r6 >> 9                                 # 0xC4B4A sar 0x9
    if not (r6 & M32) <= 0: r7 += 4              # 0xC4B4C cmp / 0xC4B4E bnh   b6 |model| >= 512
    r6 = x6ae2                                   # 0xC4B52 ld.h
    if not (r6 & M32) <= 0: r7 += 2              # 0xC4B56 cmp / 0xC4B58 bnh   b5 friction != 0
    r6 = x6c00                                   # 0xC4B5C ld.h
    if not r6 >= 0:         r7 += 1              # 0xC4B60 cmp / 0xC4B62 bge   b4 GATE FAILED
    return ((honda_bits & 0x7) | (((r7 << 4) & M32) + 8)) & 0xFF   # 0xC4B66 shl / 0xC4B68 add


def assert_rung_semantics():
    """Corner grid over both signs, the +/-512 boundary and every sentinel. Asserts, never prints."""
    vals = [-32768, -20001, -20000, -1024, -513, -512, -511, -1, 0, 1, 511, 512, 513,
            1024, 20000, 20001, 32767]
    n = 0
    for a in vals:
        for b in vals:
            for c in vals:
                for d in (-32768, -1, 0, 1, 400, 20000):
                    w = wire_byte4(a, b, c, d)
                    assert w & 0x08, "b3 fingerprint is not 1 -- every wire value must be ODD"
                    assert bool(w & 0x80) == (a < 0), "b7 is not SIGN(gp-0x6b26)"
                    assert bool(w & 0x40) == (abs(b) >= 512), "b6 is not |gp-0x6bf6| >= 512"
                    assert bool(w & 0x20) == (c != 0), "b5 is not (gp-0x6ae2 != 0)"
                    assert bool(w & 0x10) == (d < 0), "b4 is not (gp-0x6c00 < 0)"
                    assert w & 0x07 == 0x07, "Honda's bits 2:0 were not preserved"
                    n += 1
    codes = {wire_byte4(a, b, c, d, 0) >> 3 for a in (-1, 1) for b in (0, 1024)
             for c in (0, 1) for d in (-1, 1)}
    assert codes == {v for v in range(32) if v & 1}, f"only {len(codes)}/16 odd codewords reachable"
    print(f"    ✅ rung semantics: {n} corner cases, ZERO deviations; all 16 odd codewords "
          f"reachable (V86B/V87/V88/V89 reach only {{3,7,15,23,31}}) ⇒ b4 == 0 is V90-ONLY.")


def assert_lerp_untouched(buf, label):
    """🛑 Dereference 0xCBE74 + mode*4 and add 8. Print the MODE beside the address."""
    for mode in LERP_MODES:
        rec = struct.unpack_from("<I", buf, LERP_TABLE + mode * 4)[0]
        n = u16(buf, rec)
        x = struct.unpack_from("<3h", buf, rec + 2)
        y = struct.unpack_from("<3h", buf, rec + 8)
        assert n == 3, f"{label}: mode {mode} record 0x{rec:05X} has n={n}, expected 3"
        assert x == LERP_X, f"{label}: mode {mode} X @0x{rec + 2:05X} is {x}, expected {LERP_X}"
        assert y == LERP_Y, f"{label}: mode {mode} Y @0x{rec + 8:05X} is {y}, expected {LERP_Y}"
        print(f"    ✅ mode {mode}: record 0x{rec:05X}  X @0x{rec + 2:05X} = {x}  "
              f"Y @0x{rec + 8:05X} = {y}   UNTOUCHED")


def assert_frozen(buf, label):
    for a, (w, want, why) in sorted(FROZEN.items()):
        got = u16(buf, a) if w == 2 else buf[a]
        assert got == want, f"🛑 {label}: 0x{a:05X} is {got}, expected {want} -- {why}"


def build():
    base = bytearray(Path(BASE_BIN).read_bytes())
    assert len(base) == 0x100000
    base_sha = hashlib.sha256(bytes(base)).hexdigest()
    assert base_sha == BASE_SHA, f"the V89 base is {base_sha}, expected {BASE_SHA}"
    assert walk_all_blocks(bytes(base)) == 0, "the V89 base's CRC chain does not verify"
    print("=" * 102)
    print("  V90 -- the FLOWN V89, PROBE-ONLY. Four INDEPENDENT rungs + CAN 427 on gp-0x6b26.")
    print("         🛑 NOT ONE CALIBRATION CELL CHANGES.")
    print(f"    base {os.path.basename(BASE_BIN)}\n    sha256 {base_sha}")
    print("=" * 102)

    print("\n  STRUCTURE, asserted from the BASE image")
    assert rd(base, HOOK_ADDR, 4) == HOOK_BYTES, "the hook site is not V89's `movea -0x1518,gp,r6`"
    print(f"    0x{HOOK_ADDR:05X} = {HOOK_BYTES.hex()}   hook UNCHANGED")
    assert rd(base, CAVE_BASE, len(V89_CAVE)) == V89_CAVE, "the base's cave is not V89's 62 bytes"
    print(f"    0x{CAVE_BASE:05X} = V89's 62-byte cave, byte-exact")
    assert all(b == 0xFF for b in base[CAVE_BASE + len(V89_CAVE):CAVE_FREE_END]), \
        "the free run above V89's cave is not all 0xFF -- refusing to grow into it"
    print(f"    0x{CAVE_BASE + len(V89_CAVE):05X}-0x{CAVE_FREE_END:05X} all 0xFF "
          f"({CAVE_FREE_END - CAVE_BASE - len(V89_CAVE)} B free; V90 needs "
          f"{len(PAYLOAD) - len(V89_CAVE)} more and leaves {CAVE_FREE_END - CAVE_BASE - len(PAYLOAD)})")
    assert rd(base, R427_ADDR - 2, 4) == bytes.fromhex("2437") + struct.pack("<h", -R427_OLD), \
        "the 427 packer is not V87/V88/V89's `ld.h -0x6b98[gp],r6`"
    print(f"    0x{R427_ADDR - 2:05X} = {rd(base, R427_ADDR - 2, 6).hex()}   "
          f"427 currently on gp-0x{R427_OLD:04X}")
    assert (-R427_NEW & 0xFFFF) % 2 == 0 and (-R427_OLD & 0xFFFF) % 2 == 0, \
        "🛑 both displacements must be even -- an odd one selects a different opcode field"

    print("\n  TWINS -- every new halfword is copied from a verified instance IN THIS IMAGE")
    for off, w, src, why in TWINS:
        got, want = PAYLOAD[off:off + w], rd(base, src, w)
        assert got == want, f"🛑 payload +0x{off:02X} is {got.hex()}, twin 0x{src:05X} is {want.hex()}"
        print(f"    +0x{off:02X} {got.hex():8s} == 0x{src:05X}   {why}")
    for off, w, src, why in CAVE_SELF_TWINS:
        got, want = PAYLOAD[off:off + w], rd(base, src, w)
        assert got == want, f"🛑 payload +0x{off:02X} is {got.hex()}, 0x{src:05X} is {want.hex()}"
        print(f"    +0x{off:02X} {got.hex()[:16]:8s} == 0x{src:05X}   {why}")
    assert PAYLOAD[0x14:0x16] == bytes.fromhex("8031"), "🛑 subr is 8031; 3080 would be satsubr"
    assert len(PAYLOAD) == 74

    print("\n  ZERO-CALIBRATION-CHANGE CELLS, asserted on the base")
    assert_frozen(base, "base")
    print(f"    ✅ all {len(FROZEN)} named cells at their expected values "
          f"(0xC40D2 = 204 -- V89's friction lever is CARRIED, not reverted)")
    assert_lerp_untouched(base, "base")
    assert_rung_semantics()

    # ---- the two edits ---------------------------------------------------------------------------
    code = bytearray(base)
    attributed, by_addr = set(), {}

    def apply(addr, pre, post, label):
        got = rd(code, addr, len(pre))
        assert got == pre, f"0x{addr:05X}: expected {pre.hex()}, found {got.hex()}"
        code[addr:addr + len(post)] = post
        for k in range(len(post)):
            attributed.add(addr + k)
            by_addr[addr + k] = label
        print(f"    0x{addr:05X}  {len(post):3d} B   {label}")

    print("\n  EDITS")
    apply(CAVE_BASE, V89_CAVE + b"\xff" * (len(PAYLOAD) - len(V89_CAVE)), PAYLOAD,
          "EDIT 1  cave payload 62 B -> 74 B, four independent rungs")
    apply(R427_ADDR, struct.pack("<h", -R427_OLD), struct.pack("<h", -R427_NEW),
          f"EDIT 2  CAN 427 MOTOR_TORQUE: gp-0x{R427_OLD:04X} -> gp-0x{R427_NEW:04X}")

    assert all(b == 0xFF for b in code[CAVE_BASE + len(PAYLOAD):CAVE_FREE_END]), \
        "the tail above the new cave is not virgin 0xFF"
    print(f"    tail 0x{CAVE_BASE + len(PAYLOAD):05X}-0x{CAVE_FREE_END:05X} still virgin 0xFF")

    assert_frozen(code, "built image")
    assert_lerp_untouched(code, "built image")
    print(f"    ✅ every named calibration cell is byte-identical to the base AFTER the edits")

    # ---- CRC ---------------------------------------------------------------------------------
    # 🛑 DERIVED from the image's own block map, never hard-coded. The blocks are NOT uniform
    # 0x1000: block 50 is the MAIN block [0x013000,0x0C4FFC), 0xB1FFC bytes, and it owns BOTH
    # edits. 0x055FFC is live code (`6477b8f0`), not a trailer -- writing there would overwrite
    # 4 bytes of executable code and the enclosing recompute would hide it.
    touched = sorted(attributed)
    blocks = sorted({tuple(V53.owning_block(code, a)) for a in touched})
    print(f"\n  CRC -- {len(blocks)} block(s) move (trailer set DERIVED, not hard-coded)")
    for blk in blocks:
        if any(blk[1] <= a < blk[1] + 4 for a in touched):
            raise SystemExit("an edit landed on a CRC trailer")
        old_crc = struct.unpack_from("<I", code, blk[1])[0]
        new_crc = zlib.crc32(bytes(code[blk[0]:blk[1]])) & 0xFFFFFFFF
        struct.pack_into("<I", code, blk[1], new_crc)
        owners = [a for a in touched if blk[0] <= a < blk[1]]
        print(f"    [0x{blk[0]:06X},0x{blk[1]:06X}) @0x{blk[1]:06X}: 0x{old_crc:08X} -> "
              f"0x{new_crc:08X}   owns {len(owners)} of {len(touched)} touched byte(s)")
    crc_only = {blk[1] + k for blk in blocks for k in range(4)}
    assert {blk[1] for blk in blocks} == {0x0C4FFC}, \
        f"🛑 derived trailers {[hex(b[1]) for b in blocks]} -- expected exactly {{0x0C4FFC}}: " \
        "both edits lie inside the single MAIN block [0x013000,0x0C4FFC)"
    assert 0x055FFC not in crc_only, "🛑 0x055FFC is LIVE CODE, not a CRC trailer"
    assert walk_all_blocks(bytes(code)) == 0, "CRC chain FAILED"
    assert not [a for a in attributed if 0xC5000 <= a < 0xC5FFC], \
        "🛑 an edit landed in [0xC5000,0xC5FFC) -- the block the bootloader SKIPS (V40's brick)"
    assert bytes(code[0xC5000:0xC5FFC]) == bytes(base[0xC5000:0xC5FFC]), \
        "the CRC-SKIPPED block [0xC5000,0xC5FFC) is not byte-identical to the base"
    assert not [a for a in attributed if a < START or a >= END], "an edit landed outside the region"
    print("    ✅ full 50-block chain: 50/50 PASS · [0xC5000,0xC5FFC) byte-identical to the base "
          "· 0x055FFC untouched")

    # ---- zero-unattributed full diff ---------------------------------------------------------
    runs, i = [], START
    while i < END:
        if code[i] != base[i]:
            j = i
            while j < END and code[j] != base[j]:
                j += 1
            runs.append((i, j - 1))
            i = j
        else:
            i += 1
    assert bytes(code[:START]) == bytes(base[:START]), "a byte below 0x13000 changed"
    attribute = lambda d: by_addr.get(d, "CRC trailer 0xC4FFC" if d in crc_only else None)  # noqa: E731
    stray = [d for a, b in runs for d in range(a, b + 1) if attribute(d) is None]
    total = sum(b - a + 1 for a, b in runs)
    print("\n" + "=" * 102)
    print("  🛑 FULL BYTE DIFF: BUILT V90 vs the FLOWN V89 base -- over [0x13000, 0x100000)")
    print(f"    {len(runs)} differing run(s), {total} byte(s) total")
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X} {b - a + 1:4d}  {attribute(a)}")
    assert not stray, f"🛑 UNATTRIBUTED bytes vs V89: {[hex(x) for x in stray[:16]]}"
    rt = bytearray(code)
    for a in attributed | crc_only:
        rt[a] = base[a]
    assert hashlib.sha256(bytes(rt)).hexdigest() == base_sha, "the round trip does not reproduce V89"
    print("    ⇒ ZERO unattributed bytes; restoring the attributed set reproduces V89 BIT-FOR-BIT.")

    # ---- re-disassemble the cave FROM THE BUILT IMAGE, against the RUNG TABLE -----------------
    print("\n  🛑 RE-DISASSEMBLED FROM THE BUILT IMAGE, checked against the RUNG TABLE")
    listing = disassemble_cave(code, CAVE_BASE, len(PAYLOAD))
    assert len(listing) == 29, f"{len(listing)} instructions, expected 29"
    assert len(EXPECTED) == 29
    boundaries = {off for off, *_ in listing}
    for (off, addr, hx, text, kind, operand), (eoff, etext, note) in zip(listing, EXPECTED):
        assert off == eoff, f"+0x{off:02X}: expected an instruction at +0x{eoff:02X}"
        assert text.split() == etext.split(), f"+0x{off:02X}: got `{text}`, expected `{etext}`"
        if kind == "branch":
            tgt = off + operand
            assert tgt in boundaries, f"+0x{off:02X}: branch target +0x{tgt:02X} is not a boundary"
        assert kind not in ("call", "div", "loop"), "the cave must stay a straight-line leaf"
        print(f"    +0x{off:02X}  0x{addr:05X}  {hx:8s}  {text:22s}  {note or ''}")
    assert not [1 for _, _, _, t, _, _ in listing
                if t.split()[0] in ("jarl", "jr", "callt", "div", "divh", "prepare")], \
        "🛑 the cave contains a call, a loop or a divide"
    assert sum(1 for _, _, _, _, k, _ in listing if k == "branch") == 5, "expected 5 branches"
    print("    ✅ 29 instructions · 5 branches, all targets on instruction boundaries · "
          "no loop / divide / call / float · scratch r6, r7 only")

    # ---- value-anchored readback from the BUILT image -----------------------------------------
    print("\n  VALUE-ANCHORED VERIFICATION, read back from the BUILT image")
    for off, disp, bit in ((0x02, 0x6B26, "b7"), (0x0C, 0x6BF6, "b6"),
                           (0x1E, 0x6AE2, "b5"), (0x28, 0x6C00, "b4")):
        got = struct.unpack_from("<h", code, CAVE_BASE + off + 2)[0]
        assert got == -disp, f"+0x{off:02X} reads gp{got:+d}, expected gp-0x{disp:04X}"
        print(f"    {bit}: cave +0x{off:02X} = ld.h -0x{disp:04X}[gp],r6")
    shift = code[CAVE_BASE + 0x16] & 0x1F
    assert code[CAVE_BASE + 0x16] & 0xE0 == 0xA0 and shift == 9
    print(f"    b6 threshold byte 0x{CAVE_BASE + 0x16:05X} = 0x{code[CAVE_BASE + 0x16]:02x} "
          f"⇒ sar 0x{shift:x} ⇒ trips at |2639 x model| >= {1 << shift}")
    got427 = struct.unpack_from("<h", code, R427_ADDR)[0]
    assert got427 == -R427_NEW
    print(f"    427: 0x{R427_ADDR - 2:05X} = {rd(code, R427_ADDR - 2, 4).hex()} = "
          f"ld.h -0x{R427_NEW:04X}[gp],r6  ⇒ MOTOR_TORQUE = clamp(|gp-0x{R427_NEW:04X}|*5>>3,0,0x3FF)"
          f"; max {511 * 5 >> 3} of 1023 ⇒ never clips")
    assert u16(code, 0xC40D2) == 204

    # ---- .rwd ---------------------------------------------------------------------------------
    source_rwd = Path(FF.V38_RWD).read_bytes()
    assert hashlib.sha256(source_rwd).hexdigest() == FF.V38_RWD_SHA256, "V38 source .rwd drifted"
    FF.assert_x31_checksum(source_rwd, "V38 source")
    info = parse_x31(source_rwd)
    dec_tbl = build_decode_table(FF.V9B["keys"], FF.V9B["ops"])
    rwd = encode_x31(info["headers"], info["blocks"],
                     [bytes(code[START:END]).translate(invert_table(dec_tbl))])
    FF.assert_x31_checksum(rwd, "V90 output")
    back = parse_x31(rwd)
    dec = bytearray(base)
    dec[START:END] = bytes(back["encs"][0]).translate(dec_tbl)
    assert bytes(dec) == bytes(code), "the readback is not byte-identical to the built image"
    assert walk_all_blocks(bytes(dec)) == 0, "readback CRC chain FAILED"
    img_sha = hashlib.sha256(bytes(code)).hexdigest()
    rwd_sha = hashlib.sha256(rwd).hexdigest()
    print("\n    ✅ READBACK: the decoded .rwd payload is byte-identical to the built image; "
          "anchors and the 50/50 chain re-verified from it.")

    print("\n" + "=" * 102)
    if WRITE_MODE in ("", "none"):
        print("  🛑 DRY RUN -- NOTHING WRITTEN. Re-run with ACCORD_V90_WRITE=rwd to cut.")
    else:
        existing = Path(BIN_OUT).read_bytes() if os.path.exists(BIN_OUT) else None
        if existing is not None and existing != bytes(code):
            raise SystemExit(f"🛑 REFUSING TO OVERWRITE {BIN_OUT}: a DIFFERENT image already exists.")
        Path(BIN_OUT).write_bytes(bytes(code))
        print(f"  wrote {BIN_OUT}\n    SHA256 {img_sha}  ({len(code)} bytes)")
        if WRITE_MODE == "rwd":
            if os.path.exists(OUT) and Path(OUT).read_bytes() != rwd:
                raise SystemExit(f"🛑 a DIFFERENT {OUT} already exists -- ONE .rwd per build number.")
            Path(OUT).write_bytes(rwd)
            print(f"  wrote {OUT}\n    SHA256 {rwd_sha}  ({len(rwd)} bytes)")
            shipped = Path(OUT).read_bytes()
            assert hashlib.sha256(shipped).hexdigest() == rwd_sha
            FF.assert_x31_checksum(shipped, "V90 shipped")
            sd = bytearray(base)
            sd[START:END] = bytes(parse_x31(shipped)["encs"][0]).translate(dec_tbl)
            assert bytes(sd) == bytes(code), "🛑 the SHIPPED .rwd does not decode to the built image"
            assert walk_all_blocks(bytes(sd)) == 0, "shipped-from-disk CRC chain FAILED"
            assert_frozen(sd, "shipped .rwd, re-read from disk")
            assert_lerp_untouched(sd, "shipped .rwd, re-read from disk")
            assert bytes(sd[CAVE_BASE:CAVE_BASE + len(PAYLOAD)]) == PAYLOAD
            assert struct.unpack_from("<h", sd, R427_ADDR)[0] == -R427_NEW
            on_disk = Path(BIN_OUT).read_bytes()
            assert hashlib.sha256(on_disk).hexdigest() == img_sha and on_disk == bytes(code)
            print("  ✅ FROM-DISK: the shipped .rwd was re-read, re-hashed, checksum-verified, "
                  "decoded, CRC-walked and re-asserted INDEPENDENTLY (cals, LERP, cave, 427).")

    print(f"\n  V90 [{VARIANT_TOKEN}]")
    print(f"    image SHA256 {img_sha}")
    print(f"    .rwd  SHA256 {rwd_sha}  "
          f"({'WRITTEN' if WRITE_MODE == 'rwd' else 'computed, NOT written'})")
    print("  🛑 PROBE-ONLY: the delivered torque surface is BIT-IDENTICAL to the flown V89.")
    print("     b6's 512 threshold is the ONE guessed parameter; it is a single byte at 0xC4B4A.")
    print("  🛑 CRC: ONE trailer, 0xC4FFC. 0x055FFC is LIVE CODE, not a trailer -- both edits")
    print("     lie inside the single main block [0x013000,0x0C4FFC). Precedent: the flown V87")
    print("     edited 0x055DF2 and moved 0xC4FFC alone.")
    return img_sha, rwd_sha


if __name__ == "__main__":
    assert len(PAYLOAD) == 74 and len(V89_CAVE) == 62
    build()
