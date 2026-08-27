"""builds/v18_v49/build_v23_tva.py — V23 = V18 lineage + integer envelope 2x (upper+lower) + PRECISE
float-monitor alignment (Option 1: double each firing FP cross-check's FP-side AT its
comparison). For the 2020 Accord (39990-TVA-A160).

THE PROBLEM (operator-confirmed mental model):
  The 2x output gain (V18, tp+0x746c) pushes the LKAS torque command above an integer
  envelope (LERP1->2->3 -> IIR state gp-0x3574 upper / gp-0x3578 lower). Exceedance
  accumulates -> staged thresholds -> EME. The fix is to 2x the envelope. But the firmware
  runs a FLOATING-POINT parallel monitor (FUN_00043e44) that cross-checks the integer
  runtime outputs against FP-recomputed values; doubling the integer envelope without
  matching the FP side makes those cross-checks diverge -> immediate startup fault.
  V21 doubled only the integer UPPER envelope. V22 added integer LOWER + a single FP cave
  doubling the FP IIR (gp-0x3554/3558) -- but the firing cross-checks compare against OTHER
  FP quantities (governor-clamped command, colw sensor, FP slew), which V22 left at 1x.
  V21 and V22 both fault immediately at startup.

V23 STRATEGY (Option 1 -- precise, keeps every cross-check intact):
  1. Integer envelope 2x: the three LERP3-output shl <<8 -> <<9 patches (V21 upper x2 +
     V22 lower x1). The lower envelope gp-0x3578 is INDEPENDENTLY computed (its own LERP
     target, IIR, bypass, store @0x42f4c) -- verified -- so it needs its own shl.
  2. Drop V22's 0xC4FC0 cave. Instead, double each STILL-MISMATCHED cross-check's FP-side
     register IMMEDIATELY BEFORE that check's comparison. Because nothing is pre-scaled,
     each FP value arrives at 1x and is doubled exactly once -> 2x, matching the 2x integer
     side. Transient-safe (both integer and FP envelopes ramp from 0 with the same IIR
     coeff; the x2 is applied to the final value at the compare).

  Cross-check inventory (FUN_00043e44, stock disasm-verified):
    bit 1  @0x4463a  subf.s r2,lp,r10   : int gp-0x6af6 (2x) vs FP lp        -> double lp
    bit 2  @0x44662  subf.s r9,r20,r12  : int gp-0x6b00 (2x) vs FP r20       -> double r20
    bit 4  @0x44784  subf.s r16,r10,r14 : int gp-0x6b0a (2x) vs FP r10(slew) -> double r10
    bit 32 @0x448a0  addf.s r8,r13,r12  : int gp-0x6b98 (2x) vs FP fVar23    -> double r12
                       (r12 is the FP command; double it BEFORE the governor+/-8 clamps at
                        0x448a4 so fVar23 = clamp(2*cmd,+-gov,+-8) mirrors gp-0x6b98 =
                        clamp(2*cmd,+-gov,+-0x2000). +-0x2000 == 8.0, same ceiling. Doubling
                        AFTER the +-8 clamp would overshoot to 16 vs gp-0x6b98 capped at 8.)
    bit 8  @0x447ba  : int gp-0x6b04 (2x) vs bounds r2/r9 = gp-0x6af6,gp-0x6b00 (also int 2x)
                       -> all-integer, scales together, PASSES, no fix.
    bits 16,64 : safe direction / independent, no fix (see review).

  Each fix is a 4-byte in-place jr hook (over the 4-byte compare instr) into a 12-byte cave:
     cave = [addf.s rX,rX,rX  (double FP side)] [displaced compare instr] [jr back].
  For bit 32 the displaced instr forms r12, so the cave order is
     [addf.s r8,r13,r12 (displaced)] [addf.s r12,r12,r12 (double)] [jr back].

WHAT V23 EDITS (on top of stock V9 code.bin):
  Cal block #48 [0xC6000,0xC6FFC) -- halfwords (V18 lineage):
    0xC646C GAIN  tp+0x746c 891->1782   ; 0xC61B4 CLAMP tp+0x71b4 512->1024
    0xC61B2 CLAMP tp+0x71b2 512->1024
  Cal block #48 -- byte (V18 lineage):
    0xC64DE RAMPSTEP tp+0x74de 0x11->0x1B
  Main block [0x13000,0xC4FFC) -- code bytes (integer envelope 2x):
    0x42DAE shl 0x8,r9  -> 0x9   (gp-0x3574 upper IIR)     C8->C9
    0x42DCA shl 0x8,r11 -> 0x9   (gp-0x3574 upper bypass)  C8->C9
    0x42F16 shl 0x8,r10 -> 0x9   (gp-0x3578 lower IIR+byp) C8->C9
  Main block -- code regions (FP cross-check alignment: 4 hooks + 4 caves @0xC4E00):
    0x4463a jr->cave1 ; 0x44662 jr->cave2 ; 0x44784 jr->cave3 ; 0x448a0 jr->cave4
    0xC4E00 cave1(bit1) 0xC4E0C cave2(bit2) 0xC4E18 cave3(bit4) 0xC4E24 cave4(bit32)
  Main block -- PN strings (V15B/V18):
    0x13109 '-'->',' ; 0x14120 '-'->','
  Two CRC blocks recomputed: #48 @0xC6FFC ; main @0xC4FFC.

ENCODING NOTES (hand-derived from in-image instances; RE-VERIFY by disassembling built bin):
  addf.s rX,rX,rX : HW0=(X<<11)|(0x3F<<5)|X, HW1=(X<<11)|0x460, LE halfwords.
    verified vs addf.s r8,r13,r12 @0x448a0 = e8 6f 60 64 and addf.s r16,r7,r16 @0x44296.
    lp(r31)=ff ff 60 fc ; r20=f4 a7 60 a4 ; r10=ea 57 60 54 ; r12=ec 67 60 64
  jr disp22 : HW0=0x0780|((disp>>16)&0x3F), HW1=disp&0xFFFF ; verified vs V22 0x44230->0xC4FC0.
  displaced compares (disasm-verified bytes):
    0x4463a subf.s r2,lp,r10  = e2 ff 62 54
    0x44662 subf.s r9,r20,r12 = e9 a7 62 64
    0x44784 subf.s r16,r10,r14= f0 57 62 74
    0x448a0 addf.s r8,r13,r12 = e8 6f 60 64

STUDY ARTIFACT. No flash until the operator names the file + bus (kit iron rule).
"""
# --- PATH BOOTSTRAP (repo reorg 2026-08-26; MULTI-ROOT FIX 2026-08-26) ----
# These files import sibling modules by bare name.  The kit has MORE THAN ONE
# import root (each marked by a `.pkgroot` file): `analysis-2020accord/` and
# `rlog-tools/`.  The original block stopped at the FIRST `.pkgroot` above the
# file, so a `rlog-tools/` script could not see `analysis-2020accord/lib/` and
# the whole extractor family died with `ModuleNotFoundError: _grind2_lib`.
# Fix: put EVERY kit root in the repo, and every code subfolder under each, on
# sys.path -- nearest root first, so local modules still win.
import os as _os, sys as _sys
_r = _os.path.dirname(_os.path.abspath(__file__))
while not _os.path.isfile(_os.path.join(_r, ".pkgroot")):
    _n = _os.path.dirname(_r)
    if _n == _r:
        raise RuntimeError("no .pkgroot marker above " + __file__)
    _r = _n
