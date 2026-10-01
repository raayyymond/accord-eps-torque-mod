# -*- coding: utf-8 -*-
"""c3r2_intlane.py -- the INTEGER lane (C3-rev2-P / -F, design section 1.4 + lane_mirror_v295.py arithmetic, every floor
and clamp) around a continuous plant (0.1 ms sub-steps, tanh spring, optional Karnopp friction, optional fork outer
integral), with the exact 100 Hz hold at any age offset.  Used to check the linear predictions at the binding points.

Lane (per 1 kHz tick):
  th_c   = round(10 th)                     gp-0x6a00 (0.1 deg counts), refreshed once per 10 ticks (age offset e)
  r26    = clamp(s_old + (8192 th_c >> 10), +-65535) ; s_old = 8192 th_c >> 10          (E1/E2, a=0 b=8192 C=65535)
  E      = (sp << 2) - r26,   sp = 4 th_sp_c                                               (E4 + displaced shl/sub)
  abe    = EMA(1024 x)>>10, x = round(-ABE_PER kappa w) (pol = -1), alpha 37/128          (FUN_00041464)
  [P]    G = walk(GB-P, floor(230.4 v)) ; Ep = (E G) >> 8 ; D = clamp((48 abe) >> 3, +-10240)
  [F]    G = walk(GB-F) ; D = clamp((-24 x_h) >> 3), x_h = 6a56 = held 8 w_ema (E5a/E5b)
  policy hard freeze |tq| > 512 ; opposing freeze |tq| > 300 & sign(hand) != sign(Ep) ; A3 bound (|th_c| << 4|6) + 1250
         (knee 2880 counts), cap 4096 below 1382 counts ; ramp
  I      = clamp((I8>>3) + (((Ep>>5) * 40) >> 3), +-1048576) ; P = clamp((Ep 112) >> 8, +-15360)
  S      = (I >> 7) + P + D ; Sf = (S f) >> 8, f = 254 ; SCL +-15360 ; output lag 992/507 ; T = (y (-5346)) >> 15, OCL 3072
  u = -T (plant convention, + left)."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


class IntLane:
    def __init__(self, des, v):
        self.des = des
        self.vc = M.spd_counts(v)
        self.G = M.g_walk(self.vc, M.ROWS[des.table])
        self.s_old = 0
        self.I8 = 0
        self.ema1024 = 0
        self.olag = 0
        self.xh = 0
        self.frz = 0

    def tick(self, thc, sp, wx, tq=0, tqs=0, refresh=False, ema_for_hold=None):
        des = self.des
        # FUN_00041464: abe EMA of the 1 kHz motor rate (x = gp-0x4f50 counts)
        self.ema1024 = self.ema1024 + (((wx * 1024 - self.ema1024) * 37) >> 7)
        abe = self.ema1024 >> 10
        s_new = (8192 * thc) >> 10
        r26 = clamp(self.s_old + s_new, -65535, 65535)
        self.s_old = s_new
        E = s32((sp << 2) - r26)
        Ep = s32(E * self.G) >> 8
        frozen = tq > 512
        if not frozen and tq > 300 and ((tqs ^ Ep) < 0):
            frozen = True
        if not frozen:
            sh = 4 if self.vc <= 2880 else 6
            bound = (abs(thc) << sh) + 1250
            if self.vc <= 1382:
                bound = min(bound, 4096)
            t = (self.I8 >> 10) if Ep >= 0 else -(self.I8 >> 10)
            if t >= bound:
                frozen = True
        self.frz += frozen
        e5 = 0 if frozen else (Ep >> 5)
        I = clamp((self.I8 >> 3) + (s32(e5 * int(des.ki)) >> 3), -1048576, 1048576)
        P = clamp(s32(Ep * int(des.kp)) >> 8, -15360, 15360)
        if des.dop == "fresh":
            D = clamp(s32(int(des.kd) * abe) >> 3, -10240, 10240)
        else:   # held 6a56 = pol * ((abe * 48 * 1159) >> 15), pol = -1 ; D = (-Kd x) >> 3
            D = clamp(s32(-int(des.kd) * self.xh) >> 3, -10240, 10240)
        if refresh:
            self.xh = clamp(-((abe * 48 * 1159) >> 15), -12000, 12000)
        S = (I >> 7) + P + D
        self.I8 = I << 3
        Sf = s32(S * 254) >> 8
        Sc = clamp(Sf, -15360, 15360)
        t1 = s32(Sc * 507) >> 10
        t2 = s32(992 * self.olag) >> 10
        o_new = t1 + t2
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        T = clamp(s32(y * -5346) >> 15, -3072, 3072)
        return -T, dict(I=I >> 7, P=P, D=D, E=E)


def simulate(des, mem, v, a, frame=(1.0, 1.0), e=0, dur=30.0, fric=False, tau_o=None, pulse=(7.0, 120.0, 0.06),
             ramp_s=1.5, sub=10, seed=0):
    """curve hold: th_sp ramps 0 -> th_op over ramp_s, then held; a torque pulse excites the ring.  Returns arrays."""
    kap, jb = frame
    pl, ea = M.member(mem, v)
    p = M.M2.FAM["ms_free" if "ms_free" in mem else "nominal"].at(v)
    J, b, k = pl.J * jb, pl.b * jb, pl.k
    sat = M.sat(v)
    Fc, Fs = (p.Fc, p.Fs) if fric else (0.0, 0.0)
    th_op = M.theta_op(v, a) if a else 0.0
    lane = IntLane(des, v)
    d = pl.d
    e_tot = e + ea
    n = int(dur * 1000)
    th, om = 0.0, 0.0
    ubuf = [0.0] * (d + 1)
    hist = [0] * 32
    thh = 0
    Io = 0.0
    fl = [0.0] * 6
    out_th = np.zeros(n)
    out_T = np.zeros(n)
    out_I = np.zeros(n)
    hdt = 1e-3 / sub
    for i in range(n):
        t = i * 1e-3
        thc_now = int(round(10 * th))
        hist = [thc_now] + hist[:-1]
        # setpoint (fork stand-in adds an outer integral at 100 Hz on the measured angle, 60 ms round trip)
        ref = th_op * min(1.0, t / ramp_s) if a else 0.0
        if tau_o and i % 10 == 0:
            fl = [th] + fl[:-1]
            Io += 0.01 / tau_o * (ref - fl[-1])
        spd = ref + (Io if tau_o else 0.0)
        sp = 4 * int(round(10 * spd))
        refresh = (i % 10 == 0)
        thc_read = thh
        if e_tot < 0 and refresh:
            thc_read = thc_now
        wx = int(round(-M.ABE_PER * kap * om))
        u, lg = lane.tick(thc_read, sp, wx, refresh=refresh)
        if refresh:
            thh = hist[e_tot] if e_tot > 0 else thc_now
        ubuf = [u] + ubuf[:-1]
        uapp = ubuf[d]
        extra = pulse[1] if (pulse and pulse[0] <= t < pulse[0] + pulse[2]) else 0.0
        for _ in range(sub):
            spring = k * sat * math.tanh(th / sat)
            fnet = uapp + extra - spring - b * om
            if fric:
                if abs(om) < 1e-3 and abs(fnet) <= Fs:
                    om = 0.0
                    continue
                fnet -= Fc * (1 if om > 0 else -1 if om < 0 else (1 if fnet > 0 else -1))
            om += hdt * fnet / J
            th += hdt * om
        out_th[i], out_T[i], out_I[i] = th, u, lg["I"]
    return out_th, out_T, out_I, th_op, lane.frz / n


def ring_metrics(x, t0, t1, fs=1000.0):
    """dominant frequency (zero crossings of the detrended segment) and the log-decrement zeta from successive peaks."""
    seg = x[int(t0 * fs):int(t1 * fs)]
    seg = seg - np.mean(seg[-int(2 * fs):]) if len(seg) > 2 * fs else seg - seg.mean()
    zc = np.where(np.diff(np.sign(seg)) != 0)[0]
    f = (len(zc) - 1) / 2 / ((zc[-1] - zc[0]) / fs) if len(zc) > 3 else float("nan")
    pk = [abs(seg[zc[j]:zc[j + 1]]).max() for j in range(len(zc) - 1)] if len(zc) > 3 else []
    if len(pk) >= 4:
        r = np.array(pk[1:]) / np.array(pk[:-1])
        r = r[(r > 0) & np.isfinite(r)]
        dl = -np.log(np.median(r)) * 2   # half-cycles -> per cycle
        z = dl / math.sqrt(4 * math.pi ** 2 + dl ** 2)
    else:
        z = float("nan")
    return f, z, (max(pk) if pk else 0.0), (pk[-1] if pk else 0.0)


if __name__ == "__main__":
    out = []
    CASES = [  # (des, member, v, a, frame, e, tau_o, label)
        (M.C3R2P, "b_lo*ms_free", 11.9, 2.5, (0.83, 1.0), 10, None, "P worst ms_free product (lin rho 0.9989, 0.58 Hz z 0.030)"),
        (M.C3R2F, "b_lo*ms_free", 11.9, 2.5, (0.83, 1.0), 10, None, "F worst ms_free product (lin rho 0.9997, 0.59 Hz z 0.007)"),
        (M.C3R2F, "b_lo*ms_free", 11.9, 2.75, (0.83, 1.0), 10, None, "F at a 2.75 (lin rho 1.0002)"),
        (M.C3R2P, "b_lo*J_hi", 8.0, 2.5, (0.83, 1 / 1.155), 10, None, "P gated binding b_lo*J_hi (lin 1.62 Hz z 0.35)"),
        (M.C3R2P, "nominal", 11.9, 2.0, (1.0, 1.0), 0, None, "P nominal curve hold"),
    ]
    for des, mem, v, a, fr, e, tau, lab in CASES:
        for fric in (False, True):
            th, T, I, th_op, frz = simulate(des, mem, v, a, fr, e, dur=30.0, fric=fric, tau_o=tau)
            f, z, amax, alast = ring_metrics(th, 7.1, 30.0)
            pp_late = th[-5000:].max() - th[-5000:].min()
            out.append(f"{lab:58s} fric {int(fric)}: th_op {th_op:5.1f} mean(25-30s) {th[-5000:].mean():6.2f} ; ring "
                       f"{f:.2f} Hz zeta~{z:+.3f} ; max half-cycle {amax:.2f} deg ; late p-p {pp_late:.2f} deg ; "
                       f"I end {I[-1]:.0f} S ; freeze duty {frz:.2f}")
            print(out[-1], flush=True)
    (M.OUT / "intlane_out.txt").write_text("\n".join(out), encoding="utf-8")
