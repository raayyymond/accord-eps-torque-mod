# -*- coding: utf-8 -*-
"""rev_msfree.py -- the stability refuter's D4 (the ms_free curve-hold mode, GATE-2 PM 6.1-6.3 deg at 10-13 m/s) re-run
with the REV-2 firmware: hold at the 2.5 m/s^2 curve-hold angle, a 1-deg setpoint step at 4 s, 26 s; members
b_lo*ms_free (friction off, the linear worst case), b_lo*ms_free_r79F, r79F (nominal control); twist residual off / on;
V298 vs A-rev1 (synthesis) vs A-rev2 (two-level cap; 6144 S at 6 < v <= 12.5 m/s).  Reads: the first three half-peaks
after the step, cycles >= 0.25 deg in the last 12 s, p-p, and the freeze / A3-bound duty in the hold.  Refuter's engine
(rev_common.load_rsn).  ANALYSIS ONLY.  usage: python rev_msfree.py  (< 30 s)"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC  # noqa: E402

MEM = ("b_lo*ms_free", "b_lo*ms_free_r79F", "r79F")
SPEEDS = (10.0, 11.0, 11.75, 12.5, 13.0)


def job(v):
    E = RC.load_rsn()
    sys.path.insert(0, str(RC.V299 / "refute"))
    import rsn_common as C
    A = float(E.steer_from_curv(2.5 / v ** 2, v))
    vw = int(round(v * 230.4))
    sysd = (("V298", "V298", "V298", {}), ("A-rev1", "V299", "A", {}),
            ("A-rev2", "V299", "A", dict(capv=2880, capval=4096 if vw <= 1382 else 6144)))
    cols = [dict(sys=s, rule=r, fork=f, variant=var, member=m, v=v, age=10, nz=nz)
            for s, r, f, var in sysd for m in MEM for nz in (0, 1)]
    B = len(cols)
    plan = lambda t: np.full(B, A + (1.0 if t >= 4.0 else 0.0))  # noqa: E731
    R = E.run(cols, 26.0, plan, th0=A, seed=5, rec=("th", "frz", "a3", "I"))
    rows = []
    for j, c in enumerate(cols):
        e = R["th"][4000:, j].astype(float) - (A + 1.0)
        s = np.sign(e)
        idx = np.flatnonzero(s[1:] != s[:-1])
        pk = [float(np.abs(e[a:b]).max()) for a, b in zip(idx[:-1], idx[1:])][:8]
        tail = e[-12000:]
        rows.append(dict(v=v, A=round(A, 1), sys=c["sys"], member=c["member"], nz=c["nz"], peaks=[round(x, 2) for x in pk],
                         tail_cyc=C.limit_cycle(tail, 0.25), tail_pp=float(np.ptp(tail)), tail_err=float(-np.mean(tail)),
                         frz=float((R["frz"][4000:, j] > 0).mean()), a3=float((R["a3"][4000:, j] > 0).mean()),
                         Ipk=float(np.abs(R["I"][:, j]).max())))
    return rows


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(len(SPEEDS)) as p:
        rows = sum(p.map(job, SPEEDS), [])
    (RC.OUT / "rev_msfree.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    L = ["| v | A deg | member | twist | V298 peaks / tail cyc / p-p / frz / steady err (sp - theta, deg) | A-rev1 same | A-rev2 same / A3 duty |", "|---|---|---|---|---|---|---|"]
    for v in SPEEDS:
        for m in MEM:
            for nz in (0, 1):
                q = {r["sys"]: r for r in rows if r["v"] == v and r["member"] == m and r["nz"] == nz}
                cell = lambda r: f"{r['peaks'][:3]} / {r['tail_cyc']} / {r['tail_pp']:.2f} / {r['frz']:.2f} / err {r['tail_err']:+.2f}"  # noqa: E731
                L.append(f"| {v} | {q['V298']['A']} | {m} | {nz} | {cell(q['V298'])} | {cell(q['A-rev1'])} | {cell(q['A-rev2'])} / {q['A-rev2']['a3']:.2f} |")
    L.append(f"wall {time.perf_counter() - T0:.1f} s")
    txt = "\n".join(L)
    print(txt)
    (RC.OUT / "rev_msfree.md").write_text(txt, encoding="utf-8")
