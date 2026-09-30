# -*- coding: utf-8 -*-
"""s1b_detail.py -- which member / speed sets the inner worst case in s1_plane.json (Ms at delay x1.5, GM, the least-damped
closed-loop wheel mode), for a few rows.  Reads s1_plane.json only."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "s1_plane.json")))
want = sys.argv[1:] or ["V294", "a1011_G1.50", "a1011_G2.00", "a1011_G2.50", "a1011_G3.00", "a1014_G2.00", "a1017_G2.00",
                        "a1005_G2.00", "a1008_G2.00"]
for r in R:
    if r["name"] not in want:
        continue
    inn = r["inner"]
    ms = sorted(inn.items(), key=lambda kv: -kv[1]["Ms15"])[:3]
    gm = sorted(inn.items(), key=lambda kv: kv[1]["GM"])[:3]
    zm = sorted(inn.items(), key=lambda kv: kv[1]["zmin"])[:4]
    print("%s  (b %d sh %d Kp %d C %d)" % (r["name"], r["b"], r["shift"], r["kp"], r["C"]))
    print("   Ms15 worst: %s" % ["%s %.3f" % (k, v["Ms15"]) for k, v in ms])
    print("   GM   worst: %s" % ["%s %.1f" % (k, v["GM"]) for k, v in gm])
    print("   zeta worst: %s" % ["%s %.3f %s" % (k, v["zmin"], v["modes"]) for k, v in zm])
    L = {k: round(v["L13"], 2) for k, v in inn.items() if k.startswith(("nominal", "light_b"))}
    print("   |L| 1-3 Hz: %s" % L)
    o = r["outer"]
    print("   outer GM  light_b: %s" % {k: round(v["GM"], 2) for k, v in o.items() if k.startswith("light_b")})
    print("   outer GM  nominal: %s" % {k: round(v["GM"], 2) for k, v in o.items() if k.startswith("nominal")})
    print("   outer Ms  nominal/b_lo/J_hi: %s" % {k: round(v["Ms"], 2) for k, v in o.items() if not k.startswith("light_b")})
    print("   outer Ms  light_b: %s" % {k: round(v["Ms"], 2) for k, v in o.items() if k.startswith("light_b")})
