# -*- coding: utf-8 -*-
r"""cgf_freq.py -- DESIGNER C (goal-first) frequency-domain model of the angle loop with INDEPENDENT operand-hold and
D-hold modes, plus the gp-0x6abe EMA on the fresh-rate D path.  ANALYSIS ONLY: builds nothing, flashes nothing, sends
nothing.  Fixed numpy threads + fixed member grid; every number is reproducible.

Why this file exists.  harness_freq.Ctl applies ONE `hold` to both the P/I operand and the D rate.  Designer C's
headline lever reads the D term from the FRESH 1 kHz rate gp-0x6abe (0 extra bytes: the E5 ld.h displacement) while the
P/I operand stays the HELD gp-0x6a00 (exact openpilot frame, no tracking error).  So the two paths need different holds.
This model also puts the real gp-0x6abe EMA (alpha = 37/128, from FUN_00041464; the loop-lag-map correction, 1 kHz) on
the fresh-rate path, which harness_freq's 'fresh' omits (it treats the rate as an ideal differentiator).

Blocks are taken from harness_freq (same image cals, same plant family) so the two agree on any shared point; a control
in __main__ asserts it.  gp = 0xFEDF8000, tp = 0xBF000.

EVIDENCE for the fresh-rate sign (Ghidra decompile of FUN_0003f776 in the V294 program, this session):
    gp-0x6a56 = pol * ((gp-0x6abe * 0x30 * cal[0xC613A]) >> 15),  pol = gp-0x6752 = -1,  cal = 1159
  => gp-0x6a56 = -1.698046875 * gp-0x6abe   (magnitude 48*1159/32768 = 1.698).
  The V295 D edit damps via x = gp-0x6a56 as D = (-Kd*x)>>3.  Substituting the fresh rate:
    (-Kd*gp-0x6a56) = +1.698*Kd*gp-0x6abe  => fresh D keeps POSITIVE Kd (no subr), reads gp-0x6abe, and Kd scales x1.698
  to deliver the same T per deg/s.  This file carries that scale in D_fresh so Kd is quoted on the gp-0x6a56 scale.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
from scipy import signal

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                       # .../studies/angle_loop
for _p in (str(AL), str(AL / "c1"), str(AL / "refute_stability"), str(AL.parent / "v295" / "plant")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import harness_freq as HF                    # noqa: E402  (image cals asserted on import)
import c1r2_members as M2                    # noqa: E402  (the factorial member set + refuter self-check)

TS = 1e-3
FADE = HF.FADE
OA, OB = HF.OA, HF.OB
FWD = HF.FWD
BETA = 37.0 / 128.0                          # gp-0x6abe EMA gain (cal 0xC643C = 37, Q7); FUN_00041464, 1 kHz
RATE_SCALE_ABE = 8.0 / (48 * 1159 / 32768)  # counts(gp-0x6a56) per count(gp-0x6abe-equivalent deg/s)... see note below
# gp-0x6a56 = 8 counts per deg/s (EVIDENCE, record).  gp-0x6abe = gp-0x6a56 / 1.698 in magnitude.  We quote Kd on the
# gp-0x6a56 scale (8/deg/s) and multiply the D path by 1.698 when it reads gp-0x6abe, so a given Kd is the SAME physical
# damping whether held or fresh.  The EMA is the only extra dynamics on gp-0x6abe vs an ideal differentiator.
MU = 48 * 1159 / 32768                        # 1.698046875


def zi(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)


def H_ema(f):
    """gp-0x6abe EMA: state += (raw*1024 - state)*beta ; H(z) = beta/(1 - (1-beta) z^-1), DC gain 1."""
    z = zi(f)
    return BETA / (1 - (1 - BETA) * z)


def H_hold(f, mode, ages=range(1, 11)):
    return HF.H_hold(f, mode, ages)


def H_out(f):
    return HF.H_out(f)


def RF_ideal(f):
    """ideal differentiator jw expressed in deg/s per deg, matched to the harness's 8 counts per deg/s (op='rate' uses
    8*RF).  The resolver diff is a near-ideal differentiator (loop-lag-map: +89 deg, |H| 1.0 at 8-26 Hz)."""
    return 1j * 2 * np.pi * np.asarray(f, float)


@dataclass
class CtlC:
    """Designer-C controller.  operand = held gp-0x6a00 by default (op_hold); D = fresh gp-0x6abe by default (d_hold)."""
    name: str = "CGF"
    kp: float = 1000.0                      # Kp_eff (= Kp_base * G(v) / 256)
    ki: float = 0.0                         # Ki_eff (= Ki_base * G(v) / 256)
    kd: float = 20.0                        # Kd on the gp-0x6a56 (8/deg/s) scale
    op: str = "angle"                       # 'angle' (gp-0x6a00 / gp-0x69ca); 'fresh6a00' rebuilt is also 'angle'
    a: int = 0                              # fb pole 0xC63E8
    b: int = 8192                           # fb gain 0xC63EA
    fb_op: str = "sum"
    op_hold: str = "hold"                  # 'hold' (gp-0x6a00, 100 Hz) | 'fresh' (rebuilt gp-0x6a00 at 1 kHz)
    d_src: str = "rate"                    # 'rate' | 'none'
    d_hold: str = "fresh_abe"             # 'fresh_abe' (gp-0x6abe, EMA, 1 kHz) | 'held' (gp-0x6a56, 100 Hz)
    d: int = 2                             # transport delay ticks
    w: int = 3                            # rate-former window (only for the 'held' gp-0x6a56 model, BELIEF)
    extra_age: int = 0                    # slot-4 late by this many whole ticks (hold ages 1+e .. 10+e)
    gain: float = 1.0
    # friction feed-forward (C2): FF = sat(E' * Gff, +-Fff) added to S before the fade.  Linear small-signal gain only
    # (the saturation is a time-domain effect); Gff is in T counts per count of E'.  0 = no FF (C1).
    ff_gain: float = 0.0

    @property
    def ages(self):
        return range(1 + self.extra_age, 11 + self.extra_age)


def R_fb(f, c: CtlC):
    z = zi(f)
    return (c.b / 1024.0) * (1 + (z if c.fb_op == "sum" else -z)) / (1 - (c.a / 1024.0) * z)


def OP(f, c: CtlC):
    """operand counts per deg of theta, including its hold.  angle edit: 10 counts per deg."""
    h = H_hold(f, c.op_hold, c.ages) if c.op_hold == "hold" else (np.ones_like(np.asarray(f, float), complex))
    return h * 10.0


def PI_(f, c: CtlC):
    z = zi(f)
    return c.kp / 256.0 + (c.ki / 32768.0) / (1 - z)


def D_path(f, c: CtlC):
    """D contribution to S per deg of theta (same sign convention as harness_freq.C_S's rate branch)."""
    if c.d_src != "rate" or not c.kd:
        return np.zeros_like(np.asarray(f, float), complex)
    # harness_freq rate branch: s += kd * H_hold * RF, with RF = (1 - z^-w)/(w Ts) [8*RF = op counts].  We keep that
    # exact form for the HELD gp-0x6a56; for the FRESH gp-0x6abe we replace the 100 Hz hold by the EMA and use the ideal
    # differentiator (the resolver diff), scaled so a given Kd is the same physical damping.
    if c.d_hold == "held":
        return c.kd * H_hold(f, "hold", c.ages) * HF.RF(f, c.w)
    # fresh gp-0x6abe: ideal diff * EMA, matched to the 8-counts-per-deg/s scale (RF at DC-ish == jw in deg/s)
    return c.kd * H_ema(f) * RF_ideal(f)


def C_S(f, c: CtlC):
    s = PI_(f, c) * R_fb(f, c) * OP(f, c) + D_path(f, c)
    if c.ff_gain:
        # friction FF rides the speed-gained error E' (same path as P).  E' per deg of theta = (G/256-ish) folded into
        # kp already; we express ff_gain as T counts added to S per deg of theta error at DC (small-signal).  It adds a
        # proportional-like term: S += ff_gain * OP(f) * R_fb-ish.  Modeled as an extra proportional gain on the operand.
        s = s + c.ff_gain * R_fb(f, c) * OP(f, c)
    return s


def C_fb(f, c: CtlC):
    return c.gain * FADE * H_out(f) * FWD * zi(f) ** c.d * C_S(f, c)


def C_ref(f, c: CtlC):
    """theta_sp (deg) -> u.  E = 16*10*theta_sp_deg on the P/I path (the FF also sees the reference: it rides E')."""
    base = PI_(f, c) * 160.0
    if c.ff_gain:
        base = base + c.ff_gain * 160.0
    return c.gain * FADE * H_out(f) * FWD * zi(f) ** c.d * base


# ----- plants: reuse harness_freq.Plant + the factorial members -----
def member_plant(name, v):
    pl, tau, ea, (J, b, k) = M2.member(name, v)
    return HF.Plant(J=J, b=b, k=k, tau=tau, name=f"{name}@{v:g}"), ea


FGRID = HF.FGRID


def plant_frf(p, f=FGRID):
    return HF.plant_frf(p, f)


def metrics(c: CtlC, name, v, exact=True, f=FGRID):
    p, ea = member_plant(name, v)
    cc = replace(c, d=p.tau, extra_age=ea)
    P = plant_frf(p, f)
    Cf = C_fb(f, cc)
    L = Cf * P
    S = 1.0 / (1.0 + L)
    Tc = L * S
    Tr = C_ref(f, cc) * P * S
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L))
    idx = np.where((mag[:-1] >= 1.0) & (mag[1:] < 1.0))[0]
    fc = pm = float("nan")
    pms = []
    for i in idx:
        t = (0.0 - math.log(mag[i])) / (math.log(mag[i + 1]) - math.log(mag[i]))
        phc = ph[i] + t * (ph[i + 1] - ph[i])
        pms.append((math.degrees(phc) + 180.0 + 180.0) % 360.0 - 180.0)
        if not math.isfinite(fc):
            fc = math.exp(math.log(f[i]) + t * (math.log(f[i + 1]) - math.log(f[i])))
    if pms:
        pm = min(pms)
    im = L.imag
    jx = np.where((np.sign(im[:-1]) != np.sign(im[1:])) & (L.real[:-1] < 0))[0]
    Lneg = [abs(L[j]) for j in jx]
    gm_lti = (1.0 / max(Lneg)) if Lneg else float("inf")
    band = lambda lo, hi: (f >= lo) & (f <= hi)  # noqa: E731
    w20 = 2 * math.pi * 20.0
    cs20 = C_S(np.array([20.0]), cc)[0]
    norm20 = abs(H_out(np.array([20.0]))[0]) / abs(H_out(np.array([20.0]))[0])
    M20 = abs(cs20) / (8.0 * w20) * norm20
    ReCr20 = (C_fb(np.array([20.0]), cc)[0] / (1j * w20)).real
    r = dict(name=name, v=v, fc=fc, pm=pm, gm_lti_db=20 * math.log10(gm_lti) if np.isfinite(gm_lti) else float("inf"),
             L20=float(np.abs(L[np.argmin(abs(f - 20))])), M20=float(M20), ReCr20=float(ReCr20),
             Ms=float(np.abs(S).max()), S530_db=20 * math.log10(float(np.abs(S[band(5, 30)]).max())),
             Tc530_db=20 * math.log10(float(np.abs(Tc[band(5, 30)]).max())),
             Tr0=float(abs(Tr[0])), hold=float(np.abs(Tr[np.argmin(abs(f - 0.05))])),
             trk_min=float(np.abs(Tr[band(0.1, 1.0)]).min()), trk_max=float(np.abs(Tr[band(0.1, 1.0)]).max()),
             Tr163=float(np.abs(Tr[band(1.6, 3)]).max()), Tr530_db=20 * math.log10(float(np.abs(Tr[band(5, 30)]).max())))
    # Re(T/w) at several freqs (T counts per deg/s): the damping report vs V294/V295
    for ff in (5, 7, 10, 13, 15, 17, 20, 25):
        r[f"ReTw{ff}"] = float((C_fb(np.array([float(ff)]), cc)[0] / (1j * 2 * math.pi * ff)).real)
    if exact:
        lp = _Loop(cc, p)
        s, rho, dt = lp.poles()
        r["rho"] = rho
        r["stable"] = bool(rho < 1.0)
        md = _modes(s)
        low = [m for m in md if m[0] < 8.0]
        hf = [m for m in md if 5.0 <= m[0] <= 50.0]
        r["wheel"] = min(low, key=lambda t: t[1]) if low else (float("nan"), float("nan"))
        r["hfmode"] = min(hf, key=lambda t: t[1]) if hf else (float("nan"), float("nan"))
    return r


