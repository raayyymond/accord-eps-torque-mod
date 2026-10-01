# -*- coding: utf-8 -*-
"""fric_lib.py -- REFUTER (friction / nonlinear lens) for DESIGN-ANGLE-LOOP-C0-2026-09-30.  ANALYSIS ONLY.

The lane is the time harness's byte-exact LaneVec arithmetic (harness_time.py, self-tested there against
lane_mirror_v295.lane_tick), with the C0 cave inserted EXACTLY as the design's listing computes it (design sec 1.2):
    G   = G(i) + (((v - X(i)) * S(i)) >> 12)      Q12-slope walk over the 7-row table incl. the 0xFFFF sentinel
    E'  = (E * G) >> 8                            mul r8,r16,r0 ; sar 8
    if |tq| (gp-0x4f68, ld.hu) > 1024:  I8 -= I8 >> 6     (ld.w ; mov ; sar 6 ; sub ; st.w -0x6dd0)
(rec_time.LaneCave uses Honda's divq LERP and a bleed of ((I8>>3)>>6)<<3; this file uses the cave's own arithmetic.)
Guard = A2 + B2: the PID runs iff ramp != 0 and request == 1 (inputs valid).
The plant is harness_time.PlantVec's Karnopp model (10 kHz sub-steps), generalised to PER-COLUMN parameters so that
speeds / members / scenario variants batch in one run, plus an additive torque disturbance d (T counts, + left).
Sensors exactly as harness_time.run: gp-0x6a00 = 0.1 deg quantiser, gp-0x6a56 = 3 ms rate former + 1.93 counts
noise, both refreshed by slot 4 at tick % 10 == 4 AFTER the lane; the fork frame lands at tick % 10 == 0 and reads
the 0x14A angle 60 ms old.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
HERE = Path(__file__).resolve().parent
AL = HERE.parent
sys.path.insert(0, str(AL))
sys.path.insert(0, str(AL.parent / "v295" / "plant"))
import harness_time as HT          # noqa: E402
import lane_mirror_v295 as LM      # noqa: E402
import v294_plant as VP            # noqa: E402
from harness_time import s32, s32g, s16, vlerp  # noqa: E402

# ---------------------------------------------------------------------------------------------------- the C0 cave
TBL = [(691, 256, 249), (1152, 284, 338), (1843, 341, 901), (2880, 569, 2332), (4378, 1422, 724),
       (5990, 1707, 0), (0xFFFF, 1707, 0)]


def cave_G(v: int) -> int:
    """the cave's walk, exactly as listed: v <= X0 -> G0; else find i with X(i) < v <= X(i+1)."""
    v &= 0xFFFF
    if not (v > TBL[0][0]):                     # cmp r13,r8 ; bh L1   (unsigned)
        return TBL[0][1]
    i = 0
    while not (v <= TBL[i + 1][0]):             # ld.hu 6[r9] ; cmp ; bnh SEG ; addi 6
        i += 1
    X, G, S = TBL[i]
    dv = v - X                                  # sub r13,r8
    prod = int(LM.s32(dv * S))                  # mul r13,r8,r0 (low word)
    return G + (prod >> 12)                     # sar 12 ; add


GLUT = np.array([cave_G(v) for v in range(65536)], np.int64)
KP_BASE, KD, KI, ICL, DB = 450, 16, 199, 4096, 0
BLEED_THR = 1024


def spd_counts(v):
    return int(round(v * 3.6 * 64))


def kp_eff(v):
    return KP_BASE * cave_G(spd_counts(v)) / 256.0


