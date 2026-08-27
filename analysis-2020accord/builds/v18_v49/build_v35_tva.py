"""builds/v18_v49/build_v35_tva.py - V35 = V34 + DISABLE the SECOND torque gate the whole lineage missed.

WHY V34 DID NOT FIX THE GENTLE EME (root cause, this session)
=========================================================================================================
V32/V33 disabled the engage-SM decider FUN_00040d58's torque gate (gp-0x6a62 >= cal 0xC6312, 320->65535).
V34 added 2 code NOPs disabling that decider's gp-0x6cc4 angle-consensus gate. The operator flashed V34;
the gentle EME (LKAS-only torque cut on a hard turn + bump) FREQUENCY DROPPED but it STILL occurred.

Backward-tracing the PHYSICAL cut (LKAS delivery gp-0x6b3c drops) instead of the STEER_STATUS byte led to the
miss. LKAS torque is committed each cycle by FUN_0003d04c (called as FUN_0003d04c(4,0) from the ENGAGED
stay-path in FUN_00041222 @0x412ae). The project already treats "this call's commit does not run -> LKAS not
delivered -> cut" as THE gentle-EME mechanism (that is exactly what the decider disengage does -- it skips the
call). FUN_0003d04c has SEVEN internal bail gates evaluated BEFORE it commits delivery; bailing any of them
jumps straight to the return and skips the commit = cut-equivalent to a decider disengage.

Gate 7 (0x3d0a8), byte-verified + adversarially re-derived (radare2 v850.gnu) this session:
    0x3d0a8  ld.hu 29438[r5],r14   ; r14 = cal tp+0x72FE = 0xC62FE  = 320 (0x0140)
    0x3d0ac  ld.hu -27230[gp],r16  ; r16 = gp-0x6a5e  (voter AVERAGE sensor-A column torque)
    0x3d0b0  cmp r16,r14
    0x3d0b2  bh 0x3d0b8            ; cal > gp-0x6a5e -> continue (deliver)
    0x3d0b4  jr 0x3d1e6            ; gp-0x6a5e >= cal -> BAIL (skip the delivery commit) = TORQUE CUT

This is the SAME threshold (320) as the decider's 0xC6312 that V33 disabled -- but on the SIBLING signal
gp-0x6a5e (voter AVERAGE) instead of gp-0x6a62 (voter MAX). Since MAX >= AVG, disabling only the MAX gate (V33)
leaves this AVG gate as the new binding torque cut -> a hard turn that pushes sensor-A torque past 320 still
bails FUN_0003d04c's commit = the residual gentle EME. AVG is smoother than MAX, so it trips on FEWER events
-> exactly the operator's "frequency reduced but still happens." This gate was NEVER touched by V32/V33/V34.

CLEAN-LEVER VERDICT for 0xC62FE (adversarial whole-image sweep, radare2 v850.gnu, this session)
=========================================================================================================
Exactly 1 reader (Gate 7 itself, 0x3d0a8), 0 writers, no int/float twin (320.0f absent image-wide), no
word-load overlap (the only neighbor read is 0xC62FC's own bytes at 0x3f9da, unrelated), no movea/absolute
build, no FUN_0006b9xx consistency monitor. This is CLEANER than 0xC6312 (which had 3 readers) -- the same
"safe cal-only" class V33 used, NOT the multi-role lockstep class (0xC6354) V34 rejected. So V35 mirrors V33's
proven-safe move (320 -> 65535 = u16 max; gp-0x6a5e is voter-clamped to 32000, so the gate can never bail).

RESIDUAL / STILL OPEN (named plainly -- the road/telemetry is the arbiter)
=========================================================================================================
1. Gate 5 (gp-0x4f68 >= cal 0xC61EA=4096) in the SAME function MAY be a rate/velocity signal (a better fit for
   the "+ bump" half of the symptom). Its identity (torque vs rate) is UNCONFIRMED, so it is deliberately NOT
   raised here -- fixing what is validated, not guessing. If the EME persists after V35, gate 5 (0xC61EA) is
   the next lever, pending its own identity + clean-lever check.
2. The retained gp-0x6a62==0xffff voter sentinel (a bump-coincident DMA-frame glitch can trip it) survives; it
   is a genuine dead-sensor fault path and is left intact.
3. The last hop from FUN_0003d04c's skipped commit to the delivered-torque zeroing is inferred (same residual
   as handoffs/2026-07/HANDOFF-2026-07-03-v34.md sec 4), consistent but not fully decompiled.
RECOMMENDED: a V31T-style CAN-0x660 telemetry piggyback of gp-0x6a5e (0xFEDF15A2) + gp-0x6a62 (0xFEDF159E) +
gp-0x4f68 confirms WHICH gate fires before flashing -- the hard evidence three prior builds lacked.

WHAT V35 CHANGES (one new cal edit vs V34; still cal + the 4 V34 NOP bytes)
=========================================================================================================
V35 = V34 (V31 gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN + V33 0xC6312=65535 +
2 angle-consensus NOPs) PLUS one cal: 0xC62FE 320 -> 65535 (Gate-7 deliver-commit torque gate OFF).
0xC62FE is in CRC block [0xC6000,0xC6FFC) -- same block as 0xC6312 -- so only that block CRC changes vs V34.

SAFETY TRADE (operator's call -- named plainly)
=========================================================================================================
With 0xC62FE=65535 the deliver-commit no longer skips LKAS delivery on high sensor-A (average) column torque.
Same class of trade as V33's 0xC6312: the driver can no longer force an LKAS letdown through this torque gate
(openpilot brake/cancel/override upstream of the EPS still works). Hard-EME (DTC) lockstep, the invalid-sensor
sentinel, and the angle-consensus monitor's OTHER roles are all UNAFFECTED.

SAFETY: STUDY ARTIFACT. No flash until the operator names file + bus (kit iron rule).
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
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR
BIN_OUT      = plain_image_path("_v35_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V33: gentle-EME decider torque disengage -> MAX u16 (fully disabled) =====================
GENTLE_EME_MAX = 0xFFFF  # 65535
GENTLE_EME_THRESHOLD = [
    (0xC6312, 320, GENTLE_EME_MAX, "GENTLE-EME decider disengage tp+0x7312  gp-0x6a62(MAX)>= cut  320->65535 (V33, MAX u16 = OFF)"),
]

# ===================== V35: DISABLE the deliver-commit torque gate (Gate 7 of FUN_0003d04c) =====================
# FUN_0003d04c gate 7 (0x3d0a8) bails (skips the LKAS delivery commit) when gp-0x6a5e (voter AVERAGE torque)
# >= cal 0xC62FE (320). Same threshold + same physical effect as the decider's 0xC6312, on the AVG twin -- the
# residual torque cut V32/V33/V34 all missed. Raise 320 -> 65535 (u16 max); gp-0x6a5e is voter-clamped to
# 32000 so the gate can never bail. Clean cal-only lever (1 reader / 0 writers / no twin -- see docstring).
GATE7_DELIVER_MAX = 0xFFFF  # 65535
GATE7_DELIVER_THRESHOLD = [
    (0xC62FE, 320, GATE7_DELIVER_MAX, "GATE-7 deliver-commit tp+0x72FE  gp-0x6a5e(AVG)>= bail  320->65535 (V35, AVG twin of 0xC6312)"),
]

# ===================== V34: DISABLE the gp-0x6cc4 angle-consensus disengage (2 code NOPs, retained) ===========
NOP = b"\x00\x00"  # v850 nop (0x0000), verified side-effect-free
CODE_NOP_PATCHES = [
    (0x40DE2, b"\xc2\x1d", NOP, "ENGAGED be 0x40e1a (FUN_000406ae()==0 -> state4) -> nop (stay engaged)"),
    (0x40E12, b"\xcb\x05", NOP, "HOLDING bh 0x40e1a (|gp-0x6cc4|>cal0xC6354 -> state4) -> nop (stay engaged)"),
]
DECIDER_LO, DECIDER_HI = 0x40D58, 0x40E6C
NOP_BYTE_ADDRS = {0x40DE2, 0x40DE3, 0x40E12, 0x40E13}

# ===================== V31 CALIBRATION EDITS (ALL RETAINED, UNCHANGED) =====================
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  CORRIDOR_INT, "INT dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+4096 (x4)"),
    (0xC6750,  1024,  CORRIDOR_INT, "INT dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+4096 (x4)"),
    (0xC675A, -1024, -CORRIDOR_INT, "INT dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-4096 (x4)"),
    (0xC675C, -1024, -CORRIDOR_INT, "INT dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-4096 (x4)"),
]
CORRIDOR_GUARD = [
    (0xC6748,     2, "INT TABLE1 N (count)"),
    (0xC674A, -8192, "INT TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "INT TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "INT TABLE2 N (count)"),
    (0xC6756,  1024, "INT TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "INT TABLE2 X[1] velocity bkpt"),
]
FLOAT_CORRIDOR_PATCHES = [
    (0xC6598,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[0] tp+0x7598  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC659C,  1.0,  CORRIDOR_FLT, "FLOAT dir1 Y[1] tp+0x759c  corridor mirror  +1.0->+4.0 (x4)"),
    (0xC65AC, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[0] tp+0x75ac  corridor mirror  -1.0->-4.0 (x4)"),
    (0xC65B0, -1.0, -CORRIDOR_FLT, "FLOAT dir2 Y[1] tp+0x75b0  corridor mirror  -1.0->-4.0 (x4)"),
]
FLOAT_CORRIDOR_GUARD_I = [
    (0xC658C, 2, "FLOAT dir1 N (count, int32)"),
    (0xC65A0, 2, "FLOAT dir2 N (count, int32)"),
]
FLOAT_CORRIDOR_GUARD_F = [
    (0xC6590, -8.0, "FLOAT dir1 X[0]"),
    (0xC6594, -1.0, "FLOAT dir1 X[1]"),
    (0xC65A4,  1.0, "FLOAT dir2 X[0]"),
    (0xC65A8,  8.0, "FLOAT dir2 X[1]"),
]
INT_BOOST_FLOOR_PATCHES = [
    (0xC6768,    0, BOOST_INT, "INT boost Y[0] tp+0x7768  rate<=700  0->4096   (FLOOR)"),
    (0xC676A, 1536, BOOST_INT, "INT boost Y[1] tp+0x776a             1536->4096 (FLOOR)"),
    (0xC676C, 2048, BOOST_INT, "INT boost Y[2] tp+0x776c             2048->4096 (FLOOR)"),
]
FLOAT_BOOST_FLOOR_PATCHES = [
    (0xC65C4, 0.0, BOOST_FLT, "FLOAT boost Y[0] tp+0x75c4  mirror  0.0->4.0 (FLOOR)"),
    (0xC65C8, 1.5, BOOST_FLT, "FLOAT boost Y[1] tp+0x75c8  mirror  1.5->4.0 (FLOOR)"),
    (0xC65CC, 2.0, BOOST_FLT, "FLOAT boost Y[2] tp+0x75cc  mirror  2.0->4.0 (FLOOR)"),
]
INT_BOOST_GUARD = [
    (0xC6760,    3, "INT boost N (count)"),
    (0xC6762,  700, "INT boost X[0] tp+0x7762"),
    (0xC6764,  800, "INT boost X[1] tp+0x7764"),
    (0xC6766, 1100, "INT boost X[2] tp+0x7766"),
]
FLOAT_BOOST_GUARD_I = [
    (0xC65B4, 3, "FLOAT boost N (count, int32)"),
]
FLOAT_BOOST_GUARD_F = [
    (0xC65B8,  700.0, "FLOAT boost X[0]"),
    (0xC65BC,  800.0, "FLOAT boost X[1]"),
    (0xC65C0, 1100.0, "FLOAT boost X[2]"),
]
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]
FLOAT_SPEEDGAIN_GUARD_F = [
    (0xC65F0,   2.0, "SPEED-gain float Y[0] -- stock"),
    (0xC65F8,   0.5, "SPEED-gain float Y[2] -- stock"),
]
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# --- NO-CODE-EDIT guard: V35's two cal edits (0xC6312, 0xC62FE) are data-only; the code that READS them and
#     the other guarded sites MUST remain byte-identical to stock ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x561C2, b"\x44\x07\xf0\xea", "0x660 packer byte0 zero-store -- stock (V35 is NOT the telemetry build)"),
    # engage-SM decider stays stock EXCEPT the 4 V34 NOP bytes: the cal-read instructions are untouched.
    (0x40dd0, b"\xe5\x87\x13\x73", "engage-SM param2 ld.hu 0x7312[r5],r16 -- stock (reads cal 0xC6312 we edit)"),
    (0x40db8, b"\xe5\x3f\x13\x73", "engage-SM param1 ld.hu 0x7312[r5],r7  -- stock"),
    (0x40df4, b"\xe5\x3f\x13\x73", "engage-SM param3 ld.hu 0x7312[r5],r7  -- stock"),
    # deliver-commit Gate 7 (FUN_0003d04c): the cal-read + signal-read instructions are untouched (only the
    # cal VALUE at 0xC62FE changes). Guards prove V35 edits data, not the gate code.
    (0x3d0a8, b"\xe5\x77\xff\x72", "GATE-7 ld.hu 29438[r5],r14  -- stock (reads cal 0xC62FE we edit)"),
    (0x3d0ac, b"\xe4\x87\xa3\x95", "GATE-7 ld.hu -27230[gp],r16 -- stock (reads gp-0x6a5e)"),
]
CAVE_GUARD = (0xC4E00, 0x18)


def patch_cal_u(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_corridor(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<h", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_float(code, table):
    for addr, cur, new, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur} got {got} ({note})")
        struct.pack_into("<f", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6.1f} -> {new:6.1f}   {note}")


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def patch_code(code, table):
    for addr, cur, new, note in table:
        got = bytes(code[addr:addr + len(cur)])
        if got != cur:
            raise AssertionError(f"CODE 0x{addr:05X}: expected {cur.hex()} got {got.hex()} ({note})")
        assert len(new) == len(cur), "code patch must be size-preserving"
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}:   {cur.hex()} -> {new.hex()}   {note}")


def guard_decider_stock_except_nops(code, code_stock):
    """FUN_00040d58 must equal stock everywhere except the 4 NOP'd bytes."""
    diffs = [a for a in range(DECIDER_LO, DECIDER_HI) if code[a] != code_stock[a]]
    unexpected = [a for a in diffs if a not in NOP_BYTE_ADDRS]
    if unexpected:
        raise AssertionError(f"decider changed at unexpected offsets: {[hex(a) for a in unexpected]}")
    missing = [a for a in NOP_BYTE_ADDRS if code[a] != 0x00]
    if missing:
        raise AssertionError(f"NOP bytes not applied at: {[hex(a) for a in missing]}")


