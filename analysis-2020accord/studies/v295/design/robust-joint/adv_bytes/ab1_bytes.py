# -*- coding: utf-8 -*-
"""ab1_bytes.py -- ADV bytes+instrument vs candidate A (robust-joint): the cell, its readers, the CRC, cal-only.

Everything from the V294 IMAGE (sha256-asserted), little-endian.  My own raw V850 scanner (Format VII 4-byte incl.
ld.bu bit-5 parity and hw2 bit-0 discriminators, Format XIV 6-byte disp23, mov imm32, movea/addi/movhi, LE32
absolutes), POSITIVE-CONTROLLED before any null is read.  The candidate image exists ONLY IN MEMORY here (to count
the bytes a build would change and to re-verify the CRC chain) -- nothing is written to disk.
ANALYSIS ONLY."""
import hashlib
import struct
import sys
import zlib

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V294 = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
             "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V294_SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
STOCK = FW + "stock_fw_dump/code.bin"
TP, GP = 0xBF000, 0xFEDF8000

img = open(V294, "rb").read()
assert hashlib.sha256(img).hexdigest() == V294_SHA, "V294 hash"
stock = open(STOCK, "rb").read()
print("V294 sha256 OK", len(img))


def u16(b, o): return b[o] | (b[o + 1] << 8)
def s16(v): return v - 0x10000 if v & 0x8000 else v
def u32(b, o): return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)
def sext(v, n): return v - (1 << n) if v & (1 << (n - 1)) else v


# ---------------------------------------------------------------- cells
cells = {"a 0xC63E8": (0xC63E8, "s16"), "b 0xC63EA": (0xC63EA, "u16"), "C 0xC62E6": (0xC62E6, "u16"),
         "lag_a 0xC63EC": (0xC63EC, "s16"), "lag_b 0xC63EE": (0xC63EE, "u16"), "Ki 0xC63E6": (0xC63E6, "u16"),
         "Dclamp 0xC61B6": (0xC61B6, "u16"), "Pclamp 0xC61BC": (0xC61BC, "u16"), "Sclamp 0xC61BE": (0xC61BE, "s16"),
         "lane 0xC61B4": (0xC61B4, "s16"), "fwd 0xC61B2": (0xC61B2, "s16"), "gain 0xC6CD0": (0xC6CD0, "s16"),
         "deadband 0xC62E4": (0xC62E4, "u16")}
print("\n[1] cells read from the V294 image (LE):")
for k, (o, t) in cells.items():
    v = u16(img, o)
    print("   %-16s bytes %02x %02x -> %d" % (k, img[o], img[o + 1], s16(v) if t == "s16" else v))
assert u16(img, 0xC63EA) == 567 and img[0xC63EA:0xC63EC] == bytes([0x37, 0x02])
print("   1106 LE =", struct.pack("<H", 1106).hex(" "), "(design says 52 04)")


