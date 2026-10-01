# -*- coding: utf-8 -*-
r"""harness_time.py -- EXACT 1 kHz TIME-DOMAIN HARNESS for the ZERO-CAVE ANGLE LOOP in the LKAS lane FUN_00028ea6.

Written 2026-09-30 by the `harness-time` subagent.  ANALYSIS ONLY: builds no image, sends nothing, flashes nothing,
touches no fork or firmware file.  Report: analysis-2020accord/studies/angle_loop/reports/HARNESS-TIME-2026-09-30.md

WHAT IS SIMULATED (every tick = 1 ms)
  fork (100 Hz, 0xE4)  -> FUN_00052676 (gp-0x69ae = clamp(-4*raw, +-16384), or the 0x7FFF fault sentinel)
  -> THE EDITED LANE, integer-exact (LaneVec, a numpy batch port of lane_mirror_v295.lane_tick with the switches
     x_src='angle', fb_op='sum', sp_src='69ae', d_src 'E'|'rate', i_reset_on_ramp0; selftest() proves it equal to
     the scalar byte-exact mirror tick for tick on random inputs, every branch, including skips, the sentinel, the
     fade, the sign-hold gate and int32 wraps)
  -> transport delay (2 ms nominal) -> u = -T (T counts, + = LEFT)
  -> the identified plant family (analysis-2020accord/studies/v295/plant/v294_plant.family(), speed-interpolated),
     J*th'' + b*th' + k*sat*tanh(th/sat) + Fc*sgn(th') = u (+ driver hand), sub-stepped at 10 kHz, Karnopp stick
     (stuck while th' == 0 and |u - spring| <= Fs)
  -> sensors: gp-0x6a00 = 0.1 deg quantiser of th, and gp-0x6a56 = round(8*(th[n]-th[n-3])/3 ms) + white noise
     (1.93 counts, the record's standstill floor), BOTH sampled by RTOS slot 4 on (tick % 10 == 4) AFTER the lane has
     run (the lane sees a 100 Hz sample-and-hold, age 1..10 ms, mean 5.5 ms).

FORK OUTER LOOP (how it is modelled, BELIEF):
  outer='ff' (default)  stock LatControlAngle in angle mode is a FEEDFORWARD of the planner's angle: th_sp = th_ref(t)
                        sampled at 100 Hz (ZOH) -- the 60 ms round trip does not act because nothing is fed back.
  outer='pi'            a stand-in for the path-level loop: th_sp = th_ref + c, c += (10 ms / tau_o)*(th_ref - th_wire[k-6]),
                        th_wire = the 0x14A angle six frames (60 ms) old, tau_o = 1.0 s.  Used only as an interaction check.
  inactive              the fork sends the MEASURED angle (raw = -10*th_wire[k-6]) or 0 (scenario 'dis_zero').

USAGE
  python harness_time.py --selftest          # LaneVec == lane_mirror_v295.lane_tick, plant sanity, hf20 check
  python harness_time.py --sweep             # the brief's grid (456 configs), all speeds, all scenarios   (~4 min, 9 procs)
  python harness_time.py --refined           # the refinement (159 configs incl. the diagnostic output-lag poles)  (~2 min)
  python harness_time.py --final             # the 8 candidates (FLAT / ANGLE / SPEED), every scenario, + robustness over
                                             # the family + the outer 'pi' loop                                (~10 min)
  python harness_time.py --payoff            # what a cave buys: finer angle / fresh 1 kHz operands            (~2 min)
  python harness_time.py --payoff2           # finer setpoint / 1 kHz setpoint interpolation                  (~2 min)
  python harness_time.py --robust-cave       # the full-resolution option across the family                   (~7 min)
  python harness_time.py --report            # writes reports/HARNESS-TIME-2026-09-30.md (harness_time_report.py)
  python harness_time.py --all               # all of the above in order (the selftest output is cached for the report)
Fixed seeds everywhere; no network.  Results cache: _scratch/angle_loop/harness-time/ (repo root, gitignored).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

# ---- PATH BOOTSTRAP -- walk up to .pkgroot, then put the kit root and every code subfolder on the path
_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
HERE = Path(__file__).resolve().parent
KIT = HERE.parents[2]                                   # .../accord-eps-torque-mod
for _q in (HERE, KIT / "analysis-2020accord" / "studies" / "v295" / "plant"):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import lane_mirror_v295 as LM          # noqa: E402  (byte-exact scalar mirror, V295 image hash-checked)
import v294_plant as VP                # noqa: E402  (the identified plant family)

OUT = KIT / "_scratch" / "angle_loop" / "harness-time"
REPORT = HERE / "reports" / "HARNESS-TIME-2026-09-30.md"

SPEEDS = (3.0, 5.0, 8.0, 12.5, 19.0, 26.0, 30.0)
# turn amplitude per speed (deg of steering wheel): the brief fixes 90/30/3 at 3/8/26 m/s; the rest are interpolated at
# a similar lateral acceleration (0.3-0.9 m/s^2 at SR 16, L 2.83 m, no understeer) -- BELIEF on "hand-sized"
A_TURN = {3.0: 90.0, 5.0: 50.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0, 30.0: 2.5}
RAMP_S = {3.0: 3.0, 5.0: 2.0, 8.0: 1.0, 12.5: 1.0, 19.0: 1.0, 26.0: 1.0, 30.0: 1.0}
SIN_FRAC = 0.3                        # lane-keeping sinusoid amplitude = 0.3 * A_TURN
SMALL_SIN = 1.0                       # the straight-road correction: +-1 deg at 0.3 Hz at every speed
RATE_NOISE = 1.93                     # counts rms on gp-0x6a56 (V294-PLANT-IDENT-r71b.md sec 4, standstill)
E4_PHASE = 0                          # 0xE4 frame lands on tick % 10 == 0 (BELIEF; the RX task phase is not traced)
SLOT4_PHASE = 4                       # slot 4 runs on tick % 10 == 4 (EVIDENCE, FUN_00014be4)
NSUB = 10                             # plant sub-steps per 1 ms tick (10 kHz)
RAIL = 2461                           # delivered rail at S = 15360 (EVIDENCE, lane_mirror)
V295_HF20 = 3.85                      # |P/x| at 20 Hz on V295 (record; recomputed in selftest)
HF_LINE = 2.0                         # T counts rms in 5-30 Hz above which a run carries a lane-made line (BELIEF:
                                      # the record's quiet-cruise tap residual is 0.66-0.87 counts per 5 Hz band)


# ======================================================================================================================
# integer helpers (int64 numpy; >> is the V850 sar)
# ======================================================================================================================
_WRAPS = {"n": 0}


def s32(a):
    a = np.asarray(a, np.int64)
    w = ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)
    return w


def s32g(a):
    """s32 that COUNTS wraps (the int32 guard): a wrap where the V850 mul keeps the low word is reported."""
    a = np.asarray(a, np.int64)
    w = ((a + (1 << 31)) & 0xFFFFFFFF) - (1 << 31)
    _WRAPS["n"] += int(np.count_nonzero(w != a))
    return w


def s16(a):
    a = np.asarray(a, np.int64)
    return ((a + (1 << 15)) & 0xFFFF) - (1 << 15)


def vlerp(X, Y, u):
    """Honda's integer LERP (lane_mirror_v295.lerp), vectorised: flat below X[0] / at-or-above X[-1], the
    `while X[k] <= u` walk, divq truncation toward zero.  X, Y: (n,) shared or (B, n) per member; u: (B,)."""
    u = np.asarray(u, np.int64)
    B = u.shape[0]
    X = np.asarray(X, np.int64)
    Y = np.asarray(Y, np.int64)
    if X.ndim == 1:
        X = np.broadcast_to(X, (B, X.shape[0]))
        Y = np.broadcast_to(Y, (B, Y.shape[0]))
    n = X.shape[1]
    r = np.arange(B)
    k = np.clip(np.sum(X <= u[:, None], axis=1), 1, n - 1)
    x0, x1, y0, y1 = X[r, k - 1], X[r, k], Y[r, k - 1], Y[r, k]
    num = (y1 - y0) * (u - x0)
    den = x1 - x0
    den_s = np.where(den == 0, 1, den)
    q = np.abs(num) // np.abs(den_s)
    mid = y0 + np.where((num < 0) != (den_s < 0), -q, q)
    return np.where(u <= X[:, 0], Y[:, 0], np.where(u >= X[:, -1], Y[:, -1], mid))


# ======================================================================================================================
# calibration: V295 image (hash-checked by lane_mirror_v295.load_cal) + the angle-loop cal edits
# ======================================================================================================================
def base_cal():
    c = LM.load_cal()
    c = dict(c, a=0, b=8192, C=65535)          # 0xC63E8 -> 0, 0xC63EA -> 8192, 0xC62E6 -> 65535 (the angle-loop cals)
    return c


class Cfg:
    """a BATCH of lane configurations (one per member).  Fields are numpy arrays of length B (or (B, n) tables)."""

    def __init__(self, rows):
        self.rows = rows
        self.B = len(rows)
        g = lambda k, d=None: np.array([r.get(k, d) for r in rows], np.int64)  # noqa: E731
        self.kpX = np.array([r["kpX"] for r in rows], np.int64)
        self.kpY = np.array([r["kpY"] for r in rows], np.int64)
        self.kdX = np.array([r.get("kdX", (0, 11, 22, 32)) for r in rows], np.int64)
        self.kdY = np.array([r.get("kdY", (0, 0, 0, 0)) for r in rows], np.int64)
        self.Ki = g("Ki", 0)
        self.ICL = g("ICL", 10240)
        self.DB = g("DB", 4)
        self.DCL = g("DCL", 0)
        self.d_rate = np.array([bool(r.get("d_rate", False)) for r in rows])
        self.e6 = np.array([bool(r.get("e6", False)) for r in rows])
        self.key_speed = np.array([r.get("key", "idx") == "speed" for r in rows])
        self.guard_and = np.array([bool(r.get("guard_and", False)) for r in rows])
        self.oa = g("oa", 992)
        self.ob = g("ob", 507)
        self.labels = [r.get("label", "") for r in rows]

    def subset(self, idx):
        return Cfg([self.rows[i] for i in idx])


def row(kp, Ki=0, ICL=10240, DB=4, Kd=0, e6=False, label=None, kpX=(0, 68, 112, 136, 208), kpY=None, oa=992, ob=507,
        kdX=(0, 11, 22, 32), kdY=None, key="idx"):
    """one configuration.  kp = flat Kp (all five knots) unless kpY is given (an idx schedule).  Kd > 0 = edit (5)
    (D on the 100 Hz rate, DCL = 10240, the stock clamp); Kd == 0 = the V295 D (Kd 0, DCL 0)."""
    kpY = tuple(int(kp) for _ in range(5)) if kpY is None else tuple(int(v) for v in kpY)
    r = dict(kpX=tuple(int(v) for v in kpX), kpY=kpY, Ki=int(Ki), ICL=int(ICL), DB=int(DB), e6=bool(e6),
             oa=int(oa), ob=int(ob), kdX=tuple(int(v) for v in kdX), key=key)
    if kdY is not None:
        r.update(kdY=tuple(int(v) for v in kdY), DCL=10240, d_rate=True)
    elif Kd:
        r.update(kdY=(int(Kd),) * 4, DCL=10240, d_rate=True)
    else:
        r.update(kdY=(0, 0, 0, 0), DCL=0, d_rate=False)
    sched = "flat" if len(set(kpY)) == 1 else "idx" + "/".join(str(v) for v in kpY)
    r["label"] = label or ("Kp%s Ki%d ICL%d DB%d Kd%d%s%s" % (kpY[0] if sched == "flat" else sched, Ki, ICL, DB, Kd,
                                                            " e6" if e6 else "",
                                                            "" if (oa, ob) == (992, 507) else " lag%d/%d" % (oa, ob)))
    return r


# ======================================================================================================================
# THE EDITED LANE, vectorised (mirror of lane_mirror_v295.lane_tick with the angle-loop switches)
# ======================================================================================================================
class LaneVec:
    def __init__(self, cal, cfg: Cfg):
        self.c = cal
        self.cfg = cfg
        B = cfg.B
        z = lambda: np.zeros(B, np.int64)  # noqa: E731
        self.s, self.lane_ok, self.I8, self.Eprev, self.olag, self.Tprev = z(), z(), z(), z(), z(), z()
        self.log = {}

    def tick(self, angle, rate, cmd, tq, i6830, speed, ramp, act, req, pol=-1):
        c, g = self.c, self.cfg
        B = g.B
        full = lambda v: np.broadcast_to(np.asarray(v, np.int64), (B,)).copy()  # noqa: E731
        uniform = all(np.ndim(q) == 0 for q in (cmd, tq, i6830, speed))
        if uniform:      # scalar path: identical integer arithmetic (LM.lerp == vlerp), computed once for the batch
            cmd_s, tq_s, i6830_s, spd_s = int(cmd), int(tq), int(i6830), int(speed)
        angle, rate, cmd, tq, i6830, speed = map(full, (angle, rate, cmd, tq, i6830, speed))
        ramp, act, req = full(ramp), full(act), full(req)
        # -------- fb filter 0x28F4C..0x28FBE, x = gp-0x6a00 (edit 1), add r9,r26 (edit 2) -------------------------
        x = s16(angle)                                                     # 0x28F4C ld.h -0x6a00[gp],r7
        valid = (x >= -12000) & (x <= 12000)                               # 0x28F50..0x28F58
        s_old = np.where(self.lane_ok == 1, self.s, 0)                     # 0x28F66..0x28F84
        bx = s32g(x * (c["b"] & 0xFFFF))                                   # 0x28F8E mul
        as_ = s32g(int(LM.s16(c["a"])) * s_old)                            # 0x28F92 mul
        s_new = s32((as_ >> 10) + (bx >> 10))                              # 0x28F9A/0x28FA0 sar ; 0x28FA2 add
        r26 = s32(s_old + s_new)                                           # 0x28FA4 add r9,r26  (edit 2)
        C = c["C"] & 0xFFFF
        r26 = np.clip(r26, -C, C)                                          # 0x28FA6..0x28FBC
        self.s = np.where(valid, s_new, self.s)                            # 0x28FA8 st.w (valid path only)
        r26 = np.where(valid, r26, 0)                                      # 0x290B6 mov 0,r26 on the bail
        self.lane_ok = np.where(valid, 1, 2)
        # -------- guard 0x29A48..0x29A64 (edit 6 = bne -> bv: skip iff ramp == 0) ------------------------------
        run = valid & np.where(g.guard_and, (ramp != 0) & (req == 1),             # Fix A2 0x29A56 bne -> be (parallel
                               (ramp != 0) | ((~g.e6) & (req == 1)))             # trace; BELIEF here, not in the mirror)
        # -------- setpoint chain for idx (0x29032..0x29CFA); sp itself = gp-0x69ae (edit 4 at 0x29D6A) ---------
        if uniform:
            idx_s, _, _ = LM.setpoint_chain(cmd_s, c, tq=tq_s, i6830=i6830_s, speed=spd_s)
            idx = np.full(B, idx_s, np.int64)
            i682f = np.full(B, min(abs(tq_s >> 5), 255), np.int64)
        else:
            r13 = s16(cmd)                                                 # 0x29032
            LIM = vlerp(*c["lim"], speed) & 0xFFFF                         # 0x28FC8..0x29036
            r22 = np.clip(r13, -LIM, LIM)                                  # 0x2903A..0x29044
            i682f = np.minimum(np.abs(tq >> 5), 255)                       # 0x29048..0x29068
            same = (r22 < 0) == (tq < 0)                                   # 0x29A8E..0x29A9E
            taper = np.where(same, vlerp(*c["tap_same"], i682f), vlerp(*c["tap_opp"], i682f))
            spF = vlerp(*c["spF"], i6830)
            G = (spF * taper) & 0xFFFF                                     # 0x29CB4 mulu ; andi
            v = s32(G * r22) >> 16                                         # 0x29CBC mul ; sar 0x10
            v = np.where(i682f > c["cut"], 0, v)                           # 0x29A86 (cut 255: unsatisfiable)
            v = v >> 6                                                     # 0x29CD6
            v = np.clip(v, -c["idx_lo"], c["idx_hi"])
            idx = np.abs(v)                                                # 0x29CF6
        sp = s16(cmd)                                                      # 0x29D6A ld.h -0x69ae[gp],r16  (edit 4)
        E = s32g((sp << 2) - r26)                                          # 0x29D76 shl 2 ; 0x29D78 sub
        # -------- I 0x29D7A..0x29DE4 ----------------------------------------------------------------------------
        e5 = E >> 5
        DB = g.DB & 0xFFFF
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        icl = ((g.ICL & 0xFFFF) << 10) >> 3
        inc = s32g(exc * (g.Ki & 0xFFFF)) >> 3
        I = np.clip(s32g((self.I8 >> 3) + inc), -icl, icl)
        I8_new = s32g(I << 3)
        # -------- P 0x29DC6..0x29E5C ----------------------------------------------------------------------------
        key = np.where(g.key_speed, (speed >> 8) & 0xFF, idx)              # 'speed': ld.bu -0x6a5d[gp] (BELIEF edit)
        kp = vlerp(g.kpX, g.kpY, key & 0xFFFF) & 0xFFFF
        P = np.clip(s32g(E * kp) >> 8, -c["PCL"], c["PCL"])
        # -------- D 0x29E5E..0x29F06 (edit 5 swaps the operand to -Kd * gp-0x6a56) -----------------------------
        kd_l = vlerp(g.kdX, g.kdY, key & 0xFF)
        r27 = np.where((self.Eprev >= -768000) & (self.Eprev <= 768000), self.Eprev, E)
        kd = np.where(g.d_rate, s32(-(kd_l & 0xFFFF)), kd_l & 0xFFFF)
        r8 = np.where(g.d_rate, s16(rate), s32(E - r27))
        D = np.clip(s32g(kd * r8) >> 3, -g.DCL, g.DCL)
        # -------- sum, post-PID fade, sum clamp 0x29F18..0x2A162 ------------------------------------------------
        S = s32g((I >> 7) + P + D)
        if uniform:
            f = ((LM.lerp(*c["fadeA"], i6830_s) * LM.lerp(*c["fadeB"], int(i682f[0]))) & 0xFFFF) >> 8
        else:
            A = vlerp(*c["fadeA"], i6830)
            Bf = vlerp(*c["fadeB"], i682f)
            f = ((A * Bf) & 0xFFFF) >> 8
        Sf = s32g(S * f) >> 8
        SCL = c["SCL"] & 0xFFFF
        Sc = np.where(Sf > SCL, LM.s16(c["SCL"]), np.where(Sf < -SCL, LM.s16(-SCL), s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8_new, 0)                                  # 0x2A190 (0 on skip)
        self.Eprev = np.where(run, E, 0x7FFFFFFF)                           # 0x2A18C
        # -------- output lag 0x2A174..0x2A1B0 (per-member oa/ob so a lag-pole variant can be tested) ----------
        t1 = s32g(Sc * (g.ob & 0xFFFF)) >> 10
        t2 = s32g(s16(g.oa) * self.olag) >> 10
        o_new = s32(t2 + t1)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        # -------- sign-hold gate 0x2A198..0x2A1E4 ---------------------------------------------------------------
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
        self.log = dict(r26=r26, E=np.where(run, E, 0), I=np.where(run, I, 0), P=np.where(run, P, 0),
                        D=np.where(run, D, 0), Sc=Sc, y=y, yr=yr, idx=idx, kp=kp, run=run)
        return s16(T)


# ======================================================================================================================
# THE PLANT, vectorised, 10 kHz sub-steps, Karnopp stick; optional collocated two-mass mode (stress members only)
# ======================================================================================================================
class PlantVec:
    def __init__(self, member, v, B, tau_ms=None):
        p = member.at(float(v))
        self.p = p
        self.B = B
        self.J, self.b, self.k, self.Fc, self.Fs, self.sat = p.J, p.b, p.k, p.Fc, p.Fs, p.sat
        self.tau = int(p.tau_ms if tau_ms is None else tau_ms)
        self.two = p.f2 > 0
        if self.two:
            self.Jw = p.J * p.r2
            self.Jm = p.J - self.Jw
            mu = self.Jm * self.Jw / p.J
            self.Ktb = (2 * np.pi * p.f2) ** 2 * mu
            self.ctb = 2 * p.zeta2 * np.sqrt(self.Ktb * mu)
        else:
            self.Jm = p.J
        self.th = np.zeros(B)
        self.om = np.zeros(B)
        self.thw = np.zeros(B)
        self.omw = np.zeros(B)
        self.Tq = np.zeros((self.tau + 1, B))
        self.tq_p = 0

    def push_T(self, T):
        """store this tick's lane torque; return the torque written tau ticks ago (the transport delay)."""
        self.Tq[self.tq_p] = T
        self.tq_p = (self.tq_p + 1) % (self.tau + 1)
        return self.Tq[self.tq_p]

    def step(self, u, hand=None, dt=1e-3):
        """advance 1 ms under motor-side torque u (T counts, + left).  hand = (Kh, Bh, th_h): a driver hand on the
        WHEEL side (rigid: the same body)."""
        h = dt / NSUB
        ksat = self.k * self.sat
        for _ in range(NSUB):
            th, om = self.th, self.om
            fnet = u - ksat * np.tanh(th / self.sat) - self.b * om
            if self.two:
                fnet = fnet - self.Ktb * (th - self.thw) - self.ctb * (om - self.omw)
                if hand is not None:
                    Kh, Bh, thh = hand
                    fw = Kh * (thh - self.thw) - Bh * self.omw
                else:
                    fw = 0.0
            elif hand is not None:
                Kh, Bh, thh = hand
                fnet = fnet + Kh * (thh - th) - Bh * om
            stuck = (om == 0.0) & (np.abs(fnet) <= self.Fs)
            fdir = np.where(om != 0.0, np.sign(om), np.sign(fnet))
            om_new = om + np.where(stuck, 0.0, (fnet - self.Fc * fdir) / self.Jm) * h
            om_new = np.where(stuck | ((om != 0.0) & (np.sign(om_new) != np.sign(om))), 0.0, om_new)
            if self.two:
                aw = (self.Ktb * (th - self.thw) + self.ctb * (om - self.omw) + fw) / self.Jw
                self.omw = self.omw + aw * h
                self.thw = self.thw + self.omw * h
            self.om = om_new
            self.th = th + om_new * h


