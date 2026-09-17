import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import s3turns as T
import v282cmp as V

rk = '0000006c--68c6e94b17'
R = T.prep(rk)
evs, rej = T.find_turns(R)
e = [e for e in evs if abs(e['t']-751.2) < 1][0]
n = len(R['t'])
mask = np.zeros(n, bool); mask[e['w0']:e['w1']] = True; mask &= ~R['pressed']
adr = V.deriv(R['ad'])
for a,b in V.runs(mask, R['t'], min_s=2.56):
    v = R['v'][a:b]; ad = R['ad'][a:b]; adr_w = adr[a:b]; t = R['t'][a:b]
    print("v min/median/max", v.min(), np.median(v), v.max())
    i_worst = np.argmax(np.abs(adr_w))
    lo = max(0, i_worst-8); hi = min(len(t), i_worst+8)
    print("around the worst sample:")
    for k in range(lo,hi):
        print(f"  t={t[k]:8.3f} v={v[k]:6.3f} ad={ad[k]:9.2f} adr={adr_w[k]:10.1f} pressed={R['pressed'][a+k]} active={R['active'][a+k]}")
