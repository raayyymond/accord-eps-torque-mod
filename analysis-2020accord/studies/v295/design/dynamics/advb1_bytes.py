"""ADV-bytes (dynamics lens) step 1: read every cell from the V294 IMAGE; independent raw LE reader scan.

Adversary of A1017 (0xC63E8 1011 -> 1017). Independent of the designer's d4 script: written from scratch.
"""
import hashlib, os, struct, sys
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = ROOT + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
IMG293 = ROOT + "/analysis-2020accord/_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
b = open(IMG, "rb").read()
h = hashlib.sha256(b).hexdigest()
print("V294 sha256", h, "len", len(b))
assert h == "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"

TP = 0xBF000
def s16(a): return struct.unpack_from("<h", b, a)[0]
def u16(a): return struct.unpack_from("<H", b, a)[0]
def u32(a): return struct.unpack_from("<I", b, a)[0]
cells = {
    "fb_a 0xC63E8": (0xC63E8, s16), "fb_b 0xC63EA": (0xC63EA, u16), "C 0xC62E6": (0xC62E6, u16),
    "lag_a 0xC63EC": (0xC63EC, s16), "lag_b 0xC63EE": (0xC63EE, u16), "Ki 0xC63E6": (0xC63E6, u16),
    "deadband 0xC62E4": (0xC62E4, u16), "Iclamp 0xC61BA": (0xC61BA, u16), "Pclamp 0xC61BC": (0xC61BC, u16),
    "Dclamp 0xC61B6": (0xC61B6, u16), "sumclamp 0xC61BE": (0xC61BE, u16), "laneclamp 0xC61B4": (0xC61B4, u16),
    "fwdclamp 0xC61B2": (0xC61B2, u16), "fwdgain 0xC6CD0": (0xC6CD0, s16), "gate 0xC61B8": (0xC61B8, s16),
}
for k, (a, f) in cells.items():
    print(f"  {k:22s} tp+0x{a-TP:04X} bytes {b[a]:02X} {b[a+1]:02X} value {f(a)}")
print("neighbourhood 0xC63E0..0xC63FF:", b[0xC63E0:0xC6400].hex(" "))

# ---- the edit
e = bytearray(b)
e[0xC63E8:0xC63EA] = struct.pack("<h", 1017)
diff = [i for i in range(len(b)) if b[i] != e[i]]
print("edit bytes changed (before CRC):", [(hex(i), hex(b[i]), hex(e[i])) for i in diff])

# ---- raw LE reader scan for disp 0x73E8 (fb_a), 0x73EA (fb_b), controls, on ANY base register, all load/store forms
# Format VII (4-byte): hw1 = reg2<<11 | opcode6<<5 | reg1 ; hw2 = disp16 (bit0 carries the sub-op for ld.hu/ld.w/st.h/st.w)
# opcodes: ld.b 0x38, ld.h 0x39 (hw2 bit0=0), ld.w 0x39 (hw2 bit0=1), st.b 0x3A, st.h 0x3B (bit0 0), st.w 0x3B (bit0 1)
# ld.bu 0x3C/0x3D (bit b hw1[5]=disp0, hw2 bit0 = 1), ld.hu 0x3F (hw2 bit0=1)
# 6-byte extended (V850E2): hw1 = 0000 0111 10 0 reg1 style; handled by searching the 32-bit disp in the 6-byte form:
#   ld.b disp23: 0x0780|reg1, hw2 = reg3<<11 | (disp[6:0]<<4) | 0x5 ... we instead search generically below.
def scan_disp16(target_disp, base_reg=None):
    hits = []
    lo16 = target_disp & 0xFFFF
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off); hw2 = u16(off + 2)
        op6 = (hw1 >> 5) & 0x3F
        reg1 = hw1 & 0x1F
        if base_reg is not None and reg1 != base_reg:
            continue
        kind = None
        if op6 == 0x38 and hw2 == lo16: kind = "ld.b"
        elif op6 == 0x39 and (hw2 & 0xFFFE) == lo16:
            kind = "ld.w" if hw2 & 1 else "ld.h"
        elif op6 == 0x3A and hw2 == lo16: kind = "st.b"
        elif op6 == 0x3B and (hw2 & 0xFFFE) == lo16:
            kind = "st.w" if hw2 & 1 else "st.h"
        elif op6 == 0x3F and (hw2 & 1) and (hw2 & 0xFFFE) == lo16: kind = "ld.hu"
        elif op6 in (0x3C, 0x3D) and (hw2 & 1):
            d = (hw2 & 0xFFFE) | (op6 & 1)
            if d == lo16: kind = "ld.bu"
        if kind:
            hits.append((hex(off), kind, reg1, (hw1 >> 11) & 0x1F))
    return hits

for name, d in [("fb_a 0x73E8", 0x73E8), ("fb_a+1 0x73E9", 0x73E9), ("fb_b 0x73EA", 0x73EA),
                ("lag_a 0x73EC", 0x73EC), ("lag_b 0x73EE", 0x73EE)]:
    print(name, "disp16 hits (any base):", scan_disp16(d))

