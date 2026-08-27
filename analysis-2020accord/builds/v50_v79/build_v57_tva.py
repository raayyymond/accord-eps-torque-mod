#!/usr/bin/env python3
"""builds/v50_v79/build_v57_tva.py -- V57 = V55 + the 0xC646C DECOUPLING + the DEADBAND-GATE PROBE.

Two independent changes, deliberately orthogonal:

  (A) THE DECOUPLING -- 6 bytes, the 4x gain hits the LKAS forward path ONLY
      0x2A1F0  ld.h displacement  0x746C -> 0x7CD0   (tp+0x7CD0 = 0xC6CD0)   [MAIN]
      0xC6CD0  new private forward-path gain word   0xFFFF -> 3564          [CAL]
      0xC646C  the SHARED sensor scale               3564  -> 891 (stock)    [CAL]

  (B) THE PROBE -- V55's cave payload REPLACED, same base, same hook, same length
      0x14A byte4 bit7 = 1                    LIVENESS
                   bit6 = (gp-0x6806 == 0)    the deadband gate is ENABLED
                   bit5 = (gp-0x69b0 != 0)    ramp gain is LIVE
                   bit4 = (gp-0x6b30 == 0)    gate output is EXACTLY ZERO
                   bit3 = (gp-0x6b30 <  0)    gate output SIGN
                   bits 2:0 stock STEER_SENSOR_STATUS, preserved

⚠ (A) and (B) do not confound each other. The decoupling moves only the FEEDBACK readers
(0x2B656/0x2C488/0x36686/0x3684A); the probe reads the FORWARD path (gp-0x6806, gp-0x69b0,
gp-0x6b30), which V57 leaves at 3564. The probe therefore measures a baseline the decoupling
does not disturb.

=======================================================================================================
(A) WHY THE DECOUPLING -- and an honest statement of what it does NOT do
=======================================================================================================
`0xC646C` was raised for LKAS authority in TWO steps -- 891 (stock/V9) -> 1782 (V22-V37) -> 3564
(V38+), byte-verified across the plain-image archive, with the clamps 0xC61B2/0xC61B4 tracking each
step (512 -> 1024 -> 2048). ⚠ BUILD-LINEAGE recorded this as a single "891->3564 at V22"; that is
wrong. Note what did NOT track either doubling: the pre-gain deadband 0xC61B8, still 102.

It is NOT an LKAS gain. It is the
firmware's single shared Q15 sensor-to-command-domain scale with SIX readers, re-enumerated from scratch
2026-07-29 by independent Python byte scan (both V850E2 encodings, plus an LE32 absolute-pointer scan)
and corroborated instruction-by-instruction in Ghidra -- exactly 6, zero discrepancy:

    0x2A1EE  ld.h   FUN_00028ea6   FORWARD -- the CAN LKAS setpoint path. 4x is INTENDED here.
    0x2A904  --     (none)         DEAD -- not disassembled at all; sits above FUN_00028ea6's end
                                   0x2a30d, inside the known-dead FUN_0002a30e / FUN_0002a93a copies.
    0x2B656  ld.hu  FUN_0002b62c   FEEDBACK (assist-shaping task)
    0x2C488  ld.hu  FUN_0002c478   FEEDBACK (1 kHz task) -- (gp-0x4f60_RAW * GAIN) >> 15
    0x36686  ld.hu  FUN_00036682   FEEDBACK -- and its RETURN VALUE is an aggregator summand
    0x3684A  ld.hu  FUN_00036828   FEEDBACK -- modulates FUN_00036682's hysteresis dead-band WIDTH

*** THIS IS A CORRECTNESS FIX. IT IS NOT EXPECTED TO FIX THE 20-25 Hz GRINDING. ***
FUN_00036682 is y[n] = y[n-1]*(1-2a) + a*K*x[n], a = 6/1024 (0xC63D2, byte-read 06 00)
=> |H(21 Hz)| = -46.3 dB at 3564, -58.3 dB at 891. Total loop-gain change across all four feedback
readers at 22 Hz is <= 0.28 dB against a MEASURED sensor->command transfer of 0.221. Independent
confirmation from the lane side: of the ELEVEN aggregator summands, exactly ONE reads 0xC646C, and it
is the most deeply attenuated lane in the table.

=======================================================================================================
(B) WHY THE PROBE -- closing a hole in this kit's own elimination
=======================================================================================================
The deadband + sign relay in FUN_00028ea6 (0x2a1ae-0x2a206) was ELIMINATED on 2026-07-29 by measuring
`STEER_CONTROL_ACTIVE` (CAN 0x18F byte4 bit3), which the TX packer sources from gp-0x6806:

    0x55c76  ld.bu -0x6806,gp,r15      0x55c7e  andi 0x1,r15,r15
    0x55c82  shl   0x3,r15             0x55c86  st.b r10,-0x141c,gp

Route 24 measured gp-0x6806's BIT 0 == 1 in 96.26% of frames, with TWO transitions in 180 s.

*** THE HOLE: `andi 0x1` transmits PARITY, and the gate tests EXACT EQUALITY. ***
The live gate condition, byte-verified at 0x2a1ba/0x2a1bc, is `cmp r0,r12 ; bne` -- i.e. the block runs
only when gp-0x6806 is EXACTLY 0. Four of its eight live writers store a REGISTER (r6/r14/r11/r6), not
a literal, so a value of 2 would read as bit0 = 0 while the gate is DISABLED -- and, symmetrically, a
0<->2 toggle at 22 Hz would be wholly invisible: bit3 flat at 0, zero transitions. Low probability, but
it is not closed, and it rests on an argument rather than a measurement.

Bit 6 of this probe is the exact `gp-0x6806 == 0` test and closes that hole outright.
Bits 4 and 3 give a 3-state view of the gate's OUTPUT {negative, zero, positive}: a chattering relay
visits zero between sign flips, so bit4's spectrum carries a 20-25 Hz line if the mechanism is real.
Bit 5 disambiguates "zero because the ramp gain is zero" from "zero because the gate fired".

READ IT AS: if bit6 is 0 across engaged hands-off frames, the gate is inert and the thread is CLOSED by
measurement rather than by parity argument. If bit6 is 1 in any meaningful fraction, or bit4 shows a
20-25 Hz line, the elimination was premature and the deadband returns to scope.

⚠ Operator-stated expectation, recorded so a null is not re-litigated: the lead's prior is that this
comes back NEGATIVE. The build exists to close the thread properly, not because the outcome is doubted.

=======================================================================================================
GATES
=======================================================================================================
GATE 1 (RAM ownership):
  (A) VACUOUS -- two instruction bytes (a displacement field; same opcode, same registers, still EVEN so
      still decodes ld.h not ld.w) and two calibration words. 0xC6CD0 verified free by fresh full-image
      scan: zero disp16 loads, zero stores, zero 6-byte extended-disp hits, zero LE32 pointer hits;
      0xFF from 0xC6CA4 through 0xC6FEF, with the preceding 4-point LERP at 0xC6C90 ending cleanly at
      0xC6CA4 and non-FF footer bytes not resuming until 0xC6FF0.
  (B) INHERITED and NOT WIDENED -- same cave base 0xC4B34, same hook 0x55C0E, and the payload is
      READ-ONLY: it loads three gp-relative variables, writes ONLY the CAN TX buffer byte the stock code
      writes anyway (gp-0x1514), and allocates no scratch RAM. Registers touched are r6/r7, both already
      scratch at the hook site (r6 is the displaced movea's own destination). The cave region has now
      carried four flashed builds (V54, V55, V56, and V53's predecessor).
  🛑 It is still CODE in the 1 kHz TX path, not a cal edit. This is a higher risk class than a
     cal-only build, and it should be described that way.

GATE 2 (closed-loop stability):
  (A) no float mirror -- a fresh scan for ANY 32-bit tp-relative access in [0x7440,0x74A0) returned ZERO
      hits, so this cannot repeat the V27 mirror-desync brick. Forward authority is unchanged by
      construction (still 3564, new address). All four feedback readers move TOWARD factory 891.
      ✅ MANUAL FEEL: NO CHANGE EXPECTED -- and this is on-car evidence, not an argument. The gain
      went 891 (stock/V9) -> 1782 (V22-V37) -> 3564 (V38+), byte-verified across the image archive,
      with 0xC61B2/0xC61B4 tracking each step (512 -> 1024 -> 2048). The operator has driven all
      THREE values and reports no change in manual steering feel. When disengaged the FORWARD reader
      (0x2A1EE, the CAN setpoint path) is idle, so manual feel depends ONLY on readers #3-#6 -- the
      exact set V57 reverts. That experiment has therefore already been run, in both directions,
      with a null result. (An earlier draft of this file claimed feel WOULD change; that was an
      inference from "not engagement-gated", which establishes the readers are LIVE, not AUDIBLE.
      Withdrawn on the operator's three-point A/B.)
  (B) VACUOUS -- report-only into a TX payload byte no control path reads. No filter, pole, gain, clamp,
      damper or authority value moves.

*** Flash only on explicit operator instruction naming the file and the bus.
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
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_vfourframe_tva as FF
import build_v53_tva as V53
import build_v54_tva as V54
import build_v55_tva as V55

from encode_eps import build_decode_table, encode_x31, invert_table, parse_x31
from firmware_paths import plain_image_path, RWD_DIR
from verify_bootloader_crc import walk, walk_all_blocks
from build_vfourframe_tva import GP, R0, R6, R7

START, END = FF.START, FF.END
CAL_BLOCK = V53.CAL_BLOCK
MAIN_BLOCK = FF.MAIN_BLOCK

CAVE_BASE = FF.CAVE_BASE                       # 0xC4B34
CAVE_HARD_LIMIT = FF.CAVE_HARD_LIMIT           # 0xC4FF0
HOOK_ADDR = FF.HOOK_ADDR                       # 0x55C0E
HOOK_STOCK = FF.HOOK_STOCK                     # movea -0x1518,gp,r6
PAYLOAD_BYTE4_DISP = V54.PAYLOAD_BYTE4_DISP    # gp-0x1514 = CAN-330 buffer byte 4
PAYLOAD_KEEP_MASK = V54.PAYLOAD_KEEP_MASK      # 0x07
CHECKSUM_FN = V54.CHECKSUM_FN                  # 0x55C18

# ---- (A) the decoupling ---------------------------------------------------------------------------
GAIN_ADDR, GAIN_4X, GAIN_STOCK = 0xC646C, 3564, 891
PRIVATE_ADDR, PRIVATE_FREE = 0xC6CD0, 0xFFFF
LOAD_ADDR = 0x2A1EE                            # ld.h 0x746c, tp, r7
DISP_OFF = LOAD_ADDR + 2
DISP_OLD, DISP_NEW = 0x746C, 0x7CD0
INSN_HW1 = 0x3F25                              # opcode/register halfword -- MUST NOT move
TP = 0xBF000

# ---- (B) the probe --------------------------------------------------------------------------------
GATE_FLAG_DISP = 0x6806     # gp-0x6806, BYTE. Gate runs iff == 0 (cmp r0,r12 ; bne @0x2a1ba/0x2a1bc)
RAMP_DISP = 0x69b0          # gp-0x69b0, signed halfword -- the LKAS forward ramp gain
OUT_DISP = 0x6b30           # gp-0x6b30, signed halfword -- the gate's own output (st.h @0x2a206)

BIT_LIVE, BIT_GATE, BIT_RAMP, BIT_ZERO, BIT_SIGN = 0x80, 0x40, 0x20, 0x10, 0x08

COND_BE = 0x2               # Z == 1
COND_BNE = 0xA              # Z == 0
COND_BGE = V55.COND_BGE     # 0xE, signed >=

TAG = "LKAS-4x-mss0-decouple0xC646C-deadbandprobe-can330byte4"
OUT = os.path.join(RWD_DIR, f"39990-TVA,A160-V57-{TAG}-0x{START:X}-0x{END:X}.rwd")
BIN_OUT = str(plain_image_path("_v57_plain_image.bin"))
V55_BIN = str(plain_image_path("_v55_plain_image.bin"))


def u16(buf, a):
    return struct.unpack_from("<H", buf, a)[0]


# =======================================================================================================
# Encoders -- every one is a register-or-condition-field change from a byte-confirmed real instruction.
# No novel opcode VALUE is introduced. (The V54 lesson.)
# =======================================================================================================

def _self_check_encoders():
    V55._self_check_encoders()          # ldh, sar, ldbu_any, cmp_imm5 + everything V54/FF self-check

    # cmp r0,rX -- pinned to the real `cmp r0,r6` @0x2a23a and `cmp r0,r12` @0x2a1ba (the GATE's own test)
    assert V54.cmp_rr(R0, R6).hex() == "e031", "cmp r0,r6 fails the real instance @0x2a23a"
    assert V54.cmp_rr(R0, 12).hex() == "e061", "cmp r0,r12 fails the real instance @0x2a1ba"

    # Branch conditions. bne +6 is pinned EXACTLY to the real `bne 0x2a246` @0x2a240.
    assert FF.bcond(COND_BNE, +6).hex() == "ba05", "bne +6 fails the real instance @0x2a240"
    # be: cond field 0x2 confirmed against real `be` at two other displacements
    # (`be 0x296f8` @0x296f0 = +8 -> c205; `be 0x2a2b2` @0x2a2ae = +4 -> a205).
    assert FF.bcond(COND_BE, +8).hex() == "c205", "be +8 fails the real instance @0x296f0"
    assert FF.bcond(COND_BE, +4).hex() == "a205", "be +4 fails the real instance @0x2a2ae"
    assert FF.bcond(COND_BE, +6).hex() == "b205", "be +6 encoding drifted"
    assert FF.bcond(COND_BGE, +6).hex() == "be05", "bge +6 drifted from V55"
    # bge cond field cross-checked against the real `bge 0x2a222` @0x2a21a = +8.
    assert FF.bcond(COND_BGE, +8).hex() == "ce05", "bge +8 fails the real instance @0x2a21a"

    # The three bit-set moveas are the same reg1=r7 form V54 flashed as its +1 bias.
    for bit in (BIT_GATE, BIT_RAMP, BIT_ZERO, BIT_SIGN):
        raw = FF.movea(bit, R7, R7)
        assert len(raw) == 4 and raw[:2] == bytes.fromhex("273e"), f"movea 0x{bit:x},r7,r7 malformed"
    # movea 0x80,r0,r7 : hw1 = (reg2<<11)|(0x31<<5)|reg1 = (7<<11)|0x620|0 = 0x3E20 -> LE "203e"
    assert FF.movea(BIT_LIVE, R0, R7).hex() == "203e8000", "movea 0x80,r0,r7 encoding changed"
    assert FF.movea(BIT_LIVE, R0, R7)[:2] != FF.movea(BIT_LIVE, R7, R7)[:2], \
        "reg1=r0 and reg1=r7 forms must differ -- otherwise r7 would be ADDED to itself, not loaded"
    assert FF.movea(BIT_GATE, R7, R7).hex() == "273e4000", "movea 0x40,r7,r7 encoding changed"


# =======================================================================================================
# The cave -- read-only, 5 exact single-comparison tests, no arithmetic on any signal
# =======================================================================================================

def build_cave():
    """pack_deadband_state -- entered by `jarl` from 0x55C0E, returns via `jmp [lp]` to 0x55C12.

        movea 0x80,r0,r7       ; r7 = 0x80            bit7 LIVENESS
        ld.bu -0x6806[gp],r6   ; the gate enable flag
        cmp   r0,r6
        bne   +6               ; != 0 -> gate DISABLED, leave bit6 clear
        movea 0x40,r7,r7       ; bit6 = gate ENABLED (EXACT equality, not parity)
      gate_done:
        ld.h  -0x69b0[gp],r6   ; LKAS forward ramp gain
        cmp   r0,r6
        be    +6               ; == 0 -> ramp dead, leave bit5 clear
        movea 0x20,r7,r7       ; bit5 = ramp LIVE
      ramp_done:
        ld.h  -0x6b30[gp],r6   ; the gate's own output
        cmp   r0,r6
        bne   +6               ; != 0 -> leave bit4 clear
        movea 0x10,r7,r7       ; bit4 = output EXACTLY ZERO
      zero_done:
        cmp   r0,r6            ; r6 still holds gp-0x6b30 (movea wrote r7 only)
        bge   +6               ; >= 0 -> leave bit3 clear
        movea 0x8,r7,r7        ; bit3 = output NEGATIVE
      sign_done:
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

    emit(V55.ldbu_any(-GATE_FLAG_DISP, R6), f"ld.bu -0x{GATE_FLAG_DISP:x}[gp],r6 ; gate enable flag")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> gate DISABLED")
    emit(FF.movea(BIT_GATE, R7, R7), "movea 0x40,r7,r7    ; bit6 = gate ENABLED")
    gate_done = CAVE_BASE + len(body)

    emit(V55.ldh(RAMP_DISP, R6), f"ld.h -0x{RAMP_DISP:x}[gp],r6  ; ramp gain")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BE, +6), "be +6               ; == 0 -> ramp dead")
    emit(FF.movea(BIT_RAMP, R7, R7), "movea 0x20,r7,r7    ; bit5 = ramp LIVE")
    ramp_done = CAVE_BASE + len(body)

    emit(V55.ldh(OUT_DISP, R6), f"ld.h -0x{OUT_DISP:x}[gp],r6  ; gate output")
    emit(V54.cmp_rr(R0, R6), "cmp r0,r6")
    emit(FF.bcond(COND_BNE, +6), "bne +6              ; != 0 -> not zero")
    emit(FF.movea(BIT_ZERO, R7, R7), "movea 0x10,r7,r7    ; bit4 = output ZERO")
    zero_done = CAVE_BASE + len(body)

    emit(V54.cmp_rr(R0, R6), "cmp r0,r6           ; r6 still = gp-0x6b30")
    emit(FF.bcond(COND_BGE, +6), "bge +6              ; >= 0 -> not negative")
    emit(FF.movea(BIT_SIGN, R7, R7), "movea 0x8,r7,r7     ; bit3 = output NEGATIVE")
    sign_done = CAVE_BASE + len(body)

    emit(V55.ldbu_any(-PAYLOAD_BYTE4_DISP, R6), "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4")
    emit(V54.andi(PAYLOAD_KEEP_MASK, R6, R6), "andi 0x7,r6,r6      ; keep live status bits 2:0")
    emit(V54.or_rr(R7, R6), "or r7,r6")
    emit(FF.stb(R6, -PAYLOAD_BYTE4_DISP, GP), "st.b r6,-0x1514[gp]")
    emit(HOOK_STOCK, "movea -0x1518,gp,r6 ; re-exec displaced instruction")
    emit(FF.JMP_LP, "jmp [lp]            ; -> 0x55C12")

    # Every branch must land exactly on its label. Located BY POSITION in the listing (not by content),
    # because unlike V55 this cave reuses the SAME branch encoding twice (bne +6), so a
    # content-based lookup would be ambiguous.
    branch_targets = [(3, gate_done, "bne->gate_done"),
                      (7, ramp_done, "be->ramp_done"),
                      (11, zero_done, "bne->zero_done"),
                      (14, sign_done, "bge->sign_done")]
    for idx, label, name in branch_targets:
        addr, raw, _ = listing[idx]
        assert len(raw) == 2 and raw[1] == 0x05, f"{name}: listing[{idx}] is not a +6 Bcond"
        assert addr + 6 == label, f"{name} target 0x{addr + 6:05X} != label 0x{label:05X}"

    assert listing[-2][1] == HOOK_STOCK, "displaced movea must be the penultimate instruction"
    assert body.count(HOOK_STOCK) == 1, "displaced movea appears more than once"
    assert len(body) % 2 == 0, "cave length must be halfword-aligned"
    assert CAVE_BASE + len(body) <= CAVE_HARD_LIMIT, "cave overruns the hard limit"
    return bytes(body), listing


