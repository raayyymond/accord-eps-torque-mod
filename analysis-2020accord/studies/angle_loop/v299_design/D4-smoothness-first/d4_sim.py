# -*- coding: utf-8 -*-
r"""d4_sim.py -- DESIGNER D4 (smoothness-first): the NONLINEAR 1 kHz TIME SIM for every D4 claim about stick-slip,
freeze chatter and N1 release lurch.  ANALYSIS ONLY (no image, no fork edit, nothing sent).

ENGINE = the panel-2 COMMON time scorer, imported unchanged (panel2/score_time.py: nl_sim's Karnopp plant on the r71b
family, 10 kHz sub-steps, 2 ms transport, the slot-4 100 Hz angle hold, the 1 kHz gp-0x6abe EMA, the frame map, the
0xE4 ZOH, the fade, the output lag, the ramp, the rail).  Its lane class is replaced by D4Lane below, which is
ST.CandLane's arithmetic for V298's configuration (fresh D Kd 48, Ki 40, ICL 8192, GB-P, A3 + low-speed cap, the
ramp freeze, dir-2 ramp 328/66) with the D4 switches:
    H     hard freeze threshold on |gp-0x4f68|                          (V298 512)
    T     opposing threshold                                            (V298 300)
    mg    MOTION GATE: skip the opposing test while (abe ^ E') < 0 and |abe| > mg  (V298: off)
    lp    the state word h += (hs - h) >> lp (signed hand word, init 0 on the sentinel tick); the H and T tests then
          read h instead of the raw word                                (V298: off)
    mc    the in-place variant: opposing test on sign(hs - mc * abe)     (V298: off)
    gs    stiffness: G' = (G * gs) >> 8 inside [gv_lo, gv_hi] m/s       (V298: 256)
    ff    friction feedforward added to the D operand r26 (D = 6 op ~ 0.96 op T):
          ('sp', N, K, DZ, FC_lo, FC_hi): y32 += (sp<<12 - y32) >> N, ff = clamp((d32 -+ DZ) >> K, +-FC(v))
          ('err', DZ, K, FC_lo, FC_hi):  ff = clamp((|E'| - DZ)+ sgn(E') >> K, +-FC(v))
CONTROL: D4Lane with every switch at V298's value == ST.CandLane('C3B-P' with V298's ramp) bit for bit (selftest).

TWIST: the hands-off reaction word gp-0x4f60 = LP15ms(-0.69 alpha - 0.69 omega - 163 sgn omega - 61) + N(0, 120)
held at 100 Hz (M3's fit, R2 0.31: the sign is EVIDENCE, the model and the noise level are BELIEF, sized so the
|word| p50/p90 at |alpha| < 25 deg/s^2 is ~110/240 like route 79's 114/244).

MEMBERS nominal, F_hi (the family) and r79bk: nominal with the static friction set to route 79's BREAKAWAY p50 per band
(156/93/47/51/29/28 T at 2.5/6.5/10.25/15.25/21.5/28 m/s) and Coulomb = 0.8 x that (the drive-read instrument,
single method: BELIEF).

usage: python d4_sim.py selftest | run A|B [procs]     (writes _scratch/v299_D4/sim_*.json + .txt; wall time printed)
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "v299_D4"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(AL / "c3" / "rev2B"))
import rb_table as TB  # noqa: E402

_st = importlib.util.spec_from_file_location("p2_st_d4", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_st)
sys.modules["p2_st_d4"] = ST
_st.loader.exec_module(ST)
NS = ST.NS
s16, s32 = ST.s16, ST.s32
SENT32 = ST.SENT32

# ---------------------------------------------------------------------------------------------------------------------
# the r79 friction member
# ---------------------------------------------------------------------------------------------------------------------
_P0 = NS.params
_VB = np.array([2.5, 6.5, 10.25, 15.25, 21.5, 28.0])
_FS = np.array([156.0, 93.0, 47.0, 51.0, 29.0, 28.0])


def params(member, v):
    if member == "r79bk":
        J, b, k, sat, Fc, Fs, tau = _P0("nominal", v)
        fs = float(np.interp(v, _VB, _FS))
        return J, b, k, sat, 0.8 * fs, fs, tau
    return _P0(member, v)


NS.params = params

# ---------------------------------------------------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------------------------------------------------
V298_RAMP = dict(ramp_in=328, ramp_out=66)
BASE = ST.Cand("V298", "D4", tuple(TB.GB_P), "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300, **V298_RAMP)


@dataclass
class D4:
    H: int = 512
    T: int = 300
    mg: int = -1                 # -1 = off
    lp: int = 0                  # 0 = off
    mc: int = 0
    gs: int = 256
    gv: tuple = (0.0, 99.0)
    ff: tuple = None
    note: str = ""


CFG = {
    "V298": D4(note="as flown"),
    "a:H1229T450": D4(H=1229, T=450, note="(a') in-place thresholds 1229/450 (N1 cost)"),
    "b0:mg10": D4(H=1229, mg=10, note="motion gate, no state"),
    "b2:mg10lp5": D4(H=1229, mg=10, lp=5, note="(b) motion gate + hand LP 32 ms (1 state word)"),
    "b8:lp5H512": D4(H=512, mg=10, lp=5, note="(b) motion gate + hand LP 32 ms, hard 512 on the LP word"),
    "b7:lp4H512": D4(H=512, mg=10, lp=4, note="(b) motion gate + hand LP 16 ms, hard 512 on the LP word"),
    "a:GBS13": D4(note="(a) GB-S13 table (knots 10/11.75/17.5 m/s x1.3), V298 hand rules"),
    "b8+GBS13": D4(H=512, mg=10, lp=5, note="(b) + the GB-S13 table"),
    "b2+FFsp": D4(H=1229, mg=10, lp=5, ff=("sp", 7, 8, 32768, 60, 30), note="(b) + sp-rate friction FF"),
    "b2+FFerr": D4(H=1229, mg=10, lp=5, ff=("err", 40, 4, 60, 30), note="(b) + error-keyed friction FF"),
}
GB_S13 = ((714, 1178, 1041), (1843, 1465, -4238), (2304, 988, -2643), (2707, 728, 2040), (4032, 1388, 1513),
          (6198, 2188, 0), (65535, 2188, 0))          # d4_gate2.scaled(GB-P, knots 2..4, 1.3)
CANDS = []
for k_ in CFG:
    rows_ = GB_S13 if "GBS13" in k_ else tuple(TB.GB_P)
    c_ = ST.Cand(k_, "D4", rows_, "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=300, **V298_RAMP)
    CANDS.append(c_)
    if k_ not in ST.CBYID:
        ST.CANDS.append(c_)
        ST.CBYID[k_] = c_


# ---------------------------------------------------------------------------------------------------------------------
# THE D4 LANE
# ---------------------------------------------------------------------------------------------------------------------
class D4Lane(ST.CandLane):
    def __init__(self, cands, vw):
        super().__init__(cands, vw)
        cf = [CFG.get(c.id, D4()) for c in cands]
        A = lambda f: np.array([f(x) for x in cf], np.int64)  # noqa: E731
        self.H, self.T, self.mg, self.lp, self.mc = A(lambda x: x.H), A(lambda x: x.T), A(lambda x: x.mg), \
            A(lambda x: x.lp), A(lambda x: x.mc)
        vms = self.vw / 230.4
        gs = A(lambda x: x.gs)
        inb = np.array([x.gv[0] <= v_ < x.gv[1] for x, v_ in zip(cf, vms)])
        self.G = np.where(inb, s32(self.G * gs) >> 8, self.G)
        self.ffk = np.array([{None: 0, "sp": 1, "err": 2}[x.ff[0] if x.ff else None] for x in cf])
        ffp = [x.ff if x.ff else ("", 0, 0, 0, 0, 0) for x in cf]
        self.ffp = ffp
        lo = vms <= 6.0
        self.FC = np.array([(p[-2] if l_ else p[-1]) if p[0] else 0 for p, l_ in zip(ffp, lo)], np.int64)
        self.h = np.zeros(self.B, np.int64)
        self.y32 = np.zeros(self.B, np.int64)
        self.n_tog = np.zeros(self.B, np.int64)
        self.prev_fz = np.zeros(self.B, bool)
        self.ff_last = np.zeros(self.B, np.int64)

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = ST.CAL
        B = self.B
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (B,))
        act = np.broadcast_to(np.asarray(act, np.int64), (B,))
        req = np.broadcast_to(np.asarray(req, np.int64), (B,))
        tq = np.broadcast_to(np.asarray(tq, np.int64), (B,))
        x = s16(a6a00)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32(s32(x * 8192) >> 10)
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)
        sp = s16(cmd)
        first = self.Eprev == SENT32                                   # the sentinel path (engage init)
        # ---- cave: E, E'
        E = s32((sp << 2) - r26)
        Ep = s32(E * self.G) >> 8
        ab = s16(abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000
        op = np.where(abv, ab, 0)
        hs = s16(tq)
        atq = np.minimum(np.abs(tq), 0xFFFF)
        # ---- the state word h (hand LP), updated on run ticks only, init 0 on the sentinel tick
        hprev = np.where(first, 0, self.h)
        lpon = self.lp > 0
        hnew = s32(hprev + (s32(hs - hprev) >> np.where(lpon, self.lp, 0)))
        hnew = np.where(lpon, hnew, hs)
        self.h = np.where(run & lpon, hnew, self.h)
        hw = np.where(lpon, hnew, hs)                                  # the word the freeze tests read
        ahw = np.where(lpon, np.minimum(np.abs(hw), 0xFFFF), atq)
        # ---- the hand rules
        c1 = ahw > self.H
        toward = (self.mg >= 0) & ((op ^ Ep) < 0) & (np.abs(op) > self.mg)
        hsig = np.where(self.mc > 0, s32(hw - self.mc * op), hw)
        c2 = (ahw > self.T) & ((hsig ^ Ep) < 0) & ~toward
        I_S = self.I8 >> 10
        t = np.where(Ep >= 0, I_S, -I_S)
        th6 = s16(a6a00)
        sh = np.where((self.vw & 0xFFFF) <= self.arb_vth, self.arb_sh_lo, self.arb_sh)
        bound = s32((np.abs(th6) << sh) + self.arb_B)
        capon = (self.vw & 0xFFFF) <= self.arb_vcap
        bound = np.where(capon & (bound > self.arb_cap), self.arb_cap, bound)
        c3 = t >= bound
        c4 = (np.asarray(ramp, np.int64) & 0x8000) == 0
        frz = c1 | (~c1 & c2) | (~c1 & ~c2 & (c3 | c4))
        hand = c1 | c2
        # ---- friction feedforward into the D operand
        ff = np.zeros(B, np.int64)
        if (self.ffk == 1).any():
            m = self.ffk == 1
            N = np.array([p[1] if p[0] == "sp" else 1 for p in self.ffp], np.int64)
            K = np.array([p[2] if p[0] == "sp" else 1 for p in self.ffp], np.int64)
            DZ = np.array([p[3] if p[0] == "sp" else 0 for p in self.ffp], np.int64)
            x12 = sp << 12
            yprev = np.where(first, x12, self.y32)
            d32 = x12 - yprev
            ynew = yprev + (d32 >> N)
            self.y32 = np.where(run & m, ynew, self.y32)
            q = np.where(d32 > DZ, d32 - DZ, np.where(d32 < -DZ, d32 + DZ, 0))
            ff = np.where(m, np.clip(q >> K, -self.FC, self.FC), ff)
        if (self.ffk == 2).any():
            m = self.ffk == 2
            DZ = np.array([p[1] if p[0] == "err" else 0 for p in self.ffp], np.int64)
            K = np.array([p[2] if p[0] == "err" else 0 for p in self.ffp], np.int64)
            q = np.where(Ep > DZ, Ep - DZ, np.where(Ep < -DZ, Ep + DZ, 0))
            ff = np.where(m, np.clip(q >> K, -self.FC, self.FC), ff)
        op = op + ff
        self.ff_last = ff
        # ---- Honda's I (0x29D7A..): e5 = 0 on the freeze exit
        e5 = np.where(frz, 0, Ep >> 5)
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        acc = (self.I8 >> 3) + (s32(e5 * self.ki) >> 3)
        I = np.clip(s32(acc), -icl, icl)
        I8n = s32(I << 3)
        P = np.clip(s32(Ep * self.kp) >> 8, -c["PCL"], c["PCL"])
        D = np.clip(s32(self.kd * op) >> 3, -self.DCL, self.DCL)
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = ST.lerp_vec(*c["fadeB"], i682f)
        f = ((self.fA1 * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        SCL = c["SCL"]
        Sc = np.where(Sf > SCL, SCL, np.where(Sf < -SCL, -SCL, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        self.Eprev = np.where(run, Ep, SENT32)
        self.n_run += run
        self.n_frz += run & frz
        self.n_tog += run & (hand != self.prev_fz)
        self.prev_fz = np.where(run, hand, self.prev_fz)
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
        r11 = s32(yr * k) >> 15
        Tq = np.clip(r11, -c["OCL"], c["OCL"])
        self.Tprev = yr
        self.log = dict(I=np.where(run, I >> 7, 0), frz=frz, run=run, hand=hand)
        return s16(Tq)


# ---------------------------------------------------------------------------------------------------------------------
# the hands-off TWIST word (stateful closure; ST.run calls tq(t, th, om) once per tick)
# ---------------------------------------------------------------------------------------------------------------------
class Twist:
    def __init__(self, B, seed=3, sigma=120.0, scale=1.0):
        self.rng = np.random.default_rng(seed)
        self.om_prev = None
        self.alf = np.zeros(B)
        self.word = np.zeros(B)
        self.sig, self.scale, self.B = sigma, scale, B
        self.n = 0

    def __call__(self, t, th, om):
        if self.om_prev is None:
            self.om_prev = om.copy()
        a = (om - self.om_prev) * 1000.0
        self.om_prev = om.copy()
        self.alf += (a - self.alf) * (1.0 / 15.0)               # 15 ms LP of alpha (torsion bar + sensor)
        if self.n % 10 == 0:                                    # the word refreshes at 100 Hz
            self.word = self.scale * (-0.69 * self.alf - 0.69 * om - 163.0 * np.sign(om) - 61.0) + \
                self.rng.normal(0.0, self.sig, self.B)
        self.n += 1
        return self.word


# ---------------------------------------------------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------------------------------------------------
A_SLEW = {3.0: 90.0, 5.0: 60.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0}


def scn_slew(cols, twist=True):
    """hard manoeuvre: the fork's 120 deg/s capped ramp to A(v), hold 1.5 s, return at 120 deg/s, hold."""
    B = len(cols)
    A = np.array([A_SLEW[c["v"]] for c in cols])
    tr = A / 120.0

    def ref(t):
        return np.interp(t, [0, 0.5, 0.5 + tr.max(), 9], [0, 0, 1, 1]) * 0 + \
            A * np.clip((t - 0.5) / tr, 0, 1) - A * np.clip((t - 2.5 - tr) / tr, 0, 1)
    return ST.Scn(dur=6.0, ref=ref, tq=Twist(B) if twist else None), dict(A=A, t_on=0.5, tr=tr)


