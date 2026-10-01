# -*- coding: utf-8 -*-
r"""e2_a3.py -- the A3 refinement (A2 + a low-speed cap: below 6 m/s the bound is min(bound, 4096 S) = P2's own ICL),
scored against P2 and A2 on the same common-scorer batches: the whole hand family at 3.1-26.9 m/s on the four hand
members, and turn-hold at 3.1-7 m/s where the cap could bind.  ANALYSIS ONLY.  usage: python e2_a3.py [-pN] | sum"""
import json
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_exp as X  # noqa: E402
import e2_explore as EX  # noqa: E402
from e2_common import OUT  # noqa: E402

A2 = dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250)
COLS = [("P2", dict()), ("A2", A2), ("A3", dict(A2, arb_vcap=1382, arb_cap=4096)),
        ("A3-12k", dict(A2, icl=12288, arb_vcap=1382, arb_cap=4096))]
LAB = [k for k, _ in COLS]
CFG = [X.col(**kw) for _, kw in COLS]
SPEEDS = (3.1, 5.0, 6.0, 7.0, 8.0, 10.0, 11.75, 15.0, 19.0, 26.9)


def jobs():
    J = []
    for m in EX.LURCH_MEM:
        for v in SPEEDS:
            for w in (100, 400):
                J.append((("lh", v, w), CFG, m))
            for k in (0.15, 0.6, 2.0):
                J.append((("lk", v, k), CFG, m))
            J.append((("ls", v, 300.0, 0.6), CFG, m))
            J.append((("ov", v, 33), CFG, m))
    for m in EX.MEM4:
        for v in (3.1, 5.0, 6.0, 7.0):
            for a in (0.5, 1.0, 1.5):
                J.append((("th", v, EX.tgt(v, a)), CFG, m))
    return J


def summ():
    res = json.loads((OUT / "exp_a3.json").read_text())
    L = ["# e2_a3: A2 vs A3 (low-speed cap = P2's ICL below 6 m/s); lurch max per member, < 8 m/s | >= 8 m/s, worst over hands"]
    for m in EX.LURCH_MEM:
        rr = [x for x in res if x["member"] == m and x["spec"][0] != "th"]
        lo = np.max([x["m"]["lurch"] for x in rr if x["spec"][1] < 8], axis=0)
        hi = np.max([x["m"]["lurch"] for x in rr if x["spec"][1] >= 8], axis=0)
        L.append(f"{m:14s} " + " ".join(f"{k} {a:.2f} | {b:.2f}" for k, a, b in zip(LAB, lo, hi)))
        for v in SPEEDS[:5]:
            vv = np.max([x["m"]["lurch"] for x in rr if x["spec"][1] == v], axis=0)
            L.append(f"   v {v:4.1f}: " + " ".join(f"{k} {a:.2f}" for k, a in zip(LAB, vv)))
    for m in EX.MEM4:
        for a in (0.5, 1.0, 1.5):
            rr = [x for x in res if x["member"] == m and x["spec"][0] == "th" and abs(x["spec"][2] - EX.tgt(x["spec"][1], a)) < 1e-9]
            mn = np.min([x["m"]["hold"] for x in rr], axis=0)
            L.append(f"turn-hold 3.1-7 m/s min {m:10s} a {a:.1f}: " + " ".join(f"{k} {h:.3f}" for k, h in zip(LAB, mn)))
    txt = "\n".join(L)
    print(txt)
    (HERE / "e2_a3_out.txt").write_text(txt + "\n", encoding="utf-8")




def jobs_lo():
    """the common scorer's own low-speed scenarios (std = score_time.scenario + metrics) for P2 / A2 / A3 / A3-12k."""
    from e2_common import ST
    return [(("std", v, s), CFG, m) for m in ST.MEMBERS for v in (3.1, 5.0) for s in ("rh", "s02", "s05", "ssm", "st", "db",
                                                                                         "ov_light400", "ov_fade", "cs")]


def summ_lo():
    res = json.loads((OUT / "exp_a3lo.json").read_text())
    L = ["# e2_a3 low-speed (3.1 / 5 m/s) on the common scorer's own scenarios and metrics: P2 / A2 / A3 / A3-12k"]
    for key, nm, fn in (("dj_events", ("s02", "s05", "ssm"), np.sum), ("stick_pct", ("ssm",), np.max),
                        ("hold_ratio", ("rh",), np.min), ("overshoot_pct", ("st",), np.max), ("db_lag", ("db",), np.max),
                        ("lurch_overshoot", ("ov_light400",), np.max), ("lurch_overshoot", ("ov_fade",), np.max),
                        ("cs_droop", ("cs",), np.max), ("hold_slips", ("rh",), np.sum)):
        rr = [x for x in res if x["spec"][2] in nm and key in x["m"]]
        if rr:
            val = fn(np.array([x["m"][key] for x in rr]), axis=0)
            L.append(f"{key:16s} {'+'.join(nm):12s}: " + " ".join(f"{k} {v:.2f}" for k, v in zip(LAB, val)))
    txt = "\n".join(L)
    print(txt)
    (HERE / "e2_a3_lo_out.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    procs = int(next((a[2:] for a in sys.argv if a.startswith("-p")), "4"))
    if "lo" in sys.argv:
        if "sum" not in sys.argv:
            X.run_jobs(jobs_lo(), "a3lo", procs=procs)
        summ_lo()
    else:
        if "sum" not in sys.argv:
            X.run_jobs(jobs(), "a3", procs=procs)
        summ()
