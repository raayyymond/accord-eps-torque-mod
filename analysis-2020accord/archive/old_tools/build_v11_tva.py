"""build_v11_tva.py — V11 LKAS-torque builds for 2020 Accord (39990-TVA-A160).

CONTEXT / WHY THIS DIFFERS FROM V10
-----------------------------------
V10 (build_v10_tva.py) scaled 0xC4A42/0xC4A6E — which the V10A road test proved are
the DRIVER column-torque->assist curves, NOT the LKAS path (doubling them lightened
manual steering and KILLED LKAS via the override gate). V11 instead edits the actual
LKAS comma-command lane traced end-to-end in notes/TORQUE_PATH_AND_TABLE.md §0.5/§0.6:

  CAN 0xE4 -> 0xFEDF1652 setpoint=clamp(x*-4,±0x4000) -> arb FUN_00028ea6 (±limit table)
   -> distributor FUN_00025c32 (lane+4 ±0x2800) -> mixer FUN_00026c80 (LKAS acc gp-0x3d8c)
   -> gate FUN_00042ac6 -> 0xFEDF1502 -> shaper FUN_00042af8 -> demand/CSIG0 -> FOC -> motor

DISASM CORRECTION TO TORQUE_MOD_V0.md (verified in Ghidra this session, code.bin open):
  * The mixer LKAS lane is the 0x27442 block (the gp-0x3d8c accumulator). Its clamped
    result r26 is the exact value sign-extended into the gate (jarl 0x42ac6 @ 0x277f6).
    The other three ±0x2800 mixer blocks are NOT the LKAS lane.
  * The gate FUN_00042ac6 maps out-of-window to the SENTINEL 0x7FFF (not a clamp).
  * The shaper FUN_00042af8 @0x43ae8 RE-RANGE-CHECKS 0xFEDF1502 with the SAME ±0x2800
    idiom and `cmovc 0x0,r13,r12` -> anything outside ±0x2800 (incl. the 0x7FFF sentinel)
    COLLAPSES TO ZERO. TORQUE_MOD_V0.md modeled the shaper as a plain ±0x2000 clamp and
    MISSED this input gate (0x43ae8/0x43aec). So overshooting the gate window does not
    add torque — it zeroes LKAS (the Civic V10A failure mode).
  * Both range-checks use `+0x2800 / -0x5001`. Widening the window to ±W needs the 2nd
    immediate = -(2W+1); W=0x4000 -> -0x8001 OVERFLOWS imm16. So the HARD static-value-edit
    ceiling on this path is ±0x3FFF = 16383 (~2.0x). True 3x (24576) is NOT a value edit;
    it requires restructuring both comparison sequences (a code rewrite). V11 therefore
    builds the ACHIEVABLE ~2x ceiling-raise only.
  * Residual UNKNOWN (Hard Ceiling): the shaper also clamps by a RUNTIME symmetric limit
    r10 = *(gp-0x4f64) (0x43af6), itself zeroed if >0x2800. If that runtime value is below
    our target it binds first — delivered torque is then < 2x regardless of these edits.
    Not statically resolvable; needs a bench RAM probe. This build raises every STATIC
    ceiling; whether 2x is physically delivered is empirical.

MECHANICS: identical proven path to V9b/V10 — cipher v9b ((c^0xBF)^0x10)-0x9E, window
[0x13000,0x100000), raw &-key BF109E from the T2F template, self-validate by decoding our
own payload as the ECU would, splicing, and replaying the 49-block bootloader CRC walk.
Edits span TWO CRC blocks: the main block [0x13000,0xC4FFC) (all code sites) and block 23
[0xE4000,0xE4FFC) (arb table). Both stored CRCs are recomputed; the walk must read 49/49.

STUDY ARTIFACT. Not flashed by this script. Per kit safety rules no flash happens until
the operator names the file + bus.
"""
import os, sys, gzip, struct, zlib

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = str(REPO_ROOT)
FLASHING = str(FLASHING_ROOT)
for p in (HERE, FLASHING, ANALYSIS_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from encode_eps import parse_x31, build_decode_table, invert_table, encode_x31, OPS
from verify_bootloader_crc import walk

CODE_BIN     = STOCK_FW_DUMP / "code.bin"
TEMPLATE_T2F = CALIB_FILES / "39990-T2F-A210.rwd.gz"
OUT_DIR      = RWD_DIR   # operator: all .rwd land here
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"                      # comma/red-panda EPS target -> 0x18DA30F1

# v9b cipher ONLY (OPS: xor=0, sub=4)
V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- CRC blocks touched (block_start, stored-CRC-offset) ---
# code sites -> main block; arb base rows @0xE4180 -> block 0xE4000;
# arb mirror rows @0xE5180 -> block 0xE5000 (separate trailer @0xE5FFC).
TOUCHED_BLOCKS = [
    (0x13000, 0xC4FFC),   # main block (all code sites)
    (0xE4000, 0xE4FFC),   # arb table, base slots 0xE4180
    (0xE5000, 0xE5FFC),   # arb table, mirror slots 0xE5180
]

# ---------------------------------------------------------------------------
# Code-site imm16 patches.  Each tuple = (addr, current 4 bytes BE-hex, new imm16).
# Only the imm16 (little-endian at addr+2) is rewritten; the opcode/reg bytes
# (addr, addr+1) are asserted unchanged first = brick-safety guard.
#   -0x3FFF=0xC001  -0x4000=0xC000  -0x7FFF=0x8001
# ---------------------------------------------------------------------------
W = 0x3FFF        # widened plausibility window (imm16 max for the +W/-(2W+1) idiom)
NEG2WP1 = (-(2 * W + 1)) & 0xFFFF         # -(2W+1) = -0x7FFF = 0x8001
CLAMP = 0x4000    # downstream symmetric clamps (>= W, so the window stays binding)

CODE_PATCHES = [
    # distributor FUN_00025c32 lane +4 : ±0x2800 -> ±0x4000  (plain clamp, cmovge)
    (0x25c9c, "0B0600D8", (-CLAMP) & 0xFFFF, "dist addi -0x2800 -> -0x4000"),
    (0x25ca2, "20760028", CLAMP,             "dist movea 0x2800 -> 0x4000"),
    (0x25ca8, "0B060028", CLAMP,             "dist addi 0x2800 -> 0x4000"),
    (0x25cac, "207600D8", (-CLAMP) & 0xFFFF, "dist movea -0x2800 -> -0x4000"),
    # mixer FUN_00026c80 LKAS lane (gp-0x3d8c acc, feeds gate @0x277f6) : ±0x2800 -> ±W
    (0x27442, "0B0600D8", (-W) & 0xFFFF,     "mixer addi -0x2800 -> -0x3FFF"),
    (0x27446, "20D60028", W,                 "mixer movea 0x2800 -> 0x3FFF"),
    (0x2744c, "0B060028", W,                 "mixer addi 0x2800 -> 0x3FFF"),
    (0x27450, "204E00D8", (-W) & 0xFFFF,     "mixer movea -0x2800 -> -0x3FFF"),
    # gate FUN_00042ac6 plausibility window : ±0x2800 -> ±W
    (0x42ac6, "066E0028", W,                 "gate addi 0x2800 -> 0x3FFF"),
    (0x42aca, "0D06FFAF", NEG2WP1,           "gate addi -0x5001 -> -0x7FFF"),
    # shaper FUN_00042af8 INPUT range-check on 0xFEDF1502 (doc missed) : ±0x2800 -> ±W
    (0x43ae8, "0D460028", W,                 "shaper-in addi 0x2800 -> 0x3FFF"),
    (0x43aec, "0806FFAF", NEG2WP1,           "shaper-in addi -0x5001 -> -0x7FFF"),
    # shaper FUN_00042af8 final clamp : ±0x2000 -> ±0x4000
    (0x43b0e, "0E0600E0", (-CLAMP) & 0xFFFF, "shaper addi -0x2000 -> -0x4000"),
    (0x43b12, "20AE0020", CLAMP,             "shaper movea 0x2000 -> 0x4000"),
    (0x43b18, "0E060020", CLAMP,             "shaper addi 0x2000 -> 0x4000"),
    (0x43b1c, "203600E0", (-CLAMP) & 0xFFFF, "shaper movea -0x2000 -> -0x4000"),
]

# Arb setpoint-magnitude limit (FUN_00028ea6 family @0xCB844 -> tables @0xE4xxx).
# Slot = [count][9 breakpoints][9 values][term]; value row @ +0x14, all 15360 (0x3C00).
# Raise ONLY the 9 value entries per slot to 0x4000 (16384); never touch breakpoints.
# mode/gear-invariant: 6 slots @0xE4180 + mirror 6 @0xE5180.
ARB_OLD, ARB_NEW = 0x3C00, 0x4000
ARB_VALUE_OFFSETS = [base + n * 0x28 + 0x14 + 2 * i
                     for base in (0xE4180, 0xE5180)
                     for n in range(6) for i in range(9)]

# NOTE: V11A is a pure CEILING-RAISE. Road test 2026-05-25 found it imperceptible —
# openpilot rarely commands full-scale, so the raised clamps never engage. The fix is a
# SETPOINT GAIN change (shl 0x2->0x3 @0x526d2), which lives in the separate build_v12_tva.py.


def patch_code(code):
    for addr, cur_be, new_imm, note in CODE_PATCHES:
        cur = bytes.fromhex(cur_be)
        got = bytes(code[addr:addr + 4])
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur.hex().upper()} "
                                 f"got {got.hex().upper()} ({note})")
        struct.pack_into("<H", code, addr + 2, new_imm)   # rewrite imm16 only
        print(f"  0x{addr:05X}: {cur_be} -> {got[:2].hex().upper()}"
              f"{new_imm & 0xFF:02X}{(new_imm >> 8) & 0xFF:02X}   {note}")


