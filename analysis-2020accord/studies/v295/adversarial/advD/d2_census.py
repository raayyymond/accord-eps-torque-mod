"""ADV-D step 2: RAW, positive-controlled reader/writer census on the V295 IMAGE (my own decoder, shares no code with the
build script or the census).  Scans every EVEN offset in [0x13000, 0x100000) -- not instruction-synchronised, so it is a
SUPERSET (false positives are adjudicated with Ghidra afterwards; false negatives are what the controls guard against).

Forms decoded (V850E2, little-endian halfwords hw1, hw2, hw3):
  Format VII 4-byte: op6 = (hw1>>5)&0x3F, reg1 = hw1&0x1F (base), reg2 = hw1>>11
     0x38 ld.b  disp=s16(hw2)            0x3A st.b  disp=s16(hw2)
     0x39 ld.h (hw2&1==0) / ld.w (hw2&1==1)  disp=s16(hw2&~1)
     0x3B st.h / st.w by hw2 bit0          disp=s16(hw2&~1)
     0x3C/0x3D with reg2!=0 and hw2&1==1: ld.bu, disp = s16((hw2&~1)|(op6&1))   [hw2 bit0 = 0 is jarl/jr -> rejected]
     0x3F with reg2!=0 and hw2&1==1: ld.hu, disp = s16(hw2&~1)                   [bit0 = 0 is mul/setf etc.]
  Format XIV 6-byte: reg2==0, op6 in (0x3C,0x3D), hw2&1==1: disp23 = (hw3<<7) | ((hw2>>4)&0x7F), base = reg1
     (permissive: sub-opcode not decoded -> width treated as up to 4, so it over-matches; every hit is adjudicated)
  Base materialisations: movea/addi imm16 (op6 0x31 / 0x30) with reg1 in {gp r4, tp r5, r0}; movhi (op6 0x32);
     mov imm32 (hw1 = 0x0620|reg1, i.e. reg2 = 0, op6 0x31); look-ahead 64 bytes for an access off that register
     (Format VII/XIV) or, for ep (r30), any sld/sst reach [ep, ep+0x100).
  Absolute LE32 anywhere equal to a target address (pointer tables).
"""
import struct, sys, json
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
B = open(V295, "rb").read()
import hashlib
assert hashlib.sha256(B).hexdigest().startswith("5c044d65")
GP, TP = 0xFEDF8000, 0xBF000
u16 = lambda a: B[a] | (B[a + 1] << 8)
s16 = lambda v: v - 0x10000 if v & 0x8000 else v
def sx23(v):
    v &= 0x7FFFFF
    return v - 0x800000 if v & 0x400000 else v
LO, HI = 0x13000, 0x100000 - 6

def decode(i):
    """return list of (kind, base, disp, width, rw, length) for the halfword at i (superset)"""
    hw1, hw2 = u16(i), u16(i + 2)
    op6 = (hw1 >> 5) & 0x3F
    r1 = hw1 & 0x1F
    r2 = hw1 >> 11
    out = []
    if op6 == 0x38:
        out.append(("ld.b", r1, s16(hw2), 1, "R", 4))
    elif op6 == 0x39:
        out.append(("ld.w" if hw2 & 1 else "ld.h", r1, s16(hw2 & ~1 & 0xFFFF), 4 if hw2 & 1 else 2, "R", 4))
    elif op6 == 0x3A:
        out.append(("st.b", r1, s16(hw2), 1, "W", 4))
    elif op6 == 0x3B:
        out.append(("st.w" if hw2 & 1 else "st.h", r1, s16(hw2 & ~1 & 0xFFFF), 4 if hw2 & 1 else 2, "W", 4))
    elif op6 in (0x3C, 0x3D) and hw2 & 1:
        if r2 != 0:
            out.append(("ld.bu", r1, s16((hw2 & ~1 & 0xFFFF) | (op6 & 1)), 1, "R", 4))
        else:
            hw3 = u16(i + 4)
            d = sx23((hw3 << 7) | ((hw2 >> 4) & 0x7F))
            sub = hw2 & 0xF
            rw = "W" if sub in (0xD, 0xF) else "R"
            out.append(("fmtXIV(op%X,sub%X)" % (op6, sub), r1, d, 4, rw, 6))
    elif op6 == 0x3F and r2 != 0 and hw2 & 1:
        out.append(("ld.hu", r1, s16(hw2 & ~1 & 0xFFFF), 2, "R", 4))
    return out

def ea(base, disp):
    if base == 4:
        return (GP + disp) & 0xFFFFFFFF
    if base == 5:
        return (TP + disp) & 0xFFFFFFFF
    if base == 0:
        return disp & 0xFFFFFFFF
    return None

# ---------------------------------------------------------------------------------------------------- targets
T_TP = [("b 0xC63EA", 0xC63EA, 2)]
T_ALIAS = [("b RAM alias 0xFA8003EA", 0xFA8003EA, 2)]
GPC = [("s fb state gp-0x3d30", -0x3D30, 4), ("sentinel gp-0x3d2c", -0x3D2C, 1), ("fbstate2 gp-0x3d34", -0x3D34, 4),
       ("|r26>>5| gp-0x6a34", -0x6A34, 2), ("sp gp-0x6a32", -0x6A32, 2), ("S gp-0x6b2e", -0x6B2E, 2),
       ("yr gp-0x6b30", -0x6B30, 2), ("P gp-0x6b32", -0x6B32, 2), ("sum gp-0x6b34", -0x6B34, 2), ("D gp-0x6b36", -0x6B36, 2),
       ("T gp-0x6b38", -0x6B38, 2), ("fwd gp-0x6b3a", -0x6B3A, 2), ("fwd gp-0x6b3c", -0x6B3C, 2),
       ("E_prev gp-0x6cf8", -0x6CF8, 4), ("I gp-0x6dd0", -0x6DD0, 4), ("out-lag gp-0x3d3c", -0x3D3C, 4),
       ("idx gp-0x697a", -0x697A, 2), ("x gp-0x6a56", -0x6A56, 2),
       # controls (cells the decompile visibly reads/writes)
       ("CTRL bar gp-0x4f60", -0x4F60, 2), ("CTRL pol gp-0x6752", -0x6752, 1), ("CTRL gp-0x674e", -0x674E, 1)]
