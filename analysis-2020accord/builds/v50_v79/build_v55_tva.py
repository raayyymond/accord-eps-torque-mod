#!/usr/bin/env python3
"""
=========================================================================================================
V55 -- V38 base + steer-to-zero + a DUAL probe on the proven 0x14A byte4 piggyback
=========================================================================================================

V55 = V38 calibration
    + `0xC62EA` 320 -> 0            (steer-to-zero, carried from V53, CONFIRMED on-car)
    + a code cave reporting TWO signals into CAN 330 / `0x14A` byte4:

        bit  7    = (damper variant INDEX >= 10)                       [static, 1 bit]
        bits 6:3  = clamp((gp-0x6b98 >> 9) + 8, 1, 15)                 [waveform, 4 bits @ 100 Hz]
        bits 2:0  = stock STEER_SENSOR_STATUS_1/2/3, PRESERVED

WHY THESE TWO SIGNALS
---------------------------------------------------------------------------------------------------------
1. `gp-0x6b98` is the FINAL MERGED COMMAND -- the only path to FOC ("zeroing it kills both LKAS and base
   power steering", `reference_accord_shaper_deadband_dropout`). The question it answers is a PARTITION,
   not another lever: **is the ~20 Hz mode present in the motor command at all?**

     present -> the oscillation is commanded; the command path stays in scope and the `0xC6AF0` mute
                becomes motivated rather than speculative.
     absent  -> every command-path lever this kit has flashed (V39 r24, V41 motor-rate cap, V42ch2 r26,
                V43 Stage-C pole, V45 governor slew, V46 Stage-A pole, V48A type-8 carrier, V52C
                gp-0x4f60 EMA -- ALL NULL) was doomed by construction, and the search moves to the plant.

   A null is still informative: at 512 counts/level it BOUNDS the command's 20 Hz content to roughly
   <512 counts against the sensor's ~550 counts rms. It does not prove zero.

2. The damper factor tables are variant-coded through THREE stages and the selector is an EEPROM value
   NOT present in any flash dump:

       5-byte coded ID -> FUN_00057f8e() match vs 16 keys @0xCD000 -> ROW (0-15)
                       -> index byte @0xCD012 + ROW*0x24            -> INDEX (0-57)
                       -> ptr_array[INDEX]                          -> the live LERP table

   Our PN 39990-TVA-A160 -> key "TVAA1" -> row 2 -> INDEX 10 -> Factor C `0xD27BC` / Factor E `0xD27F8`,
   which ARE the tables V44 and V47 edited -- so the damping hypothesis was genuinely tested and IS
   falsified. BUT the TVA family SPLITS: {TVAA0,TVAA2,TVAA4} -> index 4, {TVAA1,TVAC1,TVAA6,TVAC4} ->
   index 10, {TVAA7} -> 12. If this ECU is coded TVAA0/2/4 then V44/V47 missed after all. That residual
   is exactly one bit wide, so it rides along for free.

     bit7 = 0  -> INDEX < 10  -> V44/V47 edited an INERT table; damping is UNTESTED, retest on index 4
     bit7 = 1  -> INDEX >= 10 -> V44/V47 edited the LIVE table; damping is genuinely falsified

LIVENESS
---------------------------------------------------------------------------------------------------------
The 4-bit waveform field is clamped to 1..15, so **bits 6:3 == 0 means THE CAVE DID NOT FIRE**. Stock
leaves those bits at 0 (proven: V53's drive read byte4 == 0x07 in 5,994/5,994 frames). This is the
`feedback-telemetry-must-reserve-a-did-not-fire-value` discipline -- a dead probe must never decode as a
legal reading.

GATES
---------------------------------------------------------------------------------------------------------
GATE 1 (RAM ownership): reads gp-0x6b98, gp+0x63fd, gp-0x1514; writes ONE byte (gp-0x1514, read-modify-
  write preserving bits 2:0). Allocates NO scratch RAM at all, so the `gp-0x1500` failure class -- which
  passed both static methods and still failed on-car -- does not arise. Clobbers only r6/r7, the same
  strict subset of V31P's proven-dead set that V54 used and that the hook site itself proves dead
  (`mov 0x8,r7` reassigns r7 at 0x55C12; r6 is the displaced instruction's own target).
GATE 2 (closed-loop): vacuous by construction -- report-only, into a TX payload byte no control path
  reads. `0xC6AF0` asserted stock. No filter, pole, gain, clamp, damper or authority value moves.

EVERY ENCODER IS A REG2-OR-CONDITION-FIELD CHANGE FROM A BYTE-CONFIRMED REAL INSTRUCTION. No novel
opcode VALUE is introduced anywhere in this cave (the V54 lesson: prefer a register field over a new
opcode, because a new opcode's only evidence is the post-build re-disassembly).

=========================================================================================================
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

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from firmware_paths import RWD_DIR, plain_image_path

import build_vfourframe_tva as FF
import build_v53_tva as V53
import build_v54_tva as V54

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks
from build_vfourframe_tva import GP, R0, R6, R7, _fmt1, _le16

# ---- inherited, unchanged -----------------------------------------------------------------------------
START, END = FF.START, FF.END
V38_PLAIN, V38_RWD = FF.V38_PLAIN, FF.V38_RWD
V38_SHA256, V38_RWD_SHA256 = FF.V38_SHA256, FF.V38_RWD_SHA256
EXPECTED_HEADERS, V9B = FF.EXPECTED_HEADERS, FF.V9B

CAVE_BASE = FF.CAVE_BASE                 # 0xC4B34
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT
HOOK_ADDR = FF.HOOK_ADDR                 # 0x55C0E
HOOK_STOCK = FF.HOOK_STOCK               # movea -0x1518,gp,r6
MAIN_BLOCK = FF.MAIN_BLOCK
CAL_BLOCK = V53.CAL_BLOCK

PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP   # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK     # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                 # 0x55C18

# ---- signal 1: the final merged motor command ---------------------------------------------------------
CMD_DISP = 0x6b98            # gp-0x6b98, SIGNED halfword, clamped +-0x2000 at 0x43b0e..0x43b20
CMD_SHIFT = 9                # 512 counts/level; 15 levels spans +-3584 = the realistic excursion
CMD_OFFSET = 8               # centre of the 1..15 field
CMD_LO, CMD_HI = 1, 15       # 0 reserved for "cave did not fire"
CMD_STORE = 0x43b52          # st.h r8,-0x6b98[gp]  (r8 = r21 = the clamped governor total)
CMD_STORE_BYTES = bytes.fromhex("64476894")
CMD_REAL_LDH = 0x19fe2       # a real `ld.h -0x6b98[gp],r10` -- our encoder differs only in reg2
CMD_REAL_LDH_BYTES = bytes.fromhex("24576894")

# ---- signal 2: the damper variant index ---------------------------------------------------------------
VARIANT_DISP = 0x63fd        # gp+0x63fd  (POSITIVE offset -- note the sign)
VARIANT_THRESH = 10          # >= 10 selects the 0xD27xx tables V44/V47 edited
VARIANT_REAL_LDBU = 0x34502  # real `ld.bu 0x63fd[gp],r13` inside FUN_00034350
VARIANT_REAL_LDBU_BYTES = bytes.fromhex("a46ffd63")
VARIANT_KEY_TABLE = 0xCD000  # 16 x 5-byte ASCII PN keys, stride 0x24
VARIANT_IDX_TABLE = 0xCD012  # the damper INDEX byte, same stride
VARIANT_STRIDE = 0x24
FACTOR_C_PTRS = 0xC9E9C
FACTOR_E_PTRS = 0xC9F84

COND_BGE = 0xE               # signed >=   (condition field only; same precedent as V54's bnh)
COND_BL = FF.COND_BC         # unsigned <  (bl == bc, already self-checked by V54)
COND_BNH = V54.COND_BNH      # unsigned <=

# NOTE: keep this SHORT. The full output path must stay under Windows MAX_PATH (260); the first
# attempt at a V54-style descriptive tag produced a 260-char path and failed with FileNotFoundError,
# which looks like a missing directory but is not.
TAG = ("LKAS-4x-V38base-minsteerspeed0"
       "-motorcmd-gp0x6b98-4bit-plus-variantbit"
       "-can330-0x14A-byte4-caveC4B34")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V55-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v55_plain_image.bin"))


# =======================================================================================================
# The four encoders neither FF nor V54 carries. Each is pinned to a REAL code.bin instance.
# =======================================================================================================

def ldh(disp_neg, reg2, reg1=GP):
    """LD.H -disp_neg[reg1],reg2 (op 0x39, hw2 bit0 = 0 selects halfword over word).

    SIGNED load -- gp-0x6b98 is written by `st.h` and read by `ld.h` at all 29 four-byte-form read
    sites, never `ld.hu`. Using V54's unsigned `ld.hu` here would corrupt every negative command."""
    assert 0 < disp_neg <= 0x8000
    return _fmt1(0x39, reg1, reg2) + _le16((0x10000 - disp_neg) & 0xFFFE)


