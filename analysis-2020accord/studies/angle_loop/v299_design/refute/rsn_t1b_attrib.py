# -*- coding: utf-8 -*-
"""rsn_t1b_attrib.py -- T1b: which half of V299 causes the 10-11.75 m/s turn-in overshoot (firmware vs fork), and two
hypothetical fixes (NOT in the design): ecl = freeze I while |E| > 16*D counts (conditional integration, D = 5 / 8 deg);
cap = A3 cap extended to v <= 2880 (12.5 m/s) at 6144 S.  Hands-off turn-in/hold/unwind, MY engine.  ANALYSIS ONLY."""
import json, sys, time, collections
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E
import rsn_common as C

SYSX = {"V298": ("V298", "V298", {}), "fw299+fk298": ("V299", "V298", {}), "fw298+fkA": ("V298", "A", {}),
        "V299A": ("V299", "A", {}), "V299B": ("V299", "B", {}),
        "A+ecl8": ("V299", "A", dict(ecl=1280)), "A+ecl5": ("V299", "A", dict(ecl=800)),
        "A+cap6144@12.5": ("V299", "A", dict(capv=2880, capval=6144))}
SPEEDS = (6.5, 8.0, 10.0, 11.75)
AMPS = (30.0, 60.0, 90.0)


def job(args):
    v, sd = args
    cols = [dict(sys=s, rule=SYSX[s][0], fork=SYSX[s][1], variant=SYSX[s][2], member=m, v=v,
                 A=min(A, 0.9 * float(E.vm_amax(v)))) for s in SYSX for A in AMPS for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols]); Rt = E.plan_rate(v); t0 = 0.5; tu = t0 + Av / Rt + 3.0
    plan = lambda t: np.clip((t - t0) * Rt, 0, Av) - np.clip((t - tu) * Rt, 0, Av)  # noqa
    R = E.run(cols, float(tu.max()) + 2.0, plan, seed=300 + sd, rec=("th", "om", "T", "I"))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float); i0, iu = int(t0 * 1000), int(tu[j] * 1000); A = c["A"]
        hit = np.flatnonzero(th[i0:iu] >= 0.9 * A)
        out.append(dict(sys=c["sys"], v=v, A=round(A, 1), member=c["member"], sd=sd, ovs=float(th[i0:iu].max() - A),
                        t90=hit[0] / 1000 if len(hit) else np.nan, err_end=float(A - th[iu - 1]),
                        und=float(-th[iu:].min()), tap=float(np.abs(R["T"][:, j]).max() / E.RAIL_T)))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(8) as p:
        res = sum(p.map(job, [(v, s) for v in SPEEDS for s in (1, 2)]), [])
    (E.OUT / "t1b.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["sys"], d["v"])].append(d)
    print("| system | v | overshoot med [max] (30/60/90 pooled) | F4 cols (<=10 m/s: >6 deg or >15 %) | t90 med | |err| at hold end med [max] | unwind past 0 max | tap pk max % |")
    print("|---|---|---|---|---|---|---|---|")
    for k in sorted(g, key=lambda k: (k[1], list(SYSX).index(k[0]))):
        L = g[k]; f = lambda q: np.array([x[q] for x in L], float)  # noqa
        f4 = sum((x["v"] <= 10.0) and (x["ovs"] > 6 or x["ovs"] > 0.15 * x["A"]) for x in L)
        print(f"| {k[0]} | {k[1]} | {np.median(f('ovs')):.1f} [{f('ovs').max():.1f}] | {f4}/{len(L)} | {np.nanmedian(f('t90')):.2f} | "
              f"{np.median(np.abs(f('err_end'))):.2f} [{np.abs(f('err_end')).max():.1f}] | {f('und').max():.1f} | {100*f('tap').max():.0f} |")
    print(f"wall {time.perf_counter()-T0:.1f} s")
