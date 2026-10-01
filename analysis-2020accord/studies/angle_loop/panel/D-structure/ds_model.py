# -*- coding: utf-8 -*-
r"""ds_model.py -- PANEL DESIGNER D-structure (2026-10-01): ONE linear model of every loop STRUCTURE this designer
evaluates, built TWO independent ways, plus the reference controllers (V282 / V294 / V295) under the same conventions.

ANALYSIS ONLY.  Builds no image, flashes nothing, sends nothing.

  (1) ANALYTIC: the LTI fundamental of the 100 Hz sample-and-hold (mean of z^-a, a = 1+e .. 10+e) composed with every LTI
      block of the lane, the 5.05 Hz output lag, the transport delay and the ZOH-discretised plant (stab_lin / harness_freq
      convention).  Used for PM (minimum over EVERY |L| = 1 crossing), LTI GM, Ms, |T|, |T_ref|, M20, L20, Re(T/omega).
  (2) EXACT PERIODIC: the 1 kHz lane written tick by tick as affine rows over the state, slot 4 refreshing the held
      operands on n % 10 == 4 AFTER the lane (TRACE angle sec 1.1/1.3), the lifted 10-tick monodromy for stability, the
      least-damped closed-loop poles and the exact gain margin; and (cross-check of (1)) the EXACT same-frequency harmonic
      of the lifted system, computed by solving the periodic steady state at every frequency.

STRUCTURES (Des.kind / Des.dsrc / Des.lead), every one an edit of the V295 lane FUN_00028ea6 (decompile first; the
integer forms are in ds_lane.py and the design page):
  kind 'angle'  : the C1 skeleton -- x := gp-0x6a00 (E1), add (E2), sp := gp-0x69ae (E4), a 0 / b 8192 / C 65535:
                  r26 = 8 th_h[n] + 8 th_h[n-1] (0.1 deg counts), E = 4 sp - r26 = 16 (th_sp - th_h) [x10 per deg],
                  E' = (E G) >> 8 (the cave), I on E' (Ki), P = (E_P Kp) >> 8, + a D term:
      dsrc 'rate_held'  C1's E5: D = (-Kd x_h) >> 3, x_h = gp-0x6a56 (100 Hz hold of 8 x the motor-rate EMA)
      dsrc 'E'          STOCK D on the error (no E5): D = (Kd (E_P[n] - E_P[n-1])) >> 3          [D1a]
      dsrc 'op'         the cave hands Honda's D multiply an operand in r26 (0x29EE0 mov r26,r8 ; nop):
            dop 'fine'        Delta of the 1 kHz motor-position accumulator gp-0x6cc4 (fresh, 32x finer)   [D1b]
            dop 'held_lp'     the held-angle difference (s_new - s_old) through a 1st-order low-pass   [D1c]
            dop 'fresh_rate'  gp-0x6abe, the 1 kHz motor-rate EMA (no hold)                           [D2a]
      lead 'fwd' / 'fb' a first-order lead E_L = X + kh (X - w), w += beta (X - w), on E' (forward: P only, I on
                  E') or on r26 (feedback: the measurement only)                                       [D2b / D2c]
  kind 'cascade': the V282-style rate loop INSIDE (x = gp-0x6a56 held, or gp-0x6abe fresh; fb filter a/b sum form with
                  its 16.5 Hz pole), the angle error OUTSIDE forming its setpoint in the cave:
                  sp_r = ka (gp-0x69ae - 4 th_h), E = 4 sp_r - r26, P/I on E, optional stock D on E   [D3]
  kind 'rate'   : V282 / V294 / V295 references (rate operand, fb filter sum or diff, P (+ D on E)).

UNITS: theta deg (+ left, the sensed motor-side angle = gp-0x6a00 / 10); omega deg/s; u plant torque T counts (+ left,
u = +FWD y); S = the lane sum before the fade, S counts.  L = -K (C_th Pt + C_w Pw): 1 + L = 0 is the characteristic
equation, L > 0 at DC = negative feedback.  Re(T/omega) = Re(-K (C_th + j w C_w) / (j w)) T counts per deg/s, > 0 damps.
M20 = |C_th + j w C_w| / (8 w) at 20 Hz: lane S counts per count of x = 8 x the wheel rate (the record's |P/x| form with
this harness's hold and rate model).

SENSOR FACTS USED (EVIDENCE unless marked):
  gp-0x6abe = EMA(1024 gp-0x4f50) >> 10, alpha = 0xC643C/128 = 37/128 (54.3 Hz), FUN_00041464, called at 0x22200 in the
      1 kHz task BEFORE the PID call at 0x22522 (raw jarl scan; Ghidra decompile 2026-10-01) -> fresh at the lane.
  gp-0x6a56 = clamp(pol ((gp-0x6abe * 48 * cal(0xC613A = 1159)) >> 15), +-12000), pol = -1, in slot 4 (FUN_0003f776,
      decompile) -> x = -1.6978 gp-0x6abe; x = 8.00 counts per deg/s (record, redo audit) -> gp-0x6abe = -4.712 per deg/s.
  gp-0x6cc4 (fresh, 1 kHz, FUN_0003bd7c at 0x2224a): gp-0x6a00 = ... + pol*lin(d) + pol*C(d), lin = d / 32.17 per 0.1 deg,
      d(gp-0x6a00)/d(lin) = 1.155 near centre .. 0.962 outward (TRACE angle sec 2.1) -> -278.5 motor counts per deg near
      centre, -334 outward.  BELIEF: the plant's theta frame is gp-0x6a00's, so the fine D's gain varies x0.83..x1.0.
  RATE MODELS for the plant -> x path: 'ema' (the bytes above: EMA of the true motor-side rate; DEFAULT here), 'w3' (the
      record harness's 3-tick position difference, BELIEF), 'ideal' (stab_lin's held true rate).
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import scipy.linalg as sla

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                   # .../studies/angle_loop
for _p in (str(AL), str(AL / "c1"), str(AL / "refute_stability"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import lane_mirror_v295 as LM          # noqa: E402  (cals read LE from the V295 image, sha asserted)

CAL = LM.load_cal()
TS = 1e-3
OA, OB = CAL["oa"], CAL["ob"]                         # 992, 507 (0xC63EC / 0xC63EE)
FWD = CAL["fwd"] / 32768.0                            # 5346/32768
FADE = 254.0 / 256.0                                  # ((255*255) & 0xFFFF) >> 8, hands off
ALPHA = 37.0 / 128.0                                  # 0xC643C
X_PER = 8.0                                           # gp-0x6a56 counts per deg/s
ABE_PER = -8.0 / (48.0 * 1159.0 / 32768.0)            # gp-0x6abe counts per deg/s = -4.712
D_PER = -278.5                                        # gp-0x6cc4 counts per deg of gp-0x6a00 near centre (BELIEF frame)
HOLD_PHASE = 4
assert (OA, OB) == (992, 507) and abs(ABE_PER + 4.7118) < 1e-3


@dataclass
class Des:
    name: str = "C1r2"
    kind: str = "angle"            # 'angle' | 'cascade' | 'rate'
    kp: float = 112.0              # Kp record (angle: Kp_base; cascade: inner Kp; rate: Kp)
    ki: float = 56.0               # Ki cal 0xC63E6
    G: float = 256.0               # cave speed gain at this operating point (E' = E G / 256)
    dsrc: str = "rate_held"        # 'none' | 'rate_held' | 'E' | 'op'
    kd: float = 20.0               # Kd record (u16, zxh)
    dop: str = ""                  # 'fine' | 'held_lp' | 'fresh_rate'
    dop_k: float = 1.0             # cave multiplier on the D operand (applied before Honda's (Kd * op) >> 3)
    lp_beta: float = 0.0           # held_lp first-order coefficient
    lead: str = ""                 # '' | 'fwd' | 'fb'
    lead_beta: float = 1.0 / 16.0
    lead_kh: float = 1.0
    fa: float = 923.0              # cascade / rate: fb filter a (signed) and b
    fb: float = 1560.0
    fb_op: str = "sum"             # 'sum' | 'diff' (rate references)
    cop: str = "held"              # cascade operand 'held' (gp-0x6a56) | 'fresh' (gp-0x6abe, sign handled in the cave)
    ka: float = 1.0                # cascade: sp_r = ka * e4, e4 = gp-0x69ae - 4 th_h (counts)
    kd_on_E: bool = False          # rate / cascade: stock D on E with Kd
    rate_model: str = "ema"        # 'ema' | 'w3' | 'ideal'
    extra_age: int = 0             # slot 4 late by this many whole ticks (hold ages 1+e .. 10+e)
    d: int = 2                     # transport ticks
    gain: float = 1.0              # loop-gain multiplier (exact-GM bisection only)
    fade: float = FADE
    sp_hold: bool = True           # the 0xE4 setpoint is a 100 Hz hold: the RX task (slot 3) writes gp-0x69ae AFTER the
    #                                lane in the arrival tick (tracer: 0 ticks preemption window) -> ages 1..10


V295 = Des("V295", kind="rate", kp=960, ki=0, fa=1011, fb=1050, fb_op="diff", dsrc="none", kd=0)
V294 = Des("V294", kind="rate", kp=960, ki=0, fa=1011, fb=567, fb_op="diff", dsrc="none", kd=0)
V282 = Des("V282", kind="rate", kp=248, ki=0, fa=923, fb=1560, fb_op="sum", dsrc="none", kd=128, kd_on_E=True)


# ======================================================================================================================
# plants (continuous A, B, Ct, Cw; the sensed angle and rate are MOTOR side)
# ======================================================================================================================
def rigid(J, b, k):
    A = np.array([[0.0, 1.0], [-k / J, -b / J]])
    B = np.array([[0.0], [1.0 / J]])
    return A, B, np.array([[1.0, 0.0]]), np.array([[0.0, 1.0]])


def two_mass(J, b, k, r2, fz, zw, J_arm_ratio=0.0, zeta_arm=0.0):
    """stab_lin.two_mass, copied (motor side Jm = (1-r2) J carries u, b, k; torsion bar to the wheel side)."""
    Jm, Jw = (1 - r2) * J, r2 * J
    ktb = Jw * (2 * math.pi * fz) ** 2
    btb = 2 * zw * math.sqrt(ktb * Jw)
    Jw2 = Jw * (1 + J_arm_ratio)
    barm = 2 * zeta_arm * math.sqrt(ktb * Jw2)
    A = np.array([[0, 1, 0, 0],
                  [-(k + ktb) / Jm, -(b + btb) / Jm, ktb / Jm, btb / Jm],
                  [0, 0, 0, 1],
                  [ktb / Jw2, btb / Jw2, -ktb / Jw2, -(btb + barm) / Jw2]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    return A, B, np.array([[1.0, 0, 0, 0]]), np.array([[0, 1.0, 0, 0]])


def c2d(A, B):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A * TS
    M[:n, n:] = B * TS
    E = sla.expm(M)
    return E[:n, :n], E[:n, n:]


_PCACHE: dict = {}


def plant_frf(plant, f):
    key = (tuple(np.round(plant[0].ravel(), 12)), tuple(np.round(plant[1].ravel(), 12)), len(f), float(f[0]),
           float(f[-1]))
    if key in _PCACHE:
        return _PCACHE[key]
    A, B, Ct, Cw = plant
    Ad, Bd = c2d(A, B)
    z = np.exp(1j * 2 * np.pi * np.asarray(f) * TS)
    n = Ad.shape[0]
    M = z[:, None, None] * np.eye(n)[None] - Ad[None]
    X = np.linalg.solve(M, np.broadcast_to(Bd, (len(z), n, 1)))[..., 0]
    Pt = X @ Ct[0]
    Pw = X @ Cw[0]
    if len(_PCACHE) > 48:                       # bounded: 48 x 2 x 3200 complex = 5 MB per process
        _PCACHE.clear()
    _PCACHE[key] = (Pt, Pw)
    return Pt, Pw


# ======================================================================================================================
# (1) ANALYTIC controller responses: S = C_th theta + C_w omega + C_ref theta_sp
# ======================================================================================================================
def _blocks(f, des: Des):
    z1 = np.exp(-2j * np.pi * np.asarray(f, float) * TS)
    e = des.extra_age
    H = np.mean([z1 ** (a + e) for a in range(1, 11)], axis=0)
    ema = ALPHA / (1 - (1 - ALPHA) * z1)
    if des.rate_model == "ema":
        Rth, Rw = 0.0 * z1, ema                     # x_h / 8 = H * (Rth theta + Rw omega)
    elif des.rate_model == "w3":
        Rth, Rw = (1 - z1 ** 3) / (3 * TS), 0.0 * z1
    elif des.rate_model == "ideal":
        Rth, Rw = 0.0 * z1, 1.0 + 0.0 * z1
    else:
        raise ValueError(des.rate_model)
    return z1, H, ema, Rth, Rw


def ctl_frf(f, des: Des):
    """returns (C_th, C_w, C_ref) in lane S counts per (deg, deg/s, deg of setpoint)."""
    Cth, Cw, Cref = _ctl_frf(f, des)
    if des.sp_hold:
        z1 = np.exp(-2j * np.pi * np.asarray(f, float) * TS)
        Cref = Cref * np.mean([z1 ** a for a in range(1, 11)], axis=0)
    return Cth, Cw, Cref


def _ctl_frf(f, des: Des):
    z1, H, ema, Rth, Rw = _blocks(f, des)
    one = np.ones_like(z1)
    g = des.G / 256.0
    if des.kind == "rate":
        R = (des.fb / 1024.0) * (1 + (z1 if des.fb_op == "sum" else -z1)) / (1 - (des.fa / 1024.0) * z1)
        gk = des.kp / 256.0 + ((des.kd / 8.0) * (1 - z1) if des.kd_on_E else 0.0)
        # S = -gk R x_h, x_h = 8 H (Rth th + Rw w)
        Cth = -gk * R * 8 * H * Rth
        Cw = -gk * R * 8 * H * Rw
        return Cth, Cw, 0.0 * one
    if des.kind == "cascade":
        if des.cop == "held":
            xth, xw = 8 * H * Rth, 8 * H * Rw
        else:                                           # fresh gp-0x6abe, sign handled in the cave: x = +4.712 ema w
            xth, xw = 0.0 * z1, -ABE_PER * ema
        R = (des.fb / 1024.0) * (1 + z1) / (1 - (des.fa / 1024.0) * z1)
        # E = 4 sp_r - r26 ; sp_r = ka * 40 (th_sp - H th) ; r26 = R x
        E_th = -4 * g * des.ka * 40 * H - R * xth          # sp_r = (e4 G >> 8) * ka : the cave's speed gain on the
        E_w = -R * xw                                      # OUTER (angle) path only
        E_ref = 4 * g * des.ka * 40 * one
        gk = des.kp / 256.0 + (des.ki / 32768.0) / (1 - z1) + ((des.kd / 8.0) * (1 - z1) if des.kd_on_E else 0.0)
        return gk * E_th, gk * E_w, gk * E_ref
    # ---------------- kind 'angle' ----------------
    r26_th = 80 * (1 + z1) * H                           # 8 th_h[n] + 8 th_h[n-1], th_h = 10 H th
    Lf = 1 + des.lead_kh * (1 - des.lead_beta / (1 - (1 - des.lead_beta) * z1)) if des.lead else one
    if des.lead == "fb":
        r26_th = Lf * r26_th
    E_th, E_ref = -r26_th, 160.0 * one                   # E = 4 sp - r26 = 160 th_sp - r26
    Ep_th, Ep_ref = g * E_th, g * E_ref                  # E'
    LP = Lf if des.lead == "fwd" else one                # P operand = Lf E' (forward lead) else E'
    PI_th = (des.kp / 256.0) * LP * Ep_th + (des.ki / 32768.0) / (1 - z1) * Ep_th
    PI_ref = (des.kp / 256.0) * LP * Ep_ref + (des.ki / 32768.0) / (1 - z1) * Ep_ref
    Cth, Cw, Cref = PI_th, 0.0 * z1, PI_ref
    kd8 = des.kd / 8.0
    if des.dsrc == "rate_held":                          # D = -Kd x_h / 8 = -Kd H rate
        Cth = Cth - des.kd * H * Rth
        Cw = Cw - des.kd * H * Rw
    elif des.dsrc == "E":                                # D = Kd/8 (E_P[n] - E_P[n-1])
        Cth = Cth + kd8 * (1 - z1) * LP * Ep_th
        Cref = Cref + kd8 * (1 - z1) * LP * Ep_ref
    elif des.dsrc == "op":
        if des.dop == "fresh_rate":                      # op = gp-0x6abe = ABE_PER ema w
            Cw = Cw + kd8 * des.dop_k * ABE_PER * ema
        elif des.dop == "fine":                          # op = d[n] - d[n-1] = D_PER (1 - z1) th
            Cth = Cth + kd8 * des.dop_k * D_PER * (1 - z1)
        elif des.dop == "held_lp":                       # op = -LP(s_new - s_old), s = 80 th_h(deg) (8 per count)
            lp = des.lp_beta / (1 - (1 - des.lp_beta) * z1)
            Cth = Cth - kd8 * des.dop_k * lp * 80 * (1 - z1) * H
        else:
            raise ValueError(des.dop)
    elif des.dsrc != "none":
        raise ValueError(des.dsrc)
    return Cth, Cw, Cref


def K_out(f, des: Des):
    z1 = np.exp(-2j * np.pi * np.asarray(f, float) * TS)
    Hout = (OB / 1024.0) * (1 + z1) / (32.0 * (1 - (OA / 1024.0) * z1))
    return des.gain * des.fade * FWD * Hout * z1 ** des.d


FGRID = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 3200),
                                  [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 1.6, 2.0, 2.5, 3.0, 5, 7, 10, 13, 15, 17, 20,
                                   25, 30.0]]))


def loop_frf(des: Des, plant, f=FGRID):
    Cth, Cw, Cref = ctl_frf(f, des)
    K = K_out(f, des)
    Pt, Pw = plant_frf(plant, f)
    L = -K * (Cth * Pt + Cw * Pw)
    S = 1.0 / (1.0 + L)
    Tr = K * Cref * Pt * S
    return dict(f=f, L=L, S=S, Tc=L * S, Tr=Tr, Cth=Cth, Cw=Cw, K=K)


def pm_all(f, L):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    pms, fcs = [], []
    for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        pms.append(((p + 180) + 180) % 360 - 180)
        fcs.append(f[i] + t * (f[i + 1] - f[i]))
    return pms, fcs


def gm_lti(f, L):
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    mag = np.abs(L)
    gms = []
    for i in range(len(f) - 1):
        w0, w1 = (ph[i] + 180) / 360, (ph[i + 1] + 180) / 360
        if math.floor(w0) != math.floor(w1):
            gms.append(-20 * math.log10(max(mag[i], 1e-12)))
    pos = [g for g in gms if g > 0]
    return min(pos) if pos else float("inf")


def m20(des: Des, f=20.0):
    Cth, Cw, _ = ctl_frf(np.array([f]), des)
    w = 2 * np.pi * f
    return float(abs(Cth[0] + 1j * w * Cw[0]) / (8 * w))


def re_tw(des: Des, f):
    f = np.atleast_1d(np.asarray(f, float))
    Cth, Cw, _ = ctl_frf(f, des)
    K = K_out(f, des)
    w = 2 * np.pi * f
    return (-K * (Cth + 1j * w * Cw) / (1j * w)).real


def metrics(des: Des, plant, f=FGRID, ref_l20=None):
    r = loop_frf(des, plant, f)
    L, S, Tc, Tr = r["L"], r["S"], r["Tc"], r["Tr"]
    pms, fcs = pm_all(f, L)
    band = lambda lo, hi: (f >= lo) & (f <= hi)  # noqa: E731
    i20 = int(np.argmin(abs(f - 20.0)))
    out = dict(pm=min(pms) if pms else float("nan"), fc=fcs[int(np.argmin(pms))] if pms else float("nan"),
               n_cross=len(pms), gm_lti=gm_lti(f, L), Ms=float(np.abs(S).max()),
               S530=20 * math.log10(float(np.abs(S[band(5, 30)]).max())),
               Tc530=20 * math.log10(float(np.abs(Tc[band(5, 30)]).max())),
               L20=float(abs(L[i20])), M20=m20(des))
    if des.kind != "rate":
        out.update(Tr530=20 * math.log10(max(float(np.abs(Tr[band(5, 30)]).max()), 1e-12)),
                   Tr163=float(np.abs(Tr[band(1.6, 3.0)]).max()), hold=float(abs(Tr[int(np.argmin(abs(f - 0.02)))])),
                   Tr02=complex(Tr[int(np.argmin(abs(f - 0.2)))]), Tr05=complex(Tr[int(np.argmin(abs(f - 0.5)))]),
                   Trpk=float(np.abs(Tr).max()), fTrpk=float(f[int(np.argmax(np.abs(Tr)))]))
    return out


# ======================================================================================================================
# (2) EXACT PERIODIC 1 kHz model: affine rows over [state | th_sp | w]
# ======================================================================================================================
class Lifted:
    """state layout is built per structure.  Inputs: column N = th_sp (deg), column N+1 = w (plant-input torque)."""

    def __init__(self, des: Des, plant):
        self.des, self.plant = des, plant
        A, B, Ct, Cw = plant
        self.Ad, self.Bd = c2d(A, B)
        self.Ct, self.Cw = Ct[0], Cw[0]
        npl = self.Ad.shape[0]
        idx = {}
        n = 0

        def alloc(name, k=1):
            nonlocal n
            idx[name] = n
            n += k
        alloc("xp", npl)
        if des.d > 0:
            alloc("ub", des.d)
        alloc("o")
        alloc("thh")            # held angle (deg)
        alloc("xh")             # held rate (deg/s; x = 8 xh)
        alloc("thp")            # angle kind: th_h as read on the previous tick (s_old)
        alloc("r")              # gp-0x6abe EMA state (deg/s units)
        alloc("I")              # integrator, S units
        alloc("Ep")             # previous E (D on E)
        alloc("w")              # lead state
        alloc("lp")             # held_lp filter state
        alloc("thf")            # previous fresh theta (fine D)
        alloc("sfb")            # cascade / rate fb filter state
        alloc("sph")            # the 100 Hz setpoint hold (gp-0x69ae), refreshed after the lane on phase 0
        if des.rate_model == "w3":
            alloc("h", 3)       # theta[n-1], theta[n-2], theta[n-3]
        ea = des.extra_age
        if ea:
            alloc("eat", ea)    # delayed samples of theta
            alloc("eax", ea)    # delayed samples of the rate sample
        self.idx, self.N, self.npl = idx, n, npl

    def _e(self, name, k=0):
        v = np.zeros(self.N + 2)
        v[self.idx[name] + k] = 1.0
        return v

    def phase(self, p, gain=1.0, open_loop=False):
        """returns (M (N x N+2) new-state rows, u_out row (the plant input this tick, before w))."""
        des, N = self.des, self.N
        e = self._e
        M = np.zeros((N, N + 2))
        xp = np.zeros((self.npl, N + 2))
        for i in range(self.npl):
            xp[i] = e("xp", i)
        th = self.Ct @ xp
        om = self.Cw @ xp
        thsp_in = np.zeros(N + 2)
        thsp_in[N] = 1.0
        thsp = e("sph") if des.sp_hold else thsp_in
        winp = np.zeros(N + 2)
        winp[N + 1] = 1.0
        r_new = (1 - ALPHA) * e("r") + ALPHA * om                  # 0x22200 FUN_00041464, before the PID
        # the rate sample slot 4 would take this tick (deg/s)
        if des.rate_model == "ema":
            rs = r_new
        elif des.rate_model == "w3":
            rs = (th - e("h", 2)) / (3 * TS)
        else:
            rs = om
        thh, xh = e("thh"), e("xh")
        g = des.G / 256.0
        if des.kind == "angle":
            s_new, s_old = 80 * thh, 80 * e("thp")
            r26 = s_new + s_old
            if des.lead == "fb":
                wn = (1 - des.lead_beta) * e("w") + des.lead_beta * r26
                r26 = r26 + des.lead_kh * (r26 - wn)
            E = 160 * thsp - r26
            Ep = g * E
            if des.lead == "fwd":
                wn = (1 - des.lead_beta) * e("w") + des.lead_beta * Ep
                EP = Ep + des.lead_kh * (Ep - wn)
            else:
                EP = Ep
            I_new = e("I") + (des.ki / 32768.0) * Ep
            P = (des.kp / 256.0) * EP
            D = np.zeros(N + 2)
            kd8 = des.kd / 8.0
            lp_new = e("lp")
            if des.dsrc == "rate_held":
                D = -des.kd * xh
            elif des.dsrc == "E":
                D = kd8 * (EP - e("Ep"))
            elif des.dsrc == "op":
                if des.dop == "fresh_rate":
                    D = kd8 * des.dop_k * ABE_PER * r_new
                elif des.dop == "fine":
                    D = kd8 * des.dop_k * D_PER * (th - e("thf"))
                elif des.dop == "held_lp":
                    lp_new = (1 - des.lp_beta) * e("lp") + des.lp_beta * (s_new - s_old)
                    D = -kd8 * des.dop_k * lp_new
            S = I_new + P + D
            if des.ki:
                M[self.idx["I"]] = I_new          # (an unused accumulator is left 0, not a spurious unit eigenvalue)
            M[self.idx["Ep"]] = EP
            M[self.idx["thp"]] = thh
            if des.dsrc == "op" and des.dop == "held_lp":
                M[self.idx["lp"]] = lp_new
            if des.lead:
                M[self.idx["w"]] = wn
        elif des.kind in ("cascade", "rate"):
            if des.kind == "rate" or des.cop == "held":
                x = X_PER * xh
            else:
                x = -ABE_PER * r_new
            s_new = (des.fa / 1024.0) * e("sfb") + (des.fb / 1024.0) * x
            r26 = (s_new + e("sfb")) if des.fb_op == "sum" else (s_new - e("sfb"))
            if des.kind == "rate":
                E = -r26
            else:
                E = 4 * g * des.ka * 40 * (thsp - thh) - r26
            I_new = e("I") + (des.ki / 32768.0) * E
            P = (des.kp / 256.0) * E
            D = (des.kd / 8.0) * (E - e("Ep")) if des.kd_on_E else np.zeros(N + 2)
            S = I_new + P + D
            if des.ki:
                M[self.idx["I"]] = I_new
            M[self.idx["Ep"]] = E
            M[self.idx["sfb"]] = s_new
        else:
            raise ValueError(des.kind)
        Sf = des.fade * S
        o_new = (OA / 1024.0) * e("o") + (OB / 1024.0) * Sf
        y = (e("o") + o_new) / 32.0
        ucmd = gain * FWD * y
        M[self.idx["o"]] = o_new
        M[self.idx["r"]] = r_new
        if des.sp_hold:
            M[self.idx["sph"]] = thsp_in if p == 0 else e("sph")
        M[self.idx["thf"]] = th
        if des.rate_model == "w3":
            M[self.idx["h"]] = th
            M[self.idx["h"] + 1] = e("h", 0)
            M[self.idx["h"] + 2] = e("h", 1)
        # slot 4 (after the lane): refresh the held registers
        ea = des.extra_age
        if ea:
            M[self.idx["eat"]] = th
            M[self.idx["eax"]] = rs
            for i in range(1, ea):
                M[self.idx["eat"] + i] = e("eat", i - 1)
                M[self.idx["eax"] + i] = e("eax", i - 1)
            src_t, src_x = e("eat", ea - 1), e("eax", ea - 1)
        else:
            src_t, src_x = th, rs
        if p == HOLD_PHASE:
            M[self.idx["thh"]] = src_t
            M[self.idx["xh"]] = src_x
        else:
            M[self.idx["thh"]] = thh
            M[self.idx["xh"]] = xh
        # transport + plant
        d = des.d
        if d > 0:
            u_out = e("ub", d - 1)
            M[self.idx["ub"]] = ucmd
            for i in range(1, d):
                M[self.idx["ub"] + i] = e("ub", i - 1)
        else:
            u_out = ucmd
        uin = (winp if open_loop else u_out + winp)
        for i in range(self.npl):
            M[self.idx["xp"] + i] = self.Ad[i] @ xp + self.Bd[i, 0] * uin
        return M, u_out, th

    def mats(self, gain=1.0, open_loop=False):
        out = [self.phase(p, gain, open_loop) for p in range(10)]
        return out

    def monodromy(self, gain=1.0):
        Phi = np.eye(self.N)
        for M, _, _ in self.mats(gain):
            Phi = M[:, :self.N] @ Phi
        return Phi

    def exact(self, gain=1.0):
        lam = np.linalg.eigvals(self.monodromy(gain))
        rho = float(np.max(np.abs(lam)))
        poles = []
        for l in lam:
            if abs(l) < 1e-9:
                continue
            s = np.log(l.astype(complex)) / (10 * TS)
            fhz = abs(s.imag) / (2 * np.pi)
            poles.append((fhz, -s.real / abs(s) if abs(s) > 0 else 1.0))
        return rho, poles

    def exact_gm(self, hi_max=1e4):
        rho1 = self.exact(1.0)[0]
        if rho1 >= 1:
            lo, hi = 1e-4, 1.0
            for _ in range(50):
                m = math.sqrt(lo * hi)
                if self.exact(m)[0] >= 1:
                    hi = m
                else:
                    lo = m
            return 20 * math.log10(lo)
        lo, hi = 1.0, 2.0
        while self.exact(hi)[0] < 1 and hi < hi_max:
            lo, hi = hi, hi * 2
        if hi >= hi_max:
            return float("inf")
        for _ in range(40):
            m = math.sqrt(lo * hi)
            if self.exact(m)[0] < 1:
                lo = m
            else:
                hi = m
        return 20 * math.log10(lo)

    def harmonic(self, f, inp="w", out="u", open_loop=True):
        """EXACT same-frequency harmonic of the periodic system: input column (th_sp or w) = e^{j w n}, output = the plant
        input u_out (out='u') or the sensed angle (out='th').  open_loop=True cuts u_out -> plant (the L computation)."""
        N = self.N
        mats = self.mats(1.0, open_loop)
        A = [m[0][:, :N] for m in mats]
        col = N if inp == "th_sp" else N + 1
        Bv = [m[0][:, col] for m in mats]
        Cr = [(m[1] if out == "u" else m[2]) for m in mats]
        C = [c[:N] for c in Cr]
        Dv = [c[col] for c in Cr]
        f = np.atleast_1d(np.asarray(f, float))
        wv = 2 * np.pi * f * TS
        Q = [np.eye(N)]
        for p in range(9, 0, -1):
            Q.insert(0, Q[0] @ A[p])            # Q[p] = A9 ... A(p+1)
        Phi = Q[0] @ A[0]
        Gam = sum(np.outer(Q[p] @ Bv[p], np.exp(1j * wv * p)) for p in range(10))   # N x F
        zz = np.exp(1j * wv * 10)
        Mx = zz[:, None, None] * np.eye(N)[None] - Phi[None]
        X = np.linalg.solve(Mx, Gam.T[..., None])[..., 0]                        # F x N   (x at phase 0)
        Y = np.zeros(len(f), complex)
        x = X
        for p in range(10):
            ep = np.exp(1j * wv * p)
            y = x @ C[p] + Dv[p] * ep
            Y += y * np.exp(-1j * wv * p)
            x = x @ A[p].T + np.outer(ep, Bv[p])
        return Y / 10.0


def lifted_L(des: Des, plant, f):
    """L from the exact harmonic: input w at the plant input, output the plant input the controller would apply."""
    lp = Lifted(des, plant)
    return -lp.harmonic(f, inp="w", out="u", open_loop=True)


def lifted_Tref(des: Des, plant, f):
    lp = Lifted(des, plant)
    return lp.harmonic(f, inp="th_sp", out="th", open_loop=False)


# ======================================================================================================================
# members (c1r2_members: the full factorial damping x inertia x delay x age, + report members), and two-mass rows
# ======================================================================================================================
def member(name, v):
    import c1r2_members as M2
    J, b, k, d, ea = M2.params(name, v)
    return rigid(J, b, k), int(d), int(ea), (J, b, k)


def at(des: Des, name, v, G=None):
    """the design at a member operating point: (des with d / extra_age / G set, plant)."""
    pl, d, ea, _ = member(name, v)
    return replace(des, d=d, extra_age=ea, G=des.G if G is None else G), pl


if __name__ == "__main__":
    # quick self-consistency: analytic L == exact harmonic L for every structure on one member
    pl = rigid(0.2, 9.76, 24.265)
    f = np.array([0.1, 0.5, 1.0, 2.0, 5.0, 13.0, 20.0, 40.0])
    for des in (Des("C1r2", G=1083), Des("D1a", dsrc="E", kd=1000, G=1083),
                Des("D1b", dsrc="op", dop="fine", kd=20, dop_k=-0.25, G=1083),
                Des("D1c", dsrc="op", dop="held_lp", kd=20, dop_k=1 / 4, lp_beta=0.1, G=1083),
                Des("D2a", dsrc="op", dop="fresh_rate", kd=34, G=1083),
                Des("D2b", lead="fwd", G=1083), Des("D2c", lead="fb", G=1083),
                Des("D3", kind="cascade", kp=40, ki=20, ka=0.5, dsrc="none"),
                Des("D3f", kind="cascade", kp=40, ki=20, ka=0.5, dsrc="none", cop="fresh"),
                V295, V282, Des("C1w3", G=1083, rate_model="w3"), Des("C1h", G=1083, extra_age=10)):
        La = loop_frf(des, pl, f)["L"]
        Lx = lifted_L(des, pl, f)
        print(f"{des.name:6s} max |La - Lx| / |La| = {np.max(np.abs(La - Lx) / np.abs(La)):.2e}   rho "
              f"{Lifted(des, pl).exact()[0]:.5f}")
