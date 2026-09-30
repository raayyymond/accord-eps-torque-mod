# -*- coding: utf-8 -*-
"""adv_mirror.py -- the ADVERSARY's OWN integer mirror of the V294 LKAS lane (FUN_00028ea6), written from the Ghidra
decompile + dry-run listing read this session (0x28F3C..0x28FBE, the PID tail and the output path 0x2A174..0x2A23C),
NOT from the harness Lane, plib.march or the golden model.  Every cal is read BY ADDRESS from an image.

Per 1 kHz tick (V850 LE, 32-bit registers; Python ints + an explicit int32 check on every product/sum the ECU holds):
  0x28F4C  x  = ld.h gp-0x6a56 ; bail unless (x + 12000) <u 24001     (addi 0x2ee0 ; addi -0x5dc1,r0 ; bnc)
  0x28F66  sentinel ld.bu gp-0x3d2c ; s_old = ld.w gp-0x3d30 if sentinel == 1 else 0
  0x28F86  b = ld.hu tp+0x73EA ; 0x28F8A a = ld.h tp+0x73E8
  0x28F8E  mul r16,r7,r0  -> x*b (low 32 bits) ; 0x28F92 mul r26,r9,r0 -> a*s_old (low 32)
  0x28F9A  sar 10 (x*b) ; 0x28FA0 sar 10 (a*s) ; 0x28FA2 add -> s_new ; 0x28FA4 subr -> r26 = s_new - s_old
  0x28FA6..0x28FBC  r26 = clamp(r26, -C, +C), C = ld.hu tp+0x72E6 ; 0x28FA8 st.w s_new -> gp-0x3d30
  0x29D76  E = (sp << shl) - r26   (shl immediate READ from the opcode at 0x29D76)
  0x29E36  P = clamp((E*Kp) >> 8, +-Pcl)  Kp = LERP(rec(0xCB994), idx), Pcl = tp+0x71BC
  I = D = 0 on V294 (Ki tp+0x73E6 = 0 ; Kd bank all 0 and D clamp tp+0x71B6 = 0) -- asserted from the image
  S = clamp(((raw) * F) >> 8, +-Scl)  F = ((F1*F2) & 0xFFFF) >> 8 ; Scl = tp+0x71BE
  0x2A174  L' = ((la*L) >> 10) + ((S*lb) >> 10) ; y = (L + L') >> 5 ; L = L'  (la tp+0x73EC s16, lb tp+0x73EE u16)
  yr = sxh((y*ramp) >> 15), ramp = 0x8000 when fully engaged
  T  = clamp(((0 + yr) * pol * gain) >> 15, +-Tcl)  gain = s16 at tp + u16[0x2A1F0] ; Tcl = tp+0x71B4 ; -> gp-0x6b38
"""
import hashlib

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V294 = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
             "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
TP = 0xBF000
SEL = 7
I32 = 1 << 31


class Ovf(ArithmeticError):
    pass


def chk(v, where):
    if v >= I32 or v < -I32:
        raise Ovf("int32 overflow at %s: %d" % (where, v))
    return v


def rd(b, a, signed=False):
    return int.from_bytes(b[a:a + 2], "little", signed=signed)


def rec(b, bank):
    r = int.from_bytes(b[bank + 4 * SEL:bank + 4 * SEL + 4], "little")
    n = rd(b, r)
    X = [rd(b, r + 2 + 2 * i) for i in range(n)]
    Y = [rd(b, r + 2 + 2 * n + 2 * i) for i in range(n)]
    return X, Y


