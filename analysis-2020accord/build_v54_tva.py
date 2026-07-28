"""
build_v54_tva.py -- V54 = V38 + minimum steer speed 0 + a 5-bit AUTHORITY probe piggybacked into CAN 330.

=======================================================================================================
V54 IN ONE LINE
    V38 calibration, `0xC62EA` 320 -> 0 (steer-to-zero, carried over from V53), and a 40-byte read-only
    cave that packs `gp-0x6966` (the FUN_0003a382 authority index) into CAN 330 / 0x14A byte4 bits 7:3
    at 100 Hz -- on a frame PROVEN to reach the comma.

WHY THIS BUILD EXISTS  [2026-07-27, after the V53 drive]
    V53 flashed and drove. Steer-to-zero worked -- confirmed independently from the rlog, not just by
    report: raw CAN 399 shows `STEER_STATUS = 0` in 100% of 5,995 frames and 226 frames of
    `STEER_CONTROL_ACTIVE = 1` below 5 km/h, a cell that is structurally EMPTY on V38.

    But the four-frame telemetry (`0x6A0`-`0x6A3`) was ABSENT from the rlog -- 0 frames across 301,824
    CAN frames on buses 0/1/2/128/129. And the null is UNINTERPRETABLE: six IDs the stock firmware
    genuinely broadcasts (`0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723`) are equally absent from
    the same log, while the three openpilot's DBC knows (`0x14A`, `0x18F`, `0x1AB`) run at 97-100 Hz.
    The new-mailbox path cannot distinguish "the cave never fired" from "dropped downstream", so it
    cannot deliver the measurement -- twice now.

    ⚠ Non-DBC IDs ARE logged (`0x669`, `0x750`, `0x674` appear in that rlog and are in no Honda DBC),
    so "openpilot didn't know the ID" is NOT the explanation. The frames are not arriving.

    V54 abandons the new-mailbox channel for the measurement and uses the piggyback channel instead.

WHAT IS BEING MEASURED, AND WHY IT IS THE ONLY THING BLOCKING THE VIBRATION WORK
    `gp-0x6966` is the index into the LERP at `0xC6AF0`, which scales the OUTPUT BOUND of the
    `FUN_0003a382` residual lane -- the leading vibration suspect:
        X (authority):     0    3277    3604   19661   32768
        Y (Q15 gain) : 32768   32768       0       0       0
    Unity below 3277; CLAMPED TO ZERO above 3604. So authority does not scale the lane's signal, it
    decides whether the lane EXISTS. It has exactly ONE command-path reader image-wide (`0x3a632`).

    The `0xC6AF0` edit DIRECTION is unresolved and must not be guessed: the lead argued mute (Y=0) and
    then keep-live (Y=32768) from the same static data one turn apart, because both hinge on a runtime
    value. `docs/STATE.md` carries a standing block on editing `0xC6AF0` until this is measured.
      authority < 3277 during the vibration -> lane live at full bound   -> V55 = mute it
      authority > 3604 during the vibration -> lane already clamped to 0 -> hypothesis dies, keep-live
      authority CROSSING the knee with the bursts -> the crossing IS the trigger -> flatten the ramp
    V54 does not guess. It measures.

THE ENCODING -- 5 bits, chosen for the two knees, not for range, and BIASED BY +1
    wire = min((gp-0x6966 >> 7) + 1, 31)      (bucket size 128 counts; saturates at >= 3840)
        wire == 0     THE CAVE DID NOT FIRE -- see below. A live probe can never emit 0.
        wire 1..25    authority <= 3199    LERP gain 32768 -- lane at FULL bound
        wire == 26    3200..3327           straddles the 3277 knee
        wire 27-28    3328..3583           inside the ramp
        wire == 29    3584..3711           straddles the 3604 knee
        wire >= 30    authority >= 3712    LERP gain 0 -- lane MUTED
    Saturation is informative, not lossy: everything above 3840 is "definitely muted". A coarser shift
    cannot work -- the two knees are only 327 counts apart, so `>>11` (the widest that fits 5 bits
    unsaturated) puts BOTH in the same bucket.

    ★ WHY THE +1 BIAS -- this is the lesson of the last two drives, encoded into the wire format.
    Stock leaves byte4 bits 7:3 at ZERO (confirmed live: byte4 == 0x07 in 5,994/5,994 V53 frames).
    Without the bias, a cave that never fired would read as bucket 0, which decodes to "authority
    0..127, lane at FULL bound" -- a PLAUSIBLE, ACTIONABLE, AND WRONG answer that would have sent V55
    off to mute a lane on the strength of a dead probe. FOURFRAME and FOURFRAME2 both produced silent
    nulls; this build refuses to let silence masquerade as data. With the bias, wire == 0 is proof the
    probe did not run, and every value 1..31 is proof it did. Costs one instruction and one bucket of
    range at the top, where everything is muted anyway.

THE CHANNEL -- CAN 330 / 0x14A byte4 bits 7:3
    Chosen because it is the only channel proven to carry anything on this car:
    - It CROSSES. 5,994 frames at 97.3 Hz in the V53 rlog.
    - The hook already exists. `0x55c0e`, inside the 330 content builder, immediately BEFORE
      `FUN_00057b24` @`0x55c18` computes the Honda 4-bit counter/checksum -- so the checksum covers the
      telemetry automatically. This matters: opendbc verifies Honda checksums (`opendbc/can/dbc.py`), and
      a bad one drops `can_valid`, which is a DISENGAGE, not a cosmetic glitch.
    - FOUR successful flashes on exactly these bits: V31P/V49P/V50P/V51P. The byte4 read-mask-or-store
      sequence here is byte-identical to V31P's, which produced correct wire data on-car (routes 77/79).
    - openpilot reads NOTHING there. `STEERING_SENSORS` contributes only `STEER_ANGLE` and
      `STEER_ANGLE_RATE` (bytes 0-3); byte4 bits 2:0 are `STEER_SENSOR_STATUS_1/2/3`, which this cave
      PRESERVES via `andi 0x7`. `0x14A` is also absent from the panda Honda RX check list
      (`0x1A6`, `0x296`, `0x158`, `0x17C`, `0x326`, `0x1BE`), so no counter/quality gating either.
    - Live confirmation from the V53 rlog: byte4 == 0x07 in 5,994/5,994 frames, i.e. bits 7:3 are
      already zero on the wire -- the cave overwrites nothing.

    ⚠ Why NOT `0x18F` byte5, which looked free from the DBC alone: bits 5:4 are LIVE, written from
    `gp-0x6880 & 3` by the packer at `0x55CAE`-`0x55CC2` (2026-07-27 handoff §1). They read constant on
    route 13 and on the V53 route only because those bits happened not to change. `0x18F` also has no
    located pre-checksum hook site. Not used.

GATE 1 -- RAM OWNERSHIP  [the kit's mandatory cave gate]
    - The cave WRITES exactly one RAM byte: `gp-0x1514` (= 0xFEDF6AEC = the 330 TX buffer 0xFEDF6AE8 +4),
      read-modify-write preserving bits 2:0. Identical target, identical sequence, to V31P.
    - It ALLOCATES NO SCRATCH RAM AT ALL. V31P needed a flag byte at `gp-0x1500`; this build reads the
      signal directly at pack time, so the whole `gp-0x1500` question -- which CLAUDE.md records as
      having passed BOTH static clearance methods and still failed on-car -- does not arise.
    - It READS `gp-0x6966` (aligned `ld.hu`, atomic against the aligned 16-bit store at `0x432c8`) and
      `gp-0x1514`. `gp-0x6966` is shadow-protected against `gp-0x4c5a` with a mismatch handler adjacent
      to the motor-off path -- reading cannot perturb a shadow, only writing could, and we never write.
    - Registers: r6 and r7 only, a strict SUBSET of V31P's proven-dead r6/r7/r8 at this site. lp is
      clobbered by the `jarl`, exactly as V31P does at this same address.

GATE 2 -- CLOSED-LOOP STABILITY
    Vacuous by construction, and that is the point: the cave is REPORT-ONLY. Its single write lands in a
    CAN transmit payload byte that no control path reads, in either magnitude or phase, in any loop. No
    calibration, filter, pole, gain, clamp or authority value moves. `0xC6AF0` is asserted stock.
    Timing: ~13 instructions at 100 Hz against the DTC-0x18 per-task cadence watchdog -- roughly two
    orders of magnitude smaller than V52C's 1 kHz cave, which cost ~0.06% of its tick.

WHAT V54 IS NOT
    - NOT a vibration fix. Nothing that could damp or excite anything changes. This is the instrument.
    - NOT carrying the four-frame mailbox cave. `0x6A0`-`0x6A3` are gone; that channel is unobservable.
    - NOT carrying the V42 ratchet fix (`0x454FE` stays stock `0x65BA`), matching V38/V53. Asserted.
    - NOT a change to `0xC646C` (stays V38's 4x = 3564) or the `0xC61B2`/`0xC61B4` clamps.

⚠ LIMITS, STATED PLAINLY
    - Sampled at 100 Hz from the 330 builder, asynchronously to Monitor 1's write at `0x432c8`. A fast
      authority excursion can alias, so "never crossed the knee" is weaker evidence than "crossed it
      here". Authority derives from |gp-0x3570>>15| and behaves as an envelope, so this is acceptable.
    - Does NOT settle 21.09 vs 78.91 Hz. `0x14A` is also 100 Hz. That was never this build's job.
    - Steer-to-zero behaviour is unchanged from V53: below ~3 mph the EPS accepts LKAS torque where it
      used to refuse. Expect high static-friction effort at walking pace.

DECODE (rlog side) -- `rlog-tools/decode_v54_authority.py`
    wire = (byte4_of_0x14A >> 3) & 0x1F
    wire == 0 -> THE PROBE DID NOT FIRE, the drive is void, do not interpret it as low authority
    else authority ~ (wire-1)*128   (>= 3840 when wire == 31)

BUILT, UNFLASHED. Do NOT flash. Do NOT send CAN. Flash only on explicit operator instruction naming
the file and the bus.
=======================================================================================================
"""

