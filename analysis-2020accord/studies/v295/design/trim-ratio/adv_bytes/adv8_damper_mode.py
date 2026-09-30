# adv8_damper_mode.py -- the only live-function consumer of the b-derived gp-0x6a34 (|r26>>5|) is the damper-mode path
# 0x2A0C6, gated by gp-0x680a == 1.  Census every access to gp-0x680a (4-byte incl. ld.bu parity + bit ops, 6-byte) in the
# V294 image; control = gp-0x3d2c (ld.bu @0x28F66, st.b @0x290D4); and read its .data boot value.
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
B = open(FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
hw = lambda a: int.from_bytes(B[a:a + 2], "little")
def s16(v): return v - 0x10000 if v & 0x8000 else v
def s23(v): return v - (1 << 23) if v & (1 << 22) else v
def scan(off):
    out = []
    for a in range(0x13000, len(B) - 6, 2):
        h1, h2 = hw(a), hw(a + 2); op = (h1 >> 5) & 0x3F; r1 = h1 & 0x1F; r2 = h1 >> 11
        if r1 == 4:
            if op in (0x38, 0x3A, 0x3E) and s16(h2) == off: out.append((a, {0x38: "ld.b", 0x3A: "st.b", 0x3E: "bitop%d" % (h1 >> 14)}[op]))
            if op in (0x3C, 0x3D) and (h2 & 1) and r2 != 0 and s16((h2 & 0xFFFE) | (op & 1)) == off: out.append((a, "ld.bu"))
            if op in (0x39, 0x3B, 0x3F) and s16(h2 & 0xFFFE) == (off & ~1): out.append((a, "h/w op%02x (covers)" % op))
        if r2 == 0 and op in (0x3C, 0x3D) and r1 == 4:
            d23 = s23((hw(a + 4) << 7) | ((h2 >> 4) & 0x7F))
            if d23 in (off, off & ~1): out.append((a, "6-byte"))
    return out
print("control gp-0x3d2c:", [("0x%05X" % a, m) for a, m in scan(-0x3d2c)])
print("gp-0x680a       :", [("0x%05X" % a, m) for a, m in scan(-0x680a)])