# 6-byte extended-displacement loads (V850E2 Format XIV): hw1 = 0000 0 111 10 0 reg1 ... disp23 split.
# Generic approach: search for a 23-bit displacement 0x73E8 in the (hw2,hw3) pair of any 6-byte candidate:
#   ld.b/ld.bu/ld.h/ld.hu/ld.w/st.* disp23: hw1 = (sub<<11?)|0x0780|reg1 ; hw2 = reg3<<11 | disp[6:0]<<4 | subop ; hw3 = disp[22:7]
def scan_disp23(target):
    hits = []
    for off in range(0x13000, 0xC0000, 2):
        hw1 = u16(off)
        if (hw1 & 0x07E0) not in (0x0780, 0x07A0):
            continue
        hw2 = u16(off + 2); hw3 = u16(off + 4)
        disp = ((hw3 << 7) | ((hw2 >> 4) & 0x7F))
        if disp & 0x400000: disp -= 0x800000
        for cand in (disp, disp & ~1):
            if cand == target:
                hits.append((hex(off), hex(hw1), hex(hw2), hex(hw3), "base r%d" % (hw1 & 0x1F)))
                break
    return hits
# positive control for the 6-byte decoder: the census's gp-0x6752 6-byte read at 0x48E56
print("6-byte control gp-0x6752 (expect 0x48e56):", [x for x in scan_disp23(-0x6752) if x[0] == "0x48e56"])
for name, d in [("fb_a", 0x73E8), ("fb_b", 0x73EA)]:
    print(name, "6-byte disp23 hits:", scan_disp23(d))

# absolute/LE32 pointers into the cell's neighbourhood anywhere in the image (data tables, mov imm32)
def scan_le32_range(lo, hi):
    out = []
    for off in range(0, len(b) - 3):
        v = u32(off)
        if lo <= v < hi:
            out.append((hex(off), hex(v)))
    return out
print("LE32 values in [0xC6000,0xC6400) (any alignment):", len(scan_le32_range(0xC6000, 0xC6400)))
print("  in [0xC63C0,0xC6400):", scan_le32_range(0xC63C0, 0xC6400))
# mov imm32 (Format VI: hw1 = 0000 0110 001 reg1 = 0x0620|reg1, then imm32 LE)
movs = []
for off in range(0x13000, 0xC0000, 2):
    hw1 = u16(off)
    if (hw1 & 0xFFE0) == 0x0620:
        imm = u32(off + 2)
        if 0xC6000 <= imm < 0xC7000:
            movs.append((hex(off), "r%d" % (hw1 & 0x1F), hex(imm)))
print("mov imm32 into the 0xC6xxx page:", movs)
# movhi 0xC / 0xD then disp16 0x63E8 / -0x9C18 on the same reg (base+disp pair)
for off in range(0x13000, 0xC0000, 2):
    hw1 = u16(off); hw2 = u16(off + 2)
    if ((hw1 >> 5) & 0x3F) == 0x32 and hw2 in (0x000C, 0x000D):  # movhi imm16, reg1, reg2
        print("  movhi", hex(hw2), "at", hex(off), "reg2 r%d" % ((hw1 >> 11) & 0x1F))
print("disp16 0x63E8 any base:", scan_disp16(0x63E8), " disp16 -0x9C18:", scan_disp16(-0x9C18))
# movea / addi imm16 (op 0x31 / 0x30) whose imm16 could complete a movhi 0xC/0xD base into 0xC63xx
ma = []
for off in range(0x13000, 0xC0000, 2):
    hw1 = u16(off); hw2 = u16(off + 2)
    op6 = (hw1 >> 5) & 0x3F
    if op6 in (0x30, 0x31):
        imm = hw2 - 0x10000 if hw2 & 0x8000 else hw2
        for base in (0xC0000, 0xD0000):
            if 0xC6380 <= base + imm < 0xC6400:
                ma.append((hex(off), "addi" if op6 == 0x30 else "movea", hex(imm), hex(base + imm)))
print("addi/movea imm completing a 0xC/0xD movhi base into 0xC6380..0xC63FF:", ma)
# ep-relative short loads: is ep (r30) ever loaded with a cal-page address?
print("mov imm32 into ep (r30) anywhere:", [(hex(o), hex(u32(o + 2))) for o in range(0x13000, 0xC0000, 2) if u16(o) == 0x0620 | 30])
# ---- positive controls for the disp16 scanner (must be found or the nulls are void)
c1 = [h for h in scan_disp16(0x73E8, 5) if h[0] == "0x28f8a"]
c2 = [h for h in scan_disp16(0x73EA, 5) if h[0] == "0x28f86"]
print("CONTROL 0x28F8A ld.h tp+0x73E8:", c1, " CONTROL 0x28F86 ld.hu tp+0x73EA:", c2)
assert c1 and c2
# ---- V293 -> V294 whole-image diff restricted to [0x13000, 0x100000)
b3 = open(IMG293, "rb").read()
d = [i for i in range(0x13000, 0x100000) if b[i] != b3[i]]
print("V293 vs V294 differing bytes in [0x13000,0x100000):", len(d))
runs = []
for i in d:
    if runs and i == runs[-1][1] + 1: runs[-1][1] = i
    else: runs.append([i, i])
for r in runs: print("   ", hex(r[0]), "..", hex(r[1]), b3[r[0]:r[1]+1].hex(), "->", b[r[0]:r[1]+1].hex())
