# -*- coding: utf-8 -*-
r"""c3r1_model.py -- INDEPENDENT stability model for the C3 round-1 refutation, lens STABILITY (2026-10-01).

ANALYSIS ONLY.  Builds no image, flashes nothing, sends nothing.  Written by the C3-r1 STABILITY refuter (a subagent of
the orchestrator `main`).

It imports NOTHING from any designer's or scorer's loop code (no score_freq / ds_model / c1_lib / c3_* / r2a_* / the
round-2 refuter's c2r2_model).  It reads only:
  * the V295 image bytes (sha asserted): OA, OB, FWD, the EMA alpha, 1159, the fade records, the Kp/Kd selector-7
    record addresses;
  * the two C3 cave hex files: the G(v) table rows AND the policy/guard immediates, decoded here from the bytes;
  * the r71b plant identification data p5c.json (J profile) and p5b_ms.json (ms_free) -- the plant family.

Formulation (deliberately different from the round-2 refuter's and the panel scorer's):
  (1) LTI "averaged hold" loop, but every plant channel is the EXACT sampled-data (modified-z) FRF with a fractional
      total delay per channel:  y_n = C x(t_n - delta_c), input ZOH applied tau_in after t_n.  The rate-former is a
      window mean (theta(t) - theta(t-w))/w, built from two exact theta channels -- so its lag is exact, not interpolated.
  (2) EXACT PERIODIC model on a 0.25 ms SUB-STEP grid (q = 4 per 1 kHz tick): one plant, a sub-step input delay line,
      a sub-step angle history for the rate former, the 10-tick hold refreshed at slot 4 AFTER the lane (or any offset),
      the 2-tap r26, the EMA, I, D, the output lag.  The 10-tick monodromy gives rho and the closed-loop poles; gain
      scaling and extra delay give the exact GM and delay margin.

Frames: theta = gp-0x6a00 / 10 (deg, +left).  The plant is written in theta coordinates.  Motor-frame operands (the
fresh gp-0x6abe, the held gp-0x6a56) see kappa * d(theta)/dt.  FA = plant J, b as identified; FB = J, b x jb (1/1.155).
Sign chain: pol = -1 (record EVIDENCE), so u (plant torque, +left) = +c_out * y (c_out = FWD/32768): with E = 16(sp - th)
this is negative feedback; the fresh D = (Kd/8) gp-0x6abe with gp-0x6abe = ABE * kappa * omega, ABE = -8/(48*1159/32768).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
from dataclasses import dataclass, replace
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
C3D = AL / "c3"
PLANT = KIT / "analysis-2020accord" / "studies" / "v295" / "plant" / "_scratch"
OUT = KIT / "_scratch" / "angle_loop" / "refute-c3r1-stability"
OUT.mkdir(parents=True, exist_ok=True)
TS = 1e-3

# ---------------------------------------------------------------------------------------------------------------------
# image constants (LE)
# ---------------------------------------------------------------------------------------------------------------------
_img = V295_IMG.read_bytes()
assert hashlib.sha256(_img).hexdigest() == V295_SHA
_u16 = lambda a: struct.unpack_from("<H", _img, a)[0]  # noqa: E731
_i16 = lambda a: struct.unpack_from("<h", _img, a)[0]  # noqa: E731
_u32 = lambda a: struct.unpack_from("<I", _img, a)[0]  # noqa: E731
OA, OB, FWD = _i16(0xC63EC), _u16(0xC63EE), _i16(0xC6CD0)
ALPHA = _u16(0xC643C) / 128.0
K1159 = _u16(0xC613A)
V295_AB = (_i16(0xC63E8), _u16(0xC63EA))
assert (OA, OB, FWD, _u16(0xC643C), K1159, V295_AB) == (992, 507, 5346, 37, 1159, (1011, 1050))
assert _u32(0xCB994 + 4 * 7) + 12 == 0xE5384 and _u32(0xCB7D4 + 4 * 7) + 10 == 0xE5126   # C3's Kp/Kd cal addresses
X_PER_ABE = 48.0 * K1159 / 32768.0           # FUN_0003f776: x = pol*((abe*48*1159)>>15)
ABE = -8.0 / X_PER_ABE                       # abe counts per deg/s (x = +8/deg/s, pol = -1)
C_OUT = FWD / 32768.0
# fade at |tq| <= 512 (fadeB X0 = 16) and grab-rate 0: ((255*255)&0xFFFF)>>8 = 254
FADE = 254.0 / 256.0


# ---------------------------------------------------------------------------------------------------------------------
# the C3 caves: table + immediates decoded from the bytes
# ---------------------------------------------------------------------------------------------------------------------
def _hexbytes(p):
    return bytes(int(t, 16) for t in Path(p).read_text().split())


def decode_cave(path, load=0xC4C00):
    bs = _hexbytes(path)
    tbl = None
    for i in range(0, len(bs) - 6, 2):
        if bs[i] == 0x29 and bs[i + 1] == 0x06:          # mov imm32, r9 (Format VI, hw1 0x0629)
            tbl = struct.unpack_from("<I", bs, i + 2)[0]
            break
    rows, off = [], tbl - load
    while True:
        X, G, S = struct.unpack_from("<HHh", bs, off)
        rows.append((X, G, S))
        off += 6
        if X == 0xFFFF:
            break
    assert off == len(bs)
    code = bs[:tbl - load]
    hw = [struct.unpack_from("<H", code, i)[0] for i in range(0, len(code) - 1, 2)]
    # movea imm16, r0, r13 (hw1 0x6e20) and addi imm16 (hw1 low 6 bits field 0x30) -- collect the immediates in order
    movea = [struct.unpack_from("<h", code, i + 2)[0] for i in range(0, len(code) - 3, 2)
             if struct.unpack_from("<H", code, i)[0] == 0x6E20]
    addi = [struct.unpack_from("<h", code, i + 2)[0] for i in range(0, len(code) - 3, 2)
            if (struct.unpack_from("<H", code, i)[0] & 0x07E0) == 0x0600 and i % 2 == 0]
    shl_imm = [h & 0x1F for h in hw if (h & 0x07E0) == 0x02C0]          # shl imm5, reg2 (Format II, op 010110)
    sar_imm = [h & 0x1F for h in hw if (h & 0x07E0) == 0x02A0]          # sar imm5
    return dict(rows=rows, tbl=tbl, n=len(bs), sha=hashlib.sha256(bs).hexdigest()[:16], movea=movea, addi=addi,
                shl=shl_imm, sar=sar_imm, has_fresh=(bytes.fromhex("24d74295") in code))


def walk_G(rows, vc):
    """the cave's walk: v <= X0 -> G0; else segment i with X(i) < v <= X(i+1): G(i) + ((v-X(i))*S(i) >> 12)."""
    v = vc & 0xFFFF
    if not v > rows[0][0]:
        return rows[0][1]
    i = 0
    while not v <= rows[i + 1][0]:
        i += 1
    X, G, S = rows[i]
    return G + (((v - X) * S) >> 12)


