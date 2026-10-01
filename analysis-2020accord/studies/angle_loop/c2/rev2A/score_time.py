# -*- coding: utf-8 -*-
r"""score_time.py -- THE COMMON TIME-DOMAIN SCORER for the angle-loop panel and the C2 rev 2 implementations
(C2 rev 2, reviser A, 2026-10-01).  It resolves the C2 refuters' finding "the common time-domain scorer
panel/score_time.py does not exist": every candidate the panel produced that can be expressed as bytes, plus this
reviser's implementations, is driven through ONE identical exact 1 kHz pipeline -- the same plant family and members,
the same sensors, the same scenarios, the same metric extractor -- in ONE batch per (scenario, speed, member), so every
column sees identical inputs.  Written in this reviser's private folder (two revisers run in parallel); the
orchestrator may promote it to panel/score_time.py.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing.

ENGINE (each piece is an existing, controlled component; nothing below re-implements lane arithmetic):
  * cave-class columns: ds_lane.DSLane, the integer-exact lane for every C1-skeleton structure (ds_selftest CHECK 1:
    == c1_lib.LaneC1F, the C1 pages' byte-exact lane, 0 / 40 000 ticks; its caves are the ds_asm listings whose
    ASSEMBLED BYTES the H1 interpreter executes 0 / 60 000 against it).  r2a_bytes.py re-runs H1 on the exact bytes.
  * zero-cave columns (A1, A2): harness_time.LaneVec (the ORIGINAL class, captured before c1_time patches the module),
    key='speed', guard_and (A2 + B2), whose selftest proves it == lane_mirror_v295.lane_tick.
  * plant: harness_time.PlantVec (Karnopp stick, 10 kHz sub-steps, 2/6 ms transport) on the r71b family.
  * sensors (ds_time's, unchanged): gp-0x6a00 held 0.1 deg at slot 4 AFTER the lane; gp-0x6abe the fresh 1 kHz integer
    EMA of gp-0x4f50 (alpha 37/128, 2.8 counts rms noise, BELIEF); gp-0x6a56 the slot-4 hold of the EMA through
    FUN_0003f776's integer form (pol -1); Honda's oscillation-detector mirror on gp-0x6c2c.
  * '+h10' members: the slot-4 refresh delivers values sampled 10 ticks earlier (hold ages 11..20).
  * the 0xE4 frame on tick % 10 == 0; the setpoint = -raw/10 deg, gp-0x69ae = clamp(-4 raw, +-16384).

MEMBERS: nominal, bc (b_lo damping, Coulomb x2 >= 10 m/s, x1.3 5-10 m/s: the friction refuter's bias-corrected world),
F_hi (nominal, friction x2), b_lo*J_hi (the J_hi refit with b_lo's per-speed damping step), nominal+h10.
SPEEDS: 3.1 5 8 10 11.9 12.5 15 17 19 22 26.9 30 m/s (the plant knots 3.1 / 8.0 / 11.9 / 17.0 / 26.9 included).

SCENARIOS: harness_time's rh s02 s05 ssm st ov_fade ov_latch sen_L16 sen_R16 dis_meas dis_zero, ds_time's ov_light400
ov_light1000 eng_load, and four added here:
  tmo   the fork STOPS sending while the wheel holds a turn: gp-0x69ae keeps the last setpoint for 510 ms (tracer: the
        pending threshold 0xC626C = 500 ms + the 200 Hz task phase), then the 0x7FFF sentinel with request 0xFF.
  cs    CO-STEER: in a held curve the driver adds a pure torque IN the turn direction (0.5 x the spring load) for 2 s
        with the torque word at 400 (below the 512 freeze: the I is NOT frozen and drains), then lets go
        (the friction refuter's expF form).
  db    DEAD BAND: the setpoint creeps 0 -> 2 deg at 0.2 deg/s from rest; the lag error once moving.
  hard  a HARD TURN: 0 -> A in 0.3 s, hold 2 s, back to 0 in 0.3 s; the 1.6-3 Hz wheel-rate energy vs the command's own.

PRE-REGISTERED BARS (written before the first run; the goal's own criteria where the harness can score them):
  hold   rh hold_ratio >= 0.90 at every speed >= 8 m/s (goal turn-hold)
  line   T 5-30 Hz rms in holds <= 2.0 counts (harness_time HF_LINE) and 0 detector reversals (goal: no new 5-30 Hz line)
  sent   sentinel excursion toward the sentinel <= 0.1 deg; tmo: |T| < 50 counts within 0.25 s of the sentinel
  wrap   0 int32 wraps
  track  s02 regression gain (wire) reported against 0.95-1.05 -- a PROXY: the goal's tracking metric is a 0.04-0.08 Hz
         weighted slope (c1r2_trackmetric), scored in r2a_freq.py; s02 at 0.2 Hz is stricter and is reported, not gated
  dj     dwell-then-jump events per scenario set (s02+s05+ssm+hold slips) reported per band; V282 is not simulable, so
         the goal's "<= V282" is decided on the car (the low-speed band is a pre-declared miss for every candidate)
  hard   hard16 / hard16_ref (1.6-3 Hz wheel-rate rms over the command's own) reported; > 1 = the loop adds energy

usage:  python score_time.py run   [--quick]      (writes _scratch/angle_loop/c2rev2A/time_<tag>.json)
        python score_time.py dense                (s02 / rh / ssm on nominal + bc at 3-30 m/s every 0.25 m/s, every column)
        python score_time.py dense2               (the same on nominal+h10 (hold ages 11-20) + F_hi)
        python score_time.py report               (score_time_out.md: the tables)
        python score_time.py selftest             (controls: see selftest())"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, replace
from multiprocessing import Pool

import numpy as np

import r2a_common as R

import harness_time as HT  # noqa: E402
_LANEVEC_ORIG = HT.LaneVec            # captured BEFORE c1_time.install_ht() rebinds HT.LaneVec to LaneC1
import ds_time as DT  # noqa: E402   (imports c1_time -> HT.LaneVec := LaneC1; we keep the original above)
import ds_lane as DL  # noqa: E402
import ds_model as DM  # noqa: E402
import lane_mirror_v295 as LM  # noqa: E402
import c1_lib as C  # noqa: E402
import score_freq as SF  # noqa: E402
sys.path.insert(0, str(R.AL / "panel" / "A-fewest-bytes"))
import panel_schedules as PS  # noqa: E402
from harness_time import s16  # noqa: E402

SPEEDS = (3.1, 5.0, 8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.9, 30.0)
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi", "nominal+h10")
SCENS = ("rh", "s02", "s05", "ssm", "st", "ov_fade", "ov_latch", "ov_light400", "ov_light1000", "sen_L16", "sen_R16",
         "dis_meas", "dis_zero", "eng_load", "tmo", "cs", "db", "hard")
TMO_S = 0.510

# amplitudes for the speeds harness_time does not carry (log-interpolated in speed over its own table)
_AV = sorted(HT.A_TURN)
for _v in set(SPEEDS) | {round(x, 2) for x in np.arange(3.0, 30.01, 0.25)}:
    if _v not in HT.A_TURN:
        HT.A_TURN[_v] = float(np.exp(np.interp(_v, _AV, [np.log(HT.A_TURN[a]) for a in _AV])))
        HT.RAMP_S[_v] = 3.0 if _v <= 3.5 else (2.0 if _v < 7.0 else 1.0)


# ---------------------------------------------------------------------------------------------------------------------
# the columns: every expressible panel candidate + this reviser's implementations
# ---------------------------------------------------------------------------------------------------------------------
def cave_columns():
    """[(label, DSLane cfg)] -- the panel's cave candidates from their own specs + R2A's implementations."""
    import ds_selftest as ST
    tabs = R.tables()
    cols = []
    # the panel (tables from score_freq's verbatim copies of each designer's spec)
    held = lambda kd: DM.Des(dsrc="rate_held", kd=kd)  # noqa: E731
    fresh = lambda kd: DM.Des(dsrc="op", dop="fresh_rate", kd=kd)  # noqa: E731
    cols.append(("B1", ST.lane_cfg(held(20), C.make_table(SF.B1_KNOTS))))
    cols.append(("B2+guard", ST.lane_cfg(fresh(41), C.make_table(SF.B2_KNOTS))))
    c = ST.lane_cfg(held(20), C.make_table(SF.B3_KNOTS))
    c["ki"] = 0
    cols.append(("B3", c))
    cols.append(("CGF-1+guard", ST.lane_cfg(fresh(48), C.make_table(SF.CGF_KNOTS))))
    import ds_final as DF
    for k in ("D1a", "D1b", "D1c", "D2b", "D2c", "D3a", "D3b"):
        cols.append((k, ST.lane_cfg(DF.CANDS[k], [tuple(r) for r in SF.DS_ROWS[k]])))
    # R2A's implementations (P1 == the panel's D2a, F1 == the panel's B0r, byte for byte)
    for k in R.IMPLS:
        if k in tabs:
            cols.append((k, R.lane_cfg(k, tabs[k])))
    return cols


A_LABELS = ("A1+B2", "A2+B2")


def a_rows(v):
    """A1 / A2 at speed v (panel_time.rows_for: re-key Kp(v), Kd(v), Ki flat 80 / Ki(v); guard_and = A2 + B2)."""
    a1 = HT.row(0, kpX=PS.KP_X, kpY=PS.KP_Y, kdX=PS.KD_X, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A1"),
                ICL=4096, DB=0, label="A1+B2")
    a1["guard_and"] = True
    a2 = HT.row(0, kpX=PS.KP_X, kpY=PS.KP_Y_A2, kdX=PS.KD_X, kdY=PS.KD_SCHED, key="speed", Ki=PS.ki_of(v, "A2"),
                ICL=4096, DB=0, label="A2+B2")
    a2["guard_and"] = True
    return [a1, a2]


def labels():
    return [k for k, _ in cave_columns()] + list(A_LABELS)


# ---------------------------------------------------------------------------------------------------------------------
# members
# ---------------------------------------------------------------------------------------------------------------------
@dataclass
class _BloJhi(HT.VP.PlantFamilyMember):
    def arrays_at(self, v):
        a = super().arrays_at(v)
        vv = np.asarray(v, float)
        a["b"] = a["b"] * np.where(vv >= 10.0, 1 / 1.8, 0.7)           # c1r2_members._dscale('b_lo', ...)
        return a


def member(name):
    base = name[:-4] if name.endswith("+h10") else name
    if base == "b_lo*J_hi":
        m = DT.member("J_hi")
        kw = {k: getattr(m, k) for k in m.__dataclass_fields__}
        kw["name"] = "b_lo*J_hi"
        return _BloJhi(**kw)
    return DT.member(base)


# ---------------------------------------------------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------------------------------------------------
def scenario(name, v):
    A = HT.A_TURN[v]
    Ah = 0.5 * A
    if name == "tmo":
        ts = 2.5
        return dict(name=name, v=v, dur=ts + 2.0, ref=lambda t: np.interp(t, [0, 0.5, 1.5, 9], [0, 0, Ah, Ah]),
                    events=[(ts + TMO_S, "fault")], hand=None, c63f6=16, inactive="meas", outer="ff", tq=None,
                    t_stop=ts, t_fault=ts + TMO_S)
    if name == "cs":
        T1_, T2_ = 3.0, 5.0
        p = member("nominal").at(v)
        load = p.k * p.sat * np.tanh(Ah / p.sat)
        d = 0.5 * load
        return dict(name=name, v=v, dur=T2_ + 4.0, ref=lambda t: np.interp(t, [0, 0.5, 1.5, 99], [0, 0, Ah, Ah]),
                    events=[], hand=None, c63f6=16, inactive="meas", outer="ff",
                    tq=lambda t: np.where((t >= T1_) & (t < T2_), 400.0, 0.0),
                    u_ext=lambda t, d=d: d * float(np.clip((t - T1_) / 0.2, 0, 1)) if t < T2_ else
                    d * float(np.clip(1 - (t - T2_) / 0.05, 0, 1)), t_push=T1_, t_rel=T2_, Ah=Ah)
    if name == "db":
        return dict(name=name, v=v, dur=12.0, ref=lambda t: np.clip(0.2 * (t - 1.0), 0.0, 2.0), events=[], hand=None,
                    c63f6=16, inactive="meas", outer="ff", tq=None)
    if name == "hard":
        t1, t2, t3 = 1.0, 3.3, 5.6
        return dict(name=name, v=v, dur=8.0, ref=lambda t: np.interp(t, [0, t1, t1 + 0.3, t2, t2 + 0.3, 99],
                                                                     [0, 0, A, A, 0, 0]),
                    events=[], hand=None, c63f6=16, inactive="meas", outer="ff", tq=None, holds=[(t1 + 0.3, t2, A)])
    return DT.scenario(name, v)


# ---------------------------------------------------------------------------------------------------------------------
# the runner (ds_time.run, extended: two lanes side by side, the aged hold, the fork stop, an external hand torque)
# ---------------------------------------------------------------------------------------------------------------------
def run(scn, cave_cfgs, a_rows_v, mem_name, v, seed=11):
    cal = HT.base_cal()
    nc, na = len(cave_cfgs), len(a_rows_v)
    B = nc + na
    lane = DL.DSLane(cal, cave_cfgs) if nc else None
    laneA = _LANEVEC_ORIG(cal, HT.Cfg(a_rows_v)) if na else None
    mem = member(mem_name)
    aged = mem_name.endswith("+h10")
    pl = HT.PlantVec(mem, v, B)
    rng = np.random.default_rng(seed)
    n_t = int(round(scn["dur"] * 1000))
    spd = int(round(v * 3.6 * 64))
    c63f6 = scn["c63f6"]
    th_r = np.zeros((n_t, B), np.float32)
    om_r = np.zeros((n_t, B), np.float32)
    T_r = np.zeros((n_t, B), np.int16)
    sp_r = np.zeros((n_t, B), np.int32)
    wire = np.zeros((n_t // 10 + 2, B), np.int64)
    nw = 0
    th0 = scn.get("th0", 0.0)
    pl.th = np.full(B, float(th0))
    held_th = HT.q_angle(pl.th)
    held_x = np.zeros(B, np.int64)
    fifo = []                                                          # (q_angle, x) per tick for the aged hold
    st_ema = np.zeros(B, np.int64)
    det = DT.Detector(B)
    cmd = np.broadcast_to(4 * held_th, (B,)).astype(np.int64)
    mode = scn.get("mode0", "engaged")
    ramp = 0x8000 if mode == "engaged" else 0
    act = 1 if mode == "engaged" else 0
    req = 1 if mode == "engaged" else 0
    events = sorted(scn["events"])
    ev_i = 0
    hand = scn.get("hand")
    hand_fn = scn.get("hand_fn")
    u_ext = scn.get("u_ext")
    t_stop = scn.get("t_stop")
    if hand is not None:
        n_h0, n_hrel, n_hramp = (int(round(hand["t0"] * 1000)), int(round(hand["t_rel"] * 1000)),
                                 int(round(hand["tramp"] * 1000)))
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
        stopped = t_stop is not None and t >= t_stop
        if n % 10 == HT.E4_PHASE and not sen and not stopped:
            k = n // 10
            th_meas = wire[max(nw - 6, 0)] / 10.0 if nw else pl.th.copy()
            if mode in ("dis", "off") or (scn.get("sp_meas_until", -1) > t):
                thc = th_meas if scn["inactive"] == "meas" else np.zeros(B)
            elif scn.get("sp_hold_from") is not None and t >= scn["sp_hold_from"]:
                thc = cmd / 40.0
            else:
                thc = np.full(B, float(scn["ref"](np.array(k * 0.01))))
            raw = s16(-np.floor(10.0 * thc + 0.5).astype(np.int64))
            cmd = np.clip(HT.s32(-(s16(raw) << 2)), -0x4000, 0x4000)
        if sen:
            cmd = np.full(B, LM.SENTINEL, np.int64)
        th_now = pl.th
        om_now = pl.om
        tq = 0 if tqf is None else int(round(float(tqf(np.array(t)))))
        g4f50 = s16(np.round(DM.ABE_PER * om_now + rng.normal(0.0, DT.N4F50, B)).astype(np.int64))
        st_prev = st_ema
        st_ema = st_ema + (((g4f50 * 1024 - st_ema) * 37) >> 7)
        det.step(st_ema - st_prev)
        T = np.zeros(B, np.int64)
        if nc:
            lane.abe = s16(st_ema[:nc] >> 10)
            lane.dacc = np.floor(DM.D_PER * th_now[:nc] + 0.5).astype(np.int64)
            T[:nc] = lane.tick(held_th[:nc], held_x[:nc], cmd[:nc], tq, 0, spd, ramp, act, req)
        if na:
            cA = cmd[nc:]
            cA = int(cA[0]) if bool((cA == cA[0]).all()) else cA
            T[nc:] = laneA.tick(held_th[nc:], held_x[nc:], cA, tq, 0, spd, ramp, act, req)
        # ---- slot 4 (100 Hz), AFTER the lane; '+h10' delivers the sample taken 10 ticks earlier
        x_now = np.clip(-((s16(st_ema >> 10) * 48 * 1159) >> 15), -12000, 12000).astype(np.int64)
        q_now = HT.q_angle(th_now)
        if aged:
            fifo.append((q_now, x_now))
            if len(fifo) > 11:
                fifo.pop(0)
        if n % 10 == HT.SLOT4_PHASE:
            if aged:
                held_th, held_x = fifo[0]
            else:
                held_th, held_x = q_now, x_now
            wire[nw] = q_now
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
        uu = -Tapp + (u_ext(t) if u_ext is not None else 0.0)
        pl.step(uu, hand=hh)
        th_r[n] = pl.th
        om_r[n] = pl.om
        T_r[n] = T
        sp_r[n] = cmd
    return dict(th=th_r, om=om_r, T=T_r, sp=sp_r, wire=wire[:nw], wraps=HT._WRAPS["n"], det_max=det.maxabs.copy(),
                det_count=det.maxcount.copy())


# ---------------------------------------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------------------------------------
def metrics(name, scn, r, v):
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    sp = r["sp"].astype(float) / 40.0
    tt = np.arange(th.shape[0]) * 1e-3
    if name == "tmo":
        i0 = int(scn["t_stop"] * 1000) - 1
        hold = (tt >= scn["t_stop"]) & (tt < scn["t_fault"])
        post = tt >= scn["t_fault"] + 0.25
        m = dict(tmo_hold_dev=np.abs(th[hold] - th[i0]).max(0), tmo_T_after=np.abs(T[post]).max(0),
                 tmo_excursion=np.abs(th[tt >= scn["t_stop"]] - th[i0]).max(0), peakT=np.abs(T).max(0),
                 wraps=np.full(th.shape[1], r["wraps"]))
    elif name == "cs":
        sg = np.sign(scn["Ah"])
        w = tt >= scn["t_rel"]
        e = (sp - th)[w] * sg
        push = (tt >= scn["t_push"]) & (tt < scn["t_rel"])
        m = dict(cs_droop=e.max(0), cs_push_ovs=((th - sp)[push] * sg).max(0),
                 cs_slips=HT._slips(th[w], om[w]), cs_e_end=np.abs(e[-1]), wraps=np.full(th.shape[1], r["wraps"]))
    elif name == "db":
        w = tt >= 3.0
        e = (sp - th)[w]
        stuck = (om[w] == 0.0)
        m = dict(db_lag=e.max(0), db_stuck_pct=100.0 * stuck.mean(0), db_slips=HT._slips(th[w], om[w]),
                 wraps=np.full(th.shape[1], r["wraps"]))
    elif name == "hard":
        A = HT.A_TURN[v]
        ref_om = np.gradient(sp, axis=0) * 1000.0
        h = HT._bp(om, 1.6, 3.0)[200:-200]
        hr = HT._bp(ref_om, 1.6, 3.0)[200:-200]
        hw = (tt >= 1.3) & (tt < 3.3)
        m = dict(hard16=np.sqrt(np.mean(h ** 2, 0)), hard16_ref=np.sqrt(np.mean(hr ** 2, 0)),
                 hard_ovs=np.max((th[hw] - A) * np.sign(A), 0), hard_hold=(th[(tt >= 2.8) & (tt < 3.3)] / A).mean(0),
                 wraps=np.full(th.shape[1], r["wraps"]))
    else:
        m = DT.metrics(name, scn, r, v)
        return {k: np.asarray(x, float) for k, x in m.items()}
    m["det_max_frac"] = r["det_max"] / DT.DET_THR
    m["det_count"] = r["det_count"]
    return {k: np.asarray(x, float) for k, x in m.items()}


def job(args):
    name, v, mem = args
    cc = cave_columns()
    cfgs = [c for _, c in cc]
    scn = scenario(name, v)
    t0 = time.time()
    r = run(scn, cfgs, a_rows(v), mem, v)
    m = metrics(name, scn, r, v)
    return dict(name=name, v=v, member=mem, metrics={k: x.tolist() for k, x in m.items()}, sec=time.time() - t0)


def run_suite(scens, speeds, members, tag, procs=15):
    jobs = [(s, v, m) for m in members for v in speeds for s in scens]
    t0 = time.time()
    out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            out.append(res)
            if (i + 1) % 50 == 0 or i + 1 == len(jobs):
                print(f"  {tag}: {i + 1}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    (R.OUT / f"time_{tag}.json").write_text(json.dumps(dict(labels=labels(), results=out)))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# controls
# ---------------------------------------------------------------------------------------------------------------------
def selftest():
    """(1) the cave columns of this runner == ds_time.run (the D designer's runner) bit for bit on the same configs and
    scenario -- the extension changed nothing it did not mean to; (2) the zero-cave columns == harness_time.run on the
    original LaneVec with the same rows, where the sensors agree (rate sensor 'ema' is ds_time's; HT.run uses w3, so the
    A columns are compared with D off, Kd = 0, which makes the rate operand irrelevant); (3) P1 == D2a and F1 == B0r
    byte-identical lane configs."""
    import ds_selftest as ST
    import ds_final as DF
    lines = []
    cc = cave_columns()
    cfgs = [c for _, c in cc]
    for nm, v in (("rh", 8.0), ("ov_fade", 3.1), ("sen_L16", 19.0), ("s05", 26.9)):
        scn = scenario(nm, v)
        r1 = run(scn, cfgs, [], "nominal", v)
        r2 = DT.run(scn, cfgs, DT.member("nominal"), v)
        d = int(np.abs(r1["T"].astype(int) - r2["T"].astype(int)).max())
        dth = float(np.abs(r1["th"] - r2["th"]).max())
        lines.append(f"CONTROL 1 {nm}@{v}: this runner vs ds_time.run, {len(cfgs)} cave columns: max|dT| {d}, "
                     f"max|dtheta| {dth:.2e}  {'OK' if d == 0 and dth == 0 else 'FAIL'}")
    # (2) A columns vs harness_time.run with the original LaneVec (Kd 0 so the rate sensor model drops out)
    rows = a_rows(12.5)
    for rr in rows:
        rr.update(kdY=(0, 0, 0, 0), DCL=0, d_rate=False)
    scn = scenario("rh", 12.5)
    rA = run(scn, [], rows, "nominal", 12.5)
    keep = HT.LaneVec
    HT.LaneVec = _LANEVEC_ORIG
    try:
        rB = HT.run(HT.scenario("rh", 12.5), HT.Cfg(rows), member("nominal"), 12.5)
    finally:
        HT.LaneVec = keep
    d = int(np.abs(rA["T"].astype(int) - rB["T"].astype(int)).max())
    lines.append(f"CONTROL 2 rh@12.5 zero-cave columns (Kd 0) vs harness_time.run/LaneVec: max|dT| {d}  "
                 f"{'OK' if d == 0 else 'DIFF (expected only if the angle sensors differ)'}")
    tabs = R.tables()
    p1 = R.lane_cfg("P1", tabs["P1"])
    d2a = ST.lane_cfg(DF.CANDS["D2a"], [tuple(r) for r in SF.DS_ROWS["D2a"]])
    f1 = R.lane_cfg("F1", tabs["F1"])
    b0r = ST.lane_cfg(DF.CANDS["B0r"], [tuple(r) for r in SF.DS_ROWS["B0r"]])
    lines.append(f"CONTROL 3 P1 cfg == D2a cfg: {p1 == d2a}; F1 cfg == B0r cfg: {f1 == b0r}")
    out = "\n".join(lines)
    print(out)
    (R.HERE / "score_time_selftest.txt").write_text(out + "\n", encoding="utf-8")


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "run"
    if w == "selftest":
        selftest()
    elif w == "run":
        quick = "--quick" in sys.argv
        if quick:
            run_suite(("rh", "s02", "tmo", "cs", "db", "hard"), (8.0, 26.9), ("nominal",), "quick")
        else:
            run_suite(SCENS, SPEEDS, MEMBERS, "full")
    elif w == "dense":
        sp = tuple(round(x, 2) for x in np.arange(3.0, 30.01, 0.25))
        run_suite(("s02", "rh", "ssm"), sp, ("nominal", "bc"), "dense")
    elif w == "dense2":
        sp = tuple(round(x, 2) for x in np.arange(3.0, 30.01, 0.25))
        run_suite(("s02", "rh", "ssm"), sp, ("nominal+h10", "F_hi"), "dense2")
