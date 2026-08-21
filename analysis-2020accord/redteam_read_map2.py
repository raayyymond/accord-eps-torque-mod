import struct, os
P = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
b = open(os.path.join(P, "analysis-2020accord/stock_fw_dump/code.bin"), "rb").read()
BASES = [0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]
SPEEDS = [0,15,40,80,120,160,200]
for mode in (24,26):
    print(f"===== MODE {mode} =====")
    for sp,B in zip(SPEEDS,BASES):
        p = struct.unpack_from("<I", b, B+mode*4)[0]
        cnt = struct.unpack_from("<H", b, p)[0]
        X = list(struct.unpack_from("<9h", b, p+0x02))
        Y = list(struct.unpack_from("<9h", b, p+0x14))
        print(f" v={sp:3d} rec=0x{p:X} n={cnt}")
        print(f"    X = {X}")
        print(f"    Y = {Y}")