# ---------------------------------------------------------------- decoder (loads/stores + address formers)
def decode(b, o):
    """returns list of (kind, width, base_reg, disp_or_imm, length) for the instruction STARTING at o (even)."""
    out = []
    hw1 = u16(b, o)
    hw2 = u16(b, o + 2) if o + 3 < len(b) else 0
    op6 = (hw1 >> 5) & 0x3F
    r1 = hw1 & 0x1F
    r2 = hw1 >> 11
    if op6 == 0x38:
        out.append(("ld.b", 1, r1, sext(hw2, 16), 4))
    elif op6 == 0x39:
        out.append(("ld.w", 4, r1, sext(hw2 & ~1, 16), 4) if hw2 & 1 else ("ld.h", 2, r1, sext(hw2, 16), 4))
    elif op6 == 0x3A:
        out.append(("st.b", 1, r1, sext(hw2, 16), 4))
    elif op6 == 0x3B:
        out.append(("st.w", 4, r1, sext(hw2 & ~1, 16), 4) if hw2 & 1 else ("st.h", 2, r1, sext(hw2, 16), 4))
    elif op6 in (0x3C, 0x3D) and (hw2 & 1) and r2 != 0:
        out.append(("ld.bu", 1, r1, sext((hw2 & ~1) | (op6 & 1), 16), 4))
    elif op6 == 0x3F and (hw2 & 1) and r2 != 0:
        out.append(("ld.hu", 2, r1, sext(hw2 & ~1, 16), 4))
    elif op6 == 0x31:
        out.append(("movea", 0, r1, sext(hw2, 16), 4))
    elif op6 == 0x30:
        out.append(("addi", 0, r1, sext(hw2, 16), 4))
    elif op6 == 0x32:
        out.append(("movhi", 0, r1, hw2, 4))
    if (hw1 & 0xFFE0) == 0x0620 and o + 6 <= len(b):
        out.append(("mov32", 0, 0, u32(b, o + 2), 6))
    grp = hw1 & 0xFFE0
    if grp in (0x0780, 0x07A0) and o + 6 <= len(b):
        hw3 = u16(b, o + 4)
        lo4, lo5 = hw2 & 0xF, hw2 & 0x1F
        byte_d = sext((hw3 << 7) | ((hw2 >> 4) & 0x7F), 23)
        hw_d = sext((hw3 << 7) | (((hw2 >> 5) & 0x3F) << 1), 23)
        if grp == 0x0780:
            if lo4 == 0x5: out.append(("ld.b/23", 1, r1, byte_d, 6))
            elif lo5 == 0x07: out.append(("ld.h/23", 2, r1, hw_d, 6))
            elif lo5 == 0x09: out.append(("ld.w/23", 4, r1, hw_d, 6))
            elif lo4 == 0xD: out.append(("st.b/23", 1, r1, byte_d, 6))
            elif lo5 == 0x0F: out.append(("st.w/23", 4, r1, hw_d, 6))
        else:
            if lo4 == 0x5: out.append(("ld.bu/23", 1, r1, byte_d, 6))
            elif lo5 == 0x07: out.append(("ld.hu/23", 2, r1, hw_d, 6))
            elif lo5 == 0x0D: out.append(("st.h/23", 2, r1, hw_d, 6))
    return out


def scan(b, lo=0x13000, hi=0x100000):
    for o in range(lo, hi - 6, 2):
        for d in decode(b, o):
            yield o, d


def overlaps(disp, width, lo, hi):
    return width > 0 and disp <= hi and disp + width - 1 >= lo


ALL = list(scan(img))
print("\n[2] raw scan: %d candidate decodes over [0x13000,0x100000)" % len(ALL))

# ---- positive controls FIRST
ctl = {
    "ld.hu tp+0x73EA @0x28F86 (b reader)": lambda o, d: o == 0x28F86 and d[0] == "ld.hu" and d[2] == 5 and d[3] == 0x73EA,
    "ld.h tp+0x73E8 @0x28F8A (a reader)": lambda o, d: o == 0x28F8A and d[0] == "ld.h" and d[2] == 5 and d[3] == 0x73E8,
    "6-byte gp-0x6752 @0x48E56": lambda o, d: o == 0x48E56 and d[0].endswith("/23") and d[2] == 4 and d[3] == -0x6752,
    "mov imm32 0xCB994 @0x29DC6": lambda o, d: o == 0x29DC6 and d[0] == "mov32" and d[3] == 0xCB994,
    "ld.hu tp+0x72E6 (C reader) somewhere": lambda o, d: d[0] == "ld.hu" and d[2] == 5 and d[3] == 0x72E6,
    "ld.w gp-0x3d30 (s load) somewhere": lambda o, d: d[0] == "ld.w" and d[2] == 4 and d[3] == -0x3D30,
    "st.h gp-0x6a34 somewhere (the |r26>>5| store)": lambda o, d: d[0].startswith("st.h") and d[2] == 4 and d[3] == -0x6A34,
}
print("   positive controls:")
allok = True
for nm, f in ctl.items():
    hits = [(o, d) for o, d in ALL if f(o, d)]
    ok = len(hits) > 0
    allok &= ok
    print("     %-46s %s  %s" % (nm, "PASS" if ok else "FAIL", ["0x%X" % o for o, _ in hits][:6]))