_repo = _r
while not _os.path.isdir(_os.path.join(_repo, ".git")):
    _n = _os.path.dirname(_repo)
    if _n == _repo:
        _repo = None
        break
    _repo = _n
_roots = [_r]
if _repo:
    for _e in sorted(_os.listdir(_repo)):
        _d = _os.path.join(_repo, _e)
        if _d != _r and _os.path.isfile(_os.path.join(_d, ".pkgroot")):
            _roots.append(_d)
_p = []
for _root in _roots:
    _p.append(_root)
    for _b, _ds, _fs in _os.walk(_root):
        _ds[:] = [_x for _x in _ds if not _x.startswith((".", "_")) and _x not in
                  ("rlogs", "ghidra_project", "__pycache__", "reference/opendbc")]
        _p.extend(_os.path.join(_b, _x) for _x in _ds)
_sys.path[:0] = [_x for _x in _p if _x not in _sys.path]
for _v in ("_os", "_sys", "_r", "_n", "_repo", "_roots", "_p", "_root",
           "_b", "_ds", "_fs", "_e", "_d", "_x", "_v"):
    globals().pop(_v, None)
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
BIN_OUT      = plain_image_path("_v23_plain_image.bin")
START, END   = 0x13000, 0x100000
CAN_SIG_BYTE = b"30"