def spd(v):
    return int(math.floor(v * 3.6 * 64.0 + 1e-9))      # gp-0x6a5e, 64 counts per km/h


@dataclass
class Design:
    name: str
    dkind: str            # 'fresh' | 'held' | 'v295' | 'v294'
    kp: float = 112.0
    ki: float = 56.0
    kd: float = 48.0
    rows: tuple = ()
    note: str = ""

    def G(self, v):
        return walk_G(self.rows, spd(v)) if self.rows else 256


def designs():
    cp = decode_cave(C3D / "c3_cave_C3-P.hex")
    cf = decode_cave(C3D / "c3_cave_C3-F.hex")
    assert cp["has_fresh"] and not cf["has_fresh"]
    return {"C3-P": Design("C3-P", "fresh", kd=48, rows=tuple(cp["rows"])),
            "C3-F": Design("C3-F", "held", kd=24, rows=tuple(cf["rows"])),
            "V295": Design("V295", "v295"), "V294": Design("V294", "v294")}


# ---------------------------------------------------------------------------------------------------------------------
# plant family (my own construction from the ident JSON; definitions from the brief)
# ---------------------------------------------------------------------------------------------------------------------
VC = np.array([3.1, 8.0, 11.9, 17.0, 26.9])
BANDS = ("0-5", "5-10", "10-15", "15-22", "22+")
_prof = {}
for r in json.load(open(PLANT / "p5c.json")):
    _prof.setdefault(r["J"], [None] * 5)[r["band"]] = (r["b"], r["k"])
