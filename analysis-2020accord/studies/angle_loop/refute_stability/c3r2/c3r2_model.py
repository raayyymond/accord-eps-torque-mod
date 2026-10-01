# -*- coding: utf-8 -*-
r"""c3r2_model.py -- the C3-rev2 STABILITY refuter's OWN loop model (2026-10-01).  ANALYSIS ONLY.

Written from the bytes and the decompiled arithmetic, NOT from any designer / scorer / earlier refuter loop code:
  * the V295 cals (OA 992, OB 507, FWD 5346, EMA alpha 37/128, 6a56 scale 1159) read LE from the V295 image (sha asserted)
  * the GB-P / GB-F / G-P48 G(v) tables parsed from the published cave hex via the cave's own `mov imm32, r9`
  * the lane arithmetic per lane_mirror_v295.py (byte-exact mirror, line-annotated) + the C3-rev2 cave listing:
        r26 = 8 th_h[n] + 8 th_h[n-1]           (0.1 deg counts)    E1/E2, a=0 b=8192 sum
        E   = 16 th_sp - r26                                         E4 + displaced shl 2 / sub
        Ep  = (E G) >> 8                                             cave G walk + mul/sar 8
        I  += ((Ep>>5) Ki) >> 3 ; S_I = I >> 7                      Honda 0x29D7C..0x29DB4  (Ki/32768 per tick)
        P   = (Ep Kp) >> 8                                           Honda 0x29E36..
        D   = (Kd op) >> 3, op = gp-0x6abe (fresh EMA)  [P]          OPH 0x29EE0 (D operand = r26 = abe)
            = (-Kd x) >> 3, x = gp-0x6a56 (held, 8/deg/s)  [F]       E5a/E5b
        S   = S_I + P + D ; Sf = f S >> 8 (f = 254 hands-off)
        o'  = (oa o + ob Sf)/1024 ; y = (o + o')/32 ; T = pol 5346 y >> 15 ; u = -T = +FWD y  (pol = -1)
  * plant (v294_plant convention): J th'' + b th' + k th = u(t - d Ts), th deg, u T counts.  Member (J,b,k,d) come from
    the brief's credible-set definitions (c1r2_members.params / FAM['ms_free'] / the two-mass convention) -- the plant
    PARAMETERS are the brief's; the LOOP below is mine.

Two formulations, both mine:
  LTI  : the 100 Hz hold as its fundamental (1/10) sum_a z^-a, plant ZOH-discretised at 1 kHz, sampled channels exact;
         PM / GM / 5-30 Hz peak / Re(T/w) / L20.
  EXACT: the true 10-tick periodic system (hold register refreshed once per 10 ticks at any age offset), built tick by
         tick as a linear map on an explicit state vector; monodromy -> rho and closed-loop poles.  Optional fork
         outer loop (100 Hz integral on the setpoint, 60 ms round trip) as explicit states.

Frames: FA = plant per deg of gp-0x6a00, the motor-frame operand (abe or 6a56) carries kappa; FB = J,b x 1/1.155.
"""
from __future__ import annotations

import hashlib
import math
import os
import struct
import sys
from dataclasses import dataclass, replace
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import numpy as np  # noqa: E402
from scipy.linalg import expm  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]                                     # .../studies/angle_loop
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "angle_loop" / "refute-c3r2-stability"
OUT.mkdir(parents=True, exist_ok=True)
for p in (str(AL / "c1"), str(AL.parent / "v295" / "plant"), str(AL / "refute_stability")):
    if p not in sys.path:
        sys.path.insert(0, p)
import c1r2_members as M2   # noqa: E402   (member PARAMETERS only: the brief's credible-set definitions)