# ======================================================================================================================
# sensors
# ======================================================================================================================
def q_angle(th):
    """gp-0x6a00 counts from the plant angle (deg, + left): a uniform 0.1 deg quantiser, round half up.  BELIEF: the
    firmware's staircase is ceil(linear) + trunc(VGR correction) on 1/32-LSB motor counts (angle_signal_mirror), i.e.
    0.1 deg steps with an offset <= 1 LSB and an occasional 2-count step where the correction LERP increments."""
    return np.floor(10.0 * th + 0.5).astype(np.int64)


# ======================================================================================================================
# scenarios
# ======================================================================================================================
def scenario(name, v):
    """returns dict(dur s, ref(t)->deg array fn, events, tq(t), hand, c63f6, inactive, outer).  Amplitudes: A_TURN."""
    A = A_TURN[v]
    Ah = 0.5 * A
    tr = RAMP_S[v]
    s = dict(name=name, v=v, events=[], hand=None, c63f6=16, inactive="meas", outer="ff", tq=None)
    if name == "rh":                                  # ramp-and-hold, both directions, return to centre
        t1, t2 = 0.5, 0.5 + tr
        t3 = t2 + 3.0
        t4 = t3 + 2 * tr
        t5 = t4 + 3.0
        t6 = t5 + tr
        dur = t6 + 2.0

        def ref(t):
            return np.interp(t, [0, t1, t2, t3, t4, t5, t6, dur], [0, 0, A, A, -A, -A, 0, 0])
        s.update(dur=dur, ref=ref, holds=[(t2, t3, A), (t4, t5, -A), (t6, dur, 0.0)])
    elif name in ("s02", "s05", "ssm"):
        f = {"s02": 0.2, "s05": 0.5, "ssm": 0.3}[name]
        amp = SMALL_SIN if name == "ssm" else SIN_FRAC * A
        ncyc = {"s02": 2.6, "s05": 4.6, "ssm": 3.1}[name]
        dur = ncyc / f

        def ref(t, f=f, amp=amp):
            return amp * np.sin(2 * np.pi * f * t)
        s.update(dur=dur, ref=ref, f=f, amp=amp, score_from=1.0 / f)
    elif name == "st":                                # step and 2 s hold
        dur = 3.0
        s.update(dur=dur, ref=lambda t: np.where(t >= 0.5, Ah, 0.0), t_step=0.5, step=Ah)
    elif name.startswith("ov"):                       # driver override: fade to the floor for 1 s, request held
        tg, tramp, thold = 2.5, 0.3, 1.0
        trel = tg + tramp + thold
        dur = trel + 3.0
        s.update(dur=dur, ref=lambda t: np.interp(t, [0, 0.5, 1.5, dur], [0, 0, Ah, Ah]), t_grab=tg, t_rel=trel,
                 hand=dict(t0=tg, tramp=tramp, t_rel=trel, delta=-Ah, Kh=2000.0, Bh=30.0),
                 tq=lambda t: np.where((t >= tg) & (t < trel), 2400.0 * np.clip((t - tg) / tramp, 0, 1),
                                       np.where((t >= trel) & (t < trel + 0.03), 2400.0 * (1 - (t - trel) / 0.03), 0.0)))
        if name in ("ov_latch", "ov_latch_e6"):
            s["events"] = [(tg + tramp, "latch_on"), (trel, "latch_off")]
    elif name.startswith("sen"):                      # 0xE4 fault sentinel while holding a turn
        sgn = 1.0 if "_L" in name else -1.0
        tf = 2.5
        dur = 6.0
        s.update(dur=dur, ref=lambda t, sg=sgn: np.interp(t, [0, 0.5, 1.5, dur], [0, 0, sg * Ah, sg * Ah]), t_fault=tf,
                 events=[(tf, "fault")], c63f6=328 if name.endswith("328") else 16)
    elif name.startswith("dis"):                      # request drop (openpilot disengage) while holding a turn
        td = 2.5
        dur = 5.5
        s.update(dur=dur, ref=lambda t: np.interp(t, [0, 0.5, 1.5, dur], [0, 0, Ah, Ah]), t_dis=td,
                 events=[(td, "disengage")], inactive="zero" if name == "dis_zero" else "meas")
    else:
        raise KeyError(name)
    return s