PROF = {J: (np.array([x[0] for x in v]), np.array([x[1] for x in v])) for J, v in _prof.items()}
_ms = json.load(open(PLANT / "p5b_ms.json"))["nominal"]
MSF = {k: np.array([_ms[b][k]["val"] for b in BANDS]) for k in ("J", "b", "k")}
B_FLOOR = 0.7 * 4.94


def _refit(J):
    if J in PROF:
        return PROF[J]
    js = sorted(PROF)
    lo = max(j for j in js if j < J)
    hi = min(j for j in js if j > J)
    w = (J - lo) / (hi - lo)
    return tuple((1 - w) * a + w * b for a, b in zip(PROF[lo], PROF[hi]))


def _at(a, v):
    return float(np.interp(v, VC, a))


@dataclass
class Plant:
    J: float
    b: float
    k: float
    tau: float = 2.0       # input transport, ms
    f2: float = 0.0
    z2: float = 0.05
    r2: float = 0.2
    conv: str = "mu"       # 'mu' free-free resonance at f2 | 'jw' wheel-side (anti-resonance) at f2


def member(name, v):
    """-> Plant.  name = '*'-joined factors: damping {b_lo, b_lo_step, b_hi, b_q, bc, b/1.9} x inertia {J_lo, J_hi, J_hi2,
    J1.0, J1.3, ms_free} x delay {tau0, tau6} x mode {mode13, mode20}.  b_lo alone = knot factors interpolated (the
    v294_plant definition); b_lo in a product = the per-speed step (the brief's 'b/1.8 at >= 10')."""
    parts = [p for p in name.split("*") if p and p != "nominal"]
    damp = [p for p in parts if p in ("b_lo", "b_lo_step", "b_hi", "b_q", "bc", "b/1.9", "bq10")]
    inert = [p for p in parts if p in ("J_lo", "J_hi", "J_hi2", "J1.0", "J1.3", "ms_free")]
    tau = 6.0 if "tau6" in parts else 0.0 if "tau0" in parts else 2.0
    mode = [p for p in parts if p.startswith("mode")]
    assert len(damp) <= 1 and len(inert) <= 1, name
    i = inert[0] if inert else ""
    if i == "ms_free":
        J, b, k = _at(MSF["J"], v), _at(MSF["b"], v), _at(MSF["k"], v)
        bb_knots = MSF["b"]
    else:
        Jr = {"": 0.2, "J_lo": 0.1, "J_hi": 0.5, "J_hi2": 0.8, "J1.0": 1.0, "J1.3": 1.3}[i]
        bb_knots, kk = _refit(Jr)
        J, b, k = Jr, _at(bb_knots, v), _at(kk, v)
    d = damp[0] if damp else ""
    if d == "b_lo" and not inert:
        b = _at(bb_knots * np.where(VC >= 10, 1 / 1.8, 0.7), v)
    elif d in ("b_lo", "b_lo_step", "bc"):
        b = b * (1 / 1.8 if v >= 10 else 0.7)
    elif d == "b/1.9":
        b = b * (1 / 1.9 if v >= 10 else 0.7)
    elif d == "b_hi":
        b = b * 1.5
    elif d == "b_q":
        b = max(0.25 * b, B_FLOOR) if v >= 12.5 else b
    elif d == "bq10":
        b = max(0.25 * b, B_FLOOR) if v >= 10.0 else b
    pl = Plant(J, b, k, tau)
    if mode:
        pl.f2, pl.z2 = (13.0, 0.10) if mode[0] == "mode13" else (20.0, 0.05)
    return pl


