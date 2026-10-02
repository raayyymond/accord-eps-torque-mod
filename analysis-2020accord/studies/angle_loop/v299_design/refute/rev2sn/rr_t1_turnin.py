# -*- coding: utf-8 -*-
"""rr_t1_turnin.py -- RD/RF/R0: hands-off turn-ins over 3..15 m/s x {30,45,60,90} deg x {linear at the planner rate,
raised-cosine 1.0 s, raised-cosine 2.0 s} x members r79F, b_lo*J_hi; systems V298 / R2 (THE DRIVE) / R1N (rev-1 fw on
the no-override fork).  Hold 4 s, unwind.  Reads overshoot (F4), t90, hold error, unwind past centre, 4-8 and 1.6-3 Hz
wheel-rate rms, stall-surges, tap peak LSB (F9), I at the A3 bound.  usage: python rr_t1_turnin.py RSN|S2.  ANALYSIS ONLY."""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rsn2 as R

ENG = sys.argv[1] if len(sys.argv) > 1 else "RSN"
PART = sys.argv[2] if len(sys.argv) > 2 else "all"   # S2 only: lin | rc (split to stay < 30 s)
SPEEDS = (3.0, 4.0, 5.0, 5.9, 6.1, 6.5, 7.0, 8.0, 9.0, 10.0, 11.0, 11.75, 12.4, 12.6, 13.0, 15.0)
AMPS = (30.0, 45.0, 60.0, 90.0)
PLANS = ("lin", "rc1", "rc2")
SYS = ("V298", "R2", "R1N")
HOLD = 4.0
T0S = 0.5


def shape(x, kind):
    x = np.clip(x, 0.0, 1.0)
    return x if kind == "lin" else 0.5 - 0.5 * np.cos(np.pi * x)


def mk_plan(Av, Tr, kinds, t0, tu):
    kl = np.array([k == "lin" for k in kinds])

    def plan(t):
        t = np.asarray(t, float) * np.ones_like(Av)
        up = np.where(kl, np.clip((t - t0) / Tr, 0, 1), 0.5 - 0.5 * np.cos(np.pi * np.clip((t - t0) / Tr, 0, 1)))
        dn = np.where(kl, np.clip((t - tu) / Tr, 0, 1), 0.5 - 0.5 * np.cos(np.pi * np.clip((t - tu) / Tr, 0, 1)))
        return Av * (up - dn)
    return plan


def metrics(th, om, T, A, ta, tu, v, I=None):
    from rsn_common import bp, stall_surge
    i0, i25, iu = int(T0S * 1000), int((ta + 2.5) * 1000), int(tu * 1000)
    ovs = float(th[i0:iu].max() - A)
    hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
    return dict(ovs=ovs, ovs25=float(th[i0:i25].max() - A),
                F4=bool(v <= 10.0 and (ovs > 6.0 or (A >= 45 and ovs > 0.15 * A))),
                F4old=bool(v <= 10.0 and (ovs > 6.0 or ovs > 0.15 * A)),
                t90=float(hit[0] / 1000) if len(hit) else None, err=float(A - th[iu - 1]),
                und=float(-th[iu:].min()), r48=float(np.sqrt(np.mean(bp(om, 4.0, 8.0)[i0:] ** 2))),
                r163=float(np.sqrt(np.mean(bp(om, 1.6, 3.0)[i0:] ** 2))),
                ss=int(stall_surge(om[::10][i0 // 10:])), tap=float(np.abs(T).max() / 8.0))


def job(args):
    v, sd = args
    if ENG == "RSN":
        E = R.E
        amax = float(E.vm_amax(v)); Rt = E.plan_rate(v)
        cols = [R.col(s, m, v, An=A, A=min(A, 0.9 * amax), kind=k) for s in SYS for A in AMPS for m in ("r79F", "b_lo*J_hi")
                for k in PLANS]
    else:
        S2 = R.load_s2()
        amax = float(S2.D2C.vm_amax(np.array([v]))[0]); Rt = S2.plan_rate(v)
        cols = [dict(cid=s, sys=s, member=m, v=v, x="ti", s=s_, An=A, A=min(A, 0.9 * amax), kind=k) for s in SYS
                for A in AMPS for m in S2.MEMBERS for k in (PLANS if PART == "all" else (("lin",) if PART == "lin" else ("rc1", "rc2"))) for s_ in (1, 2)]
    B = len(cols)
    Av = np.array([c["A"] for c in cols])
    Tr = np.array([c["A"] / Rt if c["kind"] == "lin" else (1.0 if c["kind"] == "rc1" else 2.0) for c in cols])
    ta = T0S + Tr; tu = ta + HOLD
    plan = mk_plan(Av, Tr, [c["kind"] for c in cols], T0S, tu)
    dur = float(tu.max() + Tr.max() + 1.5)
    if ENG == "RSN":
        Rr = R.E.run(cols, dur, plan, seed=400 + sd, rec=("th", "om", "T", "a3"))
    else:
        Rr = S2.run(cols, dur, plan, np.zeros(B))
    out = []
    for j, c in enumerate(cols):
        d = metrics(Rr["th"][:, j].astype(float), Rr["om"][:, j].astype(float), Rr["T"][:, j].astype(float), c["A"],
                    ta[j], tu[j], v)
        iu = int(tu[j] * 1000)
        d.update(sys=c["sys"], v=v, An=c["An"], A=c["A"], member=c["member"], kind=c["kind"], sd=sd if ENG == "RSN" else c["s"],
                 a3hold=float(Rr["a3"][int(ta[j] * 1000):iu, j].mean()))
        out.append(d)
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    jobs = [(v, sd) for v in SPEEDS for sd in (1, 2)] if ENG == "RSN" else [(v, 0) for v in SPEEDS]
    with Pool(16) as p:
        res = sum(p.map(job, jobs), [])
    (R.OUT / f"rr_t1_{ENG}{'' if PART == 'all' else '_' + PART}.json").write_text(json.dumps(res), encoding="utf-8")
    print(f"{ENG}: {len(res)} rows, wall {time.perf_counter() - T0:.1f} s")