def guard_s16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_int32(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<i", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_float(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_no_code_edit(code, table):
    for addr, expect_bytes, note in table:
        got = bytes(code[addr:addr + len(expect_bytes)])
        if got != expect_bytes:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect_bytes.hex()} got {got.hex()} ({note})")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA,A160"]))
        elif tag == b"!":
            new.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new.append((tag, [CAN_SIG_BYTE]))
        else:
            new.append((tag, list(vals)))
    return new


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def recompute_crc(code, start, crc_off):
    old = struct.unpack_from("<I", code, crc_off)[0]
    new = zlib.crc32(code[start:crc_off]) & 0xFFFFFFFF
    struct.pack_into("<I", code, crc_off, new)
    print(f"  CRC [0x{start:X},0x{crc_off:X}) @0x{crc_off:X}: 0x{old:08X} -> 0x{new:08X}")


TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),   # covers 0xC62FE (V35 Gate-7) AND 0xC6312 (V33) AND all V31 cals
    (0x13000, 0xC4FFC),   # covers the PN bytes AND the 4 V34 decider NOP bytes
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V34 + Gate-7 deliver-commit torque gate 0xC62FE 320->65535 (the residual twin of 0xC6312)")
    code = bytearray(code_stock)

    # pre-patch guards
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF before patch"

    # patches
    patch_cal_u(code, GENTLE_EME_THRESHOLD)    # V33: decider 0xC6312 320 -> 65535 (kept)
    patch_cal_u(code, GATE7_DELIVER_THRESHOLD) # V35: deliver-commit 0xC62FE 320 -> 65535 (NEW)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    patch_code(code, CODE_NOP_PATCHES)         # V34: NOP the 2 gp-0x6cc4 angle-consensus disengage branches (kept)

    # post-patch guards (untouched arms still stock)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    guard_decider_stock_except_nops(code, code_stock)   # decider stock except the 4 V34 NOP'd bytes
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave tail must remain 0xFF"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # readback asserts (decode the emitted .rwd from scratch)
    assert struct.unpack_from("<H", ecu_plain, 0xC6312 - START)[0] == GENTLE_EME_MAX, "V33 decider threshold (max) lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC62FE - START)[0] == GATE7_DELIVER_MAX, "V35 Gate-7 deliver threshold (max) lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == 1782, "GAIN lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B4 - START)[0] == 1024, "CLAMP b4 lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B2 - START)[0] == 1024, "CLAMP b2 lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for addr, _, new, _ in CORRIDOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int corridor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float corridor @0x{addr:X}"
    for addr, _, new, _ in INT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == new, f"int boost floor @0x{addr:X}"
    for addr, _, new, _ in FLOAT_BOOST_FLOOR_PATCHES:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == new, f"float boost floor @0x{addr:X}"
    for addr, expect, note in CORRIDOR_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int corridor GUARD @0x{addr:X} ({note})"
    for addr, expect, note in INT_BOOST_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int boost GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_I:
        assert struct.unpack_from("<i", ecu_plain, addr - START)[0] == expect, f"float boost N GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_BOOST_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"float boost X GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_SPEEDGAIN_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"speed-gain stock GUARD @0x{addr:X} ({note})"
    for addr, expect_bytes, note in NO_CODE_EDIT_SITES:
        got = bytes(ecu_plain[addr - START:addr - START + len(expect_bytes)])
        assert got == expect_bytes, f"unexpected code edit @0x{addr:X} ({note})"
    for addr, cur, new, note in CODE_NOP_PATCHES:   # the 2 V34 NOPs survive the encode/decode round-trip
        got = bytes(ecu_plain[addr - START:addr - START + len(new)])
        assert got == new, f"NOP not present in emitted rwd @0x{addr:X} ({note})"
    ep_diffs = [a for a in range(DECIDER_LO, DECIDER_HI)
                if ecu_plain[a - START] != code_stock[a] and a not in NOP_BYTE_ADDRS]
    assert not ep_diffs, f"decider changed at unexpected offsets in emitted rwd: {[hex(a) for a in ep_diffs]}"
    assert bytes(ecu_plain[0xC4E00 - START:0xC4E18 - START]) == b"\xff" * 0x18, "cave region must be 0xFF (no caves)"
    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    assert ecu_plain.count(pn_old) == 0 and ecu_plain.count(pn_new) == 2, "PN lost"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b - a + 1}B)")

    # V35-vs-V34 delta must be EXACTLY the 2-byte 0xC62FE threshold + the recomputed 0xC6000-block CRC (4B).
    v34_bin = plain_image_path("_v34_plain_image.bin")
    if os.path.exists(v34_bin):
        v34 = open(v34_bin, "rb").read()
        v35_img = full_image(ecu_plain)
        d = [i for i in range(START, END) if v35_img[i] != v34[i]]
        print(f"  V35-vs-V34 delta: {len(d)} bytes at {[hex(x) for x in d]}")
        expect = {0xC62FE, 0xC62FF, 0xC6FFC, 0xC6FFD, 0xC6FFE, 0xC6FFF}
        if set(d) != expect:
            print(f"  *** WARNING: V35-vs-V34 delta != {{0xC62FE/FF + 0xC6FFC block-CRC}} -- got {[hex(x) for x in d]}")
    else:
        print("  (skipping V35-vs-V34 delta check: _v34_plain_image.bin not present)")

    if not matches or fails:
        print(f"  *** {label} self-check FAILED -- not writing ***\n")
        return None

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    with open(BIN_OUT, "wb") as f:
        f.write(full_image(ecu_plain))
    print(f"  WROTE {os.path.relpath(out, REPO)}")
    print(f"  WROTE {os.path.relpath(BIN_OUT, REPO)} (1MB plain image for Ghidra verify)\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print("V35 = V34 (V31 gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN")
    print("      + V33 decider torque disengage 0xC6312 320->65535 + 2 angle-consensus NOPs)")
    print("      + NEW: deliver-commit Gate-7 torque gate 0xC62FE 320->65535 (gp-0x6a5e AVG twin of 0xC6312)")
    print("      (invalid-sensor sentinel gp-0x6a62==0xffff LEFT INTACT; gate 5 0xC61EA NOT touched -- unconfirmed)\n")
    build("V35", code, headers, tag="LKAS-2x-corridor4x-boostfloor4096-gentleEME-OFF-thresh65535-angleGateNOP-deliverGate7-65535-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
