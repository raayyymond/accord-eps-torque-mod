"""Writers and readers of gp-0x4f68 (claimed |driver torque|) and gp-0x4f60 (claimed signed hand torque), V295.
4-byte Format VII ld/st with gp base; ld.h/ld.hu/st.h/ld.w/st.w forms; positive control gp-0x69ae (4 known writers)."""
import struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
b = open(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
def scan(disp):
    out = []
    for a in range(0x13000, 0xC0000, 2):
        h1, h2 = struct.unpack_from("<HH", b, a)
        if (h1 & 0x1F) != 4: continue
        op = (h1 >> 5) & 0x3F; r2 = h1 >> 11
        if op == 0x3B and (h2 & 0xFFFE) == (disp & 0xFFFE): out.append((hex(a), "st.w" if h2 & 1 else "st.h", r2))
        if op == 0x39 and (h2 & 0xFFFE) == (disp & 0xFFFE): out.append((hex(a), "ld.w" if h2 & 1 else "ld.h", r2))
        if op == 0x3F and (h2 & 1) and (h2 & 0xFFFE) == (disp & 0xFFFE): out.append((hex(a), "ld.hu", r2))
    return out
print("CONTROL -0x69ae:", scan(-0x69ae))
print("-0x4f68:", scan(-0x4f68))
print("-0x4f60:", scan(-0x4f60))
