"""Which records do the Kp (0xCB994[sel]) and Kd (0xCB7D4[sel]) pointer tables select for the live selector 7, and do the
design's Y addresses (Kp 0xE5384 x5, Kd 0xE5126 x4) sit inside them? V295 LE reads. Layout per the decoded LERPs:
Kp @0x29DC6..0x29DE2: ep = [0xCB994 + sel*4]; r9 = [0xCB994+sel*4 ...] hw at ep+2 = X0 ... ; Y base = ld.w [r12+0xCB994] + 0xC
Kd @0x29E76..0x29E8E: ep = [0xCB7D4 + sel*4]; Y base = ld.w [r12+0xCB7D4] + 0xA"""
import struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
b = open(FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin", "rb").read()
u32 = lambda a: struct.unpack_from("<I", b, a)[0]; u16 = lambda a: struct.unpack_from("<H", b, a)[0]
sel = 7
for name, tab, yoff, n in [("Kp", 0xCB994, 0xC, 5), ("Kd", 0xCB7D4, 0xA, 4)]:
    ep = u32(tab + 4 * sel); rec = u32(tab + 4 * sel)
    print(f"{name}: ptr[{sel}] = {hex(ep)}  first halfwords:", [u16(ep + 2 * i) for i in range(12)])
    # second pointer read at ld.w 0x0(r10/r9) with r10 = r12 + table: the same entry
    print(f"   Y base = ptr + {hex(yoff)} = {hex(ep + yoff)} ->", [u16(ep + yoff + 2 * i) for i in range(n)])
