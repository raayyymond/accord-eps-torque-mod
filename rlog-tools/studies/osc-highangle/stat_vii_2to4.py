# -*- coding: utf-8 -*-
"""Pre-registered statistic (vii): 2-4 Hz band EXCESS, MID stratum (8-18 m/s), engaged -- band_excess_2to4_speed_matched.py's
score() applied to the house caches r31 (V278r3), r2e (V276), r32/r33/r34 (V280 rev 2), plus the corpus p95 read the same way.
Run: python rlog-tools/studies/osc-highangle/stat_vii_2to4.py
"""
import glob, os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "rlog-tools", "studies", "osc-2to4"))
import band_excess_2to4_speed_matched as B  # noqa: E402
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WANT = ("r2e", "r31", "r32", "r33", "r34")
res = {}
corpus = []
for root in B.CACHE_ROOTS:
    for fp in sorted(glob.glob(os.path.join(ROOT, root, "*", "*.npz"))):
        tag = os.path.basename(os.path.dirname(fp))
        if os.path.basename(fp) != tag + ".npz":
            continue
        d = B.load(fp)
        if d is None:
            continue
        s = B.score(d)
        if tag in WANT:
            res[tag] = s
        corpus.append(s)
def cell(s, key, ch="rate_f"):
    c = s["cells"].get(key, {})
    return c.get("secs", 0), c.get(ch, {}), c
print("stat (vii): rate_f excess24 by stratum (engaged, ALL roads) -- prereg threshold < 1.39 (corpus p95)")
for tag in WANT:
    if tag not in res:
        print("  %s: no house cache" % tag); continue
    s = res[tag]
    for st in ("LOW", "MID", "HIGH"):
        secs, c, cc = cell(s, "%s.ENG.ALL" % st)
        ce = cell(s, "%s.ENG.ALL" % st, "e4tq")[1]
        print("  %s %-6s %-4s %6.1f s: rate excess24 %s  peak %s Hz x%s Q%s | cmd excess24 %s | coh24 %s gain24 %s ph24 %s" % (
            tag, s["build"], st, secs, "%.3f" % c["excess24"] if "excess24" in c else "--",
            "%.2f" % c["peak_f"] if c.get("peak_f") else "--", "%.2f" % c["peak_excess"] if c.get("peak_excess") else "--", "%.0f" % c["peak_Q"] if c.get("peak_Q") else "--",
            "%.3f" % ce["excess24"] if "excess24" in ce else "--",
            "%.3f" % cc["coh24"] if "coh24" in cc else "--", "%.3f" % cc["gain24"] if "gain24" in cc else "--", "%.0f" % cc["ph24"] if "ph24" in cc else "--"))
    for st in ("MID",):
        secs, c, cc = cell(s, "%s.ENG.STR" % st)
        print("  %s        %s-STR %6.1f s: rate excess24 %s" % (tag, st, secs, "%.3f" % c["excess24"] if "excess24" in c else "--"))
vals = [s["cells"]["%s.ENG.ALL" % nm]["rate_f"]["excess24"] for s in corpus for nm in ("MID", "HIGH")
        if s["cells"].get("%s.ENG.ALL" % nm, {}).get("secs", 0) >= 60 and "rate_f" in s["cells"]["%s.ENG.ALL" % nm] and "excess24" in s["cells"]["%s.ENG.ALL" % nm]["rate_f"]]
print("corpus MID+HIGH engaged cells >= 60 s: n=%d p50 %.2f p75 %.2f p95 %.2f max %.2f" % (len(vals), np.median(vals), np.percentile(vals, 75), np.percentile(vals, 95), max(vals)))
json.dump({k: v for k, v in res.items()}, open(os.path.join(HERE, "_scratch", "stat_vii_2to4.json"), "w"), indent=1, default=float)
