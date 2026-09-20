"""Adversarial verification of finding D3.
Re-derive the section-C cmd_to_rate and desrate_to_cmd spectra directly from the cached per-route
.npz data (NOT from d_analyze.out), and test the lens's named confound: drop route 0000006c
(the dominant V282 route, 62 segments) and see whether the qualitative claim survives.
Also spot-check T64B (4x demand) does not carry the torque-mode low-coherence result alone.
"""
import sys, json
import numpy as np
from scipy import signal

HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
sys.path.insert(0, HERE)
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
from d_extract import BLK_COLS, EV_COLS

VBS = {'2.5-8': (2.5, 8), '8-15': (8, 15)}
NPS = 256

def load_route(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    return dict(group=V.ROUTES[rk]['group'], RUNS=D['RUNS'], RUNLEN=D['RUNLEN'])

def split_runs(r):
    out, o = [], 0
    for n in r['RUNLEN']:
        out.append(r['RUNS'][:, o:o + n]); o += n
    return out

def run_spectra(runs, vb, x_key, y_key):
    v0, v1 = VBS[vb]
    Pxx = Pyy = Pxy = None; sec = 0.0; fr = None
    for r in runs:
        v = r[0]
        m = (v >= v0) & (v < v1)
        idx = np.nonzero(np.diff(np.r_[0, m.astype(int), 0]))[0].reshape(-1, 2)
        for a, b in idx:
            if b - a < NPS:
                continue
            X = dict(sad=r[1], sadc=r[2], sa=r[3], sr=r[4], out=r[5], f=r[6], p=r[7], i=r[8])
            X['rdes'] = np.gradient(X['sadc']) * 100
            x = signal.detrend(X[x_key][a:b]); y = signal.detrend(X[y_key][a:b])
            f, pxx = signal.welch(x, 100, nperseg=NPS); _, pyy = signal.welch(y, 100, nperseg=NPS); _, pxy = signal.csd(x, y, 100, nperseg=NPS)
            w = b - a
            Pxx = pxx * w if Pxx is None else Pxx + pxx * w
            Pyy = pyy * w if Pyy is None else Pyy + pyy * w
            Pxy = pxy * w if Pxy is None else Pxy + pxy * w
            fr = f; sec += w / 100
    if Pxx is None:
        return None
    outb = {}
    for lo, hi in [(0.3, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 10.0)]:
        s = (fr >= lo) & (fr < hi)
        coh = np.abs(Pxy[s]) ** 2 / np.maximum(Pxx[s] * Pyy[s], 1e-30)
        H = np.abs(Pxy[s]) / np.maximum(Pxx[s], 1e-30)
        ph = np.degrees(np.angle(Pxy[s].sum()))
        fc = float(np.average(fr[s], weights=Pxx[s]))
        outb[f'{lo}-{hi}'] = dict(coh=float(np.average(coh, weights=Pxx[s])), H=float(np.average(H, weights=Pxx[s])),
                                   lag_s=float(-ph / 360 / fc))
    outb['sec'] = sec
    return outb

ROUTE_SETS = {
    'V282_all3': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac'],
    'V282_no6c': ['00000064--ce6b0b0ebb', '00000065--b9f78988bd'],
    'V282old_all3': ['00000039--f56039af87', '0000003a--283a39a1d6', '0000003c--927965c2b4'],
    'T64_only': ['0000006c--68c6e94b17', '0000006d--05e83bb04f'],
    'T64B_only': ['0000006e--6ca3e014fd'],
    'T5_only': ['00000076--d0b7ea7e4d'],
    'T4_only': ['00000075--6c8687d5bd'],
    'Torque_ex_T64B': ['0000006c--68c6e94b17', '0000006d--05e83bb04f', '00000076--d0b7ea7e4d', '00000075--6c8687d5bd'],
}

results = {}
for name, rks in ROUTE_SETS.items():
    runs = sum([split_runs(load_route(rk)) for rk in rks], [])
    for vb in VBS:
        for nm, (xk, yk) in {'cmd_to_rate': ('out', 'sr'), 'desrate_to_cmd': ('rdes', 'out')}.items():
            r = run_spectra(runs, vb, xk, yk)
            results[f'{name}|{vb}|{nm}'] = r

for k, r in results.items():
    if r is None:
        print(f'{k:40s} none'); continue
    print(f"{k:40s} {r['sec']:6.0f}s " + ' | '.join(f"{b}: coh {r[b]['coh']:.2f} H {r[b]['H']:.3g} lag {r[b]['lag_s']:+.3f}" for b in ['0.3-1.0', '1.0-2.0', '2.0-4.0', '4.0-10.0']))

json.dump({k: v for k, v in results.items()}, open(f'{HERE}/../verify/d_v282low__D3__confound/confound_results.json', 'w'), indent=1, default=float)