def light_b(v):
    T_PER_U = 2625.4
    kv = [2, 4, 6, 8, 10, 12.5, 15, 17.5, 20, 23, 28]
    ku = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0134]
    k = np.interp(VC, kv, ku) * T_PER_U
    return Plant(8e-5 * T_PER_U, 6e-4 * T_PER_U, _at(k, v), 2.0)


def plant_ss(pl: Plant, jb=1.0):
    """continuous (A, B, Cth, Cw); motor-side collocated sensing; J, b scaled by jb (FB)."""
    J, b, k = pl.J * jb, pl.b * jb, pl.k
    if pl.f2 <= 0:
        A = np.array([[0.0, 1.0], [-k / J, -b / J]])
        B = np.array([[0.0], [1.0 / J]])
        return A, B, np.array([1.0, 0.0]), np.array([0.0, 1.0])
    Jw = pl.r2 * J
    Jm = J - Jw
    if pl.conv == "mu":
        mu = Jm * Jw / J
        K = (2 * np.pi * pl.f2) ** 2 * mu
        c = 2 * pl.z2 * np.sqrt(K * mu)
    else:
        K = (2 * np.pi * pl.f2) ** 2 * Jw
        c = 2 * pl.z2 * np.sqrt(K * Jw)
    A = np.array([[0, 1, 0, 0], [-(k + K) / Jm, -(b + c) / Jm, K / Jm, c / Jm], [0, 0, 0, 1],
                  [K / Jw, c / Jw, -K / Jw, -c / Jw]], float)
    B = np.array([[0], [1 / Jm], [0], [0]], float)
    return A, B, np.array([1.0, 0, 0, 0]), np.array([0, 1.0, 0, 0])


def _expm_pair(A, B, t):
    n = A.shape[0]
    M = np.zeros((n + 1, n + 1))
    M[:n, :n] = A * t
    M[:n, n:] = B * t
    E = sla.expm(M)
    return E[:n, :n], E[:n, n:]


# ---------------------------------------------------------------------------------------------------------------------
# (1) LTI averaged-hold loop with exact fractional-delay sampled channels
# ---------------------------------------------------------------------------------------------------------------------
FG = np.unique(np.concatenate([np.logspace(-2.3, math.log10(499.0), 2600),
                               [0.05, 0.1, 0.5, 1, 2, 3, 5, 7, 10, 13, 15, 16, 17, 20, 25, 30]]))


def chan_frf(A, B, C, tau_ms, f):
    """exact sampled FRF of u_n (ZOH, applied tau after t_n) -> y_n = C x(t_n).  tau may be fractional (ms)."""
    tt = tau_ms * 1e-3 / TS
    m = int(math.floor(tt + 1e-12))
    eps = tt - m
    Phi, _ = _expm_pair(A, B, TS)
    if eps > 1e-12:
        P1, G1 = _expm_pair(A, B, eps * TS)
        P2, G2 = _expm_pair(A, B, (1 - eps) * TS)
        Ga, Gb = P2 @ G1, G2
    else:
        Ga, Gb = np.zeros_like(B), _expm_pair(A, B, TS)[1]
    zi = np.exp(-2j * np.pi * np.asarray(f) * TS)          # z^-1
    n = A.shape[0]
    z = 1 / zi
    M = z[:, None, None] * np.eye(n)[None] - Phi[None]
    X = np.linalg.solve(M, np.broadcast_to((Ga + 0j), (len(z), n, 1)))[..., 0] * (zi ** (m + 1))[:, None] \
        + np.linalg.solve(M, np.broadcast_to((Gb + 0j), (len(z), n, 1)))[..., 0] * (zi ** m)[:, None]
    return X @ C


