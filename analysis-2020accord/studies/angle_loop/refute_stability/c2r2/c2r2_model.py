# -*- coding: utf-8 -*-
r"""c2r2_model.py -- INDEPENDENT stability model for the C2 rev 2 refutation (stability lens), 2026-10-01.

ANALYSIS ONLY.  Builds no image, flashes nothing, sends nothing.

Written by the C2-rev2 STABILITY refuter (a subagent).  It imports NOTHING from the designers' loop code
(ds_model / ds_lane / score_freq / c1_lib / stab_lin / harness_freq / r2a_*).  It reads:
  * the V295 image bytes (cals LE, sha asserted)                                   -- lane constants
  * the cave hex files the two revisers published (table rows parsed from the bytes; the table address is
    read from the cave's own `mov imm32,r9`)                                        -- the G(v) walk
  * the r71b plant identification data (v295/plant/_scratch/p5c.json, p5b_ms.json) -- the plant family
and builds the loop from the lane's instruction-level description (TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path,
lane_mirror_v295.lane_tick, the designs' cave listings) and my own Ghidra reads this session:
  FUN_00041464  gp-0x6abe = EMA(1024*gp-0x4f50) >> 10, alpha = u16 cal 0xC643C / 128 = 37/128  (slot 0, before the lane)
  FUN_0003f776  gp-0x6a56 = pol * ((gp-0x6abe * 48 * u16 0xC613A=1159) >> 15), clamp +-12000, zero if invalid (slot 4)
  FUN_00068fbe  gp-0x4f50 = an IRQ-protected snapshot of gp-0x29c4 (FUN_00068f52: 2-sample mean of the resolver delta)
  0x2A174..0x2A1FE (V294, dry run)  o' = (ob*S>>10) + (oa*o>>10); y = (o + o') >> 5; y*ramp>>15; *(fwd*pol)>>15

Two models of the SAME loop:
  (A) EXACT PERIODIC: the 1 kHz lane written tick by tick as a linear map on the full state (plant ZOH-discretised,
      transport delay line, the EMA, the held angle / held rate refreshed at slot 4 AFTER the lane, the 2-tap r26, the
      integrator, the output lag).  10-tick monodromy -> rho, least-damped poles; gain scaling -> exact GM (up AND down);
      extra delay -> exact delay margin.
  (B) AVERAGED-HOLD LTI: the hold replaced by its exact fundamental (1/10) sum z^-a, a = 1+e..10+e -> L(e^jw), PM over
      every |L|=1 crossing, LTI GM, |Tc|, |Tref|, Re(T/omega), M20, L20 (the brief's GATE-2 quantities).

Sign/unit frame: theta deg (+left, the gp-0x6a00 frame / 10), omega deg/s, u plant torque in T counts (+left).  The lane
sum S (S counts) maps to u by +fade*Hout*fwd (the pol / 0x14A sign chain is taken as the negative-feedback one -- if it
were not, P itself would be positive feedback and every candidate would fail at once; that is the in-flight R1 check).
  E'  = g * (160 theta_sp - 80 (th_h[n] + th_h[n-1]))         g = G(v)/256   (E = 4 sp - r26, a=0 b=8192, add)
  I  += (Ki/32768) E'   (I>>7 after e5 = E'>>5, *Ki >> 3)       P = (Kp/256) E'
  D(fresh, P-type) = (Kd/8) * gp-0x6abe = (Kd/8) * ABE * r     ABE = -8/(48*1159/32768) = -4.7121 counts per deg/s
  D(held,  F-type) = -(Kd/8) * x_h,  x_h = 8 * r(slot sample)  (1.6978 * 4.7121 = 8.0000; pol = -1 makes both signs agree)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import scipy.linalg as sla

KIT = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod")
FW = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
V295_IMG = FW / "analysis-2020accord" / (
    "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
    "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
V295_SHA = "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
AL = KIT / "analysis-2020accord" / "studies" / "angle_loop"
PLANT = KIT / "analysis-2020accord" / "studies" / "v295" / "plant" / "_scratch"
TS = 1e-3
SLOT = 4                 # slot-4 refresh on n % 10 == 4, AFTER the lane (TRACE angle sec 1.3)

# ----------------------------------------------------------------------------------------------------------------------
# lane constants, read LE from the V295 image
# ----------------------------------------------------------------------------------------------------------------------
_img = V295_IMG.read_bytes()
assert hashlib.sha256(_img).hexdigest() == V295_SHA
_u16 = lambda a: struct.unpack_from("<H", _img, a)[0]   # noqa: E731
_i16 = lambda a: struct.unpack_from("<h", _img, a)[0]   # noqa: E731
OA, OB = _i16(0xC63EC), _u16(0xC63EE)                    # 992, 507
FWD = _i16(0xC6CD0)                                      # 5346
ALPHA = _u16(0xC643C) / 128.0                            # 37/128
K1159 = _u16(0xC613A)                                    # 1159
V295_A, V295_B = _i16(0xC63E8), _u16(0xC63EA)            # 1011, 1050
assert (OA, OB, FWD, _u16(0xC643C), K1159, V295_A, V295_B) == (992, 507, 5346, 37, 1159, 1011, 1050)
X_PER_ABE = 48.0 * K1159 / 32768.0                       # 1.69781 x counts per gp-0x6abe count
ABE = -8.0 / X_PER_ABE                                   # gp-0x6abe counts per deg/s (pol = -1, x = +8/deg/s)
FADE = 254.0 / 256.0                                     # ((255*255)&0xFFFF)>>8 hands off


# ----------------------------------------------------------------------------------------------------------------------
# cave tables, parsed from the published hex (the bytes, not the docs)
# ----------------------------------------------------------------------------------------------------------------------
def cave_table(hexpath: Path, load=0xC4C00):
    bs = bytes(int(t, 16) for t in hexpath.read_text().split())
    # find the 6-byte `mov imm32, r9` (hw1 0x0629) and read the table address from it
    for i in range(0, len(bs) - 6, 2):
        if bs[i] == 0x29 and bs[i + 1] == 0x06:
            tbl = struct.unpack_from("<I", bs, i + 2)[0]
            break
    else:
        raise ValueError("no mov imm32,r9")
    off = tbl - load
    rows = []
    while True:
        X, G, S = struct.unpack_from("<HHh", bs, off)
        rows.append((X, G, S))
        off += 6
        if X == 0xFFFF:
            break
    assert off == len(bs), (hexpath.name, off, len(bs))
    return rows, tbl, hashlib.sha256(bs).hexdigest()


def walk_G(rows, v_counts: int) -> int:
    """the cave's own walk (listing 0xC4C16..0xC4C50): v <= X0 -> G0; else first row i with v <= X(i+1) -> segment i."""
    v = v_counts & 0xFFFF
    if not (v > rows[0][0]):
        return rows[0][1]
    i = 0
    while True:
        if v <= rows[i + 1][0]:
            X, G, S = rows[i]
            dv = v - X
            return G + ((dv * S) >> 12)
        i += 1


