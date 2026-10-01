# -*- coding: utf-8 -*-
"""c1r2_time.py -- the TIME harness (harness_time.run / metrics / per_speed_score, UNMODIFIED) on the C1 rev-2
candidates, with the cave emulated by c1_lib.LaneC1 exactly as the listing computes it.  Re-uses c1_time's job /
member / scoring machinery (rev 1's c1_time.rows() hard-coded Kd 16 per row, so this file builds its own rows from the
variants, each row carrying its own Kd and Ki).  ANALYSIS ONLY.

usage:  python c1r2_time.py run <suite>          (suites: nominal, robust, robust2, pi)
        python c1r2_time.py score <suite> [--detail]
Outputs: _scratch/angle_loop/c1/time_r2_<suite>.json ; c1/time_r2_<suite>_score.txt"""
from __future__ import annotations

import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402
import c1_time as T1  # noqa: E402   (installs the C1 lane into harness_time at import -- workers too)

HT = T1.HT
SPEEDS = T1.SPEEDS


CANDS = {   # label: (kp_base, kd, ki, knots) -- "C1r2" is c1_lib's r2 variant (THE rev-2 design); the alternative is the
            # 5-knot table under the same factorial envelope (12 table bytes fewer)
    "C1r2 (7 knots)": (C.VARIANTS["r2"]["kp"], C.VARIANTS["r2"]["kd"], C.VARIANTS["r2"]["ki"], C.VARIANTS["r2"]["knots"]),
    "alt 5 knots": (112, 20, 56, [(3.1, 940), (8.0, 1300), (10.0, 847), (11.75, 701), (26.9, 2041)]),
}


def rows():
    r = []
    for lab, (kp, kd, ki, kn) in CANDS.items():
        r.append(C.c1_row(C.make_table(kn), f"{lab} (freeze 512+ramp)", kp_base=kp, kd=kd, ki_base=ki, thr=512,
                          rampfrz=True, pol="freeze"))
    V = C.VARIANTS
    r.append(C.c1_row(C.make_table(V["kd16"]["knots"]), "C1 rev 1 (REFUTED; reference)", kp_base=225, kd=16,
                      ki_base=100, thr=512, rampfrz=True, pol="freeze"))
    return r


# ---- the round-2 refuter's combined members in the TIME harness (friction, quantisation, integer lane included).
# ---- b_q applies b -> max(0.25 b, 3.46) at >= 12.5 m/s EXACTLY as c1r2_members does (a per-speed override of
# ---- arrays_at, not a knot edit, so the step sits at 12.5 m/s and not on a V_CENTRES interpolation).
from dataclasses import dataclass as _dc  # noqa: E402

import numpy as _np  # noqa: E402

_member0 = T1.member


@_dc
class _BQ(T1.VP.PlantFamilyMember):
    def arrays_at(self, v):
        a = super().arrays_at(v)
        vv = _np.asarray(v, float)
        a["b"] = _np.where(vv >= 12.5, _np.maximum(0.25 * a["b"], 0.7 * 4.94), a["b"])
        return a


def _member(name):
    if name in ("b_q", "b_q*J_hi", "b_q*J1.0"):
        base = {"b_q": "nominal", "b_q*J_hi": "J_hi", "b_q*J1.0": "J1.0"}[name]
        m = _member0(base)
        kw = {k: getattr(m, k) for k in m.__dataclass_fields__}
        kw["name"] = name
        return _BQ(**kw)
    return _member0(name)


T1.member = _member

SUITES = dict(T1.SUITES)
SUITES["robust"] = dict(T1.SUITES["robust"])
SUITES["robust"]["members"] = T1.SUITES["robust"]["members"] + ("b_q", "b_q*J_hi", "b_q*J1.0")


def run_suite(suite):
    s = SUITES[suite]
    rw = rows()
    jobs = [(nm, v, rw, m, s["outer"], {}) for m in s["members"] for v in SPEEDS for nm in s["scen"]]
    t0 = time.time()
    out = []
    with Pool(14) as pool:
        for i, res in enumerate(pool.imap_unordered(T1.job, jobs)):
            out.append(res)
            if (i + 1) % 50 == 0 or i + 1 == len(jobs):
                print("  %s %d/%d, %.0f s" % (suite, i + 1, len(jobs), time.time() - t0), flush=True)
    (C.OUT / f"time_r2_{suite}.json").write_text(json.dumps(dict(rows=rw, results=out)))


def score(suite, detail=False):
    # c1_time.score reads time_<suite>.json and writes time_<suite>_score.txt; point it at the rev-2 files
    src = C.OUT / f"time_r2_{suite}.json"
    tmp = C.OUT / f"time_r2tmp_{suite}.json"
    tmp.write_bytes(src.read_bytes())
    orig_here = T1.HERE
    T1.HERE = C.OUT
    try:
        T1.score(f"r2tmp_{suite}", detail=detail)
    finally:
        T1.HERE = orig_here
    (HERE / f"time_r2_{suite}_score.txt").write_bytes((C.OUT / f"time_r2tmp_{suite}_score.txt").read_bytes())


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run_suite(sys.argv[2])
    else:
        score(sys.argv[2], detail="--detail" in sys.argv)
