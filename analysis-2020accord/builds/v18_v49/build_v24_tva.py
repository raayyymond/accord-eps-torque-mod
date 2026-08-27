"""builds/v18_v49/build_v24_tva.py — V24 = the OPTION-2 fix for the 2020 Accord (39990-TVA-A160).

WHY V24 EXISTS (the V21/V22/V23 failure, now fully characterized):
  V18 doubled the LKAS output gain (tp+0x746c 891->1782). To stop the resulting
  envelope-exceedance EME, V21+ doubled the INTEGER torque envelope (LERP3 output
  shl 0x8 -> 0x9 at 0x42DAE/0x42DCA upper, 0x42F16 lower). But the firmware cross-checks
  the integer envelope against a FLOATING-POINT twin every 1 kHz cycle with a FIXED +-5 LSB
  window, in TWO places:
    (A) INLINE in the rate-shaper FUN_00042af8 @0x43172-0x431c0:
          upper: |trunc(float[gp-0x6db0]*1024) - int16[gp-0x6af6]| > 5  -> fault (sp+0x30)
          lower: |trunc(float[gp-0x6db8]*1024) - int16[gp-0x6b00]| > 5  -> fault code 2 (sp+0x18)
        gp-0x6af6/gp-0x6b00 = de-scaled (sar 0x8) integer envelope IIR gp-0x3574/gp-0x3578.
        gp-0x6db0/gp-0x6db8 = FP envelope twins, written ONLY by FUN_00043e44
        (st.w lp,-0x6db0[gp] @0x449f4 ; st.w r20,-0x6db8[gp] @0x44a30), read ONLY here.
    (B) FUN_00043e44 weighted-bit monitor, bits 1 & 2 (envelope) @0x4463a/0x44662:
          bit1: |lp - float(gp-0x6af6)/1024| > 5/1024 ; bit2: |r20 - float(gp-0x6b00)/1024| > 5/1024
        (bits 4/8/32 are COMMAND-domain -- already 2x from the V18 gain, and ran fine in V18 --
         so they are NOT touched here. V23's caves on bit4/bit32 were WRONG: they doubled an
         already-2x command FP value -> 4x vs 2x -> they introduced failures. DROPPED in V24.)

  THE STRUCTURAL FACT (emulation-confirmed): doubling the envelope makes BOTH operands of
  these checks ~2x, so the absolute FP-vs-integer rounding discrepancy ALSO doubles:
        v24_diff = trunc(2F*1024) - 2S = 2*(trunc(F*1024) - S) = 2*stock_diff (+- 1 LSB rounding)
  The +-5 window is fixed, so the effective tolerance halves to +-2.5 LSB and the check trips
  once the routine rounding divergence reaches >=3 LSB. V23 proved Option 1 (align the paths)
  cannot work: V23 DID double both FP twins (caves 1&2; cold-verified lp/r20 live-unchanged to
  their stores) and STILL faults -- because alignment cannot beat a fixed absolute tolerance
  that scales against you. Hence Option 2: WIDEN the tolerance.

V24 STRATEGY (Option 2 -- minimal, bounded-safe):
  1. Keep V18 cal lineage (gain/clamps/RAMPSTEP) + PN.
  2. Keep integer envelope 2x: shl 0x9 at 0x42DAE/0x42DCA/0x42F16.
  3. Keep ONLY caves 1 & 2 (double lp@0x4463a -> gp-0x6db0 ; double r20@0x44662 -> gp-0x6db8).
     These double the FP twins so they track the 2x integer shadow; required for check (A) to be
     satisfiable at all, and they also set the FP side of bit1/bit2 in (B). DROP caves 3 & 4.
  4. (A) inline envelope check -- NEUTRALIZED (NOT a +-15 widen; see note below).
        cmp imm5 SIGN-EXTENDS, so 0xb->0x1f is NOT cmp 31, it is cmp -1 (=0xFFFFFFFF). The check
        is an UNSIGNED range test, so comparing against 0xFFFFFFFF forces "always in range" via the
        firmware's native no-fault path (zero clobber risk). addi 0x5->0xf shifts the single
        residual fault point to diff == -16 (a gross >15 LSB divergence that never occurs normally).
        Net: (A) is silent for all realistic diffs. Edits: 0x43190/0x431b4 addi 0x5->0xf ;
        0x43196/0x431b6 cmp 0xb->0x1f (the only symmetric window cmp imm5 can express is +-7,
        < the ~+-11 the 2x discrepancy needs, so a real +-15 widen of (A) is impossible in-place).
     (B) bit1/bit2 float threshold 5/1024 (0x3ba00000) -> 15/1024 (0x3c700000) -- TRUE +-15 widen:
            0x44640 movhi imm hi 0x3ba0->0x3c70 (positive bound r7; shared, also loosens the
                    POSITIVE side of bits 4/8/32 -- harmless, more permissive only);
            0x44648 movhi imm -0x4460->-(15/1024) i.e. 0xbba0->0xbc70 (bit1 negative bound);
            0x4466c same 0xbba0->0xbc70 (bit2 negative bound).
     (B) bit1/bit2 ARE the same envelope comparison as (A) upper/lower, scaled by 1024
     (twin vs integer shadow). So "(A) neutralized + (B) at +-15/1024" = the envelope-divergence
     check now lives at a true +-15 in the (B) instance; (A) is the redundant inline copy, retired.
     Why +-15 on (B): v24_diff = 2*stock_diff +- rounding <= 2*5+1 = 11; +-15 covers it w/ margin.

WHAT V24 EDITS (on top of stock V9 code.bin):
  Cal block #48 [0xC6000,0xC6FFC) -- V18 lineage:
    0xC646C GAIN 891->1782 ; 0xC61B4 CLAMP 512->1024 ; 0xC61B2 CLAMP 512->1024 ; 0xC64DE RAMPSTEP 0x11->0x1B
  Main block [0x13000,0xC4FFC):
    integer envelope 2x:  0x42DAE / 0x42DCA / 0x42F16  C8->C9
    neutralize inline (A):0x43190 05->0f ; 0x43196 6b->7f ; 0x431B4 05->0f ; 0x431B6 6b->7f
                          (cmp 0x1f = cmp -1 -> unsigned always-in-range; addi 0xf -> residual pt -16)
    tol-widen bits (B):   0x44640 a0->70 ; 0x44641 3b->3c ; 0x44648 a0->70 ; 0x44649 bb->bc ;
                          0x4466C a0->70 ; 0x4466D bb->bc
    FP-twin caves 1&2:    hook 0x4463A->cave1@0xC4E00 ; hook 0x44662->cave2@0xC4E0C
    PN strings:           0x13109 / 0x14120  '-'->','
  CRC: block #48 @0xC6FFC ; main @0xC4FFC.

ENCODING NOTES (all verified by disassembling code.bin in Ghidra this session):
  inline upper @0x4318e `addi 0x5,r12,r15` = 0c7e0500 ; @0x43196 `cmp 0xb,r15` = 6b7a
  inline lower @0x431b2 `addi 0x5,r10,r6`  = 0a360500 ; @0x431b6 `cmp 0xb,r6`  = 6b32
    addi imm16 0x5->0xf : low imm byte 0x05->0x0f at instr+2 (0x43190 / 0x431b4).
    cmp imm5 0xb->0x1f  : byte[0] 0x6b->0x7f (imm5 in bits[4:0]: 01011->11111) at 0x43196/0x431b6.
  bit1 thresh @0x4463e `movhi 0x3ba0,r0,r7` = 403ea03b (imm hw @0x44640 = 0x3ba0)
  bit1 neg   @0x44646 `movhi -0x4460,r0,r14`= 4076a0bb (imm hw @0x44648 = 0xbba0)
  bit2 neg   @0x4466a `movhi -0x4460,r0,r16`= 4086a0bb (imm hw @0x4466c = 0xbba0)
    5/1024  = 0x3ba00000 ; -5/1024  = 0xbba00000
    15/1024 = 0x3c700000 ; -15/1024 = 0xbc700000  (imm hw 0x3c70 / 0xbc70)
  addf.s rX,rX,rX : lp(r31)=ffff60fc ; r20=f4a760a4  (verified vs in-image addf.s instances)
  jr disp22 : HW0=0x0780|((disp>>16)&0x3F), HW1=disp&0xFFFF.
  displaced compares: 0x4463a subf.s r2,lp,r10 = e2ff6254 ; 0x44662 subf.s r9,r20,r12 = e9a76264

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
BIN_OUT      = plain_image_path("_v24_plain_image.bin")
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

# --- Code-section byte patches (main block) ------------------------------------
#   integer envelope 2x  +  tolerance-widening on BOTH envelope monitors (+-5 -> +-15 LSB).
CODE_BYTE_PATCHES = [
    # integer envelope 2x (shl 0x8 -> shl 0x9)
    (0x42DAE, 0xC8, 0xC9, "shl 0x8,r9  -> 0x9   [gp-0x3574 upper IIR]"),
    (0x42DCA, 0xC8, 0xC9, "shl 0x8,r11 -> 0x9   [gp-0x3574 upper bypass]"),
    (0x42F16, 0xC8, 0xC9, "shl 0x8,r10 -> 0x9   [gp-0x3578 lower IIR+byp]"),
    # (A) NEUTRALIZE inline envelope check in FUN_00042af8 (cmp imm5 sign-extends: 0x1f = cmp -1 =
    #     unsigned compare vs 0xFFFFFFFF -> always-in-range; addi 0xf -> residual fault only at diff=-16).
    #     A real +-15 widen is impossible in-place (cmp imm5 maxes at +-7); (B) carries the +-15 check.
    (0x43190, 0x05, 0x0F, "inline UP addi 0x5->0xf  [residual fault pt -> gross -16]"),
    (0x43196, 0x6B, 0x7F, "inline UP cmp 0xb->0x1f  [= cmp -1 -> unsigned always-in-range (neutralize)]"),
    (0x431B4, 0x05, 0x0F, "inline LO addi 0x5->0xf  [residual fault pt -> gross -16]"),
    (0x431B6, 0x6B, 0x7F, "inline LO cmp 0xb->0x1f  [= cmp -1 -> unsigned always-in-range (neutralize)]"),
    # (B) bit1/bit2 envelope threshold in FUN_00043e44: 5/1024 -> 15/1024 (movhi imm hi halfwords)
    (0x44640, 0xA0, 0x70, "bit1/2 POS thr +5/1024->+15/1024  movhi 0x3ba0->0x3c70 (lo byte)"),
    (0x44641, 0x3B, 0x3C, "bit1/2 POS thr +5/1024->+15/1024  movhi 0x3ba0->0x3c70 (hi byte)"),
    (0x44648, 0xA0, 0x70, "bit1   NEG thr -5/1024->-15/1024  movhi -0x4460->0xbc70 (lo byte)"),
    (0x44649, 0xBB, 0xBC, "bit1   NEG thr -5/1024->-15/1024  movhi -0x4460->0xbc70 (hi byte)"),
    (0x4466C, 0xA0, 0x70, "bit2   NEG thr -5/1024->-15/1024  movhi -0x4460->0xbc70 (lo byte)"),
    (0x4466D, 0xBB, 0xBC, "bit2   NEG thr -5/1024->-15/1024  movhi -0x4460->0xbc70 (hi byte)"),
]

# --- Part-number string byte patches (main block) -- V18 lineage ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

# ---------------------------------------------------------------------------
# FP-twin doubling: 2 hooks (in-place 4B jr) + 2 caves (12B each).
# Cave doubles the FP register the displaced compare reads; that doubled value
# also propagates UNCHANGED to the FP-twin store (lp->gp-0x6db0 @0x449f4,
# r20->gp-0x6db8 @0x44a30 -- verified live-unchanged), so the twin tracks the 2x
# integer envelope shadow that the inline +-5 check (A) compares against.
# ---------------------------------------------------------------------------
CAVE_BASE = 0xC4E00

def jr(frm, to):
    """4-byte V850 jr disp22 from `frm` to `to`."""
    disp = (to - frm) & 0xFFFFFFFF
    hw0 = 0x0780 | ((disp >> 16) & 0x3F)
    hw1 = disp & 0xFFFF
    return struct.pack("<HH", hw0, hw1)

ADDF = {  # addf.s rX,rX,rX  (rX *= 2)
    "lp":  bytes.fromhex("ffff60fc"),   # r31
    "r20": bytes.fromhex("f4a760a4"),
}
# (name, hook_addr, displaced_bytes, double_bytes)  -- cave = [double][displaced][jr->hook+4]
FIX = [
    ("bit1", 0x4463A, bytes.fromhex("e2ff6254"), ADDF["lp"]),   # subf.s r2,lp,r10  ; lp -> gp-0x6db0
    ("bit2", 0x44662, bytes.fromhex("e9a76264"), ADDF["r20"]),  # subf.s r9,r20,r12 ; r20 -> gp-0x6db8
]

def build_caves():
    """Return (code_region_patches, cave_blob_at_base). Each patch is
    (addr, expected_old, new, note)."""
    patches = []
    cave_addr = CAVE_BASE
    cave_blob = bytearray()
    for name, hook, disp, dbl in FIX:
        body = dbl + disp                      # double the FP operand, then the displaced compare
        ret  = hook + 4                        # return to instruction after the displaced one
        cave = body + jr(cave_addr + len(body), ret)
        assert len(cave) == 12, f"{name} cave len {len(cave)}"
        patches.append((cave_addr, b"\xff" * len(cave), bytes(cave),
                        f"CAVE {name} @0x{cave_addr:05X}  double+displaced+jr->0x{ret:05X}"))
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
    print(f"{label}: V18 lineage + integer env 2x + FP-twin 2x (caves 1&2) + tol-widen +-5->+-15")
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
    # tolerance widening readback
    assert ecu_plain[0x43190 - START] == 0x0F and ecu_plain[0x43196 - START] == 0x7F, "inline UP widen lost"
    assert ecu_plain[0x431B4 - START] == 0x0F and ecu_plain[0x431B6 - START] == 0x7F, "inline LO widen lost"
    assert struct.unpack_from("<H", ecu_plain, 0x44640 - START)[0] == 0x3C70, "bit1/2 POS thr lost"
    assert struct.unpack_from("<H", ecu_plain, 0x44648 - START)[0] == 0xBC70, "bit1 NEG thr lost"
    assert struct.unpack_from("<H", ecu_plain, 0x4466C - START)[0] == 0xBC70, "bit2 NEG thr lost"
    # caves: 2 hooks present, bit4/bit32 hook sites must remain STOCK (caves dropped)
    for name, hook, disp, dbl in FIX:
        idx = [f[0] for f in FIX].index(name)
        assert bytes(ecu_plain[hook - START:hook - START + 4]) == jr(hook, CAVE_BASE + idx * 12), \
            f"hook {name} lost"
    assert bytes(ecu_plain[0x44784 - START:0x44784 - START + 4]) == bytes.fromhex("f0576274"), \
        "bit4 site must be STOCK (cave dropped)"
    assert bytes(ecu_plain[0x448A0 - START:0x448A0 - START + 4]) == bytes.fromhex("e86f6064"), \
        "bit32 site must be STOCK (cave dropped)"
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
    print(f"baseline = V9 stock; V24 = V18 lineage + 3 shl + 2 FP-twin caves + 10 tol-widen bytes\n")
    build("V24", code, headers, tag="LKAS-2x-EMEfix-intenv2x-FPtwin2x-Bthr15-Aneutral-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
