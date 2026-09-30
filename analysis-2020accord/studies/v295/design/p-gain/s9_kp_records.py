# -*- coding: utf-8 -*-
"""s9_kp_records.py -- the 28 Kp records of bank 0xCB994 on the V294 image (and stock / V293 / V282): pointer, count
word, X[5], Y[5]; plus the 0xCB994 accessors' record layout as the decompile reads it (rec+2..+10 = X, rec+0xC..+0x14 =
Y).  Bytes only, little-endian.  ANALYSIS ONLY."""
import hashlib
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IM = {"V294": FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"}
b = open(IM["V294"], "rb").read()
print("V294 sha256", hashlib.sha256(b).hexdigest())
u16 = lambda a: int.from_bytes(b[a:a + 2], "little")
u32 = lambda a: int.from_bytes(b[a:a + 4], "little")
ptrs = [u32(0xCB994 + 4 * i) for i in range(28)]
print("distinct record pointers:", len(set(ptrs)), " slot 7 ->", hex(ptrs[7]))
for i, p in enumerate(ptrs):
    n = u16(p)
    X = [u16(p + 2 + 2 * k) for k in range(5)]
    Y = [u16(p + 12 + 2 * k) for k in range(5)]
    print("slot %2d rec 0x%05X count %d X %s Y %s" % (i, p, n, X, Y))
s = sorted(ptrs)
print("min gap between records (bytes):", min(s[i + 1] - s[i] for i in range(27)))
