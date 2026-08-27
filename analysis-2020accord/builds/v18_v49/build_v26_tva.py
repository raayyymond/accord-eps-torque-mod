"""builds/v18_v49/build_v26_tva.py — V26 = V25 (2x GAIN + 2x INTEGER corridor) + MATCHED 2x FLOAT corridor twin.

WHY THIS REPLACES V25:
  V25 doubled the INTEGER direction corridor (dir1/dir2 Y @0xC674E/50/5A/5C: +-1024 -> +-2048) so the 2x
  LKAS command would sit INSIDE the corridor and not wind up the soft-EME integrator gp-0x3570. That part
  was correct -- the corridor IS the envelope the command is differenced against (instruction-verified:
  integrator accumulation @0x43220/0x43236 = (cmd - corridor_wall r29/r27); walls come from the dir1/dir2
  LERP Y-cals).

  But V25 HARD-FAULTED at full lock (DTC 0xF00049, EPS shutdown). Root cause: the consistency monitor
  FUN_00043e44 is a LOCKSTEP-REDUNDANCY checker -- the corridor/integrator is computed BOTH in fixed-point
  integer AND in float, and the monitor trips (accumulates divergence to 128.0 -> DTC) if the two drift
  apart. V25 doubled the INTEGER corridor but left the FLOAT corridor twin STOCK:

    INTEGER corridor dir1/dir2 Y  @0xC674E.. (s16)  : stock +-1024 = +-1.0  (in the monitor's /1024 units)
    FLOAT   corridor LERP Y-table @0xC6664.. (f32)  : stock 1.0  (velocity-indexed, N=7, flat)

  Stock: integer +-1024 -> +-1.0 == float 1.0  -> lockstep holds (V18 never hard-faulted).
  V25:   integer doubled to 2.0   != float 1.0  -> drift 1.0 >> ~0.001 monitor threshold -> accumulates
         fastest at full lock (integrator driven hardest by gp-0x6acc assist demand) -> DTC.

  V26 FIX (operator directive: "change the envelope ... AND update the floating point path so the
  float-integer consistency checks pass"): double the FLOAT corridor twin to 2.0 to MATCH the doubled
  integer corridor. Restores lockstep -> every downstream int/float twin (gp-0x6af6/gp-0x6db0,
  gp-0x6b00/gp-0x6db8, gp-0x6b0a/gp-0x6dc0) recomputes identically -> no divergence -> no hard fault,
  while the wider corridor still prevents integrator wind-up -> no soft EME. NO monitor-code edit, NO
  threshold tampering -- pure cal data, both sides of the SAME quantity scaled together.

THE FLOAT CORRIDOR TWIN (cold-mapped this session; byte-confirmed + FUN_00043e44 trace):
  Velocity-indexed float LERP, base tp+0x7648 (0xC6648). Layout [N][X0..X_{N-1}][Y0..Y_{N-1}] as f32:
    N      @0xC6644 = 7
    X[0..6]@0xC6648 = [-7.0, -6.0, -5.0, 0.0, 5.0, 6.0, 7.0]  (column velocity breakpoints)
    Y[0..6]@0xC6664 = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]     (corridor magnitude, flat = +-1.0 int)
  gp-0x6db0 = LERP(this table, |col_vel|). V26 scales ONLY the 7 Y floats 1.0 -> 2.0. N + X untouched.

WHAT V26 EDITS (on stock V9 code.bin) -- block #48 [0xC6000,0xC6FFC):
  GAIN  tp+0x746c @0xC646C  891 -> 1782    (x2, V18)
  CLAMP tp+0x71b4 @0xC61B4  512 -> 1024    (x2, V18)
  CLAMP tp+0x71b2 @0xC61B2  512 -> 1024    (x2, V18)
  RAMP  tp+0x74de @0xC64DE  0x11 -> 0x1B   (V18 re-engage ramp)
  INT   corridor dir1 Y @0xC674E/50  +1024 -> +2048 ; dir2 Y @0xC675A/5C  -1024 -> -2048   (x2, V25)
  FLOAT corridor twin Y @0xC6664/68/6C/70/74/78/7C  1.0 -> 2.0  (x2, V26 NEW)
  PN @0x13109/@0x14120  '-' -> ','
  CRC: block #48 @0xC6FFC ; main @0xC4FFC. No code-byte patches; no caves.

SAFETY: study artifact. No flash until the operator names the file + bus (kit iron rule). The corridor is
  still the anti-fight / anti-oscillation gate widened x2; operator weighed this. V26 ADDS no new authority
  change vs V25 -- it only restores the float-side lockstep that V25 left broken.
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
BIN_OUT      = plain_image_path("_v26_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- Calibration UNSIGNED halfword patches (block #48) -- V18 lineage ---
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
    (0xC674E,  1024,  2048, "dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+2048 (x2)"),
    (0xC6750,  1024,  2048, "dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+2048 (x2)"),
    (0xC675A, -1024, -2048, "dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-2048 (x2)"),
    (0xC675C, -1024, -2048, "dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-2048 (x2)"),
]

# --- INTEGER corridor STRUCTURE guard: X breakpoints + N counts MUST stay stock (s16) ---
CORRIDOR_GUARD = [
    (0xC6748,     2, "TABLE1 N (count)"),
    (0xC674A, -8192, "TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "TABLE2 N (count)"),
    (0xC6756,  1024, "TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "TABLE2 X[1] velocity bkpt"),
]

# --- FLOAT corridor TWIN f32 Y-value patches (block #48) -- V26 NEW: the lockstep match ---
#   ONLY the 7 corridor-magnitude (Y) floats are scaled x2. N + X (velocity) breakpoints untouched.
FLOAT_CORRIDOR_PATCHES = [
    (0xC6664, 1.0, 2.0, "float corridor Y[0] tp+0x7664  1.0->2.0 (x2)"),
    (0xC6668, 1.0, 2.0, "float corridor Y[1] tp+0x7668  1.0->2.0 (x2)"),
    (0xC666C, 1.0, 2.0, "float corridor Y[2] tp+0x766c  1.0->2.0 (x2)"),
    (0xC6670, 1.0, 2.0, "float corridor Y[3] tp+0x7670  1.0->2.0 (x2)"),
    (0xC6674, 1.0, 2.0, "float corridor Y[4] tp+0x7674  1.0->2.0 (x2)"),
    (0xC6678, 1.0, 2.0, "float corridor Y[5] tp+0x7678  1.0->2.0 (x2)"),
    (0xC667C, 1.0, 2.0, "float corridor Y[6] tp+0x767c  1.0->2.0 (x2)"),
]

# --- FLOAT corridor STRUCTURE guard: N + X breakpoints MUST stay stock (N=int32, X=f32) ---
FLOAT_CORRIDOR_GUARD_I = [
    (0xC6644, 7, "FLOAT corridor N (count, int32)"),
]
FLOAT_CORRIDOR_GUARD_F = [
    (0xC6648, -7.0, "FLOAT corridor X[0]"),
    (0xC664C, -6.0, "FLOAT corridor X[1]"),
    (0xC6650, -5.0, "FLOAT corridor X[2]"),
    (0xC6654,  0.0, "FLOAT corridor X[3]"),
    (0xC6658,  5.0, "FLOAT corridor X[4]"),
    (0xC665C,  6.0, "FLOAT corridor X[5]"),
    (0xC6660,  7.0, "FLOAT corridor X[6]"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 -- calibration (gain/clamps/rampstep/int+float corridor)
    (0x13000, 0xC4FFC),  # main block -- PN only
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


def guard_corridor(code, table):
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


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


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


def build(label, code_stock, headers, tag):
    print("=" * 78)
    print(f"{label}: V25 (2x GAIN + 2x INT corridor) + MATCHED 2x FLOAT corridor twin (lockstep restore)")
    code = bytearray(code_stock)

    guard_corridor(code, CORRIDOR_GUARD)         # int corridor X/N stock before touching
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)    # float corridor N stock
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)    # float corridor X stock
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)       # V25: integer corridor x2
    patch_float(code, FLOAT_CORRIDOR_PATCHES)    # V26: float corridor twin x2 (the lockstep match)
    patch_bytes(code, PN_PATCHES)
    guard_corridor(code, CORRIDOR_GUARD)         # confirm int X/N untouched after Y edits
    guard_int32(code, FLOAT_CORRIDOR_GUARD_I)    # confirm float N untouched
    guard_float(code, FLOAT_CORRIDOR_GUARD_F)    # confirm float X untouched
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
    for addr, expect, note in CORRIDOR_GUARD:
        got = struct.unpack_from("<h", ecu_plain, addr - START)[0]
        assert got == expect, f"int corridor GUARD @0x{addr:X} expected {expect} got {got} ({note})"
    for addr, _, new, _ in FLOAT_CORRIDOR_PATCHES:
        got = struct.unpack_from("<f", ecu_plain, addr - START)[0]
        assert got == new, f"float corridor @0x{addr:X} expected {new} got {got}"
    for addr, expect, note in FLOAT_CORRIDOR_GUARD_I:
        got = struct.unpack_from("<i", ecu_plain, addr - START)[0]
        assert got == expect, f"float corridor N GUARD @0x{addr:X} expected {expect} got {got} ({note})"
    for addr, expect, note in FLOAT_CORRIDOR_GUARD_F:
        got = struct.unpack_from("<f", ecu_plain, addr - START)[0]
        assert got == expect, f"float corridor X GUARD @0x{addr:X} expected {expect} got {got} ({note})"
    # NO code-section edits should exist: shl sites + monitor sites must be byte-identical to stock.
    for a in (0x42DAE, 0x42DCA, 0x42F16, 0x43190, 0x43196, 0x431B4, 0x431B6,
              0x44640, 0x44648, 0x4466C, 0x447DD, 0x4463A, 0x44662):
        assert ecu_plain[a - START] == code_stock[a], f"unexpected code edit @0x{a:X} (should be stock)"
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
    print(f"baseline = V9 stock; V26 = V18 gain/clamps/ramp + 2x INT corridor + 2x FLOAT corridor twin + PN\n")
    build("V26", code, headers, tag="LKAS-2x-corridor2x-floattwin2x-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
