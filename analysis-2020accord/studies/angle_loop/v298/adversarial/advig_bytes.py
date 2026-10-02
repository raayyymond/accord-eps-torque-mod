"""ADV interlocks-gates V298: byte-exact decode of the relink-critical fields + the GB table + cals + records,
read straight from the BUILT image (no Ghidra). V850E2 little-endian.
Checks the KNOWN DEFECT class: table pointer, freeze/cam/op-skip jr targets, hook jarl."""
import glob, struct
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
img = open(glob.glob(FW + "_v298_*_plain_image.bin")[0], "rb").read()
stock = open(FW + "stock_fw_dump/code.bin", "rb").read()

def u16(a): return img[a] | (img[a+1] << 8)
def s16(a):
    v = u16(a); return v - 0x10000 if v & 0x8000 else v

def dec_jr_jarl(a):
    """V850 Format-V jr/jarl disp22: hw1 bits[10:6]=0b11110, disp in bits of the two halfwords.
    Encoding: w1 = img[a..a+1] LE, w2 = img[a+2..a+3] LE. disp = ((w1 & 0x3F)<<16 | w2) with bit0 forced 0,
    sign-extended from bit21. jarl has bit11 (LSB of second nibble) set via w1 bit... decode robustly:"""
    w1 = u16(a); w2 = u16(a+2)
    sub = (w1 >> 5) & 0x3F          # bits 10:5
    disp_hi = w1 & 0x3F             # bits 5:0  -> disp[21:16]
    disp = (disp_hi << 16) | w2
    disp &= 0x3FFFFF
    if disp & 0x200000: disp -= 0x400000
    tgt = (a + disp) & 0xFFFFFFFF
    # opcode: 0x3C=jr (bit0 of w2 region)/jarl distinguished by w1 bit0? use known: jr w1 top byte 0x07/0xb6..
    return tgt, hex(w1), hex(w2), disp

def dec_mov_imm32(a):
    """mov imm32, reg : 6-byte. w1 = 0x0620|reg? Format VI: byte pattern 'xx 06 LL LL HH HH' -> imm = bytes a+2..a+5 LE."""
    imm = img[a+2] | (img[a+3] << 8) | (img[a+4] << 16) | (img[a+5] << 24)
    return imm

print("=== relink-critical fields (BUILT image bytes) ===")
# hook jarl at 0x29D76
tgt, w1, w2, d = dec_jr_jarl(0x29D76)
print(f"HOOK  0x29D76 bytes {img[0x29D76:0x29D7A].hex()}  -> target {hex(tgt)}  (want 0xc4c00)  r6_ret=0x29d7a")
# op-skip jr at 0xC4C14
tgt, w1, w2, d = dec_jr_jarl(0xC4C14)
print(f"OPSKIP 0xC4C14 bytes {img[0xC4C14:0xC4C18].hex()} -> target {hex(tgt)}  (want 0x2a164)")
# freeze jr at 0xC4CC4
tgt, *_ = dec_jr_jarl(0xC4CC4)
print(f"FRZ   0xC4CC4 bytes {img[0xC4CC4:0xC4CC8].hex()}  -> target {hex(tgt)}  (want 0x29d7e)")
# cam jr at 0xC4CD4
tgt, *_ = dec_jr_jarl(0xC4CD4)
print(f"CAM   0xC4CD4 bytes {img[0xC4CD4:0xC4CD8].hex()}  -> target {hex(tgt)}  (want 0x29d7e)")
# table ptr mov imm32 at 0xC4C1C
imm = dec_mov_imm32(0xC4C1C)
print(f"GBPTR 0xC4C1C bytes {img[0xC4C1C:0xC4C22].hex()} -> imm {hex(imm)}  (want 0xc4cda)")

print()
print("=== Honda A2/B2 skips confirm the epilogue reuse ===")
for a in (0x29A5C, 0x29A64):
    tgt, *_ = dec_jr_jarl(a)
    print(f"  {hex(a)} bytes {img[a:a+4].hex()} -> {hex(tgt)} (want 0x2a164)")

print()
print("=== GB-P table at 0xC4CDA (7 rows x 3 x int16 LE) ===")
want = [(714,1178,1041),(1843,1465,-6264),(2304,760,-2033),(2707,560,1570),(4032,1068,2118),(6198,2188,0),(0xFFFF,2188,0)]
ok = True
for i in range(7):
    base = 0xC4CDA + i*6
    x = u16(base); g = s16(base+2); off = s16(base+4)
    wx, wg, wo = want[i]
    good = (x == (wx & 0xFFFF) and g == wg and off == wo)
    ok &= good
    print(f"  row{i} @{hex(base)}: X={x} G={g} off={off}   want=({wx},{wg},{wo})  {'OK' if good else 'MISMATCH'}")
print("GB table byte-exact:", ok)
# table extent: last row ends at 0xC4CDA+42 = 0xC4D04; verify FF after
print("bytes after table 0xC4D04:", img[0xC4D04:0xC4D0C].hex(), "(expect ff..)")

print()
print("=== cals (block 0xC6000) read back ===")
cal = {"a 0xC63E8":(0xC63E8,0),"b 0xC63EA":(0xC63EA,8192),"C 0xC62E6":(0xC62E6,65535),
       "DB 0xC62E4":(0xC62E4,0),"Ki 0xC63E6":(0xC63E6,40),"ICL 0xC61BA":(0xC61BA,8192),"DCL 0xC61B6":(0xC61B6,10240)}
for nm,(a,w) in cal.items():
    v=u16(a); print(f"  {nm}: {v}  want {w}  {'OK' if v==w else 'MISMATCH'}  (stock {stock[a]|(stock[a+1]<<8)})")

print()
print("=== records (block 0xE5000) ===")
print("  Kp Y 0xE5384 x5:", [u16(0xE5384+2*i) for i in range(5)], "want 112x5  (stock", [stock[0xE5384+2*i]|(stock[0xE5384+2*i+1]<<8) for i in range(5)],")")
print("  Kd Y 0xE5126 x4:", [u16(0xE5126+2*i) for i in range(4)], "want 48x4   (stock", [stock[0xE5126+2*i]|(stock[0xE5126+2*i+1]<<8) for i in range(4)],")")
# fade neutralize: fadeB2 record 0xE54FC (24B) := fadeB record 0xE564C
fb2 = img[0xE54FC:0xE54FC+24]; fb = img[0xE564C:0xE564C+24]
print("  fadeB2 0xE54FC == fadeB 0xE564C ?", fb2 == fb)
print("    fadeB2:", fb2.hex())
print("    fadeB :", fb.hex())
print("    stock fadeB2:", stock[0xE54FC:0xE54FC+24].hex())

print()
print("=== version string ===")
print("  0x13100:", img[0x13100:0x1310E], " 0x1310D =", hex(img[0x1310D]), "(want 0x41 'A')")
print("  0x1310E:", img[0x1310E:0x1311C])
