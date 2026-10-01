# -*- coding: utf-8 -*-
r"""c3nl_r71b.py -- the goal's tracking metric on route r71b's OWN angle paths, on my independent loop, with the run's
REAL SPEED TRACE (the common scorer simulates each run at its median speed: the G(v) dip, the ARB slope knee at
12.5 m/s and the plant's k(v) never move inside a run there).  Also: the dwell-then-jump events on the real paths,
listed one by one (the common scorer's tables show a 6.6-6.8 deg 'max snap' for C3-P on r71b that the design does not
discuss).  ANALYSIS ONLY.

Run selection = the scorer's r71b_runs(): lateral engaged (controlsState.active), steeringPressed false, >= 15 s,
banded by speed (8-15 / 15-22 / > 22 m/s on every sample).  Reference = carState.steeringAngleDeg at 100 Hz.
Metric = OLS slope (with intercept) of the 0.5 Hz zero-phase-LPF wheel angle on the LPF reference from 4 s (scorer's).
Modes: 'med' (constant median speed, = the scorer), 'vel' (the run's own vEgo(t)); 'q' = r71b's torque word replayed.
usage: python c3nl_r71b.py run [procs] | report"""
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
import c3nl_sim as S  # noqa: E402

KIT = HERE.parents[3]
SRC = KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz"
OUTD = S.OUT / "r71b"
OUTD.mkdir(parents=True, exist_ok=True)
BANDS = ((8.0, 15.0, "8-15"), (15.0, 22.0, "15-22"), (22.0, 99.0, ">22"))
MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
IMPLS = ("C3-P", "C3-F", "P2")


def runs():
    d = np.load(SRC)
    t, v, sa, sp, stq = d["t_cst"], d["vego"], d["sa_deg"], d["spress"], d["storque"]
    act = np.interp(t, d["t_cs"], d["cs_active"]) > 0.5
    fs = 1 / np.median(np.diff(t))
    out = []
    for lo, hi, nm in BANDS:
        m = act & (v >= lo) & (v < hi) & (sp < 0.5)
        e = np.flatnonzero(np.diff(np.r_[0, m.astype(int), 0]))
        for a, b in zip(e[::2], e[1::2]):
            if b - a >= 15 * fs:
                tr = t[a:b] - t[a]
                fr = np.arange(0, tr[-1], 0.01)
                out.append(dict(band=nm, v=float(np.median(v[a:b])), dur=float(tr[-1]), t0=float(t[a]),
                                ref=np.interp(fr, tr, sa[a:b]), tq=np.interp(fr, tr, stq[a:b] * 128.0 / 125.0),
                                vel=np.interp(fr, tr, v[a:b]), vmin=float(v[a:b].min()), vmax=float(v[a:b].max())))
    return out


