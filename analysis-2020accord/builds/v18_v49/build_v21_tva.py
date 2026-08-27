"""builds/v18_v49/build_v21_tva.py — V21 LKAS 2x + EME fix + LERP3 shift ×2 for the 2020 Accord (39990-TVA-A160).

LINEAGE: V18 (2x arb gain/clamps + EME RAMP-ONLY fix + PN string) PLUS two new code-section
byte patches that raise the LERP3 output shift from <<8 to <<9 in both the main IIR path (r9)
and the bypass/snap path (r11) of s_motor_torque_rate_shaper.

WHAT V21 EDITS (on top of stock V9 code.bin):
  Calibration block #48 [0xC6000, 0xC6FFC) — halfwords (u16 LE):
    0xC646C  GAIN     tp+0x746c   891   -> 1782   (x2, from V14/V15/V18)
    0xC61B4  CLAMP    tp+0x71b4   512   -> 1024   (x2, from V14/V15/V18)
    0xC61B2  CLAMP    tp+0x71b2   512   -> 1024   (x2, from V14/V15/V18)

  Calibration block #48 — single byte (u8):
    0xC64DE  RAMPSTEP tp+0x74de   0x11 -> 0x1B    (17->27, V18 EME override-ramp fix)

  Main block [0x13000, 0xC4FFC) — code bytes (NEW for V21):
    0x42DAE  SHL imm  shl 0x8,r9   0xC8 -> 0xC9   (LERP3 out: r9  << 8 -> << 9, main IIR)
    0x42DCA  SHL imm  shl 0x8,r11  0xC8 -> 0xC9   (LERP3 out: r11 << 8 -> << 9, bypass/snap)

  Main block [0x13000, 0xC4FFC) — part-number strings (from V15B/V18):
    0x13109  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x13100)
    0x14120  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x14117)

  Two CRC blocks recomputed: block #48 @0xC6FFC ; main block @0xC4FFC.

DISASM VERIFICATION (GhidraMCP, 2026-05-30):
  0x42DAE: shl 0x8, r9   bytes c8 4a  in s_motor_torque_rate_shaper — after ld.w gp-0x3574,r11
           (loads lerp3 output); r9 carries the value into the IIR multiply chain.
  0x42DCA: shl 0x8, r11  bytes c8 5a  — bypass/snap branch (mov r9,r11 then immediate shift+store).
  V850 SHL-imm encoding: [15:11]=reg2, [10:5]=0x16 (opcode), [4:0]=imm5.
  Patching byte at the instruction's low address changes imm5 LSB: 01000->01001 (8->9). ✓

STUDY ARTIFACT. No flash until the operator names the file + bus (kit iron rule).
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

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP

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
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- Calibration halfword patches (block #48) — V18 lineage from stock ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V14/V15/V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V14/V15/V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V14/V15/V18)"),
]

# --- Calibration single-byte patches (block #48) ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (byte) [V18 EME fix]"),
]

# --- Code-section byte patches (main block) — NEW for V21 ---
# V850 SHL imm encoding: [15:11]=reg2, [10:5]=opcode(0x16), [4:0]=imm5(shift amount).
# The patched byte is the low byte of the 16-bit instruction; bit0 is the LSB of imm5.
# C8=1100_1000 → imm5=01000=8; C9=1100_1001 → imm5=01001=9.
CODE_BYTE_PATCHES = [
    (0x42DAE, 0xC8, 0xC9, "SHL imm  0x42DAE  shl 0x8,r9  -> shl 0x9,r9   [LERP3 out IIR main path]"),
    (0x42DCA, 0xC8, 0xC9, "SHL imm  0x42DCA  shl 0x8,r11 -> shl 0x9,r11  [LERP3 out bypass/snap]"),
]

# --- Part-number string byte patches (main block) ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits (2x + EME fix + SM-gate rescale/max)
    (0x13000, 0xC4FFC),  # main block — code byte patches (LERP3 shift) + PN string edits
]


def patch_cal(code):
    for addr, cur, new, note in CAL_PATCHES:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} ({cur:#06x}) -> {new:6d} ({new:#06x})   {note}")


def patch_cal_bytes(code):
    for addr, cur, new, note in CAL_BYTE_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}                {note}")


def patch_code_bytes(code):
    for addr, cur, new, note in CODE_BYTE_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}                {note}")


def patch_pn(code):
    for addr, cur, new, note in PN_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}                {note}")


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
    print(f"{label}: V18 lineage + LERP3 shift <<8-><<9 (code patch)   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code)
    patch_cal_bytes(code)
    patch_code_bytes(code)
    patch_pn(code)
    for start, crc_off in TOUCHED_BLOCKS:
        recompute_crc(code, start, crc_off)

    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    # self-check: re-decode the emitted rwd, confirm cipher round-trip + all bootloader CRCs valid
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")

    # lineage readback from re-decoded payload
    gain    = struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0]
    assert gain == 1782, f"GAIN lineage lost (expected 1782, got {gain})"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lineage lost (expected 0x1B)"
    shl_r9  = ecu_plain[0x42DAE - START]
    shl_r11 = ecu_plain[0x42DCA - START]
    assert shl_r9  == 0xC9, f"LERP3 shl r9  patch lost (expected 0xC9, got {shl_r9:#04x})"
    assert shl_r11 == 0xC9, f"LERP3 shl r11 patch lost (expected 0xC9, got {shl_r11:#04x})"
    print(f"  lineage OK: GAIN={gain}  RAMPSTEP=0x1B  shl_r9=0x{shl_r9:02X}  shl_r11=0x{shl_r11:02X}")

    # byte-diff vs stock (count + regions)
    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b-a+1}B)")

    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    n_old, n_new = ecu_plain.count(pn_old), ecu_plain.count(pn_new)
    print(f"  old PN in payload: {n_old}   new PN in payload: {n_new}")
    assert n_old == 0 and n_new == 2, "PN-fix lineage lost"

    if not matches or fails:
        print(f"  *** {label} self-check FAILED — not writing ***\n")
        return None
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{tag}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.relpath(out, REPO)}\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock)")
    print(f"baseline = V9 stock; V21 = V18 lineage (3 cal HW + 1 cal B + 2 PN) + 2 code bytes\n")
    build("V21", code, headers, tag="LKAS-2x-EMEfix-ramponly-LERP3shift9-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
