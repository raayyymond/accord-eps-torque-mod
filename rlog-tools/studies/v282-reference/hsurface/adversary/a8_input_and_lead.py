"""ADVERSARY A8 - two remaining ways the comparison could be wrong.

 1. THE INPUT CHANNEL IS NOT EXOGENOUS. The logged `desiredCurvature` is the planner's output AFTER lane
    centering has added a correction computed from the camera's view of where the car is, and after clip_curvature
    has rate-limited it. If the demand responds to the achieved motion, |H| is a closed-loop object and the sign of
    its bias depends on how much road disturbance each route had. Granger test: does the achieved motion's past
    predict the demand's future beyond the demand's own past? Reported for each group, plus the reverse direction
    as a scale, plus a synthetic feedforward-only control so the number has a zero.

 2. THE TWO BUILDS DID NOT FLY THE SAME LOOKAHEAD. A1: UseAutoSteerDelay = 0 on all three V282 routes (fixed
    SteerDelay 0.2 s) and 1 on all five torque routes (learned 0.28-0.30 s). The controller advances the reference
    by that lookahead, so the torque builds were aiming FURTHER AHEAD. Re-measure the phase with both groups
    normalised to a common lookahead by shifting the achieved channel, and report the equivalent delay in seconds.

usage: python a8_input_and_lead.py
"""
import sys
from pathlib import Path
import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from a2_hindep import load_route, my_runs, windows, band_stats, GROUP, FS

NPS = 4096
f = np.fft.rfftfreq(NPS, 1 / FS)
BANDS = [(0.08, 0.25), (0.15, 0.30), (0.30, 0.60)]
GROUPS = ["V282", "V282old", "T64", "T64B", "T5", "T4"]
DEC = 10          # decimate to 10 Hz for the Granger fit (everything of interest is below 1 Hz)
P = 20            # 2 s of past


def granger(x, y, p=P):
    """Incremental R^2 from adding y's past to an AR(p) model of x. Returns (R2_inc_y_to_x, R2_inc_x_to_y)."""
    def fit(tgt, cols):
        n = len(tgt) - p
        A = np.column_stack([np.ones(n)] + [c[p - k - 1:p - k - 1 + n] for c in cols for k in range(p)])
        b = tgt[p:]
        coef, *_ = np.linalg.lstsq(A, b, rcond=None)
        r = b - A @ coef
        return float(np.dot(r, r))
    sx = fit(x, [x]); sxy = fit(x, [x, y])
    sy = fit(y, [y]); syx = fit(y, [y, x])
    return 1 - sxy / max(sx, 1e-30), 1 - syx / max(sy, 1e-30)


print("=== 1) Granger: does the ACHIEVED motion predict the DEMAND's future? (10 Hz, 2 s of past) ===")
print("    control first: a purely feedforward synthetic chain must read ~0 in the y->x column")
rng = np.random.default_rng(3)
n = 30000
xs = signal.sosfiltfilt(signal.butter(2, 0.5, btype="low", fs=10.0, output="sos"), rng.standard_normal(n))
ys = np.concatenate([np.zeros(3), xs[:-3]]) * 0.9 + 0.05 * rng.standard_normal(n)
a, b = granger(xs, ys)
print(f"    synthetic feedforward:      y->x {a:+.4f}   x->y {b:+.4f}")
xs2 = xs + 0.3 * np.concatenate([np.zeros(2), ys[:-2]])      # now let x depend on y's past
a, b = granger(xs2, ys)
print(f"    synthetic WITH feedback 0.3: y->x {a:+.4f}   x->y {b:+.4f}\n")

res = {}
lead = {}
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    x_all, y_all = np.nan_to_num(S["x_model"]), np.nan_to_num(S["y_pose"])
    A, B, W = [], [], 0
    for i0, i1 in my_runs(m, S["t"], 41.0):
        x = signal.decimate(x_all[i0:i1], DEC, ftype="fir", zero_phase=True)
        y = signal.decimate(y_all[i0:i1], DEC, ftype="fir", zero_phase=True)
        if len(x) < 5 * P:
            continue
        aa, bb = granger(x, y)
        A.append(aa); B.append(bb); W += 1
    res.setdefault(g, []).append((np.median(A) if A else np.nan, np.median(B) if B else np.nan, W))
    lead.setdefault(g, []).append(float(np.nanmedian(S["ld"][m])))
    del S
