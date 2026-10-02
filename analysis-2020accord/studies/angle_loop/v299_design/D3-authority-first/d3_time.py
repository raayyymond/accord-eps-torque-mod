# -*- coding: utf-8 -*-
r"""d3_time.py -- D3 (authority-first) TIME-DOMAIN scoring.  ANALYSIS ONLY.

ENGINE = the kit's panel-2 COMMON time scorer (panel2/score_time.py) UNCHANGED: CandLane (the V298 lane, integer-exact,
H1-validated against the cave bytes), the Karnopp plant family (nl_sim.params, 10 kHz sub-steps, 2 ms transport), the
sensors (gp-0x6a00 slot-4 hold, the 1 kHz gp-0x6abe EMA), and its metrics().  Additions, each stated:
  * MEMBER 'meas' = 'nominal' with ROUTE 79's measured Coulomb friction (drive_read.txt friction(): Fc 156 / 79 / 74 /
    86 / 94 / 55 T at 0-5 / 5-8 / 8-12.5 / 12.5-18 / 18-25 / >25 m/s; Fs = 1.25 Fc) -- single method, BELIEF on shape.
  * RQLane = CandLane + D3's RATE-QUALIFIED HAND FREEZE (a candidate flag 'RQ' in Cand.note): when the fresh rate says
    the wheel is moving TOWARD the setpoint faster than |gp-0x6abe| >= 32 counts (6.8 deg/s motor frame), the two hand
    freezes (|tq| > thr, opposing |tq| > sgn) are skipped; the A3 bound and the ramp freeze are unchanged.  Integer
    mirror of the D3 cave bytes (d3_cave.py asserts the same predicate).
  * PART B: a FORK MODEL (V298's Dom 2712e1336 _update_angle: rate limiter min(cap, VM jerk), error clip, O1 relay with
    the release reset; + D3's O1 persistence and D-cancel lead) driving the same lane/plant, and the REACTION TWIST on
    the torque word: gp-0x4f60 = -0.55 alpha - 0.3 omega - 150 tanh(omega/5) (route 79: M3's signed fit -0.69 alpha -
    0.69 omega - 163 sgn(omega), R2 0.31; d3_r79's |twist| = 209 + 0.40 |alpha|).  Model BELIEF; sign EVIDENCE.

usage: python d3_time.py A   -> PART A: goal-criteria subset (st, s10_05, ov_lt511, ov_lt1000, ov_fm2400, cs, hard),
                                score_time's 'ff' fork, members nominal / b_lo*J_hi (+ meas for s10_05, ov_lt1000);
                                16 jobs = one round on 16 processes (13 s)
       python d3_time.py B   -> PART B: hands-off turns through the fork model (90/60/30 deg at 3/5/8 m/s at a 300 deg/s
                                planner peak, + 450 deg/s; 10 deg at 17.5 and 4 deg at 26.9 m/s), firmware x fork
                                configurations; members nominal / meas / b_lo*J_hi (8 s)
CANDIDATES: V298 (the image); D3a = implementation (a): G x1.2 @3.1 tapering to x1.0 @8 m/s + hand-freeze thresholds
1229/800; D3a0 = thresholds only; D3b = D3a + SCL/PCL 19072; RQ, X8192 = rejected variants (kept for the record).
outputs _scratch/angle_loop/v299-D3/time_{A,B}.{txt,json}
"""
from __future__ import annotations

import contextlib
import io
import json
import math
import os
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(AL / "panel2"))
import d3_common as D  # noqa: E402

_ST = None
RQ_ABE = 32                                                   # |gp-0x6abe| >= 32 <=> (abe >> 5) not in {-1, 0}


