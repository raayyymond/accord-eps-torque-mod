# -*- coding: utf-8 -*-
"""adv1_reader_census.py -- ADV bytes+instrument, V295 trim-ratio (b 0xC63EA 567 -> 964).

Independent raw little-endian census of EVERY way the V294 image could read the cell [0xC63EA, 0xC63EC) -- wider than the
designer's s11 (which scanned tp-base only, code region only, and no register-built bases):
  S1  4-byte Format VII/VIII load/store/bit-op, ANY base register, hw2 disp16 in {0x73EA,0x73EB} (tp-copy bases) and a
      word access at 0x73E8 that spans a+b;
  S2  6-byte Format XIV, ANY base, disp23 in {tp-rel 0x73E8..0x73EB} or r0-absolute {0xC63E8..0xC63EB};
  S3  absolute LE32 anywhere in the image equal to any address in [0xC62EC, 0xC63EB] (pointer tables / ep bases);
  S4  register-built bases: mov imm32 / movhi(+movea|addi|ori) / movea|addi from tp / mov tp,rX, with the value within
      disp16 reach of the cell, followed (48-byte look-ahead) by a load whose EA overlaps the cell; ep (r30) writes of any
      constant within sld reach (254 B below the cell);
  S5  the fb-state / fb-derived cells: gp-0x3d30 (s), gp-0x3d2c (sentinel), gp-0x6a34 (|r26>>5|), 4- and 6-byte;
  S6  callers of the twin FUN_0002a93a (the only other reader of gp-0x6a34) by jarl/jr disp22/disp32 and LE32 pointer.
POSITIVE CONTROLS (each scanner must find its control or its null is void):
  a  tp+0x73E8 ld.h @0x28F8A ; C tp+0x72E6 @0x28F96/0x28F9C/0x28FB8 ; 6-byte gp-0x6752 @0x48E56 ;
  mov imm32 0xCB994 (Kp bank) @0x29DC6 ; call FUN_00028ea6 from 0x22522 ; gp-0x3d30 ld.w @0x28F7C.
Whole image [0, 0x100000) scanned at every even offset (a linear sweep over-reports mid-instruction halves; it never
under-reports); every hit is listed with its region for adjudication.
"""
import hashlib

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMG = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
            "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
B = open(IMG, "rb").read()
SHA = hashlib.sha256(B).hexdigest()
print("V294 image sha256 %s  %s" % (SHA, "MATCH" if SHA.startswith("3143616d5b79bdb7") and SHA.endswith("89dbdd85") else "MISMATCH"))
N = len(B)
TP = 0xBF000
GP = 0xFEDF8000


def hw(a):
    return int.from_bytes(B[a:a + 2], "little")


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def s23(v):
    return v - (1 << 23) if v & (1 << 22) else v


def u16at(a):
    return hw(a)


print("cells: a[0xC63E8] s16 = %d ; b[0xC63EA] u16 = %d (0x%04x) ; C[0xC62E6] u16 = %d ; outlag 0xC63EC s16 %d / 0xC63EE %d"
      % (s16(hw(0xC63E8)), hw(0xC63EA), hw(0xC63EA), hw(0xC62E6), s16(hw(0xC63EC)), hw(0xC63EE)))
print("bytes 0xC63E0..0xC63F0:", B[0xC63E0:0xC63F0].hex(" "))

CELL = (0xC63EA, 0xC63EC)


def overlaps(ea, w):
    return ea < CELL[1] and ea + w > CELL[0]


def region(a):
    if a < 0x13000:
        return "boot/low"
    if a < 0xC0000:
        return "code"
    if a < 0xC6000:
        return "0xC0000-0xC6000 (cave/cal)"
    if a < 0xD0000:
        return "cal 0xC6000-0xD0000"
    return "high 0xD0000+ (records/data)"


# ---- 4-byte Format VII / VIII decoder: returns (mnem, width, base, disp, is_store) or None
def dec4(a):
    h1, h2 = hw(a), hw(a + 2)
    op = (h1 >> 5) & 0x3F
    r1 = h1 & 0x1F
    r2 = h1 >> 11
    if op == 0x38:
        return ("ld.b", 1, r1, s16(h2), False)
    if op == 0x39:
        return ("ld.w", 4, r1, s16(h2 & 0xFFFE), False) if h2 & 1 else ("ld.h", 2, r1, s16(h2), False)
    if op == 0x3A:
        return ("st.b", 1, r1, s16(h2), True)
    if op == 0x3B:
        return ("st.w", 4, r1, s16(h2 & 0xFFFE), True) if h2 & 1 else ("st.h", 2, r1, s16(h2), True)
    if op in (0x3C, 0x3D) and (h2 & 1) and r2 != 0:
        d = (h2 & 0xFFFE) | (op & 1)
        return ("ld.bu", 1, r1, s16(d), False)
    if op == 0x3F and (h2 & 1) and r2 != 0:
        return ("ld.hu", 2, r1, s16(h2 & 0xFFFE), False)
    if op == 0x3E:
        sub = h1 >> 14
        return (("set1", "not1", "clr1", "tst1")[sub], 1, r1, s16(h2), sub != 3)
    return None


