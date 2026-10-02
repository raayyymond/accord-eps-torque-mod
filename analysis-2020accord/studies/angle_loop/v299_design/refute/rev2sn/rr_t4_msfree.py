# -*- coding: utf-8 -*-
"""rr_t4_msfree.py -- RG / F10: the ms_free curve-hold mode (GATE-2 PM 6.1-6.3 deg, inherited) on the rev-2 two-level cap
vs V298, across 8..14 m/s (both sides of the 12.5 m/s cap edge) and three curve-hold lateral accelerations 1.5 / 2.5 /
3.5 m/s^2 (F10's window starts at 1.5).  Hold at the curve angle from t=0, a 1-deg setpoint step at 4 s, 18 s total,
twist residual ON, age 10 ms.  Reads: first 3 half-peaks of theta - sp after the step, F10 as written (0.4-0.8 Hz
band-pass of theta - sp from 4.5 s: a half-peak > 1 deg, or > 2 consecutive half-cycles >= 0.5 deg), steady error over
the last 4 s, A3-bound duty.  MY engine.  usage: python rr_t4_msfree.py (< 30 s).  ANALYSIS ONLY."""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R
MEM = ("b_lo*ms_free", "b_lo*ms_free_r79F", "ms_free_r79F", "r79F")
SPEEDS = (8.0, 9.0, 10.0, 11.0, 11.75, 12.4, 12.6, 13.0, 14.0)
ALAT = (1.5, 2.5, 3.5)


def f10(e):
    from rsn_common import bp
    y = bp(e, 0.4, 0.8)
    s = np.sign(y); idx = np.flatnonzero(s[1:] != s[:-1])
    pk = np.array([np.abs(y[a:b]).max() for a, b in zip(idx[:-1], idx[1:])]) if len(idx) > 2 else np.zeros(0)
    run = best = 0
    for p in pk:
        run = run + 1 if p >= 0.5 else 0
        best = max(best, run)
    return float(pk.max()) if len(pk) else 0.0, int(best)


def job(v):
    E = R.E
    cols = [R.col(s, m, v, age=10, nz=1, al=a) for s in ("V298", "R2") for m in MEM for a in ALAT]
    B = len(cols)
    A = np.array([float(E.steer_from_curv(c["al"] / v ** 2, v)) for c in cols])
    plan = lambda t: A + (1.0 if t >= 4.0 else 0.0)  # noqa
    Rr = E.run(cols, 18.0, plan, th0=A, seed=5, rec=("th", "a3", "frz"))
    out = []
    for j, c in enumerate(cols):
        th = Rr["th"][:, j].astype(float)
        e = th - (A[j] + (np.arange(len(th)) >= 4000))
        e4 = e[4000:]
        s = np.sign(e4); idx = np.flatnonzero(s[1:] != s[:-1])
        pk = [float(np.abs(e4[a:b]).max()) for a, b in zip(idx[:-1], idx[1:])][:3]
        hp, nrun = f10(e[4500:])
        out.append(dict(sys=c["sys"], member=c["member"], v=v, al=c["al"], A=float(A[j]), peaks=[round(p, 2) for p in pk],
                        f10_hp=hp, f10_run=nrun, F10=bool(hp > 1.0 or nrun > 2), err=float(-e[-4000:].mean()),
                        a3=float(Rr["a3"][4000:, j].mean()), frz=float(Rr["frz"][4000:, j].mean())))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(len(SPEEDS)) as p:
        res = sum(p.map(job, SPEEDS), [])
    (R.OUT / "rr_t4_msfree.json").write_text(json.dumps(res), encoding="utf-8")
    print("| v | member | a_lat | A deg | V298: peaks / F10 hp,run / err / frz | R2: peaks / F10 hp,run / err / a3 |")
    print("|---|---|---|---|---|---|")
    for v in SPEEDS:
        for m in MEM:
            for a in ALAT:
                q = {d["sys"]: d for d in res if d["v"] == v and d["member"] == m and d["al"] == a}
                c = lambda d, k: f"{d['peaks']} / {d['f10_hp']:.2f},{d['f10_run']}{' F10' if d['F10'] else ''} / {d['err']:+.2f} / {d[k]:.2f}"  # noqa
                print(f"| {v} | {m} | {a} | {q['R2']['A']:.1f} | {c(q['V298'], 'frz')} | {c(q['R2'], 'a3')} |")
    for s in ("V298", "R2"):
        Y = [d for d in res if d["sys"] == s]
        print(s, "F10 fires:", sorted({(d['v'], d['member'], d['al']) for d in Y if d['F10']}))
    print(f"wall {time.perf_counter() - T0:.1f} s")