def patch_arb(code):
    n = 0
    for off in ARB_VALUE_OFFSETS:
        v = struct.unpack_from("<H", code, off)[0]
        if v != ARB_OLD:
            raise AssertionError(f"arb 0x{off:05X}: expected 0x{ARB_OLD:04X} got 0x{v:04X}")
        struct.pack_into("<H", code, off, ARB_NEW)
        n += 1
    print(f"  arb table: {n} value entries 0x{ARB_OLD:04X} -> 0x{ARB_NEW:04X} "
          f"(12 slots x 9; breakpoints untouched)")


def make_tva_headers(template_info):
    new = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new.append((tag, [b"39990-TVA-A110", b"39990-TVA-A160"]))
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


def build(label, code_stock, headers, tag="LKAS-2x-corrected"):
    print("=" * 74)
    print(f"{label}: LKAS-lane ~2x ceiling-raise (window ±0x{W:04X}, clamp ±0x{CLAMP:04X}, "
          f"arb 0x{ARB_NEW:04X})   cipher v9b")
    code = bytearray(code_stock)

    patch_code(code)
    patch_arb(code)
    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    # self-validate exactly as the ECU would
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")
    if not matches or fails:
        print(f"  *** {label} self-check FAILED — not writing ***\n")
        return None
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA-A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.relpath(out, REPO)}\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  %=30 -> 0x18DA30F1\n")

    # V11A = ceiling-raise only. Road test 2026-05-25: NOT perceptible — openpilot
    # rarely commands full-scale, so the raised clamps never engage (a ceiling-raise is
    # invisible unless the command saturates). The fix (clamps + setpoint gain) is V12A,
    # in build_v12_tva.py. V11A is kept for reference / A-B comparison.
    build("V11A", code, headers)

    print("=" * 74)
    print("V11B (requested 3x) NOT BUILT — 3x (24576) is not reachable by value edits.")
    print("  The gate (0x42ac6) AND shaper input-check (0x43ae8) both use the +0x2800/")
    print("  -0x5001 plausibility idiom; widening the window to ±W needs 2nd imm=-(2W+1),")
    print("  and W=0x4000 overflows imm16. Hard window ceiling = ±0x3FFF (~2.0x). Anything")
    print("  above it is mapped to 0x7FFF by the gate and then ZEROED by the shaper.")
    print("  3x requires restructuring both comparison sequences (a code rewrite), and is")
    print("  further gated by the runtime symmetric limit *(gp-0x4f64). See module docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
