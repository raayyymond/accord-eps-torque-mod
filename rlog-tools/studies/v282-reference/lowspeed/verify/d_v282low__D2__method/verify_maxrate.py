import sys, numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS=100.0
def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)

results={}
for rk, meta in V.ROUTES.items():
    g = meta['group']
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS=D['RUNS']; RUNLEN=D['RUNLEN']; o=0
    raw_max=[]; f5_max=[]
    for n in RUNLEN:
        r = RUNS[:, o:o+n]; o+=n
        if n<300: continue
        v=r[0]; sr=r[4]
        m8=(v>=2.5)&(v<8.0)
        if m8.sum()<50: continue
        raw_max.append(np.max(np.abs(sr[m8])))
        sr5=lp(sr,5.0,2)
        f5_max.append(np.max(np.abs(sr5[m8])))
    results.setdefault(g, dict(raw=[], f5=[]))
    results[g]['raw'].extend(raw_max); results[g]['f5'].extend(f5_max)

print("group   raw_max(top3)              f5(5Hz-lp)_max(top3)")
for g,d in results.items():
    raw=np.sort(d['raw'])[-3:] if d['raw'] else []
    f5=np.sort(d['f5'])[-3:] if d['f5'] else []
    print(f"{g:8s} raw_top3={raw}  f5_top3={f5}  raw_overall_max={max(d['raw']) if d['raw'] else None:.1f}  f5_overall_max={max(d['f5']) if d['f5'] else None:.1f}")