def sar(imm5, reg2):
    """SAR imm5,reg2 (Format II, op 0x15) -- ARITHMETIC shift, sign-preserving.

    V54 used SHR (op 0x14, logical) because gp-0x6966 is unsigned. gp-0x6b98 is signed, so a logical
    shift would map every negative command to a huge positive one."""
    assert 0 <= imm5 <= 31
    return _fmt1(0x15, imm5, reg2)


def ldbu_any(disp, reg2, reg1=GP):
    """LD.BU disp[reg1],reg2 for EITHER sign and EITHER parity of displacement.

    V850E encodes ld.bu as op `1111 0b` where **b = disp bit 0**, with hw2 = (disp & 0xFFFE) | 1 (the
    trailing 1 being the ld.bu/ld.hu selector). V54's helper hard-coded op 0x3C and therefore only ever
    emitted EVEN displacements; gp+0x63fd is ODD, so it needs op 0x3D. Both forms are pinned below."""
    d = disp & 0xFFFF
    return _fmt1(0x3C | (d & 1), reg1, reg2) + _le16((d & 0xFFFE) | 1)


def cmp_imm5(imm5, reg2):
    """CMP imm5,reg2 (Format II, op 0x13) -- compares reg2 against a SIGN-EXTENDED 5-bit immediate."""
    assert -16 <= imm5 <= 15, "Format II imm5 is SIGNED"
    return _fmt1(0x13, imm5 & 0x1F, reg2)


