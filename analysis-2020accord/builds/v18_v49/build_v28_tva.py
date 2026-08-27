"""builds/v18_v49/build_v28_tva.py

⚠⚠⚠ DO NOT FLASH — V28 is ANALYSIS-FALSIFIED (2026-06-03, after this script was written). A follow-up
disasm trace (0x43040-0x43172) showed gp-0x6af6 = max(driver-torque IIR gp-0x3574, corridor floor), so the
monitors are an INT-vs-FLOAT LOCKSTEP on max(driver-torque, corridor), NOT a corridor twin. V28's premise
below ("divergence = 2x residual") mis-identified the max's secondary arm: it is the LARGE driver-torque
demand, not a small fixed table. The trampoline doubles the WHOLE float twin (incl. the torque arm), so when
the wheel is turned (hand torque -> demand-dominated) the float twin = 2x torque vs the int wall = torque ->
divergence ~ FULL torque, which the +-10/1024 / +-15 LSB tolerance widen CANNOT cover -> V28 faults like V27.
Corrected fix = V29 (cal-only matched corridor): DROP the trampoline AND the tolerance widen; widen the
corridor FLOOR by doubling BOTH int cal 0xC674E AND the float corridor mirror 0xC6590/0xC65A4 (matched).
See docs/handoffs/2026-06/HANDOFF-2026-06-03-v28.md (correction banner) + memory/reference/firmware/reference_accord_corridor_lockstep.md.
The rationale below is the as-built (now-falsified) reasoning, kept for the trail.

V28 = V27 + a PROPORTIONAL widen of BOTH corridor consistency monitors so the
doubled float-vs-int residual stays inside tolerance. Fixes V27's immediate hard-fault.

WHY THIS REPLACES V27 (which FLASHED -> hard fault the instant the wheel was turned):
  Root cause (confirmed by decomp + 4 tracers + algebra): V27 doubles BOTH the float corridor TWIN
  (gp-0x6db0/db8, via the 0xC4E00 trampoline) AND the integer corridor WALL (gp-0x6af6/b00, via the
  cal 0xC674E). Both reach exactly 2x, so the corridor matches at the PRIMARY corridor (the float
  tables 0xC6590/0xC65A4 are exact mirrors of the int corridor). BUT the watchdog twin is
  fVar8 = polarity x MAX(corridor, SECONDARY tables 0xC65B8/0xC65D4 whose Y reaches 2.0); in stock
  the secondary term exceeds the corridor by a small RESIDUAL <= 5/1024 (the monitor tolerance), and
  doubling BOTH twin and wall doubles that residual:
        divergence_V27 = 2 x (stock divergence)  <=  2 x 5/1024 = 10/1024
  which exceeds the +-5/1024 (Monitor 2) / +-5 LSB (Monitor 1) window the instant polarity != 0
  (any steering) -> fault SM ramps to 0x3f1b hard shutdown in ~10 cycles. (No symmetric doubling can
  avoid this -- it is the residual itself that doubles.)

V28 FIX (operator-directed): keep V27's both-x2 (the cal-doubled wall ALSO widens the soft-EME
  integrator gp-0x3570, so the soft EME is addressed), and widen BOTH monitors' corridor tolerance
  to 2x so the doubled residual fits:
    Since stock divergence <= 5/1024 EVERYWHERE (the car works stock), V27 divergence <= 10/1024
    EVERYWHERE; a 10/1024 (Monitor 2) / +-15 LSB (Monitor 1) window provably passes. This is a
    PROPORTIONAL recalibration to the 2x design point, NOT blinding: a genuinely wrong corridor
    diverges by ~1.0 = 1024 LSB, still far outside the widened window. Only the dir1/dir2 CORRIDOR
    checks are widened; the integrator (weight 4) and delivered-torque (weight 32) checks track
    (both sides see the same widened wall) and are left at their own tolerances.

EXACT MONITOR-2 (watchdog FUN_00043e44) tolerance constants (byte-scan verified on stock code.bin;
  the +5/1024 movhi is SHARED, the -5/1024 is a SEPARATE movhi per check):
    0x4463E movhi 0x3ba0,r0,r7  = +5/1024  (SHARED positive; used by dir1, dir2, and weight 4/16/32)
    0x44646 movhi 0xbba0,r0,r14 = -5/1024  (dir1 negative)
    0x4466A movhi 0xbba0,r0,r16 = -5/1024  (dir2 negative)
    (0x4478C / 0x448E6 movhi 0xbba0 belong to NON-corridor weights -> LEFT STOCK on purpose.)
  We widen r7/r14/r16 only: +-5/1024 (0x3ba0/0xbba0) -> +-10/1024 (0x3c20/0xbc20).

EXACT MONITOR-1 (shaper FUN_00042af8) tolerance (one signed-unsigned-wrap window per direction):
    0x4318E addi 0x5,r12,r15 ; 0x43196 cmp 0xb,r15   (dir1)
    0x431B2 addi 0x5,r10,r6  ; 0x431B6 cmp 0xb,r6     (dir2)
  We widen addi 0x5->0xf and cmp 0xb->0x1e (window +-5 -> ~+-15 LSB, covers 2x5 + the +-1 trunc).

SAFETY: study artifact. No flash until the operator names the file + bus (kit iron rule). All edits
  are in the main CRC block [0x13000,0xC4FFC). The trampoline/cave/cal are IDENTICAL to V27; the only
  new bytes are the 10 tolerance bytes. Re-verify the built _v28_plain_image.bin in Ghidra before flash.
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
BIN_OUT      = plain_image_path("_v28_plain_image.bin")
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

# --- INTEGER direction-corridor SIGNED s16 Y-value patches (block #48) -- same as V27 ---
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

# --- FLOAT corridor LERP_B (0xC6664) MUST stay STOCK 1.0 (V26's edit reverted) ---
FLOAT_LERPB_STOCK_GUARD = [
    (0xC6664, 1.0, "FLOAT LERP_B Y[0] tp+0x7664 -- MUST stay stock 1.0 (V26 broke this)"),
    (0xC6668, 1.0, "FLOAT LERP_B Y[1]"),
    (0xC666C, 1.0, "FLOAT LERP_B Y[2]"),
    (0xC6670, 1.0, "FLOAT LERP_B Y[3]"),
    (0xC6674, 1.0, "FLOAT LERP_B Y[4]"),
    (0xC6678, 1.0, "FLOAT LERP_B Y[5]"),
    (0xC667C, 1.0, "FLOAT LERP_B Y[6]"),
]

# --- CODE patches (main block): trampoline + cave -- IDENTICAL to V27 ---
B = bytes
CODE_PATCHES = [
    (0x4463A, B([0xe2,0xff,0x62,0x54]), B([0x88,0x07,0xc6,0x07]),
     "trampoline @0x4463a: subf.s r2,lp,r10 -> jr 0xC4E00"),
    (0xC4E00, B([0xff,0xff,0xff,0xff]), B([0xff,0xff,0x60,0xfc]),
     "cave +0x00: addf.s lp,lp,lp     (double dir1 twin)"),
    (0xC4E04, B([0xff,0xff,0xff,0xff]), B([0xf4,0xa7,0x60,0xa4]),
     "cave +0x04: addf.s r20,r20,r20  (double dir2 twin)"),
    (0xC4E08, B([0xff,0xff,0xff,0xff]), B([0xe2,0xff,0x62,0x54]),
     "cave +0x08: subf.s r2,lp,r10    (displaced dir1 divergence)"),
    (0xC4E0C, B([0xff,0xff,0xff,0xff]), B([0xb7,0x07,0x32,0xf8]),
     "cave +0x0c: jr 0x0004463e       (return)"),
]
CAVE_TAIL_GUARD = (0xC4E10, 0x8)   # 0xC4E10..0xC4E17 == 0xFF

# --- V28 NEW: corridor-monitor TOLERANCE widen (main block) -- single-byte patches ---
#   Monitor 2 (watchdog): movhi imm 0x3ba0(+5/1024)/0xbba0(-5/1024) -> 0x3c20(+10/1024)/0xbc20(-10/1024)
#   Monitor 1 (shaper):   addi 0x5->0xf (LE low byte) ; cmp 0xb->0x1e (imm5 in opcode low byte)
TOLERANCE_PATCHES = [
    (0x44640, 0xa0, 0x20, "M2 dir1+ r7  movhi 0x3ba0->0x3c20  (+5/1024->+10/1024, SHARED positive)"),
    (0x44641, 0x3b, 0x3c, "M2 dir1+ r7  movhi high byte"),
    (0x44648, 0xa0, 0x20, "M2 dir1- r14 movhi 0xbba0->0xbc20  (-5/1024->-10/1024)"),
    (0x44649, 0xbb, 0xbc, "M2 dir1- r14 movhi high byte"),
    (0x4466C, 0xa0, 0x20, "M2 dir2- r16 movhi 0xbba0->0xbc20  (-5/1024->-10/1024)"),
    (0x4466D, 0xbb, 0xbc, "M2 dir2- r16 movhi high byte"),
    (0x43190, 0x05, 0x0f, "M1 dir1 addi imm 0x5->0xf (window center)"),
    (0x43196, 0x6b, 0x7e, "M1 dir1 cmp 0xb->0x1e (window 2x = +-~15 LSB)"),
    (0x431B4, 0x05, 0x0f, "M1 dir2 addi imm 0x5->0xf"),
    (0x431B6, 0x6b, 0x7e, "M1 dir2 cmp 0xb->0x1e"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 -- calibration (gain/clamps/rampstep/int corridor)
    (0x13000, 0xC4FFC),  # main block -- code trampoline + cave + monitor tolerances + PN
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


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def patch_code(code, table):
    for addr, old, new, note in table:
        assert len(old) == len(new)
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}: {old.hex()} -> {new.hex()}   {note}")


def guard_corridor(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<h", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


def guard_float(code, table):
    for addr, expect, note in table:
        got = struct.unpack_from("<f", code, addr)[0]
        if got != expect:
            raise AssertionError(f"GUARD 0x{addr:05X}: expected {expect} got {got} ({note})")


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
    print(f"{label}: V27 (2x INT corridor + twin trampoline) + 2x widen of BOTH corridor monitors")
    code = bytearray(code_stock)

    # guards BEFORE patching
    guard_corridor(code, CORRIDOR_GUARD)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)
    assert bytes(code[CAVE_TAIL_GUARD[0]:CAVE_TAIL_GUARD[0] + CAVE_TAIL_GUARD[1]]) == b"\xff" * CAVE_TAIL_GUARD[1]
    assert bytes(code[0xC4E00:0xC4E10]) == b"\xff" * 0x10, "cave 0xC4E00..0xC4E0F must be stock 0xFF before patch"

    # patches
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)           # integer corridor x2
    patch_code(code, CODE_PATCHES)                   # V27 trampoline + cave (double float twins)
    patch_bytes(code, TOLERANCE_PATCHES)             # V28 NEW: widen both corridor monitors 2x
    patch_bytes(code, PN_PATCHES)

    # guards AFTER patching
    guard_corridor(code, CORRIDOR_GUARD)
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)       # confirm 0xC6664 STILL stock 1.0
    assert bytes(code[CAVE_TAIL_GUARD[0]:CAVE_TAIL_GUARD[0] + CAVE_TAIL_GUARD[1]]) == b"\xff" * CAVE_TAIL_GUARD[1], \
        "cave tail 0xC4E10.. must remain 0xFF"

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
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        got = struct.unpack_from("<f", ecu_plain, addr - START)[0]
        assert got == expect, f"LERP_B stock GUARD @0x{addr:X} expected {expect} got {got} ({note})"
    for addr, _, new, note in CODE_PATCHES:
        got = bytes(ecu_plain[addr - START:addr - START + len(new)])
        assert got == new, f"code patch @0x{addr:X} expected {new.hex()} got {got.hex()} ({note})"
    assert bytes(ecu_plain[0xC4E10 - START:0xC4E18 - START]) == b"\xff" * 0x8, "cave tail must be 0xFF"
    # V28 tolerance bytes present exactly
    for addr, _, new, note in TOLERANCE_PATCHES:
        assert ecu_plain[addr - START] == new, f"tolerance @0x{addr:X} expected {new:#04x} got {ecu_plain[addr-START]:#04x} ({note})"
    # widened tolerance constants decode to the intended values
    assert struct.unpack_from("<H", ecu_plain, 0x44640 - START)[0] == 0x3c20, "M2 r7 imm not 0x3c20"
    assert struct.unpack_from("<H", ecu_plain, 0x44648 - START)[0] == 0xbc20, "M2 r14 imm not 0xbc20"
    assert struct.unpack_from("<H", ecu_plain, 0x4466C - START)[0] == 0xbc20, "M2 r16 imm not 0xbc20"
    assert struct.unpack_from("<H", ecu_plain, 0x43190 - START)[0] == 0x000f, "M1 dir1 addi imm not 0xf"
    assert struct.unpack_from("<H", ecu_plain, 0x43196 - START)[0] == 0x7a7e, "M1 dir1 cmp not 0x7a7e"
    assert struct.unpack_from("<H", ecu_plain, 0x431B4 - START)[0] == 0x000f, "M1 dir2 addi imm not 0xf"
    assert struct.unpack_from("<H", ecu_plain, 0x431B6 - START)[0] == 0x327e, "M1 dir2 cmp not 0x327e"
    # the two NON-corridor watchdog negatives MUST remain stock -5/1024 (not over-widened)
    assert struct.unpack_from("<H", ecu_plain, 0x4478E - START)[0] == 0xbba0, "0x4478C non-corridor tol moved!"
    assert struct.unpack_from("<H", ecu_plain, 0x448E8 - START)[0] == 0xbba0, "0x448E6 non-corridor tol moved!"
    # OTHER code sites must remain byte-identical to stock (no stray edits).
    # (0x4463A trampoline + 0xC4E00 cave + the 10 tolerance bytes are the only code edits.)
    for a in (0x42DAE, 0x42DCA, 0x42F16, 0x43172, 0x43176, 0x44662, 0x449F4, 0x44A30, 0x44A2A):
        assert ecu_plain[a - START] == code_stock[a], f"unexpected code edit @0x{a:X} (should be stock)"
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
    for a, bb in runs:
        print(f"     0x{a:05X}-0x{bb:05X} ({bb - a + 1}B)")

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
    print("baseline = V9 stock; V28 = V27 (V18 gain/clamps/ramp + 2x INT corridor + twin trampoline)")
    print("          + 2x PROPORTIONAL widen of BOTH corridor monitors (Monitor 2 watchdog 5/1024->10/1024")
    print("          on r7/r14/r16 ; Monitor 1 shaper +-5->+-15 LSB on dir1/dir2) + PN")
    print("          (0xC6664 LEFT STOCK ; non-corridor weight tolerances LEFT STOCK)\n")
    build("V28", code, headers, tag="LKAS-2x-corridor2x-twindbl-MONtol2x-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
