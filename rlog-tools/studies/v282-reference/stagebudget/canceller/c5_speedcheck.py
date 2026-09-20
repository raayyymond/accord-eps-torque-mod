# -*- coding: utf-8 -*-
"""c5: is the stage's realised transfer speed-independent?  It must be (it is pure software on curvature,
and v^2 cancels in a lat-accel ratio at constant v), but Regime B is quoted at 8-15 m/s, so check it there
rather than assume.  Also the group means used in the write-up.

usage: python c5_speedcheck.py"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402
from c2_stage import CFG, reconstruct, segs_for, band_stats  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANDS = [(0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
SPD = [(8, 15), (15, 22), (22, 99)]
SEL = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac",
       "0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
       "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]

print("=" * 122)
print("STAGE u->setpoint(logged), split by speed bin.  If the stage is speed-independent these rows match")
print("the pooled numbers in C2-OUT.txt.  Windows must spend the run inside the bin, so low bins thin out.")
print("=" * 122)
acc = {}
for r in SEL:
    S = V.load(r)
    R = reconstruct(S, CFG[r])
    print("-- %-22s %-7s" % (r, CFG[r]["g"]))
    for (v1, v2) in SPD:
        row = "     %2d-%2d m/s " % (v1, v2)
        for (f1, f2) in BANDS:
            nps = 4096 if f2 <= 0.30 else (2048 if f2 <= 0.60 else 1024)
            sg = segs_for(S, R, "u", "sp_log", vmin=v1, vmax=v2, min_s=40.0)
            bs = band_stats(sg, f1, f2, nps)
            if bs is None:
                row += "    --            "
                continue
            row += "  |H| %5.3f lag %5.1f" % (bs["H"], bs["lag_ms"])
            acc.setdefault((CFG[r]["g"], v1, f1), []).append((bs["H"], bs["lag_ms"]))
        print(row)
    del S, R
print()
print("GROUP MEANS (stage only):")
for g in ("V282", "T64", "T64B", "T5", "T4"):
    for (v1, v2) in SPD:
        row = "   %-6s %2d-%2d m/s " % (g, v1, v2)
        any_ = False
        for (f1, f2) in BANDS:
            k = (g, v1, f1)
            if k in acc:
                a = np.array(acc[k])
                row += "  %.2f-%.2f: |H| %5.3f lag %5.1f (n%d)" % (f1, f2, a[:, 0].mean(), a[:, 1].mean(), len(a))
                any_ = True
        if any_:
            print(row)
