# -*- coding: utf-8 -*-
r"""s2_time.py -- V299 judge panel, scorer S2 (COMMON TIME / NONLINEAR).  ONE nonlinear 1 kHz sim for EVERY candidate
(D1..D5 and their implementations) on ONE manoeuvre set, scored identically.  ANALYSIS ONLY: builds no image, flashes
nothing, sends nothing, edits no fork / firmware / golden-model file.

ENGINE (reused, unchanged; every reuse is controlled in `control`):
  * panel2/score_time.py (loaded by path as module p2_st_s2): the Karnopp plant on the r71b family (10 kHz sub-steps,
    2 ms transport), the frame map (gp-0x6a00 = C(motor angle), motor rate = omega / kappa), the 1 kHz gp-0x6abe EMA
    with sensor noise, the slot-4 100 Hz angle hold, the fade records, the output lag, the ramp, the rail constants.
  * d2_common.py (D2's): the V298 image read (sha 177abf04, GB-P rows asserted), the fork's VM jerk / accel limits from
    route 79's CarParams.
THE LANE = S2Lane below: score_time.CandLane.tick's arithmetic (0x28F4C..0x2A20C + the V298 cave) re-written with
  every candidate's firmware edit as a per-column switch:
    thr  hard hand freeze on |gp-0x4f68| (V298 512; D1/D3/D5 1229)      sgn  opposing freeze (V298 300; D3 800; 0 = off)
    asym D1c's asymmetric A3 bound (|theta| term := 0 when sign(theta) != sign(E'))
    d4   D4b's state word h = h + ((hs - h) >> 5) (gp-0x6a32, 0 on the sentinel tick) read by both hand tests, plus the
         motion gate (opposing freeze skipped while gp-0x6abe opposes E' and |abe| > 10)       [d4_cave.d4b_hand]
    d5a  D5-(a): washout D (op - (EMA_2^-9(op<<16) >> 16), seeded on the sentinel) + friction comp
         clamp((E' 75) >> 12, +-67) added to D's operand                                     [DESIGN-V299-D5 2(a)]
    rows the G(v) table (GB-P / D1 G0-1400 / D3 GB_D3 / D4 GB-S13);  scl/pcl the sum / P clamps (D3b 19072)
  CONTROLS (`python s2_time.py control`): S2Lane == score_time.CandLane (V298) == d1_time.D1Lane (D1c) ==
  d4_sim.D4Lane (D4b 'b8:lp5H512', D4a 'a:GBS13') bit for bit on the common scorer's own scenarios.
THE FORK (100 Hz; honda/carcontroller.py _update_angle @ Dom 2712e1336 re-implemented, every candidate's change a
  per-column switch): the 20 Hz model staircase (ZOH 50 ms; D2b interpolates), carState i-1 (the 0x14A sample one
  frame older), the VM jerk limit min'd with the rate cap (per-candidate schedule), the VM accel limit, O1 (on/off
  thresholds, debounce, instant-hard, D3's held-1200), O1 setpoint theta + lead*rate, the release restart from the
  wheel (apply_angle_last := theta), the error clip (post-clip value stored as apply_angle_last, as the fork does),
  D2's takeover ramp (rate AND clip x since/0.4 s), D2b's 2nd-order limiter (1500 deg/s^2 + braking) and plan lead
  tau(v) (bounded 4 deg / 0.6 m/s^2), D2a's SteerDelay +0.10 s (= plan sampled 0.10 s ahead, BELIEF), D3's K3
  D-cancel lead (after the clip, 0 under O1 and 0.3 s after release) and K4 (120 deg/s for 0.5 s after release),
  D5's lead (5-frame boxcar slope + 30 ms pole, before the clip, history seeded on release).
THE TORQUE WORD gp-0x4f60 (BELIEF model, sign EVIDENCE): the r79 hands-off reaction fit
  word = -0.69 alpha - 0.69 omega - 163 tanh(omega/2) - 61  (alpha = 8 Hz LP of d omega/dt, deg/s^2; omega deg/s)
  + an AR(1) residual at 100 Hz (sd 206, lag-1 0.89: d1_r79.json, the same fit), one realisation shared by all columns
  + the hand's prescribed word when a hand is on.  The fork sees |word|/1.024 (0x18F, i-1 sample).
PLANT MEMBERS: r79F = nominal with route 79's Coulomb friction (156 T <= 5 m/s, 85 T >= 6 m/s, Fs 1.25 Fc; D5's
  member, BELIEF single-method) and b_lo*J_hi (the heavy refuter member).
MANOEUVRES (groups run in parallel processes; every candidate is a column of the SAME run):
  TI  60 deg turn-in at 3 and 8 m/s at the planner's demand rate min(320, jerk-5 rate) = 320 / 216 deg/s, hold 2.5 s,
      unwind at the same rate; residual noise on (x=1) and off (x=0)
  C2  2 deg correction at 15 and 25 m/s: x=fast (0.25 s ramp), x=slow (1.33 deg/s drift = r79's dwell drift)
  LH  hold under a light hand: word 400, stiff hand (Kh 2000, Bh 30) displaces the wheel 30 % of the hold angle toward
      centre (x=c) or outward (x=o) for 2 s, release; 5 and 15 m/s
  OV  hand override: word ramps to 1500 in 0.3 s, the hand drags the wheel to centre, holds 1.5 s, releases; 5, 15 m/s
  RD  request drop mid-turn (hold at A/2), 3 and 8 m/s
usage:  python s2_time.py control | run [group,...] | report
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
V299 = HERE.parents[1]                       # .../v299_design
AL = V299.parent                             # .../studies/angle_loop
KIT = AL.parents[2]
OUT = KIT / "_scratch" / "v299_S2"
OUT.mkdir(parents=True, exist_ok=True)
for _q in (V299 / "D2-fork-first", AL / "panel", AL / "c1", AL / "c3" / "rev2B", AL / "refute_c2r2_nonlinear", AL):
    if str(_q) not in sys.path:
        sys.path.insert(0, str(_q))
_st = importlib.util.spec_from_file_location("p2_st_s2", AL / "panel2" / "score_time.py")
ST = importlib.util.module_from_spec(_st)
sys.modules["p2_st_s2"] = ST
_st.loader.exec_module(ST)
import d2_common as D2C  # noqa: E402

NS = ST.NS
s16, s32, lerp_vec = ST.s16, ST.s32, ST.lerp_vec
SENT32 = ST.SENT32
RAIL_TAP = 2461.0 / 8.0

# ---------------------------------------------------------------------------------------------------------------------
# plant member r79F (D5's: route 79's single-method Coulomb estimate; BELIEF)
# ---------------------------------------------------------------------------------------------------------------------
_P0 = NS.params


def _params(member, v):
    if member == "r79F":
        J, b, k, sat, Fc, Fs, tau = _P0("nominal", v)
        Fc = float(np.interp(v, [5.0, 6.0], [156.0, 85.0]))
        return J, b, k, sat, Fc, 1.25 * Fc, tau
    return _P0(member, v)


NS.params = _params
ST.Plant._cache = {}
MEMBERS = ("r79F", "b_lo*J_hi")

# ---------------------------------------------------------------------------------------------------------------------
# G tables (EVIDENCE: GB-P read from the V298 image by d2_common; the others from each design page, slopes re-derived)
# ---------------------------------------------------------------------------------------------------------------------
GBP = tuple(tuple(r) for r in D2C.ROWS)
GB_G0 = ((714, 1400, 236),) + GBP[1:]                                   # D1 a2 (0xC4CDC/DE)
GB_D3 = ((714, 1414, 185),) + GBP[1:]                                   # D3 (a)/(b) row 0
GB_S13 = ((714, 1178, 1041), (1843, 1465, -4238), (2304, 988, -2643), (2707, 728, 2040), (4032, 1388, 1513),
          (6198, 2188, 0), (65535, 2188, 0))                            # D4 (a) GB-S13
for _rows in (GB_G0, GB_D3, GB_S13):                                    # each row-0/segment slope = the next knot
    for (x0, g0, s0), (x1, g1, s1) in zip(_rows[:-2], _rows[1:-1]):
        assert abs(g0 + ((x1 - x0) * s0 >> 12) - g1) <= 1, (_rows, x0)

# ---------------------------------------------------------------------------------------------------------------------
# candidates: firmware (lane switches) x fork
# ---------------------------------------------------------------------------------------------------------------------
FWD = dict(rows=GBP, thr=512, sgn=300, asym=False, d4=False, d5a=False, scl=15360, pcl=15360)
FW = {
    "V298": dict(),
    "D1c": dict(thr=1229, sgn=0, asym=True),
    "D1a": dict(thr=1229, sgn=1229),
    "D1cG0": dict(thr=1229, sgn=0, asym=True, rows=GB_G0),
    "D3a": dict(thr=1229, sgn=800, rows=GB_D3),
    "D3b": dict(thr=1229, sgn=800, rows=GB_D3, scl=19072, pcl=19072),
    "D4b": dict(d4=True),
    "D4a": dict(rows=GB_S13),
    "D4bS13": dict(d4=True, rows=GB_S13),
    "D5a": dict(thr=1229, sgn=1229, d5a=True),
}
EBP = (3.1, 8.0, 10.0, 11.75, 17.5, 26.9)
EV298 = (17.0, 15.5, 19.5, 17.0, 8.5, 4.5)
FKD = dict(cap_bp=(0.0, 99.0), cap_v=(1.2, 1.2), clip=EV298, inst=600.0, d600=0, hi=1200.0, hi_n=0, off=500.0,
           o1lead=0.06, take=0.0, k4=False, acc=0.0, plead=0.0, plead_sched=False, stair=True, lead3=0.0, lead5=0.0)
FK = {
    "V298": dict(),
    "D2a": dict(cap_v=(3.0, 3.0), clip=(27.2, 24.8, 31.2, 27.2, 8.5, 4.5), inst=1200.0, d600=8, o1lead=0.0,
                take=0.4, plead=0.10),
    "D2b": dict(cap_v=(3.0, 3.0), clip=(27.2, 24.8, 31.2, 27.2, 8.5, 4.5), inst=1200.0, d600=8, o1lead=0.0,
                take=0.4, acc=1500.0, plead_sched=True, stair=False),
    "D3a": dict(cap_bp=(0.0, 5.0, 8.0, 10.0), cap_v=(3.0, 3.0, 2.0, 1.2), clip=(30.0, 25.0, 19.5, 17.0, 8.5, 4.5),
                inst=2500.0, d600=0, hi=1200.0, hi_n=10, off=1000.0, k4=True, lead3=0.5),
    "D3b": dict(cap_bp=(0.0, 5.0, 8.0, 10.0), cap_v=(4.0, 4.0, 2.0, 1.2), clip=(40.0, 30.0, 19.5, 17.0, 8.5, 4.5),
                inst=2500.0, d600=0, hi=1200.0, hi_n=10, off=1000.0, k4=True, lead3=0.5),
    "D4": dict(inst=1e9, d600=5),
    "D5b": dict(cap_v=(2.5, 2.5), clip=(35.0, 32.0, 19.5, 17.0, 8.5, 4.5), inst=1200.0, d600=6, lead5=0.5),
    "D5a": dict(cap_v=(2.5, 2.5), clip=(35.0, 32.0, 19.5, 17.0, 8.5, 4.5), inst=1200.0, d600=6),
}
# id: (fw, fork, label)
CANDS = {
    "V298": ("V298", "V298", "flown baseline"),
    "D1c": ("D1c", "V298", "D1 (b) RECOMMENDED"),
    "D1a": ("D1a", "V298", "D1 (a) cal-only, NOT FOR FLIGHT"),
    "D1c+G0": ("D1cG0", "V298", "D1 a2 dose on D1c"),
    "D2a": ("V298", "D2a", "D2 (a) fork-only"),
    "D2b": ("V298", "D2b", "D2 (b) fork-only + 2nd order + lead"),
    "D3a": ("D3a", "D3a", "D3 (a) RECOMMENDED"),
    "D3b": ("D3b", "D3b", "D3 (b) rail raised, not recommended"),
    "D4b": ("D4b", "D4", "D4 (b) RECOMMENDED"),
    "D4a": ("D4a", "D4", "D4 (a) cal + in-place"),
    "D4b+S13": ("D4bS13", "D4", "D4 graft"),
    "D5b": ("D1a", "D5b", "D5 V299-b PRIMARY"),
    "D5a": ("D5a", "D5a", "D5 V299-a alternative"),
    # GRAFTS (scorer's own, not a designer's implementation): D1c's firmware under the other designers' forks
    "G:D1c+D3fork": ("D1c", "D3a", "graft: D1c firmware + D3 (a) fork"),
    "G:D1c+D5fork": ("D1c", "D5b", "graft: D1c firmware + D5 (b) fork"),
    "G:D1c+D2bfork": ("D1c", "D2b", "graft: D1c firmware + D2 (b) fork"),
}
CIDS = tuple(CANDS)


def fw_of(cid):
    return dict(FWD, **FW[CANDS[cid][0]])


def fk_of(cid):
    return dict(FKD, **FK[CANDS[cid][1]])


def mk_cand(cid):
    f = fw_of(cid)
    c = ST.Cand(cid, "S2", f["rows"], "fresh", 48, ki=40, icl=8192, arb=ST.ARB_A3, sgn_thr=f["sgn"], thr=f["thr"],
                ramp_in=328, ramp_out=66)
    for k in ("asym", "d4", "d5a", "scl", "pcl"):
        setattr(c, "s2_" + k, f[k])
    return c


# ---------------------------------------------------------------------------------------------------------------------
# THE LANE
# ---------------------------------------------------------------------------------------------------------------------
class S2Lane(ST.CandLane):
    """score_time.CandLane.tick's arithmetic for the V298 configuration family + every V299 firmware switch."""

    def __init__(self, cands, vw):
        super().__init__(cands, vw)
        B = self.B
        g = lambda k, d: np.array([getattr(c, "s2_" + k, d) for c in cands])  # noqa: E731
        self.asym = g("asym", False).astype(bool)
        self.d4 = g("d4", False).astype(bool)
        self.d5a = g("d5a", False).astype(bool)
        self.scl = g("scl", 15360).astype(np.int64)
        self.pcl = g("pcl", 15360).astype(np.int64)
        self.h = np.zeros(B, np.int64)               # D4b gp-0x6a32
        self.lp = np.zeros(B, np.int64)              # D5a gp-0x6c44
        self.sh = np.where((self.vw & 0xFFFF) <= 2880, 4, 6)
        self.capon = (self.vw & 0xFFFF) <= 1382
        self.log = {}

    def tick(self, a6a00, x69, xheld, abe, cmd, tq, ramp, act, req, pol=-1):
        c = ST.CAL
        B = self.B
        ramp = np.broadcast_to(np.asarray(ramp, np.int64), (B,))
        act = np.broadcast_to(np.asarray(act, np.int64), (B,))
        req = np.broadcast_to(np.asarray(req, np.int64), (B,))
        tq = np.broadcast_to(np.asarray(tq, np.int64), (B,))
        # ---- fb filter 0x28F4C..0x28FBE (x := gp-0x6a00; a 0, b 8192, C 65535)
        x = s16(a6a00)
        valid = (x >= -12000) & (x <= 12000)
        s_old = np.where(self.lane_ok == 1, self.s, 0)
        s_new = s32((0 * s_old >> 10) + (s32(x * 8192) >> 10))
        r26 = np.clip(s32(s_old + s_new), -65535, 65535)
        self.s = np.where(valid, s_new, self.s)
        r26 = np.where(valid, r26, 0)
        self.lane_ok = np.where(valid, 1, 2)
        run = valid & (ramp != 0) & (req == 1)                          # A2 + B2
        sp = s16(cmd)
        # ---- the cave: E, G walk, E'
        E = s32((sp << 2) - r26)                                        # 0xC4C00 shl 2 ; sub r26,r16
        prod = E * self.G
        self.wraps += int(np.count_nonzero(s32(prod) != prod))
        Ep = s32(prod) >> 8                                             # 0xC4C54 mul ; sar 8
        ab = s16(abe)
        abv = ((ab + 13000) & 0xFFFFFFFF) <= 26000
        op = np.where(abv, ab, 0)                                       # r26 = validated gp-0x6abe
        first = self.Eprev == SENT32                                    # Honda's first-tick sentinel gp-0x6cf8
        hs = s16(tq)                                                    # gp-0x4f60 (signed)
        # [D4b] h = h_prev + ((hs - h_prev) >> 5), h_prev := 0 on the sentinel tick ; st.h gp-0x6a32
        hprev = np.where(first, 0, self.h)
        hn = s32(hprev + (s32(hs - hprev) >> 5))
        atq = np.where(self.d4, np.abs(hn), np.minimum(np.abs(tq), 0xFFFF))
        c1 = atq > self.thr                                             # hard freeze
        c2v = (self.sgn > 0) & (np.abs(hs) > self.sgn) & ((hs ^ Ep) < 0)  # V298 / D3 opposing (hs)
        c2d = ((np.abs(hn) > self.sgn) & ((hn ^ Ep) < 0)
               & (((op ^ Ep) >= 0) | (((op + 10) & 0xFFFFFFFF) <= 20)))  # [D4b] on h, motion-gated
        c2 = np.where(self.d4, c2d, c2v)
        I_S = self.I8 >> 10
        t = np.where(Ep >= 0, I_S, -I_S)
        th6 = s16(a6a00)
        opnd = np.where(self.asym & ((th6 ^ Ep) < 0), 0, np.abs(th6))  # [D1c] asymmetric bound
        bound = s32((opnd << self.sh) + 1250)
        bound = np.where(self.capon & (bound > 4096), 4096, bound)
        c3 = t >= bound                                                 # A3
        c4 = (ramp & 0x8000) == 0
        hand = c1 | c2
        frz = hand | c3 | c4
        # [D5a] washout + friction comp on D's operand
        x16 = op << 16
        lpn = np.where(first, x16, self.lp + ((x16 - self.lp) >> 9))
        pf = np.clip(s32(Ep * 75) >> 12, -67, 67)
        op_d = np.where(self.d5a, op - (lpn >> 16) + pf, op)
        # ---- Honda's I 0x29D7A..0x29DC2 (freeze exit: e5 = 0)
        e5 = np.where(frz, 0, Ep >> 5)
        icl = ((self.icl & 0xFFFF) << 10) >> 3
        acc = (self.I8 >> 3) + (s32(e5 * self.ki) >> 3)
        self.wraps += int(np.count_nonzero(s32(acc) != acc))
        I = np.clip(s32(acc), -icl, icl)
        I8n = s32(I << 3)
        # ---- P, D, sum, fade, sum clamp
        P = np.clip(s32(Ep * self.kp) >> 8, -self.pcl, self.pcl)
        D = np.clip(s32(self.kd * op_d) >> 3, -self.DCL, self.DCL)
        S = s32((I >> 7) + P + D)
        i682f = np.minimum(np.abs(tq >> 5), 255)
        fB = lerp_vec(*c["fadeB"], i682f)
        f = ((self.fA1 * fB) & 0xFFFF) >> 8
        Sf = s32(S * f) >> 8
        Sc = np.where(Sf > self.scl, self.scl, np.where(Sf < -self.scl, -self.scl, s16(Sf)))
        Sc = np.where(run, Sc, 0)
        self.I8 = np.where(run, I8n, 0)
        self.Eprev = np.where(run, Ep, SENT32)
        self.h = np.where(run, s16(hn), self.h)
        self.lp = np.where(run, lpn, self.lp)
        self.n_run += run
        self.n_frz += run & frz
        # ---- output lag, sign-hold gate, forward gain, OCL
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
        self.log = dict(I=np.where(run, I >> 7, 0), frz=run & frz, hand=run & hand, a3=run & c3 & ~hand,
                        cI=np.where(run, np.abs(Ep >> 5), 0), run=run)
        return s16(T)


