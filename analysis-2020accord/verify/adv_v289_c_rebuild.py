# -*- coding: utf-8 -*-
"""ADVERSARY C (build-script audit) -- V289 rev 1 -- INDEPENDENT REBUILD, CRC CHAIN, .rwd DECODE, FULL DIFF.

Shares NO code with build_v289_tva.py.  Everything here is re-derived:
  * a fresh V850E2 assembler written from the ISA field layout (Formats I, II, III, V, VI, VII, XI);
  * the cave/tail SOURCE transcribed as MNEMONICS from the builder's declared listing (the semantic
    declaration), then assembled here -- so an encoder bug in the builder cannot be inherited;
  * the CRC chain walker re-implemented from the bootloader description (END-8/END-6 fields,
    backward linked list, the verified 0xC6000 bridge);
  * an x31 .rwd parser + a brute-forced cipher (never the builder's key/op table);
  * a byte-granular full-file diff V282 -> V289.

Run:  python adv_v289_c_rebuild.py      (read-only; writes nothing outside stdout)
Exit 0 only if every claim reproduces.  Prereg: docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md sec. C.
"""
import hashlib
import itertools
import operator
import os
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
TAG = ("V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5"
       "-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP")
V282 = ROOT / "analysis-2020accord" / ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X"
                                       ".FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V289_IMG = ROOT / "analysis-2020accord" / f"_v289_{TAG}_plain_image.bin"
V289_RWD = ROOT / "flashing-2020accord" / "rwd" / f"39990-TVA,A160-{TAG}-0x13000-0x100000.rwd"
V288_RWD = ROOT / "flashing-2020accord" / "rwd" / ("39990-TVA,A160-V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE"
                                                   ".R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP"
                                                   "-0x13000-0x100000.rwd")
CLAIM_IMG = "f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed"
CLAIM_RWD = "20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c"
CLAIM_BASE = "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe"
START, END = 0x13000, 0x100000

fails = []


