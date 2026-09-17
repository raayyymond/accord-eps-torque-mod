import sys; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import numpy as np, s3turns as T, v282cmp as V
from scipy import signal
for rk in ['0000006c--2bc842dbac','00000075--6c8687d5bd','0000006e--6ca3e014fd']:
    R=T.prep(rk); u=R['active']&~R['pressed']&(R['v']>=2.5)&(R['v']<8)
    X=Y=XY=0; n=0
    for a,b in V.runs(u,R['t'],min_s=5.12):
        x=V.deriv(R['ad'][a:b]); y=R['sr'][a:b]
        f,p=signal.welch(x,100,nperseg=512); _,q=signal.welch(y,100,nperseg=512); _,c=signal.csd(x,y,100,nperseg=512)
        X=X+p*(b-a); Y=Y+q*(b-a); XY=XY+c*(b-a); n+=b-a
    m=(f>=0.5)&(f<=6)
    print(rk,R['group'],'sec',n/100)
    for fi,px,py,cxy in zip(f[m],X[m]/n,Y[m]/n,XY[m]/n):
        print(f"   {fi:4.2f} des {px:8.1f} meas {py:8.1f} coh {abs(cxy)**2/(px*py):.2f} phase(meas-des) {np.degrees(np.angle(cxy)):+5.0f}")
    del R
