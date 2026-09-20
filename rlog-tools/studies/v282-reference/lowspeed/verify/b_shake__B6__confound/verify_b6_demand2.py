"""Extend CHECK 3 to the <3 bin (the finding's largest claimed ratio, 65.9 vs 7.4 = x8.9) and add the
setpoint-angle-rate (Paa) column alongside model-angle-rate (Pmm), demand-matched by absang."""
import numpy as np
BASE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/b_shake/'
OUT = BASE + 'out/'
NORM = 2.0 / (np.sum(np.hanning(256) ** 2) * 100)
DF = 100 / 256


def load(rk):
    return np.load(OUT + f'b04_rows_{rk}.npz')


def r_of(P_sum, n):
    return float(np.sqrt(np.sum(P_sum) * NORM * DF / max(n, 1)))


def group_stat(routes, lo, hi, amin=None, amax=None):
    Pmm = 0.0; Paa = 0.0; n = 0
    for rk in routes:
        X = load(rk)
        s = (X['v'] >= lo) & (X['v'] < hi)
        if amin is not None:
            s = s & (X['absang'] >= amin) & (X['absang'] < amax)
        Pmm = Pmm + X['Pmm'][s].sum(0)
        Paa = Paa + X['Paa'][s].sum(0)
        n += int(s.sum())
    return dict(n=n, model_rate=r_of(Pmm, n), setpoint_rate=r_of(Paa, n))


T64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f']
T64B = ['0000006e--6ca3e014fd']
V282 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']

for lo, hi, blab in [(0, 3, '<3'), (6, 8, '6-8')]:
    print(f"===== speed bin {blab} =====")
    for name, rks in [('T64', T64), ('T64B', T64B), ('V282', V282)]:
        Xs = [load(rk) for rk in rks]
        aa = np.concatenate([X['absang'][(X['v'] >= lo) & (X['v'] < hi)] for X in Xs])
        if len(aa):
            print(f"  {name:6s} absang: n={len(aa):4d} mean={aa.mean():6.1f} p50={np.percentile(aa,50):5.1f} p90={np.percentile(aa,90):6.1f}")
    ABINS = [(0, 5, '0-5deg'), (5, 10, '5-10deg'), (10, 20, '10-20deg'), (20, 9999, '20+deg')]
    for amin, amax, alab in ABINS:
        t64 = group_stat(T64, lo, hi, amin, amax)
        t64b = group_stat(T64B, lo, hi, amin, amax)
        v282 = group_stat(V282, lo, hi, amin, amax)
        print(f"  {alab:9s} T64 n={t64['n']:4d} model={t64['model_rate']:6.2f} setpt={t64['setpoint_rate']:6.2f}  |  "
              f"T64B n={t64b['n']:4d} model={t64b['model_rate']:6.2f} setpt={t64b['setpoint_rate']:6.2f}  |  "
              f"V282 n={v282['n']:4d} model={v282['model_rate']:6.2f} setpt={v282['setpoint_rate']:6.2f}")
    print()

# overall window-count share by demand bin per group (is the pooled stat a mix-shift artifact?)
print("===== window-count SHARE by demand bin, speed 3-6 (mix-shift check) =====")
for name, rks in [('T64', T64), ('T64B', T64B), ('V282', V282)]:
    Xs = [load(rk) for rk in rks]
    aa = np.concatenate([X['absang'][(X['v'] >= 3) & (X['v'] < 6)] for X in Xs])
    tot = len(aa)
    shares = [(np.sum((aa >= a) & (aa < b)) / tot * 100) for a, b in [(0, 5), (5, 10), (10, 20), (20, 9999)]]
    print(f"  {name:6s} n={tot:4d}  share 0-5:{shares[0]:5.1f}%  5-10:{shares[1]:5.1f}%  10-20:{shares[2]:5.1f}%  20+:{shares[3]:5.1f}%")
