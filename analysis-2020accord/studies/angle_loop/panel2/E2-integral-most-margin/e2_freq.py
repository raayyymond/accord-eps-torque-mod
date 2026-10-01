# -*- coding: utf-8 -*-
r"""e2_freq.py -- GATE 2 for designer E2's implementations on THE COMMON FREQUENCY SCORER (panel/score_freq.py, used by
composition: its validate(), score(), summarize() and reference computations, unchanged).  ANALYSIS ONLY.

What the integral policies do to the LINEAR loop (EVIDENCE by construction, the lane code): every E2 policy (ICL, the
opposing-hand freeze, the angle-referenced bound, the leak) acts ONLY through the I's input r6 and Honda's clamp.  While
no condition holds (hands off, |I| below the bound and below ICL) the loop is P2's exactly; while a freeze holds it is
P2 with the I frozen = the Ki-0 loop.  So GATE 2 is scored on exactly two linear loops:
  P2       (Kp 112, Ki 56, fresh-rate D Kd 34, P2's 6-knot G)  -- CONTROL: reproduces rev2-A's 0 fails / 46.7 / 32.6
  P2-I0    the same with Ki 0: every frozen state of every E2 policy, AND policy (iii)'s firmware loop
and, as the inherited-defect check, the refuters' D-operand frame reading FA (D per plant degree x 1/1.155, the
measured gp-0x6a00 : motor-frame slope near centre): P2-FA, P2-I0-FA.  The leak (policy ii) is a lag-integrator
Ki/(1 - (1 - lambda) z), lambda = 56/8192, between those two loops; it is not scored separately (BELIEF).
usage: python e2_freq.py [quick]"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from e2_common import R, OUT  # noqa: E402
import score_freq as SF  # noqa: E402


def cands():
    tbl = [tuple(r) for r in R.tables()["P2"]]
    p2 = SF.Cand("P2", "rev2A", kind="angle", dsrc="op", dop="fresh_rate", cont=SF.cave_cont_rows(tbl, 112, 56, 34),
                 note="rev2-A P2 (E2's skeleton)")
    i0 = replace(p2, cid="P2-I0", cont=SF.cave_cont_rows(tbl, 112, 0, 34), note="P2 with the I frozen / Ki 0")
    fa = replace(p2, cid="P2-FA", dop_k=1 / 1.155, note="P2, D operand x 1/1.155 (frame reading FA)")
    i0fa = replace(i0, cid="P2-I0-FA", dop_k=1 / 1.155, note="P2-I0, frame reading FA")
    return [p2, i0, fa, i0fa]


def _row(args):
    cid, m, v = args
    c = {x.cid: x for x in cands()}[cid]
    return (cid, m, v), SF.score(c, m, v)


def main(quick=False):
    t0 = time.time()
    assert SF.validate()
    members = SF.GATED if not quick else ("nominal", "J_hi", "b_lo", "b_q", "b_q*J1.0", "b_q*J1.0+h10")
    speeds = SF.GRID if not quick else [3.0, 8.0, 12.5, 17.0, 26.9]
    v295M20 = SF.score_ref("V295", "nominal", 12.5)["M20"]
    v294M20 = SF.score_ref("V294", "nominal", 12.5)["M20"]
    refRe = {nm: {ff: SF.score_ref(nm, "nominal", 12.5)[f"ReTw{ff}"] for ff in (7, 10, 13, 16, 20)}
             for nm in ("V294", "V295", "V282")}
    v295Re20 = {0: 1e9, 10: 1e9}
    for v in speeds:
        for ea, nm in ((0, "nominal"), (10, "nominal+h10")):
            Pt, Pw, d, ea2, _ = SF.plant_frf(nm, v)
            Cth, Cw, Cref, K = SF.ref_ctl_frf("V295", SF.FGRID, d, ea2)
            iff = int(np.argmin(abs(SF.FGRID - 20.0)))
            wf = 2 * np.pi * 20.0
            v295Re20[ea] = min(v295Re20[ea], float((-K[iff] * (Cth[iff] + 1j * wf * Cw[iff]) / (1j * wf)).real))
    v295L20 = {(m, v): SF.score_ref("V295", m, v)["L20"] for m in members for v in speeds}
    jobs = [(c.cid, m, v) for c in cands() for m in members for v in speeds]
    rows = {}
    with Pool(6) as pool:
        for k, r in pool.imap_unordered(_row, jobs, chunksize=40):
            rows[k] = r
    L = [f"# e2_freq: GATE 2 on the common scorer, {len(members)} gated members x {len(speeds)} speeds "
         f"({time.time() - t0:.0f} s)"]
    summ = {}
    for c in cands():
        rr = {(m, v): rows[(c.cid, m, v)] for m in members for v in speeds}
        s = SF.summarize(c, rr, list(members), list(speeds), v295M20, v294M20, v295L20, v295Re20, refRe)
        summ[c.cid] = s
        L.append(f"[{c.cid:9s}] minPM nominal {s['minPM_nom']:.1f} | tier-A single {s['minPM_single']:.1f} | "
                 f"tier-B combined {s['minPM_comb']:.1f} ({s['bind']}) | peak 5-30 {s['peak530']:+.1f} dB | "
                 f"M20 x{s['M20_ratio']:.2f} | L20 x{s['L20_ratio']:.2f} | fails {s['n_fail']}")
        for f in s["fails"][:12]:
            L.append(f"      fail {f}")
    txt = "\n".join(L)
    print(txt)
    (HERE / ("e2_freq_out.txt" if not quick else "e2_freq_quick.txt")).write_text(txt + "\n", encoding="utf-8")
    (OUT / "e2_freq_summary.json").write_text(json.dumps(summ, default=float, indent=1))


if __name__ == "__main__":
    main(quick=len(sys.argv) > 1 and sys.argv[1] == "quick")
