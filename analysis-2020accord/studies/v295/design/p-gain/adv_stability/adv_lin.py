# -*- coding: utf-8 -*-
"""adv_lin.py -- MY OWN linear inner-loop machinery (exact ZOH discretisation of the continuous plant via the matrix
exponential -- NOT the harness's semi-implicit Euler -- plus the lane's exact 1 kHz state equations), two methods:
  (1) eigenvalues of the discrete closed loop  -> every closed-loop pole's f and zeta
  (2) the frequency response L(f) (continuous plant x ZOH x discrete lane)  -> GM / PM / Ms
Plant topologies:
  rigid : J th'' + b th' + k th = u                        (sensor/actuator on th)
  T1    : two-mass, road (b, k) on the MOTOR side, free hand-wheel mass Jw via (K, c)   (the harness's stress member)
  T2    : two-mass, motor mass Jm carries the actuator+sensor, compliance (K, c) to the RACK mass Jr carrying (b, k)
  T3    : T2 geometry but the rate sensor on the RACK mass (non-collocated; adversarial)
Units: T counts, deg, deg/s; x = 8 counts per deg/s; u = -T (lane output in tap sign), delay tau ticks.
"""
import numpy as np
from scipy.linalg import expm

DT = 1e-3


def plant_cont(J, b, k, top="rigid", f2=0.0, z2=0.05, r2=0.2):
    """returns (Ac, Bc, c_sense, c_angle) ; c_sense picks the sensed angle, c_angle the angle the fork reads."""
    if top == "rigid" or f2 <= 0:
        Ac = np.array([[0.0, 1.0], [-k / J, -b / J]])
        Bc = np.array([0.0, 1.0 / J])
        c = np.array([1.0, 0.0])
        return Ac, Bc, c, c
    if top == "T1":
        Jw = J * r2
        Jm = J - Jw
        mu = Jm * Jw / J
        K = (2 * np.pi * f2) ** 2 * mu
        cc = 2 * z2 * np.sqrt(K * mu)
        # x = [thm, om_m, thw, om_w]
        Ac = np.array([[0, 1, 0, 0],
                       [-(k + K) / Jm, -(b + cc) / Jm, K / Jm, cc / Jm],
                       [0, 0, 0, 1],
                       [K / Jw, cc / Jw, -K / Jw, -cc / Jw]], float)
        Bc = np.array([0, 1 / Jm, 0, 0], float)
        return Ac, Bc, np.array([1.0, 0, 0, 0]), np.array([0, 0, 1.0, 0])
    if top in ("T2", "T3"):
        Jm = J * (1 - r2)          # motor+pinion (actuator side)
        Jr = J * r2                # rack/road side
        mu = Jm * Jr / J
        K = (2 * np.pi * f2) ** 2 * mu
        cc = 2 * z2 * np.sqrt(K * mu)
        # x = [thm, om_m, thr, om_r]; road (b, k) on the rack mass
        Ac = np.array([[0, 1, 0, 0],
                       [-K / Jm, -cc / Jm, K / Jm, cc / Jm],
                       [0, 0, 0, 1],
                       [K / Jr, cc / Jr, -(K + k) / Jr, -(cc + b) / Jr]], float)
        Bc = np.array([0, 1 / Jm, 0, 0], float)
        cs = np.array([1.0, 0, 0, 0]) if top == "T2" else np.array([0, 0, 1.0, 0])
        return Ac, Bc, cs, np.array([0, 0, 1.0, 0])
    raise ValueError(top)


def c2d(Ac, Bc, dt=DT):
    n = Ac.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = Ac
    M[:n, n] = Bc
    E = expm(M * dt)
    return E[:n, :n], E[:n, n]


def closed_loop_A(Ac, Bc, cs, lane, tau=2, w=3, m=254, lane_on=True):
    """exact 1 kHz linear closed loop.  lane: dict fb_a, fb_b, fb_op, kp, kd, lag_a, lag_b, gain."""
    Ad, Bd = c2d(Ac, Bc)
    npl = Ad.shape[0]
    a, bb = lane["fb_a"] / 1024.0, lane["fb_b"] / 1024.0
    diff = lane["fb_op"] == "diff"
    kp, kd = lane["kp"], lane.get("kd", 0.0)
    la, lb, G = lane["lag_a"] / 1024.0, lane["lag_b"] / 1024.0, lane["gain"] / 32768.0
    # state layout
    i_h = npl                 # hist th[n-1..n-w]
    i_s = i_h + w             # s[n-1]
    i_r = i_s + 1             # r26[n-1]
    i_o = i_r + 1             # o[n-1]
    i_T = i_o + 1             # T[n-1..n-tau]
    N = i_T + tau

    def step(z):
        xp = z[:npl]
        th = cs @ xp
        hist = z[i_h:i_h + w]
        x = 8.0 * (th - hist[w - 1]) / (w * DT)
        s0, r0, o0 = z[i_s], z[i_r], z[i_o]
        if lane_on:
            s1 = a * s0 + bb * (-x)
            r1 = (s1 - s0) if diff else (s1 + s0)
            PD = -(kp / 256.0) * r1 - (kd / 8.0) * (r1 - r0)
            S = (m / 256.0) * PD
            o1 = la * o0 + lb * S
            T = G * (o0 + o1) / 32.0
        else:
            s1, r1, o1, T = s0, r0, o0, 0.0
        Tq = z[i_T:i_T + tau]
        u = -(Tq[tau - 1] if tau > 0 else T)
        zn = np.zeros(N)
        zn[:npl] = Ad @ xp + Bd * u
        zn[i_h] = th
        zn[i_h + 1:i_h + w] = hist[:w - 1]
        zn[i_s], zn[i_r], zn[i_o] = s1, r1, o1
        if tau > 0:
            zn[i_T] = T
            zn[i_T + 1:i_T + tau] = Tq[:tau - 1]
        return zn

    return np.column_stack([step(e) for e in np.eye(N)])