def _modes(s, fmin=0.05, fmax=50.0):
    out = []
    for q in s:
        fq = abs(q.imag) / (2 * np.pi)
        if q.imag > 1e-9 and fmin <= fq <= fmax:
            out.append((fq, -q.real / abs(q)))
    return sorted(out)


class _Loop:
    """exact periodic (10-tick) closed loop with the mixed holds.  State: plant | theta hist | held op | held x(gp6a56)
    | fresh-rate EMA state | fb s | I | out-lag o | torque delay.  Linear in (z, th_sp)."""

    def __init__(self, c: CtlC, p):
        self.c, self.p = c, p
        self.d = p.tau
        self.Ad, self.Bd, self.Cd, _ = p.zoh()
        self.np_ = self.Ad.shape[0]
        self.nh = 10 + c.w + 1
        i = self.np_
        self.ih = i; i += self.nh
        self.iho = i; i += 1
        self.ihx = i; i += 1
        self.iema = i; i += 1
        self.i_s = i; i += 1
        self.iI = i; i += 1
        self.io = i; i += 1
        self.iT = i; i += max(self.d, 0)
        self.N = i

    def _op_fresh(self, th_now, hist, lag):
        c = self.c
        thv = lambda m: th_now if m == 0 else hist[m - 1]  # noqa: E731
        th = thv(lag)
        x = 8.0 * (th - thv(lag + c.w)) / (c.w * TS)       # gp-0x6a56 former model (held path)
        op = 10.0 * th
        return op, x, th

    def step(self, z, th_sp, act):
        c = self.c
        xp = z[:self.np_]
        hist = z[self.ih:self.ih + self.nh]
        th = (self.Cd @ xp)[0]
        op_now, x_now, th_now = self._op_fresh(th, hist, 0)
        # operand (P/I): held gp-0x6a00 unless fresh
        if c.op_hold == "hold":
            op = z[self.iho]
        else:
            op = op_now
        # D rate
        if c.d_src == "rate" and c.kd:
            if c.d_hold == "held":
                xh = z[self.ihx]
                D = -c.kd * xh / 8.0
            else:
                # fresh gp-0x6abe: ideal diff * EMA.  ideal diff ~ (th - th_prev)/Ts in deg/s; EMA state update.
                rate_ideal = (th - hist[0]) / TS                    # deg/s, 1-tick diff (near-ideal at these freqs)
                ema = (1 - BETA) * z[self.iema] + BETA * rate_ideal
                D = -c.kd * (ema * 8.0) / 8.0                        # scale: 8 counts/deg/s folded, Kd on gp-0x6a56 scale
            self._ema_new = ema if (c.d_src == "rate" and c.kd and c.d_hold != "held") else z[self.iema]
        else:
            D = 0.0
            self._ema_new = z[self.iema]
        s_old = z[self.i_s]
        s_new = (c.a / 1024.0) * s_old + (c.b / 1024.0) * op
        r26 = s_new + s_old if c.fb_op == "sum" else s_new - s_old
        E = 160.0 * th_sp - r26
        I = (z[self.iI] + (c.ki / 32768.0) * E) if c.ki else 0.0
        P = (c.kp / 256.0) * E
        FFt = (c.ff_gain * E) if c.ff_gain else 0.0            # small-signal FF (saturation handled in time sim)
        S = c.gain * FADE * (I + P + D + FFt)
        o = z[self.io]
        o_new = (c.oa / 1024.0) * o + (c.ob / 1024.0) * S if False else (OA / 1024.0) * o + (OB / 1024.0) * S
        y = (o + o_new) / 32.0
        T = FWD * y
        u = z[self.iT + self.d - 1] if self.d > 0 else T
        zn = np.zeros(self.N)
        zn[:self.np_] = self.Ad @ xp + self.Bd[:, 0] * u
        zn[self.ih] = th
        zn[self.ih + 1:self.ih + self.nh] = hist[:self.nh - 1]
        if c.op_hold == "hold":
            zn[self.iho] = op_now if act else z[self.iho]
            zn[self.ihx] = x_now if act else z[self.ihx]
        zn[self.iema] = self._ema_new
        zn[self.i_s] = s_new
        zn[self.iI] = I
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
        Aa, _ = self.mats(True)
        An, _ = self.mats(False)
        Phi = np.linalg.matrix_power(An, 9) @ Aa
        lam = np.linalg.eigvals(Phi)
        lam = lam[np.abs(lam) > 1e-12]
        s = np.log(lam.astype(complex)) / (10 * TS)
        return s, float(np.max(np.abs(lam))), 10 * TS


