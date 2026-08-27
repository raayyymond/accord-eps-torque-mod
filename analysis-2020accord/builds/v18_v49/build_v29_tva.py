"""builds/v18_v49/build_v29_tva.py - V29 = V18 (2x GAIN) + MATCHED 2x DIRECTION-CORRIDOR (int + the CORRECT float mirror).

V29 supersedes V28 (ANALYSIS-FALSIFIED) and V27/V26 (both FLASHED->faulted). It is CAL-ONLY: NO code
trampoline, NO monitor-tolerance widen, NO 0xC6664 edit. It is "V26 done right" -- V26 doubled the WRONG
float table; V29 doubles the right one.

=========================================================================================================
THE CORRECTED MODEL (this session, read shaper FUN_00042af8 + watchdog FUN_00043e44 disasm/decomp MYSELF)
=========================================================================================================
The two consistency monitors BOTH cross-check the FLOAT twins (gp-0x6db0 dir1 / gp-0x6db8 dir2, x1024)
against the INT walls (gp-0x6af6 / gp-0x6b00), window +-5 LSB:
  - Monitor 1 (shaper FUN_00042af8 @ ~0x43190): |float(gp-0x6db0)*1024 - int(gp-0x6af6)| in a +-5 window
  - Monitor 2 (watchdog FUN_00043e44 @0x4463a): |gp-0x6db0 - gp-0x6af6/1024| <= 5/1024  (weight 1/2)
A divergence accumulator >=128.0 -> FUN_000462e6(0x3f1b) -> hard shutdown (DTC 0xF00049).

The INT wall is a THREE-WAY MAX (shaper decomp lines ~582-644, both tracers reconciled):
    gp-0x6af6 = max( dir_corridor[cal 0x774e],  driver-torque IIR[gp-0x3574, sar-8],  boost[cal 0x7760] )
              * polarity(gp-0x6752)
  - dir_corridor = LERP over the s16 table @0xC6748 (N=2, X=velocity[-8192,-1024], Y=+1024 flat).  ** the soft-EME corridor **
  - IIR          = gp-0x3574 driver-column-torque IIR (>>8 to natural scale).
  - boost        = LERP over the s16 table @0xC6760 (X=[700,800,1100] torque, Y=[0,1536,2048]).

The FLOAT twin (computed in FUN_00043e44) recomputes the SAME max through FLOAT MIRROR tables. Its
corridor arm is the flat +-1.0 LERP tables that I traced feeding ONLY the twin (r11/r7 -> r9/r2 -> lp/r20,
not reused as a sign, not stored elsewhere):
    dir1 corridor mirror: table @0xC658C (N=2, X=[-8,-1], Y @0xC6598/0xC659C = +1.0)  <- LERP reads Y@0x7598
    dir2 corridor mirror: table @0xC65A0 (N=2, X=[ 1, 8], Y @0xC65AC/0xC65B0 = -1.0)  <- LERP reads Y@0x75ac
  (1024 int <-> 1.0 float in the monitor's /1024 units; both tables are FLAT, so the velocity-vs-torque
   index axis is moot -- they always emit the flat value.)

  ** NOT 0xC6664 ** : that table (X@0xC6648, Y@0xC6664, flat 1.0) is the ENVELOPE LERP_B -- it feeds the
    early envelope lp -> gp-0x6da8 and the SEPARATE envelope monitor gp-0x6c84 (decomp line ~1287), which
    is NONZERO at rest. V26 doubled 0xC6664 -> +offset at rest -> FLASHED -> hard fault AT REST. Left STOCK.
  ** NOT 0xC6590/0xC65A4 ** : those are the X (velocity/torque) BREAKPOINTS, not the Y magnitude. The
    HANDOFF's V29 proposal named these by mistake; doubling them would scale the index axis, not the corridor.

=========================================================================================================
WHY V29 IS SAFE WHERE V25/V26/V27 FAULTED
=========================================================================================================
  V25 (int corridor 0x774e x2 only)            -> int wall corridor arm doubled, float twin stock -> desync
                                                  at full lock (corridor-dominant) -> DTC.
  V26 (V25 + 0xC6664 x2)                        -> 0xC6664 is the ENVELOPE, not the corridor -> +2.0 envelope
                                                  offset at rest -> DTC at rest.
  V27 (V25 + trampoline doubling the WHOLE twin)-> doubled the torque/boost arms too -> when turning
                                                  (demand-dominated) float=2x demand vs int=1x demand ->
                                                  divergence ~ full demand -> DTC when turning.
  V29 doubles ONLY the matched CORRIDOR arm on BOTH sides (int 0x774e + float 0xC6598/0xC65AC). The IIR and
      boost arms are untouched on both sides, so:
        - wherever the corridor dominates the max: both sides = 2x corridor -> matched.
        - wherever IIR or boost dominates: both sides unchanged -> matched (at the stock <=5/1024 residual).
      The stock float-vs-int residual is NOT amplified (V27's fatal flaw). The monitors stay fully live:
      a genuinely-wrong corridor (~1024 LSB) still diverges far outside +-5 -> recalibration, not blinding.
  The 2x LKAS torque itself is V18's arb-output GAIN (0xC646C), which is INDEPENDENT of the wall
      (Tracer-verified: GAIN cal absent from the wall computation 0x43040-0x43172) -> it never desyncs the
      monitor and is already FLASHED+road-validated. The corridor widen only gives that 2x command room in
      the soft-EME integrator gp-0x3570 (the corridor feeds it) so the command does not wind up the SM cutback.

CONFIDENCE ~85%. Residual (road test is the arbiter, per feedback_operator_lived_experience):
  (a) if the felt soft EME is the driver-override torque-sensor PLAUSIBILITY dropout (not corridor overflow),
      the corridor widen will not fix THAT -- but V29 still delivers safe 2x and must not hard-fault.
  (b) the int corridor (velocity-indexed) and float corridor mirror (torque-indexed) are matched only
      because both are FLAT; verified flat in stock bytes. Pre-flash: re-disassemble the built image.

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
BIN_OUT      = plain_image_path("_v29_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- Calibration UNSIGNED halfword patches (block #48) -- V18 lineage (the real 2x torque) ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]

# --- Calibration single-byte patches (block #48) -- V18 lineage ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]

# --- INTEGER direction-corridor SIGNED s16 Y-value patches (block #48) -- V25 lineage ---
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  2048, "INT dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+2048 (x2)"),
    (0xC6750,  1024,  2048, "INT dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+2048 (x2)"),
    (0xC675A, -1024, -2048, "INT dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-2048 (x2)"),
    (0xC675C, -1024, -2048, "INT dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-2048 (x2)"),
]

# --- INTEGER corridor STRUCTURE guard: X breakpoints + N counts MUST stay stock (s16) ---
CORRIDOR_GUARD = [
    (0xC6748,     2, "INT TABLE1 N (count)"),
    (0xC674A, -8192, "INT TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "INT TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "INT TABLE2 N (count)"),
    (0xC6756,  1024, "INT TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "INT TABLE2 X[1] velocity bkpt"),
]

# --- FLOAT direction-corridor MIRROR f32 Y-value patches (block #48) -- V29 NEW: the CORRECT lockstep match.
#   These are the flat +-1.0 LERP tables whose output (r11 dir1 / r7 dir2) feeds ONLY the float twin lp/r20.
FLOAT_CORRIDOR_PATCHES = [
    (0xC6598,  1.0,  2.0, "FLOAT dir1 Y[0] tp+0x7598  corridor mirror  +1.0->+2.0 (x2)"),
    (0xC659C,  1.0,  2.0, "FLOAT dir1 Y[1] tp+0x759c  corridor mirror  +1.0->+2.0 (x2)"),
    (0xC65AC, -1.0, -2.0, "FLOAT dir2 Y[0] tp+0x75ac  corridor mirror  -1.0->-2.0 (x2)"),
    (0xC65B0, -1.0, -2.0, "FLOAT dir2 Y[1] tp+0x75b0  corridor mirror  -1.0->-2.0 (x2)"),
]

# --- FLOAT corridor-mirror STRUCTURE guard: N (int32) + X (f32) breakpoints MUST stay stock ---
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

# --- ENVELOPE LERP_B (0xC6664) MUST stay STOCK 1.0 (V26 broke this -> rest fault) ---
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0 (V26 broke this; NOT the corridor)"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]

# --- BOOST table (0xC65B8 float / 0xC6760 int) + SPEED-gain (0xC65D4) MUST stay STOCK (untouched max arms) ---
FLOAT_OTHER_ARMS_GUARD_F = [
    (0xC65B8, 700.0, "BOOST float X[0] -- stock (untouched max arm)"),
    (0xC65C8,   1.5, "BOOST float Y[1] -- stock"),
    (0xC65CC,   2.0, "BOOST float Y[2] -- stock"),
    (0xC65F0,   2.0, "SPEED-gain float Y[0] -- stock"),
    (0xC65F8,   0.5, "SPEED-gain float Y[2] -- stock"),
]
INT_BOOST_GUARD = [
    (0xC676A, 1536, "BOOST int Y[1] tp+0x776a -- stock (untouched max arm)"),
    (0xC676C, 2048, "BOOST int Y[2] tp+0x776c -- stock"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# --- NO-CODE-EDIT guard: these stock code sites MUST remain byte-identical (V29 is cal-only) ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10 (V27 hooked this; V29 must NOT)"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock (V28 widened; V29 must NOT)"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
]
CAVE_GUARD = (0xC4E00, 0x18)   # 0xC4E00..0xC4E17 == 0xFF (no trampoline cave)


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
    (0xC6000, 0xC6FFC),  # block #48 -- calibration (gain/clamps/rampstep/int+float corridor)
    (0x13000, 0xC4FFC),  # main block -- PN only
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V18 GAIN (2x) + MATCHED 2x direction corridor (INT 0x774e + FLOAT 0xC6598/0xC65AC)")
    code = bytearray(code_stock)

    # guards BEFORE patching
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_OTHER_ARMS_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF before patch"

    # patches (all calibration data; no code)
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)         # INT direction corridor x2
    patch_float(code, FLOAT_CORRIDOR_PATCHES)      # FLOAT direction-corridor mirror x2 (the lockstep match)
    patch_bytes(code, PN_PATCHES)

    # guards AFTER patching (confirm only the intended cells moved)
    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)     # 0xC6664 still stock (NOT V26's mistake)
    guard_float(code, FLOAT_OTHER_ARMS_GUARD_F)    # boost/speed arms still stock
    guard_s16(code, INT_BOOST_GUARD)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave tail must remain 0xFF"

    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    # self-check: re-decode the emitted rwd, confirm cipher round-trip + all bootloader CRCs
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

    # --- readback (decode the emitted .rwd, confirm every intended value survived) ---
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == 1782, "GAIN lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B4 - START)[0] == 1024, "CLAMP b4 lost"
    assert struct.unpack_from("<H", ecu_plain, 0xC61B2 - START)[0] == 1024, "CLAMP b2 lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for addr, _, new, _ in CORRIDOR_PATCHES:
        got = struct.unpack_from("<h", ecu_plain, addr - START)[0]
        assert got == new, f"int corridor @0x{addr:X} expected {new} got {got}"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        got = struct.unpack_from("<f", ecu_plain, addr - START)[0]
        assert got == new, f"float corridor @0x{addr:X} expected {new} got {got}"
    for addr, expect, note in CORRIDOR_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int corridor GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_CORRIDOR_GUARD_I:
        assert struct.unpack_from("<i", ecu_plain, addr - START)[0] == expect, f"float corridor N GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_CORRIDOR_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"float corridor X GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"LERP_B stock GUARD @0x{addr:X} ({note})"
    for addr, expect, note in FLOAT_OTHER_ARMS_GUARD_F:
        assert struct.unpack_from("<f", ecu_plain, addr - START)[0] == expect, f"other-arm stock GUARD @0x{addr:X} ({note})"
    for addr, expect, note in INT_BOOST_GUARD:
        assert struct.unpack_from("<h", ecu_plain, addr - START)[0] == expect, f"int boost GUARD @0x{addr:X} ({note})"
    # NO code-section edits: trampoline site + monitor tolerance sites + cave must be byte-identical to stock.
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
    print("baseline = V9 stock; V29 = V18 gain/clamps/ramp + 2x INT corridor (0x774e)")
    print("          + 2x FLOAT corridor mirror (0xC6598/0xC659C/0xC65AC/0xC65B0) + PN")
    print("          (0xC6664 ENVELOPE left STOCK ; boost/speed arms left STOCK ; NO code edits)\n")
    build("V29", code, headers, tag="LKAS-2x-corridor2x-floatmirror-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
