"""Adversarial CONFOUND check on finding B2 (b_shake / lowspeed).
Lens: V282's <8 m/s bucket is dominated by ONE route (0000006c--2bc842dbac).
T64B (0000006e) carries 4x the demand of 6c/6d inside the 'rev64' torque group.
Question: does the claimed torque-mode vs V282 shake ranking (9.7 vs 2.6 deg/s
at <8 m/s, |H| 0.73 vs 0.25) survive when the dominant single route is pulled
out of each side?

Reuses the exact wstats() formula from b05_summary.py (rate rms, coherence,
transfer-function magnitude H) on the b04_rows_<route>.npz window arrays that
B2's own numbers were computed from. Run from
rlog-tools/studies/v282-reference/lowspeed/b_shake/ (relative paths to out/).
"""
import numpy as np

NPS = 256
NORM = 1.0 / (np.sum(np.hanning(256) ** 2) * 100) * 2
f = np.fft.rfftfreq(NPS, 0.01)
BB = (f >= 1.5) & (f <= 3.55)
df = f[1] - f[0]


def wstats(P, A, C):
    Prr = P.sum(0); Paa = A.sum(0); Sra = C.sum(0); n = len(P)
    coh = np.abs(Sra) ** 2 / np.maximum(Prr * Paa, 1e-30)
    cohw = float(np.average(coh, weights=Prr))
    rr = np.sqrt(Prr.sum() * NORM * df / n)
    H = float(np.average(np.abs(Sra) / np.maximum(Paa, 1e-30), weights=Paa))
    return dict(rate=rr, coh=cohw, H=H, n=n)


def bin_stats(R, rks, lo, hi, seed=0):
    P, A, C = [], [], []
    for rk in rks:
        X = R[rk]
        s = (X['v'] >= lo) & (X['v'] < hi)
        P.append(X['Prr'][s]); A.append(X['Paa'][s]); C.append(X['Sra'][s])
    P = np.concatenate(P); A = np.concatenate(A); C = np.concatenate(C)
    if len(P) < 5:
        return None
    st = wstats(P, A, C)
    rng = np.random.default_rng(seed)
    B = [wstats(P[i], A[i], C[i]) for i in (rng.integers(0, len(P), len(P)) for _ in range(500))]
    st['rate_ci'] = [float(np.percentile([b['rate'] for b in B], 2.5)), float(np.percentile([b['rate'] for b in B], 97.5))]
    return st


if __name__ == '__main__':
    import os
    os.chdir(os.path.join(os.path.dirname(__file__), '..', '..', 'b_shake'))

    V282 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
    DOMINANT = '0000006c--2bc842dbac'
    REV64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']
    T64B = '0000006e--6ca3e014fd'  # 4x demand route

    RV = {rk: dict(np.load(f'out/b04_rows_{rk}.npz')) for rk in V282}
    RT = {rk: dict(np.load(f'out/b04_rows_{rk}.npz')) for rk in REV64}
    RT4 = {rk: dict(np.load(f'out/b04_rows_00000075--6c8687d5bd.npz')) for rk in ['00000075--6c8687d5bd']}

    print('=== window-time weight of the dominant V282 route ===')
    for rk in V282:
        v = RV[rk]['v']
        n8 = ((v >= 0) & (v < 8)).sum()
        print(rk, 'n_windows<8:', n8)

    print()
    print('=== V282 <8 m/s: full group vs excluding the dominant route ===')
    for lo, hi, lab in [(0, 3, '<3'), (3, 6, '3-6'), (6, 8, '6-8'), (0, 8, '<8')]:
        full = bin_stats(RV, V282, lo, hi)
        excl = bin_stats(RV, [r for r in V282 if r != DOMINANT], lo, hi)
        print(f'{lab:5s} full: rate {full["rate"]:.2f} {full["rate_ci"]} H {full["H"]:.2f}  |  '
              f'excl-dominant: rate {excl["rate"]:.2f} {excl["rate_ci"]} H {excl["H"]:.2f}')

    print()
    print('=== rev64 (torque) <8 m/s: full group (incl 4x-demand T64B) vs T64 only (excl T64B) ===')
    full = bin_stats(RT, REV64, 0, 8)
    excl = bin_stats(RT, [r for r in REV64 if r != T64B], 0, 8)
    print(f'rev64 full: rate {full["rate"]:.2f} {full["rate_ci"]}  |  T64-only (excl T64B): rate {excl["rate"]:.2f} {excl["rate_ci"]}')

    print()
    print('=== independent T4 route (different day/road, matched low demand), <8 m/s ===')
    t4 = bin_stats(RT4, ['00000075--6c8687d5bd'], 0, 8)
    print(f'T4 <8: rate {t4["rate"]:.2f} {t4["rate_ci"]}')
