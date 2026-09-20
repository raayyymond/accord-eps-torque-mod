import sys, numpy as np
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low')
import v282cmp as V
from d_extract import EV_COLS
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
E = {c:i for i,c in enumerate(EV_COLS)}
groups={}
for rk, meta in V.ROUTES.items():
    D=np.load(f'{HERE}/data/{rk}.npz')
    EV=D['EV']
    groups.setdefault(meta['group'],[]).append(EV)
print("Independent recompute of E events rate_ratio (peak_rate_meas/peak_rate_des), 2.5-8 m/s")
for g,arrs in groups.items():
    EV = np.concatenate([a for a in arrs if len(a)]) if any(len(a) for a in arrs) else np.zeros((0,len(EV_COLS)))
    if not len(EV): continue
    m = (EV[:,E['v']]>=2.5)&(EV[:,E['v']]<8.0)
    X = EV[m]
    if not len(X): continue
    rr = X[:,E['peak_rate_meas']]/X[:,E['peak_rate_des']]
    print(f"{g:8s} n={len(X):3d}  median_ratio={np.median(rr):.3f}  p25={np.percentile(rr,25):.3f}  p75={np.percentile(rr,75):.3f}")
    print(f"          overrun median={np.median(X[:,E['overrun']]):.3f}")
