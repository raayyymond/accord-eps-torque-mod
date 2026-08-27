"""builds/v18_v49/build_v27_tva.py — V27 = V18 base + 2x INTEGER corridor + a CODE trampoline that doubles the
FLOAT corridor twins so BOTH lockstep monitors track the widened corridor. NO 0xC6664 edit.

WHY THIS REPLACES V26 (which FLASHED -> hard fault at rest, wheel un-turnable):
  V26 tried to make the float corridor twin = 2.0 by doubling cal 0xC6664. That was the WRONG table:
  0xC6664 is LERP_B, a velocity-indexed ENVELOPE multiplier. The float envelope is
      Y = base/1024 + lerp_b * lerp_a,   and at rest lerp_a = 2.0 (LERP_A Y[0]=2.0).
  So doubling lerp_b (1.0->2.0) ADDED a constant +lerp_a (= +2.0) offset to the float watchdog
  envelope at EVERY operating point including parked/centered -> the watchdog diverged from the
  (un-widened) integer side from t=0 -> DTC 0xF00049 + latched motor-off within ~10 cycles.
  (Root cause re-confirmed on the STOCK image code.bin = ghidra_project/code.bin.)

THE REAL CORRIDOR LOCKSTEP (instruction-verified on STOCK code.bin, NOT the _v2x images):
  The float corridor twins are computed in FUN_00043e44:
      lp  (dir1 twin) = r2_corridor x r13   @0x4461e   (or r9_corridor x r13 @0x44624)
      r20 (dir2 twin) = r13 x r9_corridor   @0x4462e        r13 = float(polarity gp-0x6752)
  lp -> stored to gp-0x6db0 @0x449f4 ; r20 -> stored to gp-0x6db8 @0x44a30.
  Both monitors compare the twin against wall/1024 (wall = LERP over the int corridor cal):
      Monitor 1 (FUN_00042af8 @0x43172): trunc(twin x 1024) ~= int_wall  (gp-0x6af6 / gp-0x6b00)
      Monitor 2 (FUN_00043e44 @0x4463a/0x44662): |twin - float(wall)/1024| <= 5/1024 -> weights 1.0/2.0
  Widening the int corridor cal (0xC674E.. -> +-2048) makes wall/1024 = +-2.0 at full lock while
  the float twin stays +-1.0 -> divergence +-1.0 >> 5/1024 -> BOTH monitors fault at full lock
  (this is exactly the V25 hard fault). At rest both wall and twin ~= 0 (LERP near center) -> no fault,
  which is why V25 faulted only at full lock.

V27 FIX -- double the float twins lp & r20 so they track the widened wall, via a trampoline in the
  genuinely-free 0xC4E00 cave (stock = all 0xFF; verified). Collateral-verified: after 0x4463a, lp is
  used ONLY by the dir1 divergence + its store (gp-0x6db0), and r20 ONLY by the dir2 divergence + its
  store (gp-0x6db8); no other consumer, and NO jarl between 0x4463a and the stores (lp=r31 not
  clobbered). The earlier LERP/threshold uses of lp/r20 are at LOWER addresses (0x4448a.., 0x44586)
  i.e. BEFORE the twin assignments at 0x4461e/0x4462e -> they use earlier register values, unaffected.

  Trampoline: replace the inline dir1-divergence at 0x4463a (`subf.s r2,lp,r10` = e2 ff 62 54) with
  `jr 0xC4E00`, and put in the cave:
      0xC4E00: addf.s lp,lp,lp     ; double dir1 twin (lp -> 2*lp)
      0xC4E04: addf.s r20,r20,r20  ; double dir2 twin (r20 -> 2*r20)
      0xC4E08: subf.s r2,lp,r10    ; the displaced instruction (now r10 = 2*lp - wall1/1024)
      0xC4E0C: jr 0x4463e          ; return to the instruction after the trampoline
  Net effect: lp & r20 (hence both divergences AND gp-0x6db0/gp-0x6db8) are doubled. At full lock
  twin 1.0->2.0 == wall/1024 = 2.0 -> Monitor 1 trunc(2.0x1024)=2048=wall, Monitor 2 |2.0-2.0|=0.
  Monitors stay FULLY LIVE: a genuinely wrong corridor LERP still diverges from the doubled-expected
  value (this is a recalibration to the 2x design point, NOT a disable).

WHAT V27 EDITS (on stock V9 code.bin):
  block #48 [0xC6000,0xC6FFC):
    GAIN  tp+0x746c @0xC646C  891 -> 1782   (x2, V18)
    CLAMP tp+0x71b4 @0xC61B4  512 -> 1024   (x2, V18)
    CLAMP tp+0x71b2 @0xC61B2  512 -> 1024   (x2, V18)
    RAMP  tp+0x74de @0xC64DE  0x11 -> 0x1B  (V18 re-engage ramp)
    INT corridor dir1 Y @0xC674E/50  +1024 -> +2048 ; dir2 Y @0xC675A/5C  -1024 -> -2048  (x2)
    (0xC6664 float LERP_B = LEFT STOCK 1.0 -- V26's mistake reverted)
  main block [0x13000,0xC4FFC):
    CODE trampoline @0x4463A  (subf.s -> jr 0xC4E00)
    CODE cave @0xC4E00..0xC4E0F  (addf.s lp,lp,lp ; addf.s r20,r20,r20 ; subf.s r2,lp,r10 ; jr 0x4463e)
    PN @0x13109/@0x14120  '-' -> ','
  CRC: block #48 @0xC6FFC ; main @0xC4FFC.

SAFETY: study artifact. No flash until the operator names the file + bus (kit iron rule). This is the
  FIRST code-section patch on the Accord platform -- it doubles only the watchdog's float corridor
  twins (gp-0x6db0/gp-0x6db8), which are NOT delivered torque; the integrator twin (gp-0x6dc0) and all
  other monitor checks are untouched. The build self-check round-trips the cipher, re-walks all
  bootloader CRCs, and reads back every intended edit; the cave/trampoline encodings must be
  re-verified by disassembling _v27_plain_image.bin in Ghidra (code.bin baseline) before any flash.
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
BIN_OUT      = plain_image_path("_v27_plain_image.bin")
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

# --- INTEGER direction-corridor SIGNED s16 Y-value patches (block #48) ---
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

# --- CODE patches (main block): trampoline + cave (the V27 twin-doubling fix) ---
#   Each entry: (addr, old_bytes, new_bytes, note). Verified on stock code.bin.
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
# the 0x10 bytes after the cave code MUST remain stock 0xFF
CAVE_TAIL_GUARD = (0xC4E10, 0x8)   # 0xC4E10..0xC4E17 == 0xFF

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 -- calibration (gain/clamps/rampstep/int corridor)
    (0x13000, 0xC4FFC),  # main block -- code trampoline + cave + PN
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
    print(f"{label}: V18 base + 2x INT corridor + CODE trampoline doubling float corridor twins")
    code = bytearray(code_stock)

    # guards BEFORE patching
    guard_corridor(code, CORRIDOR_GUARD)             # int corridor X/N stock
    guard_float(code, FLOAT_LERPB_STOCK_GUARD)       # 0xC6664 LERP_B stock 1.0 (must NOT be touched)
    assert bytes(code[CAVE_TAIL_GUARD[0]:CAVE_TAIL_GUARD[0] + CAVE_TAIL_GUARD[1]]) == b"\xff" * CAVE_TAIL_GUARD[1]
    assert bytes(code[0xC4E00:0xC4E10]) == b"\xff" * 0x10, "cave 0xC4E00..0xC4E0F must be stock 0xFF before patch"

    # patches
    patch_cal_u(code, CAL_PATCHES)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_corridor(code, CORRIDOR_PATCHES)           # integer corridor x2
    patch_code(code, CODE_PATCHES)                   # V27: trampoline + cave (double float twins)
    patch_bytes(code, PN_PATCHES)

    # guards AFTER patching
    guard_corridor(code, CORRIDOR_GUARD)             # int X/N untouched
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
    # 0xC6664 LERP_B must have survived as STOCK 1.0 (we did NOT touch it)
    for addr, expect, note in FLOAT_LERPB_STOCK_GUARD:
        got = struct.unpack_from("<f", ecu_plain, addr - START)[0]
        assert got == expect, f"LERP_B stock GUARD @0x{addr:X} expected {expect} got {got} ({note})"
    # CODE patches present exactly
    for addr, _, new, note in CODE_PATCHES:
        got = bytes(ecu_plain[addr - START:addr - START + len(new)])
        assert got == new, f"code patch @0x{addr:X} expected {new.hex()} got {got.hex()} ({note})"
    # cave tail still 0xFF
    assert bytes(ecu_plain[0xC4E10 - START:0xC4E18 - START]) == b"\xff" * 0x8, "cave tail must be 0xFF"
    # OTHER code sites must remain byte-identical to stock (no stray edits).
    # (0x4463A is now the trampoline; 0xC4E00.. is the cave -- excluded from this stock check.)
    for a in (0x42DAE, 0x42DCA, 0x42F16, 0x43172, 0x43176, 0x43190, 0x43196,
              0x431B4, 0x431B6, 0x44662, 0x449F4, 0x44A30, 0x44A2A):
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
    print("baseline = V9 stock; V27 = V18 gain/clamps/ramp + 2x INT corridor")
    print("          + CODE trampoline @0x4463a doubling float twins lp/r20 in 0xC4E00 cave + PN")
    print("          (0xC6664 LEFT STOCK -- V26's mistake reverted)\n")
    build("V27", code, headers, tag="LKAS-2x-corridor2x-twindbl-codetrampoline-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
