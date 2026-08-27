#!/usr/bin/env python3
"""verify/verify_v68_image.py -- INDEPENDENT post-build integrity verifier for V68 (and any V68 derivative).

DESIGN RULE (the V40 process lesson, CLAUDE.md; same rule as verify/verify_v52c_image.py): a verifier and the
builder it checks MUST NOT share an assumption. This file therefore imports NOTHING from
builds/v50_v79/build_v68_tva.py / builds/v50_v79/build_v67_tva.py / builds/telemetry/build_vfourframe_tva.py. The CRC block walk, the V850E2
instruction decode, the cave geometry, the payload semantics and the control-path anchors are all
re-implemented here and run against the BUILT BYTES.

READ-ONLY. It never writes a firmware byte and never flashes.

It answers, mechanically:
  1. Do both CRC walks pass (bootloader's 49-block bridge walk AND the 50-block full chain)?
  2. Is the diff vs the V67 reference confined to {the cave span, the MAIN CRC trailer}?
     -- i.e. is the control path byte-identical, which is V68's core claim?
  3. Does the cave decode, by linear sweep from the built bytes, into the intended instruction list?
  4. Is the trampoline transparent (displaced instruction re-executed LAST, `jmp [lp]` return)?
  5. Is there EXACTLY ONE store in the cave, and is it the CAN-330 payload byte gp-0x1514?
  6. Does the cave fit inside the all-0xFF region, and where does that region actually END?
  7. Are the control-path anchors (repoint, arms, sar sites, lockout, private gain) at their
     expected values?
  8. Does rlog-tools/probe/decode_v68_probe.py's CAVE_HEX match the image?

Usage:
    ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares \
        python verify/verify_v68_image.py [--built PATH] [--reference PATH]

Exit code 0 = all checks pass. Any failure prints FAIL lines and exits 1.

NOTE: this proves BYTE + STRUCTURAL integrity only. It does NOT close GATE 1 (RAM ownership) or
GATE 2 (closed-loop stability), and it is not a substitute for reading the cave in Ghidra.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(HERE)

# --- geometry, restated here rather than imported ------------------------------------------------
SPAN = (0x13000, 0x100000)          # the flashed region; NEVER diff outside it (0xFF filler below)
CAVE_BASE = 0xC4B34
CAVE_PROVEN = 68                    # the extent flown by V55/V57/V58/V59/V64/V65/V66/V67/V68
HOOK_ADDR = 0x55C0E
MAIN_BLOCK = (0x13000, 0xC4FFC)
CAL_BLOCK = (0xC6000, 0xC6FFC)
GP_DISP_PAYLOAD = 0x1514            # CAN-330 / 0x14A byte4
GP_DISP_DISPLACED = 0x1518          # the hook's own displaced `movea -0x1518,gp,r6`
DECODER = os.path.join(REPO, "rlog-tools", "probe/decode_v68_probe.py")

# The intended cave, as (bytes, text). Written out longhand so a drift shows up as a diff, not as a
# re-derivation that moves with the builder.
INTENDED = [
    ("203e8800", "movea 0x88,r0,r7     ; bit7 LIVENESS | bit3 BUILD-CLASS MARKER"),
    ("8437fb97", "ld.bu -0x6806[gp],r6 ; THE GATE"),
    ("6132", "cmp   0x1,r6"),
    ("b605", "blt   +6"),
    ("273e4000", "movea 0x40,r7,r7     ; bit6 = gp-0x6806 != 0"),
    ("a4372198", "ld.bu -0x67df[gp],r6 ; detector FSM state. ODD disp 0x9821 -> opcode 0x3D"),
    ("6132", "cmp   0x1,r6"),
    ("b605", "blt   +6"),
    ("273e2000", "movea 0x20,r7,r7     ; bit5 = gp-0x67df != 0  (FSM LEFT NEUTRAL)"),
    ("8437e798", "ld.bu -0x671a[gp],r6 ; Honda's 1 kHz oscillation detector"),
    ("6132", "cmp   0x1,r6"),
    ("b605", "blt   +6"),
    ("273e1000", "movea 0x10,r7,r7     ; bit4 = gp-0x671a >= 1  (V67 tested >= 5)"),
    ("8437edea", "ld.bu -0x1514[gp],r6 ; CAN-330 payload byte4"),
    ("c6360700", "andi  0x7,r6,r6      ; keep live STEER_SENSOR_STATUS 2:0"),
    ("0731", "or    r7,r6"),
    ("4437ecea", "st.b  r6,-0x1514[gp] ; THE ONLY STORE"),
    ("2436e8ea", "movea -0x1518,gp,r6  ; re-exec the displaced instruction, LAST"),
    ("7f00", "jmp   [lp]           ; -> 0x55C12"),
]

# (address, width, expected, what). Every one is on V67's control path, carried unchanged by V68.
ANCHORS = [
    (0x3AA94, 4, "847ffb97", "the V67 repoint: ld.bu -0x6806[gp],r15 (stock reads -0x683c)"),
    (0xC6440, 2, "0008", "0xC6440 arm gp-0x671a = 2048, STOCK"),
    (0xC6442, 2, "0004", "0xC6442 arm gp-0x671d = 1024, STOCK (BELOW stock gain if it ever arms)"),
    (0xC6444, 2, "0002", "0xC6444 r26 arm = 512, STOCK"),
    (0xC6446, 2, "7c14", "0xC6446 r24 LKAS arm = 5244 (V67's edit, carried)"),
    (0x3AB70, 2, "aa32", "sar site, STOCK"),
    (0x3AB76, 2, "aa32", "sar site, STOCK"),
    (0x3AC20, 2, "aa42", "sar site, STOCK"),
    (0xC62EA, 2, "0000", "0xC62EA low-speed steer lockout = 0 (V53)"),
    (0xC6CD0, 2, "ec0d", "0xC6CD0 private LKAS forward gain = 3564 (V57 decouple)"),
    (0xC646C, 2, "7b03", "0xC646C shared sensor scale = 891 (reverted to stock-equivalent by V57)"),
    # 🛑 the calibration fact the gp-0x67ac exclusion rests on: 11 per-slot roles, none 6 or 7.
    (0xC4124, 11, "0000050005050000000500", "0xC4124 role table -- no slot is 6 or 7 => gp-0x67ac is 0"),
]

FAILURES: list[str] = []
N = [0]


def check(cond, label, detail=""):
    N[0] += 1
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    if not cond:
        FAILURES.append(label)
        if detail:
            print(f"         {detail}")
    return cond


def u16(b, a):
    return struct.unpack_from("<H", b, a)[0]


def u32(b, a):
    return struct.unpack_from("<I", b, a)[0]


# ---------------------------------------------------------------------------------------------
# A from-scratch V850E2 length decoder, sufficient for the cave's instruction set.
# Format I/II/III are 2 bytes; Format VI (movea/addi/andi/ori) and Format VII (ld/st) are 4.
# Bcond is Format III and must be recognised BEFORE the opcode-field test, because its opcode
# field aliases the 4-byte space.
# ---------------------------------------------------------------------------------------------
FOUR_BYTE_OPS = {0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
                 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F}
STORE_OPS = {0x3A: "st.b", 0x3B: "st.h/st.w"}
LOAD_OPS = {0x38: "ld.b", 0x39: "ld.h/ld.w", 0x3C: "ld.bu(even)", 0x3D: "ld.bu(odd)", 0x3F: "ld.hu"}


def insn_len(hw):
    if ((hw >> 7) & 0xF) == 0b1011:          # Bcond, Format III
        return 2
    return 4 if ((hw >> 5) & 0x3F) in FOUR_BYTE_OPS else 2


def sweep(img, base, end):
    off = base
    while off < end:
        hw = u16(img, off)
        n = insn_len(hw)
        yield off, bytes(img[off:off + n])
        off += n


def gp_disp_of(raw):
    """Kit-convention POSITIVE gp offset of a 4-byte Format-VII gp-relative load/store."""
    hw1, hw2 = struct.unpack("<HH", raw)
    op = (hw1 >> 5) & 0x3F
    if op in (0x3C, 0x3D):                   # ld.bu: displacement bit0 lives in the OPCODE field
        d = (hw2 & 0xFFFE) | (op & 1)
    else:
        d = hw2 & 0xFFFE
    return op, (0x10000 - d) & 0xFFFF, hw1 & 0x1F, hw1 >> 11


def crc_walk(img, bridge):
    """Replay the bootloader's linked-list CRC walk. bridge=True is the 49-block BL walk."""
    region_start, end = SPAN
    bstart = u16(img, end - 8) << 12
    blen = (u16(img, end - 6) << 12) - 4
    bridged = False
    seen = fails = 0
    while True:
        if bstart < 0 or bstart + blen + 4 > len(img):
            return seen, fails + 1
        if (zlib.crc32(img[bstart:bstart + blen]) & 0xFFFFFFFF) != u32(img, bstart + blen):
            fails += 1
        seen += 1
        if bstart == region_start:
            return seen, fails
        if bridge and bstart == 0xC6000 and not bridged:
            bridged, bstart, blen = True, region_start, 0xB1FFC
            continue
        nxt = u16(img, bstart - 8) << 12
        if nxt == bstart or seen > 200:
            return seen, fails
        bstart, blen = nxt, (u16(img, bstart - 6) << 12) - 4


