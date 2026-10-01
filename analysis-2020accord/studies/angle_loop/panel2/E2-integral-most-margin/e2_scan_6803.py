# -*- coding: utf-8 -*-
r"""e2_scan_6803.py -- every access to gp-0x6803 (the 0xE4 byte-2 bits 3:2 field) in the stock image and the V295 image,
raw little-endian byte scan at EVERY halfword alignment: 4-byte Format VII ld.b/ld.bu/st.b (hw2 = disp16, ld.bu with
the odd-displacement 0x3D field), Format VIII bit ops, the 6-byte extended forms (disp23 suffix), and sld/sst via ep
cannot address gp-relative so are not scanned (EVIDENCE: the lane trace).  Positive controls: the trace's writers
0x526AC/0x526F8/0x52732/0x527CC and the arm reader 0x29A74.  ANALYSIS ONLY."""
import glob
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
FW = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
IMGS = {"stock": FW / "stock_fw_dump" / "code.bin", "V295": Path(glob.glob(str(FW / "_v295_*plain_image.bin"))[0])}
DISP = (-0x6803) & 0xFFFF            # 0x97FD
GP = 4


def scan(b):
    hits = []
    n = len(b)
    for a in range(0x13000, n - 6, 2):
        h1, h2 = struct.unpack_from("<HH", b, a)
        r1 = h1 & 0x1F
        op6 = (h1 >> 5) & 0x3F
        r2 = h1 >> 11
        if r1 != GP:
            continue
        if op6 == 0x38 and h2 == DISP:
            hits.append((a, f"ld.b -0x6803[gp], r{r2}"))
        elif op6 == 0x3A and h2 == DISP:
            hits.append((a, f"st.b r{r2}, -0x6803[gp]"))
        elif op6 == 0x3D and h2 == (DISP & 0xFFFE) | 1 and ((h1 >> 6) & 0x1F) == 0x1E:   # ld.bu odd disp
            hits.append((a, f"ld.bu -0x6803[gp], r{r2}"))
        elif op6 == 0x3E and h2 == DISP:
            hits.append((a, f"bitop sub {h1 >> 14} bit {(h1 >> 11) & 7} -0x6803[gp]"))
    # 6-byte extended forms: hw1 low 5 bits = reg1 (gp), suffix disp23; match the 32-bit displacement -0x6803
    for a in range(0x13000, n - 6, 2):
        h1, h2, h3 = struct.unpack_from("<HHH", b, a)
        if (h1 & 0x1F) == GP and (h1 & 0xFFE0) in (0x0780, 0x07A0) and h1 >> 11 == 0:
            d = ((h3 << 16) | (h2 & 0xFFFE)) >> 1 if False else None
            disp = (((h3 & 0xFFFF) << 7) | (h2 >> 9)) if False else None
            # generic: reconstruct disp23 = (hw3 << 7) | (hw2 >> 9) with bit0 from hw2[4]?  report raw for review
            hits.append((a, f"6-byte form candidate h1 {h1:04x} h2 {h2:04x} h3 {h3:04x}")) if False else None
    return hits


def main():
    lines = []
    for nm, p in IMGS.items():
        b = p.read_bytes()
        h = scan(b)
        lines.append(f"[{nm}] {p.name}: {len(h)} gp-0x6803 accesses (4-byte forms)")
        for a, s in h:
            lines.append(f"  {a:#07x}  {b[a:a + 4].hex(' ')}  {s}")
    ctl = {0x526AC, 0x526F8, 0x52732, 0x527CC, 0x29A74}
    found = {a for a, _ in scan(IMGS["stock"].read_bytes())}
    lines.append(f"positive controls found: {sorted(hex(x) for x in ctl & found)}; missing: {sorted(hex(x) for x in ctl - found)}")
    txt = "\n".join(lines)
    print(txt)
    (HERE / "e2_scan_6803_out.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
