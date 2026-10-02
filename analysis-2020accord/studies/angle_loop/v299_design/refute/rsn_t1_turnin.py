# -*- coding: utf-8 -*-
"""rsn_t1_turnin.py -- T1: hands-off turn-in / hold / unwind sweep, V298 vs V299-A vs V299-B on MY engine.
speeds x amplitudes x members x twist seeds; the design's own F4 (overshoot > 6 deg or > 15 % of the turn at
<= 10 m/s) evaluated per column.  ANALYSIS ONLY.  usage: python rsn_t1_turnin.py [ka]"""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
import rsn_common as C

SPEEDS = (3.0, 5.0, 6.5, 8.0, 10.0, 11.75)
AMPS = (30.0, 60.0, 90.0)
MEMBERS = ("r79F", "b_lo*J_hi")
SEEDS = (1, 2)
KA = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0


def job(v):
    cols = []
    for s in C.SYS:
        for A in AMPS:
            for m in MEMBERS:
                for sd in SEEDS:
                    rule, fork = C.SYS[s]
                    cols.append(dict(sys=s, rule=rule, fork=fork, member=m, v=v, A=min(A, 0.9 * float(E.vm_amax(v))),
                                     sd=sd, ka=KA))
    B = len(cols)
    Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v)
    t0, hold = 0.5, 2.5
    ta = t0 + Av / Rt; tu = ta + hold; dur = float(tu.max() + Av.max() / Rt + 2.0)
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa: E731
    out = []
    for sd in SEEDS:                       # one run per seed (the twist residual realisation shared by every system)
        sel = [j for j, c in enumerate(cols) if c["sd"] == sd]
        sub = [cols[j] for j in sel]
        Avs = Av[sel]; tas = ta[sel]; tus = tu[sel]
        pl_ = lambda t, Avs=Avs, tus=tus: np.clip((t - t0) * Rt, 0, Avs) - np.clip((t - tus) * Rt, 0, Avs)  # noqa
        R = E.run(sub, dur, pl_, seed=100 * sd, rec=("th", "om", "T", "w", "I", "frz", "hard", "a3"))
        for j, c in enumerate(sub):
            th = R["th"][:, j].astype(float); om = R["om"][:, j].astype(float)
            i0, ia, iu = int(t0 * 1000), int(tas[j] * 1000), int(tus[j] * 1000)
            A = c["A"]
            hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
            ovs = float(th[i0:iu].max() - A)
            und = float(-th[iu:].min())
            hold_seg = th[iu - 1500:iu]
            lc = C.limit_cycle(hold_seg, 0.5)
            r110 = float(np.sqrt(np.mean(C.bp(om, 1.0, 10.0)[iu - 1500:iu] ** 2)))
            o1 = R["o1"][:, j]; vh = R["viahard"][:, j]
            hd = R["hard"][i0:, j] > 0
            d = dict(sys=c["sys"], member=c["member"], v=v, A=round(A, 1), sd=sd,
                     t90=hit[0] / 1000.0 if len(hit) else np.nan, wpk=float(np.abs(om[i0:iu]).max()),
                     ovs=ovs, ovs_pct=100 * ovs / A, und=und, F4=bool(v <= 10.0 and (ovs > 6.0 or ovs > 0.15 * A)),
                     tap_pk=float(np.abs(R["T"][:, j]).max() / E.RAIL_T),
                     o1_eps=C.episodes(o1), viahard=int(vh.sum()), hard_tog_s=C.toggles(hd) / (len(hd) / 1000),
                     hard_duty=float(hd.mean()), a3_duty=float((R["a3"][i0:, j] > 0).mean()),
                     w_p99=float(np.percentile(np.abs(R["w"][i0:, j]), 99)), ss=C.stall_surge(om[::10]),
                     lc_hold=lc, r110_hold=r110, I_end=float(R["I"][iu - 1, j]),
                     err_end=float(R["plan"][iu // 10 - 1, j] - th[iu - 1]))
            out.append(d)
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(len(SPEEDS)) as p:
        res = sum(p.map(job, SPEEDS), [])
    (E.OUT / f"t1_ka{KA}.json").write_text(json.dumps(res), encoding="utf-8")
    import collections
    print("| sys | v | A | t90 med | w pk med | ovs med [worst] | ovs% worst | F4 cols | und worst | tap pk worst | O1 eps med | via-hard tot | hard tog/s med | w p99 med | ss tot | lc_hold max | r1-10 hold med |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["sys"], d["v"], d["A"])].append(d)
    for k in sorted(g, key=lambda k: (k[1], k[2], k[0])):
        L = g[k]; f = lambda q: np.array([x[q] for x in L], float)  # noqa
        print(f"| {k[0]} | {k[1]} | {k[2]} | {np.nanmedian(f('t90')):.2f} | {np.median(f('wpk')):.0f} | "
              f"{np.median(f('ovs')):.1f} [{f('ovs').max():.1f}] | {f('ovs_pct').max():.0f} | {int(f('F4').sum())}/{len(L)} | "
              f"{f('und').max():.1f} | {100*f('tap_pk').max():.0f} | {np.median(f('o1_eps')):.0f} | {int(f('viahard').sum())} | "
              f"{np.median(f('hard_tog_s')):.1f} | {np.median(f('w_p99')):.0f} | {int(f('ss').sum())} | {int(f('lc_hold').max())} | {np.median(f('r110_hold')):.2f} |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
