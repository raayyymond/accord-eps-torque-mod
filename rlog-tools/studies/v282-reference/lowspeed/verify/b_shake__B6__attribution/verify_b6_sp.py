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

def welch_rms_sp(rks, lo, hi):
    Pmm_sum = 0.0; n = 0
    for rk in rks:
        S = V.load(rk)
        v = S['v']
        sR = np.nan_to_num(S['sR'], nan=16.5)
        sp = np.nan_to_num(S['setpoint'])
        sa_des = np.degrees((-sp / np.maximum(v*v, 1.0)) * sR * L_ * (1 - SF * v * v))
        sr = S['sr']
        m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_des)
        for a, b in V.runs(m, S['t'], min_s=4.0):
            adr = np.gradient(sa_des[a:b]) * 100
            vb = v[a:b]
            for s in range(0, b - a - NPS + 1, HOP):
                vm = vb[s:s+NPS].mean()
                if not (lo <= vm < hi):
                    continue
                A = np.fft.rfft(signal.detrend(adr[s:s+NPS]) * win)
                Pmm_sum += np.sum(np.abs(A[BB])**2)
                n += 1
    if n == 0:
        return None, 0
    rms = np.sqrt(Pmm_sum * NORM * df / n)
    return float(rms), n

rev64 = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']
v282 = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
for lo, hi, name in [(0,3,'<3'), (3,6,'3-6'), (6,8,'6-8')]:
    r, n = welch_rms_sp(rev64, lo, hi)
    print(f"rev64 {name:5s} n={n:4d} setpoint-angle-rate={r:.2f}")
for lo, hi, name in [(0,3,'<3'), (3,6,'3-6'), (6,8,'6-8')]:
    r, n = welch_rms_sp(v282, lo, hi)
    print(f"V282  {name:5s} n={n:4d} setpoint-angle-rate={r:.2f}")
