# -*- coding: utf-8 -*-
"""REFUTER (stability lens), 2026-09-30.  INDEPENDENT linear model of the C0 edited lane + the r71b plant family.
Written from the lane bytes as documented in lane_mirror_v295.lane_tick (x_src angle, fb_op sum, sp 69ae, d_src rate)
and the C0 cave listing (E' = E*G(v)>>8 at 0x29D76).  Does NOT import harness_freq / harness_time / rec_*.
Only the PLANT PARAMETERS (data) are taken from v294_plant.family().

Two analyses:
  (1) LTI fundamental FRF of the loop (100 Hz hold -> (1/10) sum_{a=1..10} z^-a) -> fc, PM, GM, Ms.
  (2) EXACT 10-tick periodic state space (slot-4 hold updates on n%10 == 4 AFTER the PID reads) -> monodromy
      spectral radius (stability), least-damped closed-loop poles, exact gain margin by bisection, delay margin.
Integer floors, clamps, quantisation and friction are NOT in this file (linear only).
"""
import sys, math, json, os
import numpy as np
import scipy.linalg as sla

sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/plant")
import v294_plant as VP

TS = 1e-3
OA, OB = 992, 507             # 0xC63EC / 0xC63EE output lag (V295 values, unchanged in C0)
FWD = 5346 / 32768            # 0xC6CD0 forward gain magnitude (pol -1 -> u = -T is + along the error)
FADE = 254 / 256              # hands-off fade ((255*255)&0xFFFF)>>8
KP_BASE, KI, KD = 450, 199, 16
HOLD_PHASE = 4                # slot 4 activates on c % 10 == 4 (TRACE angle §1.1)

# ---------------- the cave's speed gain, integer, exactly as listed in the design §1.2 ----------------
X = [691, 1152, 1843, 2880, 4378, 5990, 0xFFFF]
GK = [256, 284, 341, 569, 1422, 1707, 1707]
SL = [249, 338, 901, 2332, 724, 0, 0]


def G_of_v(vmps):
    vc = int(vmps * 3.6 * 64)                 # gp-0x6a5e, 64 counts per km/h
    if vc <= X[0]:
        return GK[0]
    i = 0
    while not (vc <= X[i + 1]):
        i += 1
    return GK[i] + (((vc - X[i]) * SL[i]) >> 12)


# ---------------- plants ----------------
def rigid(J, b, k):
    A = np.array([[0.0, 1.0], [-k / J, -b / J]])
    B = np.array([[0.0], [1.0 / J]])
    Ct = np.array([[1.0, 0.0]]); Cw = np.array([[0.0, 1.0]])
    return A, B, Ct, Cw


def two_mass(J, b, k, r2, fz, zw, J_arm_ratio=0.0, zeta_arm=0.0, k_arm_ratio=0.0):
    """motor side Jm=(1-r2)J carries u, b, k (tires/rack act on the motor side); torsion bar k_tb to the wheel side
    Jw=r2*J (+ arms J_arm = ratio*Jw).  fz = hands-off wheel-on-bar frequency (BELIEF 13 Hz, ident §4).
    zw = hands-off wheel-side damping ratio about the bar.  Arms: extra damping zeta_arm (about the bar mode with arms)
    and optional ground stiffness k_arm = k_arm_ratio*k_tb.  Sensor = MOTOR side (collocated: gp-0x6a00 from gp-0x6cc4)."""
    Jm, Jw = (1 - r2) * J, r2 * J
    ktb = Jw * (2 * math.pi * fz) ** 2
    btb = 2 * zw * math.sqrt(ktb * Jw)
    Jw2 = Jw * (1 + J_arm_ratio)
    barm = 2 * zeta_arm * math.sqrt(ktb * Jw2)
    karm = k_arm_ratio * ktb
    # states th_m, w_m, th_w, w_w
    A = np.array([[0, 1, 0, 0],
                  [-(k + ktb) / Jm, -(b + btb) / Jm, ktb / Jm, btb / Jm],
                  [0, 0, 0, 1],
                  [ktb / Jw2, btb / Jw2, -(ktb + karm) / Jw2, -(btb + barm) / Jw2]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    Ct = np.array([[1.0, 0, 0, 0]]); Cw = np.array([[0, 1.0, 0, 0]])
    return A, B, Ct, Cw


def c2d(A, B):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1)); M[:n, :n] = A * TS; M[:n, n:] = B * TS
    E = sla.expm(M)
    return E[:n, :n], E[:n, n:]


# ---------------- controller description ----------------
class Ctl:
    def __init__(self, v, kp=KP_BASE, ki=KI, kd=KD, d=2, extra_age=0, rate_pole_hz=None, G=None, fade=FADE):
        self.v = v
        self.G = G_of_v(v) if G is None else G
        self.kp, self.ki, self.kd, self.d = kp, ki, kd, d
        self.extra_age = extra_age            # slot-4 late by this many whole ticks (hold ages 1+e .. 10+e)
        self.rate_pole_hz = rate_pole_hz      # optional 1st-order filter on the rate former (BELIEF probe)
        self.fade = fade


