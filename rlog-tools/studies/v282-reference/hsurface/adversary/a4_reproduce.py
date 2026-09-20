"""ADVERSARY A4 - can the PUBLISHED numbers be reproduced with the study's OWN library, and how far do they move
under choices the published table does not state?

Targets: (a) band |H| 0.89/0.90/1.12 and 1.09/1.17/1.31; (b) the high-jerk event gains 0.95-0.99 vs 1.29.
For (b) the published table does not say which achieved channel was used, and v282cmp.event_metrics DEFAULTS to
`la_act`, which A3 showed is curvature*v^2 - an angle-derived channel whose scale is a fork constant.

usage: python a4_reproduce.py
"""
import sys
from pathlib import Path
import numpy as np

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY))
import v282cmp as V  # the study's own shared library, used here only to REPRODUCE its numbers

print(V._self_test())
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]

band, ev_rows = {}, []
for rk, meta in V.ROUTES.items():
    S = V.load(rk)
    g = meta["group"]
    band[(g, rk)] = [(np.nan_to_num(S["model"][a:b]), np.nan_to_num(S["la_pose"][a:b]))
                     for a, b in V.runs(V.usable(S, 15.0), S["t"], min_s=41.0)]
    for vmin in (5.0, 15.0):
        ev, _ = V.jerk_events(S, vmin=vmin)
        for e in ev:
            i0 = e["idx"] - int(1.5 * V.FS); i1 = e["idx"] + int(3.0 * V.FS)
            ma = V.event_metrics(S, i0, i1, ach_key="la_act")
            mp = V.event_metrics(S, i0, i1, ach_key="la_pose")
            ev_rows.append(dict(g=g, r=rk, vmin=vmin, v=e["v"], jerk=abs(e["jerk_peak"]),
                                la=e["la_peak"], g_act=ma["gain"], g_pose=mp["gain"],
                                lag_act=ma["lag"], lag_pose=mp["lag"]))
    del S

print("\n=== (a) band |H| with the study's own band_H, model -> la_pose, runs>=41 s, v>=15 ===")
print("   (nperseg is chosen INSIDE band_H from the shortest run in the list it is handed, so it is printed too)")
for f1, f2 in [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]:
    line = f"  {f1:.2f}-{f2:.2f}"
    for g in GROUPS:
        segs = [s for (gg, r), ss in band.items() if gg == g for s in ss]
        res = V.band_H(segs, f1, f2)
        if res:
            nps = int(2 ** np.floor(np.log2(min(len(x) for x, _ in segs))))
            line += f"  {g} {res['H']:.3f}(coh{res['coh']:.2f},nps{min(nps,8192)},nseg{res['n']})"
    print(line)

print("\n=== nperseg actually used per group (band_H's hidden, group-dependent choice) ===")
for g in GROUPS:
    segs = [s for (gg, r), ss in band.items() if gg == g for s in ss]
    segs = [s for s in segs if len(s[0]) >= 256]
    if not segs:
        continue
    L = [len(x) for x, _ in segs]
    nps = min(int(2 ** np.floor(np.log2(min(L)))), 8192)
    print(f"  {g:8s} nseg {len(L):3d}  shortest {min(L)/V.FS:6.1f} s  longest {max(L)/V.FS:7.1f} s  "
          f"=> nperseg {nps} ({nps/V.FS:.1f} s, df {V.FS/nps:.4f} Hz)")

print("\n=== equal-footing control: force every group through the SAME nperseg by truncating every run to the "
      "global shortest, then re-run band_H ===")
allsegs = [s for ss in band.values() for s in ss if len(s[0]) >= 256]
Lmin = min(len(x) for x, _ in allsegs)
nps_g = min(int(2 ** np.floor(np.log2(Lmin))), 8192)
for f1, f2 in [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]:
    line = f"  {f1:.2f}-{f2:.2f} (nps {nps_g})"
    for g in GROUPS:
        segs = [(x[:Lmin], y[:Lmin]) for (gg, r), ss in band.items() if gg == g for x, y in ss if len(x) >= Lmin]
        res = V.band_H(segs, f1, f2)
        if res:
            line += f"  {g} {res['H']:.3f}"
    print(line)

print("\n=== (b) high-jerk events with the study's own finder and metrics ===")
for vmin in (5.0, 15.0):
    print(f"  vmin {vmin}:")
    for g in GROUPS:
        rr = [e for e in ev_rows if e["g"] == g and e["vmin"] == vmin]
        if not rr:
            continue
        per_route = {}
        for e in rr:
            per_route.setdefault(e["r"], []).append(e)
        ga = [np.median([e["g_act"] for e in v]) for v in per_route.values()]
        gp = [np.median([e["g_pose"] for e in v]) for v in per_route.values()]
        la = [np.median([e["lag_act"] for e in v]) for v in per_route.values()]
        lpp = [np.median([e["lag_pose"] for e in v]) for v in per_route.values()]
        print(f"    {g:8s} nev {len(rr):4d} ({len(per_route)} routes)  gain_act {np.median(ga):.3f} "
              f"[{min(ga):.2f},{max(ga):.2f}]  gain_pose {np.median(gp):.3f} [{min(gp):.2f},{max(gp):.2f}]  "
              f"lag_act {np.median(la):.3f}  lag_pose {np.median(lpp):.3f}")
