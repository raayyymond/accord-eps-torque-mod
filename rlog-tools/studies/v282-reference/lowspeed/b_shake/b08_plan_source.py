"""b08: is the 1.5-3.5 Hz desired-angle-rate content already in the MODEL desired curvature, or added by the fork's setpoint
shaping? rms of each (deg/s) and coherence of the wheel rate with each, per group x bin (from b04 windows)."""
import numpy as np, bs
G = {'rev64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd'], 'T5': ['00000076--d0b7ea7e4d'],
     'T4': ['00000075--6c8687d5bd'], 'V282': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac'],
     'V282old': ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']}
NORM = 2.0 / (np.sum(np.hanning(256) ** 2) * 100); df = 100 / 256
for g, rks in G.items():
    for lo, hi, lab in bs.BINS + [(0, 8, '<8')]:
        acc = dict(Prr=0, Paa=0, Pmm=0, Sra=0, Srm=0, n=0)
        for rk in rks:
            X = np.load(bs.OUT + f'b04_rows_{rk}.npz'); s = (X['v'] >= lo) & (X['v'] < hi)
            for k in ('Prr', 'Paa', 'Pmm', 'Sra', 'Srm'):
                acc[k] = acc[k] + X[k][s].sum(0)
            acc['n'] += int(s.sum())
        c = lambda S, P: float(np.average(np.abs(S) ** 2 / np.maximum(acc['Prr'] * P, 1e-30), weights=acc['Prr']))
        r = lambda P: float(np.sqrt(np.sum(P) * NORM * df / max(acc['n'], 1)))
        print(f"{g:8s} {lab:5s} n{acc['n']:4d}  rate {r(acc['Prr']):5.2f}  setpoint-angle-rate {r(acc['Paa']):5.2f} (coh {c(acc['Sra'], acc['Paa']):.2f})"
              f"  model-angle-rate {r(acc['Pmm']):5.2f} (coh {c(acc['Srm'], acc['Pmm']):.2f})")