def plant_channels(pl: Plant, f, jb=1.0, rf_ms=0.0, extra_ms=0.0, d_extra_ms=0.0):
    """(P_theta, P_rate): u -> theta sample, u -> measured motor rate (deg/s of theta x 1; kappa applied later).
    rf_ms = 0: the instantaneous rate; > 0: the window mean (theta(t) - theta(t - rf))/rf (resolver delta form).
    extra_ms: extra input delay (delay margin probe).  d_extra_ms: an extra delay on the rate operand only."""
    A, B, Ct, Cw = plant_ss(pl, jb)
    tau = pl.tau + extra_ms
    Pt = chan_frf(A, B, Ct, tau, f)
    if rf_ms <= 0:
        Pw = chan_frf(A, B, Cw, tau + d_extra_ms, f)
    else:
        Pw = (chan_frf(A, B, Ct, tau + d_extra_ms, f) - chan_frf(A, B, Ct, tau + d_extra_ms + rf_ms, f)) / (rf_ms * 1e-3)
    return Pt, Pw


def Hhold(f, e):
    """100 Hz hold refreshed at slot 4 AFTER the lane, the value e ticks late: ages e+1 .. e+10 (e = -1: ages 0..9)."""
    zi = np.exp(-2j * np.pi * np.asarray(f) * TS)
    return np.mean([zi ** a for a in range(e + 1, e + 11)], axis=0)


def EMA(f):
    zi = np.exp(-2j * np.pi * np.asarray(f) * TS)
    return ALPHA / (1 - (1 - ALPHA) * zi)


def Kout(f, fade=1.0):
    zi = np.exp(-2j * np.pi * np.asarray(f) * TS)
    return fade * FADE * C_OUT * (OB / 1024.0) * (1 + zi) / (32.0 * (1 - (OA / 1024.0) * zi))


def controller(des: Design, v, f, e, kappa=1.0, noI=False, kd_scale=1.0, abe_late=0):
    """-> (Cth, Cw, Cref): S counts per deg of theta, per deg/s of theta (motor operand includes kappa), per deg of sp."""
    zi = np.exp(-2j * np.pi * np.asarray(f) * TS)
    H = Hhold(f, e)
    ema = EMA(f) * (zi ** abe_late)
    if des.dkind in ("fresh", "held"):
        g = des.G(v) / 256.0
        PI = des.kp / 256.0 + (0.0 if noI else des.ki / 32768.0) / (1 - zi)
        Cth = -g * 80.0 * (1 + zi) * H * PI
        Cref = g * 160.0 * PI * Hhold(f, 0)
        if des.dkind == "fresh":
            Cw = (des.kd * kd_scale / 8.0) * ABE * kappa * ema
        else:
            Cw = -(des.kd * kd_scale / 8.0) * 8.0 * kappa * H * ema
    else:
        a, b = V295_AB[0], (V295_AB[1] if des.dkind == "v295" else 567)
        filt = (b / 1024.0) * (1 - zi) / (1 - (a / 1024.0) * zi)
        Cth = np.zeros_like(zi)
        Cw = -(960.0 / 256.0) * filt * 8.0 * kappa * H * ema
        Cref = np.zeros_like(zi)
    return Cth, Cw, Cref


def loop(des, pl, v, f=FG, e=0, kappa=1.0, jb=1.0, rf_ms=0.0, noI=False, fade=1.0, gain=1.0, extra_ms=0.0,
         kd_scale=1.0, abe_late=0, d_extra_ms=0.0):
    Pt, Pw = plant_channels(pl, f, jb, rf_ms, extra_ms, d_extra_ms)
    Cth, Cw, Cref = controller(des, v, f, e, kappa, noI, kd_scale, abe_late)
    K = gain * Kout(f, fade)
    L = -K * (Cth * Pt + Cw * Pw)
    Sx = 1 / (1 + L)
    Tr = K * Cref * Pt * Sx
    return L, Sx, Tr, (Cth, Cw, K)


