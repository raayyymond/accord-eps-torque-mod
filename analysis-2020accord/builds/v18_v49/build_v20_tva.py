"""builds/v18_v49/build_v20_tva.py — V20A / V20B HIGH-END LKAS for the 2020 Accord (39990-TVA-A160).

Two SM-gate variants in the V19 lineage. Both push the override-snap authority
state-machine arming thresholds further out so a high-end (>2x) LKAS command survives
longer before the EME "snap" cut.

  V20A = V19 lineage + SM3 arm 61440 -> 65535 (0xFFFF, architectural max). SM2 left at V19 (32768).
  V20B = V19 lineage + SM3 arm 61440 -> 65535  AND  SM2 arm 32768 -> 49152 (3x of stock 16384).

Both are built FROM STOCK code.bin (same flow as build_v18/v19_tva.py) — NOT by decoding a
prior .rwd. From stock the full V19 lineage plus the V20 delta is applied in one pass:

  cal halfwords (block #48): GAIN 891->1782, CLAMP 512->1024 (x2),
      SM2 16384->{32768 V20A | 49152 V20B}, SM3 30720->65535
  cal byte (block #48):      RAMPSTEP 0x11->0x1B (override re-engage ramp, from V18)
  PN strings (main block):   '39990-TVA-A160' -> '39990-TVA,A160' (x2, from V15B/V18)

================================ WHY 0xFFFF IS THE SM3 CEILING (verified 2026-05-30) ===========
tp+0x71dc (flash 0xC61DC) is SIMULTANEOUSLY the monitor-integrator clamp AND SM3's trip
threshold (s_motor_torque_rate_shaper / FUN_00042af8). Constraints:
  * 16-bit field, loaded ld.hu  -> hard max 0xFFFF = 65535.
  * clamp arithmetic is cal<<15: 65535<<15 = 0x7FFF8000, still positive int32 (no signed
    overflow). 0x10000<<15 would be 0x80000000 = negative -> would invert the clamp. So 0xFFFF
    is the true maximum; you cannot go higher in this field.
  * SM3 compares uVar53 (=|integ>>15|) DIRECTLY to the cal, so 0xFFFF is coherent FOR SM3.
SM3 at 0xFFFF means: in the SM3 sense the monitor effectively never trips on wind-up alone
(the integrator can never exceed its own clamp), i.e. SM3 is pushed to its weakest setting.

================================ THE SM2 uVar34 WRAP CAVEAT (do not trip over this) ============
SM2 does NOT compare uVar53 directly. It compares uVar34 = (uVar53*1092)>>10, TRUNCATED to
16 bits (zxh). uVar34 wraps once uVar53 > ~61454. V19's SM3 clamp of 61440 sat JUST below the
wrap on purpose. With SM3 now at 65535 the integrator CAN reach the wrap zone (uVar53 in
61455..65535 -> uVar34 wraps to a SMALL value). That matters ONLY to SM2. In both variants SM2
arms FAR below the wrap:
   V20A SM2=32768 -> arms at uVar53 ~ 30728   (<< 61454, binds first; wrap zone never decides)
   V20B SM2=49152 -> arms at uVar53 ~ 46091   (<< 61454, still coherent)
So in BOTH builds SM2 is the FIRST monitor to cut, and the wrap zone is never the operative
regime. (If a future build raised SM2 above ~49152 toward the wrap, re-analyze: a too-high SM2
could wrap and become incoherent. 49152 is safe; that is the practical SM2 ceiling for 3x.)
Verified: reference/firmware/reference_accord_override_snap_state_machines.md.

================================ EXPECTED EFFECT (analyst note, NOT a guarantee) ===============
  V20A: SM2 unchanged at 32768 -> SM2 still arms first (~uVar53 30728). Raising SM3 to its max
        is therefore expected to be LARGELY INERT vs V19 in normal driving: the cut that V19
        gets from SM2 still happens at the same point. V20A is the controlled "isolate SM3"
        experiment - if it feels identical to V19, that confirms SM2 (not SM3) is the binding
        monitor on-car. If it feels different, SM3 was contributing.
  V20B: SM2 raised to 49152 (3x of stock 16384) AND SM3 maxed. This is the actual "3x" gate
        set - both shaper wind-up monitors pushed to ~3x / max. Expected to let a 3x-magnitude
        sustained command run substantially longer (or indefinitely below ~uVar53 46091) before
        any shaper cut. This is a REAL loosening of an anti-oscillation / runaway guard.

SAFETY (kit iron rule): both builds WIDEN safety monitors. Build only; the operator explicitly
requested these on 2026-05-30. NO FLASH until the operator names the exact file + bus, repeated
back first. SM1 is left STOCK in both (it is velocity+opposition-gated, not the 2x/3x-magnitude
culprit). The envelope LERP lever was DECLINED this session (high-velocity tail unresolved).

STUDY ARTIFACT. Per the project rule on safety monitors, this build WIDENS anti-oscillation
gates and was produced only after explicit operator sign-off on the trade (2026-05-30).

Usage:  python builds/v18_v49/build_v20_tva.py
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

# --- Per-variant calibration halfword patches (block #48), expected_old verified vs stock V9 ---
# Both variants carry the full V19 lineage (GAIN/CLAMP x2 + SM2 + SM3) applied directly from
# stock; the V20 delta is SM3 -> 65535 (both) and, for V20B, SM2 -> 49152.
VARIANTS = {
    "V20A": dict(
        tag="LKAS-2x-highend-SM3max-PNfix",
        desc="V19 high-end 2x + SM3 arm 30720->65535 (0xFFFF max); SM2 at V19 32768",
        cal=[
            (0xC646C,   891,  1782, "GAIN     tp+0x746c  arb Q15 output gain   891->1782   (x2, V14/V18/V19)"),
            (0xC61B4,   512,  1024, "CLAMP    tp+0x71b4  arb output clamp      512->1024   (x2, V14/V18/V19)"),
            (0xC61B2,   512,  1024, "CLAMP    tp+0x71b2  limit&pack clamp      512->1024   (x2, V14/V18/V19)"),
            (0xC6422, 16384, 32768, "SM2 GATE tp+0x7422  override-snap SM2 arm 16384->32768 (V19 high-end 2x)"),
            (0xC61DC, 30720, 65535, "SM3 TRIP tp+0x71dc  SM3 trip + integ clamp 30720->65535 (V20 0xFFFF max)"),
        ],
    ),
    "V20B": dict(
        tag="LKAS-2x-highend-SM3max-SM2x3-PNfix",
        desc="V19 high-end 2x + SM3 arm 30720->65535 (max) + SM2 arm 16384->49152 (3x of stock)",
        cal=[
            (0xC646C,   891,  1782, "GAIN     tp+0x746c  arb Q15 output gain   891->1782   (x2, V14/V18/V19)"),
            (0xC61B4,   512,  1024, "CLAMP    tp+0x71b4  arb output clamp      512->1024   (x2, V14/V18/V19)"),
            (0xC61B2,   512,  1024, "CLAMP    tp+0x71b2  limit&pack clamp      512->1024   (x2, V14/V18/V19)"),
            (0xC6422, 16384, 49152, "SM2 GATE tp+0x7422  override-snap SM2 arm 16384->49152 (V20B 3x of stock)"),
            (0xC61DC, 30720, 65535, "SM3 TRIP tp+0x71dc  SM3 trip + integ clamp 30720->65535 (V20 0xFFFF max)"),
        ],
    ),
}

# --- Calibration single-byte patch (block #48), common to both variants (from V18) ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (byte) [V18 EME]"),
]

# --- Part-number string byte patches (main block), common to both variants (from V15B/V18) ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits (2x + EME fix + SM-gate rescale/max)
    (0x13000, 0xC4FFC),  # main block — part-number string edits
]


def patch_cal(code, cal_patches):
    for addr, cur, new, note in cal_patches:
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


def build(label, spec, code_stock, headers):
    print("=" * 78)
    print(f"{label}: {spec['desc']}   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code, spec["cal"])
    patch_cal_bytes(code)
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

    # lineage / intent readback from the re-decoded payload
    want = {addr: new for addr, _old, new, _n in spec["cal"]}
    sm2  = struct.unpack_from("<H", ecu_plain, 0xC6422 - START)[0]
    sm3  = struct.unpack_from("<H", ecu_plain, 0xC61DC - START)[0]
    gain = struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0]
    assert sm2 == want[0xC6422], f"SM2 readback {sm2} != intended {want[0xC6422]}"
    assert sm3 == want[0xC61DC] == 0xFFFF, f"SM3 readback {sm3} != 0xFFFF max"
    assert gain == 1782, "GAIN lineage lost (expected 1782)"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lineage lost (expected 0x1B)"
    print(f"  lineage OK: GAIN={gain}  SM2={sm2} (0x{sm2:04X})  SM3={sm3} (0x{sm3:04X})  RAMPSTEP=0x1B")

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
    out = os.path.join(OUT_DIR, f"39990-TVA,A160-{label}-{spec['tag']}-0x{START:X}-0x{END:X}.rwd")
    with open(out, "wb") as f:
        f.write(rwd)
    print(f"  WROTE {os.path.relpath(out, REPO)}\n")
    return out


def main():
    code = open(CODE_BIN, "rb").read()
    assert len(code) == 0x100000, f"code.bin must be 1 MB, got 0x{len(code):X}"
    template_info = parse_x31(gzip.decompress(open(TEMPLATE_T2F, "rb").read()))
    headers = make_tva_headers(template_info)
    print(f"code.bin 0x{len(code):X}  window [0x{START:X},0x{END:X})  (built from stock, not from a prior .rwd)")
    print(f"baseline = V9 stock; both variants = V19 lineage (5 cal halfwords + 1 cal byte + 2 PN)")
    print(f"V20 delta over V19: SM3 -> 65535 (0xFFFF max) [both]; V20B also SM2 -> 49152 (3x)\n")
    build("V20A", VARIANTS["V20A"], code, headers)
    build("V20B", VARIANTS["V20B"], code, headers)
    print("Both V20 builds complete. UNFLASHED. Name file+bus explicitly to flash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
