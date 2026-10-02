# -*- coding: utf-8 -*-
r"""rev_turnin.py -- V299 rev 2: the A3-cap edit sized on the hands-off turn-in, in BOTH engines.
60-deg (and 30 / 90 on the refuter's engine) hands-off turn-in at the planner's rate, hold 6 s, unwind; speeds 3, 5, 6,
8, 10, 11.75, 12.5 m/s; members r79F and b_lo*J_hi; config A fork (G4 600/80 ms | 1200 instant, lead 0, takeover 0.4,
cap 120, clip x1.0).  Systems: V298 (fw + fork), A-rev1 (synthesis firmware: cap 4096 at v-word <= 1382), and the
rev-2 cap candidates capv 2880 (12.5 m/s) x capval 4096 / 5120 / 6144 / 7168.
Reads per column: overshoot over the plan in the first 2.5 s of hold (F4: > 6 deg or > 15 % at <= 10 m/s), t90,
hold error at 2.5 s and at 6 s (A - theta, + = short of the turn), unwind past centre, tap peak, A3-bound duty in the
hold.  ANALYSIS ONLY.  Wall printed (< 30 s)."""
import collections, json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC

SPEEDS = (3.0, 5.0, 6.0, 8.0, 10.0, 11.75, 12.5)
SYSV = [("V298", "V298", "V298", {}), ("A-rev1", "V299", "A", RC.CAPS["rev1"])] + \
       [(f"A-{k}", "V299", "A", RC.CAPS[k]) for k in ("c4096", "c5120", "c6144", "c7168")]
HOLD = 6.0


def metrics(th, T, a3, A, t0, ta, tu, v, rail):
    i0, ia, i25, iu = int(t0 * 1000), int(ta * 1000), int((ta + 2.5) * 1000), int(tu * 1000)
    hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
    ovs = float(th[i0:i25].max() - A)
    return dict(ovs=ovs, F4=bool(v <= 10.0 and (ovs > 6.0 or ovs > 0.15 * A)),
                t90=hit[0] / 1000 if len(hit) else None, err25=float(A - th[i25 - 1]), err6=float(A - th[iu - 1]),
                und=float(-th[iu:].min()), tap=float(np.abs(T).max() / rail), a3=float(np.mean(a3[ia:iu] > 0)))


def rsn_job(args):
    v, sd = args
    E = RC.load_rsn()
    cols = [dict(sys=s, rule=r, fork=f, variant=var, member=m, v=v, A=min(A, 0.9 * float(E.vm_amax(v))))
            for s, r, f, var in SYSV for A in (30.0, 60.0, 90.0) for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v); t0 = 0.5; ta = t0 + Av / Rt; tu = ta + HOLD
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa
    R = E.run(cols, float(tu.max() + Av.max() / Rt + 2.0), plan, seed=300 + sd, rec=("th", "T", "a3"))
    out = []
    for j, c in enumerate(cols):
        d = metrics(R["th"][:, j].astype(float), R["T"][:, j].astype(float), R["a3"][:, j], c["A"], t0, ta[j], tu[j], v, E.RAIL_T)
        d.update(eng="RSN", sys=c["sys"], v=v, A=round(c["A"], 1), member=c["member"], sd=sd)
        out.append(d)
    return out


def s2_job(v):
    S2 = RC.load_s2()
    G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.FK["SYNA"] = dict(**G4)
    S2.CANDS = {}
    for s, r, f, var in SYSV:
        if s == "V298":
            S2.CANDS[s] = ("V298", "V298", s)
        else:
            S2.FW["fw_" + s] = dict(thr=1229, sgn=0, asym=True, **var)
            S2.CANDS[s] = ("fw_" + s, "SYNA", s)
    A = min(60.0, 0.9 * float(S2.D2C.vm_amax(np.array([v]))[0]))
    cols = [dict(cid=c, member=m, v=v, x="ti", s=s) for c in S2.CANDS for m in S2.MEMBERS for s in (0, 1, 2, 3)]
    B = len(cols); Rt = S2.plan_rate(v); t0 = 0.5; ta = t0 + A / Rt; tu = ta + HOLD
    plan = lambda t: np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A)  # noqa
    R = S2.run(cols, tu + A / Rt + 2.0, plan, np.zeros(B))
    out = []
    for j, c in enumerate(cols):
        d = metrics(R["th"][:, j].astype(float), R["T"][:, j].astype(float), R["a3"][:, j], A, t0, ta, tu, v, 2461.0)
        d.update(eng="S2", sys=c["cid"], v=v, A=round(A, 1), member=c["member"], sd=c["s"])
        out.append(d)
    return out


def job(a):
    return rsn_job(a[1]) if a[0] == "R" else s2_job(a[1])


if __name__ == "__main__":
    T0 = time.perf_counter()
    jobs = [("S", v) for v in SPEEDS] + [("R", (v, sd)) for v in SPEEDS for sd in (1, 2)]
    with Pool(16) as p:
        res = sum(p.map(job, jobs), [])
    (RC.OUT / "rev_turnin.json").write_text(json.dumps(res), encoding="utf-8")
    L = []
    for eng, amps in (("S2", None), ("RSN", (60.0,)), ("RSN", (30.0, 90.0))):
        L.append(f"\n### {eng} engine, {'60 deg' if amps != (30.0, 90.0) else '30 + 90 deg pooled (A bounded by 0.9 amax)'}; "
                 f"{'2 members x seeds 0-3' if eng == 'S2' else '2 members x seeds 1-2'}")
        L.append("| system | v | ovs med [max] deg | F4 cols | t90 med s | hold err @2.5 s med [max abs] | hold err @6 s med [max abs] | unwind past 0 max | tap pk max % | A3 duty hold med |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        g = collections.defaultdict(list)
        for d in res:
            if d["eng"] != eng:
                continue
            if eng == "RSN" and amps == (60.0,) and abs(d["A"] - 60.0) > 0.05:
                continue
            if eng == "RSN" and amps == (30.0, 90.0) and abs(d["A"] - 60.0) <= 0.05:
                continue
            g[(d["sys"], d["v"])].append(d)
        for (s, v) in sorted(g, key=lambda k: ([x[0] for x in SYSV].index(k[0]), k[1])):
            X = g[(s, v)]; f = lambda q: np.array([x[q] if x[q] is not None else np.nan for x in X], float)  # noqa
            L.append(f"| {s} | {v} | {np.median(f('ovs')):.1f} [{f('ovs').max():.1f}] | {int(f('F4').sum())}/{len(X)} | "
                     f"{np.nanmedian(f('t90')):.2f} | {np.median(f('err25')):.2f} [{np.abs(f('err25')).max():.1f}] | "
                     f"{np.median(f('err6')):.2f} [{np.abs(f('err6')).max():.1f}] | {f('und').max():.1f} | {100*f('tap').max():.0f} | "
                     f"{np.median(f('a3')):.2f} |")
    L.append(f"\nwall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L); print(txt); (RC.OUT / "rev_turnin.md").write_text(txt, encoding="utf-8")
