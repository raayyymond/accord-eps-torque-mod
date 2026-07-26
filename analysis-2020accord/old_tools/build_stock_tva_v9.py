"""build_stock_tva_v9.py — two cipher-variant stock-recovery candidates.

V8 failed at checkProgrammingDependencies (NRC 0x72). Root cause established:
V8's encode cipher did NOT match the V850-family on-ECU decryptor, so the ECU
decrypted V8's payload to garbage and the per-block CRC-32 chain failed.

V8 used (the now-disproven) ((c - 0xBF) + 0x10) ^ 0x9E  [sub,add,xor / keys BF,10,9E].
Do NOT rebuild that — it is already known wrong.

This builds the two remaining cipher hypotheses, SAME window [0x13000,0x100000),
SAME written &-key BF109E (raw bytes the ECU reads into k0,k1,k2). Only the
encode arithmetic differs:

  v9a  T2F-file cipher (cracked from genuine 39990-T2F-A210.rwd, reveals its
       part number):           decode = ((c - 0x9E) + 0xBF) ^ 0x10   [sub,add,xor]
  v9b  TVA-ECU-disasm cipher (FUN_0xB35E in code.bin, the resident decryptor
       actually invoked by TransferData):
                               decode = ((c ^ 0xBF) ^ 0x10) - 0x9E   [xor,xor,sub]

v9b is the favored hypothesis (it is the literal resident decryptor for written
key BF109E); v9a covers the case where the real decode matches the T2F family
file rather than the resident FUN_0xB35E (e.g. RAM-kernel override).

Each candidate is verified by: decode its own payload with its assumed ECU
decoder, splice into a 1 MB image, and replay the bootloader CRC-32 walk
(verify_bootloader_crc.walk). A correct candidate yields 49/49 CRC blocks PASS.
"""
import os, sys, gzip, struct

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
CHUNK        = 128
START, END   = 0x13000, 0x100000

# --- TVA x31 header construction (inlined; was build_stock_tva_v8) ---
CAN_SIG_BYTE = b"30"            # comma/red-panda EPS target -> 0x18DA30F1
EXPECT_CAN   = 0x18DA30F1


def make_tva_headers(template_info):
    """Copy #/?/& verbatim from a genuine V850 template; substitute /, !, %.
      /  -> [A110, A160]   (both part numbers; sibling-family two-version convention)
      !  -> mirrored Group A marker (vestigial on V850; not the SA secret)
      %  -> 30              (comma CAN 0x18DA30F1)
    """
    new_headers = []
    for tag, vals in template_info["headers"]:
        if tag == b"/":
            new_headers.append((tag, [b"39990-TVA-A110", b"39990-TVA-A160"]))
        elif tag == b"!":
            new_headers.append((tag, [vals[0], vals[0]]))
        elif tag == b"%":
            new_headers.append((tag, [CAN_SIG_BYTE]))
        else:
            new_headers.append((tag, list(vals)))
    return new_headers


def can_addr(sig_bytes):
    return 0x18DA00F1 | (int(sig_bytes.decode("ascii"), 16) << 8)

# ops index map: OPS = [xor,and,or,add,sub,mul,floordiv,mod] -> xor=0 add=3 sub=4
VARIANTS = {
    "v9a": dict(keys=(0x9E, 0xBF, 0x10), ops=(OPS[4], OPS[3], OPS[0]),
                desc="T2F-file cipher  ((c-0x9E)+0xBF)^0x10   [sub,add,xor]"),
    "v9b": dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
                desc="TVA-ECU-disasm   ((c^0xBF)^0x10)-0x9E   [xor,xor,sub]"),
}


def full_image(plain_window):
    img = bytearray(b"\xff" * 0x100000)
    img[START:END] = plain_window
    return bytes(img)


def build(label, code, headers):
    v = VARIANTS[label]
    dec = build_decode_table(v["keys"], v["ops"])          # the ECU decoder hypothesis
    assert dec is not None, f"{label}: cipher non-bijective"
    enc = invert_table(dec)
    window = code[START:END]
    payload = window.translate(enc)

    blocks = [{"start": START, "length": END - START}]
    rwd = encode_x31(headers, blocks, [payload])

    # --- verify: decode the payload AS THE ECU WOULD, then CRC-walk it ---
    info = parse_x31(rwd)
    ecu_plain = bytes(info["encs"][0]).translate(dec)
    matches_code = ecu_plain == window
    fails = walk(full_image(ecu_plain), label=f"{label} ({v['desc']})")

    csum = struct.unpack("<I", rwd[-4:])[0]
    out = os.path.join(OUT_DIR, f"39990-TVA-A160-RECONSTRUCTED-{label}-0x{START:X}-0x{END:X}.rwd")
    print(f"  cipher          : {v['desc']}")
    print(f"  &-key written   : {bytes(info['key']).hex().upper()} (raw, unchanged)")
    print(f"  ECU-decode==code: {matches_code}    CRC blocks failing: {fails}")
    print(f"  rwd size        : 0x{len(rwd):X}  trailer csum 0x{csum:08X}")
    if not matches_code or fails:
        print(f"  *** {label} self-check FAILED — not writing ***")
        return None
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.basename(out)}")
    return out, payload


def main():
    code = open(CODE_BIN, "rb").read()
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  "
          f"CAN 0x{can_addr(CAN_SIG_BYTE):08X}\n")

    results = {}
    for label in ("v9a", "v9b"):
        print("=" * 72)
        r = build(label, code, headers)
        if r:
            results[label] = r[1]
        print()

    # sanity: the two payloads must differ from each other (different ciphers)
    if "v9a" in results and "v9b" in results:
        same = results["v9a"] == results["v9b"]
        print(f"v9a payload == v9b payload : {same}  (expected False — distinct ciphers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