_self_check_encoders()
CAVE_BYTES, CAVE_LISTING = build_cave()


def decode_field(byte4):
    """Decode 0x14A byte4 into the probe's five bits. field == 0 => THE CAVE DID NOT FIRE."""
    field = (byte4 >> 3) & 0x1F
    if field == 0:
        return None
    return {
        "live": bool(byte4 & BIT_LIVE),
        "gate_enabled": bool(byte4 & BIT_GATE),
        "ramp_live": bool(byte4 & BIT_RAMP),
        "out_zero": bool(byte4 & BIT_ZERO),
        "out_negative": bool(byte4 & BIT_SIGN),
    }


def assert_probe_sites(code, label="V57"):
    """The hook and the cave, checked on whatever image is passed (pre-write, post-write, readback)."""
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == FF.jarl_lp(CAVE_BASE, HOOK_ADDR), \
        f"{label}: hook at 0x{HOOK_ADDR:05X} is not our jarl"
    assert bytes(code[CAVE_BASE:CAVE_BASE + len(CAVE_BYTES)]) == CAVE_BYTES, \
        f"{label}: cave bytes do not match"
    assert HOOK_ADDR < CHECKSUM_FN, "hook must precede the checksum computation"
    # Nothing of V55's payload may survive past our jmp -- stale instructions there are unreachable,
    # but leaving them would make a future re-disassembly ambiguous about which build is present.
    tail = bytes(code[CAVE_BASE + len(CAVE_BYTES):CAVE_BASE + len(V55.CAVE_BYTES)])
    assert set(tail) <= {0xFF}, f"{label}: V55 cave remnants survive past our payload"


