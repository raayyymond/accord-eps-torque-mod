# -*- coding: utf-8 -*-
"""d9_traces -- read the saved d5 traces: (1) S5 lane change -- is the post-manoeuvre lateral accel a LAG tail (same sign
as the last lobe) or an OVERSHOOT (opposite sign)?  (2) S3 light resistance -- the post-release swing.  (3) S2 curve exit."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import d5_synth as S

rows = S.build_rows()
T = {c: np.load(os.path.join(HERE, "out", "d5_traces_%s_p22_s3.npz" % c.replace("+", "_"))) for c in ("V294+r1", "V295+r1", "V295+r2alt")}
L = []
P = lambda s: (print(s), L.append(s))  # noqa: E731
for kind, mem, v in (("S5", "nominal", 22.0), ("S5", "nominal", 26.9), ("S5", "b_lo", 26.9), ("S5", "light_b", 26.9)):
    j = [i for i, r in enumerate(rows) if r["kind"] == kind and r["member"] == mem and r["v"] == v][0]
    P("%s %s v%.1f (demand: +1.5 sin over 10-14 s; last lobe NEGATIVE)" % (kind, mem, v))
    for c in T:
        la, ld = T[c]["la_act"][j], T[c]["la_des"][j]
        post = la[1400:2400]
        P("   %-11s la_act at 14.0/14.5/15/16/18/20 s: %s | min/max post %.3f/%.3f | t of |la|<0.05 after 14 s: %.2f s" % (
            c, " ".join("%+.3f" % la[int(t * 100)] for t in (14.0, 14.5, 15.0, 16.0, 18.0, 20.0)), post.min(), post.max(),
            (np.flatnonzero(np.abs(post) > 0.05)[-1] + 1) / 100.0 if np.any(np.abs(post) > 0.05) else 0.0))
for kind, mem, v in (("S3", "nominal", 26.9), ("S3", "nominal", 22.0), ("S3", "light_b", 22.0)):
    j = [i for i, r in enumerate(rows) if r["kind"] == kind and r["member"] == mem and r["v"] == v][0]
    P("%s %s v%.1f (150 T push 10-14 s, not flagged pressed)" % (kind, mem, v))
    for c in T:
        la, ii, ang = T[c]["la_act"][j], T[c]["i"][j], T[c]["ang"][j]
        P("   %-11s la at 9.9/11/13.9/14.5/15/16/18/22 s: %s | i at 9.9/13.9/16/22: %s | wheel deg at 13.9/15/16: %s" % (
            c, " ".join("%+.3f" % la[int(t * 100)] for t in (9.9, 11.0, 13.9, 14.5, 15.0, 16.0, 18.0, 22.0)),
            " ".join("%+.3f" % ii[int(t * 100)] for t in (9.9, 13.9, 16.0, 22.0)),
            " ".join("%+.2f" % ang[int(t * 100)] for t in (13.9, 15.0, 16.0))))
open(os.path.join(HERE, "out", "d9_traces_out.txt"), "w").write("\n".join(L) + "\n")