import glob
import hashlib
import os
import struct
import sys
import zlib

if not __debug__:
    raise RuntimeError("V54 builder requires assertions; do not run with python -O")

from firmware_paths import REPO_ROOT, RWD_DIR, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# Encoders, CRC-chain gates and the V38 baseline constants come from the FOURFRAME2 builder verbatim.
# The lockout lever and its safety scans come from the V53 builder verbatim. Importing both means the
# only thing typed fresh in this file is the 40-byte cave itself.
import build_vfourframe_tva as FF
import build_v53_tva as V53

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from verify_bootloader_crc import walk, walk_all_blocks

from build_vfourframe_tva import GP, R0, R6, R7, _fmt1, _le16

START, END = FF.START, FF.END
V38_PLAIN, V38_RWD = FF.V38_PLAIN, FF.V38_RWD
V38_SHA256, V38_RWD_SHA256 = FF.V38_SHA256, FF.V38_RWD_SHA256
EXPECTED_HEADERS, V9B = FF.EXPECTED_HEADERS, FF.V9B

CAVE_BASE = FF.CAVE_BASE             # 0xC4B34 -- the same verified 0xFF run V31P/FOURFRAME used
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT
HOOK_ADDR = FF.HOOK_ADDR             # 0x55C0E -- 330 builder, immediately before the checksum call
HOOK_STOCK = FF.HOOK_STOCK           # movea -0x1518,gp,r6