def spd_counts(v_mps: float) -> int:
    """gp-0x6a5e = 64 counts per km/h (EVIDENCE in the trace); integer as the firmware holds it."""
    return int(math.floor(v_mps * 3.6 * 64.0 + 1e-9))


# ----------------------------------------------------------------------------------------------------------------------
# designs (from the two revision pages + their hex)
# ----------------------------------------------------------------------------------------------------------------------
@dataclass
class Design:
    name: str
    hexfile: str | None
    dkind: str            # 'fresh' (gp-0x6abe in the cave, +Kd) | 'held' (gp-0x6a56 in place, -Kd) | 'v295' | 'v294'
    kp: float = 112.0
    ki: float = 56.0
    kd: float = 34.0
    rows: list = field(default_factory=list)
    tbl_addr: int = 0
    sha: str = ""

    def G(self, v):
        return walk_G(self.rows, spd_counts(v)) if self.rows else 256


def load_designs():
    c2a = AL / "c2" / "rev2A"
    ds = AL / "panel" / "D-structure"
    out = {}
    for nm, hf, dk, kd in (("P2", c2a / "c2_cave_P2.hex", "fresh", 34), ("F2", c2a / "c2_cave_F2.hex", "held", 20),
                           ("D2a", ds / "ds_cave_D2a.hex", "fresh", 34), ("B0r", ds / "ds_cave_B0r.hex", "held", 20)):
        rows, tbl, sha = cave_table(hf)
        out[nm] = Design(nm, str(hf), dk, kd=kd, rows=rows, tbl_addr=tbl, sha=sha)
    return out