def ST():
    global _ST
    if _ST is None:
        with contextlib.redirect_stdout(io.StringIO()):
            import score_time as S
        NS = S.NS
        _orig = NS.params

        def params(member, v):
            if member == "meas":
                J, b, k, sat, Fc, Fs, tau = _orig("nominal", v)
                Fc = float(np.interp(v, [2.5, 6.5, 10.25, 15.25, 21.5, 28.0], [156, 79, 74, 86, 94, 55]))
                return J, b, k, sat, Fc, 1.25 * Fc, tau
            return _orig(member, v)
        NS.params = params

        class RQLane(S.CandLane):
            """CandLane + the D3 rate-qualified hand freeze (columns whose Cand.note contains 'RQ')."""

            def __init__(self, cands, vw):
                super().__init__(cands, vw)
                self.rq = np.array(["RQ" in c.note for c in cands])

            def cave_stage(self, sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW):
                out = super().cave_stage(sp, r26, ramp, a6a00, abe, tq, I8, Eprev, bxC, bxW)
                atq_ = np.minimum(np.abs(tq), 0xFFFF)
                hs_ = S.s16(tq)
                self._hand = (atq_ > self.thr) | ((self.sgn > 0) & (np.abs(hs_) > self.sgn) & ((hs_ ^ out["Ep"]) < 0))
                if not self.rq.any():
                    return out
                Ep = out["Ep"]
                ab = S.s16(abe)
                fast = ((((ab >> 5) + 1) & 0xFFFFFFFF) > 1)       # (abe >> 5) + 1 unsigned > 1 <=> |abe| >= 32 (approx)
                toward = fast & ((ab ^ Ep) < 0)                    # abe = -4.712 w: sign(w) == sign(E') (moving to sp)
                # the A3 / ramp part of the parent's ordered decision (c3 | c4), recomputed verbatim
                I_S = I8 >> 10
                t = np.where(Ep >= 0, I_S, -I_S)
                th6 = S.s16(a6a00)
                sh = np.where((self.arb_sh_lo >= 0) & ((self.vw & 0xFFFF) <= self.arb_vth), self.arb_sh_lo, self.arb_sh)
                bound = S.s32((np.abs(th6) << np.where(self.arb_on, sh, 0)) + self.arb_B)
                capon = (self.arb_vcap >= 0) & ((self.vw & 0xFFFF) <= self.arb_vcap)
                bound = np.where(capon & (bound > self.arb_cap), self.arb_cap, bound)
                c3 = self.arb_on & (t >= bound)
                c4 = self.ramp_frz & ((np.asarray(ramp, np.int64) & 0x8000) == 0)
                out["frz"] = np.where(self.rq & toward, c3 | c4, out["frz"])
                return out
        S.CandLane = RQLane
        _ST = S
    return _ST


A3 = (6, 4, 2880, 1250, 1382, 4096)


def cands():
    S = ST()
    base = S.Cand("V298", "E2", D.GB_P, "fresh", kd=48, kp=112, ki=40, icl=8192, thr=512, sgn_thr=300, arb=A3,
                  ramp_frz=True, ramp_in=328, ramp_out=66, note="V298 image cells (dir-2 ramps; fadeB2 == fadeB)")
    G12 = D.scaled_rows(1.2, mult_8=1.0)          # the D3 (a) table: x1.2 at 3.1 m/s tapering to x1.0 at 8.0 m/s
    return {
        "V298": base,
        # (a): G x1.2 <= 8 m/s + hand-freeze thresholds 512 -> 1229, 300 -> 800 (cave immediates; no new code)
        "D3a": replace(base, id="D3a", rows=G12, thr=1229, sgn_thr=800, note="in-place: G1.2 + T1229/800"),
        "D3a0": replace(base, id="D3a0", thr=1229, sgn_thr=800, note="attribution: thresholds alone (G1.0)"),
        # (b): (a) + SCL 19072 (set per job)
        "D3b": replace(base, id="D3b", rows=G12, thr=1229, sgn_thr=800, note="(a) + SCL 19072"),
        # REJECTED variants, kept for the record
        "RQ": replace(base, id="RQ", rows=G12, note="RQ"),
        "X8192": replace(base, id="X8192", rows=G12, thr=1229, sgn_thr=800, arb=A3[:5] + (8192,),
                         note="rejected: raised thresholds + A3 cap 8192"),
    }