def must(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


# ------------------------------------------------------------------------------------------------
# A fresh V850E2 assembler.  Register numbers: r0=0 gp=4 tp=5 lp=31.
# ------------------------------------------------------------------------------------------------
def H(v):
    return struct.pack("<H", v & 0xFFFF)


def fI(op, r1, r2):            # Format I  : reg2[15:11] op[10:5] reg1[4:0]
    return H((r2 << 11) | (op << 5) | r1)


def fII(op, imm5, r2):         # Format II : reg2[15:11] op[10:5] imm5[4:0]
    return H((r2 << 11) | (op << 5) | (imm5 & 0x1F))


def fIII(cond, disp9):         # Format III: disp[8:4]<<11 | 1011<<7 | disp[3:1]<<4 | cond
    d = disp9 & 0x1FF
    return H(((d >> 4) << 11) | (0xB << 7) | (((d >> 1) & 7) << 4) | cond)


def fV_jr(pc, target):         # Format V  : reg2=0 | 011110 | disp[21:16] ; disp[15:0]
    d = (target - pc) & 0x3FFFFF
    assert d & 1 == 0
    return H((0x1E << 6) | (d >> 16)) + H(d & 0xFFFF)


def fVI(op, r1, r2, imm16):    # Format VI : reg2 op reg1 ; imm16  (movea 0x31, andi 0x36)
    return H((r2 << 11) | (op << 5) | r1) + H(imm16)


def fVII(op, r1, r2, hw2):     # Format VII: reg2 op reg1 ; disp16 (bit0 = width/select flag)
    return H((r2 << 11) | (op << 5) | r1) + H(hw2)


def fXI_mul(r1, r2, r3=0):     # Format XI : reg2 111111 reg1 ; reg3 01000100000 (0x220)
    return H((r2 << 11) | (0x3F << 5) | r1) + H((r3 << 11) | 0x0220)


OPI = dict(mov=0x00, jmp=0x03, mulh=0x07, **{"or": 0x08}, subr=0x0C, sub=0x0D, add=0x0E, cmp=0x0F)
OPII = dict(movi=0x10, cmpi=0x13, sar=0x15, shl=0x16)
COND = dict(bl=1, be=2, br=5, blt=6, ble=7, bne=0xA, bge=0xE, bgt=0xF)
GP, TP, LP = 4, 5, 31


def asm(line, pc):
    """One mnemonic line -> bytes.  Syntax is the builder's listing syntax (e.g. 'ld.w -0x6c44[gp],r9')."""
    mn, _, rest = line.strip().partition(" ")
    args = [a.strip() for a in rest.split(",")] if rest.strip() else []

    def R(t):
        t = t.strip()
        return {"gp": GP, "tp": TP, "lp": LP, "r0": 0}.get(t, int(t[1:]) if t.startswith("r") else None)

    def I(t):
        return int(t, 0)

    def mem(t):                  # 'disp[base]'
        d, _, b = t.partition("[")
        return I(d), R(b.rstrip("]"))

    if mn in ("ld.w", "ld.h", "ld.hu", "ld.bu"):
        (d, b), r2 = mem(args[0]), R(args[1])
        d &= 0xFFFF
        if mn == "ld.w":
            assert d % 4 == 0
            return fVII(0x39, b, r2, (d & 0xFFFE) | 1)
        if mn == "ld.h":
            return fVII(0x39, b, r2, d & 0xFFFE)
        if mn == "ld.hu":
            return fVII(0x3F, b, r2, (d & 0xFFFE) | 1)
        return fVII(0x3C | (d & 1), b, r2, (d & 0xFFFE) | 1)          # ld.bu: disp bit0 rides in op bit0
    if mn in ("st.w", "st.h", "st.b"):
        r2, (d, b) = R(args[0]), mem(args[1])
        d &= 0xFFFF
        if mn == "st.w":
            assert d % 4 == 0
            return fVII(0x3B, b, r2, (d & 0xFFFE) | 1)
        if mn == "st.h":
            return fVII(0x3B, b, r2, d & 0xFFFE)
        return fVII(0x3A, b, r2, d)
    if mn == "andi":
        return fVI(0x36, R(args[1]), R(args[2]), I(args[0]))
    if mn == "movea":
        return fVI(0x31, R(args[1]), R(args[2]), I(args[0]) & 0xFFFF)
    if mn == "mul":
        return fXI_mul(R(args[0]), R(args[1]), R(args[2]))
    if mn == "mov":
        if args[0].startswith("r") or args[0] in ("gp", "tp", "lp"):
            return fI(OPI["mov"], R(args[0]), R(args[1]))
        v = I(args[0])
        if -16 <= v <= 15:
            return fII(OPII["movi"], v, R(args[1]))
        return H((0x31 << 5) | R(args[1])) + struct.pack("<i", v if v < 2 ** 31 else v - 2 ** 32)   # mov imm32
    if mn == "cmp":
        if args[0].startswith("r"):
            return fI(OPI["cmp"], R(args[0]), R(args[1]))
        return fII(OPII["cmpi"], I(args[0]), R(args[1]))
    if mn in ("sar", "shl"):
        return fII(OPII[mn], I(args[0]), R(args[1]))
    if mn in ("add", "sub", "subr", "or"):
        return fI(OPI[mn], R(args[0]), R(args[1]))
    if mn == "jmp":
        return fI(OPI["jmp"], R(args[0].strip("[]")), 0)
    if mn in COND:
        t = args[0]
        disp = I(t) if t[0] in "+-" else I(t) - pc
        return fIII(COND[mn], disp)
    if mn == "jr":
        return fV_jr(pc, I(args[0]))
    raise ValueError(line)


def assemble(src, at):
    out, pc = bytearray(), at
    for line in src.strip().split("\n"):
        line = line.split(";")[0].strip()
        if not line:
            continue
        b = asm(line, pc)
        out += b
        pc += len(b)
    return bytes(out)


# ------------------------------------------------------------------------------------------------
# THE DECLARED EDITS, as mnemonics (transcribed from the builder's docstring/listing -- its semantic
# claim -- NOT its byte output).  Coefficients: b0=b2=16048=0x3eb0, b1=a1=-31842=-0x7c62, a2=15712=0x3d60.
# ------------------------------------------------------------------------------------------------
NOTCH_SRC = """
ld.w  -0x6c44[gp],r9
ld.w  -0x6c3c[gp],r13
andi  0x3fff,r13,r13
add   r13,r9
movea 0x3eb0,r0,r13
mul   r12,r13,r0
mov   r13,r7
add   r13,r9
mov   r9,r6
sar   0xe,r6
andi  0x3fff,r9,r9
st.w  r9,-0x6c3c[gp]
movea 0x3d60,r0,r13
mul   r6,r13,r0
sub   r13,r7
ld.w  -0x6c40[gp],r13
st.w  r7,-0x6c40[gp]
mov   r12,r9
sub   r6,r9
movea -0x7c62,r0,r7
mul   r9,r7,r0
add   r7,r13
st.w  r13,-0x6c44[gp]
mov   0x0,r13
cmp   0x0,r9
bge   +4
mov   0x2,r13
mov   r6,r12
mov   r9,r7
cmp   0x0,r7
bge   +4
subr  r0,r7
cmp   0x0,r6
bge   +4
subr  r0,r6
cmp   r6,r7
mov   0x8,r7
bge   +4
mov   0x0,r7
or    r7,r13
shl   0x4,r13
st.h  r13,-0x6c3a[gp]
ld.hu 0x71be[tp],r9
cmp   r9,r12
ble   +4
mov   r9,r12
subr  r0,r9
cmp   r9,r12
bge   +4
mov   r9,r12
ld.hu 0x73ee[tp],r7
jr    0x2a178
"""
TAIL_SRC = """
ld.hu -0x6c3a[gp],r7
andi  0xa0,r7,r7
ld.bu -0x1514[gp],r6
andi  0x5f,r6,r6
or    r7,r6
st.b  r6,-0x1514[gp]
movea -0x1518,gp,r6
jmp   [lp]
"""
HOOK, NOTCH_AT, EXIT, TAIL_AT = 0x2A174, 0xC4C00, 0xC4BD6, 0xC4BDC
CAL = {0xC63E8: (923, 875), 0xC63EA: (1560, 2301)}
ALLOWED = [(0x2A174, 4), (0xC4BD6, 4), (0xC4BDC, 28), (0xC4C00, 140), (0xC63E8, 1), (0xC63EA, 2),
           (0xC4FFC, 4), (0xC6FFC, 4)]


# ------------------------------------------------------------------------------------------------
# CRC chain -- from the bootloader description, not from the kit's walker.
# ------------------------------------------------------------------------------------------------
def u16(b, o):
    return b[o] | (b[o + 1] << 8)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def chain(img, bridge):
    """Yield (start, end) blocks.  bridge=True replays the bootloader (0xC6000 -> [0x13000,0xC4FFC))."""
    bs, bl = u16(img, END - 8) << 12, (u16(img, END - 6) << 12) - 4
    seen = set()
    while True:
        assert bs not in seen
        seen.add(bs)
        yield bs, bs + bl
        if bs == START:
            return
        if bridge and bs == 0xC6000:
            bs, bl = START, 0xB1FFC
            continue
        bs, bl = u16(img, bs - 8) << 12, (u16(img, bs - 6) << 12) - 4


def crc_check(img, bridge):
    n = bad = 0
    for s, e in chain(img, bridge):
        n += 1
        if zlib.crc32(img[s:e]) & 0xFFFFFFFF != u32(img, e):
            bad += 1
    return n, bad


# ------------------------------------------------------------------------------------------------
# x31 .rwd -- own parser, brute-forced cipher.
# ------------------------------------------------------------------------------------------------
OPS = [operator.xor, operator.and_, operator.or_, operator.add, operator.sub, operator.mul, operator.floordiv,
       operator.mod]


def parse_x31(raw):
    assert raw[:3] == b"1\r\n"
    i, hdr = 3, []
    for _ in range(6):
        tag = raw[i:i + 3]
        i += 3
        vals = []
        while raw[i:i + 3] != tag:
            j = raw.index(b"\r\n", i)
            vals.append(raw[i:j])
            i = j + 2
        i += 3
        hdr.append((tag[:1], vals))
    body, trailer = raw[i:-4], raw[-4:]
    assert len(body) % 130 == 0, len(body)
    chunks = [(((body[k] << 12) | (body[k + 1] << 4)), body[k + 2:k + 130]) for k in range(0, len(body), 130)]
    return hdr, chunks, trailer, i


def crack(enc_chunk, known_plain, keyvals):
    for keys in set(itertools.permutations(keyvals)):
        for ops in itertools.product(range(8), repeat=3):
            tbl = bytearray(256)
            ok = True
            for e in range(256):
                try:
                    tbl[e] = OPS[ops[2]](OPS[ops[1]](OPS[ops[0]](e, keys[0]), keys[1]), keys[2]) & 0xFF
                except ZeroDivisionError:
                    ok = False
                    break
            if ok and len(set(tbl)) == 256 and enc_chunk.translate(bytes(tbl)) == known_plain:
                return bytes(tbl), keys, ops
    return None, None, None


# ================================================================================================
def main():
    base = V282.read_bytes()
    print("[0] inputs")
    must(hashlib.sha256(base).hexdigest() == CLAIM_BASE, "V282 base sha256 == recorded")
    must(len(base) == END, "base is 1 MiB")

    print("[1] INDEPENDENT REBUILD from the declared edits (own assembler, own CRC)")
    img = bytearray(base)
    notch = assemble(NOTCH_SRC, NOTCH_AT)
    tail = assemble(TAIL_SRC, TAIL_AT)
    must(len(notch) == 140, f"notch cave assembles to {len(notch)} B (claim 140)")
    must(len(tail) == 28, f"tail assembles to {len(tail)} B (claim 28)")
    hook_jr, exit_jr = fV_jr(HOOK, NOTCH_AT), fV_jr(EXIT, TAIL_AT)
    must(hook_jr.hex() == "89078caa", f"hook jr 0x2A174->0xC4C00 = {hook_jr.hex()} (worked: d=0x9AA8C -> 0789 aa8c)")
    must(exit_jr.hex() == "80070600", f"exit jr 0xC4BD6->0xC4BDC = {exit_jr.hex()} (d=6)")
    must(notch[-4:].hex() == "b607f054", f"return jr 0xC4C88->0x2A178 = {notch[-4:].hex()} (d=-0x9AA10 -> 0x3651F0)")
    must(base[HOOK:HOOK + 4].hex() == "e53fef73", "hook site in V282 is ld.hu 0x73ee,tp,r7 (e53fef73)")
    must(base[EXIT:EXIT + 4].hex() == "7f00ffff", "0xC4BD6 in V282 is jmp [lp] + ff ff")
    must(all(b == 0xFF for b in base[TAIL_AT:TAIL_AT + 28]) and all(b == 0xFF for b in base[NOTCH_AT:NOTCH_AT + 140]),
         "both cave targets are all-0xFF in V282")
    must(notch[-8:-4] == base[HOOK:HOOK + 4], "the displaced ld.hu is replicated byte-identically as the cave's penultimate instr")
    for at, blob in ((HOOK, hook_jr), (NOTCH_AT, notch), (EXIT, exit_jr), (TAIL_AT, tail)):
        img[at:at + len(blob)] = blob
    for cell, (old, new) in CAL.items():
        must(u16(img, cell) == old, f"0x{cell:05X} was {old} in V282")
        struct.pack_into("<H", img, cell, new)
    # recompute the two trailers myself
    c1 = zlib.crc32(img[0x13000:0xC4FFC]) & 0xFFFFFFFF
    c2 = zlib.crc32(img[0xC6000:0xC6FFC]) & 0xFFFFFFFF
    struct.pack_into("<I", img, 0xC4FFC, c1)
    struct.pack_into("<I", img, 0xC6FFC, c2)
    print(f"       recomputed CRC cells: 0xC4FFC = {img[0xC4FFC:0xC5000].hex()} (0x{c1:08X}), 0xC6FFC = {img[0xC6FFC:0xC7000].hex()} (0x{c2:08X})")
    my_sha = hashlib.sha256(bytes(img)).hexdigest()
    print(f"       rebuilt sha256 = {my_sha}")
    must(my_sha == CLAIM_IMG, "REBUILT image sha256 == claimed f0c10c29...")

    print("[2] the image on disk")
    disk = V289_IMG.read_bytes()
    must(hashlib.sha256(disk).hexdigest() == CLAIM_IMG, "on-disk image sha256 == claimed")
    must(disk == bytes(img), "on-disk image == my rebuild, byte for byte")
    # which blocks own the edits, by my own chain walk
    blocks = list(chain(disk, bridge=False))
    owners = sorted({(s, e) for s, e in blocks for at, n in ALLOWED[:6] for o in range(at, at + n) if s <= o < e})
    must(owners == [(0x13000, 0xC4FFC), (0xC6000, 0xC6FFC)], f"edited bytes are owned by exactly {[(hex(s), hex(e)) for s, e in owners]}")
    must(u32(disk, 0xC4FFC) == c1 and u32(disk, 0xC6FFC) == c2, "both stored CRC cells equal my recomputation")
    n50, bad50 = crc_check(disk, bridge=False)
    n49, bad49 = crc_check(disk, bridge=True)
    must((n50, bad50) == (50, 0), f"full linked-list chain: {n50} blocks, {bad50} mismatches")
    must((n49, bad49) == (49, 0), f"bootloader replay (0xC6000 bridge): {n49} blocks, {bad49} mismatches")
    skipped = {(s, e) for s, e in chain(disk, False)} - {(s, e) for s, e in chain(disk, True)}
    must(skipped == {(0xC5000, 0xC5FFC)}, f"the one block the bootloader skips is {[(hex(s), hex(e)) for s, e in skipped]}")
    must(disk[0xC4FF0:0xC4FFC].hex() == "010101010000c6001300b200", "0xC4FF0-0xC4FFB chain fields untouched")

    print("[3] FULL-FILE DIFF V282 -> V289")
    d = [i for i in range(len(base)) if base[i] != disk[i]]
    runs, cur = [], None
    for a in d:
        if cur and a == cur[1]:
            cur[1] = a + 1
        else:
            cur = [a, a + 1]
            runs.append(cur)
    allowed = set()
    for at, n in ALLOWED:
        allowed |= set(range(at, at + n))
    for s, e in runs:
        print(f"       [0x{s:06X},0x{e:06X}) {e - s:3d} B  {base[s:e].hex() if e - s <= 12 else '...'} -> {disk[s:e].hex() if e - s <= 12 else '...'}")
    outside = [a for a in d if a not in allowed]
    must(outside == [], f"{len(d)} differing bytes in {len(runs)} runs; OUTSIDE the allowed set: {[hex(a) for a in outside]}")
    must(len(d) == 185 and len(runs) == 10, f"count: {len(d)} bytes / {len(runs)} runs (script claims 185 / 10)")
    touched188 = allowed | {0xC63E9}          # the builder writes 0xC63E8 as a halfword: 188 touched
    touched_eq = sorted(touched188 - set(d))
    print(f"       touched-but-unchanged bytes: {[hex(a) for a in touched_eq]}"
          f" (values {[hex(disk[a]) for a in touched_eq]})")
    must(touched_eq == [0xC4C0A, 0xC4C20, 0xC63E9], "exactly 3 of 188 touched bytes equal their old value: TWO cave 0xFF bytes"
                                                   " (0xC4C0A, 0xC4C20) + the 0x03 high byte of 0xC63E8 -- NOT 'three notch-cave bytes'")
    must(disk[0xC4BF8:0xC4C00] == b"\xff" * 8 and disk[0xC4BDA:0xC4BDC] == b"\xff\xff", "fillers 0xC4BDA-DB and 0xC4BF8-FF still 0xFF")
    must(disk[0xC4B34:0xC4BD6] == base[0xC4B34:0xC4BD6], "the five flown 0x14A rungs 0xC4B34-0xC4BD5 are byte-identical")
    must(disk[0xC4C8C:0xC4FF0] == b"\xff" * (0xC4FF0 - 0xC4C8C), "0xC4C8C-0xC4FEF still free (0xFF)")

    print("[4] the .rwd on disk, decoded with my own parser and a brute-forced cipher")
    raw = V289_RWD.read_bytes()
    must(hashlib.sha256(raw).hexdigest() == CLAIM_RWD, "on-disk .rwd sha256 == claimed 20fa1757...")
    hdr, chunks, trailer, body_off = parse_x31(raw)
    must(struct.unpack("<I", trailer)[0] == sum(raw[:-4]) & 0xFFFFFFFF, f"file trailer {trailer.hex()} == LE sum32 of the body")
    print("       headers:", [(t, v) for t, v in hdr])
    keyhex = [v for t, v in hdr if t == b"&"][0][0]
    keyvals = list(bytes.fromhex(keyhex.decode()))
    addrs = [a for a, _ in chunks]
    must(addrs == list(range(START, END, 128)), f"chunk addresses are contiguous 0x13000..0xFFF80 step 128 ({len(chunks)} chunks)")
    tbl, keys, ops = crack(chunks[0][1], disk[START:START + 128], keyvals)
    must(tbl is not None, f"cipher recovered by brute force: keys {[hex(k) for k in keys] if keys else None} ops {ops}")
    plain = b"".join(c.translate(tbl) for _, c in chunks)
    must(plain == disk[START:END], "decoded .rwd payload == on-disk image over [0x13000,0x100000)")
    must(plain == bytes(img)[START:END], "decoded .rwd payload == MY REBUILD over [0x13000,0x100000)")
    parts = [v for t, v in hdr if t == b"/"][0]
    must(b"39990-TVA,A160" in parts or b"39990-TVA-A160" in parts, f"part-number header carries the TVA-A160 target: {parts}")
    if V288_RWD.exists():
        raw288 = V288_RWD.read_bytes()
        _, _, _, off288 = parse_x31(raw288)
        must(raw288[:off288] == raw[:body_off], "header block identical to the V288 rev 2 .rwd's")

    print("[5] disk hygiene")
    rwds = [p.name for p in (ROOT / "flashing-2020accord" / "rwd").glob("*V289*")]
    imgs = [p.name for p in (ROOT / "analysis-2020accord").glob("*v289*")] + [p.name for p in (ROOT / "analysis-2020accord").glob("*V289*")]
    must(len(rwds) == 1 and not rwds[0].startswith("SUPERSEDED"), f"exactly one V289 .rwd in the firmware root: {rwds}")
    must(len(set(imgs)) == 1, f"exactly one V289 image in the firmware root: {sorted(set(imgs))}")
    must(V289_RWD.name.split("-0x13000")[0].replace("39990-TVA,A160-", "") == V289_IMG.name[len("_v289_"):-len("_plain_image.bin")],
         "the .rwd filename tag == the image filename tag")

    print("[6] tag honesty: the realised notch centre from the integer coefficients IN THE IMAGE")
    import math
    b0, b1 = 16048, -31842
    # confirm the coefficients from the bytes: movea imm16 at 0xC4C0E (b0), 0xC4C3C (b1), 0xC4C26 (a2)
    mb0 = struct.unpack_from("<h", disk, 0xC4C0E + 2)[0]
    mb1 = struct.unpack_from("<h", disk, 0xC4C3C + 2)[0]
    ma2 = struct.unpack_from("<h", disk, 0xC4C26 + 2)[0]
    must((mb0, mb1, ma2) == (16048, -31842, 15712), f"coefficients read from the image: b0 {mb0}, b1=a1 {mb1}, a2 {ma2}")
    f0 = math.acos(-mb1 / (2 * mb0)) * 1000 / (2 * math.pi)
    fp = math.acos(-mb1 / (2 * math.sqrt(16384 * ma2))) * 1000 / (2 * math.pi)
    print(f"       zero (notch centre) = {f0:.4f} Hz ; pole angle = {fp:.4f} Hz ; tag says 20.05HZ ; design 20.05")
    must(abs(f0 - 20.05) < 0.05, f"tag 20.05HZ vs realised {f0:.3f} Hz: |delta| = {abs(f0 - 20.05):.3f} Hz (< the 0.05 Hz Q14 grid)")

    print()
    print("RESULT:", "ALL REPRODUCED" if not fails else f"{len(fails)} FAILURE(S): {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