# ----------------------------------------------------------------------------------------------------------------------
# plant family (r71b ident data; member definitions from the brief)
# ----------------------------------------------------------------------------------------------------------------------
VC = np.array([3.1, 8.0, 11.9, 17.0, 26.9])
BANDS = ("0-5", "5-10", "10-15", "15-22", "22+")
_rows = json.load(open(PLANT / "p5c.json"))
PROF = {}
for r in _rows:
    PROF.setdefault(r["J"], [None] * 5)[r["band"]] = (r["b"], r["k"])
PROF = {J: (np.array([x[0] for x in v]), np.array([x[1] for x in v])) for J, v in PROF.items()}
_ms = json.load(open(PLANT / "p5b_ms.json"))["nominal"]
MSF = {k: np.array([_ms[b][k]["val"] for b in BANDS]) for k in ("J", "b", "k")}
B_FLOOR = 0.7 * 4.94


def _interpJ(J):
    if J in PROF:
        return PROF[J]
    js = sorted(PROF)
    lo = max(j for j in js if j < J)
    hi = min(j for j in js if j > J)
    w = (J - lo) / (hi - lo)
    return tuple((1 - w) * a + w * b for a, b in zip(PROF[lo], PROF[hi]))


def _at(arr, v):
    return float(np.interp(v, VC, arr))


@dataclass
class Plant:
    J: float
    b: float
    k: float
    d: int = 2            # transport ticks
    ea: int = 0           # extra hold age (0 or 10)
    f2: float = 0.0       # two-mass option
    z2: float = 0.05
    r2: float = 0.2
    conv: str = "mu"      # 'mu' : free-free resonance at f2 (the gate's two_mass_mu) | 'jw': wheel-side anti-res at f2
    ddelay: float = 0.0   # extra fractional delay on the D operand's rate (ticks) - rate-former sensitivity
    note: str = ""


