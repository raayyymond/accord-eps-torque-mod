import sys; sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s3_accel')
import numpy as np, s3turns as T, v282cmp as V
from scipy import signal
for rk in ['0000006c--2bc842dbac','00000065--b9f78988bd','0000006e--6ca3e014fd','0000006d--05e83bb04f','00000075--6c8687d5bd']:
    R=T.prep(rk); u=R['active']&~R['pressed']
    t=R['t']; dt=np.diff(t)
    k=R['model']/np.maximum(R['v'],0.5)**2
    # how often does desired curvature change sample to sample
    ch=np.mean(np.abs(np.diff(k))>1e-7)
    out=[]
    for lo,hi in [(2.5,8),(8,15),(15,40)]:
        m=u&(R['v']>=lo)&(R['v']<hi)
        segs=V.runs(m,t,min_s=5.12)
        xx=0;yy=0;sec=0
        for a,b in segs:
            f,p=signal.welch(V.deriv(R['ad'][a:b]),100,nperseg=512); _,q=signal.welch(R['sr'][a:b],100,nperseg=512)
            xx=xx+p*(b-a); yy=yy+q*(b-a); sec+=b-a
        if sec==0: continue
        mm=(f>=1.5)&(f<6); df=f[1]-f[0]
        out.append(f"{lo}-{hi}: des {np.sqrt(np.sum(xx[mm]/sec)*df):5.1f} meas {np.sqrt(np.sum(yy[mm]/sec)*df):5.1f}")
    print(rk,R['group'],'dt med %.4f'%np.median(dt),'frac curv changes/sample %.2f'%ch,' | '.join(out))
    del R
