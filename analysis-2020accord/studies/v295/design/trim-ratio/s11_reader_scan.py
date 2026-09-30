# -*- coding: utf-8 -*-
"""s11_reader_scan.py -- independent raw LE scan (second method to Ghidra's listing) for every access to the one cell
this lens changes, 0xC63EA = tp+0x73EA, over the code region [0x13000, 0xC0000) of the V294 image.  Opcode-agnostic
(any 4-byte Format VII/VIII form with base tp = r5 and disp 0x73EA/0x73EB, any 6-byte Format XIV form with base r5 and
disp23 = 0x73EA/0x73EB, any absolute LE32 0x000C63EA anywhere in the image).  POSITIVE CONTROLS: tp+0x73E8 (a, one
reader at 0x28F8A) and tp+0x72E6 (C, three readers 0x28F96 / 0x28F9C / 0x28FB8), per the census and the Ghidra listing.
Linear sweep at every even offset -> may over-report mid-instruction halves (adjudicate against Ghidra), never under-reports."""
import os

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMG = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
            "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
b = open(IMG, "rb").read()


def hw(a):
    return int.from_bytes(b[a:a + 2], "little")


def scan(disp):
    hits4, hits6 = [], []
    for a in range(0x13000, 0xC0000 - 6, 2):
        h1, h2 = hw(a), hw(a + 2)
        if (h1 & 0x1F) == 5 and (h2 & 0xFFFE) == disp and (h1 >> 5) & 0x3F in range(0x38, 0x40):
            hits4.append(a)
        # Format XIV 6-byte load/store: hw1 = 00000 | opcode 0x3C/0x3D | reg1 (the first draft tested 0x07E0 and its
        # positive control at 0x48E56 (hw1 0x0784) FAILED -- fixed to the opcode field; the control below re-checks it)
        if (h1 >> 11) == 0 and ((h1 >> 5) & 0x3F) in (0x3C, 0x3D) and (h1 & 0x1F) == 5:
            d23 = (hw(a + 4) << 7) | ((h2 >> 4) & 0x7F)
            if (d23 & ~1) == disp:
                hits6.append(a)
    abs32 = [i for i in range(0, len(b) - 4, 2) if int.from_bytes(b[i:i + 4], "little") == 0xBF000 + disp]
    return hits4, hits6, abs32


for nm, disp, expect in (("CONTROL a  tp+0x73E8", 0x73E8, [0x28F8A]),
                         ("CONTROL C  tp+0x72E6", 0x72E6, [0x28F96, 0x28F9C, 0x28FB8]),
                         ("TARGET  b  tp+0x73EA", 0x73EA, None)):
    h4, h6, ab = scan(disp)
    ok = "" if expect is None else ("  control %s" % ("FOUND" if all(e in h4 for e in expect) else "MISSED -> scan void"))
    print("%-22s 4-byte %s | 6-byte %s | abs LE32 %s%s" % (nm, [hex(x) for x in h4], [hex(x) for x in h6],
                                                          [hex(x) for x in ab], ok))
print("value at 0xC63EA in the V294 image: %d (u16 LE)" % hw(0xC63EA))

# 6-byte decoder POSITIVE CONTROL (census c2: the 6-byte gp-0x6752 access at 0x48E56, base gp = r4)
a = 0x48E56
h1, h2, h3 = hw(a), hw(a + 2), hw(a + 4)
d23 = (h3 << 7) | ((h2 >> 4) & 0x7F)
d23s = d23 - (1 << 23) if d23 & (1 << 22) else d23
print("6-byte control at 0x48E56: hw1 %04x base r%d  format-XIV %s  disp23 %d (-0x%x) -> expect -0x6752 (or -0x6753 with the"
      " bit-0 width flag): %s" % (h1, h1 & 0x1F, (h1 & 0xFFE0) == 0x07E0, d23s, -d23s,
                                  "FOUND" if (d23s & ~1) == (-0x6752 & ~1) or abs(d23s) in (0x6752, 0x6753) else "MISSED"))
print("   and the fixed 6-byte predicate accepts it: %s" % ((h1 >> 11) == 0 and ((h1 >> 5) & 0x3F) in (0x3C, 0x3D)))
# a 6-byte scan of gp (r4) for -0x6752 over the code region must find 0x48E56
g6 = [x for x in range(0x13000, 0xC0000 - 6, 2) if (hw(x) >> 11) == 0 and ((hw(x) >> 5) & 0x3F) in (0x3C, 0x3D)
      and (hw(x) & 0x1F) == 4 and ((((hw(x + 4) << 7) | ((hw(x + 2) >> 4) & 0x7F)) - (1 << 23)) & ~1) == (-0x6752 & ~1)]
print("   6-byte scan of gp-0x6752 over the code region: %s (control %s)" % ([hex(x) for x in g6], "FOUND" if 0x48E56 in g6 else "MISSED"))