def member(name: str, v: float) -> Plant:
    """Brief's credible set.  Names compose with '*' (one damping, one inertia, one delay, two-mass), '+h10' = slot 4
    10 ticks late (ages 11..20), '+h0' = slot 4 ages 0..9 (before the lane)."""
    ea = 0
    if name.endswith("+h10"):
        name, ea = name[:-4], 10
    elif name.endswith("+h0"):
        name, ea = name[:-3], -1
    parts = name.split("*")
    damp, inert, tau, mode = "", "", 2, None
    for p in parts:
        if p in ("nominal", ""):
            continue
        if p in ("b_lo", "b_lo_knot", "b_hi", "b_q", "b_q0", "bq10", "bc", "b/1.9"):
            damp = p
        elif p in ("J_lo", "J_hi", "J_hi2", "J1.0", "J1.3", "ms_free", "J0.3"):
            inert = p
        elif p in ("tau0", "tau6", "tau10"):
            tau = int(p[3:])
        elif p.startswith("mode"):
            mode = p
        else:
            raise KeyError(p)
    # inertia refit
    if inert == "ms_free":
        J, b, k = _at(MSF["J"], v), _at(MSF["b"], v), _at(MSF["k"], v)
    elif inert == "J0.3":                      # the refuter-named b_lo*J0.3: nominal fit, J overridden
        bb, kk = PROF[0.2]
        J, b, k = 0.3, _at(bb, v), _at(kk, v)
    else:
        Jr = {"": 0.2, "J_lo": 0.1, "J_hi": 0.5, "J_hi2": 0.8, "J1.0": 1.0, "J1.3": 1.3}[inert]
        bb, kk = _interpJ(Jr)
        J, b, k = Jr, _at(bb, v), _at(kk, v)
    # damping corner (applied to the refit's own b)
    if damp in ("b_lo", "bc"):
        b = b * (1 / 1.8 if v >= 10 else 0.7)
    elif damp == "b_lo_knot":                  # v294_plant FAM['b_lo']: factors on the knots, interpolated in speed
        bb, _ = _interpJ(J) if inert not in ("ms_free", "J0.3") else (PROF[0.2][0], None)
        fac = np.where(VC >= 10, 1 / 1.8, 0.7)
        b = _at(bb * fac, v) if inert not in ("ms_free",) else _at(MSF["b"] * fac, v)
    elif damp == "b/1.9":
        b = b * (1 / 1.9 if v >= 10 else 0.7)
    elif damp == "b_hi":
        b = b * 1.5
    elif damp == "b_q":
        b = max(0.25 * b, B_FLOOR) if v >= 12.5 else b
    elif damp == "bq10":
        b = max(0.25 * b, B_FLOOR) if v >= 10.0 else b
    elif damp == "b_q0":
        b = 0.25 * b if v >= 12.5 else b
    pl = Plant(J, b, k, d=tau, ea=ea)
    if mode:
        pl.f2, pl.z2 = (13.0, 0.10) if mode == "mode13" else (20.0, 0.05) if mode == "mode20" else (0, 0)
    return pl


def light_b(v):
    T_PER_U = 2625.4
    kv = [2, 4, 6, 8, 10, 12.5, 15, 17.5, 20, 23, 28]
    ku = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134]
    k = np.interp(VC, kv, ku) * T_PER_U
    return Plant(8e-5 * T_PER_U, 6e-4 * T_PER_U, _at(k, v), d=2)


