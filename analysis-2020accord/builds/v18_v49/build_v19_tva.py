"""builds/v18_v49/build_v19_tva.py — V19 HIGH-END LKAS 2x for the 2020 Accord (39990-TVA-A160).

GOAL: enable the full 2x LKAS torque to SURVIVE the high-end (hard driver-override /
sharp-turn) regime without the EME "snap" — by rescaling the authority-gate state
machines PROPORTIONALLY to the new 2x envelope, NOT by defeating them.

LINEAGE: V18 (road-validated, "drives well": 2x arb gain/clamps + override-debounce ramp
+ part-number string fix) PLUS exactly two more calibration halfwords that move the
override-snap state-machine arming gates to the 2x envelope.

============================ WHY THESE TWO BYTES ============================
The EME snap (whole-EPS momentary cut during hard mid-turn override) is THREE redundant
authority-gate state machines inside s_motor_torque_rate_shaper (FUN_00042af8), OR-linked
by a 3-way MIN. Each zeroes a Q15 authority node (0x8000=unity, 0=cut) when it "arms".
Verified 2026-05-29/30 (Trace A — instruction-level, 4-agent swarm + operator-directed
re-verification of the command-vs-velocity seed dispute):

  - All three arm off the COMMAND-magnitude path (command -> integrator gp-0x3570 ->
    uVar53/uVar34), NOT column velocity. This is WHY the EME is 2x-only: 2x command
    drives the integrator higher, crossing the gates that 1x sits just under.

  SM-arming thresholds (cal-addressable, tp=0xBF000):
    SM1  tp+0x71de = 0xC61DE = 2048    |cmd|>this AND col-velocity>tp+0x71e0(7168)
                                        AND command OPPOSES column motion (anti-oscillation)
    SM2  tp+0x7422 = 0xC6422 = 16384   |integrated cmd|*1092/1024 > this
    SM3  tp+0x71dc = 0xC61DC = 30720   integrator SATURATES (=its clamp=30720) for 20 cyc
                                        (30720 == 2 x 15360 stock full authority)

  At 1x full command uVar34 ~= 16380 (just under SM2's 16384 — matches the prior finding).
  At a clean 2x the integrator saturates at its 30720 clamp (= SM3 trip) and uVar34 -> ~32760
  (>> SM2's 16384). So a 2x build drives BOTH SM2 (crossed mid-range) and SM3 (crossed at
  peak). SM1 is velocity+opposition-gated and is NOT the 2x-only culprit, so it is LEFT STOCK.

THE EDIT (proportional rescale — preserves each monitor's RELATIVE trip point at 2x):
  0xC6422  tp+0x7422  SM2 gate            16384 (0x4000) -> 32768 (0xF... 0x8000)
  0xC61DC  tp+0x71dc  SM3 trip + integ.   30720 (0x7800) -> 61440 (0xF000)
                      clamp ceiling
  Arithmetic safety on 0xC61DC: the integrator clamp is uVar39*0x8000. At 0xF000:
  0xF000*0x8000 = 0x78000000 < INT32_MAX (0x7FFFFFFF) -> no overflow. Verified.

  This is NOT defeating the monitors: after the edit SM2 still trips at ~100% and SM3 at
  ~200% of the NEW (2x) authority — the same relative points as stock at 1x. The residual,
  inherent loosening (which the operator has explicitly accepted): a 2x LKAS command may now
  oppose column motion with 2x the ABSOLUTE torque for the same relative duration before the
  cut engages. You cannot have 2x authority AND a monitor that cuts at 1x torque.

============================ HONEST OPEN ITEMS ============================
  * COMMAND FULL-SCALE AMBIGUITY: a mode gate at decompile L651 caps the SM1 operand to
    +/-0x2000/0x3000 in modes 0/2. The "~15360 full-scale" reading (which makes the SM3
    edit NECESSARY at 2x) relies on the active LKAS mode bypassing that gate; the active
    mode value (FUN_000074c4[tp+4]) is NOT verified. If full-scale is actually ~8192, only
    0xC6422 is needed and the 0xC61DC edit is HARMLESS-BUT-UNNECESSARY (integrator never
    reaches 30720, so raising its clamp changes nothing). Including it is the conservative
    choice — necessary in one scenario, inert in the other.
  * WHICH SM FIRES in the real EME is NOT discriminated on-car (the gate is RAM-internal,
    invisible). A CAN 0x427 motor-torque + steering capture through one real EME is the
    recommended pre-flash discriminator (also pins the scale -> confirms if 0xC61DC needed).
  * SM-cal SHARED-CONSUMER CHECK: 0xC61DC is read as both the integrator clamp (L696) and
    SM3's trip; 0xC6422 only in SM2 (L980/L1000). No surprise external consumers expected
    (both live in the shaper SM region) but tp/gp-relative xrefs don't resolve in Ghidra.

WHAT V19 EDITS (on top of stock V9 code.bin):
  Calibration block #48 [0xC6000, 0xC6FFC) — halfwords (u16 LE):
    0xC646C  GAIN     tp+0x746c   891   -> 1782    (x2, from V14/V18)
    0xC61B4  CLAMP    tp+0x71b4   512   -> 1024    (x2, from V14/V18)
    0xC61B2  CLAMP    tp+0x71b2   512   -> 1024    (x2, from V14/V18)
    0xC6422  SM2 GATE tp+0x7422   16384 -> 32768   (NEW: high-end 2x — SM2 to 2x envelope)
    0xC61DC  SM3 TRIP tp+0x71dc   30720 -> 61440   (NEW: high-end 2x — SM3/integ to 2x env.)

  Calibration block #48 — single byte (u8):
    0xC64DE  RAMPSTEP tp+0x74de   0x11  -> 0x1B    (from V18: lengthens override re-engage)

  Part-number strings (main block [0x13000, 0xC4FFC)) — from V15B/V18:
    0x13109  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x13100)
    0x14120  '-' (0x2D) -> ',' (0x2C)   ('39990-TVA-A160'@0x14117)

  Two CRC blocks recomputed: block #48 @0xC6FFC ; main block @0xC4FFC.

STUDY ARTIFACT. No flash until the operator names the file + bus (kit iron rule).
Per the project rule on safety monitors, this build WIDENS anti-oscillation gates and was
produced only after explicit operator sign-off on the trade (2026-05-30).
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
    (0xC646C,   891,  1782, "GAIN     tp+0x746c  arb Q15 output gain   891->1782  (x2, V14/V18)"),
    (0xC61B4,   512,  1024, "CLAMP    tp+0x71b4  arb output clamp      512->1024  (x2, V14/V18)"),
    (0xC61B2,   512,  1024, "CLAMP    tp+0x71b2  limit&pack clamp      512->1024  (x2, V14/V18)"),
    (0xC6422, 16384, 32768, "SM2 GATE tp+0x7422  override-snap SM2 arm 16384->32768 (NEW high-end 2x)"),
    (0xC61DC, 30720, 61440, "SM3 TRIP tp+0x71dc  SM3 trip + integ clamp 30720->61440 (NEW high-end 2x)"),
]

# --- Calibration single-byte patches (block #48) ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (byte) [V18 EME]"),
]

# --- Part-number string byte patches (main block) ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits (2x + EME fix + SM-gate rescale)
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
    print(f"{label}: HIGH-END LKAS 2x (V18 base + SM2/SM3 gate rescale) + PN string   cipher v9b")
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
    print(f"baseline = V9 stock; edits = 5 cal halfwords + 1 cal byte + 2 PN string bytes")
    print(f"(V18 = 3 halfwords + 1 byte + 2 PN; V19 adds 2 SM-gate halfwords for high-end 2x)\n")
    build("V19", code, headers, tag="LKAS-2x-highend-SMgate-rescale-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