SCENARIOS = ("rh", "s02", "s05", "ssm", "st", "ov_fade", "ov_latch", "ov_latch_e6",
             "sen_L16", "sen_L328", "sen_R16", "sen_R328", "dis_meas", "dis_zero")
SC_TRACK = ("rh", "s02", "s05", "ssm", "st")


# ======================================================================================================================
# the closed-loop run
# ======================================================================================================================
def run(scn, cfg: Cfg, member, v, cal=None, outer="ff", tau_o=1.0, seed=11, rec_extra=False, ang_mult=1, fresh=False,
        sp_fine=False, sp_interp=False):
    """ang_mult > 1: the lane's x is the angle at (0.1 / ang_mult) deg resolution with fb gain b = 8192 / ang_mult, so
    r26 = 16 * theta (0.1 deg counts) is unchanged and only the RESOLUTION changes (a cave reading the motor-count
    accumulator could supply up to 32x; the +-12000 gate then caps |theta| at 1200 / ang_mult deg).  fresh: the lane's
    angle and rate operands are refreshed every tick (1 kHz, gp-0x69ca / gp-0x6abe class) instead of held by slot 4.
    Both are CAVE options, simulated to size their payoff; the default (1, False) is the in-place edit set.
    sp_fine: gp-0x69ae carries the setpoint at 0.025 deg (every value, not only multiples of 4 -- what the handler's
    shl 2 throws away; an interface/handler change, BELIEF).  sp_interp: the setpoint is ramped linearly over each
    10 ms frame at 1 kHz (a setpoint-interpolation cave, V288's class) -- one frame of extra delay."""
    cal = base_cal() if cal is None else cal
    if ang_mult != 1:
        cal = dict(cal, b=8192 // int(ang_mult))
    if scn["name"] == "ov_latch_e6":                    # the e6 variant: force edit (6) on every member
        cfg = Cfg([dict(r, e6=True) for r in cfg.rows])
    elif scn["name"] == "ov_latch":
        cfg = Cfg([dict(r, e6=False) for r in cfg.rows])
    B = cfg.B
    lane = LaneVec(cal, cfg)
    pl = PlantVec(member, v, B)
    rng = np.random.default_rng(seed)
    n_t = int(round(scn["dur"] * 1000))
    spd = int(round(v * 3.6 * 64))                      # gp-0x6a5e, 64 counts per km/h
    c63f6 = scn["c63f6"]
    # recorded series
    th_r = np.zeros((n_t, B), np.float32)
    om_r = np.zeros((n_t, B), np.float32)
    T_r = np.zeros((n_t, B), np.int16)
    I_r = np.zeros((n_t, B), np.int32) if rec_extra else None
    P_r = np.zeros((n_t, B), np.int32) if rec_extra else None
    sp_r = np.zeros((n_t, B), np.int32)
    wire = np.zeros((n_t // 10 + 2, B), np.int64)      # gp-0x6a00 as published at each slot-4 pass (0x14A)
    nw = 0
    held_th = np.zeros(B, np.int64)
    held_x = np.zeros(B, np.int64)
    hist = [np.zeros(B) for _ in range(4)]              # plant angle at tick starts n, n-1, n-2, n-3
    cmd = np.zeros(B, np.int64)
    corr = np.zeros(B)
    ramp, act, req = 0x8000, 1, 1
    mode = "engaged"
    events = sorted(scn["events"])
    ev_i = 0
    hand = scn["hand"]
    if hand is not None:
        n_h0, n_hrel, n_hramp = int(round(hand["t0"] * 1000)), int(round(hand["t_rel"] * 1000)), int(round(hand["tramp"] * 1000))
        th_grab = np.zeros(B)
    tqf = scn["tq"]
    sen = False
    _WRAPS["n"] = 0
    for n in range(n_t):
        t = n * 1e-3
        while ev_i < len(events) and t >= events[ev_i][0] - 1e-9:
            kind = events[ev_i][1]
            mode = {"fault": "fault", "disengage": "dis", "latch_on": "latch", "latch_off": "relatch"}[kind]
            if kind == "fault":
                sen = True
            ev_i += 1
        # ---- engage SM (ramp gp-0x69b0, act gp-0x6806, request gp-0x6805), common to the batch
        if mode == "engaged":
            ramp, act, req = 0x8000, 1, 1
        elif mode in ("fault", "dis"):
            ramp, act, req = max(0, ramp - c63f6), 0, (0xFF if mode == "fault" else 0)
        elif mode == "latch":                           # state 5: -0xC63F4 (328) per tick, request still 1
            ramp, act, req = max(0, ramp - 328), 0, 1
        elif mode == "relatch":                         # state 1 -> 3: +0xC63F8 (33) per tick, act := 1
            ramp, act, req = min(0x8000, ramp + 33), 1, 1
        # ---- the fork frame (100 Hz)
        if n % 10 == E4_PHASE and not sen:
            k = n // 10
            th_meas = wire[max(nw - 6, 0)] / 10.0 if nw else np.zeros(B)      # the 0x14A angle ~60 ms old
            if mode in ("dis",):
                thc = th_meas if scn["inactive"] == "meas" else np.zeros(B)
            else:
                thc = np.full(B, float(scn["ref"](np.array(k * 0.01))))
                if outer == "pi":
                    corr = corr + (0.01 / tau_o) * (thc - th_meas)
                    thc = thc + corr
            raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))          # 0xE4 STEER_TORQUE = -10*theta_sp
            cmd_new = np.clip(s32(-(s16(raw) << 2)), -0x4000, 0x4000)       # FUN_00052676
            if sp_fine:
                cmd_new = np.clip(np.floor(40.0 * thc + 0.5).astype(np.int64), -0x4000, 0x4000)
            if sp_interp:
                cmd_prev, cmd_next = cmd.copy(), cmd_new
            else:
                cmd = cmd_new
        if sp_interp and not sen and n >= 10:
            ph = (n - E4_PHASE) % 10 + 1
            cmd = cmd_prev + ((cmd_next - cmd_prev) * ph) // 10
        elif sp_interp and not sen:
            cmd = cmd_new
        if sen:
            cmd = np.full(B, LM.SENTINEL, np.int64)
        # ---- tick-start snapshot of the plant angle (the 1 kHz motor-position snapshot)
        th_now = pl.th                                  # motor-side angle (the encoder side in the two-mass option)
        hist = [th_now.copy()] + hist[:3]
        tq = 0 if tqf is None else int(round(float(tqf(np.array(t)))))
        # ---- the lane (slot 0), on the HELD angle and rate
        cmd_in = int(cmd[0]) if bool((cmd == cmd[0]).all()) else cmd
        T = lane.tick(held_th, held_x, cmd_in, tq, 0, spd, ramp, act, req)
        # ---- slot 4 (100 Hz): refresh gp-0x6a00 and gp-0x6a56 from this tick's inputs, AFTER the lane
        if n % 10 == SLOT4_PHASE or fresh:
            held_th = np.floor(10.0 * ang_mult * th_now + 0.5).astype(np.int64) if ang_mult != 1 else q_angle(th_now)
            xr = 8.0 * (hist[0] - hist[3]) / 0.003 + rng.normal(0.0, RATE_NOISE, B)
            held_x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
        if n % 10 == SLOT4_PHASE:
            wire[nw] = q_angle(th_now)                   # the 0x14A angle stays 0.1 deg at 100 Hz
            nw += 1
        # ---- transport delay, plant
        Tapp = pl.push_T(T.astype(float))
        hh = None
        if hand is not None and n_h0 <= n < n_hrel:
            if n == n_h0:
                th_grab = pl.th.copy()
            frac = min(1.0, (n - n_h0) / n_hramp)
            hh = (hand["Kh"], hand["Bh"], th_grab + frac * hand["delta"])
        pl.step(-Tapp, hand=hh)
        th_r[n] = pl.th
        om_r[n] = pl.om
        T_r[n] = T
        sp_r[n] = cmd
        if rec_extra:
            I_r[n] = lane.log["I"] >> 7
            P_r[n] = lane.log["P"]
    out = dict(th=th_r, om=om_r, T=T_r, sp=sp_r, wire=wire[:nw], wraps=_WRAPS["n"])
    if rec_extra:
        out.update(I=I_r, P=P_r)
    return out


# ======================================================================================================================
# metrics
# ======================================================================================================================
def _bp(x, lo, hi, fs=1000.0):
    from scipy import signal
    sos = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def _peak_f(T):
    """frequency (Hz) of the largest 5-30 Hz PSD bin of T (Welch, 1 s segments)."""
    from scipy import signal
    if T.shape[0] < 1000:
        return np.zeros(T.shape[1])
    f, P = signal.welch(T - T.mean(0), fs=1000.0, nperseg=1000, axis=0)
    band = (f >= 5) & (f <= 30)
    return f[band][np.argmax(P[band], axis=0)]


def _slips(th, om):
    """STICK-SLIP inside a hold: number of slips that follow a stuck interval of >= 100 ms (omega exactly 0) and move
    the wheel >= 0.1 deg (one angle LSB) within the next 0.5 s.  A clean hold (settled, or tracking a still reference)
    scores 0; a hold that creeps toward its target in jumps (I against static friction) scores one per jump."""
    out = np.zeros(th.shape[1], int)
    for j in range(th.shape[1]):
        stuck = om[:, j] == 0.0
        for a, b in _runs(stuck, 100):
            if b < len(stuck) - 1:
                e = min(b + 500, len(stuck) - 1)
                if abs(th[e, j] - th[b - 1, j]) >= 0.1:
                    out[j] += 1
    return out


def _hunt(th, om, T):
    """hunting / limit cycle in a window: (th p2p deg, omega reversals with |om| > 0.2 deg/s, T p2p, dominant f Hz)."""
    p2p = th.max(0) - th.min(0)
    sgn = np.sign(np.where(np.abs(om) > 0.2, om, 0.0))
    rev = np.zeros(th.shape[1], int)
    for j in range(th.shape[1]):
        s = sgn[:, j][sgn[:, j] != 0]
        rev[j] = int(np.count_nonzero(np.diff(s) != 0)) if len(s) > 1 else 0
    Tp = T.max(0).astype(float) - T.min(0).astype(float)
    return p2p, rev, Tp


def metrics(name, scn, r, v):
    """per-member metrics (dict of arrays) for one scenario run."""
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    sp = r["sp"].astype(float) / 40.0                         # deg: cmd = 4 * theta_sp counts, 0.1 deg per count
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    m = {}
    m["peakT"] = np.abs(T).max(0)
    m["rail_pct"] = 100.0 * np.mean(np.abs(T) >= RAIL - 6, axis=0)
    m["wraps"] = np.full(th.shape[1], r["wraps"])
    m["diverged"] = (np.abs(th).max(0) > 600) | ~np.isfinite(th).all(0)
    if name in ("rh", "st"):
        if name == "rh":
            holds = scn["holds"]
        else:
            holds = [(scn["t_step"], scn["dur"], scn["step"])]
        ess, ratio, p2p, rev, Tp, ovs = [], [], [], [], [], []
        for (a, b, tgt) in holds:
            w_end = (tt >= b - 0.5) & (tt < b)
            e = (sp[w_end] - th[w_end]).mean(0)
            ess.append(e)
            if tgt != 0:
                w_r = (tt >= b - 1.5) & (tt < b)
                ratio.append((th[w_r] / tgt).mean(0))
                w_h = (tt >= a) & (tt < b)
                ovs.append(np.max((th[w_h] - tgt) * np.sign(tgt), axis=0))
            w_l = (tt >= b - 1.5) & (tt < b)
            p, rv, tp = _hunt(th[w_l], om[w_l], T[w_l])
            p2p.append(p), rev.append(rv), Tp.append(tp)
        ess = np.array(ess)
        m["ess_max"] = np.abs(ess).max(0)
        m["ess_turn"] = np.abs(ess[:-1]).max(0) if name == "rh" else np.abs(ess).max(0)
        m["ess_ctr"] = np.abs(ess[-1]) if name == "rh" else np.zeros(th.shape[1])
        m["hold_ratio"] = np.array(ratio).min(0)
        m["hold_slips"] = np.array([_slips(th[(tt >= a + 0.5) & (tt < b)], om[(tt >= a + 0.5) & (tt < b)])
                                    for (a, b, tgt) in holds]).sum(0)
        m["hunt_p2p"] = np.array(p2p).max(0)
        m["hunt_rev"] = np.array(rev).max(0)
        m["hunt_Tp2p"] = np.array(Tp).max(0)
        m["overshoot"] = np.array(ovs).max(0)
        # 1.6-3 Hz wheel-rate rms over the whole manoeuvre, and the reference's own (control)
        ref_om = np.gradient(sp, axis=0) * 1000.0
        m["hard16"] = np.sqrt(np.mean(_bp(om, 1.6, 3.0)[200:-200] ** 2, axis=0))
        m["hard16_ref"] = np.sqrt(np.mean(_bp(ref_om, 1.6, 3.0)[200:-200] ** 2, axis=0))
        # HF content of T in 5-30 Hz during the holds (a lane-made line would show here)
        hm = np.zeros(n, bool)
        for (a, b, tgt) in holds:
            hm |= (tt >= a + 0.5) & (tt < b)
        Tb = _bp(T, 5.0, 30.0)
        m["T_hf"] = np.sqrt(np.mean(Tb[hm] ** 2, axis=0))
        m["T_hf_f"] = _peak_f(T[hm])
        if name == "st":
            A = scn["step"]
            band = max(0.05 * abs(A), 0.2)
            w = tt >= scn["t_step"]
            bad = np.abs(th[w] - A) > band
            last = np.where(bad.any(0), (len(bad) - 1 - np.argmax(bad[::-1], axis=0)), -1)
            settle = (last + 1) * 1e-3
            m["settle_s"] = np.where(bad[-200:].any(0), np.inf, settle)
            m["overshoot_pct"] = 100.0 * m["overshoot"] / abs(A)
    elif name in ("s02", "s05", "ssm"):
        f = scn["f"]
        amp = scn["amp"]
        w = tt >= scn["score_from"]
        # 100 Hz frames (the wire): the published gp-0x6a00 and the received setpoint
        wire = r["wire"].astype(float) / 10.0
        nf = wire.shape[0]
        fr_t = (np.arange(nf) * 10 + SLOT4_PHASE) * 1e-3
        fr_sp = sp[(np.arange(nf) * 10 + SLOT4_PHASE).clip(0, n - 1)]
        fw = fr_t >= scn["score_from"]
        X = fr_sp[fw]
        Yw = wire[fw]
        xm = X - X.mean(0)
        m["track_gain"] = (xm * (Yw - Yw.mean(0))).sum(0) / (xm ** 2).sum(0)
        # fitted gain and phase of the continuous angle at f
        s_ = np.sin(2 * np.pi * f * tt[w])[:, None]
        c_ = np.cos(2 * np.pi * f * tt[w])[:, None]
        a = 2 * np.mean(th[w] * s_, 0)
        b = 2 * np.mean(th[w] * c_, 0)
        m["fit_gain"] = np.hypot(a, b) / amp
        m["phase_deg"] = np.degrees(np.arctan2(b, a))
        m["err_rms"] = np.sqrt(np.mean((sp[w] - th[w]) ** 2, 0))
        # dwell-then-jump on the 100 Hz true wheel rate and angle
        om_f = om[(np.arange(nf) * 10 + SLOT4_PHASE).clip(0, n - 1)][fw]
        th_f = th[(np.arange(nf) * 10 + SLOT4_PHASE).clip(0, n - 1)][fw]
        ref_f = X
        ev, jmax, dw_ex, stick = dwell_jump(om_f, th_f, ref_f)
        m["dj_events"] = ev
        m["dj_maxjump"] = jmax
        m["dwell_excess_pm"] = dw_ex
        m["stick_pct"] = stick
        m["T_hf"] = np.sqrt(np.mean(_bp(T, 5.0, 30.0)[w] ** 2, axis=0))
        m["T_hf_f"] = _peak_f(T[w])
    elif name.startswith("ov"):
        trel = scn["t_rel"]
        Ah = 0.5 * A_TURN[v]
        w = tt >= trel
        th_rel = th[int(trel * 1000) - 1]
        m["lurch_peakT"] = np.abs(T[w]).max(0)
        m["lurch_overshoot"] = np.max((th[w] - Ah) * np.sign(Ah), axis=0)          # beyond the setpoint
        m["lurch_swing"] = th[w].max(0) - th[w].min(0)
        m["th_at_release"] = th_rel
        ok = np.abs(th[w] - Ah) <= 0.1 * abs(Ah) + 0.2
        m["return_s"] = np.where(ok.any(0), np.argmax(ok, axis=0) * 1e-3, np.inf)
    elif name.startswith("sen"):
        tf = scn["t_fault"]
        w = tt >= tf
        i0 = int(tf * 1000) - 1
        sgn = 1.0 if "_L" in name else -1.0
        m["sen_peakT"] = np.abs(T[w]).max(0)
        m["sen_dur_s"] = np.sum(np.abs(T[w]) > 50, axis=0) * 1e-3
        m["sen_excursion"] = np.max((th[w] - th[i0]) * sgn, axis=0)
        m["sen_excursion_abs"] = np.abs(th[w] - th[i0]).max(0)
    elif name.startswith("dis"):
        td = scn["t_dis"]
        w = tt >= td
        i0 = int(td * 1000) - 1
        m["dis_excursion"] = np.abs(th[w] - th[i0]).max(0)
        m["dis_peakT"] = np.abs(T[w]).max(0)
    return m


def dwell_jump(om_f, th_f, ref_f):
    """DWELL-THEN-JUMP on 100 Hz series (B columns), two detectors.

    (a) the brief's form, made reference-relative: a DWELL = the 0.10 s moving mean of |wheel rate| < 0.25 deg/s for
        >= 100 ms (10 frames) WHILE the reference moved >= 0.1 deg (one angle LSB) over the dwell (so a smooth
        sinusoid's own turning-point pause is not a dwell); the SNAP = the wheel's angle change from the dwell's end to
        the start of the next dwell (at most 0.5 s), the record's snap; EVENT if the snap >= max(2 x the reference's
        change over the same interval, 0.2 deg = 2 LSB), i.e. the wheel CAUGHT UP rather than moved with the reference.
    (b) the RECORD's detector (rlog-tools/studies/grind/v293_symptom_instruments.dwells: 0.10 s moving mean of |rate|
        < 0.25 deg/s for >= 0.20 s), counted on the wheel AND on the reference; reported as the EXCESS per minute.
    stick_pct = % of frames with the wheel exactly stuck (omega == 0) while the reference moves > 0.5 deg/s."""
    B = om_f.shape[1]
    ker = np.ones(10) / 10.0
    ref_om = np.gradient(ref_f, axis=0) * 100.0
    ev = np.zeros(B, int)
    jmax = np.zeros(B)
    dw_ex = np.zeros(B)
    stick = np.zeros(B)
    nmin = om_f.shape[0] / 6000.0
    rs_ref = np.convolve(np.abs(ref_om[:, 0]), ker, "same")
    n_ref = len(_runs(rs_ref < 0.25, 20))
    for j in range(B):
        rs = np.convolve(np.abs(om_f[:, j]), ker, "same")
        th, rf = th_f[:, j], ref_f[:, j]
        cnt, jm = 0, 0.0
        runs = _runs(rs < 0.25, 10)
        for q, (a, b) in enumerate(runs):
            if b + 2 >= len(th):
                continue
            if abs(rf[b - 1] - rf[a]) < 0.1:
                continue
            e = runs[q + 1][0] if q + 1 < len(runs) else len(th) - 1
            e = min(e, b + 50, len(th) - 1)
            jump = abs(th[e] - th[b])
            if jump >= max(2.0 * abs(rf[e] - rf[b]), 0.2):
                cnt += 1
                jm = max(jm, jump)
        ev[j], jmax[j] = cnt, jm
        dw_ex[j] = (len(_runs(rs < 0.25, 20)) - n_ref) / max(nmin, 1e-9)
        moving = np.abs(ref_om[:, j]) > 0.5
        stick[j] = 100.0 * np.mean((om_f[:, j] == 0.0) & moving) / max(np.mean(moving), 1e-9)
    return ev, jmax, dw_ex, stick


def _runs(mask, minlen):
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= minlen:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


# ======================================================================================================================
# the record's 20 Hz comparator: |(P + D) / x| at 20 Hz (V295 3.85, V294 2.08, V282 44.90)
# ======================================================================================================================
def hf20(kp, kd=0):
    """lane P (+ D) per x count at 20 Hz, x = 8 counts per deg/s of wheel rate (the record's |P/x| form, which does
    NOT include the 100 Hz hold, the fade or the output stage -- those are common to every build compared).
    angle loop: P = Kp * (8*th[n] + 8*th[n-1]) / 256 with th in 0.1 deg counts = 10*omega/(j*W); D = -Kd*x/8."""
    W = 2 * np.pi * 20.0
    z1 = np.exp(-1j * W * 1e-3)
    Pp = (kp / 256.0) * 8.0 * abs(1 + z1) * 10.0 / W / 8.0          # per x count (x = 8*omega)
    Dd = kd / 8.0
    return float(np.hypot(Pp, Dd))


def hf20_v295():
    W = 2 * np.pi * 20.0
    z = np.exp(1j * W * 1e-3)
    a, b = 1011 / 1024.0, 1050 / 1024.0
    r = b * (1 - 1 / z) / (1 - a / z)
    return float(abs(r) * 960 / 256.0)


# ======================================================================================================================
# selftest: LaneVec == the scalar byte-exact mirror (lane_mirror_v295.lane_tick), every branch
# ======================================================================================================================
def selftest(n_cfg=12, n_ticks=12000, seed=5):
    t0 = time.time()
    cal = base_cal()
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_cfg):
        kpY = tuple(int(v) for v in rng.integers(0, 12000, 5)) if i % 3 else (int(rng.integers(100, 9000)),) * 5
        kpX = tuple(sorted(int(v) for v in rng.integers(0, 241, 5))) if i % 2 else (0, 68, 112, 136, 208)
        r = row(0, Ki=int(rng.choice([0, 37, 256, 1024, 4096, 65535])), ICL=int(rng.choice([0, 1024, 4096, 10240, 65535])),
                DB=int(rng.choice([0, 1, 4, 9])), Kd=int(rng.choice([0, 8, 16, 32, 300])), e6=bool(i % 2),
                kpX=kpX, kpY=kpY, oa=int(rng.choice([992, 960, 900])), ob=int(rng.choice([507, 1000, 1500])))
        rows.append(r)
    cfg = Cfg(rows)
    lane = LaneVec(cal, cfg)
    sts = [LM.LaneState() for _ in range(n_cfg)]
    cals = []
    eds = []
    for r in rows:
        c = dict(cal, kp=(r["kpX"], r["kpY"]), Ki=r["Ki"], ICL=r["ICL"], DB=r["DB"], kd=(r["kdX"], r["kdY"]),
                 DCL=r["DCL"], oa=r["oa"], ob=r["ob"])
        cals.append(c)
        eds.append(LM.Edits(x_src="angle", fb_op="sum", sp_src="69ae", d_src="rate" if r["d_rate"] else "E",
                            i_reset_on_ramp0=r["e6"]))
    ang, rate, tq = 0, 0, 0
    raw = 0
    ramp, act, req = 0x8000, 1, 1
    mism = 0
    fields = ("r26", "E", "I", "P", "D", "Sc", "y", "yr")
    branch = dict(skip=0, invalid=0, sentinel=0, gate_block=0, fade=0, rail=0)
    for t in range(n_ticks):
        ang = int(np.clip(ang + rng.integers(-60, 61), -13000, 13000))
        if t % 997 == 0:
            ang = int(rng.choice([ang, 12500, -12500, 0]))
        rate = int(np.clip(rate + rng.integers(-50, 51), -3000, 3000))
        if t % 10 == 0:
            raw = int(rng.integers(-4500, 4500))
        cmd = LM.e4_handler(None if (t // 700) % 9 == 4 else raw)
        tq = int(np.clip(tq + rng.integers(-150, 151), -4500, 4500))
        i6830 = int(rng.integers(0, 25)) if t % 50 == 0 else 0
        spd = int(rng.integers(0, 9000))
        ph = (t // 400) % 6
        if ph == 0:
            ramp, act, req = 0x8000, 1, 1
        elif ph == 1:
            ramp, act, req = max(0, ramp - 16), 0, 0
        elif ph == 2:
            ramp, act, req = max(0, ramp - 328), 0, 1
        elif ph == 3:
            ramp, act, req = min(0x8000, ramp + 33), 1, 1
        elif ph == 4:
            ramp, act, req = 0, 0, int(rng.choice([0, 1, 0xFF]))
        else:
            ramp, act, req = int(rng.integers(0, 0x8001)), int(rng.integers(0, 2)), 1
        if t % 2:      # odd ticks: array inputs -> the VECTOR setpoint/fade path; even ticks: the scalar path
            Tv = lane.tick(ang, rate, np.full(n_cfg, cmd), np.full(n_cfg, tq), np.full(n_cfg, i6830),
                           np.full(n_cfg, spd), ramp, act, req, pol=-1)
        else:
            Tv = lane.tick(ang, rate, cmd, tq, i6830, spd, ramp, act, req, pol=-1)
        for j in range(n_cfg):
            Ts = LM.lane_tick(sts[j], cals[j], eds[j], rate=rate, angle=ang, cmd69ae=cmd, tq=tq, i6830=i6830,
                              speed=spd, ramp=ramp, act6806=act, req6805=req, pol=-1)
            lg = sts[j].log
            bad = int(Ts) != int(Tv[j])
            for k in fields:
                a = lg.get(k)
                a = 0 if a is None else a
                if int(a) != int(lane.log[k][j]):
                    bad = True
            if bad:
                mism += 1
                if mism < 5:
                    print("  MISMATCH tick", t, "cfg", j, {k: (sts[j].log.get(k), int(lane.log[k][j])) for k in fields},
                          "T", Ts, int(Tv[j]))
            branch["skip"] += int(lg["E"] is None)
            branch["invalid"] += int(abs(ang) > 12000)
            branch["sentinel"] += int(cmd == LM.SENTINEL)
            branch["gate_block"] += int(act == 0 and lg.get("yr", 1) == 0 and lg.get("y", 0) != 0)
            branch["fade"] += int(lg.get("f", 254) not in (254, None) and lg["E"] is not None)
            branch["rail"] += int(abs(Ts) >= RAIL - 6)
    total = n_cfg * n_ticks
    print("SELFTEST 1  LaneVec vs lane_mirror_v295.lane_tick (angle edits, pol -1): %d mismatching ticks of %d  %s"
          "   [branch coverage %s]  (%.0f s)" % (mism, total, "PASS" if mism == 0 else "FAIL", branch, time.time() - t0))
    ok = mism == 0
    # 2. the lane alone at rest: E == 16*(theta_sp - theta) and the DC torque per deg (T ~= 0.1*Kp per deg)
    cfg = Cfg([row(1000, Ki=0)])
    lane = LaneVec(cal, cfg)
    for _ in range(3000):
        T = lane.tick(0, 0, 4 * 10, 0, 0, 5000, 0x8000, 1, 1)
    print("SELFTEST 2  Kp 1000, error 1.0 deg, hands off: E = %d (want 160), T = %d (record: ~100 per deg)"
          % (int(lane.log["E"][0]), int(T[0])))
    ok &= int(lane.log["E"][0]) == 160 and 95 <= abs(int(T[0])) <= 105
    # 3. plant: Karnopp hold below Fs, slides above
    mem = VP.constant_member(VP.PlantParams(J=0.2, b=2.0, k=20.0, Fc=30.0, Fs=40.0, tau_ms=0))
    p = PlantVec(mem, 10.0, 2)
    for _ in range(500):
        p.step(np.array([39.0, 41.0]))
    print("SELFTEST 3  plant: |u| 39 < Fs 40 -> th %.4f (want 0); |u| 41 -> th %.4f (want > 0)" % (p.th[0], p.th[1]))
    ok &= p.th[0] == 0.0 and p.th[1] > 0
    # 4. plant: linear step static gain and damped frequency (rigid, friction off)
    mem = VP.constant_member(VP.PlantParams(J=0.2, b=0.2, k=20.0, Fc=0.0, Fs=0.0, tau_ms=0))
    p = PlantVec(mem, 10.0, 1)
    ths = []
    for _ in range(20000):
        p.step(np.array([100.0]))
        ths.append(p.th[0])
    ths = np.array(ths)
    zc = np.flatnonzero(np.diff(np.sign(ths[:4000] - 5.0)) != 0)
    fd = 1000.0 / (2 * np.mean(np.diff(zc)))
    fth = math.sqrt(100) / (2 * math.pi) * math.sqrt(1 - (0.2 / (2 * math.sqrt(4.0))) ** 2)
    print("SELFTEST 4  plant: static th %.3f (want 5.000), damped f %.3f Hz (want %.3f)" % (ths[-1], fd, fth))
    ok &= abs(ths[-1] - 5) < 0.02 and abs(fd - fth) < 0.03
    # 5. the 20 Hz comparator reproduces the record's V295 3.85
    print("SELFTEST 5  |P/x| at 20 Hz: V295 recomputed %.2f (record 3.85); angle loop Kp 6000 -> %.2f, Kd 16 -> %.2f"
          % (hf20_v295(), hf20(6000), hf20(0, 16)))
    ok &= abs(hf20_v295() - 3.85) < 0.01
    # 6. the speed-keyed LERP key (candidate edit; not in lane_mirror_v295): Kp == LERP(kp, gp-0x6a5e >> 8)
    r = row(0, kpX=(2, 4, 11, 17, 23), kpY=(1500, 1200, 1800, 1500, 2500), kdX=(2, 4, 7, 11), kdY=(28, 24, 24, 0),
            key="speed", Ki=0)
    bad = 0
    for v in np.arange(0.0, 40.0, 0.37):
        lane = LaneVec(cal, Cfg([r]))
        spd = int(round(v * 3.6 * 64))
        lane.tick(0, 0, 40, 0, 0, spd, 0x8000, 1, 1)
        bad += int(lane.log["kp"][0]) != (LM.lerp(r["kpX"], r["kpY"], spd >> 8) & 0xFFFF)
    print("SELFTEST 6  speed-keyed Kp == LERP(kp, speed>>8) over 0-40 m/s: %d mismatches  %s" % (bad, "PASS" if bad == 0 else "FAIL"))
    ok &= bad == 0
    print("SELFTEST", "PASS" if ok else "FAIL")
    return ok


# ======================================================================================================================
# sweep machinery (multiprocessing over (speed, scenario) jobs)
# ======================================================================================================================
KP_SWEEP = (500, 900, 1500, 2500, 4000, 6000)
KI_SWEEP = (256, 1024)                # "small", "medium"
ICL_SWEEP = (1024, 4096, 10240)
DB_SWEEP = (0, 1, 4)
KD_SWEEP = (0, 8, 16, 32)


def flat_rows():
    rows = []
    for kp in KP_SWEEP:
        for kd in KD_SWEEP:
            rows.append(row(kp, Ki=0, Kd=kd))
            for ki in KI_SWEEP:
                for icl in ICL_SWEEP:
                    for db in DB_SWEEP:
                        rows.append(row(kp, Ki=ki, ICL=icl, DB=db, Kd=kd))
    return rows


def _job(args):
    name, v, rows, member_name, outer, extra = args[:6]
    opts = args[6] if len(args) > 6 else {}
    fam = VP.family()
    if member_name.startswith("nominal+mode"):
        f2 = float(member_name.split("mode")[1].split("Hz")[0])
        member = fam["nominal"].with_mode20(f2=f2, zeta2=0.1 if f2 < 15 else 0.05, r2=0.2)
    else:
        member = fam[member_name]
    scn = scenario(name, v)
    cfg = Cfg(rows)
    t0 = time.time()
    r = run(scn, cfg, member, v, outer=outer, **opts)
    m = metrics(name, scn, r, v)
    m = {k: np.asarray(val).tolist() for k, val in m.items()}
    return dict(name=name, v=v, member=member_name, outer=outer, metrics=m, sec=time.time() - t0, extra=extra,
                opts=json.dumps(opts, sort_keys=True))


def run_jobs(jobs, procs=None, tag=""):
    import multiprocessing as mp
    procs = procs or min(9, os.cpu_count() or 4)
    t0 = time.time()
    out = []
    with mp.Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(_job, jobs)):
            out.append(res)
            if (i + 1) % 10 == 0 or i + 1 == len(jobs):
                print("  %s %d/%d jobs done, %.0f s" % (tag, i + 1, len(jobs), time.time() - t0), flush=True)
    return out


def save(obj, fn):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / fn, "w") as f:
        json.dump(obj, f)


def load(fn):
    with open(OUT / fn) as f:
        return json.load(f)


def chunks(rows, n=160):
    return [rows[i:i + n] for i in range(0, len(rows), n)]


def merge(res):
    """merge chunked job results back to one metrics dict per (name, v, member, outer), in chunk order."""
    out = {}
    for r in sorted(res, key=lambda r: (r["name"], r["v"], r["member"], r["outer"], r.get("opts", "{}"), r["extra"] or 0)):
        key = (r["name"], r["v"], r["member"], r["outer"], r.get("opts", "{}"))
        if key not in out:
            out[key] = dict(r, metrics={k: list(v) for k, v in r["metrics"].items()})
        else:
            for k, v in r["metrics"].items():
                out[key]["metrics"][k].extend(v)
    return list(out.values())


def refined_rows():
    """a refinement around what the brief's grid found (run 2026-09-30 after the first sweep): a LOW-SPEED grid with
    D between 16 and 32 (the 20 Hz comparator caps Kd at ~30 with Kp 1500), a HIGH-SPEED grid around Kp 2500 / Ki 1024,
    and a DIAGNOSTIC output-lag pole (10 / 20 Hz, DC held at 0.990) -- a STRUCK lever in the record (BUILD-LINEAGE V287:
    'output-lag pole 0xC63EC/EE at >= 10 Hz ... fires Honda's oscillation detector'), run only to show what binds."""
    rows = []
    for kp in (1200, 1500, 2000):
        for kd in (20, 24, 28):
            rows.append(row(kp, Ki=0, Kd=kd))
            for ki in (256, 1024):
                for icl in (1024, 4096):
                    for db in (0, 1):
                        rows.append(row(kp, Ki=ki, ICL=icl, DB=db, Kd=kd))
    for kp in (1800, 2000, 2500, 3000):
        for ki in (512, 1024, 2048):
            for icl in (1024, 4096):
                for kd in (0, 8, 16):
                    if kp == 2500 and ki == 1024:
                        continue
                    rows.append(row(kp, Ki=ki, ICL=icl, DB=0, Kd=kd))
    for oa, ob in ((962, 982), (903, 1917)):
        for kp in (1500, 2500, 4000):
            for kd in (0, 16):
                rows.append(row(kp, Ki=256, ICL=4096, DB=0, Kd=kd, oa=oa, ob=ob))
    return rows


def do_refined():
    rows = refined_rows()
    jobs = [(nm, v, ch, "nominal", "ff", ci) for v in SPEEDS for nm in SCENARIOS for ci, ch in enumerate(chunks(rows))]
    print("REFINED SWEEP: %d configs x %d speeds x %d scenarios" % (len(rows), len(SPEEDS), len(SCENARIOS)), flush=True)
    res = merge(run_jobs(jobs, tag="refined"))
    save(dict(rows=rows, results=res), "refined_sweep.json")
    return rows, res


def do_sweep():
    rows = flat_rows()
    jobs = [(nm, v, ch, "nominal", "ff", ci) for v in SPEEDS for nm in SCENARIOS for ci, ch in enumerate(chunks(rows))]
    print("FLAT SWEEP: %d configs x %d speeds x %d scenarios" % (len(rows), len(SPEEDS), len(SCENARIOS)), flush=True)
    res = merge(run_jobs(jobs, tag="flat"))
    save(dict(rows=rows, results=res), "flat_sweep.json")
    return rows, res


# ======================================================================================================================
# scoring against THE GOAL
# ======================================================================================================================
def table(res, rows):
    """{(scenario, v): {metric: np.array over configs}}"""
    T = {}
    for r in res:
        T[(r["name"], float(r["v"]))] = {k: np.array(v, float) for k, v in r["metrics"].items()}
    return T


def per_speed_score(T, v, kp_vals, kd_vals, strict=True):
    """per-config gates at speed v.  strict=True also gates TEXTURE (T in 5-30 Hz during the sinusoids <= HF_LINE);
    strict=False gates only LINES (limit cycles in the holds).  Returns (gates dict, allpass, cost)."""
    rh, st = T[("rh", v)], T[("st", v)]
    s02, s05, ssm = T[("s02", v)], T[("s05", v)], T[("ssm", v)]
    div = rh["diverged"].astype(bool) | st["diverged"].astype(bool) | s02["diverged"].astype(bool) \
        | s05["diverged"].astype(bool) | ssm["diverged"].astype(bool)
    hunt = (np.maximum(rh["hunt_p2p"], st["hunt_p2p"]) >= 0.2) & (np.maximum(rh["hunt_rev"], st["hunt_rev"]) >= 2)
    line = np.maximum(rh["T_hf"], st["T_hf"]) > HF_LINE
    texture = np.maximum.reduce([s02["T_hf"], s05["T_hf"], ssm["T_hf"]]) <= HF_LINE
    stable = ~div & ~hunt & ~line
    dj = s02["dj_events"] + s05["dj_events"] + ssm["dj_events"] + rh["hold_slips"] + st["hold_slips"]
    stick_ok = dj <= 0
    dz_ok = (rh["ess_turn"] <= max(0.3, 0.03 * A_TURN[v])) & (ssm["fit_gain"] >= 0.8)
    tg = np.minimum(s02["track_gain"], s05["track_gain"])
    tg_hi = np.maximum(s02["track_gain"], s05["track_gain"])
    track_ok = (tg >= 0.95) & (tg_hi <= 1.05)
    hold_ok = rh["hold_ratio"] >= 0.90
    hf20_ok = np.array([hf20(kp, kd) <= V295_HF20 for kp, kd in zip(kp_vals, kd_vals)])
    need_track = v >= 8.0
    gates = dict(stable=stable, texture=texture | (not strict), stick=stick_ok, deadzone=dz_ok,
                 track=track_ok | (not need_track), hold=hold_ok | (not need_track), hf20=hf20_ok)
    allpass = np.logical_and.reduce(list(gates.values()))
    cost = (np.abs(1 - tg) * 10 + np.abs(1 - tg_hi) * 5 + np.abs(1 - rh["hold_ratio"]) * 5
            + rh["ess_turn"] / max(A_TURN[v], 1) * 10 + np.minimum(dj, 20) * 0.5 + (~stable) * 100 + (~hf20_ok) * 50
            + np.clip(st["overshoot_pct"], 0, 100) / 50 + np.maximum.reduce([s02["T_hf"], s05["T_hf"], ssm["T_hf"]]) * 0.2
            + np.abs(1 - ssm["fit_gain"]) * 2)
    return gates, allpass, cost


# ======================================================================================================================
# selection: FLAT, IDEAL speed schedule (Kp(v) by cave), ANGLE-INDEXED (cal-only, Kp keyed by |theta_sp|)
# ======================================================================================================================
GATES = ("stable", "texture", "stick", "deadzone", "track", "hold", "hf20")


def flat_scores(rows, res, strict=True):
    T = table(res, rows)
    kp = np.array([max(r["kpY"]) for r in rows])
    kd = np.array([r["kdY"][0] if r["d_rate"] else 0 for r in rows])
    out = {}
    for v in SPEEDS:
        gates, allpass, cost = per_speed_score(T, v, kp, kd, strict=strict)
        out[v] = dict(gates=gates, allpass=allpass, cost=cost)
    return T, out


def combo_key(r):
    return (r["Ki"], r["ICL"] if r["Ki"] else 0, r["DB"] if r["Ki"] else 0, r["kdY"][0] if r["d_rate"] else 0)


def select(rows, res, strict=True):
    """returns dict with the best FLAT config, the best IDEAL Kp(v) schedule, and per-speed feasibility."""
    T, sc = flat_scores(rows, res, strict=strict)
    n = len(rows)
    npass = np.zeros(n, int)
    csum = np.zeros(n)
    for v in SPEEDS:
        npass += sc[v]["allpass"].astype(int)
        csum += np.minimum(sc[v]["cost"], 200)
    order = np.lexsort((csum, -npass))
    flat_best = int(order[0])
    flat_top = [int(i) for i in order[:8]]
    # IDEAL speed schedule: same (Ki, ICL, DB, Kd), Kp chosen per speed
    combos = {}
    for i, r in enumerate(rows):
        combos.setdefault(combo_key(r), []).append(i)
    ideal = []
    for ck, idxs in combos.items():
        pick, np_, cs = {}, 0, 0.0
        for v in SPEEDS:
            best = min(idxs, key=lambda i: (not sc[v]["allpass"][i], sc[v]["cost"][i]))
            pick[v] = best
            np_ += int(sc[v]["allpass"][best])
            cs += min(sc[v]["cost"][best], 200)
        ideal.append((np_, -cs, ck, pick))
    ideal.sort(key=lambda t: (t[0], t[1]), reverse=True)
    # per-speed feasibility: does ANY config pass every gate at that speed?  and which gate is the binding one
    feas = {}
    for v in SPEEDS:
        g = sc[v]["gates"]
        feas[v] = dict(n_all=int(sc[v]["allpass"].sum()),
                       n_gate={k: int(np.sum(g[k])) for k in GATES},
                       best=int(np.argmin(np.where(sc[v]["allpass"], sc[v]["cost"], 1e9 + sc[v]["cost"]))))
    return dict(T=T, sc=sc, flat_best=flat_best, flat_top=flat_top, npass=npass, csum=csum, ideal=ideal, feas=feas)


def idx_of_deg(deg):
    """the Kp-schedule key for a setpoint of `deg` (hands off): idx = |4*10*deg| * 65025 >> 22 (16.1257 counts/step)."""
    cmd = int(np.clip(4 * int(round(10 * deg)), -16384, 16384))
    return LM.setpoint_chain(cmd, base_cal())[0]


# ======================================================================================================================
# THE FINAL CANDIDATES (chosen from flat_sweep.json + refined_sweep.json; see the report for how)
# ======================================================================================================================
def kmh_key(v):
    """the speed key of a speed-keyed LERP: gp-0x6a5e >> 8 = 4 km/h per count (ld.bu of the high byte)."""
    return int(round(v * 3.6 * 64)) >> 8


def final_candidates():
    """explicit candidates, one or two per schedule type.  Labels are the report's names."""
    I = dict(Ki=1024, ICL=4096, DB=0)
    c = []
    # FLAT: one Kp/Kd for every speed (cal-only)
    c.append(row(2500, Kd=16, label="FLAT-T  Kp2500 Ki1024 ICL4096 DB0 Kd16 (best flat, line-only reading)", **I))
    c.append(row(500, Ki=256, ICL=10240, DB=0, Kd=16, label="FLAT-S  Kp500 Ki256 ICL10240 DB0 Kd16 (best flat, strict reading)"))
    c.append(row(1200, Ki=1024, ICL=4096, DB=1, Kd=24, label="FLAT-L  Kp1200 Ki1024 ICL4096 DB1 Kd24 (the 3 m/s winner, flown flat)"))
    # ANGLE-INDEXED (cal-only): Kp on idx = |theta_sp| / 1.6126 deg; Kd flat 24 (edit 5)
    X = (0, idx_of_deg(5.0), idx_of_deg(12.0), idx_of_deg(30.0), idx_of_deg(50.0))
    c.append(row(0, kpX=X, kpY=(2500, 1500, 1800, 1200, 1200), Kd=24,
                 label="ANGLE-1 Kp(|th_sp|) 2500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24", **I))
    c.append(row(0, kpX=X, kpY=(1500, 1500, 1800, 1200, 1200), Kd=24,
                 label="ANGLE-2 Kp(|th_sp|) 1500/1500/1800/1200/1200 @ 0/5/12/30/50 deg, Kd24", **I))
    c.append(row(0, kpX=X, kpY=(2500, 1500, 1800, 1200, 1200), Kd=28,
                 label="ANGLE-3 = ANGLE-1 with Kd28", **I))
    # SPEED-KEYED (Kp and Kd on gp-0x6a5e >> 8): the IDEAL Kp(v)/Kd(v) a speed schedule gives, common Ki/ICL/DB
    kx = (kmh_key(3.0), kmh_key(5.0), kmh_key(12.5), kmh_key(19.0), kmh_key(26.0))
    dx = (kmh_key(3.0), kmh_key(5.0), kmh_key(8.0), kmh_key(12.5))
    c.append(row(0, kpX=kx, kpY=(1500, 1200, 1800, 1500, 2500), kdX=dx, kdY=(28, 24, 24, 0), key="speed",
                 label="SPEED-1 Kp(v) 1500/1200/1800/1500/2500 @ 3/5/12.5/19/26 m/s, Kd(v) 28/24/24/0 @ 3/5/8/12.5", **I))
    c.append(row(0, kpX=kx, kpY=(1500, 1200, 1800, 1500, 2500), kdX=dx, kdY=(28, 24, 24, 0), key="speed",
                 Ki=640, ICL=4096, DB=0, label="SPEED-2 = SPEED-1 with Ki 640"))
    return c


def do_final():
    cands = final_candidates()
    jobs = [(nm, v, cands, "nominal", "ff", 0) for v in SPEEDS for nm in SCENARIOS]
    res = merge(run_jobs(jobs, tag="final"))
    save(dict(rows=cands, results=res), "final.json")
    members = ("J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_lo", "F_hi", "tau0", "tau6", "light_b", "ms_free",
               "nominal+mode13Hz", "nominal+mode20Hz")
    jobs = [(nm, v, cands, mem, "ff", 0) for mem in members for v in SPEEDS for nm in SC_TRACK]
    res_rob = merge(run_jobs(jobs, tag="robust"))
    jobs = [(nm, v, cands, "nominal", "pi", 0) for v in SPEEDS for nm in SC_TRACK]
    res_pi = merge(run_jobs(jobs, tag="outer-pi"))
    save(dict(rows=cands, members=members, results=res_rob, results_pi=res_pi), "final_robust.json")


def do_payoff():
    """WHAT A CAVE BUYS: the same candidates with a finer angle (x4, x8) and/or a fresh 1 kHz operand."""
    cands = [r for r in final_candidates() if r["label"].split()[0] in ("FLAT-T", "ANGLE-1", "SPEED-1")]
    variants = ({"ang_mult": 4}, {"ang_mult": 8}, {"fresh": True}, {"ang_mult": 8, "fresh": True})
    jobs = [(nm, v, cands, "nominal", "ff", 0, op) for op in variants for v in SPEEDS for nm in SC_TRACK]
    res = merge(run_jobs(jobs, tag="payoff"))
    save(dict(rows=cands, variants=[json.dumps(o, sort_keys=True) for o in variants], results=res), "payoff.json")


def do_payoff2():
    """the SETPOINT side of the texture: finer setpoint units and/or 1 kHz setpoint interpolation (cave/interface options)."""
    cands = [r for r in final_candidates() if r["label"].split()[0] in ("FLAT-T", "ANGLE-1", "SPEED-1")]
    variants = ({"sp_fine": True}, {"sp_interp": True}, {"sp_fine": True, "sp_interp": True},
                {"sp_fine": True, "sp_interp": True, "ang_mult": 8, "fresh": True})
    jobs = [(nm, v, cands, "nominal", "ff", 0, op) for op in variants for v in SPEEDS for nm in SC_TRACK]
    res = merge(run_jobs(jobs, tag="payoff2"))
    save(dict(rows=cands, variants=[json.dumps(o, sort_keys=True) for o in variants], results=res), "payoff2.json")


def do_robust_cave():
    """robustness of the FULL-RESOLUTION cave option (setpoint 0.025 deg + 1 kHz interpolation + angle x8 + fresh 1 kHz
    operands) across the plant family, for the same candidates -- does a fresh operand buy margin?"""
    cands = [r for r in final_candidates() if r["label"].split()[0] in ("FLAT-T", "ANGLE-1", "SPEED-1")]
    op = {"sp_fine": True, "sp_interp": True, "ang_mult": 8, "fresh": True}
    members = ("J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_lo", "F_hi", "tau0", "tau6", "light_b", "ms_free",
               "nominal+mode13Hz", "nominal+mode20Hz")
    jobs = [(nm, v, cands, mem, "ff", 0, op) for mem in members for v in SPEEDS for nm in SC_TRACK]
    res = merge(run_jobs(jobs, tag="robust-cave"))
    save(dict(rows=cands, members=members, opts=json.dumps(op, sort_keys=True), results=res), "robust_cave.json")


def do_guard_a2():
    """Fix A2 of TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates (0x29A56 bne -> be: the PID runs iff
    ramp != 0 AND request == 1), simulated on the safety scenarios against the stock guard."""
    base = [r for r in final_candidates() if r["label"].split()[0] in ("FLAT-T", "ANGLE-1", "SPEED-1")]
    rows = [dict(r, label=r["label"].split()[0] + " stock-guard") for r in base] +            [dict(r, guard_and=True, label=r["label"].split()[0] + " guard-A2") for r in base]
    names = ("ov_fade", "ov_latch", "sen_L16", "sen_L328", "sen_R16", "dis_meas", "dis_zero")
    jobs = [(nm, v, rows, "nominal", "ff", 0) for v in SPEEDS for nm in names]
    res = merge(run_jobs(jobs, tag="guard-A2"))
    save(dict(rows=rows, results=res), "guard_a2.json")


# ======================================================================================================================
# main
# ======================================================================================================================
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--payoff", action="store_true")
    ap.add_argument("--payoff2", action="store_true")
    ap.add_argument("--robust-cave", dest="robust_cave", action="store_true")
    ap.add_argument("--guard-a2", dest="guard_a2", action="store_true")
    ap.add_argument("--refined", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    if a.selftest or a.all:
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            selftest()
        print(buf.getvalue(), end="")
        OUT.mkdir(parents=True, exist_ok=True)
        lines = [ln for ln in buf.getvalue().splitlines() if ln.startswith("SELFTEST")]
        (OUT / "selftest_out.txt").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    if a.quick:
        cal = base_cal()
        fam = VP.family()
        cfg = Cfg([row(900), row(2500, Ki=256, ICL=4096, DB=1), row(6000, Ki=1024, ICL=4096, DB=0, Kd=16)])
        for v in (3.0, 26.0):
            for nm in ("rh", "s02", "st"):
                scn = scenario(nm, v)
                t0 = time.time()
                r = run(scn, cfg, fam["nominal"], v)
                m = metrics(nm, scn, r, v)
                print(v, nm, "%.1fs" % (time.time() - t0), {k: np.round(np.asarray(val, float), 3).tolist()
                                                           for k, val in m.items()})
    if a.sweep or a.all:
        do_sweep()
    if a.refined or a.all:
        do_refined()
    if a.final or a.all:
        do_final()
    if a.payoff or a.all:
        do_payoff()
    if a.payoff2 or a.all:
        do_payoff2()
    if a.robust_cave or a.all:
        do_robust_cave()
    if a.guard_a2 or a.all:
        do_guard_a2()
    if a.report or a.all:
        import harness_time_report as R
        R.write_report()