def plant_ct(pl: Plant):
    """continuous (A, B, Ct, Cw).  Sensed angle / rate are MOTOR side (collocated); u acts on the motor mass."""
    if pl.f2 <= 0:
        A = np.array([[0.0, 1.0], [-pl.k / pl.J, -pl.b / pl.J]])
        B = np.array([[0.0], [1.0 / pl.J]])
        return A, B, np.array([1.0, 0.0]), np.array([0.0, 1.0])
    Jw = pl.r2 * pl.J
    Jm = pl.J - Jw
    if pl.conv == "mu":
        mu = Jm * Jw / pl.J
        K = (2 * np.pi * pl.f2) ** 2 * mu
        c = 2 * pl.z2 * np.sqrt(K * mu)
    else:  # 'jw': the wheel side alone rings at f2 (anti-resonance of the motor-side FRF)
        K = (2 * np.pi * pl.f2) ** 2 * Jw
        c = 2 * pl.z2 * np.sqrt(K * Jw)
    A = np.array([[0, 1, 0, 0],
                  [-(pl.k + K) / Jm, -(pl.b + c) / Jm, K / Jm, c / Jm],
                  [0, 0, 0, 1],
                  [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    return A, B, np.array([1.0, 0, 0, 0]), np.array([0, 1.0, 0, 0])


def zoh(A, B, T=TS):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A * T
    M[:n, n:] = B * T
    E = sla.expm(M)
    return E[:n, :n], E[:n, n:]


def zoh_frac(A, B, eps):
    """input switches at eps*T inside the tick: x+ = Phi x + G_old u_old + G_new u_new"""
    Phi, _ = zoh(A, B)
    if eps <= 0:
        return Phi, np.zeros_like(B), zoh(A, B)[1]
    P1, G1 = zoh(A, B, eps * TS)          # [0, eps T) under u_old
    P2, G2 = zoh(A, B, (1 - eps) * TS)    # [eps T, T) under u_new
    return Phi, P2 @ G1, G2


# ----------------------------------------------------------------------------------------------------------------------
# (A) EXACT PERIODIC MODEL
# ----------------------------------------------------------------------------------------------------------------------
class Periodic:
    """state layout built at construction; tick(n, X, sp) is linear in (X, sp) and works on column blocks."""

    def __init__(self, des: Design, pl: Plant, v: float, gain=1.0, extra_delay=0.0, noI=False, kd_scale=1.0):
        self.des, self.pl, self.v = des, pl, v
        A, B, Ct, Cw = plant_ct(pl)
        tot = pl.d + extra_delay
        dint = int(math.floor(tot + 1e-12))
        eps = tot - dint
        self.Phi, self.Gold, self.Gnew = zoh_frac(A, B, eps)
        self.np = A.shape[0]
        self.Ct, self.Cw = Ct, Cw
        self.dint = dint
        self.gain = gain
        self.g = des.G(v) / 256.0
        self.kp = des.kp / 256.0
        self.ki = 0.0 if noI else des.ki / 32768.0
        self.kd = des.kd * kd_scale
        self.ea = pl.ea
        # rate seen by the EMA: omega(nT - ddelay*T) approximated by linear interpolation between samples
        self.ddelay = pl.ddelay
        idx = {}
        n0 = 0

        def alloc(nm, k=1):
            nonlocal n0
            idx[nm] = slice(n0, n0 + k)
            n0 += k
        alloc("xp", self.np)
        alloc("r")          # EMA (deg/s)
        alloc("thh")        # held angle (deg)
        alloc("thhp")       # held angle used on the previous tick (s_old)
        alloc("xh")         # held rate (x counts = 8 * deg/s) -- held designs and the V29x references
        alloc("I")          # integrator (S counts)
        alloc("o")          # output lag state
        alloc("s")          # V29x fb filter state
        alloc("Tb", max(dint + 1, 1))   # T[n-1] .. T[n-dint-1]
        alloc("wprev")      # omega[n-1] (rate-former delay sensitivity)
        if self.ea > 0:
            alloc("thb", self.ea)        # theta[n-1] .. theta[n-ea]
            alloc("rb", self.ea)
        self.idx, self.n = idx, n0

    def tick(self, n, X, sp):
        """X: (nstate, m) ; sp: (m,) or scalar.  Returns X_next."""
        ix = self.idx
        des = self.des
        Y = X.copy()
        xp = X[ix["xp"]]
        th = self.Ct @ xp
        w = self.Cw @ xp
        wprev = X[ix["wprev"]][0]
        if self.ddelay > 0:
            a = min(self.ddelay, 1.0)
            w_rf = (1 - a) * w + a * wprev
        else:
            w_rf = w
        r = X[ix["r"]][0]
        r_new = (1 - ALPHA) * r + ALPHA * w_rf
        thh, thhp, xh = X[ix["thh"]][0], X[ix["thhp"]][0], X[ix["xh"]][0]
        slot = (n % 10) == SLOT
        if slot and self.ea < 0:          # ages 0..9: slot 4 refreshes BEFORE the lane on the slot tick
            thh = th
            xh = 8.0 * r_new
        I = X[ix["I"]][0]
        o = X[ix["o"]][0]
        if des.dkind in ("fresh", "held"):
            Ep = self.g * (160.0 * sp - 80.0 * (thh + thhp))
            I_new = I + self.ki * Ep
            P = self.kp * Ep
            if des.dkind == "fresh":
                D = (self.kd / 8.0) * ABE * r_new
            else:
                D = -(self.kd / 8.0) * xh
            S = I_new + P + D
            s_new = 0.0 * X[ix["s"]][0]          # unused by the angle lane: keep it out of the spectrum
            if self.ki == 0.0:
                I_new = 0.0 * I                   # frozen / absent integrator = a constant bias, not a mode
        else:  # V295 / V294 reference rate loops (hold on x, diff fb filter, flat Kp 960, map setpoint ignored)
            bfb = V295_B if des.dkind == "v295" else 567
            s = X[ix["s"]][0]
            s_new = (V295_A / 1024.0) * s + (bfb / 1024.0) * xh
            r26 = s_new - s
            S = (960.0 / 256.0) * (-r26)
            I_new = 0.0 * I
        Sf = FADE * S * self.gain
        o_new = (OA / 1024.0) * o + (OB / 1024.0) * Sf
        y = (o + o_new) / 32.0
        T = (FWD / 32768.0) * y
        # slot 4 refresh AFTER the lane (ages 1..10), or 10 ticks late (+h10, ages 11..20)
        Y[ix["thhp"]] = thh
        Y[ix["thh"]] = thh
        Y[ix["xh"]] = xh
        if slot and self.ea >= 0:
            if self.ea > 0:
                Y[ix["thh"]] = X[ix["thb"]][self.ea - 1]
                Y[ix["xh"]] = 8.0 * X[ix["rb"]][self.ea - 1]
            else:
                Y[ix["thh"]] = th
                Y[ix["xh"]] = 8.0 * r_new
        Y[ix["r"]] = r_new
        Y[ix["I"]] = I_new
        Y[ix["o"]] = o_new
        Y[ix["s"]] = s_new
        Y[ix["wprev"]] = w
        # transport: u applied during this tick = T[n-dint] (switching at eps from T[n-dint-1])
        Tb = X[ix["Tb"]]                         # Tb[0] = T[n-1], Tb[j] = T[n-1-j]
        u_new = T if self.dint == 0 else Tb[self.dint - 1]
        u_old = Tb[self.dint] if self.dint < Tb.shape[0] else Tb[-1]
        if self.dint == 0:
            u_old = Tb[0]
        Y[ix["xp"]] = self.Phi @ xp + np.outer(self.Gnew[:, 0], u_new) + np.outer(self.Gold[:, 0], u_old)
        Tb_new = np.vstack([T[None, :], Tb[:-1]])
        Y[ix["Tb"]] = Tb_new
        if self.ea > 0:
            thb, rb = X[ix["thb"]], X[ix["rb"]]
            Y[ix["thb"]] = np.vstack([th[None, :], thb[:-1]])
            Y[ix["rb"]] = np.vstack([r_new[None, :], rb[:-1]])
        return Y

    def tick_matrix(self, n):
        I = np.eye(self.n)
        A = self.tick(n, I, np.zeros(self.n))
        b = self.tick(n, np.zeros((self.n, 1)), np.ones(1))[:, 0]
        return A, b

    def monodromy(self):
        M = np.eye(self.n)
        Bl = np.zeros(self.n)
        mats = []
        for n in range(10):
            A, b = self.tick_matrix(n)
            mats.append((A, b))
            M = A @ M
            Bl = A @ Bl + b
        self._mats = mats
        return M, Bl

    def rho_poles(self):
        M, _ = self.monodromy()
        lam = np.linalg.eigvals(M)
        rho = float(np.max(np.abs(lam)))
        # continuous-equivalent poles (10 ms step); report the least-damped oscillatory one below 50 Hz
        lam_nz = lam[np.abs(lam) > 1e-9]
        s = np.log(lam_nz.astype(complex)) / (10 * TS)
        f = np.abs(s.imag) / (2 * np.pi)
        zeta = -s.real / np.maximum(np.abs(s), 1e-12)
        osc = (f > 0.2) & (f < 49.9)
        if osc.any():
            j = int(np.argmin(np.where(osc, zeta, 9)))
            return rho, float(zeta[j]), float(f[j]), lam
        return rho, float("nan"), float("nan"), lam


def exact_stable(des, pl, v, **kw):
    return Periodic(des, pl, v, **kw).rho_poles()[0] < 1.0 - 1e-9


def exact_gm_up(des, pl, v, hi=64.0, tol=0.01, **kw):
    """smallest gain k > 1 with rho >= 1 (dB).  inf if stable up to `hi`."""
    if not exact_stable(des, pl, v, gain=1.0, **kw):
        return -np.inf
    lo, h = 1.0, hi
    if exact_stable(des, pl, v, gain=h, **kw):
        # scan for an intermediate instability window too
        for k in (1.5, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48):
            if not exact_stable(des, pl, v, gain=k, **kw):
                h = k
                break
        else:
            return np.inf
    # first unstable k on a coarse ladder below h
    ks = np.geomspace(1.0, h, 24)[1:]
    for k in ks:
        if not exact_stable(des, pl, v, gain=k, **kw):
            h = k
            break
        lo = k
    while h / lo > 1 + tol:
        m = math.sqrt(lo * h)
        if exact_stable(des, pl, v, gain=m, **kw):
            lo = m
        else:
            h = m
    return 20 * math.log10(lo)


def exact_gm_down(des, pl, v, lo_k=0.02, **kw):
    """largest gain k < 1 with rho >= 1 (dB, negative) on a ladder down to lo_k; -inf dB if stable all the way."""
    for k in np.geomspace(1.0, lo_k, 30)[1:]:
        if not exact_stable(des, pl, v, gain=k, **kw):
            return 20 * math.log10(k)
    return -np.inf


def exact_delay_margin(des, pl, v, hi=40.0, tol=0.05, **kw):
    """extra transport delay (ms) at which rho reaches 1."""
    if not exact_stable(des, pl, v, **kw):
        return 0.0
    lo, h = 0.0, None
    for dd in (0.5, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 40, 50, 60, 70, 80, 100, 130, 160, 200):
        if not exact_stable(des, pl, v, extra_delay=dd, **kw):
            h = dd
            break
        lo = dd
    if h is None:
        return np.inf
    while h - lo > max(tol, 0.002 * h):
        m = 0.5 * (lo + h)
        if exact_stable(des, pl, v, extra_delay=m, **kw):
            lo = m
        else:
            h = m
    return lo


# ----------------------------------------------------------------------------------------------------------------------
# (B) AVERAGED-HOLD LTI MODEL (closed form)
# ----------------------------------------------------------------------------------------------------------------------
FG = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 3000),
                               [0.02, 0.05, 0.1, 0.2, 0.5, 1, 1.6, 2, 2.5, 3, 5, 7, 10, 13, 15, 16, 17, 20, 25, 30]]))


