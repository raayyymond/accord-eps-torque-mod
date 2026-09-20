"""ADVERSARY A5 - hunt for ANY defensible recipe that yields the published high-jerk event gain "T64 1.29".

A4 found 1.05-1.11 for T64 under the study library's own defaults, on both achieved channels and both speed
gates. Before calling the published number unreproducible I sweep the choices a reasonable analyst could have
made: the aggregator (median / mean / pooled regression), the jerk threshold, the window, the speed gate, and
whether the gain is a regression or a peak ratio. If nothing lands near 1.29 for T64 while V282 keeps landing at
0.95-0.99, the contrast as published is not supported by these routes.

usage: python a5_eventgain_hunt.py
"""
import sys
from pathlib import Path
import numpy as np

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY))
import v282cmp as V

GROUPS = ["V282", "T64", "T64B", "T5", "T4", "V282old"]
CFG = []
for thr in (0.5, 0.8, 1.2):
    for vmin in (5.0, 15.0):
        for post in (3.0, 2.5):
            CFG.append(dict(thr=thr, vmin=vmin, post=post))

rows = []
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    for c in CFG:
        ev, _ = V.jerk_events(S, jerk_thr=c["thr"], vmin=c["vmin"], post=c["post"])
        for e in ev:
            i0 = e["idx"] - int(1.5 * V.FS); i1 = e["idx"] + int(c["post"] * V.FS)
            for ch in ("la_act", "la_pose"):
                m = V.event_metrics(S, i0, i1, ach_key=ch)
                rows.append(dict(g=meta["group"], r=rk, ch=ch, gain=m["gain"], pk=m["peak_ratio"], **c))
    del S

print(f"{'thr':>4s} {'vmin':>5s} {'post':>5s} {'ch':8s} {'agg':8s} | " + " ".join(f"{g:>9s}" for g in GROUPS))
hits = []
for c in CFG:
    for ch in ("la_act", "la_pose"):
        for agg in ("median", "mean", "routemed", "peakratio"):
            line = f"{c['thr']:4.1f} {c['vmin']:5.1f} {c['post']:5.1f} {ch:8s} {agg:8s} | "
            vals = {}
            for g in GROUPS:
                rr = [x for x in rows if x["g"] == g and x["ch"] == ch and all(x[k] == v for k, v in c.items())]
                if not rr:
                    line += f"{'--':>9s} "
                    continue
                if agg == "median":
                    z = float(np.median([x["gain"] for x in rr]))
                elif agg == "mean":
                    z = float(np.mean([x["gain"] for x in rr]))
                elif agg == "peakratio":
                    z = float(np.median([x["pk"] for x in rr]))
                else:
                    pr = {}
                    for x in rr:
                        pr.setdefault(x["r"], []).append(x["gain"])
                    z = float(np.median([np.median(v) for v in pr.values()]))
                vals[g] = z
                line += f"{z:9.3f} "
            print(line + f" n_T64 {len([x for x in rows if x['g']=='T64' and x['ch']==ch and all(x[k]==v for k,v in c.items())]):3d}")
            if "T64" in vals and vals["T64"] >= 1.22:
                hits.append((c, ch, agg, vals))

print(f"\nrecipes reaching T64 >= 1.22: {len(hits)}")
for c, ch, agg, vals in hits:
    print("   ", c, ch, agg, {k: round(v, 3) for k, v in vals.items()})
