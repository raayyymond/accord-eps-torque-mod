"""build_v15b_tva.py — V15B LKAS 2x-torque build for the 2020 Accord (39990-TVA,A160).

LINEAGE: identical to V15A except that it also patches the two occurrences of the
part-number string '39990-TVA-A160' that live inside the firmware payload itself
(found at abs 0x13100 and 0x14117 in code.bin).  V15A only changed the x31 header's
'/' tag; the ECU's UDS DID readback (0x22 F18C / 0x22 F100) comes from the embedded
firmware strings, not the RWD header — so V15A still reported the old hyphen PN.

WHAT V15B EDITS (on top of V14 calibration patches):
  Calibration (block #48 [0xC6000, 0xC6FFC)):
    0xC646C  GAIN  tp+0x746c  891  -> 1782  (x2)
    0xC61B4  CLAMP tp+0x71b4  512  -> 1024  (x2)
    0xC61B2  CLAMP tp+0x71b2  512  -> 1024  (x2)

  Part-number strings (main block [0x13000, 0xC4FFC)):
    0x13109  byte 9 of '39990-TVA-A160'  0x2D ('-') -> 0x2C (',')
    0x14120  byte 9 of '39990-TVA-A160'  0x2D ('-') -> 0x2C (',')
    (both become '39990-TVA,A160')

  Two CRC blocks recomputed:
    block #48  [0xC6000, 0xC6FFC)  CRC @0xC6FFC
    main block [0x13000, 0xC4FFC)  CRC @0xC4FFC

STUDY ARTIFACT.  No flash until the operator names the file + bus (kit iron rule).
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
OUT_DIR      = RWD_DIR
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- Calibration halfword patches (block #48) ---
CAL_PATCHES = [
    (0xC646C, 891,  1782, "GAIN  tp+0x746c  arb Q15 output gain  891->1782 (x2)"),
    (0xC61B4, 512,  1024, "CLAMP tp+0x71b4  arb output clamp      512->1024 (x2)"),
    (0xC61B2, 512,  1024, "CLAMP tp+0x71b2  limit&pack clamp      512->1024 (x2)"),
]

# --- Part-number string byte patches (main block) ---
# '39990-TVA-A160': byte index 9 is the '-' between TVA and A160.
# 0x13109 = 0x13100 + 9,  0x14120 = 0x14117 + 9
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# Block CRC recomputation: (block_start, crc_offset)
TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits
    (0x13000, 0xC4FFC),  # main block — part-number string edits
]


def patch_cal(code):
    for addr, cur, new, note in CAL_PATCHES:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:5d} ({cur:#06x}) -> {new:5d} ({new:#06x})   {note}")


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
    print("=" * 74)
    print(f"{label}: LKAS 2x + PN string fix   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code)
    patch_pn(code)
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
    csum = struct.unpack("<I", rwd[-4:])[0]
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw)")
    print(f"  ECU-decode==patched code: {matches}   CRC blocks failing: {fails}")
    print(f"  rwd size 0x{len(rwd):X}  trailer csum 0x{csum:08X}")

    # extra: confirm PN strings in decrypted payload
    pn_old = b"39990-TVA-A160"
    pn_new = b"39990-TVA,A160"
    print(f"  old PN in payload: {ecu_plain.count(pn_old)}   new PN in payload: {ecu_plain.count(pn_new)}")

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
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  %=30 -> 0x18DA30F1")
    print(f"baseline = V9 stock; edits = 3 cal halfwords + 2 PN string bytes\n")
    build("V15B", code, headers, tag="LKAS-2x-arbgain-clamps-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