SCL_OF = {"V298": 15360, "D3a": 15360, "D3a0": 15360, "D3b": 19072, "X8192": 15360, "RQ": 15360}
SPEEDS_A = (3.0, 5.0, 8.0, 10.0, 11.9, 17.0, 26.9)
SCN_A = ("st", "s10_05", "ov_lt511", "ov_lt1000", "ov_fm2400", "cs", "hard")
MEMB_A = ("nominal", "b_lo*J_hi", "meas")


def jobA(args):
    scn, member, cids = args
    S = ST()
    CC = cands()
    assert len(set(SCL_OF[c] for c in cids)) == 1
    S.CAL["SCL"] = SCL_OF[cids[0]]
    cols = [dict(cand=CC[c], member=member, v=v) for c in cids for v in SPEEDS_A]
    sc, meta = S.scenario(scn, cols)
    r = S.run(cols, sc, frame="vgr")
    m = S.metrics(scn, meta, r, cols)
    out = []
    nv = len(SPEEDS_A)
    for i, c in enumerate(cids):
        out.append((scn, member, c, {k: np.asarray(x, float)[i * nv:(i + 1) * nv].tolist() for k, x in m.items()
                                     if k not in ("XY", "holds") and np.ndim(x) > 0 and len(x) == len(cols)}))
    return out


# =====================================================================================================================
# PART B -- the fork model + the twist
# =====================================================================================================================
CAP_BP, CAP_D3 = [0.0, 5.0, 8.0, 10.0], [300.0, 300.0, 200.0, 120.0]
EMAX_D3 = [30.0, 25.0, 19.5, 17.0, 8.5, 4.5]
FORKS = {
    "F298": dict(cap_v=[120.0] * 4, emax_v=D.EMAX_V298, o1=(600, 500, 0, 1e9), lead=0.0),
    "FD3": dict(cap_v=CAP_D3, emax_v=EMAX_D3, o1=(1200, 1000, 10, 2500), lead=1.0),
    "FD3-half": dict(cap_v=CAP_D3, emax_v=EMAX_D3, o1=(1200, 1000, 10, 2500), lead=0.5),
    "FD3-nolead": dict(cap_v=CAP_D3, emax_v=EMAX_D3, o1=(1200, 1000, 10, 2500), lead=0.0),
    "FD3-noO1fix": dict(cap_v=CAP_D3, emax_v=EMAX_D3, o1=(600, 500, 0, 1e9), lead=0.5),
    "FD3-400": dict(cap_v=[450.0, 450.0, 200.0, 120.0], emax_v=EMAX_D3, o1=(1200, 1000, 10, 2500), lead=0.5),
    # (b)'s fork: cap 400 deg/s and clip 40 / 30 deg at 3.1 / 8 m/s so P can use the raised SCL/PCL
    "FD3-b": dict(cap_v=[400.0, 400.0, 200.0, 120.0], emax_v=[40.0, 30.0, 19.5, 17.0, 8.5, 4.5],
                  o1=(1200, 1000, 10, 2500), lead=0.5),
    # TESTED, NOT ADOPTED: the raised cap only AWAY from centre; toward centre (unwind) 180 deg/s at <= 5 m/s
    "FD3-asym": dict(cap_v=CAP_D3, cap_dn=[180.0, 180.0, 150.0, 120.0], emax_v=EMAX_D3, o1=(1200, 1000, 10, 2500),
                     lead=0.5),
}
TURNS = ((3.0, 90.0, 300.0), (5.0, 60.0, 300.0), (8.0, 30.0, 300.0), (17.5, 10.0, 20.0), (26.9, 4.0, 8.0))
TURNS_FAST = ((3.0, 90.0, 450.0), (5.0, 60.0, 450.0))
CONFIGS = (("V298", "F298", TURNS), ("V298", "FD3-half", TURNS), ("D3a0", "FD3-half", TURNS), ("D3a", "F298", TURNS),
           ("D3a", "FD3-noO1fix", TURNS), ("D3a", "FD3-nolead", TURNS), ("D3a", "FD3-half", TURNS),
           ("D3a", "FD3", TURNS), ("RQ", "FD3-half", TURNS[:3]), ("X8192", "FD3-half", TURNS[:3]),
           ("D3a", "FD3-400", TURNS_FAST), ("D3b", "FD3-400", TURNS_FAST), ("D3a", "FD3-asym", TURNS),
           ("V298", "FD3-asym", TURNS[:3]), ("D3b", "FD3-b", TURNS[:3] + TURNS_FAST),
           ("D3a", "FD3-b", TURNS[:3] + TURNS_FAST))
