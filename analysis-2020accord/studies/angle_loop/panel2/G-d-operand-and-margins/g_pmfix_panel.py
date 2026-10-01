# -*- coding: utf-8 -*-
r"""g_pmfix_panel.py -- does the shared PM formula (finding 1) change any number the round-1 panel / SCORE-FREQ published?
Re-scores every score_freq candidate (score_freq.CANDS, the panel's own specs) on the brief's gated set and grid at kappa 1
and lists every point where pm_fixed != the shared formula, with the crossing phases and whether the GATE-2 verdict at that
point changes.  ANALYSIS ONLY.   usage: python g_pmfix_panel.py   -> g_pmfix_panel_out.txt"""
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g_ext as X  # noqa: E402

SF = X.SF


def job(args):
    ci, m, v = args
    c = SF.CANDS[ci]
    if c.kind != "angle":
        return None
    try:
        r = X.metrics_ext(c, m, v)
    except Exception:
        return None
    if abs(r["pm"] - r["pm_raw"]) > 1e-6:
        bar = SF.PMBAR.get(m, 45.0 if m in SF.TIER_A else 30.0)
        return (c.cid, m, v, r["pm_raw"], r["pm"], (r["pm_raw"] < bar) != (r["pm"] < bar))
    return None


if __name__ == "__main__":
    jobs = [(i, m, v) for i in range(len(SF.CANDS)) for m in SF.GATED for v in SF.GRID]
    with Pool(6) as pool:
        res = [r for r in pool.map(job, jobs, chunksize=32) if r]
    L = [f"points where pm_fixed != the shared formula, over every angle-kind score_freq candidate x the brief's gated set x "
         f"the 0.25 m/s grid ({len(jobs)} points): {len(res)}; GATE-2 verdict changed at {sum(1 for r in res if r[5])}"]
    for r in res[:60]:
        L.append(f"   {r[0]:16s} {r[1]:22s} @{r[2]:5.2f}: shared {r[3]:7.1f}  fixed {r[4]:6.1f}  verdict changed: {r[5]}")
    print("\n".join(L))
    (HERE / "g_pmfix_panel_out.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
