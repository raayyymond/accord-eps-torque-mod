# -*- coding: utf-8 -*-
"""SECTION Q -- the fork/route CONTROL.  V282old is the SAME EPS with an older fork on other roads.
If its excess tracking error is as large as the torque mode's AND made of the same thing, the stream's
attribution fails.  Same admissibility, same decomposition."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import dflib as D, fastH as FH, v282cmp as C
from summary import GROUPS, G2R, gather, decomp, cellp, build, splithalf, MIN_WIN, cells

LOG = []
def pr(s=""):
    print(s, flush=True); LOG.append(s)

SURF = build("y", 2)
pr("=" * 134)
pr("SECTION Q   CONTROL -- V282old (same V282 EPS, older fork, different roads) scored the same way")
pr("=" * 134)
pr("Question: is the torque mode's deficit distinguishable from ordinary fork/route variation?")
pr("")
pr(f"{'band':>11s} {'v':>7s} {'Q':>2s} | {'V282':>18s} | {'V282old vs V282':>34s} | {'TQall vs V282':>34s}")
pr(f"{'':>11s} {'':>7s} {'':>2s} | {'H':>5s}{'NE':>6s}{'lag':>7s} | {'H':>5s}{'NE':>6s}{'NEx':>5s}{'dlag':>6s}"
   f"{'lagfrac':>8s}{'n':>5s} | {'H':>5s}{'NE':>6s}{'NEx':>5s}{'dlag':>6s}{'lagfrac':>8s}{'n':>5s}")
rows = []
for f1, f2, W in D.BANDS[:4]:
    WS = SURF[(f1, f2, W)]
    for slo, shi in D.SPD:
        pooled = [w["A"] for g, rks in GROUPS if g != "TQall" for rk in rks for w in WS[rk]
                  if slo <= w["v"] < shi]
        if len(pooled) < 5 * MIN_WIN:
            continue
        ed = [float(q) for q in np.percentile(pooled, [0, 25, 50, 75, 90, 100])]
        ed[0], ed[-1] = 0.0, 1e9
        for q in range(5):
            wv = gather(WS, G2R["V282"], slo, shi, ed[q], ed[q+1])
            wo = gather(WS, G2R["V282old"], slo, shi, ed[q], ed[q+1])
            wt = gather(WS, G2R["TQall"], slo, shi, ed[q], ed[q+1])
            v, o, t = cellp(wv), cellp(wo), cellp(wt)
            if not v or v["coh"] < D.COH_MIN:
                continue
            def blk(r):
                if not r or r["coh"] < D.COH_MIN:
                    return f"{'--':^34s}", None
                d = decomp(r, v)
                ex = d["NEc"] - d["NEc_v"]
                fr = (d["NEc"] - d["NEc_gain"]) / ex if ex > 0.02 else float("nan")
                return (f"{r['H']:5.2f}{r['NE']:6.2f}{r['NE']/max(v['NE'],1e-9):5.2f}"
                        f"{1000*(r['lag']-v['lag']):+6.0f}{fr:8.2f}{r['n']:5d}", (ex, fr))
            bo, ro = blk(o); bt, rt = blk(t)
            if ro is None and rt is None:
                continue
            pr(f"{f'{f1:.2f}-{f2:.2f}':>11s} {f'{slo}-{shi}':>7s} {q+1:2d} | "
               f"{v['H']:5.2f}{v['NE']:6.2f}{1000*v['lag']:+7.0f} | {bo} | {bt}")
            rows.append((ro, rt))
pr("")
for nm, i in (("V282old", 0), ("TQall", 1)):
    fr = [r[i][1] for r in rows if r[i] and np.isfinite(r[i][1]) and r[i][0] > 0.02]
    ex = [r[i][0] for r in rows if r[i] and r[i][0] > 0.02]
    if fr:
        pr(f"{nm:8s}: {len(ex)} admissible cells with a positive coherent excess; median excess "
           f"{np.median(ex):.2f}; LAG accounts for a median {100*np.median(fr):.0f} % of it "
           f"(IQR {100*np.percentile(fr,25):.0f}-{100*np.percentile(fr,75):.0f} %); "
           f">=60 % in {sum(1 for f in fr if f>=0.6)}/{len(fr)} cells")
with open(os.path.join(HERE, "CONTROL-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
