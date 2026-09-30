# -*- coding: utf-8 -*-
"""adv_lib.py -- ADVERSARY "stability" (p-gain candidate R1.3_8_100): MY OWN byte decoder, integer lane and linear
transfer functions.  Independent of the designer's scripts and of v295_harness (which is used ONLY as a comparison
target, never as a source).  Analysis only: reads images, writes nothing outside this folder.

Sources of the arithmetic: census V294-LKAS-PID-DESIGN-SPACE.md section 2 (listing addresses there) -- re-typed here
from the census text, then spot-checked tick-for-tick against the golden model (a1_spotcheck.py).
"""
import hashlib
import math

import numpy as np

FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMG_V294 = FW + ("_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
                 "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
SHA_V294 = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
IMG_V282 = FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin"
SEL = 7
KP_BANK, KD_BANK, MAP_BANK = 0xCB994, 0xCB7D4, 0xC9A88
CAND_X = (0, 8, 54, 100, 208)
CAND_Y = (1248, 1248, 1104, 960, 960)
WIRE_PER_IDX = 2 ** 22 / (4 * 65025)


def u16(b, a):
    return b[a] | (b[a + 1] << 8)


def s16(b, a):
    v = u16(b, a)
    return v - 65536 if v >= 32768 else v


def u32(b, a):
    return b[a] | (b[a + 1] << 8) | (b[a + 2] << 16) | (b[a + 3] << 24)


def load(path, sha=None):
    b = bytearray(open(path, "rb").read())
    h = hashlib.sha256(b).hexdigest()
    if sha and h != sha:
        raise RuntimeError("hash mismatch " + h)
    return b, h


def record(b, bank, slot=SEL):
    r = u32(b, bank + 4 * slot)
    n = u16(b, r)
    X = [u16(b, r + 2 + 2 * i) for i in range(n)]
    Y = [u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)]
    return r, X, Y


def write_candidate(b):
    """rewrite the Kp X and Y knots in ALL 28 records (the candidate spec).  Returns a new bytearray."""
    c = bytearray(b)
    recs = set()
    for slot in range(28):
        r = u32(c, KP_BANK + 4 * slot)
        recs.add(r)
        n = u16(c, r)
        assert n == 5, (slot, hex(r), n)
        for i in range(5):
            c[r + 2 + 2 * i:r + 4 + 2 * i] = CAND_X[i].to_bytes(2, "little")
            c[r + 12 + 2 * i:r + 14 + 2 * i] = CAND_Y[i].to_bytes(2, "little")
    assert len(recs) == 28
    return c


def cells(b):
    """every lane knob by ADDRESS (census section 3 table)."""
    d = {}
    d["fb_a"] = s16(b, 0xC63E8)
    d["fb_b"] = u16(b, 0xC63EA)
    d["fb_clamp"] = u16(b, 0xC62E6)
    op = (u16(b, 0x28FA4) >> 5) & 0x3F          # add = 0x0E, subr = 0x0C (Format I opcode field)
    d["fb_op"] = {0x0E: "sum", 0x0C: "diff"}[op]
    hw = u16(b, 0x29D76)
    assert (hw >> 5) & 0x3F == 0x16, "not shl imm5"
    d["e_shift"] = hw & 0x1F
    _, d["kp_x"], d["kp_y"] = record(b, KP_BANK)
    _, d["kd_x"], d["kd_y"] = record(b, KD_BANK)
    _, d["map_x"], d["map_y"] = record(b, MAP_BANK)
    d["d_clamp"] = u16(b, 0xC61B6)
    d["ki"] = u16(b, 0xC63E6)
    d["deadband"] = u16(b, 0xC62E4)
    d["i_clamp"] = u16(b, 0xC61BA)
    d["p_clamp"] = u16(b, 0xC61BC)
    d["sum_clamp"] = u16(b, 0xC61BE)
    d["lag_a"] = s16(b, 0xC63EC)
    d["lag_b"] = u16(b, 0xC63EE)
    d["gain"] = s16(b, 0xBF000 + u16(b, 0x2A1F0))
    d["t_clamp"] = u16(b, 0xC61B4)
    d["idx_clamp"] = b[0xC64F0]
    return d


