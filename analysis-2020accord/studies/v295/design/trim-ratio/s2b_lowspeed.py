# -*- coding: utf-8 -*-
"""s2b_lowspeed.py -- from s2_sweep.json: the LOW-FREQUENCY (0.3-1 Hz) wheel rate, straight delivery and the J-style
lat-accel error per band, candidate / V294 (same batch).  The trim's inertia below its pole lowers and de-damps the
low-speed wheel mode (redo audit 2026-09-23); this is the table that shows whether a candidate pays for it."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "s2_sweep.json")))
bands = ("0-5", "5-10", "10-15", "15-22", "22+")
names = sorted({k.split("|")[1] for k in S} - {"V294"})
for dist in ("full", "lp"):
    for p in ("nominal", "light_b", "b_lo", "J_hi"):
        b0 = S["%s|V294|%s" % (dist, p)]
        print("=== %s %s  V294 r_lo %s  straight %s  J_err %s" % (
            dist, p, [round(b0[b]["r_lo"], 2) for b in bands], [round(b0[b]["straight_delivery"], 3) for b in bands],
            [round(b0[b]["J_err"], 4) for b in bands]))
        for nm in names:
            r = S["%s|%s|%s" % (dist, nm, p)]
            print("   %-12s r_lo x %s | straight d %s | J_err x %s" % (
                nm, " ".join("%.2f" % (r[b]["r_lo"] / b0[b]["r_lo"]) for b in bands),
                " ".join("%+.3f" % (r[b]["straight_delivery"] - b0[b]["straight_delivery"]) for b in bands),
                " ".join("%.3f" % (r[b]["J_err"] / b0[b]["J_err"]) for b in bands)))