MAIN_BLOCK = FF.MAIN_BLOCK           # (0x13000, 0xC4FFC) -- holds the cave and the hook
CAL_BLOCK = V53.CAL_BLOCK            # (0xC6000, 0xC6FFC) -- holds the lockout cal

# ---- the signal under measurement --------------------------------------------------------------------
AUTHORITY_DISP = 0x6966              # gp-0x6966, FUN_0003a382's LERP index; sole cmd-path reader 0x3a632
AUTHORITY_SHIFT = 7                  # 128 counts per bucket
AUTHORITY_BIAS = 1                   # +1 so a live probe can never emit 0; wire 0 == "cave did not fire"
AUTHORITY_MAX_BUCKET = 31            # 5 bits
PAYLOAD_BYTE4_DISP = 0x1514          # gp-0x1514 = 0xFEDF6AEC = CAN-330 buffer (0xFEDF6AE8) byte 4
PAYLOAD_KEEP_MASK = 0x07             # bits 2:0 = STEER_SENSOR_STATUS_1/2/3, live, must be preserved
CHECKSUM_FN = 0x55C18                # FUN_00057b24 call site -- runs AFTER the hook, covers our bits

# V31P's byte4 pack sequence, flashed four times and confirmed correct on the wire (routes 77/79).
# Reused as LITERALS, not re-derived -- these exact bytes are the proven part of this cave.
V31P_LDBU_BYTE4 = bytes.fromhex("8437edea")   # ld.bu -0x1514[gp],r6
V31P_ANDI_KEEP = bytes.fromhex("c6360700")    # andi 0x7,r6,r6
V31P_OR_R7_R6 = bytes.fromhex("0731")         # or r7,r6
V31P_STB_BYTE4 = bytes.fromhex("4437ecea")    # st.b r6,-0x1514[gp]
V31P_SHL3_R7 = bytes.fromhex("c33a")          # shl 0x3,r7

COND_BNH = 0x3                       # Bcond "not higher" = (CY or Z) = unsigned <=

TAG = ("LKAS-4x-V38base-minsteerspeed0-lockout0xC62EA-320to0"
       "-authority-gp0x6966-5bit-probe-can330-0x14A-byte4-bits7to3-100hz-caveC4B34")
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V54-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v54_plain_image.bin"))


# -------------------------------------------------------------------------------------------------------
# The three encoders FF does not carry. Each is checked below against a REAL code.bin instance.
# -------------------------------------------------------------------------------------------------------

