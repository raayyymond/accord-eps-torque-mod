# -*- coding: utf-8 -*-
"""c3r1_intlane.py -- MY integer lane for C3-P / C3-F (written from the cave listing + the in-place edits + the V295
lane bytes; constants from the image and the cave hex) closed through a continuous plant at 0.1 ms sub-steps with the
exact 10-tick hold (slot 4 after the lane, offset e), integer sensors (theta 0.1-deg counts, the resolver-rate word in
gp-0x6abe units through Honda's integer EMA), the 2 ms transport, optional Coulomb/static friction (Karnopp), optional
constant road torque (crown), optional hand torque word |tq| for the freeze.  Batch over B independent runs (numpy).

Purposes (stability lens): (1) the integer loop's ring vs the linear model's ring; (2) small-signal limit cycles
(quantisation, hold, friction) after settling; (3) the A3 bound regime (crown at theta ~ 0) for a sustained
oscillation; (4) the rate-invalid state (op := 0 / held 0 -> D off).
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r1_model as M  # noqa: E402

I64 = np.int64


def s32(a):
    a = np.asarray(a, I64) & 0xFFFFFFFF
    return np.where(a >= 0x80000000, a - (1 << 32), a)


def s16(a):
    a = np.asarray(a, I64) & 0xFFFF
    return np.where(a >= 0x8000, a - 0x10000, a)


class Lane:
    """byte-level C3 lane (vectorised).  dkind 'fresh' (C3-P) | 'held' (C3-F)."""

    def __init__(self, des, B, policy="A3", icl=8192, ki=56, kp=112, kd=None, fade=254):
        self.des, self.B = des, B
        self.rows = des.rows
        self.kd = int(des.kd if kd is None else kd)
        self.kp, self.ki, self.icl = kp, ki, icl
        self.policy = policy
        self.fade = fade
        z = lambda: np.zeros(B, I64)  # noqa: E731
        self.s_old, self.I8, self.olag = z(), z(), z()
        self.lane_ok = np.ones(B, I64)
        self.log = {}

    def G(self, vc):
        return M.walk_G(self.rows, int(vc))

    def tick(self, thh, abe, xh, vc, tq, sp, ramp=0x8000, rate_valid=None):
        """thh = gp-0x6a00 (held), abe = gp-0x6abe, xh = gp-0x6a56 (held), vc = gp-0x6a5e (scalar), tq = |gp-0x4f60|,
        sp = gp-0x69ae.  Returns T = gp-0x6b38 (tap sign)."""
        x = s16(thh)
        s_new = s32(8192 * x) >> 10                                   # a = 0, b = 8192
        s_old = np.where(self.lane_ok == 1, self.s_old, 0)
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)              # E2 add, C 65535
        self.s_old = s_new
        E = s32((s16(sp) << 2) - r26)                                 # cave 0xC4C00/02
        if self.des.dkind == "fresh":
            op = s16(abe)
            op = np.where(((op + 13000) & 0xFFFFFFFF) > 26000, 0, op)  # Honda's validity form, cmovh
        G = self.G(vc)
        Ep = s32(E * G) >> 8                                          # mul ; sar 8
        frozen = tq > 512                                             # ld.hu -0x4f68 ; cmp ; bh
        if self.policy in ("A3", "A2"):
            ath = np.abs(s16(thh))
            sh = 4 if vc <= 2880 else 6
            bound = (ath << sh) + 1250
            if self.policy == "A3" and vc <= 1382:
                bound = np.minimum(bound, 4096)
            t = self.I8 >> 10
            t = np.where(Ep >= 0, t, -t)
            frozen = frozen | (t >= bound) | ((ramp & 0x8000) == 0)
        e5 = np.where(frozen, 0, Ep >> 5)
        icl = (self.icl << 10) >> 3
        inc = s32(e5 * self.ki) >> 3
        I = np.clip(s32((self.I8 >> 3) + inc), -icl, icl)
        P = np.clip(s32(Ep * self.kp) >> 8, -15360, 15360)
        if self.des.dkind == "fresh":
            D = np.clip(s32(self.kd * op) >> 3, -10240, 10240)
        else:
            D = np.clip(s32(-self.kd * s16(xh)) >> 3, -10240, 10240)
        S = s32((I >> 7) + P + D)
        Sf = s32(S * self.fade) >> 8
        Sc = np.clip(Sf, -15360, 15360)
        t1 = s32(Sc * 507) >> 10
        t2 = s32(992 * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        r11 = s32(yr * (-5346)) >> 15                                 # pol * fwd = -5346
        T = np.clip(r11, -3072, 3072)
        self.I8 = s32(I << 3)
        self.log = dict(E=E, Ep=Ep, I=I, P=P, D=D, S=S, frozen=frozen)
        return T


def simulate(des, pl, v, n_ticks, sp_deg, B=1, e=0, kappa=1.0, jb=1.0, fric=0.0, Fs_ratio=1.25, crown=0.0,
             tq=None, th0=0.0, policy="A3", sub=10, rate_noise=0.0, seed=0, rf_sub=0, invalid_after=None, kd=None,
             tau_ms=None, record=("th", "T", "I", "frozen"), sat=None, d_ext=None, fork=None):
    """sp_deg: (B, n_ticks) or callable(n)->(B,) setpoint (deg, theta frame).  fric = Coulomb (T counts); Fs = Fs_ratio*fric.
    crown: constant road torque on the plant (T counts, + = left).  tq: (B, n_ticks) |hand torque word| or None.
    Returns dict of (B, n_ticks) arrays."""
    rng = np.random.default_rng(seed)
    lane = Lane(des, B, policy=policy, kd=kd)
    J, b, k = pl.J * jb, pl.b * jb, pl.k
    h = M.TS / sub
    tau = pl.tau if tau_ms is None else tau_ms
    nd = int(round(tau * 1e-3 / h))
    ubuf = np.zeros((nd + 1, B))
    up = 0
    th = np.full(B, float(th0))
    om = np.zeros(B)
    thh = np.round(10 * th).astype(I64)
    xh = np.zeros(B, I64)
    ema = np.zeros(B, I64)
    hist = np.tile(th, (max(rf_sub, 1) + 1, 1))
    hp = 0
    vc = M.spd(v)
    rec = {kk: np.zeros((B, n_ticks)) for kk in record}
    samples = []
    th_log = []
    fI = np.zeros(B)
    sp_held = np.zeros(B)
    Fc, Fs = fric, fric * Fs_ratio
    for n in range(n_ticks):
        # sensors at t_n
        if rf_sub > 0:
            w_meas = (th - hist[(hp - rf_sub) % len(hist)]) / (rf_sub * h)
        else:
            w_meas = om
        raw = np.round(M.ABE * kappa * w_meas + (rng.normal(0, rate_noise, B) if rate_noise else 0)).astype(I64)
        if invalid_after is not None and n >= invalid_after:
            raw = np.full(B, 0x7FFF, I64)
            ema = np.full(B, 0x7FFF * 1024, I64)
            abe = np.full(B, 0x7FFF, I64)
        else:
            raw = np.clip(raw, -13000, 13000)
            ema = ema + (s32((raw * 1024 - ema) * 37) >> 7)
            abe = ema >> 10
        sp = np.asarray(sp_deg(n) if callable(sp_deg) else sp_deg[:, n], float)
        if fork is not None:                     # fork angle integral stand-in: 100 Hz, round trip fork[1] ms
            tau_o, rt = fork
            th_log.append(th.copy())
            if n % 10 == 0:
                j = max(0, len(th_log) - 1 - int(rt))
                fI[:] = fI + (sp - th_log[j]) * 0.01 / tau_o
                sp_held[:] = sp + fI
            sp = sp_held.copy()
        spc = np.clip(4 * np.round(10 * sp).astype(I64), -0x4000, 0x4000)   # raw = -10 sp ; gp-0x69ae = clamp(-4 raw)
        tqn = np.zeros(B, I64) if tq is None else np.asarray(tq[:, n], I64)
        T = lane.tick(thh, abe, xh, vc, tqn, spc)
        # this tick's slot-4 samples (theta counts, gp-0x6a56 from this tick's abe); slot 4 AFTER the lane refreshes the
        # hold from the sample taken e ticks earlier (e == 0 -> this tick's: ages 1..10)
        if invalid_after is not None and n >= invalid_after:
            xs = np.zeros(B, I64)
        else:
            xs = np.clip(-(s32(abe * 48 * 1159) >> 15), -12000, 12000)
        samples.append((np.round(10 * th).astype(I64), xs))
        if len(samples) > e + 1:
            samples.pop(0)
        if n % 10 == 4:
            thh, xh = samples[0] if len(samples) == e + 1 else samples[0]
        for kk in record:
            if kk == "th":
                rec[kk][:, n] = th
            elif kk == "T":
                rec[kk][:, n] = T
            elif kk == "I":
                rec[kk][:, n] = lane.log["I"] >> 7
            elif kk == "frozen":
                rec[kk][:, n] = lane.log["frozen"]
            elif kk == "D":
                rec[kk][:, n] = lane.log["D"]
            elif kk == "P":
                rec[kk][:, n] = lane.log["P"]
        # plant sub-steps (u = -T, + = left), Karnopp friction, semi-implicit Euler
        for j in range(sub):
            ubuf[up] = -T.astype(float)
            up = (up + 1) % (nd + 1)
            u = ubuf[up] + crown
            spring = k * th if sat is None else k * sat * np.tanh(th / sat)
            fnet = u - spring - b * om
            if d_ext is not None:
                fnet = fnet + d_ext(n)
            if np.any(np.asarray(Fc) > 0):
                stuck = (om == 0.0) & (np.abs(fnet) <= Fs)
                fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
                om_new = om + np.where(stuck, 0.0, (fnet - Fc * fdir) / J) * h
                om_new[stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om)))] = 0.0
            else:
                om_new = om + fnet / J * h
            hist[hp] = th
            hp = (hp + 1) % len(hist)
            om = om_new
            th = th + om * h
    return rec