class LaneC0:
    """C0 lane, batch.  Per-column: Kp base/Kd/Ki/ICL/DB/bleed on/off may be overridden by arrays (for the variants)."""

    def __init__(self, B, cal=None, kp=KP_BASE, kd=KD, ki=KI, icl=ICL, db=DB, bleed=True, cave=True, gmul=1):
        self.c = HT.base_cal() if cal is None else cal
        self.B = B
        f = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        self.kp, self.kd, self.ki, self.icl, self.db = f(kp), f(kd), f(ki), f(icl), f(db)
        self.bleed = np.broadcast_to(np.asarray(bleed, bool), (B,)).copy()
        self.cave = np.broadcast_to(np.asarray(cave, bool), (B,)).copy()
        self.gmul = f(gmul)                 # EXPERIMENT ONLY: table G scaled (a re-based table), not the design
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.Eprev, self.olag, self.Tprev = z(), z(), z(), z(), z(), z()
        self.log = {}

    def tick(self, angle, rate, cmd, tq, speed, ramp, act, req, i6830=0, pol=-1):
        c, B = self.c, self.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        angle, rate, cmd, tq, speed, ramp, act, req, i6830 = map(full, (angle, rate, cmd, tq, speed, ramp, act, req, i6830))
        x = s16(angle)                                                     # 0x28F4C ld.h -0x6a00 (E1)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        bx = s32g(x * (c["b"] & 0xFFFF))
        as_ = s32g(int(LM.s16(c["a"])) * s_old)
        s_new = s32((as_ >> 10) + (bx >> 10))
        r26 = s32(s_old + s_new)                                           # 0x28FA4 add (E2)
        C = c["C"] & 0xFFFF
        r26 = np.clip(r26, -C, C)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                             # A2 + B2 (bVar2 true when inputs valid)
        sp = s16(cmd)                                                      # 0x29D6A ld.h -0x69ae (E4)
        E = s32g((sp << 2) - r26)                                          # cave: displaced shl 2 ; sub r26
        G = GLUT[speed & 0xFFFF] * self.gmul
        E = np.where(self.cave, s32g(E * G) >> 8, E)                       # cave: mul ; sar 8
        atq = np.abs(tq) & 0xFFFF                                          # gp-0x4f68 (|tq|), ld.hu
        over = self.bleed & (atq > BLEED_THR)
        self.I8 = np.where(over, s32(self.I8 - (self.I8 >> 6)), self.I8)   # cave: 8I -= 8I >> 6 ; st.w
        e5 = E >> 5                                                        # 0x29D7C
        DBv = self.db & 0xFFFF
        exc = np.where(e5 > DBv, e5 - DBv, np.where(e5 < -DBv, e5 + DBv, 0))
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        inc = s32g(exc * (self.ki & 0xFFFF)) >> 3
        I = np.clip(s32g((self.I8 >> 3) + inc), -icl, icl)                 # 0x29DA4..0x29DC2
        I8_new = s32g(I << 3)
        P = np.clip(s32g(E * (self.kp & 0xFFFF)) >> 8, -c["PCL"], c["PCL"])  # 0x29E36 mul ; sar 8 (Kp record flat)
        kd = s32(-(self.kd & 0xFFFF))                                      # E5: subr r0,r7
        D = np.clip(s32g(kd * s16(rate)) >> 3, -10240, 10240)              # E5: ld.h -0x6a56 ; DCL 10240
        S = s32g((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        f = ((vlerp(*c["fadeA"], i6830) * vlerp(*c["fadeB"], i682f)) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)
        self.Eprev = np.where(run, E, 0x7FFFFFFF)
        t1 = s32g(Sc * (c["ob"] & 0xFFFF)) >> 10
        t2 = s32g(int(LM.s16(c["oa"])) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr_pass = s16(s32g(y * ramp) >> 15)
        if c["g74a3"] == 1:
            dz = c["dz"]
            block = ((s16(y) <= dz) & (y >= -(dz & 0xFFFF))) | (s32g(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & block, 0, yr_pass)
        else:
            yr = yr_pass
        k = int(LM.s32(LM.s16(pol) * LM.s16(c["fwd"])))
        r11 = s32g(yr * k) >> 15
        OCL = c["OCL"] & 0xFFFF
        T = np.where(r11 > OCL, LM.s16(c["OCL"]), np.where(r11 < -OCL, -OCL, r11))
        self.Tprev = yr
        self.log = dict(E=np.where(run, E, 0), I=np.where(run, I, 0), P=np.where(run, P, 0), D=np.where(run, D, 0),
                        S=np.where(run, S, 0), f=f, run=run, G=G)
        return s16(T)


# ---------------------------------------------------------------------------------------------------- plant
class Plant:
    """harness_time.PlantVec's Karnopp plant with per-column parameters (arrays of length B) and a disturbance."""

    def __init__(self, J, b, k, Fc, Fs, sat, tau_ms=2):
        f = lambda a: np.asarray(a, float).copy()  # noqa: E731
        self.J, self.b, self.k, self.Fc, self.Fs, self.sat = map(f, (J, b, k, Fc, Fs, sat))
        self.B = self.J.shape[0]
        self.tau = int(tau_ms)
        self.th = np.zeros(self.B)
        self.om = np.zeros(self.B)
        self.Tq = np.zeros((self.tau + 1, self.B))
        self.tq_p = 0

    def push_T(self, T):
        self.Tq[self.tq_p] = T
        self.tq_p = (self.tq_p + 1) % (self.tau + 1)
        return self.Tq[self.tq_p]

    def step(self, u, hand=None, d=0.0, dt=1e-3):
        h = dt / HT.NSUB
        ksat = self.k * self.sat
        for _ in range(HT.NSUB):
            th, om = self.th, self.om
            fnet = u + d - ksat * np.tanh(th / self.sat) - self.b * om
            if hand is not None:
                Kh, Bh, thh = hand
                fnet = fnet + Kh * (thh - th) - Bh * om
            stuck = (om == 0.0) & (np.abs(fnet) <= self.Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
            om_new = om + np.where(stuck, 0.0, (fnet - self.Fc * fdir) / self.J) * h
            om_new = np.where(stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om))), 0.0, om_new)
            self.om = om_new
            self.th = th + om_new * h


def plant_for(members, speeds, fric_scale=None, tau_ms=2):
    fam = VP.family()
    P = {k: [] for k in ("J", "b", "k", "Fc", "Fs", "sat")}
    for i, (m, v) in enumerate(zip(members, speeds)):
        p = fam[m].at(float(v))
        fs = 1.0 if fric_scale is None else fric_scale[i]
        for kk in P:
            val = getattr(p, kk)
            if kk in ("Fc", "Fs"):
                val *= fs
            P[kk].append(val)
    return Plant(**P, tau_ms=tau_ms)


# ---------------------------------------------------------------------------------------------------- closed loop
def run(cols, dur, seed=11, rec_I=False):
    """cols: list of dicts, one per batch column, with keys
         member, v (m/s), ref(t)->deg, tq(t)->gp-0x4f60 counts, hand(t)->(Kh,Bh,th_target_fn) or None,
         d(t)->T counts disturbance, mode(t)-> 'off' | 'engaged' | 'engage_ramp' (ramp +33/tick from 0),
         sp_src(t) -> 'ref' | 'meas'   (what the fork sends), kp/kd/ki/icl/db/bleed/cave overrides.
       Returns recorded arrays (n_t, B)."""
    B = len(cols)
    mem = [c.get("member", "nominal") for c in cols]
    vs = [c["v"] for c in cols]
    pl = plant_for(mem, vs, [c.get("fric", 1.0) for c in cols], tau_ms=cols[0].get("tau_ms", 2))
    lane = LaneC0(B, kp=[c.get("kp", KP_BASE) for c in cols], kd=[c.get("kd", KD) for c in cols],
                  ki=[c.get("ki", KI) for c in cols], icl=[c.get("icl", ICL) for c in cols],
                  db=[c.get("db", DB) for c in cols], bleed=[c.get("bleed", True) for c in cols],
                  cave=[c.get("cave", True) for c in cols], gmul=[c.get("gmul", 1) for c in cols])
    th0 = np.array([c.get("th0", 0.0) for c in cols])
    pl.th = th0.copy()
    rng = np.random.default_rng(seed)
    n_t = int(round(dur * 1000))
    spd = np.array([spd_counts(v) for v in vs], np.int64)
    rec = dict(th=np.zeros((n_t, B), np.float32), om=np.zeros((n_t, B), np.float32), T=np.zeros((n_t, B), np.int16),
               sp=np.zeros((n_t, B), np.float32), ramp=np.zeros((n_t, B), np.int32))
    if rec_I:
        rec.update(I=np.zeros((n_t, B), np.int32), P=np.zeros((n_t, B), np.int32), D=np.zeros((n_t, B), np.int32),
                   f=np.zeros((n_t, B), np.int16), E=np.zeros((n_t, B), np.int32))
    wire = np.zeros((n_t // 10 + 2, B), np.int64)
    nw = 0
    held_th = HT.q_angle(pl.th)
    held_x = np.zeros(B, np.int64)
    hist = [pl.th.copy() for _ in range(4)]
    wire[0] = held_th
    nw = 1
    cmd = 4 * held_th
    ramp = np.zeros(B, np.int64)
    for n in range(n_t):
        t = n * 1e-3
        modes = [c["mode"](t) if callable(c.get("mode")) else c.get("mode", "engaged") for c in cols]
        req = np.array([0 if m == "off" else 1 for m in modes], np.int64)
        act = np.array([0 if m == "off" else 1 for m in modes], np.int64)
        for j, m in enumerate(modes):
            if m == "off":
                ramp[j] = max(0, ramp[j] - 16)
            elif m == "engage_ramp":
                ramp[j] = min(0x8000, ramp[j] + 33)
            else:
                ramp[j] = 0x8000 if m == "engaged" else ramp[j]
        if n % 10 == HT.E4_PHASE:
            th_meas = wire[max(nw - 6, 0)] / 10.0
            thc = np.empty(B)
            for j, c in enumerate(cols):
                src = c["sp_src"](t) if callable(c.get("sp_src")) else c.get("sp_src", "ref")
                if src == "meas" or modes[j] == "off":
                    thc[j] = th_meas[j]
                elif src == "hold":
                    thc[j] = cmd[j] / 40.0
                else:
                    thc[j] = float(c["ref"](t))
            raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
            cmd = np.clip(s32(-(s16(raw) << 2)), -0x4000, 0x4000)
        th_now = pl.th
        hist = [th_now.copy()] + hist[:3]
        tq = np.array([int(round(float(c["tq"](t)))) if callable(c.get("tq")) else int(c.get("tq", 0)) for c in cols],
                      np.int64)
        T = lane.tick(held_th, held_x, cmd, tq, spd, ramp, act, req)
        if n % 10 == HT.SLOT4_PHASE:
            held_th = HT.q_angle(th_now)
            xr = 8.0 * (hist[0] - hist[3]) / 0.003 + rng.normal(0.0, HT.RATE_NOISE, B)
            held_x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
            wire[nw] = held_th
            nw += 1
        Tapp = pl.push_T(T.astype(float))
        hands = [c["hand"](t) if callable(c.get("hand")) else None for c in cols]
        if any(h is not None for h in hands):
            Kh = np.array([h[0] if h is not None else 0.0 for h in hands])
            Bh = np.array([h[1] if h is not None else 0.0 for h in hands])
            thh = np.array([h[2] if h is not None else 0.0 for h in hands])
            hh = (Kh, Bh, thh)
        else:
            hh = None
        d = np.array([float(c["d"](t)) if callable(c.get("d")) else float(c.get("d", 0.0)) for c in cols])
        pl.step(-Tapp, hand=hh, d=d)
        rec["th"][n] = pl.th
        rec["om"][n] = pl.om
        rec["T"][n] = T
        rec["sp"][n] = cmd / 40.0
        rec["ramp"][n] = ramp
        if rec_I:
            rec["I"][n] = lane.log["I"] >> 7
            rec["P"][n] = lane.log["P"]
            rec["D"][n] = lane.log["D"]
            rec["f"][n] = lane.log["f"]
            rec["E"][n] = lane.log["E"]
    rec["wire"] = wire[:nw]
    return rec


def dj_on(rec, t0=0.0, t1=None):
    """the time harness's own dwell_jump detector on the 100 Hz samples of [t0, t1)."""
    n = rec["th"].shape[0]
    idx = np.arange(HT.SLOT4_PHASE, n, 10)
    tt = idx * 1e-3
    w = (tt >= t0) & (tt < (t1 if t1 is not None else 1e9))
    idx = idx[w]
    om_f = rec["om"][idx].astype(float)
    th_f = rec["th"][idx].astype(float)
    ref_f = rec["sp"][idx].astype(float)
    return HT.dwell_jump(om_f, th_f, ref_f)


def slips(rec, t0, t1):
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    w = (tt >= t0) & (tt < t1)
    return HT._slips(rec["th"][w].astype(float), rec["om"][w].astype(float))
