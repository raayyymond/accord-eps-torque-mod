"""Adversarial verification of B6: torque-mode routes carry more 1.5-3.5 Hz content in the MODEL's desired
curvature (angle-rate) at low speed than V282, per b08_plan_source.py.

Confound checks requested by the lens:
 1. Un-pool T64 (6c,6d) from T64B (6e, ~4x demand) -- does rev64's gap over V282 survive on T64 alone?
 2. Drop the 62-segment V282 route (0000006c--2bc842dbac) -- does the gap survive on 64+65 alone?
 3. Demand-match: bin by mean |steering angle| in the window (absang, already in b04 rows) and compare
    model-angle-rate content within matched demand bins, not just matched speed bins.
 4. Cross-route consistency: does each torque-mode route individually (not just pooled) exceed each
    individual V282 route at matched speed AND matched demand decile?

All from the existing out/b04_rows_<route>.npz windows -- no rlog reload, no RAM pressure.
"""
import numpy as np
import sys
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/b_shake/'
OUT = BASE + 'out/'

TORQUE_ALL = {'0000006c--68c6e94b17': 'T64', '0000006d--05e83bb04f': 'T64', '0000006e--6ca3e014fd': 'T64B',
              '00000076--d0b7ea7e4d': 'T5', '00000075--6c8687d5bd': 'T4'}
V282_ALL = {'00000064--ce6b0b0ebb': 'V282', '00000065--b9f78988bd': 'V282', '0000006c--2bc842dbac': 'V282',
            '00000039--f56039af87': 'V282old', '0000003a--283a39a1d6': 'V282old', '0000003c--927965c2b4': 'V282old'}
