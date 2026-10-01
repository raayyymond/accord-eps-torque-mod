# -*- coding: utf-8 -*-
"""c2r2_intlane.py -- my OWN integer lane (P-type fresh D / F-type held D) on a LINEAR continuous plant (no Coulomb),
1 kHz, exact 100 Hz holds, to check that the linear least-damped-pole predictions survive the integer arithmetic
(sar floors, the e5 = E'>>5 I quantiser, the EMA >> 10, the output-lag >> 5) at the binding points, and that no
integer limit cycle appears in 5-30 Hz once settled.  Every line mirrors an instruction or a cal of the design pages
(rev2-A sec 1.4 p2_tick; lane_mirror_v295.lane_tick for the shared lane) -- written independently here.
ANALYSIS ONLY."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c2r2_model as M  # noqa: E402


def sar(x, n):
    return x >> n          # Python floor shift == V850 sar on int


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def sim(des, pl, v, th0=0.0, sp_deg=2.0, n_ticks=4000, pol=-1):
    A, B, Ct, Cw = M.plant_ct(pl)
    Phi, Gam = M.zoh(A, B)
    x = np.zeros(A.shape[0])
    x[0] = th0
    G = des.G(v)
    ub = [0.0] * pl.d
    s_ema = 0x7FFFFFFF
    thc_hist = []
    abe_hist = []
    th_h = int(round(10 * th0))
    x_h = 0
    s_old = 8 * th_h
    I8 = 0
    olag = 0
    th_log, T_log = [], []
    raw = int(round(-10 * sp_deg))
    sp = clamp(-(raw << 2), -0x4000, 0x4000)
    for n in range(n_ticks):
        th = float(Ct @ x)
        om = float(Cw @ x)
        # FUN_00068f52/00068fbe: gp-0x4f50 (motor-rate counts; sign so that gp-0x6abe = -4.712 per deg/s, pol -1)
        r4f50 = clamp(int(round(M.ABE * om)), -13000, 13000)
        # FUN_00041464: EMA, alpha 37/128 in Q10
        if s_ema == 0x7FFFFFFF:
            s_ema = r4f50 * 1024
        else:
            s_ema = s32(s_ema + sar(s32((r4f50 * 1024 - s_ema) * 37), 7))
        abe = s_ema >> 10
        thc_hist.append(int(round(10 * th)))
        abe_hist.append(abe)
        # ---- lane ----
        s_new = sar(8192 * th_h, 10)                       # a = 0 ; b = 8192
        r26 = clamp(s32(s_old + s_new), -65535, 65535)    # E2 add ; C 65535
        s_old = s_new
        E = s32((sp << 2) - r26)                          # cave: shl 2 ; sub r26
        Ep = s32(E * G) >> 8                              # E' = (E G) >> 8
        e5 = Ep >> 5                                      # 0x29D7C (no freeze: hands off, ramp full)
        icl = ((4096) << 10) >> 3
        I = clamp(s32((I8 >> 3) + (s32(e5 * int(des.ki)) >> 3)), -icl, icl)
        I8 = s32(I << 3)
        P = clamp(s32(Ep * int(des.kp)) >> 8, -15360, 15360)
        if des.dkind == "fresh":
            op = abe if ((abe + 13000) & 0xFFFFFFFF) <= 26000 else 0
            D = clamp(s32(int(des.kd) * op) >> 3, -10240, 10240)
        else:
            D = clamp(s32(-int(des.kd) * x_h) >> 3, -10240, 10240)
        S = s32((I >> 7) + P + D)
        Sf = s32(S * 254) >> 8
        Sc = clamp(Sf, -15360, 15360)
        o_new = s32((s32(Sc * 507) >> 10) + (s32(992 * olag) >> 10))
        y = s32(olag + o_new) >> 5
        olag = o_new
        yr = clamp(s32(y * 0x8000) >> 15, -32768, 32767)
        T = clamp(s32(yr * (pol * 5346)) >> 15, -3072, 3072)
        # ---- slot 4 after the lane ----
        if n % 10 == 4:
            age = pl.ea if pl.ea > 0 else 0
            j = len(thc_hist) - 1 - age
            j = max(j, 0)
            th_h = clamp(thc_hist[j], -32768, 32767)
            a_s = abe_hist[j]
            x_h = clamp(pol * (s32(a_s * 48 * 1159) >> 15), -12000, 12000)
        # ---- plant: u (+left) = -T (T + = steer right) ----
        ub.append(-float(T))
        u = ub.pop(0)                                     # u[n] = -T[n-d]
        x = Phi @ x + Gam[:, 0] * u
        th_log.append(th)
        T_log.append(T)
    return np.array(th_log), np.array(T_log)


def ring_fit(th, t0=300, f_lo=0.5, f_hi=8.0):
    """dominant ring after t0: frequency from zero crossings of the detrended signal, decay from successive peaks"""
    y = th[t0:] - th[-500:].mean()
    zc = np.where(np.diff(np.sign(y)) != 0)[0]
    if len(zc) < 4:
        return float("nan"), float("nan"), len(zc)
    per = 2 * np.mean(np.diff(zc[:8])) * 1e-3
    f = 1 / per
    pk = []
    for a, b in zip(zc[:-1], zc[1:]):
        seg = np.abs(y[a:b + 1])
        pk.append(seg.max())
    pk = np.array(pk[:8])
    if len(pk) >= 3 and pk[0] > 0 and pk[-1] > 0:
        dec = np.log(pk[0] / pk[-1]) / (len(pk) - 1)       # log decrement per half cycle
        zeta = dec / math.sqrt(math.pi ** 2 + dec ** 2)
    else:
        zeta = float("nan")
    return f, zeta, len(zc)


def hf_rms(T, lo=5, hi=30):
    y = T[-2000:] - T[-2000:].mean()
    Y = np.fft.rfft(y * np.hanning(len(y)))
    f = np.fft.rfftfreq(len(y), 1e-3)
    band = (f >= lo) & (f <= hi)
    return float(np.sqrt(np.sum(np.abs(Y[band]) ** 2)) / len(y) * 2)


if __name__ == "__main__":
    D = M.load_designs()
    cases = [("P2", "b_q*J1.0+h10", 26.9), ("P2", "b_q*J1.0", 15.5), ("P2", "b_q*J1.0+h10", 15.75),
             ("F2", "b_q*J1.0+h10", 15.5), ("F2", "b_q*J1.0", 15.5), ("P2", "b_lo*J_hi*tau6+h10", 8.0),
             ("P2", "J1.0+h10", 1.0), ("P2", "nominal", 26.9), ("F2", "nominal", 26.9),
             ("D2a", "b_q*J1.0+h10", 26.9), ("B0r", "b_q*J1.0+h10", 15.5)]
    print("design member                 v     | linear: rho    least-damped f/zeta | integer sim: ring f / zeta  zc  | "
          "settled 5-30 Hz T rms (counts)")
    for dn, mn, v in cases:
        pl = M.member(mn, v)
        rho, z, f, _ = M.Periodic(D[dn], pl, v).rho_poles()
        th, T = sim(D[dn], pl, v, sp_deg=2.0, n_ticks=6000)
        fr, zr, nzc = ring_fit(th)
        print(f"{dn:4s} {mn:22s} {v:5.2f} | {rho:.4f}  {f:5.2f} Hz {z:.3f}        | {fr:5.2f} Hz {zr:.3f}  {nzc:3d}"
              f"  | {hf_rms(T):.3f}   final err {2.0 - th[-500:].mean():+.3f} deg")
    # light_b (report-only) on F2 at 27 m/s, +h10: the linear model says rho > 1 -> does the integer lane limit-cycle?
    for dn in ("F2", "P2"):
        pl = M.light_b(27.0)
        pl.ea = 10
        th, T = sim(D[dn], pl, 27.0, sp_deg=2.0, n_ticks=8000)
        y = th[-3000:] - th[-3000:].mean()
        print(f"light_b+h10 {dn} @27: last-3 s theta p-p {y.max() - y.min():.3f} deg, T p-p {T[-3000:].max() - T[-3000:].min()}, "
              f"ring fit {ring_fit(th, t0=4000)}")
