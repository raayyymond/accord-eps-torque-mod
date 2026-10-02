"""Find st.h/st.w writers of gp-0x69ea (the 0x14A rate source), positive-controlled on st.h -0x69ae @0x526F2.
4-byte Format VII only (gp base, reg1 = 4); plus a 6-byte disp23 st.h scan (hw1 = 0x0780|reg?). V295 image."""
import struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
b = open(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
def scan(disp):
    hw2 = disp & 0xFFFF; out = []
    for a in range(0x13000, 0xC0000, 2):
        h1, h2 = struct.unpack_from("<HH", b, a)
        if (h1 & 0x1F) == 4 and ((h1 >> 5) & 0x3F) == 0x3B and (h2 & 0xFFFE) == hw2:
            out.append((hex(a), "st.w" if h2 & 1 else "st.h", "r%d" % (h1 >> 11)))
    return out
print("CONTROL st -0x69ae:", scan(-0x69ae))
print("st -0x69ea:", scan(-0x69ea))
print("st -0x6a56:", scan(-0x6a56))
