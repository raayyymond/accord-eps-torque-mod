"""ADV-bytes step 2: image-wide census of the gp cells the edit changes (r26 -> gp-0x6a34, fb state gp-0x3d30,
sentinel gp-0x3d2c, published PID cells, the out-lag state, T) -- 4-byte AND 6-byte forms AND absolute LE32,
positive-controlled. Independent decoder (not the census c2 code)."""
import struct
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-"
       "FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
b = open(IMG, "rb").read()
GP = 0xFEDF8000
u16 = lambda a: struct.unpack_from("<H", b, a)[0]
u32 = lambda a: struct.unpack_from("<I", b, a)[0]
def sx16(v): return v - 0x10000 if v & 0x8000 else v

def decode_all(lo=0x13000, hi=0x100000):
    ix = {}
    for a in range(lo, hi - 6, 2):
        h0, h1 = u16(a), u16(a + 2)
        r1, op, r2 = h0 & 31, (h0 >> 5) & 0x3F, h0 >> 11
        m = None
        if op == 0x38: m, d = "ld.b", sx16(h1)
        elif op == 0x39: m, d = ("ld.w" if h1 & 1 else "ld.h"), sx16(h1 & 0xFFFE)
        elif op == 0x3A: m, d = "st.b", sx16(h1)
        elif op == 0x3B: m, d = ("st.w" if h1 & 1 else "st.h"), sx16(h1 & 0xFFFE)
        elif op in (0x3C, 0x3D) and (h1 & 1): m, d = "ld.bu", sx16((h1 & 0xFFFE) | (op & 1))
        elif op == 0x3E: m, d = ("set1", "not1", "clr1", "tst1")[(h0 >> 14) & 3], sx16(h1)
        elif op == 0x3F and (h1 & 1) and r2 != 0: m, d = "ld.hu", sx16(h1 & 0xFFFE)
        if m: ix.setdefault((r1, d), []).append((a, m, 4))
        if (h0 & 0xFFE0) in (0x0780, 0x07A0) and (h1 & 0xF) in (5, 7, 9, 0xD, 0xF):
            h2 = u16(a + 4)
            d6 = (sx16(h2) << 7) | ((h1 >> 4) & 0x7F)
            ix.setdefault((h0 & 31, d6), []).append((a, "x6:%x/%x" % (h0 & 0xFFE0, h1 & 0xF), 6))
    return ix
ix = decode_all()
def gp(off): return ix.get((4, -off), [])
# ---- controls: known sites from the decompile/listing (0x28F7C ld.w gp-0x3d30 ; 0x28FA8 st.w ; 0x28F66 ld.bu gp-0x3d2c)
for off, site in ((0x3d30, 0x28F7C), (0x3d30, 0x28FA8), (0x3d2c, 0x28F66), (0x6a56, 0x28F4C), (0x6752, 0x48E56)):
    ok = any(s[0] == site for s in gp(off))
    print(f"CONTROL gp-0x{off:x} @0x{site:X}: {'PASS' if ok else 'FAIL'}")
    assert ok
cells = {0x6a34: "|r26>>5|", 0x3d30: "fb state s", 0x3d2c: "fb sentinel", 0x6b2e: "S published", 0x6b32: "P published",
         0x6b34: "raw sum published", 0x6b36: "D published", 0x6b30: "yr", 0x3d3c: "out-lag state", 0x6b38: "T lane",
         0x6b3c: "gated fwd", 0x6b3a: "fwd clamped", 0x680a: "damper-mode flag", 0x6cf8: "E_prev", 0x6dd0: "I state"}
FUN_PID = (0x28EA6, 0x2A30E); TWIN = (0x2A30E, 0x2B422)
for off, what in cells.items():
    sites = sorted(gp(off))
    absv = [hex(i) for i in range(0x13000, 0x100000 - 3) if u32(i) == (GP - off) & 0xFFFFFFFF]
    def where(a):
        if FUN_PID[0] <= a < FUN_PID[1]: return "PID"
        if TWIN[0] <= a < TWIN[1]: return "twin"
        return "ELSEWHERE"
    print(f"gp-0x{off:x} {what:20s}: " + ", ".join(f"{hex(a)} {m} [{where(a)}]" for a, m, _ in sites) + (f" ; abs {absv}" if absv else ""))