def lerp(X, Y, i):
    """listing-style LERP (0x29DC6..0x29E32): flat outside, walk, 32-bit sub/mul, SIGNED divq trunc toward 0, zxh."""
    if not X[0] < i:
        return Y[0]
    if not i < X[-1]:
        return Y[-1]
    k = 1
    while X[k] <= i:
        k += 1
    num = (Y[k] - Y[k - 1]) * (i - X[k - 1])
    den = X[k] - X[k - 1]
    q = int(num / den) if num * den >= 0 else -int(abs(num) // abs(den))
    return (Y[k - 1] + q) & 0xFFFF


def table(X, Y, n=256):
    return np.array([lerp(X, Y, i) for i in range(n)], np.int64)


# ---------------------------------------------------------------------------------------------------------------------
# the integer lane (P-only when Ki = Kd = 0; I and D mirrored for the V282 comparison), scalar, my own transcription
# ---------------------------------------------------------------------------------------------------------------------
class MyLane:
    def __init__(self, c):
        self.c = dict(c)
        self.kp_t = table(c["kp_x"], c["kp_y"])
        self.kd_t = table(c["kd_x"], c["kd_y"])
        self.map_t = table(c["map_x"], c["map_y"])
        self.reset()

    def reset(self):
        self.s = 0
        self.restart = False
        self.o = 0
        self.I8 = 0
        self.Eprev = 0x7FFFFFFF

    def demand(self, wire):
        """0xE4 wire (+ right) -> (idx, sp in the kit march convention sp = -sgn_fw*map).  Hands-off (bar 0, G 255)."""
        S = max(-0x4000, min(0x4000, -4 * int(wire)))
        prod = ((65025 & 0xFFFF) * S) >> 16
        v = prod >> 6
        v = max(-self.c["idx_clamp"], min(self.c["idx_clamp"], v))
        idx = abs(v)
        sgn = -1 if v < 0 else 1
        return idx, -sgn * int(self.map_t[idx])

    def tick(self, x, sp, idx, m=254):
        c = self.c
        bail = abs(x) > 12000
        s_old = 0 if self.restart else self.s
        s_new = ((c["fb_a"] * s_old) >> 10) + ((c["fb_b"] * (0 if bail else x)) >> 10)
        r26 = (s_new - s_old) if c["fb_op"] == "diff" else (s_new + s_old)
        r26 = max(-c["fb_clamp"], min(c["fb_clamp"], r26))
        if not bail:
            self.s = s_new
        self.restart = bail
        if bail:
            r26 = 0
        E = (sp << c["e_shift"]) - r26
        I = 0
        if c["ki"]:
            e5 = E >> 5
            db = c["deadband"]
            exc = e5 - db if e5 > db else (e5 + db if e5 < -db else 0)
            icl = (c["i_clamp"] << 10) >> 3
            I = max(-icl, min(icl, (self.I8 >> 3) + ((exc * c["ki"]) >> 3)))
            self.I8 = 0 if bail else I << 3
            if bail:
                I = 0
        kp = int(self.kp_t[idx])
        P = max(-c["p_clamp"], min(c["p_clamp"], (E * kp) >> 8))
        D = 0
        if c["d_clamp"]:
            kd = int(self.kd_t[idx])
            ep = self.Eprev if abs(self.Eprev) <= 768000 else E
            D = max(-c["d_clamp"], min(c["d_clamp"], ((E - ep) * kd) >> 3))
        self.Eprev = 0x7FFFFFFF if bail else E
        S = max(-c["sum_clamp"], min(c["sum_clamp"], (m * ((I >> 7) + P + D)) >> 8))
        if bail:
            S = 0
        o2 = ((c["lag_a"] * self.o) >> 10) + ((S * c["lag_b"]) >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        T = max(-c["t_clamp"], min(c["t_clamp"], (y * c["gain"]) >> 15))
        return T, dict(r26=r26, E=E, P=P, S=S, y=y, D=D, I=I)


def static_surface(c, idx_list=range(241), n_ticks=4000, m=254):
    """T(idx) at constant command, x = 0, marched from cold state until settled (my own march)."""
    out = []
    for i in idx_list:
        L = MyLane(c)
        sp = int(L.map_t[i])
        T = 0
        for _ in range(n_ticks):
            T, _ = L.tick(0, sp, i, m)
        out.append(T)
    return np.array(out)


# ---------------------------------------------------------------------------------------------------------------------
# LINEAR transfer functions of the lane (1 kHz, exact z), my own derivation from the arithmetic above
# ---------------------------------------------------------------------------------------------------------------------
TS = 1e-3


def zinv(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)


def H_fb(c, f):
    """r26 per x count."""
    zi = zinv(f)
    a, b = c["fb_a"] / 1024.0, c["fb_b"] / 1024.0
    num = (1 - zi) if c["fb_op"] == "diff" else (1 + zi)
    return b * num / (1 - a * zi)


def H_lag(c, f):
    zi = zinv(f)
    return (c["lag_b"] / 1024.0) * (1 + zi) / (32.0 * (1 - (c["lag_a"] / 1024.0) * zi))


def S_per_x(c, f, kp, kd=0.0, m=254):
    """PID sum S per x count at sp = 0 (P and D on E = -r26); sign: S = -(kp/256 + kd/8 (1-z^-1)) r26 * m/256."""
    zi = zinv(f)
    return -(kp / 256.0 + kd / 8.0 * (1 - zi)) * H_fb(c, f) * m / 256.0


def P_per_x_mag(c, f, kp, kd=0.0):
    """|PID/x| before the taper (the record's '|P/x|' metric: V294 2.079, V282 44.90 at 20 Hz)."""
    zi = zinv(f)
    return np.abs((kp / 256.0 + kd / 8.0 * (1 - zi)) * H_fb(c, f))


def T_per_x(c, f, kp, kd=0.0, m=254):
    """delivered T (tap sign) per x count (x in the lane's input sign)."""
    return S_per_x(c, f, kp, kd, m) * H_lag(c, f) * c["gain"] / 32768.0


def T_per_wire_ff(c, f, slope_sp_per_wire, kp_eff=None, m=254):
    """FF path: T per wire count (small-signal), given d(sp<<e * Kp)/dwire already folded into slope (P counts per wire
    per 256): pass slope = d(sp*Kp)/dwire (sp counts * Kp units per wire)."""
    return (2 ** c["e_shift"]) * slope_sp_per_wire / 256.0 * m / 256.0 * H_lag(c, f) * c["gain"] / 32768.0
