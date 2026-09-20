import sys
sys.path.insert(0, '.')
import numpy as np
from scipy import signal
import v282cmp as V

L_, SF = 2.83, -7.0e-4
NPS, HOP = 256, 128
f = np.fft.rfftfreq(NPS, 0.01); BB = (f >= 1.5) & (f <= 3.55)
win = signal.get_window('hann', NPS)
NORM = 2.0 / (np.sum(np.hanning(256) ** 2) * 100); df = 100 / 256

def welch_rms(rk, lo, hi):
    S = V.load(rk)
    v = S['v']
    sR = np.nan_to_num(S['sR'], nan=16.5)
    D = np.load(V.CACHE / f'{rk}.npz')
    curv = D['cs_des_curv']
    sa_mdl = np.degrees(curv * sR * L_ * (1 - SF * v * v))
    sr = S['sr']
    m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_mdl)
    Pmm_sum = 0.0; n = 0
    for a, b in V.runs(m, S['t'], min_s=4.0):
        amr = np.gradient(sa_mdl[a:b]) * 100
        vb = v[a:b]
        for s in range(0, b - a - NPS + 1, HOP):
            vm = vb[s:s+NPS].mean()
            if not (lo <= vm < hi):
                continue
            M = np.fft.rfft(signal.detrend(amr[s:s+NPS]) * win)
            Pmm_sum += np.sum(np.abs(M[BB])**2)
            n += 1
    if n == 0:
        return None, 0
    rms = np.sqrt(Pmm_sum * NORM * df / n)
    return float(rms), n

for rk, lab in [('0000006c--68c6e94b17', 'rev64-6c'), ('0000006d--05e83bb04f', 'rev64-6d'),
                ('0000006e--6ca3e014fd', 'rev64-6e'),
                ('00000064--ce6b0b0ebb', 'V282-64'), ('00000065--b9f78988bd', 'V282-65'),
                ('0000006c--2bc842dbac', 'V282-6c')]:
    for lo, hi, name in [(3, 6, '3-6'), (6, 8, '6-8')]:
        r, n = welch_rms(rk, lo, hi)
        print(f"{lab:12s} {name:5s} n={n:6d}  welch-rms(model angle rate) = {r}")
