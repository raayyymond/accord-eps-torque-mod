"""RED-TEAM R1: read the assist-map ROM records straight out of stock code.bin.

Anchor first (CLAUDE.md: off-by-0x1000 has recurred 5x), then dump.
"""
import struct, os
P = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
b = open(os.path.join(P, "analysis-2020accord/stock_fw_dump/code.bin"), "rb").read()
print("code.bin length", hex(len(b)))

# ---- ANCHOR 1: the biquad coefficients at 0xC60A8 (known bytes from GATE2 doc)
anc = b[0xC60A8:0xC60A8+16]
print("0xC60A8 =", anc.hex(), "->", struct.unpack("<4f", anc))
assert anc.hex() == "f8c2c4bf7576223f0ebef0bf3a3b513f", "ANCHOR FAILED - file offset != address"
print("ANCHOR OK: file offset == address\n")

# ---- ANCHOR 2: known byte cals
for a, name, w in [(0xC6200,"clamp 8192","H"),(0xC649B,"biquad arm","B"),(0xC64FA,"arm thresh","B"),
                   (0xC6384,"slope cap 2048","H"),(0xC6178,"snap 5274","H"),(0xC6468,"slew 2639","H"),
                   (0xC613A,"multi 1159","H"),(0xC61F6,"r24 deadband 3","H"),(0xC6C42,"deriv N 4","H")]:
    n = struct.unpack_from("<"+w, b, a)[0]
    print(f"  {name:22s} 0x{a:X} = {n}")

print("\n---- the 7 speed-indexed pointer-array bases ----")
BASES = [0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0]
SPEEDS = [0,15,40,80,120,160,200]
for sp, B in zip(SPEEDS, BASES):
    ptrs = struct.unpack_from("<8I", b, B)   # first 8 mode slots
    print(f" v={sp:3d} km/h base 0x{B:X}: " + " ".join(f"{p:08X}" for p in ptrs))
