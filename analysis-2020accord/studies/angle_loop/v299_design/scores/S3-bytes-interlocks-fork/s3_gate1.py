"""S3 GATE-1 static census of the two new RAM words proposed this round (read-only, vectorised numpy).

D4b: gp-0x6a32 (halfword, 0xFEDF15CE).   D5a: gp-0x6c44 (word, 0xFEDF13BC).
Method = V289's gp_accesses decode rules (build_v289_tva.gp_accesses) re-implemented with numpy over EVERY even
offset of the V298 image (a linear scan over-reports: the safe direction for a null), plus absolute-literal and
movhi-hi scans, plus gp-base materialisations (addi/movea gp) within [-0x100,+0x100] of each word, which are the
register-indirect (gp-0x1500-class) leads to adjudicate.  Wall time printed.
"""
import glob, os, time
from pathlib import Path
import numpy as np

T0 = time.time()
ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
img = Path(glob.glob(str(ROOT / "analysis-2020accord" / "_v298_*_plain_image.bin"))[0]).read_bytes()
GP, GPB = 4, 0xFEDF8000
a8 = np.frombuffer(img, np.uint8)
h = a8[0::2].astype(np.uint32) | (a8[1::2].astype(np.uint32) << 8)          # halfword at 2k
n = len(h)
addr = np.arange(n, dtype=np.int64) * 2
h2 = np.roll(h, -1); h3 = np.roll(h, -2)
reg1, op, reg2 = h & 0x1F, (h >> 5) & 0x3F, h >> 11
sx16 = lambda x: ((x.astype(np.int64) + 0x8000) & 0xFFFF) - 0x8000
gpm = reg1 == GP
rows = []   # (addr, kind, disp, width)
def add(mask, kind, disp, width):
    for a, d, w in zip(addr[mask], np.broadcast_to(disp, h.shape)[mask], np.broadcast_to(width, h.shape)[mask]):
        rows.append((int(a), kind if isinstance(kind, str) else kind, int(d), int(w)))
add(gpm & (op == 0x38), "ld.b", sx16(h2), 1)
add(gpm & (op == 0x3A), "st.b", sx16(h2), 1)
m = gpm & (op == 0x39); add(m & (h2 & 1 == 1), "ld.w", sx16(h2 & 0xFFFE), 4); add(m & (h2 & 1 == 0), "ld.h", sx16(h2 & 0xFFFE), 2)
m = gpm & (op == 0x3B); add(m & (h2 & 1 == 1), "st.w", sx16(h2 & 0xFFFE), 4); add(m & (h2 & 1 == 0), "st.h", sx16(h2 & 0xFFFE), 2)
add(gpm & (op == 0x3F), "ld.hu", sx16(h2 & 0xFFFE), 2)
m = gpm & ((op == 0x3C) | (op == 0x3D))
d23 = ((h3.astype(np.int64) << 7) | ((h2.astype(np.int64) >> 4) & 0x7F))
d23 = ((d23 + (1 << 22)) & ((1 << 23) - 1)) - (1 << 22)
add(m & (reg2 == 0), "ext6", d23, 4)
add(m & (reg2 != 0) & (h2 & 1 == 1), "ld.bu", sx16((h2 & 0xFFFE) | (op & 1)), 1)
add(gpm & (op == 0x3E), "bitop", sx16(h2), 1)
add(gpm & ((op == 0x30) | (op == 0x31)), "addi/movea", sx16(h2), 1)

out = []
def say(s=""): out.append(s); print(s)
say(f"gp-relative decodes (all even offsets): {len(rows)}")
# positive controls: words the cave is known to touch
for d, w, nm in ((-0x6abe, 2, "gp-0x6abe"), (-0x6dd0, 4, "gp-0x6dd0"), (-0x6cf8, 4, "gp-0x6cf8"), (-0x4f68, 2, "gp-0x4f68")):
    hits = [r for r in rows if r[1] != "addi/movea" and r[2] < d + w and r[2] + r[3] > d]
    say(f"  positive control {nm}: {len(hits)} accessors")
for d, w, nm in ((-0x6a32, 2, "D4b gp-0x6a32"), (-0x6c44, 4, "D5a gp-0x6c44")):
    absa = (GPB + d) & 0xFFFFFFFF
    say(f"\n{nm} = 0x{absa:08X}")
    hits = [r for r in rows if r[1] != "addi/movea" and r[2] < d + w and r[2] + r[3] > d]
    for r in hits: say(f"  direct  0x{r[0]:05X} {r[1]:6s} disp {r[2]:#x} w{r[3]}")
    if not hits: say("  direct accessors: NONE")
    near = [r for r in rows if r[1] == "addi/movea" and -0x100 <= r[2] - d <= 0x100]
    for r in near: say(f"  gp-base materialisation 0x{r[0]:05X} gp{r[2]:+#x} (word at offset {d - r[2]:+#x} from it)")
    if not near: say("  gp-base materialisations within +-0x100: NONE")
    lit = np.flatnonzero((h[:-1] | (h[1:] << 16)) == absa) * 2
    say(f"  absolute 32-bit literal (2-aligned): {[hex(x) for x in lit]}")
    hi, lo = absa >> 16, absa & 0xFFFF
    if lo & 0x8000: hi = (hi + 1) & 0xFFFF
    mh = np.flatnonzero((op == 0x32) & (h2 == hi)) * 2
    say(f"  movhi 0x{hi:04X} sites: {len(mh)} (lo {lo:#06x}; pairs adjudicated below)")
    pairs = []
    for a in mh:
        dst = int(h[a // 2] >> 11)
        for j in range(2, 10):
            k = a // 2 + j
            if k + 1 < n and (h[k] & 0x1F) == dst and ((h[k] >> 5) & 0x3F) >= 0x30 and abs(int(sx16(np.array([h[k + 1]]))[0]) - int(sx16(np.array([lo]))[0])) <= 0x100:
                pairs.append((hex(int(a)), hex(int(k * 2)), int(sx16(np.array([h[k + 1]]))[0])))
                break
    say(f"  movhi+(ld/st/addi/movea) pairs landing within 0x100 of the word: {pairs}")
say(f"\nwall {time.time() - T0:.1f} s")
Path(__file__).with_suffix(".txt").write_text("\n".join(out))