T_GP = [(n, (GP + o) & 0xFFFFFFFF, w) for n, o, w in GPC]
TARGETS = T_TP + T_ALIAS + T_GP
def overlaps(a, w, t, tw):
    return a is not None and a < t + tw and t < a + w

hits = {n: [] for n, _, _ in TARGETS}
tp_disp_hits = []           # any-base accesses with disp == 0x73EA-ish (for base-agnostic view)
for i in range(LO, HI, 2):
    for kind, base, disp, w, rw, ln in decode(i):
        a = ea(base, disp)
        for n, t, tw in TARGETS:
            if overlaps(a, w, t, tw):
                hits[n].append((i, kind, base, disp, rw))
        if base not in (4, 5, 0) and disp in (0x73E8, 0x73EA, 0x73EB, 0x3EA, 0x3E8):
            tp_disp_hits.append((i, kind, base, disp, rw))

# absolute LE32 pointers
le32 = {}
for n, t, tw in TARGETS:
    le32[n] = [i for i in range(0, len(B) - 4) if t - 3 <= struct.unpack_from("<I", B, i)[0] <= t + tw - 1 and i % 2 == 0]

# base materialisations with look-ahead
mat = []
for i in range(LO, HI, 2):
    hw1, hw2 = u16(i), u16(i + 2)
    op6 = (hw1 >> 5) & 0x3F
    r1 = hw1 & 0x1F
    r2 = hw1 >> 11
    val = None
    if op6 in (0x30, 0x31) and r2 != 0 and r1 in (0, 4, 5):          # addi / movea imm16, r1, r2
        val = ((GP if r1 == 4 else TP if r1 == 5 else 0) + s16(hw2)) & 0xFFFFFFFF
        dst, ln = r2, 4
    elif op6 == 0x32 and r2 != 0 and r1 == 0:                           # movhi imm16, r0, r2
        val, dst, ln = (hw2 << 16) & 0xFFFFFFFF, r2, 4
    elif op6 == 0x31 and r2 == 0 and r1 != 0:                           # mov imm32, r1  (6-byte)
        val, dst, ln = (hw2 | (u16(i + 4) << 16)), r1, 6
    else:
        continue
    for n, t, tw in TARGETS:
        if not (-0x8000 <= t - val <= 0x7FFF + 0x100) and not (-0x400000 <= t - val <= 0x3FFFFF and False):
            continue
        # look-ahead: accesses off dst whose ea overlaps the target; also movea imm, dst, dst chains
        for j in range(i + ln, min(i + ln + 64, HI), 2):
            for kind, base, disp, w, rw, l2 in decode(j):
                if base == dst and overlaps((val + disp) & 0xFFFFFFFF, w, t, tw):
                    mat.append((n, i, val, dst, j, kind, disp, rw))
            hwa, hwb = u16(j), u16(j + 2)
            if ((hwa >> 5) & 0x3F) in (0x30, 0x31) and (hwa & 0x1F) == dst and (hwa >> 11) != 0:
                v2 = (val + s16(hwb)) & 0xFFFFFFFF
                if -0x8000 <= t - v2 <= 0x7FFF:
                    for k in range(j + 4, min(j + 68, HI), 2):
                        for kind, base, disp, w, rw, l2 in decode(k):
                            if base == (hwa >> 11) and overlaps((v2 + disp) & 0xFFFFFFFF, w, t, tw):
                                mat.append((n, i, v2, hwa >> 11, k, kind, disp, rw))
        if dst == 30 and 0 <= t - val < 0x100:
            mat.append((n, i, val, 30, None, "ep-reach(sld/sst)", t - val, "?"))

print("=== raw Format VII / XIV hits (gp r4 / tp r5 / r0 bases), V295 image ===")
for n, _, _ in TARGETS:
    L = hits[n]
    print("%-28s %3d : %s" % (n, len(L), ", ".join("0x%X %s%s %s" % (i, k, "" , rw) for i, k, b_, d, rw in L)))
print("\n=== absolute LE32 pointers equal to a target (any alignment even) ===")
for n in le32:
    print("%-28s %s" % (n, [hex(x) for x in le32[n]]))
print("\n=== register-built bases reaching a target (movea/addi gp|tp|r0, movhi, mov imm32; 64-byte look-ahead) ===")
for m in mat:
    print("  %-26s mat@0x%X val 0x%08X r%d  access@%s %s disp %s %s" % (m[0], m[1], m[2], m[3], hex(m[4]) if m[4] else "-", m[5], m[6], m[7]))
print("\n=== any-base (not gp/tp/r0) accesses with disp 0x73E8/0x73EA/0x73EB/0x3EA/0x3E8 ===")
for h in tp_disp_hits:
    print("  0x%X %s base r%d disp 0x%X %s" % h)
json.dump({"hits": {k: v for k, v in hits.items()}, "le32": le32, "mat": mat, "anybase": tp_disp_hits},
          open("d2_census.json", "w"), indent=0, default=str)
