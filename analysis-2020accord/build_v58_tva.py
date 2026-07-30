#!/usr/bin/env python3
"""build_v58_tva.py -- V58 = V57 with the cave payload replaced by the ANGLE-RATE LANE probe.

WHAT V58 IS
-----------
A POST-PROCESSOR over `_v57_plain_image.bin`. It transcribes nothing from V57 -- not the cave, not the
hook, not the calibration. Same principle V56 used over V55 and V53 used with FOURFRAME2.

*** V58 CHANGES NOTHING BUT THE CAVE PAYLOAD. *** V57's calibration (the 0xC646C decoupling: 0x2A1F0
disp -> 0x7CD0, 0xC6CD0 <- 3564, 0xC646C -> 891) is on the car, fault-free, and stays byte-identical.
Same cave base 0xC4B34, same hook 0x55C0E, same 68-byte extent. Only the MAIN CRC block moves.

WHY THIS PROBE
--------------
Every calibration lever for both symptoms is now closed (see docs/BUILD-LINEAGE.md):
  RATCHET (~7.4 Hz): 0xC61D6 slew REJECTED (activates an uncalibrated 2D map; "highest-risk, last/never");
      0xC6424 deadband INERT (pinned while slew=0); 0xC64DE re-engage ramp ALREADY applied at 27 since
      V18; 0x454FE fixed by V42 and ST==4 never fires on-car; the +-565 slew is a CODE IMMEDIATE
      (`mov 0x440d4000,r6` = 565.0f), not cal-editable; no output rate limiter exists as a cal.
  GRINDING (20-25 Hz): no usable notch -- the two 3-tap FIR slots (0xC4018/1C/20 and 0xC4048/4C/50,
      both stock (1.0,0.0,0.0) = identity) run at 1 kHz, where a 21 Hz notch needs b=[1,-1.9826,1],
      which costs -35.2 dB at DC and needs coefficients of ~(57,-114,57) to normalise. Ill-conditioned;
      dead as a lever. 0xC6372/0xC636E is a DEAD BRANCH (tp+0x7498=tp+0x7499=1 routes boost AND damping
      past it to read gp-0x6ba6 directly). Damping's own table 0xD2738 is flat unity -- a no-op.
      gp-0x6bbe's damping SIGN is unresolved: gp-0x6a56 is NOT independently sensed (it is
      clamp(polarity*((gp-0x6abe*48*cal)>>15), +-12000), i.e. MOTOR resolver rate scaled) and baseline's
      Branch A is also gp-0x6abe-derived, so `rate_error = baseline - angle_rate` may partially cancel.

=> Nothing is buildable with a certified sign. This probe measures the two things that would settle it.

WHAT IT MEASURES -- CAN 0x14A byte4, 100 Hz
-------------------------------------------
    bit 7 = 1                        LIVENESS (constant; field==0 => the cave did not fire => VOID)
    bit 6 = (gp-0x6bbe <  0)         SIGN of the angle-rate/boost lane  -> the DAMPING PHASE
    bit 5 = (gp-0x6bbe == +512)      the lane pinned at its POSITIVE ceiling (0xD20C0, flat 512)
    bit 4 = (gp-0x6b9a <  0)         SIGN of the FIR chain output = boost's AMPLITUDE GATE
    bit 3 = (gp-0x6b9a == 0)         that gate dead/zero
    bits 2:0 = stock STEER_SENSOR_STATUS_1/2/3, preserved

bit6 is the primary result. STEER_ANGLE_RATE is ALREADY on the bus (0x18F[2:4]), so the cross-spectrum
phase between bit6 and it at 20-25 Hz measures the damping sign directly -- the thing static analysis
has flip-flopped on three times. The method is VALIDATED, not hoped for: V57's bit3 is a 1-bit sign
channel and it returned coherence 0.958 at 21.31 Hz against STEER_ANGLE_RATE on route 29's burst.

bit5 catches the real failure mode: the lane's ceiling is a SATURATING clamp, so if it pins, the
damping derivative goes to ZERO exactly at the peaks of the grinding -- damping vanishing where it is
needed. Only the POSITIVE rail is exactly testable with an arithmetic shift (x>>9 == 1 iff x == 512;
x>>9 == -1 for ALL x in [-512,-1]), so the negative rail is inferred from bit6 + bit5 together.

bit4/bit3 test the mechanism found 2026-07-30: gp-0x6ba6/gp-0x6b9a is the FIR chain's output and it
indexes boost's NON-flat table (0xD28DC, Y = 16384..8187 -- more motor rate, HALF the boost amplitude),
landing as `blendedMagnitude` in `term3 = (term2 * blendedMagnitude) >> 14` @0x34ffa. If that gate
oscillates at 20-25 Hz it amplitude-modulates the strongest identified carrier. Nobody has computed the
FIR -> clamp -> 565-slew -> 2-EMA cascade response, so measure it rather than model it.

🛑🛑 THE PARAGRAPH ABOVE IS WRONG ON BOTH COUNTS -- corrected 2026-07-30 AFTER V58 flew, by byte read
of the image plus fresh disassembly. Kept as written (this kit does not rewrite history) with the
correction attached. The bit4 MEASUREMENT is sound and reproduced across four runs; only the mechanism
hung on it was wrong. See docs/HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md.

  (1) `gp-0x6b9a` does NOT index anything. Its ONLY live consumer in FUN_00034a72 is a five-input
      plausibility gate -- `|gp-0x6b9a| <= 25600` (addi 0x6400 / ori 0xc801 / cmp / bnc @0x34c9c-cb4)
      ANDed with checks on gp-0x6ba6, gp-0x4f68, gp-0x4f60 and gp-0x6c2e into r21, which zeroes r24
      @0x34fc8. r15 is OVERWRITTEN at 0x34ca4, so no value path survives. Its SIGN -- the thing bit4
      measures -- has no effect on the output at all. Two of its three reads in that function
      (@0x34b5e, @0x34b68) are DEAD CODE: tp+0x7499 = 1 (byte-verified) takes the branch @0x34b3c.
  (2) `0xD28DC` is real but hangs off pointer table **0xca4f4**, NOT 0xca23c. Resolved from image
      bytes LE across all 34 modes: 0xca4f4 -> ...0xD28DC... (PRESENT); 0xca23c -> ...0xD2888...
      (0xD28DC ABSENT). 0xca154 / 0xc7970 / 0xca06c / 0xca40c / 0xca324: absent.

  *** THE ACTUAL INDEX IS `gp-0x6ba6`, and `gp-0x6ba6 == |gp-0x6b9a|`. *** FUN_0003b66a writes both
  from the same r28: `cmp r0,r28 / mov r28,r13 / bge 0x3b886 / subr r0,r13` @0x3b874-87c takes the
  magnitude, then st.h r13,-0x6ba6[gp] @0x3b892 and st.h r28,-0x6b9a[gp] @0x3b8b0. Byte-scanned for
  BOTH gp-relative encodings: exactly one writer each, image-wide.

  CONSEQUENCE, and it is why V59 exists: V58 measured the SIGNED sibling crossing zero at 20.93 Hz
  (per-run coherence 0.649/0.970/0.769/0.881; 13.69 toggles/s ENGAGED vs 0.61 DISENGAGED at matched
  creep). The table index is therefore that signal RECTIFIED -- a minimum at every zero crossing,
  sweeping the boost amplitude curve at ~2x the mode frequency on the BASE ASSIST path. The
  parametric mechanism is real; it just lives one cell over. What V58 cannot say is DEPTH: a sign bit
  carries no amplitude, and if |gp-0x6b9a| never clears X1 = 512 the coefficient stays pinned at 16384
  and nothing modulates. V59 (thermometer on gp-0x6ba6 at 512/1024/2048) measures exactly that.

CAVE DISCIPLINE
---------------
Read-only. Four EXACT single comparisons, one arithmetic shift, no arithmetic on any signal, no new RAM,
two scratch registers only (r6 = value, r7 = accumulator) -- exactly V57's register budget.
*** Only condition codes already PINNED to real instruction instances are used: BGE (0xE) and BNE (0xA).
BLT/BLE/BGT are deliberately avoided -- introducing an unpinned cond field into a cave is not worth a
polarity convenience. *** Code caves are this kit's ONLY bricking class (V24, V27, V48B all bricked the
ECU), which is why this reuses a base/hook/extent that has already flown fault-free.

NOT PROBEABLE, deliberately omitted: the +-666 mid-chain clamp and the rate_error +-12000 clamp inside
FUN_00034a72 are TRANSIENT REGISTERS (r13/r22), never stored to any gp-relative cell. Reaching them
would need added arithmetic in the cave. Refused.

Decoder: rlog-tools/decode_v58_boostlane.py
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

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from firmware_paths import plain_image_path, RWD_DIR
from verify_bootloader_crc import walk, walk_all_blocks
from build_vfourframe_tva import GP, R0, R6, R7

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34 -- unchanged from V55/V57
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E -- unchanged
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- the probe ------------------------------------------------------------------------------------
LANE_DISP = 0x6bbe          # gp-0x6bbe, signed halfword -- the angle-rate/boost lane output
GATE_DISP = 0x6b9a          # gp-0x6b9a, signed halfword -- FIR chain output (boost amplitude gate)

LANE_CEILING = 512          # 0xD20C0 LERP, count=5, X=(0,640,2560,5760,6400), Y=(512,)*5 -- flat
RAIL_SHIFT = 9              # x >> 9 == 1  <=>  x == 512 exactly, for x clamped to [-512, +512]

BIT_LIVE, BIT_SIGN, BIT_RAIL, BIT_GSIGN, BIT_GZERO = 0x80, 0x40, 0x20, 0x10, 0x08

COND_BNE = V57.COND_BNE     # 0xA, Z == 0   -- pinned to the real `bne 0x2a246` @0x2a240
COND_BGE = V57.COND_BGE     # 0xE, signed >= -- pinned to the real `bge 0x2a222` @0x2a21a

TAG = "LKAS-4x-mss0-decouple0xC646C-boostlaneprobe-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V58-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v58_plain_image.bin"))
V57_BIN = str(plain_image_path("_v57_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


def _self_check_encoders():
    """Every encoder must reproduce a real instance, or an already-self-checked FF/V54/V55 encoder."""
    V57._self_check_encoders()          # inherits V55/V54/FF self-checks incl. sar, cmp_imm5, ldh

    # sar: pinned in V55 to the real `sar 0xf,r11` @0x2a202, whose bytes ARE `af5a` (file order).
    assert V55.sar(0xF, 11).hex() == "af5a", "sar drifted from the real `sar 0xf,r11` @0x2a202"
    # Decode OUR operand out of the encoding rather than trusting the helper: Format II packs
    # hw = (reg2 << 11) | (op << 5) | imm5, op(sar) = 0x15.
    hw = struct.unpack("<H", V55.sar(RAIL_SHIFT, R6))[0]
    assert (hw >> 11) == R6, f"sar reg2 field is {hw >> 11}, expected r{R6}"
    assert ((hw >> 5) & 0x3F) == 0x15, "sar opcode field is not 0x15"
    assert (hw & 0x1F) == RAIL_SHIFT, f"sar imm5 field is {hw & 0x1F}, expected {RAIL_SHIFT}"

    # cmp imm5: Format II, SIGNED 5-bit immediate, op 0x13. Our only use is cmp 1,r6.
    hw = struct.unpack("<H", V55.cmp_imm5(1, R6))[0]
    assert (hw >> 11) == R6, f"cmp_imm5 reg2 field is {hw >> 11}, expected r{R6}"
    assert ((hw >> 5) & 0x3F) == 0x13, "cmp_imm5 opcode field is not 0x13"
    assert (hw & 0x1F) == 1, "cmp_imm5 imm5 field is not 1"
    assert V55.cmp_imm5(1, R6) != V55.cmp_imm5(1, R7), "cmp_imm5 ignores its register operand"
    assert V55.cmp_imm5(1, R6) != V55.cmp_imm5(2, R6), "cmp_imm5 ignores its immediate"

    # ld.h displacement: the second halfword must be the two's-complement of the gp offset.
    for disp in (LANE_DISP, GATE_DISP):
        raw = V55.ldh(disp, R6)
        assert len(raw) == 4, "ld.h must be 4 bytes"
        assert struct.unpack_from("<H", raw, 2)[0] == (0x10000 - disp) & 0xFFFF, \
            f"ld.h -0x{disp:x}[gp] displacement halfword is wrong"

    # Only PINNED condition codes. Assert we never emit anything else.
    assert FF.bcond(COND_BNE, +6).hex() == "ba05", "bne +6 fails the real instance @0x2a240"
    assert FF.bcond(COND_BGE, +6).hex() == "be05", "bge +6 drifted from V55/V57"
    assert FF.bcond(COND_BGE, +8).hex() == "ce05", "bge +8 fails the real instance @0x2a21a"

    # The bit-set moveas are the reg1=r7 accumulate form V54/V55/V57 all flashed.
    for bit in (BIT_SIGN, BIT_RAIL, BIT_GSIGN, BIT_GZERO):
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"movea 0x{bit:x},r7,r7 malformed"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"


def build_cave():
    """pack_boost_lane_state -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.h  -0x6bbe[gp],r6   ; the angle-rate/boost lane output (signed)
        cmp   r0,r6
        bge   +6               ; >= 0 -> leave bit6 clear
        movea 0x40,r7,r7       ; bit6 = lane NEGATIVE            <- THE DAMPING PHASE
      sign_done:
        sar   9,r6             ; r6 = lane >> 9; == 1 iff lane == +512 (lane is clamped to +-512)
        cmp   1,r6
        bne   +6               ; != 1 -> not at the positive ceiling
        movea 0x20,r7,r7       ; bit5 = lane PINNED at +512
      rail_done:
        ld.h  -0x6b9a[gp],r6   ; FIR chain output = boost's amplitude gate (signed)
        cmp   r0,r6
        bge   +6               ; >= 0 -> leave bit4 clear
        movea 0x10,r7,r7       ; bit4 = gate NEGATIVE
      gsign_done:
        cmp   r0,r6            ; r6 still holds gp-0x6b9a (movea wrote r7 only)
        bne   +6               ; != 0 -> leave bit3 clear
        movea 0x8,r7,r7        ; bit3 = gate EXACTLY ZERO
      gzero_done:
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

    emit(V55.ldh(LANE_DISP, R6), f"ld.h -0x{LANE_DISP:x}[gp],r6  ; boost/angle-rate lane")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BGE, +6), "bge +6              ; >= 0 -> not negative")
    emit(FF.movea(BIT_SIGN, R7, R7), "movea 0x40,r7,r7    ; bit6 = lane NEGATIVE")
    sign_done = CAVE_BASE + len(body)

    emit(V55.sar(RAIL_SHIFT, R6), f"sar {RAIL_SHIFT},r6             ; lane >> {RAIL_SHIFT}")
    emit(V55.cmp_imm5(1, R6), "cmp 1,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 1 -> not at +512")
    emit(FF.movea(BIT_RAIL, R7, R7), "movea 0x20,r7,r7    ; bit5 = lane PINNED at +512")
    rail_done = CAVE_BASE + len(body)

    emit(V55.ldh(GATE_DISP, R6), f"ld.h -0x{GATE_DISP:x}[gp],r6  ; FIR out = amplitude gate")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BGE, +6), "bge +6              ; >= 0 -> not negative")
    emit(FF.movea(BIT_GSIGN, R7, R7), "movea 0x10,r7,r7    ; bit4 = gate NEGATIVE")
    gsign_done = CAVE_BASE + len(body)

    emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; r6 still = gp-0x6b9a")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> not zero")
    emit(FF.movea(BIT_GZERO, R7, R7), "movea 0x8,r7,r7     ; bit3 = gate EXACTLY ZERO")
    gzero_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # Every branch must land exactly on its label. Located BY POSITION, not by content: this cave
    # reuses `bge +6` twice AND `bne +6` twice, so a content-based lookup would be ambiguous.
    branch_targets = [(3, sign_done, "bge->sign_done"),
                      (7, rail_done, "bne->rail_done"),
                      (11, gsign_done, "bge->gsign_done"),
                      (14, gzero_done, "bne->gzero_done")]
    for idx, label, name in branch_targets:
        addr, raw, _ = listing[idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"

    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    assert len(body) <= len(V55.CAVE_BYTES), \
        f"V58 cave ({len(body)}B) exceeds the proven extent ({len(V55.CAVE_BYTES)}B)"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


def decode_field(byte4):
    """Decode 0x14A byte4 into V58's five bits. field == 0 => THE CAVE DID NOT FIRE (VOID)."""
    field = (byte4 >> 3) & 0x1F
    if field == 0:
        return None
    return {
        "live": bool(byte4 & BIT_LIVE),
        "lane_negative": bool(byte4 & BIT_SIGN),
        "lane_at_pos_ceiling": bool(byte4 & BIT_RAIL),
        "gate_negative": bool(byte4 & BIT_GSIGN),
        "gate_zero": bool(byte4 & BIT_GZERO),
    }


def assert_probe_sites(code, label="V58"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    # Nothing of V57's payload may survive past our jmp.
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V57 cave remnants survive past our payload"


def build():
    if not os.path.exists(V57_BIN):
        print(f"  {V57_BIN} missing -- running the V57 builder first\n")
        V57.build()
    v57 = bytearray(open(V57_BIN, "rb").read())
    print(f"  V57 source {V57_BIN}\n    SHA256 {hashlib.sha256(bytes(v57)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v57, "V57 source")
    assert walk(bytes(v57), label="V57 source") == 0
    assert walk_all_blocks(bytes(v57), label="V57 source") == 0
    V57.assert_probe_sites(v57, "V57 source")        # V57's OWN cave must be intact first
    V55.assert_variant_tables(v57)
    V57.assert_decoupled(v57, "V57 source")
    assert u16(v57, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V57 source lost the lockout edit"

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v57)

    # ---- pre-flight: V57's calibration must be exactly what we expect to CARRY FORWARD ------------
    assert u16(code, V57.PRIVATE_ADDR) == V57.GAIN_4X, "V57's private LKAS gain is not 3564"
    assert u16(code, V57.GAIN_ADDR) == V57.GAIN_STOCK, "V57's shared sensor scale is not stock 891"
    assert u16(code, V57.DISP_OFF) == V57.DISP_NEW, "V57's retargeted displacement is missing"
    assert u16(code, V57.LOAD_ADDR) == V57.INSN_HW1, "the opcode/register halfword moved"

    # the lane and gate we are about to read must be inside the gp-relative window the encoders assume
    assert 0 < LANE_DISP <= 0x7FFF and 0 < GATE_DISP <= 0x7FFF
    assert LANE_DISP % 2 == 0 and GATE_DISP % 2 == 0, "ld.h needs an EVEN displacement"

    # the ceiling this probe tests against must still be the flat 512 LERP we measured
    lerp = struct.unpack_from("<11H", code, 0xD20C0)
    assert lerp[0] == 5, f"0xD20C0 point count is {lerp[0]}, expected 5"
    assert lerp[1:6] == (0, 640, 2560, 5760, 6400), f"0xD20C0 X row moved: {lerp[1:6]}"
    assert lerp[6:11] == (LANE_CEILING,) * 5, f"0xD20C0 Y row is not flat {LANE_CEILING}: {lerp[6:11]}"

    # ---- THE ONLY EDIT: replace the cave payload -------------------------------------------------
    print(f"\n  THE PROBE -- replace V57's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes, V57 was {len(V57.CAVE_BYTES)}):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v57[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V57's -- same cave base, same jarl"
    assert_probe_sites(code, "V58")

    # ---- everything V57 established must still hold ----------------------------------------------
    V57.assert_decoupled(code, "V58")
    V55.assert_variant_tables(code)
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "0xC6AF0 must stay STOCK -- V56's mute is falsified"
    # V58 is a PROBE: not one calibration byte may move relative to V57.
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC61B2, "fwd clamp"), (0xC61B4, "fwd clamp"),
                    (0xC6440, "r24"), (0xC6442, "r24"), (0xC6446, "r24"), (0xC61F6, "r24 deadzone"),
                    (0xC643E, "r26"), (0xC61D6, "slew step -- V16 REJECTED, must stay 0"),
                    (0xC6424, "shaper deadband"), (0xC64C9, "2D-map mux"),
                    (0xC646C, "shared sensor scale"), (0xC6CD0, "private LKAS gain")):
        assert u16(code, a) == u16(v57, a), f"{name} 0x{a:05X} moved -- V58 changes NO calibration"
    assert code[0xC64DE] == v57[0xC64DE] == 27, "V18's re-engage ramp must stay at 27"
    assert code[0xC64A3] == v57[0xC64A3] == 1, "the deadband ENABLE byte must stay stock"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A,
              0xD200C, 0xD2000):
        assert u16(code, a) == u16(baseline, a), f"damper/rate cal 0x{a:05X} moved"
    # the two FIR coefficient triples must stay identity -- V58 does NOT enable them
    for a in (0xC4018, 0xC401C, 0xC4020, 0xC4048, 0xC404C, 0xC4050):
        assert struct.unpack_from("<I", code, a) == struct.unpack_from("<I", v57, a), \
            f"FIR coefficient 0x{a:05X} moved -- V58 must not touch the FIR"

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
    d57 = [i for i in range(0x13000, 0x100000) if code[i] != v57[i]]
    permitted = (set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
                 | set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)))
    stray = [i for i in d57 if i not in permitted]
    assert not stray, f"V58 vs V57 touches bytes outside the cave + MAIN CRC: {[hex(x) for x in stray]}"
    assert set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)) <= set(d57), "MAIN CRC trailer did not move"
    cal_trailer = set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
    assert not (cal_trailer & set(d57)), \
        "the CAL CRC moved -- V58 changes no calibration, so it must not"
    print(f"\n  V58 vs V57: {len(d57)} bytes  (cave payload + MAIN CRC only; CAL block untouched)")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V58 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V58")
    assert walk(bytes(code), label="V58") == 0
    assert walk_all_blocks(bytes(code), label="V58") == 0
    assert_probe_sites(code, "V58")
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
    FF.assert_x31_checksum(rwd, "V58 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V58 readback")
    assert walk(bytes(readback), label="V58 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V58 readback") == 0
    assert_probe_sites(readback, "V58 readback")
    V55.assert_variant_tables(readback)
    V57.assert_decoupled(readback, "V58 readback")
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

    print(f"\n  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  PROBE: 0x14A byte4  bit7=LIVENESS  bit6=(gp-0x6bbe<0, the DAMPING PHASE)")
    print("                      bit5=(gp-0x6bbe==+512, lane pinned at its ceiling)")
    print("                      bit4=(gp-0x6b9a<0)  bit3=(gp-0x6b9a==0)  bits2:0 = stock status")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("  GATE 1 RAM ownership: INHERITED -- same cave base/hook/extent as V55/V57, both of which")
    print("          flew fault-free. Read-only, no new RAM, r6/r7 only (V57's exact budget).")
    print("  GATE 2 closed-loop stability: VACUOUS -- V58 writes nothing to any control path and")
    print("          changes NO calibration byte. Its only output is a TX payload byte no control")
    print("          path reads. *** Still CODE in the 1 kHz TX path: a higher risk class than")
    print("          cal-only, which is why the base/hook/extent are reused rather than moved.")
    print("\n  HOW TO READ IT: cross-spectrum phase of bit6 against STEER_ANGLE_RATE (0x18F[2:4],")
    print("          already on the bus) at 20-25 Hz gives the damping sign directly. Method")
    print("          validated on V57's bit3: coherence 0.958 at 21.31 Hz from a 1-bit channel.")
    print("          Condition on LATERAL engagement (carControl.latActive / 0x18F byte4 bit3),")
    print("          NEVER carState.cruiseState.enabled, and use SUSTAINED effort")
    print("          |lowpass(tq,3Hz)|<=200 for hands-off -- the raw |tq|<=200 test discards the")
    print("          frames carrying 8.79x the oscillation amplitude.")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
