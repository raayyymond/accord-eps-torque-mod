# -*- coding: utf-8 -*-
"""ADV-C part 1 -- V295 build audit, INDEPENDENT of the kit: no kit module is imported.
hashlib / struct / glob / os only.  My own CRC-32 (table built here), my own chain walker (structure taken from the
bootloader decompile FUN_0000b006 and the constants read from the stock bytes at 0xB070..0xB083), my own edit, my
own .rwd decoder (substitution learned from the FLOWN V294 pair, cross-checked against the header keys).
ANALYSIS ONLY -- writes nothing to the firmware dir."""
import glob
import hashlib
import os
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares"
AN = FW + "/analysis-2020accord"
RWD = FW + "/flashing-2020accord/rwd"
START, END, CODE_END = 0x13000, 0x100000, 0xC0000

EXP = dict(
    stock="3f1d55a98aac6e73631d94d583065c57d83dd3a86df0e7d06e56a3feb58fd822",
    v293="f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17",
    v294="3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85",
    v295="5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
    v294rwd="a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a",
    v295rwd="f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87",
)
FAILS, NOTES = [], []


def chk(cond, msg):
    print(("  [ok]   " if cond else "  [FAIL] ") + msg)
    if not cond:
        FAILS.append(msg)


def one(pattern):
    g = [p for p in glob.glob(pattern) if not os.path.basename(p).upper().startswith(("SUPERSEDED", "DO-NOT", "RATCHET"))]
    return g


def sha(b):
    return hashlib.sha256(b).hexdigest()


u16 = lambda b, o: b[o] | (b[o + 1] << 8)                                        # noqa: E731
s16 = lambda b, o: u16(b, o) - 0x10000 if u16(b, o) & 0x8000 else u16(b, o)      # noqa: E731
u32 = lambda b, o: b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)  # noqa: E731

print("=" * 110)
print(" [A] ARTIFACTS ON DISK")
imgs295 = glob.glob(AN + "/*v295*") + glob.glob(AN + "/*V295*")
imgs295 = sorted(set(imgs295))
rwds295 = sorted(set(glob.glob(RWD + "/*V295*") + glob.glob(RWD + "/*v295*")))
rwds294 = sorted(set(glob.glob(RWD + "/*-V294-*")))
print("  V295 image files:", [os.path.basename(p) for p in imgs295])
print("  V295 rwd files  :", [os.path.basename(p) for p in rwds295])
print("  V294 rwd files  :", [os.path.basename(p) for p in rwds294])
chk(len(imgs295) == 1 and len(rwds295) == 1, "exactly one V295 plain image and one V295 rwd on disk (any prefix)")
chk(len(rwds294) == 1, "exactly one V294 rwd on disk")
P = dict(
    stock=AN + "/stock_fw_dump/code.bin",
    v293=one(AN + "/_v293_*_plain_image.bin")[0],
    v294=one(AN + "/_v294_*_plain_image.bin")[0],
    v295=imgs295[0],
    v294rwd=rwds294[0],
    v295rwd=rwds295[0],
)
D = {k: open(v, "rb").read() for k, v in P.items()}
for k in ("stock", "v293", "v294", "v295", "v294rwd", "v295rwd"):
    h = sha(D[k])
    chk(h == EXP[k], f"{k:8s} sha256 {h}  ({len(D[k]):,} B)")
stock, v293, v294, v295 = D["stock"], D["v293"], D["v294"], D["v295"]

# ---------------------------------------------------------------------------------------------------------
print("\n [B] CRC SCHEME, FROM THE BOOTLOADER (stock code.bin, below 0x13000)")


