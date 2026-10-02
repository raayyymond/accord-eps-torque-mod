# -*- coding: utf-8 -*-
"""rsn_t1c_smooth.py -- T1c: is the 10-11.75 m/s overshoot an artefact of the linear-ramp plan?  Raised-cosine
turn-ins (duration 1.0 / 1.5 / 2.5 s) of 30 / 45 / 60 deg at 9 / 10 / 11.75 m/s, V298 vs V299-A vs V299-B, and the
hypothetical A3-cap fix (cap 6144 S through v <= 2880, NOT the design).  r79F + b_lo*J_hi, 2 seeds.  MY engine.
ANALYSIS ONLY."""
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

SYSX = {"V298": ("V298", "V298", {}), "V299A": ("V299", "A", {}), "V299B": ("V299", "B", {}),
        "A+cap6144": ("V299", "A", dict(capv=2880, capval=6144))}


def job(args):
    v, sd = args
    cols = [dict(sys=s, rule=SYSX[s][0], fork=SYSX[s][1], variant=SYSX[s][2], member=m, v=v, A=A, Tr=Tr)
            for s in SYSX for A in (30.0, 45.0, 60.0) for Tr in (1.0, 1.5, 2.5) for m in ("r79F", "b_lo*J_hi")]
    Av = np.array([c["A"] for c in cols])
    Tr = np.array([c["Tr"] for c in cols])
    t0 = 0.5

    def plan(t):
        x = np.clip((t - t0) / Tr, 0, 1)
        return Av * 0.5 * (1 - np.cos(np.pi * x))
    dur = t0 + Tr.max() + 3.0
    R = E.run(cols, dur, plan, seed=4000 + sd, rec=("th",))
    out = []
    for j, c in enumerate(cols):
        th = R["th"][:, j].astype(float)
        out.append(dict(sys=c["sys"], v=v, A=c["A"], Tr=c["Tr"], ovs=float(th[int(t0 * 1000):].max() - c["A"]),
                        err_end=float(c["A"] - th[-1])))
    return out


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(6) as p:
        res = sum(p.map(job, [(v, s) for v in (9.0, 10.0, 11.75) for s in (1, 2)]), [])
    (E.OUT / "t1c.json").write_text(json.dumps(res), encoding="utf-8")
    g = collections.defaultdict(list)
    for d in res:
        g[(d["v"], d["A"], d["sys"])].append(d)
    print("| v | A | system | overshoot max by ramp time 1.0/1.5/2.5 s | F4 (>6 deg or >15 %) cols | |err| end max |")
    print("|---|---|---|---|---|---|")
    for k in sorted(g, key=lambda k: (k[0], k[1], list(SYSX).index(k[2]))):
        L = g[k]
        by = {Tr: max(x["ovs"] for x in L if x["Tr"] == Tr) for Tr in (1.0, 1.5, 2.5)}
        f4 = sum((x["ovs"] > 6.0 or x["ovs"] > 0.15 * x["A"]) for x in L)
        print(f"| {k[0]} | {k[1]:.0f} | {k[2]} | " + "/".join(f"{by[t]:.1f}" for t in (1.0, 1.5, 2.5)) +
              f" | {f4}/{len(L)} | {max(abs(x['err_end']) for x in L):.1f} |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