def pm_gm(L, f=FG):
    """PM = 180 - |wrap(phase)| at each |L| = 1 crossing (min), its fc; GM up (dB) at -180 crossings with |L| < 1."""
    mag = np.abs(L)
    ph = np.unwrap(np.angle(L)) * 180 / np.pi
    s = mag - 1
    idx = np.where((s[:-1] * s[1:] <= 0) & (mag[:-1] != mag[1:]))[0]
    PM, FC = math.inf, math.nan
    for i in idx:
        t = (1 - mag[i]) / (mag[i + 1] - mag[i])
        p = ph[i] + t * (ph[i + 1] - ph[i])
        pmv = 180 - abs(((p + 180) % 360) - 180)
        if pmv < PM:
            PM, FC = pmv, f[i] + t * (f[i + 1] - f[i])
    wr = np.floor((ph + 180) / 360)
    jx = np.where(wr[:-1] != wr[1:])[0]
    m = mag[jx]
    up = m[m < 1]
    GMu = float(-20 * np.log10(up.max())) if len(up) else math.inf
    return PM, FC, GMu


def metrics(des, pl, v, **kw):
    L, Sx, Tr, (Cth, Cw, K) = loop(des, pl, v, **kw)
    PM, FC, GMu = pm_gm(L)
    band = (FG >= 5) & (FG <= 30)
    Tc = np.abs(L * Sx)
    return dict(PM=PM, fc=FC, GMu=GMu, Tc530=20 * np.log10(Tc[band].max()),
                Tr530=20 * np.log10(max(np.abs(Tr[band]).max(), 1e-12)), Ms=float(np.abs(Sx).max()))


def retw(des, v, fq, e=0, kappa=1.0, tau=2.0, abe_late=0, rf_ms=0.0):
    """Re(T/omega) at frequency fq: the controller's delivered torque per deg/s of the motor rate (> 0 damps), with
    the transport and the fade, T = -u (the tap sign).  rf_ms adds the rate-former window lag to the motor operand."""
    f = np.atleast_1d(np.asarray(fq, float))
    Cth, Cw, _ = controller(des, v, f, e, kappa, abe_late=abe_late)
    zi = np.exp(-2j * np.pi * f * TS)
    w = 2 * np.pi * f
    K = Kout(f) * np.exp(-1j * w * tau * 1e-3)
    rf = (1 - np.exp(-1j * w * rf_ms * 1e-3)) / (1j * w * rf_ms * 1e-3) if rf_ms > 0 else 1.0
    # theta = omega/(jw) [plant angle]; the motor operand carries the rate-former filter.  u/omega = K (Cth/jw + Cw rf);
    # damping = u opposing omega, so Re(T/omega) := -Re(u/omega)
    return -(K * (Cth / (1j * w) + Cw * rf)).real


