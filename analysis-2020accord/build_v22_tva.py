"""build_v22_tva.py — V22 = V21 + symmetric negative-envelope 2x + float-monitor 2x match.

LINEAGE: V21 (V18 lineage: 2x arb gain/clamps + EME RAMP-ONLY fix + PN string, PLUS the two
LERP3-output shl <<8 -> <<9 code patches on the integer rate-shaper's UPPER bound gp-0x3574)
PLUS three NEW edits for V22:

  EDIT 1 — integer-side NEGATIVE envelope (gp-0x3578) 2x, same single-instruction method as V21:
    0x42F16  SHL imm  shl 0x8,r10 -> shl 0x9,r10   0xC8 -> 0xC9
      Lower-bound IIR+bypass scaling in s_motor_torque_rate_shaper. The shl fires BEFORE the
      IIR-vs-bypass branch (be 0x42F40), so this ONE byte covers both IIR and bypass cases
      (unlike the upper bound gp-0x3574, which needed two shl patches at 0x42DAE/0x42DCA).
      Value rides in r9 -> consumed at 0x43142 (sar 0x8,r9), the lower-bound pipeline twin of
      the upper bound's 0x43136 (sar 0x8,r11). Verified: 2 refs total, both inside the shaper.

  EDITS 2 & 3 — float-monitor (FUN_00043e44) upper_raw/lower_raw 2x, to MATCH the doubled
  integer envelope so the report-only watchdog's flags f1/f3/f6 do not diverge -> no 0x3f1b CAN
  fault in the high-torque regime. The float monitor cross-checks the integer shaper's runtime
  outputs (gp-0x6af6/6b00/6b0a/6b98), which now carry the doubled envelope; the monitor must
  double its own recomputed envelope to agree.

  The float path has NO standalone scalar instruction to byte-flip (the base term shares the
  universal r1=1/1024 const and the runtime gp-0x6444 table), so the only faithful 2x is to
  scale upper_raw (r10) and lower_raw (r12) directly, AFTER both are finalized and BEFORE any
  consumption (the IIR at 0x4427e/0x442b0). That point is 0x44230. Two mulf.s are 8 bytes and
  cannot fit in place, so V22 uses a MINIMAL single-instruction redirect into a verified code
  cave; nothing else in the image shifts.

  Redirect (overwrites exactly ONE 4-byte instruction, no shift):
    0x44230  jr 0xC4FC0       was: ld.hu -0x6966,gp,r7  (e4 3f 9b 96) -> jr (88 07 90 0d)

  Code cave (free 0xFF padding at 0xC4FC0, inside main CRC block [0x13000,0xC4FFC), well before
  the block descriptor at 0xC4FF0). 20 bytes, 5 instructions:
    0xC4FC0  movhi 0x4000,r0,r7    40 3e 00 40   ; r7 = 2.0f
    0xC4FC4  mulf.s r7,r10,r10     e7 57 64 54   ; upper_raw *= 2
    0xC4FC8  mulf.s r7,r12,r12     e7 67 64 64   ; lower_raw *= 2
    0xC4FCC  ld.hu -0x6966,gp,r7   e4 3f 9b 96   ; displaced original instruction
    0xC4FD0  jr 0x44234            b7 07 64 f2   ; return to next instruction

  Control flow preserved: the two existing br 0x44230 (at 0x441d4, 0x441f8) plus the fall-through
  all reach 0x44230 -> jr -> cave -> doubling -> re-run displaced ld.hu -> jr back to 0x44234.
  r10/r12 verified live at 0x44230 on every path and not consumed until 0x4427e/0x442b0 (after
  the cave). r7 is the only scratch; the displaced ld.hu reloads it, so no register is corrupted.

WHAT V22 EDITS (on top of stock V9 code.bin):
  Calibration block #48 [0xC6000, 0xC6FFC) — halfwords (u16 LE):  [inherited from V21/V18]
    0xC646C  GAIN     tp+0x746c   891   -> 1782   (x2)
    0xC61B4  CLAMP    tp+0x71b4   512   -> 1024   (x2)
    0xC61B2  CLAMP    tp+0x71b2   512   -> 1024   (x2)
  Calibration block #48 — single byte (u8):  [inherited]
    0xC64DE  RAMPSTEP tp+0x74de   0x11 -> 0x1B    (17->27)
  Main block [0x13000, 0xC4FFC) — code bytes:
    0x42DAE  shl 0x8,r9  -> shl 0x9,r9    0xC8 -> 0xC9  [V21: gp-0x3574 upper IIR]
    0x42DCA  shl 0x8,r11 -> shl 0x9,r11   0xC8 -> 0xC9  [V21: gp-0x3574 upper bypass/snap]
    0x42F16  shl 0x8,r10 -> shl 0x9,r10   0xC8 -> 0xC9  [V22 EDIT 1: gp-0x3578 lower IIR+bypass]
  Main block [0x13000, 0xC4FFC) — code regions (V22 EDITS 2 & 3):
    0x44230  ld.hu -> jr 0xC4FC0          (4 B redirect, in place)
    0xC4FC0  cave: movhi/mulf.s/mulf.s/ld.hu/jr  (20 B into 0xFF padding)
  Main block [0x13000, 0xC4FFC) — part-number strings:  [inherited]
    0x13109  '-' -> ','   ;  0x14120  '-' -> ','

  Two CRC blocks recomputed: block #48 @0xC6FFC ; main block @0xC4FFC (covers cave + redirect).

DISASM/ENCODING NOTES (2026-05-31):
  - shl-imm: [15:11]=reg2, [10:5]=0x16, [4:0]=imm5; low byte C8(imm5=8)->C9(imm5=9). Verified
    0x42F16 stock byte = 0xC8 (shl 0x8,r10) in s_motor_torque_rate_shaper.
  - jr disp22: hw0 = 0x0780 | disp[21:16], hw1 = disp[15:0] (LE halfwords). Cross-checked vs
    in-image jr's: 0x2c jr 0x80 = 80 07 54 00 ; 0x234 jr 0x1e0 = bf 07 ac ff (neg).
      0x44230 -> 0xC4FC0 : disp=+0x80D90 -> 88 07 90 0d
      0xC4FD0 -> 0x44234 : disp=-0x80D9C -> b7 07 64 f2
  - movhi 0x4000,r0,r7 = 40 3e 00 40 (vs movhi 0x3f80,r0,r10 = 40 56 80 3f @0x445f4).
  - mulf.s r7,r10,r10 = e7 57 64 54 ; mulf.s r7,r12,r12 = e7 67 64 64
    (vs mulf.s r17,r8,r10 = f1 47 64 54 @0x4317a; FP subop field [10:5]=0x3F preserved).
  - NOTE: encodings hand-derived and cross-checked against real in-image instructions; Ghidra
    script-assembly was unavailable (GHIDRA_MCP_ALLOW_SCRIPTS unset). Re-verify by disassembling
    the built image before any flash.

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

# --- Code-section byte patches (main block) ---
# V850 SHL imm encoding: [15:11]=reg2, [10:5]=opcode(0x16), [4:0]=imm5(shift amount).
# The patched byte is the low byte of the 16-bit instruction; bit0 is the LSB of imm5.
# C8=1100_1000 -> imm5=01000=8; C9=1100_1001 -> imm5=01001=9.
CODE_BYTE_PATCHES = [
    (0x42DAE, 0xC8, 0xC9, "SHL imm  0x42DAE  shl 0x8,r9  -> shl 0x9,r9   [V21 gp-0x3574 upper IIR]"),
    (0x42DCA, 0xC8, 0xC9, "SHL imm  0x42DCA  shl 0x8,r11 -> shl 0x9,r11  [V21 gp-0x3574 upper bypass]"),
    (0x42F16, 0xC8, 0xC9, "SHL imm  0x42F16  shl 0x8,r10 -> shl 0x9,r10  [V22 gp-0x3578 lower IIR+bypass]"),
]

# --- Code-region patches (main block) — V22 float-monitor 2x via minimal redirect + cave ---
# Each entry: (addr, expected_old_bytes, new_bytes, note). Old bytes are verified before patching.
CAVE_ADDR = 0xC4FC0
REDIRECT_OLD = bytes.fromhex("e43f9b96")          # ld.hu -0x6966, gp, r7  @ 0x44230
REDIRECT_NEW = bytes.fromhex("8807900d")          # jr 0xC4FC0
CAVE_OLD     = b"\xff" * 20                        # free padding
CAVE_NEW     = bytes.fromhex(
    "403e0040"   # 0xC4FC0  movhi 0x4000,r0,r7    ; r7 = 2.0f
    "e7576454"   # 0xC4FC4  mulf.s r7,r10,r10     ; upper_raw *= 2
    "e7676464"   # 0xC4FC8  mulf.s r7,r12,r12     ; lower_raw *= 2
    "e43f9b96"   # 0xC4FCC  ld.hu -0x6966,gp,r7   ; displaced original
    "b70764f2"   # 0xC4FD0  jr 0x44234            ; return
)
CODE_REGION_PATCHES = [
    (0x44230,   REDIRECT_OLD, REDIRECT_NEW, "REDIRECT 0x44230  ld.hu -> jr 0xC4FC0  [V22 float 2x entry]"),
    (CAVE_ADDR, CAVE_OLD,     CAVE_NEW,     "CAVE     0xC4FC0  movhi/mulf.s*2/ld.hu/jr  [V22 float upper+lower 2x]"),
]

# --- Part-number string byte patches (main block) ---
PN_PATCHES = [
    (0x13109, 0x2D, 0x2C, "PN byte@0x13109  '-'->','  ('39990-TVA-A160'@0x13100)"),
    (0x14120, 0x2D, 0x2C, "PN byte@0x14120  '-'->','  ('39990-TVA-A160'@0x14117)"),
]

TOUCHED_BLOCKS = [
    (0xC6000, 0xC6FFC),  # block #48 — calibration edits
    (0x13000, 0xC4FFC),  # main block — code byte patches + code regions (redirect+cave) + PN
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


def patch_code_regions(code):
    for addr, old, new, note in CODE_REGION_PATCHES:
        assert len(old) == len(new), f"region length mismatch at 0x{addr:05X}"
        got = bytes(code[addr:addr + len(old)])
        if got != old:
            raise AssertionError(
                f"0x{addr:05X}: expected {old.hex()} got {got.hex()} ({note})")
        code[addr:addr + len(new)] = new
        print(f"  0x{addr:05X}:   {old.hex()} -> {new.hex()}   {note}")


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
    print(f"{label}: V21 lineage + gp-0x3578 2x + float-monitor upper/lower 2x   cipher v9b")
    code = bytearray(code_stock)

    patch_cal(code)
    patch_cal_bytes(code)
    patch_code_bytes(code)
    patch_code_regions(code)
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
    shl_r10 = ecu_plain[0x42F16 - START]
    assert shl_r9  == 0xC9, f"LERP3 shl r9  patch lost (expected 0xC9, got {shl_r9:#04x})"
    assert shl_r11 == 0xC9, f"LERP3 shl r11 patch lost (expected 0xC9, got {shl_r11:#04x})"
    assert shl_r10 == 0xC9, f"gp-0x3578 shl r10 patch lost (expected 0xC9, got {shl_r10:#04x})"
    redirect = bytes(ecu_plain[0x44230 - START:0x44234 - START])
    cave     = bytes(ecu_plain[CAVE_ADDR - START:CAVE_ADDR - START + len(CAVE_NEW)])
    assert redirect == REDIRECT_NEW, f"float redirect lost (got {redirect.hex()})"
    assert cave == CAVE_NEW, f"float cave lost (got {cave.hex()})"
    print(f"  lineage OK: GAIN={gain}  RAMPSTEP=0x1B  shl_r9/r11/r10=0x{shl_r9:02X}/0x{shl_r11:02X}/0x{shl_r10:02X}")
    print(f"  float redirect @0x44230 = {redirect.hex()}   cave @0x{CAVE_ADDR:05X} = {cave.hex()}")

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
    print(f"baseline = V9 stock; V22 = V21 (3 cal HW + 1 cal B + 2 code B + 2 PN)")
    print(f"          + gp-0x3578 shl (1 code B) + float redirect (4 B) + cave (20 B)\n")
    build("V22", code, headers, tag="LKAS-2x-EMEfix-symNEGenv-floatmon2x-PNfix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
