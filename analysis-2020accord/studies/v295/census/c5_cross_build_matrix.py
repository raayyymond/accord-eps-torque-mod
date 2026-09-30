"""
c5_cross_build_matrix.py -- the LKAS-PID cells down every plain image on disk (V38 onward), READ FROM THE IMAGES,
so the design agent can see which PID values have ever moved, on which builds, and which have been frozen.
Flown / not-flown status is NOT inferred here -- take it from BUILD-LINEAGE (this script only reads bytes).

Run:  python c5_cross_build_matrix.py  -> _scratch/out/c5_matrix.csv
"""
import csv
import os
import re
import struct
from pathlib import Path

ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")) / "analysis-2020accord"
SEL = 7


def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]


def rec(b, bank, n):
    p = u32(b, bank + 4 * SEL)
    if not (0xC0000 <= p < 0x100000 - 64):
        return None
    return tuple(u16(b, p + 2 + 2 * n + 2 * i) for i in range(n))


COLS = [
    ("fb_op@28FA4", lambda b: {0xD1C9: "add", 0xD189: "subr"}.get(u16(b, 0x28FA4), hex(u16(b, 0x28FA4)))),
    ("shl@29D76", lambda b: u16(b, 0x29D76) & 0x1F if u16(b, 0x29D76) & 0xFFE0 == 0x82C0 else hex(u16(b, 0x29D76))),
    ("hook@28F8E", lambda b: "mul" if b[0x28F8E:0x28F92] == bytes.fromhex("f03f2002") else b[0x28F8E:0x28F92].hex()),
    ("hook@2A174", lambda b: "ld.hu" if b[0x2A174:0x2A178] == bytes.fromhex("e53fef73") else b[0x2A174:0x2A178].hex()),
    ("hook@29D72", lambda b: "st.h" if b[0x29D72:0x29D76] == bytes.fromhex("6487ce95") else b[0x29D72:0x29D76].hex()),
    ("a C63E8", lambda b: s16(b, 0xC63E8)), ("b C63EA", lambda b: u16(b, 0xC63EA)), ("C C62E6", lambda b: u16(b, 0xC62E6)),
    ("db C62E4", lambda b: u16(b, 0xC62E4)), ("Ki C63E6", lambda b: u16(b, 0xC63E6)), ("Icl C61BA", lambda b: u16(b, 0xC61BA)),
    ("Pcl C61BC", lambda b: u16(b, 0xC61BC)), ("Dcl C61B6", lambda b: u16(b, 0xC61B6)), ("Scl C61BE", lambda b: u16(b, 0xC61BE)),
    ("oa C63EC", lambda b: s16(b, 0xC63EC)), ("ob C63EE", lambda b: u16(b, 0xC63EE)),
    ("Ocl C61B4", lambda b: u16(b, 0xC61B4)), ("Fcl C61B2", lambda b: u16(b, 0xC61B2)),
    ("gain", lambda b: s16(b, 0xBF000 + u16(b, 0x2A1F0))),
    ("Kp sel7", lambda b: rec(b, 0xCB994, 5)), ("Kd sel7", lambda b: rec(b, 0xCB7D4, 4)),
    ("map sel7 Ymax", lambda b: (rec(b, 0xC9A88, 10) or (None,))[-1]),
    ("r24 arm C6446", lambda b: u16(b, 0xC6446)),
]


def key(name):
    m = re.search(r"_v(\d+)", name)
    return (int(m.group(1)) if m else 0, name)


def main():
    files = sorted([p for p in ROOT.glob("*_plain_image.bin") if key(p.name)[0] >= 38], key=lambda p: key(p.name))
    files.insert(0, ROOT / "stock_fw_dump" / "code.bin")
    rows = []
    for p in files:
        b = p.read_bytes()
        rows.append([p.name[:70]] + [str(f(b)) for _, f in COLS])
    od = Path(__file__).resolve().parent / "_scratch" / "out"
    od.mkdir(exist_ok=True)
    with open(od / "c5_matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image"] + [c for c, _ in COLS])
        w.writerows(rows)
    # print only the rows where a PID cell differs from the previous row (compact ledger)
    prev = None
    for r in rows:
        if prev is None or r[1:] != prev[1:]:
            diffs = [f"{COLS[i][0]}={r[i + 1]}" for i in range(len(COLS)) if prev is None or r[i + 1] != prev[i + 1]]
            print(f"{r[0][:60]:60s} | {'; '.join(diffs)}")
        prev = r
    # every distinct value each PID cell has ever held on disk
    print("\nDISTINCT VALUES ON DISK, per cell:")
    for i, (c, _) in enumerate(COLS):
        vals = {}
        for r in rows:
            vals.setdefault(r[i + 1], []).append(r[0][:24])
        print(f"  {c:14s}: " + " | ".join(f"{v} (x{len(n)}, first {n[0]})" for v, n in vals.items()))


if __name__ == "__main__":
    main()