def poles(A, fmax=150.0):
    ev = np.linalg.eigvals(A)
    out = []
    for z in ev:
        if abs(z) < 1e-12:
            continue
        s = np.log(z) / DT
        f = abs(s.imag) / (2 * np.pi)
        zeta = -s.real / abs(s) if abs(s) > 0 else 1.0
        if s.imag > 1e-9 and f < fmax:
            out.append((f, zeta))
        elif abs(s.imag) <= 1e-9:
            out.append((0.0, 1.0 if s.real < 0 else -1.0, float(s.real)))
    return out, float(np.max(np.abs(ev)))


def osc_poles(A, fmin=0.05, fmax=150.0):
    ev = np.linalg.eigvals(A)
    res = []
    for z in ev:
        if abs(z) < 1e-12:
            continue
        s = np.log(z) / DT
        f = s.imag / (2 * np.pi)
        if f > fmin and f < fmax:
            res.append((f, -s.real / abs(s)))
    return sorted(res), float(np.max(np.abs(ev)))


# ------------------------------------------------------------------ frequency response
def lane_CT(lane, f, m=254):
    """T (tap sign) per lane-input count xl, exact z."""
    zi = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    a, bb = lane["fb_a"] / 1024.0, lane["fb_b"] / 1024.0
    num = (1 - zi) if lane["fb_op"] == "diff" else (1 + zi)
    H = bb * num / (1 - a * zi)
    PD = -(lane["kp"] / 256.0 + lane.get("kd", 0.0) / 8.0 * (1 - zi)) * H
    la, lb = lane["lag_a"] / 1024.0, lane["lag_b"] / 1024.0
    return (m / 256.0) * PD * lb * (1 + zi) / (32.0 * (1 - la * zi)) * lane["gain"] / 32768.0


def plant_frf(Ac, Bc, c, f):
    """c (sI - A)^-1 B at s = j 2 pi f (continuous)."""
    out = np.zeros(len(f), complex)
    I = np.eye(Ac.shape[0])
    for i, ff in enumerate(f):
        out[i] = c @ np.linalg.solve(2j * np.pi * ff * I - Ac, Bc)
    return out


def inner_L(lane, Ac, Bc, cs, f, tau=2, w=3, m=254):
    f = np.asarray(f, float)
    zi = np.exp(-2j * np.pi * f * DT)
    RF = (1 - zi ** w) / (w * DT)
    zoh = np.exp(-1j * np.pi * f * DT) * np.sinc(f * DT)
    P = plant_frf(Ac, Bc, cs, f)
    CT = lane_CT(lane, f, m)
    G = 8.0 * CT * RF * P * zoh * np.exp(-2j * np.pi * f * tau * DT)
    return -G


def margins(f, L):
    mag = np.abs(L)
    out = dict(Ms=float(np.max(1.0 / np.abs(1 + L))), f_Ms=float(f[np.argmax(1.0 / np.abs(1 + L))]))
    # gain margin: crossings of the negative real axis (Im L changes sign with Re L < 0)
    gm = []
    im = L.imag
    for i in np.flatnonzero(np.sign(im[:-1]) != np.sign(im[1:])):
        t = im[i] / (im[i] - im[i + 1])
        Lc = L[i] + t * (L[i + 1] - L[i])
        if Lc.real < 0:
            gm.append((float(f[i] + t * (f[i + 1] - f[i])), float(1.0 / abs(Lc))))
    out["GM_list"] = gm
    out["GM"] = min([g for _, g in gm], default=float("inf"))
    out["f_GM"] = min(gm, key=lambda t: t[1])[0] if gm else float("nan")
    pm = []
    for i in np.flatnonzero(np.sign(mag[:-1] - 1) != np.sign(mag[1:] - 1)):
        pm.append((float(f[i]), float(180.0 + np.degrees(np.angle(L[i])))))
    out["PM_list"] = pm
    out["PM"] = min([((p + 180) % 360) - 180 for _, p in pm], default=float("inf"))
    return out