def scn_creep(cols, twist=True, rate=1.5):
    """small-correction drift: +rate deg/s for 3 s, hold 2 s, -rate deg/s for 3 s (reversal), hold 2 s."""
    B = len(cols)

    def ref(t):
        return np.ones(B) * (rate * np.clip(t - 1.0, 0, 3.0) - rate * np.clip(t - 5.0, 0, 3.0))
    return ST.Scn(dur=8.5, ref=ref, tq=Twist(B, sigma=60.0, scale=0.5) if twist else None), dict(rate=rate)


def scn_jit(cols):
    """quasi-static hold at 0.5 A with route 79's measured one-quantum setpoint jitter (+-0.1 deg reversals ~4.6/s)."""
    B = len(cols)
    rng = np.random.default_rng(9)
    A = np.array([ST.A_turn(c["v"]) for c in cols]) * 0.5
    flips = np.cumsum(rng.random(3000) < 0.046)                 # 100 Hz frames: a flip with p 0.046 -> 4.6 /s
    jit = 0.1 * (flips % 2)

    def ref(t):
        k = min(int(t * 100), 2999)
        return A * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1]) + jit[k]
    return ST.Scn(dur=8.0, ref=ref, tq=Twist(B, sigma=60.0, scale=0.5)), dict(A=A)


