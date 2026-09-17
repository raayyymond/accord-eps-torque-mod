import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
import numpy as np
from scipy import signal

THR, VMIN = 0.4, 3.0  # matches s2_extract.py thresholds

def raw_peaks_below8(S, thr=THR):
    model = np.nan_to_num(S['model'])
    j = V.deriv(V.lowpass(model, 2.0))
    aj = np.abs(j)
    pk, _ = signal.find_peaks(aj, height=thr, distance=int(2.0*V.FS))
    v = S['v']; pressed = S['pressed']; active = S['active']
    below8 = v[pk] < 8.0
    idx = pk[below8]
    n = len(idx)
    n_pressed = int(np.sum(pressed[idx]))
    n_inactive = int(np.sum(~active[idx]))
    n_usable = int(np.sum(active[idx] & ~pressed[idx]))
    return n, n_pressed, n_inactive, n_usable

for rk, meta in V.ROUTES.items():
    f = V.CACHE / f"{rk}.npz"
    if not f.exists(): continue
    S = V.load(rk)
    n, npress, ninact, nusable = raw_peaks_below8(S)
    print(f"{rk:24s} {meta['group']:8s} raw_peaks<8m/s={n:3d} pressed={npress:3d} inactive={ninact:3d} usable(active&~pressed)={nusable:3d}")
