"""ADV-bytes step 3 (lineage cross-check): the V294 REDO audit's own outer-loop model (rp5_outer_loop, studies/v294/
redo_2026-09-23/physics) found that moving the fb pole to 0.94 Hz with K/J HELD costs light-world PM at 26 m/s
(+34 -> +18 deg).  A1017 moves the pole to 1.09 Hz with b HELD (K_alpha x 13/7 = 1.857).  Evaluate A1017 in THAT model
(an independent plant world from the V295 harness) -- does the design's "outer loop improves at 26.9 m/s" survive?"""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "v294", "redo_2026-09-23", "physics"))
import rp5_outer_loop as O  # noqa: E402

print("redo model: outer-loop PM at the FIRST gain crossover and min |1+L| (Ms), tau 25 ms, fric on")
for a, tg, lab in ((1011, 1.0, "V294 (shipped)"), (1017, (1024 - 1011) / (1024 - 1017), "A1017 b held (K x1.857)"),
                   (1017, 1.0, "a 1017, K held (redo class)"), (1018, 1.0, "a 1018, K held (redo rp8c row)")):
    O.WP = -math.log(a / 1024) / 1e-3
    for world in ("light", "ident"):
        row = []
        for v in (3, 5, 8, 12.5, 19, 26):
            k = float(np.interp(v, O.HOLD_V_BP, O.HOLD_K_V))
            b = 6e-4 if world == "light" else 1 / float(np.interp(v, O.G_BP, O.G_V))
            p4, c4, f, Lf = O.margins(v, True, b, k, trim_gain=tg)
            Ms = float(np.max(1 / np.abs(1 + Lf)))
            gm = min([1 / g for fc, g in c4 if fc > 0.05] or [float("inf")])
            row.append(f"{v}:PM{p4[0][1]:+.0f}/Ms{Ms:.2f}/GM{gm:.2f}" if p4 else f"{v}:--")
        print(f"  {lab:32s} {world:5s}: " + "  ".join(row))
