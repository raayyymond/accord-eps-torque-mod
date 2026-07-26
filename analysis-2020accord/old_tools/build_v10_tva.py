"""build_v10_tva.py — V10a / V10b modified-torque builds (from V9b recipe).

Base recipe is the CONFIRMED V9b stock build (HOW_TO_BUILD_ACCORD_TVA_RWD.md):
  - cipher v9b ONLY:  decode = ((c ^ 0xBF) ^ 0x10) - 0x9E   [xor,xor,sub], keys BF 10 9E
    (v9a is retired — the V9b flash proved the resident decryptor is the ECU's real path)
  - window [0x13000, 0x100000) single contiguous block, &-key raw BF109E, %=30 (comma)
  - self-validate: decode our own payload as the ECU would, splice at 0x13000, run the
    bootloader CRC-32 walk -> require 49/49 PASS before writing.

V10 change vs V9b (stock): the two candidate torque Y-axis lists in the UNPROTECTED-page
0xC4000 (but CRC-covered by the MAIN block [0x13000,0xC4FFC)) are:
  1. LINEARIZED — replaced by a linear ramp from the list's own start value to its own
     end value across all 12 points (start/end preserved exactly).
  2. SCALED — every linearized value multiplied by 2 (V10a) or 3 (V10b).

CAVEAT THAT §3c GETS WRONG: 0xC4A42/0xC4A6E live in flash page 0xC4000, which the doc
calls "unprotected (no CRC recompute)". That is true only for a *per-4 KB-block* trailer —
page 0xC4000 has none. But the bytes [0xC4000,0xC4FFC) ARE inside the bootloader MAIN block
[0x13000, 0xC4FFC), whose CRC-32 is stored at 0xC4FFC (walk block #49). Editing these bytes
therefore REQUIRES recomputing that main-block CRC, or the ECU returns NRC 0x72. This script
recomputes exactly that one word and nothing else (we touch no protected 4 KB block body, so
no +0xFFC trailer and no +0xFF6 chain pointer changes — per §7 "patch only your target").
"""
import os, sys, gzip, struct, zlib

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
OUT_DIR      = RWD_DIR
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"                      # comma/red-panda EPS target -> 0x18DA30F1

# v9b cipher ONLY (OPS: xor=0, add=3, sub=4)
V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- the two torque Y-axis lists (TORQUE_PATH_AND_TABLE.md §3c), 12 x int16 LE each ---
TORQUE_LISTS = {0xC4A42: 12, 0xC4A6E: 12}
MAIN_START, MAIN_END = 0x13000, 0xC4FFC   # main-block CRC region; stored CRC at MAIN_END


def read_int16le(buf, off, n):
    return [struct.unpack_from("<h", buf, off + 2 * i)[0] for i in range(n)]


def write_int16le(buf, off, vals):
    for i, v in enumerate(vals):
        if not (-32768 <= v <= 32767):
            raise ValueError(f"value {v} at index {i} (off 0x{off:X}) out of int16 range")
        struct.pack_into("<h", buf, off + 2 * i, v)


def linearize_and_scale(vals, factor):
    """Linear ramp start->end across len(vals) points (round-half-up to int base),
    then multiply every point by `factor` (exact integer scale)."""
    n = len(vals)
    start, end = vals[0], vals[-1]
    base = [round(start + (end - start) * i / (n - 1)) for i in range(n)]
    return base, [v * factor for v in base]


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


def build(label, factor, code_stock, headers):
    print("=" * 72)
    print(f"{label}: linearize + x{factor}   cipher v9b {V9B['desc']}")
    code = bytearray(code_stock)

    # 1) patch the two torque lists in place
    for off, n in TORQUE_LISTS.items():
        orig = read_int16le(code, off, n)
        base, scaled = linearize_and_scale(orig, factor)
        write_int16le(code, off, scaled)
        print(f"  0x{off:X} stock   : {orig}")
        print(f"  0x{off:X} linear  : {base}")
        print(f"  0x{off:X} x{factor} -> : {scaled}")

    # 2) recompute the MAIN-block CRC that covers [0x13000, 0xC4FFC) (the ONLY CRC affected)
    old = struct.unpack_from("<I", code, MAIN_END)[0]
    new = zlib.crc32(code[MAIN_START:MAIN_END]) & 0xFFFFFFFF
    struct.pack_into("<I", code, MAIN_END, new)
    print(f"  main-block CRC @0x{MAIN_END:X}: 0x{old:08X} -> 0x{new:08X} (recomputed)")

    # 3) encipher window with v9b, wrap x31 (raw &-key BF109E carried verbatim by template)
    dec = build_decode_table(V9B["keys"], V9B["ops"]); assert dec is not None
    enc = invert_table(dec)
    window  = bytes(code[START:END])
    payload = window.translate(enc)
    rwd = encode_x31(headers, [{"start": START, "length": END - START}], [payload])

    # 4) self-validate exactly as the ECU would: decode our payload, splice, CRC-walk
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label} x{factor}")
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")
    if not matches or fails:
        print(f"  *** {label} self-check FAILED — not writing ***\n")
        return None
    out = os.path.join(OUT_DIR, f"39990-TVA-A160-{label}-torque-linear-x{factor}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.basename(out)}\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  %=30 -> 0x18DA30F1\n")
    build("V10a", 2, code, headers)
    build("V10b", 3, code, headers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
