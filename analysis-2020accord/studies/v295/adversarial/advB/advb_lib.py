"""advb_lib.py -- ADV-B's own helpers: image loading (hash-checked), LE cell reads, a raw V850 gp/tp access scanner
with positive controls.  Written independently of the build script and of the census scanner.

Python = the bin_decompile conda env.  Analysis only: reads files, never sends, never flashes.
"""
import hashlib
import os
import struct

FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = {
    "V295": FW + "/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
    "V294": FW + "/analysis-2020accord/_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
    "V293": FW + "/analysis-2020accord/_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
}
SHA = {
    "V295": "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed",
    "V294": "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85",
    "V293": "f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17",
}
RWD_V295 = FW + "/flashing-2020accord/rwd/39990-TVA,A160-V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP-0x13000-0x100000.rwd"
RWD_V295_SHA = "f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87"
GP = 0xFEDF8000
TP = 0xBF000


def find_v282():
    """V282 image: pick the file whose name starts _v282 in the firmware root (reported, hashed)."""
    d = FW + "/analysis-2020accord"
    c = sorted(f for f in os.listdir(d) if f.startswith("_v282") and f.endswith("_plain_image.bin"))
    return [os.path.join(d, f) for f in c]


def load(name_or_path, want_sha=None):
    p = IMG.get(name_or_path, name_or_path)
    b = open(p, "rb").read()
    h = hashlib.sha256(b).hexdigest()
    ws = want_sha or SHA.get(name_or_path)
    if ws is not None and h != ws:
        raise RuntimeError("hash mismatch %s: %s" % (name_or_path, h))
    return b, h


def u8(b, a): return b[a]
def u16(b, a): return struct.unpack_from("<H", b, a)[0]
def s16(b, a): return struct.unpack_from("<h", b, a)[0]
def u32(b, a): return struct.unpack_from("<I", b, a)[0]


def rec(b, bank, sel=7):
    """per-variant record pointer: LE32 at bank + 4*sel."""
    return u32(b, bank + 4 * sel)


def lerp_rec(b, bank, n, sel=7):
    """a LERP record: u16 count, then count X u16, then count Y u16.  Returns (rec, X, Y); asserts the count == n."""
    r = rec(b, bank, sel)
    cnt = u16(b, r)
    assert cnt == n, "record 0x%X count %d != %d" % (r, cnt, n)
    X = [u16(b, r + 2 + 2 * i) for i in range(n)]
    Y = [u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)]
    return r, X, Y


def sx16(v): return v - 0x10000 if v & 0x8000 else v


def scan(b, lo=0x13000, hi=0x100000):
    """every even offset decoded as a 4-byte Format VII load/store (and bit op) or 6-byte Format XIV; returns list of
    (addr, len, mnem, base_reg, reg2, disp).  hw2 bit-0 discriminators applied (ld.bu / ld.hu vs jr/jarl/mul)."""
    out = []
    n = min(hi, len(b)) - 6
    for a in range(lo, n, 2):
        h0 = b[a] | (b[a + 1] << 8)
        h1 = b[a + 2] | (b[a + 3] << 8)
        r1 = h0 & 31
        op = (h0 >> 5) & 0x3F
        r2 = h0 >> 11
        m = None
        if op == 0x38:
            m, d = "ld.b", sx16(h1)
        elif op == 0x39:
            m, d = ("ld.w" if h1 & 1 else "ld.h"), sx16(h1 & 0xFFFE)
        elif op == 0x3A:
            m, d = "st.b", sx16(h1)
        elif op == 0x3B:
            m, d = ("st.w" if h1 & 1 else "st.h"), sx16(h1 & 0xFFFE)
        elif op in (0x3C, 0x3D) and (h1 & 1):
            m, d = "ld.bu", sx16((h1 & 0xFFFE) | (op & 1))
        elif op == 0x3E:
            m, d = ("set1", "not1", "clr1", "tst1")[(h0 >> 14) & 3], sx16(h1)
        elif op == 0x3F and (h1 & 1) and r2 != 0:
            m, d = "ld.hu", sx16(h1 & 0xFFFE)
        if m is not None:
            out.append((a, 4, m, r1, r2, d))
        if (h0 & 0xFFE0) in (0x0780, 0x07A0) and (h1 & 0xF) in (5, 7, 9, 0xD, 0xF):
            h2 = b[a + 4] | (b[a + 5] << 8)
            disp = (sx16(h2) << 7) | ((h1 >> 4) & 0x7F)
            k = {(0x0780, 5): "ld.b", (0x07A0, 5): "ld.bu", (0x0780, 7): "ld.h", (0x07A0, 7): "ld.hu",
                 (0x0780, 9): "ld.w", (0x0780, 0xD): "st.b", (0x07A0, 0xD): "st.h", (0x0780, 0xF): "st.w"}.get(
                (h0 & 0xFFE0, h1 & 0xF), "x6?")
            out.append((a, 6, k + "(x6)", h0 & 31, (h1 >> 11) & 31, disp))
    return out


def gp_hits(S, disp, span=2):
    """accesses whose [disp, disp+width) overlaps [disp, disp+span) on base gp (r4)."""
    w = {"ld.b": 1, "ld.bu": 1, "st.b": 1, "ld.h": 2, "ld.hu": 2, "st.h": 2, "ld.w": 4, "st.w": 4,
         "set1": 1, "clr1": 1, "not1": 1, "tst1": 1}
    r = []
    for (a, L, m, r1, r2, d) in S:
        if r1 != 4:
            continue
        mm = m.replace("(x6)", "")
        ww = w.get(mm, 1)
        if d < disp + span and d + ww > disp:
            r.append((a, L, m, r1, r2, d))
    return r
