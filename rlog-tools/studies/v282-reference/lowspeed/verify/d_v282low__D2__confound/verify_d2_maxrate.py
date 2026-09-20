import sys
import numpy as np
from scipy import signal
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS = 100.0
def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)

def load_runs(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS = D['RUNS']; RUNLEN = D['RUNLEN']
    out, o = [], 0
    for n in RUNLEN:
        out.append(RUNS[:, o:o+n]); o += n
    return out

V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']
V282OLD_ROUTES = ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4']
TORQUE_ROUTES = {'T64': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
                  'T64B': ['0000006e--6ca3e014fd'],
                  'T5': ['00000076--d0b7ea7e4d'],
                  'T4': ['00000075--6c8687d5bd']}

def maxrate_sr5(routes, vlo=2.5, vhi=15.0):
    mx = 0.0
    per = {}
    for rk in routes:
        rmax = 0.0
        for r in load_runs(rk):
            if r.shape[1] < 20:
                continue
            v, sr = r[0], r[4]
            m = (v >= vlo) & (v < vhi)
            if m.sum() < 20:
                continue
            sr5 = lp(sr, 5.0, 2)
            rmax = max(rmax, float(np.max(np.abs(sr5[m]))))
        per[rk] = rmax
        mx = max(mx, rmax)
    return mx, per

for name, routes in [('V282', V282_ROUTES), ('V282old', V282OLD_ROUTES)] + list(TORQUE_ROUTES.items()):
    mx, per = maxrate_sr5(routes)
    print(f"{name:8s} max sr5(5Hz-lp) rate = {mx:.1f}  per-route: { {k[:8]: round(v,1) for k,v in per.items()} }")

# also raw sr max, restricted to <15 m/s usable exactly as claim states "below 15 m/s"
print()
for name, routes in [('V282', V282_ROUTES), ('V282old', V282OLD_ROUTES)]:
    mx = 0.0
    for rk in routes:
        for r in load_runs(rk):
            v, sr = r[0], r[4]
            m = (v < 15.0)
            if m.sum():
                mx = max(mx, float(np.max(np.abs(sr[m]))))
    print(f"{name} raw sr max (v<15): {mx:.1f}")
