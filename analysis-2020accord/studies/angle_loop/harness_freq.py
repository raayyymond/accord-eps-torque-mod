# -*- coding: utf-8 -*-
r"""harness_freq.py -- EXACT DISCRETE FREQUENCY-DOMAIN HARNESS FOR THE ANGLE LOOP in the LKAS lane FUN_00028ea6
(the zero-cave in-place edit set of TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md section 3), on the identified
plant family.  2026-09-30, subagent "harness-freq".  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

WHAT IS MODELLED (every block is a line of the decompiled arithmetic, linearised: integer floors and clamps off)
------------------------------------------------------------------------------------------------------------------
  theta  = plant angle, deg, + LEFT  (= openpilot steeringAngleDeg = gp-0x6a00 / 10; tracer-angle EVIDENCE)
  u      = plant input torque, T counts, + LEFT  (u = -T, T = gp-0x6b38 in the 427 tap's sign; v294_plant convention)

  operand  op[n]   angle edit (0x28F4C ld.h -0x6a00): op = 10*theta (0.1 deg counts)       [hold modes below]
                   rate (V295/V282, ld.h -0x6a56):    op = x = 8 * RF(theta)  (8.00 counts per deg/s; RF = w-tick
                                                       position difference, w = 3 ms -- BELIEF, the record's former)
  hold     HOLD    the lane (slot 0, every tick) reads a cell written by slot 4 on one tick in ten, AFTER slot 0 in
                   the activation tick  =>  op_lane[n] = op[k(n)], age n-k(n) = 1..10 ticks (tracer EVIDENCE).
                   'hold'   : EXACT periodic sample-and-hold (lifted 10-tick monodromy for poles, gain margin, delay
                              margin; time-domain simulation for the closed-loop fundamentals)
                   'avg'    : its LTI fundamental, (1/10) sum_{a=1..10} z^-a  (exact for the same-frequency component;
                              aliases at 100k +- f are dropped -- quantified in the self-test)
                   'cont'   : the continuous approximation e^{-s 5.5 ms} sinc(f * 10 ms)  (pure ZOH e^{-s 5 ms} sinc +
                              the 1-tick age offset)
                   'fresh'  : age 0 (a cave reading the 1 kHz gp-0x69ca / gp-0x6abe, written before the PID in slot 0)
  fb filter        s_new = (a*s_old + b*op)/1024 ; r26 = s_new +- s_old   (0x28F86..0x28FA4; 'sum' = add, 'diff' = subr)
                   angle edit: a = 0, b = 8192, sum  =>  r26 = 8*op[n] + 8*op[n-1]  (2-tap FIR, DC 16)
  error            E = (sp << 2) - r26 ; angle edit sp = gp-0x69ae = -4*raw  =>  E = 16*(theta_sp - theta) in counts
  P                (E*Kp) >> 8                                         (0x29E36..0x29E3E)
  I                I += ((E>>5 - DB) * Ki) >> 3 ; contributes I >> 7  =>  Ki/32768 * E/(1 - z^-1)   (DB = 0 linear)
  D                'rate' (edit 5): (-Kd * x_held) >> 3 = -Kd * H * RF(theta)  [x = gp-0x6a56, held]
                   'E'    (stock):  (Kd * (E - E_prev)) >> 3
  fade             S = (f*(I>>7 + P + D)) >> 8, f = ((255*255)&0xFFFF)>>8 = 254 hands-off, ramp = 0x8000
  output lag       o' = (oa*o + ob*S)/1024 ; y = (o + o')/32  (oa 992, ob 507 read from the image: 5.05 Hz, DC 0.990)
  forward gain     T = pol * 5346 * y / 32768, pol = -1  =>  u = -T = +FWD*y
  transport        u applied d ticks later (d = 2 ms nominal = the record's T -> wheel-acceleration delay; 3 alt)
  plant            u -> theta : 1/(J s^2 + b s + k)  ZOH-discretised at 1 kHz, (J, b, k) from v294_plant.family()
                   + the record's 20 Hz representations:
                     'two-mass' (rp4 / v294_plant.with_mode20): collocated, motor angle sensed, f2 12-40, r2 0.2-0.8,
                                 zeta2 0.02-0.05
                     'mult'     (V289/V290 loopshape20 fits): theta * wp^2/(s^2 + 2 zp wp s + wp^2), optionally
                                 kappa-blended 1 + kappa (M - 1): 'resonant' 21.0 Hz/0.010, 'smooth+mode' 22.5/0.05,
                                 'weak-mode' 22.25/0.04 kappa 0.3

  C_fb  (theta deg -> u T counts) = FADE*Hout*FWD*z^-d * [ (Kp/256 + Ki/32768/(1-z^-1) [+ Kd/8 (1-z^-1) if D on E])
                                                           * R(z) * OP(z)  +  Kd*H*RF  (if D on rate) ]
  C_ref (theta_sp deg -> u)       = FADE*Hout*FWD*z^-d * (Kp/256 + Ki/32768/(1-z^-1)) * 16 * 10      (angle edit)
  L = C_fb * P ;  T_ref = C_ref*P/(1+L) ;  S = 1/(1+L) ;  T_comp = L/(1+L)

Run:  python harness_freq.py --selftest     (cross-checks; ~1 min)
      python harness_freq.py                (the full study; writes _scratch/angle_loop/harness_freq/out.txt + .json)
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from scipy import signal

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent / "v295" / "plant", HERE.parent / "v295" / "lib"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import lane_mirror_v295 as LM          # noqa: E402  byte-exact V295 lane mirror (cals read LE from the image, sha asserted)
import v294_plant as VP                 # noqa: E402  the identified plant family

KIT = _d
OUTDIR = KIT.parent / "_scratch" / "angle_loop" / "harness_freq"   # repo-root scratch (KIT = analysis-2020accord)
TS = 1e-3
SPEEDS = (3.0, 5.0, 8.0, 12.5, 19.0, 26.0, 30.0)
_OUT: list[str] = []


def pr(s=""):
    print(s, flush=True)
    _OUT.append(str(s))


# ======================================================================================================================
# CALIBRATION READ FROM THE V295 IMAGE (the base the edits are applied to)
# ======================================================================================================================
CAL = LM.load_cal()                      # asserts sha 5c044d65...
FADE = (((255 * 255) & 0xFFFF) >> 8) / 256.0           # 254/256, hands-off, both fade LERPs at 255 (0x2A0B4..0x2A0C2)
assert CAL["fadeA"][1][0] == 255 and CAL["fadeB"][1][0] == 255
OA, OB = CAL["oa"], CAL["ob"]                           # 992, 507
FWD = CAL["fwd"] / 32768.0                              # 5346/32768
KP_X = CAL["kp"][0]                                     # idx knots of the Kp record (0xCB994[7])
KD_X = CAL["kd"][0]
IDX_PER_DEG = 4 * 65025 / 65536 / 64 * 10               # idx per deg of |theta_sp| (0x29CBC..0x29CD6, hands-off)
L_WB, SR = 2.83, 16.0                                   # road geometry for the angle-indexed schedule (BELIEF: Accord
#                                                         wheelbase 2.83 m; SR ~16, measured 14.6-17.6 on the fork map)


def theta_max_deg(v, alat=3.0):
    """largest steering-wheel angle reachable at speed v with lateral accel <= alat: theta = L*kappa*SR, kappa = a/v^2."""
    return math.degrees(L_WB * alat / v ** 2 * SR)


# ======================================================================================================================
# CONTROLLER DESCRIPTION
# ======================================================================================================================
@dataclass
class Ctl:
    name: str = "angle"
    op: str = "angle"          # 'angle' (gp-0x6a00 / gp-0x69ca) | 'rate' (gp-0x6a56)
    hold: str = "hold"         # 'hold' | 'avg' | 'cont' | 'fresh' | 'hold09' (ages 0..9)
    a: int = 0                 # fb pole cell 0xC63E8 (signed)
    b: int = 8192              # fb gain cell 0xC63EA
    fb_op: str = "sum"         # 'sum' | 'diff'
    kp: float = 1000.0
    ki: float = 0.0
    kd: float = 0.0
    d_src: str = "rate"        # 'rate' | 'E' | 'none'
    oa: int = OA
    ob: int = OB
    d: int = 2                 # transport delay, ticks
    w: int = 3                 # rate-former window, ticks (BELIEF)
    gain: float = 1.0          # loop-gain multiplier (gain-margin bisection only)

    @property
    def ages(self):
        return range(0, 10) if self.hold == "hold09" else range(1, 11)


V295 = Ctl("V295", op="rate", a=1011, b=1050, fb_op="diff", kp=960, d_src="none")
V294 = Ctl("V294", op="rate", a=1011, b=567, fb_op="diff", kp=960, d_src="none")
V282 = Ctl("V282", op="rate", a=923, b=1560, fb_op="sum", kp=248, kd=128, d_src="E")


def ki_for(kp, f_i):
    """Ki giving the PI corner at f_i Hz: omega_I = 7.8125 Ki/Kp  (Ki/32768*1000 per s over Kp/256)."""
    return 2 * math.pi * f_i * kp / 7.8125


# ======================================================================================================================
# ANALYTIC FREQUENCY RESPONSES (exact at 1 kHz for every LTI block)
# ======================================================================================================================
def zi(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)


def H_hold(f, mode="hold", ages=range(1, 11)):
    f = np.asarray(f, float)
    if mode in ("hold", "avg", "hold09"):
        return np.mean([zi(f) ** a for a in ages], axis=0)
    if mode == "cont":
        return np.exp(-2j * np.pi * f * 5.5e-3) * np.sinc(f * 10e-3)
    if mode == "cont5":
        return np.exp(-2j * np.pi * f * 5.0e-3) * np.sinc(f * 10e-3)
    if mode == "fresh":
        return np.ones_like(f, complex)
    raise ValueError(mode)


def H_out(f, oa=OA, ob=OB):
    z = zi(f)
    return (ob / 1024.0) * (1 + z) / (32.0 * (1 - (oa / 1024.0) * z))


def RF(f, w=3):
    """deg/s per deg: x/8 = (theta[n] - theta[n-w])/(w Ts)."""
    return (1 - zi(f) ** w) / (w * TS)


def R_fb(f, c: Ctl):
    z = zi(f)
    return (c.b / 1024.0) * (1 + (z if c.fb_op == "sum" else -z)) / (1 - (c.a / 1024.0) * z)


def OP(f, c: Ctl):
    """operand counts per deg of theta, INCLUDING the hold."""
    h = H_hold(f, c.hold, c.ages)
    return h * (10.0 if c.op == "angle" else 8.0 * RF(f, c.w))


def PI_(f, c: Ctl):
    z = zi(f)
    g = c.kp / 256.0 + (c.ki / 32768.0) / (1 - z)
    if c.d_src == "E":
        g = g + (c.kd / 8.0) * (1 - z)
    return g


def C_S(f, c: Ctl):
    """S (before the fade) per deg of theta on the FEEDBACK path, sign flipped so negative feedback is positive."""
    s = PI_(f, c) * R_fb(f, c) * OP(f, c)
    if c.d_src == "rate" and c.kd:
        s = s + c.kd * H_hold(f, c.hold, c.ages) * RF(f, c.w)
    return s


def C_fb(f, c: Ctl):
    return c.gain * FADE * H_out(f, c.oa, c.ob) * FWD * zi(f) ** c.d * C_S(f, c)


def C_ref(f, c: Ctl):
    """theta_sp (deg) -> u for the angle edit: sp<<2 = 16*theta_sp_counts... E = 16*10*theta_sp_deg."""
    return c.gain * FADE * H_out(f, c.oa, c.ob) * FWD * zi(f) ** c.d * PI_(f, c) * 160.0


def M20(c: Ctl, f=20.0):
    """THE RECORD'S 20 Hz MEASURE: controller P-counts (S before the fade) per count of the true wheel-rate x = 8*dtheta/dt
    (8 per deg/s), normalised to V295's downstream chain (fade*Hout*FWD) if the output lag differs.  For V295 with
    hold='fresh' and an ideal differentiator this is the record's 3.85; V282's is 44.90."""
    w = 2 * np.pi * f
    cs = C_S(np.array([f]), c)[0]
    norm = abs(H_out(np.array([f]), c.oa, c.ob)[0]) / abs(H_out(np.array([f]))[0])
    return abs(cs) / (8.0 * w) * norm


def Re_Cr(c: Ctl, f=20.0):
    """the torque per unit wheel RATE at the motor (T counts per deg/s), real part: > 0 adds damping to a COLLOCATED mode at
    f, < 0 removes it (rp4's measure, with this harness's hold and delay)."""
    w = 2 * np.pi * f
    return (C_fb(np.array([f]), c)[0] / (1j * w)).real


# ======================================================================================================================
# PLANTS
# ======================================================================================================================
@dataclass
class Plant:
    J: float
    b: float
    k: float
    tau: int = 2               # transport delay ticks (overrides Ctl.d when use_tau)
    f2: float = 0.0            # collocated two-mass mode (rp4 / v294_plant.with_mode20)
    zeta2: float = 0.05
    r2: float = 0.2
    fp: float = 0.0            # multiplicative V289-style mode
    zp: float = 0.05
    kappa: float | None = None
    name: str = ""

    def ss(self):
        """continuous state space, u (T counts, + left) -> theta (deg, the SENSED motor-side angle)."""
        J, b, k = self.J, self.b, self.k
        if self.f2 > 0:
            Jw = J * self.r2
            Jm = J - Jw
            mu = Jm * Jw / J
            K = (2 * np.pi * self.f2) ** 2 * mu
            c = 2 * self.zeta2 * np.sqrt(K * mu)
            A = np.array([[0, 1, 0, 0],
                          [-(k + K) / Jm, -(b + c) / Jm, K / Jm, c / Jm],
                          [0, 0, 0, 1],
                          [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
            B = np.array([[0], [1 / Jm], [0], [0]], float)
            C = np.array([[1, 0, 0, 0]], float)
            return A, B, C, np.zeros((1, 1))
        num, den = np.array([1.0]), np.array([J, b, k], float)
        if self.fp > 0:
            wp = 2 * np.pi * self.fp
            mden = np.array([1.0, 2 * self.zp * wp, wp ** 2])
            mnum = np.array([wp ** 2])
            if self.kappa is not None:
                mnum = np.polyadd((1 - self.kappa) * mden, self.kappa * mnum)
            num, den = np.polymul(num, mnum), np.polymul(den, mden)
        A, B, C, D = signal.tf2ss(num, den)
        return A, B, C, D

    def zoh(self):
        A, B, C, D = self.ss()
        Ad, Bd, Cd, Dd, _ = signal.cont2discrete((A, B, C, D), TS, method="zoh")
        return Ad, Bd, Cd, Dd

    def frf(self, f):
        """ZOH-discretised theta/u at 1 kHz (deg per T count)."""
        Ad, Bd, Cd, Dd = self.zoh()
        z = 1.0 / zi(f)                       # e^{+j w T}
        n = Ad.shape[0]
        out = np.empty(len(np.atleast_1d(f)), complex)
        I = np.eye(n)
        for i, zz in enumerate(np.atleast_1d(z)):
            out[i] = (Cd @ np.linalg.solve(zz * I - Ad, Bd))[0, 0] + Dd[0, 0]
        return out


def plant_at(member: str, v: float, fam=None, **mode) -> Plant:
    fam = fam or FAM
    p = fam[member].at(v)
    return Plant(J=p.J, b=p.b, k=p.k, tau=p.tau_ms, name=f"{member}@{v:g}", **mode)


FAM = VP.family()


# ======================================================================================================================
# THE EXACT 1 kHz STATE-SPACE (with the 100 Hz sample-and-hold as a real register), built tick by tick
# ======================================================================================================================
class Loop:
    """closed loop at 1 kHz.  State = [plant | theta history | held op | held x | fb state s | I | E_prev | out-lag o |
    torque delay line].  step(z, theta_sp, act) is linear in (z, theta_sp); matrices are built from unit vectors."""

    def __init__(self, c: Ctl, p: Plant, use_plant_tau=True):
        self.c, self.p = c, p
        self.d = p.tau if use_plant_tau else c.d
        self.Ad, self.Bd, self.Cd, _ = p.zoh()
        self.np_ = self.Ad.shape[0]
        self.nh = 10 + c.w + 1                 # theta history depth (avg-mode needs op[n-10] which needs theta[n-10-w])
        i = self.np_
        self.ih = i; i += self.nh
        self.iho = i; i += 1                   # held operand register
        self.ihx = i; i += 1                   # held rate register (D on rate)
        self.i_s = i; i += 1
        self.iI = i; i += 1
        self.iE = i; i += 1
        self.io = i; i += 1
        self.iT = i; i += max(self.d, 0)
        self.N = i

    def _op_fresh(self, th_now, hist, lag):
        """fresh operand and fresh x at tick n-lag (lag 0 = now), from the theta history (hist[0] = theta[n-1])."""
        c = self.c
        thv = lambda m: th_now if m == 0 else hist[m - 1]  # noqa: E731
        th = thv(lag)
        x = 8.0 * (th - thv(lag + c.w)) / (c.w * TS)
        op = 10.0 * th if c.op == "angle" else x
        return op, x

    def step(self, z, th_sp, act):
        c = self.c
        xp = z[:self.np_]
        hist = z[self.ih:self.ih + self.nh]
        th = (self.Cd @ xp)[0]
        op_now, x_now = self._op_fresh(th, hist, 0)
        if c.hold in ("hold", "hold09"):
            op, xh = z[self.iho], z[self.ihx]
            if c.hold == "hold09" and act:      # slot 4 lands BEFORE slot 0 in the activation tick (age 0..9 case)
                op, xh = op_now, x_now
        elif c.hold == "avg":
            ps = [self._op_fresh(th, hist, a) for a in c.ages]
            op = sum(q[0] for q in ps) / len(ps)
            xh = sum(q[1] for q in ps) / len(ps)
        elif c.hold == "fresh":
            op, xh = op_now, x_now
        else:
            raise ValueError("state space supports hold/hold09/avg/fresh only")
        s_old = z[self.i_s]
        s_new = (c.a / 1024.0) * s_old + (c.b / 1024.0) * op
        r26 = s_new + s_old if c.fb_op == "sum" else s_new - s_old
        if c.op == "angle":
            E = 160.0 * th_sp - r26            # sp<<2 = 16 * (10 theta_sp)
        else:
            E = -r26                           # rate builds: loop analysis only (sp = 0)
        I = (z[self.iI] + (c.ki / 32768.0) * E) if c.ki else 0.0   # Ki = 0: no accumulator state (it is 0)
        P = (c.kp / 256.0) * E
        if c.d_src == "rate":
            D = -c.kd * xh / 8.0
        elif c.d_src == "E":
            D = (c.kd / 8.0) * (E - z[self.iE])
        else:
            D = 0.0
        S = c.gain * FADE * (I + P + D)
        o = z[self.io]
        o_new = (c.oa / 1024.0) * o + (c.ob / 1024.0) * S
        y = (o + o_new) / 32.0
        T = FWD * y                            # u = -T_tap = +FWD*y (pol = -1)
        if self.d > 0:
            u = z[self.iT + self.d - 1]
        else:
            u = T
        zn = np.zeros(self.N)
        zn[:self.np_] = self.Ad @ xp + self.Bd[:, 0] * u
        zn[self.ih] = th
        zn[self.ih + 1:self.ih + self.nh] = hist[:self.nh - 1]
        if c.hold in ("hold", "hold09"):
            if act:
                zn[self.iho], zn[self.ihx] = op_now, x_now
            else:
                zn[self.iho], zn[self.ihx] = z[self.iho], z[self.ihx]
        # (avg / fresh: the registers are unused and must not carry a spurious z = 1 eigenvalue; they stay 0)
        zn[self.i_s] = s_new
        zn[self.iI] = I
        zn[self.iE] = E
        zn[self.io] = o_new
        if self.d > 0:
            zn[self.iT] = T
            zn[self.iT + 1:self.iT + self.d] = z[self.iT:self.iT + self.d - 1]
        return zn, th

    def mats(self, act):
        A = np.column_stack([self.step(e, 0.0, act)[0] for e in np.eye(self.N)])
        B = self.step(np.zeros(self.N), 1.0, act)[0]
        return A, B

    def poles(self):
        """exact closed-loop poles: lifted 10-tick monodromy for 'hold', 1-tick map otherwise.  Returns s-plane poles
        (frequencies folded into 0..50 Hz for 'hold', 0..500 Hz otherwise) and the spectral radius per second."""
        if self.c.hold in ("hold", "hold09"):
            Aa, _ = self.mats(True)
            An, _ = self.mats(False)
            Phi = np.linalg.matrix_power(An, 9) @ Aa
            lam = np.linalg.eigvals(Phi)
            dt = 10 * TS
        else:
            A, _ = self.mats(False)
            lam = np.linalg.eigvals(A)
            dt = TS
        lam = lam[np.abs(lam) > 1e-12]
        s = np.log(lam.astype(complex)) / dt
        return s, float(np.max(np.abs(lam))), dt

    def simulate(self, th_sp, z0=None):
        """time-domain march of the exact linear loop (activation tick every 10th tick, phase 0)."""
        Aa, Ba = self.mats(True)
        An, Bn = self.mats(False)
        z = np.zeros(self.N) if z0 is None else z0
        out = np.empty(len(th_sp))
        Cth = np.zeros(self.N)
        Cth[:self.np_] = self.Cd[0]
        for n, r in enumerate(th_sp):
            out[n] = Cth @ z
            if n % 10 == 0:
                z = Aa @ z + Ba * r
            else:
                z = An @ z + Bn * r
        return out


def modes(s, fmin=0.05, fmax=50.0):
    out = []
    for q in s:
        f = abs(q.imag) / (2 * np.pi)
        if q.imag > 1e-9 and fmin <= f <= fmax:
            out.append((f, -q.real / abs(q)))
    return sorted(out)


def exact_gm(c: Ctl, p: Plant, lo=1e-3, hi=1e3):
    """exact gain margin of the periodic loop: the scalar multiplier on the controller output at which the lifted
    spectral radius reaches 1 (bisection in log)."""
    def rho(g):
        return Loop(replace(c, gain=g), p).poles()[1]
    if rho(1.0) >= 1.0:
        # unstable at nominal: find the largest gain-reduction that stabilises (GM < 1)
        if rho(lo) >= 1.0:
            return float("nan")
        a, b_ = lo, 1.0
    else:
        if rho(hi) < 1.0:
            return float("inf")
        a, b_ = 1.0, hi
    for _ in range(26):
        m = math.sqrt(a * b_)
        if rho(m) < 1.0:
            a = m
        else:
            b_ = m
    return math.sqrt(a * b_)


def delay_margin(c: Ctl, p: Plant, dmax=40):
    """extra transport-delay ticks before the exact periodic loop goes unstable."""
    for extra in range(0, dmax + 1):
        pp = replace(p, tau=p.tau + extra)
        if Loop(c, pp).poles()[1] >= 1.0:
            return extra - 1
    return dmax


# ======================================================================================================================
# FREQUENCY-DOMAIN METRICS (LTI fundamental: hold -> its averaging filter)
# ======================================================================================================================
FGRID = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 2500),
                                  [0.05, 0.1, 0.3, 0.5, 1.0, 1.6, 2.0, 2.5, 3.0, 13.0, 15.0, 17.0, 20.0, 30.0]]))
_PFRF_CACHE: dict = {}


def plant_frf(p: Plant, f=FGRID):
    key = (p.J, p.b, p.k, p.f2, p.zeta2, p.r2, p.fp, p.zp, p.kappa, id(f) if f is not FGRID else "G")
    if key not in _PFRF_CACHE:
        _PFRF_CACHE[key] = p.frf(f)
    return _PFRF_CACHE[key]


def metrics(c: Ctl, p: Plant, exact=True, f=FGRID):
    cc = replace(c, d=p.tau)
    P = plant_frf(p, f)
    Cf = C_fb(f, cc)
    L = Cf * P
    S = 1.0 / (1.0 + L)
    Tc = L * S
    Tr = C_ref(f, cc) * P * S if c.op == "angle" else None
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    # crossovers of |L| = 1 (from above)
    idx = np.where((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    fc = pm = float("nan")
    if len(idx):
        i = idx[0]
        t = (0.0 - math.log(mag[i])) / (math.log(mag[i + 1]) - math.log(mag[i]))
        fc = math.exp(math.log(f[i]) + t * (math.log(f[i + 1]) - math.log(f[i])))
        phc = ph[i] + t * (ph[i + 1] - ph[i])
        pm = (math.degrees(phc) + 180.0 + 180.0) % 360.0 - 180.0
    # phase crossovers: L real and negative
    im = L.imag
    jx = np.where((np.sign(im[:-1]) != np.sign(im[1:])) & (L.real[:-1] < 0))[0]
    Lneg = [abs(L[j]) for j in jx]
    gm_lti = (1.0 / max(Lneg)) if Lneg else float("inf")
    f180 = f[jx[int(np.argmax(Lneg))]] if Lneg else float("nan")
    band = lambda lo, hi: (f >= lo) & (f <= hi)  # noqa: E731
    r = dict(fc=fc, pm=pm, gm_lti_db=20 * math.log10(gm_lti) if np.isfinite(gm_lti) else float("inf"), f180=f180,
             L20=float(np.abs(L[np.argmin(abs(f - 20))])), L1317=float(mag[band(13, 17)].max()),
             T20=float(np.abs(Tc[np.argmin(abs(f - 20))])), T1317=float(np.abs(Tc[band(13, 17)]).max()),
             Ms=float(np.abs(S).max()), S530_db=20 * math.log10(float(np.abs(S[band(5, 30)]).max())),
             Tc530_db=20 * math.log10(float(np.abs(Tc[band(5, 30)]).max())),
             M20=M20(cc), ReCr20=Re_Cr(cc), S163=float(np.abs(S[band(1.6, 3)]).max()))
    if Tr is not None:
        T0 = abs(Tr[0])
        trk = np.abs(Tr[band(0.1, 1.0)])
        # tracking over 0.1-1 Hz, ABSOLUTE (the inner loop on its own above 0.1 Hz) and NORMALISED by the DC value (the
        # fork's slow correction assumed to supply the DC as a static gain); turn-hold = |T_ref| at 0.05 Hz (a 20 s turn)
        r.update(Tr0=float(T0), trk_min=float(trk.min()), trk_max=float(trk.max()),
                 trkn_min=float(trk.min() / T0), trkn_max=float(trk.max() / T0),
                 hold=float(np.abs(Tr[np.argmin(abs(f - 0.05))])),
                 Tr530_db=20 * math.log10(float(np.abs(Tr[band(5, 30)]).max())),
                 Tr163=float(np.abs(Tr[band(1.6, 3)]).max()), Trpk=float(np.abs(Tr).max()),
                 fTrpk=float(f[int(np.argmax(np.abs(Tr)))]))
        # DC stiffness against a torque disturbance, T counts per deg (P only; I -> infinite)
        r["stiff_dc"] = p.k + (FADE * FWD * (OB / 1024 * 2 / 32 / (1 - OA / 1024)) * c.kp / 256 * 160) if c.ki == 0 \
            else float("inf")
    if exact:
        lp = Loop(cc, p)
        s, rho, dt = lp.poles()
        r["rho"] = rho
        r["stable"] = rho < 1.0
        md = modes(s, 0.05, 50.0 if c.hold in ("hold", "hold09") else 499.0)
        low = [m for m in md if m[0] < 8.0]
        hf = [m for m in md if 5.0 <= m[0] <= 50.0]
        r["wheel"] = min(low, key=lambda t: t[1]) if low else (float("nan"), float("nan"))
        r["hfmode"] = min(hf, key=lambda t: t[1]) if hf else (float("nan"), float("nan"))
    return r


# ======================================================================================================================
# SELF-TESTS (the cross-checks the report quotes)
# ======================================================================================================================
def selftest():
    ok = True
    pr("=== SELF-TEST 1: the record's 20 Hz numbers reproduced (fresh x, ideal differentiator, no fade/lag) ===")
    for c, want in ((V295, 3.85), (V294, 2.079), (V282, 44.90)):
        z = zi(np.array([20.0]))[0]
        r = (c.b / 1024) * (1 + (z if c.fb_op == "sum" else -z)) / (1 - c.a / 1024 * z)
        g = c.kp / 256 + ((c.kd / 8) * (1 - z) if c.d_src == "E" else 0)
        v = abs(g * r)
        pr(f"  {c.name}: |P/x| at 20 Hz = {v:.3f}   (record {want})   "
           f"with the 100 Hz hold and the 3 ms former: {M20(c):.3f}")
        ok &= abs(v - want) / want < 0.01
    pr("\n=== SELF-TEST 2: analytic FRF == state-space FRF (LTI modes: avg, fresh), angle P+I+D, nominal 12.5 m/s ===")
    p = plant_at("nominal", 12.5)
    for hold in ("avg", "fresh"):
        c = Ctl(kp=2000, ki=300, kd=16, hold=hold)
        lp = Loop(c, p)
        A, B = lp.mats(False)
        # open-loop: break at u -- simplest check: closed-loop T_ref from the state space vs analytic
        Cth = np.zeros(lp.N)
        Cth[:lp.np_] = lp.Cd[0]
        worst = 0.0
        for f in (0.3, 1.0, 3.0, 10.0, 20.0, 45.0):
            zz = np.exp(2j * np.pi * f * TS)
            x = np.linalg.solve(zz * np.eye(lp.N) - A, B)
            ss_tr = Cth @ x
            Pf = p.frf(np.array([f]))[0]
            cc = replace(c, d=p.tau)
            L = C_fb(np.array([f]), cc)[0] * Pf
            an = C_ref(np.array([f]), cc)[0] * Pf / (1 + L)
            worst = max(worst, abs(ss_tr - an) / abs(an))
        pr(f"  hold={hold}: worst relative |T_ref(state space) - T_ref(analytic)| over 0.3-45 Hz = {worst:.2e}")
        ok &= worst < 1e-6
    pr("\n=== SELF-TEST 3: the BYTE-EXACT integer lane (lane_mirror_v295.lane_tick, edits 1-5, pol -1) vs C_fb ===")
    pr("    driven open loop by a sinusoidal angle through an emulated 100 Hz hold (age 1..10), theta_sp = 0;")
    pr("    the fundamental of u = -T over whole cycles vs the model -C_fb(f) with d = 0 (gp-0x6b38 is pre-transport);")
    pr("    a ratio of 1.00x / 0 deg proves u = -C_fb*theta, i.e. the edited lane is NEGATIVE feedback on the angle")
    cal = dict(CAL, a=0, b=8192, C=65535, DB=0, DCL=10240, ICL=10240)
    ed = LM.Edits(x_src="angle", fb_op="sum", sp_src="69ae", d_src="rate")
    for kp, ki, kd in ((2000, 0, 0), (2000, 300, 0), (2000, 0, 16), (3000, 500, 8)):
        cal2 = dict(cal, kp=(KP_X, (kp,) * 5), kd=(KD_X, (kd,) * 4), Ki=ki)
        c = Ctl(kp=kp, ki=ki, kd=kd, hold="hold", d=0)
        line = []
        for f, A_deg in ((0.5, 3.0), (2.0, 3.0), (5.0, 3.0), (10.0, 3.0), (20.0, 3.0)):
            per = int(round(1000 / f))
            n_tot = per * int(math.ceil(3000 / per)) + 2 * per
            st = LM.LaneState()
            th_c = [A_deg * 10 * math.sin(2 * math.pi * f * n * TS) for n in range(n_tot + 10)]
            th_i = [int(round(v)) for v in th_c]
            held_th, held_x = 0, 0
            u = []
            for n in range(n_tot):
                T = LM.lane_tick(st, cal2, ed, rate=held_x, angle=held_th, cmd69ae=0, pol=-1)
                u.append(-T)
                if n % 10 == 0:                   # slot 4 writes AFTER slot 0 on the activation tick
                    held_th = th_i[n]
                    x_true = 8.0 * (th_c[n] - th_c[n - 3]) / 10.0 / (3 * TS) if n >= 3 else 0.0
                    held_x = int(round(x_true))
            u = np.array(u[-(n_tot - 2 * per):], float)
            nn = np.arange(n_tot - (n_tot - 2 * per), n_tot)
            ph = np.exp(-2j * np.pi * f * nn * TS)
            U = 2 * np.mean((u - u.mean()) * ph)
            TH = 2 * np.mean(np.array([A_deg * math.sin(2 * math.pi * f * k * TS) for k in nn]) * ph)
            meas = U / TH
            mod = -C_fb(np.array([f]), c)[0]          # u = -C_fb * theta: NEGATIVE feedback through pol = -1
            line.append(f"{f:g}Hz {abs(meas) / abs(mod):.3f}x {math.degrees(np.angle(meas / mod)):+.1f}deg")
        pr(f"  Kp {kp} Ki {ki} Kd {kd}: measured/model  " + " | ".join(line))
    pr("    (integer floors in P/I/D/lag/T and the angle's 0.1 deg LSB make the residual; agreement to ~1-3 % / ~1-2 deg")
    pr("     means the chain, the sign and the hold model are the bytes')")
    pr("\n=== SELF-TEST 4: exact periodic loop vs its LTI fundamental, closed loop (theta_sp sine, nominal 12.5 m/s) ===")
    for kp, kd in ((2500, 0), (2500, 16)):
        c = Ctl(kp=kp, kd=kd, hold="hold")
        lp = Loop(c, p)
        row = []
        for f in (1.0, 3.0, 10.0, 20.0):
            per = int(round(1000 / f))
            n_tot = per * int(math.ceil(4000 / per)) + 4 * per
            n = np.arange(n_tot)
            r = np.sin(2 * np.pi * f * n * TS)
            th = lp.simulate(r)
            seg = slice(n_tot - per * int(math.ceil(2000 / per)), n_tot)
            ph = np.exp(-2j * np.pi * f * n[seg] * TS)
            meas = np.mean(th[seg] * ph) / np.mean(r[seg] * ph)
            cc = replace(Ctl(kp=kp, kd=kd, hold="avg"), d=p.tau)
            Pf = p.frf(np.array([f]))[0]
            an = C_ref(np.array([f]), cc)[0] * Pf / (1 + C_fb(np.array([f]), cc)[0] * Pf)
            row.append(f"{f:g}Hz exact {abs(meas):.4f}/{math.degrees(np.angle(meas)):+.1f} vs LTI-avg "
                       f"{abs(an):.4f}/{math.degrees(np.angle(an)):+.1f}")
        pr(f"  Kp {kp} Kd {kd}: " + " | ".join(row))
    pr("\n=== SELF-TEST 5: hold kernel forms at 3 and 20 Hz (|H|, phase) ===")
    for mode in ("hold", "hold09", "cont", "cont5", "fresh"):
        h = H_hold(np.array([3.0, 20.0]), mode, range(0, 10) if mode == "hold09" else range(1, 11))
        pr(f"  {mode:7s}: 3 Hz {abs(h[0]):.4f} {math.degrees(np.angle(h[0])):+.2f} deg | 20 Hz {abs(h[1]):.4f} "
           f"{math.degrees(np.angle(h[1])):+.2f} deg")
    pr("SELFTEST " + ("PASS" if ok else "FAIL"))
    return ok


# ======================================================================================================================
# THE STUDY
# ======================================================================================================================
KDS = (0, 8, 16, 24, 32)                 # Kd (edit 5, D on the held rate): D = -Kd*x/8  ->  0.160*Kd T per deg/s
# Ki specs.  ('flat', Ki): the ONE scalar cell 0xC63E6 (ld.hu), so the PI corner f_I = 7.8125*Ki/(2 pi Kp) falls as Kp(v)
# rises.  ('fI', f): Ki proportional to Kp -- what a cave that schedules a gain on E (P and I together) would give.
KIS = (("flat", 0), ("flat", 150), ("flat", 400), ("fI", 0.2), ("fI", 0.4))
KPS = np.unique(np.round(np.logspace(math.log10(300), math.log10(8000), 49)))
IDENT = ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "tau0", "tau6", "ms_free")
LOOPSHAPE20 = KIT.parent / "rlog-tools" / "studies" / "grind" / "_scratch" / "loopshape20_plants.json"


def kis_str(kis):
    return f"Ki {kis[1]:3d}" if kis[0] == "flat" else f"fI {kis[1]:.1f}"


def ctl(kp, kd, kis, **kw):
    ki = kis[1] if kis[0] == "flat" else ki_for(kp, kis[1])
    return Ctl(kp=float(kp), kd=float(kd), ki=float(ki), **kw)


def fmt_row(v, c, r):
    w = r.get("wheel", (float("nan"),) * 2)
    h = r.get("hfmode", (float("nan"),) * 2)
    return (f"{v:5.1f} {c.kp:6.0f} {c.ki:4.0f} {c.kd:3.0f} | fc {r['fc']:5.2f} PM {r['pm']:6.1f} "
            f"GM {r.get('gm_exact_db', r['gm_lti_db']):5.1f} f180 {r['f180']:5.1f} | L20 {r['L20']:.4f} M20 {r['M20']:.2f} "
            f"ReCr20 {r['ReCr20']:+.2f} | Ms {r['Ms']:.2f} S5-30 {r['S530_db']:+.1f} "
            f"T5-30 {max(r.get('Tr530_db', -99), r['Tc530_db']):+.1f} Tr1.6-3 {r.get('Tr163', float('nan')):.2f}"
            f" | Tr0 {r.get('Tr0', float('nan')):.3f} hold {r.get('hold', float('nan')):.3f}"
            f" trk {r.get('trk_min', float('nan')):.3f}-{r.get('trk_max', float('nan')):.3f}"
            f" | wheel {w[0]:.2f}Hz z{w[1]:.2f} hf {h[0]:.1f}Hz z{h[1]:.2f}")


def gates(r, r295, strict=False):
    """SAFETY gates (frequency-domain proxies of the goal's 5-30 Hz criteria).  Written before the sweep was scored;
    the strict |S| reading ('lineS') was added after the first pass showed that every 2.5-3.5 Hz design fails it."""
    nocross = not np.isfinite(r["fc"])
    g = dict(PM45=bool(nocross or r["pm"] >= 45.0),
             GM6=bool(r.get("gm_exact_db", r["gm_lti_db"]) >= 6.0),
             M20=bool(r["M20"] <= r295["M20"] * (1 + 1e-9)),
             L20=bool(r["L20"] <= r295["L20"] * (1 + 1e-9)),
             lineT=bool(max(r.get("Tr530_db", -99.0), r["Tc530_db"]) <= 3.0),
             pole=bool(not (r["hfmode"][1] < 0.2)),
             stable=bool(r["stable"]))
    if strict:
        g["lineS"] = bool(r["S530_db"] <= 3.0)
    return g


def perf_ok(r, v):
    """PERFORMANCE (the goal's band criteria, frequency-domain proxies): fc >= 2.5 Hz at every speed; at v >= 8 m/s also
    tracking |T_ref| in 0.95-1.05 over 0.1-1 Hz (absolute) and turn-hold |T_ref(0.05 Hz)| >= 0.90."""
    ok = bool(np.isfinite(r["fc"]) and r["fc"] >= 2.5)
    if v >= 8.0:
        ok = ok and 0.95 <= r["trk_min"] and r["trk_max"] <= 1.05 and r["hold"] >= 0.90
    return bool(ok)


def kp_for_fc(kd, kis, p: Plant, target, lo=50.0, hi=20000.0, **kw):
    def fc_of(kp):
        x = metrics(ctl(kp, kd, kis, **kw), p, exact=False)["fc"]
        return x if np.isfinite(x) else 0.0
    if not (fc_of(lo) < target < fc_of(hi)):
        return float("nan")
    for _ in range(40):
        m = math.sqrt(lo * hi)
        if fc_of(m) < target:
            lo = m
        else:
            hi = m
    return math.sqrt(lo * hi)


def full(c: Ctl, p: Plant):
    r = metrics(c, p, exact=True)
    r["gm_exact_db"] = 20 * math.log10(exact_gm(c, p)) if r["stable"] else float("-inf")
    return r


def safe_set(kd, kis, p, r295, strict=False, grid=KPS, cache=None, **kw):
    """grid Kp values passing every safety gate (LTI GM >= 6 dB in the scan; the exact GM is checked at the edge).
    Returns (lo, hi) of the contiguous safe block containing the largest safe Kp, or (nan, nan)."""
    ok = []
    for kp in grid:
        r = cache[float(kp)] if cache is not None else metrics(ctl(kp, kd, kis, **kw), p, exact=True)
        g = gates(r, r295, strict)
        g["GM6"] = r["gm_lti_db"] >= 6.0
        ok.append(all(g.values()))
    if not any(ok):
        return float("nan"), float("nan")
    j = max(i for i, o in enumerate(ok) if o)
    i = j
    while i > 0 and ok[i - 1]:
        i -= 1
    return float(grid[i]), float(grid[j])


DESIGN_KEYS = ("fc", "pm", "gm_exact_db", "M20", "L20", "ReCr20", "S530_db", "Tc530_db", "Tr530_db", "hold", "trk_min",
               "trk_max")


def _clean(r):
    return {kk: vv for kk, vv in r.items() if not isinstance(vv, tuple)}


def study():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    js = {}
    pr("# harness_freq.py -- angle-loop frequency-domain study (2026-09-30)")
    pr(f"# image cals (V295, LE): oa {OA} ob {OB} fwd {CAL['fwd']} PCL {CAL['PCL']} SCL {CAL['SCL']} OCL {CAL['OCL']} "
       f"DB {CAL['DB']} ICL {CAL['ICL']} Kp X {KP_X} Kd X {KD_X}")
    g0 = FADE * FWD * OB / 1024 * 2 / 32 / (1 - OA / 1024)
    k_dc = g0 / 256 * 160
    pr(f"# DC: u (T counts) per deg of angle error = {k_dc:.5f} * Kp ; D = {g0:.4f} * Kd T per deg/s ;"
       f" I-rate = {g0 * 160 * 1000 / 32768:.4f} * Ki T per deg per s ; PI corner f_I = 7.8125*Ki/(2 pi Kp) Hz")

    # ---------------- 0. plant ----------------
    pr("\n## 0. PLANT (v294_plant.family(); linear in speed between the fit knots 3.1/8/11.9/17/26.9 m/s, flat outside)")
    pr("  v m/s |  J      b      k     Fc    Fs  | roots of J s^2+b s+k (Hz) | light_b (prior, BELIEF) J b k")
    for v in SPEEDS:
        pn = FAM["nominal"].at(v)
        lb = FAM["light_b"].at(v)
        rts = np.roots([pn.J, pn.b, pn.k])
        pr(f"  {v:5.1f} | {pn.J:.3f} {pn.b:6.2f} {pn.k:6.1f} {pn.Fc:5.1f} {pn.Fs:5.1f} | "
           + " ".join(f"{abs(q) / 2 / np.pi:6.3f}" for q in rts) + f" | {lb.J:.3f} {lb.b:.2f} {lb.k:.1f}")
    pr("  member corners at each speed (J / b / k):")
    for m in IDENT[1:] + ("light_b",):
        pr(f"   {m:8s} " + "  ".join(f"{v:g}:{FAM[m].at(v).J:.2f}/{FAM[m].at(v).b:.1f}/{FAM[m].at(v).k:.0f}"
                                     for v in SPEEDS))

    # ---------------- 1. hold cost ----------------
    pr("\n## 1. WHAT THE 100 Hz HOLD COSTS (angle operand: hold then the FIR 8th[n]+8th[n-1]; phase of the operand path)")
    for f in (1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 6.0, 13.0, 15.0, 17.0, 20.0):
        fa = np.array([f])
        r_h = np.angle(R_fb(fa, Ctl()) * H_hold(fa, "hold"))[0]
        r_f = np.angle(R_fb(fa, Ctl()) * H_hold(fa, "fresh"))[0]
        pr(f"  {f:5.1f} Hz: held {math.degrees(r_h):+7.2f} deg |H| {abs(H_hold(fa))[0]:.4f} | fresh {math.degrees(r_f):+6.2f}"
           f" | HOLD COST {math.degrees(r_h - r_f):+6.2f} deg | output lag {math.degrees(np.angle(H_out(fa))[0]):+6.1f} deg"
           f" |Hout| {abs(H_out(fa))[0]:.3f} | 2 ms transport {-360 * f * 0.002:+5.1f} deg")

    # ---------------- 2. references ----------------
    pr("\n## 2. REFERENCE LOOPS on the same nominal plants (rate operand, held, w 3 ms, d = 2 ms) -- the 20 Hz bars")
    ref = {}
    for v in SPEEDS:
        p = plant_at("nominal", v)
        for c in (V295, V294, V282):
            r = full(c, p)
            ref[(c.name, v)] = r
            pr(f"  {c.name} " + fmt_row(v, c, r))
    js["ref"] = {f"{k[0]}@{k[1]}": _clean(r) for k, r in ref.items()}

    # ---------------- 3. sweep ----------------
    pr("\n## 3. SWEEP: angle loop, held gp-0x6a00 (+ held gp-0x6a56 for D), nominal member, d = 2 ms (every 6th grid Kp"
       " printed; the full grid is in out.json)")
    pr("   v Kp Ki Kd | crossover, PM, GM(LTI) dB, phase-crossover | |L(20)|, M20 (record measure), Re Cr(20) T/(deg/s) |"
       " Ms, max|S| 5-30 dB, max(|T_ref|,|T|) 5-30 dB, max|T_ref| 1.6-3 Hz | T_ref(0), turn-hold |T_ref(0.05 Hz)|,"
       " tracking |T_ref| over 0.1-1 Hz | exact closed-loop wheel mode (<8 Hz) and least-damped 5-50 Hz mode")
    sweep = {}
    for v in SPEEDS:
        p = plant_at("nominal", v)
        for kd in KDS:
            for kis in KIS:
                for kp in KPS:
                    sweep[(v, kd, kis, float(kp))] = metrics(ctl(kp, kd, kis), p, exact=True)
        for kd in KDS:
            for kis in KIS:
                for kp in KPS[::6]:
                    pr("  " + fmt_row(v, ctl(kp, kd, kis), sweep[(v, kd, kis, float(kp))]))
    keys = ("fc", "pm", "gm_lti_db", "L20", "M20", "ReCr20", "Ms", "S530_db", "Tc530_db", "Tr530_db", "Tr0", "hold",
            "trk_min", "trk_max", "Tr163")
    for v in SPEEDS:                         # the full sweep as one CSV per speed (each well under the 256 KB cap)
        rows = ["kd,ki_kind,ki_val,kp,ki," + ",".join(keys) + ",wheel_f,wheel_z,hf_f,hf_z"]
        for (vv, kd, kis, kp), r in sweep.items():
            if vv != v:
                continue
            rows.append(f"{kd},{kis[0]},{kis[1]},{kp:.0f},{ctl(kp, kd, kis).ki:.1f}," + ",".join(f"{r[k]:.5g}" for k in keys)
                        + f",{r['wheel'][0]:.4g},{r['wheel'][1]:.4g},{r['hfmode'][0]:.4g},{r['hfmode'][1]:.4g}")
        (OUTDIR / f"sweep_v{v:g}.csv").write_text("\n".join(rows), encoding="utf-8")

    # ---------------- 4. Kp(v) for 2.5 / 3.0 / 3.5 Hz ----------------
    pr("\n## 4. Kp(v) FOR A 2.5 / 3.0 / 3.5 Hz CROSSOVER (nominal), exact GM, and the gates it fails "
       "(T-reading; 'lineS' = the strict |S| reading)")
    design = {}
    for v in SPEEDS:
        p = plant_at("nominal", v)
        r295 = ref[("V295", v)]
        for kd in KDS:
            for kis in KIS:
                for tgt in (2.5, 3.0, 3.5):
                    kp = kp_for_fc(kd, kis, p, tgt)
                    if not np.isfinite(kp):
                        pr(f"  v {v:5.1f} Kd {kd:2d} {kis_str(kis)}: fc {tgt} unreachable")
                        continue
                    c = ctl(kp, kd, kis)
                    r = full(c, p)
                    g = gates(r, r295, strict=True)
                    design[(v, kd, kis, tgt)] = (kp, r, g)
                    fails = [k for k, ok in g.items() if not ok]
                    pr(f"  fc {tgt} " + fmt_row(v, c, r) + " | FAILS " + (" ".join(fails) if fails else "none")
                       + ("" if perf_ok(r, v) else " | perf X"))
    js["design"] = {f"{k[0]}|{k[1]}|{k[2][0]}{k[2][1]}|{k[3]}": [d[0]] + [d[1][kk] for kk in DESIGN_KEYS]
                    + [" ".join(g for g, ok in d[2].items() if not ok)] for k, d in design.items()}
    js["design_columns"] = ["kp"] + list(DESIGN_KEYS) + ["failed_gates"]

    # ---------------- 5. safe windows (nominal) ----------------
    pr("\n## 5. SAFE Kp WINDOW PER SPEED (nominal). [lo-hi] = the contiguous block of grid Kp passing EVERY safety gate"
       " (PM >= 45, GM >= 6 dB, M20 <= V295, |L(20)| <= V295, max(|T_ref|,|T|) 5-30 <= +3 dB, no 5-50 Hz pole with"
       " zeta < 0.2, stable), T-reading; S = its upper edge under the strict |S| reading; fc at the upper edge;"
       " perf = grid Kp meeting PERFORMANCE (fc >= 2.5; >= 8 m/s also tracking 0.95-1.05 over 0.1-1 Hz and hold >= 0.90),"
       " shown as its min; OK = some Kp is both safe and performing")
    window = {}
    for kd in KDS:
        for kis in KIS:
            line = []
            for v in SPEEDS:
                p = plant_at("nominal", v)
                r295 = ref[("V295", v)]
                cache = {float(kp): sweep[(v, kd, kis, float(kp))] for kp in KPS}
                lo, hi = safe_set(kd, kis, p, r295, cache=cache)
                _, hiS = safe_set(kd, kis, p, r295, strict=True, cache=cache)
                pk = [float(kp) for kp in KPS if perf_ok(cache[float(kp)], v)]
                both = [k for k in pk if np.isfinite(lo) and lo <= k <= hi]
                fcT = cache[hi]["fc"] if np.isfinite(hi) else float("nan")
                window[(kd, kis, v)] = dict(lo=lo, hi=hi, hiS=hiS, perf_min=(min(pk) if pk else float("nan")),
                                            both=both, fcT=fcT)
                line.append(f"{v:g}: [{lo:4.0f}-{hi:4.0f}] S{hiS:4.0f} fc {fcT:4.2f} perf {min(pk) if pk else float('nan'):5.0f}"
                            + (" OK" if both else " X"))
            pr(f"  Kd {kd:2d} {kis_str(kis)} | " + " | ".join(line))
    js["window"] = {f"{k[0]}|{k[1][0]}{k[1][1]}|{k[2]}": w for k, w in window.items()}

    # ---------------- 6. the three schedules ----------------
    pr("\n## 6. SCHEDULES (nominal first; robustness across the identified family in section 7)")
    pr("  6a. SPEED-SCHEDULED gain [needs the speed-LERP cave]: Kp(v) = the Kp for fc 3.0 Hz, capped at the safe upper"
       " edge; Kd flat; Ki flat (Kp-only schedule) or Ki proportional to Kp (an E-gain schedule, fI rows)")
    sched = {}
    best = None
    for kd in KDS:
        for kis in KIS:
            rows, fcs, okall, kps = [], [], True, {}
            for v in SPEEDS:
                p = plant_at("nominal", v)
                k3 = design.get((v, kd, kis, 3.0), (float("nan"),))[0]
                w = window[(kd, kis, v)]
                if np.isfinite(k3) and np.isfinite(w["hi"]) and w["lo"] <= k3 <= w["hi"]:
                    kp = k3
                elif np.isfinite(k3) and np.isfinite(w["hi"]) and k3 > w["hi"]:
                    kp = w["hi"]
                else:
                    kp = w["hi"]
                if not np.isfinite(kp):
                    okall = False
                    rows.append(f"{v:g}: none")
                    fcs.append(0.0)
                    continue
                kps[v] = kp
                r = metrics(ctl(kp, kd, kis), p, exact=True)
                fcs.append(r["fc"] if np.isfinite(r["fc"]) else 0.0)
                okall = okall and perf_ok(r, v) and all(gates(r, ref[("V295", v)]).values())
                rows.append(f"{v:g}: Kp {kp:5.0f} Ki {ctl(kp, kd, kis).ki:4.0f} fc {r['fc']:.2f} PM {r['pm']:.0f} hold {r['hold']:.2f}"
                            f" trk {r['trk_min']:.2f}-{r['trk_max']:.2f}" + ("" if perf_ok(r, v) else " X"))
            sched[(kd, kis)] = dict(minfc=min(fcs), ok=okall, kps=kps)
            pr(f"   Kd {kd:2d} {kis_str(kis)} | min fc {min(fcs):.2f} | "
               f"{'MEETS every perf criterion at every speed' if okall else 'fails'} | " + " ; ".join(rows))
            score = (okall, sum(perf_ok(metrics(ctl(kps[v], kd, kis), plant_at('nominal', v), exact=False), v)
                                for v in kps), min(fcs))
            sched[(kd, kis)]["score"] = score
            if best is None or score > sched[best]["score"]:
                best = (kd, kis)
    pr(f"  -> best (Kd, Ki) for the speed schedule on the nominal: Kd {best[0]} {kis_str(best[1])}")
    pr("\n  6b. FLAT Kp (cal-only): one Kp at every speed = the largest Kp inside the safe block at EVERY speed")
    flat = {}
    for kd in KDS:
        for kis in KIS:
            his = [window[(kd, kis, v)]["hi"] for v in SPEEDS]
            los = [window[(kd, kis, v)]["lo"] for v in SPEEDS]
            kp = float(np.min(his)) if all(np.isfinite(his)) else float("nan")
            if np.isfinite(kp) and kp < max(los):
                kp = float("nan")
            rows = []
            if np.isfinite(kp):
                for v in SPEEDS:
                    r = metrics(ctl(kp, kd, kis), plant_at("nominal", v), exact=True)
                    rows.append(f"{v:g}: fc {r['fc']:.2f} PM {r['pm']:.0f} hold {r['hold']:.2f} trk {r['trk_min']:.2f}-"
                                f"{r['trk_max']:.2f}" + ("" if perf_ok(r, v) else " X"))
            flat[(kd, kis)] = kp
            pr(f"   Kd {kd:2d} {kis_str(kis)} | Kp {kp:5.0f} | " + " ; ".join(rows))
    pr("\n  6c. ANGLE-INDEXED Kp (cal-only: the 5-knot Kp record keyed by idx = 0.620*|theta_sp| deg). A knot at |theta_sp|"
       " = theta can be reached by every speed v with theta_max(v) = (180/pi)*L*SR*3/v^2 >= theta (L 2.83 m, SR 16,"
       " a_lat <= 3 m/s^2), i.e. by every v <= v(theta), INCLUDING 3 m/s; its safe Kp is the min over those speeds of"
       " the safe upper edge.")
    for v in SPEEDS:
        pr(f"   theta_max({v:g} m/s) = {theta_max_deg(v):7.1f} deg -> idx {theta_max_deg(v) * IDX_PER_DEG:6.1f}")
    for kd, kis in sorted(sched, key=lambda q: sched[q]["score"], reverse=True)[:6]:
        his = [window[(kd, kis, v)]["hi"] for v in SPEEDS]
        knots = []
        for v in SPEEDS:
            reach = [vv for vv in SPEEDS if theta_max_deg(vv) >= theta_max_deg(v) - 1e-9]
            knots.append((theta_max_deg(v), float(np.nanmin([window[(kd, kis, vv)]["hi"] for vv in reach]))))
        mono = all(his[i] <= his[i + 1] for i in range(len(his) - 1) if np.isfinite(his[i]) and np.isfinite(his[i + 1]))
        pr(f"   Kd {kd:2d} {kis_str(kis)}: safe upper edge by speed {[round(x) if np.isfinite(x) else None for x in his]}"
           f" (monotone in v: {mono}) -> knots " + ", ".join(f"{t:.0f} deg: {k:.0f}" for t, k in knots))
    js["sched"] = {f"{k[0]}|{k[1][0]}{k[1][1]}": {"minfc": v["minfc"], "ok": v["ok"], "kps": v["kps"]}
                   for k, v in sched.items()}
    js["flat"] = {f"{k[0]}|{k[1][0]}{k[1][1]}": v for k, v in flat.items()}

    # ---------------- 6d. speed schedule of Kp AND Kd, E-gain I ----------------
    pr("\n  6d. SPEED-SCHEDULED Kp AND Kd [cave, or both LERP keys moved to speed -- BELIEF, not traced], Ki = Kp*const"
       " (PI corner fI fixed, as an E-gain schedule gives). Per speed: for each Kd, Kp = the fc-3.0 Hz Kp capped at the"
       " safe upper edge; choose the Kd that passes every safety gate AND performance with the highest fc (else the safe"
       " one with the highest fc).")
    sched2 = {}
    for fi in (0.2, 0.3, 0.4):
        kis_ = ("fI", fi)
        rows, npass, dsg = [], 0, {}
        for v in SPEEDS:
            p = plant_at("nominal", v)
            r295 = ref[("V295", v)]
            cands = []
            for kd_ in KDS:
                lo, hi = safe_set(kd_, kis_, p, r295)
                if not np.isfinite(hi):
                    continue
                k3 = kp_for_fc(kd_, kis_, p, 3.0)
                kp_ = k3 if (np.isfinite(k3) and lo <= k3 <= hi) else hi
                r = metrics(ctl(kp_, kd_, kis_), p, exact=True)
                ok_s = all(gates(r, r295).values())
                cands.append((ok_s and perf_ok(r, v), ok_s, r["fc"] if np.isfinite(r["fc"]) else 0.0, -kd_, kd_, kp_, r))
            if not cands:
                rows.append(f"{v:g}: none")
                continue
            cands.sort(reverse=True)
            okp, oks, fcv, _, kd_, kp_, r = cands[0]
            npass += okp
            dsg[v] = (kp_, kd_)
            rows.append(f"{v:g}: Kp {kp_:5.0f} Kd {kd_:2d} Ki {ctl(kp_, kd_, kis_).ki:4.0f} fc {r['fc']:.2f} PM {r['pm']:.0f}"
                        f" M20 {r['M20']:.2f} hold {r['hold']:.2f} trk {r['trk_min']:.2f}-{r['trk_max']:.2f}"
                        + ("" if okp else " X"))
        sched2[fi] = dict(npass=npass, dsg=dsg)
        pr(f"   fI {fi:.1f} | passes at {npass}/{len(SPEEDS)} speeds | " + " ; ".join(rows))
    fbest = max(sched2, key=lambda q: (sched2[q]["npass"], -abs(q - 0.3)))
    kis = ("fI", fbest)
    dsg = sched2[fbest]["dsg"]
    kp_sched = {v: dsg[v][0] for v in dsg}
    kd_sched = {v: dsg[v][1] for v in dsg}
    pr(f"  -> chosen: fI {fbest} | " + ", ".join(f"{v:g}: Kp {kp_sched[v]:.0f} Kd {kd_sched[v]}" for v in SPEEDS))
    js["sched2"] = {str(k): {"npass": v["npass"], "dsg": {str(a): b for a, b in v["dsg"].items()}} for k, v in sched2.items()}

    # ---------------- 7. robustness across the identified family ----------------
    pr(f"\n## 7. ROBUSTNESS of the 6d schedule (fI {fbest}) across the family (designed on the nominal).  CREDIBLE set ="
       f" nominal, J_lo, J_hi (0.5), b_lo, b_hi, tau0, tau6; STRESS = J_hi2 (0.8), ms_free (J free: 2.03 at 12.5 m/s),"
       f" light_b (the PRIOR, BELIEF; predicts the drive worse than every identified member)")
    CRED = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")
    STRESS = ("J_hi2", "ms_free", "light_b")
    for v in SPEEDS:
        for m in CRED + STRESS:
            p = plant_at(m, v)
            c = ctl(kp_sched[v], kd_sched[v], kis)
            r = full(c, p)
            r295 = metrics(V295, p, exact=True)
            g = gates(r, r295)
            fails = [k for k, ok in g.items() if not ok]
            pr(f"   {m:8s} " + fmt_row(v, c, r) + " | FAILS " + (" ".join(fails) if fails else "none")
               + ("" if perf_ok(r, v) else " | perf X"))
    pr("\n   safe upper edge per member at the schedule's Kd(v); ROBUST Kp(v) = min(design Kp, CREDIBLE edge):")
    kp_rob = {}
    for v in SPEEDS:
        caps = {}
        for m in CRED + STRESS:
            p = plant_at(m, v)
            caps[m] = safe_set(kd_sched[v], kis, p, metrics(V295, p, exact=True))[1]
        edge = float(np.nanmin([caps[m] for m in CRED]))
        kp_rob[v] = min(kp_sched[v], edge) if np.isfinite(edge) else float("nan")
        bind = min(CRED, key=lambda m: caps[m] if np.isfinite(caps[m]) else -1)
        r = metrics(ctl(kp_rob[v], kd_sched[v], kis), plant_at("nominal", v), exact=True) if np.isfinite(kp_rob[v]) else None
        pr(f"   v {v:5.1f} Kd {kd_sched[v]:2d}: design Kp {kp_sched[v]:5.0f} | credible edge {edge:5.0f} (binding {bind}) ->"
           f" ROBUST Kp {kp_rob[v]:5.0f}: nominal fc {r['fc']:.2f} PM {r['pm']:.0f} hold {r['hold']:.2f} trk"
           f" {r['trk_min']:.2f}-{r['trk_max']:.2f}{'' if perf_ok(r, v) else ' X'} | " + " ".join(f"{m}:{caps[m]:.0f}" for m in caps))
    js["kp_rob"] = {str(k): v for k, v in kp_rob.items()}
    js["kp_sched"] = {str(k): v for k, v in kp_sched.items()}
    js["kd_sched"] = {str(k): v for k, v in kd_sched.items()}
    js["best"] = [list(kis)]

    # ---------------- 8. fresh operand ----------------
    pr("\n## 8. WHAT A FRESH 1 kHz OPERAND BUYS (a cave: theta and the D rate read fresh, same tick; nominal; 6d schedule)")
    pr("   (gp-0x69ca alone is NOT the setpoint's frame: slope 1/1.155 near centre and a 0-7.3 deg offset shape; this"
       " assumes the cave rebuilds gp-0x6a00 at 1 kHz, tracer-angle option (b)/(c))")
    for v in SPEEDS:
        p = plant_at("nominal", v)
        r295 = ref[("V295", v)]
        kp, kd = kp_sched[v], kd_sched[v]
        rh = full(ctl(kp, kd, kis, hold="hold"), p)
        rf = full(ctl(kp, kd, kis, hold="fresh"), p)
        r9 = metrics(ctl(kp, kd, kis, hold="hold09"), p, exact=True)
        kmh = safe_set(kd, kis, p, r295)[1]
        kmf = safe_set(kd, kis, p, r295, hold="fresh")[1]
        fch = metrics(ctl(kmh, kd, kis), p, exact=False)["fc"] if np.isfinite(kmh) else float("nan")
        fcf = metrics(ctl(kmf, kd, kis, hold="fresh"), p, exact=False)["fc"] if np.isfinite(kmf) else float("nan")
        pr(f"   v {v:5.1f} Kp {kp:5.0f} Kd {kd:2d}: held PM {rh['pm']:5.1f} GM {rh['gm_exact_db']:5.1f} M20 {rh['M20']:.2f}"
           f" ReCr20 {rh['ReCr20']:+.2f} | fresh PM {rf['pm']:5.1f} ({rf['pm'] - rh['pm']:+.1f}) GM {rf['gm_exact_db']:5.1f}"
           f" M20 {rf['M20']:.2f} ReCr20 {rf['ReCr20']:+.2f} | ages 0-9 PM {r9['pm']:5.1f} | safe upper edge held {kmh:5.0f}"
           f" (fc {fch:.2f}) fresh {kmf:5.0f} (fc {fcf:.2f})")

    # ---------------- 9. the 20 Hz plant mode, as the record models it ----------------
    pr("\n## 9. THE 20 Hz PLANT MODE (stress cases; NOT identified on r71b): exact closed-loop (lifted) zeta of the"
       " least-damped 10-50 Hz pole -- open plant / V295 / V282 / the 6d schedule (held) / same with a fresh operand."
       " Rows whose 'open' entry is ~25/50 Hz with zeta > 0.9 are members where the flexible mode is overdamped by b"
       " (r2 0.8 at speed): no mode to de-damp.")
    stress = []
    for f2 in (16.0, 20.0, 24.0):
        for r2 in (0.2, 0.5, 0.8):
            for z2 in (0.02, 0.05):
                stress.append(("two-mass", dict(f2=f2, r2=r2, zeta2=z2)))
    if LOOPSHAPE20.exists():
        l20 = json.load(open(LOOPSHAPE20))
        for nm in ("resonant", "smooth+mode", "weak-mode"):
            d = l20[nm]
            if d.get("fp"):
                stress.append(("mult:" + nm, dict(fp=d["fp"], zp=d["zp"], kappa=d.get("kappa"))))
    else:
        pr("   (loopshape20_plants.json not found; multiplicative modes skipped)")

    def flex(c, p):
        lp = Loop(replace(c, d=p.tau), p)
        s, rho, _ = lp.poles()
        md = modes(s, 10.0, 50.0)
        return (min(md, key=lambda t: t[1]) if md else (float("nan"), float("nan"))), rho

    st_js = []
    for v in (3.0, 12.5, 26.0):
        base = FAM["nominal"].at(v)
        for kind, kwm in stress:
            p = Plant(J=base.J, b=base.b, k=base.k, tau=2, **kwm)
            po = flex(replace(V295, gain=1e-9), p)[0]
            a = flex(V295, p)
            b_ = flex(V282, p)
            c_ = flex(ctl(kp_sched[v], kd_sched[v], kis), p)
            d_ = flex(ctl(kp_sched[v], kd_sched[v], kis, hold="fresh"), p)
            tag = lambda x: " UNSTABLE" if x[1] >= 1 else ""  # noqa: E731
            st_js.append(dict(v=v, kind=kind, kw=kwm, open=po, v295=a[0], v282=b_[0], held=c_[0], fresh=d_[0],
                              rho=[a[1], b_[1], c_[1], d_[1]]))
            pr(f"   v {v:5.1f} {kind:17s} {json.dumps(kwm):46s} open {po[0]:5.1f}Hz z{po[1]:.3f} | V295 {a[0][0]:5.1f}/{a[0][1]:+.3f}"
               f"{tag(a)} | V282 {b_[0][0]:5.1f}/{b_[0][1]:+.3f}{tag(b_)} | angle held {c_[0][0]:5.1f}/{c_[0][1]:+.3f}"
               f"{tag(c_)} | angle fresh {d_[0][0]:5.1f}/{d_[0][1]:+.3f}{tag(d_)}")
    js["stress"] = st_js

    # ---------------- 10. quantisation and friction (static estimates) ----------------
    pr("\n## 10. THE ANGLE LSB AND THE FRICTION (static / describing-function estimates; the time-domain harness must confirm)")
    pr("   gp-0x6a00 is int16 at 0.1 deg: one LSB moves the P torque by Kp*0.01002 T counts. Near an LSB boundary the"
       " quantiser is a relay; the DF relay limit cycle sits at the phase crossover f180 with angle amplitude"
       " A = 2*LSB*|L(f180)|/pi and torque fundamental |C_fb(f180)|*2*LSB/pi. It survives only if that torque swing beats"
       " static friction Fs (else the wheel sticks inside the LSB).")
    for tagname, sched_kp in (("6d design", kp_sched), ("ROBUST", kp_rob)):
        for v in SPEEDS:
            p = plant_at("nominal", v)
            pn = FAM["nominal"].at(v)
            kp = sched_kp[v]
            c = replace(ctl(kp, kd_sched[v], kis), d=p.tau)
            r = metrics(c, p, exact=False)
            f180 = r["f180"]
            if np.isfinite(f180):
                Cf = abs(C_fb(np.array([f180]), c)[0])
                Lf = Cf * abs(p.frf(np.array([f180]))[0])
            else:
                Cf = Lf = float("nan")
            lsb = 0.1
            A = 2 * lsb * Lf / math.pi
            Tq = Cf * 2 * lsb / math.pi
            kpp = k_dc * kp
            pr(f"   {tagname:9s} v {v:5.1f} Kp {kp:5.0f}: T per LSB {kpp * lsb:5.1f} vs Fs {pn.Fs:5.1f} | f180 {f180:5.1f} Hz"
               f" |L| {Lf:.3f} -> LC angle {A:.4f} deg, torque {Tq:5.1f} T counts, rate {2 * math.pi * f180 * A:.2f} deg/s"
               f" {'(friction holds: no LC)' if Tq < pn.Fs else '(LC plausible)'} | friction band Fs/(Kp*{k_dc:.4f}+k)"
               f" {pn.Fs / (kpp + pn.k):.3f} deg vs torque-mode 2Fc/k {2 * pn.Fc / pn.k:.2f} deg")

    # ---------------- 11. the output lag (a cal) ----------------
    pr("\n## 11. THE OUTPUT LAG 0xC63EC/0xC63EE (cal; struck on V282 for GM -- BUILD-LINEAGE 'Struck the same day') on the"
       " angle loop: pole moved, DC held at 0.990 (ob = 0.990*16*(1024-oa)); M20 normalised to V295's lag; 6d Kd(v)")
    for oa_ in (992, 979, 960, 940):
        ob_ = int(round(0.990 * 16 * (1024 - oa_)))
        fpole = -math.log(oa_ / 1024) / (2 * math.pi * TS)
        row = []
        for v in (3.0, 12.5, 26.0):
            p = plant_at("nominal", v)
            kd = kd_sched[v]
            k3 = kp_for_fc(kd, kis, p, 3.0, oa=oa_, ob=ob_)
            r = metrics(ctl(k3, kd, kis, oa=oa_, ob=ob_), p, exact=True) if np.isfinite(k3) else None
            row.append(f"{v:g}: Kp {k3:5.0f} PM {r['pm']:5.1f} M20 {r['M20']:.2f} L20 {r['L20']:.4f}" if r else f"{v:g}: -")
        pr(f"   oa {oa_} ob {ob_} (pole {fpole:5.2f} Hz) | " + " ; ".join(row))

    json.dump(_round(js), open(OUTDIR / "out.json", "w"), indent=0,
              default=lambda o: float(o) if isinstance(o, np.floating) else (bool(o) if isinstance(o, np.bool_) else str(o)))
    _write_chunked("out", _OUT)


def _round(o):
    """5 significant digits for every float in a json tree (keeps out.json small)."""
    if isinstance(o, dict):
        return {str(k): _round(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return float(f"{float(o):.5g}") if np.isfinite(o) else str(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def _write_chunked(stem, lines, cap=240_000):
    """write lines to <stem>_partN.txt, each under `cap` bytes (the kit's 256 KB read cap)."""
    for old in OUTDIR.glob(f"{stem}_part*.txt"):
        old.unlink()
    part, buf, size = 1, [], 0
    for ln in lines:
        b = len(ln.encode("utf-8")) + 1
        if buf and size + b > cap:
            (OUTDIR / f"{stem}_part{part}.txt").write_text("\n".join(buf), encoding="utf-8")
            part, buf, size = part + 1, [], 0
        buf.append(ln)
        size += b
    if buf:
        (OUTDIR / f"{stem}_part{part}.txt").write_text("\n".join(buf), encoding="utf-8")


def bode_tables(designs):
    """Bode/margin tables for named designs: designs = {name: (Ctl-builder(v) -> Ctl or None)}.  Prints |L| / angle L /
    |T_ref| / |S| at fixed frequencies per speed, and writes a coarse FRF json for plotting (artifact input)."""
    FB = np.array([0.05, 0.1, 0.3, 0.5, 1.0, 1.6, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 13.0, 15.0, 17.0, 20.0, 25.0, 30.0])
    FP = np.unique(np.concatenate([np.logspace(-1.3, math.log10(60.0), 220), FB]))
    out = {}
    for name, mk in designs.items():
        pr(f"\n### BODE: {name}")
        pr("   f Hz  " + " ".join(f"{f:>6g}" for f in FB))
        for v in SPEEDS:
            c = mk(v)
            if c is None:
                continue
            p = plant_at("nominal", v)
            cc = replace(c, d=p.tau)
            for tag, ff in (("tab", FB), ("plot", FP)):
                P = p.frf(ff)
                L = C_fb(ff, cc) * P
                S = 1 / (1 + L)
                Tr = C_ref(ff, cc) * P * S if c.op == "angle" else L * S
                if tag == "tab":
                    pr(f"   v {v:4.1f} Kp {c.kp:5.0f} Ki {c.ki:4.0f} Kd {c.kd:3.0f}")
                    pr("     |L|    " + " ".join(f"{abs(x):6.3f}" for x in L))
                    pr("     angL   " + " ".join(f"{math.degrees(np.angle(x)):6.0f}" for x in L))
                    pr("     |Tref| " + " ".join(f"{abs(x):6.3f}" for x in Tr))
                    pr("     |S|    " + " ".join(f"{abs(x):6.3f}" for x in S))
                else:
                    out[f"{name}@{v:g}"] = dict(kp=c.kp, ki=c.ki, kd=c.kd, f=ff.tolist(), Lmag=np.abs(L).tolist(),
                                                Lph=np.degrees(np.unwrap(np.angle(L))).tolist(),
                                                Tr=np.abs(Tr).tolist(), S=np.abs(S).tolist())
    for old in OUTDIR.glob("bode*.json"):
        old.unlink()
    for i, name in enumerate(designs):      # one json per design keeps each file under the 256 KB cap
        json.dump(_round({k: v for k, v in out.items() if k.startswith(name + "@")}),
                  open(OUTDIR / f"bode_{i + 1}.json", "w"))
    _write_chunked("bode", _OUT)


# the single-schedule designs (one speed gain on E, Kd flat 16, PI corner 0.3 Hz), from the report's section 7b
E_GAIN_DESIGN = {3.0: 896, 5.0: 960, 8.0: 1028, 12.5: 2335, 19.0: 4628, 26.0: 4628, 30.0: 4628}
E_GAIN_ROBUST = {3.0: 637, 5.0: 682, 8.0: 730, 12.5: 1178, 19.0: 3070, 26.0: 3520, 30.0: 3520}


def bode_main():
    js = json.load(open(OUTDIR / "out.json"))
    kis = tuple(js["best"][0])
    kp_s = {float(k): v for k, v in js["kp_sched"].items()}
    kd_s = {float(k): v for k, v in js["kd_sched"].items()}
    kp_r = {float(k): v for k, v in js["kp_rob"].items()}
    eg = ("fI", 0.3)
    designs = {
        "E-GAIN schedule, ROBUST (Kd 16, fI 0.3) -- the recommended first dose": (lambda v: ctl(E_GAIN_ROBUST[v], 16, eg)),
        "E-GAIN schedule, nominal design (Kd 16, fI 0.3)": (lambda v: ctl(E_GAIN_DESIGN[v], 16, eg)),
        f"Kp+Kd schedule (6d, {kis_str(kis)}), nominal design": (lambda v: ctl(kp_s[v], kd_s[v], kis)),
        "E-GAIN ROBUST with a FRESH 1 kHz operand": (lambda v: ctl(E_GAIN_ROBUST[v], 16, eg, hold="fresh")),
        "FLAT Kp 1100 Kd 24 fI 0.2 (cal-only best flat)": (lambda v: ctl(1100, 24, ("fI", 0.2))),
        "V295 (reference; rate operand: the T_ref row is its complementary T)": (lambda v: V295),
    }
    bode_tables(designs)

def egain_main():
    """SECTION 7b: the SINGLE-schedule design (one speed-LERP gain g(v) on E => Kp and Ki scale together, PI corner fI
    fixed; Kd flat), its robustness across the family, the wheel modes it predicts per member (the pre-registration a
    drive can check), and the static turn-hold with the integrator deadband."""
    ref = {v: metrics(V295, plant_at("nominal", v), exact=True) for v in SPEEDS}
    pr("## 7b. SINGLE SPEED SCHEDULE (g(v) on E; Kd flat; Ki = Kp*const): per speed Kp = fc-3.0 Hz Kp capped at the"
       " safe upper edge (nominal)")
    for kd in (12, 16, 20):
        for fi in (0.25, 0.3, 0.35):
            kis = ("fI", fi)
            rows, npass = [], 0
            for v in SPEEDS:
                p = plant_at("nominal", v)
                lo, hi = safe_set(kd, kis, p, ref[v])
                k3 = kp_for_fc(kd, kis, p, 3.0)
                kp = k3 if (np.isfinite(k3) and np.isfinite(hi) and lo <= k3 <= hi) else hi
                if not np.isfinite(kp):
                    rows.append(f"{v:g}: none")
                    continue
                r = metrics(ctl(kp, kd, kis), p, exact=True)
                ok = perf_ok(r, v) and all(gates(r, ref[v]).values())
                npass += ok
                rows.append(f"{v:g}: Kp {kp:.0f} Ki {ctl(kp, kd, kis).ki:.0f} fc {r['fc']:.2f} PM {r['pm']:.0f} M20 {r['M20']:.2f}"
                            f" trk {r['trk_min']:.2f}-{r['trk_max']:.2f}" + ("" if ok else " X"))
            pr(f"   Kd {kd} fI {fi}: passes {npass}/7 | " + " ; ".join(rows))
    kd, kis = 16, ("fI", 0.3)
    CRED = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6")
    STRESS = ("J_hi2", "ms_free", "light_b")
    pr(f"\n   ROBUSTNESS of the Kd 16 fI 0.3 design and the ROBUST schedule (min of design and the CREDIBLE-family edge)")
    for v in SPEEDS:
        caps, cells = {}, []
        for m in CRED + STRESS:
            p = plant_at(m, v)
            r295 = metrics(V295, p, exact=True)
            caps[m] = safe_set(kd, kis, p, r295)[1]
            r = full(ctl(E_GAIN_DESIGN[v], kd, kis), p)
            cells.append(f"{m}:PM{r['pm']:.0f}/GM{r['gm_exact_db']:.0f}" + ("" if all(gates(r, r295).values()) else "!"))
        edge = min(caps[m] for m in CRED)
        pr(f"   v {v:4g} design Kp {E_GAIN_DESIGN[v]}: " + " ".join(cells))
        pr(f"        credible edge {edge:.0f} (binding {min(CRED, key=lambda m: caps[m])}); ROBUST Kp {E_GAIN_ROBUST[v]}"
           f" | stress edges " + " ".join(f"{m}:{caps[m]:.0f}" for m in STRESS))
    pr("\n   PRE-REGISTRATION: exact closed-loop wheel mode (least-damped pair < 8 Hz), fc and PM per member -- what the"
       " first drive's 0x14A angle should show if each member were the truth")
    for nm, S in (("ROBUST", E_GAIN_ROBUST), ("design", E_GAIN_DESIGN)):
        for v in SPEEDS:
            out = []
            for m in ("nominal", "b_lo", "J_lo", "J_hi", "b_hi", "light_b"):
                r = metrics(ctl(S[v], kd, kis), plant_at(m, v), exact=True)
                w = r["wheel"]
                out.append(f"{m}: fc {r['fc']:.2f} PM {r['pm']:.0f} wheel {w[0]:.2f}Hz z{w[1]:.2f}"
                           + ("" if r["stable"] else " UNSTABLE"))
            pr(f"   {nm:6s} v {v:4g} Kp {S[v]}: " + " | ".join(out))
    pr("\n   STATIC TURN-HOLD WITH THE I DEADBAND (DB = 0xC62E4; the I stops inside e in [-2DB, 2DB+1] counts, i.e."
       " |e| <~ (2DB+1)/10 deg): hold = 1 - min(k*theta/(Kp'+k), zone)/theta, theta = (180/pi)*L*SR*a/v^2."
       " NOTE: with g(v) applied to E BEFORE the I's E>>5, the zone in degrees shrinks as 1/g(v) (BELIEF: depends on"
       " where the cave applies g); the rows below are for a FIXED zone.")
    G = math.degrees(L_WB * SR)
    k_dc = FADE * FWD * OB / 1024 * 2 / 32 / (1 - OA / 1024) / 256 * 160
    for v in (8.0, 12.5, 19.0, 26.0, 30.0):
        k = FAM["nominal"].at(v).k
        for a in (0.5, 1.0, 2.0):
            th = G * a / v ** 2
            row = []
            for nm, S in (("design", E_GAIN_DESIGN), ("robust", E_GAIN_ROBUST)):
                eP = k * th / (k_dc * S[v] + k)
                row.append(f"{nm} P-only {1 - eP / th:.3f} " + " ".join(
                    f"DB{db} {1 - min(eP, (2 * db + 1) / 10) / th:.3f}" for db in (4, 2, 1)))
            pr(f"   v {v:4g} a {a} m/s2 theta {th:6.1f} deg | " + " | ".join(row))
    _write_chunked("egain", _OUT)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    if "--selftest" in sys.argv:
        selftest()
        (OUTDIR / "selftest.txt").write_text("\n".join(_OUT), encoding="utf-8")
    elif "--bode" in sys.argv:
        bode_main()
    elif "--egain" in sys.argv:
        egain_main()
    else:
        study()
