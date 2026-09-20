"""Frame-level |measured rate|/|demand rate| for demand rate > 40 deg/s, and max |measured rate| below 15 m/s,
reconstructed independently from RUNS (v, sad, sadc, sa, sr, out, f, p, i, e4), speed-filtered 2.5-15 m/s.
Also the 'never exceeded 151 deg/s' claim, and repeats with route 6c excluded from V282.
"""
import sys
import numpy as np
from scipy import signal
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS = 100.0

def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)

def deriv(x):
    return np.gradient(x) * FS

def load_runs(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS = D['RUNS']; RUNLEN = D['RUNLEN']
    out, o = [], 0
    for n in RUNLEN:
        out.append(RUNS[:, o:o+n]); o += n
    return out  # each: rows v, sad, sadc, sa, sr, out, f, p, i, e4

V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
V282OLD_ROUTES = ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']
TORQUE_ROUTES = {'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
                  'T64B': ['0000006e--6ca3e014fd'],
                  'T5': ['00000076--d0b7ea7e4d'],
                  'T4': ['00000075--6c8687d5bd']}

def frame_stats(routes, vlo=2.5, vhi=15.0, thresh=40.0, exclude=None):
    ratios = []
    maxrate = 0.0
    per_route_max = {}
    for rk in routes:
        if exclude and exclude in rk:
            continue
        rmax = 0.0
        for r in load_runs(rk):
            if r.shape[1] < 20:
                continue
            v, sad, sr = r[0], r[1], r[4]
            m_v = (v >= vlo) & (v < vhi)
            if m_v.sum() < 20:
                continue
            rate_des = deriv(lp(sad, 2.0, 2))
            m = m_v & (np.abs(rate_des) > thresh)
            if m.sum():
                ratios.append(np.abs(sr[m]) / np.abs(rate_des[m]))
            if m_v.sum():
                rmax = max(rmax, float(np.max(np.abs(sr[m_v]))))
        per_route_max[rk] = rmax
        maxrate = max(maxrate, rmax)
    R = np.concatenate(ratios) if ratios else np.array([])
    return R, maxrate, per_route_max

print("=== frame-level |rate|/|demand rate|, demand>40 deg/s, speed 2.5-15 m/s ===")
for name, routes in [('V282', V282_ROUTES), ('V282old', V282OLD_ROUTES)] + list(TORQUE_ROUTES.items()):
    R, mx, prm = frame_stats(routes)
    if len(R):
        print(f"{name:8s} n={len(R):6d} median_ratio={np.median(R):.3f} mean={np.mean(R):.3f} max|rate|={mx:.1f}  per_route_max={ {k[:8]: round(v,1) for k,v in prm.items()} }")
    else:
        print(f"{name:8s} n=0 max|rate|={mx:.1f}")

print("\n=== V282 excluding route 6c ===")
R, mx, prm = frame_stats(V282_ROUTES, exclude='6c')
if len(R):
    print(f"no-6c n={len(R)} median_ratio={np.median(R):.3f} mean={np.mean(R):.3f} max|rate|={mx:.1f} per_route_max={ {k[:8]: round(v,1) for k,v in prm.items()} }")
else:
    print("no-6c: n=0 (no frames exceed threshold outside route 6c)", "max|rate|=", mx)

print("\n=== V282 route 6c ONLY ===")
R, mx, prm = frame_stats(['0000006c--2bc842dbac'])
if len(R):
    print(f"6c-only n={len(R)} median_ratio={np.median(R):.3f} mean={np.mean(R):.3f} max|rate|={mx:.1f}")
