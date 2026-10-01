# -*- coding: utf-8 -*-
r"""c3nl_speed.py -- SPEED-VARYING curves (the common scorer holds v constant per column): a constant-radius curve
driven while braking or accelerating, so the G(v) walk (incl. the 10-12.5 m/s dip), the ARB slope knee at 12.5 m/s
(shl 4 <-> shl 6, bound x4) and the low-speed cap at 6 m/s are all crossed WHILE the I holds the spring.
ANALYSIS ONLY.

  decelA  sp = const 9.73 deg (a_lat 1.5 at 20 m/s), 3 s at 20 m/s, brake -1.5 m/s^2 to 5 m/s, 4 s at 5 m/s
  decelB  sp = const 28.8 deg (a_lat 2.5 at 15 m/s), 3 s at 15, brake -1.5 to 3 m/s, 4 s at 3
  accelA  decelA reversed in time (5 -> 20 m/s at +1.5)
  accelB  decelB reversed (3 -> 15 m/s at +1.5)
  decelC  sp = const 9.73 deg, brake -3.0 m/s^2 20 -> 5 (a hard stop in a curve)
Metrics: worst |th - sp| after the first 2.5 s, per crossing window (+-0.5 s around 12.5 and 6 m/s) vs elsewhere; the
worst 1 s-mean hold ratio while v >= 8 m/s; dwell-then-jump events while v >= 8.
usage: python c3nl_speed.py"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c3nl_sim as S  # noqa: E402

MEMBERS = ("nominal", "bc", "F_hi", "b_lo*J_hi")
IMPLS = ("C3-P", "C3-F", "P2", "E2-A3")


def vprof(name):
    if name in ("decelA", "decelC"):
        a = 1.5 if name == "decelA" else 3.0
        v0, v1 = 20.0, 5.0
    elif name == "decelB":
        a, v0, v1 = 1.5, 15.0, 3.0
    elif name == "accelA":
        a, v0, v1 = -1.5, 5.0, 20.0
    else:
        a, v0, v1 = -1.5, 3.0, 15.0
    Tb = abs(v0 - v1) / abs(a)
    dur = 3.0 + Tb + 4.0
    return (lambda t: np.interp(t, [0, 3.0, 3.0 + Tb, 99], [v0, v0, v1, v1])), dur, Tb


def job(args):
    name, member = args
    vf, dur, Tb = vprof(name)
    sp = 9.73 if name in ("decelA", "decelC", "accelA") else 28.8
    cols = [dict(impl=i, member=member, v=float(vf(0.0))) for i in IMPLS]
    B = len(cols)
    ref = lambda t: sp * np.interp(t, [0, 0.2, 1.7, 999], [0, 0, 1, 1]) * np.ones(B)  # noqa: E731
    scn = S.Scn(dur=dur, ref=ref, vel=lambda t: vf(t) * np.ones(B))
    r = S.run(cols, scn)
    th, om, v = r["th"].astype(float), r["om"].astype(float), r["v"].astype(float)
    n = th.shape[0]
    tt = np.arange(n) * 1e-3
    e = th - sp
    out = []
    for j, c in enumerate(cols):
        w = tt >= 2.5
        res = dict(impl=c["impl"], emax=float(np.abs(e[w, j]).max()))
        for vk in (12.5, 6.0):
            k = np.flatnonzero(np.diff(np.sign(v[:, j] - vk)) != 0)
            if len(k):
                win = (tt >= tt[k[0]] - 0.5) & (tt <= tt[k[0]] + 0.5)
                res[f"e@{vk}"] = float(np.abs(e[win, j]).max())
                res[f"om@{vk}"] = float(np.abs(om[win, j]).max())
        hi = (v[:, j] >= 8.0) & w
        # worst 1 s mean hold ratio while v >= 8
        hr = []
        for a in range(2500, n - 1000, 250):
            if hi[a:a + 1000].all():
                hr.append(th[a:a + 1000, j].mean() / sp)
        res["hold_min_ge8"] = float(min(hr)) if hr else float("nan")
        lo = (v[:, j] < 8.0) & w
        hl = []
        for a in range(2500, n - 1000, 250):
            if lo[a:a + 1000].all():
                hl.append(th[a:a + 1000, j].mean() / sp)
        res["hold_min_lt8"] = float(min(hl)) if hl else float("nan")
        idx = np.arange(4, n, 10)
        fw = (idx * 1e-3 >= 2.5) & (v[idx, j] >= 8.0)
        ref1k = np.full(n, sp)
        ev, jm, _ = S.dwell_jump(om[idx][fw][:, j:j + 1], th[idx][fw][:, j:j + 1], ref1k[idx][fw][:, None])
        res["dj_ge8"] = int(ev[0])
        res["dj_max"] = float(jm[0])
        res["farb_duty_ge8"] = float(r["farb"][hi, j].mean()) if hi.any() else float("nan")
        out.append(res)
    return name, member, out


def main():
    jobs = [(nm, mb) for nm in ("decelA", "decelB", "accelA", "accelB", "decelC") for mb in MEMBERS]
    L = ["# speed-varying curves (constant radius) -- worst |th - sp| and hold ratios", "",
         "| scenario | member | impl | max abs err after 2.5 s | err +-0.5 s @12.5 | err @6 | worst 1 s hold v>=8 | "
         "worst 1 s hold v<8 | dj events v>=8 (max) | ARB-freeze duty v>=8 |", "|---|---|---|---|---|---|---|---|---|---|"]
    with Pool(10) as pool:
        for name, member, out in sorted(pool.map(job, jobs)):
            for r in out:
                L.append(f"| {name} | {member} | {r['impl']} | {r['emax']:.2f} | {r.get('e@12.5', float('nan')):.2f} | "
                         f"{r.get('e@6.0', float('nan')):.2f} | {r['hold_min_ge8']:.3f} | {r['hold_min_lt8']:.3f} | "
                         f"{r['dj_ge8']} ({r['dj_max']:.2f}) | {r['farb_duty_ge8']:.2f} |")
    txt = "\n".join(L) + "\n"
    (HERE / "out" / "speed_report.md").write_text(txt, encoding="utf-8")
    print(txt)


if __name__ == "__main__":
    main()
