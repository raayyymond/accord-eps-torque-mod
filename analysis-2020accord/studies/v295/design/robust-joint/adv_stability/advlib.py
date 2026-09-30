# -*- coding: utf-8 -*-
"""advlib.py -- adversary "stability" (vs robust-joint candidate A): MY OWN cell reader, integer lane, linear lane
transfer, plant transfer and state-space closed loop.  Written from the census listing (V294-LKAS-PID-DESIGN-SPACE.md
section 2) and the golden-model docstrings, NOT from rj_*.py or the harness's lane/loop functions.

Units: x = rate operand counts (8 per deg/s), T = delivered lane torque (tap sign, T counts), plant u = -T (+ left),
theta deg + left.  Lane is fed x_lane = -8*omega (the kit's march convention: x_lane = +raw 0x18F = -8 omega_left).
ANALYSIS ONLY: sends nothing, flashes nothing, builds nothing.
"""
import os
import sys
import numpy as np

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG = {
    "V294": FW + "_v294_V294-V293BASE-ACCELTRIM.SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.567-KP.FLAT.960.ALL-KD0-R24.2048-"
                 "MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin",
    "V282": FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
}
V294_SHA = "3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85"
SEL = 7
DT = 1e-3


def u16(b, a): return int.from_bytes(b[a:a + 2], "little")
def s16(b, a): return int.from_bytes(b[a:a + 2], "little", signed=True)
def u32(b, a): return int.from_bytes(b[a:a + 4], "little")


def rec(b, bank):
    r = u32(b, bank + 4 * SEL)
    n = u16(b, r)
    return [u16(b, r + 2 + 2 * i) for i in range(n)], [u16(b, r + 2 + 2 * n + 2 * i) for i in range(n)]


def read_cells(tag):
    import hashlib
    b = open(IMG[tag], "rb").read()
    if tag == "V294":
        assert hashlib.sha256(b).hexdigest() == V294_SHA
    hw_shl = u16(b, 0x29D76)            # Format II shl imm5, reg2: imm5 = low 5 bits
    hw_op = u16(b, 0x28FA4)             # add (0xC9D1 LE -> hw 0xD1C9) vs subr (0x89D1 LE -> hw 0xD189)
    op = {0xD1C9: "sum", 0xD189: "diff"}[hw_op]
    kpX, kpY = rec(b, 0xCB994)
    kdX, kdY = rec(b, 0xCB7D4)
    mX, mY = rec(b, 0xC9A88)
    c = dict(a=s16(b, 0xC63E8), b=u16(b, 0xC63EA), C=u16(b, 0xC62E6), op=op, sh=hw_shl & 0x1F,
             kpX=kpX, kpY=kpY, kdX=kdX, kdY=kdY, dcl=u16(b, 0xC61B6), ki=u16(b, 0xC63E6),
             pcl=u16(b, 0xC61BC), scl=u16(b, 0xC61BE), tcl=u16(b, 0xC61B4), la=s16(b, 0xC63EC), lb=u16(b, 0xC63EE),
             gain=s16(b, 0xC6CD0), mapX=mX, mapY=mY, idxcl=b[0xC64F0])
    return c


def lerp_int(X, Y, i):
    """kit LERP (integer walk, as the harness/golden: floor of linear interpolation between knots)."""
    return int(np.interp(i, X, Y))