def assert_decoupled(code, label):
    """V53's shared guard, minus the gain word V57 deliberately moves."""
    for address, (value, note) in V53.STOCK_CALS.items():
        if address == GAIN_ADDR:
            continue
        got = u16(code, address)
        assert got == value, f"{label}: 0x{address:05X} is {got}, expected {value} ({note})"
    assert u16(code, V53.RATCHET_ADDR) == V53.RATCHET_STOCK_HW, \
        f"{label}: 0x{V53.RATCHET_ADDR:05X} is not the stock bne -- V57 is cut from V38 like V55"


def build():
    if not os.path.exists(V55_BIN):
        print(f"  {V55_BIN} missing -- running the V55 builder first\n")
        V55.build()
    v55 = bytearray(open(V55_BIN, "rb").read())
    print(f"  V55 source {V55_BIN}\n    SHA256 {hashlib.sha256(bytes(v55)).hexdigest()}")

    # ---- gate the SOURCE before touching it ------------------------------------------------------
    FF.assert_crc_chain(v55, "V55 source")
    assert walk(bytes(v55), label="V55 source") == 0
    assert walk_all_blocks(bytes(v55), label="V55 source") == 0
    V55.assert_probe_sites(v55, hook_is_stock=False)      # V55's OWN cave must be intact first
    V55.assert_variant_tables(v55)
    assert u16(v55, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW, "V55 source lost the lockout edit"
    V53.assert_stock_cals(v55, "V55 source")

    baseline = bytearray(open(FF.V38_PLAIN, "rb").read())
    V55.V54.assert_v38_baseline(baseline)

    code = bytearray(v55)

    # ---- pre-flight ------------------------------------------------------------------------------
    assert u16(code, GAIN_ADDR) == GAIN_4X, f"0x{GAIN_ADDR:05X} is not the 4x value"
    assert u16(code, PRIVATE_ADDR) == PRIVATE_FREE, f"0x{PRIVATE_ADDR:05X} is not free"
    assert u16(code, LOAD_ADDR) == INSN_HW1, f"0x{LOAD_ADDR:05X} hw1 unexpected"
    assert u16(code, DISP_OFF) == DISP_OLD, f"0x{DISP_OFF:05X} disp unexpected"
    assert TP + DISP_OLD == GAIN_ADDR and TP + DISP_NEW == PRIVATE_ADDR
    assert DISP_NEW % 2 == 0, "disp must stay EVEN or the opcode decodes as ld.w"
    for a in range(PRIVATE_ADDR - 0x10, PRIVATE_ADDR + 0x10, 2):
        assert u16(code, a) == 0xFFFF, f"0x{a:05X} is not 0xFFFF -- 0xC6CD0's neighbourhood is not free"
    assert len(CAVE_BYTES) <= len(V55.CAVE_BYTES), \
        f"V57 cave ({len(CAVE_BYTES)}B) exceeds V55's proven extent ({len(V55.CAVE_BYTES)}B)"

    # ---- (A) THE DECOUPLING ----------------------------------------------------------------------
    print("\n  (A) THE DECOUPLING -- give the LKAS forward path its own gain word:")
    struct.pack_into("<H", code, DISP_OFF, DISP_NEW)
    print(f"    0x{DISP_OFF:05X}  ld.h displacement  0x{DISP_OLD:04X} -> 0x{u16(code, DISP_OFF):04X}"
          f"   (tp+0x{DISP_NEW:04X} = 0x{PRIVATE_ADDR:05X})   [MAIN]")
    struct.pack_into("<H", code, PRIVATE_ADDR, GAIN_4X)
    print(f"    0x{PRIVATE_ADDR:05X}  private LKAS gain  0xFFFF -> {u16(code, PRIVATE_ADDR)}   [CAL]")
    struct.pack_into("<H", code, GAIN_ADDR, GAIN_STOCK)
    print(f"    0x{GAIN_ADDR:05X}  shared sensor scale  {GAIN_4X} -> {u16(code, GAIN_ADDR)} (stock)"
          f"   [CAL]")
    assert u16(code, LOAD_ADDR) == INSN_HW1, "the opcode/register halfword moved"
    assert u16(code, TP + u16(code, DISP_OFF)) == GAIN_4X, \
        "the retargeted load does not resolve to 3564 -- LKAS authority would change"

    # ---- (B) THE PROBE ---------------------------------------------------------------------------
    print(f"\n  (B) THE PROBE -- replace V55's cave payload at 0x{CAVE_BASE:05X} "
          f"({len(CAVE_BYTES)} bytes, V55 was {len(V55.CAVE_BYTES)}):")
    for addr, raw, text in CAVE_LISTING:
        print(f"    0x{addr:05X}  {raw.hex():<12s} {text}")
    code[CAVE_BASE:CAVE_BASE + len(V55.CAVE_BYTES)] = \
        CAVE_BYTES + b"\xff" * (len(V55.CAVE_BYTES) - len(CAVE_BYTES))
    assert bytes(code[HOOK_ADDR:HOOK_ADDR + 4]) == bytes(v55[HOOK_ADDR:HOOK_ADDR + 4]), \
        "the hook must be byte-identical to V55's -- same cave base, same jarl"
    assert_probe_sites(code, "V57")

    # ---- everything V55 established must still hold ------------------------------------------------
    assert_decoupled(code, "V57")
    V55.assert_variant_tables(code)
    assert u16(code, V53.LOCKOUT_ADDR) == V53.LOCKOUT_NEW
    assert u16(code, 0xC62E8) == 12800, "HI bound disturbed"
    assert struct.unpack_from("<11H", code, V53.AUTHORITY_LERP_ADDR) == \
        tuple(V53.AUTHORITY_LERP_STOCK), "0xC6AF0 must stay STOCK -- V56's mute is falsified"
    for a, name in ((0xC6450, "Stage-A pole"), (0xC644A, "Stage-C pole"), (0xC63D2, "FUN_36682 EMA"),
                    (0xC6372, "boost input EMA"), (0xC636E, "damping input EMA"),
                    (0xC61B8, "pre-gain deadband"), (0xC61B2, "fwd clamp"), (0xC61B4, "fwd clamp"),
                    (0xC6440, "r24"), (0xC6442, "r24"), (0xC6446, "r24"), (0xC61F6, "r24 deadzone"),
                    (0xC643E, "r26")):
        assert u16(code, a) == u16(v55, a), f"{name} 0x{a:05X} moved -- V57 changes ONE lever only"
    assert code[0xC64A3] == v55[0xC64A3] == 1, \
        "the deadband ENABLE byte must stay stock -- the probe MEASURES this block, it must not alter it"
    for a in (0xD27C6, 0xD27DA, 0xD2802, 0xD2804, 0xD2806, 0xD2816, 0xD2818, 0xD281A,
              0xD200C, 0xD2000):
        assert u16(code, a) == u16(baseline, a), f"damper/rate cal 0x{a:05X} moved"

    # ---- CRC -------------------------------------------------------------------------------------
    assert V53.owning_block(code, PRIVATE_ADDR) == CAL_BLOCK
    assert V53.owning_block(code, GAIN_ADDR) == CAL_BLOCK
    assert V53.owning_block(code, DISP_OFF) == MAIN_BLOCK
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
    d55 = [i for i in range(0x13000, 0x100000) if code[i] != v55[i]]
    permitted = ({DISP_OFF, DISP_OFF + 1, PRIVATE_ADDR, PRIVATE_ADDR + 1, GAIN_ADDR, GAIN_ADDR + 1}
                 | set(range(CAVE_BASE, CAVE_BASE + len(V55.CAVE_BYTES)))
                 | set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4))
                 | set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)))
    stray = [i for i in d55 if i not in permitted]
    assert not stray, f"V57 vs V55 touches bytes outside the edit + cave + CRCs: {[hex(x) for x in stray]}"
    for lo, name in ((DISP_OFF, "displacement"), (PRIVATE_ADDR, "private gain"),
                     (GAIN_ADDR, "shared gain")):
        assert any(i in d55 for i in (lo, lo + 1)), f"{name} did not actually change"
    assert set(range(CAL_BLOCK[1], CAL_BLOCK[1] + 4)) <= set(d55), "CAL CRC trailer did not move"
    assert set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4)) <= set(d55), "MAIN CRC trailer did not move"
    print(f"\n  V57 vs V55: {len(d55)} bytes")

    d38 = [i for i in range(0x13000, 0x100000) if code[i] != baseline[i]]
    print(f"  V57 vs V38: {len(d38)} bytes changed in [0x13000,0x100000)")
    runs = []
    for i in d38:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        print(f"    0x{a:05X}-0x{b:05X}  ({b - a + 1} bytes)")

    # ---- post-write gates ------------------------------------------------------------------------
    FF.assert_crc_chain(code, "V57")
    assert walk(bytes(code), label="V57") == 0
    assert walk_all_blocks(bytes(code), label="V57") == 0
    assert_probe_sites(code, "V57")
    V55.assert_variant_tables(code)

    open(BIN_OUT, "wb").write(bytes(code))
    print(f"\n  wrote {BIN_OUT}\n    SHA256 {hashlib.sha256(bytes(code)).hexdigest()}")

    # ---- encode + decode-back, re-running every gate on the readback -------------------------------
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
    FF.assert_x31_checksum(rwd, "V57 output")
    back = parse_x31(rwd)
    assert back["headers"] == FF.EXPECTED_HEADERS
    assert back["blocks"] == [{"start": START, "length": END - START}]
    readback = bytearray(baseline)
    readback[START:END] = bytes(back["encs"][0]).translate(decode)
    assert bytes(readback[START:END]) == bytes(code[START:END]), "RWD does not decode back to the image"
    FF.assert_crc_chain(readback, "V57 readback")
    assert walk(bytes(readback), label="V57 readback") == 0
    assert walk_all_blocks(bytes(readback), label="V57 readback") == 0
    assert_probe_sites(readback, "V57 readback")
    V55.assert_variant_tables(readback)
    assert u16(readback, DISP_OFF) == DISP_NEW and u16(readback, LOAD_ADDR) == INSN_HW1
    assert u16(readback, PRIVATE_ADDR) == GAIN_4X and u16(readback, GAIN_ADDR) == GAIN_STOCK
    assert u16(readback, TP + u16(readback, DISP_OFF)) == GAIN_4X
    assert readback[0xC64A3] == 1, "readback: the deadband enable byte moved"

    print(f"  wrote {OUT}\n    SHA256 {hashlib.sha256(rwd).hexdigest()}")

    print("\n  PROBE: 0x14A byte4  bit7=LIVENESS  bit6=(gp-0x6806==0, gate ENABLED)")
    print("                      bit5=(gp-0x69b0!=0, ramp live)  bit4=(gp-0x6b30==0)")
    print("                      bit3=(gp-0x6b30<0)   bits2:0 = stock STEER_SENSOR_STATUS")
    print("         field==0 (bits 7:3 all clear) means THE CAVE DID NOT FIRE -- a VOID reading.")
    print("  GATE 1: (A) vacuous; (B) inherited -- same cave base/hook/extent, read-only, no new RAM.")
    print("          *** still CODE in the 1 kHz TX path, a higher risk class than a cal-only build.")
    print("  GATE 2: (A) no float mirror; forward authority unchanged; feedback readers -> stock 891.")
    print("          manual feel: NO change expected -- the operator has driven 891/1782/3564 and")
    print("          reports no difference; when disengaged only readers #3-#6 are live. (B) vacuous.")
    print("\n  *** Flash only on explicit operator instruction naming the file and the bus.")


if __name__ == "__main__":
    build()