assert allok, "a positive control failed -- nulls below are void"


def census(name, base_reg, lo, hi):
    hits = [(o, d) for o, d in ALL if d[2] == base_reg and d[1] > 0 and overlaps(d[3], d[1], lo, hi)]
    print("   %s: %d accesses" % (name, len(hits)))
    for o, d in hits:
        print("      0x%05X %-9s w%d %s%+#x" % (o, d[0], d[1], {4: "gp", 5: "tp"}[base_reg], d[3]))
    return hits


print("\n[3] accesses overlapping the b cell (tp+0x73EA..0x73EB), any width, any encoding:")
hb = census("tp+[0x73EA,0x73EB]", 5, 0x73EA, 0x73EB)
print("   (and the a cell, for the ld.w-both-cells case) :")
ha = census("tp+[0x73E8,0x73E9]", 5, 0x73E8, 0x73E9)

print("\n[4] address-forming references that could reach 0xC63EA register-indirectly:")
abs_hits = [o for o in range(0, len(img) - 3) if 0xC63E0 <= u32(img, o) <= 0xC63EF]
print("   LE32 constants in [0xC63E0,0xC63EF] anywhere in the image: %s" % ["0x%X" % o for o in abs_hits])
m32 = [(o, d[3]) for o, d in ALL if d[0] == "mov32" and 0xC6000 <= d[3] <= 0xC63EB]
print("   mov imm32 in [0xC6000,0xC63EB]: %s" % [("0x%X" % o, "0x%X" % v) for o, v in m32])
tpform = [(o, d[0], d[3]) for o, d in ALL if d[0] in ("movea", "addi") and d[2] == 5 and 0x7000 <= d[3] <= 0x73EB]
print("   movea/addi imm, tp -> ptr into tp+[0x7000,0x73EB]: %d  %s" % (len(tpform), [("0x%X" % o, m, "0x%X" % v) for o, m, v in tpform][:20]))
mh = [o for o, d in ALL if d[0] == "movhi" and d[3] in (0x000C,)]
near = []
for o in mh:
    for q in range(o + 4, o + 24, 2):
        for d in decode(img, q):
            if d[0] in ("movea", "addi") and 0x6000 <= (d[3] & 0xFFFF) <= 0x63EB:
                near.append(("0x%X" % o, "0x%X" % q, d[0], "0x%X" % (0xC0000 + d[3])))
print("   movhi 0x000C sites: %d; followed (<=5 insns) by movea/addi 0x6000..0x63EB: %s" % (len(mh), near))
# ep (r30) assignments
ep = [(o, d) for o, d in ALL if d[0] in ("movea", "mov32", "movhi", "addi") and (u16(img, o) >> 11) == 30]
print("   instructions writing ep (r30) via movea/addi/movhi (reg2=30): %d" % len(ep))
epv = sorted({("%s" % d[0], d[3] if d[0] != "movea" else d[3]) for o, d in ep})
print("     distinct (op, imm): %s" % epv[:30])
mov32_ep = [(o, d[3]) for o, d in ALL if d[0] == "mov32" and (u16(img, o) & 0x1F) == 30]
print("   mov imm32 -> ep: %s" % [("0x%X" % o, "0x%X" % v) for o, v in mov32_ep][:20])
mov_ep = sorted({u16(img, o) & 0x1F for o in range(0x13000, 0xC0000, 2)
                 if ((u16(img, o) >> 5) & 0x3F) == 0 and (u16(img, o) >> 11) == 30})
print("   Format-I 'mov rX, ep' source registers seen (raw, may include data): %s" % mov_ep)