def q_of(f):
    return np.exp(-2j * np.pi * np.asarray(f, float) * TS)    # z^-1


def H_avg(f, ea):
    q = q_of(f)
    lo = 0 if ea < 0 else 1 + ea
    return np.mean([q ** a for a in range(lo, lo + 10)], axis=0)


def ctl_frf(des: Design, v, f, ea, kd_scale=1.0, ddelay=0.0, noI=False):
    """returns (Cth, Cw, Cref, Kout_nodelay) : S counts per deg (theta), per deg/s (omega), per deg (theta_sp)."""
    q = q_of(f)
    H = H_avg(f, ea)
    ema = ALPHA / (1 - (1 - ALPHA) * q)
    rf = (1 - min(ddelay, 1)) + min(ddelay, 1) * q if ddelay > 0 else 1.0
    Kout = FADE * (FWD / 32768.0) * (OB / 1024.0) * (1 + q) / (32.0 * (1 - (OA / 1024.0) * q))
    if des.dkind in ("fresh", "held"):
        g = des.G(v) / 256.0
        ki = 0.0 if noI else des.ki / 32768.0
        PI = des.kp / 256.0 + ki / (1 - q)
        Cth = -g * 80.0 * (1 + q) * H * PI
        Cref = g * 160.0 * PI * H_avg(f, 0)                  # 0xE4 setpoint: 100 Hz hold, ages 1..10
        if des.dkind == "fresh":
            Cw = (des.kd * kd_scale / 8.0) * ABE * ema * rf
        else:
            Cw = -(des.kd * kd_scale / 8.0) * 8.0 * H * ema * rf
    else:
        bfb = V295_B if des.dkind == "v295" else 567
        filt = (bfb / 1024.0) * (1 - q) / (1 - (V295_A / 1024.0) * q)
        Cth = np.zeros_like(q)
        Cw = -(960.0 / 256.0) * filt * 8.0 * H * ema * rf
        Cref = np.zeros_like(q)
    return Cth, Cw, Cref, Kout


