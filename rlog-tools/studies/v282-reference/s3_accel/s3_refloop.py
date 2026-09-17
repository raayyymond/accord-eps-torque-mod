"""Is the model's desired curvature DRIVEN BY the wheel at 1-3 Hz at low speed (reference in the loop)?
Per route, engaged hands-off 2.5-8 m/s runs >= 5.12 s: desired-angle-rate vs steering-rate cross spectrum.
Reports per 0.5 Hz band: desired rms, measured rms, coherence, phase(meas - des) [negative = wheel lags desired (normal);
positive/near 180 = wheel LEADS the desired, i.e. the desired is following the car]."""
import sys, json; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import numpy as np, s3turns as T, v282cmp as V
from scipy import signal
OUT='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel/out/'
res={}
for rk in V.ROUTES:
    R=T.prep(rk); u=R['active']&~R['pressed']&(R['v']>=2.5)&(R['v']<8)
    X=Y=XY=0; n=0
    for a,b in V.runs(u,R['t'],min_s=5.12):
        x=V.deriv(R['ad'][a:b]); y=R['sr'][a:b]
        f,p=signal.welch(x-x.mean(),100,nperseg=512); _,q=signal.welch(y-y.mean(),100,nperseg=512); _,c=signal.csd(x-x.mean(),y-y.mean(),100,nperseg=512)
        X=X+p*(b-a); Y=Y+q*(b-a); XY=XY+c*(b-a); n+=b-a
    if n==0: continue
    X,Y,XY=X/n,Y/n,XY/n; df=f[1]-f[0]; row={}
    line=f"{rk} {R['group']:7s} {n/100:5.0f}s"
    for lo,hi in [(0.3,1.0),(1.0,2.0),(2.0,3.0),(3.0,5.0)]:
        m=(f>=lo)&(f<hi)
        coh=float(np.abs(XY[m].sum())**2/(X[m].sum()*Y[m].sum()))
        ph=float(np.degrees(np.angle(XY[m].sum())))
        row[f"{lo}-{hi}"]=dict(des=float(np.sqrt(X[m].sum()*df)),meas=float(np.sqrt(Y[m].sum()*df)),coh=coh,phase=ph)
        line+=f" | {lo}-{hi}: des {row[f'{lo}-{hi}']['des']:5.1f} meas {row[f'{lo}-{hi}']['meas']:5.1f} coh {coh:.2f} ph {ph:+4.0f}"
    res[rk]=dict(group=R['group'],sec=n/100,bands=row); print(line,flush=True)
    del R
json.dump(res,open(OUT+'s3_refloop.json','w'),indent=1)