class MyLane:
    """byte-exact integer lane, I = D = 0 path only (V294 structure; Kd/Ki must be zero), batch over B, int64 numpy.
    Arithmetic per the census listing: 0x28F86..0x28FA8 fb lag; 0x29D76 shl; 0x29E36 P; 0x2A0B4 taper; 0x2A174 lag."""

    def __init__(self, c, B, b_override=None):
        assert c["ki"] == 0
        self.kd_on = bool(c["dcl"]) and any(k != 0 for k in c["kdY"])
        self.dcl = c["dcl"]
        self.kdLUT = np.array([lerp_int(c["kdX"], c["kdY"], i) for i in range(256)], np.int64)
        self.Eprev = np.full(B, 0x7FFFFFFF, np.int64)
        self.a, self.b, self.C = c["a"], (c["b"] if b_override is None else b_override), c["C"]
        self.op, self.sh = c["op"], c["sh"]
        self.kpX, self.kpY = c["kpX"], c["kpY"]
        self.flatkp = len(set(self.kpY)) == 1
        self.pcl, self.scl, self.tcl = c["pcl"], c["scl"], c["tcl"]
        self.la, self.lb, self.g = c["la"], c["lb"], c["gain"]
        self.mapLUT = np.array([lerp_int(c["mapX"], c["mapY"], i) for i in range(256)], np.int64)
        self.kpLUT = np.array([lerp_int(self.kpX, self.kpY, i) for i in range(256)], np.int64)
        self.B = B
        self.s = np.zeros(B, np.int64)
        self.L = np.zeros(B, np.int64)
        self.live = np.ones(B, bool)
        self.maxabs = {}

    def _track(self, k, v):
        m = int(np.max(np.abs(v))) if np.size(v) else 0
        if m > self.maxabs.get(k, 0):
            self.maxabs[k] = m

    def tick(self, x, sp, idx, m=254, bail=None):
        """x int64 (B,), sp signed setpoint (B,), idx (B,), m taper. bail: bool (B,) -> this tick is a filter bail."""
        x = np.asarray(x, np.int64)
        s_old = np.where(self.live, self.s, 0)
        bx = self.b * x
        as_ = self.a * s_old
        self._track("b*x", bx); self._track("a*s", as_)
        s_new = (as_ >> 10) + (bx >> 10)
        d = (s_new - s_old) if self.op == "diff" else (s_new + s_old)
        r26 = np.clip(d, -self.C, self.C)
        self.s = s_new
        E = (np.asarray(sp, np.int64) << self.sh) - r26
        kp = self.kpLUT[np.asarray(idx, np.int64)]
        EK = E * kp
        self._track("E*Kp", EK)
        P = np.clip(EK >> 8, -self.pcl, self.pcl)
        if self.kd_on:                                   # 0x29E5E..0x29F06: D on the full error, E_prev window 768000
            r27 = np.where(np.abs(self.Eprev) <= 768000, self.Eprev, E)
            D = np.clip(((E - r27) * self.kdLUT[np.asarray(idx, np.int64)]) >> 3, -self.dcl, self.dcl)
            self.Eprev = E if bail is None else np.where(bail, 0x7FFFFFFF, E)
            raw = P + D
        else:
            raw = P
        S = np.clip((raw * m) >> 8, -self.scl, self.scl)
        if bail is not None:
            S = np.where(bail, 0, S)
            r26 = np.where(bail, 0, r26)
        L2 = ((self.la * self.L) >> 10) + ((S * self.lb) >> 10)
        y = (self.L + L2) >> 5
        self.L = L2
        T = np.clip((y * self.g) >> 15, -self.tcl, self.tcl)
        if bail is not None:
            self.live = ~bail          # sentinel 2 after a bail: the next tick reads s as 0
        else:
            self.live = np.ones(self.B, bool)
        return T, r26, P


# ----------------------------------------------------------------------------------------------------------------------
# linear transfers (my own derivation from the listing; z = e^{jwT}, 1 kHz)
# ----------------------------------------------------------------------------------------------------------------------
def lane_T_per_x(c, f, b=None, m=254, kd=None, kp=None):
    """T/x (tap-sign T per x count) at sp = 0, clamps off.  fb: s = (b/1024) x / (1 - a/1024 z^-1);
    r26 = (1 -/+ z^-1) s ; E = -r26 ; P = Kp/256 E (+ D = Kd/8 (1 - z^-1) E) ; S = m/256 P ;
    lag: y = (lb/1024)(1 + z^-1) / (32 (1 - la/1024 z^-1)) S ; T = gain/32768 y."""
    b = c["b"] if b is None else b
    zi = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    sfb = (b / 1024.0) / (1 - (c["a"] / 1024.0) * zi)
    r = sfb * ((1 - zi) if c["op"] == "diff" else (1 + zi))
    E = -r
    kpv = (c["kpY"][0] if kp is None else kp) / 256.0
    if kd is None:
        kd = c["kdY"][0] if (c.get("dcl", 0) and c.get("kdY")) else 0
    kdv = kd / 8.0
    PD = (kpv + kdv * (1 - zi)) * E
    S = m / 256.0 * PD
    y = (c["lb"] / 1024.0) * (1 + zi) / (32.0 * (1 - (c["la"] / 1024.0) * zi)) * S
    return y * c["gain"] / 32768.0, PD


