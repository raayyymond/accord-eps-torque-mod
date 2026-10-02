# -*- coding: utf-8 -*-
"""rsn_t8_msfree.py -- T8: the GATE-2 sub-bar ms_free curve-hold mode (my T5: PM 6.3 deg at b_lo*ms_free, 11.75 m/s,
a 2.5 m/s^2, age 10; 1.6 deg with route 79's D x0.55) in the NONLINEAR time domain: hold at the curve-hold angle,
a 1-deg setpoint step at 4 s, 26 s total; members b_lo*ms_free (friction OFF = the linear worst case),
b_lo*ms_free_r79F and ms_free_r79F (route 79's Coulomb), nominal r79F as control; V298 vs V299-A; twist residual
off / on.  Reads: half-cycle peaks after the step, decay per cycle, and whether a cycle is still running in the last
12 s (sign changes of theta - plan with half-cycle peak >= 0.25 deg, and p-p).  MY engine; one process per speed.
ANALYSIS ONLY."""
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

MEM = ("b_lo*ms_free", "b_lo*ms_free_r79F", "ms_free_r79F", "r79F")


def job(v):
    A = float(E.steer_from_curv(2.5 / v ** 2, v))
    cols = [dict(sys=s, rule=r, fork=f, member=m, v=v, age=10, nz=nz)
            for s, r, f in (("V298", "V298", "V298"), ("V299A", "V299", "A")) for m in MEM for nz in (0, 1)]
    B = len(cols)
    plan = lambda t: np.full(B, A + (1.0 if t >= 4.0 else 0.0))  # noqa: E731
    R = E.run(cols, 26.0, plan, th0=A, seed=5, rec=("th", "frz"))
    rows = []
    for j, c in enumerate(cols):
        e = R["th"][4000:, j].astype(float) - (A + 1.0)
        s = np.sign(e)
        idx = np.flatnonzero(s[1:] != s[:-1])
        pk = [float(np.abs(e[a:b]).max()) for a, b in zip(idx[:-1], idx[1:])][:8]
        tail = e[-12000:]
        rows.append(dict(v=v, A=round(A, 1), sys=c["sys"], member=c["member"], nz=c["nz"], peaks=[round(x, 2) for x in pk],
                         dec=(pk[2] / pk[0]) if len(pk) >= 3 and pk[0] > 0 else None,
                         tail_cyc=C.limit_cycle(tail, 0.25), tail_pp=float(np.ptp(tail)),
                         frz_duty=float((R["frz"][4000:, j] > 0).mean())))
    return rows


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(4) as p:
        rows = sum(p.map(job, (10.0, 11.0, 11.75, 13.0)), [])
    (E.OUT / "t8_msfree.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    print("| v | A deg | member | twist resid | V298: first 3 half-peaks / last-12 s cycles>=0.25 / p-p | V299-A: same | freeze duty V298/V299 |")
    print("|---|---|---|---|---|---|---|")
    for v in (10.0, 11.0, 11.75, 13.0):
        for m in MEM:
            for nz in (0, 1):
                a = [r for r in rows if r["v"] == v and r["member"] == m and r["nz"] == nz and r["sys"] == "V298"][0]
                b = [r for r in rows if r["v"] == v and r["member"] == m and r["nz"] == nz and r["sys"] == "V299A"][0]
                print(f"| {v} | {a['A']} | {m} | {nz} | {a['peaks'][:3]} / {a['tail_cyc']} / {a['tail_pp']:.2f} | "
                      f"{b['peaks'][:3]} / {b['tail_cyc']} / {b['tail_pp']:.2f} | {a['frz_duty']:.3f}/{b['frz_duty']:.3f} |")
    print(f"wall {time.perf_counter() - T0:.1f} s")
