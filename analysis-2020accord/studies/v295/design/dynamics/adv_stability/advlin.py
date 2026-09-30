# -*- coding: utf-8 -*-
"""advlin.py -- adversary `stability`: MY OWN linear model of the V294-class inner loop and the fork's outer loop.
Independent of the harness's linear tools (loop_frf / closed_loop_modes / outer_frf) in three ways:
  * the plant is discretised EXACTLY (zero-order hold, matrix exponential), not by semi-implicit Euler;
  * the loop is assembled as one discrete state-space (eigenvalues) AND as a Nyquist product (margins) -- two methods;
  * the lane transfer is written from the census listing arithmetic (sp = 0, floors/clamps off), and checked against a
    TIME-DOMAIN sine response of my own INTEGER lane (s0_lane_spotcheck.MyLane) in s1_linear.py.
Plant parameters (J, b, k per speed band) are the plant study's family (data, via H.family()); the two-mass stress form
is the harness's physical arrangement (spring/damper/road on the motor-rack side, the steering wheel a free inertia on
the torsion bar, x sensed motor-side = collocated), plus my own NON-collocated variant (x sensed wheel-side) as a harsher
stress case that is NOT the physical sensing (kappa says the 0x18F rate is rack side).

Units: T counts; theta deg (+ left); u = -T (+ left); x = 8 counts per deg/s; the lane is fed x_lane = -x.
"""
import math

import numpy as np
from scipy.linalg import expm

DT = 1e-3


# ------------------------------------------------------------------------------------------------ lane (linear, sp = 0)
class LaneLin:
    """op 'diff' (V294 class) or 'sum' (V282); a, b fb lag; kp, kd (flat); la, lb output lag; gain; m taper."""

    def __init__(self, a=1011, b=567, op="diff", kp=960, kd=0, la=992, lb=507, gain=5346, m=254, name=""):
        self.a, self.b, self.op, self.kp, self.kd = a / 1024.0, b / 1024.0, op, kp, kd
        self.la, self.lb, self.gain, self.m, self.name = la / 1024.0, lb / 1024.0, gain / 32768.0, m, name

    def ctf(self, f):
        """T / x_lane, exact 1 kHz z-transfer."""
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        zi = 1 / z
        R = self.b * ((1 - zi) if self.op == "diff" else (1 + zi)) / (1 - self.a * zi)
        E = -R
        PID = (self.kp / 256.0 + (self.kd / 8.0) * (1 - zi)) * E
        S = self.m / 256.0 * PID
        y = self.lb * (1 + zi) / (32.0 * (1 - self.la * zi)) * S
        return y * self.gain

    def ptf(self, f):
        """(P + D) / x_lane before the taper (|P/x| of the record)."""
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        zi = 1 / z
        R = self.b * ((1 - zi) if self.op == "diff" else (1 + zi)) / (1 - self.a * zi)
        return (self.kp / 256.0 + (self.kd / 8.0) * (1 - zi)) * (-R)

    def ff_per_wire(self, f, sp_per_wire=4.30 / (2 ** 22 / (4 * 65025)), e_shift=2):
        """wire count -> T (the feedforward path; unchanged by the fb cells)."""
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        zi = 1 / z
        E = (2 ** e_shift) * sp_per_wire
        S = self.m / 256.0 * (self.kp / 256.0 + (self.kd / 8.0) * (1 - zi)) * E
        y = self.lb * (1 + zi) / (32.0 * (1 - self.la * zi)) * S
        return y * self.gain


def trim_T_per_omega(lane, f, w=3, age_ms=0.0):
    """opposing torque per deg/s of the SENSED-side wheel rate: T/omega = -8 * C_T * RF / s * e^{-s age}."""
    f = np.asarray(f, float)
    z = np.exp(2j * np.pi * f * DT)
    s = 2j * np.pi * f
    RF = (1 - z ** (-w)) / (w * DT)
    return -8.0 * lane.ctf(f) * RF / s * np.exp(-s * age_ms * 1e-3)


