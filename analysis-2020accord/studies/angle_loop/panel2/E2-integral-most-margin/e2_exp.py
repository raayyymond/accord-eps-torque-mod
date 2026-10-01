# -*- coding: utf-8 -*-
r"""e2_exp.py -- designer E2's experiments on THE COMMON TIME SCORER (c2/rev2A/score_time.run, extended additively:
lane_cls / ramp_in / tq_cols, CONTROL 1-3 re-run OK after the edit) with E2Lane (CONTROL E2-0: defaults == DSLane bit
for bit).  ANALYSIS ONLY.

SCENARIOS ADDED HERE (each defined below; the brief's and the refuters' definitions where they exist):
  th:<alat|deg>   TURN-HOLD sized from r71b or by lateral acceleration (nl_turnhold's form: ramp 1.5 s from 0.5 s, hold
                  8 s, hold ratio = mean(theta)/target over 9-11 s); target deg = alat * L * SR / v^2 (L 2.83, SR 16)
  rr:<band>:<i>   THE GOAL'S TRACKING METRIC on r71b's own engaged hands-not-pressed angle paths (nl_realref's form: the
                  run's measured steering angle is the setpoint path, simulated at the run's median speed; slope = OLS
                  of the 0.5 Hz zero-phase-LPF wheel angle on the LPF reference, runs concatenated per band, from 4 s);
                  'rrq' = the same with r71b's OWN measured driver-torque word replayed time-aligned (carState torque
                  x 128/125 = gp-0x4f60, EVIDENCE e2_data_r71b (0)) -- the hands-off reaction and the resting hand
  lh:<w>          LIGHT STIFF HAND, the brief's convention (ds_time ov_light: grab at 2.5 s, take the wheel to 0 from the
                  held 0.5 A_TURN over 0.3 s, hold 3 s, release in 30 ms) with the word SIGNED as the hand pushes:
                  gp-0x4f60 = -w (the hand pushes -theta; EVIDENCE sign, e2_data_r71b (1))
  lk:<kappa>      the same stiff hand with a CONSISTENT sensor: gp-0x4f60 = (hand torque on the wheel, T counts) / kappa
                  (kappa = T counts per torque word, unknown on this car: swept 0.15 / 0.6 / 2.0)
  ls:<F>:<kappa>  TORQUE-SOURCE light hand: a constant -F T counts for 3 s (ramp 0.2 s in, 30 ms out), word = -F/kappa
  eng / eng2      ENGAGE UNDER LOAD (ds_time eng_load), stock ramp-in 33/tick (0.99 s) / the gp-0x6803 == 2 arm 328
                  (0.10 s); the fade arm follows the column's fade2 key
  ov / ov2        FIRM HAND (harness ov_fade, word 2400 SIGNED -2400), stock / 6803 == 2 ramp
usage: python e2_exp.py <experiment>   (see EXPERIMENTS at the bottom)"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e2_common import ST, R, OUT, KIT  # noqa: E402
import e2_lane as EL  # noqa: E402
import harness_time as HT  # noqa: E402
import ds_time as DT  # noqa: E402

SRC = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"
BANDS = ((8.0, 15.0, "8-15"), (15.0, 22.0, "15-22"), (22.0, 99.0, ">22"))
L_WB, SR_C = 2.83, 16.0


# ---------------------------------------------------------------------------------------------------------------------
# columns
# ---------------------------------------------------------------------------------------------------------------------
def base():
    tabs = R.tables()
    return R.lane_cfg("P2", tabs["P2"])


def col(**kw):
    c = base()
    c.update(kw)
    return c


# ---------------------------------------------------------------------------------------------------------------------
# r71b paths
# ---------------------------------------------------------------------------------------------------------------------
_RUNS = None


def r71b_runs():
    global _RUNS
    if _RUNS is None:
        d = np.load(SRC)
        t, v, sa, sp, st = d["t_cst"], d["vego"], d["sa_deg"], d["spress"], d["storque"]
        act = np.interp(t, d["t_cs"], d["cs_active"]) > 0.5
        fs = 1 / np.median(np.diff(t))
        out = {}
        for lo, hi, nm in BANDS:
            m = act & (v >= lo) & (v < hi) & (sp < 0.5)
            e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
            rr = [(a, b) for a, b in zip(e[::2], e[1::2]) if b - a >= 15 * fs]
            out[nm] = [(t[a:b] - t[a], sa[a:b].copy(), float(np.median(v[a:b])), st[a:b] * 128.0 / 125.0)
                       for a, b in rr]
        _RUNS = out
    return _RUNS


# ---------------------------------------------------------------------------------------------------------------------
# scenarios
# ---------------------------------------------------------------------------------------------------------------------
def scn_turnhold(v, tgt):
    return dict(name="th", v=v, dur=11.0, ref=lambda t, g=tgt: g * float(np.interp(t, [0, 0.5, 2.0, 99], [0, 0, 1, 1])),
                events=[], hand=None, c63f6=16, inactive="meas", outer="ff", tq=None, tgt=tgt)


def scn_realref(band, i, replay):
    tr, sa, vm, tqw = r71b_runs()[band][i]
    dur = float(tr[-1]) + 0.5
    fr = np.arange(0, dur, 0.01)
    REF = np.interp(fr, tr, sa, right=sa[-1])
    TQ = np.interp(fr, tr, tqw, right=0.0)
    s = dict(name="rr", v=vm, dur=dur, ref=lambda t, R_=REF: R_[min(int(round(float(t) * 100)), len(R_) - 1)],
             events=[], hand=None, c63f6=16, inactive="meas", outer="ff", th0=float(REF[0]), nlen=int(tr[-1] * 100),
             REF=REF, tq=None)
    if replay:
        s["tq"] = lambda t, Q=TQ: Q[min(int(float(t) * 100), len(Q) - 1)]
    return s


def scn_light_word(v, w):
    s = DT.scenario("ov_light400", v)
    f0 = s["tq"]
    s = dict(s, name=f"lh{w}", tq=lambda t, f0=f0, w=w: -f0(t) * (w / 400.0))
    return s


def _hand_sensor(kappa):
    def f(t, pl, tq, hh):
        if hh is None:
            return np.zeros(pl.B, np.int64)
        Kh, Bh, thh = hh
        hT = Kh * (np.asarray(thh) - pl.th) - Bh * pl.om
        return np.round(np.clip(hT / kappa, -32767, 32767)).astype(np.int64)
    return f


def scn_light_kappa(v, kappa):
    s = DT.scenario("ov_light400", v)
    s = dict(s, name=f"lk{kappa}", tq=None, tq_cols=_hand_sensor(kappa))
    return s


def scn_light_source(v, F, kappa):
    s = DT.scenario("ov_light400", v)
    tg, trel = s["t_grab"], s["t_rel"]

    def u(t, F=F, tg=tg, trel=trel):
        if t < tg or t >= trel + 0.03:
            return 0.0
        if t < trel:
            return -F * min(1.0, (t - tg) / 0.2)
        return -F * (1 - (t - trel) / 0.03)
    s = dict(s, name=f"ls{F}:{kappa}", hand=None, u_ext=u, tq=lambda t, u=u, k=kappa: u(float(t)) / k)
    return s


def scn_firm(v, ramp_in=33):
    s = HT.scenario("ov_fade", v)
    f0 = s["tq"]
    return dict(s, name="ov", tq=lambda t, f0=f0: -f0(t), ramp_in=ramp_in)


def scn_eng(v, ramp_in=33):
    s = DT.scenario("eng_load", v if v in (3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 19.0, 26.0, 30.0) else v)
    return dict(s, ramp_in=ramp_in)


def build(spec):
    kind = spec[0]
    if kind == "th":
        return scn_turnhold(spec[1], spec[2])
    if kind == "rr":
        return scn_realref(spec[1], spec[2], spec[3])
    if kind == "lh":
        return scn_light_word(spec[1], spec[2])
    if kind == "lk":
        return scn_light_kappa(spec[1], spec[2])
    if kind == "ls":
        return scn_light_source(spec[1], spec[2], spec[3])
    if kind == "ov":
        return scn_firm(spec[1], spec[2])
    if kind == "eng":
        return scn_eng(spec[1], spec[2])
    if kind == "std":
        return ST.scenario(spec[2], spec[1])
    raise KeyError(kind)


# ---------------------------------------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------------------------------------
_SOS = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")


def metrics(spec, scn, r, lane_stats):
    kind = spec[0]
    th = r["th"].astype(float)
    tt = np.arange(th.shape[0]) * 1e-3
    out = {}
    if kind == "th":
        w = (tt >= 9.0) & (tt < 11.0)
        out["hold"] = (th[w].mean(0) / scn["tgt"]).tolist()
    elif kind == "rr":
        n = scn["nlen"]
        th100 = th[::10][:n]
        out["x"] = signal.sosfiltfilt(_SOS, scn["REF"][:n])[400:].tolist()
        out["y"] = [signal.sosfiltfilt(_SOS, th100[:, j])[400:].tolist() for j in range(th.shape[1])]
    elif kind in ("lh", "lk", "ls", "ov"):
        m = HT.metrics("ov_fade", scn, r, scn["v"])
        out["lurch"] = np.asarray(m["lurch_overshoot"]).tolist()
        out["swing"] = np.asarray(m["lurch_swing"]).tolist()
        out["peakT"] = np.asarray(m["lurch_peakT"]).tolist()
        # the hand's work: max |gp-0x4f60| the sensor model produced is not stored; report theta at release
        out["th_rel"] = np.asarray(m["th_at_release"]).tolist()
        out["return_s"] = np.where(np.isfinite(m["return_s"]), m["return_s"], 99.0).tolist()
        Ah = 0.5 * HT.A_TURN[scn["v"]]
        w2 = (tt >= scn["t_rel"] + 0.5) & (tt < scn["t_rel"] + 3.0)
        out["under"] = ((Ah - th[w2]) * np.sign(Ah)).max(0).tolist()      # shortfall 0.5-3 s after release
    elif kind == "eng":
        m = DT.metrics("eng_load", scn, r, scn["v"])
        out["droop"] = np.asarray(m["droop"]).tolist()
        out["eng_ovs"] = np.asarray(m["overshoot"]).tolist()
        out["e_end"] = np.asarray(m["e_end"]).tolist()
    elif kind == "std":
        m = ST.metrics(spec[2], scn, r, spec[1])
        out = {k: np.asarray(x, float).tolist() for k, x in m.items()}
    out["frz_duty"] = lane_stats.tolist()
    out["wraps"] = int(r["wraps"])
    return out


class _Cap:
    """captures the E2Lane instance score_time.run builds, for its freeze-duty counters."""
    last = None


class E2LaneCap(EL.E2Lane):
    def __init__(self, cal, cfgs):
        super().__init__(cal, cfgs)
        _Cap.last = self


def job(args):
    spec, cols, mem = args
    scn = build(spec)
    v = scn["v"]
    t0 = time.time()
    r = ST.run(scn, cols, [], mem, v, lane_cls=E2LaneCap)
    ln = _Cap.last
    duty = ln.n_frz / np.maximum(ln.n_run, 1)
    return dict(spec=list(spec), member=mem, m=metrics(spec, scn, r, duty), sec=time.time() - t0)


def run_jobs(jobs, tag, procs=8):
    t0 = time.time()
    out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            out.append(res)
            if (i + 1) % 20 == 0 or i + 1 == len(jobs):
                print(f"  {tag}: {i + 1}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    (OUT / f"exp_{tag}.json").write_text(json.dumps(out))
    return out


def rr_slopes(res, ncol):
    """band -> member -> [slope per column] from rr results (runs concatenated per band)."""
    acc = {}
    for x in res:
        if x["spec"][0] != "rr":
            continue
        key = (x["spec"][1], bool(x["spec"][3]), x["member"])
        acc.setdefault(key, ([], [[] for _ in range(ncol)]))
        acc[key][0].append(np.array(x["m"]["x"]))
        for j in range(ncol):
            acc[key][1][j].append(np.array(x["m"]["y"][j]))
    out = {}
    for key, (X, Ys) in acc.items():
        Xc = np.concatenate(X)
        sl = []
        for j in range(ncol):
            Y = np.concatenate(Ys[j])
            b = np.linalg.lstsq(np.vstack([Xc, np.ones_like(Xc)]).T, Y, rcond=None)[0]
            sl.append(float(b[0]))
        out[key] = sl
    return out
