"""ADV UNIT-SCALE V297 -- pre-build byte reads on the V295 BASE (no V297 image exists).
Reads every site the C3-rev2-F design edits, and the cals of its unit chain, LE, from the V295 image.
Nothing here is credit for a V297 image; it only pins what the build would have to start from."""
import hashlib, struct, os
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
V294 = FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
STOCK = FW + "stock_fw_dump/code.bin"
b5 = open(V295, "rb").read(); b4 = open(V294, "rb").read()
print("V295 sha256", hashlib.sha256(b5).hexdigest())
print("V294 sha256", hashlib.sha256(b4).hexdigest())
d = [a for a in range(0x13000, 0x100000) if b5[a] != b4[a]]
print("V294 vs V295 diffs in [0x13000,0x100000):", len(d), [hex(a) for a in d][:40])
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
hx = lambda b, a, n: " ".join(f"{x:02x}" for x in b[a:a+n])
print("\n-- 0xE4 intake 0x526C8..0x526F6 (V295) --"); print(hx(b5, 0x526C8, 0x30))
print("\n-- in-place sites, V295 bytes vs the design's 'V295 ->' column --")
sites = {"E1 0x28F4C": (0x28F4C, "24 3f aa 95"), "E2 0x28FA4": (0x28FA4, "89 d1"),
         "B2 0x29A50": (0x29A50, "e2 47 00 00"), "A2 0x29A56": (0x29A56, "da 05"),
         "E4 0x29D6A": (0x29D6A, "08 80 ed 80"), "HOOK 0x29D76": (0x29D76, "c2 82 ba 81"),
         "E5a 0x29EDE": (0x29EDE, "c7 00"), "E5b 0x29EE0": (0x29EE0, "10 40 bb 41"), "V1 0x1310D": (0x1310D, "30")}
for k, (a, exp) in sites.items():
    got = hx(b5, a, len(exp.split()))
    print(f"{k:14s} got {got:12s} design {exp:12s} {'OK' if got == exp else 'MISMATCH'}")
print("\n-- unit-chain cals (V295, LE) --")
cals = {"a fb pole 0xC63E8": 0xC63E8, "b fb gain 0xC63EA": 0xC63EA, "C r26 clamp 0xC62E6": 0xC62E6,
        "DB I deadband 0xC62E4": 0xC62E4, "Ki 0xC63E6": 0xC63E6, "ICL 0xC61BA": 0xC61BA, "DCL 0xC61B6": 0xC61B6,
        "OCL 0xC61B4": 0xC61B4, "P clamp 0xC61BC": 0xC61BC, "SCL 0xC61BE": 0xC61BE}
for k, a in cals.items(): print(f"{k:24s} u16 {u16(b5,a):6d}  s16 {s16(b5,a):6d}")
print("Kp Y 0xE5384 x5:", [u16(b5, 0xE5384 + 2*i) for i in range(5)])
print("Kd Y 0xE5126 x4:", [u16(b5, 0xE5126 + 2*i) for i in range(4)])
print("\n-- cave region 0xC4C00..0xC4D00 in V295: all 0xFF? --", all(x == 0xFF for x in b5[0xC4C00:0xC4D00]))
print(hx(b5, 0xC4BF0, 0x20))
print("\n-- speed-keyed record 0xE51A8 (X then Y), 16 halfwords --")
print([u16(b5, 0xE51A8 + 2*i) for i in range(16)])