def scn_out(cols, w):
    """N1 OUTWARD light hold (rb_n1's 'out_2_*_3' form on the common engine): hold the planned Ah; from 2.5 s a stiff
    hand drags the wheel OUTWARD to 2 Ah over 0.3 s and holds it 3 s with the signed word +w (pushing away from the
    setpoint, i.e. outward), then lets go in 30 ms.  lurch = max overshoot past Ah (toward centre is droop)."""
    B = len(cols)
    A = np.array([ST.A_turn(c["v"]) for c in cols])
    Ah = 0.5 * A
    sg = np.sign(Ah)
    tg, tr, thold = 2.5, 0.3, 3.0
    trel = tg + tr + thold

    def ref(t):
        return Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1])

    def tq(t, th, om):
        if tg <= t < trel:
            return sg * w * min(1.0, (t - tg) / tr)
        if trel <= t < trel + 0.03:
            return sg * w * (1 - (t - trel) / 0.03)
        return 0.0 * sg

    def hand(t):
        if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
            return None
        fr = min(1.0, (t - tg) / tr)
        return (np.full(B, 2000.0), np.full(B, 30.0), Ah + fr * Ah)
    S = ST.Scn(dur=trel + 3.0, ref=ref, tq=tq, hand=hand, rec_I=True)
    return S, dict(t_rel=trel, Ah=Ah)


