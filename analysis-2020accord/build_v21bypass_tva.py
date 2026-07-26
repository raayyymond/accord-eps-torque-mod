"""build_v21bypass_tva.py — Diagnostic: V18 lineage + BYPASS path shl only.

PURPOSE: Isolate whether the bypass-path shl 0x8→0x9 alone (without the IIR path edit)
is sufficient to trigger the V21 startup EPS fault. At engine start, tp+0x74CA=0 selects
the bypass path; the IIR path at 0x42DAE never runs at startup. If this build also kills
the EPS immediately at startup, the fault lives in the bypass path's effect (gp-0x3574
doubled via bypass, shl 0x9 at 0x42DCA). If it passes, then either both patches together
are required, or the IIR path patch is the actual trigger.

LINEAGE: V18 (2x arb gain/clamps + EME RAMP-ONLY fix + PN string) PLUS ONE new code byte:

  Main block [0x13000, 0xC4FFC) — code byte:
    0x42DCA  SHL imm  shl 0x8,r11  0xC8 -> 0xC9   (LERP3 out: bypass/snap path only)

  0x42DAE is LEFT STOCK (shl 0x8,r9 — IIR main path unchanged).

STUDY ARTIFACT. No flash until the operator names the file + bus (kit iron rule).
"""
import os, sys, gzip, struct, zlib

from firmware_paths import CALIB_FILES, FLASHING_ROOT, REPO_ROOT, RWD_DIR, STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
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

# --- Calibration halfword patches (block #48) — V18 lineage ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]

# --- Calibration single-byte patches (block #48) ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME fix)"),
]

# --- Code-section byte patches — BYPASS PATH ONLY (diagnostic) ---
# 0x42DAE (IIR path) is intentionally left at stock 0xC8.
CODE_BYTE_PATCHES = [
    (0x42DCA, 0xC8, 0xC9, "SHL imm  0x42DCA  shl 0x8,r11 -> shl 0x9,r11  [bypass/snap only — IIR stock]"),
]

# --- Part-number string byte patches ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),
    (0x13000, 0xC4FFC),
]


def patch_cal(code):
    for addr, cur, new, note in CAL_PATCHES:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_cal_bytes(code):
    for addr, cur, new, note in CAL_BYTE_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}: {cur:#04x} -> {new:#04x}   {note}")


def patch_code_bytes(code):
    for addr, cur, new, note in CODE_BYTE_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}: {cur:#04x} -> {new:#04x}   {note}")


def patch_pn(code):
    for addr, cur, new, note in PN_PATCHES:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}: {cur:#04x} -> {new:#04x}   {note}")


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
    print(f"{label}: V18 lineage + bypass shl only (0x42DCA patched, 0x42DAE stock)")
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

    # self-check
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label}")

    # verify IIR site is STOCK and bypass site is patched
    iir_byte    = ecu_plain[0x42DAE - START]
    bypass_byte = ecu_plain[0x42DCA - START]
    assert iir_byte    == 0xC8, f"IIR site 0x42DAE should be stock 0xC8, got {iir_byte:#04x}"
    assert bypass_byte == 0xC9, f"bypass site 0x42DCA should be 0xC9, got {bypass_byte:#04x}"

    gain = struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0]
    assert gain == 1782, f"GAIN lineage lost (expected 1782, got {gain})"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lineage lost"

    diffs = [i for i in range(START, END) if code[i] != code_stock[i]]
    runs = []
    for i in diffs:
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])

    print(f"  ECU-decode==patched: {matches}   CRC blocks failing: {fails}")
    print(f"  IIR site  0x42DAE = 0x{iir_byte:02X} (stock OK)")
    print(f"  bypass    0x42DCA = 0x{bypass_byte:02X} (patched OK)")
    print(f"  byte-diff vs stock: {len(diffs)} bytes in {len(runs)} run(s):")
    for a, b in runs:
        print(f"     0x{a:05X}-0x{b:05X} ({b-a+1}B)")

    pn_old = b"39990-TVA-A160"; pn_new = b"39990-TVA,A160"
    assert ecu_plain.count(pn_old) == 0 and ecu_plain.count(pn_new) == 2, "PN-fix lineage lost"

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
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})")
    print(f"baseline = V18; bypass-only = V18 + shl 0x9 at 0x42DCA only\n")
    build("V21bypass", code, headers, tag="LKAS-2x-EMEfix-ramponly-bypassSHL9only-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