def main():
    ap = argparse.ArgumentParser()
    default_root = os.environ.get("ACCORD_FIRMWARE_ROOT",
                                  os.path.join(os.path.dirname(REPO), "accord-firmwares"))
    an = os.path.join(default_root, "analysis-2020accord")
    ap.add_argument("--built", default=os.path.join(an, "_v68_plain_image.bin"))
    ap.add_argument("--reference", default=os.path.join(an, "_v67_plain_image.bin"),
                    help="the base whose CONTROL PATH the built image must reproduce byte for byte")
    ap.add_argument("--cave-len", type=int, default=None,
                    help="expected used cave length; default = inferred from trailing 0xFF")
    a = ap.parse_args()

    built = bytearray(open(a.built, "rb").read())
    ref = bytearray(open(a.reference, "rb").read())
    print(f"built     {a.built}\n          SHA256 {hashlib.sha256(bytes(built)).hexdigest()}")
    print(f"reference {a.reference}\n          SHA256 {hashlib.sha256(bytes(ref)).hexdigest()}\n")

    print("== 1. CRC chain ==")
    for lbl, bridge, want in (("bootloader walk (bridged, 49 blocks)", True, 49),
                              ("full linked list (50 blocks)", False, 50)):
        seen, fails = crc_walk(bytes(built), bridge)
        check(fails == 0 and seen == want, f"{lbl}: {seen} blocks, {fails} mismatch(es)")
    for nm, blk in (("MAIN", MAIN_BLOCK), ("CAL", CAL_BLOCK)):
        calc = zlib.crc32(built[blk[0]:blk[1]]) & 0xFFFFFFFF
        check(calc == u32(built, blk[1]),
              f"{nm} block [0x{blk[0]:X},0x{blk[1]:X}) CRC 0x{calc:08X} matches its trailer")

    print("\n== 2. diff vs the reference, restricted to [0x13000,0x100000) ==")
    cave_span = set(range(CAVE_BASE, CAVE_BASE + CAVE_PROVEN))
    main_crc = set(range(MAIN_BLOCK[1], MAIN_BLOCK[1] + 4))
    d = [i for i in range(*SPAN) if built[i] != ref[i]]
    stray = [i for i in d if i not in cave_span | main_crc]
    print(f"       {len(d)} differing bytes: {len([i for i in d if i in cave_span])} cave + "
          f"{len([i for i in d if i in main_crc])} MAIN CRC")
    check(not stray, "ZERO differences outside {cave span, MAIN CRC trailer}",
          f"stray at {[hex(x) for x in stray[:24]]}")
    cal_d = [i for i in range(*CAL_BLOCK) if built[i] != ref[i]]
    check(not cal_d, f"the CAL block is byte-identical to the reference ({len(cal_d)} differ)",
          f"differs at {[hex(x) for x in cal_d[:24]]}")
    check(u32(built, CAL_BLOCK[1]) == u32(ref, CAL_BLOCK[1]),
          "the CAL CRC trailer did NOT move -- proof no calibration byte changed")
    check(u32(built, MAIN_BLOCK[1]) != u32(ref, MAIN_BLOCK[1]),
          "the MAIN CRC trailer DID move -- the cave really changed")

    print("\n== 3. cave geometry, derived from the bytes ==")
    blk = bytes(built[CAVE_BASE:CAVE_BASE + CAVE_PROVEN])
    used = len(blk.rstrip(b"\xff"))
    want_len = a.cave_len if a.cave_len is not None else used
    check(used == want_len, f"cave uses {used} of {CAVE_PROVEN} proven bytes "
                            f"({CAVE_PROVEN - used} trailing 0xFF)")
    check(used % 2 == 0, "cave length is halfword-aligned")
    check(set(blk[used:]) <= {0xFF}, "the tail of the proven extent is clean 0xFF -- no remnants")
    # where the all-0xFF region actually ends, and why
    i = CAVE_BASE + used
    while i < 0x100000 and built[i] == 0xFF:
        i += 1
    link_start = u16(built, 0xC4FF8) << 12
    link_len = (u16(built, 0xC4FFA) << 12) - 4
    print(f"       contiguous 0xFF runs to 0x{i:05X}; free region = "
          f"[0x{CAVE_BASE:05X},0x{i:05X}) = {i - CAVE_BASE} bytes")
    check(i == 0xC4FF0, "the 0xFF region ends at 0xC4FF0 -- the CAVE HARD LIMIT")
    check((link_start, link_len) == (0x13000, 0xB1FFC),
          f"0xC4FF8/0xC4FFA are the CRC chain link fields -> block 0x{link_start:05X} "
          f"len 0x{link_len:05X}; THIS is what bounds the cave, not padding")
    check(CAVE_BASE + used <= 0xC4FF0, "the cave ends below the hard limit")

    print("\n== 4/5. cave decoded by linear sweep from the BUILT bytes ==")
    got = list(sweep(built, CAVE_BASE, CAVE_BASE + used))
    ok = len(got) == len(INTENDED)
    check(ok, f"{len(got)} instructions decoded, {len(INTENDED)} intended")
    if ok:
        bad = []
        for (addr, raw), (hexs, text) in zip(got, INTENDED):
            mark = "" if raw.hex() == hexs else f"   <<< expected {hexs}"
            if mark:
                bad.append(hex(addr))
            print(f"       0x{addr:05X}  {raw.hex():<10s} {text}{mark}")
        check(not bad, "every cave instruction matches the intended encoding", f"at {bad}")
    stores = [(addr, raw) for addr, raw in got
              if len(raw) == 4 and ((u16(raw, 0) >> 5) & 0x3F) in STORE_OPS]
    check(len(stores) == 1, f"EXACTLY ONE store in the cave (found {len(stores)})",
          f"at {[hex(x) for x, _ in stores]}")
    if len(stores) == 1:
        op, disp, reg1, reg2 = gp_disp_of(stores[0][1])
        check((disp, reg1) == (GP_DISP_PAYLOAD, 4),
              f"the sole store is st.b r{reg2},-0x{disp:04x}[r{reg1}] = the CAN-330 payload byte")
    check(got[-1][1] == bytes.fromhex("7f00"), "the cave returns via `jmp [lp]`")
    op, disp, reg1, reg2 = gp_disp_of(got[-2][1])
    check((disp, reg1, reg2) == (GP_DISP_DISPLACED, 4, 6),
          "the displaced hook instruction is re-executed LAST (movea -0x1518,gp,r6)")
    jarl = bytes(built[HOOK_ADDR:HOOK_ADDR + 4])
    check(jarl == bytes(ref[HOOK_ADDR:HOOK_ADDR + 4]),
          f"the hook at 0x{HOOK_ADDR:05X} is byte-identical to the reference ({jarl.hex()})")
    check(HOOK_ADDR < 0x55C18, "the hook precedes the CAN checksum computation at 0x55C18")
    # the cells the cave reads, reported so a re-aim is visible at a glance
    print("       cells read by the cave:")
    for addr, raw in got:
        if len(raw) == 4 and ((u16(raw, 0) >> 5) & 0x3F) in LOAD_OPS:
            op, disp, reg1, reg2 = gp_disp_of(raw)
            print(f"         0x{addr:05X}  {LOAD_OPS[op]:<12s} gp-0x{disp:04x} -> r{reg2}")

    print("\n== 6. control-path anchors ==")
    for addr, w, want, what in ANCHORS:
        gotb = bytes(built[addr:addr + w]).hex()
        extra = f" = {u16(built, addr)}" if w == 2 else ""
        check(gotb == want, f"0x{addr:05X} {gotb}{extra}  {what}", f"expected {want}")

    print("\n== 7. decoder link ==")
    if os.path.exists(DECODER):
        txt = open(DECODER, encoding="utf-8").read()
        m = re.search(r'^CAVE_HEX\s*=\s*"([0-9a-f]+)"', txt, re.M)
        check(bool(m) and m.group(1) == blk[:used].hex(),
              "rlog-tools/probe/decode_v68_probe.py CAVE_HEX matches the built cave",
              f"decoder {m.group(1) if m else '(absent)'}\n         image   {blk[:used].hex()}")
    else:
        check(False, f"{DECODER} exists")

    print("\n" + "=" * 96)
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILURE(S) out of {N[0]} checks")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print(f"RESULT: ALL {N[0]} CHECKS PASSED")
    print("NOTE: BYTE + STRUCTURAL integrity only. GATE 1 (RAM ownership) and GATE 2 (closed-loop")
    print("      stability) are NOT closed by this script, and neither is a Ghidra read of the cave.")


if __name__ == "__main__":
    main()