def mov(x, n):
    k = np.ones(n) / n
    return np.apply_along_axis(lambda c: np.convolve(c, k, "same"), 0, x)


def stall_count(om100, mask):
    """M4's stall-surge detector on 100 Hz frames (turn >= 10 deg/s, stall < 0.25 x, surge > 0.75 x within 0.25 s)."""
    mbar = mov(om100, 50)
    out = []
    for j in range(om100.shape[1]):
        mb = mbar[:, j]
        turn = mask & (np.abs(mb) >= 10.0)
        u = om100[:, j] * np.sign(mb)
        f3 = np.convolve(u, np.ones(3) / 3, "same")
        stall = turn & (f3 < 0.25 * np.abs(mb))
        surge = turn & (f3 > 0.75 * np.abs(mb))
        n = 0
        for a, b in NS.runs_of(stall, 2):
            nxt = np.flatnonzero(surge[b:b + 26])
            prv = np.flatnonzero(surge[max(0, a - 26):a])
            if len(nxt) and len(prv):
                n += 1
        out.append(n)
    return np.array(out, float)


def metrics(name, meta, r, lane_stats, cols):
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    plan1k = np.repeat(r["plan"].astype(float), 10, axis=0)[:n]
    m = dict(peakT=np.abs(T).max(0), frz_duty=lane_stats["frz"], tog_per_s=lane_stats["tog"])
    if name in ("slew", "slew_nt"):
        om100 = om[4::10]
        msk = np.ones(om100.shape[0], bool)
        m["stalls"] = stall_count(om100, msk)
        m["hard16"] = np.sqrt(np.mean(ST._bp(om, 1.6, 3.0)[200:-200] ** 2, 0))
        m["T_hf"] = np.sqrt(np.mean(ST._bp(T, 5, 30)[500:] ** 2, 0))
        w = (tt >= 0.5) & (tt < 2.5)
        m["lag_p50"] = np.median(np.abs(plan1k[w] - th[w]), 0)
        m["reach"] = (th[(tt >= 2.0) & (tt < 2.5)].mean(0) / meta["A"])
        m["I_end"] = r["I"][int(2.4 * 1000)].astype(float) if r.get("I") is not None else np.zeros(len(cols))
        return m
    if name in ("creep", "creep_nt"):
        idx = np.arange(4, n, 10)
        ev, jm = NS.dwell_jump(om[idx], th[idx], plan1k[idx])
        m["dj"], m["dj_max"] = ev.astype(float), jm
        mv = np.abs(np.gradient(plan1k[idx], axis=0) * 100.0) > 0.05
        m["stick_pct"] = 100.0 * ((om[idx] == 0.0) & mv).sum(0) / np.maximum(mv.sum(0), 1)
        w = tt >= 1.5
        m["lag_max"] = np.abs(plan1k[w] - th[w]).max(0)
        m["slips"] = NS.slips(th[w], om[w]).astype(float)
        m["T_hf"] = np.sqrt(np.mean(ST._bp(T, 5, 30)[w] ** 2, 0))
        return m
    if name.startswith("out"):
        trel, Ah = meta["t_rel"], meta["Ah"]
        w = tt >= trel + 0.05
        i_r = int(trel * 1000)
        m["lurch_in"] = np.max((Ah - th[w]) * np.sign(Ah), 0)          # swing back PAST the setpoint toward centre
        m["settle_err"] = np.abs(th[tt >= trel + 2.5] - Ah).max(0)
        m["I_rel"] = r["I"][i_r - 2].astype(float)
        m["T_rel"] = np.abs(T[i_r - 2]).astype(float)
        return m
    if name == "rn":
        w = tt >= 3.0
        e = (plan1k - th)[w]
        m["e_rms"] = e.std(0)
        m["hunt_rev"] = ST._rev(om[w]).astype(float)
        m["hunt_p2p"] = th[w].max(0) - th[w].min(0)
        m["T_hf"] = np.sqrt(np.mean(ST._bp(T, 5, 30)[w] ** 2, 0))
        m["om_hf"] = np.sqrt(np.mean(ST._bp(om, 5, 30)[w] ** 2, 0))
        return m
    if name == "jit":
        w = tt >= 2.5
        m["T_hf"] = np.sqrt(np.mean(ST._bp(T, 5, 30)[w] ** 2, 0))
        m["T_jit"] = np.sqrt(np.mean(ST._bp(T, 2, 30)[w] ** 2, 0))
        m["hunt_rev"] = ST._rev(om[w]).astype(float)
        m["hunt_p2p"] = th[w].max(0) - th[w].min(0)
        m["slips"] = NS.slips(th[w], om[w]).astype(float)
        return m
    return ST.metrics(name, meta, r, cols)


