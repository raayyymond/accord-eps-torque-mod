# -*- coding: utf-8 -*-
"""f7b: per-band detail for named candidates from a sweep JSON (every metric, both disturbance models, every member),
as V295+r1 absolute and candidate - r1 (or x r1 for rate / J metrics).
Usage: python f7b_detail.py <stage> name1 [name2 ...]"""
import sys, json
import numpy as np

stage = sys.argv[1]
names = sys.argv[2:]
J = json.load(open("out/f4_%s.json" % stage))
res = {tuple(k.split("|")): v for k, v in J["res"].items()}
dists = sorted({k[0] for k in res})
members = sorted({k[2] for k in res}, key=lambda m: (m != "nominal", m))
B = ("0-5", "5-10", "10-15", "15-22", "22+", "8-22")
for n in names:
    print("\n" + "=" * 150 + "\n%s  %s" % (n, J["meta"].get(n)))
    for d in dists:
        for m in members:
            r, b = res[(d, n, m)], res[(d, "r1", m)]
            print("  %-4s %-8s lc %.2f Hz %+.1f dB (r1 %+.1f)" % (d, m, r["limit_cycle"]["f"], r["limit_cycle"]["dB"], b["limit_cycle"]["dB"]))
            for band in B:
                if band not in r or band not in b:
                    continue
                x, y = r[band], b[band]
                rat = lambda k: (x[k] / y[k]) if (y[k] and np.isfinite(y[k])) else float("nan")  # noqa: E731
                print("      %-6s trk %.3f (%+.3f)  hold %.3f (%+.3f)  straight %.3f (%+.3f)  ish %.2f (%+.2f)  J %.3f x%.2f  "
                      "hard16 %.2f x%.2f  s13 %.3f x%.2f  s03 %.3f x%.2f  s15 x%.2f  cmd x%.2f  sat %.4f" % (
                          band, x["track_gain"], x["track_gain"] - y["track_gain"], x["turn_hold"], x["turn_hold"] - y["turn_hold"],
                          x["straight_delivery"], x["straight_delivery"] - y["straight_delivery"], x["i_share"],
                          x["i_share"] - y["i_share"], x["J_err"], rat("J_err"), x["hard16"], rat("hard16"), x["s13"], rat("s13"),
                          x["s03"], rat("s03"), rat("s15"), rat("cmd_rms"), x["sat4096"]))
