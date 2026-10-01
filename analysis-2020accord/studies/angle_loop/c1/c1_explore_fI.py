# -*- coding: utf-8 -*-
"""c1_explore_fI.py -- the PI corner fI (Ki_base / Kp_base) and Kd are the global knobs the E-gain cave leaves.
For each (fI, Kd): recompute the GATE-2 envelope (c1_design_G machinery, same members and tiers), fit the table knots
under MARGIN x envelope by a linear program (maximise the sum of knot G, every 0.25 m/s grid point under the envelope,
flat outside the end knots), then score the LINEAR tracking proxy Re(T_ref) at 0.2 / 0.5 Hz (the regression slope of
y on a unit sine = |T| cos(phi), the time harness's track_gain definition) and |T_ref(0.05 Hz)| (turn-hold proxy) on
nominal / b_lo / b_hi / J_hi / J_lo / tau6 at 8..30 m/s, plus M20 and Re(T/omega) at 13 Hz at 26 m/s.
ANALYSIS ONLY; the time harness re-scores the chosen point.  Usage: python c1_explore_fI.py [fI,..] [Kd,..] [knotset]"""
from __future__ import annotations

import json
import math
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_members as M  # noqa: E402
import c1_design_G as D  # noqa: E402

KNOTSETS = {"5": (3.1, 8.0, 12.0, 17.0, 26.9), "6": (3.1, 8.0, 12.0, 13.0, 17.0, 26.9),
            "6b": (3.1, 8.0, 11.9, 12.75, 16.0, 26.9), "7": (3.1, 8.0, 11.9, 12.5, 14.0, 17.0, 26.9)}
MARGIN = 0.955
SPEEDS = D.SPEEDS
TRK_V = (8.0, 10.0, 11.9, 12.5, 15.0, 17.0, 19.0, 22.0, 26.0, 30.0)
TRK_M = ("nominal", "b_lo", "b_hi", "J_hi", "J_lo", "tau6")


def env_job(args):
    v, ki, kd = args
    out = {}
    for name in M.TIER_A + M.TIER_B:
        A, B = D.AB(name, v, ki=ki, kd=kd)
        best = None
        for G in D.GGRID:
            pm, fc = D.pm_of((G / 256) * A + B)
            if not (pm >= M.TIER_PM[name]):
                break
            best = int(G)
        out[name] = best or 0
    return v, min(out.values())


def fit_knots(env, kv):
    vs = np.array(sorted(env))
    e = np.array([env[v] for v in vs], float) * MARGIN
    n = len(kv)
    Aub, bub = [], []
    for v, ev in zip(vs, e):
        row = np.zeros(n)
        if v <= kv[0]:
            row[0] = 1
        elif v >= kv[-1]:
            row[-1] = 1
        else:
            i = max(j for j in range(n - 1) if kv[j] <= v)
            w = (v - kv[i]) / (kv[i + 1] - kv[i])
            row[i], row[i + 1] = 1 - w, w
        Aub.append(row)
        bub.append(ev)
    r = linprog(-np.ones(n), A_ub=np.array(Aub), b_ub=np.array(bub), bounds=[(256, 8000)] * n, method="highs")
    return [(v, int(math.floor(g))) for v, g in zip(kv, r.x)]


def track(tbl, ki_base, kd):
    import harness_freq as HF
    f = np.array([0.05, 0.2, 0.5])
    rows = {}
    for v in TRK_V:
        for m in TRK_M:
            c = C.hf_ctl(v, tbl, ki_base=ki_base, kd=kd)
            p = HF.plant_at(m, v)
            cc = HF.replace(c, d=p.tau)
            P = p.frf(f)
            Tr = HF.C_ref(f, cc) * P / (1 + HF.C_fb(f, cc) * P)
            rows[(v, m)] = (abs(Tr[0]), Tr[1].real, Tr[2].real)
    c26 = C.hf_ctl(26.0, tbl, ki_base=ki_base, kd=kd)
    hi = dict(M20=HF.M20(c26), Re13=HF.Re_Cr(HF.replace(c26, d=2), 13.0), Re7=HF.Re_Cr(HF.replace(c26, d=2), 7.0))
    return rows, hi