# ---------------------------------------------------------------------------------------------------------------------
# (2) EXACT PERIODIC model on a sub-step grid
# ---------------------------------------------------------------------------------------------------------------------
class Periodic:
    """q sub-steps per tick (h = T/q).  Order inside tick n: sample theta(t_n) and the rate; EMA update; lane (uses the
    held theta of a PREVIOUS slot); slot 4 (n % 10 == 4) refreshes the hold from the samples taken e ticks earlier
    (e = 0: this tick's; ages 1..10); e = -1 refreshes BEFORE the lane (ages 0..9); then q plant sub-steps with the input
    delay line (tau_in in sub-steps)."""

    def __init__(self, des, pl, v, e=0, kappa=1.0, jb=1.0, rf_sub=0, noI=False, fade=1.0, gain=1.0, extra_sub=0,
                 q=4, kd_scale=1.0, abe_late=0, d_extra_sub=0):
        self.des, self.v, self.e, self.kappa, self.q = des, v, e, kappa, q
        A, B, Ct, Cw = plant_ss(pl, jb)
        h = TS / q
        self.Ph, self.Gh = _expm_pair(A, B, h)
        self.Ct, self.Cw = Ct, Cw
        self.np = A.shape[0]
        tin = pl.tau * 1e-3 / h
        assert abs(tin - round(tin)) < 1e-9, "tau must be a multiple of the sub-step"
        self.min = int(round(tin)) + extra_sub
        self.rf = rf_sub               # 0 = instantaneous omega(t_n); >0 = window mean over rf sub-steps
        self.dx = d_extra_sub          # extra delay on the rate operand (sub-steps)
        self.g = des.G(v) / 256.0
        self.ki = 0.0 if noI else des.ki / 32768.0
        self.kp = des.kp / 256.0
        self.kd = des.kd * kd_scale
        self.gainf = gain * fade * FADE * C_OUT
        self.abe_late = abe_late
        hist = max(self.rf + self.dx, 1)
        lay = {}
        n0 = 0

        def al(nm, k):
            nonlocal n0
            lay[nm] = (n0, n0 + k)
            n0 += k
        al("x", self.np)
        al("ub", max(self.min, 1))     # u delay line (oldest at the end)
        al("th_hist", hist)            # theta at the previous `hist` sub-steps (newest first)
        al("w_hist", hist)             # omega at the previous sub-steps
        al("r", 1)
        al("rl", max(abe_late, 1))     # abe history for a late fresh read
        al("thh", 1)
        al("thhp", 1)
        al("xh", 1)
        al("I", 1)
        al("o", 1)
        al("s", 1)                     # V29x fb filter
        al("T", 1)                     # controller output held across the tick
        if e > 0:
            al("thb", e)
            al("rb", e)
        self.lay, self.n = lay, n0

    def _sl(self, nm):
        a, b = self.lay[nm]
        return slice(a, b)

    def tick_map(self, n):
        """the (n x n) linear map of one tick at phase n (sp = 0)."""
        N = self.n
        M = np.eye(N)
        X = np.eye(N)            # columns = basis states; we propagate the identity
        Y = X.copy()
        L = self._sl
        th = self.Ct @ X[L("x")]
        w = self.Cw @ X[L("x")]
        # measured motor rate at t_n (theta-frame deg/s; kappa applied below)
        if self.rf == 0 and self.dx == 0:
            wm = w
        elif self.rf == 0:
            wm = X[L("w_hist")][self.dx - 1]
        else:
            th_now = th if self.dx == 0 else X[L("th_hist")][self.dx - 1]
            wm = (th_now - X[L("th_hist")][self.dx + self.rf - 1]) / (self.rf * TS / self.q)
        r = X[L("r")][0]
        r_new = (1 - ALPHA) * r + ALPHA * self.kappa * wm
        r_use = r_new if self.abe_late == 0 else X[L("rl")][self.abe_late - 1]
        slot = (n % 10) == 4
        thh, thhp, xh = X[L("thh")][0], X[L("thhp")][0], X[L("xh")][0]
        if slot and self.e < 0:
            thh = th
            xh = 8.0 * r_new
        des = self.des
        if des.dkind in ("fresh", "held"):
            Ep = self.g * (-80.0) * (thh + thhp)
            I_new = X[L("I")][0] + self.ki * Ep
            P = self.kp * Ep
            D = (self.kd / 8.0) * ABE * r_use if des.dkind == "fresh" else -(self.kd / 8.0) * xh
            S = I_new + P + D
            if self.ki == 0.0:
                I_new = 0.0 * X[L("I")][0]       # a frozen I is a constant bias (eigenvalue 1, not a mode): drop it
            s_new = 0.0 * X[L("s")][0]
        else:
            b = V295_AB[1] if des.dkind == "v295" else 567
            s = X[L("s")][0]
            s_new = (V295_AB[0] / 1024.0) * s + (b / 1024.0) * xh
            S = (960.0 / 256.0) * (-(s_new - s))
            I_new = 0.0 * X[L("I")][0]
        o = X[L("o")][0]
        o_new = (OA / 1024.0) * o + (OB / 1024.0) * S
        T = self.gainf * (o + o_new) / 32.0       # u (plant torque, +left)
        Y[L("thhp")] = thh
        Y[L("thh")] = thh
        Y[L("xh")] = xh
        if slot and self.e >= 0:
            if self.e == 0:
                Y[L("thh")] = th
                Y[L("xh")] = 8.0 * r_new
            else:
                Y[L("thh")] = X[L("thb")][self.e - 1]
                Y[L("xh")] = 8.0 * X[L("rb")][self.e - 1]
        if self.e > 0:
            Y[L("thb")] = np.vstack([th[None], X[L("thb")][:-1]])
            Y[L("rb")] = np.vstack([r_new[None], X[L("rb")][:-1]])
        Y[L("r")] = r_new
        rl = X[L("rl")]
        Y[L("rl")] = np.vstack([r_new[None], rl[:-1]])
        Y[L("I")] = I_new
        Y[L("o")] = o_new
        Y[L("s")] = s_new
        Y[L("T")] = T
        M = Y
        # q plant sub-steps
        for j in range(self.q):
            M = self._substep(M)
        return M

    def _substep(self, X):
        L = self._sl
        Y = X.copy()
        x = X[L("x")]
        T = X[L("T")][0]
        ub = X[L("ub")]
        if self.min == 0:
            u = T
            Y[L("ub")] = 0 * ub
        else:
            u = ub[-1]
            Y[L("ub")] = np.vstack([T[None], ub[:-1]])
        th = self.Ct @ x
        w = self.Cw @ x
        Y[L("th_hist")] = np.vstack([th[None], X[L("th_hist")][:-1]])
        Y[L("w_hist")] = np.vstack([w[None], X[L("w_hist")][:-1]])
        Y[L("x")] = self.Ph @ x + np.outer(self.Gh[:, 0], u)
        return Y

    def monodromy(self):
        M = np.eye(self.n)
        for n in range(10):
            M = self.tick_map(n) @ M
        return M

    def rho_ring(self):
        lam = np.linalg.eigvals(self.monodromy())
        rho = float(np.max(np.abs(lam)))
        lam = lam[np.abs(lam) > 1e-6]
        s = np.log(lam.astype(complex)) / (10 * TS)
        fz = np.abs(s.imag) / (2 * np.pi)
        zeta = -s.real / np.maximum(np.abs(s), 1e-12)
        osc = (fz > 0.2) & (fz < 49.9)
        if osc.any():
            j = int(np.argmin(np.where(osc, zeta, 9)))
            return rho, float(fz[j]), float(zeta[j]), lam
        return rho, math.nan, math.nan, lam