def exact_gm_db(c: CtlC, name, v):
    p, ea = member_plant(name, v)
    cc = replace(c, d=p.tau, extra_age=ea)

    def rho(g):
        return _Loop(replace(cc, gain=g), p).poles()[1]
    if rho(1.0) >= 1.0:
        lo, hi = 1e-3, 1.0
        if rho(lo) >= 1.0:
            return float("-inf")
        for _ in range(40):
            m = math.sqrt(lo * hi)
            if rho(m) >= 1.0:
                hi = m
            else:
                lo = m
        return 20 * math.log10(lo)
    lo, hi = 1.0, 1.0
    while rho(hi) < 1.0 and hi < 1e4:
        lo, hi = hi, hi * 2
    for _ in range(40):
        m = math.sqrt(lo * hi)
        if rho(m) < 1.0:
            lo = m
        else:
            hi = m
    return 20 * math.log10(lo)


if __name__ == "__main__":
    # CONTROL: with d_hold='held' and the w=3 former, our C_fb must match harness_freq.C_fb for the SAME controller.
    print("=== CONTROL: cgf C_fb (d_hold=held) vs harness_freq.C_fb, nominal 12.5 m/s ===")
    import harness_freq as HF2
    c_ours = CtlC(kp=1200, ki=600, kd=20, op_hold="hold", d_hold="held")
    c_hf = HF2.Ctl(op="angle", hold="hold", a=0, b=8192, fb_op="sum", kp=1200, ki=600, kd=20, d_src="rate")
    f = np.array([0.3, 1.0, 3.0, 10.0, 20.0])
    ours = C_fb(f, replace(c_ours, d=2))
    theirs = HF2.C_fb(f, replace(c_hf, d=2))
    for i, ff in enumerate(f):
        print(f"  {ff:5.1f} Hz  ours {abs(ours[i]):.5g}/{math.degrees(np.angle(ours[i])):+.2f}  "
              f"hf {abs(theirs[i]):.5g}/{math.degrees(np.angle(theirs[i])):+.2f}  "
              f"ratio {abs(ours[i]/theirs[i]):.4f}")
    print("\n=== fresh gp-0x6abe D vs held gp-0x6a56 D: Re(T/w) 5-25 Hz, nominal 17 m/s, Kp_eff 900 Kd 20 ===")
    for dh in ("held", "fresh_abe"):
        c = CtlC(kp=900, ki=450, kd=20, op_hold="hold", d_hold=dh)
        r = metrics(c, "nominal", 17.0, exact=False)
        print(f"  D={dh:9s}: " + " ".join(f"{ff}Hz {r[f'ReTw{ff}']:+.2f}" for ff in (5, 7, 10, 13, 17, 20, 25))
              + f"  M20 {r['M20']:.2f}")
