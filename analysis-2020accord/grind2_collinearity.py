#!/usr/bin/env python3
"""IS "FIXED GRIND #1" COLLINEAR WITH "BROUGHT GRIND #2"? -- the operator's hypothesis, tested.

The operator's claim: *every time the rate-lane grind-#1 fix has been introduced, grind #2 came with
it.* If in this corpus every build that measurably moved grind #1 is ALSO a build with grind-#2
events (or with no usable grind-#2 exposure), then the two are confounded and no build has ever
demonstrated the combination the record claims for V67/V68.

GRIND #1 = 18-22 Hz envelope, p90 over ENGAGED CREEP windows, same `_windows` instrument.
🛑 The split-half null comes FIRST. A build-to-build ratio smaller than a build's own split-half
spread is not a finding (`feedback-episodes-not-windows`).

Usage:  python grind2_collinearity.py
"""
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import r47_orchestrator_checks as R47  # noqa: E402
import _grind2_delivered_lib as D  # noqa: E402

CREEP = (0.3, 4.0)
G1, G2 = "18-22", "40-49"
BURST, WIN_S = 500.0, 2.56
ROUTES = [("V61", ["_cache_r31"]), ("V58", ["_cache_r2b"]), ("V59", ["_cache_r2c"]),
          ("V64", ["_cache_r35"]), ("V62", ["_cache_r37"]), ("V65", ["_cache_r3a", "_cache_r3b"]),
          ("V67", ["_cache_r47"]), ("V68", ["_cache_v68"]), ("V69", ["_cache_r4f"]),
          ("V70", ["_cache_r50"]), ("V71B", ["_cache_r54"]), ("V71C", ["_cache_r58"]),
          ("V72", ["_cache_r59"]), ("V73", ["_cache_r5a"]), ("V74", ["_cache_r5d"])]
GATED = {"V67", "V68", "V71C"}

print("harvesting ...", flush=True)
ROWS = {}
for n, cs in ROUTES:
    r = []
    for c in cs:
        r += R47._windows(c, n, lambda v: CREEP[0] <= v < CREEP[1])
    ROWS[n] = [x for x in r if x["lat"] > 0.5]     # ENGAGED creep only
    print(f"   {n:5s} {len(ROWS[n]):4d} engaged-creep windows", flush=True)

B = D.load_all()
st = B["stock"]

# --------------------------------------------------------------- split-half null -----------------
STOCKPOOL = ["V58", "V59", "V61", "V64", "V69", "V70"]
v = np.array([r[G1] for n in STOCKPOOL for r in ROWS[n]])
ep = np.array([hash((n, r["ep"])) for n in STOCKPOOL for r in ROWS[n]])
null = R47._split_half_null(v, ep, q=90)
print(f"\n🛑 SPLIT-HALF NULL, computed INSIDE the stock-lane pool with the identical estimator "
      f"(p90 of 18-22 Hz,\n   episodes resampled): a build-vs-stock ratio must fall OUTSIDE "
      f"[{null[0]:.3f}, {null[1]:.3f}] to mean anything.")

base = np.percentile([r[G1] for n in STOCKPOOL for r in ROWS[n]], 90)
print(f"   stock-lane pool p90(18-22 Hz) at engaged creep = {base:.1f} counts, "
      f"{sum(len(ROWS[n]) for n in STOCKPOOL)} windows")

print(f"\n{'build':6s} {'delivered eng r24/r26':>22s} | {'g1 p90':>8s} {'ratio':>7s} "
      f"{'[95% CI, episodes]':>22s} {'moved?':>8s} | {'g2 events':>10s} {'g2 corner secs':>15s} "
      f"{'g2 max':>8s}")
rows_out = []
for n, _ in ROUTES:
    d = D.delivered(B[n], st, 0, 3000, engaged=True)
    a = np.array([r[G1] for r in ROWS[n]])
    aep = np.array([hash((n, r["ep"])) for r in ROWS[n]])
    if len(a) < 5:
        continue
    ci = R47._boot_ratio(a, aep, v, ep, q=90)
    g1 = np.percentile(a, 90)
    moved = "YES" if (ci[2] < null[0] or ci[0] > null[1]) else "no"
    bw = [r for r in ROWS[n] if r[G2] > BURST]
    corner = [r for r in ROWS[n] if r["ang"] >= 100]
    rows_out.append((n, d, g1, ci, moved, len(bw), len(corner) * WIN_S / 2))
    print(f"{n:6s} {d[0]:10.3f}/{d[1]:10.3f} | {g1:8.1f} {ci[1]:7.3f} "
          f"[{ci[0]:8.3f},{ci[2]:8.3f}] {moved:>8s} | {len(bw):10d} {len(corner) * WIN_S / 2:15.1f} "
          f"{max((r[G2] for r in ROWS[n]), default=float('nan')):8.1f}")

print("\n" + "=" * 118)
print("THE 2x2 THE OPERATOR IS POINTING AT -- 'moved grind #1' x 'has grind-#2 evidence'")
print("=" * 118)
moved_y = [r for r in rows_out if r[4] == "YES"]
moved_n = [r for r in rows_out if r[4] == "no"]
print(f"   MOVED grind #1 : {[r[0] for r in moved_y]}")
print(f"   did NOT move   : {[r[0] for r in moved_n]}")
print(f"\n   {'build':6s} {'moved g1':>9s} {'g2 events':>10s} {'engaged-creep CORNER secs':>26s}  "
      f"verdict")
for n, d, g1, ci, moved, nb, cs in rows_out:
    if nb > 0:
        vd = "grind #2 PRESENT"
    elif cs >= 60:
        vd = "grind #2 absent AND powered"
    else:
        vd = f"grind #2 not observed -- but only {cs:.1f} s in the burst regime ⇒ UNINFORMATIVE"
    print(f"   {n:6s} {moved:>9s} {nb:10d} {cs:26.1f}  {vd}")