def rate_former(f, w=3):
    """x = 8 * (th[n] - th[n-w]) / (w dt) as a transfer from theta (deg) to x: 8 (1 - z^-w)/(w dt)."""
    zi = np.exp(-2j * np.pi * np.asarray(f, float) * DT)
    return 8.0 * (1 - zi ** w) / (w * DT)


def opposing_T_per_omega(c, f, b=None, w=3, extra_delay_ms=0.0):
    """torque OPPOSING wheel motion per deg/s (0 deg = damping, +90 inertia, -90 spring/anti-damping side).
    omega -> theta = omega/s -> x_lane = -rate_former(theta) -> T (tap) -> u = -T.  Opposing = -u/omega = T/omega...
    u = -T and T = C * x_lane = C * (-RF * omega/s)  =>  u = C RF omega / s  => opposing = -u/omega = -C RF / s."""
    f = np.asarray(f, float)
    s = 2j * np.pi * f
    C, _ = lane_T_per_x(c, f, b)
    return -C * rate_former(f, w) / s * np.exp(-s * extra_delay_ms * 1e-3)


# ----------------------------------------------------------------------------------------------------------------------
# continuous plant (my own): rigid J s^2 + b s + k, or collocated two-mass (motor side J_m carries the actuator and the
# sensor; wheel side J_w through spring K and damper c).  Transport delay tau on the actuator.
# ----------------------------------------------------------------------------------------------------------------------
def plant_theta_per_u(p, f):
    s = 2j * np.pi * np.asarray(f, float)
    J, bb, k = p["J"], p["b"], p["k"]
    if p.get("f2", 0) > 0:
        r2 = p["r2"]
        Jw = J * r2
        Jm = J - Jw
        mu = Jm * Jw / J
        K = (2 * np.pi * p["f2"]) ** 2 * mu
        cc = 2 * p["zeta2"] * np.sqrt(K * mu)
        Zw = (cc * s + K) * Jw * s ** 2 / (Jw * s ** 2 + cc * s + K)
        G = 1.0 / (Jm * s ** 2 + bb * s + k + Zw)
    else:
        G = 1.0 / (J * s ** 2 + bb * s + k)
    return G * np.exp(-s * p.get("tau_ms", 2) * 1e-3)


def inner_L(c, p, f, b=None, m=254):
    """inner return ratio with the 1/(1+L) convention: loop gain around u:  u = -T, T = C x_lane, x_lane = -RF theta,
    theta = P u (ZOH at 1 kHz included)  =>  u = C RF P u  => loop transfer G_loop = C RF P zoh, L = -G_loop."""
    f = np.asarray(f, float)
    C, _ = lane_T_per_x(c, f, b, m)
    zoh = np.exp(-1j * np.pi * f * DT) * np.sinc(f * DT)
    return -(C * rate_former(f, p.get("w", 3)) * plant_theta_per_u(p, f) * zoh)


def margins(f, L):
    mag = np.abs(L)
    S = 1.0 / (1.0 + L)
    out = dict(Ms=float(np.max(np.abs(S))), fMs=float(f[int(np.argmax(np.abs(S)))]))
    ang = np.angle(L)
    # gain margin: where L crosses the negative real axis (Im L changes sign with Re L < 0)
    gm = []
    for i in np.flatnonzero(np.diff(np.sign(L.imag)) != 0):
        t = L.imag[i] / (L.imag[i] - L.imag[i + 1])
        Lc = L[i] + t * (L[i + 1] - L[i])
        if Lc.real < 0:
            gm.append((float(f[i]), float(1.0 / max(abs(Lc.real), 1e-12))))
    out["GM"] = min([g for _, g in gm], default=float("inf"))
    out["fGM"] = min(gm, key=lambda t: t[1])[0] if gm else float("nan")
    pm = []
    for i in np.flatnonzero(np.diff(np.sign(mag - 1.0)) != 0):
        pm.append((float(f[i]), float(180.0 - abs(np.degrees(ang[i])))))    # angle in (-180, 180]
    out["PM"] = min([q for _, q in pm], default=float("inf"))
    out["xover"] = [q for q, _ in pm]
    out["minReL"] = float(np.min(L.real))
    return out


