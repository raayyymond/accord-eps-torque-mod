"""builds/v18_v49/build_v30_tva.py - V30 = V29 with the direction corridor sized to also contain the post-governor
COMP_TORQUE (driver-override compensation), not just the 2x LKAS command.

V30 is identical to V29 in every respect EXCEPT the corridor magnitude: V29 doubled it (1024->2048,
float 1.0->2.0) to hold the 2x LKAS command (<=1024); V30 raises it to 4096 (float 4.0) to also hold the
additive comp term that FUN_000456a4 bakes into gp-0x6acc BEFORE the shaper compares it to the wall.

=========================================================================================================
WHY 4096 (operator-directed: "increase the corridor to also contain the added COMP_TORQUE")
=========================================================================================================
The value compared against the wall is gp-0x6acc = governed_LKAS + COMP_TERM:
  - governed_LKAS  : clamp-bounded by the arb/pack clamp 0xC61B4 -> <= 1024 (V18 2x).
  - COMP_TERM      : driver-override compensation added in FUN_000456a4 (post-governor), engaged only at
                     high column ANGLE (gate LERP1(|gp-0x69ca|) < gp-0x6ac0 LKAS cmd).
                     🛑 CORRECTED 2026-08-08: gp-0x69ca is the ANGLE ACCUMULATOR (0.1 deg/count),
                     NOT driver torque. Sole writers FUN_0003bd7c@0x3c09a + a zero-reset; it sums at Q7
                     unity into 0x14A STEER_WHEEL_ANGLE, and FUN_0003fd9c holds (float)gp-0x69ca * 0.1.
                     The 'driver torque' label predates the angle chain being decompiled and was never
                     re-verified. See memory/accord/calibration/accord-factord-is-the-angle-error-lever.md.
                     ⊕ NOTE: this header's COMP_TERM / gp-0x6acc description is the SAME post-governor
                     comp-add that 2026-08-08 confirmed is the bridge carrying the 11-lane aggregator to
                     the delivered motor command. See memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md.
                     COMP_TERM = MIN(|raw|, LERP2_cap), LERP2_cap (cal 0xC67D8 table) reaches **2560**.
  Worst-case |gp-0x6acc| = |governed_LKAS| + |COMP_TERM| = 1024 + 2560 = 3584.
  -> corridor 4096 (= 4x stock, float 4.0) contains it with ~512 LSB margin, regardless of the comp sign.

  ⚠ UNCERTAINTY (honest): the *realized* COMP_TERM = (gp-0x6ac0 - LERP1)*3072>>10 capped at 2560. Because
  the gate requires LERP1 < gp-0x6ac0 and LERP1 only drops to ~1000 at very high column angle, the actual
  term may be far below 2560 unless gp-0x6ac0's range is large (NOT pinned this session). 4096 is the
  CONSERVATIVE worst-case sizing; if the comp term is actually small, V29's 2048 would already suffice and
  4096 is harmless headroom EXCEPT that it further loosens the integrator cutback (see SAFETY TRADE).

=========================================================================================================
SAFETY TRADE (operator's call) -- name it plainly
=========================================================================================================
The corridor feeds the soft-EME integrator gp-0x3570: it winds up on (gp-0x6acc - corridor) when the
command exceeds the corridor. With corridor=4096 >= worst-case command 3584, the integrator effectively
NEVER winds up in normal+override operation -> the corridor-based soft-EME cutback (and the override SMs
that arm off gp-0x3570) effectively DO NOT FIRE. That is the point (no soft EME / no LKAS drop when the
driver adds torque), but it means the 2x LKAS is HELD even when the driver overrides -- the "fights the
driver" regime that reference_accord_driver_override_plausibility_eme cautioned about. V19's SM-gate
rescale is the alternative if a *proportional* (not defeated) override response is wanted. The operator
weighs this; nothing is flashed without an explicit file+bus call.

=========================================================================================================
LOCKSTEP (unchanged from V29 -- this is why it is still HARD-EME-safe)
=========================================================================================================
The corridor is one arm of the consistency-monitored wall gp-0x6af6 = max(corridor, IIR-envelope, boost).
Raising the INT corridor cal (0xC674E) MUST be matched by the FLOAT corridor mirror (0xC6598/0xC65AC) or
the int-vs-float monitor desyncs -> DTC 0xF00049. V30 raises BOTH to 4096 / 4.0 in lockstep:
  INT  0xC674E/0xC6750 1024->4096 ; 0xC675A/0xC675C -1024->-4096
  FLT  0xC6598/0xC659C  1.0->4.0  ; 0xC65AC/0xC65B0  -1.0->-4.0   (4096/1024 = 4.0 exact)
The IIR-envelope (cap 12288) and boost (cap 2048) arms are UNTOUCHED, so the only changed arm is matched
on both sides -> residual unchanged, monitor stays live (a genuinely-wrong corridor still diverges).
The 2x torque is V18's GAIN (monitor-independent, flashed+validated). NO trampoline, NO tolerance widen,
0xC6664/boost/speed LEFT STOCK & guarded, ZERO code edits.

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
BIN_OUT      = plain_image_path("_v30_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

CORRIDOR_INT = 4096    # V30 corridor magnitude (V29 was 2048). float mirror = 4096/1024 = 4.0
CORRIDOR_FLT = 4.0

# --- Calibration UNSIGNED halfword patches (block #48) -- V18 lineage (the real 2x torque) ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]

# --- INTEGER direction-corridor SIGNED s16 Y-value patches (block #48) ---
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

# --- FLOAT direction-corridor MIRROR f32 Y-value patches (block #48) -- matched lockstep ---
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

# --- ENVELOPE LERP_B (0xC6664) MUST stay STOCK 1.0 (V26 broke this -> rest fault) ---
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "ENVELOPE LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0"),
    (0xC6668, 1.0, "ENVELOPE LERP_B Y[1]"),
    (0xC666C, 1.0, "ENVELOPE LERP_B Y[2]"),
    (0xC6670, 1.0, "ENVELOPE LERP_B Y[3]"),
    (0xC6674, 1.0, "ENVELOPE LERP_B Y[4]"),
    (0xC6678, 1.0, "ENVELOPE LERP_B Y[5]"),
    (0xC667C, 1.0, "ENVELOPE LERP_B Y[6]"),
]

# --- BOOST (angular-rate) + SPEED-gain arms MUST stay STOCK (untouched max arms) ---
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

PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# --- NO-CODE-EDIT guard: these stock code sites MUST remain byte-identical (V30 is cal-only) ---
NO_CODE_EDIT_SITES = [
    (0x4463A, b"\xe2\xff\x62\x54", "trampoline site -- stock subf.s r2,lp,r10"),
    (0x44640, b"\xa0\x3b",         "M2 dir1+ tol movhi imm 0x3ba0 (+5/1024) -- stock"),
    (0x44648, b"\xa0\xbb",         "M2 dir1- tol movhi imm 0xbba0 (-5/1024) -- stock"),
    (0x4466C, b"\xa0\xbb",         "M2 dir2- tol movhi imm 0xbba0 (-5/1024) -- stock"),
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
    (0xC6000, 0xC6FFC),
    (0x13000, 0xC4FFC),
]


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V29 + corridor sized for LKAS(<=1024)+COMP(<=2560): INT 0x774e & FLOAT 0xC6598 -> {CORRIDOR_INT}/{CORRIDOR_FLT}")
    code = bytearray(code_stock)

    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_OTHER_ARMS_GUARD_F)
    guard_s16(code, INT_BOOST_GUARD)
    guard_no_code_edit(code, NO_CODE_EDIT_SITES)
    assert bytes(code[CAVE_GUARD[0]:CAVE_GUARD[0] + CAVE_GUARD[1]]) == b"\xff" * CAVE_GUARD[1], "cave must be 0xFF before patch"

    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_float(code, FLOAT_CORRIDOR_PATCHES)
    patch_bytes(code, PN_PATCHES)

    guard_s16(code, CORRIDOR_GUARD)
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    guard_float(code, FLOAT_OTHER_ARMS_GUARD_F)
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

    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")

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
    print(f"baseline = V9 stock; V30 = V18 gain/clamps/ramp + corridor x4 (INT 0x774e -> {CORRIDOR_INT}")
    print(f"          + FLOAT mirror 0xC6598/0xC65AC -> {CORRIDOR_FLT}) sized for LKAS+COMP, + PN")
    print("          (0xC6664 ENVELOPE / boost / speed left STOCK ; NO code edits)\n")
    build("V30", code, headers, tag="LKAS-2x-corridor4x-LKASplusCOMP-floatmirror-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