def lerp(X, Y, x):
    """the firmware walk (decompile): x <= X0 -> Y0 ; x >= Xn -> Yn ; else segment X[k-1] <= x < X[k],
    y = (Y[k]-Y[k-1])*(x-X[k-1]) / (X[k]-X[k-1]) + Y[k-1], C-style division (truncate toward zero)."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= x:
        k += 1
    num = (Y[k] - Y[k - 1]) * (x - X[k - 1])
    den = X[k] - X[k - 1]
    q = abs(num) // den
    q = q if num >= 0 else -q
    return q + Y[k - 1]


def load_cells(path=V294, **over):
    b = open(path, "rb").read()
    c = dict(sha=hashlib.sha256(b).hexdigest())
    c["a"] = rd(b, 0xC63E8, True)
    c["b"] = rd(b, 0xC63EA)
    c["C"] = rd(b, 0xC62E6)
    h = rd(b, 0x29D76)
    assert (h >> 5) & 0x3F == 0x16, "0x29D76 not shl imm5"
    c["shl"] = h & 0x1F
    op = (rd(b, 0x28FA4) >> 5) & 0x3F
    c["op"] = {0x0C: "subr", 0x0E: "add"}[op]
    c["kpX"], c["kpY"] = rec(b, 0xCB994)
    c["kdX"], c["kdY"] = rec(b, 0xCB7D4)
    c["mapX"], c["mapY"] = rec(b, 0xC9A88)
    c["tBX"], c["tBY"] = rec(b, 0xCBC34)
    c["tDX"], c["tDY"] = rec(b, 0xCBBC4)
    c["Ki"] = rd(b, 0xC63E6)
    c["Dcl"] = rd(b, 0xC61B6)
    c["Pcl"] = rd(b, 0xC61BC)
    c["Scl"] = rd(b, 0xC61BE)
    c["la"] = rd(b, 0xC63EC, True)
    c["lb"] = rd(b, 0xC63EE)
    c["gain"] = rd(b, TP + rd(b, 0x2A1F0), True)
    c["Tcl"] = rd(b, 0xC61B4)
    c["idxcl"] = b[0xC64F0]
    assert c["Ki"] == 0 and c["Dcl"] == 0 and all(v == 0 for v in c["kdY"]), "V294 I/D not zero?"
    c.update(over)
    return c


class Lane:
    def __init__(self, c, pol=1, ramp=0x8000):
        self.c = c
        self.pol = pol
        self.ramp = ramp
        self.kp = [lerp(c["kpX"], c["kpY"], i) for i in range(256)]
        self.map = [lerp(c["mapX"], c["mapY"], i) for i in range(256)]
        self.s = 0
        self.sent = 0          # boots 0 (.data) -> first tick s_old = 0
        self.L = 0
        self.max_as = 0
        self.max_bx = 0

    def fb(self, x):
        """0x28F4C..0x28FBE ; returns r26 or None on a bail (PID skipped)"""
        c = self.c
        if not (0 <= x + 12000 < 24001):          # unsigned compare after addi 0x2ee0
            self.sent = 2
            return None
        s_old = self.s if self.sent == 1 else 0
        p_bx = chk(x * c["b"], "0x28F8E x*b")
        p_as = chk(c["a"] * s_old, "0x28F92 a*s")
        self.max_as = max(self.max_as, abs(p_as))
        self.max_bx = max(self.max_bx, abs(p_bx))
        s_new = chk((p_as >> 10) + (p_bx >> 10), "0x28FA2 add")
        r26 = chk(s_new - s_old if c["op"] == "subr" else s_new + s_old, "0x28FA4")
        C = c["C"]
        r26 = C if r26 > C else (-C if r26 < -C else r26)
        self.s = s_new
        self.sent = 1
        return r26

    def tick(self, x, sp, idx, F=254):
        c = self.c
        r26 = self.fb(x)
        if r26 is None:
            S = 0
            P = 0
        else:
            E = chk((sp << c["shl"]) - r26, "0x29D78 E")
            P = chk(E * self.kp[idx], "0x29E36 E*Kp") >> 8
            P = c["Pcl"] if P > c["Pcl"] else (-c["Pcl"] if P < -c["Pcl"] else P)
            raw = P                                     # I>>7 = 0, D = 0 on V294
            S = chk(raw * F, "taper mul") >> 8
            S = c["Scl"] if S > c["Scl"] else (-c["Scl"] if S < -c["Scl"] else S)
        L2 = (chk(c["la"] * self.L, "la*L") >> 10) + (chk(S * c["lb"], "S*lb") >> 10)
        y = chk(self.L + L2, "L+L'") >> 5
        self.L = L2
        yr = chk(y * self.ramp, "y*ramp") >> 15
        assert -32768 <= yr <= 32767, "sxh"
        v = chk(yr * self.pol * c["gain"], "yr*pol*gain") >> 15
        T = c["Tcl"] if v > c["Tcl"] else (-c["Tcl"] if v < -c["Tcl"] else v)
        self.r26 = r26
        self.P = P
        return T
