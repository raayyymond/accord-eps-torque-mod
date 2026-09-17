import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

M = 3279*0.45359237+136.0; WB=2.83; AF=0.39*WB; AR=WB-AF; TSF=0.8467
_M0,_WB0=1326.+136.,2.70; _AF0=_WB0*0.4; _AR0=_WB0-_AF0
CF=192150*TSF*M/_M0*(AR/WB)/(_AR0/_WB0); CR=202500*TSF*M/_M0*(AF/WB)/(_AF0/_WB0)
SF=M*(CF*AF-CR*AR)/(WB**2*CF*CR); SR_FIX=16.33
def curv_to_angle(k,v): return -np.degrees(k*SR_FIX*WB*(1.0-SF*v**2))

rk='00000064--ce6b0b0ebb'
S=V.load(rk)
v=np.nan_to_num(S['v']); vv=np.maximum(v,0.5)
k_m=np.nan_to_num(S['model'])/vv**2
ad=curv_to_angle(k_m,v)
adr=V.deriv(ad)
u=V.usable(S,2.5,8.0)
segs=V.runs(u,S['t'],min_s=5.12)
a,b = segs[0]
x = adr[a:b]
print("segment len", b-a, "raw max|.|", np.max(np.abs(x)))
idx = np.argmax(np.abs(x))
print("spike at local idx", idx, "of", b-a, "value", x[idx], "neighbors", x[max(0,idx-3):idx+4])

f,p = signal.welch(x-x.mean(), V.FS, nperseg=512)
df = f[1]-f[0]
for lo,hi in [(1,2),(2,3),(0,50)]:
    m=(f>=lo)&(f<hi)
    print(f"welch band {lo}-{hi}: rms={np.sqrt(np.sum(p[m])*df):.2f}")

# time-domain: what is total variance of x, and how does it split by Parseval across the FULL welch band 0-50?
print("time-domain rms of (x-mean)", np.sqrt(np.mean((x-x.mean())**2)))

# how many welch sub-windows (nperseg=512, noverlap=256 default) does this segment produce, and where does idx fall?
nperseg=512; noverlap=256
starts = list(range(0, len(x)-nperseg+1, nperseg-noverlap))
print("n subwindows", len(starts), "starts", starts, "spike idx", idx)