# ---- 6-byte Format XIV (reg2 field = 0, opcode 0x3C/0x3D)
def dec6(a):
    h1, h2, h3 = hw(a), hw(a + 2), hw(a + 4)
    if (h1 >> 11) != 0 or ((h1 >> 5) & 0x3F) not in (0x3C, 0x3D):
        return None
    r1 = h1 & 0x1F
    low4 = h2 & 0xF
    odd = (h1 >> 5) & 1
    d23 = s23((h3 << 7) | ((h2 >> 4) & 0x7F))
    tbl = {(0, 0x5): ("ld.b", 1), (1, 0x5): ("ld.bu", 1), (0, 0xD): ("st.b", 1), }
    if (odd, low4) in tbl:
        m, w = tbl[(odd, low4)]
        return (m, w, r1, d23, m.startswith("st"))
    lo5 = h2 & 0x1F
    tbl2 = {(0, 0x07): ("ld.h", 2), (1, 0x07): ("ld.hu", 2), (0, 0x09): ("ld.w", 4), (1, 0x0D): ("st.h", 2),
            (0, 0x0F): ("st.w", 4)}
    if (odd, lo5) in tbl2:
        m, w = tbl2[(odd, lo5)]
        return (m, w, r1, d23 & ~1, m.startswith("st"))
    return ("6b?", 2, r1, d23 & ~1, False)


BASEVAL = {0: 0, 5: TP, 4: GP}


def ea_of(base, disp):
    if base in BASEVAL:
        return (BASEVAL[base] + disp) & 0xFFFFFFFF
    return None


# =============== S1 + S2 : direct forms, any base
print("\n== S1/S2 direct forms, whole image ==")


def scan_direct(target_lo, target_hi, allow_bases=None, label=""):
    """all 4-byte and 6-byte accesses with a KNOWN base (r0/tp/gp) whose [EA, EA+w) overlaps [lo,hi)"""
    hits = []
    for a in range(0, N - 6, 2):
        d = dec4(a)
        if d:
            m, w, r1, disp, st = d
            ea = ea_of(r1, disp)
            if ea is not None and ea < target_hi and ea + w > target_lo:
                hits.append((a, 4, m, r1, disp, ea))
        d = dec6(a)
        if d:
            m, w, r1, disp, st = d
            ea = ea_of(r1, disp)
            if ea is not None and ea < target_hi and ea + w > target_lo:
                hits.append((a, 6, m, r1, disp, ea))
    return hits


def show(hits, label):
    print("  %s: %d hit(s)" % (label, len(hits)))
    for a, ln, m, r1, disp, ea in hits:
        print("     0x%05X  %d-byte %-6s disp %+#x [r%d] -> EA 0x%X   (%s)" % (a, ln, m, disp, r1, ea, region(a)))


h_b = scan_direct(0xC63EA, 0xC63EC)
show(h_b, "TARGET b [0xC63EA,0xC63EC)")
h_a = scan_direct(0xC63E8, 0xC63EA)
show(h_a, "CONTROL a [0xC63E8,0xC63EA)  expect 0x28F8A")
h_C = scan_direct(0xC62E6, 0xC62E8)
show(h_C, "CONTROL C [0xC62E6,0xC62E8)  expect 0x28F96/9C/B8")
h_g = scan_direct((GP - 0x6752) & 0xFFFFFFFF, (GP - 0x6752 + 1) & 0xFFFFFFFF)
print("  CONTROL 6-byte gp-0x6752 @0x48E56: %s" % ("FOUND" if any(x[0] == 0x48E56 and x[1] == 6 for x in h_g) else "MISSED"))

# any base register, disp16 in 0x73E8..0x73EB (would matter if tp were copied into another register)
print("\n== S1b 4-byte, ANY base, disp16 hitting tp-offset 0x73E8..0x73EB (tp-copy bases) ==")
anyb = []
for a in range(0, N - 4, 2):
    d = dec4(a)
    if d:
        m, w, r1, disp, st = d
        if r1 not in (0, 4, 5) and (0x73E8 <= disp <= 0x73EB) and disp + w > 0x73EA:
            anyb.append((a, m, r1, disp))
print("  %d hit(s) with a non-r0/gp/tp base:" % len(anyb), ["0x%05X %s %#x[r%d] (%s)" % (a, m, d, r, region(a)) for a, m, r, d in anyb])