def dec_fmt6(b, o):
    """Format VI: hw1 = reg2<<11 | op6<<5 | reg1 ; hw2 = imm16.  movea op6 0x31 (sign-ext), movhi 0x32."""
    hw1, hw2 = u16(b, o), u16(b, o + 2)
    return (hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11, hw2


consts = []
for o in (0xB070, 0xB078, 0xB080):          # movea lo ; movhi hi  (pairs; reg chain checked)
    op_a, r1a, r2a, lo = dec_fmt6(stock, o)
    op_h, r1h, r2h, hi = dec_fmt6(stock, o + 4) if dec_fmt6(stock, o + 2)[0] != 0x32 else dec_fmt6(stock, o + 2)
    consts.append((o, op_a, lo, op_h, hi))
print("  raw halfwords 0xB06C..0xB088:", " ".join(f"{u16(stock, a):04x}" for a in range(0xB06C, 0xB088, 2)))
# Decode every Format-VI instruction in 0xB060..0xB090 and pair movhi+movea on the same register
insns = []
o = 0xB060
movimm = {}
while o < 0xB090:
    if (u16(stock, o) & 0xFFE0) == 0x0620:                 # Format VI 48-bit: mov imm32, reg1
        r = u16(stock, o) & 0x1F
        v = u32(stock, o + 2)
        movimm[o] = (r, v)
        print(f"    0x{o:05X} mov 0x{v:X}, r{r}   (6-byte form)")
        o += 6
        continue
    op6, r1, r2, imm = dec_fmt6(stock, o)
    if op6 in (0x31, 0x32):
        insns.append((o, {0x31: "movea", 0x32: "movhi"}[op6], r1, r2, imm))
        o += 4
    else:
        o += 2
for i in insns:
    print(f"    0x{i[0]:05X} {i[1]} 0x{i[4]:04X}, r{i[2]}, r{i[3]}")
vals = {}
for i, (oa, ka, r1a, r2a, ia) in enumerate(insns):
    for (ob, kb, r1b, r2b, ib) in insns[i + 1:i + 3]:
        if ka == "movea" and kb == "movhi" and r2a == r1b == r2b:
            v = ((ib << 16) + (ia - 0x10000 if ia & 0x8000 else ia)) & 0xFFFFFFFF
            vals[oa] = v
        if ka == "movhi" and kb == "movea" and r2a == r1b:
            v = ((ia << 16) + (ib - 0x10000 if ib & 0x8000 else ib)) & 0xFFFFFFFF
            vals[oa] = v
for k, (r, v) in movimm.items():
    vals[k] = v
print("  constants formed:", {hex(k): hex(v) for k, v in vals.items()})
NOTES.append("lib/verify_bootloader_crc.py docstring calls 0xB070/0xB072 'movea 0x6000 / movhi 0x000C'; the bytes are a "
              "6-byte `mov imm32` at 0xB06E (0622 6000 000c), likewise 0xB078 (063d) and 0xB07E (063c). Same constants.")
BRIDGE_FROM, BRIDGE_TO, BRIDGE_LEN = 0xC6000, 0x13000, 0xB1FFC
chk({BRIDGE_FROM, BRIDGE_TO, BRIDGE_LEN} <= set(vals.values()),
    "bootloader forms 0xC6000 (bridge compare), 0x13000 (main start), 0xB1FFC (main len) -- read from the bytes")

# my CRC-32: reflected, poly 0xEDB88320, init 0xFFFFFFFF, final xor 0xFFFFFFFF, 32-bit LE words = bytes in order
TBL = []
for n in range(256):
    c = n
    for _ in range(8):
        c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
    TBL.append(c)


def crc32(buf):
    c = 0xFFFFFFFF
    for x in buf:
        c = TBL[(c ^ x) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF


chk(crc32(b"123456789") == 0xCBF43926, "my CRC-32 check value crc32('123456789') == 0xCBF43926 (CRC-32/ISO-HDLC)")


def chain(img, bridge):
    """FUN_0000b006 structure: head descriptor at END-8 (u16 start page) / END-6 (u16 page count); len = pages*4K - 4;
    trailer u32 LE at start+len; next = descriptor at start-8/-6; stop at region start; bridge 0xC6000 -> main."""
    bs, bl = u16(img, END - 8) << 12, (u16(img, END - 6) << 12) - 4
    out = []
    while True:
        out.append((bs, bs + bl))
        if bs == START or len(out) > 300:
            break
        if bridge and bs == BRIDGE_FROM:
            bs, bl = BRIDGE_TO, BRIDGE_LEN
            continue
        bs, bl = u16(img, bs - 8) << 12, (u16(img, bs - 6) << 12) - 4
    return out


def crc_report(img, bridge):
    res = [(b0, b1, crc32(img[b0:b1]), u32(img, b1)) for b0, b1 in chain(img, bridge)]
    return res, sum(1 for r in res if r[2] == r[3])


STOCK_FULL = None
for name in ("stock", "v293", "v294", "v295"):
    img = D[name]
    rf, okf = crc_report(img, False)
    rb, okb = crc_report(img, True)
    chk(okf == len(rf) and okb == len(rb), f"{name:6s} full chain {okf}/{len(rf)}   bootloader walk {okb}/{len(rb)}")
    if name == "stock":
        STOCK_FULL = rf
        spans = sorted((b0, b1 + 4) for b0, b1, _, _ in rf)
        gaps = [(hex(spans[i][1]), hex(spans[i + 1][0])) for i in range(len(spans) - 1) if spans[i][1] != spans[i + 1][0]]
        chk(spans[0][0] == START and spans[-1][1] == END and not gaps,
            f"stock: {len(rf)} blocks tile [0x13000,0x100000) with no gap/overlap (trailers included)")
        main_full = [s for s in rf if s[0] == START][0]
        print(f"    main block by the stored links: [0x{main_full[0]:X},0x{main_full[1]:X});  bootloader bridge gives "
              f"[0x13000,0x{START + BRIDGE_LEN:X})")
        bset = {(b0, b1) for b0, b1, *_ in rb}
        fset = {(b0, b1) for b0, b1, *_ in rf}
        print(f"    blocks only in the full chain: {[(hex(a), hex(b)) for a, b in sorted(fset - bset)]};"
              f" only in the bootloader walk: {[(hex(a), hex(b)) for a, b in sorted(bset - fset)]}")
    if name == "v295":
        for b0, b1, c, s in rf:
            if b0 <= 0xC63EA < b1:
                print(f"    V295 owning block [0x{b0:X},0x{b1:X}) crc 0x{c:08X} stored 0x{s:08X}")
chain_same = all(chain(D[n], False) == chain(stock, False) for n in ("v293", "v294", "v295"))
chk(chain_same, "the block table (full chain) is identical on stock, V293, V294, V295 (no build moved a descriptor)")

# ---------------------------------------------------------------------------------------------------------
print("\n [C] MY OWN REBUILD: V294 + (u16 LE 1050 at the address the reader instruction resolves) + my CRC")
# tp from the image's own boot code 0x140C0..: decode by field layout
def boot_tp_gp(img):
    regs, o, log = {0: 0}, 0x140C0, []
    while o < 0x140D8:
        hw1 = u16(img, o)
        op6, r1, r2 = (hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11
        g = lambda r: regs.get(r, 0) if r else 0                                # noqa: E731
        if op6 == 0x0E:                                   # add reg1, reg2 (Format I)
            regs[r2] = (g(r1) + g(r2)) & 0xFFFFFFFF; log.append(f"add r{r1},r{r2}"); o += 2; continue
        imm = u16(img, o + 2)
        if op6 == 0x34:                                   # ori (zero-ext)
            regs[r2] = g(r1) | imm; log.append(f"ori 0x{imm:x},r{r1},r{r2}")
        elif op6 == 0x32:                                 # movhi
            regs[r2] = (g(r1) + (imm << 16)) & 0xFFFFFFFF; log.append(f"movhi 0x{imm:x},r{r1},r{r2}")
        elif op6 == 0x31:                                 # movea (sign-ext)
            regs[r2] = (g(r1) + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF; log.append(f"movea 0x{imm:x},r{r1},r{r2}")
        else:
            raise SystemExit(f"unexpected op6 {op6:#x} at 0x{o:X}")
        o += 4
    return regs, log


regs, log = boot_tp_gp(v294)
print("   boot:", " ; ".join(log), f"-> tp 0x{regs.get(5, 0):X} gp 0x{regs.get(4, 0):X}")
chk(regs.get(5) == 0xBF000 and regs.get(4) == 0xFEDF8000, "tp = 0xBF000, gp = 0xFEDF8000 from the image's own boot code")
hw1, hw2 = u16(v294, 0x28F86), u16(v294, 0x28F88)
op6, r1, r2 = (hw1 >> 5) & 0x3F, hw1 & 0x1F, hw1 >> 11
dsp = hw2 & 0xFFFE
dsp = dsp - 0x10000 if dsp & 0x8000 else dsp
CELL = (regs[r1] + dsp) & 0xFFFFFFFF
print(f"   0x28F86: hw1 {hw1:04x} hw2 {hw2:04x} op6 {op6:#x} reg1 r{r1} reg2 r{r2} hw2[0]={hw2 & 1} -> ld.hu "
      f"0x{dsp:X}[r{r1}] = 0x{CELL:X}")
chk(op6 == 0x3F and hw2 & 1 and r1 == 5 and r2 != 0 and CELL == 0xC63EA, "the reader is ld.hu tp+0x73EA -> 0xC63EA")
chk(u16(v294, CELL) == 567, f"V294 value at the cell = {u16(v294, CELL)} (567 expected)")
mine = bytearray(v294)
mine[CELL:CELL + 2] = bytes([1050 & 0xFF, 1050 >> 8])
owning = [(b0, b1) for b0, b1 in chain(bytes(mine), False) if b0 <= CELL and CELL + 2 <= b1]
chk(len(owning) == 1, f"owning block of the cell by MY walker: {[(hex(a), hex(b)) for a, b in owning]}")
recomputed = []
for b0, b1 in chain(bytes(mine), False):          # recompute EVERY trailer in the chain (a stale one would show)
    c = crc32(bytes(mine[b0:b1]))
    if u32(mine, b1) != c:
        recomputed.append((hex(b0), hex(b1), hex(u32(mine, b1)), hex(c)))
    mine[b1:b1 + 4] = struct.pack("<I", c)
print("   trailers that changed on recompute:", recomputed)
chk(len(recomputed) == 1 and recomputed[0][1] == hex(0xC6FFC), "exactly ONE trailer moved: the owning block's")
chk(sha(bytes(mine)) == EXP["v295"], f"MY REBUILD sha256 {sha(bytes(mine))} == on-disk V295")
chk(bytes(mine) == v295, "my rebuild is byte-equal to the on-disk V295 image over the WHOLE file")

# ---------------------------------------------------------------------------------------------------------
print("\n [D] FULL DIFFS")


def runs(addrs):
    out = []
    for a in sorted(addrs):
        if out and a == out[-1][1]:
            out[-1][1] = a + 1
        else:
            out.append([a, a + 1])
    return out


TRAILERS = {b1 + k for _, b1, _, _ in STOCK_FULL for k in range(4)}
d_whole = [a for a in range(len(v295)) if v295[a] != v294[a]]
print("   V295 vs V294, WHOLE FILE:", [(hex(s), hex(e - 1), v294[s:e].hex(" "), v295[s:e].hex(" ")) for s, e in runs(d_whole)])
chk(set(d_whole) == {0xC63EA, 0xC63EB, 0xC6FFC, 0xC6FFD, 0xC6FFE, 0xC6FFF}, "V295 vs V294 = exactly 0xC63EA-EB + 0xC6FFC-FF")
chk(not [a for a in d_whole if a < CODE_END], "0 bytes differ in [0, 0xC0000) (code region untouched)")
chk(v295[0xC63E8:0xC63EA] == v294[0xC63E8:0xC63EA] and v295[0xC63EC:0xC63EE] == v294[0xC63EC:0xC63EE],
    "neighbours 0xC63E8 (a) and 0xC63EC (output-lag a) unchanged")
print(f"   0xC63E0..0xC63F0 V295: {v295[0xC63E0:0xC63F0].hex(' ')}")
chk(u16(v295, 0xC63EA) == 1050, f"V295 0xC63EA LE = {u16(v295, 0xC63EA)} (bytes {v295[0xC63EA:0xC63EC].hex(' ')})")
below = [a for a in range(0, START) if v295[a] != v294[a]]
chk(not below, "below 0x13000 (filler) V295 == V294")

# V293 -> V295 attribution
KP_TBL, KD_TBL, MAP_TBL = 0xCB994, 0xCB7D4, 0xC9A88


def rec_y_bytes(img, tbl, nslots=28):
    out = set()
    for s in range(nslots):
        p = u32(img, tbl + 4 * s)
        n = u16(img, p)
        out |= set(range(p + 2 + 2 * n, p + 2 + 4 * n))
    return out


KP_Y = rec_y_bytes(v295, KP_TBL)
KD_Y = rec_y_bytes(v295, KD_TBL)
attr294 = {0x28FA4: "V294 add->subr", 0x28FA5: "V294 add->subr", 0x29D76: "V294 shl5->shl2", 0x29D77: "V294 shl5->shl2",
           0xC62E6: "V294 C 0->1024", 0xC62E7: "V294 C 0->1024", 0xC63E8: "V294 a", 0xC63E9: "V294 a",
           0xC63EA: "b (V294 1560->567, V295 ->1050)", 0xC63EB: "b (V294 1560->567, V295 ->1050)"}


def attribute(a, table):
    if a in table:
        return table[a]
    if a in KP_Y:
        return "Kp bank Y"
    if a in KD_Y:
        return "Kd bank Y"
    if a in TRAILERS:
        return "CRC trailer"
    return "UNATTRIBUTED"


d_293 = [a for a in range(START, END) if v295[a] != v293[a]]
cats = {}
for a in d_293:
    cats.setdefault(attribute(a, attr294), []).append(a)
print(f"   V295 vs V293 over [0x13000,0x100000): {len(d_293)} bytes")
for k, v in sorted(cats.items()):
    print(f"     {k:34s} {len(v):4d}  {[hex(x) for x in v[:10]]}{' ...' if len(v) > 10 else ''}")
chk("UNATTRIBUTED" not in cats, "every V293->V295 differing byte is attributed (V294's six edits, b, Kp Y, CRC trailers)")
trl = sorted({a & ~0xFFF | 0xFFC for a in cats.get("CRC trailer", [])})
print("     trailer blocks touched:", [hex(t) for t in trl])
kp_vals = sorted({s16(v295, a) for a in KP_Y if a % 2 == (min(KP_Y) % 2)})
print("     V295 Kp Y values over all 28 records:", kp_vals, " V293:", sorted({s16(v293, a) for a in KP_Y if a % 2 == (min(KP_Y) % 2)}))

# stock -> V295 : via the V282 image (the documented 1,984-byte census) + V293 + V294 + V295 deltas
v282p = one(AN + "/_v282_*_plain_image.bin")
v282 = open(v282p[0], "rb").read()
print(f"   V282 image {os.path.basename(v282p[0])[:40]}... sha {sha(v282)[:16]}")
chk(sha(v282) == "0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe", "V282 image sha == the V282 delta doc's")
S = lambda x, y: {a for a in range(START, END) if x[a] != y[a]}                    # noqa: E731
d_st_282, d_282_293, d_293_294, d_294_295 = S(stock, v282), S(v282, v293), S(v293, v294), S(v294, v295)
d_st_295 = S(stock, v295)
print(f"   |stock^V282| {len(d_st_282)}  |V282^V293| {len(d_282_293)}  |V293^V294| {len(d_293_294)}  "
      f"|V294^V295| {len(d_294_295)}  |stock^V295| {len(d_st_295)}")
chk(len(d_st_282) == 1984, "stock vs V282 = 1,984 bytes (the V282 doc's fully attributed census)")
chk(d_st_295 <= (d_st_282 | d_282_293 | d_293_294 | d_294_295), "every stock^V295 byte lies in a documented delta")
# V282 -> V293 attribution: V293's five
R24, DCL, CCL = 0xC6446, 0xC61B6, 0xC62E6
attr293 = {R24: "r24 arm", R24 + 1: "r24 arm", DCL: "D clamp", DCL + 1: "D clamp", CCL: "fb clamp C", CCL + 1: "fb clamp C"}
c293 = {}
for a in sorted(d_282_293):
    c293.setdefault(attribute(a, attr293), []).append(a)
for k, v in sorted(c293.items()):
    print(f"     V282->V293 {k:20s} {len(v):4d}  {[hex(x) for x in v[:8]]}{' ...' if len(v) > 8 else ''}")
chk("UNATTRIBUTED" not in c293, "every V282->V293 byte is one of V293's five (C, Kd Y, D clamp, Kp Y, r24) or a trailer")
reverted = sorted(d_st_282 - d_st_295)
print(f"   bytes non-stock on V282 but STOCK again on V295: {len(reverted)} {[hex(a) for a in reverted[:12]]}")
newly = sorted(d_st_295 - d_st_282)
print(f"   bytes non-stock on V295 but stock on V282: {len(newly)}")

# ---------------------------------------------------------------------------------------------------------
print("\n [E] .rwd -- my own decoder")


def parse_rwd(raw):
    assert raw[:3] == b"1\r\n", raw[:3]
    i, fields = 3, []
    for _ in range(6):
        tag = raw[i:i + 3]
        i += 3
        vals = []
        while raw[i:i + 3] != tag:
            e = raw.index(b"\r\n", i)
            vals.append(raw[i:e])
            i = e + 2
        i += 3
        fields.append((tag[:1].decode(), vals))
    hdr_len = i
    body, trailer = raw[i:-4], u32(raw, len(raw) - 4)
    return fields, hdr_len, body, trailer


def chunks(body):
    assert len(body) % 130 == 0
    return [((body[j] << 12) | (body[j + 1] << 4), body[j + 2:j + 130]) for j in range(0, len(body), 130)]


out = {}
for tag in ("v294rwd", "v295rwd"):
    raw = D[tag]
    fields, hl, body, trailer = parse_rwd(raw)
    ch = chunks(body)
    addrs = [a for a, _ in ch]
    contiguous = all(addrs[k + 1] == addrs[k] + 128 for k in range(len(addrs) - 1))
    csum = sum(raw[:-4]) & 0xFFFFFFFF
    out[tag] = (fields, hl, ch, raw)
    print(f"   {tag}: header {hl} B, fields {[(f, [v.decode('latin1') for v in vals]) for f, vals in fields]}")
    print(f"          {len(ch)} chunks [0x{addrs[0]:X},0x{addrs[-1] + 128:X}) contiguous={contiguous}; "
          f"additive checksum 0x{csum:08X} vs trailer 0x{trailer:08X}")
    chk(addrs[0] == START and addrs[-1] + 128 == END and contiguous and len(ch) == (END - START) // 128,
        f"{tag}: payload covers exactly [0x13000,0x100000) in 128-B contiguous chunks")
    chk(csum == trailer, f"{tag}: 32-bit additive checksum of every preceding byte == trailer")
# learn the substitution from the FLOWN V294 pair
learn = {}
conflict = 0
for a, enc in out["v294rwd"][2]:
    for k, e in enumerate(enc):
        p = v294[a + k]
        if learn.setdefault(e, p) != p:
            conflict += 1
chk(conflict == 0 and len(learn) == 256 and len(set(learn.values())) == 256,
    f"substitution learned from the FLOWN V294 rwd/image pair: {len(learn)} codes, bijective, {conflict} conflicts")
keys = out["v295rwd"][0][4][1][0].decode()
kb = [int(keys[i:i + 2], 16) for i in (0, 2, 4)]
ops = {"xor": lambda x, k: x ^ k, "add": lambda x, k: (x + k) & 0xFF, "sub": lambda x, k: (x - k) & 0xFF}
match = []
for o1 in ops:
    for o2 in ops:
        for o3 in ops:
            if all(ops[o3](ops[o2](ops[o1](e, kb[0]), kb[1]), kb[2]) == learn[e] for e in range(256)):
                match.append((o1, o2, o3))
print(f"   header '&' keys {keys} -> {kb}; op triples reproducing the learned table: {match}")
chk(len(match) >= 1, "the learned table is a keyed (op,op,op) cipher over the header's own keys (structure, not just a lookup)")
chk(out["v294rwd"][0] == out["v295rwd"][0] and out["v294rwd"][1] == out["v295rwd"][1],
    "V294 and V295 rwd headers byte-identical (part numbers, keys)")
dec = bytearray(b"\xff" * len(v295))
for a, enc in out["v295rwd"][2]:
    dec[a:a + 128] = bytes(learn[e] for e in enc)
chk(bytes(dec[START:END]) == v295[START:END], "MY decode of the V295 rwd == the V295 image over [0x13000,0x100000)")
r4, r5 = out["v294rwd"][3], out["v295rwd"][3]
rd = [k for k in range(len(r4)) if r4[k] != r5[k]]
chk(len(r4) == len(r5), "V294 and V295 rwd have equal length")
print(f"   rwd V294 vs V295: {len(rd)} differing bytes at {[hex(k) for k in rd]}")
hl = out["v295rwd"][1]
mapped = []
for k in rd:
    if k >= len(r5) - 4:
        mapped.append(("checksum", k))
    else:
        j = k - hl
        a = ((r5[hl + (j // 130) * 130] << 12) | (r5[hl + (j // 130) * 130 + 1] << 4)) + (j % 130) - 2
        mapped.append(("image", a))
print("   mapped:", [(t, hex(a)) for t, a in mapped])
img_bytes = {a for t, a in mapped if t == "image"}
chk(img_bytes == set(d_whole) and all(t in ("image", "checksum") for t, _ in mapped),
    "the rwd delta is EXACTLY the 6 image bytes + the 4-byte container checksum")
print("   part numbers in the header:", [v.decode() for v in out["v295rwd"][0][2][1]])
# the kit convention cross-check (the precedent formula), for the record
prec = bytes((((e ^ 0xBF) ^ 0x10) - 0x9E) & 0xFF for e in range(256))
chk(all(prec[e] == learn[e] for e in range(256)), "the precedent redo's formula == my learned table")

print("\n" + "=" * 110)
print(f" RESULT: {len(FAILS)} FAIL(s)")
for f in FAILS:
    print("   -", f)