def frf(ctl, plant, f):
    """LTI fundamental of the loop, L(e^{jwT}) for frequencies f (Hz)."""
    A, B, Ct, Cw = plant
    Ad, Bd = c2d(A, B)
    z = np.exp(1j * 2 * np.pi * np.asarray(f) * TS)
    n = Ad.shape[0]
    Pt = np.array([(Ct @ np.linalg.solve(zz * np.eye(n) - Ad, Bd))[0, 0] for zz in z])
    Pw = np.array([(Cw @ np.linalg.solve(zz * np.eye(n) - Ad, Bd))[0, 0] for zz in z])
    zi = 1 / z
    hold = sum(zi ** (a + ctl.extra_age) for a in range(1, 11)) / 10
    Hout = (OB / 1024) * (1 + zi) / (32 * (1 - (OA / 1024) * zi))
    K = ctl.fade * FWD * Hout * zi ** ctl.d
    g = ctl.G / 256
    PI = ctl.kp / 256 + (ctl.ki / 32768) / (1 - zi)
    Ctheta = g * PI * 80 * (1 + zi) * hold
    rf = 1.0
    if ctl.rate_pole_hz:
        a = math.exp(-2 * math.pi * ctl.rate_pole_hz * TS)
        rf = (1 - a) / (1 - a * zi)
    Comega = ctl.kd * hold * rf
    L = K * (Ctheta * Pt + Comega * Pw)
    return L, K * Ctheta, K * Comega, Pt, Pw


def margins(ctl, plant, fmin=0.02, fmax=499.0, npts=6000):
    f = np.logspace(math.log10(fmin), math.log10(fmax), npts)
    L = frf(ctl, plant, f)[0]
    mag = np.abs(L); ph = np.unwrap(np.angle(L)) * 180 / np.pi
    # crossovers
    pms, fcs = [], []
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            p = ph[i] + t * (ph[i + 1] - ph[i])
            pm = ((p + 180) + 180) % 360 - 180
            pms.append(pm); fcs.append(f[i] + t * (f[i + 1] - f[i]))
    gms = []
    for i in range(len(f) - 1):
        a0 = ((ph[i] + 180) % 360) - 180; a1 = ((ph[i + 1] + 180) % 360) - 180
        # crossing of -180 (mod 360)
        w0 = (ph[i] + 180) / 360; w1 = (ph[i + 1] + 180) / 360
        if math.floor(w0) != math.floor(w1):
            gms.append((f[i], -20 * math.log10(max(mag[i], 1e-12))))
    S = 1 / (1 + L)
    band = (f >= 5) & (f <= 30)
    pm = min(pms) if pms else float('nan')
    fc = fcs[int(np.argmin(pms))] if pms else float('nan')
    gm = min([g for (_, g) in gms if g > 0], default=float('inf'))
    return dict(pm=pm, fc=fc, gm=gm, Ms=float(np.max(np.abs(S))), S530=20 * math.log10(float(np.max(np.abs(S[band])))),
                fcs=fcs, pms=pms, f=f, L=L)


