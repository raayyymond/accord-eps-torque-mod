"""ADV interlocks-gates V298 / F6 + GATE 1: positive-controlled gp-relative reader/writer census on the BUILT image,
whole code region [0x13000,0x100000). Targets: gp-0x6a32 (the cell the E4 edit changed what gets stored), the cave's
read cells (confirm no NEW writer), and the flash-pointer uniqueness of the rewritten LERP records."""
import glob, struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
img = open(glob.glob(FW + "_v298_*_plain_image.bin")[0], "rb").read()
stock = open(FW + "stock_fw_dump/code.bin", "rb").read()
LO, HI = 0x13000, 0x100000
def s16(v): return v - 0x10000 if v & 0x8000 else v
def s23(v): return v - (1 << 23) if v & (1 << 22) else v
def scan(image, base, disp):
    hits = []
    for a in range(LO, HI - 2, 2):
        hw1, hw2 = struct.unpack_from("<HH", image, a)
        r1 = hw1 & 31; op = (hw1 >> 5) & 0x3F; r2 = hw1 >> 11
        if r1 == base:
            d = None; kind = None
            if op == 0x38: d = s16(hw2); kind = "ld.b"
            elif op == 0x39: d = s16(hw2 & ~1); kind = "ld.w" if hw2 & 1 else "ld.h"
            elif op == 0x3A: d = s16(hw2); kind = "st.b"
            elif op == 0x3B: d = s16(hw2 & ~1); kind = "st.w" if hw2 & 1 else "st.h"
            elif op in (0x3C, 0x3D) and (hw2 & 1) and r2 != 0: d = s16((hw2 & ~1) | (op & 1)); kind = "ld.bu"
            elif op == 0x3F and (hw2 & 1) and r2 != 0: d = s16(hw2 & ~1); kind = "ld.hu"
            if d == disp: hits.append((a, kind, r2, "4B"))
        if (hw1 & 0xFFC0) == 0x0780 and r1 == base and a + 6 <= HI:
            hw3 = struct.unpack_from("<H", image, a + 4)[0]
            sub = (hw1 >> 5) & 1; low = hw2 & 0xF
            d = s23((hw3 << 7) | ((hw2 >> 4) & 0x7F)); r3 = hw2 >> 11
            tbl = {(0,0x5):"ld.b",(1,0x5):"ld.bu",(0,0x7):"ld.h",(1,0x7):"ld.hu",(0,0x9):"ld.w",(0,0xD):"st.b",(1,0xD):"st.h",(0,0xF):"st.w"}
            k = tbl.get((sub, low))
            if k and d == disp: hits.append((a, k, r3, "6B"))
    return hits
GP = 4  # gp register index
# positive control: a known gp-0x6b38 reader/writer should exist (the 427 torque tap / delivered lane torque)
ctl = scan(img, GP, -0x6b38)
print(f"CONTROL gp-0x6b38 (delivered torque): {len(ctl)} hits  (expect >=1)  e.g. {ctl[:3]}")
print()
for disp, nm in [(-0x6a32, "gp-0x6a32 (E4-changed store target)"), (-0x6abe, "gp-0x6abe (cave fresh rate op)"),
                 (-0x6a00, "gp-0x6a00 (theta)"), (-0x4f60, "gp-0x4f60 (signed hand tq)"),
                 (-0x6dd0, "gp-0x6dd0 (Honda I state)"), (-0x4f68, "gp-0x4f68 (|driver tq|)")]:
    h = scan(img, GP, disp); hs = scan(stock, GP, disp)
    reads = [x for x in h if x[1].startswith("ld")]; writes = [x for x in h if x[1].startswith("st")]
    print(f"{nm}: V298 {len(reads)} rd / {len(writes)} wr   (stock {sum(1 for x in hs if x[1][0]=='l')} rd / {sum(1 for x in hs if x[1][0]=='s')} wr)")
    for a, k, r, w in h:
        tag = " <== NEW vs stock" if (a, k, r, w) not in hs else ""
        print(f"    {a:06x} {k:5s} r{r:<2d} {w}{tag}")
print()
# flash pointer uniqueness of the rewritten LERP records (pointers live little-endian in the 0xCB000..0xCC400 table region)
print("LERP record pointer uniqueness (scan 0xCB000..0xCC400 for LE32 == record base):")
for rec, nm in [(0xFEDE54FC & 0xFFFFFFFF, "fadeB2 0xE54FC"), (0xE54FC, "0xE54FC(flashaddr)"),
                (0xE5384, "KpY 0xE5384"), (0xE5126, "KdY 0xE5126"), (0xE564C, "fadeB 0xE564C")]:
    cnt = []
    for a in range(0xCB000, 0xCC400, 2):
        v = struct.unpack_from("<I", img, a)[0]
        if v == rec: cnt.append(hex(a))
    print(f"   {nm}: {len(cnt)} pointer(s) {cnt}")
