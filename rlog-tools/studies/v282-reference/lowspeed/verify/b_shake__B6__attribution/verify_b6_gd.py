import sys
sys.path.insert(0, '.')
import numpy as np
from scipy import signal
import v282cmp as V

L_, SF = 2.83, -7.0e-4
NPS, HOP = 256, 128
f = np.fft.rfftfreq(NPS, 0.01); BB = (f >= 1.5) & (f <= 3.55)
fb = f[BB]; om = 2*np.pi*fb
win = signal.get_window('hann', NPS)

def collect(rk, lo, hi):
    S = V.load(rk)
    v = S['v']
    sR = np.nan_to_num(S['sR'], nan=16.5)
    D = np.load(V.CACHE / f'{rk}.npz')
    curv = D['cs_des_curv']
    sa_mdl = np.degrees(curv * sR * L_ * (1 - SF * v * v))
    sr = S['sr']
    m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_mdl)
    Sra_list, Prr_list = [], []
    for a, b in V.runs(m, S['t'], min_s=4.0):
        x = sr[a:b]
        amr = np.gradient(sa_mdl[a:b]) * 100
        vb = v[a:b]
        for s in range(0, b - a - NPS + 1, HOP):
            vm = vb[s:s+NPS].mean()
            if not (lo <= vm < hi):
                continue
            R = np.fft.rfft(signal.detrend(x[s:s+NPS]) * win)
            M = np.fft.rfft(signal.detrend(amr[s:s+NPS]) * win)
            Srm = np.conj(M[BB]) * R[BB]
            Sra_list.append(Srm); Prr_list.append(np.abs(R[BB])**2)
    return np.array(Sra_list), np.array(Prr_list)

rks = ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '0000006e--6ca3e014fd']
Srm_all, Prr_all = [], []
for rk in rks:
    Srm, Prr = collect(rk, 0, 8)
    Srm_all.append(-Srm)  # sign correction per b09
    Prr_all.append(Prr)
Srm_all = np.concatenate(Srm_all); Prr_all = np.concatenate(Prr_all)
print("n windows:", len(Srm_all))
Ssum = Srm_all.sum(0); Wsum = Prr_all.sum(0)
ph = np.unwrap(np.angle(Ssum))
slope = np.polyfit(om, ph, 1, w=np.sqrt(Wsum))[0]
gd = -slope
print("group delay (ms):", gd*1000)
