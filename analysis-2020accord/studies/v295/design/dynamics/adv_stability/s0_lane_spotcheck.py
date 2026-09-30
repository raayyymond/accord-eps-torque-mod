# -*- coding: utf-8 -*-
"""s0_lane_spotcheck.py -- adversary `stability` (V295 A1017).  My OWN byte-exact lane, written from the census listing
pseudocode (V294-LKAS-PID-DESIGN-SPACE.md section 2), NOT imported from the harness or the plant study.

1. read every cell I use BY ADDRESS from the V294 image (sha-checked), little-endian, my own reader;
2. my lane == the golden model (lkas_fb_lag + lkas_rate_pid_tick) tick for tick, V294 and A1017 cells, random x/sp;
3. SPOT CHECK OF THE HARNESS: harness Lane == golden model on the same ticks (one lane tick, required by the brief).
Analysis only: nothing built/flashed/sent.
"""
import hashlib
import os
import sys
from dataclasses import replace

import numpy as np

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "model"))
IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
       "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
       "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
SEL = 7


def u16(b, a):
    return b[a] | (b[a + 1] << 8)


def s16(b, a):
    v = u16(b, a)
    return v - 65536 if v >= 32768 else v


def u32(b, a):
    return u16(b, a) | (u16(b, a + 2) << 16)


def rec(b, bank):
    r = u32(b, bank + 4 * SEL)
    n = u16(b, r)
    return [u16(b, r + 2 + 2 * i) for i in range(n)], [u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)]


def read_cells(path=IMG):
    b = open(path, "rb").read()
    h = hashlib.sha256(b).hexdigest()
    assert h == SHA, h
    c = dict(fb_a=s16(b, 0xC63E8), fb_b=u16(b, 0xC63EA), fb_C=u16(b, 0xC62E6), lag_a=s16(b, 0xC63EC),
             lag_b=u16(b, 0xC63EE), p_cl=u16(b, 0xC61BC), s_cl=u16(b, 0xC61BE), t_cl=u16(b, 0xC61B4),
             ki=u16(b, 0xC63E6), d_cl=u16(b, 0xC61B6))
    c["fb_a_bytes"] = b[0xC63E8:0xC63EA].hex()
    c["gain_disp"] = u16(b, 0x2A1F0)
    c["gain"] = s16(b, 0xBF000 + c["gain_disp"])
    c["e_shift"] = u16(b, 0x29D76) & 0x1F
    c["op_28FA4"] = u16(b, 0x28FA4)
    c["kp_X"], c["kp_Y"] = rec(b, 0xCB994)
    c["kd_X"], c["kd_Y"] = rec(b, 0xCB7D4)
    c["map_X"], c["map_Y"] = rec(b, 0xC9A88)
    return c


def lerp(X, Y, x):
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            num, den = (Y[i + 1] - Y[i]) * (x - X[i]), X[i + 1] - X[i]
            q = abs(num) // abs(den)
            return Y[i] + (-q if (num < 0) != (den < 0) else q)
    raise AssertionError