def plant_frf(pl: Plant, f):
    A, B, Ct, Cw = plant_ct(pl)
    Phi, Gam = zoh(A, B)
    z = np.exp(2j * np.pi * np.asarray(f) * TS)
    n = Phi.shape[0]
    M = z[:, None, None] * np.eye(n)[None] - Phi[None]
    X = np.linalg.solve(M, np.broadcast_to(Gam, (len(z), n, 1)))[..., 0]
    return X @ Ct, X @ Cw


def pm_all(f, L):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    pms, fcs = [], []
    for i in np.where((mag[:-1] - 1) * (mag[1:] - 1) <= 0)[0]:
        if mag[i] == mag[i + 1]:
            continue
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        pms.append(((ph[i] + t * (ph[i + 1] - ph[i])) + 180 + 180) % 360 - 180)
        fcs.append(f[i] + t * (f[i + 1] - f[i]))
    return pms, fcs


def gm_lti(f, L):
    """gain margins at every -180 (mod 360) crossing: smallest positive (up) and the largest negative (down)."""
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    mag = np.abs(L)
    up, dn = [], []
    for i in range(len(f) - 1):
        if math.floor((ph[i] + 180) / 360) != math.floor((ph[i + 1] + 180) / 360):
            g = -20 * math.log10(max(mag[i], 1e-12))
            (up if g > 0 else dn).append(g)
    return (min(up) if up else np.inf), (max(dn) if dn else -np.inf)