def _self_check_encoders():
    """Every encoder must reproduce a real instance, or an already-self-checked FF/V54 encoder."""
    V54._self_check_encoders()           # ld.hu, shr, movea, Bcond, cmp_rr, shl, ldbu, andi, or_rr, ...

    assert ldh(CMD_DISP, 10) == CMD_REAL_LDH_BYTES, \
        f"ldh fails the real `ld.h -0x6b98[gp],r10` @0x{CMD_REAL_LDH:05X}"
    assert ldh(CMD_DISP, R7).hex() == "243f6894", "ld.h -0x6b98[gp],r7 encoding changed"

    # sar: pinned to the real `sar 0xf,r11` @0x2a202 = 0x5aaf (the Q15 shift in the arb gain chain).
    assert sar(15, 11).hex() == "af5a", "sar fails the real `sar 0xf,r11` @0x2a202"
    assert sar(CMD_SHIFT, R7).hex() == "a93a", "sar 0x9,r7 encoding changed"
    # SAR and SHR must differ in exactly one opcode bit, and must NOT be interchangeable.
    assert sar(CMD_SHIFT, R7) != FF.shr(CMD_SHIFT, R7), "sar collapsed onto shr -- sign would be lost"

    # ld.bu, both parities. The even form must reproduce V54's flashed byte4 read exactly.
    assert ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == V54.V31P_LDBU_BYTE4, \
        "ldbu_any(even) fails V31P's flashed `ld.bu -0x1514[gp],r6`"
    assert ldbu_any(-PAYLOAD_BYTE4_DISP, R6) == V54.ldbu(PAYLOAD_BYTE4_DISP, R6), \
        "ldbu_any disagrees with V54's verified negative-displacement helper"
    assert ldbu_any(VARIANT_DISP, 13) == VARIANT_REAL_LDBU_BYTES, \
        f"ldbu_any(odd) fails the real `ld.bu 0x63fd[gp],r13` @0x{VARIANT_REAL_LDBU:05X}"
    assert ldbu_any(VARIANT_DISP, R6).hex() == "a437fd63", "ld.bu 0x63fd[gp],r6 encoding changed"

    assert cmp_imm5(VARIANT_THRESH, R6).hex() == "6a32", "cmp 0xa,r6 encoding changed"
    try:
        cmp_imm5(16, R6)
    except AssertionError:
        pass
    else:
        raise AssertionError("cmp_imm5 accepted 16 -- Format II imm5 is SIGNED (-16..15)")

    # Branch conditions: only the condition field differs from FF's verified instances.
    assert FF.bcond(COND_BGE, +6).hex() == "be05", "bge +6 encoding changed"
    assert FF.bcond(COND_BL, +6).hex() == "b105", "bl/bc +6 drifted from its real instance"
    assert FF.bcond(COND_BNH, +6).hex() == "b305", "bnh +6 drifted from V54"

    # Setting bit 7 reuses movea with reg1=r7 -- V54's flashed +1-bias encoder, different immediate.
    assert FF.movea(0x80, R7, R7).hex() == "273e8000", "movea 0x80,r7,r7 encoding changed"
    assert FF.movea(1, R7, R7) == V54.bias_r7(1), "movea reg1=r7 form drifted from V54's bias"