# ----------------------------------------------------------------------------------------------------------------------
# state-space closed loop (my own): continuous plant discretised EXACTLY (matrix exponential, ZOH) at 1 kHz, plus the
# rate former history, the lane filters and an integer-tick transport delay.  sp = 0, clamps/floors off.
# ----------------------------------------------------------------------------------------------------------------------
def closed_poles(c, p, b=None, m=254, lane_on=True, kd=None):
    """kd: None -> use the cells' Kd (Kd bank knot 0 if the D clamp is non-zero, else 0)."""
    from scipy.linalg import expm
    b = c["b"] if b is None else b
    if kd is None:
        kd = c["kdY"][0] if (c.get("dcl", 0) and c.get("kdY")) else 0
    kdv = kd / 8.0
    J, bb, k = p["J"], p["b"], p["k"]
    two = p.get("f2", 0) > 0
    if two:
        r2 = p["r2"]; Jw = J * r2; Jm = J - Jw; mu = Jm * Jw / J
        K = (2 * np.pi * p["f2"]) ** 2 * mu; cc = 2 * p["zeta2"] * np.sqrt(K * mu)
        # states: th, om, thw, omw ; input u on motor side
        Ac = np.array([[0, 1, 0, 0],
                       [-(k + K) / Jm, -(bb + cc) / Jm, K / Jm, cc / Jm],
                       [0, 0, 0, 1],
                       [K / Jw, cc / Jw, -K / Jw, -cc / Jw]], float)
        Bc = np.array([0, 1 / Jm, 0, 0], float)
    else:
        Ac = np.array([[0, 1], [-k / J, -bb / J]], float)
        Bc = np.array([0, 1 / J], float)
    npl = Ac.shape[0]
    M = np.zeros((npl + 1, npl + 1)); M[:npl, :npl] = Ac * DT; M[:npl, npl] = Bc * DT
    E_ = expm(M)
    Ad, Bd = E_[:npl, :npl], E_[:npl, npl]
    w = p.get("w", 3)
    tau = int(round(p.get("tau_ms", 2)))
    # state vector: plant(npl) | hist th[n-1..n-w] (w) | s | L | Eprev | Tq[n-1..n-tau] (tau)
    ih = npl; is_ = ih + w; iL = is_ + 1; iE = iL + 1; iT = iE + 1
    N = iT + tau
    a_, b_ = c["a"] / 1024.0, b / 1024.0
    kp = c["kpY"][0] / 256.0
    la, lb, G = c["la"] / 1024.0, c["lb"] / 1024.0, c["gain"] / 32768.0
    A = np.zeros((N, N))
    for j in range(N):
        z = np.zeros(N); z[j] = 1.0
        th = z[0]
        xl = -8.0 * (th - z[ih + w - 1]) / (w * DT)
        s, L, Ep = z[is_], z[iL], z[iE]
        if lane_on:
            s_new = a_ * s + b_ * xl
            r26 = (s_new - s) if c["op"] == "diff" else (s_new + s)
            Ecur = -r26
            S = (m / 256.0) * (kp * Ecur + kdv * (Ecur - Ep))
            L_new = la * L + lb * S
            T = G * (L + L_new) / 32.0
        else:
            s_new, L_new, T, Ecur = s, L, 0.0, 0.0
        Tapp = z[iT + tau - 1] if tau > 0 else T
        u = -Tapp
        zn = np.zeros(N)
        zn[:npl] = Ad @ z[:npl] + Bd * u
        zn[ih] = th
        zn[ih + 1:ih + w] = z[ih:ih + w - 1]
        zn[is_], zn[iL], zn[iE] = s_new, L_new, Ecur
        if tau > 0:
            zn[iT] = T
            zn[iT + 1:iT + tau] = z[iT:iT + tau - 1]
        A[:, j] = zn
    ev = np.linalg.eigvals(A)
    modes = []
    for zp in ev:
        if abs(zp) < 1e-9:
            continue
        sp_ = np.log(zp) / DT
        if sp_.imag >= -1e-9:
            fr = abs(sp_.imag) / (2 * np.pi)
            zeta = -sp_.real / abs(sp_) if abs(sp_) > 0 else 1.0
            modes.append((float(fr), float(zeta)))
    modes.sort()
    return modes, float(np.max(np.abs(ev)))
