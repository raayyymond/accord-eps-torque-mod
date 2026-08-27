#!/usr/bin/env python3
"""Census for the Q/damping re-score: engaged runs, speed, gear, falling edges.

Routes 6f=V86, 6e=V85, 70=V86B.  Loads the SAME per-segment caches every prior score used.
"""
import sys, json
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parents[2]
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "analysis-2020accord"))
import _r31_common as C31   # noqa

ROUTES = {"V86/6f": ("_scratch/cache/r6f", "r6fs", range(4)),
          "V85/6e": ("_scratch/cache/r6e", "r6es", range(8)),
          "V86B/70": ("_scratch/cache/r70", "r70s", range(4))}
GEAR = ["unknown", "park", "drive", "neutral", "reverse", "sport", "low", "brake", "eco",
        "manumatic"]

out = {}
for tag, (cache, pfx, segs) in ROUTES.items():
    print("=" * 100); print(tag)
    tot_eng = tot = 0.0
    runs_all = []
    edges = []
    for s in segs:
        p = ROOT / cache / f"{pfx}{s}.npz"
        if not p.exists():
            continue
        d = C31.load(s, ROOT / cache, pfx)
        fs = C31.fs_of(d)
        t = np.asarray(d["t"], float)
        lat = np.asarray(d["cc_lat"], float) > 0.5
        v = np.asarray(d["cs_v"], float)
        g = np.asarray(d["cs_gear"], float)
        tot += len(t) / fs
        tot_eng += lat.sum() / fs
        # engaged runs >= 5 s
        for a, b in C31.runs_of(lat, t, int(5 * fs)):
            runs_all.append(dict(seg=int(s), T=(b - a) / fs, n=b - a,
                                 v_med=float(np.median(v[a:b])), v_min=float(np.min(v[a:b])),
                                 v_max=float(np.max(v[a:b])), t0=float(t[a]), t1=float(t[b - 1]),
                                 gear=int(np.median(g[a:b]))))
        # falling edges of latActive with >=3 s engaged before and >=3 s manual after
        fe = np.flatnonzero(lat[:-1] & ~lat[1:])
        for i in fe:
            pre = int(3 * fs)
            post = int(3 * fs)
            if i - pre < 0 or i + post >= len(t):
                continue
            if not lat[i - pre:i + 1].all():
                continue
            if lat[i + 1:i + 1 + post].any():
                continue
            edges.append(dict(seg=int(s), i=int(i), t=float(t[i]),
                              v=float(v[i]), gear=int(g[i]),
                              pre_eng_s=float(np.flatnonzero(~lat[:i + 1])[-1:] .size and
                                              (i - np.flatnonzero(~lat[:i + 1])[-1]) / fs
                                              if (~lat[:i + 1]).any() else (i + 1) / fs),
                              post_man_s=float((np.flatnonzero(lat[i + 1:])[0] / fs)
                                               if lat[i + 1:].any() else (len(t) - i - 1) / fs)))
        print(f"  seg {s}: fs={fs:.4f} n={len(t)} dur={len(t)/fs:6.1f}s  eng={lat.sum()/fs:6.1f}s "
              f"({100*lat.mean():5.1f}%)  gears={sorted(set(g.astype(int)))} "
              f"v[{v.min():.2f},{v.max():.2f}]")
    runs_all.sort(key=lambda r: -r["T"])
    print(f"  TOTAL {tot:.1f} s, engaged {tot_eng:.1f} s")
    print(f"  engaged runs >=5 s: n={len(runs_all)}  "
          f"lengths {[round(r['T'],1) for r in runs_all[:12]]}")
    print(f"  falling edges (>=3s eng before, >=3s man after): n={len(edges)}")
    for e in edges[:12]:
        print(f"      seg{e['seg']} t={e['t']:7.1f}  v={e['v']:.2f} m/s gear={GEAR[e['gear']]} "
              f"pre={e['pre_eng_s']:.1f}s post={e['post_man_s']:.1f}s")
    out[tag] = dict(total_s=tot, engaged_s=tot_eng, runs=runs_all, edges=edges)

(ROOT / "_scratch/cache/r6f").mkdir(exist_ok=True)
json.dump(out, open(ROOT / "_scratch/cache/r6f" / "qd_census.json", "w"), indent=1)
print("\nwrote _scratch/cache/r6f/qd_census.json")