# =======================================================================================================
# The cave
# =======================================================================================================

def build_cave():
    """pack_cmd_and_variant -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        ld.h  -0x6b98[gp],r7   ; r7 = final merged motor command (SIGNED, +-8192)
        sar   0x9,r7           ; r7 = cmd >> 9   (arithmetic; -16..15)
        movea 0x8,r7,r7        ; centre -> -8..23
        movea 0x1,r0,r6
        cmp   r6,r7
        bge   +6               ; signed r7 >= 1 -> keep
        movea 0x1,r0,r7        ; else clamp low (0 stays reserved for "did not fire")
      lo_ok:
        movea 0xf,r0,r6
        cmp   r6,r7
        bnh   +6               ; r7 <= 15 -> keep
        movea 0xf,r0,r7        ; else clamp high
      hi_ok:
        shl   0x3,r7           ; -> bits 6:3
        ld.bu 0x63fd[gp],r6    ; damper variant INDEX (note: POSITIVE gp offset)
        cmp   0xa,r6
        bl    +6               ; index < 10 -> leave bit 7 clear
        movea 0x80,r7,r7       ; else set bit 7  (r7 <= 0x78 here, so this is a pure bit-set)
      var_done:
        ld.bu -0x1514[gp],r6   ; 330 payload byte4
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

    emit(ldh(CMD_DISP, R7), f"ld.h -0x{CMD_DISP:x}[gp],r7   ; r7 = MOTOR COMMAND (signed)")
    emit(sar(CMD_SHIFT, R7), f"sar 0x{CMD_SHIFT:x},r7           ; arithmetic >> {CMD_SHIFT}")
    emit(FF.movea(CMD_OFFSET, R7, R7), f"movea 0x{CMD_OFFSET:x},r7,r7      ; centre the field")
    emit(FF.movea(CMD_LO, R0, R6), f"movea 0x{CMD_LO:x},r0,r6      ; low clamp")
    emit(V54.cmp_rr(R6, R7), "cmp r6,r7")
    emit(FF.bcond(COND_BGE, +6), "bge +6              ; signed r7 >= 1 -> skip")
    emit(FF.movea(CMD_LO, R0, R7), f"movea 0x{CMD_LO:x},r0,r7      ; clamp low (0 stays reserved)")
    lo_ok = CAVE_BASE + len(body)
    emit(FF.movea(CMD_HI, R0, R6), f"movea 0x{CMD_HI:x},r0,r6      ; high clamp")
    emit(V54.cmp_rr(R6, R7), "cmp r6,r7")
    emit(FF.bcond(COND_BNH, +6), "bnh +6              ; r7 <= 15 -> skip")
    emit(FF.movea(CMD_HI, R0, R7), f"movea 0x{CMD_HI:x},r0,r7      ; clamp high")
    hi_ok = CAVE_BASE + len(body)
    emit(V54.shl(3, R7), "shl 0x3,r7          ; -> bits 6:3")
    emit(ldbu_any(VARIANT_DISP, R6), f"ld.bu 0x{VARIANT_DISP:x}[gp],r6  ; damper variant INDEX (+gp)")
    emit(cmp_imm5(VARIANT_THRESH, R6), f"cmp 0x{VARIANT_THRESH:x},r6")
    emit(FF.bcond(COND_BL, +6), "bl +6               ; index < 10 -> bit7 stays clear")
    emit(FF.movea(0x80, R7, R7), "movea 0x80,r7,r7    ; set bit 7")
    var_done = CAVE_BASE + len(body)
    emit(ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # Every branch must land exactly on its label. Located BY CONTENT, so inserting an instruction can
    # never silently desynchronise these checks from the branches they guard.
    for cond, label, name in ((COND_BGE, lo_ok, "bge->lo_ok"),
                              (COND_BNH, hi_ok, "bnh->hi_ok"),
                              (COND_BL, var_done, "bl->var_done")):
        raw = FF.bcond(cond, +6)
        sites = [a for a, r, _ in listing if r == raw]
        assert len(sites) == 1, f"expected exactly one {name} branch, found {len(sites)}"
        assert sites[0] + 6 == label, f"{name} target 0x{sites[0] + 6:05X} != label 0x{label:05X}"

    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    return bytes(body), listing


CAVE_BYTES, CAVE_LISTING = build_cave()


# =======================================================================================================
# The wire model -- Python mirror of the cave, instruction for instruction
# =======================================================================================================

def wire_cmd(cmd):
    """The 4-bit field the cave puts on bits 6:3, given a signed gp-0x6b98. Never 0 when live."""
    assert -0x8000 <= cmd <= 0x7FFF
    v = (cmd >> CMD_SHIFT) + CMD_OFFSET      # Python >> on negatives is arithmetic, like SAR
    return max(CMD_LO, min(v, CMD_HI))


def wire_byte4(cmd, variant_index, status_bits=0x7):
    """The full byte4 the cave writes."""
    b = (wire_cmd(cmd) << 3) | (status_bits & PAYLOAD_KEEP_MASK)
    if variant_index >= VARIANT_THRESH:
        b |= 0x80
    return b


def cmd_range_for(field):
    """Inverse: the gp-0x6b98 range a 4-bit field value stands for."""
    if field <= CMD_LO:
        return (None, (CMD_LO - CMD_OFFSET + 1) * (1 << CMD_SHIFT) - 1)
    if field >= CMD_HI:
        return ((CMD_HI - CMD_OFFSET) * (1 << CMD_SHIFT), None)
    lo = (field - CMD_OFFSET) * (1 << CMD_SHIFT)
    return (lo, lo + (1 << CMD_SHIFT) - 1)


def _self_check_wire():
    # Liveness: a live cave can NEVER emit 0 in the waveform field, for ANY input.
    for c in range(-0x8000, 0x8000, 7):
        assert wire_cmd(c) >= CMD_LO, f"wire_cmd({c}) == 0 -- 0 is reserved for 'did not fire'"
        assert wire_cmd(c) <= CMD_HI, f"wire_cmd({c}) overflows the 4-bit field"
    # The field must never bleed into the preserved status bits, nor into the variant bit.
    for c in (-0x2000, -1, 0, 1, 0x2000):
        assert (wire_cmd(c) << 3) & PAYLOAD_KEEP_MASK == 0, "waveform bleeds into status bits 2:0"
        assert (wire_cmd(c) << 3) & 0x80 == 0, "waveform bleeds into the variant bit 7"
    # Monotonicity -- the decode is only meaningful if the map is order-preserving.
    prev = wire_cmd(-0x2000)
    for c in range(-0x2000, 0x2001, 13):
        cur = wire_cmd(c)
        assert cur >= prev, f"wire_cmd not monotonic at {c}"
        prev = cur
    # Zero command must land mid-field, so a symmetric oscillation is not clipped on one side.
    assert wire_cmd(0) == CMD_OFFSET, "zero command must sit at the centre of the field"
    # The realistic excursion (+-3584 = governed LKAS 1024 + COMP 2560) must map onto the field
    # ENDPOINTS -- i.e. the 15 levels are spent exactly on the range the command actually uses, with
    # saturation reserved for the extremes beyond it.
    assert wire_cmd(3584) == CMD_HI and wire_cmd(-3584) == CMD_LO, \
        "the +-3584 realistic excursion must map onto the field endpoints"
    # ...and the interior must be genuinely unclipped across that range, so a ripple is resolved.
    assert wire_cmd(3583) == CMD_HI - 1 and wire_cmd(-3072) == CMD_LO + 1, \
        "the field interior must be unclipped across the realistic excursion"
    # Saturation must be a strict outside-only behaviour: distinct inputs inside the range must not
    # collapse onto the endpoints from within.
    assert wire_cmd(-3073) == CMD_LO and wire_cmd(4095) == CMD_HI, "saturation boundary moved"
    # The variant bit must be independent of the waveform.
    assert wire_byte4(0, 4) & 0x80 == 0 and wire_byte4(0, 10) & 0x80 == 0x80, "variant bit wrong"
    assert wire_byte4(0, 4) & 0x78 == wire_byte4(0, 10) & 0x78, "variant bit disturbs the waveform"


# =======================================================================================================

def u16(code, address):
    return struct.unpack_from("<H", code, address)[0]


def assert_probe_sites(code, hook_is_stock=True):
    """Everything this cave reads or hooks must be where the analysis says it is.

    `hook_is_stock` is True pre-write (the site must still be the displaced movea) and False after the
    jarl has been patched in -- at which point the site must be exactly that jarl and nothing else."""
    if hook_is_stock:
        assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site is not the stock movea"
    else:
        assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
            "hook site is not the expected jarl into the cave"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    assert bytes(code[0x55AD4:0x55AD4 + 4]) == V54.V31P_LDBU_BYTE4, \
        "stock 330 builder's byte4 access @0x55AD4 moved -- payload offset not confirmed"
    # Signal 1: the store that defines gp-0x6b98, and the real ld.h our encoder is pinned to.
    assert bytes(code[CMD_STORE:CMD_STORE + 4]) == CMD_STORE_BYTES, \
        f"the gp-0x6b98 store @0x{CMD_STORE:05X} moved -- signal 1 is not confirmed"
    assert bytes(code[CMD_REAL_LDH:CMD_REAL_LDH + 4]) == CMD_REAL_LDH_BYTES, \
        f"the real ld.h @0x{CMD_REAL_LDH:05X} moved -- the encoder has lost its anchor"
    # Signal 2: the real ld.bu our odd-displacement encoder is pinned to.
    assert bytes(code[VARIANT_REAL_LDBU:VARIANT_REAL_LDBU + 4]) == VARIANT_REAL_LDBU_BYTES, \
        f"the real ld.bu 0x63fd[gp] @0x{VARIANT_REAL_LDBU:05X} moved -- signal 2 is not confirmed"


def assert_variant_tables(code):
    """The ROW->INDEX->table chain must be exactly as analysed, or bit 7 means nothing."""
    rows = []
    for n in range(16):
        key = bytes(code[VARIANT_KEY_TABLE + n * VARIANT_STRIDE:
                         VARIANT_KEY_TABLE + n * VARIANT_STRIDE + 5]).decode("ascii", "replace")
        idx = code[VARIANT_IDX_TABLE + n * VARIANT_STRIDE]
        cptr = struct.unpack_from("<I", code, FACTOR_C_PTRS + idx * 4)[0]
        eptr = struct.unpack_from("<I", code, FACTOR_E_PTRS + idx * 4)[0]
        rows.append((n, key, idx, cptr, eptr))
    by_key = {k: (i, c, e) for _, k, i, c, e in rows}
    assert by_key["TVAA1"] == (10, 0xD27BC, 0xD27F8), \
        "TVAA1 no longer resolves to index 10 / 0xD27BC / 0xD27F8 -- the whole bit-7 reading is void"
    assert by_key["TVAA0"][0] == 4 and by_key["TVAA2"][0] == 4 and by_key["TVAA4"][0] == 4, \
        "the TVA family no longer splits 4-vs-10 -- bit 7 would not discriminate"
    # The threshold must actually separate the two candidate outcomes.
    assert by_key["TVAA0"][0] < VARIANT_THRESH <= by_key["TVAA1"][0], \
        "VARIANT_THRESH does not separate index 4 from index 10"
    # V44/V47 edited entries 10 and 11; bit7=1 must imply one of the tables they touched.
    assert struct.unpack_from("<I", code, FACTOR_C_PTRS + 10 * 4)[0] == 0xD27BC
    assert struct.unpack_from("<I", code, FACTOR_E_PTRS + 10 * 4)[0] == 0xD27F8
    return rows


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    V54.assert_v38_baseline(baseline)
    assert_probe_sites(baseline)
    rows = assert_variant_tables(baseline)
    FF.assert_crc_chain(baseline, "V38 baseline")
    assert walk(bytes(baseline), label="V38 baseline") == 0
    assert walk_all_blocks(bytes(baseline), label="V38 baseline") == 0
    V53.assert_sole_reader(baseline)

    source_rwd = open(V38_RWD, "rb").read()
    assert hashlib.sha256(source_rwd).hexdigest() == V38_RWD_SHA256
    FF.assert_x31_checksum(source_rwd, "V38 source")
    source_info = parse_x31(source_rwd)
    assert source_info["headers"] == EXPECTED_HEADERS
    assert source_info["key"] == list(V9B["keys"])
    assert source_info["blocks"] == [{"start": START, "length": END - START}]
    decode = build_decode_table(V9B["keys"], V9B["ops"])
    encode = invert_table(decode)
    assert bytes(source_info["encs"][0]).translate(decode) == bytes(baseline[START:END]), \
        "V38 RWD does not decode to _v38_plain_image.bin"

    _self_check_encoders()
    _self_check_wire()

    code = bytearray(baseline)

    # ---- CHANGE 1 (CODE): the dual probe cave + its hook ------------------------------------------
    hook_bytes = FF.jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"\n  CHANGE 1 (CODE) -- dual probe into CAN 330 / 0x14A byte4:")
    print(f"    cave @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes "
          f"(limit {CAVE_HARD_LIMIT - CAVE_BASE}, "
          f"headroom {CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)})")
    print(f"    hook @0x{HOOK_ADDR:05X}: {HOOK_STOCK.hex()} -> {hook_bytes.hex()}  "
          f"(movea -> jarl 0x{CAVE_BASE:05X},lp), returns to 0x{HOOK_ADDR + 4:05X}")
    print(f"    checksum FUN_00057b24 @0x{CHECKSUM_FN:05X} runs AFTER the hook -> covers the probe bits")
    for addr, raw, text in CAVE_LISTING:
        print(f"      0x{addr:05X}  {raw.hex():<12s} {text}")

    code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)] = CAVE_BYTES
    code[HOOK_ADDR:HOOK_ADDR + 4] = hook_bytes
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave bytes not written"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_HARD_LIMIT]) == \
        b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)), "cave tail moved"

    # ---- CHANGE 2 (CAL, 1 halfword): minimum steer speed 320 -> 0 ---------------------------------
    print(f"\n  CHANGE 2 (CAL, 1 halfword) -- minimum steer speed (carried from V53, CONFIRMED on-car):")
    struct.pack_into("<H", code, V53.LOCKOUT_ADDR, V53.LOCKOUT_NEW)
    print(f"    0x{V53.LOCKOUT_ADDR:05X}: {V53.LOCKOUT_STOCK} -> {V53.LOCKOUT_NEW}   "
          f"({V53.LOCKOUT_STOCK / 64.0625:.3f} km/h -> 0)")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    V53.assert_stock_cals(code, "V55")

    # ---- the measurement ---------------------------------------------------------------------------
    print(f"\n  WIRE ENCODING -> 0x14A byte4")
    print(f"    bit  7   = (gp+0x{VARIANT_DISP:x} damper variant INDEX >= {VARIANT_THRESH})")
    print(f"    bits 6:3 = clamp((gp-0x{CMD_DISP:x} >> {CMD_SHIFT}) + {CMD_OFFSET}, "
          f"{CMD_LO}, {CMD_HI})   [{1 << CMD_SHIFT} counts/level]")
    print(f"    bits 2:0 = stock STEER_SENSOR_STATUS, preserved")
    print(f"    rlog decode: field = (byte4 >> 3) & 0x0F ; variant = (byte4 >> 7) & 1")
    print(f"    *** field == 0 means THE CAVE DID NOT FIRE -- the drive is VOID, not 'low command'")
    print(f"\n    {'gp-0x6b98':>10s}  {'field':>5s}   decoded range")
    for c in (-8192, -3584, -2048, -1024, -512, -1, 0, 511, 1024, 2048, 3584, 8191):
        f = wire_cmd(c)
        lo, hi = cmd_range_for(f)
        rng = (f"<= {hi}" if lo is None else f">= {lo}" if hi is None else f"{lo}..{hi}")
        print(f"    {c:10d}  {f:5d}   {rng}")

    print(f"\n    variant bit 7, and what each answer licenses:")
    print(f"      0  -> INDEX < 10  -> V44/V47 edited an INERT table; damping is UNTESTED "
          f"(retest on index 4 = 0xD07BC/0xD07F8)")
    print(f"      1  -> INDEX >= 10 -> V44/V47 edited the LIVE table; damping is genuinely FALSIFIED")
    print(f"\n    ROW -> INDEX -> table chain in this image:")
    for n, key, idx, cptr, eptr in rows:
        star = "  <== our PN 39990-TVA-A160" if key == "TVAA1" else ""
        print(f"      row {n:2d}  {key:>5s}  idx {idx:2d}  C=0x{cptr:05X} E=0x{eptr:05X}"
              f"  bit7={1 if idx >= VARIANT_THRESH else 0}{star}")

    # ---- CRC coverage -----------------------------------------------------------------------------
    assert V53.owning_block(code, CAVE_BASE) == MAIN_BLOCK, "cave is not in the MAIN CRC block"
    assert V53.owning_block(code, HOOK_ADDR) == MAIN_BLOCK, "hook is not in the MAIN CRC block"
    assert V53.owning_block(code, V53.LOCKOUT_ADDR) == CAL_BLOCK, "lockout is not in the CAL CRC block"
    print()
    for block in sorted({MAIN_BLOCK, CAL_BLOCK}):
        old_crc = struct.unpack_from("<I", code, block[1])[0]
        new_crc = zlib.crc32(code[block[0]:block[1]]) & 0xFFFFFFFF
        struct.pack_into("<I", code, block[1], new_crc)
        print(f"  CRC [0x{block[0]:X},0x{block[1]:X}) @0x{block[1]:X}: 0x{old_crc:08X} -> 0x{new_crc:08X}")

    # ---- exact diff vs V38 ------------------------------------------------------------------------
    allowed = set(range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES)))
    allowed.update(range(HOOK_ADDR, HOOK_ADDR + 4))
    allowed.update({V53.LOCKOUT_ADDR, V53.LOCKOUT_ADDR + 1})
    for block in (MAIN_BLOCK, CAL_BLOCK):
        allowed.update(range(block[1], block[1] + 4))
    diff = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    stray = [i for i in diff if i not in allowed]
    assert not stray, f"UNEXPECTED byte changes: {[hex(x) for x in stray[:20]]}"
    print(f"\n  V55 vs V38: {len(diff)} bytes changed in [0x13000,0x100000), all accounted for")
    runs = []
    for i in diff:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates: everything re-verified on the BUILT image -------------------------------
    FF.assert_crc_chain(code, "V55")
    assert walk(bytes(code), label="V55") == 0
    assert walk_all_blocks(bytes(code), label="V55") == 0
    assert_probe_sites(code, hook_is_stock=False)
    assert_variant_tables(code)
    assert u16(code, V53.AUTHORITY_LERP_ADDR) == V53.AUTHORITY_LERP_STOCK[0], \
        "0xC6AF0 must remain stock -- V55 is report-only"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "the 0xC6AF0 authority LERP moved"
    # The damper tables V44/V47 touched must be STOCK here -- V55 changes no dynamics.
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A):
        assert u16(code, a) == u16(baseline, a), f"damper cal 0x{a:05X} moved -- V55 is report-only"

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}")
    print(f"    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback -------------------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    open(OUT, "wb").write(rwd)
    FF.assert_x31_checksum(rwd, "V55 output")
    back = parse_x31(rwd)
    assert back["headers"] == EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    round_trip = bytearray(baseline)
    round_trip[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(round_trip[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(round_trip, "V55 readback")
    assert walk(bytes(round_trip), label="V55 readback") == 0
    assert walk_all_blocks(bytes(round_trip), label="V55 readback") == 0
    assert_probe_sites(round_trip, hook_is_stock=False)
    assert_variant_tables(round_trip)
    assert bytes(round_trip[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        "cave does not survive the RWD round trip"

    print(f"  wrote {OUT}")
    print(f"    SHA256 {hashlib.sha256(rwd).hexdigest()}")
    print("\n  GATE 1 (RAM): reads gp-0x6b98, gp+0x63fd, gp-0x1514; writes ONE byte (gp-0x1514, RMW,")
    print("                bits 2:0 preserved). NO scratch RAM. Clobbers r6/r7 only (proven dead).")
    print("  GATE 2 (loop): vacuous -- report-only. 0xC6AF0 stock; no filter/pole/gain/clamp/damper moves.")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
