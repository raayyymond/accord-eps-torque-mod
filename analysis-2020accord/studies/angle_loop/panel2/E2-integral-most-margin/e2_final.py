# -*- coding: utf-8 -*-
r"""e2_final.py -- THE SCORED RUN of designer E2's implementations (after e2_explore.py), in ONE batch per (scenario,
speed, member) so every column sees identical inputs, all on the common time scorer (c2/rev2A/score_time.run with the
additive lane_cls / ramp_in / tq_cols hooks) and E2Lane (CONTROL E2-0, CONTROL C).  ANALYSIS ONLY.

  suite   the common scorer's OWN scenario list, speeds and members (score_time.SCENS x SPEEDS x MEMBERS), its OWN
          metrics (score_time.metrics) -- the scenarios exactly as defined there (their hand words are UNSIGNED
          positive, which an opposing-hand test reads as an AIDING hand: the conservative reading for policy S)
  ext     e2_exp's scenarios: turn-hold sized from r71b, the goal metric on r71b's paths (clean and with r71b's own
          torque word replayed), the light-hand family (signed word / consistent sensor / torque source), the firm
          hand, engage-under-load at the stock and the gp-0x6803 == 2 ramp-in.
usage: python e2_final.py suite|ext [-pN]  ;  python e2_final.py sum"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2_exp as X  # noqa: E402
from e2_common import ST, OUT  # noqa: E402
import e2_explore as EX  # noqa: E402

COLS = [
    ("P2", dict()),                                                     # rev2-A primary, unchanged (reference)
    ("R1", dict(icl=8192)),                                             # ICL only (cal)
    ("S", dict(icl=8192, sgn_thr=300)),                                 # (i) opposing-hand freeze, raw > 300
    ("L", dict(icl=8192, leak_s=13, leak_thr=512)),                     # (ii) leak tau 146 ms above |tq| 512
    ("A", dict(icl=8192, arb_sh=6, arb_B=1250)),                        # (v) angle-referenced bound, one slope
    ("A2", dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250)),            # (v) two slopes
    ("A2S", dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, sgn_thr=300)),  # (v)+(i)
    ("A2-12k", dict(icl=12288, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250)),       # (v) larger clamp
    ("A2-NR", dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, ramp_frz=False)),  # no ramp freeze
    ("A2-X", dict(icl=8192, arb_sh=6, arb_sh_lo=4, arb_vth=2880, arb_B=1250, fade2=True)),       # + (iv) fade arm
]
LAB = [k for k, _ in COLS]
CFG = [X.col(**kw) for _, kw in COLS]


def job_suite(args):
    name, v, mem = args
    scn = ST.scenario(name, v)
    t0 = time.time()
    r = ST.run(scn, CFG, [], mem, v, lane_cls=X.E2LaneCap)
    m = ST.metrics(name, scn, r, v)
    return dict(name=name, v=v, member=mem, metrics={k: np.asarray(x, float).tolist() for k, x in m.items()},
                sec=time.time() - t0)


def jobs_ext():
    J = []
    for m in EX.MEM4:
        for v in EX.TH_SPEEDS:
            for a in EX.ALAT:
                J.append((("th", v, EX.tgt(v, a)), CFG, m))
    R = X.r71b_runs()
    for m in EX.MEM4:
        for rp in (False, True):
            for b in R:
                for i in range(len(R[b])):
                    J.append((("rr", b, i, rp), CFG, m))
    for m in EX.LURCH_MEM:
        for v in EX.LURCH_SPEEDS:
            for w in (100, 200, 400, 511):
                J.append((("lh", v, w), CFG, m))
            for k in (0.15, 0.6, 2.0):
                J.append((("lk", v, k), CFG, m))
            for k in (0.6, 2.0):
                J.append((("ls", v, 300.0, k), CFG, m))
            J.append((("ov", v, 33), CFG, m))
        for v in (3.0, 5.0, 8.0, 10.0, 12.5, 15.0, 19.0, 26.0):
            for ri in (33, 328):
                J.append((("eng", v, ri), CFG, m))
    return J


def run_suite(procs):
    jobs = [(s, v, m) for m in ST.MEMBERS for v in ST.SPEEDS for s in ST.SCENS]
    t0 = time.time()
    out = []
    with Pool(procs) as pool:
        for i, res in enumerate(pool.imap_unordered(job_suite, jobs, chunksize=1)):
            out.append(res)
            if (i + 1) % 50 == 0 or i + 1 == len(jobs):
                print(f"  suite: {i + 1}/{len(jobs)}, {time.time() - t0:.0f} s", flush=True)
    (OUT / "final_suite.json").write_text(json.dumps(dict(labels=LAB, results=out)))


if __name__ == "__main__":
    w = sys.argv[1] if len(sys.argv) > 1 else "ext"
    procs = int(next((a[2:] for a in sys.argv if a.startswith("-p")), "6"))
    if w == "suite":
        run_suite(procs)
    elif w == "ext":
        X.run_jobs(jobs_ext(), "final_ext", procs=procs)
