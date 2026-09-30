"""ADV-bytes (p-gain) step 7: the Kp bank 0xCB994 read from EVERY plain image on disk (lineage from BYTES, not docs):
live slot-7 X/Y, whether the 28 records agree, whether any record is non-flat / falling, the shl immediate at 0x29D76 and the
fb op at 0x28FA4 (which operand Kp multiplied)."""
import glob, os, re, struct
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
imgs = sorted(glob.glob(ROOT + "/analysis-2020accord/**/*plain_image.bin", recursive=True))
stock = ROOT + "/analysis-2020accord/stock_fw_dump/code.bin"
imgs = [stock] + imgs
def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]
rows = []
for p in imgs:
    b = open(p, "rb").read()
    if len(b) < 0x100000:
        continue
    try:
        ptrs = [u32(b, 0xCB994 + 4 * s) for s in range(28)]
        recs = []
        for q in ptrs:
            n = u16(b, q)
            recs.append((tuple(u16(b, q + 2 + 2 * k) for k in range(5)), tuple(u16(b, q + 12 + 2 * k) for k in range(5)), n))
    except Exception as e:
        continue
    X7, Y7, n7 = recs[7]
    ys = set(r[1] for r in recs)
    nonflat = [s for s, r in enumerate(recs) if len(set(r[1])) > 1]
    falling = [s for s, r in enumerate(recs) if any(r[1][k + 1] < r[1][k] for k in range(4))]
    xs7_default = X7 == (0, 68, 112, 136, 208)
    shl = u16(b, 0x29D76) & 0x1F
    op = {0x0E: "add", 0x0C: "subr"}.get((u16(b, 0x28FA4) >> 5) & 0x3F, "?")
    name = os.path.basename(p)
    m = re.match(r"(SUPERSEDED-DO-NOT-FLASH-)?_?(v[0-9a-z]+)", name, re.I)
    tag = ("SUPERSEDED " if name.startswith("SUPERSEDED") else "") + (m.group(2) if m else name[:20])
    rows.append((tag, X7, Y7, len(ys), nonflat, falling, xs7_default, shl, op, name))
seen = set()
for r in rows:
    key = (r[1], r[2], r[3], tuple(r[4]), tuple(r[5]), r[7], r[8])
    flag = ""
    if r[5]:
        flag += " FALLING-Y"
    if not r[6]:
        flag += " X-MOVED"
    if r[4]:
        flag += " NONFLAT(%d rec)" % len(r[4])
    print("%-22s slot7 X %s Y %s | distinct Y tuples %2d | shl %d op %-4s%s" % (r[0], r[1], r[2], r[3], r[7], r[8], flag))
print("\nimages with ANY falling Kp record:", [r[0] for r in rows if r[5]])
print("images with slot-7 X moved:", [(r[0], r[1]) for r in rows if not r[6]])
print("n images read:", len(rows))
