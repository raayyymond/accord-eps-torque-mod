# -*- coding: utf-8 -*-
"""adv_lib.py -- adversary "stability" on V295 trim-ratio (b 0xC63EA 567 -> 964).  MY OWN code, written independently of
v295_harness.py and of the designer's scripts.  The plant family parameters (v294_plant.family) are used as DATA only.

Contents
  read_cells(path)            cells read by address from an image (LE), my own reader
  IntLane                     byte-exact integer lane (numpy int64 batch), Ki/Kd included, from the golden-model arithmetic
  ctrl_frf(c, f)              x_in -> T linear FRF of the lane (fb lag sum/diff, P, D on E, taper, output lag, gain)
  plant_ss(p)                 continuous state space of a (rigid | collocated two-mass) plant, u = -T (+left)
  closed_loop_eigs(...)       1 kHz closed loop, EXACT ZOH plant discretisation (NOT semi-implicit Euler), rate former,
                              transport delay, linearised lane -> eigenvalues -> (f, zeta) list
  inner_L(...)                return ratio L(e^jw) of the trim loop, margins GM / PM / Ms
Nothing here sends or flashes anything.
"""
import hashlib
import os
import sys

import numpy as np
from scipy.linalg import expm

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FW = r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
IMGS = {
    "V294": FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
                 "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
    "V293": FW + "_v293_V293-V282BASE-TORQUEMODE.FB0-KD0.BANK.ALL+DCLAMP0-KP.FLAT.120.ALL-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_"
                 "plain_image.bin",
    "V282": FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
V294_SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
TP = 0xBF000
SEL = 7
DT = 1e-3
for _p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"),
           os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"),
           os.path.join(KIT, "analysis-2020accord", "model")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ------------------------------------------------------------------------------------------------ cells (my reader)
def _u16(b, a):
    return b[a] | (b[a + 1] << 8)


def _s16(b, a):
    v = _u16(b, a)
    return v - 65536 if v >= 32768 else v


def _u32(b, a):
    return b[a] | (b[a + 1] << 8) | (b[a + 2] << 16) | (b[a + 3] << 24)


def _rec(b, bank):
    r = _u32(b, bank + 4 * SEL)
    n = _u16(b, r)
    X = tuple(_u16(b, r + 2 + 2 * i) for i in range(n))
    Y = tuple(_u16(b, r + 2 + 2 * n + 2 * i) for i in range(n))
    return X, Y


def read_cells(name):
    path = IMGS[name]
    b = open(path, "rb").read()
    sha = hashlib.sha256(b).hexdigest()
    if name == "V294":
        assert sha == V294_SHA, sha
    hw = _u16(b, 0x29D76)
    assert (hw >> 5) & 0x3F == 0x16, "0x29D76 not shl imm5"
    op = (_u16(b, 0x28FA4) >> 5) & 0x3F
    fb_op = {0x0E: "sum", 0x0C: "diff"}[op]
    kpx, kpy = _rec(b, 0xCB994)
    kdx, kdy = _rec(b, 0xCB7D4)
    mx, my = _rec(b, 0xC9A88)
    gain = _s16(b, TP + _u16(b, 0x2A1F0))
    return dict(name=name, sha=sha, fb_a=_s16(b, 0xC63E8), fb_b=_u16(b, 0xC63EA), fb_clamp=_u16(b, 0xC62E6), fb_op=fb_op,
                e_shift=hw & 0x1F, kp_x=kpx, kp_y=kpy, kd_x=kdx, kd_y=kdy, d_clamp=_u16(b, 0xC61B6), ki=_u16(b, 0xC63E6),
                deadband=_u16(b, 0xC62E4), i_clamp=_u16(b, 0xC61BA), p_clamp=_u16(b, 0xC61BC), sum_clamp=_u16(b, 0xC61BE),
                lag_a=_s16(b, 0xC63EC), lag_b=_u16(b, 0xC63EE), gain=gain, t_clamp=_u16(b, 0xC61B4), map_x=mx, map_y=my,
                idx_clamp=b[0xC64F0])


def lerp(X, Y, x):
    """firmware LERP: flat outside, trunc-toward-zero divide (golden model lkas_rate_lerp semantics, my code)."""
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X) - 1):
        if X[i] <= x <= X[i + 1]:
            num, den = (Y[i + 1] - Y[i]) * (x - X[i]), (X[i + 1] - X[i])
            q = abs(num) // abs(den)
            return Y[i] + (-q if (num < 0) != (den < 0) else q)
    raise AssertionError


