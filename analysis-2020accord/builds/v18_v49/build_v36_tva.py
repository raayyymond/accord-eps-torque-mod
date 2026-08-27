"""builds/v18_v49/build_v36_tva.py - V36 = V31 (UNCHANGED) + DISABLE the gentle-EME DEBOUNCE STATE MACHINE
                       (torque channel gp-0x682f AND angle-rate channel param_1 both raised to unsigned max).

WHAT V36 CHANGES (operator-directed 2026-07-14)
=========================================================================================================
Root cause localized this session (rlog telemetry + Ghidra, self-verified): the gentle EME
(STEER_STATUS=no_torque_alert_2, felt as a sharp slight wheel-straightening mid-turn) is produced by a
DEBOUNCE STATE MACHINE, NOT by the engage-SM decider torque-MAX gate (0xC6312, which fires as benign
~10 Hz background and was shown NOT to correlate with the cut -> V33's 320->65535 was chasing the wrong
gate; V36 leaves 0xC6312 at stock 320).

The debounce FSM lives in TWO functions that BOTH read the SAME calibration thresholds and BOTH drive the
STEER_STATUS byte gp-0x6807:
    FUN_0002a30e            (0x2a30e, the status producer; rise 0x2a420.., hold 0x2a49a..)
    m_steer_torque_arbitration (0x29xxx inline twin; rise 0x2923e.., hold 0x292b8..)
A signed counter gp-0x6757 starts at -cal(0xC64E2)=-5 and only advances while a qualifying condition holds;
STEER_STATUS=4 fires only after 5 consecutive qualifying cycles. The qualifying condition (byte-verified in
Ghidra, both functions, rise + hold branches) is:

    gp-0x682f > cal[0xC64B4/B5]           (TORQUE channel:  gp-0x682f = min(|arb signal|>>5, 255))
      OR  param_1 > cal[0xC61C0]          (RATE channel:    param_1 = angular-rate magnitude, thr 1600)
      OR (param_2 && ((gp-0x682f>cal[0xC64B7] && param_1>cal[0xC61C2])         [secondary AND terms]
                   ||  (gp-0x682f>cal[0xC64B6] && param_1>cal[0xC61C4])))

Every load is ld.bu/ld.hu (UNSIGNED) and every compare is `cmp; bh` (UNSIGNED "branch if higher"), i.e. the
test is `cal < signal`. Raising each cal to its unsigned datatype max makes `cal < signal` PERMANENTLY FALSE:
  - byte cals -> 0xFF (255): gp-0x682f is a byte clamped to 255, so `255 < gp-0x682f` can never be true.
  - u16 cals  -> 0xFFFF (65535): param_1 is a clamped angular-rate magnitude (<= 65535), so `65535 < param_1`
    can never be true.
=> the debounce counter can never advance -> STEER_STATUS=4 can never be produced by either function.
This disables the TORQUE and the ANGLE-RATE trigger conditions COMPLETELY, exactly as directed.

BLAST RADIUS (verified: whole-image operand scan for each tp-displacement)
=========================================================================================================
0xC64B4/B5/B6/B7 (74b4/b5/b6/b7) and 0xC61C0/C2/C4 (71c0/c2/c4) are read ONLY by FUN_0002a30e and
m_steer_torque_arbitration -- the two copies of this one FSM. No other function reads them (all other search
hits were branch-target substring false-positives; the `mov 0xc71c4,ep` @0x2bb36 is a different ADDRESS,
0xC71C4, not the cal 0xC61C4). Both copies use the cals for the identical debounce purpose, so raising them
disables the condition in BOTH -- consistent with "disable the debounce state machine."

LEFT STOCK (deliberate)
=========================================================================================================
- 0xC64B8 (=112): a THIRD gp-0x682f threshold, but it gates the SEPARATE gp-0x6758 counter whose saturation
  raises STEER_STATUS=7 + logs DTC 0x49 (FUN_00016de6). That is a fault/DTC path, NOT the gentle EME
  (status 4). Left untouched so genuine fault detection is preserved. (Offer: include if operator wants the
  whole FSM inert.)
- 0xC6312 (=320): the engage-SM decider torque-MAX gate. Stock/V31. NOT the trigger (this session's finding).

CAVEAT -- honest status (operator has this in the handoff)
=========================================================================================================
STEER_STATUS=4 was shown to be a REPORT; the exact instruction that ZEROES the LKAS motor term during the
felt cut was NOT located this session (the previously-assumed anchor gp-0x6809 is dead code -- 0 writers).
V36 provably kills the STEER_STATUS=4 debounce SM (and its arbitration twin). IF the felt assist-drop is
driven by this same gp-0x682f/param_1 condition (very likely -- same signals, same arbitration function),
V36 eliminates the gentle EME. IF the felt drop persists with NO STEER_STATUS=4, that is itself the decisive
result: the assist-drop is a separate path. V36 is thus a clean discriminating experiment, not a guaranteed
fix. STUDY ARTIFACT -- no flash until the operator names file + bus (kit iron rule).

ALL V31 EDITS RETAINED UNCHANGED: GAIN 1782, clamps 1024, ramp 0x1B, corridor x4 int+float, boost floor
4096 int+float, PN. ZERO code edits (cal-only).
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
BIN_OUT      = plain_image_path("_v36_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V36: gentle-EME DEBOUNCE-SM conditions -> unsigned MAX (fully disabled) ============
# TORQUE channel (gp-0x682f), byte cals, unsigned compare -> max 0xFF. gp-0x682f is clamped to 255, so
# `0xFF < gp-0x682f` is never true. RISE uses 0xC64B4; HOLD uses 0xC64B5; secondary AND-terms use B7/B6.
DEBOUNCE_TORQUE_CALS = [  # (addr, cur, new, note) -- byte
    (0xC64B4, 112, 0xFF, "DEBOUNCE torque RISE tp+0x74b4  gp-0x682f> cut  112->255 (V36 MAX u8 = OFF)"),
    (0xC64B5,  96, 0xFF, "DEBOUNCE torque HOLD tp+0x74b5  gp-0x682f> cut   96->255 (V36 MAX u8 = OFF)"),
    (0xC64B7,  64, 0xFF, "DEBOUNCE torque 2ndAND tp+0x74b7 gp-0x682f> cut  64->255 (V36 MAX u8 = OFF)"),
    (0xC64B6,  54, 0xFF, "DEBOUNCE torque 2ndAND tp+0x74b6 gp-0x682f> cut  54->255 (V36 MAX u8 = OFF)"),
]
# RATE channel (param_1 angular-rate magnitude), u16 cals, unsigned compare -> max 0xFFFF. param_1 is a
# clamped rate (<= 65535), so `0xFFFF < param_1` is never true. RISE+HOLD share 0xC61C0; secondary C2/C4.
DEBOUNCE_RATE_CALS = [  # (addr, cur, new, note) -- u16
    (0xC61C0, 1600, 0xFFFF, "DEBOUNCE rate PRIMARY tp+0x71c0  param_1> cut 1600->65535 (V36 MAX u16 = OFF)"),
    (0xC61C2,  896, 0xFFFF, "DEBOUNCE rate 2ndAND  tp+0x71c2  param_1> cut  896->65535 (V36 MAX u16 = OFF)"),
    (0xC61C4, 1280, 0xFFFF, "DEBOUNCE rate 2ndAND  tp+0x71c4  param_1> cut 1280->65535 (V36 MAX u16 = OFF)"),
]

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

# ----- pre/post GUARD: the debounce-SM cals must be at their STOCK values before we patch -----
DEBOUNCE_STOCK_GUARD_U8 = [
    (0xC64B8, 112, "gp-0x6758 counter thr tp+0x74b8 -- LEFT STOCK (fault/DTC path, not gentle EME)"),
]
GENTLE_EME_DECIDER_STOCK_GUARD_U16 = [
    (0xC6312, 320, "engage-SM decider torque-MAX gate 0xC6312 -- LEFT STOCK 320 (V31 base; NOT the trigger)"),
]

# --- NO-CODE-EDIT guard: V36 is cal-only; these stock code sites MUST remain byte-identical ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x561C2, b"\x44\x07\xf0\xea", "0x660 packer byte0 zero-store -- stock (V36 is NOT a telemetry build)"),
    # engage-SM decider stays stock (cal-only edit): the disengage-decider instructions are untouched.
    (0x40dd0, b"\xe5\x87\x13\x73", "engage-SM param2 ld.hu 0x7312[tp],r16 -- stock (reads 0xC6312 kept 320)"),
    (0x40db8, b"\xe5\x3f\x13\x73", "engage-SM param1 ld.hu 0x7312[tp],r7  -- stock"),
    (0x40df4, b"\xe5\x3f\x13\x73", "engage-SM param3 ld.hu 0x7312[tp],r7  -- stock"),
    # debounce-SM cal READ sites stay stock (proves cal-only: only the cal DATA changes, not the code)
    (0x2a420, b"\x85\x6f\xb5\x74", "FUN_0002a30e rise ld.bu 0x74b4[tp],r13 -- stock (reads cal we edit)"),
    (0x2a42c, b"\xe5\x4f\xc1\x71", "FUN_0002a30e rise ld.hu 0x71c0[tp],r9  -- stock"),
    (0x2a49a, b"\xa5\x57\xb5\x74", "FUN_0002a30e hold ld.bu 0x74b5[tp],r10 -- stock"),
    (0x2a4a6, b"\xe5\x47\xc1\x71", "FUN_0002a30e hold ld.hu 0x71c0[tp],r8  -- stock"),
    (0x2923e, b"\x85\x5f\xb5\x74", "arb rise ld.bu 0x74b4[tp],r11 -- stock"),
    (0x2924a, b"\xe5\x47\xc1\x71", "arb rise ld.hu 0x71c0[tp],r8  -- stock"),
    (0x292b8, b"\xa5\x4f\xb5\x74", "arb hold ld.bu 0x74b5[tp],r9  -- stock"),
    (0x292c4, b"\xe5\x3f\xc1\x71", "arb hold ld.hu 0x71c0[tp],r7  -- stock"),
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


def guard_u16(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_u8(code, table):
    for addr, expect, note in table:
        if code[addr] != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {code[addr]} ({note})")


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
    (0xC6000, 0xC6FFC),   # covers debounce cals (0xC61C0.., 0xC64B4..) AND all V31 cals
    (0x13000, 0xC4FFC),   # covers the PN bytes
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V31 (unchanged) + gentle-EME DEBOUNCE-SM torque+rate conditions -> unsigned MAX (OFF)")
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
    guard_u8(code, DEBOUNCE_STOCK_GUARD_U8)
    guard_u16(code, GENTLE_EME_DECIDER_STOCK_GUARD_U16)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF before patch"

    # patches -- V36 debounce-SM disable
    patch_bytes(code, DEBOUNCE_TORQUE_CALS)    # gp-0x682f byte thresholds -> 0xFF
    patch_cal_u(code, DEBOUNCE_RATE_CALS)      # param_1 u16 thresholds -> 0xFFFF
    # V31 base (unchanged)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)

    # post-patch guards (untouched arms still stock; left-stock cals still stock)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_u8(code, DEBOUNCE_STOCK_GUARD_U8)                 # 0xC64B8 STILL stock
    guard_u16(code, GENTLE_EME_DECIDER_STOCK_GUARD_U16)     # 0xC6312 STILL stock 320
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
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
    for addr, _, new, _ in DEBOUNCE_TORQUE_CALS:
        assert ecu_plain[addr - START] == new, f"debounce torque cal @0x{addr:X} lost (want {new:#x})"
    for addr, _, new, _ in DEBOUNCE_RATE_CALS:
        assert struct.unpack_from("<H", ecu_plain, addr - START)[0] == new, f"debounce rate cal @0x{addr:X} lost"
    # left-stock invariants must survive
    assert ecu_plain[0xC64B8 - START] == 112, "0xC64B8 must stay stock 112 (fault-counter path)"
    assert struct.unpack_from("<H", ecu_plain, 0xC6312 - START)[0] == 320, "0xC6312 must stay stock 320 (V31 base)"
    # V31 base survives
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
    print("V36 = V31 (gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN)")
    print("      + gentle-EME DEBOUNCE-SM torque channel (0xC64B4/B5/B6/B7 -> 255)")
    print("      + gentle-EME DEBOUNCE-SM rate  channel (0xC61C0/C2/C4 -> 65535)")
    print("      (0xC64B8 fault-counter + 0xC6312 decider LEFT STOCK; cal-only, NO code edits)\n")
    build("V36", code, headers, tag="V31-debounceSM-OFF-torqueMax255-rateMax65535")
    return 0


if __name__ == "__main__":
    sys.exit(main())