def lane_run(cols, scn):
    """ST.run with D4Lane (ST.run builds `CandLane(cands, vw)` from the module global)."""
    ST.CandLane = D4Lane
    holder = {}
    orig_init = D4Lane.__init__

    def init(self, cands, vw):
        orig_init(self, cands, vw)
        holder["lane"] = self
    D4Lane.__init__ = init
    try:
        r = ST.run(cols, scn, frame="vgr")
    finally:
        D4Lane.__init__ = orig_init
    ln = holder["lane"]
    return r, dict(frz=ln.n_frz / np.maximum(ln.n_run, 1), tog=ln.n_tog / max(scn.dur, 1e-9))


SPEEDS = (3.0, 5.0, 8.0, 12.5, 19.0, 26.0)
MEMBERS = ("nominal", "F_hi", "r79bk")
SCN_SETS = {"A1": ("slew", "slew_nt", "creep", "creep_nt"), "A2": ("jit", "s03_05", "rn"),
            "B1": ("ov_lt400", "ov_lt511", "cs"), "B2": ("ov3_lt511", "ov_fm2400"), "C": ("out400", "out511", "out1000")}
B_IDS = ("V298", "a:GBS13", "a:H1229T450", "b0:mg10", "b2:mg10lp5", "b8:lp5H512", "b7:lp4H512")


