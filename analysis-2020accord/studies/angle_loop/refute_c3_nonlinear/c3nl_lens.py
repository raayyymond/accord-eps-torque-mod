# -*- coding: utf-8 -*-
r"""c3nl_lens.py -- the C3 NONLINEAR lens: scenarios the common time scorer does NOT run, on my independent loop
(c3nl_sim, controlled bit-exact against the scorer's run() in c3nl_control K4).  ANALYSIS ONLY.

SCENARIOS (members nominal / bc / F_hi / b_lo*J_hi; impls C3-P, C3-F and the references P2, E2-A3;
speeds 3, 5, 8.00..30.00 every 0.25 + 11.9, 26.9):
  out_*    OUTWARD light hand (the direction the scorer never runs): holding the turn Ah, a stiff hand (Kh 2000, Bh 30,
           the scorer's own hand model) takes the wheel FURTHER into the turn to m*Ah over 0.3 s and holds it, word
           +sg*w (w 400 / 511, below the 512 freeze) for 1 s or 3 s, then releases (word to 0 in 30 ms).
  nudge_*  straight road (sp 0): the same stiff light hand nudges the wheel to d = 2 / 5 deg, holds 1 / 3 s, releases.
  kap_*    the outward hand read by a CONSISTENT sensor: word = hand force / kappa_T (kappa_T 0.6 / 2.0 T per word).
  tsrc_*   a TORQUE-SOURCE outward hand: +sg*Th (Th 150 / 300 T) for 1 / 3 s, word = Th (kappa_T 1), release in 50 ms.
  part_*   INWARD partial drag to 0.5*Ah (the scorer drags only to 0), word 400 / 511, 1 / 3 s.
  scurve_* an S-bend: sp = A sin(2 pi 0.1 t), A from a_lat 1.5 / 2.0 m/s^2 (L 2.83, SR 16), 25 s.
  rev_*    a held-turn REVERSAL: +A (a_lat 1.5) for 6 s, 1.5 s transition to -A, hold 6 s.
  small_*  small corrections the scorer does not run: +-0.3 deg 0.1 Hz, +-0.5 deg 0.2 Hz, +-1 deg 0.3 Hz.
  zero_*   straight-road hold: a crosswind/crown step d = 100..500 T at sp 0 (steady error; M-C3-9), and 30 s of
           0.5-30 Hz road noise 15 T rms at sp 0 (hunt / dwell at centre).
  aged_*   the scorer's own ov_lt511 / ov_fm2400 / th(a 2.5) / s10_02 with the +h10 sensor age (ages 11-20).
usage: python c3nl_lens.py run [procs] [scn-prefix,...] | list"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402

OUTD = S.OUT / "lens"
OUTD.mkdir(parents=True, exist_ok=True)
SPEEDS = tuple(sorted(set([3.0, 5.0, 11.9, 26.9] + [round(8.0 + 0.25 * i, 2) for i in range(89)])))
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
IMPLS = ("C3-P", "C3-F", "P2", "E2-A3")


def hold_ref(Ah):
    return lambda t: Ah * np.interp(t, [0, 0.5, 1.5, 999], [0, 0, 1, 1])


def _road(B, n, rms, seed=5):
    from scipy import signal
    rng = np.random.default_rng(seed)
    w = rng.normal(0.0, 1.0, (n + 2000, B))
    sos = signal.butter(2, [0.5, 30.0], "bandpass", fs=1000.0, output="sos")
    y = signal.sosfilt(sos, w, axis=0)[2000:]
    return (y / y.std(0, keepdims=True) * rms).astype(np.float32)


def build(name, cols):
    """returns (Scn, meta)."""
    B = len(cols)
    v = np.array([c["v"] for c in cols])
    A = np.array([S.A_turn(x) for x in v])
    Ah = 0.5 * A
    sg = np.sign(Ah)
    p = name.split("_")
    kind = p[0]
    if kind in ("out", "kap", "part"):
        # out_<m>_<w>_<hold> | kap_<m>_<kappa>_<hold> | part_<frac>_<w>_<hold>
        m = float(p[1])
        hold = float(p[3])
        tg, tr = 2.5, 0.3
        trel = tg + tr + hold
        target = m * Ah
        if kind == "kap":
            kap = float(p[2])
        else:
            w = float(p[2])
            word_sign = 1.0 if kind == "out" else -1.0       # outward: word with the turn; inward: against it

        def hand(t):
            if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
                return None
            fr = min(1.0, (t - tg) / tr)
            return (np.full(B, 2000.0), np.full(B, 30.0), Ah + fr * (target - Ah))

        if kind == "kap":
            def tq(t, th, om, hf):
                if tg <= t < trel:
                    return hf / kap
                if trel <= t < trel + 0.03:
                    return 0.0 * hf
                return 0.0 * hf
        else:
            def tq(t, th, om, hf):
                if tg <= t < trel:
                    return word_sign * sg * w * min(1.0, (t - tg) / tr)
                if trel <= t < trel + 0.03:
                    return word_sign * sg * w * (1 - (t - trel) / 0.03)
                return 0.0 * sg
        return S.Scn(dur=trel + 3.5, ref=hold_ref(Ah), tq=tq, hand=hand), dict(t_rel=trel, Ah=Ah, target=target)
    if kind == "knudge":                                   # knudge_<d>_<kappa_T>_<hold>: consistent-sensor nudge
        d = float(p[1]) * np.ones(B)
        kap = float(p[2])
        hold = float(p[3])
        tg, tr = 1.0, 0.3
        trel = tg + tr + hold

        def hand(t):
            if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
                return None
            fr = min(1.0, (t - tg) / tr)
            return (np.full(B, 2000.0), np.full(B, 30.0), fr * d)

        def tq(t, th, om, hf):
            return hf / kap if tg <= t < trel else 0.0 * hf
        return S.Scn(dur=trel + 3.5, ref=lambda t: np.zeros(B), tq=tq, hand=hand), dict(t_rel=trel, d=d)
    if kind == "tnudge":                                   # tnudge_<Th>_<hold>: torque-source nudge, word = Th
        Th = float(p[1])
        hold = float(p[2])
        T1 = 1.0
        T2 = T1 + 0.2 + hold

        def uext(t):
            if T1 <= t < T2:
                return Th * min(1.0, (t - T1) / 0.2) * np.ones(B)
            if T2 <= t < T2 + 0.05:
                return Th * (1 - (t - T2) / 0.05) * np.ones(B)
            return np.zeros(B)
        return S.Scn(dur=T2 + 3.5, ref=lambda t: np.zeros(B), uext=uext,
                     tq=lambda t, th, om, hf: np.asarray(uext(t))), dict(t_rel=T2, d=np.ones(B))
    if kind == "nudge":
        d = float(p[1]) * np.ones(B)
        w = float(p[2])
        hold = float(p[3])
        tg, tr = 1.0, 0.3
        trel = tg + tr + hold

        def hand(t):
            if not (int(round(tg * 1000)) <= int(round(t * 1000)) < int(round(trel * 1000))):
                return None
            fr = min(1.0, (t - tg) / tr)
            return (np.full(B, 2000.0), np.full(B, 30.0), fr * d)

        def tq(t, th, om, hf):
            if tg <= t < trel:
                return w * min(1.0, (t - tg) / tr) * np.ones(B)
            if trel <= t < trel + 0.03:
                return w * (1 - (t - trel) / 0.03) * np.ones(B)
            return np.zeros(B)
        return S.Scn(dur=trel + 3.5, ref=lambda t: np.zeros(B), tq=tq, hand=hand), dict(t_rel=trel, d=d)
    if kind == "tsrc":
        Th = float(p[1])
        hold = float(p[2])
        T1 = 2.5
        T2 = T1 + 0.2 + hold

        def uext(t):
            if T1 <= t < T2:
                return sg * Th * min(1.0, (t - T1) / 0.2)
            if T2 <= t < T2 + 0.05:
                return sg * Th * (1 - (t - T2) / 0.05)
            return 0.0 * sg

        def tq(t, th, om, hf):
            return np.asarray(uext(t))                       # kappa_T = 1: the word reads the hand torque
        return S.Scn(dur=T2 + 3.5, ref=hold_ref(Ah), uext=uext, tq=tq), dict(t_rel=T2, Ah=Ah)
    if kind == "scurve":
        a = float(p[1])
        Aa = np.array([S.tgt_alat(x, a) for x in v])
        return S.Scn(dur=25.0, ref=lambda t: Aa * np.sin(2 * np.pi * 0.1 * t)), dict(A=Aa, f=0.1, t0=5.0)
    if kind == "rev":
        a = float(p[1])
        Aa = np.array([S.tgt_alat(x, a) for x in v])
        return S.Scn(dur=16.0, ref=lambda t: Aa * np.interp(t, [0, 0.5, 2.0, 8.0, 9.5, 99], [0, 0, 1, 1, -1, -1])), \
            dict(A=Aa)
    if kind == "small":
        amp, f = float(p[1]), float(p[2])
        return S.Scn(dur=4.0 / f, ref=lambda t: amp * np.sin(2 * np.pi * f * t) * np.ones(B)), dict(f=f, t0=1.0 / f)
    if kind == "zero":
        if p[1] == "wind":
            d = float(p[2])
            return S.Scn(dur=12.0, ref=lambda t: np.zeros(B),
                         uext=lambda t: d * np.interp(t, [0, 2.0, 2.5, 99], [0, 0, 1, 1]) * np.ones(B)), dict(d=d)
        rd = _road(B, 31600, 15.0)
        return S.Scn(dur=31.5, ref=lambda t: np.zeros(B), uext=lambda t: rd[int(round(t * 1000))]), dict()
    raise KeyError(name)


SCN = []
for m in ("1.5", "2"):
    for w in ("400", "511"):
        for h in ("1", "3"):
            SCN.append(f"out_{m}_{w}_{h}")
for k in ("0.6", "2"):
    for h in ("1", "3"):
        SCN.append(f"kap_1.5_{k}_{h}")
        SCN.append(f"kap_2_{k}_{h}")
for th_ in ("150", "300"):
    for h in ("1", "3"):
        SCN.append(f"tsrc_{th_}_{h}")
for d in ("2", "5"):
    for w in ("400", "511"):
        for h in ("1", "3"):
            SCN.append(f"nudge_{d}_{w}_{h}")
for w in ("400", "511"):
    for h in ("1", "3"):
        SCN.append(f"part_0.5_{w}_{h}")
for d in ("2", "5"):
    for k in ("0.6", "2"):
        SCN.append(f"knudge_{d}_{k}_3")
for th_ in ("150", "300"):
    SCN.append(f"tnudge_{th_}_3")
SCN += ["scurve_1.5", "scurve_2", "rev_1.5", "rev_2", "small_0.3_0.1", "small_0.5_0.2", "small_1_0.3",
        "zero_wind_100", "zero_wind_200", "zero_wind_300", "zero_wind_500", "zero_road"]


def metrics(name, meta, r, cols):
    th, om, T = r["th"].astype(float), r["om"].astype(float), r["T"].astype(float)
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    plan = r["plan"].astype(float)
    plan1k = np.repeat(plan, 10, axis=0)[:n]
    kind = name.split("_")[0]
    m = dict(wraps=float(r["wraps"]))
    if kind in ("out", "kap", "part", "tsrc"):
        trel, Ah = meta["t_rel"], meta["Ah"]
        sg = np.sign(Ah)
        i_r = int(trel * 1000)
        w = tt >= trel
        m["under"] = np.max((Ah - th[w]) * sg, 0)           # toward centre past the setpoint (the 'droop' lurch)
        m["over"] = np.max((th[w] - Ah) * sg, 0)            # past the setpoint into the turn
        m["th_rel"] = th[i_r - 1]
        m["I_rel"] = r["I"][i_r - 2].astype(float)
        m["frz_hold"] = r["frz"][int((trel - 0.5) * 1000):i_r].mean(0).astype(float)
        m["farb_hold"] = r["farb"][int((trel - 0.5) * 1000):i_r].mean(0).astype(float)
        m["hf_rel"] = np.abs(r["hf"][i_r - 2]).astype(float)
        m["settle_err"] = np.abs(th[-500:] - Ah).max(0)
        return m
    if kind in ("nudge", "knudge", "tnudge"):
        trel, d = meta["t_rel"], meta["d"]
        i_r = int(trel * 1000)
        w = tt >= trel
        m["over"] = np.max(-th[w] * np.sign(d), 0)          # past centre to the other side
        m["th_rel"] = th[i_r - 1]
        m["I_rel"] = r["I"][i_r - 2].astype(float)
        m["hf_rel"] = np.abs(r["hf"][i_r - 2]).astype(float)
        m["settle_err"] = np.abs(th[-500:]).max(0)
        return m
    if kind in ("scurve", "rev"):
        w = tt >= (5.0 if kind == "scurve" else 2.5)
        e = (plan1k - th)[w]
        m["e_max"] = np.abs(e).max(0)
        Ax = meta["A"]
        m["e_max_rel"] = m["e_max"] / np.abs(Ax)
        X = plan1k[w] - plan1k[w].mean(0)
        Y = th[w] - th[w].mean(0)
        m["slope"] = (X * Y).sum(0) / np.maximum((X ** 2).sum(0), 1e-12)
        if kind == "rev":
            h1 = (tt >= 6.0) & (tt < 8.0)
            h2 = (tt >= 14.0) & (tt < 16.0)
            m["hold1"] = th[h1].mean(0) / Ax
            m["hold2"] = -th[h2].mean(0) / Ax
            m["ovs2"] = np.max(-(th[tt >= 9.5]) / Ax - 1.0, 0)
        idx = (np.arange(r["wire"].shape[0]) * 10 + 4).clip(0, n - 1)
        fw = idx * 1e-3 >= (5.0 if kind == "scurve" else 2.5)
        ev, jm, _ = S.dwell_jump(om[idx][fw], th[idx][fw], plan1k[idx][fw])
        m["dj"], m["dj_max"] = ev.astype(float), jm
        return m
    if kind == "small":
        f, t0 = meta["f"], meta["t0"]
        idx = (np.arange(r["wire"].shape[0]) * 10 + 4).clip(0, n - 1)
        fw = idx * 1e-3 >= t0
        X = plan1k[idx][fw]
        Yw = r["wire"].astype(float)[fw] / 10.0
        xm = X - X.mean(0)
        m["gain"] = (xm * (Yw - Yw.mean(0))).sum(0) / np.maximum((xm ** 2).sum(0), 1e-12)
        ev, jm, _ = S.dwell_jump(om[idx][fw], th[idx][fw], plan1k[idx][fw])
        m["dj"], m["dj_max"] = ev.astype(float), jm
        mv = np.abs(np.gradient(plan1k[idx][fw], axis=0) * 100.0) > 0.05
        m["stick_pct"] = 100.0 * ((om[idx][fw] == 0.0) & mv).sum(0) / np.maximum(mv.sum(0), 1)
        return m
    if kind == "zero":
        w = tt >= (8.0 if "wind" in name else 1.5)
        m["e_mean"] = np.abs(th[w].mean(0))
        m["e_max"] = np.abs(th[w]).max(0)
        m["I_end"] = r["I"][-1].astype(float)
        m["farb_end"] = r["farb"][-1000:].mean(0).astype(float)
        if "road" in name:
            sgn = np.sign(np.where(np.abs(om[w]) > 0.2, om[w], 0.0))
            rev = np.zeros(th.shape[1])
            for j in range(th.shape[1]):
                s_ = sgn[:, j][sgn[:, j] != 0]
                rev[j] = np.count_nonzero(np.diff(s_) != 0) if len(s_) > 1 else 0
            m["rev"] = rev
            m["p2p"] = th[w].max(0) - th[w].min(0)
            idx = (np.arange(r["wire"].shape[0]) * 10 + 4).clip(0, n - 1)
            fw = idx * 1e-3 >= 1.5
            zz = np.zeros_like(plan1k[idx][fw])
            ev, jm, _ = S.dwell_jump(om[idx][fw], th[idx][fw], zz + 0.0)
            m["dj"] = ev.astype(float)
        return m
    raise KeyError(name)


def columns(name, member, age=0):
    return [dict(impl=i, member=member, v=v, age=age) for v in SPEEDS for i in IMPLS]


def job(args):
    name, member, age = args
    cols = columns(name, member, age)
    scn, meta = build(name, cols)
    t0 = time.time()
    r = S.run(cols, scn)
    m = metrics(name, meta, r, cols)
    keys = [dict(impl=c["impl"], v=c["v"]) for c in cols]
    return dict(scn=name, member=member, age=age, keys=keys, sec=time.time() - t0,
                m={k: np.asarray(x, float).tolist() for k, x in m.items()})


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        print(len(SCN), SCN)
        return
    procs = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    pref = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    scns = [s for s in SCN if pref is None or any(s.startswith(q) for q in pref)]
    jobs = [(s, mb, 0) for s in scns for mb in MEMBERS]
    t0 = time.time()
    print(f"{len(jobs)} jobs", flush=True)
    with Pool(procs) as pool:
        for i, r in enumerate(pool.imap_unordered(job, jobs, chunksize=1)):
            fn = OUTD / f"{r['scn']}__{r['member'].replace('*', 'x')}__a{r['age']}.json"
            fn.write_text(json.dumps(r))
            if (i + 1) % 8 == 0 or i + 1 == len(jobs):
                print(f"  {i + 1}/{len(jobs)} {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