def with_b(c, b, name=None):
    d = dict(c)
    d["fb_b"] = b
    d["name"] = name or ("b%d" % b)
    return d


# ------------------------------------------------------------------------------------------------ integer lane (mine)
class IntLane:
    """batch integer lane.  Per tick, golden-model arithmetic (lkas_fb_lag + lkas_rate_pid_tick), taper m as a factor,
    pol = +1, ramp identity.  Bail (|x| > 12000): r26 = 0, PID skipped (S = 0), next tick restarts s from 0."""

    def __init__(self, cells_list):
        self.c = cells_list
        B = len(cells_list)
        g = lambda k: np.array([c[k] for c in cells_list], np.int64)  # noqa: E731
        self.a, self.b, self.C = g("fb_a"), g("fb_b"), g("fb_clamp")
        self.diff = np.array([c["fb_op"] == "diff" for c in cells_list])
        self.sh = g("e_shift")
        self.ki, self.db, self.dcl = g("ki"), g("deadband"), g("d_clamp")
        self.icl = (g("i_clamp") << 10) >> 3
        self.pcl, self.scl, self.tcl = g("p_clamp"), g("sum_clamp"), g("t_clamp")
        self.la, self.lb, self.gain = g("lag_a"), g("lag_b"), g("gain")
        self.kp_tab = np.array([[lerp(c["kp_x"], c["kp_y"], i) for i in range(256)] for c in cells_list], np.int64)
        self.kd_tab = np.array([[lerp(c["kd_x"], c["kd_y"], i) for i in range(256)] for c in cells_list], np.int64)
        self.map_tab = np.array([[lerp(c["map_x"], c["map_y"], i) for i in range(256)] for c in cells_list], np.int64)
        self.B = B
        self.rows = np.arange(B)
        self.reset()
        self.maxabs = {}

    def reset(self):
        B = self.B
        self.s = np.zeros(B, np.int64)
        self.restart = np.zeros(B, bool)
        self.I8 = np.zeros(B, np.int64)
        self.Ep = np.full(B, 0x7FFFFFFF, np.int64)
        self.o = np.zeros(B, np.int64)

    def _track(self, k, v):
        m = int(np.abs(v).max()) if v.size else 0
        if m > self.maxabs.get(k, 0):
            self.maxabs[k] = m

    def tick(self, x, sp, idx, m=254):
        x = np.asarray(x, np.int64) * np.ones(self.B, np.int64)
        sp = np.asarray(sp, np.int64) * np.ones(self.B, np.int64)
        idx = np.asarray(idx, np.int64) * np.ones(self.B, np.int64)
        m = np.asarray(m, np.int64) * np.ones(self.B, np.int64)
        bail = np.abs(x) > 12000
        s0 = np.where(self.restart, 0, self.s)
        xb = np.where(bail, 0, x)
        p1, p2 = self.a * s0, self.b * xb
        self._track("a*s", p1)
        self._track("b*x", p2)
        sn = (p1 >> 10) + (p2 >> 10)
        r26 = np.where(self.diff, sn - s0, sn + s0)
        self.s = np.where(bail, self.s, sn)
        self.restart = bail
        self.cbind = np.abs(r26) > self.C
        r26 = np.clip(r26, -self.C, self.C)
        r26 = np.where(bail, 0, r26)
        E = (sp << self.sh) - r26
        e5 = E >> 5
        exc = np.where(e5 > self.db, e5 - self.db, np.where(e5 < -self.db, e5 + self.db, 0))
        I = np.clip((self.I8 >> 3) + ((exc * self.ki) >> 3), -self.icl, self.icl)
        self.I8 = np.where(bail, 0, I << 3)
        I = np.where(bail, 0, I)
        kp = self.kp_tab[self.rows, idx]
        p4 = E * kp
        self._track("E*Kp", p4)
        Pu = p4 >> 8
        self.pbind = np.abs(Pu) > self.pcl
        P = np.clip(Pu, -self.pcl, self.pcl)
        kd = self.kd_tab[self.rows, idx]
        r27 = np.where(np.abs(self.Ep) <= 768000, self.Ep, E)
        D = np.clip(((E - r27) * kd) >> 3, -self.dcl, self.dcl)
        self.Ep = np.where(bail, 0x7FFFFFFF, E)
        Ssum = (I >> 7) + P + D
        S = np.clip((m * Ssum) >> 8, -self.scl, self.scl)
        S = np.where(bail, 0, S)
        o2 = ((self.la * self.o) >> 10) + ((S * self.lb) >> 10)
        y = (self.o + o2) >> 5
        self.o = o2
        self._track("y", y)
        T = np.clip((y * self.gain) >> 15, -self.tcl, self.tcl)
        self.last = dict(r26=r26, E=E, P=P, D=D, S=S, y=y, T=T)
        return T