BINS = [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8'), (8, 15, '8-15'), (0, 8, '<8')]

NORM = 2.0 / (np.sum(np.hanning(256) ** 2) * 100)
DF = 100 / 256


def load(rk):
    return np.load(OUT + f'b04_rows_{rk}.npz')


def r_of(P_sum, n):
    """Same formula as b08_plan_source.py: rms(deg/s) of band power summed across windows, divided by n."""
    return float(np.sqrt(np.sum(P_sum) * NORM * DF / max(n, 1)))


def group_stat(routes, lo, hi, amin=None, amax=None):
    """Pool windows across a list of route keys, restricted to speed [lo,hi) and optionally absang [amin,amax)."""
    Pmm = 0.0; Prr = 0.0; n = 0; absangs = []
    for rk in routes:
        X = load(rk)
        s = (X['v'] >= lo) & (X['v'] < hi)
        if amin is not None:
            s = s & (X['absang'] >= amin) & (X['absang'] < amax)
        Pmm = Pmm + X['Pmm'][s].sum(0)
        Prr = Prr + X['Prr'][s].sum(0)
        n += int(s.sum())
        absangs.append(X['absang'][s])
    absangs = np.concatenate(absangs) if absangs else np.zeros(0)
    return dict(n=n, model_rate=r_of(Pmm, n), wheel_rate=r_of(Prr, n),
                absang_mean=float(absangs.mean()) if len(absangs) else float('nan'))


def per_route_stat(rk, lo, hi, amin=None, amax=None):
    return group_stat([rk], lo, hi, amin, amax)


print("=" * 100)
print("CHECK 1: un-pool T64 (6c,6d) from T64B (6e) -- b08 pooled all three as 'rev64'")
print("=" * 100)
T64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f']
T64B = ['0000006e--6ca3e014fd']
V282 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
for lo, hi, lab in BINS:
    t64 = group_stat(T64, lo, hi)
    t64b = group_stat(T64B, lo, hi)
    v282 = group_stat(V282, lo, hi)
    ratio_pooled_vs_v282 = group_stat(T64 + T64B, lo, hi)['model_rate'] / max(v282['model_rate'], 1e-9)
    ratio_t64_only_vs_v282 = t64['model_rate'] / max(v282['model_rate'], 1e-9)
    print(f"{lab:5s} T64(6c,6d) n={t64['n']:4d} model_rate={t64['model_rate']:6.2f} absang={t64['absang_mean']:5.1f}  |  "
          f"T64B(6e) n={t64b['n']:4d} model_rate={t64b['model_rate']:6.2f} absang={t64b['absang_mean']:5.1f}  |  "
          f"V282 n={v282['n']:4d} model_rate={v282['model_rate']:6.2f} absang={v282['absang_mean']:5.1f}  |  "
          f"ratio(pooled rev64/V282)={ratio_pooled_vs_v282:5.2f}  ratio(T64-only/V282)={ratio_t64_only_vs_v282:5.2f}")

print()
print("=" * 100)
print("CHECK 2: drop the 62-segment V282 route 0000006c--2bc842dbac")
print("=" * 100)
V282_no62 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd']
V282_only62 = ['0000006c--2bc842dbac']
for lo, hi, lab in BINS:
    full = group_stat(V282, lo, hi)
    no62 = group_stat(V282_no62, lo, hi)
    only62 = group_stat(V282_only62, lo, hi)
    rev64 = group_stat(T64 + T64B, lo, hi)
    t64only = group_stat(T64, lo, hi)
    print(f"{lab:5s} V282-full n={full['n']:4d} model_rate={full['model_rate']:6.2f}  |  "
          f"V282-no62(64,65) n={no62['n']:4d} model_rate={no62['model_rate']:6.2f}  |  "
          f"V282-only62 n={only62['n']:4d} model_rate={only62['model_rate']:6.2f}  |  "
          f"ratio(rev64-pooled / V282-no62)={rev64['model_rate']/max(no62['model_rate'],1e-9):5.2f}  "
          f"ratio(T64-only / V282-no62)={t64only['model_rate']/max(no62['model_rate'],1e-9):5.2f}")

print()
print("=" * 100)
print("CHECK 3: demand-matched (bin by mean |steering angle| in-window, absang) at fixed speed bin 3-6 m/s")
print("=" * 100)
lo, hi = 3, 6
# collect absang range actually present in each group to choose sane matched bins
for rk_list, name in [(T64, 'T64(6c,6d)'), (T64B, 'T64B(6e)'), (V282_no62, 'V282(64,65)'), (V282, 'V282-full')]:
    Xs = [load(rk) for rk in rk_list]
    aa = np.concatenate([X['absang'][(X['v'] >= lo) & (X['v'] < hi)] for X in Xs])
    if len(aa):
        print(f"{name:14s} absang in [{lo},{hi}) m/s: n={len(aa)} mean={aa.mean():.1f} p10={np.percentile(aa,10):.1f} "
              f"p50={np.percentile(aa,50):.1f} p90={np.percentile(aa,90):.1f}")
    else:
        print(f"{name:14s} absang in [{lo},{hi}) m/s: NO WINDOWS")

print()
ABINS = [(0, 5, '0-5deg'), (5, 10, '5-10deg'), (10, 20, '10-20deg'), (20, 40, '20-40deg')]
for amin, amax, alab in ABINS:
    t64 = group_stat(T64, lo, hi, amin, amax)
    t64b = group_stat(T64B, lo, hi, amin, amax)
    v282full = group_stat(V282, lo, hi, amin, amax)
    v282no62 = group_stat(V282_no62, lo, hi, amin, amax)
    print(f"{alab:9s} T64 n={t64['n']:4d} model_rate={t64['model_rate']:6.2f}  |  "
          f"T64B n={t64b['n']:4d} model_rate={t64b['model_rate']:6.2f}  |  "
          f"V282full n={v282full['n']:4d} model_rate={v282full['model_rate']:6.2f}  |  "
          f"V282no62 n={v282no62['n']:4d} model_rate={v282no62['model_rate']:6.2f}")

print()
print("=" * 100)
print("CHECK 4: per-route, all bins (does EVERY torque route exceed EVERY V282 route, or is it pooling-driven?)")
print("=" * 100)
for lo, hi, lab in BINS:
    print(f"--- speed bin {lab} ---")
    for rk in list(TORQUE_ALL) + list(V282_ALL):
        s = per_route_stat(rk, lo, hi)
        grp = TORQUE_ALL.get(rk, V282_ALL.get(rk))
        print(f"  {grp:8s} {rk:24s} n={s['n']:4d} model_rate={s['model_rate']:6.2f} absang={s['absang_mean']:5.1f}")