V9B = dict(keys=(0xBF, 0x10, 0x9E), ops=(OPS[0], OPS[0], OPS[4]),
           desc="((c^0xBF)^0x10)-0x9E [xor,xor,sub]")

# --- Calibration halfword patches (block #48) -- V18 lineage ---
CAL_PATCHES = [
    (0xC646C,   891, 1782, "GAIN     tp+0x746c  arb Q15 output gain  891->1782 (x2, V18)"),
    (0xC61B4,   512, 1024, "CLAMP    tp+0x71b4  arb output clamp     512->1024 (x2, V18)"),
    (0xC61B2,   512, 1024, "CLAMP    tp+0x71b2  limit&pack clamp     512->1024 (x2, V18)"),
]

# --- Calibration single-byte patches (block #48) -- V18 lineage ---
CAL_BYTE_PATCHES = [
    (0xC64DE, 0x11, 0x1B, "RAMPSTEP tp+0x74de  re-engage ramp step  17->27 (V18 EME ramp)"),
]

# --- Code-section byte patches (main block) -- integer envelope 2x ---
CODE_BYTE_PATCHES = [
    (0x42DAE, 0xC8, 0xC9, "shl 0x8,r9  -> 0x9   [gp-0x3574 upper IIR]   (V21)"),
    (0x42DCA, 0xC8, 0xC9, "shl 0x8,r11 -> 0x9   [gp-0x3574 upper bypass] (V21)"),
    (0x42F16, 0xC8, 0xC9, "shl 0x8,r10 -> 0x9   [gp-0x3578 lower IIR+byp](V22)"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# ---------------------------------------------------------------------------
# FP cross-check alignment: 4 hooks (in-place 4B jr) + 4 caves (12B each).
# ---------------------------------------------------------------------------
CAVE_BASE = 0xC4E00

def jr(frm, to):
    """4-byte V850 jr disp22 from `frm` to `to`."""
    disp = (to - frm) & 0xFFFFFFFF
    hw0 = 0x0780 | ((disp >> 16) & 0x3F)
    hw1 = disp & 0xFFFF
    return struct.pack("<HH", hw0, hw1)

# (name, hook_addr, displaced_bytes, double_bytes, double_first)
#   double_first=True  -> cave = [double][displaced][jr]   (bits 1,2,4: double the FP
#                          operand that the displaced compare reads)
#   double_first=False -> cave = [displaced][double][jr]   (bit 32: displaced forms r12,
#                          then we double r12 before returning into the clamp chain)
ADDF = {  # addf.s rX,rX,rX  (rX *= 2)
    "lp":  bytes.fromhex("ffff60fc"),   # r31
    "r20": bytes.fromhex("f4a760a4"),
    "r10": bytes.fromhex("ea576054"),
    "r12": bytes.fromhex("ec676064"),
}
FIX = [
    ("bit1",  0x4463A, bytes.fromhex("e2ff6254"), ADDF["lp"],  True),   # subf.s r2,lp,r10
    ("bit2",  0x44662, bytes.fromhex("e9a76264"), ADDF["r20"], True),   # subf.s r9,r20,r12
    ("bit4",  0x44784, bytes.fromhex("f0576274"), ADDF["r10"], True),   # subf.s r16,r10,r14
    ("bit32", 0x448A0, bytes.fromhex("e86f6064"), ADDF["r12"], False),  # addf.s r8,r13,r12
]

def build_caves():
    """Return (code_region_patches, cave_blob_at_base). Each patch is
    (addr, expected_old, new, note)."""
    patches = []
    cave_addr = CAVE_BASE
    cave_blob = bytearray()
    for name, hook, disp, dbl, dbl_first in FIX:
        body = (dbl + disp) if dbl_first else (disp + dbl)
        ret  = hook + 4                       # return to instruction after the displaced one
        cave = body + jr(cave_addr + len(body), ret)
        assert len(cave) == 12, f"{name} cave len {len(cave)}"
        # cave write (expect free 0xFF padding)
        patches.append((cave_addr, b"\xff" * len(cave), bytes(cave),
                        f"CAVE {name} @0x{cave_addr:05X}  double+displaced+jr->0x{ret:05X}"))
        # hook write (expect the original compare instruction)
        patches.append((hook, disp, jr(hook, cave_addr),
                        f"HOOK {name} @0x{hook:05X}  jr->0x{cave_addr:05X} (was {disp.hex()})"))
        cave_blob += cave
        cave_addr += len(cave)
    return patches, bytes(cave_blob)

CODE_REGION_PATCHES, _ = build_caves()

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 -- calibration
    (0x13000, 0xC4FFC),  # main block -- code bytes + caves/hooks + PN
]


def patch_cal(code):
    for addr, cur, new, note in CAL_PATCHES:
        got = struct.unpack_from("<H", code, addr)[0]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#06x} got {got:#06x} ({note})")
        struct.pack_into("<H", code, addr, new)
        print(f"  0x{addr:05X}: {cur:6d} -> {new:6d}   {note}")


def patch_bytes(code, table):
    for addr, cur, new, note in table:
        got = code[addr]
        if got != cur:
            raise AssertionError(f"0x{addr:05X}: expected {cur:#04x} got {got:#04x} ({note})")
        code[addr] = new
        print(f"  0x{addr:05X}:   {cur:#04x} -> {new:#04x}   {note}")


def patch_regions(code, table):
    for addr, old, new, note in table:
        assert len(old) == len(new), f"region len mismatch @0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(f"0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}:   {old.hex()} -> {new.hex()}   {note}")


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
    print(f"{label}: V18 lineage + integer env 2x (3 shl) + 4 FP-checks aligned (caves)")
    code = bytearray(code_stock)

    patch_cal(code)
    patch_bytes(code, CAL_BYTE_PATCHES)
    patch_bytes(code, CODE_BYTE_PATCHES)
    patch_regions(code, CODE_REGION_PATCHES)
    patch_bytes(code, PN_PATCHES)
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

    # lineage / patch readback
    assert struct.unpack_from("<H", ecu_plain, 0xC646C - START)[0] == 1782, "GAIN lost"
    assert ecu_plain[0xC64DE - START] == 0x1B, "RAMPSTEP lost"
    for a in (0x42DAE, 0x42DCA, 0x42F16):
        assert ecu_plain[a - START] == 0xC9, f"shl @0x{a:X} lost"
    for name, hook, disp, dbl, dbl_first in FIX:
        assert bytes(ecu_plain[hook - START:hook - START + 4]) == jr(hook,
            CAVE_BASE + [f[0] for f in FIX].index(name) * 12), f"hook {name} lost"
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
    print(f"baseline = V9 stock; V23 = V18 lineage + 3 shl + 4 FP-check caves\n")
    build("V23", code, headers, tag="LKAS-2x-EMEfix-intenv2x-FPalign4-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
