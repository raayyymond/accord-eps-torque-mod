# -*- coding: utf-8 -*-
"""The design stream's own metric: is the MOVE TERM'S internal limit binding?

The stream defended gain 2.0 with "the move term's limit (1.0 below 8 m/s) is nowhere near binding".
This prints exactly that quantity -- max and percentiles of the UNCLIPPED move term, and the share of
frames the limit bites -- next to the quantity that actually bounds the lever, the total command.
ANALYSIS ONLY.  Run: python movelimit.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ffrecon as F                      # noqa: E402
import v282cmp as C                      # noqa: E402
from sweep import route_frames, FS, BANDS, GAINS, DWELL_HI, TRANS_LO   # noqa: E402

routes = [(rk, cfg) for rk, cfg in F.ROUTECFG.items()
          if cfg["ff_live"] and (C.CACHE / f"{rk}.npz").exists()]
EDG = np.arange(0.0, 10.0005, 0.005)
acc = {}
adrstat = {}
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    aadr = np.abs(D["adr"])
    for lo, hi, bn in BANDS:
        bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
        if bm.sum() < 200:
            continue
        s = adrstat.setdefault(bn, dict(h=np.zeros(4000), n=0, mx=0.0))
        s["h"] += np.histogram(np.minimum(aadr[bm], 1999.0), bins=np.arange(0, 2000.5, 0.5))[0]
        s["n"] += int(bm.sum())
        s["mx"] = max(s["mx"], float(aadr[bm].max()))
        for rn, rm in (("all", bm), ("dwell", bm & (aadr < DWELL_HI)),
                       ("trans", bm & (aadr >= TRANS_LO))):
            if rm.sum() == 0:
                continue
            for g in GAINS:
                raw = np.abs(g * D["r"])
                a = acc.setdefault((g, bn, rn), dict(h=np.zeros(len(EDG) - 1), n=0, mx=0.0,
                                                     nclip=0, secclip=0.0, per_route={}))
                a["h"] += np.histogram(np.minimum(raw[rm], 9.99), bins=EDG)[0]
                a["n"] += int(rm.sum())
                a["mx"] = max(a["mx"], float(raw[rm].max()))
                a["nclip"] += int((rm & (raw > D["lim"])).sum())
                a["secclip"] += float((rm & (raw > D["lim"])).sum() / FS)
                a["per_route"][cfg["tag"]] = float(raw[rm].max())
    del D


def pct(h, edg, q):
    n = h.sum()
    if n == 0:
        return float("nan")
    return float(edg[min(int(np.searchsorted(np.cumsum(h) / n, q)) + 1, len(edg) - 1)])


print("=" * 112)
print("DESIRED-ANGLE RATE the move term is fed (|angle_des_rate|, deg/s), engaged hands-off")
print("=" * 112)
print(f"{'band':>6s} {'sec':>8s} {'p50':>8s} {'p90':>8s} {'p99':>8s} {'p99.9':>8s} {'max':>9s}")
eb = np.arange(0, 2000.5, 0.5)
for bn in ("2-8", "8-15", ">15"):
    if bn not in adrstat:
        continue
    s = adrstat[bn]
    print(f"{bn:>6s} {s['n']/FS:8.0f} " + " ".join(f"{pct(s['h'], eb, q):8.1f}"
                                                   for q in (0.5, 0.9, 0.99, 0.999))
          + f" {s['mx']:9.1f}")
print()
print("=" * 112)
print("THE MOVE TERM BEFORE ITS OWN CLIP  (|gain * angle_des_rate / G(v)|, torque)")
print("  the limit is 1.00 below 8 m/s, 1.40 from 10 m/s up")
print("=" * 112)
for bn in ("2-8", "8-15", ">15"):
    if (0.5, bn, "all") not in acc:
        continue
    print(f"--- {bn} m/s")
    print(f"{'gain':>5s} {'regime':>7s} {'max raw':>8s} {'p99':>7s} {'p99.9':>7s} "
          f"{'% clipped':>10s} {'s clipped':>10s}  per-route max raw")
    for g in GAINS:
        for rn in ("all", "trans"):
            a = acc.get((g, bn, rn))
            if not a or a["n"] == 0:
                continue
            pr_ = " ".join(f"{t}:{v:.2f}" for t, v in sorted(a["per_route"].items()))
            print(f"{g:5.2f} {rn:>7s} {a['mx']:8.3f} {pct(a['h'], EDG, 0.99):7.3f} "
                  f"{pct(a['h'], EDG, 0.999):7.3f} {100.0*a['nclip']/a['n']:10.4f} "
                  f"{a['secclip']:10.2f}  {pr_ if rn == 'all' else ''}")
    print()