MEMB_B = ("nominal", "meas", "b_lo*J_hi")
DUR_B = 4.5
T_IN = 0.3


def plan_of(v, A, Rpk):
    Tr = A * math.pi / (2.0 * Rpk)                           # raised cosine: peak rate A pi / (2 Tr)

    def f(t):
        t = np.asarray(t, float)
        up = np.clip((t - T_IN) / Tr, 0, 1)
        dn = np.clip((t - (T_IN + Tr + 1.6)) / Tr, 0, 1)
        return A * 0.5 * (1 - np.cos(np.pi * up)) * (1 - 0.5 * (1 - np.cos(np.pi * dn)))
    return f, Tr


def run_fork(cols, fork_by_col):
    """score_time.run with the fork model in place of its 'ff' fork.  cols: dict(cand, member, v, A, R)."""
    S = ST()
    B = len(cols)
    cands_ = [c["cand"] for c in cols]
    vw = np.array([int(round(c["v"] * 3.6 * 64)) for c in cols], np.int64)
    lane = S.CandLane(cands_, vw)
    pl = S.Plant(cols)
    rng = np.random.default_rng(11)
    plans = [plan_of(c["v"], c["A"], c["R"])[0] for c in cols]
    FK = [FORKS[f] for f in fork_by_col]
    cap = np.array([min(float(np.interp(c["v"], CAP_BP, f["cap_v"])), D.vm_rate(c["v"])) for c, f in zip(cols, FK)])
    cap_dn = np.array([min(float(np.interp(c["v"], CAP_BP, f.get("cap_dn", f["cap_v"]))), D.vm_rate(c["v"]))
                       for c, f in zip(cols, FK)])
    emax = np.array([float(np.interp(c["v"], D.EMAX_BP, f["emax_v"])) for c, f in zip(cols, FK)])
    on_t = np.array([f["o1"][0] for f in FK], float)
    off_t = np.array([f["o1"][1] for f in FK], float)
    pers = np.array([f["o1"][2] for f in FK], int)
    inst = np.array([f["o1"][3] for f in FK], float)
    lead_g = np.array([float(f["lead"]) for f in FK])
    tau_ff = lead_g * np.array([D.cD_T_per_dps() / D.cP_T_per_deg(c["cand"].rows, c["v"]) for c in cols])
    lead_max = tau_ff * cap
    nT = int(DUR_B * 1000)
    th_r = np.zeros((nT, B), np.float32)
    om_r = np.zeros((nT, B), np.float32)
    T_r = np.zeros((nT, B), np.int16)
    o1_r = np.zeros((nT, B), bool)
    frz_r = np.zeros((nT, B), bool)
    hand_r = np.zeros((nT, B), bool)
    tq_r = np.zeros((nT, B), np.float32)
    ap_r = np.zeros((nT, B), np.float32)
    apply = pl.th.copy()
    wire = []
    held_th = np.floor(10 * pl.th + 0.5).astype(np.int64)
    held_x = np.zeros(B, np.int64)
    st = np.zeros(B, np.int64)
    cmd = 4 * held_th
    ramp = np.full(B, 0x8000, np.int64)
    last = pl.th.copy()
    rate_f = np.zeros(B)
    o1 = np.zeros(B, bool)
    above = np.zeros(B, int)
    om_prev = np.zeros(B)
    a_f = np.zeros(B)
    tqv = np.zeros(B)
    for n in range(nT):
        t = n * 1e-3
        if n % 10 == 0:
            k6 = max(len(wire) - 6, 0)
            th_meas = wire[k6] / 10.0 if wire else pl.th.copy()
            k7 = max(len(wire) - 7, 0)
            om_meas = (wire[k6] - wire[k7]) / 10.0 / 0.01 if len(wire) > 7 else np.zeros(B)
            cs_tq = np.abs(tqv) / 1.024                             # carState steeringTorque (raw wire units)
            above = np.where(cs_tq > on_t, above + 1, 0)
            was = o1.copy()
            o1 = np.where(o1, cs_tq > off_t, (above > pers) | (cs_tq > inst))
            last = np.where(was & ~o1, th_meas, last)               # the release reset (V298 behaviour, kept)
            plan = np.array([p(t) for p in plans]).ravel()
            apply = np.clip(plan, last - cap * 0.01, last + cap * 0.01)
            toward0 = np.abs(apply) < np.abs(last)                  # unwinding: the limiter's step reduces |angle|
            apply = np.where(toward0, np.clip(apply, last - cap_dn * 0.01, last + cap_dn * 0.01), apply)
            apply = np.where(o1, th_meas + om_meas * 0.06, apply)
            apply = np.clip(apply, th_meas - emax, th_meas + emax)
            rate_f = rate_f + ((apply - last) / 0.01 - rate_f) * (0.01 / 0.03)
            lead = np.where(~o1, np.clip(tau_ff * rate_f, -lead_max, lead_max), 0.0)
            sent = apply + lead
            last = apply
            raw = S.s16(-np.floor(10.0 * sent + 0.5).astype(np.int64))
            cmd = np.clip(S.s32(-(raw << 2)), -0x4000, 0x4000)
        a_now = (pl.om - om_prev) / 1e-3
        a_f = a_f + (a_now - a_f) * 0.1
        om_prev = pl.om.copy()
        tqv = -0.55 * a_f - 0.3 * pl.om - 150.0 * np.tanh(pl.om / 5.0)
        tqi = np.round(tqv).astype(np.int64)
        om_m = pl.om / S.FRAME.kappa(pl.th)
        g4f50 = S.s16(np.round(S.ABE_PER * om_m + rng.normal(0.0, S.N4F50, B)).astype(np.int64))
        st = st + (((g4f50 * 1024 - st) * 37) >> 7)
        abe = S.s16(st >> 10)
        x69 = np.floor(10.0 * S.FRAME.cinv(pl.th) + 0.5).astype(np.int64)
        T = lane.tick(held_th, x69, held_x, abe, cmd, tqi, ramp, 1, 1)
        if n % 10 == 4:
            held_th = np.floor(10.0 * pl.th + 0.5).astype(np.int64)
            held_x = np.clip(-((S.s16(st >> 10) * 48 * 1159) >> 15), -12000, 12000)
            wire.append(held_th.copy())
        pl.step(-pl.delay(T.astype(float)))
        th_r[n], om_r[n], T_r[n] = pl.th, pl.om, T
        o1_r[n] = o1
        frz_r[n] = lane.log["frz"]
        hand_r[n] = lane._hand
        tq_r[n] = tqv
        ap_r[n] = apply
    return dict(th=th_r, om=om_r, T=T_r, o1=o1_r, frz=frz_r, tq=tq_r, ap=ap_r, hand=hand_r)


