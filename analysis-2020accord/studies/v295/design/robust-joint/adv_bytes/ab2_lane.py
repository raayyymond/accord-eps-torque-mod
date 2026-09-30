# -*- coding: utf-8 -*-
"""ab2_lane.py -- MY OWN integer mirror of the V294 LKAS lane, written from the Ghidra decompile of FUN_00028ea6 on the
V294 program (lines quoted below) and the listing 0x28F4C..0x28FC2 (dry-run), every constant READ FROM THE IMAGE.
Not derived from the harness, plib or the golden model (those are the cross-checks in ab2_arith.py).

Per 1 ms tick (Ki = 0, Kd = 0, D clamp = 0 on V294 -- asserted from the image):
  bail  = not(|bar|<=25600 and pol in {-1,0,1} and |x|<=12000 and pol != 0)      decompile l.69-71 ; 0x28F50..0x28F62
  s_old = s if sentinel == 1 else 0                                                 l.75-82 ; 0x28F66..0x28F84
  s_new = low32(a*s_old)>>10 + low32(x*b)>>10                                      l.85-87 ; 0x28F8E/92 mul .. r0 (low word)
  r26   = clamp(s_new - s_old, +-C) ; s := s_new ; sentinel := 1                   0x28FA4 subr ; 0x28FA6..0x28FBE
  (bail: r26 := 0, sentinel := 2, PID skipped -> S := 0 into the output lag)       l.161-170, l.1212-1219
  E     = (sp << shl) - r26                                                         l.980 ; 0x29D76 shl imm (read from image)
  P     = clamp((E*Kp)>>8, +-Pcl)                                                   l.1039-1049
  S     = clamp((P * taper)>>8, +-Scl)       (taper = ((F1*F2)&0xFFFF)>>8 = 254 at rest)   l.1188-1210
  L'    = (la*L>>10) + (S*lb>>10) ; y = (L+L')>>5 ; L = L'                        l.1229-1233
  yr    = (short)((y*ramp)>>15)                                                     l.1249
  T     = clamp(((0 + yr)*pol*gain)>>15, +-lane)                                    l.1253-1270 (addend gp-0x6b2c == 0)
ANALYSIS ONLY."""
import hashlib
import struct

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V294 = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
             "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V294_SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
SLOT = 7


def _u16(b, o): return struct.unpack_from("<H", b, o)[0]
def _s16(b, o): return struct.unpack_from("<h", b, o)[0]
def _u32(b, o): return struct.unpack_from("<I", b, o)[0]


def _rec(b, bank, slot=SLOT):
    p = _u32(b, bank + 4 * slot)
    n = _u16(b, p)
    X = [_u16(b, p + 2 + 2 * k) for k in range(n)]
    Y = [_u16(b, p + 2 + 2 * n + 2 * k) for k in range(n)]
    return p, X, Y


def lerp(X, Y, v):
    """the image's LERP walk (decompile l.104-122 form): below X0 -> Y0; >= Xn-1 -> Yn-1; else integer interpolate,
    C-style division (truncation toward zero)."""
    if v <= X[0]:
        return Y[0]
    if v >= X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= v:
        k += 1
    num = (Y[k] - Y[k - 1]) * (v - X[k - 1])
    den = X[k] - X[k - 1]
    q = abs(num) // den
    return Y[k - 1] + (q if num >= 0 else -q)


def cells(img=None, b_override=None):
    if img is None:
        img = open(V294, "rb").read()
        assert hashlib.sha256(img).hexdigest() == V294_SHA
    hw = _u16(img, 0x29D76)
    assert ((hw >> 5) & 0x3F) == 0x16, "0x29D76 is not shl imm5"
    op = _u16(img, 0x28FA4)
    assert op in (0xD189, 0xD1C9)
    c = dict(a=_s16(img, 0xC63E8), b=_u16(img, 0xC63EA), C=_u16(img, 0xC62E6), shl=hw & 0x1F,
             op="diff" if op == 0xD189 else "sum", Pcl=_u16(img, 0xC61BC), Scl=_s16(img, 0xC61BE),
             la=_s16(img, 0xC63EC), lb=_u16(img, 0xC63EE), gain=_s16(img, 0xC6CD0), lane=_s16(img, 0xC61B4),
             Ki=_u16(img, 0xC63E6), Dcl=_u16(img, 0xC61B6))
    c["map_rec"], c["mapX"], c["mapY"] = _rec(img, 0xC9A88)
    c["kp_rec"], c["kpX"], c["kpY"] = _rec(img, 0xCB994)
    c["kd_rec"], c["kdX"], c["kdY"] = _rec(img, 0xCB7D4)
    _, bX, bY = _rec(img, 0xCBC34)       # taper B (gp-0x6830 axis)
    _, dX, dY = _rec(img, 0xCBBC4)       # taper D (|bar>>5| axis)
    c["taper_rest"] = ((bY[0] * dY[0]) & 0xFFFF) >> 8
    c["tapB"], c["tapD"] = (bX, bY), (dX, dY)
    assert c["Ki"] == 0 and c["Dcl"] == 0 and all(v == 0 for v in c["kdY"]), "V294 has I/D off"
    assert len(set(c["kpY"])) == 1
    c["Kp"] = c["kpY"][0]
    c["SP"] = [lerp(c["mapX"], c["mapY"], i) for i in range(241)]
    if b_override is not None:
        c["b"] = int(b_override)
    return c


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