def job(args):
    mode, member = args
    R = runs()
    cols = [dict(impl=i, member=member, v=R[k]["v"], run=k) for k in range(len(R)) for i in IMPLS]
    idx = [c["run"] for c in cols]
    nf = int(max(R[i]["dur"] for i in set(idx)) * 100) + 2
    REF = np.stack([np.pad(R[i]["ref"], (0, nf - len(R[i]["ref"])), mode="edge") for i in idx], 1)
    TQ = np.stack([np.pad(R[i]["tq"], (0, nf - len(R[i]["tq"])), mode="constant") for i in idx], 1)
    VEL = np.stack([np.pad(R[i]["vel"], (0, nf - len(R[i]["vel"])), mode="edge") for i in idx], 1)
    ref = lambda t: REF[min(int(round(t * 100)), nf - 1)]  # noqa: E731
    tq = (lambda t, th, om, hf: TQ[min(int(t * 100), nf - 1)]) if "q" in mode else None  # noqa: E731
    vel = (lambda t: VEL[min(int(t * 100), nf - 1)]) if mode.startswith("vel") else None  # noqa: E731
    dur = max(R[i]["dur"] for i in set(idx)) + 0.5
    scn = S.Scn(dur=dur, ref=ref, tq=tq, vel=vel, th0=REF[0].copy())
    t0 = time.time()
    r = S.run(cols, scn)
    th, om = r["th"].astype(float), r["om"].astype(float)
    n = th.shape[0]
    plan = r["plan"].astype(float)
    plan1k = np.repeat(plan, 10, axis=0)[:n]
    sos = signal.butter(4, 0.5, "lowpass", fs=100.0, output="sos")
    th100 = th[::10]
    res = []
    for j, c in enumerate(cols):
        L = min(len(R[c["run"]]["ref"]), th100.shape[0], plan.shape[0])
        x = signal.sosfiltfilt(sos, plan[:L, j])
        y = signal.sosfiltfilt(sos, th100[:L, j])
        xs, ys = x[400:], y[400:]
        xm = xs - xs.mean()
        slope = float((xm * (ys - ys.mean())).sum() / max((xm ** 2).sum(), 1e-12))
        d = np.gradient(x) * 100.0
        msk = (np.abs(x) >= 3.0) & (np.abs(d) <= np.maximum(1.0, 0.05 * np.abs(x))) & (np.arange(L) >= 400)
        e = np.flatnonzero(np.diff(np.r_[0, msk.astype(int), 0]))
        holds = [[float(y[a:b].mean() / x[a:b].mean()), float(x[a:b].mean()), float(a / 100.0)]
                 for a, b in zip(e[::2], e[1::2]) if b - a >= 150]
        ii = np.arange(400, L) * 10 + 4
        ii = ii[ii < n]
        ev, jm, lst = S.dwell_jump(om[ii, j:j + 1], th[ii, j:j + 1], plan1k[ii, j:j + 1])
        evl = [(float((400 + b) / 100.0), jump, dref) for (b, jump, dref) in lst[0]]
        # the excursions behind the largest event: |th - plan| at the event and the I state
        res.append(dict(impl=c["impl"], run=c["run"], band=R[c["run"]]["band"], v=c["v"], slope=slope, holds=holds,
                        X=xs.astype(np.float32).tolist(), Y=ys.astype(np.float32).tolist(),
                        dj=int(ev[0]), dj_max=float(jm[0]), dj_list=evl, dur=len(ii) / 100.0,
                        emax=float(np.abs(plan1k[4000:L * 10, j] - th[4000:L * 10, j]).max())))
    return dict(mode=mode, member=member, res=res, sec=time.time() - t0)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "run":
        procs = int(sys.argv[2]) if len(sys.argv) > 2 else 8
        jobs = [(md, mb) for md in ("med", "vel", "medq", "velq") for mb in MEMBERS]
        with Pool(procs) as pool:
            for r in pool.imap_unordered(job, jobs):
                (OUTD / f"{r['mode']}__{r['member'].replace('*', 'x')}.json").write_text(json.dumps(r))
                print(r["mode"], r["member"], f"{r['sec']:.0f} s", flush=True)
        return
    # report
    R = runs()
    L = ["# r71b real paths: tracking slope (worse member), constant median speed vs the run's real speed", ""]
    L.append("runs: " + "; ".join(f"#{k} {r['band']} v_med {r['v']:.1f} [{r['vmin']:.1f}-{r['vmax']:.1f}] "
                                   f"{r['dur']:.0f}s" for k, r in enumerate(R)))
    L.append("")
    tab = {}
    for f in sorted(OUTD.glob("*.json")):
        d = json.loads(f.read_text())
        for x in d["res"]:
            tab.setdefault((d["mode"], x["impl"], x["band"]), {}).setdefault(d["member"], []).append(x)
    L.append("| mode | impl | band | slope per member (concatenated runs) nominal / bc / F_hi / b_lo*J_hi | worst | "
             "real-curve hold min | dj events / 100 s (max snap) |")
    L.append("|---|---|---|---|---|---|---|")
    for (md, im, bd), per in sorted(tab.items()):
        sl, hmin, djn, djd, djm = [], 9.0, 0, 0.0, 0.0
        for mb in MEMBERS:
            xs = per.get(mb, [])
            if not xs:
                sl.append(float("nan"))
                continue
            X = np.concatenate([np.array(x["X"]) for x in xs])
            Y = np.concatenate([np.array(x["Y"]) for x in xs])
            xm = X - X.mean()
            sl.append(float((xm * (Y - Y.mean())).sum() / (xm ** 2).sum()))
            for x in xs:
                for h in x["holds"]:
                    hmin = min(hmin, h[0])
                djn += x["dj"]
                djd += x["dur"]
                djm = max(djm, x["dj_max"])
        L.append(f"| {md} | {im} | {bd} | {' / '.join(f'{s:.3f}' for s in sl)} | {min(sl):.3f} | {hmin:.3f} | "
                 f"{100 * djn / max(djd, 1e-9):.2f} ({djm:.2f}) |")
    L.append("")
    L.append("## dwell-then-jump events with jump >= 1.5 deg (mode, member, impl, run, t s, jump deg, reference change deg)")
    for f in sorted(OUTD.glob("*.json")):
        d = json.loads(f.read_text())
        for x in d["res"]:
            for (tt, jump, dref) in x["dj_list"]:
                if jump >= 1.5:
                    L.append(f"- {d['mode']} {d['member']} {x['impl']} run#{x['run']} ({x['band']}, v_med "
                             f"{x['v']:.1f}) t {tt:.2f} s jump {jump:.2f} ref-change {dref:+.2f}")
    txt = "\n".join(L) + "\n"
    (HERE / "out" / "r71b_report.md").write_text(txt, encoding="utf-8")
    print(txt[:20000])


if __name__ == "__main__":
    main()
