"""Independent verification: (1) re-run the fixed_lag positive control myself (not trusting the shipped assert),
(2) recompute act.slag directly from V.load() for a sample of stored events and diff against the stored JSON field,
(3) recompute the matched-pair diff for hi>=15 T64 vs V282 with my OWN match+bootstrap implementation and compare
    to s2_results.json's act.slag figure.
"""
import sys, json, glob
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

FS = V.FS

def fixed_lag(x, y, i0, i1, lo=-50, hi=80):
    yy = y[i0:i1] - y[i0:i1].mean(); best = (-2, 0, 0)
    for L in range(lo, hi + 1):
        xx = x[i0 - L:i1 - L]; xx = xx - xx.mean()
        den = np.sqrt(np.dot(xx, xx) * np.dot(yy, yy))
        c = np.dot(xx, yy) / den if den > 0 else 0
        if c > best[0]:
            best = (c, L, np.dot(xx, yy) / max(np.dot(xx, xx), 1e-12))
    return best[1] / FS, float(best[2]), float(best[0])

# ---- (1) positive control, my own re-derivation ----
print("=== positive control ===")
t = np.arange(-3, 5.5, 0.01)
for d in (0.0, 0.1, 0.25, 0.4, -0.15):
    x = np.tanh(3 * t); y = 0.9 * np.tanh(3 * (t - d))
    L, g, c = fixed_lag(x, y, 200, 550)
    print(f"  true d={d:+.2f}  recovered L={L:+.3f}  gain={g:.3f}  corr={c:.4f}")

