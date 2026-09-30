# -*- coding: utf-8 -*-
"""advA_vec.py -- numpy lane-parallel copy of advA_lane.Lane.tick (engaged path, gate not live, addend 0).
Validated tick-for-tick against the scalar mirror in a3/a4 before any number is used.  int64 arrays, every
32-bit op wrapped by w32 (so a wrap would SHOW, not be hidden by int64)."""
import numpy as np
import advA_lane as A

M32 = np.int64(0xFFFFFFFF)


def w32(v):
    v = np.asarray(v, np.int64) & M32
    return np.where(v & 0x80000000, v - (1 << 32), v)


def sxh(v):
    v = np.asarray(v, np.int64) & 0xFFFF
    return np.where(v & 0x8000, v - 0x10000, v)


class VecLane:
    def __init__(self, c, B):
        self.c = c; self.B = B
        self.a = np.int64(c["fb_a"]); self.b = np.int64(c["fb_b"] & 0xFFFF); self.C = np.int64(c["fb_clamp"])
        self.esh = int(c["e_shift"]); assert c["fb_op"] == "diff" and c["ki"] == 0
        self.pcl = np.int64(c["p_clamp"]); self.scl = np.int64(c["sum_clamp_u"]); assert c["sum_clamp_s"] == c["sum_clamp_u"]
        self.la = np.int64(c["lag_a"]); self.lb = np.int64(c["lag_b"]); self.gain = np.int64(c["gain"])
        self.tcl = np.int64(c["t_clamp_u"]); assert c["t_clamp_s"] == c["t_clamp_u"]
        assert c["d_clamp"] == 0 and all(v == 0 for v in c["kd_y"])
        self.kp_tab = np.array([A.lerp(c["kp_x"], c["kp_y"], i) for i in range(256)], np.int64)
        self.map_tab = np.array([A.lerp(c["map_x"], c["map_y"], i) for i in range(256)], np.int64)
        self.reset()
        self.maxp = {}

    def reset(self):
        B = self.B
        self.s = np.zeros(B, np.int64); self.sent = np.zeros(B, np.int64); self.o = np.zeros(B, np.int64)

    def _mx(self, k, v):
        m = int(np.abs(v).max()) if np.size(v) else 0
        if m > self.maxp.get(k, 0):
            self.maxp[k] = m

    def tick(self, x, sp, idx, m=254, pol=1, bail=None):
        x = np.asarray(x, np.int64) * np.ones(self.B, np.int64)
        bail = (np.abs(x) > 12000) if bail is None else (np.asarray(bail, bool) | (np.abs(x) > 12000))
        s_old = np.where(self.sent == 1, self.s, 0)
        bx = w32(sxh(x) * self.b); as_ = w32(self.a * s_old)
        self._mx("bx", bx); self._mx("as", as_)
        s_new = w32((as_ >> 10) + (bx >> 10))
        r26raw = w32(s_new - s_old)
        r26 = np.clip(r26raw, -self.C, self.C)
        self.s = np.where(bail, self.s, s_new)
        self.sent = np.where(bail, 2, 1)
        r26 = np.where(bail, 0, r26)
        E = w32(w32(np.asarray(sp, np.int64) << self.esh) - r26)
        kp = self.kp_tab[np.asarray(idx) * np.ones(self.B, np.int64)]
        pp = w32(E * kp); self._mx("E*Kp", pp)
        P = np.clip(pp >> 8, -self.pcl, self.pcl)
        mS = w32(np.asarray(m, np.int64) * P); self._mx("m*S", mS)
        S = sxh(np.clip(mS >> 8, -self.scl, self.scl))
        S = np.where(bail, 0, S)
        p12 = w32(S * self.lb); p7 = w32(self.la * self.o)
        self._mx("S*lb", p12); self._mx("la*o", p7)
        o_new = w32((p12 >> 10) + (p7 >> 10))
        y = w32(self.o + o_new) >> 5
        self.o = o_new
        yr = sxh(w32(y * 0x8000) >> 15); self._mx("y*ramp", w32(y * 0x8000))
        k = w32(sxh(pol) * sxh(self.gain))
        tt = w32(yr * k); self._mx("y*gain", tt)
        T = np.clip(tt >> 15, -self.tcl, self.tcl)
        self.last = dict(r26=r26, r26raw=r26raw, P=P, S=S, y=y, E=E)
        return T
