# -*- coding: utf-8 -*-
r"""e2_explore.py -- ROUND 1 of designer E2: every integral policy in ONE batch per (scenario, speed, member) on the
common time scorer, so every column sees identical inputs.  ANALYSIS ONLY.

COLUMNS (all on rev2-A's P2 skeleton: fresh-rate D Kd 34, the 6-knot G(v), Kp 112, Ki 56, guards A2/B2; only the
integral policy and ICL differ):
  P2        ICL 4096, freeze |tq| > 512 or ramp not full                     (rev2-A primary, the reference)
  I6k/I8k/I12k   ICL 6144 / 8192 / 12288, P2's policy                          (cal only: the clamp alone)
  S200r/S300r    ICL 8192 + OPPOSING-HAND freeze on raw gp-0x4f60 > 200 / 300 (policy i)
  S200l          ICL 8192 + OPPOSING-HAND freeze on Honda's 5 Hz IIR gp-0x3d34 (> 200 words equivalent)
  A12/A12h/A11   ICL 8192 + ANGLE-REFERENCED I BOUND, 102 T/deg + 200 T / 102 + 100 T / 51 + 200 T
  L13            ICL 8192 + LEAK (tau 146 ms) above |tq| 512 instead of the freeze (policy ii)
  LS             ICL 8192 + opposing hand > 200 raw LEAKS (tau 146 ms) instead of freezing (policy ii, sign-aware)
  A12S           ICL 8192 + ARB 102/200 + opposing-hand freeze raw 300
  A12-12k        ICL 12288 + ARB 102/200
usage: python e2_explore.py [th|rr|lurch|eng|all]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_exp as X  # noqa: E402
from e2_common import OUT  # noqa: E402

COLS = [
    ("P2", dict()),
    ("I6k", dict(icl=6144)),
    ("I8k", dict(icl=8192)),
    ("I12k", dict(icl=12288)),
    ("S200r", dict(icl=8192, sgn_thr=200)),
    ("S300r", dict(icl=8192, sgn_thr=300)),
    ("S200l", dict(icl=8192, sgn_thr=200, sgn_src="lp")),
    ("A12", dict(icl=8192, arb_k=12, arb_B=1250)),
    ("A12h", dict(icl=8192, arb_k=12, arb_B=625)),
    ("A11", dict(icl=8192, arb_k=11, arb_B=1250)),
    ("L13", dict(icl=8192, leak_s=13, leak_thr=512)),
    ("LS", dict(icl=8192, sgn_thr=200, leak_s=13, leak_thr=65535, leak_opp=True)),
    ("A12S", dict(icl=8192, arb_k=12, arb_B=1250, sgn_thr=300)),
    ("A12-12k", dict(icl=12288, arb_k=12, arb_B=1250)),
]
LAB = [k for k, _ in COLS]
CFG = [X.col(**kw) for _, kw in COLS]
MEM4 = ("nominal", "bc", "F_hi", "b_lo*J_hi")
TH_SPEEDS = (8.0, 9.0, 10.0, 11.0, 11.75, 12.5, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, 24.0, 26.9, 30.0)
ALAT = (1.5, 2.5, 3.5)
LURCH_SPEEDS = (3.1, 5.0, 8.0, 10.0, 11.0, 11.75, 12.5, 15.0, 19.0, 26.9)
LURCH_MEM = ("nominal", "bc", "b_lo*J_hi", "b_lo*J_hi+h10")


def tgt(v, a):
    return float(min(a * X.L_WB * X.SR_C / v ** 2 * 180 / np.pi, 90.0))


def jobs_th():
    return [(("th", v, tgt(v, a)), CFG, m) for m in MEM4 for v in TH_SPEEDS for a in ALAT]


def jobs_rr():
    R = X.r71b_runs()
    return [(("rr", b, i, rp), CFG, m) for m in MEM4 for rp in (False, True) for b in R for i in range(len(R[b]))]


def jobs_lurch():
    specs = []
    for v in LURCH_SPEEDS:
        specs += [("lh", v, w) for w in (100, 200, 400, 511)]
        specs += [("lk", v, k) for k in (0.15, 0.6, 2.0)]
        specs += [("ls", v, 300.0, k) for k in (0.6, 2.0)]
        specs += [("ov", v, 33)]
    return [(s, CFG, m) for m in LURCH_MEM for s in specs]


def jobs_eng():
    return [(("eng", v, ri), CFG, m) for m in LURCH_MEM for v in (3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 19.0, 26.0)
            for ri in (33, 328)]


def summarize(tag):
    res = json.loads((OUT / f"exp_{tag}.json").read_text())
    L = [f"# e2_explore {tag}: columns " + " ".join(LAB)]
    if tag == "th":
        for m in MEM4:
            for a in ALAT:
                rows = [x for x in res if x["member"] == m and abs(x["spec"][2] - tgt(x["spec"][1], a)) < 1e-9]
                rows.sort(key=lambda x: x["spec"][1])
                mn = np.min([x["m"]["hold"] for x in rows if x["spec"][1] >= 8.0], axis=0)
                L.append(f"turn-hold min over 8-30 m/s  {m:10s} a {a:.1f}: " + " ".join(f"{k} {h:.3f}" for k, h in zip(LAB, mn)))
                worst = [rows[int(np.argmin([x["m"]["hold"][j] for x in rows]))]["spec"][1] for j in range(len(LAB))]
                L.append(f"   at v: " + " ".join(f"{k} {w:g}" for k, w in zip(LAB, worst)))
    elif tag == "rr":
        sl = X.rr_slopes(res, len(LAB))
        for key in sorted(sl):
            L.append(f"r71b goal metric band {key[0]:>5s} replay {str(key[1]):5s} {key[2]:10s}: "
                     + " ".join(f"{k} {s:.3f}" for k, s in zip(LAB, sl[key])))
        for rp in (False, True):
            du = np.mean([x["m"]["frz_duty"] for x in res if x["spec"][3] == rp], axis=0)
            L.append(f"mean I-freeze/leak duty on r71b paths, replay {rp}: " + " ".join(f"{k} {d:.3f}" for k, d in zip(LAB, du)))
    elif tag == "lurch":
        kinds = sorted({tuple(x["spec"][:1] + x["spec"][2:]) for x in res}, key=str)
        for m in LURCH_MEM:
            for kd in kinds:
                rows = [x for x in res if x["member"] == m and tuple(x["spec"][:1] + x["spec"][2:]) == kd]
                lu = np.max([x["m"]["lurch"] for x in rows], axis=0)
                L.append(f"lurch max over speeds {m:14s} {str(kd):22s}: " + " ".join(f"{k} {h:.2f}" for k, h in zip(LAB, lu)))
    elif tag == "eng":
        for m in LURCH_MEM:
            for ri in (33, 328):
                rows = [x for x in res if x["member"] == m and x["spec"][2] == ri]
                dr = np.max([x["m"]["droop"] for x in rows], axis=0)
                ov = np.max([x["m"]["eng_ovs"] for x in rows], axis=0)
                L.append(f"engage droop max {m:14s} ramp {ri:3d}: " + " ".join(f"{k} {h:.2f}" for k, h in zip(LAB, dr)))
                L.append(f"engage overshoot max {m:10s} ramp {ri:3d}: " + " ".join(f"{k} {h:.2f}" for k, h in zip(LAB, ov)))
    txt = "\n".join(L)
    print(txt)
    (HERE / f"e2_explore_{tag}.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    groups = {"th": jobs_th, "rr": jobs_rr, "lurch": jobs_lurch, "eng": jobs_eng}
    todo = list(groups) if w == "all" else [w]
    for g in todo:
        if "--sum" not in sys.argv:
            X.run_jobs(groups[g](), g, procs=int(next((a[2:] for a in sys.argv if a.startswith("-p")), "8")))
        summarize(g)