class Lane:
    def __init__(self, c):
        self.c = c
        self.s = 0          # gp-0x3d30 (boots 0)
        self.sent = 0       # gp-0x3d2c (boots 0)
        self.L = 0          # gp-0x3d3c
        self.max_as = 0     # largest |a*s| product seen (int32 audit)
        self.max_bx = 0
        self.wrap = 0       # count of products that would not fit int32

    def fb(self, x, bail=False):
        c = self.c
        if bail or not (-12000 <= x <= 12000):
            self.sent = 2
            return None
        s_old = self.s if self.sent == 1 else 0
        pa, pb = c["a"] * s_old, x * c["b"]
        self.max_as = max(self.max_as, abs(pa))
        self.max_bx = max(self.max_bx, abs(pb))
        if s32(pa) != pa or s32(pb) != pb:
            self.wrap += 1
        s_new = (s32(pa) >> 10) + (s32(pb) >> 10)
        r26 = s_new - s_old if c["op"] == "diff" else s_old + s_new
        self.s = s_new
        self.sent = 1
        C = c["C"]
        return C if r26 > C else (-C if r26 < -C else r26)

    def tick(self, x, sp, taper=None, ramp=0x8000, pol=1, bail=False, fb_force=None):
        c = self.c
        r26 = self.fb(x, bail) if fb_force is None else fb_force
        if r26 is None:                      # bail: PID skipped this tick, S = 0 into the lag
            S = 0
            P = 0
        else:
            E = (sp << c["shl"]) - r26
            P = (E * c["Kp"]) >> 8
            P = c["Pcl"] if P > c["Pcl"] else (-c["Pcl"] if P < -c["Pcl"] else P)
            tp = c["taper_rest"] if taper is None else taper
            S = (P * tp) >> 8
            S = c["Scl"] if S > c["Scl"] else (-c["Scl"] if S < -c["Scl"] else S)
        Ln = ((c["la"] * self.L) >> 10) + ((S * c["lb"]) >> 10)
        y = (self.L + Ln) >> 5
        self.L = Ln
        yr = y * ramp >> 15
        yr = ((yr + 0x8000) & 0xFFFF) - 0x8000
        T = (yr * pol * c["gain"]) >> 15
        T = c["lane"] if T > c["lane"] else (-c["lane"] if T < -c["lane"] else T)
        return T, r26, P, S


def r26_series(x1k, c):
    """the fb former alone over a 1 kHz x series (no bails: |x| is clipped to 12000 by the caller)."""
    a, b, C = c["a"], c["b"], c["C"]
    s = 0
    out = [0] * len(x1k)
    mx = 0
    for i, x in enumerate(x1k):
        pa = a * s
        if abs(pa) > mx:
            mx = abs(pa)
        s_new = (pa >> 10) + ((x * b) >> 10)
        r = s_new - s
        out[i] = C if r > C else (-C if r < -C else r)
        s = s_new
    return out, mx


def lag_series(S_list, c):
    la, lb, g, lane = c["la"], c["lb"], c["gain"], c["lane"]
    L = 0
    out = [0] * len(S_list)
    for i, S in enumerate(S_list):
        Ln = ((la * L) >> 10) + ((S * lb) >> 10)
        y = (L + Ln) >> 5
        L = Ln
        v = (y * g) >> 15
        out[i] = lane if v > lane else (-lane if v < -lane else v)
    return out