# 6-byte with ANY base and disp23 in the tp-rel or absolute window
six_any = []
for a in range(0, N - 6, 2):
    d = dec6(a)
    if d:
        m, w, r1, disp, st = d
        if (0x73E8 <= disp <= 0x73EB or 0xC63E8 <= disp <= 0xC63EB) and r1 not in (0, 4, 5):
            six_any.append((a, m, r1, disp))
print("  6-byte any-base disp in window: %d" % len(six_any), ["0x%05X %s %#x[r%d]" % x for x in six_any])

# =============== S3 absolute LE32
print("\n== S3 absolute LE32 in [0xC62EC, 0xC63EB] anywhere in the image ==")
abs_hits = []
for i in range(0, N - 4, 2):
    v = int.from_bytes(B[i:i + 4], "little")
    if 0xC62EC <= v <= 0xC63EB:
        abs_hits.append((i, v))
print("  %d hit(s):" % len(abs_hits), ["0x%05X=0x%X (%s)" % (i, v, region(i)) for i, v in abs_hits])
kp = [i for i in range(0, N - 4, 2) if int.from_bytes(B[i:i + 4], "little") == 0xCB994]
print("  CONTROL LE32 0xCB994 (Kp bank, mov imm32 @0x29DC6 imm at 0x29DC8): %s" % ("FOUND" if 0x29DC8 in kp else "MISSED %s" % kp))

# =============== S4 register-built bases
print("\n== S4 register-built bases within disp16 reach, 48-byte look-ahead for a load hitting the cell ==")
REACH = (0xC63EA - 0x7FFF, 0xC63EB + 0x8000)
sites = []  # (addr, len, reg, value, how)
for a in range(0x13000, N - 6, 2):
    h1 = hw(a)
    op = (h1 >> 5) & 0x3F
    r1, r2 = h1 & 0x1F, h1 >> 11
    if h1 & 0xFFE0 == 0x0620 and r1 != 0:           # mov imm32, r1
        v = int.from_bytes(B[a + 2:a + 6], "little")
        sites.append((a, 6, r1, v, "mov imm32"))
    elif op == 0x31 and r2 != 0:                       # movea simm16, r1, r2
        if r1 == 5:
            sites.append((a, 4, r2, (TP + s16(hw(a + 2))) & 0xFFFFFFFF, "movea tp"))
        elif r1 == 0:
            sites.append((a, 4, r2, s16(hw(a + 2)) & 0xFFFFFFFF, "movea r0"))
    elif op == 0x30 and r2 != 0 and r1 == 5:          # addi simm16, tp, r2
        sites.append((a, 4, r2, (TP + s16(hw(a + 2))) & 0xFFFFFFFF, "addi tp"))
    elif op == 0x32 and r2 != 0:                       # movhi imm16, r1, r2
        hi = hw(a + 2) << 16
        base = TP if r1 == 5 else (0 if r1 == 0 else None)
        if base is not None:
            v = (base + hi) & 0xFFFFFFFF
            # low half: next 1..3 instructions movea/addi/ori with reg1 == r2
            for k in (4, 8, 12):
                g1 = hw(a + k)
                gop, gr1, gr2 = (g1 >> 5) & 0x3F, g1 & 0x1F, g1 >> 11
                if gr1 == r2 and gop in (0x30, 0x31):
                    sites.append((a, 4, gr2, (v + s16(hw(a + k + 2))) & 0xFFFFFFFF, "movhi+movea/addi"))
                    break
                if gr1 == r2 and gop == 0x34:
                    sites.append((a, 4, gr2, (v | hw(a + k + 2)) & 0xFFFFFFFF, "movhi+ori"))
                    break
            sites.append((a, 4, r2, v, "movhi"))
    elif op == 0x00 and r2 != 0 and r1 == 5:           # mov tp, r2
        sites.append((a, 2, r2, TP, "mov tp"))