# ------------------------------------------------------------------------------------------------ linear lane FRF (mine)
def ctrl_frf(c, f, m=254, idx=60, part="T"):
    """x_in -> T (tap sign, T counts per x count) of the linearised lane.  x_in is what the lane is fed (= +wire = -x)."""
    z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
    zi = 1 / z
    a, b = c["fb_a"] / 1024.0, c["fb_b"] / 1024.0
    S_ = b / (1 - a * zi)                                  # s per x_in
    F = S_ * ((1 - zi) if c["fb_op"] == "diff" else (1 + zi))   # r26 per x_in
    kp = lerp(c["kp_x"], c["kp_y"], idx)
    kd = lerp(c["kd_x"], c["kd_y"], idx) if c["d_clamp"] else 0
    PID = (kp / 256.0 + (kd / 8.0) * (1 - zi))            # per E ; Ki ignored here (0 on every cell set used)
    Px = -PID * F                                         # (P + D) per x_in (E = -r26 on the x path)
    if part == "P":
        return Px
    Sx = (m / 256.0) * Px
    OL = (c["lag_b"] / 1024.0) * (1 + zi) / (32.0 * (1 - (c["lag_a"] / 1024.0) * zi))
    return Sx * OL * c["gain"] / 32768.0


# ------------------------------------------------------------------------------------------------ plants
def plant_ss(p):
    """continuous (A, B, Cth) with state [th, om] or [th, om, thw, omw]; input u (T counts, +left); output th (motor)."""
    if p.f2 > 0:
        Jw = p.J * p.r2
        Jm = p.J - Jw
        mu = Jm * Jw / p.J
        K = (2 * np.pi * p.f2) ** 2 * mu
        cc = 2 * p.zeta2 * np.sqrt(K * mu)
        A = np.array([[0, 1, 0, 0],
                      [-(p.k + K) / Jm, -(p.b + cc) / Jm, K / Jm, cc / Jm],
                      [0, 0, 0, 1],
                      [K / Jw, cc / Jw, -K / Jw, -cc / Jw]], float)
        B = np.array([0, 1 / Jm, 0, 0], float)
    else:
        A = np.array([[0, 1], [-p.k / p.J, -p.b / p.J]], float)
        B = np.array([0, 1 / p.J], float)
    Cth = np.zeros(A.shape[0])
    Cth[0] = 1.0
    return A, B, Cth


def zoh(A, B, dt=DT):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A * dt
    M[:n, n] = B * dt
    E = expm(M)
    return E[:n, :n], E[:n, n]


def closed_loop_A(p, c, lane_on=True, m=254, idx=60, tau=None, w=None):
    """1 kHz closed-loop one-step map.  Order of events at tick n: x[n] = 8 (th[n] - th[n-w]) / (w dt); lane -> T[n];
    u applied over [n, n+1) is -T[n - tau] (ZOH); plant advances by the exact ZOH map."""
    tau = int(p.tau_ms if tau is None else tau)
    w = int(p.rate_win_ms if w is None else w)
    Ac, Bc, Cth = plant_ss(p)
    Ad, Bd = zoh(Ac, Bc)
    npl = Ad.shape[0]
    a, b = c["fb_a"] / 1024.0, c["fb_b"] / 1024.0
    kp = lerp(c["kp_x"], c["kp_y"], idx)
    kd = lerp(c["kd_x"], c["kd_y"], idx) if c["d_clamp"] else 0
    la, lb, g = c["lag_a"] / 1024.0, c["lag_b"] / 1024.0, c["gain"] / 32768.0
    diff = c["fb_op"] == "diff"
    # state: plant (npl) | th history th[n-1..n-w] (w) | s | Eprev | o | Tq[n-1..n-tau] (tau)
    i_h = npl
    i_s = npl + w
    i_E = i_s + 1
    i_o = i_E + 1
    i_T = i_o + 1
    N = i_T + tau

    def step(zv):
        th = Cth @ zv[:npl]
        hist = zv[i_h:i_h + w]
        x = 8.0 * (th - hist[w - 1]) / (w * DT)
        if lane_on:
            xin = -x
            s0 = zv[i_s]
            sn = a * s0 + b * xin
            r26 = (sn - s0) if diff else (sn + s0)
            E = -r26
            PD = (kp / 256.0) * E + (kd / 8.0) * (E - zv[i_E])
            S = (m / 256.0) * PD
            o0 = zv[i_o]
            on = la * o0 + lb * S
            T = g * (o0 + on) / 32.0
        else:
            sn, E, on, T = zv[i_s], zv[i_E], zv[i_o], 0.0
        Tq = zv[i_T:i_T + tau]
        T_app = Tq[tau - 1] if tau > 0 else T
        u = -T_app
        out = np.zeros(N)
        out[:npl] = Ad @ zv[:npl] + Bd * u
        out[i_h] = th
        out[i_h + 1:i_h + w] = hist[:w - 1]
        out[i_s], out[i_E], out[i_o] = sn, E, on
        if tau > 0:
            out[i_T] = T
            out[i_T + 1:i_T + tau] = Tq[:tau - 1]
        return out

    return np.column_stack([step(e) for e in np.eye(N)])


