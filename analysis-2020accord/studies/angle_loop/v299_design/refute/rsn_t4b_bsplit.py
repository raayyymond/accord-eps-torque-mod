# -*- coding: utf-8 -*-
"""rsn_t4b_bsplit.py -- T4b: what in config B costs the low-speed turn-in (twist-driven O1 relay vs cap vs clip), and
whether a hard-path debounce removes it.  V299 firmware under forks A, B and hypothetical B variants (NOT the design):
B_nohard (no instant > 1200 path), B_h2 (> 1200 held 2 frames), B_capOnly (cap 250, clip x1.0), B_clipOnly (cap 120,
clip x1.6).  Hands-off 60/90 deg turn-ins at 3-8 m/s, r79F + b_lo*J_hi, 3 seeds.  MY engine.  ANALYSIS ONLY."""
import collections
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E  # noqa: E402
import rsn_common as C  # noqa: E402

FKS = ("A", "B", "B_nohard", "B_h2", "B_capOnly", "B_clipOnly")
SPEEDS = (3.0, 5.0, 6.5, 8.0)


def job(args):
    v, sd = args
    cols = [dict(sys=f, rule="V299", fork=f, member=m, v=v, A=A) for f in FKS for A in (60.0, 90.0)
            for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols])
    Rt = E.plan_rate(v)
    t0 = 0.5
    tu = t0 + Av / Rt + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa: E731
    R = E.run(cols, float(tu.max()) + 0.1, plan, seed=2000 + sd, rec=("th", "om", "T"))
    out = []
    for j, c in enumerate(cols):
        i0, iu = int(t0 * 1000), int(tu[j] * 1000)
        th = R["th"][:, j].astype(float)
        om = R["om"][:, j].astype(float)
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * c["A"])
        o1 = R["o1"][i0 // 10:iu // 10, j]
        out.append(dict(sys=c["sys"], v=v, A=c["A"], t90=float(hit[0] / 1000) if len(hit) else np.nan,
                        ovs=float(th[i0:iu].max() - c["A"]), o1=int(np.count_nonzero(o1[1:] & ~o1[:-1])),
                        vh=int(R["viahard"][i0 // 10:iu // 10, j].sum()), ss=int(C.stall_surge(om[i0:iu][::10])),
                        r510=float(np.sqrt(np.mean(C.bp(om, 5.0, 10.0)[i0:iu] ** 2))),
                        tap=float(np.abs(R["T"][:, j]).max() / E.RAIL_T)))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(12) as p:
        res = sum(p.map(job, [(v, s) for v in SPEEDS for s in (1, 2, 3)]), [])
    (E.OUT / "t4b.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["sys"], d["v"])].append(d)
    print("| fork (V299 fw) | v | t90 med | overshoot max | O1 entries/turn | turns w/ via-hard | stall-surge/turn | wheel 5-10 Hz rms | tap pk max % |")
    print("|---|---|---|---|---|---|---|---|---|")
    for v in SPEEDS:
        for f in FKS:
            L = g[(f, v)]
            q = lambda k: np.array([x[k] for x in L], float)  # noqa: E731
            print(f"| {f} | {v} | {np.nanmedian(q('t90')):.2f} | {q('ovs').max():.1f} | {q('o1').mean():.1f} | "
                  f"{int((q('vh') > 0).sum())}/{len(L)} | {q('ss').mean():.1f} | {np.median(q('r510')):.2f} | {100 * q('tap').max():.0f} |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
