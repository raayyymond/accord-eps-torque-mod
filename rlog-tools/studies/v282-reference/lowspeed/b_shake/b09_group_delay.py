"""b09: group delay of wheel rate relative to (a) the fork setpoint desired-angle rate and (b) the MODEL desired-curvature
angle rate (sign corrected: the model-curvature angle correlates -0.986 with steeringAngleDeg, so it is negated here),
from the 1.5-3.5 Hz cross-spectra of b04 (unwrapped phase slope, weighted by rate power). >0 = wheel LAGS the demand.
Negative group delay vs the model = the model's curvature follows the wheel (reverse path)."""
import numpy as np, bs
G = {'rev64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd'], 'T5': ['00000076--d0b7ea7e4d'],
     'T4': ['00000075--6c8687d5bd'], 'V282': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac'],
     'V282old': ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']}
f = np.fft.rfftfreq(256, 0.01); fb = f[(f >= 1.5) & (f <= 3.55)]; om = 2 * np.pi * fb
rng = np.random.default_rng(0)
def gd(S, w):
    ph = np.unwrap(np.angle(S)); return float(-np.polyfit(om, ph, 1, w=np.sqrt(w))[0]), np.degrees(np.angle(S)).round(0)
for g, rks in G.items():
    for lo, hi, lab in [(0, 8, '<8'), (3, 8, '3-8'), (8, 15, '8-15')]:
        Sra, Srm, Prr = [], [], []
        for rk in rks:
            X = np.load(bs.OUT + f'b04_rows_{rk}.npz'); s = (X['v'] >= lo) & (X['v'] < hi)
            Sra.append(X['Sra'][s]); Srm.append(-X['Srm'][s]); Prr.append(X['Prr'][s])
        Sra = np.concatenate(Sra); Srm = np.concatenate(Srm); Prr = np.concatenate(Prr)
        ga, pa = gd(Sra.sum(0), Prr.sum(0)); gm, pm = gd(Srm.sum(0), Prr.sum(0))
        B = []
        for _ in range(300):
            i = rng.integers(0, len(Sra), len(Sra)); B.append((gd(Sra[i].sum(0), Prr[i].sum(0))[0], gd(Srm[i].sum(0), Prr[i].sum(0))[0]))
        B = np.array(B)
        print(f"{g:8s} {lab:5s} n{len(Sra):4d}  gd vs setpoint {ga*1000:+5.0f} ms [{np.percentile(B[:,0],2.5)*1000:+.0f},{np.percentile(B[:,0],97.5)*1000:+.0f}] phase {pa}"
              f" | gd vs model {gm*1000:+5.0f} ms [{np.percentile(B[:,1],2.5)*1000:+.0f},{np.percentile(B[:,1],97.5)*1000:+.0f}] phase {pm}")
