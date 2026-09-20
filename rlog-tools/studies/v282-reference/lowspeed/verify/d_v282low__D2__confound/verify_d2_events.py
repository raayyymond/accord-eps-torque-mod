import sys
import numpy as np
HERE = 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
sys.path.insert(0, HERE)
from d_extract import EV_COLS
E = {c: i for i, c in enumerate(EV_COLS)}

V282_ROUTES = ['00000064--ce6b0b0ebb', '00000065--b9f78988bd', '0000006c--2bc842dbac']

def load(rk):
    D = np.load(f'{HERE}/data/{rk}.npz')
    return D['EV']

print("=== per-route event counts & peak_rate_meas max, V282 ===")
allev = []
for rk in V282_ROUTES:
    EV = load(rk)
    allev.append(EV)
    if len(EV) == 0:
        print(rk, "no events"); continue
    for vb in [(2.5,8),(8,15)]:
        m = (EV[:,E['v']]>=vb[0])&(EV[:,E['v']]<vb[1])
        X = EV[m]
        if len(X)==0:
            continue
        rr = X[:,E['peak_rate_meas']]/X[:,E['peak_rate_des']]
        print(f"{rk} speed{vb}: n={len(X)} rate_ratio_med={np.median(rr):.3f} max_peak_rate_meas={np.max(np.abs(X[:,E['peak_rate_meas']])):.1f}")

allev = np.concatenate(allev)
for vb in [(2.5,8),(8,15)]:
    m = (allev[:,E['v']]>=vb[0])&(allev[:,E['v']]<vb[1])
    X = allev[m]
    print(f"POOLED speed{vb}: n={len(X)} max|peak_rate_meas|={np.max(np.abs(X[:,E['peak_rate_meas']])) if len(X) else float('nan'):.1f}")

print("\n=== no-6c pooled ===")
noC = np.concatenate([load(rk) for rk in V282_ROUTES if '6c' not in rk])
for vb in [(2.5,8),(8,15)]:
    m = (noC[:,E['v']]>=vb[0])&(noC[:,E['v']]<vb[1])
    X = noC[m]
    if len(X)==0:
        print(f"speed{vb}: n=0"); continue
    rr = X[:,E['peak_rate_meas']]/X[:,E['peak_rate_des']]
    print(f"speed{vb}: n={len(X)} rate_ratio(25/50/75)={np.percentile(rr,[25,50,75])} max|meas|={np.max(np.abs(X[:,E['peak_rate_meas']])):.1f}")
