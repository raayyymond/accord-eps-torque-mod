# -*- coding: utf-8 -*-
r"""e2_scan_callers.py -- who reaches the gp-0x6803 readers outside the lane?  Raw scan of the stock image at every
halfword alignment for Format V jarl/jr (opcode field 0x1E, hw2 bit 0 = 0, EVEN target) and Format VI/VII-free LE32
literals of each function entry (pointer tables, DID tables).  POSITIVE CONTROL: 0x22522 -> FUN_00028ea6 (jarl) must
be found.  ANALYSIS ONLY."""
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
B = Path("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin").read_bytes()
TARGETS = {0x28EA6: "FUN_00028ea6 (CONTROL)", 0x2A508: "FUN_0002a508", 0x2A93A: "FUN_0002a93a",
           0x2B35A: "FUN_0002b35a", 0x4E82E: "FUN_0004e82e", 0x2B418: "0x2B418 (twin tail)"}


def main():
    hits = {t: [] for t in TARGETS}
    for a in range(0, len(B) - 4, 2):
        h1, h2 = struct.unpack_from("<HH", B, a)
        if ((h1 >> 6) & 0x1F) == 0x1E and (h2 & 1) == 0:
            d = ((h1 & 0x3F) << 16) | h2
            if d & (1 << 21):
                d -= 1 << 22
            t = a + d
            if t in TARGETS:
                hits[t].append((a, "jarl" if (h1 >> 11) else "jr", f"r{h1 >> 11}"))
    lits = {t: [] for t in TARGETS}
    for a in range(0, len(B) - 4):
        v = struct.unpack_from("<I", B, a)[0]
        if v in TARGETS:
            lits[v].append(a)
    lines = []
    for t, nm in TARGETS.items():
        lines.append(f"{nm:28s} {t:#07x}: Format-V branches {[(hex(a), k, r) for a, k, r in hits[t]]}; "
                     f"LE32 literals at {[hex(x) for x in lits[t]]}")
    ok = any(a == 0x22522 for a, _, _ in hits[0x28EA6])
    lines.append(f"CONTROL 0x22522 -> 0x28EA6 found: {ok}")
    txt = "\n".join(lines)
    print(txt)
    (HERE / "e2_scan_callers_out.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