def job(args):
    scn, member = args
    t0 = time.time()
    cands = [c for c in CANDS if (not scn.startswith(("ov", "cs", "out"))) or c.id in B_IDS]
    cols = [dict(cand=c, member=member, v=v) for v in SPEEDS for c in cands]
    if scn == "th":
        cols = [dict(cand=c, member=member, v=v, alat=a) for v in SPEEDS for a in ((1.5, 2.5) if v >= 8 else (0.0,))
                for c in CANDS]
    if scn in ("slew", "slew_nt"):
        S, meta = scn_slew(cols, twist=(scn == "slew"))
        S.rec_I = True
    elif scn in ("creep", "creep_nt"):
        S, meta = scn_creep(cols, twist=(scn == "creep"))
    elif scn == "jit":
        S, meta = scn_jit(cols)
    elif scn.startswith("out"):
        S, meta = scn_out(cols, float(scn[3:]))
    elif scn == "rn":
        S, meta = ST.scenario("rn30", cols)
        S.dur = 9.0
    else:
        S, meta = ST.scenario(scn, cols)
        if scn == "s03_05":
            S.dur = 8.0
    r, ls = lane_run(cols, S)
    m = metrics(scn, meta, r, ls, cols)
    keys = [dict(id=c["cand"].id, v=c["v"], alat=c.get("alat")) for c in cols]
    return dict(scn=scn, member=member, keys=keys, sec=time.time() - t0,
                m={k: np.asarray(x, float).tolist() for k, x in m.items() if np.ndim(x) == 1})


