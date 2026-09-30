"""ADV-bytes step 5: the cal page 0xC6000..0xC6FFF is COPIED to RAM 0xFA800000 at boot (listing 0x146DC..0x1471A, found
this session) and FUN_00059560 translates [0xC6000, 0xC7FFF] -> +(-0x58C6000) = 0xFA800000..  Is there any reader of
the RAM mirror of 0xC63E8 (= 0xFA8003E8) or of the ROM cell through a base register holding 0xC6000 / 0xFA800000?
Scan: (i) LE32 constants in the mirror window; (ii) every movhi 0xFA80 / mov imm32 0xFA80xxxx site; (iii) every
disp16 0x03E8 / 0x03E9 access on ANY base register (a base of 0xC6000 or 0xFA800000 + 0x3E8 hits the cell)."""
import struct
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-"
       "FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
b = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", b, a)[0]
u32 = lambda a: struct.unpack_from("<I", b, a)[0]
LO, HI = 0x13000, 0xC0000
print("(i) LE32 in [0xFA800000,0xFA802000):", [(hex(o), hex(u32(o))) for o in range(0, len(b) - 3) if 0xFA800000 <= u32(o) < 0xFA802000])
mh = [(hex(o), "r%d" % (u16(o) >> 11)) for o in range(LO, HI, 2) if ((u16(o) >> 5) & 0x3F) == 0x32 and u16(o + 2) == 0xFA80]
print("(ii) movhi 0xFA80 sites:", mh)
# disp16 0x03E8 (+ld.bu parity 0x03E9, ld.hu/ld.w disp|1) on any base
hits = []
for o in range(LO, HI, 2):
    h0, h1 = u16(o), u16(o + 2)
    op = (h0 >> 5) & 0x3F
    d = None
    if op in (0x38, 0x3A) and h1 == 0x03E8: d = ("ld.b" if op == 0x38 else "st.b")
    elif op in (0x39, 0x3B) and (h1 & 0xFFFE) == 0x03E8: d = {0x39: "ld.h/w", 0x3B: "st.h/w"}[op]
    elif op == 0x3F and (h1 & 1) and (h1 & 0xFFFE) == 0x03E8 and (h0 >> 11): d = "ld.hu"
    elif op in (0x3C, 0x3D) and (h1 & 1) and ((h1 & 0xFFFE) | (op & 1)) in (0x03E8, 0x03E9): d = "ld.bu"
    if d: hits.append((hex(o), d, "base r%d" % (h0 & 31)))
print("(iii) disp16 0x03E8/9 accesses on any base:", hits)
# ep-relative short loads cannot reach +0x3E8 (sld.h max disp 0xFE) -- stated, and no ep = cal base was found in advb1
