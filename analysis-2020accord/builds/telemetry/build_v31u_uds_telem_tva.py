"""builds/telemetry/build_v31u_uds_telem_tva.py - V31U = V31 drivability cal + CORRECTED UDS-over-CAN RAM telemetry.

WHAT THIS IS (2026-07-10)
=========================================================================================================
V31U = the studied V31 drivability calibration (gain 2x / clamps / ramp + corridor x4 + boost-floor 4096
+ float mirror + PN) PLUS a comma-visible RAM read of the 4 gentle-EME signals via the EPS APPLICATION
UDS stack (SID 0x22 ReadDataByIdentifier, DID 0x4801), which answers natively on CAN
(req 0x18DA30F1 / resp 0x18DAF130) and crosses the car gateway (unlike broadcast 0x660, gateway-filtered).

This SUPERSEDES the earlier UDStelem build (builds/telemetry/build_uds_telem_tva.py), which had an off-by-one-ENTRY bug:
it wrote the cave pointer into DID 0x4800's handler_ptr field (0xB780C) instead of DID 0x4801's (0xB7820),
so DID 0x4801 reads ran its stock handler and returned constant/stale bytes (empirically confirmed:
bit-exact 0/5828/104/0 across sessions and a full-range wheel yank).

CORRECTED DISPATCH MODEL (Ghidra-traced 2026-07-10, byte-verified against code.bin + the old build image):
  * The RDBI per-DID table's TRUE base is 0xB77FC (NOT 0xB7800), stride 0x14, struct:
      u16 did; u16 declared_len; u32 gate; u32 session; u32 group(low byte=groupID); u32 handler_ptr;
  * The LIVE per-DID payload dispatch reads handler_ptr at entry+0x10 and calls it with a ctx POINTER in
    r6 (FUN_000209ea, drained per-tick by w_steer_control_task after FUN_00021036 arms the pending bit).
    Proven live: DID 0xF181 builds its app-id string through its own handler_ptr with the SAME
    ctx+0xC=len / FUN_000211ba / FUN_0002114e / FUN_0002073a idiom the cave uses.
  * DID 0x4801 = idx1, entry base 0xB7810: declared_len @0xB7812, groupID @0xB781C, handler_ptr @0xB7820.

THE PATCH (UDS telemetry; TRUE-scheme, minimal)
=========================================================================================================
  * handler_ptr @0xB7820  0x0004D8DC -> 0x000C4E00 (the cave)     <- THE FIX the old build missed
  * declared_len @0xB7812 0x0038(56) -> 0x000A(10 = 8 data + 2 DID echo)
  * cave handler @0xC4E00 (72B, verbatim from the old build; ABI verified: ctx ptr in r6 matches the
    handler_ptr call site) reads gp-0x6a62/gp-0x6a5e/gp-0x4f68/gp-0x6cc4, appends 8 LE bytes.
  * DID 0x4800's handler_ptr @0xB780C is LEFT STOCK (0x0004D5C2). Building from stock guarantees this;
    a guard asserts it. (The old build wrongly overwrote it -> DID 0x4800 fault telemetry was clobbered.)
Read `22 48 01` on 0x18DA30F1 -> `62 48 01 <MAXlo MAXhi AVGlo AVGhi TQlo TQhi ANGlo ANGhi>` (LE u16 each).

SAFETY: STUDY ARTIFACT. Read-only DID, no SecurityAccess, default session; the cave is a register-clean
clone of the stock 0xF181-class handler (only store is ctx+0xc len; only scratch regs r6/r7/r15; saves/
restores lp). Touches only the diagnostic read surface + the V31 cal tables -- no command/torque/motor/
soft-EME/engage-SM/fault CODE is edited. No flash until the operator names file + bus (kit iron rule).
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
BIN_OUT      = plain_image_path("_v31u_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096
CORRIDOR_FLT = 4.0
BOOST_INT    = 4096
BOOST_FLT    = 4.0

# ===================== V31 CALIBRATION EDITS (base; verbatim from V31/V31T/TIER1) =====================
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
# NO EPS control CODE is edited; these stock soft-EME sites MUST remain byte-identical.
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
]

# ===================== CORRECTED UDS telemetry patch (TRUE 0xB77FC table scheme) =====================
CAVE = 0x0C4E00
HANDLER = bytes.fromhex(                 # 72B, verbatim from builds/telemetry/build_uds_telem_tva.py (ABI verified)
    "80072100"      # prepare {lp},0
    "207e0a00"      # movea 0x0A,r0,r15
    "667f0c00"      # st.h  r15,0xc[r6]      (ctx->declared_len = 10; r6 = ctx ptr)
    "b5ffaec3"      # jarl  0x000211ba,lp
    "26069e15dffe"  # mov   0xFEDF159E,r6    (voter-MAX gp-0x6a62)
    "023a"          # mov   2,r7
    "b5ff36c3"      # jarl  0x0002114e,lp
    "2606a215dffe"  # mov   0xFEDF15A2,r6    (voter-AVG gp-0x6a5e)
    "023a"          # mov   2,r7
    "b5ff2ac3"      # jarl  0x0002114e,lp
    "26069830dffe"  # mov   0xFEDF3098,r6    (|column torque| gp-0x4f68)
    "023a"          # mov   2,r7
    "b5ff1ec3"      # jarl  0x0002114e,lp
    "26063c13dffe"  # mov   0xFEDF133C,r6    (angle gp-0x6cc4)
    "023a"          # mov   2,r7
    "b5ff12c3"      # jarl  0x0002114e,lp
    "b5fffab8"      # jarl  0x0002073a,lp
    "40063f00"      # dispose 0x0,{lp},[lp]
)
assert len(HANDLER) == 72, len(HANDLER)

# (file_offset, stock_bytes, new_bytes, note)
UDS_PATCHES = [
    (0xB7820, bytes.fromhex("dcd80400"), struct.pack("<I", CAVE),
     "DID 0x4801 handler_ptr 0x0004D8DC -> 0x000C4E00 (cave)   <- the fix"),
    (0xB7812, bytes.fromhex("3800"),     struct.pack("<H", 0x000A),
     "DID 0x4801 declared_len 56 -> 10 (=8 data + 2 DID echo)"),
    (CAVE,    b"\xff" * 72,              HANDLER,
     "telemetry cave handler (reads 4 gentle-EME RAM signals, appends 8 bytes)"),
]
# stock-identity guards (prove we hit the right entry AND do NOT disturb DID 0x4800)
UDS_GUARD = [
    (0xB7810, bytes.fromhex("0148"),     "DID 0x4801 id (idx1) unchanged"),
    (0xB781C, bytes.fromhex("04000000"), "DID 0x4801 groupID field unchanged (0x04)"),
    (0xB780C, bytes.fromhex("c2d50400"), "DID 0x4800 handler_ptr MUST stay stock 0x0004D5C2 (old build's bug)"),
]


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
    for addr, old, new, note in table:
        assert len(old) == len(new), f"code patch length mismatch @0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"CODE 0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}: {old.hex()} -> {new.hex()}   {note}")


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


def guard_bytes(code, table):
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


# V31 cal edits live in the 0xC6000 block; UDS table+cave+PN live in the 0x13000 block.
TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),
    (0x13000, 0xC4FFC),
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V31 base + CORRECTED UDS-over-CAN RAM telemetry (repurpose DID 0x4801 handler_ptr)")
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
    guard_bytes(code, NO_CODE_EDIT_SITES)
    guard_bytes(code, UDS_GUARD)
    assert bytes(code[CAVE:CAVE + 96]) == b"\xff" * 96, "cave region (0xC4E00) must be 0xFF in stock"

    # V31 calibration patches (base)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_corridor(code, INT_BOOST_FLOOR_PATCHES)
    patch_float(code, FLOAT_BOOST_FLOOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    # corrected UDS telemetry patch (handler_ptr -> cave, len, cave body)
    print("  --- UDS telemetry patch (DID 0x4801 handler_ptr -> cave @0xC4E00) ---")
    patch_code(code, UDS_PATCHES)

    # post-patch guards (untouched arms + protected sites still stock)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_int32(code, FLOAT_BOOST_GUARD_I)
    guard_float(code, FLOAT_BOOST_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_SPEEDGAIN_GUARD_F)
    guard_bytes(code, NO_CODE_EDIT_SITES)
    guard_bytes(code, UDS_GUARD)          # DID 0x4800 hp / 0x4801 id / groupID all still stock
    assert bytes(code[CAVE + 72:CAVE + 96]) == b"\xff" * 24, "cave tail must remain 0xFF"

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

    # readback asserts (decode the emitted .rwd from scratch) -- V31 cal
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
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X}"
    for addr, expect_bytes, note in NO_CODE_EDIT_SITES:
        got = bytes(ecu_plain[addr - START:addr - START + len(expect_bytes)])
        assert got == expect_bytes, f"unexpected code edit @0x{addr:X} ({note})"
    # readback asserts -- corrected UDS telemetry
    assert struct.unpack_from("<I", ecu_plain, 0xB7820 - START)[0] == CAVE, "0x4801 handler_ptr != cave"
    assert struct.unpack_from("<H", ecu_plain, 0xB7812 - START)[0] == 0x000A, "0x4801 declared_len != 10"
    assert bytes(ecu_plain[0xB7810 - START:0xB7812 - START]) == bytes.fromhex("0148"), "DID id changed"
    assert struct.unpack_from("<I", ecu_plain, 0xB780C - START)[0] == 0x0004D5C2, "DID 0x4800 hp disturbed!"
    assert struct.unpack_from("<I", ecu_plain, 0xB781C - START)[0] == 0x04, "0x4801 groupID disturbed"
    assert bytes(ecu_plain[CAVE - START:CAVE - START + 72]) == HANDLER, "cave handler lost"
    assert bytes(ecu_plain[CAVE - START + 72:CAVE - START + 96]) == b"\xff" * 24, "cave tail not 0xFF"
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
    print("V31U = V31 (gain/clamps/ramp + corridor x4 + boost floor 4096 + float mirror + PN)")
    print("     + CORRECTED UDS DID 0x4801 -> cave reading 4 gentle-EME RAM signals (handler_ptr @0xB7820)")
    print("       read `22 48 01` on 0x18DA30F1 -> `62 48 01 <MAX AVG |torq| angle>` (LE u16 each)\n")
    build("V31U", code, headers, tag="UDStelem-DID4801-RAMread")
    return 0


if __name__ == "__main__":
    sys.exit(main())