TS = 1e-3
FW_ROOT = Path(os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares"))
V295 = FW_ROOT / "analysis-2020accord" / (
    "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0"
    "-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
_img = V295.read_bytes()
assert hashlib.sha256(_img).hexdigest() == "5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed"
_u16 = lambda a: struct.unpack_from("<H", _img, a)[0]   # noqa: E731
_i16 = lambda a: struct.unpack_from("<h", _img, a)[0]   # noqa: E731
OA, OB = _i16(0xC63EC), _u16(0xC63EE)                    # 992, 507
FWD = _i16(0xC6CD0) / 32768.0                            # 5346/32768
ALPHA = _u16(0xC643C) / 128.0                            # 37/128 (FUN_00041464 EMA)
S6A56 = 48.0 * _u16(0xC613A) / 32768.0                   # 6a56 = pol * abe * 1.6977
ABE_PER = 8.0 / S6A56                                    # |abe| counts per deg/s of the motor-linear rate (4.712)
assert (OA, OB, _i16(0xC6CD0), _u16(0xC643C), _u16(0xC613A)) == (992, 507, 5346, 37, 1159)
FADE0 = 254.0 / 256.0
S_C = 1.155


# ------------------------------------------------------------------------------------------------- tables (from hex)
def cave_rows(path, load=0xC4C00):
    bs = bytes(int(t, 16) for t in Path(path).read_text().split())
    for i in range(0, len(bs) - 6, 2):
        if bs[i] == 0x29 and bs[i + 1] == 0x06:          # mov imm32, r9 (Format VI hw1 0x0629)
            tbl = struct.unpack_from("<I", bs, i + 2)[0]
            break
    off, rows = tbl - load, []
    while True:
        X, G, S = struct.unpack_from("<HHh", bs, off)
        rows.append((X, G, S))
        off += 6
        if X == 0xFFFF:
            break
    return tuple(rows), hashlib.sha256(bs).hexdigest()[:12], len(bs)


def g_walk(vc, rows):
    """the cave's integer walk (ds_asm._walk): flat G0 at v <= X0; G = G(i) + ((v - X(i)) S(i)) >> 12 in segment i."""
    if vc <= rows[0][0]:
        return rows[0][1]
    i = 0
    while not (vc <= rows[i + 1][0]):
        i += 1
    X, G, S = rows[i]
    return G + (((vc - X) * S) >> 12)


def spd_counts(v):
    return int(math.floor(v * 3.6 * 64 + 1e-9))        # gp-0x6a5e, 64 counts per km/h


CAV = AL / "c3" / "rev2B"
ROWS = {}
for nm, fn in (("GB-P", CAV / "c3b_cave_C3B-P_score.hex"), ("GB-F", CAV / "c3b_cave_C3B-F_score.hex"),
               ("G-P48", AL / "c3" / "c3_cave_C3-P.hex"), ("G-F24", AL / "c3" / "c3_cave_C3-F.hex")):
    ROWS[nm] = cave_rows(fn)[0]
# the rows printed on the design page (DESIGN-ANGLE-LOOP-C3-rev2 section 1.3 / rev2-B section 1.3)
PAGE = {"GB-P": ((714, 1178, 1041), (1843, 1465, -6264), (2304, 760, -2033), (2707, 560, 1570), (4032, 1068, 2118),
                 (6198, 2188, 0), (0xFFFF, 2188, 0)),
        "GB-F": ((714, 1009, 892), (1843, 1255, -4753), (2304, 720, -1626), (2707, 560, 1097), (4032, 915, 1953),
                 (6198, 1948, 0), (0xFFFF, 1948, 0))}
for _k, _r in PAGE.items():
    assert ROWS[_k] == _r, (_k, ROWS[_k])


@dataclass(frozen=True)
class Design:
    name: str
    dop: str              # 'fresh' | 'held' | 'none' (D off: rate-invalid PI-only)
    kp: float = 112.0
    ki: float = 40.0
    kd: float = 48.0
    table: str | None = "GB-P"
    a_fb: int = 0          # V295-class rate loop only: fb pole / gain (0xC63E8 / 0xC63EA), 'diff'
    b_fb: int = 0

    def G(self, v):
        if self.table is None:
            return 256.0
        return float(g_walk(spd_counts(v), ROWS[self.table]))


C3R2P = Design("C3-rev2-P", "fresh", 112, 40, 48, "GB-P")
C3R2F = Design("C3-rev2-F", "held", 112, 40, 24, "GB-F")
C3P56 = Design("C3-P(Ki56)", "fresh", 112, 56, 48, "G-P48")          # validation anchor (round-1 C3)
C3F56 = Design("C3-F(Ki56)", "held", 112, 56, 24, "G-F24")
V295D = Design("V295", "v295", 960, 0, 0, None, 1011, 1050)                # x = gp-0x6a56 held, 'diff', Kp 960 flat
V294D = Design("V294", "v295", 960, 0, 0, None, 1011, 567)


# ------------------------------------------------------------------------------------------------- plants
def sat(v):
    return 19.3 + 546.0 * math.exp(-v / 3.01)          # v294_plant.sat_prior (BELIEF, the prior)


def theta_op(v, a, SR=16.0, L=2.83):
    return math.degrees(L * a / v ** 2 * SR)


@dataclass
class Plant:
    J: float
    b: float
    k: float
    d: int
    mode: tuple | None = None      # (f2, zeta2, r2, placement 'mu'|'wheel')

    def ss(self, jb=1.0):
        J, b, k = self.J * jb, self.b * jb, self.k
        if self.mode is None:
            A = np.array([[0.0, 1.0], [-k / J, -b / J]])
            B = np.array([[0.0], [1.0 / J]])
            return A, B, np.array([1.0, 0.0]), np.array([0.0, 1.0])
        f2, z2, r2, plc = self.mode
        Jw = J * r2
        Jm = J - Jw
        mu = Jm * Jw / J
        K = (2 * np.pi * f2) ** 2 * (mu if plc == "mu" else Jw)
        c = 2 * z2 * np.sqrt(K * (mu if plc == "mu" else Jw))
        A = np.array([[0, 1, 0, 0],
                      [-(k + K) / Jm, -(b + c) / Jm, K / Jm, c / Jm],
                      [0, 0, 0, 1],
                      [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
        B = np.array([[0], [1 / Jm], [0], [0]], float)
        return A, B, np.array([1.0, 0, 0, 0]), np.array([0, 1.0, 0, 0])

    def zoh(self, jb=1.0):
        A, B, Cth, Cw = self.ss(jb)
        n = A.shape[0]
        M = np.zeros((n + 1, n + 1))
        M[:n, :n], M[:n, n:] = A * TS, B * TS
        E = expm(M)
        return E[:n, :n], E[:n, n:], Cth, Cw


SINGLE = ("nominal", "J_lo", "J_hi", "b_lo", "b_hi", "tau0", "tau6", "mode13", "mode20", "ms_free")
COMBINED = ("b_lo*J_hi", "b_lo*tau6", "J1.0", "b_q", "b_q*J_hi", "b_q*J1.0", "b_q*tau6")
MSF2 = ("b_lo*ms_free", "b_q*ms_free")
REPORT = ("J1.3", "b_q*J1.3", "J_hi2", "b_lo*J_hi2", "b_lo*ms_free*tau6", "b_q*ms_free*tau6", "b_lo*J_hi*tau6")


def member(name, v):
    """(Plant, extra_age).  Parameters per the brief (c1r2_members / v294_plant FAM); '+h10' = hold ages 11-20."""
    ea = 0
    if name.endswith("+h10"):
        name, ea = name[:-4], 10
    if name in ("mode13", "mode20"):
        J, b, k, d, _ = M2.params("nominal", v)
        f2, z2 = (13.0, 0.1) if name == "mode13" else (20.0, 0.05)
        return Plant(J, b, k, int(d), (f2, z2, 0.2, "mu")), ea
    if "ms_free" in name:
        p = M2.FAM["ms_free"].at(v)
        J, b, k, d = p.J, p.b, p.k, 2
        for q in name.split("*"):
            if q in ("b_lo", "b_q"):
                b = M2._dscale(q, b, v)
            elif q == "tau6":
                d = 6
        return Plant(J, b, k, d), ea
    J, b, k, d, e0 = M2.params(name, v)
    return Plant(J, b, k, int(d)), ea + e0


# ------------------------------------------------------------------------------------------------- LTI FRF
def fgrid(n=3000):
    f = np.unique(np.concatenate([np.logspace(-2.5, math.log10(499.0), n), np.linspace(0.05, 3.0, 1200),
                                  np.linspace(3, 40, 800)]))
    return f


F = fgrid()


def plant_frf(pl: Plant, f, jb=1.0):
    Ad, Bd, Cth, Cw = pl.zoh(jb)
    z = np.exp(2j * np.pi * np.asarray(f) * TS)
    n = Ad.shape[0]
    Mz = z[:, None, None] * np.eye(n)[None] - Ad[None]
    X = np.linalg.solve(Mz, np.broadcast_to(Bd, (len(z), n, 1)))[:, :, 0]
    return X @ Cth, X @ Cw


def zi(f):
    return np.exp(-2j * np.pi * np.asarray(f) * TS)


def Hbar(f, e):
    """mean_{a = 1+e .. 10+e} z^-a  (e = -1: ages 0-9; 0: 1-10; 10: 11-20)."""
    z = zi(f)
    return np.mean([z ** a for a in range(1 + e, 11 + e)], axis=0)


def Kout(f, d, fade=FADE0):
    z = zi(f)
    Hout = (OB / 1024.0) * (1 + z) / (32.0 * (1 - (OA / 1024.0) * z))
    return fade * FWD * Hout * z ** d


def controller(des: Design, v, f, e, kappa, ki=None, kd_scale=1.0, G=None):
    """(Cth, Cw, Cref): u = -(Cth th + Cw w) + Cref th_sp, BEFORE Kout.  th deg, w deg/s of th, th_sp deg."""
    z = zi(f)
    G = des.G(v) if G is None else G
    ki = des.ki if ki is None else ki
    PI = (G / 256.0) * (des.kp / 256.0 + (ki / 32768.0) / (1 - z))
    H = Hbar(f, e)
    Cth = PI * 80.0 * (1 + z) * H
    ema = ALPHA / (1 - (1 - ALPHA) * z)
    if des.dop == "fresh":
        Cw = kd_scale * (des.kd / 8.0) * ABE_PER * kappa * ema
    elif des.dop == "held":
        Cw = kd_scale * (des.kd / 8.0) * 8.0 * kappa * ema * H
    elif des.dop == "v295":
        R = (des.b_fb / 1024.0) * (1 - z) / (1 - (des.a_fb / 1024.0) * z)
        Cw = (des.kp / 256.0) * R * 8.0 * kappa * ema * H
        return 0.0 * z, Cw, 0.0 * z
    else:
        Cw = 0.0 * z
    Cref = PI * 160.0
    return Cth, Cw, Cref


def loop_L(des, pl, v, f=F, e=0, kappa=1.0, jb=1.0, fade=FADE0, ki=None, kd_scale=1.0, tau_o=None, rt=0.060,
           chans=None):
    Pt, Pw = plant_frf(pl, f, jb) if chans is None else chans
    Cth, Cw, Cref = controller(des, v, f, e, kappa, ki=ki, kd_scale=kd_scale)
    K = Kout(f, pl.d, fade)
    L = K * (Cth * Pt + Cw * Pw)
    if tau_o:
        w = 2 * np.pi * np.asarray(f)
        zf = np.exp(-1j * w * 0.01)
        Ko = (0.01 / tau_o) / (1 - zf) * np.exp(-1j * w * rt)      # 100 Hz integral, round trip rt
        L = L + K * Cref * Ko * Pt
    return L, K * Cref * Pt


def pm_gm(L, f=F):
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    s = mag - 1
    idx = np.where((s[:-1] * s[1:] <= 0) & (mag[:-1] != mag[1:]))[0]
    PM, FC = float("inf"), float("nan")
    for i in idx:
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        w = ((p + 180) % 360) - 180
        pm = 180 - abs(w)
        if pm < PM:
            PM, FC = pm, f[i] + t * (f[i + 1] - f[i])
    wr = np.floor((ph + 180) / 360)
    jx = np.where(wr[:-1] != wr[1:])[0]
    m = mag[jx]
    up, dn = m[m < 1], m[m >= 1]
    gmu = float(-20 * np.log10(up.max())) if len(up) else float("inf")
    gmd = float(20 * np.log10(dn.min())) if len(dn) else float("inf")
    return PM, FC, gmu, gmd


def peak530(L, Tref, f=F):
    b = (f >= 5) & (f <= 30)
    S = 1 / (1 + L)
    return 20 * math.log10(max(np.abs(L * S)[b].max(), np.abs(Tref * S)[b].max(), 1e-12))


# ------------------------------------------------------------------------------------------------- EXACT periodic
class Periodic:
    """explicit-state 1 kHz model with the true 100 Hz hold register; linear in the state."""

    def __init__(self, des, pl, v, e=0, kappa=1.0, jb=1.0, fade=FADE0, ki=None, kd_scale=1.0, tau_o=None,
                 rt_ticks=60, wmode="inst", gain=1.0, extra_delay=0):
        self.des, self.pl, self.v, self.e, self.kap = des, pl, v, e, kappa
        self.fade, self.ki = fade, (des.ki if ki is None else ki)
        self.kds, self.tau_o, self.wmode, self.gain = kd_scale, tau_o, wmode, gain
        self.G = des.G(v)
        self.Ad, self.Bd, self.Cth, self.Cw = pl.zoh(jb)
        self.d = pl.d + extra_delay
        self.rt_f = max(1, rt_ticks // 10)                 # fork round trip in 100 Hz ticks
        n = self.Ad.shape[0]
        idx, i = {}, 0
        for nm, sz in (("x", n), ("ud", max(self.d, 1)), ("th", 22), ("ema_h", 22), ("thh", 1), ("thp", 1), ("xh", 1),
                       ("ema", 1), ("I", 1), ("o", 1), ("Io", 1), ("fl", self.rt_f), ("s", 1)):
            idx[nm] = slice(i, i + sz)
            i += sz
        self.idx, self.N = idx, i
        self.A = [self._tick_matrix(p) for p in range(10)]

    def _tick(self, X, p):
        """X: (N, m) batch of state columns at the start of tick p; returns the next states."""
        g = self.idx
        des = self.des
        Y = np.zeros_like(X)
        x = X[g["x"]]
        thn = self.Cth @ x
        wn = self.Cw @ x
        th_hist = X[g["th"]]
        if self.wmode == "bd1":
            wn = (thn - th_hist[0]) / TS
        e = self.e
        thh, thp = X[g["thh"]][0], X[g["thp"]][0]
        ema = X[g["ema"]][0] + ALPHA * (self.kap * wn - X[g["ema"]][0])
        if e < 0 and p == 0:                               # ages 0-9: refresh BEFORE the lane read
            thh = thn
        thsp = X[g["Io"]][0] if self.tau_o else 0.0 * thn
        if des.dop == "v295":                              # the V295/V294 rate loop: x held, s' = (a s + b x)/1024
            xh = 8.0 * ema if (e < 0 and p == 0) else X[g["xh"]][0]
            s_new = (des.a_fb * X[g["s"]][0] + des.b_fb * xh) / 1024.0
            r26 = s_new - X[g["s"]][0]
            Y[g["s"]][0] = s_new
            E = -r26
            Ep = E
        else:
            r26 = 80.0 * (thh + thp)
            E = 160.0 * thsp - r26
            Ep = E * self.G / 256.0
        I = X[g["I"]][0] + Ep * self.ki / 32768.0
        P = Ep * des.kp / 256.0
        if des.dop == "fresh":
            D = -self.kds * (des.kd / 8.0) * ABE_PER * ema
        elif des.dop == "held":
            xh = 8.0 * ema if (e < 0 and p == 0) else X[g["xh"]][0]
            D = -self.kds * (des.kd / 8.0) * xh
        else:
            D = 0.0 * ema
        S = (I + P + D) * self.fade * self.gain
        o = X[g["o"]][0]
        o_new = (OA * o + OB * S) / 1024.0
        y = (o + o_new) / 32.0
        ucmd = FWD * y
        ud = X[g["ud"]]
        if self.d == 0:
            uapp = ucmd
            Y[g["ud"]][0] = 0.0
        else:
            uapp = ud[self.d - 1]
            Y[g["ud"]][1:self.d] = ud[0:self.d - 1]
            Y[g["ud"]][0] = ucmd
        Y[g["x"]] = self.Ad @ x + self.Bd @ uapp[None, :]
        Y[g["th"]][1:] = th_hist[:-1]
        Y[g["th"]][0] = thn
        eh = X[g["ema_h"]]
        Y[g["ema_h"]][1:] = eh[:-1]
        Y[g["ema_h"]][0] = ema
        Y[g["thp"]][0] = thh
        Y[g["ema"]][0] = ema
        Y[g["I"]][0] = I if self.ki != 0 else 0.0 * I     # Ki 0: the frozen I is a constant (no perturbation state)
        Y[g["o"]][0] = o_new
        # 100 Hz refresh at the END of tick p == 0 (slot 4 after slot 0): sample from e ticks earlier
        if p == 0:
            if e <= 0:
                Y[g["thh"]][0] = thn
                Y[g["xh"]][0] = 8.0 * ema
            else:
                Y[g["thh"]][0] = Y[g["th"]][e]           # theta(t_{n-e})
                Y[g["xh"]][0] = 8.0 * Y[g["ema_h"]][e]
        else:
            Y[g["thh"]][0] = X[g["thh"]][0]
            Y[g["xh"]][0] = X[g["xh"]][0]
        # fork outer loop (100 Hz integral, round trip rt)
        if self.tau_o:
            fl = X[g["fl"]]
            if p == 0:
                Y[g["fl"]][1:] = fl[:-1]
                Y[g["fl"]][0] = thn
                Y[g["Io"]][0] = X[g["Io"]][0] - (0.01 / self.tau_o) * fl[-1]
            else:
                Y[g["fl"]] = fl
                Y[g["Io"]][0] = X[g["Io"]][0]
        return Y

    def _tick_matrix(self, p):
        return self._tick(np.eye(self.N), p)

    def monodromy(self):
        M = np.eye(self.N)
        for p in range(10):
            M = self.A[p] @ M
        return M

    def poles(self):
        lam = np.linalg.eigvals(self.monodromy())
        lam = lam[np.abs(lam) > 1e-9]
        return lam

    def rho_ring(self, fmin=0.05):
        """(rho, f Hz, zeta) of the least-damped oscillatory pole above fmin (rho over ALL poles)."""
        lam = self.poles()
        rho = float(np.abs(lam).max())
        s = np.log(lam.astype(complex)) / (10 * TS)
        fr = np.abs(s.imag) / (2 * np.pi)
        osc = fr > fmin
        if not osc.any():
            return rho, float("nan"), float("nan")
        zeta = -s.real[osc] / np.abs(s[osc])
        j = int(np.argmin(zeta))
        return rho, float(fr[osc][j]), float(zeta[j])


def gm_exact(des, pl, v, hi=8.0, **kw):
    """smallest gain multiplier > 1 giving rho >= 1 (bisection; inf if > hi)."""
    if Periodic(des, pl, v, gain=hi, **kw).rho_ring()[0] < 1:
        return float("inf")
    lo, h = 1.0, hi
    for _ in range(30):
        m = math.sqrt(lo * h)
        if Periodic(des, pl, v, gain=m, **kw).rho_ring()[0] < 1:
            lo = m
        else:
            h = m
    return 20 * math.log10(lo)


if __name__ == "__main__":
    for nm, r in ROWS.items():
        print(nm, r, "min G", min(g_walk(vc, r) for vc in range(0, 8100)))
    print("ABE_PER", ABE_PER, "ALPHA", ALPHA, "FWD", FWD)