def exact_rho(des, pl, v, **kw):
    return Periodic(des, pl, v, **kw).rho_ring()[0]


def exact_gm_up(des, pl, v, hi=40.0, **kw):
    if exact_rho(des, pl, v, gain=1.0, **kw) >= 1:
        return -math.inf
    lo = 1.0
    k = 1.0
    hk = None
    while k < hi:
        k *= 1.25
        if exact_rho(des, pl, v, gain=k, **kw) >= 1:
            hk = k
            break
        lo = k
    if hk is None:
        return math.inf
    for _ in range(14):
        m = math.sqrt(lo * hk)
        if exact_rho(des, pl, v, gain=m, **kw) >= 1:
            hk = m
        else:
            lo = m
    return 20 * math.log10(lo)


def exact_dm(des, pl, v, q=4, max_ms=80.0, **kw):
    """extra input delay (ms, sub-step resolution) at which rho reaches 1."""
    if exact_rho(des, pl, v, q=q, **kw) >= 1:
        return 0.0
    lo, hi = 0, None
    s = 1
    while s * 1000 / (q * 1000) <= max_ms:
        if exact_rho(des, pl, v, q=q, extra_sub=s, **kw) >= 1:
            hi = s
            break
        lo = s
        s = s * 2
    if hi is None:
        return math.inf
    while hi - lo > 1:
        m = (lo + hi) // 2
        if exact_rho(des, pl, v, q=q, extra_sub=m, **kw) >= 1:
            hi = m
        else:
            lo = m
    return lo * (1.0 / q)