def jobB(args):
    member, scl_tag = args
    S = ST()
    CC = cands()
    S.CAL["SCL"] = 19072 if scl_tag == "b" else 15360
    S.CAL["PCL"] = 19072 if scl_tag == "b" else 15360         # (b) raises the P clamp with the sum clamp
    cols, cid, fk = [], [], []
    for c_id, f_id, turns in CONFIGS:
        if (SCL_OF[c_id] == 19072) != (scl_tag == "b"):
            continue
        for v, A, R in turns:
            cols.append(dict(cand=CC[c_id], member=member, v=v, A=A, R=R))
            cid.append(c_id)
            fk.append(f_id)
    r = run_fork(cols, fk)
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    out = []
    rail = (19072 if scl_tag == "b" else 15360) * D.T_PER_S
    for j, c in enumerate(cols):
        f, Tr = plan_of(c["v"], c["A"], c["R"])
        pl_ = f(tt)
        A = c["A"]
        win = (tt >= T_IN) & (tt < T_IN + Tr + 1.6)
        i90 = np.flatnonzero(th[:, j] >= 0.9 * A)
        t90 = (tt[i90[0]] - T_IN) if len(i90) else 99.0
        tail = tt >= T_IN + Tr + 1.6
        out.append(dict(member=member, cid=cid[j], fork=fk[j], v=c["v"], A=A, R=c["R"],
                        tap_pk=float(np.abs(T[:, j]).max() / 8.0), rail_frac=float(np.abs(T[:, j]).max() / rail),
                        rail_ms=float((np.abs(T[:, j]) >= 0.98 * rail).sum()), om_pk=float(np.abs(om[:, j]).max()),
                        t90=float(t90), t90_plan=float(Tr * 0.795), lagmax=float(np.max((pl_ - th[:, j])[win])),
                        ovs=float(np.max(th[win, j] - A)),
                        hold=float(np.mean(th[(tt >= T_IN + Tr + 1.2) & (tt < T_IN + Tr + 1.6), j]) / A),
                        unwind_ovs=float(np.max(-th[tail, j])) if tail.any() else 0.0,
                        o1_ms=float(r["o1"][:, j].sum()), frz_duty=float(r["frz"][win, j].mean()),
                        hand_duty=float(r["hand"][win, j].mean()),
                        hand_tog=float(np.count_nonzero(np.diff(r["hand"][win, j].astype(np.int8)) == 1)),
                        tw_pk=float(np.abs(r["tq"][:, j]).max()),
                        hf=float(np.sqrt(np.mean(S._bp(om[:, j:j + 1], 4.0, 8.0) ** 2))),
                        hf_ref=float(np.sqrt(np.mean(S._bp(np.gradient(r["ap"][:, j:j + 1].astype(float), axis=0)
                                                           * 1000.0, 4.0, 8.0) ** 2)))))
    return out


