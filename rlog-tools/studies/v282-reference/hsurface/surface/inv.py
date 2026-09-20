# -*- coding: utf-8 -*-
"""Inventory that decides the surface's grid: how much laterally-engaged time each route carries,
how it splits by speed, and the RUN-LENGTH distribution (a window longer than the runs means no cell).

Also checks the instrument is comparable between the two EPS modes before any |H| is computed:
  - corr(la_pose, la_act) and the sign of la_pose, per route;
  - the model->achieved scale on a slow band (a gross-error tripwire);
  - what fraction of frames are railed (|out| >= 0.99), per speed bin, per route.

ANALYSIS ONLY, read-only.  usage: python inv.py
"""
import json, os, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import v282cmp as V  # noqa: E402

SPD = [(0, 8), (8, 15), (15, 22), (22, 40)]
EXTRA = {  # cached routes not in the shared registry; group from params_all.json (own initData)
    "00000070--717f5a7866": dict(group="T2", eps="V293", note="rev 2 ident, RatePlantFF=0"),
    "00000071--f2c9d073a3": dict(group="T2", eps="V293", note="rev 2, fric 0.011"),
    "00000072--8001fc3048": dict(group="T3", eps="V293", note="rev 3, fric 0.0"),
    "00000073--79fd149dd8": dict(group="T3", eps="V293", note="rev 3, fric 0.212 (hidden relay)"),
    "00000074--2bf17ca67d": dict(group="T4", eps="V293", note="rev 4, short"),
}
ALL = dict(V.ROUTES)
for k, v in EXTRA.items():
    ALL.setdefault(k, v)

rows = []
print("route                    grp      eng_s   runs  runlen p50/p90/max   " + "  ".join(f"{a}-{b}m/s" for a, b in SPD))
for rk in sorted(ALL):
    f = V.CACHE / f"{rk}.npz"
    if not f.exists():
        print(f"{rk:24s} NO CACHE"); continue
    S = V.load(rk)
    u = V.usable(S)
    rr = V.runs(u, S["t"], min_s=2.0)
    L = np.array([(S["t"][b - 1] - S["t"][a]) for a, b in rr]) if rr else np.array([0.0])
    per = []
    for lo, hi in SPD:
        m = V.usable(S, lo, hi)
        per.append(m.sum() / V.FS)
    # instrument
    uu = u & np.isfinite(S["la_pose"]) & np.isfinite(S["la_act"])
    c_pa = float(np.corrcoef(S["la_pose"][uu], S["la_act"][uu])[0, 1]) if uu.sum() > 100 else float("nan")
    c_mp = float(np.corrcoef(np.nan_to_num(S["model"][uu]), S["la_pose"][uu])[0, 1]) if uu.sum() > 100 else float("nan")
    sl = float(np.dot(S["la_pose"][uu], np.nan_to_num(S["model"][uu])) /
               max(np.dot(np.nan_to_num(S["model"][uu]), np.nan_to_num(S["model"][uu])), 1e-9)) if uu.sum() > 100 else float("nan")
    rail = {}
    for lo, hi in SPD:
        m = V.usable(S, lo, hi)
        rail[f"{lo}-{hi}"] = float((np.abs(S["out"][m]) >= 0.99).mean()) if m.sum() > 50 else float("nan")
    rows.append(dict(route=rk, group=ALL[rk]["group"], eng=float(u.sum() / V.FS), nruns=len(rr),
                     p50=float(np.percentile(L, 50)), p90=float(np.percentile(L, 90)), mx=float(L.max()),
                     per_spd=per, corr_pose_act=c_pa, corr_model_pose=c_mp, slope_model_pose=sl, rail=rail))
    print(f"{rk:24s} {ALL[rk]['group']:8s} {u.sum()/V.FS:7.0f} {len(rr):5d}  "
          f"{np.percentile(L,50):5.1f}/{np.percentile(L,90):5.1f}/{L.max():6.1f}   " +
          "  ".join(f"{p:7.0f}" for p in per))
    del S

print("\ninstrument comparability (usable frames): corr(pose,act)  corr(model,pose)  slope pose~model  rail frac by speed")
for r in rows:
    print(f"   {r['route']:24s} {r['group']:8s} {r['corr_pose_act']:+.3f}  {r['corr_model_pose']:+.3f}  {r['slope_model_pose']:+.3f}   " +
          "  ".join(f"{k}:{v:.4f}" for k, v in r["rail"].items()))

# run-length availability: how many W-second windows exist per speed bin at several W
print("\nwindows available per speed bin at window length W (non-overlapping, inside one contiguous run)")
for W in (5.12, 10.24, 20.48, 40.96):
    n = int(W * V.FS)
    print(f"  W={W:6.2f}s")
    for grp in ("V282", "V282old", "T64", "T64B", "T5", "T4", "T3", "T2"):
        tot = [0, 0, 0, 0]
        for r in rows:
            if r["group"] != grp:
                continue
            S = V.load(r["route"])
            for lo, hi in SPD:
                m = V.usable(S, lo, hi)
                for a, b in V.runs(m, S["t"], min_s=W):
                    tot[SPD.index((lo, hi))] += (b - a) // n
            del S
        print(f"     {grp:8s} " + "  ".join(f"{t:5d}" for t in tot))

json.dump(rows, open(HERE / "inv.json", "w"), indent=1)
print("\nwrote inv.json")