inreach = [s for s in sites if REACH[0] <= s[3] <= REACH[1]]
print("  constant/base materialisations: %d total, %d within disp16 reach of the cell" % (len(sites), len(inreach)))
ctrl_kp = [s for s in sites if s[3] == 0xCB994 and s[0] == 0x29DC6]
print("  CONTROL mov imm32 0xCB994 @0x29DC6 materialisation found: %s" % bool(ctrl_kp))
look_hits = []
for (a, ln, reg, v, how) in inreach:
    for k in range(a + ln, min(a + ln + 48, N - 6), 2):
        d = dec4(k)
        if d:
            m, w, r1, disp, st = d
            if r1 == reg and overlaps((v + disp) & 0xFFFFFFFF, w):
                look_hits.append((a, how, reg, v, k, m, disp))
        d6 = dec6(k)
        if d6:
            m, w, r1, disp, st = d6
            if r1 == reg and overlaps((v + disp) & 0xFFFFFFFF, w):
                look_hits.append((a, how, reg, v, k, m, disp))
        # sld/sst via ep
        if reg == 30:
            g = hw(k)
            r2g = g >> 11
            if r2g != 0:
                if (g >> 4) & 0x7F == 0b0000111:          # sld.hu disp5 (disp4<<1)
                    if overlaps(v + ((g & 0xF) << 1), 2):
                        look_hits.append((a, how, reg, v, k, "sld.hu", (g & 0xF) << 1))
                if (g >> 4) & 0x7F == 0b0000110:          # sld.bu disp4
                    if overlaps(v + (g & 0xF), 1):
                        look_hits.append((a, how, reg, v, k, "sld.bu", g & 0xF))
                o4 = (g >> 7) & 0xF
                if o4 == 0b0110 and overlaps(v + (g & 0x7F), 1):
                    look_hits.append((a, how, reg, v, k, "sld.b", g & 0x7F))
                if o4 == 0b1000 and overlaps(v + ((g & 0x7F) << 1), 2):
                    look_hits.append((a, how, reg, v, k, "sld.h", (g & 0x7F) << 1))
                if o4 == 0b1010 and (g & 1) == 0 and overlaps(v + ((g & 0x7E) << 1), 4):
                    look_hits.append((a, how, reg, v, k, "sld.w", (g & 0x7E) << 1))
print("  look-ahead loads hitting the cell through a built base: %d" % len(look_hits))
for x in look_hits:
    print("     base @0x%05X %s r%d=0x%X  ->  0x%05X %s disp %#x" % x)
# positive control for the look-ahead machinery: the Kp bank base 0xCB994 is followed by a load of [base + 4*sel]
# (register-indexed, so not a constant EA) -- use instead a synthetic control: any tp-copy site followed by a tp-rel load
ep_writes = [s for s in sites if s[2] == 30]
print("  ep (r30) constant writes anywhere: %d" % len(ep_writes), ["0x%05X %s 0x%X" % (s[0], s[4], s[3]) for s in ep_writes][:20])
tpc = [s for s in sites if s[4] in ("mov tp", "movea tp", "addi tp")]
print("  tp-derived bases (mov tp,rX / movea|addi imm,tp,rX): %d" % len(tpc),
      ["0x%05X %s r%d=0x%X" % (s[0], s[4], s[2], s[3]) for s in tpc][:40])

# =============== S5 fb-state cells
print("\n== S5 fb-state and fb-derived gp cells (4- and 6-byte, whole image) ==")
for nm, off, expect in (("s  gp-0x3d30", 0x3D30, {0x28F7C, 0x28FA8}), ("sentinel gp-0x3d2c", 0x3D2C, None),
                        ("|r26>>5| gp-0x6a34", 0x6A34, {0x290CA, 0x2A0CA, 0x2AFAE})):
    lo = (GP - off) & 0xFFFFFFFF
    hits = scan_direct(lo, lo + 2)
    ok = "" if expect is None else ("  control %s" % ("FOUND ALL" if expect <= {h[0] for h in hits} else "MISSED"))
    show(hits, nm + ok)

# =============== S6 callers of the twin FUN_0002a93a (and control FUN_00028ea6 <- 0x22522)
print("\n== S6 callers (jarl/jr disp22, disp32, LE32 pointers) ==")


def callers(target):
    out = []
    for a in range(0x13000, N - 6, 2):
        h1, h2 = hw(a), hw(a + 2)
        if ((h1 >> 6) & 0x1F) == 0x1E and (h2 & 1) == 0:      # Format V jarl/jr disp22
            d = ((h1 & 0x3F) << 16) | h2
            d = d - (1 << 22) if d & (1 << 21) else d
            if a + d == target:
                out.append((a, "jarl/jr d22 r%d" % (h1 >> 11)))
        if (h1 & 0xFFE0) == 0x02E0:                            # jr/jarl disp32
            d = int.from_bytes(B[a + 2:a + 6], "little")
            d = d - (1 << 32) if d & (1 << 31) else d
            if a + d == target:
                out.append((a, "jarl/jr d32 r%d" % (h1 & 0x1F)))
    for i in range(0, N - 4, 2):
        if int.from_bytes(B[i:i + 4], "little") == target:
            out.append((i, "LE32 pointer (%s)" % region(i)))
    return out


print("  CONTROL FUN_00028ea6:", ["0x%05X %s" % x for x in callers(0x28EA6)], "(expect 0x22522)")
print("  TWIN    FUN_0002a93a:", ["0x%05X %s" % x for x in callers(0x2A93A)])
print("  TWIN    FUN_0002a892:", ["0x%05X %s" % x for x in callers(0x2A892)])