def selftest():
    """CONTROL: D4Lane('V298') == ST.CandLane(V298 Cand) bit for bit on a hard scenario with a twist word."""
    cols = [dict(cand=CANDS[0], member=mb, v=v) for v in (3.0, 12.5, 26.0) for mb in ("nominal", "r79bk")]
    S1, _ = scn_slew(cols)
    S2, _ = scn_slew(cols)
    r1, _ = lane_run(cols, S1)
    ST.CandLane = _ORIG
    cols2 = [dict(cand=BASE, member=c["member"], v=c["v"]) for c in cols]
    r2 = ST.run(cols2, S2, frame="vgr")
    d = int(np.count_nonzero(r1["T"] != r2["T"]))
    print("SELFTEST D4Lane(V298) vs ST.CandLane(C3B-P, dir-2 ramp): differing T words %d of %d" % (d, r1["T"].size))
    return d


_ORIG = ST.CandLane


def main():
    t0 = time.time()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "selftest":
        selftest()
    else:
        which = sys.argv[2] if len(sys.argv) > 2 else "A"
        procs = int(sys.argv[3]) if len(sys.argv) > 3 else 16
        jobs = [(s, mb) for s in SCN_SETS[which] for mb in MEMBERS]
        jobs.sort(key=lambda j: -{"rn": 9, "jit": 8, "s03_05": 8, "creep": 8.5, "creep_nt": 8.5, "ov3_lt511": 9.3}.get(j[0], 7))
        with Pool(procs) as pool:
            res = pool.map(job, jobs, chunksize=1)
        json.dump(res, open(OUT / ("sim_raw_%s.json" % which), "w"))
        print("jobs %d, max job %.1f s" % (len(res), max(r["sec"] for r in res)))
    print("WALL %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