def modes_of(A):
    ev = np.linalg.eigvals(A)
    rho = float(np.max(np.abs(ev)))
    out = []
    for zp in ev:
        if abs(zp) < 1e-12:
            continue
        s = np.log(zp) / DT
        if s.imag > 1e-9:
            out.append((float(s.imag / (2 * np.pi)), float(-s.real / abs(s))))
    out.sort()
    return rho, out


def plant_frf_th(p, f):
    """th / u of the ZOH-discretised plant at 1 kHz (exact), deg per T count."""
    Ac, Bc, Cth = plant_ss(p)
    Ad, Bd = zoh(Ac, Bc)
    z = np.exp(2j * np.pi * np.asarray(f, float) * DT)
    n = Ad.shape[0]
    Mz = z[:, None, None] * np.eye(n)[None] - Ad[None]
    X = np.linalg.solve(Mz, np.broadcast_to(Bd.astype(complex), (len(z), n))[..., None])[..., 0]
    return X @ Cth


def inner_L(p, c, f, m=254, idx=60, tau=None, w=None):
    """return ratio of the trim loop, L = -G_d * z^-tau * C * R with C: x_in -> T, x_in = -x, u = -T (see docstring of
    closed_loop_A for timing).  1 + L = 0 is the characteristic equation."""
    tau = p.tau_ms if tau is None else tau
    w = int(p.rate_win_ms if w is None else w)
    f = np.asarray(f, float)
    z = np.exp(2j * np.pi * f * DT)
    R = 8.0 * (1 - z ** (-w)) / (w * DT)
    C = ctrl_frf(c, f, m=m, idx=idx)
    G = plant_frf_th(p, f)
    # u = -z^-tau T ; T = C x_in = -C R th  ->  u = z^-tau C R th ; th = G u  ->  1 - G z^-tau C R = 0
    return -G * z ** (-tau) * C * R


def margins(f, L):
    """GM (min over -180 crossings of 1/|L|), PM (min over |L| = 1 crossings), Ms = max 1/|1+L|."""
    ph = np.unwrap(np.angle(L))
    mag = np.abs(L)
    gm = np.inf
    for i in range(len(f) - 1):
        for k in range(-5, 6):
            tgt = -np.pi + 2 * np.pi * k
            if (ph[i] - tgt) * (ph[i + 1] - tgt) <= 0 and ph[i] != ph[i + 1]:
                t = (tgt - ph[i]) / (ph[i + 1] - ph[i])
                mg = mag[i] + t * (mag[i + 1] - mag[i])
                if mg > 0:
                    gm = min(gm, 1.0 / mg)
    pm = np.inf
    for i in range(len(f) - 1):
        if (mag[i] - 1) * (mag[i + 1] - 1) <= 0 and mag[i] != mag[i + 1]:
            t = (1 - mag[i]) / (mag[i + 1] - mag[i])
            pp = ph[i] + t * (ph[i + 1] - ph[i])
            pm = min(pm, abs(((pp + np.pi) + np.pi) % (2 * np.pi) - np.pi) * 180 / np.pi)
    S = 1.0 / np.abs(1 + L)
    j = int(np.argmax(S))
    return dict(GM=gm, PM=pm, Ms=float(S[j]), f_Ms=float(f[j]))
