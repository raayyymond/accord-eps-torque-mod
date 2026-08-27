"""builds/v18_v49/build_v18_tva.py — V18 LKAS 2x + EME (driver-override dropout) FIX for the 2020 Accord (39990-TVA,A160).

LINEAGE: V15B (2x arb gain/clamps + part-number string fix) PLUS the EME RAMP-ONLY fix.
Following multi-analyst confirmation, the 'slew' and 'deadband' changes from V16/V17 were discarded:
the slew edit activates dangerous dormant code, and the deadband edit is mathematically inert without the slew. 

Because the operator strongly rejected a 1.5x gain backoff and demands the full 2.0x LKAS torque preserved,
the only remaining logically sound, on-path lever to directly mitigate the EME dropout is the override-debounce ramp.
Modifying `0xC64DE: 0x11 -> 0x1B` correctly increases the ramp threshold (17 -> 27). This softens and 
LENGTHENS the re-engagement transition, aiming to cushion the snap during an aggressive driver-override state.

WHAT V18 EDITS (on top of stock V9 code.bin):
  Calibration block #48 [0xC6000, 0xC6FFC) — halfwords (u16 LE):
    0xC646C  GAIN     tp+0x746c   891   -> 1782   (x2, from V14/V15)
    0xC61B4  CLAMP    tp+0x71b4   512   -> 1024   (x2, from V14/V15)
    0xC61B2  CLAMP    tp+0x71b2   512   -> 1024   (x2, from V14/V15)
  
  Calibration block #48 — single byte (u8):
    0xC64DE  RAMPSTEP tp+0x74de   0x11  -> 0x1B   (NEW: 17->27, LENGTHENS override re-engage ramp)

  Part-number strings (main block [0x13000, 0xC4FFC)) — from V15B:
    0x13109  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x13100)
    0x14120  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x14117)

  Two CRC blocks recomputed: block #48 @0xC6FFC ; main block @0xC4FFC.

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

# --- Calibration halfword patches (block #48) ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2)"),
]

# --- Calibration single-byte patches (block #48) ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (byte) [EME]"),
]

# --- Part-number string byte patches (main block) ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits (2x + EME fix)
    (0x13000, 0xC4FFC),  # main block — part-number string edits
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
    print(f"{label}: LKAS 2x + EME RAMP-ONLY fix + PN string   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code)
    patch_cal_bytes(code)
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
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})")
    print(f"baseline = V9 stock; edits = 3 cal halfwords + 1 cal byte + 2 PN string bytes\n")
    build("V18", code, headers, tag="LKAS-2x-EMEfix-ramponly-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
