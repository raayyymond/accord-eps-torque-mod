import sys
sys.path.insert(0, '.')
import numpy as np
from scipy import signal
import v282cmp as V

L_, SF = 2.83, -7.0e-4

def band_rms(rk, lo, hi):
    S = V.load(rk)
    v = S['v']
    sR = np.nan_to_num(S['sR'], nan=16.5)
    D = np.load(V.CACHE / f'{rk}.npz')
    curv = D['cs_des_curv']
    sa_mdl = np.degrees(curv * sR * L_ * (1 - SF * v * v))
    sr = S['sr']
    m = V.usable(S, 0, 15) & np.isfinite(sr) & np.isfinite(v) & np.isfinite(sa_mdl)
    SOS = signal.butter(4, [1.5, 3.5], btype='band', fs=100, output='sos')
    vals = []
    for a, b in V.runs(m, S['t'], min_s=4.0):
        amr = np.gradient(sa_mdl[a:b]) * 100
        vb = v[a:b]
        sel = (vb >= lo) & (vb < hi)
        if sel.sum() < 100:
            continue
        filt = signal.sosfiltfilt(SOS, amr)
        vals.append(filt[sel])
    if not vals:
        return None, 0
    allv = np.concatenate(vals)
    return float(np.sqrt(np.mean(allv**2))), len(allv)

for rk, lab in [('0000006c--68c6e94b17', 'rev64-6c'), ('0000006d--05e83bb04f', 'rev64-6d'),
                ('00000064--ce6b0b0ebb', 'V282-64'), ('00000065--b9f78988bd', 'V282-65'),
                ('0000006c--2bc842dbac', 'V282-6c')]:
    for lo, hi, name in [(3, 6, '3-6'), (6, 8, '6-8')]:
        r, n = band_rms(rk, lo, hi)
        print(f"{lab:12s} {name:5s} n={n:6d}  bandpass-rms(model angle rate) = {r}")
    del rk
