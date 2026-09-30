"""ADV-bytes (p-gain) step 1b: adjudicate the three LE32/imm32 values that point into the uncalled twin island,
and the two movhi 0xD sites (could they form 0xCB994?)."""
import os, struct
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = ROOT + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
b = open(IMG, "rb").read()
u16 = lambda a: struct.unpack_from("<H", b, a)[0]
u32 = lambda a: struct.unpack_from("<I", b, a)[0]
for a in (0x1E4C0, 0x5A360, 0x75B60):
    print(hex(a), b[a:a + 0x30].hex(" "))
# the table around 0x75b78: neighbouring aligned words
print("words around 0x75B78:", [hex(u32(o)) for o in range(0x75B58, 0x75B98, 4)])
# 0x2A61E and 0x2B000 inside the twin: bytes there
for a in (0x2A61E, 0x2B000):
    print("twin @", hex(a), b[a - 8:a + 16].hex(" "))
# movhi 0xD sites: next 3 halfword-instructions raw
for a in (0x1C4F2, 0x50B3C):
    print("movhi 0xd @", hex(a), b[a:a + 16].hex(" "))
