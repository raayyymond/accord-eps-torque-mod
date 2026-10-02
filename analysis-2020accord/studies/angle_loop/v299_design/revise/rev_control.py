# -*- coding: utf-8 -*-
"""rev_control.py -- the transformed engines (rev_common) reproduce the originals bit for bit at the defaults, and the
two new switches are live (negative controls).  60-deg hands-off turn-in at 6 / 10 / 12.5 m/s, both members.  ANALYSIS ONLY."""
import sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rev_common as RC


def s2_job(which):
    S2 = RC.load_s2() if which != "orig" else RC.load_s2_orig()
    G4 = dict(inst=1200.0, d600=8, o1lead=0.0, take=0.4)
    S2.FK["SYNA"] = dict(**G4)
    S2.CANDS = {"V298": ("V298", "V298", ""), "SYN-A": ("D1c", "SYNA", "")}
    if which == "cap":
        S2.FW["D1cC"] = dict(thr=1229, sgn=0, asym=True, capv=2880, capval=6144)
        S2.CANDS["SYN-A"] = ("D1cC", "SYNA", "")
    if which == "short":
        S2.FK["SYNA"] = dict(short_n=5, **G4)
    cols = [dict(cid=c, member=m, v=v, x="ti", s=1) for c in ("V298", "SYN-A") for m in S2.MEMBERS for v in (6.0, 10.0, 12.5)]
    A = 50.0; Rt = np.array([S2.plan_rate(c["v"]) for c in cols]); t0 = 0.5; tu = t0 + A / Rt + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A)  # noqa
    R = S2.run(cols, 4.0, plan, np.zeros(len(cols)))
    return which, R["th"].astype(np.float64), R["T"].astype(np.int64)


def rsn_job(which):
    E = RC.load_rsn() if which != "orig" else RC.load_rsn_orig()
    var = dict(capv=2880, capval=6144) if which == "cap" else {}
    fk = "A_s5" if which == "short" else "A"
    cols = [dict(rule=r, fork=f, member=m, v=v, variant=(var if r == "V299" else {}))
            for r, f in (("V298", "V298"), ("V299", fk)) for m in ("r79F", "b_lo*J_hi") for v in (6.0, 10.0, 12.5)]
    A = 50.0; Rt = E.plan_rate(8.0); t0 = 0.5; tu = t0 + A / Rt + 2.5
    plan = lambda t: np.clip((t - t0) * Rt, 0, A) - np.clip((t - tu) * Rt, 0, A) + np.zeros(len(cols))  # noqa
    R = E.run(cols, 4.0, plan, seed=101, rec=("th", "T"))
    return which, R["th"].astype(np.float64), R["T"].astype(np.int64)


if __name__ == "__main__":
    T0 = time.perf_counter()
    with Pool(8) as p:
        a = p.map(s2_job, ("orig", "rev", "cap", "short"))
        b = p.map(rsn_job, ("orig", "rev", "cap", "short"))
    for eng, res in (("S2", a), ("RSN", b)):
        d = {w: (th, T) for w, th, T in res}
        o = d["orig"]
        for w in ("rev", "cap", "short"):
            dth = np.abs(d[w][0] - o[0]).max(axis=0); dT = np.abs(d[w][1] - o[1]).max(axis=0)
            print(f"{eng}: transformed '{w}' vs original: max|dth| per column {np.round(dth, 4).tolist()}  "
                  f"max|dT| {dT.tolist()}")
    print(f"wall {time.perf_counter() - T0:.1f} s")