# ------------------------------------------------------------------------------------------------ plant
class Plant:
    """rigid (f2 = 0) or two-mass.  Motor/rack side: J_m, b, k, input u.  Wheel side: J_w on the torsion bar (K, c).
    sense='motor' (collocated, the physical case) or 'wheel' (non-collocated stress)."""

    def __init__(self, J, b, k, f2=0.0, zeta2=0.05, r2=0.2, sense="motor"):
        self.J, self.b, self.k, self.f2, self.zeta2, self.r2, self.sense = J, b, k, f2, zeta2, r2, sense
        if f2 > 0:
            Jw = J * r2
            Jm = J - Jw
            mu = Jm * Jw / J
            K = (2 * np.pi * f2) ** 2 * mu
            c = 2 * zeta2 * math.sqrt(K * mu)
            # x = [th, om, thw, omw]
            A = np.array([[0, 1, 0, 0],
                          [-(k + K) / Jm, -(b + c) / Jm, K / Jm, c / Jm],
                          [0, 0, 0, 1],
                          [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
            B = np.array([[0], [1 / Jm], [0], [0]], float)
            self.C_motor = np.array([[1, 0, 0, 0]], float)
            self.C_wheel = np.array([[0, 0, 1, 0]], float)
        else:
            A = np.array([[0, 1], [-k / J, -b / J]], float)
            B = np.array([[0], [1 / J]], float)
            self.C_motor = self.C_wheel = np.array([[1, 0]], float)
        self.Ac, self.Bc = A, B
        n = A.shape[0]
        M = np.zeros((n + 1, n + 1))
        M[:n, :n] = A * DT
        M[:n, n:] = B * DT
        E = expm(M)
        self.Ad, self.Bd = E[:n, :n], E[:n, n:]
        self.n = n
        self.Cs = self.C_motor if sense == "motor" else self.C_wheel

    def P_disc(self, f, out="sense"):
        """theta / u of the ZOH-discretised plant, sampled at the tick boundaries (deg per T count).
        Modal sum C V diag(1/(z - lam)) V^-1 Bd (the plant's poles are distinct for every member used)."""
        C = self.Cs if out == "sense" else (self.C_wheel if out == "wheel" else self.C_motor)
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        if not hasattr(self, "_eig"):
            lam, V = np.linalg.eig(self.Ad)
            self._eig = (lam, V, np.linalg.solve(V, self.Bd))
        lam, V, VB = self._eig
        cv = (C @ V)[0]
        return np.sum((cv * VB[:, 0])[None, :] / (z[:, None] - lam[None, :]), axis=1)

    def P_disc_check(self, f, out="sense"):
        C = self.Cs if out == "sense" else (self.C_wheel if out == "wheel" else self.C_motor)
        z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
        I = np.eye(self.n)
        return np.array([(C @ np.linalg.solve(zz * I - self.Ad, self.Bd))[0, 0] for zz in z])

    def P_cont(self, f, out="sense"):
        C = self.Cs if out == "sense" else (self.C_wheel if out == "wheel" else self.C_motor)
        s = 2j * np.pi * np.asarray(f, float)
        I = np.eye(self.n)
        return np.array([(C @ np.linalg.solve(ss * I - self.Ac, self.Bc))[0, 0] for ss in s])


# ------------------------------------------------------------------------------------------------ inner loop
def inner_L(lane, plant, f, tau=2, w=3):
    """return ratio (1 + L form): L = -8 C_T RF z^-tau P_d  (x_lane = -x, u = -T)."""
    f = np.asarray(f, float)
    z = np.exp(2j * np.pi * f * DT)
    RF = (1 - z ** (-w)) / (w * DT)
    return -8.0 * lane.ctf(f) * RF * z ** (-tau) * plant.P_disc(f)


def inner_A(lane, plant, tau=2, w=3):
    """the closed-loop 1 kHz state matrix: plant (exact ZOH), angle history (w), lane states s, o, E_prev, T buffer."""
    n = plant.n
    ih = n                      # history th[n-1..n-w] of the SENSED angle
    i_s, i_o, i_e = n + w, n + w + 1, n + w + 2
    i_T = n + w + 3
    N = i_T + tau
    A = np.zeros((N, N))
    Cs = plant.Cs[0]
    # x = 8 * (th_s[n] - th_s[n-w]) / (w DT) ; th_s[n] = Cs . xp ; th_s[n-w] = hist[w-1]
    # lane: s' = a s + b (-x) ; r = s' -/+ s ; E = -r ; S = m/256 (kp/256 E + kd/8 (E - Ep)) ; o' = la o + lb S ;
    # T = gain (o + o') / 32 ; u[n] = -T[n - tau] (tau = 0: this tick's T)
    kx = 8.0 / (w * DT)
    # express x as a row over the state
    xrow = np.zeros(N)
    xrow[:n] += kx * Cs
    xrow[ih + w - 1] -= kx
    s_new = lane.a * np.eye(N)[i_s] + lane.b * (-xrow)
    r = s_new - np.eye(N)[i_s] if lane.op == "diff" else s_new + np.eye(N)[i_s]
    E = -r
    S = lane.m / 256.0 * (lane.kp / 256.0 * E + lane.kd / 8.0 * (E - np.eye(N)[i_e]))
    o_new = lane.la * np.eye(N)[i_o] + lane.lb * S
    T = lane.gain * (np.eye(N)[i_o] + o_new) / 32.0
    u = -(np.eye(N)[i_T + tau - 1] if tau > 0 else T)
    # plant
    A[:n, :n] = plant.Ad
    A[:n, :] += plant.Bd @ u[None, :]
    # history: hist'[0] = th_s[n], hist'[k] = hist[k-1]
    A[ih, :n] = Cs
    for k in range(1, w):
        A[ih + k, ih + k - 1] = 1.0
    A[i_s] = s_new
    A[i_o] = o_new
    A[i_e] = E
    if tau > 0:
        A[i_T] = T
        for k in range(1, tau):
            A[i_T + k, i_T + k - 1] = 1.0
    return A


def modes_of(A):
    ev = np.linalg.eigvals(A)
    rho = float(np.max(np.abs(ev)))
    out = []
    for zp in ev:
        if abs(zp) < 1e-9:
            continue
        s = np.log(zp) / DT
        if s.imag > 1e-6:
            out.append((float(s.imag / (2 * np.pi)), float(-s.real / abs(s))))
    out.sort()
    return out, rho


def margins(f, L):
    mag = np.abs(L)
    ang = np.angle(L)
    S = 1.0 / (1.0 + L)
    Ms = float(np.max(np.abs(S)))
    fMs = float(f[int(np.argmax(np.abs(S)))])
    xc = np.flatnonzero(np.diff(np.sign(mag - 1.0)) != 0)
    PM = [float(180.0 + np.degrees(ang[i])) if ang[i] <= 0 else float(180.0 - np.degrees(ang[i])) for i in xc]
    PM = [((p + 180) % 360) - 180 for p in PM]
    pc = np.flatnonzero(np.diff(np.sign(np.sin(ang))) != 0)
    GM = [(float(f[i]), float(1.0 / max(mag[i], 1e-15))) for i in pc if np.cos(ang[i]) < 0]
    return dict(Ms=Ms, fMs=fMs, xover=[float(f[i]) for i in xc], PM_min=min(PM, default=float("inf")),
                GM_min=min([g for _, g in GM], default=float("inf")), GM=GM)


# ------------------------------------------------------------------------------------------------ outer loop (fork r1)
LOW_SPEED_X, LOW_SPEED_Y = [0, 10, 20, 30], [12, 10.5, 8, 5]
KP, KI, LAF, FRIC, THR = 0.9, 0.3, 14.0, 0.011, 0.30
SF, CHI, WB = -0.0006999872680281922, 0.0, 2.8299999237060547


def kla(v, sr=16.84):
    """d(la_meas)/d(theta_wheel), m/s^2 per deg (magnitude; the fork's sign makes the loop negative feedback)."""
    cf = (1.0 - CHI) / (1.0 - SF * v ** 2) / WB
    return cf / sr * v ** 2 * np.pi / 180.0


def outer_L(lane, plant, v, f, tau=2, w=3, pipe_ms=22.0, relay_frac=1.0, sr=16.84, ki=KI, kp=KP, zoh=True):
    """outer return ratio: e_lsf = -(1 + lsf/Kp) * la_meas ; Cf = Kp + Ki dt/(1 - z100^-1) + relay slope ;
    torque = ctrl/LAF ; wire = 4096 torque ; 100 Hz ZOH + pipe ; FF path (1 kHz) ; plant with the inner loop closed ;
    the fork reads the WHEEL-side angle (0x14A)."""
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    z100 = np.exp(s * 0.01)
    lsf = (np.interp(v, LOW_SPEED_X, LOW_SPEED_Y) / max(v, 1.0)) ** 2
    relay = relay_frac * FRIC * LAF / THR
    Cf = (kp + ki * 0.01 / (1 - 1 / z100) + relay) * (1 + lsf / kp)
    zh = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01) if zoh else 1.0
    pipe = np.exp(-s * pipe_ms * 1e-3)
    Lin = inner_L(lane, plant, f, tau=tau, w=w)
    z = np.exp(s * DT)
    Pw = plant.P_disc(f, out="wheel") * z ** (-tau)        # wheel angle / u (delay included)
    Pcl = Pw / (1 + Lin)
    return kla(v, sr) * Pcl * lane.ff_per_wire(f) * zh * pipe * 4096.0 / LAF * Cf


def alpha_per_cmd(lane, plant, f, tau=2, w=3):
    """wheel-side angular acceleration per 0xE4 count, inner loop closed, 100 Hz command ZOH."""
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    z = np.exp(s * DT)
    zh = np.exp(-1j * np.pi * f * 0.01) * np.sinc(f * 0.01)
    Lin = inner_L(lane, plant, f, tau=tau, w=w)
    Pw = plant.P_disc(f, out="wheel") * z ** (-tau)
    return s ** 2 * Pw * lane.ff_per_wire(f) * zh / (1 + Lin)
