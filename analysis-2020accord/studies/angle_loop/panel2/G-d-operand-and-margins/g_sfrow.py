# -*- coding: utf-8 -*-
r"""g_sfrow.py -- each of designer G's implementations as ONE ROW of the common frequency scorer's own table
(panel/score_freq.py: its score(), its summarize(), its write_report() column set; the brief's GATED set at kappa 1, the
0.25 m/s grid, hold ages 1-10 and 11-20), with NOTHING changed -- so the row is directly comparable with
SCORE-FREQ-2026-10-01.md.  The angle-own D (box10) is not a score_freq Cand kind; its row uses g_ext.metrics_ext (the same
extractor, the box10 FRF added) and is marked.  The pm reported here is score_freq's own formula; g_gate shows it equals
pm_fixed on every point of every implementation.  ANALYSIS ONLY.
usage: python g_sfrow.py <impl> ...   -> g_sfrow_out.md"""
from __future__ import annotations

import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402
import g_gate as GG  # noqa: E402

SF = X.SF


def job(args):
    iid, m, v = args
    c = GG.cand_of(iid)
    if GG.impls()[iid]["dkind"] == "box10":
        r = X.metrics_ext(c, m, v)
        r["pm"] = r["pm_raw"]
        pr = c.cont(v)
        r["kp_eff"] = pr["kp"] * pr["G"] / 256.0
        r["ki_eff"] = pr["ki"] * pr["G"] / 256.0
        r["has_I"] = pr["ki"] > 0
        return iid, m, v, r
    return iid, m, v, SF.score(c, m, v)


def main(iids, procs=6):
    members, speeds = list(SF.GATED), SF.GRID
    v295M20 = SF.score_ref("V295", "nominal", 12.5)["M20"]
    v294M20 = SF.score_ref("V294", "nominal", 12.5)["M20"]
    refRe = {nm: {ff: SF.score_ref(nm, "nominal", 12.5)[f"ReTw{ff}"] for ff in (7, 10, 13, 16, 20)}
             for nm in ("V294", "V295", "V282")}
    import numpy as np
    v295Re20 = {0: 1e9, 10: 1e9}
    for v in speeds:
        for ea, nm in ((0, "nominal"), (10, "nominal+h10")):
            Pt, Pw, d, ea2, _ = SF.plant_frf(nm, v)
            Cth, Cw, Cref, K = SF.ref_ctl_frf("V295", SF.FGRID, d, ea2)
            iff = int(np.argmin(abs(SF.FGRID - 20.0)))
            wf = 2 * np.pi * 20.0
            v295Re20[ea] = min(v295Re20[ea], float((-K[iff] * (Cth[iff] + 1j * wf * Cw[iff]) / (1j * wf)).real))
    v295L20 = {(m, v): SF.score_ref("V295", m, v)["L20"] for m in members for v in speeds}
    with Pool(procs) as pool:
        res = pool.map(job, [(i, m, v) for i in iids for m in members for v in speeds], chunksize=16)
    summary = {}
    for iid in iids:
        rows = {(m, v): r for i, m, v, r in res if i == iid}
        summary[iid] = SF.summarize(GG.cand_of(iid), rows, members, speeds, v295M20, v294M20, v295L20, v295Re20, refRe)
        summary[iid]["cid"] = iid
    refpack = dict(v295M20=v295M20, v294M20=v294M20, v295Re20=v295Re20, refRe=refRe)
    keep = SF.OUT
    SF.OUT = X.OUT                                   # write_report's table file goes to this designer's scratch
    try:
        table = SF.write_report(summary, refpack, False)
    finally:
        SF.OUT = keep
    (HERE / "g_sfrow_out.md").write_text(
        "# designer G's implementations as rows of the common frequency scorer's table (score_freq, unchanged; brief's "
        "gated set, kappa 1)\n\n" + table + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
