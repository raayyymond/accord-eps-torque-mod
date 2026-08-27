"""builds/v18_v49/build_v25_tva.py — V25 CLEAN = V18 2x GAIN + 2x DIRECTION CORRIDOR (2020 Accord, 39990-TVA-A160).

WHY THIS REPLACES THE EARLIER V25 (shl/envelope + B-cleanup) APPROACH:
  The V21-V24 thread doubled the INTEGER ENVELOPE (shl 0x8->0x9 on gp-0x3574/gp-0x3578). That envelope
  is a WATCHDOG REFERENCE ONLY -- instruction-verified: it gates neither delivered torque
  (gp-0x6b98 = clamp(min(lanes, governor gp-0x4f64), +-0x2000); envelope absent) NOR the soft-EME
  state machine. Doubling it did nothing useful and only DESYNCED the integer-vs-float consistency
  monitors, which IS the hard fault (DTC 0xF00049, startup/wheel-move) that V19-V24 suffered. So the
  entire shl + FP-twin caves + inline-A neutralize + bit-threshold widen + weight-8 exclude package
  existed only to clean up damage the shl itself caused. Dropping the shl removes the hard fault at the
  source -- nothing on the consistency-monitor side needs touching.

THE TWO REAL LEVERS (this build uses exactly these):
  1. GAIN tp+0x746c (V18): doubles the actual LKAS command/torque -> real 2x at the wheel.
  2. DIRECTION CORRIDOR tp+0x7748 (dir1, UPPER) / tp+0x7754 (dir2, LOWER): the reference the command is
     compared against in the soft-EME command integrator gp-0x3570. Per-tick wind-up delta =
     (command - dir_boundary)<<13, accumulating only when the command exits the corridor [dir2, dir1].
     Stock corridor is a FLAT +-1024 (Y[0]=Y[1] in both tables; velocity-independent). The 2x GAIN
     doubles the command, so the stock +-1024 corridor is exceeded -> integrator winds up -> SM2/SM3
     authority cutback -> V18's soft, recoverable ~10s EME (no DTC, no dash light). Scaling the corridor
     to +-2048 lets the 2x command sit INSIDE it -> wind-up stops -> soft-EME headroom restored,
     proportional to the gain.

  Soft EME (recoverable) is the corridor; hard fault (DTC) was the consistency monitors -- and the hard
  fault only ever existed because of the shl. No shl here => no hard fault => corridor is the only fix.

CORRIDOR TABLE FORMAT (cold-mapped this session; tracer + disasm at s_motor_torque_rate_shaper):
  Each table = [N][X0..X_{N-1}][Y0..Y_{N-1}], N=2, halfwords (s16). X = column angular velocity
  breakpoints (gp-0x4f60, Q10 rad/s); Y = corridor bound (command-domain raw counts, full-scale
  +-8192 = +-0x2000). dir1=TABLE1 output (UPPER), dir2=TABLE2 output (LOWER). LERP base loads:
  movea 0x7748,tp,r6 @0x4304c ; movea 0x7754,tp,r15 @0x430b2 ; Y-array base = base+6.
    TABLE1 (tp+0x7748): N=2 | X[-8192,-1024] | Y[+1024,+1024]   -> dir1 = +1024  (UPPER)
    TABLE2 (tp+0x7754): N=2 | X[+1024,+8192] | Y[-1024,-1024]   -> dir2 = -1024  (LOWER)
  V25 scales ONLY the Y (corridor-bound) halfwords x2; the X (velocity) breakpoints and the N counts
  are left STOCK (asserted). Y values stay well inside s16 and inside the +-8192 command clamp.

WHAT V25 EDITS (on stock V9 code.bin):
  Cal block #48 [0xC6000,0xC6FFC):
    GAIN  tp+0x746c @0xC646C  891 -> 1782    (x2, V18)
    CLAMP tp+0x71b4 @0xC61B4  512 -> 1024    (x2, V18)
    CLAMP tp+0x71b2 @0xC61B2  512 -> 1024    (x2, V18)
    RAMP  tp+0x74de @0xC64DE  0x11 -> 0x1B   (V18 re-engage ramp)
    CORRIDOR dir1 Y @0xC674E  +1024 -> +2048 ; @0xC6750  +1024 -> +2048
    CORRIDOR dir2 Y @0xC675A  -1024 -> -2048 ; @0xC675C  -1024 -> -2048
  Main block [0x13000,0xC4FFC):
    PN strings @0x13109 / @0x14120  '-' -> ','
  CRC: block #48 @0xC6FFC ; main @0xC4FFC. No code-byte patches; no caves.

SAFETY (operator weighed): the corridor is the anti-fight / anti-oscillation authority gate. Widening it
  x2 lets a LKAS command up to 2x farther from the column-motion direction persist before the SM2/SM3
  cutback arms -- a proportional loosening of override-snap responsiveness, matched to the 2x gain.
  STUDY ARTIFACT. No flash until the operator names the file + bus (kit iron rule).
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
BIN_OUT      = plain_image_path("_v25_plain_image.bin")
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

# --- Direction-corridor SIGNED s16 Y-value patches (block #48) -- the soft-EME headroom lever ---
#   ONLY the corridor-bound (Y) halfwords are scaled x2. X (velocity) breakpoints + N counts untouched.
CORRIDOR_PATCHES = [
    (0xC674E,  1024,  2048, "dir1 Y[0] tp+0x774e  UPPER corridor  +1024->+2048 (x2)"),
    (0xC6750,  1024,  2048, "dir1 Y[1] tp+0x7750  UPPER corridor  +1024->+2048 (x2)"),
    (0xC675A, -1024, -2048, "dir2 Y[0] tp+0x775a  LOWER corridor  -1024->-2048 (x2)"),
    (0xC675C, -1024, -2048, "dir2 Y[1] tp+0x775c  LOWER corridor  -1024->-2048 (x2)"),
]

# --- Corridor STRUCTURE guard: X breakpoints + N counts MUST stay stock (s16) ---
CORRIDOR_GUARD = [
    (0xC6748,     2, "TABLE1 N (count)"),
    (0xC674A, -8192, "TABLE1 X[0] velocity bkpt"),
    (0xC674C, -1024, "TABLE1 X[1] velocity bkpt"),
    (0xC6754,     2, "TABLE2 N (count)"),
    (0xC6756,  1024, "TABLE2 X[0] velocity bkpt"),
    (0xC6758,  8192, "TABLE2 X[1] velocity bkpt"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 -- calibration (gain/clamps/rampstep/corridor)
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


def guard_corridor(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
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
    print(f"{label}: CLEAN = V18 2x GAIN + 2x DIRECTION CORRIDOR (no shl, no consistency-monitor edits)")
    code = bytearray(code_stock)

    guard_corridor(code, CORRIDOR_GUARD)   # confirm stock structure before touching
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)
    patch_bytes(code, PN_PATCHES)
    guard_corridor(code, CORRIDOR_GUARD)   # confirm X/N untouched after Y edits
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
        assert got == new, f"corridor @0x{addr:X} expected {new} got {got}"
    for addr, expect, note in CORRIDOR_GUARD:
        got = struct.unpack_from("<h", ecu_plain, addr - START)[0]
        assert got == expect, f"corridor GUARD @0x{addr:X} expected {expect} got {got} ({note})"
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
    print(f"baseline = V9 stock; V25 CLEAN = V18 gain/clamps/rampstep + 2x direction corridor + PN\n")
    build("V25", code, headers, tag="LKAS-2x-V18gain-corridor2x-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
