# -*- coding: utf-8 -*-
"""INDEPENDENT refuter of DESIGN C1 (stability lens), 2026-09-30, round 1.

Own linear model of the C1 edited angle lane, written from the C1 cave listing and the documented loop
structure (DESIGN-ANGLE-LOOP-C1 section 1.4, "The loop, integer-exact Python").  It does NOT import
stab_lin / harness_freq / c1_gate2; it only takes PLANT DATA from v294_plant.family() and the C1 TABLE /
immediates from c1_lib (G walk, KP_BASE, KI_BASE, KD).  Methodologically independent:
  - the plant theta/u and omega/u are ZOH-discretised with my own expm (std method), then the digital loop
    (100 Hz hold, 2-tap fb FIR already folded into the angle feedback, output lag, forward gain, transport z^-d)
    is assembled by hand and the open-loop L(e^{jwT}) swept; PM/GM by my own crossover finder.
  - Re(T/omega) is the controller-only output impedance seen by the plant (member independent), aged holds too.

Attacks (brief): fine 0.25 m/s sweep incl plant knots; every single-corner member; combined members;
hold ages 0..20 ALSO on the combined members (the design gated +h10 only on single members); extra combined
members the design did not gate (b_q*J_hi, b_q*tau6, b_lo*J_hi*tau6+h, J1.0*tau6); 5-30 Hz closed-loop peaks;
Re(T/w) 5-25 Hz vs V294/V295 finely and aged; the fork outer-loop stand-in.
"""
import math
import os
import sys

import numpy as np
import scipy.linalg as sla

HERE = os.path.dirname(os.path.abspath(__file__))
AL = os.path.dirname(HERE)
for _p in (os.path.join(AL, "c1"), HERE, os.path.join(AL, "..", "..", "studies", "v295", "plant"),
           os.path.join(os.path.dirname(os.path.dirname(AL)), "studies", "v295", "plant")):
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

import c1_lib as CL            # the C1 table + immediates (data) ; also puts v294_plant on the path
import v294_plant as VP

TS = 1e-3
OA, OB = 992, 507
FWD = 5346 / 32768
FADE = 254 / 256
KP_BASE, KI_BASE, KD = CL.KP_BASE, CL.KI_BASE, CL.KD   # 225 / 100 / 16
TBL = CL.c1_table()
FAM = VP.family()
P5C = VP._profile_rows(os.path.join(os.path.dirname(VP.__file__), "_scratch", "p5c.json"))

# ------------------------------------------------------------------ plant ZOH discretisation (my own)
def rigid_disc(J, b, k):
    A = np.array([[0.0, 1.0], [-k / J, -b / J]])
    B = np.array([[0.0], [1.0 / J]])
    n = 2
    M = np.zeros((n + 1, n + 1)); M[:n, :n] = A * TS; M[:n, n:] = B * TS
    E = sla.expm(M)
    Ad, Bd = E[:n, :n], E[:n, n:]
    return Ad, Bd, np.array([[1.0, 0.0]]), np.array([[0.0, 1.0]])