class MyLane:
    """batch lane, int64, V294 structure (diff operand, Ki = 0, Kd = 0 as built; D kept general for V282 tests).
    Per tick (census section 2):  s_new = (a*s>>10) + (b*x>>10) ; r26 = clamp(s_new - s_old, +-C) ; s = s_new
    E = (sp << sh) - r26 ; P = clamp((E*Kp)>>8, +-Pcl) ; S = clamp((m*P)>>8, +-Scl)
    o' = (la*o>>10) + (S*lb>>10) ; y = (o + o')>>5 ; o = o' ; T = clamp((y*gain)>>15, +-Tcl)     (ramp = 0x8000, pol = 1)
    bail |x| > 12000: r26 = 0, PID skipped (S = 0 into the output lag), next tick s_old := 0."""

    def __init__(self, B, fb_a, fb_b, C=1024, sh=2, kp=960, la=992, lb=507, gain=5346, pcl=15360, scl=15360, tcl=3072,
                 op="diff"):
        self.B = B
        self.a, self.b, self.C, self.sh, self.kp = (np.asarray(v, np.int64) * np.ones(B, np.int64) for v in (fb_a, fb_b, C, sh, kp))
        self.la, self.lb, self.gain, self.pcl, self.scl, self.tcl = la, lb, gain, pcl, scl, tcl
        self.op = op
        self.s = np.zeros(B, np.int64)
        self.o = np.zeros(B, np.int64)
        self.rst = np.zeros(B, bool)
        self.max_as = np.zeros(B, np.int64)
        self.n_Cbind = np.zeros(B, np.int64)
        self.n_Pbind = np.zeros(B, np.int64)
        self.max_r26 = np.zeros(B, np.int64)

    def tick(self, x, sp, m=254):
        x = np.asarray(x, np.int64)
        bail = np.abs(x) > 12000
        s_old = np.where(self.rst, 0, self.s)
        pa = self.a * s_old
        self.max_as = np.maximum(self.max_as, np.abs(pa))
        s_new = (pa >> 10) + ((self.b * np.where(bail, 0, x)) >> 10)
        r = (s_new - s_old) if self.op == "diff" else (s_new + s_old)
        self.max_r26 = np.maximum(self.max_r26, np.abs(r))
        self.n_Cbind += (np.abs(r) > self.C) & ~bail
        r = np.clip(r, -self.C, self.C)
        self.s = np.where(bail, self.s, s_new)
        self.rst = bail
        r = np.where(bail, 0, r)
        E = (np.asarray(sp, np.int64) << self.sh) - r
        Pr = (E * self.kp) >> 8
        self.n_Pbind += (np.abs(Pr) > self.pcl) & ~bail
        P = np.clip(Pr, -self.pcl, self.pcl)
        S = np.clip((np.asarray(m, np.int64) * P) >> 8, -self.scl, self.scl)
        S = np.where(bail, 0, S)
        o2 = ((self.la * self.o) >> 10) + ((S * self.lb) >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        T = np.clip((y * self.gain) >> 15, -self.tcl, self.tcl)
        return T, r


def main():
    import eps_lkas_chain_model as M
    c = read_cells()
    print("V294 image sha OK.  cells by address:", {k: v for k, v in c.items() if not k.endswith("_X") and not k.endswith("_Y")})
    print("  Kp X/Y", c["kp_X"], c["kp_Y"], " Kd X/Y", c["kd_X"], c["kd_Y"], " map Y", c["map_Y"])
    assert c["fb_a"] == 1011 and c["fb_a_bytes"] == "f303" and c["fb_b"] == 567 and c["fb_C"] == 1024
    assert c["lag_a"] == 992 and c["lag_b"] == 507 and c["gain"] == 5346 and c["e_shift"] == 2
    assert c["op_28FA4"] == 0xD189, hex(c["op_28FA4"])          # subr r9,r26 (89 d1 LE)
    print("  A1017: 0xC63E8 bytes F3 03 -> F9 03 = %d" % int.from_bytes(bytes([0xF9, 0x03]), "little"))
    rng = np.random.default_rng(20260930)
    tot = 0
    mism_mine = 0
    mism_h = 0
    sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "design", "harness"))
    import v295_harness as H
    base = H.Cells.v294()
    for fa in (1011, 1017):
        cal = replace(M.Calibration(), fb_clamp=1024, fb_lag_a=fa, fb_lag_b=567, fb_op="diff", e_shift=2,
                      kp_x=tuple(c["kp_X"]), kp_y=tuple(c["kp_Y"]), kd_x=tuple(c["kd_X"]), kd_y=tuple(c["kd_Y"]),
                      pid_d_clamp=0, pid_ki=0, pid_p_clamp=15360, sum_clamp=15360, out_lag_a=992, out_lag_b=507,
                      lkas_forward_gain=5346, out_clamp=3072, assist_map_x=tuple(c["map_X"]), assist_map_y=tuple(c["map_Y"]))
        B, N = 6, 8000
        lane = MyLane(B, fa, 567)
        hl = H.Lane([base.replace(fb_a=fa, name="A%d" % fa)] * B)
        sts = [M.EpsState() for _ in range(B)]
        # x: random walk with occasional big jumps (incl. |x| up to 12000 to hit the clamp and int32 corners)
        x = np.cumsum(rng.integers(-300, 301, (B, N)), axis=1)
        x = np.clip(x, -12000, 12000)
        idxs = rng.integers(0, 241, (B, N // 10))
        sg = rng.choice([-1, 1], (B, N // 10))
        for n in range(N):
            fr = n // 10
            sp = np.array([sg[i, fr] * lerp(c["map_X"], c["map_Y"], int(idxs[i, fr])) for i in range(B)], np.int64)
            T, r = lane.tick(x[:, n], sp)
            Th, _ = hl.tick(x[:, n], sp, idxs[:, fr].astype(np.int64), np.full(B, 254, np.int64))
            for i in range(B):
                fb = M.lkas_fb_lag(int(x[i, n]), sts[i], cal)
                g = M.lkas_rate_pid_tick(int(sp[i]), fb, int(idxs[i, fr]), sts[i], cal, pol=1, taper=254)
                mism_mine += int(g["T"] != T[i]) + int(fb != r[i])
                mism_h += int(g["T"] != Th[i])
                tot += 1
        print("  fb_a %d: my lane vs golden: %d mismatches (T and r26) over %d ticks; harness Lane vs golden: %d; "
              "max |r26| %d (C binds %d), max |a*s| %.3e" % (fa, mism_mine, tot, mism_h, lane.max_r26.max(),
                                                           lane.n_Cbind.sum(), lane.max_as.max()))
    print("RESULT", "PASS" if mism_mine == 0 and mism_h == 0 else "FAIL")


if __name__ == "__main__":
    main()
