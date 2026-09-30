# adv6_T_readers.py -- every access to gp-0x6b38 (the delivered lane torque T, the 427 tap source) in the V294 IMAGE,
# 4- and 6-byte forms, whole image (Ghidra's stock program cannot see the V294-only caves). Control: st.h @0x2A23C.
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
B = open(FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
hw = lambda a: int.from_bytes(B[a:a + 2], "little")
def s16(v): return v - 0x10000 if v & 0x8000 else v
def s23(v): return v - (1 << 23) if v & (1 << 22) else v
T = -0x6b38
hits = []
for a in range(0x13000, len(B) - 6, 2):
    h1, h2 = hw(a), hw(a + 2); op = (h1 >> 5) & 0x3F; r1 = h1 & 0x1F; r2 = h1 >> 11
    if r1 == 4 and op in (0x38, 0x39, 0x3A, 0x3B, 0x3F, 0x3C, 0x3D, 0x3E):
        disp = s16(h2 & 0xFFFE) if op in (0x39, 0x3B, 0x3F) else (s16((h2 & 0xFFFE) | (op & 1)) if op in (0x3C, 0x3D) else s16(h2))
        if disp in (T, T + 1):
            hits.append((a, "4b op%02x r%d" % (op, r2)))
    if r2 == 0 and op in (0x3C, 0x3D) and r1 == 4:
        d23 = s23((hw(a + 4) << 7) | ((h2 >> 4) & 0x7F)) & ~1
        if d23 == T:
            hits.append((a, "6b"))
print([("0x%05X" % a, k) for a, k in hits])
