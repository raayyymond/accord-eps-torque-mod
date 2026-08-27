"""builds/v18_v49/build_v34_tva.py - V34 = V33 + DISABLE the GENTLE-EME angle-consensus disengage (2 code NOPs).

WHY V33 DID NOT FIX THE GENTLE EME (root cause, this session)
=========================================================================================================
V33 raised cal 0xC6312 (320->65535) to disable the sensor-A torque-MAGNITUDE disengage in FUN_00040d58.
The operator flashed it; the gentle EME (LKAS-only cut, STEER_STATUS=no_torque_alert_2, no DTC, on a hard
curve + bump) STILL occurred. Verified by radare2 v850.gnu THIS session: the ENGAGED/HOLDING branches of the
engage-SM decider FUN_00040d58 have a SECOND, independent disengage that V33 never touched:

    ENGAGED (param 2):  after the gp-0x6a62 checks ->  jarl FUN_000406ae ; cmp r0,r10 ; be 0x40e1a
                        FUN_000406ae() == 0  ->  r12 = 4  (leave the delivering state)
    HOLDING (param 3):  after the gp-0x6a62 checks ->  ld.w gp-0x6cc4 ; ABS ; cmp cal 0xC6354(=4825) ; bh 0x40e1a
                        |gp-0x6cc4| > 4825   ->  r12 = 4  (leave the delivering state)

FUN_000406ae is a 4-history-array CONSENSUS monitor: return 0 ("not confirmed") when the current gp-0x6cc4
deviates from its recent consensus by >= cal 0xC6354 (4825), OR when history is insufficient. gp-0x6cc4
(= 0xFEDF133C) is an ANGLE/POSITION-domain tracking ACCUMULATOR (three writers, all with mod-2048/4096
wrap-correction idioms; angles wrap, torque does not). A road bump on a curve mechanically jolts steering
angle -> gp-0x6cc4 spikes past the 4825 consensus band for one cycle (NO debounce) -> decider returns state 4
-> LKAS leaves the delivering state and re-arms = the gentle EME. The prior "torque-only" characterization
missed this because it stopped at the first (gp-0x6a62) gate and never walked the branch bodies to 0x40e1a.

WHY NOT JUST RAISE cal 0xC6354 (the clean-looking cal lever)  --  REJECTED AS UNSAFE
=========================================================================================================
Whole-image scan (this session): 0xC6354 has 14 readers across 5 roles -- not only the two disengage gates
but also a +/-window gate and a scale factor INSIDE the pipeline that computes gp-0x6cc4 itself, plus a mode
selector. gp-0x6cc4 is lockstep-shadowed (gp-0x4D0C, FUN_0006b9fa fault check). Raising 0xC6354 would perturb
the tracking pipeline and could DESYNC the shadow -> a HARD EME (DTC) -- the V25-V27 fault class. So we do NOT
touch the cal. Instead we make the DECIDER ignore the consensus result with two surgical code NOPs.

WHAT V34 CHANGES (the new fix -- 2 code edits, in-place, no trampoline)
=========================================================================================================
    0x40DE2:  be 0x40e1a  (c2 1d)  -> nop (00 00)   ENGAGED: ignore FUN_000406ae()==0 -> stay engaged
    0x40E12:  bh 0x40e1a  (cb 05)  -> nop (00 00)   HOLDING: ignore |gp-0x6cc4|>4825 -> stay engaged
Each 2-byte conditional branch is replaced by a v850 `nop` (0x0000, confirmed side-effect-free). After the
NOP the code falls through to the existing "stay" path (`ld.bu -0x35b6[gp],r12 ; br 0x40e68`, r12=substate=0).
The `jarl FUN_000406ae` CALL is LEFT IN PLACE, so FUN_000406ae's own side effect (st.w r12,-0x35ac[gp] at
0x40862) still happens exactly as stock -- only the decider's REACTION to the result is nulled. cal 0xC6354 is
NOT touched, so its other 4 roles and the gp-0x6cc4 pipeline/shadow are untouched (no hard-fault risk).

V34 ALSO KEEPS V33's 0xC6312 -> 65535 (operator-directed: belt-and-suspenders -- kills the torque-magnitude
return-2 path too). So on V34 the ENGAGED/HOLDING decider cannot leave the delivering state on EITHER
gp-0x6a62 magnitude OR gp-0x6cc4 angle-consensus. The gp-0x6a62 == 0xffff invalid-sensor sentinel is STILL
left intact (a genuine dead-torque-sensor fault path).

SAFETY TRADE (operator's call -- named plainly)
=========================================================================================================
1. From V33: with 0xC6312=65535 the driver can no longer wrest LKAS authority through the sensor-A torque
   gate (openpilot brake/cancel/override upstream of EPS still works).
2. NEW in V34: the gp-0x6cc4 angle/position PLAUSIBILITY monitor no longer drops LKAS. That monitor also
   catches a genuine steering-angle-tracking discontinuity; disabling its LKAS-cut means LKAS stays engaged
   through such an event. The HARD-EME (DTC) lockstep and the invalid-sensor sentinel are UNAFFECTED.
RESIDUAL: if the real trigger were instead the voter gp-0x6a62==0xffff frame-glitch sentinel (Tracer A,
lower-probability), V34 would NOT fix it -- that path is deliberately retained. Confirm on the road.

CODE-EDIT SAFETY (this is NOT a cal-only build -- the decider is no longer byte-identical to stock)
=========================================================================================================
Exactly 4 code bytes change (two 2-byte branches -> nop), both inside FUN_00040d58, both in CRC block
[0x13000,0xC4FFC) (CRC @0xC4FFC, recomputed). The rest of the decider is guarded byte-identical to stock.
No trampoline, no cave use. ALL V31 EDITS RETAINED: GAIN 1782, clamps 1024, ramp 0x1B, corridor x4 int+float,
boost floor 4096 int+float, PN. Plus V33's 0xC6312=65535.

SAFETY: STUDY ARTIFACT. No flash until the operator names file + bus (kit iron rule).
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
BIN_OUT      = plain_image_path("_v34_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V33: gentle-EME disengage threshold -> MAX u16 (fully disabled) =====================
# ld.hu (unsigned 16-bit) + unsigned compare -> datatype max = 0xFFFF = 65535. gp-0x6a62 is voter-clamped
# to 32000, so 65535 makes `gp-0x6a62 < threshold` unconditionally true -> torque-magnitude disengage OFF.
GENTLE_EME_MAX = 0xFFFF  # 65535
GENTLE_EME_THRESHOLD = [
    (0xC6312, 320, GENTLE_EME_MAX, "GENTLE-EME disengage tp+0x7312  gp-0x6a62>= cut  320->65535 (V33, MAX u16 = OFF)"),
]

# ===================== V34: DISABLE the gp-0x6cc4 angle-consensus disengage (2 code NOPs) =====================
# In FUN_00040d58 the ENGAGED (param 2) and HOLDING (param 3) branches leave the delivering state (r12=4) when
# the gp-0x6cc4 angle/position consensus fails. We null the two conditional branches to 0x40e1a (mov 4,r12) so
# each falls through to the "stay engaged" path. The jarl FUN_000406ae CALL is retained (its st.w -0x35ac[gp]
# side effect still runs as stock); only the decider's reaction to the result is removed. cal 0xC6354 untouched.
NOP = b"\x00\x00"  # v850 nop (0x0000), verified side-effect-free
CODE_NOP_PATCHES = [
    (0x40DE2, b"\xc2\x1d", NOP, "ENGAGED be 0x40e1a (FUN_000406ae()==0 -> state4) -> nop (stay engaged)"),
    (0x40E12, b"\xcb\x05", NOP, "HOLDING bh 0x40e1a (|gp-0x6cc4|>cal0xC6354 -> state4) -> nop (stay engaged)"),
]
# The decider function spans [DECIDER_LO, DECIDER_HI); after patching it must equal stock EVERYWHERE except the
# 4 NOP'd bytes -- proves we changed only the two branches and nothing else in the engage SM.
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

# --- NO-CODE-EDIT guard: V33 is cal-only; these stock code sites MUST remain byte-identical ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x561C2, b"\x44\x07\xf0\xea", "0x660 packer byte0 zero-store -- stock (V33 is NOT the V31T telemetry build)"),
    # engage-SM decider stays stock (cal-only edit): the disengage-decider instructions are untouched.
    (0x40dd0, b"\xe5\x87\x13\x73", "engage-SM param2 ld.hu 0x7312[r5],r16 -- stock (reads the cal we edit)"),
    (0x40db8, b"\xe5\x3f\x13\x73", "engage-SM param1 ld.hu 0x7312[r5],r7  -- stock"),
    (0x40df4, b"\xe5\x3f\x13\x73", "engage-SM param3 ld.hu 0x7312[r5],r7  -- stock"),
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
    (0xC6000, 0xC6FFC),   # covers the gentle-EME threshold (0xC6312) AND all V31 cals
    (0x13000, 0xC4FFC),   # covers the PN bytes
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V33 (0xC6312=65535) + 2 code NOPs disabling the gp-0x6cc4 angle-consensus disengage")
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
    patch_cal_u(code, GENTLE_EME_THRESHOLD)    # V33: 0xC6312 320 -> 65535 (kept)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    patch_code(code, CODE_NOP_PATCHES)         # V34: NOP the 2 gp-0x6cc4 angle-consensus disengage branches

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
    guard_decider_stock_except_nops(code, code_stock)   # V34: decider stock except the 4 NOP'd bytes
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
    assert struct.unpack_from("<H", ecu_plain, 0xC6312 - START)[0] == GENTLE_EME_MAX, "GENTLE-EME threshold (max) lost"
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
    for addr, cur, new, note in CODE_NOP_PATCHES:   # V34: the 2 NOPs survive the encode/decode round-trip
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
    print("V34 = V31 (gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN)")
    print("      + V33 GENTLE-EME torque-magnitude disengage 0xC6312 320 -> 65535 (kept)")
    print("      + 2 code NOPs @0x40de2/0x40e12 disabling the gp-0x6cc4 angle-consensus disengage (state 4)")
    print("      (invalid-sensor sentinel gp-0x6a62==0xffff LEFT INTACT; cal 0xC6354 NOT touched)\n")
    build("V34", code, headers, tag="LKAS-2x-corridor4x-boostfloor4096-gentleEME-OFF-thresh65535-angleGateNOP-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