for g in GROUPS:
    v = np.array([x[:2] for x in res[g]], dtype=float)
    print(f"  {g:8s} y->x {np.nanmedian(v[:,0]):+.4f}   x->y {np.nanmedian(v[:,1]):+.4f}   "
          f"(per-route y->x {[f'{z:+.3f}' for z in v[:,0]]})")

print("\n=== 2) equivalent delay from the measured band phase, and the same after normalising the lookahead ===")
print("    logged lookahead (liveDelay.lateralDelay, = the fixed SteerDelay when UseAutoSteerDelay is off):")
for g in GROUPS:
    print(f"      {g:8s} {[f'{z:.3f}' for z in lead[g]]} s")
LEAD_COMMON = 0.20

acc = {}
for r, g in GROUP.items():
    S = load_route(r)
    m = S["lat_active"] & ~S["pressed"] & (S["v"] >= 15.0)
    x_all, y_all = np.nan_to_num(S["x_model"]), np.nan_to_num(S["y_pose"])
    extra = float(np.nanmedian(S["ld"][m])) - LEAD_COMMON          # s of extra advance this route flew
    k = int(round(extra * FS))
    for i0, i1 in my_runs(m, S["t"], 41.0):
        x, y = x_all[i0:i1], y_all[i0:i1]
        yn = np.concatenate([np.full(k, y[0]), y[:-k]]) if k > 0 else y     # undo the extra advance
        for pxx, pyy, pxy, _ in windows(x, y, NPS, NPS // 2):
            acc.setdefault((g, "raw"), []).append(dict(pxx=pxx, pyy=pyy, pxy=pxy))
        for pxx, pyy, pxy, _ in windows(x, yn, NPS, NPS // 2):
            acc.setdefault((g, "lead-normalised"), []).append(dict(pxx=pxx, pyy=pyy, pxy=pxy))
    del S

print(f"\n{'band':>12s} {'group':8s} {'mode':16s} {'Hmag':>6s} {'phase':>7s} {'tau_eq_s':>8s} {'NRMSE':>6s} "
      f"{'egain':>6s} {'ephase':>7s}")
for f1, f2 in BANDS:
    for g in GROUPS:
        for mode in ("raw", "lead-normalised"):
            st = band_stats(acc.get((g, mode), []), f, f1, f2)
            if not st:
                continue
            tau = -st["phase_deg"] / 360.0 / max(st["fbar"], 1e-9)
            print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {mode:16s} {st['H_mag']:6.3f} {st['phase_deg']:7.1f} "
                  f"{tau:8.3f} {st['nrmse']:6.3f} {st['e_gain']:6.3f} {st['e_phase']:7.3f}")
    print()

print("=== 3) the scalar question: |H| ranks differently from a tracking error. Both, side by side. ===")
print(f"{'band':>12s} {'group':8s} {'|H|':>6s} {'|H|-1':>7s} {'NRMSE':>6s} {'rank by |H-1|':>14s} {'rank by NRMSE':>14s}")
for f1, f2 in BANDS:
    rows = []
    for g in GROUPS:
        st = band_stats(acc.get((g, "raw"), []), f, f1, f2)
        if st:
            rows.append((g, st["H_mag"], abs(st["H_mag"] - 1), st["nrmse"]))
    r1 = {g: i + 1 for i, (g, _, _, _) in enumerate(sorted(rows, key=lambda z: z[2]))}
    r2 = {g: i + 1 for i, (g, _, _, _) in enumerate(sorted(rows, key=lambda z: z[3]))}
    for g, H, dH, nr in rows:
        print(f"{f1:5.2f}-{f2:4.2f} {g:8s} {H:6.3f} {dH:7.3f} {nr:6.3f} {r1[g]:14d} {r2[g]:14d}")
    print()
