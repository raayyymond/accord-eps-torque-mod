# -*- coding: utf-8 -*-
r"""s5b_kf_sweep.py -- D5-architect.  (a)'s friction comp adds Kf to the small-signal P: find the largest Kf that keeps
the panel-2 R2-box GATE 2 at 0 fails (washout D included).  s5_gate2's pipeline (the common scorer, unchanged) on a
trimmed member x speed set first (the binding members), then the winner on the full box.  Wall printed (< 30 s)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
t0 = time.time()
import s5_gate2 as G  # noqa: E402

BIND = ("b_q*J1.0+h10", "b_lo*ms_free+h10", "b_q*ms_free+h10", "J_hi+h10", "b_lo*J_hi+h10", "nominal", "ms_free")
G.SPD = [3.1, 8.0, 11.9, 17.0, 20.0, 26.9]
res = {}
for kf in (0, 14, 28, 42, 56, 84, 112):
    sp = G.SF.Spec("a", "D5", G.GBP, 48, kp=112.0 + kf, ki=40.0, dkind="fresh")
    g = G.gate(sp, True, members=tuple(m for m in G.SF.MEMBERS if m in BIND))
    res[kf] = g
    print("Kf %3d: fails %3d worst PM-bar %+.1f (%s) GMmin %.1f dB T530 %+.1f dB" % (
        kf, g["fails"], g["worst_margin_over_bar"], g["worst"], g["gm_min"], g["t530_max"]))
ok = [k for k, g in res.items() if g["fails"] == 0]
best = max(ok) if ok else 0
G.SPD = [3.1, 5.0, 8.0, 9.0, 10.0, 11.0, 11.9, 13.0, 15.75, 17.0, 20.0, 26.9]
sp = G.SF.Spec("a", "D5", G.GBP, 48, kp=112.0 + best, ki=40.0, dkind="fresh")
g = G.gate(sp, True)
print("FULL R2 box at Kf %d: fails %d worst PM-bar %+.1f (%s) GMmin %.1f dB T530 %+.1f dB" % (
    best, g["fails"], g["worst_margin_over_bar"], g["worst"], g["gm_min"], g["t530_max"]))
print("wall %.1f s" % (time.time() - t0))
