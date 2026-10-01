# -*- coding: utf-8 -*-
r"""ds_time.py -- the exact 1 kHz time harness for the D-structure implementations: harness_time's plant (Karnopp,
10 kHz sub-steps), scenarios and metrics, UNCHANGED, around ds_lane.DSLane (integer-exact), with the sensor set the
structures need.  ANALYSIS ONLY.  Fixed seeds.

SENSORS (each tick n; slot 4 on n % 10 == 4 AFTER the lane, the lane sees the held cells aged 1..10):
  gp-0x6a00  held, 0.1 deg quantiser of the motor-side angle (harness_time.q_angle)
  gp-0x6abe  FRESH every tick, the integer mirror of FUN_00041464:  gp-0x4f50 = s16(round(-4.712 omega + n)),
             u = 1024 gp-0x4f50 ; st += ((u - st) * 37) >> 7 ; gp-0x6abe = st >> 10   (0x22200, before the PID)
             n = white noise 2.8 counts rms (BELIEF: sized so that the held x shows the record's 1.93 counts rms floor)
  gp-0x6a56  held: sensor 'ema' (DEFAULT, the bytes): clamp(-((gp-0x6abe * 48 * 1159) >> 15), +-12000) sampled by
             slot 4 (FUN_0003f776);  sensor 'w3' (the record harness's BELIEF former): round(8 (th[n] - th[n-3]) /
             3 ms) + 1.93 counts noise -- kept to reproduce the C1 pages' numbers
  gp-0x6cc4  FRESH every tick, motor counts = floor(D_PER * theta + 0.5), D_PER = -278.5 per deg (BELIEF frame)
  gp-0x6c2c  Honda's oscillation-detector input, the integer mirror of FUN_00041464 lines (decompile 2026-10-01):
             d = st_new - st_prev ; d32 = clamp(32 d, +-0xFA0000) (|d| >= 0x7D000 -> +0xFA0000) ;
             s2 += ((d32 - s2) * 14) >> 6 ; gp-0x6c2c = s2 >> 9 ; FUN_000428d4: reversals past +-12800 within
             50 ticks, the cut (x0.600) needs 15-20 reversals and gp-0x6a5e <= 960 (15 km/h)
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ds_model as Mdl  # noqa: E402
import ds_lane as DL  # noqa: E402
import harness_time as HT  # noqa: E402
import lane_mirror_v295 as LM  # noqa: E402
import c1_time as T1  # noqa: E402  (members incl. 'bc', 'J1.0', two-mass; installs LaneC1 into HT -- not used here)
from harness_time import s32, s16  # noqa: E402

OUT = Mdl.AL.parents[2] / "_scratch" / "angle_loop" / "D-structure"
OUT.mkdir(parents=True, exist_ok=True)
N4F50 = 2.8
DET_THR, DET_DWELL = 12800, 50


def member(name):
    import c1r2_time as T2          # b_q / b_q*J_hi / b_q*J1.0 with the per-speed step at 12.5 m/s
    return T2._member(name) if name.startswith("b_q") else T1.member(name)


class Detector:
    def __init__(self, B):
        self.s2 = np.zeros(B, np.int64)
        self.state = np.zeros(B, np.int64)       # 0 neutral, 1 last crossed +, 2 last crossed -
        self.dwell = np.zeros(B, np.int64)
        self.count = np.zeros(B, np.int64)
        self.maxabs = np.zeros(B, np.int64)
        self.maxcount = np.zeros(B, np.int64)

    def step(self, dst):
        d = dst
        big = d >= 0x7D000
        d32 = np.where(big, 0xFA0000, np.clip(d * 32, -0xFA0000, 0xFA0000))
        self.s2 = self.s2 + (((d32 - self.s2) * 14) >> 6)
        x = self.s2 >> 9
        self.maxabs = np.maximum(self.maxabs, np.abs(x))
        st = self.state
        n0 = st == 0
        # state 0: crossing + -> 1 ; crossing - -> 2 ; counter reset
        new = np.where(n0 & (x > DET_THR), 1, np.where(n0 & (x < -DET_THR), 2, st))
        self.count = np.where(n0, 0, self.count)
        self.dwell = np.where(n0, 0, self.dwell)
        # state 1/2: timeout -> 0 ; opposite crossing -> count++ and flip
        to = (~n0) & (self.dwell >= DET_DWELL)
        f1 = (st == 1) & ~to & (x < -DET_THR)
        f2 = (st == 2) & ~to & (x > DET_THR)
        flip = f1 | f2
        new = np.where(to, 0, np.where(f1, 2, np.where(f2, 1, new)))
        self.count = np.where(flip, self.count + 1, self.count)
        self.dwell = np.where(flip | to, 0, np.where(~n0, self.dwell + 1, self.dwell))
        self.state = new
        self.maxcount = np.maximum(self.maxcount, self.count)
        return x


def run(scn, cfgs, mem, v, cal=None, sensor="ema", seed=11, rec_extra=False):
    cal = HT.base_cal() if cal is None else cal
    B = len(cfgs)
    lane = DL.DSLane(cal, cfgs)
    pl = HT.PlantVec(mem, v, B)
    rng = np.random.default_rng(seed)
    n_t = int(round(scn["dur"] * 1000))
    spd = int(round(v * 3.6 * 64))
    c63f6 = scn["c63f6"]
    th_r = np.zeros((n_t, B), np.float32)
    om_r = np.zeros((n_t, B), np.float32)
    T_r = np.zeros((n_t, B), np.int16)
    sp_r = np.zeros((n_t, B), np.int32)
    ext = {k: np.zeros((n_t, B), np.int32) for k in ("I", "P", "D")} if rec_extra else None
    wire = np.zeros((n_t // 10 + 2, B), np.int64)
    nw = 0
    th0 = scn.get("th0", 0.0)
    pl.th = np.full(B, float(th0))
    held_th = HT.q_angle(pl.th)
    held_x = np.zeros(B, np.int64)
    hist = [pl.th.copy() for _ in range(4)]
    st_ema = np.zeros(B, np.int64)
    det = Detector(B)
    cmd = 4 * held_th
    mode = scn.get("mode0", "engaged")
    ramp = 0x8000 if mode == "engaged" else 0
    act = 1 if mode == "engaged" else 0
    req = 1 if mode == "engaged" else 0
    events = sorted(scn["events"])
    ev_i = 0
    hand = scn.get("hand")
    hand_fn = scn.get("hand_fn")
    if hand is not None:
        n_h0, n_hrel, n_hramp = int(round(hand["t0"] * 1000)), int(round(hand["t_rel"] * 1000)), int(round(hand["tramp"] * 1000))
        th_grab = np.zeros(B)
    tqf = scn["tq"]
    sen = False
    HT._WRAPS["n"] = 0
    for n in range(n_t):
        t = n * 1e-3
        while ev_i < len(events) and t >= events[ev_i][0] - 1e-9:
            kind = events[ev_i][1]
            mode = {"fault": "fault", "disengage": "dis", "latch_on": "latch", "latch_off": "relatch",
                    "engage": "relatch"}[kind]
            if kind == "fault":
                sen = True
            ev_i += 1
        if mode == "engaged":
            ramp, act, req = 0x8000, 1, 1
        elif mode in ("fault", "dis"):
            ramp, act, req = max(0, ramp - c63f6), 0, (0xFF if mode == "fault" else 0)
        elif mode == "latch":
            ramp, act, req = max(0, ramp - 328), 0, 1
        elif mode == "relatch":
            ramp, act, req = min(0x8000, ramp + 33), 1, 1
        elif mode == "off":
            ramp, act, req = max(0, ramp - 16), 0, 0
        if n % 10 == HT.E4_PHASE and not sen:
            k = n // 10
            th_meas = wire[max(nw - 6, 0)] / 10.0 if nw else pl.th.copy()
            if mode in ("dis", "off") or (scn.get("sp_meas_until", -1) > t):
                thc = th_meas if scn["inactive"] == "meas" else np.zeros(B)
            elif scn.get("sp_hold_from") is not None and t >= scn["sp_hold_from"]:
                thc = cmd / 40.0
            else:
                thc = np.full(B, float(scn["ref"](np.array(k * 0.01))))
            raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
            cmd = np.clip(s32(-(s16(raw) << 2)), -0x4000, 0x4000)
        if sen:
            cmd = np.full(B, LM.SENTINEL, np.int64)
        th_now = pl.th
        om_now = pl.om
        hist = [th_now.copy()] + hist[:3]
        tq = 0 if tqf is None else int(round(float(tqf(np.array(t)))))
        # ---- slot 0, before the PID: FUN_00041464 (gp-0x6abe EMA, gp-0x6c2c) and FUN_0003bd7c (gp-0x6cc4)
        g4f50 = s16(np.round(Mdl.ABE_PER * om_now + rng.normal(0.0, N4F50, B)).astype(np.int64))
        u = g4f50 * 1024
        st_prev = st_ema
        st_ema = st_ema + (((u - st_ema) * 37) >> 7)
        lane.abe = s16(st_ema >> 10)
        det.step(st_ema - st_prev)
        lane.dacc = np.floor(Mdl.D_PER * th_now + 0.5).astype(np.int64)
        T = lane.tick(held_th, held_x, cmd, tq, 0, spd, ramp, act, req)
        # ---- slot 4 (100 Hz), AFTER the lane
        if n % 10 == HT.SLOT4_PHASE:
            held_th = HT.q_angle(th_now)
            if sensor == "ema":
                held_x = np.clip(-((s16(st_ema >> 10) * 48 * 1159) >> 15), -12000, 12000).astype(np.int64)
            else:
                xr = 8.0 * (hist[0] - hist[3]) / 0.003 + rng.normal(0.0, HT.RATE_NOISE, B)
                held_x = np.clip(np.round(xr), -12000, 12000).astype(np.int64)
            wire[nw] = held_th
            nw += 1
        Tapp = pl.push_T(T.astype(float))
        hh = None
        if hand_fn is not None:
            hh = hand_fn(t)
        elif hand is not None and n_h0 <= n < n_hrel:
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
            ext["I"][n] = lane.log["I"] >> 7
            ext["P"][n] = lane.log["P"]
            ext["D"][n] = lane.log["D"]
    out = dict(th=th_r, om=om_r, T=T_r, sp=sp_r, wire=wire[:nw], wraps=HT._WRAPS["n"], det_max=det.maxabs.copy(),
               det_count=det.maxcount.copy())
    if rec_extra:
        out.update(ext)
    return out


# ------------------------------------------------------------------------------------------------- extra scenarios
def scenario(name, v):
    """harness_time.scenario, plus: ov_light<tq> (a LIGHT hand, |tq| word constant <= 1000, the stiff position hand
    holding 0.5*A off for 3 s, no fork O1), eng_load (engage while the driver holds a curve, the fork sends the measured
    angle at the engage frame and holds it, the hand lets go over 0.2 s 0.3 s after the engage edge)."""
    if name.startswith("ov_light"):
        a = float(name[len("ov_light"):])
        s = HT.scenario("ov_fade", v)
        tg, tramp, thold = s["t_grab"], 0.3, 3.0
        trel = tg + tramp + thold
        s.update(name=name, dur=trel + 3.0, t_rel=trel,
                 hand=dict(s["hand"], t_rel=trel, Kh=2000.0, Bh=30.0),
                 tq=lambda t, a=a, tg=tg, trel=trel, tramp=tramp: np.where(
                     (t >= tg) & (t < trel), a * np.clip((t - tg) / tramp, 0, 1),
                     np.where((t >= trel) & (t < trel + 0.03), a * (1 - (t - trel) / 0.03), 0.0)), events=[])
        return s
    if name == "eng_load":
        th0 = {3.0: 45.0, 5.0: 25.0, 8.0: 15.0, 10.0: 10.0, 12.5: 6.0, 15.0: 4.0, 19.0: 2.5, 26.0: 1.5, 30.0: 1.2}.get(
            v, 3.0)
        TE, lag = 2.0, 0.3

        def hand_fn(t, th0=th0):
            if t < TE + lag:
                return (2000.0, 30.0, th0)
            fr = min(1.0, (t - TE - lag) / 0.2)
            if fr >= 1.0:
                return None
            return (2000.0 * (1 - fr), 30.0 * (1 - fr), th0)
        return dict(name=name, v=v, dur=TE + 5.0, events=[(TE, "engage")], hand=None, hand_fn=hand_fn, c63f6=16,
                    inactive="meas", outer="ff", tq=None, ref=lambda t: 0.0, mode0="off", th0=th0, t_eng=TE,
                    sp_meas_until=TE + 0.011, sp_hold_from=TE + 0.011)
    return HT.scenario(name, v)


def metrics(name, scn, r, v):
    if name == "eng_load":
        th = r["th"].astype(float)
        sp = r["sp"].astype(float) / 40.0
        T = r["T"].astype(float)
        tt = np.arange(th.shape[0]) * 1e-3
        w = tt >= scn["t_eng"]
        sg = np.sign(scn["th0"])
        e = (sp - th)[w] * sg
        m = dict(droop=e.max(0), overshoot=(-e).max(0), peakT=np.abs(T[w]).max(0), e_end=np.abs(e[-1]),
                 slips=HT._slips(th[w], r["om"][w].astype(float)))
    elif name.startswith("ov_light"):
        m = HT.metrics("ov_fade", scn, r, v)
    else:
        m = HT.metrics(name, scn, r, v)
    m["det_max_frac"] = r["det_max"] / DET_THR
    m["det_count"] = r["det_count"]
    # 40-200 Hz content of the lane torque (the 100 Hz staircase / impulse texture), T counts rms, after 1 s
    T = r["T"].astype(float)
    if T.shape[0] > 2000:
        m["T_100"] = np.sqrt(np.mean(HT._bp(T, 40.0, 200.0)[1000:-200] ** 2, axis=0))
    return m


def job(args):
    scn_name, v, cfgs, mem, sensor = args
    scn = scenario(scn_name, v)
    t0 = time.time()
    r = run(scn, cfgs, member(mem), v, sensor=sensor)
    m = metrics(scn_name, scn, r, v)
    return dict(name=scn_name, v=v, member=mem, sensor=sensor,
                metrics={k: np.asarray(x, float).tolist() for k, x in m.items()}, sec=time.time() - t0)


def run_suite(cfgs, labels, members, speeds, scens, sensor="ema", procs=15, tag="suite"):
    jobs = [(s, v, cfgs, m, sensor) for m in members for v in speeds for s in scens]
    t0 = time.time()
    out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs)):
            out.append(res)
            if (i + 1) % 40 == 0 or i + 1 == len(jobs):
                print(f"  {tag}: {i + 1}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    (OUT / f"time_{tag}.json").write_text(json.dumps(dict(labels=labels, cfgs=[{k: (v if not isinstance(v, (list, tuple))
                                                                                     else [list(x) if isinstance(x, tuple) else x for x in v])
                                                                                 for k, v in c.items()} for c in cfgs],
                                                         results=out)))
    return out
