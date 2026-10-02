# -*- coding: utf-8 -*-
r"""rsn_engine.py -- REFUTER (stability-nonlinear) of DESIGN-V299-SYNTHESIS: MY OWN 1 kHz lane + 100 Hz fork + twist
model, written from the synthesis' integer listing (its section 1.2) and the fork source at Dom 2712e1336
(carcontroller._update_angle, lateral.apply_steer_angle_limits_vm), NOT imported from S2 / score_time.
ANALYSIS ONLY: builds no image, flashes nothing, sends nothing, edits no fork / firmware / golden-model file.

Shared DATA only (not scorers): the V298 image (cal cells, GB-P rows, fade records; sha 177abf04 asserted), the r71b
plant family parameter table (v294_plant.family), the angle correction LERP (angle_signal_mirror.Cal) for the
motor/wheel frame, route 79's CarParams (VM) and M3's reaction fit (d1_r79.json).

Lane (per column): rule 'V298' = hard freeze |w| > 512, opposing freeze |w| > 300 & sign(w) != sign(E'), symmetric A3;
                   rule 'V299' = hard freeze |w| > 1229, no opposing clause, asymmetric A3 (theta term := 0 when
                   sign(theta) != sign(E')).  Honda's I/P/D/sum/fade/clamp/output-lag/pol/fwd/OCL as V298.
Fork  (per column): V298 = on > 600 instant / off <= 500, lead 0.06, cap 1.2 deg/frame, clip x1.0, no takeover;
                   V299-A = on > 1200 instant | > 600 for 8 frames, off <= 500, lead 0, takeover 0.4 s (rate AND clip),
                   cap 1.2; V299-B = A + cap 2.5 deg/frame + clip x1.6 at the <= 11.75 m/s knots.
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
V299 = HERE.parent
AL = V299.parent
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "v299_REFSN"
OUT.mkdir(parents=True, exist_ok=True)
for _p in (AL, KIT / "analysis-2020accord" / "studies" / "v295" / "plant"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import v294_plant as VP  # noqa: E402
import angle_signal_mirror as AM  # noqa: E402

# ------------------------------------------------------------------------------------------------ image (EVIDENCE)
_FW = Path(os.environ["ACCORD_FIRMWARE_ROOT"]) / "analysis-2020accord"
_IMG = Path(glob.glob(str(_FW / "_v298_*_plain_image.bin"))[0]).read_bytes()
assert hashlib.sha256(_IMG).hexdigest().startswith("177abf04")
_u16 = lambda a: struct.unpack_from("<H", _IMG, a)[0]  # noqa: E731
_i16 = lambda a: struct.unpack_from("<h", _IMG, a)[0]  # noqa: E731
_u32 = lambda a: struct.unpack_from("<I", _IMG, a)[0]  # noqa: E731


def _rec(bank, sel=7):
    p = _u32(bank + 4 * sel)
    n = _u16(p)
    return (np.array([_u16(p + 2 + 2 * i) for i in range(n)], np.int64),
            np.array([_u16(p + 2 + 2 * n + 2 * i) for i in range(n)], np.int64))


CAL = dict(PCL=_u16(0xC61BC), SCL=_u16(0xC61BE), OCL=_u16(0xC61B4), DCL=_u16(0xC61B6), ICL=_u16(0xC61BA),
           KI=_u16(0xC63E6), OA=_i16(0xC63EC), OB=_u16(0xC63EE), FWD=_i16(0xC6CD0), KP=_u16(0xE5384),
           KD=_u16(0xE5126), RIN=_u16(0xC63FC), ROUT=_u16(0xC63FA), fadeA=_rec(0xCBB54), fadeB=_rec(0xCBAE4))
assert (CAL["PCL"], CAL["SCL"], CAL["OCL"], CAL["DCL"], CAL["ICL"], CAL["KI"], CAL["KP"], CAL["KD"]) == \
    (15360, 15360, 3072, 10240, 8192, 40, 112, 48), CAL
ROWS = [struct.unpack_from("<HHh", _IMG, 0xC4CDA + 6 * i) for i in range(7)]
assert ROWS[0] == (714, 1178, 1041) and ROWS[-1] == (65535, 2188, 0)
RAIL_T = 2461.0
ABE_PER = -8.0 / (48.0 * 1159.0 / 32768.0)        # gp-0x6abe counts per motor deg/s
ABE_NOISE = 2.8


def s16(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)


def s32(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)


def lerp_u(X, Y, u):
    """unsigned-x LERP clamped at the ends, truncation toward zero (Honda's LERP form)."""
    u = np.asarray(u, np.int64)
    k = np.clip(np.searchsorted(X, u, side="right"), 1, len(X) - 1)
    x0, x1, y0, y1 = X[k - 1], X[k], Y[k - 1], Y[k]
    num = (y1 - y0) * (u - x0)
    q = np.abs(num) // (x1 - x0)
    mid = y0 + np.where(num < 0, -q, q)
    return np.where(u <= X[0], Y[0], np.where(u >= X[-1], Y[-1], mid))


def G_walk(vw):
    """the cave's GB-P walk on gp-0x6a5e (unsigned), segment X_i < v <= X_i+1, slope >> 12."""
    vw = np.asarray(vw, np.int64) & 0xFFFF
    X = np.array([r[0] for r in ROWS], np.int64)
    Gk = np.array([r[1] for r in ROWS], np.int64)
    S = np.array([r[2] for r in ROWS], np.int64)
    i = np.clip(np.searchsorted(X, vw, side="left") - 1, 0, len(X) - 2)
    return np.where(vw <= X[0], Gk[0], Gk[i] + (s32((vw - X[i]) * S[i]) >> 12))


# ------------------------------------------------------------------------------------------------ the lane (mine)
class Lane:
    def __init__(self, rules, vw, variants=None):
        B = self.B = len(rules)
        self.vw = np.asarray(vw, np.int64)
        self.G = G_walk(self.vw)
        v299 = np.array([r == "V299" for r in rules])
        var = variants or [{}] * B
        self.thr = np.array([vv.get("thr", 1229 if r else 512) for r, vv in zip(v299, var)], np.int64)
        self.sgn = np.array([vv.get("sgn", 0 if r else 300) for r, vv in zip(v299, var)], np.int64)
        self.asym = np.array([vv.get("asym", bool(r)) for r, vv in zip(v299, var)])
        self.sh = np.where((self.vw & 0xFFFF) > 2880, 6, 4)
        self.capv = np.array([vv.get("capv", 1382) for vv in var], np.int64)
        self.capval = np.array([vv.get("capval", 4096) for vv in var], np.int64)
        self.ecl = np.array([vv.get("ecl", 1 << 40) for vv in var], np.int64)
        self.capon = (self.vw & 0xFFFF) <= self.capv
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.ok, self.I8, self.olag, self.Tprev = z(), z(), z(), z(), z()
        self.fA = lerp_u(*CAL["fadeA"], np.zeros(B, np.int64))
        self.icl = (CAL["ICL"] << 10) >> 3
        self.log = {}

    def tick(self, a6a00, abe, cmd, w, ramp, req=1, act=1, pol=-1):
        B = self.B
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (B,))
        w = np.broadcast_to(np.asarray(w, np.int64), (B,))
        x = s16(a6a00)
        s_new = s32(x * 8192) >> 10                                   # 8 x
        r26 = np.clip(s32(np.where(self.ok == 1, self.s, 0) + s_new), -65535, 65535)
        self.s, self.ok = s_new, np.ones(B, np.int64)
        run = (ramp != 0) & (req == 1)
        E = s32((s16(cmd) << 2) - r26)                                # 0xC4C00 shl 2 ; sub r26,r16
        Ep = s32(E * self.G) >> 8                                     # 0xC4C54 mul ; sar 8
        ab = s16(abe)
        assert np.all(((ab + 13000) & 0xFFFFFFFF) <= 26000), "op-skip path reached"
        aw = np.minimum(np.abs(w), 0xFFFF)                            # gp-0x4f68
        hard = aw > self.thr                                          # 0xC4C5E..
        opp = (self.sgn > 0) & (aw > self.sgn) & ((s16(w) ^ Ep) < 0)  # V298 only (bnh; ld.h -0x4f60; xor; blt)
        th = s16(a6a00)
        r9 = np.where(self.asym & ((th ^ Ep) < 0), 0, th)            # V299 0xC4C6E..0xC4C74
        r9 = s32((np.abs(r9) << self.sh) + 1250)
        r9 = np.where(self.capon & ((r9 & 0xFFFFFFFF) > self.capval), self.capval, r9)
        t = self.I8 >> 10
        t = np.where(Ep < 0, -t, t)
        a3 = t >= r9
        rf = (ramp & 0x8000) == 0
        frz = hard | opp | a3 | rf | (np.abs(E) > self.ecl)   # ecl: a hypothetical fix (not in V299)
        e5 = np.where(frz, 0, Ep >> 5)
        I = np.clip(s32((self.I8 >> 3) + (s32(e5 * CAL["KI"]) >> 3)), -self.icl, self.icl)
        P = np.clip(s32(Ep * CAL["KP"]) >> 8, -CAL["PCL"], CAL["PCL"])
        D = np.clip(s32(CAL["KD"] * ab) >> 3, -CAL["DCL"], CAL["DCL"])
        S = s32((I >> 7) + P + D)
        fB = lerp_u(*CAL["fadeB"], np.minimum(np.abs(w >> 5), 255))
        f = ((self.fA * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = CAL["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, s32(I << 3), 0)
        t1 = s32(Sc * CAL["OB"]) >> 10
        t2 = s32(CAL["OA"] * self.olag) >> 10
        o_new = s32(t1 + t2)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        if act == 0:
            blk = ((s16(y) <= 102) & (y >= -102)) | (s32(y * self.Tprev) <= 0)
            yr = np.where(blk, 0, yr)
        T = np.clip(s32(yr * (pol * CAL["FWD"])) >> 15, -CAL["OCL"], CAL["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), P=P, D=D, frz=run & frz, hard=run & (hard | opp),
                        a3=run & a3 & ~hard & ~opp, cI=np.abs(Ep >> 5) * run, Ep=Ep)
        return s16(T)


# ------------------------------------------------------------------------------------------------ plant (family data)
_FAM = VP.family()


def params(member, v):
    at = lambda nm: {k: float(np.asarray(q).ravel()[0]) for k, q in _FAM[nm].arrays_at(np.array([float(v)])).items()}  # noqa: E731,E501
    if member == "r79F":                          # nominal + route 79's single-method Coulomb (S2's / D5's member)
        a = at("nominal")
        a["Fc"] = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
        a["Fs"] = 1.25 * a["Fc"]
    elif member == "r79F_hiFs":                   # stiction ratio 1.6 (hunting-prone variant)
        a = at("nominal")
        a["Fc"] = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
        a["Fs"] = 1.6 * a["Fc"]
    elif member == "b_lo*J_hi":
        a = at("J_hi")
        a["b"] *= (1 / 1.8 if v >= 10.0 else 0.7)
    elif member in ("b_lo*ms_free", "b_lo*ms_free_r79F"):
        a = at("ms_free")
        a["b"] *= at("b_lo")["b"] / at("nominal")["b"]
        if member.endswith("_r79F"):
            a["Fc"] = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
            a["Fs"] = 1.25 * a["Fc"]
    elif member == "ms_free_r79F":
        a = at("ms_free")
        a["Fc"] = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
        a["Fs"] = 1.25 * a["Fc"]
    elif member.endswith("_nf"):
        a = params(member[:-3], v)
        return dict(a, Fc=0.0, Fs=0.0)
    else:
        a = at(member)
    return a


class Plant:
    """Karnopp stick-slip: J th'' + b th' + k sat tanh(th/sat) + friction = u (+ hand); 10 kHz sub-steps; 2 ms
    transport on the lane torque."""

    def __init__(self, members, vs, tau=2):
        P = [params(m, v) for m, v in zip(members, vs)]
        g = lambda k: np.array([p[k] for p in P])  # noqa: E731
        self.J, self.b, self.k, self.sat, self.Fc, self.Fs = g("J"), g("b"), g("k"), g("sat"), g("Fc"), g("Fs")
        B = len(P)
        self.th, self.om = np.zeros(B), np.zeros(B)
        self.buf = np.zeros((tau + 1, B))
        self.tau, self.n = tau, 0

    def delay(self, T):
        L = self.buf.shape[0]
        self.buf[self.n % L] = T
        out = self.buf[(self.n - self.tau) % L].copy()
        self.n += 1
        return out

    def step(self, u, Kh=None, Bh=None, thh=None, dt=1e-3, nsub=10):
        h = dt / nsub
        for _ in range(nsub):
            th, om = self.th, self.om
            net = u - self.k * self.sat * np.tanh(th / self.sat) - self.b * om
            if Kh is not None:
                net = net + Kh * (thh - th) - Bh * om
            stuck = (om == 0.0) & (np.abs(net) <= self.Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(net))
            om_new = om + np.where(stuck, 0.0, (net - self.Fc * fdir) / self.J) * h
            om_new = np.where(stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om))), 0.0, om_new)
            self.om = om_new
            self.th = th + om_new * h


class Frame:
    """gp-0x6a00 = C(motor angle): kappa = d(wheel)/d(motor-linear) from the correction LERP (motor-frame D operand)."""

    def __init__(self):
        c = AM.Cal("v295")
        k = 1159 * 900 / (8 * 256 * 16384)
        lin = np.array([x * 512 / 45 * k / 10.0 for x in c.X])
        cor = np.array(c.Y, float) / 10.0
        phi = np.linspace(0.0, 450.0, 9001)
        self.th = phi + np.interp(phi, lin, cor)
        self.kap = 1.0 + np.gradient(np.interp(phi, lin, cor), phi)

    def kappa(self, th):
        return np.interp(np.abs(th), self.th, self.kap)


FRAME = Frame()

# ------------------------------------------------------------------------------------------------ fork / VM (mine)
_CP = json.loads(str(np.load(KIT / "analysis-2020accord" / "_scratch" / "cache" / "v280" / "r79_fork.npz")
                     ["carparams_json"]))
_M, _L, _AF = _CP["mass"], _CP["wheelbase"], _CP["centerToFront"]
_SF = _M * (_CP["tireStiffnessFront"] * _AF - _CP["tireStiffnessRear"] * (_L - _AF)) / (
    _L ** 2 * _CP["tireStiffnessFront"] * _CP["tireStiffnessRear"])
_SR = _CP["steerRatio"]
MAX_LAT = 3.0 + 9.81 * 0.06


def steer_from_curv(c, v):
    return np.degrees(c * _SR * _L * (1.0 - _SF * v ** 2))


def vm_rate(v):          # deg/s from the 3.589 m/s^3 jerk limit
    v = np.maximum(v, 1.0)
    return steer_from_curv(MAX_LAT / v ** 2, v)


def vm_amax(v):
    v = np.maximum(v, 1.0)
    return steer_from_curv(MAX_LAT / v ** 2, v)


def plan_rate(v):        # the planner: clip_curvature jerk 5 m/s^3, capped at r79's p99 320 deg/s
    return float(min(320.0, steer_from_curv(5.0 / v ** 2, v)))


EBP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
EV = np.array([17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
FORKS = {
    "V298": dict(cap=120.0, clipx=1.0, on=600.0, hard=600.0, deb=0, off=500.0, lead=0.06, take=0.0),
    "A": dict(cap=120.0, clipx=1.0, on=600.0, hard=1200.0, deb=8, off=500.0, lead=0.0, take=0.4),
    "B": dict(cap=250.0, clipx=1.6, on=600.0, hard=1200.0, deb=8, off=500.0, lead=0.0, take=0.4),
    # hypothetical variants (NOT the design): no instant hard path; hard path held 2 frames; B without the takeover
    "B_nohard": dict(cap=250.0, clipx=1.6, on=600.0, hard=1e9, deb=8, off=500.0, lead=0.0, take=0.4),
    "B_h2": dict(cap=250.0, clipx=1.6, on=600.0, hard=1200.0, deb=8, off=500.0, lead=0.0, take=0.4, hard_n=2),
    "B_capOnly": dict(cap=250.0, clipx=1.0, on=600.0, hard=1200.0, deb=8, off=500.0, lead=0.0, take=0.4),
    "B_clipOnly": dict(cap=120.0, clipx=1.6, on=600.0, hard=1200.0, deb=8, off=500.0, lead=0.0, take=0.4),
}


def clip_of(v, clipx):
    sc = np.where(EBP <= 11.75, clipx, 1.0)
    return float(np.interp(v, EBP, EV * sc))


_RE = json.loads((V299 / "D1-firmware-minimal" / "out" / "d1_r79.json").read_text())["reaction"]
TW = dict(a=_RE["J"], b=_RE["b"], fc=_RE["Fc"], c0=_RE["c0"], sd=_RE["res_std"], ac=_RE["ac1"])


# ------------------------------------------------------------------------------------------------ runner
def run(cols, dur, plan, th0=None, hand=None, uext=None, drop_t=None, seed=7, rec=("th", "om", "T", "w", "I", "frz",
                                                                                     "hard", "a3")):
    """cols: list of dict(rule, fork, member, v, [ka twist alpha scale], [ks residual scale], [age 0|10 ms],
    [nz 0/1 residual on], [variant dict]).  plan(t, j_mask) -> (B,) deg.  hand(t) -> None | (Kh, Bh, thh, w_hand).
    uext(t) -> (B,) external wheel torque (T, + left).  Records 1 kHz arrays + 100 Hz fork arrays."""
    B = len(cols)
    vv = np.array([c["v"] for c in cols], float)
    vw = np.round(vv * 3.6 * 64).astype(np.int64)
    lane = Lane([c["rule"] for c in cols], vw, [c.get("variant", {}) for c in cols])
    pl = Plant([c["member"] for c in cols], vv)
    if th0 is not None:
        pl.th = np.asarray(th0, float) * np.ones(B)
    fk = [FORKS[c["fork"]] for c in cols]
    FK = lambda k: np.array([f[k] for f in fk], float)  # noqa: E731
    cap, on, hardv, deb, off, lead, take = FK("cap"), FK("on"), FK("hard"), FK("deb"), FK("off"), FK("lead"), FK("take")
    hard_n = np.array([f.get("hard_n", 1) for f in fk], float)
    chi = np.zeros(B)
    dmax0 = np.minimum(vm_rate(vv), cap) * 0.01
    amax = vm_amax(vv)
    emax0 = np.array([clip_of(c["v"], f["clipx"]) for c, f in zip(cols, fk)])
    ka = np.array([c.get("ka", 1.0) for c in cols])
    ks = np.array([c.get("ks", 1.0) for c in cols]) * np.array([c.get("nz", 1) for c in cols])
    age = np.array([c.get("age", 0) for c in cols])
    rng = np.random.default_rng(seed)
    rngw = np.random.default_rng(seed + 1)
    nT = int(round(dur * 1000))
    nF = nT // 10 + 1
    R = {k: np.zeros((nT, B), np.float32) for k in rec}
    R.update(sp=np.zeros((nF, B), np.float32), o1=np.zeros((nF, B), bool), clipb=np.zeros((nF, B), bool),
             viahard=np.zeros((nF, B), bool), plan=np.zeros((nF, B), np.float32))
    q = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held = q.copy()
    qhist = [q.copy() for _ in range(11)]
    st = np.zeros(B, np.int64)
    cmd = s32(-((-q) << 2))
    wire_q, wire_om, wire_w = [], [], []
    last = pl.th.copy()
    o1 = np.zeros(B, bool)
    c600 = np.zeros(B)
    since = np.full(B, 1e9)
    lat = True
    ramp = 0x8000
    al_f = np.zeros(B)
    om_prev = pl.om.copy()
    a8 = math.exp(-2 * math.pi * 8.0 / 1000.0)
    nz = np.zeros(B)
    plan_z = plan(0.0)
    tt = 0.0
    for n in range(nT):
        tt = n * 1e-3
        if drop_t is not None and tt >= drop_t:
            lat = False
            ramp = max(0, ramp - CAL["ROUT"])
        # ---- fork, 100 Hz (carState i-1 = the 0x14A sample one frame older)
        if n % 10 == 0:
            k = len(wire_q)
            if k >= 2:
                thm, omm, tqm = wire_q[k - 2] / 10.0, wire_om[k - 2], np.abs(wire_w[k - 2]) / 1.024
            else:
                thm, omm, tqm = pl.th.copy(), pl.om.copy(), np.zeros(B)
            if lat:
                c600 = np.where(tqm > on, c600 + 1, 0)
                was = o1
                chi = np.where(tqm > hardv, chi + 1, 0)
                inst = chi >= hard_n
                trig = inst | ((deb > 0) & (c600 >= deb)) | ((deb == 0) & (tqm > on))
                o1 = np.where(was, tqm > off, trig)
                R["viahard"][n // 10] = ~was & o1 & inst
                rel = was & ~o1
                since = np.where(rel, 0.0, since)
                last = np.where(rel, thm, last)
                if n % 50 == 0:
                    plan_z = plan(tt)                                  # 20 Hz model staircase
                kk = np.where(take > 0, np.minimum(1.0, since / np.maximum(take, 1e-9)), 1.0)
                dm = dmax0 * kk
                a1 = np.clip(last + np.clip(plan_z - last, -dm, dm), -amax, amax)
                a2 = np.where(o1, thm + omm * lead, a1)
                em = emax0 * kk
                a3 = np.clip(a2, thm - em, thm + em)
                R["clipb"][n // 10] = np.abs(a3 - a2) > 1e-6
                last = a3
                since = since + 0.01
                sp = a3
            else:
                o1[:] = False
                sp = thm.copy()
                last = thm.copy()
            raw = s16(np.floor(-10.0 * sp + 0.5).astype(np.int64))
            cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
            R["sp"][n // 10], R["o1"][n // 10], R["plan"][n // 10] = sp, o1, plan_z
            nz = TW["ac"] * nz + math.sqrt(1 - TW["ac"] ** 2) * TW["sd"] * rngw.normal(size=B)
        # ---- the torque word gp-0x4f60 (M3 fit, BELIEF model) + any hand
        al_f = a8 * al_f + (1 - a8) * (pl.om - om_prev) * 1000.0
        om_prev = pl.om.copy()
        word = ka * TW["a"] * al_f + TW["b"] * pl.om + TW["fc"] * np.tanh(pl.om / 2.0) + TW["c0"] + ks * nz
        hh = hand(tt) if hand is not None else None
        if hh is not None:
            word = word + hh[3]
        wi = np.clip(np.round(word), -32767, 32767).astype(np.int64)
        # ---- sensors
        om_m = pl.om / FRAME.kappa(pl.th)
        g4f50 = s16(np.round(ABE_PER * om_m + rng.normal(0.0, ABE_NOISE, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        T = lane.tick(held, abe, cmd, wi, ramp, req=1 if lat else 0, act=1 if lat else 0)
        qn = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        qhist.append(qn)
        qhist.pop(0)
        if n % 10 == 4:
            held = np.where(age == 10, qhist[0], qn)
            wire_q.append(qn)
            wire_om.append(pl.om.copy())
            wire_w.append(word.copy())
        u = -pl.delay(T.astype(float))
        if uext is not None:
            u = u + uext(tt)
        if hh is None:
            pl.step(u)
        else:
            pl.step(u, hh[0], hh[1], hh[2])
        L = lane.log
        for kname, val in (("th", pl.th), ("om", pl.om), ("T", T), ("w", word), ("I", L["I"]), ("frz", L["frz"]),
                           ("hard", L["hard"]), ("a3", L["a3"]), ("P", L["P"]), ("D", L["D"])):
            if kname in R:
                R[kname][n] = val
    return R
