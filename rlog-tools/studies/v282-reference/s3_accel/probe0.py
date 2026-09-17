import sys; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np, v282cmp as V
for rk in V.ROUTES:
    S=V.load(rk); u=V.usable(S)
    v=S['v']; sa=np.abs(S['sa']-np.nan_to_num(S['aoff']))
    ae=V.accel_events(S)
    s=[]
    for lo,hi in [(0,3),(3,5),(5,8),(8,15),(15,40)]:
        m=u&(v>=lo)&(v<hi); s.append(f"{lo}-{hi}:{m.sum()/100:5.0f}s a>30:{(m&(sa>30)).sum()/100:4.0f}s a>90:{(m&(sa>90)).sum()/100:4.0f}")
    print(rk, S['meta']['group'], len(ae), '|', ' '.join(s))
    print('   lat_delay med', np.nanmedian(S['lat_delay']), 'sR', np.nanmedian(S['sR']), 'nan la_yaw', np.isnan(S['la_yaw']).mean(), 'corr act/yaw', np.corrcoef(np.nan_to_num(S['la_act'][u]),np.nan_to_num(S['la_yaw'][u]))[0,1])
    del S