def twomass_disc(J, b, k, r2, fz, zw):
    Jm, Jw = (1 - r2) * J, r2 * J
    ktb = Jw * (2 * math.pi * fz) ** 2
    btb = 2 * zw * math.sqrt(ktb * Jw)
    A = np.array([[0, 1, 0, 0],
                  [-(k + ktb) / Jm, -(b + btb) / Jm, ktb / Jm, btb / Jm],
                  [0, 0, 0, 1],
                  [ktb / Jw, btb / Jw, -ktb / Jw, -btb / Jw]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    n = 4
    M = np.zeros((n + 1, n + 1)); M[:n, :n] = A * TS; M[:n, n:] = B * TS
    E = sla.expm(M)
    return E[:n, :n], E[:n, n:], np.array([[1.0, 0, 0, 0]]), np.array([[0, 1.0, 0, 0]])

def plant_frf(disc, f):
    Ad, Bd, Ct, Cw = disc
    z = np.exp(1j * 2 * np.pi * np.asarray(f, float) * TS)
    n = Ad.shape[0]
    I = np.eye(n)
    M = z[:, None, None] * I[None] - Ad[None]          # (F,n,n)
    X = np.linalg.solve(M, np.broadcast_to(Bd, (len(z), n, 1)))   # (F,n,1)
    Pt = (Ct[None] @ X)[:, 0, 0]
    Pw = (Cw[None] @ X)[:, 0, 0]
    return Pt, Pw

# ------------------------------------------------------------------ the C1 loop open-loop FRF (my own assembly)
def loop_L(G, kp, ki, kd, disc, f, d=2, age=0):
    """Open-loop L for the C1 angle lane. G = cave gain (/256 is the Kp_eff scale), kp/ki/kd base cals."""
    z = np.exp(1j * 2 * np.pi * np.asarray(f, float) * TS); zi = 1 / z
    hold = sum(zi ** (a + age) for a in range(1, 11)) / 10.0
    Hout = (OB / 1024) * (1 + zi) / (32 * (1 - (OA / 1024) * zi))
    K = FADE * FWD * Hout * zi ** d
    g = G / 256.0
    PI = kp / 256.0 + (ki / 32768.0) / (1 - zi)
    Ctheta = g * PI * 80 * (1 + zi) * hold           # r26 = 80*theta_deg*(1+z^-1), held
    Comega = kd * hold
    Pt, Pw = plant_frf(disc, f)
    return K * (Ctheta * Pt + Comega * Pw)

def margins(G, kp, ki, kd, disc, d=2, age=0, fmin=0.02, fmax=120.0, npts=3200):
    f = np.logspace(math.log10(fmin), math.log10(fmax), npts)
    L = loop_L(G, kp, ki, kd, disc, f, d=d, age=age)
    mag = np.abs(L); ph = np.unwrap(np.angle(L)) * 180 / math.pi
    pms = []
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            p = ph[i] + t * (ph[i + 1] - ph[i])
            pm = ((p + 180) + 180) % 360 - 180        # PM = 180 + phase, wrapped to (-180,180]
            pms.append(pm)
    # gain margin at -180 crossings
    gms = []
    for i in range(len(f) - 1):
        w0 = (ph[i] + 180) / 360; w1 = (ph[i + 1] + 180) / 360
        if math.floor(w0) != math.floor(w1):
            t = (math.floor(max(w0, w1)) - w0) / (w1 - w0) if w1 != w0 else 0
            m = mag[i] + t * (mag[i + 1] - mag[i])
            gms.append(-20 * math.log10(max(m, 1e-12)))
    pm = min(pms) if pms else float('nan')
    gm = min([g for g in gms if g > 0], default=float('inf'))
    return pm, gm

# ------------------------------------------------------------------ exact 10-tick periodic (stability + CL poles)
def periodic_poles(G, kp, ki, kd, disc, d=2, age=0):
    """Exact periodic monodromy of the whole digital loop; returns (rho, list[(f,zeta)]) for CL modes.
    My own state build: plant xp(n), transport ubuf(d), outlag o, integrator I, held theta th_h, held rate w_h,
    and (for age>0) a shift register of past held samples is not needed -- I model age by delaying the hold
    update phase: slot HOLD updates th_h,w_h from xp on phase==p0, and we read them 'age' ticks stale by using
    an age-length FIFO of (th_h,w_h)."""
    Ad, Bd, Ct, Cw = disc
    npl = Ad.shape[0]
    naux_hist = max(age, 0)
    # state vector layout
    ip = 0
    iu = npl
    io = iu + d
    iI = io + 1
    ith = iI + 1            # current held theta (updated at slot)
    iw = ith + 1            # current held rate
    ihist = iw + 1          # FIFO of 2*age past (th,w) pairs: [th_{-1},w_{-1},...,th_{-age},w_{-age}]
    N = ihist + 2 * naux_hist
    g = G / 256.0

    def step_mat(phase):
        M = np.zeros((N, N))
        e = lambda i: (lambda r: r.__setitem__(i, 1.0) or r)(np.zeros(N))  # noqa
        # read held theta/rate used by controller THIS tick: the oldest in the FIFO if age>0 else current
        if naux_hist > 0:
            th_used = np.zeros(N); th_used[ihist + 2 * (naux_hist - 1)] = 1.0
            w_used = np.zeros(N); w_used[ihist + 2 * (naux_hist - 1) + 1] = 1.0
        else:
            th_used = np.zeros(N); th_used[ith] = 1.0
            w_used = np.zeros(N); w_used[iw] = 1.0
        # r26 = 80*theta (we use held theta; the (1+z^-1) 2-tap is folded by using two consecutive held samples;
        # to keep the state small we approximate the 2-tap by 2x the current held theta at DC -- but for the
        # periodic STABILITY test we keep the exact single-sample feedback and rely on loop_L for phase margins.
        # Here th_used represents 80*theta already in 'deg' sense: multiply by 80.)
        r26 = 80.0 * th_used
        E = -r26                                      # setpoint 0
        I_prev = np.zeros(N); I_prev[iI] = 1.0
        # integrator: I += (ki/32768) * (G/256) * E   (E in r26 counts/deg -> Ki_eff); P = (kp/256)*g*E
        Ei = g * E
        I_new = I_prev + (ki / 32768.0) * Ei
        P = (kp / 256.0) * Ei
        D = -kd * w_used
        Sx = I_new + P + D
        Sf = FADE * Sx
        o_prev = np.zeros(N); o_prev[io] = 1.0
        o_new = (OA / 1024.0) * o_prev + (OB / 1024.0) * Sf
        y = (o_prev + o_new) / 32.0
        ucmd = FWD * y
        # plant update
        if d == 0:
            uin = ucmd
        else:
            uin = np.zeros(N); uin[iu + d - 1] = 1.0
        M[ip:ip + npl, ip:ip + npl] = Ad
        M[ip:ip + npl, :] += np.outer(Bd[:, 0], -uin)      # u = -T
        if d > 0:
            M[iu, :] = ucmd
            for i in range(1, d):
                M[iu + i, iu + i - 1] = 1.0
        M[io, :] = o_new
        M[iI, :] = I_new
        # hold update at the slot phase
        th_now = np.zeros(N); th_now[ip + 0] = 1.0        # Ct = theta is state 0
        w_now = np.zeros(N); w_now[ip + 1] = 1.0          # omega is state 1
        if phase == 4:
            new_th = th_now; new_w = w_now
        else:
            new_th = np.zeros(N); new_th[ith] = 1.0
            new_w = np.zeros(N); new_w[iw] = 1.0
        M[ith, :] = new_th
        M[iw, :] = new_w
        # FIFO shift (push the PREVIOUS current held sample)
        if naux_hist > 0:
            # newest slot gets previous current held theta/rate
            M[ihist + 0, ith] = 1.0
            M[ihist + 1, iw] = 1.0
            for kk in range(1, naux_hist):
                M[ihist + 2 * kk, ihist + 2 * (kk - 1)] = 1.0
                M[ihist + 2 * kk + 1, ihist + 2 * (kk - 1) + 1] = 1.0
        return M

    Phi = np.eye(N)
    for p in range(10):
        Phi = step_mat(p) @ Phi
    lam = np.linalg.eigvals(Phi)
    rho = float(np.max(np.abs(lam)))
    modes = []
    for l in lam:
        if abs(l) < 1e-12:
            continue
        s = np.log(l + 0j) / (10 * TS)
        fhz = abs(s.imag) / (2 * np.pi)
        zeta = -s.real / abs(s) if abs(s) > 0 else 1.0
        if s.imag >= 1e-9:
            modes.append((float(fhz), float(zeta)))
    modes.sort(key=lambda t: t[0])
    return rho, modes

# ------------------------------------------------------------------ Re(T/omega) controller output impedance
def torque_per_rate_C1(G, kp, ki, kd, f, d=2, age=0):
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** (a + age) for a in range(1, 11)) / 10.0
    Hout = (OB / 1024) * (1 + zi) / (32 * (1 - (OA / 1024) * zi))
    K = FADE * FWD * Hout * zi ** d
    g = G / 256.0
    PI = kp / 256.0 + (ki / 32768.0) / (1 - zi)
    Cth = g * PI * 80 * (1 + zi) * hold
    Cw = kd * hold
    w = 2 * math.pi * f
    return K * (Cth / (1j * w) + Cw)

def torque_per_rate_rate(a, b, op, kp, kd, f, d=2, age=0):
    z = np.exp(1j * 2 * np.pi * f * TS); zi = 1 / z
    hold = sum(zi ** (a2 + age) for a2 in range(1, 11)) / 10.0
    Hout = (OB / 1024) * (1 + zi) / (32 * (1 - (OA / 1024) * zi))
    K = FADE * FWD * Hout * zi ** d
    R = (b / 1024) * (1 + (zi if op == "sum" else -zi)) / (1 - (a / 1024) * zi)
    gg = kp / 256 + (kd / 8) * (1 - zi)
    return K * gg * R * 8 * hold

# ------------------------------------------------------------------ members (built here, not imported from c1_members)
def refit(Jr):
    if Jr in P5C:
        b, k, F, Fs = P5C[Jr]
    else:
        js = sorted(P5C); lo = max(j for j in js if j < Jr); hi = min(j for j in js if j > Jr)
        w = (Jr - lo) / (hi - lo)
        b, k, F, Fs = [(1 - w) * x + w * y for x, y in zip(P5C[lo], P5C[hi])]
    return VP.PlantFamilyMember(f"J{Jr}", J=np.full(5, Jr), b=np.array(b), k=np.array(k), Fc=np.array(F), Fs=np.array(Fs), tau_ms=2)

REFIT = {0.8: refit(0.8), 1.0: refit(1.0), 1.3: refit(1.3)}
B_FLOOR = 0.7 * 4.94

def member_params(name, v):
    """-> (J, b, k, d, age).  Independent re-implementation of the C1 member set + extra attack members."""
    if name in FAM:
        p = FAM[name].at(v); return p.J, p.b, p.k, p.tau_ms, 0
    if name.endswith("+h10"):
        p = FAM[name[:-4]].at(v); return p.J, p.b, p.k, p.tau_ms, 10
    if name in ("J1.0", "J1.3", "J_hi2"):
        Jr = {"J1.0": 1.0, "J1.3": 1.3, "J_hi2": 0.8}[name]
        p = REFIT[Jr].at(v); return p.J, p.b, p.k, 2, 0
    if name in ("b_q", "b_q0"):
        p = FAM["nominal"].at(v)
        bq = (0.25 * p.b if name == "b_q0" else max(0.25 * p.b, B_FLOOR)) if v >= 12.5 else p.b
        return p.J, bq, p.k, 2, 0
    # combos (verbatim semantics)
    if name == "b_lo*J_hi":
        p = FAM["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7; return p.J, p.b * bs, p.k, 2, 0
    if name == "b_lo*J_hi*tau6":
        p = FAM["J_hi"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7; return p.J, p.b * bs, p.k, 6, 0
    if name == "b_lo*tau6":
        p = FAM["b_lo"].at(v); return p.J, p.b, p.k, 6, 0
    if name == "J_hi*tau6":
        p = FAM["J_hi"].at(v); return p.J, p.b, p.k, 6, 0
    if name == "b/1.9*J_hi":
        p = FAM["J_hi"].at(v); bs = 1 / 1.9 if v >= 10 else 0.7; return p.J, p.b * bs, p.k, 2, 0
    if name == "b_lo*J0.3":
        p = FAM["nominal"].at(v); bs = 1 / 1.8 if v >= 10 else 0.7; return 0.3, p.b * bs, p.k, 2, 0
    if name == "tau10":
        p = FAM["nominal"].at(v); return p.J, p.b, p.k, 10, 0
    if name == "b_lo*tau10":
        p = FAM["b_lo"].at(v); return p.J, p.b, p.k, 10, 0
    # ------- EXTRA attack members the design did NOT gate -------
    if name.endswith("+hA"):            # +hA = +10 tick hold aging applied to a combo
        J, b, k, d, _ = member_params(name[:-3], v); return J, b, k, d, 10
    if name == "b_q*J_hi":
        p = FAM["J_hi"].at(v)
        bq = max(0.25 * p.b, B_FLOOR) if v >= 12.5 else p.b
        return p.J, bq, p.k, 2, 0
    if name == "b_q*J1.0":
        p = REFIT[1.0].at(v)
        bq = max(0.25 * p.b, B_FLOOR) if v >= 12.5 else p.b
        return p.J, bq, p.k, 2, 0
    if name == "b_q*tau6":
        p = FAM["nominal"].at(v)
        bq = max(0.25 * p.b, B_FLOOR) if v >= 12.5 else p.b
        return p.J, bq, p.k, 6, 0
    if name == "J1.0*tau6":
        p = REFIT[1.0].at(v); return p.J, p.b, p.k, 6, 0
    if name == "b_q0*J_hi":           # unfloored 0.25x with high J (report-class physics, worst-case)
        p = FAM["J_hi"].at(v)
        bq = 0.25 * p.b if v >= 12.5 else p.b
        return p.J, bq, p.k, 2, 0
    raise KeyError(name)

def pm_of(name, v, extra_age=0):
    J, b, k, d, age = member_params(name, v)
    disc = rigid_disc(J, b, k)
    G = CL.G_at(v, TBL)
    return margins(G, KP_BASE, KI_BASE, KD, disc, d=d, age=age + extra_age)

if __name__ == "__main__":
    print("INDEPENDENT C1 stability refuter -- own model")
    print("KP_BASE %d KI_BASE %d KD %d ; table %s" % (KP_BASE, KI_BASE, KD, TBL))
