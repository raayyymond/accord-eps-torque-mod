# -*- coding: utf-8 -*-
r"""s4_closed_loop.py -- D5-architect (V299 design round).  CLOSED-LOOP time-domain scoring of V298 vs V299-(b) vs
V299-(a), firmware lane + FORK model together, on the panel-2 COMMON engine (panel2/score_time.py: CandLane = the
byte-exact lane arithmetic H1-validated against the V298-class cave bytes; the Karnopp plant family; the 100 Hz held
angle; the 1 kHz gp-0x6abe EMA), imported unchanged.  What THIS script adds (each line marked):
  * a FORK MODEL at 100 Hz (the operator's fork _update_angle, re-implemented): the 20 Hz model staircase (plan ZOH
    50 ms), carState i-1 (the angle two 0x14A frames old), the rate cap (deg/frame), the error clip ANGLE_ERROR_MAX(v),
    O1 (V298: on > 600 raw / off <= 500; V299: on > 1200 raw OR > 600 raw for >= 6 frames / off <= 500), and for
    (b) the LEAD tau_L(v) w_f (5-frame boxcar slope + 30 ms pole) and the BREAKAWAY KICK delta_f(v) sgn exp(-t/0.3 s);
  * a lane subclass for (a): washout D (D on abe - abe_lp, abe_lp = EMA 1/256, reset to abe on the first-tick
    sentinel) and the friction comp clamp((E' Kf) >> 8, +-Lf) added to S beside P (both memoryless except abe_lp);
  * a plant member 'r79F' = nominal with Coulomb friction set to route 79's single-method estimate (156 T <= 5 m/s,
    85 T above; Fs = 1.25 Fc) -- BELIEF (instrument, single method); 'nominal' is the identified family.
SCENARIOS: slew (300 deg/s planned trapezoid, hold 2 s, return), drift (1.5 deg/s, the small-correction stick),
n1 (opposing hand 400 / 700 / 1000 gp, 1 s, release), hold (road noise 15 T rms, 20 s: limit cycles), sin (+-1 deg
0.2 Hz: small-correction tracking).  ANALYSIS ONLY.  Each scenario runs in its own process (spawn).  Wall printed.
usage: python s4_closed_loop.py [procs]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
for _q in (AL / "panel", AL / "c1", AL / "c3" / "rev2B", AL / "refute_c2r2_nonlinear", AL):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
_st = importlib.util.spec_from_file_location("p2_st_d5", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_st)
sys.modules["p2_st_d5"] = ST
_st.loader.exec_module(ST)
import rb_table as RT  # noqa: E402

NS = ST.NS
s16, s32, lerp_vec = ST.s16, ST.s32, ST.lerp_vec
OUT = KIT / "_scratch" / "out" / "v299_D5"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------------------------------------------------
# plant member r79F (BELIEF: route 79's single-method Coulomb estimate)
# ---------------------------------------------------------------------------------------------------------------------
_params0 = NS.params


def _params(member, v):
    if member == "r79F":
        J, b, k, sat, Fc, Fs, tau = _params0("nominal", v)
        Fc = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
        return J, b, k, sat, Fc, 1.25 * Fc, tau
    return _params0(member, v)


NS.params = _params
ST.Plant._cache = {}

# ---------------------------------------------------------------------------------------------------------------------
# candidates (firmware side)
# ---------------------------------------------------------------------------------------------------------------------
GBP = tuple(tuple(r) for r in RT.GB_P)
ARB_V299 = (6, 4, 2880, 1250, 0, 4096)          # A3 kept; the low-speed 4096 cap only at standstill (vcap 1382 -> 0)
FW = {
    "V298": ST.Cand("V298", "D5", GBP, "fresh", 48, ki=40, icl=8192, thr=512, sgn_thr=300, arb=ST.ARB_A3,
                    ramp_in=328, ramp_out=66),
    # FINAL (after s4b_slew_attrib): the A3 low-speed 4096 cap is KEPT (removing it caused the +10 % turn-in
    # overshoot at 3 m/s); the only firmware rule change of (b) is the freeze: hard 512 -> 1229, opposing 300 -> off
    "V299b": ST.Cand("V299b", "D5", GBP, "fresh", 48, ki=40, icl=8192, thr=1229, sgn_thr=0, arb=ST.ARB_A3,
                     ramp_in=328, ramp_out=66),
    "V299a": ST.Cand("V299a", "D5", GBP, "fresh", 48, ki=40, icl=8192, thr=1229, sgn_thr=0, arb=ST.ARB_A3,
                     ramp_in=328, ramp_out=66),
}
A_FEAT = {"V299a": dict(wash=9, kf=28, lf=400)}  # washout EMA shift 9 (tau 512 ms); friction Kf 28 (GATE-2 max, s5b) / Lf 400 S

# fork side
EBP = np.array([3.1, 8.0, 10.0, 11.75, 17.5, 26.9])
EV298 = np.array([17.0, 15.5, 19.5, 17.0, 8.5, 4.5])
EV299 = np.array([35.0, 32.0, 19.5, 17.0, 8.5, 4.5])
GKN = np.array([1178.0, 1465.0, 760.0, 560.0, 1068.0, 2188.0])
TAU_L = 0.5 * 89.5 / GKN                         # s: lead = 0.5 x (D per wheel deg/s) / (P per deg), image arithmetic
#   (0.5 <= the measured D fraction 0.55-0.88 of design, so the lead never exceeds the D it cancels; s4b: 0.7 overshoots)
KT = 0.04375 * GKN                               # T per deg of P (= 0.2734 G S/deg x 0.16 T/S)
FC79 = np.interp(EBP, [5.0, 6.0], [156.0, 85.0])
DELTA_F = np.minimum(0.5 * FC79 / KT, 1.0)       # deg: breakaway kick amplitude (b)
FORK = {
    "V298": dict(cap=1.2, clip=EV298, o1="V298", lead=0.0, kick=0.0),
    # kick OFF in the final (b): s7_kick_rate.py shows the trigger firing 85-260 /min on route 79's real plan noise
    "V299b": dict(cap=2.5, clip=EV299, o1="deb60", lead=1.0, kick=0.0),
    "V299a": dict(cap=2.5, clip=EV299, o1="deb60", lead=0.0, kick=0.0),
}
CANDS = ("V298", "V299b", "V299a")
MEMBERS = ("nominal", "r79F")
SR, LWB = 16.84, 2.83


def jerk_cap(v):
    """the fork's VM jerk limit, deg per 10 ms frame (MAX_LATERAL_JERK 3.589 m/s^3; small-angle VM, no understeer)."""
    return np.degrees(3.589 / np.maximum(v, 1.0) ** 2 * LWB * SR) * 0.01