print("\n[5] gp cells the b edit scales: r26's published |r26>>5| (gp-0x6a34), the fb state s (gp-0x3d30), sentinel (gp-0x3d2c)")
h6a34 = census("gp-0x6a34 (|r26>>5|, short)", 4, -0x6A34, -0x6A33)
h3d30 = census("gp-0x3d30 (s, word)", 4, -0x3D30, -0x3D2D)
h3d2c = census("gp-0x3d2c (sentinel, byte)", 4, -0x3D2C, -0x3D2C)
abs6a34 = [o for o in range(0, len(img) - 3) if u32(img, o) in (GP - 0x6A34, GP - 0x6A34 - 2, GP - 0x3D30)]
print("   LE32 absolute GP-0x6a34 / GP-0x6a36 / GP-0x3d30 anywhere: %s" % ["0x%X" % o for o in abs6a34])

print("\n[6] code-region diff V294 vs stock over [0x13000, 0xC0000) (validity of stock Ghidra xrefs for V294):")
diff = [o for o in range(0x13000, 0xC0000) if img[o] != stock[o]]
runs = []
for o in diff:
    if runs and o <= runs[-1][1] + 1:
        runs[-1][1] = o
    else:
        runs.append([o, o])
print("   %d bytes in %d runs: %s" % (len(diff), len(runs), ["0x%X-0x%X" % (a, b) for a, b in runs][:40]))

# ---------------------------------------------------------------- the CRC chain + the candidate (in memory only)
def blocks(b, region_start=0x13000, region_len=0xED000):
    END = region_start + region_len
    bs, bl = u16(b, END - 8) << 12, (u16(b, END - 6) << 12) - 4
    out = []
    for _ in range(200):
        out.append((bs, bs + bl))
        if bs == region_start:
            break
        nsp, nn = u16(b, bs - 8), u16(b, bs - 6)
        if (nsp << 12) == bs:
            break
        bs, bl = nsp << 12, (nn << 12) - 4
    return out


BL = blocks(img)
print("\n[7] CRC blocks (linked list, no bridge): %d" % len(BL))
bad = [(a, e) for a, e in BL if (zlib.crc32(img[a:e]) & 0xFFFFFFFF) != u32(img, e)]
print("   V294 blocks with a CRC mismatch: %s" % bad)
cov = [(a, e) for a, e in BL if a <= 0xC63EA < e]
print("   block(s) covering 0xC63EA: %s" % [("0x%X" % a, "0x%X" % e) for a, e in cov])
# bootloader bridge: [0x13000, 0x13000+0xB1FFC) main block -- does it also cover 0xC63EA?
print("   bootloader main bridge block [0x13000, 0xC4FFC) covers 0xC63EA: %s" % (0x13000 <= 0xC63EA < 0xC4FFC))
cand = bytearray(img)
struct.pack_into("<H", cand, 0xC63EA, 1106)
for a, e in cov:
    struct.pack_into("<I", cand, e, zlib.crc32(bytes(cand[a:e])) & 0xFFFFFFFF)
d2 = [o for o in range(len(img)) if cand[o] != img[o]]
print("   in-memory candidate: %d bytes differ from V294: %s" % (len(d2), ["0x%X" % o for o in d2]))
bad2 = [(a, e) for a, e in blocks(bytes(cand)) if (zlib.crc32(cand[a:e]) & 0xFFFFFFFF) != u32(cand, e)]
print("   candidate blocks with CRC mismatch (full chain): %s" % bad2)
print("   candidate sha256 (in memory, NOT written): %s" % hashlib.sha256(bytes(cand)).hexdigest())
# second method: the kit's own verifier
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/lib")
import contextlib, io  # noqa: E401,E402
import verify_bootloader_crc as VB  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    f1 = VB.walk(bytes(cand)); f2 = VB.walk_all_blocks(bytes(cand))
print("   kit verifier on the in-memory candidate: bootloader walk fails %d, full chain fails %d" % (f1, f2))
# the V293 -> V294 precedent in the same block
v293 = open(FW + "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
for a, e in cov:
    dd = [o for o in range(a, e + 4) if v293[o] != img[o]]
    print("   precedent: V293->V294 changed %d bytes inside that block incl. its trailer (flown on r71b): %s"
          % (len(dd), ["0x%X" % o for o in dd][:24]))
