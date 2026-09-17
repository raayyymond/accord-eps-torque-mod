import sys; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np, v282cmp as V
for rk in ['00000064--ce6b0b0ebb','0000006c--68c6e94b17','00000039--f56039af87']:
    S=V.load(rk); u=V.usable(S,5)
    for k in ['la_act','la_yaw','la_pose','model','setpoint']:
        x=S[k][u]; print(rk,k,'nan',np.isnan(x).mean(),'std',np.nanstd(x), 'corr w model', np.corrcoef(np.nan_to_num(x),np.nan_to_num(S['model'][u]))[0,1])
    # curvature from pose vs angle at low speed
    u2=V.usable(S,3,8)&(np.abs(S['sr'])<5)
    k_pose=S['la_pose'][u2]/S['v'][u2]**2; ang=(S['sa']-S['aoff'])[u2]
    print('  slope curv_pose per deg', np.polyfit(ang,k_pose,1), ' model curv per deg', np.polyfit(ang,S['model'][u2]/S['v'][u2]**2,1))
    del S