def cmp_rr(reg1, reg2):
    """CMP reg1,reg2 (Format I, op 0x0F) -- computes reg2 - reg1, result discarded, flags set.
    Verified against the real `cmp lp,r10` @0x290D2 = ff51, recorded in build_v53_tva.py as the
    instruction that consumes the low-speed lockout cal."""
    return _fmt1(0x0F, reg1, reg2)


def shl(imm5, reg2):
    """SHL imm5,reg2 (Format II, op 0x16). Verified against V31P's flashed `shl 0x3,r7` = c33a."""
    assert 0 <= imm5 <= 31
    return _fmt1(0x16, imm5, reg2)


def bias_r7(imm16=1):
    """r7 += imm16, encoded as `movea imm16,r7,r7`.

    Deliberately NOT `add imm5,r7` (Format II op 0x12). That would introduce a NEW OPCODE VALUE whose
    only evidence would be the post-build re-disassembly -- a stronger claim than this kit accepts for
    a cave. `movea imm16,reg1,reg2` computes reg2 = reg1 + sign_extend(imm16); using reg1 = r7 instead
    of r0 changes only a REGISTER FIELD inside an encoder already verified against the real
    `movea 0x100,r0,r7` @0x1d7ee -- the same "only one field differs" precedent FOURFRAME used for
    bc-vs-bnc. The reg1 != 0 form is also live at the hook site itself: the displaced instruction is
    `movea -0x1518,gp,r6`. Costs 2 extra bytes against 1170 bytes of headroom."""
    return FF.movea(imm16, R7, R7)


def ldbu(disp_neg, reg2, reg1=GP):
    """LD.BU -disp_neg[reg1],reg2 (op 0x3C, `disp|1` selector like ld.hu).
    Verified against V31P's flashed `ld.bu -0x1514[gp],r6` = 8437edea."""
    assert 0 < disp_neg <= 0x8000
    return _fmt1(0x3C, reg1, reg2) + _le16(((0x10000 - disp_neg) & 0xFFFE) | 1)


def andi(imm16, reg1, reg2):
    """ANDI imm16,reg1,reg2 (Format VI, op 0x36) -- zero-extends, no sign trap.
    Verified against V31P's flashed `andi 0x7,r6,r6` = c6360700."""
    assert 0 <= imm16 <= 0xFFFF
    return _fmt1(0x36, reg1, reg2) + _le16(imm16)


def or_rr(reg1, reg2):
    """OR reg1,reg2 (Format I, op 0x08) -> reg2 |= reg1. Verified against V31P's `or r7,r6` = 0731."""
    return _fmt1(0x08, reg1, reg2)


def _self_check_encoders():
    """Every encoder used by this cave must reproduce a real instance or an FF self-checked encoder."""
    FF._self_check_encoders()          # ld.hu, shr, movea, Bcond, jarl_lp, JMP_LP, ...

    # NEW here -- each against a real, byte-verified instance.
    assert cmp_rr(31, 10).hex() == "ff51", \
        "cmp_rr fails the real `cmp lp,r10` @0x290D2 (V53's lockout consumer)"
    assert cmp_rr(31, 10) == V53.SPEED_CMP_BYTES, "cmp_rr disagrees with build_v53_tva.SPEED_CMP_BYTES"
    assert shl(0x3, R7) == V31P_SHL3_R7, "shl fails V31P's flashed `shl 0x3,r7`"
    assert ldbu(PAYLOAD_BYTE4_DISP, R6) == V31P_LDBU_BYTE4, "ldbu fails V31P's flashed byte4 read"
    assert andi(PAYLOAD_KEEP_MASK, R6, R6) == V31P_ANDI_KEEP, "andi fails V31P's flashed keep-mask"
    assert or_rr(R7, R6) == V31P_OR_R7_R6, "or_rr fails V31P's flashed `or r7,r6`"
    # The bias reuses movea's already-verified encoder with reg1=r7 instead of r0. Pin both forms so a
    # change to either is caught, and confirm the reg1!=0 form matches the real hook-site instruction.
    assert bias_r7(1).hex() == "273e0100", "movea 0x1,r7,r7 (the +1 bias) encoding changed"
    assert FF.movea(0xEAE8, GP, R6) == HOOK_STOCK, \
        "movea with reg1!=0 does not reproduce the real `movea -0x1518,gp,r6` at the hook site"
    assert FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP) == V31P_STB_BYTE4, \
        "FF.stb does not reproduce V31P's flashed byte4 store"

    # The authority read must be the SAME displacement halfword FOURFRAME2 verified for gp-0x6966
    # (its byte diff showed 0xC4D42: 2395 -> 9b96, i.e. disp halfword 0x969B).
    assert FF.ldhu(AUTHORITY_DISP, R7).hex() == "e43f9b96", \
        "ld.hu -0x6966[gp],r7 does not match FOURFRAME2's verified authority displacement"

    # movea with a 5-bit-unsafe immediate: 31 does NOT fit Format II's SIGNED imm5 (-16..15), so the
    # saturation constant must be movea, never movi5. Guard that mistake permanently.
    try:
        FF.movi5(AUTHORITY_MAX_BUCKET, R7)
    except AssertionError:
        pass
    else:
        raise AssertionError("movi5 accepted 31 -- Format II imm5 is SIGNED; saturation must use movea")
    assert FF.movea(0x1F, R0, R7).hex() == "203e1f00", "movea 0x1f,r0,r7 encoding changed"
    assert FF.movea(0x1F, R0, R6).hex() == "20361f00", "movea 0x1f,r0,r6 encoding changed"

    # Bcond: only the condition field differs from FF's verified bc/bnc, and the displacement (+6) is
    # the exact value FF cross-checks against the real `bc disp=+6` @0x2fc.
    assert FF.bcond(COND_BNH, +6).hex() == "b305", "bnh +6 encoding changed"
    assert FF.bcond(FF.COND_BC, +6).hex() == "b105", "Bcond formula drifted from its real instance"


