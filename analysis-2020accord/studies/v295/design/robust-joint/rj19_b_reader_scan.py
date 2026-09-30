# -*- coding: utf-8 -*-
"""rj19_b_reader_scan.py -- lens robust-joint: crux check (second method, Python raw LE scan) that the pick's ONLY changed
cell, b @ 0xC63EA = tp+0x73EA, has exactly one reader in the V294 image (the fb filter's ld.hu at 0x28F86) and no
writer, with a positive control (a = tp+0x73E8 read by ld.h at 0x28F8A).  Loose scan: every even offset in the code
region whose second halfword is the displacement (or disp|1) and whose reg1 field is tp (r5) -- then decoded by opcode
field; plus the 6-byte extended form and an absolute LE32 0x000C63EA search.  ANALYSIS ONLY."""
import hashlib
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF."
       "C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
b = open(IMG, "rb").read()
assert hashlib.sha256(b).hexdigest() == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
u16 = lambda a: int.from_bytes(b[a:a + 2], "little")
print("cell values: a @0xC63E8 = %d, b @0xC63EA = %d (LE bytes %s)" % (int.from_bytes(b[0xC63E8:0xC63EA], "little", signed=True),
                                                                   u16(0xC63EA), b[0xC63EA:0xC63EC].hex()))
OPN = {0x38: "ld.b", 0x39: "ld.h/ld.w", 0x3A: "st.b", 0x3B: "st.h/st.w", 0x3C: "ld.bu(ev)/jr", 0x3D: "ld.bu(odd)/jarl",
       0x3E: "set1..", 0x3F: "ld.hu/st.hu"}
def scan(disp):
    hits = []
    for a in range(0x13000, 0xC0000, 2):
        hw1, hw2 = u16(a), u16(a + 2)
        if (hw2 & 0xFFFE) != disp:
            continue
        reg1 = hw1 & 0x1F
        op = (hw1 >> 5) & 0x3F
        if reg1 != 5 or op not in OPN:
            continue
        hits.append((a, op, OPN[op], hw1, hw2))
    return hits
for nm, disp in (("control a tp+0x73E8", 0x73E8), ("b tp+0x73EA", 0x73EA)):
    h = scan(disp)
    print("%s: %d hits" % (nm, len(h)))
    for a, op, name, hw1, hw2 in h:
        print("   0x%05X  hw1 %04x hw2 %04x  op 0x%02X %s  reg2 r%d  bit0 %d" % (a, hw1, hw2, op, name, hw1 >> 11, hw2 & 1))
# absolute references (LE32) and the 6-byte extended form's 32-bit displacement
for val in (0x000C63EA, 0x73EA):
    pat = val.to_bytes(4, "little")
    offs = [i for i in range(0x13000, 0xC0000) if b[i:i + 4] == pat]
    print("LE32 0x%08X in code region: %s" % (val, [hex(o) for o in offs]))
