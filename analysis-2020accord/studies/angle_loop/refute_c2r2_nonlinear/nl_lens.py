# -*- coding: utf-8 -*-
r"""nl_lens.py -- the NONLINEAR lens on C2 rev 2 (P2, F2 of rev2-A; D2a, B0r of rev2-B), run on my own simulation
(nl_sim: lane = the listed instructions, cave = the bytes via nl_cave, plant = my Karnopp integrator; CONTROL:
ctl_vs_designers.py reproduces the designers' engine bit-for-bit on deterministic inputs).  ANALYSIS ONLY.

Members nominal, bc, F_hi, b_lo*J_hi; hold ages native (1..10) and +h10 (11..20); speeds 8.00..30.00 every 0.25 m/s plus
the knots 11.9 / 26.9 (8.0 / 17.0 are on the grid) and 3.1 / 5.0 for context.  Amplitudes: harness A_TURN, log-interpolated.

usage: python nl_lens.py run [procs]     -> _scratch/angle_loop/refute-c2r2-nonlinear/lens_<scn>_<member>.npz
       python nl_lens.py report          -> lens_report.txt (tables quoted in the REFUTE report)"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nl_sim as S  # noqa: E402

OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "refute-c2r2-nonlinear"
OUT.mkdir(parents=True, exist_ok=True)
IMPLS = ("P2", "F2", "D2a", "B0r")
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
SPEEDS = tuple(sorted(set([3.1, 5.0, 11.9, 26.9] + [round(8.0 + 0.25 * i, 2) for i in range(89)])))
AGES = (0, 10)
_AT = {3.0: 90.0, 5.0: 50.0, 8.0: 30.0, 12.5: 12.0, 19.0: 5.0, 26.0: 3.0, 30.0: 2.5}
_K = sorted(_AT)


def A_turn(v):
    return float(np.exp(np.interp(v, _K, [np.log(_AT[k]) for k in _K])))


def cols_for(member):
    return [dict(impl=i, member=member, v=v, age=a) for a in AGES for v in SPEEDS for i in IMPLS]


def load_at(c, A):
    J, b, k, sat, Fc, Fs, tau = S.params(c["member"], c["v"])
    return k * sat * np.tanh(A / sat)


# ------------------------------------------------------------------------------------------------------------------
def scenario(name, cols):
    B = len(cols)
    A = np.array([A_turn(c["v"]) for c in cols])
    Ah = 0.5 * A
    if name == "rh":            # ramp 1 s, hold 6 s, swing to -A over 2 s, hold 6 s, back over 1 s, hold 3 s
        knots_t = [0, 0.5, 1.5, 7.5, 9.5, 15.5, 16.5, 19.5]
        knots_y = [0, 0, 1, 1, -1, -1, 0, 0]
        return S.Scn(dur=19.5, ref=lambda t: A * np.interp(t, knots_t, knots_y)), dict(
            holds=[(1.5, 7.5, A), (9.5, 15.5, -A), (16.5, 19.5, 0 * A)])
    if name in ("s02", "s05"):
        f = 0.2 if name == "s02" else 0.5
        dur = (3.0 if name == "s02" else 5.0) / f
        return S.Scn(dur=dur, ref=lambda t: 0.3 * A * np.sin(2 * np.pi * f * t)), dict(f=f, t0=1.0 / f)
    if name.startswith("mic"):   # small corrections: mic03 = +-0.3 deg 0.1 Hz ; mic05 = +-0.5 deg 0.2 Hz ; mic10 = +-1 deg 0.3 Hz
        amp, f = {"mic03": (0.3, 0.1), "mic05": (0.5, 0.2), "mic10": (1.0, 0.3)}[name]
        dur = 3.0 / f + 1.0 / f
        return S.Scn(dur=dur, ref=lambda t: amp * np.sin(2 * np.pi * f * t) * np.ones(B)), dict(f=f, t0=1.0 / f, amp=amp)
    if name == "db":             # creep 0 -> 2 deg at 0.2 deg/s
        return S.Scn(dur=13.0, ref=lambda t: np.clip(0.2 * (t - 1.0), 0, 2.0) * np.ones(B)), dict()
    if name.startswith("ov_"):   # hold Ah, hand grabs at 2.5 s (ramp 0.3 s), holds 3 s, releases (word to 0 in 30 ms)
        tg, tr, th_ = 2.5, 0.3, 3.0
        trel = tg + tr + th_
        kind = name[3:]
        word = {"firm": 2400.0, "lt400": 400.0, "lt511": 511.0, "src": 500.0, "srcF": 500.0, "co400": 400.0,
                "co700": 700.0}[kind]

        def tq(t, th, om, word=word):
            if tg <= t < trel:
                return word * min(1.0, (t - tg) / tr)
            if trel <= t < trel + 0.03:
                return word * (1 - (t - trel) / 0.03)
            return 0.0
        ref = lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1])  # noqa: E731
        meta = dict(t_rel=trel, Ah=Ah)
        if kind in ("firm", "lt400", "lt511"):          # stiff position hand holding the wheel Ah back toward 0
            st = {}

            def hand(t):
                n = int(round(t * 1000))
                if not (int(tg * 1000) <= n < int(trel * 1000)):
                    return None
                if "g" not in st:
                    st["g"] = Ah.copy()
                fr = min(1.0, (t - tg) / tr)
                return (np.full(B, 2000.0), np.full(B, 30.0), Ah - fr * Ah)
            return S.Scn(dur=trel + 3.5, ref=ref, tq=tq, hand=hand), meta
        load = np.array([load_at(c, a) for c, a in zip(cols, Ah)])
        if kind == "src":                                # pure torque opposing the turn = 0.5 x spring load (light, word 500)
            mag = -0.5 * load * np.sign(Ah)
        elif kind == "srcF":                             # pure opposing torque of 300 T counts (word 500)
            mag = -300.0 * np.sign(Ah)
        else:                                            # co-steer: helping torque 0.5 x load
            mag = 0.5 * load * np.sign(Ah)

        def uext(t, mag=mag):
            if tg <= t < trel:
                return mag * min(1.0, (t - tg) / 0.2)
            if trel <= t < trel + 0.05:
                return mag * (1 - (t - trel) / 0.05)
            return 0.0 * mag
        return S.Scn(dur=trel + 3.5, ref=ref, tq=tq, uext=uext), meta
    if name == "eng":            # engage under load: hand holds th0 (Ah) until 2.3 s, engage at 2.0 s, fork holds th_meas
        TE = 2.0
        th0 = Ah.copy()

        def hand(t):
            if t < TE + 0.3:
                return (np.full(B, 2000.0), np.full(B, 30.0), th0)
            fr = min(1.0, (t - TE - 0.3) / 0.2)
            if fr >= 1.0:
                return None
            return (np.full(B, 2000.0 * (1 - fr)), np.full(B, 30.0 * (1 - fr)), th0)
        return S.Scn(dur=TE + 5.0, ref=lambda t: 0 * A, hand=hand, events=((TE, "engage"),), mode0="off", th0=th0,
                     sp_meas_until=TE + 0.011, sp_hold_from=TE + 0.011), dict(t_eng=TE, th0=th0)
    if name == "tmo":            # fork stops at 3.0 s in a held turn: setpoint held 510 ms, then sentinel/0xFF
        ts = 3.0
        return S.Scn(dur=ts + 2.5, ref=lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1]),
                     events=((ts, "stop"), (ts + 0.510, "fault"))), dict(t_stop=ts, t_fault=ts + 0.510)
    if name == "tmos":           # fork stops mid-sinusoid (0.3 A at 0.2 Hz, at the zero crossing = max rate)
        ts = 5.0
        return S.Scn(dur=ts + 2.5, ref=lambda t: 0.3 * A * np.sin(2 * np.pi * 0.2 * t),
                     events=((ts, "stop"), (ts + 0.510, "fault"))), dict(t_stop=ts, t_fault=ts + 0.510)
    if name == "sen":            # 0xE4 fault sentinel during a held turn
        tf = 3.0
        return S.Scn(dur=tf + 2.5, ref=lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1]),
                     events=((tf, "fault"),)), dict(t_fault=tf)
    if name == "dis":            # request drop during a held turn (fork then sends the measured angle)
        td = 3.0
        return S.Scn(dur=td + 2.5, ref=lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 99], [0, 0, 1, 1]),
                     events=((td, "dis"),)), dict(t_dis=td)
    raise KeyError(name)


def metrics(name, meta, r, cols):
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    sp = r["sp"].astype(float) / 40.0
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    m = dict(wraps=np.full(len(cols), r["wraps"]), peakT=np.abs(T).max(0))
    if name == "rh":
        ratio, sl, rev, hf, ovs = [], [], [], [], []
        for (a, b, tgt) in meta["holds"]:
            w = (tt >= a + 0.5) & (tt < b)
            if np.any(tgt != 0):
                wr = (tt >= b - 1.5) & (tt < b)
                ratio.append((th[wr] / tgt).mean(0))
                ovs.append(np.max((th[(tt >= a) & (tt < b)] - tgt) * np.sign(tgt), 0))
            sl.append(S.slips(th[w], om[w]))
            sg = np.sign(np.where(np.abs(om[w]) > 0.2, om[w], 0.0))
            rv = np.zeros(th.shape[1], int)
            for j in range(th.shape[1]):
                s_ = sg[:, j][sg[:, j] != 0]
                rv[j] = int(np.count_nonzero(np.diff(s_) != 0)) if len(s_) > 1 else 0
            rev.append(rv)
            hf.append(np.sqrt(np.mean(S.bp(T, 5, 30)[w] ** 2, 0)))
        m.update(hold=np.min(ratio, 0), slips=np.sum(sl, 0), slips_max_hold=np.max(sl, 0), rev=np.max(rev, 0),
                 T_hf=np.max(hf, 0), ovs=np.max(ovs, 0))
    elif name in ("s02", "s05") or name.startswith("mic"):
        t0 = meta["t0"]
        m["gain"] = S.wire_gain(r, t0)
        f = meta["f"]
        w = tt >= t0
        s_ = np.sin(2 * np.pi * f * tt[w])[:, None]
        c_ = np.cos(2 * np.pi * f * tt[w])[:, None]
        ra, rb = 2 * np.mean(sp[w] * s_, 0), 2 * np.mean(sp[w] * c_, 0)
        ya, yb = 2 * np.mean(th[w] * s_, 0), 2 * np.mean(th[w] * c_, 0)
        m["fit_gain"] = np.hypot(ya, yb) / np.maximum(np.hypot(ra, rb), 1e-9)
        idx = (np.arange(r["wire"].shape[0]) * 10 + 4).clip(0, n - 1)
        fw = idx * 1e-3 >= t0
        ev, jm = S.dwell_jump(om[idx][fw], th[idx][fw], sp[idx][fw])
        m["dj"], m["dj_max"] = ev, jm
        mv = np.abs(np.gradient(sp[idx][fw], axis=0) * 100.0) > 0.05
        m["stick_pct"] = 100.0 * ((om[idx][fw] == 0.0) & mv).sum(0) / np.maximum(mv.sum(0), 1)
        m["T_hf"] = np.sqrt(np.mean(S.bp(T, 5, 30)[w] ** 2, 0))
    elif name == "db":
        w = tt >= 3.0
        m["db_lag"] = (sp - th)[w].max(0)
        m["db_slips"] = S.slips(th[w], om[w])
    elif name.startswith("ov_"):
        trel = meta["t_rel"]
        Ah = meta["Ah"]
        w = tt >= trel
        m["lurch"] = np.max((th[w] - Ah) * np.sign(Ah), 0)              # beyond the setpoint
        m["droop"] = np.max((Ah - th[w]) * np.sign(Ah), 0)              # behind the setpoint after release
        m["swing"] = th[w].max(0) - th[w].min(0)
        m["th_rel"] = th[int(trel * 1000) - 1]
        m["I_rel"] = r["I"][int(trel * 1000) - 2].astype(float)
        m["frz_hold"] = r["frz"][int(trel * 1000) - 500:int(trel * 1000) - 1].mean(0)
    elif name == "eng":
        w = tt >= meta["t_eng"]
        sg = np.sign(meta["th0"])
        e = (sp - th)[w] * sg
        m["droop"] = (-e).max(0)          # wheel falls back toward centre behind the held command
        m["ovs"] = e.max(0)
    elif name in ("tmo", "tmos"):
        i0 = int(meta["t_stop"] * 1000) - 1
        hold = (tt >= meta["t_stop"]) & (tt < meta["t_fault"])
        m["hold_dev"] = np.abs(th[hold] - th[i0]).max(0)
        m["T_after"] = np.abs(T[tt >= meta["t_fault"] + 0.25]).max(0)
        m["exc"] = np.abs(th[tt >= meta["t_stop"]] - th[i0]).max(0)
    elif name == "sen":
        i0 = int(meta["t_fault"] * 1000) - 1
        w = tt >= meta["t_fault"]
        m["sen_peakT_after_50ms"] = np.abs(T[tt >= meta["t_fault"] + 0.05]).max(0)
        m["sen_exc"] = np.abs(th[w] - th[i0]).max(0)
    elif name == "dis":
        i0 = int(meta["t_dis"] * 1000) - 1
        w = tt >= meta["t_dis"]
        m["dis_exc"] = np.abs(th[w] - th[i0]).max(0)
        m["dis_T_after_150ms"] = np.abs(T[tt >= meta["t_dis"] + 0.15]).max(0)
    return {k: np.asarray(v, float) for k, v in m.items()}


SCENS = ("rh", "s02", "s05", "mic03", "mic05", "mic10", "db", "ov_firm", "ov_lt400", "ov_lt511", "ov_src", "ov_srcF",
         "ov_co400", "ov_co700", "eng", "tmo", "tmos", "sen", "dis")


def job(args):
    name, member = args
    cols = cols_for(member)
    scn, meta = scenario(name, cols)
    t0 = time.time()
    r = S.run(cols, scn)
    m = metrics(name, meta, r, cols)
    np.savez_compressed(OUT / f"lens_{name}_{member.replace('*', 'x')}.npz", **m)
    return name, member, time.time() - t0


def run_all(procs=6, scens=SCENS, members=MEMBERS):
    jobs = [(s, m) for s in scens for m in members]
    t0 = time.time()
    with Pool(procs) as p:
        for i, (s, mb, sec) in enumerate(p.imap_unordered(job, jobs)):
            print(f"  [{i + 1}/{len(jobs)}] {s} {mb} {sec:.0f} s (total {time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "run"
    if w == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        sc = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else SCENS
        run_all(procs, sc)
