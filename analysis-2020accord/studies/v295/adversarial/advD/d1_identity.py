"""ADV-D step 1: identity of the BUILT image, from disk. hashlib/zlib/struct only for the crux."""
import hashlib, zlib, struct, sys
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
V294 = FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
RWD = "C:/Users/dudei/Desktop/Projects/accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
b5 = open(V295, "rb").read(); b4 = open(V294, "rb").read(); rw = open(RWD, "rb").read()
h5, h4, hr = (hashlib.sha256(x).hexdigest() for x in (b5, b4, rw))
print("V295 image", len(b5), h5)
print("V294 image", len(b4), h4)
print("V295 rwd  ", len(rw), hr)
assert h5 == "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
assert h4 == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
diff = [i for i in range(len(b5)) if b5[i] != b4[i]]
print("diff offsets (whole file):", [hex(i) for i in diff])
for i in diff:
    print("  0x%X  V294 %02x  V295 %02x" % (i, b4[i], b5[i]))
u16 = lambda b, a: struct.unpack_from("<H", b, a)[0]
s16 = lambda b, a: struct.unpack_from("<h", b, a)[0]
print("0xC63EA b: V294 %d  V295 %d" % (u16(b4, 0xC63EA), u16(b5, 0xC63EA)))
print("0xC63E8 a: %d/%d  0xC62E6 C: %d/%d  0xC63EC lag_a %d  0xC63EE lag_b %d" % (s16(b4, 0xC63E8), s16(b5, 0xC63E8),
      u16(b4, 0xC62E6), u16(b5, 0xC62E6), s16(b5, 0xC63EC), u16(b5, 0xC63EE)))
crc = zlib.crc32(b5[0xC6000:0xC6FFC]) & 0xFFFFFFFF
print("crc32 [0xC6000,0xC6FFC) = 0x%08X ; trailer LE = 0x%08X ; BE = 0x%08X" % (crc, struct.unpack_from("<I", b5, 0xC6FFC)[0],
      struct.unpack_from(">I", b5, 0xC6FFC)[0]))
crc4 = zlib.crc32(b4[0xC6000:0xC6FFC]) & 0xFFFFFFFF
print("V294 crc32 same block = 0x%08X ; trailer LE 0x%08X" % (crc4, struct.unpack_from("<I", b4, 0xC6FFC)[0]))
# code bytes of interest identical (lane, forward path, monitors, cave, tap)
regions = {"code [0x13000,0xC0000)": (0x13000, 0xC0000), "caves 0xC4000-0xC5000": (0xC4000, 0xC5000),
           "FUN_00028ea6 region 0x28EA6-0x2A300": (0x28EA6, 0x2A300)}
for nm, (a, b) in regions.items():
    print("identical %-40s %s" % (nm, b5[a:b] == b4[a:b]))