def main():
    fis = [float(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else [0.45, 0.50, 0.55, 0.62]
    kds = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [16]
    kset = KNOTSETS[sys.argv[3] if len(sys.argv) > 3 else "5"]
    res = {}
    for kd in kds:
        for fI in fis:
            ki = int(round(2 * math.pi * fI * C.KP_BASE / 7.8125))
            with Pool(12) as pool:
                env = dict(pool.map(env_job, [(v, ki, kd) for v in SPEEDS]))
            knots = fit_knots(env, kset)
            tbl = C.make_table(knots)
            tr, hi = track(tbl, ki, kd)
            p2 = sum(1 for k, (h, a, b) in tr.items() if 0.95 <= a <= 1.05)
            p5 = sum(1 for k, (h, a, b) in tr.items() if 0.95 <= b <= 1.05)
            pn = sum(1 for k, (h, a, b) in tr.items() if k[1] == "nominal" and 0.95 <= a <= 1.05 and 0.95 <= b <= 1.05)
            res[f"{fI}|{kd}"] = dict(ki=ki, kd=kd, knots=knots, env={str(k): v for k, v in env.items()},
                                     track={f"{k[0]}|{k[1]}": v for k, v in tr.items()}, hi=hi)
            print(f"fI {fI:.2f} Ki {ki} Kd {kd} knots " + " ".join(f"{v:g}:{g}" for v, g in knots) + " Kp_eff " +
                  "/".join(f"{225 * g / 256:.0f}" for _, g in knots) +
                  f" | pass 0.2Hz {p2}/60 0.5Hz {p5}/60 nominal-both {pn}/10 | M20@26 {hi['M20']:.2f} "
                  f"Re7 {hi['Re7']:+.2f} Re13 {hi['Re13']:+.2f}", flush=True)
            for m in TRK_M:
                print(f"    {m:8s} " + " ".join(f"{v:4.1f}:{tr[(v, m)][1]:.3f}/{tr[(v, m)][2]:.3f}" for v in TRK_V))
    tag = "_".join(sys.argv[1:]).replace(",", "-") or "default"
    (C.OUT / f"explore_{tag}.json").write_text(json.dumps(res))


def report():
    """summarise every explore_*.json in the scratch dir into explore_fI_summary.txt (the runs quoted on the page)."""
    lines = []
    for fn in sorted(C.OUT.glob("explore_*.json")):
        res = json.loads(fn.read_text())
        lines.append(f"== {fn.name}")
        for key, d in res.items():
            tr = {tuple(k.split("|")): v for k, v in d.get("track", {}).items()}
            p2 = sum(1 for v in tr.values() if 0.95 <= v[1] <= 1.05)
            p5 = sum(1 for v in tr.values() if 0.95 <= v[2] <= 1.05)
            hi = d.get("hi", {})
            lines.append(f"  fI|Kd {key}: Ki {d.get('ki')} knots {d.get('knots')} | Re(T_ref) in 0.95-1.05: 0.2 Hz {p2}/{len(tr)} "
                         f"0.5 Hz {p5}/{len(tr)} | M20@26 {hi.get('M20', float('nan')):.2f} Re13@26 {hi.get('Re13', float('nan')):+.2f}")
            for m in TRK_M:
                cells = [f"{k[0]}:{v[1]:.3f}/{v[2]:.3f}" for k, v in tr.items() if k[1] == m]
                if cells:
                    lines.append(f"      {m:8s} " + " ".join(cells))
    NL = chr(10)
    (HERE / "explore_fI_summary.txt").write_text(NL.join(lines), encoding="utf-8")
    print(NL.join(lines[:12]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report()
    else:
        main()