def lti_metrics(des, pl: Plant, v, f=FG, kd_scale=1.0, noI=False, gain=1.0):
    Pt, Pw = plant_frf(pl, f)
    Cth, Cw, Cref, Ko = ctl_frf(des, v, f, pl.ea, kd_scale=kd_scale, ddelay=pl.ddelay, noI=noI)
    q = q_of(f)
    K = gain * Ko * q ** pl.d
    L = -K * (Cth * Pt + Cw * Pw)
    S = 1 / (1 + L)
    Tc = L * S
    Tr = K * Cref * Pt * S
    pms, fcs = pm_all(f, L)
    gup, gdn = gm_lti(f, L)
    band = (f >= 5) & (f <= 30)
    i20 = int(np.argmin(abs(f - 20)))
    w20 = 2 * np.pi * 20
    out = dict(pm=min(pms) if pms else np.nan, fc=fcs[int(np.argmin(pms))] if pms else np.nan, ncross=len(pms),
               gm_up=gup, gm_dn=gdn, Ms=float(np.abs(S).max()),
               Tc530=20 * math.log10(float(np.abs(Tc[band]).max())),
               Tr530=20 * math.log10(max(float(np.abs(Tr[band]).max()), 1e-12)),
               L20=float(abs(L[i20])), M20=float(abs(Cth[i20] + 1j * w20 * Cw[i20]) / (8 * w20)),
               Tr163=float(np.abs(Tr[(f >= 1.6) & (f <= 3.0)]).max()) if des.dkind in ("fresh", "held") else np.nan,
               hold=float(abs(Tr[int(np.argmin(abs(f - 0.02)))])) if des.dkind in ("fresh", "held") else np.nan)
    return out, (L, Tr, S)


def re_t_over_w(des, v, f, ea, d=2, kd_scale=1.0, ddelay=0.0):
    """controller output impedance, T counts per deg/s, > 0 damps (torque opposing the motion)."""
    Cth, Cw, Cref, Ko = ctl_frf(des, v, f, ea, kd_scale=kd_scale, ddelay=ddelay)
    q = q_of(f)
    w = 2 * np.pi * np.asarray(f)
    u_per_th = Ko * q ** d * (Cth + 1j * w * Cw)      # +left torque per deg of +left motion
    return (-(u_per_th) / (1j * w)).real


V295_REF = Design("V295", None, "v295")
V294_REF = Design("V294", None, "v294")