# ---------------------------------------------------------------------------------------------------------------------
# the lane subclass for (a) -- tick() is score_time.CandLane.tick verbatim except the two marked additions
# ---------------------------------------------------------------------------------------------------------------------
class LaneA(ST.CandLane):
    def __init__(self, cands, vw):
        super().__init__(cands, vw)
        B = self.B
        self.wash = np.array([A_FEAT.get(c.id, {}).get("wash", 0) for c in cands], np.int64)
        self.kf = np.array([A_FEAT.get(c.id, {}).get("kf", 0) for c in cands], np.int64)
        self.lf = np.array([A_FEAT.get(c.id, {}).get("lf", 0) for c in cands], np.int64)
        self.lp = np.zeros(B, np.int64)          # [ADDED] abe_lp << 16 (the one new RAM word of (a))

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = ST.CAL
        B = self.B
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (B,))
        act = np.broadcast_to(np.asarray(act, np.int64), (B,))
        req = np.broadcast_to(np.asarray(req, np.int64), (B,))
        tq = np.broadcast_to(np.asarray(tq, np.int64), (B,))
        x = np.where(self.fb69, s16(x69), s16(a6a00))
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((0 * s_old >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(cmd)
        cv = self.cave_stage(sp, r26, ramp, a6a00, abe, tq, self.I8, self.Eprev, self.bxC, self.bxW)
        self.wraps += cv["wraps"]
        Ep, frz, leak = cv["Ep"], cv["frz"], cv["leak"]
        e5 = np.where(frz | leak, cv["r6"], Ep >> 5)
        DB = self.DB
        exc = np.where(e5 > DB, e5 - DB, np.where(e5 < -DB, e5 + DB, 0))
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        acc = (cv["I8c"] >> 3) + (s32(exc * self.ki) >> 3)
        I = np.clip(s32(acc), -icl, icl)
        I8n = s32(I << 3)
        P = np.clip(s32(Ep * self.kp) >> 8, -c["PCL"], c["PCL"])
        # [ADDED (a)] washout: op' = op - abe_lp ; abe_lp EMA 2^-wash, seeded to op on the first tick (gp-0x6cf8 sentinel)
        op = cv["op"]
        first = self.Eprev == ST.SENT32
        lp = np.where(first, op << 16, self.lp)
        lp = np.where(self.wash > 0, lp + (((op << 16) - lp) >> np.maximum(self.wash, 1)), 0)
        op_w = np.where(self.wash > 0, op - (lp >> 16), op)
        Dop = s32(self.kd * op_w) >> 3
        Dhe = s32(-self.kd * s16(xheld)) >> 3
        D = np.clip(np.where(self.dop == 1, Dhe, Dop), -self.DCL, self.DCL)
        # [ADDED (a)] friction comp beside P: clamp((E' Kf) >> 8, +-Lf)
        Pf = np.clip(s32(Ep * self.kf) >> 8, -self.lf, self.lf)
        S = s32((I >> 7) + P + D + Pf)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fA = np.where(self.fade2, self.fA2, self.fA1)
        fB = np.where(self.fade2, lerp_vec(*c["fadeB2"], i682f), lerp_vec(*c["fadeB"], i682f))
        f = ((fA * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        self.Eprev = np.where(run, Ep, ST.SENT32)
        self.lp = np.where(run, lp, 0)
        self.n_run += run
        self.n_frz += run & (frz | leak)
        t1 = s32(Sc * c["ob"]) >> 10
        t2 = s32(c["oa"] * self.olag) >> 10
        o_new = s32(t1 + t2)
        y = s32(self.olag + o_new) >> 5
        self.olag = o_new
        yr = s16(s32(y * ramp) >> 15)
        if c["g74a3"] == 1:
            blk = ((s16(y) <= c["dz"]) & (y >= -c["dz"])) | (s32(y * self.Tprev) <= 0)
            yr = np.where((act == 0) & blk, 0, yr)
        k = pol * c["fwd"]
        T = np.clip(s32(yr * k) >> 15, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), frz=frz | leak, run=run, S=np.where(run, Sc, 0))
        return s16(T)


# ---------------------------------------------------------------------------------------------------------------------
# the runner: score_time.run's tick loop with the FORK MODEL added at 100 Hz
# ---------------------------------------------------------------------------------------------------------------------
def run(cols, dur, plan_fn, tq_fn=None, hand_fn=None, road=0.0, th0=None, seed=11):
    B = len(cols)
    cands = [FW[c["cand"]] for c in cols]
    vw = np.array([int(round(c["v"] * 3.6 * 64)) for c in cols], np.int64)
    lane = LaneA(cands, vw)
    pl = ST.Plant([dict(member=c["member"], v=c["v"]) for c in cols])
    if th0 is not None:
        pl.th = np.asarray(th0, float).copy()
    rng = np.random.default_rng(seed)
    vv = np.array([c["v"] for c in cols])
    fk = [FORK[c["cand"]] for c in cols]
    cap = np.minimum(np.array([f["cap"] for f in fk]), jerk_cap(vv))
    emax = np.array([np.interp(c["v"], EBP, f["clip"]) for c, f in zip(cols, fk)])
    deb = np.array([f["o1"] == "deb60" for f in fk])
    leadg = np.array([f["lead"] for f in fk]) * np.interp(vv, EBP, TAU_L)
    kickA = np.array([f["kick"] for f in fk]) * np.interp(vv, EBP, DELTA_F)
    nT = int(round(dur * 1000))
    th_r = np.zeros((nT, B), np.float32)
    T_r = np.zeros((nT, B), np.int16)
    plan_r = np.zeros((nT, B), np.float32)
    spf_r = np.zeros((nT, B), np.float32)
    o1_r = np.zeros((nT, B), bool)
    wire = []
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    road_n = ST._road(B, nT, road) if road > 0 else None
    # fork state
    last = pl.th.copy()
    sp_hist = [pl.th.copy() for _ in range(6)]
    slope_f = np.zeros(B)
    o1 = np.zeros(B, bool)
    pos = np.zeros(B, int)
    kick_s = np.zeros(B)
    kick_t0 = np.full(B, -9.0)
    prev_sg = np.zeros(B)
    plan_z = pl.th.copy()
    sp_fork = pl.th.copy()
    tqv = np.zeros(B, np.int64)
    a_lp = np.exp(-0.01 / 0.03)
    for n in range(nT):
        t = n * 1e-3
        if n % 50 == 0:                                                    # [FORK] 20 Hz model staircase
            plan_z = np.asarray(plan_fn(t), float) * np.ones(B)
        if n % 10 == 0:
            thm = (wire[-2] / 10.0) if len(wire) >= 2 else pl.th.copy()    # [FORK] carState i-1
            thm2 = (wire[-3] / 10.0) if len(wire) >= 3 else thm
            ratem = (thm - thm2) / 0.01
            raw_tq = np.abs(tqv) / 1.024
            on600 = raw_tq > 600
            pos = np.where(on600, pos + 1, 0)
            on = np.where(deb, (raw_tq > 1200) | (pos >= 6), on600)
            was = o1.copy()
            o1 = np.where(on, True, np.where(raw_tq <= 500, False, o1))
            last = np.where(was & ~o1, thm, last)                         # release: re-start from the wheel
            r1 = np.clip(plan_z, last - cap, last + cap)
            r3 = np.where(o1, thm + ratem * 0.06, r1)
            sp_hist = sp_hist[1:] + [r1.copy()]
            slope = (sp_hist[-1] - sp_hist[0]) / 0.05                     # [FORK (b)] 5-frame boxcar slope
            slope_f = a_lp * slope_f + (1 - a_lp) * slope
            sg = np.where(np.abs(slope_f) > 0.5, np.sign(slope_f), 0.0)
            newk = (sg != 0) & (sg != prev_sg)
            kick_s = np.where(newk, sg, kick_s)
            kick_t0 = np.where(newk, t, kick_t0)
            prev_sg = np.where(sg != 0, sg, prev_sg)
            kick = kick_s * kickA * np.exp(-(t - kick_t0) / 0.3)
            r3 = np.where(o1, r3, r3 + leadg * slope_f + kick)
            r4 = np.clip(r3, thm - emax, thm + emax)
            last = np.where(o1, r4, r1)
            sp_fork = r4
            raw = s16(-np.floor(10.0 * r4 + 0.5).astype(np.int64))
            cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
        tqv = np.zeros(B, np.int64) if tq_fn is None else np.round(np.asarray(tq_fn(t, pl.th, pl.om), float)
                                                                   * np.ones(B)).astype(np.int64)
        om_m = pl.om / ST.FRAME.kappa(pl.th)
        g4f50 = s16(np.round(ST.ABE_PER * om_m + rng.normal(0.0, ST.N4F50, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        x69 = np.floor(10.0 * ST.FRAME.cinv(pl.th) + 0.5).astype(np.int64)
        T = lane.tick(held_th, x69, held_x, abe, cmd, tqv, 0x8000, 1, 1)
        q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
        if n % 10 == 4:
            held_th = q_now
            held_x = np.clip(-((s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
            wire.append(q_now.copy())
        u = -pl.delay(T.astype(float))
        if road_n is not None:
            u = u + road_n[n]
        hh = hand_fn(t) if hand_fn is not None else None
        if hh is None:
            pl.step(u)
        else:
            pl.step(u, *hh)
        th_r[n], T_r[n], plan_r[n], spf_r[n], o1_r[n] = pl.th, T, plan_z, sp_fork, o1
    return dict(th=th_r, T=T_r, plan=plan_r, sp=spf_r, o1=o1_r)


# ---------------------------------------------------------------------------------------------------------------------
# scenarios + metrics
# ---------------------------------------------------------------------------------------------------------------------
SLEW_A = {3.0: 90.0, 5.0: 90.0, 8.0: 45.0, 12.0: 20.0, 20.0: 8.0}
SPEEDS = tuple(SLEW_A)


def cols_for(speeds, extra=None):
    out = []
    for v in speeds:
        for m in MEMBERS:
            for c in CANDS:
                for e in (extra or [None]):
                    out.append(dict(cand=c, member=m, v=v, x=e))
    return out


def sc_slew():
    cols = cols_for(SPEEDS)
    A = np.array([SLEW_A[c["v"]] for c in cols])
    R = 300.0
    t1, th_ = 0.5, 2.0
    tA = A / R

    def plan(t):
        return np.where(t < t1, 0.0, np.where(t < t1 + tA, (t - t1) * R,
                        np.where(t < t1 + tA + th_, A, np.maximum(A - (t - t1 - tA - th_) * R, 0.0))))
    r = run(cols, 6.5, plan)
    th, T, sp = r["th"].astype(float), r["T"].astype(float) / 8.0, r["sp"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    out = []
    for j, c in enumerate(cols):
        a = A[j]
        i_in = int((t1 + tA[j]) * 1000)                  # plan arrives at A
        i_end = int((t1 + tA[j] + th_) * 1000)
        w = slice(int(t1 * 1000), i_in)
        om = np.gradient(th[:, j]) * 1000.0
        cover = th[i_in, j] / a                          # wheel travel when the plan arrives
        t90 = tt[np.argmax(th[:, j] >= 0.9 * a)] - t1 if (th[:, j] >= 0.9 * a).any() else np.nan
        over = (th[i_in:i_end, j].max() - a) / a
        err_sl = np.median(np.abs(sp[w, j] - th[w, j]))
        # 18-22 Hz T content over the whole run (grind band), rms LSB
        from scipy import signal
        sos = signal.butter(2, [18, 22], "bandpass", fs=1000, output="sos")
        g20 = float(np.sqrt(np.mean(signal.sosfiltfilt(sos, T[:, j]) ** 2)))
        ret = slice(i_end, i_end + int(tA[j] * 1000))
        cover_ret = (a - th[min(i_end + int(tA[j] * 1000), len(tt) - 1), j]) / a
        out.append(dict(cand=c["cand"], member=c["member"], v=c["v"], A=a, cover=float(cover),
                        cover_ret=float(cover_ret), t90=float(t90), t_plan=float(tA[j]), over=float(over),
                        err_slew_p50=float(err_sl), w_peak=float(np.abs(om).max()), T_peak=float(np.abs(T[:, j]).max()),
                        T_p99=float(np.percentile(np.abs(T[:, j]), 99)), g20_rms=g20))
    return "slew", out


def sc_drift():
    sp_ = (3.0, 8.0, 12.0, 20.0)
    cols = cols_for(sp_)
    D_ = 1.5

    def plan(t):
        return np.where(t < 1.0, 0.0, np.where(t < 5.0, (t - 1.0) * D_, np.where(t < 8.0, 6.0,
                        np.where(t < 12.0, 6.0 - (t - 8.0) * D_, 0.0)))) * np.ones(len(cols))
    r = run(cols, 14.0, plan)
    th, pl_ = r["th"].astype(float), r["plan"].astype(float)
    out = []
    for j, c in enumerate(cols):
        om = np.gradient(th[:, j]) * 1000.0
        omp = np.gradient(pl_[:, j]) * 1000.0
        omp = np.convolve(omp, np.ones(200) / 200, "same")
        stuck = (np.abs(np.convolve(om, np.ones(20) / 20, "same")) < 0.25) & (np.abs(omp) > 1.0)
        d = np.diff(np.r_[0, stuck.astype(int), 0])
        s_, e_ = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
        L = (e_ - s_)
        dw = int((L >= 200).sum())
        dmin = (np.abs(omp) > 1.0).sum() / 60000.0
        err = pl_[:, j] - th[:, j]
        brk = [float(abs(err[e])) for s, e in zip(s_, e_) if e - s >= 200 and e < len(err)]
        mov = np.abs(omp) > 1.0
        out.append(dict(cand=c["cand"], member=c["member"], v=c["v"], dwells=dw, dwells_per_min=dw / max(dmin, 1e-9),
                        stuck_frac=float(stuck[mov].mean()), brk_err_p50=float(np.median(brk)) if brk else 0.0,
                        lag_err_p50=float(np.median(np.abs(err[mov]))), lead_err_p50=float(np.median(-err[mov] * np.sign(omp[mov])))))
    return "drift", out


def sc_n1():
    sp_ = (5.0, 12.0, 20.0)
    W = (400.0, 700.0, 1000.0)
    cols = cols_for(sp_, extra=W)
    B = len(cols)
    Ah = np.array([{5.0: 20.0, 12.0: 6.0, 20.0: 2.5}[c["v"]] for c in cols])
    w = np.array([c["x"] for c in cols])
    sg = np.sign(Ah)
    tg, tr, th_, trel = 2.5, 0.3, 1.0, 3.8

    def plan(t):
        return Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1])

    def tq(t, th, om):
        if tg <= t < trel:
            return -sg * w * min(1.0, (t - tg) / tr)
        if trel <= t < trel + 0.03:
            return -sg * w * (1 - (t - trel) / 0.03)
        return 0.0 * sg

    def hand(t):
        if not (tg <= t < trel):
            return None
        fr = min(1.0, (t - tg) / tr)
        return (np.full(B, 2000.0), np.full(B, 30.0), Ah - fr * Ah)
    r = run(cols, 7.0, plan, tq_fn=tq, hand_fn=hand)
    th = r["th"].astype(float)
    out = []
    i0 = int(trel * 1000)
    for j, c in enumerate(cols):
        after = th[i0:, j] - Ah[j]
        lurch = float(np.max(after * sg[j]))
        out.append(dict(cand=c["cand"], member=c["member"], v=c["v"], w=c["x"], lurch_deg=lurch,
                        under_hand_dev=float(abs(th[i0 - 1, j] - Ah[j])), o1_frac=float(r["o1"][int(tg * 1000):i0, j].mean())))
    return "n1", out


def sc_hold():
    sp_ = (3.0, 8.0, 12.0, 20.0)
    cols = cols_for(sp_)
    Ah = np.array([{3.0: 45.0, 8.0: 15.0, 12.0: 6.0, 20.0: 2.5}[c["v"]] for c in cols])

    def plan(t):
        return Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1])
    r = run(cols, 16.0, plan, road=15.0)
    th, T = r["th"].astype(float), r["T"].astype(float) / 8.0
    from scipy import signal
    out = []
    s = slice(4000, None)
    for j, c in enumerate(cols):
        om = np.gradient(th[s, j]) * 1000.0
        sgn = np.sign(np.where(np.abs(om) > 0.2, om, 0))
        sgn = sgn[sgn != 0]
        rev = int(np.count_nonzero(np.diff(sgn) != 0)) if len(sgn) > 1 else 0
        b48 = signal.sosfiltfilt(signal.butter(2, [4, 8], "bandpass", fs=1000, output="sos"), T[s, j])
        b1322 = signal.sosfiltfilt(signal.butter(2, [13, 22], "bandpass", fs=1000, output="sos"), T[s, j])
        out.append(dict(cand=c["cand"], member=c["member"], v=c["v"], rev_per_s=rev / 12.0,
                        T48_rms=float(np.sqrt(np.mean(b48 ** 2))), T1322_rms=float(np.sqrt(np.mean(b1322 ** 2))),
                        err_rms=float(np.sqrt(np.mean((th[s, j] - Ah[j]) ** 2)))))
    return "hold", out


def sc_sin():
    sp_ = (12.0, 20.0)
    cols = cols_for(sp_)

    def plan(t):
        return 1.0 * np.sin(2 * np.pi * 0.2 * t) * np.ones(len(cols))
    r = run(cols, 15.0, plan)
    th, pl_ = r["th"].astype(float), r["plan"].astype(float)
    out = []
    s = slice(5000, None)
    tt = np.arange(th.shape[0])[s] * 1e-3
    E = np.exp(-2j * np.pi * 0.2 * tt)
    for j, c in enumerate(cols):
        H = np.sum(th[s, j] * E) / np.sum(np.sin(2 * np.pi * 0.2 * tt) * E)
        out.append(dict(cand=c["cand"], member=c["member"], v=c["v"], gain=float(abs(H)),
                        lag_ms=float(-np.angle(H) / (2 * np.pi * 0.2) * 1000)))
    return "sin", out


SCN = {"slew": sc_slew, "drift": sc_drift, "n1": sc_n1, "hold": sc_hold, "sin": sc_sin}


def job(name):
    t0 = time.time()
    nm, out = SCN[name]()
    return nm, out, time.time() - t0


if __name__ == "__main__":
    T0 = time.time()
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    with Pool(procs) as P:
        res = P.map(job, list(SCN))
    R = {nm: dict(rows=out, wall=w) for nm, out, w in res}
    R["wall_total_s"] = time.time() - T0
    (OUT / "s4_closed_loop.json").write_text(json.dumps(R, indent=1), encoding="utf-8")
    for nm, out, w in res:
        print("== %s (%.1f s)" % (nm, w))
        keys = [k for k in out[0] if k not in ("cand", "member", "v", "w")]
        for row in out:
            print("  %-6s %-8s v %4.1f %s %s" % (row["cand"], row["member"], row["v"],
                                               ("w %4.0f" % row["w"]) if "w" in row else "",
                                               " ".join("%s %.3g" % (k, row[k]) for k in keys if isinstance(row[k], (int, float)))))
    print("wall total %.1f s" % (time.time() - T0))
