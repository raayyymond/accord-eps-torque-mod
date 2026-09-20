import sys, numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
FS=100.0
def lp(x, fc, order=4):
    return signal.sosfiltfilt(signal.butter(order, fc, btype='low', fs=FS, output='sos'), x)
def deriv(x):
    return np.gradient(x) * FS

results={}
for rk, meta in V.ROUTES.items():
    g = meta['group']
    D = np.load(f'{HERE}/data/{rk}.npz')
    RUNS=D['RUNS']; RUNLEN=D['RUNLEN']; o=0
    ratios=[]
    for n in RUNLEN:
        r = RUNS[:, o:o+n]; o+=n
        if n<300: continue
        v=r[0]; sad=r[1]; sr=r[4]
        rate_des = deriv(lp(sad, 2.0, 2))
        sr5 = lp(sr, 5.0, 2)
        m = (v>=2.5)&(v<8.0)&(np.abs(rate_des)>40)
        if m.sum():
            ratios.append(np.abs(sr5[m])/np.abs(rate_des[m]))
    if ratios:
        allr=np.concatenate(ratios)
        results[g]=(len(allr), np.median(allr), np.mean(allr))
print("group    n     median    mean  (using 5Hz-lp measured rate / 2Hz-lp demand-rate deriv, own lead)")
for g,(n,med,mean) in results.items():
    print(f"{g:8s} {n:5d}  {med:.3f}   {mean:.3f}")