# ---------------------------------------------------------------------------------------------------------------------
# fork constants
# ---------------------------------------------------------------------------------------------------------------------
LEAD_B_BP = (3.1, 8.0, 10.0, 11.75, 14.0, 17.5, 22.0, 26.9)       # D2b tau(v)
LEAD_B_V = (0.05, 0.10, 0.15, 0.25, 0.32, 0.35, 0.22, 0.10)
GKN = np.array([1178.0, 1465.0, 760.0, 560.0, 1068.0, 2188.0])
TAU_L5 = 89.5 / GKN                                                 # D5 ANGLE_LEAD_V
REACT = json.loads((V299 / "D1-firmware-minimal" / "out" / "d1_r79.json").read_text())["reaction"]
NOISE_SD, NOISE_AC = float(REACT["res_std"]), float(REACT["ac1"])


def tau_d3(v, rows):
    """D3 K3: tau_D = 4.532 / c_P(v), c_P = 160 G 112 / 65536 * 0.16029 T/deg, G = the A16B table's walk."""
    G = ST.glut(rows)[int(round(v * 230.4))]
    return 4.532 / (160.0 * G * 112.0 / 65536.0 * 0.16029)


# ---------------------------------------------------------------------------------------------------------------------
# THE RUNNER
# ---------------------------------------------------------------------------------------------------------------------
def run(cols, dur, plan, th0, hand=None, drop_t=None, seed=11, lane_cls=S2Lane):
    """cols: dict(cid, member, v, x, nz).  plan(t_arr) -> (B,) deg (vectorised over per-column times).
    hand(t) -> None | (Kh, Bh, th_h, w_hand) (B,) arrays.  Returns recordings."""
    B = len(cols)
    cands = [mk_cand(c["cid"]) for c in cols]
    vv = np.array([c["v"] for c in cols], float)
    vw = np.round(vv * 3.6 * 64).astype(np.int64)
    lane = lane_cls(cands, vw)
    pl = ST.Plant([dict(member=c["member"], v=c["v"]) for c in cols])
    pl.th = np.asarray(th0, float).copy()
    rng = np.random.default_rng(seed)
    sidx = np.array([int(c.get("s", 1)) for c in cols])            # residual-noise seed (0 = no residual)
    NSEED = int(sidx.max()) + 1
    ckeys = sorted(set((c["member"], c["v"], str(c["x"]), c.get("s", 1)) for c in cols))
    cidx = np.array([ckeys.index((c["member"], c["v"], str(c["x"]), c.get("s", 1))) for c in cols])  # same draw for
    #                                                                                    every candidate of a condition
    fk = [fk_of(c["cid"]) for c in cols]
    F = lambda k: np.array([f[k] for f in fk], float)  # noqa: E731
    capv = np.array([np.interp(c["v"], f["cap_bp"], f["cap_v"]) for c, f in zip(cols, fk)])
    jerk = D2C.vm_dmax_jerk(vv)
    amax = D2C.vm_amax(vv)
    dmax0 = np.minimum(jerk, capv)
    emax0 = np.array([np.interp(c["v"], EBP, f["clip"]) for c, f in zip(cols, fk)])
    inst, d600, hi, hi_n, off = F("inst"), F("d600"), F("hi"), F("hi_n"), F("off")
    o1lead, take, acc = F("o1lead"), F("take"), F("acc") * 1e-4
    k4 = F("k4") > 0
    stair = F("stair") > 0
    plead = np.where(F("plead_sched") > 0, np.interp(vv, LEAD_B_BP, LEAD_B_V), F("plead"))
    sched = F("plead_sched") > 0
    lbound = np.minimum(4.0, np.degrees(D2C.STEER_FROM_CURV(0.6 / np.maximum(vv, 1.0) ** 2, vv)))
    g3 = F("lead3")
    tau3 = np.array([tau_d3(c["v"], fw_of(c["cid"])["rows"]) for c in cols])
    cap3 = capv * 100.0
    g5 = F("lead5") * np.interp(vv, EBP, TAU_L5)
    a30 = math.exp(-0.01 / 0.03)
    nT = int(round(dur * 1000))
    nF = nT // 10 + 1
    R = dict(th=np.zeros((nT, B), np.float32), om=np.zeros((nT, B), np.float32), T=np.zeros((nT, B), np.int16),
             word=np.zeros((nT, B), np.float32), I=np.zeros((nT, B), np.int16), frz=np.zeros((nT, B), bool),
             hand=np.zeros((nT, B), bool), a3=np.zeros((nT, B), bool), cI=np.zeros((nT, B), np.int32),
             run=np.zeros((nT, B), bool), hf=np.zeros((nT, B), np.float32),
             sp=np.zeros((nF, B), np.float32), plan=np.zeros((nF, B), np.float32), o1=np.zeros((nF, B), bool),
             clipb=np.zeros((nF, B), bool), rateb=np.zeros((nF, B), bool))
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    ramp = np.full(B, 0x8000, np.int64)
    act = req = 1
    wire, wom, wtq = [], [], []
    # fork state
    last = pl.th.copy()
    prev_rate = np.zeros(B)
    o1 = np.zeros(B, bool)
    c600 = np.zeros(B)
    chi = np.zeros(B)
    since = np.full(B, 1e9)
    hist = np.repeat(pl.th[None, :], 6, axis=0)
    slope_f = np.zeros(B)
    sdf = np.zeros(B)
    plan_z = plan(np.zeros(B) + plead * (~sched))
    sp_out = pl.th.copy()
    lat = True
    # word state
    a8 = math.exp(-2 * math.pi * 8.0 / 1000.0)
    al_f = np.zeros(B)
    om_prev = pl.om.copy()
    nz = np.zeros(NSEED)
    rng_w = np.random.default_rng(seed + 1000)
    for n in range(nT):
        t = n * 1e-3
        if drop_t is not None and t >= drop_t - 1e-9 and lat:
            lat = False
        if not lat:
            ramp = np.maximum(0, ramp - 66)
            act, req = 0, 0
        if n % 10 == 0:
            k = len(wire)
            if k >= 2:
                thm, omm, tqm = wire[k - 2] / 10.0, wom[k - 2], np.abs(wtq[k - 2]) / 1.024
            else:
                thm, omm, tqm = pl.th.copy(), pl.om.copy(), np.zeros(B)
            if lat:
                c600 = np.where(tqm > 600.0, c600 + 1, 0)
                chi = np.where(tqm > hi, chi + 1, 0)
                on = (tqm > inst) | ((d600 > 0) & (c600 >= d600)) | ((hi_n > 0) & (chi > hi_n))
                was = o1
                o1 = np.where(on, True, np.where(tqm <= off, False, o1))
                rel = was & ~o1
                since = np.where(rel, 0.0, since)
                last = np.where(rel, thm, last)
                prev_rate = np.where(rel, 0.0, prev_rate)
                hist = np.where(rel[None, :], thm[None, :], hist)
                slope_f = np.where(rel, 0.0, slope_f)
                if n % 50 == 0:
                    plan_z = plan(t + plead * (~sched))
                base = np.where(stair, plan_z, plan(np.full(B, t)))
                dl = np.clip(plan(t + plead) - plan(np.full(B, t)), -lbound, lbound)
                des = np.where(sched, base + dl, base)
                kk = np.where(take > 0, np.minimum(1.0, since / np.maximum(take, 1e-9)), 1.0)
                dm = np.where(k4 & (since < 0.5), np.minimum(dmax0, 1.2), dmax0) * kk
                dd = des - last
                rb = np.sign(dd) * np.sqrt(2.0 * acc * np.abs(dd))
                rcmd = np.clip(np.where(acc > 0, rb, dd), -dm, dm)
                rnew = np.where(acc > 0, np.clip(rcmd, prev_rate - acc, prev_rate + acc), rcmd)
                r1 = last + rnew
                r2 = np.clip(r1, -amax, amax)
                r3 = np.where(o1, thm + omm * o1lead, r2)
                hist = np.concatenate([hist[1:], r2[None, :]], 0)
                slope_f = a30 * slope_f + (1 - a30) * (hist[-1] - hist[0]) / 0.05
                r3l = np.where(o1, r3, r3 + g5 * slope_f)
                em = emax0 * kk
                r4 = np.clip(np.clip(r3, thm - em, thm + em), -400, 400)
                r4l = np.clip(np.clip(r3l, thm - em, thm + em), -400, 400)
                sdf = a30 * sdf + (1 - a30) * (r4 - last) / 0.01
                l3 = np.clip(g3 * tau3 * sdf, -g3 * tau3 * cap3, g3 * tau3 * cap3)
                l3 = np.where(o1 | (since < 0.3), 0.0, l3)
                sp_out = r4l + l3
                R["clipb"][n // 10] = np.abs(r4 - r3) > 1e-3
                R["rateb"][n // 10] = np.abs(r1 - des) > 1e-3
                prev_rate = r4 - last
                last = r4
                since = since + 0.01
            else:
                o1[:] = False
                sp_out = thm.copy()
                last = thm.copy()
            raw = s16(-np.floor(10.0 * sp_out + 0.5).astype(np.int64))
            cmd = np.clip(s32(-(raw << 2)), -0x4000, 0x4000)
            R["sp"][n // 10], R["o1"][n // 10] = sp_out, o1
            R["plan"][n // 10] = plan(np.full(B, t))
        # ---- the torque word gp-0x4f60
        al_f = a8 * al_f + (1 - a8) * (pl.om - om_prev) * 1000.0
        om_prev = pl.om.copy()
        if n % 10 == 0:
            nz = NOISE_AC * nz + math.sqrt(1 - NOISE_AC ** 2) * NOISE_SD * rng_w.normal(size=NSEED)
            nz[0] = 0.0
        word = -0.69 * al_f - 0.69 * pl.om - 163.0 * np.tanh(pl.om / 2.0) - 61.0 + nz[sidx]
        hh = hand(t) if hand is not None else None
        if hh is not None:
            word = word + hh[3]
        tqv = np.clip(np.round(word), -32767, 32767).astype(np.int64)
        # ---- sensors, lane
        om_m = pl.om / ST.FRAME.kappa(pl.th)
        g4f50 = s16(np.round(ST.ABE_PER * om_m + rng.normal(0.0, ST.N4F50, len(ckeys))[cidx]).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = s16(st >> 10)
        x69 = np.floor(10.0 * ST.FRAME.cinv(pl.th) + 0.5).astype(np.int64)
        T = lane.tick(held_th, x69, held_x, abe, cmd, tqv, ramp, act, req)
        if n % 10 == 4:
            q_now = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
            held_th = q_now
            held_x = np.clip(-((s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
            wire.append(q_now)
            wom.append(pl.om.copy())
            wtq.append(word.copy())
        u = -pl.delay(T.astype(float))
        if hh is None:
            pl.step(u)
        else:
            R["hf"][n] = hh[0] * (hh[2] - pl.th) - hh[1] * pl.om
            pl.step(u, hh[0], hh[1], hh[2])
        L = lane.log
        R["th"][n], R["om"][n], R["T"][n], R["word"][n] = pl.th, pl.om, T, word
        R["I"][n], R["frz"][n], R["hand"][n], R["a3"][n], R["cI"][n], R["run"][n] = (
            L["I"], L["frz"], L["hand"], L["a3"], L["cI"], L["run"])
    R["wraps"] = lane.wraps
    return R


# ---------------------------------------------------------------------------------------------------------------------
# metric helpers (vectorised over columns)
# ---------------------------------------------------------------------------------------------------------------------
def _bp(x, lo, hi, fs=1000.0):
    from scipy import signal
    sos = signal.butter(2, [lo, hi], "bandpass", fs=fs, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0)


def _runs(m, nmin):
    d = np.diff(np.r_[0, m.astype(np.int8), 0])
    a, b = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    k = (b - a) >= nmin
    return np.c_[a[k], b[k]]


def _mov(x, n):
    return np.convolve(x, np.ones(n) / n, "same")


def stall_surge_count(om100):
    """m4_episodes.stall_surge on a 100 Hz wheel-rate column (route-agnostic definition, unchanged)."""
    mbar = _mov(om100, 50)
    turn = np.abs(mbar) >= 10.0
    f3 = _mov(om100 * np.sign(mbar), 3)
    stall = turn & (f3 < 0.25 * np.abs(mbar))
    surge = np.flatnonzero(turn & (f3 > 0.75 * np.abs(mbar)))
    Rr = _runs(stall, 2)
    n = 0
    for a, b in Rr:
        j = np.searchsorted(surge, b)
        i = np.searchsorted(surge, a) - 1
        if j < len(surge) and surge[j] - b <= 25 and i >= 0 and a - surge[i] <= 25:
            n += 1
    return n


def dwell_jumps(th100, sp100, i0, i1):
    """DWELL-THEN-JUMP (m4_dwell form, 100 Hz): 0.1 s mean |rate| < 0.25 deg/s for >= 0.2 s while the setpoint moves
    >= 0.2 deg or |sp - th| >= 0.5 deg at the dwell's end; the JUMP = wheel travel in the 0.2 s after the dwell.
    Returns (n dwells, n with a jump >= 0.3 deg, max jump deg, stuck fraction)."""
    om = np.gradient(th100) * 100.0
    rs = _mov(np.abs(om), 10)
    m = np.zeros(len(th100), bool)
    m[i0:i1] = rs[i0:i1] < 0.25
    nd = nj = 0
    jmax = 0.0
    for a, b in _runs(m, 20):
        if abs(sp100[b - 1] - sp100[a]) >= 0.2 or abs(sp100[b - 1] - th100[b - 1]) >= 0.5:
            nd += 1
            jj = abs(th100[min(b + 20, len(th100) - 1)] - th100[b - 1])
            if jj >= 0.3:
                nj += 1
            jmax = max(jmax, jj)
    return nd, nj, jmax, float(m[i0:i1].mean()) if i1 > i0 else np.nan


def toggles(x):
    return int(np.count_nonzero(x[1:] != x[:-1]))


def common_metrics(R, j, i0, i1):
    """the identically-tabulated columns over [i0, i1) ticks."""
    th, om, T = R["th"][:, j].astype(float), R["om"][:, j].astype(float), R["T"][:, j].astype(float)
    w = slice(i0, i1)
    run_ = R["run"][w, j]
    cI = R["cI"][w, j].astype(float) * run_
    tot = cI.sum()
    kept = float((cI * ~R["frz"][w, j]).sum() / tot) if tot > 0 else np.nan
    hand_lost = float((cI * R["hand"][w, j]).sum() / tot) if tot > 0 else np.nan
    secs = (i1 - i0) / 1000.0
    om100 = om[::10]
    o1 = R["o1"][i0 // 10:i1 // 10, j]
    aw = np.abs(R["word"][w, j])
    return dict(w_p50=float(np.percentile(aw, 50)), w_p90=float(np.percentile(aw, 90)),
                w_p99=float(np.percentile(aw, 99)),
                tap_pk=float(np.abs(T[w]).max() / 8.0 / RAIL_TAP), kept=kept, hand_lost=hand_lost,
                hand_duty=float(R["hand"][w, j].mean()), hand_tog_s=toggles(R["hand"][w, j]) / secs,
                o1_eps=int(np.count_nonzero(o1[1:] & ~o1[:-1]) + (1 if (len(o1) and o1[0]) else 0)),
                o1_frac=float(o1.mean()) if len(o1) else 0.0,
                ss=stall_surge_count(om100[i0 // 10:i1 // 10]),
                r48=float(np.sqrt(np.mean(_bp(om, 4.0, 8.0)[w] ** 2))),
                r163=float(np.sqrt(np.mean(_bp(om, 1.6, 3.0)[w] ** 2))))


# ---------------------------------------------------------------------------------------------------------------------
# MANOEUVRES
# ---------------------------------------------------------------------------------------------------------------------
_AT = {3.0: 90.0, 5.0: 50.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0, 30.0: 2.5}


def A_turn(v):
    k = sorted(_AT)
    return float(np.exp(np.interp(v, k, [np.log(_AT[x]) for x in k])))


def plan_rate(v):
    """the planner's demand rate: clip_curvature jerk 5 m/s^3 through the VM, capped at r79's planner p99 (320)."""
    return float(min(320.0, np.degrees(D2C.STEER_FROM_CURV(5.0 / v ** 2, v))))


SEEDS = (1, 2, 3)


def cols_for(speeds, xs, seeds=SEEDS):
    return [dict(cid=c, member=m, v=v, x=x, s=s)
            for v in speeds for x in xs for m in MEMBERS for s in seeds for c in CIDS]


def grp_TI():
    cols = cols_for((3.0, 8.0), ("ti",), seeds=(0,) + SEEDS)
    B = len(cols)
    A = 60.0
    Rt = np.array([plan_rate(c["v"]) for c in cols])
    t0 = 0.5
    ta = t0 + A / Rt
    tu = ta + 2.5

    def plan(t):
        return np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A)
    dur = 5.6
    R = run(cols, dur, plan, np.zeros(B))
    out = []
    tt = np.arange(R["th"].shape[0]) * 1e-3
    PL = plan(np.repeat(tt[:, None], B, 1))
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        om = R["om"][:, j].astype(float)
        i0, ia, iu = int(t0 * 1000), int(ta[j] * 1000), int(tu[j] * 1000)
        pl_ = PL[:, j]
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
        t90 = hit[0] / 1000.0 if len(hit) else np.nan
        outside = np.flatnonzero(np.abs(th[ia:iu] - A) > 2.0)
        settle = (outside[-1] + 1) / 1000.0 if len(outside) else 0.0
        if len(outside) and outside[-1] >= iu - ia - 1:
            settle = np.nan
        hit2 = np.flatnonzero(th[iu:] <= 0.1 * A)
        th100, sp100 = th[::10], R["sp"][:len(th[::10]), j]
        nd, nj, jmax, stuck = dwell_jumps(th100, sp100, ia // 10, iu // 10)
        spa = np.flatnonzero(sp100[i0 // 10:iu // 10] >= 0.99 * A)          # the SENT setpoint arrives
        cov_sp = float(th100[i0 // 10 + spa[0]] / A) if len(spa) else np.nan
        t_spa = spa[0] / 100.0 if len(spa) else np.nan
        d = dict(cov_sp=cov_sp, t_spa=t_spa, cid=c["cid"], member=c["member"], v=c["v"], x=c["x"], s=c["s"],
                 cover05=float(th[i0 + 500] / A), t90=t90, wpk=float(om[i0:iu].max()),
                 ovs=float(th[i0:iu].max() - A), settle=settle, maxlag=float((pl_ - th)[i0:iu].max()),
                 t90_out=hit2[0] / 1000.0 if len(hit2) else np.nan, under=float(-th[iu:].min()),
                 dj=nj, dwell=nd, jmax=jmax)
        d.update(common_metrics(R, j, i0, len(th)))
        out.append(d)
    return out


def grp_C2():
    cols = cols_for((15.0, 25.0), ("fast", "slow"))
    B = len(cols)
    A = 2.0
    tr = np.array([0.25 if c["x"] == "fast" else 1.5 for c in cols])
    t0, tu = 0.6, 3.6

    def plan(t):
        return A * (np.clip((t - t0) / tr, 0, 1) - np.clip((t - tu) / tr, 0, 1))
    R = run(cols, 6.0, plan, np.zeros(B))
    tt = np.arange(R["th"].shape[0]) * 1e-3
    PL = plan(np.repeat(tt[:, None], B, 1))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        i0, ie, iu = int(t0 * 1000), int((t0 + tr[j]) * 1000), int(tu * 1000)
        e = PL[:, j] - th
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
        outside = np.flatnonzero(np.abs(th[ie:iu] - A) > 0.2)
        settle = (outside[-1] + 1) / 1000.0 if len(outside) else 0.0
        if len(outside) and outside[-1] >= iu - ie - 1:
            settle = np.nan
        th100, sp100 = th[::10], R["sp"][:len(th[::10]), j]
        nd, nj, jmax, stuck = dwell_jumps(th100, sp100, i0 // 10, len(th100) - 1)
        d = dict(cid=c["cid"], member=c["member"], v=c["v"], x=c["x"], s=c["s"], t90=hit[0] / 1000.0 if len(hit) else np.nan,
                 g05=float(th[ie + 500] / A), ovs=float(th[i0:iu].max() - A), settle=settle,
                 maxlag=float(np.abs(e[i0:]).max()), erms=float(np.sqrt(np.mean(e[i0:] ** 2))),
                 dwell=nd, dj=nj, jmax=jmax, stuck=stuck)
        d.update(common_metrics(R, j, i0, len(th)))
        out.append(d)
    return out


def _hand_grp(speeds, xs, W, frac, tg, thold, dur):
    cols = cols_for(speeds, xs)
    B = len(cols)
    Ah = np.array([0.5 * A_turn(c["v"]) for c in cols])
    sg = np.sign(Ah)
    dirn = np.array([{"c": -1.0, "o": 1.0, "ov": -1.0}[c["x"]] for c in cols])
    thh_end = Ah + dirn * frac * Ah
    trel = tg + 0.3 + thold
    Kh = np.full(B, 2000.0)
    Bh = np.full(B, 30.0)

    def hand(t):
        if tg <= t < trel:
            fr = min(1.0, (t - tg) / 0.3)
            return Kh, Bh, Ah + fr * (thh_end - Ah), dirn * sg * W * fr
        if trel <= t < trel + 0.03:
            return np.zeros(B), np.zeros(B), Ah, dirn * sg * W * (1 - (t - trel) / 0.03)
        return None

    def plan(t):
        return Ah * np.ones_like(t)
    R = run(cols, dur, plan, Ah.copy(), hand=hand)
    return cols, R, Ah, sg, dirn, trel


def grp_LH():
    tg, thold = 3.0, 2.0
    cols, R, Ah, sg, dirn, trel = _hand_grp((5.0, 15.0), ("c", "o"), 400.0, 0.3, tg, thold, 7.8)
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        ig, ih, ir = int(tg * 1000), int((tg + 0.3) * 1000), int(trel * 1000)
        I = R["I"][:, j].astype(float)
        after = (th[ir:ir + 2000] - Ah[j]) * sg[j] * -dirn[j]          # + = swinging past the setpoint, away from
        back = np.flatnonzero(np.abs(th[ir:ir + 2000] - Ah[j]) <= 1.0)  # the side the hand held the wheel on
        d = dict(cid=c["cid"], member=c["member"], v=c["v"], x=c["x"], s=c["s"],
                 lurch=float(max(after.max(), 0.0)), droop=float(abs(th[ir + 1500] - Ah[j])),
                 t_back=back[0] / 1000.0 if len(back) else np.nan,
                 dI_T=float((I[ir - 1] - I[ig - 1]) * 5346 / 32768 * sg[j] * -1.0),
                 frz_hold=float(R["frz"][ih:ir, j].mean()), hand_hold=float(R["hand"][ih:ir, j].mean()),
                 tap_hold=float(np.abs(R["T"][ih:ir, j]).max() / 8.0 / RAIL_TAP),
                 hf_hold=float(np.abs(R["hf"][ir - 500:ir, j]).mean()))
        d.update(common_metrics(R, j, ig, len(th)))
        out.append(d)
    return out


def grp_OV():
    tg, thold = 3.0, 1.5
    cols, R, Ah, sg, dirn, trel = _hand_grp((5.0, 15.0), ("ov",), 1500.0, 1.0, tg, thold, 7.5)
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        T = np.abs(R["T"][:, j].astype(float))
        ig, ir = int(tg * 1000), int(trel * 1000)
        Tpre = T[ig - 300:ig].mean()
        o1 = R["o1"][ig // 10:ir // 10, j]
        t_o1 = (np.flatnonzero(o1)[0] * 10) if o1.any() else np.nan
        low = T[ig:ir] <= 0.5 * max(Tpre, 1.0)
        t_y = np.nan
        for a, b in _runs(low, 100):
            t_y = float(a)
            break
        hit = np.flatnonzero(sg[j] * th[ir:] >= 0.9 * abs(Ah[j]))
        d = dict(cid=c["cid"], member=c["member"], v=c["v"], x=c["x"], s=c["s"], t_o1_ms=t_o1, t_yield_ms=t_y,
                 hf_hold=float(np.abs(R["hf"][ir - 500:ir, j]).mean()), Tres=float(T[ir - 500:ir].mean()),
                 Tpre=float(Tpre), ov_tap=float(T[ig:ir].max() / 8.0 / RAIL_TAP), rel_t90=hit[0] / 1000.0 if len(hit) else np.nan,
                 rel_ovs=float((sg[j] * th[ir:]).max() - abs(Ah[j])),
                 rel_tap=float(T[ir:].max() / 8.0 / RAIL_TAP))
        d.update(common_metrics(R, j, ig, len(th)))
        out.append(d)
    return out


def grp_RD():
    cols = cols_for((3.0, 8.0), ("rd",), seeds=(1,))
    B = len(cols)
    Ah = np.array([0.5 * A_turn(c["v"]) for c in cols])
    td = 3.0
    R = run(cols, 5.0, lambda t: Ah * np.ones_like(t), Ah.copy(), drop_t=td)
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        T = np.abs(R["T"][:, j].astype(float))
        i = int(td * 1000)
        d = dict(cid=c["cid"], member=c["member"], v=c["v"], x=c["x"], s=c["s"], Tpre=float(T[i - 100:i].mean()),
                 T150=float(T[i + 150]), T50=float(T[i + 50]), wpk=float(np.abs(R["om"][i:i + 1000, j]).max()),
                 dth1=float(abs(th[i + 1000] - th[i])))
        d.update(common_metrics(R, j, int(1.5 * 1000), i))
        out.append(d)
    return out


GROUPS = {"TI": grp_TI, "C2": grp_C2, "LH": grp_LH, "OV": grp_OV, "RD": grp_RD}


def _job(g):
    t0 = time.perf_counter()
    rows = GROUPS[g]()
    return g, rows, time.perf_counter() - t0


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    return o


# ---------------------------------------------------------------------------------------------------------------------
# CONTROLS: S2Lane against the common scorer's lane and the designers' own lanes, bit for bit
# ---------------------------------------------------------------------------------------------------------------------
CTL_SPEEDS = (3.1, 11.9, 17.0, 26.9)
CTL_SCN = (("ov_lt1000", 6.5), ("hard", 5.0))


def _ctl_lane(which):
    """-> (lane class, [cand objects]) for a control run, each in its own process."""
    if which == "S2":
        return S2Lane, [mk_cand(k) for k in ("V298", "D1c", "D4b", "D4a")]
    if which == "CandLane":
        return ST.CandLane, [D2C.v298_cand(ST)]
    if which == "D1Lane":
        _s = importlib.util.spec_from_file_location("d1_time_s2", V299 / "D1-firmware-minimal" / "d1_time.py")
        M = importlib.util.module_from_spec(_s)
        sys.modules["d1_time_s2"] = M
        _s.loader.exec_module(M)
        c = M.mk("D1c", 1229, 0, True, M.ST.ARB_A3)
        return M.D1Lane, [c]
    if which == "D4Lane":
        _s = importlib.util.spec_from_file_location("d4_sim_s2", V299 / "D4-smoothness-first" / "d4_sim.py")
        M = importlib.util.module_from_spec(_s)
        sys.modules["d4_sim_s2"] = M
        _s.loader.exec_module(M)
        NS.params = _params                                # d4_sim re-binds nl_sim.params; nominal passes through
        d4b = next(c for c in M.CANDS if c.id == "b8:lp5H512")
        d4a = next(c for c in M.CANDS if c.id == "a:GBS13")
        d4b.id_s2, d4a.id_s2 = "D4b", "D4a"
        return M.D4Lane, [d4b, d4a]
    raise KeyError(which)


def _ctl_job(which):
    t0 = time.perf_counter()
    lane, cands = _ctl_lane(which)
    out = {}
    for scn_name, dur in CTL_SCN:
        cols = [dict(cand=c, member="nominal", v=v) for v in CTL_SPEEDS for c in cands]
        scn, _ = ST.scenario(scn_name, cols)
        scn.dur = dur
        ST.CandLane = lane
        r = ST.run(cols, scn, noise=0.0)       # sensor noise off: the per-column draw depends on the column count
        for j, c in enumerate(cols):
            cid = getattr(c["cand"], "id_s2", None) or {"C3B-P": "V298"}.get(c["cand"].id, c["cand"].id)
            out[(scn_name, cid, c["v"])] = (r["T"][:, j].astype(int), r["th"][:, j].astype(float))
    return which, out, time.perf_counter() - t0


def control():
    t0 = time.perf_counter()
    import rb_table as TB
    lines = ["C0 rb_table.GB_P == d2_common.ROWS (read from the V298 image, sha 177abf04): %s"
             % (tuple(tuple(r) for r in TB.GB_P) == GBP)]
    with Pool(4) as p:
        res = dict((w, (o, wt)) for w, o, wt in p.map(_ctl_job, ["S2", "CandLane", "D1Lane", "D4Lane"]))
    S2o = res["S2"][0]
    ok = True
    for ref, cids in (("CandLane", ("V298",)), ("D1Lane", ("D1c",)), ("D4Lane", ("D4b", "D4a"))):
        R = res[ref][0]
        for (scn, cid, v), (T, th) in sorted(R.items(), key=lambda kv: str(kv[0])):
            if cid not in cids:
                cid = {"V298": "V298"}.get(cid, cid)
            Ta, tha = S2o[(scn, cid, v)]
            dT, dth = int(np.abs(Ta - T).max()), float(np.abs(tha - th).max())
            ok &= (dT == 0 and dth == 0.0)
            lines.append(f"S2Lane({cid}) vs {ref} [{scn} @ {v} m/s]: max|dT| {dT}  max|dth| {dth:.1e}")
    # negative control: D1c's S2 columns against CandLane(V298) must DIFFER on the hand scenario
    neg = [int(np.abs(S2o[("ov_lt1000", "D1c", v)][0] - res["CandLane"][0][("ov_lt1000", "V298", v)][0]).max())
           for v in CTL_SPEEDS]
    lines.append(f"NEGATIVE CONTROL S2Lane(D1c) vs CandLane(V298) [ov_lt1000]: max|dT| per speed {neg} (must be > 0)")
    lines.append(f"ALL CONTROLS PASS: {ok} ; negative control differs: {all(x > 0 for x in neg)}")
    lines.append("job walls: " + ", ".join(f"{k} {v[1]:.1f} s" for k, v in res.items()))
    lines.append(f"wall {time.perf_counter() - t0:.1f} s")
    txt = "\n".join(lines)
    print(txt)
    (HERE / "s2_control.txt").write_text(txt + "\n", encoding="utf-8")


def main_run(groups):
    T0 = time.perf_counter()
    with Pool(len(groups)) as p:
        res = p.map(_job, groups)
    allr = {}
    walls = {}
    for g, rows, wt in res:
        allr[g] = [_clean(r) for r in rows]
        walls[g] = wt
    path = OUT / "s2_results.json"                                 # _scratch/v299_S2 (0.8 MB, regenerable)
    prev = json.loads(path.read_text()) if path.exists() else {"rows": {}, "walls": {}}
    prev["rows"].update(allr)
    prev["walls"].update(walls)
    prev["wall_total_last"] = time.perf_counter() - T0
    path.write_text(json.dumps(prev, indent=0), encoding="utf-8")
    print("walls:", {k: round(v, 1) for k, v in walls.items()}, "total %.1f s" % (time.perf_counter() - T0))


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "run"
    if a == "control":
        control()
    elif a == "run":
        gs = sys.argv[2].split(",") if len(sys.argv) > 2 else list(GROUPS)
        main_run(gs)