# -------------------------------------------------------------------------------------------------------
# The cave
# -------------------------------------------------------------------------------------------------------

def build_cave():
    """pack_authority -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        ld.hu -0x6966[gp],r7     ; r7 = authority (u16, 0..32768)
        shr   0x7,r7             ; r7 = authority >> 7          (0..256)
        movea 0x1,r7,r7          ; +1 bias -- a live probe never emits 0 (movea, not a new opcode)
        movea 0x1f,r0,r6         ; r6 = 31 (saturation ceiling)
        cmp   r6,r7              ; r7 - 31
        bnh   +6                 ; unsigned r7 <= 31 -> keep it
        movea 0x1f,r0,r7         ; else saturate
      skip:
        shl   0x3,r7             ; bucket -> bits 7:3
        ld.bu -0x1514[gp],r6     ; 330 payload byte4
        andi  0x7,r6,r6          ; preserve live STEER_SENSOR_STATUS bits 2:0
        or    r7,r6
        st.b  r6,-0x1514[gp]
        movea -0x1518,gp,r6      ; re-execute the displaced instruction, LAST (r6 was scratch)
        jmp   [lp]
    """
    body = bytearray()
    listing = []

    def emit(raw, text):
        listing.append((CAVE_BASE + len(body), raw, text))
        body.extend(raw)

    emit(FF.ldhu(AUTHORITY_DISP, R7), f"ld.hu -0x{AUTHORITY_DISP:x}[gp],r7 ; r7 = AUTHORITY")
    emit(FF.shr(AUTHORITY_SHIFT, R7), f"shr 0x{AUTHORITY_SHIFT:x},r7        ; r7 = authority >> 7")
    emit(bias_r7(AUTHORITY_BIAS), "movea 0x1,r7,r7       ; +1 bias: a live probe never emits 0")
    emit(FF.movea(AUTHORITY_MAX_BUCKET, R0, R6), "movea 0x1f,r0,r6      ; r6 = 31 ceiling")
    emit(cmp_rr(R6, R7), "cmp r6,r7             ; r7 - 31")
    emit(FF.bcond(COND_BNH, +6), "bnh +6                ; r7 <= 31 (unsigned) -> skip saturate")
    emit(FF.movea(AUTHORITY_MAX_BUCKET, R0, R7), "movea 0x1f,r0,r7      ; saturate to 31")
    skip_target = CAVE_BASE + len(body)
    emit(shl(3, R7), "shl 0x3,r7            ; bucket -> bits 7:3")
    emit(ldbu(PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6  ; CAN-330 payload byte4")
    emit(andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6        ; keep live status bits 2:0")
    emit(or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]   ; write byte4 back")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6   ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]              ; -> 0x55C12")

    # The branch must land exactly on `shl`, not inside anything. Located by content, not by index,
    # so inserting an instruction can never silently desynchronise this check from the branch.
    bnh = [(a, r) for a, r, _ in listing if r == FF.bcond(COND_BNH, +6)]
    assert len(bnh) == 1, "expected exactly one bnh in the cave"
    assert bnh[0][0] + 6 == skip_target, \
        f"bnh target 0x{bnh[0][0] + 6:05X} != skip label 0x{skip_target:05X}"
    assert [a for a, r, _ in listing if r == shl(3, R7)] == [skip_target], \
        "the skip label is not the shl instruction"
    # Displaced instruction is re-executed LAST, after r6 is finished with as scratch.
    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    return bytes(body), listing


CAVE_BYTES, CAVE_LISTING = build_cave()


def wire_bucket(authority):
    """The exact value the cave puts on the wire, in Python. Used for the decode table + assertions.
    Mirrors the cave instruction-for-instruction: shr, +1, saturate at 31. Never returns 0, so a
    wire value of 0 means the cave did not run."""
    return min((authority >> AUTHORITY_SHIFT) + AUTHORITY_BIAS, AUTHORITY_MAX_BUCKET)


def lerp_gain(authority):
    """The 0xC6AF0 Q15 gain this authority selects (stock table), for the decode table."""
    xs = V53.AUTHORITY_LERP_STOCK[1:6]
    ys = V53.AUTHORITY_LERP_STOCK[6:11]
    if authority <= xs[0]:
        return ys[0]
    for i in range(len(xs) - 1):
        if xs[i] <= authority <= xs[i + 1]:
            span = xs[i + 1] - xs[i]
            return ys[i] + (ys[i + 1] - ys[i]) * (authority - xs[i]) // span
    return ys[-1]


# -------------------------------------------------------------------------------------------------------

def u16(code, address):
    return struct.unpack_from("<H", code, address)[0]


def assert_v38_baseline(code):
    assert len(code) == 0x100000, f"V38 image must be 1 MiB, got 0x{len(code):X}"
    assert hashlib.sha256(bytes(code)).hexdigest() == V38_SHA256, "baseline is not the V38 image"
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site is not the stock movea"
    assert bytes(code[CAVE_BASE:CAVE_HARD_LIMIT]) == b"\xff" * (CAVE_HARD_LIMIT - CAVE_BASE), \
        "cave region is not all 0xFF -- refusing to overwrite"
    assert CAVE_BASE + len(CAVE_BYTES) <= CAVE_HARD_LIMIT, "cave overruns its free region"
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_STOCK, "lockout cal is not at its stock value"
    assert bytes(code[V53.LOCKOUT_READER:V53.LOCKOUT_READER + 4]) == V53.LOCKOUT_READER_BYTES, \
        "the lockout's sole reader moved"
    assert bytes(code[V53.SPEED_CMP_ADDR:V53.SPEED_CMP_ADDR + 2]) == V53.SPEED_CMP_BYTES, \
        "the speed comparison moved"
    V53.assert_stock_cals(code, "V38 baseline")


def assert_payload_site(code):
    """The hook must sit where V31P proved it does: inside the 330 builder, before the checksum call."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == HOOK_STOCK, "hook site changed"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the counter/checksum computation"
    # The stock builder's own byte4 read must still be the instruction V31P anchored against.
    assert bytes(code[0x55AD4:0x55AD4 + 4]) == V31P_LDBU_BYTE4, \
        "stock 330 builder's byte4 access @0x55AD4 moved -- the payload offset is not confirmed"


def build():
    baseline = bytearray(open(V38_PLAIN, "rb").read())
    assert_v38_baseline(baseline)
    assert_payload_site(baseline)
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

    code = bytearray(baseline)

    # ---- CHANGE 1 (CODE): the authority probe cave + its hook -------------------------------------
    hook_bytes = FF.jarl_lp(CAVE_BASE, HOOK_ADDR)
    print(f"\n  CHANGE 1 (CODE) -- 5-bit AUTHORITY probe into CAN 330 / 0x14A byte4 bits 7:3:")
    print(f"    cave @0x{CAVE_BASE:05X}: {len(CAVE_BYTES)} bytes "
          f"(limit {CAVE_HARD_LIMIT - CAVE_BASE}, headroom {CAVE_HARD_LIMIT - CAVE_BASE - len(CAVE_BYTES)})")
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
    print(f"\n  CHANGE 2 (CAL, 1 halfword) -- minimum steer speed (carried over from V53):")
    struct.pack_into("<H", code, V53.LOCKOUT_ADDR, V53.LOCKOUT_NEW)
    print(f"    0x{V53.LOCKOUT_ADDR:05X}: {V53.LOCKOUT_STOCK} -> {V53.LOCKOUT_NEW}   "
          f"({V53.LOCKOUT_STOCK / 64.0625:.3f} km/h -> 0)")
    print(f"    HI bound 0xC62E8 = {u16(code, 0xC62E8)} UNTOUCHED -> the 0x7FFF SNA sentinel still fails")
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    V53.assert_stock_cals(code, "V54")

    # ---- the measurement this build exists for ----------------------------------------------------
    print(f"\n  WIRE ENCODING  wire = min((gp-0x{AUTHORITY_DISP:x} >> {AUTHORITY_SHIFT}) + "
          f"{AUTHORITY_BIAS}, {AUTHORITY_MAX_BUCKET})   ->  0x14A byte4 bits 7:3")
    print(f"    rlog decode:  wire = (byte4 >> 3) & 0x1F ;  wire == 0 means THE CAVE DID NOT FIRE")
    print(f"    {'authority':>10s}  {'wire':>5s}  {'0xC6AF0 Q15':>11s}   meaning")
    print(f"    {'(no probe)':>10s}  {0:5d}  {'--':>11s}   🛑 CAVE DID NOT FIRE -- drive is void")
    for auth in (0, 1024, 3199, 3277, 3300, 3450, 3603, 3604, 3711, 3840, 8192, 32768):
        b, g = wire_bucket(auth), lerp_gain(auth)
        meaning = ("lane at FULL bound" if g == 32768 else
                   "lane MUTED" if g == 0 else "inside the ramp")
        sat = " (saturated)" if b == AUTHORITY_MAX_BUCKET else ""
        print(f"    {auth:10d}  {b:5d}  {g:11d}   {meaning}{sat}")

    # The liveness guarantee -- the whole reason for the +1 bias.
    assert min(wire_bucket(a) for a in range(0, 0x8001)) >= 1, \
        "a live probe must NEVER emit 0 -- 0 is reserved for 'the cave did not fire'"
    # The two knees must each land in a bucket of their own, and below/above must be unambiguous.
    assert wire_bucket(3277) == 26 and wire_bucket(3604) == 29, "the two knees moved buckets"
    assert wire_bucket(3199) == 25, "the last full-bound authority must sit below the 3277 knee bucket"
    assert wire_bucket(3711) == 29, "3711 must share the 3604 knee bucket"
    assert wire_bucket(3840) == AUTHORITY_MAX_BUCKET, "saturation must begin at 3840"
    assert lerp_gain(3840) == 0, "the saturation floor must lie above the mute knee"
    assert wire_bucket(32768) == AUTHORITY_MAX_BUCKET, "encoding endpoint wrong"
    assert all(wire_bucket(a) << 3 <= 0xF8 for a in (0, 3277, 3604, 32768)), "bucket overflows bits 7:3"
    assert (wire_bucket(32768) << 3) & PAYLOAD_KEEP_MASK == 0, "bucket bleeds into the live status bits"
    # Every wire value must decode back to an authority range on the correct side of both knees.
    for auth in range(0, 0x8001, 7):
        w = wire_bucket(auth)
        if w < 26:
            assert lerp_gain(auth) == 32768, f"wire {w} must imply full bound (authority {auth})"
        if w > 29:
            assert lerp_gain(auth) == 0, f"wire {w} must imply a muted lane (authority {auth})"

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
    diffs, runs = FF.changed_runs(baseline, code)
    assert set(diffs) <= allowed, f"unexpected V54-vs-V38 bytes: {sorted(set(diffs) - allowed)}"
    assert bytes(code[START:HOOK_ADDR]) == bytes(baseline[START:HOOK_ADDR]), "code before hook moved"
    assert bytes(code[HOOK_ADDR + 4:CAVE_BASE]) == bytes(baseline[HOOK_ADDR + 4:CAVE_BASE]), \
        "code between hook and cave moved"
    assert bytes(code[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]) == \
        bytes(baseline[CAVE_BASE + len(CAVE_BYTES):MAIN_BLOCK[1]]), "code after cave moved"
    assert bytes(code[0xC5000:V53.LOCKOUT_ADDR]) == bytes(baseline[0xC5000:V53.LOCKOUT_ADDR]), \
        "cal/data before the lockout moved"
    assert bytes(code[V53.LOCKOUT_ADDR + 2:CAL_BLOCK[1]]) == \
        bytes(baseline[V53.LOCKOUT_ADDR + 2:CAL_BLOCK[1]]), "cal/data after the lockout moved"
    assert bytes(code[CAL_BLOCK[1] + 4:0x100000]) == bytes(baseline[CAL_BLOCK[1] + 4:0x100000]), \
        "data above the CAL block moved"

    # ---- V54 vs V53: the lockout must be identical, the cave must be entirely different -----------
    v53_img = bytearray(open(str(plain_image_path("_v53_plain_image.bin")), "rb").read())
    assert hashlib.sha256(bytes(v53_img)).hexdigest() == \
        "6be6055357506b87afe21ea622d46bda35ececfe5bb9038834e643d0f0292e1f", \
        "_v53_plain_image.bin is not the recorded V53 image"
    assert u16(v53_img, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW == u16(code, V53.LOCKOUT_ADDR), \
        "V54 must carry V53's steer-to-zero unchanged"
    assert struct.unpack_from("<11H", v53_img, V53.AUTHORITY_LERP_ADDR) == \
        struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR), "0xC6AF0 must match V53 (stock)"
    assert bytes(v53_img[CAVE_BASE:CAVE_BASE + 4]) != bytes(code[CAVE_BASE:CAVE_BASE + 4]), \
        "V54's cave should not be FOURFRAME2's"
    print(f"\n  V54-vs-V53: steer-to-zero identical, 0xC6AF0 identical (stock); the four-frame mailbox")
    print(f"    cave is REPLACED by the {len(CAVE_BYTES)}-byte authority probe on a channel that crosses.")

    # ---- CRC / bootloader gates -------------------------------------------------------------------
    FF.assert_crc_chain(code, "V54 plain")
    assert walk(bytes(code), label="V54") == 0
    assert walk_all_blocks(bytes(code), label="V54") == 0

    # ---- encode, decode the emitted RWD back, re-run every gate on the readback --------------------
    window = bytes(code[START:END])
    rwd = encode_x31(source_info["headers"], source_info["blocks"], [window.translate(encode)])
    FF.assert_x31_checksum(rwd, "V54 emitted")
    emitted = parse_x31(rwd)
    decoded = bytes(emitted["encs"][0]).translate(decode)
    assert decoded == window, "V54 RWD does not decode back to the built image"
    readback = FF.full_image(decoded)
    FF.assert_crc_chain(readback, "V54 RWD readback")
    assert walk(readback, label="V54 RWD readback") == 0
    assert walk_all_blocks(readback, label="V54 RWD readback") == 0
    assert bytes(readback[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, "cave lost in RWD"
    assert bytes(readback[HOOK_ADDR:HOOK_ADDR + 4]) == hook_bytes, "hook lost in RWD"
    assert u16(readback, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "lockout edit lost in RWD"
    assert u16(readback, 0xC646C) == 3564, "4x gain lost in RWD"
    V53.assert_stock_cals(readback, "V54 RWD readback")

    cave_span = range(CAVE_BASE, CAVE_BASE + len(CAVE_BYTES))
    print(f"\n  V54-vs-V38 exact lineage: {len(diffs)} changed bytes in {len(runs)} runs")
    for first, last in runs:
        kind = ("cave pack_authority" if first in cave_span else
                "hook movea->jarl" if first == HOOK_ADDR else
                "MAIN CRC trailer" if first == MAIN_BLOCK[1] else
                "CAL CRC trailer" if first == CAL_BLOCK[1] else
                "lockout 0xC62EA 320->0" if first == V53.LOCKOUT_ADDR else "UNEXPECTED")
        assert kind != "UNEXPECTED", f"unexplained run 0x{first:05X}-0x{last:05X}"
        print(f"    0x{first:05X}-0x{last:05X} ({last - first + 1}B)  {kind}")
    print(f"  V38 SHA-256:     {V38_SHA256}")
    print(f"  V54 SHA-256:     {hashlib.sha256(code).hexdigest()}")
    print(f"  V54 RWD SHA-256: {hashlib.sha256(rwd).hexdigest()}")
    return bytes(code), rwd


def main():
    stale = [p for p in glob.glob(os.path.join(RWD_DIR, "39990-TVA,A160-V54-*.rwd"))
             if os.path.abspath(p) != os.path.abspath(OUT)]
    for path in stale + [OUT, BIN_OUT, OUT + ".tmp", BIN_OUT + ".tmp"]:
        if os.path.exists(path):
            os.remove(path)
            print(f"  removed stale artifact {os.path.relpath(path, REPO)}")

    print("V54 = V38 + minimum steer speed 0 + a 5-bit gp-0x6966 AUTHORITY probe on CAN 330")
    print("  Change 1: 40-byte read-only cave -> 0x14A byte4 bits 7:3 @100 Hz (channel PROVEN to cross)")
    print("  Change 2: 0xC62EA 320 -> 0  (steer-to-zero, unchanged from V53)")
    print("  Report-only: no filter, pole, gain, clamp or authority value moves. 0xC6AF0 stays stock.")
    code, rwd = build()

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT + ".tmp", "wb") as h:
        h.write(rwd)
    with open(BIN_OUT + ".tmp", "wb") as h:
        h.write(code)
    os.replace(OUT + ".tmp", OUT)
    os.replace(BIN_OUT + ".tmp", BIN_OUT)
    print(f"\n  WROTE {os.path.relpath(OUT, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)}")
    print("\n  UNFLASHED. Do NOT flash. Do NOT send CAN. Flash only on explicit operator instruction")
    print("  naming the file + bus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