def mainA():
    t0 = time.time()
    # 16 jobs = one round on 16 processes (< 30 s).  D3b is omitted here: S never reaches SCL 15360 in these scenarios
    # (peakT <= 2285 T < 2462), so D3b == D3a bit for bit -- shown by the first full run (time_A_v1 in the report).
    jobsA = [(s, m, ("V298", "D3a") + (("X8192", "RQ") if s in ("hard", "ov_lt1000", "cs") else ()))
             for s in SCN_A for m in ("nominal", "b_lo*J_hi")] +             [(s, "meas", ("V298", "D3a") + (("X8192", "RQ") if s == "ov_lt1000" else ())) for s in ("s10_05", "ov_lt1000")]
    with Pool(16) as pool:
        ra = [x for xs in pool.map(jobA, jobsA, chunksize=1) for x in xs]
    L = [f"D3 time scoring PART A (panel2/score_time + RQLane; fork 'ff'); speeds {SPEEDS_A}",
         "V298 = the image; D3a = (a) G x1.2 <= 8 m/s + hand-freeze thresholds 1229/800 (cave immediates); "
         "D3b = D3a + SCL 19072; RQ = REJECTED rate-qualified freeze (G1.2, 512/300); "
         "X8192 = REJECTED first cut (thr 1229 / sgn 800 / A3 cap 8192)"]
    keys = {"st": ("settle", "ovs_pct", "hold", "slips", "peakT"), "s10_05": ("fit_gain", "phase", "stick_pct", "dj"),
            "ov_lt511": ("lurch", "droop", "I_rel"), "ov_lt1000": ("lurch", "droop", "I_rel"),
            "ov_fm2400": ("lurch", "droop"), "cs": ("droop", "lurch", "push_ovs"),
            "hard": ("hard_ratio", "ovs", "hold", "peakT")}
    RA = {f"{s}|{m}|{c}": x for s, m, c, x in ra}
    for scn in SCN_A:
        L.append(f"\n== {scn} ==")
        for mem in MEMB_A:
            for cid in ("V298", "D3a", "D3b", "RQ", "X8192"):
                m = RA.get(f"{scn}|{mem}|{cid}")
                if m is None:
                    continue
                s = f"  {mem:10s} {cid:5s}"
                for kk in keys[scn]:
                    s += f" | {kk} " + " ".join(f"{x:7.2f}" for x in m[kk])
                L.append(s)
    L.append(f"\nwall time {time.time() - t0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (D.OUT / "time_A.txt").write_text(txt, encoding="utf-8")
    (D.OUT / "time_A.json").write_text(json.dumps(RA), encoding="utf-8")


def mainB():
    t0 = time.time()
    jobsB = [(m, "a") for m in MEMB_B] + [(m, "b") for m in MEMB_B]
    with Pool(16) as pool:
        rb = [x for xs in pool.map(jobB, jobsB, chunksize=1) for x in xs]
    L = ["D3 time scoring PART B: hands-off turns through the FORK MODEL with the reaction twist on the torque word.",
         "tap_pk LSB (rail 307.8; SCL 19072: 382) | rail ms | wheel peak deg/s | t90 s (plan's own) | max lag deg | "
         "overshoot deg | hold | unwind overshoot | O1 ms | I-stopped duty (hand or A3) in turn | hand-freeze duty / "
         "onsets in turn | twist peak | 4-8 Hz rate rms "
         "wheel / sent setpoint (deg/s)"]
    for mem in MEMB_B:
        L.append(f"\n== member {mem} ==")
        for v, A, R in TURNS + TURNS_FAST:
            for c_id, f_id, turns in CONFIGS:
                x = [q for q in rb if q["member"] == mem and q["v"] == v and q["cid"] == c_id and q["fork"] == f_id
                     and q["R"] == R]
                if not x:
                    continue
                q = x[0]
                L.append(f"  v{v:5.1f} A{A:5.1f} {c_id:5s}+{f_id:11s} tap {q['tap_pk']:6.1f} rail {q['rail_ms']:4.0f}ms "
                         f"om {q['om_pk']:6.1f} t90 {q['t90']:5.2f} ({q['t90_plan']:4.2f}) lag {q['lagmax']:5.1f} "
                         f"ovs {q['ovs']:+5.1f} hold {q['hold']:5.3f} unw {q['unwind_ovs']:+5.1f} O1 {q['o1_ms']:4.0f} "
                         f"frz {q['frz_duty']:.3f} hand {q['hand_duty']:.3f}/{q['hand_tog']:3.0f} tw {q['tw_pk']:5.0f} hf {q['hf']:5.2f}/{q['hf_ref']:5.2f}")
    L.append(f"\nwall time {time.time() - t0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (D.OUT / "time_B.txt").write_text(txt, encoding="utf-8")
    (D.OUT / "time_B.json").write_text(json.dumps(rb), encoding="utf-8")


if __name__ == "__main__":
    (mainA if (len(sys.argv) > 1 and sys.argv[1].upper() == "A") else mainB)()
