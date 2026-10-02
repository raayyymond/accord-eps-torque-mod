# -*- coding: utf-8 -*-
"""rsn_t4_relay.py -- T4: the twist-driven relays under config B vs A vs V298 on MY engine: fork O1 entries (all /
via-hard), their peak rate in any 1-s window, the 1229 firmware freeze, stall-surges, t90; twist alpha-scale ka 1.0 /
1.3 (M3's fit is R^2 0.31, extrapolated above |alpha| 1000).  Hands-off 60/90 deg turn-ins at 3-8 m/s, 4 seeds.
ANALYSIS ONLY.  usage: python rsn_t4_relay.py"""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
import rsn_common as C

SPEEDS = (3.0, 5.0, 6.5, 8.0)
AMPS = (60.0, 90.0)
SEEDS = (1, 2, 3, 4)
KAS = (1.0, 1.3)


def job(args):
    v, sd = args
    cols = [dict(sys=s, rule=C.SYS[s][0], fork=C.SYS[s][1], member="r79F", v=v, A=A, ka=ka)
            for s in C.SYS for A in AMPS for ka in KAS]
    Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v); t0 = 0.5
    tu = t0 + Av / Rt + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa
    R = E.run(cols, float(tu.max()) + 0.1, plan, seed=1000 + sd, rec=("th", "om", "T", "w", "frz", "hard"))
    out = []
    for j, c in enumerate(cols):
        i0, iu = int(t0 * 1000), int(tu[j] * 1000)
        o1 = R["o1"][i0 // 10:iu // 10, j]; vh = R["viahard"][i0 // 10:iu // 10, j]
        ent = np.flatnonzero(o1[1:] & ~o1[:-1]) + 1
        pk = max([np.count_nonzero((ent >= a) & (ent < a + 100)) for a in range(0, len(o1), 10)] + [0])
        th = R["th"][:, j].astype(float); om = R["om"][:, j].astype(float)
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * c["A"])
        hd = R["hard"][i0:iu, j] > 0
        out.append(dict(sys=c["sys"], v=v, A=c["A"], ka=c["ka"], sd=sd, o1=int(len(ent)), vh=int(vh.sum()), pk1s=int(pk),
                        o1_frac=float(o1.mean()), hard_eps=C.episodes(hd), hard_duty=float(hd.mean()),
                        ss=int(C.stall_surge(om[i0:iu][::10])), t90=hit[0] / 1000 if len(hit) else np.nan,
                        wp99=float(np.percentile(np.abs(R["w"][i0:iu, j]), 99)),
                        r48=float(np.sqrt(np.mean(C.bp(om, 4.0, 8.0)[i0:iu] ** 2)))))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(16) as p:
        res = sum(p.map(job, [(v, s) for v in SPEEDS for s in SEEDS]), [])
    (E.OUT / "t4_relay.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["sys"], d["ka"], d["v"], d["A"])].append(d)
    print("| sys | ka | v | A | O1 entries/turn med [max] | via-hard turns | peak O1 entries in 1 s | O1 time frac | 1229-freeze eps/turn | stall-surge/turn | t90 med | word p99 med | r4-8 Hz med |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for k in sorted(g, key=lambda k: (k[1], k[2], k[3], k[0])):
        L = g[k]; f = lambda q: np.array([x[q] for x in L], float)  # noqa
        print(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]:.0f} | {np.median(f('o1')):.1f} [{f('o1').max():.0f}] | {int((f('vh')>0).sum())}/{len(L)} | "
              f"{f('pk1s').max():.0f} | {np.median(f('o1_frac')):.2f} | {np.median(f('hard_eps')):.1f} | {np.mean(f('ss')):.1f} | "
              f"{np.nanmedian(f('t90')):.2f} | {np.median(f('wp99')):.0f} | {np.median(f('r48')):.1f} |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
