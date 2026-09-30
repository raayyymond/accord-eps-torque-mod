# -*- coding: utf-8 -*-
"""ADV-A a9: light, positive-controlled cross-check that 0xC63EA (tp+0x73EA) has one code reader in the V295 image:
every even offset in [0x13000, 0xC0000) whose halfword is 0x73EA/0x73EB (disp16 forms, hw2 = disp|1 for ld.hu) with a
tp (r5) base in the preceding halfword; the 6-byte disp23 forms (disp low16 at +2, any 4-byte-aligned-or-not); and the
absolute LE32 0x000C63EA / the RAM alias.  Controls: 0x28F86 (ld.hu 0x73ea,tp) and 0x28F8A (ld.h 0x73e8,tp)."""
import os, struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares"
b = open(FW + "/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
u16 = lambda a: struct.unpack_from("<H", b, a)[0]


def scan(disp):
    hits4, hits6 = [], []
    for a in range(0x13000, 0xC0000 - 4, 2):
        hw1, hw2 = u16(a), u16(a + 2)
        if hw2 in (disp, disp | 1) and (hw1 & 0x1F) == 5:
            hits4.append((hex(a), hex(hw1), (hw1 >> 5) & 0x3F))
        # 6-byte extended forms: hw1 base field = r5 and the 16 low disp bits in the 2nd halfword, 3rd holds high bits
        if (hw1 & 0x1F) == 5 and a + 6 <= 0xC0000 and hw2 in (disp, disp | 1) and u16(a + 4) == 0:
            hits6.append(hex(a))
    return hits4, hits6


for nm, disp in (("0x73E8 (control a)", 0x73E8), ("0x73EA (b)", 0x73EA)):
    h4, h6 = scan(disp)
    print(nm, "4-byte tp hits:", h4, "| 6-byte-shaped:", h6)
absol = [hex(a) for a in range(0x13000, 0xC0000 - 3) if struct.unpack_from("<I", b, a)[0] in (0xC63EA, 0xC63E8, 0xFA8003EA)]
print("LE32 absolute 0xC63E8/0xC63EA/0xFA8003EA anywhere in code:", absol)
