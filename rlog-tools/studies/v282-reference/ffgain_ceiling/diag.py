# -*- coding: utf-8 -*-
"""Adversarial checks on the sweep's headline: is the 2-8 m/s ceiling an artefact of a few frames?

1  per-route contribution to the 2-8 m/s maxima and rail seconds
2  the top |FF| frames themselves -- route, time, speed, angle, demand rate, hold, move
3  sensitivity: drop |angle| > 200 deg, drop v < 3 m/s, use p99.9 instead of max
ANALYSIS ONLY.  Run: python diag.py
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ffrecon as F                      # noqa: E402
import v282cmp as C                      # noqa: E402
from sweep import route_frames, FS       # noqa: E402

CACHE = C.CACHE
routes = [(rk, cfg) for rk, cfg in F.ROUTECFG.items()
          if cfg["ff_live"] and (CACHE / f"{rk}.npz").exists()]

print("=" * 118)
print("1  PER-ROUTE, 2-8 m/s, engaged hands-off")
print("=" * 118)
print(f"{'route':6s} {'rev':22s} {'sec':>7s} | " +
      " ".join(f"{'g=' + format(g, '.2f') + ': maxFF maxTOT sRail':>30s}" for g in (0.5, 1.0, 2.0)))
top = []
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    bm = D["mask"] & (D["v"] >= 2.0) & (D["v"] < 8.0)
    if bm.sum() < 200:
        print(f"{cfg['tag']:6s} {cfg['rev']:22s} {bm.sum()/FS:7.1f}   (too little)")
        del D
        continue
    cells = []
    for g in (0.5, 1.0, 2.0):
        mv = np.clip(g * D["r"], -D["lim"], D["lim"])
        ffa = np.abs(D["hold"] + mv)
        ua = np.abs(D["u0"] - (mv - D["mv0"]))
        cells.append(f"{ffa[bm].max():9.3f} {ua[bm].max():7.3f} {(bm & (ua >= 1.0)).sum()/FS:6.2f}")
    print(f"{cfg['tag']:6s} {cfg['rev']:22s} {bm.sum()/FS:7.1f} | " + " ".join(f"{c:>30s}" for c in cells))
    # collect the top frames by |FF| at gain 0.5 for inspection
    mv = np.clip(0.5 * D["r"], -D["lim"], D["lim"])
    ffa = np.abs(D["hold"] + mv)
    idx = np.where(bm)[0]
    order = idx[np.argsort(-ffa[idx])][:12]
    for j in order:
        top.append((float(ffa[j]), cfg["tag"], float(D["t"][j] - D["t"][0]), float(D["v"][j]),
                    float(D["sa"][j]), float(D["ad"][j]), float(D["adr"][j]), float(D["hold"][j]),
                    float(mv[j]), float(D["u0"][j])))
    del D

print()
print("=" * 118)
print("2  THE 20 LARGEST |hold+move| FRAMES at the flown gain 0.5, 2-8 m/s")
print("=" * 118)
print(f"{'|FF|':>6s} {'route':6s} {'t rel s':>9s} {'v':>6s} {'angle':>8s} {'ang_des':>9s} "
      f"{'des rate':>9s} {'hold':>7s} {'move':>7s} {'|TOT| log':>10s}")
for r in sorted(top, reverse=True)[:20]:
    print(f"{r[0]:6.3f} {r[1]:6s} {r[2]:9.1f} {r[3]:6.2f} {r[4]:8.1f} {r[5]:9.1f} {r[6]:9.1f} "
          f"{r[7]:7.3f} {r[8]:7.3f} {abs(r[9]):10.3f}")

print()
print("=" * 118)
print("3  SENSITIVITY of the 2-8 m/s ceiling (criterion A: max |hold+move| <= 1.00)")
print("=" * 118)
SUBS = [("all 2-8", lambda D: (D["v"] >= 2.0) & (D["v"] < 8.0)),
        ("2-8, |angle|<=200", lambda D: (D["v"] >= 2.0) & (D["v"] < 8.0) & (np.abs(D["sa"]) <= 200.0)),
        ("2-8, |angle|<=90", lambda D: (D["v"] >= 2.0) & (D["v"] < 8.0) & (np.abs(D["sa"]) <= 90.0)),
        ("3-8", lambda D: (D["v"] >= 3.0) & (D["v"] < 8.0)),
        ("5-8", lambda D: (D["v"] >= 5.0) & (D["v"] < 8.0))]
FINE = [round(x, 3) for x in np.arange(0.5, 4.001, 0.05)]
EDG = np.arange(0.0, 6.0005, 0.005)
acc = {}
for rk, cfg in routes:
    D = route_frames(rk, cfg)
    for sn, fn in SUBS:
        bm = D["mask"] & fn(D)
        if bm.sum() < 200:
            continue
        for g in FINE:
            mv = np.clip(g * D["r"], -D["lim"], D["lim"])
            ffa = np.abs(D["hold"] + mv)
            ua = np.abs(D["u0"] - (mv - D["mv0"]))
            a = acc.setdefault((sn, g), dict(maxff=0.0, h=np.zeros(len(EDG) - 1), n=0, secu=0.0,
                                            per_route={}))
            a["maxff"] = max(a["maxff"], float(ffa[bm].max()))
            a["h"] += np.histogram(np.minimum(ffa[bm], 5.99), bins=EDG)[0]
            a["n"] += int(bm.sum())
            a["secu"] += float((bm & (ua >= 1.0)).sum() / FS)
            a["per_route"][cfg["tag"]] = float(ffa[bm].max())
    del D


def pct(h, q):
    n = h.sum()
    if n == 0:
        return float("nan")
    k = min(int(np.searchsorted(np.cumsum(h) / n, q)) + 1, len(EDG) - 1)
    return float(EDG[k])


print(f"{'subset':20s} {'sec':>8s} {'g: pooled max<=1':>17s} {'g: median route':>16s} "
      f"{'g: p99.9<=1':>12s} | {'max|FF| @0.5':>13s} {'@1.0':>8s} {'@2.0':>8s} "
      f"{'p99.9 @0.5':>11s} {'@2.0':>8s}")
for sn, _ in SUBS:
    if (sn, 0.5) not in acc:
        continue
    gA = max([g for g in FINE if acc[(sn, g)]["maxff"] <= 1.0], default=None)
    gM = max([g for g in FINE
              if float(np.median(list(acc[(sn, g)]["per_route"].values()))) <= 1.0], default=None)
    gP = max([g for g in FINE if pct(acc[(sn, g)]["h"], 0.999) <= 1.0], default=None)
    print(f"{sn:20s} {acc[(sn,0.5)]['n']/FS:8.1f} {str(gA):>17s} {str(gM):>16s} {str(gP):>12s} | "
          f"{acc[(sn,0.5)]['maxff']:13.3f} {acc[(sn,1.0)]['maxff']:8.3f} {acc[(sn,2.0)]['maxff']:8.3f} "
          f"{pct(acc[(sn,0.5)]['h'],0.999):11.3f} {pct(acc[(sn,2.0)]['h'],0.999):8.3f}")
print()
print("per-route max |hold+move| in the 2-8 band, by gain (the pooled max is the WORST route):")
for sn in ("all 2-8", "2-8, |angle|<=90"):
    if (sn, 0.5) not in acc:
        continue
    tags = sorted(acc[(sn, 0.5)]["per_route"])
    print(f"  {sn}")
    print(f"     {'gain':>5s} " + " ".join(f"{t:>7s}" for t in tags))
    for g in (0.5, 0.75, 1.0, 1.5, 2.0):
        print(f"     {g:5.2f} " + " ".join(f"{acc[(sn,g)]['per_route'].get(t,float('nan')):7.3f}"
                                          for t in tags))