# ---------------- exact periodic state space ----------------
def phase_mats(ctl, plant, gain=1.0):
    """state: [xp (np), ubuf (d), o_prev, s_prev, I, th_h, w_h, (rf)] ; returns list of 10 A matrices."""
    A, B, Ct, Cw = plant
    Ad, Bd = c2d(A, B)
    npl = Ad.shape[0]
    d = ctl.d
    hasrf = bool(ctl.rate_pole_hz)
    # indices
    ip = 0; iu = npl; io = npl + d; isp = io + 1; iI = isp + 1; ith = iI + 1; iw = ith + 1; irf = iw + 1
    # extra age: chain of 'extra_age' delay registers between the slot-4 sample and th_h/w_h
    ea = ctl.extra_age
    iea_t = irf + (1 if hasrf else 0)
    iea_w = iea_t + ea
    N = iea_w + ea
    g = ctl.G / 256
    a_rf = math.exp(-2 * math.pi * ctl.rate_pole_hz * TS) if hasrf else 0.0
    mats = []
    for p in range(10):
        M = np.zeros((N, N))
        # lane outputs as linear functions of the state (row vectors)
        def row(): return np.zeros(N)
        th_h = row(); th_h[ith] = 1
        s_prev = row(); s_prev[isp] = 1
        E = -80 * (th_h + s_prev)              # theta_sp = 0 for the homogeneous system
        Ep = g * E
        I_new = row(); I_new[iI] = 1; I_new = I_new + Ep * ctl.ki / 32768
        P = Ep * ctl.kp / 256
        w_used = row()
        if hasrf:
            # rf_new = a*rf + (1-a)*w_h ; D uses rf_new
            w_used[irf] = a_rf; w_used[iw] += (1 - a_rf)
        else:
            w_used[iw] = 1
        D = -ctl.kd * w_used
        S = P + I_new + D
        Sf = ctl.fade * S
        o_new = row(); o_new[io] = OA / 1024; o_new = o_new + (OB / 1024) * Sf
        o_prev = row(); o_prev[io] = 1
        y = (o_prev + o_new) / 32
        ucmd = gain * FWD * y
        # plant input this tick
        if d == 0:
            uin = ucmd
        else:
            uin = row(); uin[iu + d - 1] = 1          # oldest in the buffer
        # plant update
        M[ip:ip + npl, ip:ip + npl] = Ad
        M[ip:ip + npl, :] += np.outer(Bd[:, 0], uin)
        # buffer shift: ubuf[0] <- ucmd, ubuf[i] <- ubuf[i-1]
        if d > 0:
            M[iu, :] = ucmd
            for i in range(1, d):
                M[iu + i, iu + i - 1] = 1
        M[io, :] = o_new
        M[isp, :] = th_h
        M[iI, :] = I_new
        if hasrf:
            M[irf, :] = w_used
        # hold registers
        th_now = np.zeros(N); th_now[ip:ip + npl] = Ct[0]
        w_now = np.zeros(N); w_now[ip:ip + npl] = Cw[0]
        if ea > 0:
            # delay chain of the sampled plant outputs (the slot-4 task runs ea ticks late)
            M[iea_t, :] = th_now
            M[iea_w, :] = w_now
            for i in range(1, ea):
                M[iea_t + i, iea_t + i - 1] = 1
                M[iea_w + i, iea_w + i - 1] = 1
            src_t = np.zeros(N); src_t[iea_t + ea - 1] = 1
            src_w = np.zeros(N); src_w[iea_w + ea - 1] = 1
        else:
            src_t, src_w = th_now, w_now
        if p == HOLD_PHASE:
            M[ith, :] = src_t
            M[iw, :] = src_w
        else:
            M[ith, ith] = 1
            M[iw, iw] = 1
        mats.append(M)
    return mats


def monodromy(ctl, plant, gain=1.0):
    mats = phase_mats(ctl, plant, gain)
    Phi = np.eye(mats[0].shape[0])
    for M in mats:
        Phi = M @ Phi
    return Phi


def exact(ctl, plant):
    Phi = monodromy(ctl, plant)
    lam = np.linalg.eigvals(Phi)
    rho = float(np.max(np.abs(lam)))
    poles = []
    for l in lam:
        if abs(l) < 1e-9:
            continue
        s = np.log(l) / (10 * TS)
        fhz = abs(s.imag) / (2 * np.pi)
        if fhz < 0.3:
            continue
        z = -s.real / abs(s)
        poles.append((fhz, z))
    poles.sort(key=lambda t: t[1])
    return rho, poles


def exact_gm(ctl, plant):
    lo, hi = 1e-3, 1.0
    if max(abs(np.linalg.eigvals(monodromy(ctl, plant, 1.0)))) >= 1:
        # unstable at nominal: find the gain reduction that stabilises
        hi = 1.0; lo = 1e-3
        for _ in range(60):
            m = math.sqrt(lo * hi)
            if max(abs(np.linalg.eigvals(monodromy(ctl, plant, m)))) >= 1:
                hi = m
            else:
                lo = m
        return 20 * math.log10(lo)
    lo, hi = 1.0, 1.0
    while max(abs(np.linalg.eigvals(monodromy(ctl, plant, hi)))) < 1 and hi < 1e4:
        lo, hi = hi, hi * 2
    for _ in range(50):
        m = math.sqrt(lo * hi)
        if max(abs(np.linalg.eigvals(monodromy(ctl, plant, m)))) < 1:
            lo = m
        else:
            hi = m
    return 20 * math.log10(lo)


def delay_margin_ticks(ctl, plant, maxd=80):
    import copy
    base = ctl.d
    for extra in range(0, maxd):
        c2 = copy.copy(ctl); c2.d = base + extra
        rho = max(abs(np.linalg.eigvals(monodromy(c2, plant))))
        if rho >= 1:
            return extra
    return maxd


def member_at(fam, name, v, bscale=1.0, Jover=None, tau=None):
    m = fam[name]
    p = m.at(v)
    J = p.J if Jover is None else Jover
    return p, rigid(J, p.b * bscale, p.k), (p.tau_ms if tau is None else tau)


if __name__ == "__main__":
    fam = VP.family()
    # self-check 1: LTI-FRF Nyquist stability vs exact monodromy on a few points
    for v in (3, 12.5, 26):
        p, pl, tau = member_at(fam, "nominal", v)
        c = Ctl(v, d=tau)
        mg = margins(c, pl)
        rho, poles = exact(c, pl)
        print(f"v {v:5.1f} G {c.G} Kp_eff {450*c.G/256:.0f} | fc {mg['fc']:.2f} PM {mg['pm']:.1f} GM(lti) {mg['gm']:.1f} "
              f"| rho {rho:.4f} least-damped {poles[:2]}")
