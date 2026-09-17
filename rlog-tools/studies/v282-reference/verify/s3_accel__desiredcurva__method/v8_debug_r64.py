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
SOS = signal.butter(4,[1.0,3.0],btype='band',fs=V.FS,output='sos')

rk='00000064--ce6b0b0ebb'
S=V.load(rk)
v=np.nan_to_num(S['v']); vv=np.maximum(v,0.5)
k_m=np.nan_to_num(S['model'])/vv**2
ad=curv_to_angle(k_m,v)
adr=V.deriv(ad)
u=V.usable(S,2.5,8.0)
segs=V.runs(u,S['t'],min_s=5.12)
print("n segs", len(segs), [ (b-a) for a,b in segs])
for a,b in segs:
    x=adr[a:b]
    xb=signal.sosfiltfilt(SOS,x)
    print(f"seg len={b-a} raw_adr max|.|={np.max(np.abs(x)):8.1f} filt max|.|={np.max(np.abs(xb)):8.1f} filt_rms={np.sqrt(np.mean(xb**2)):7.2f} vmin={v[a:b].min():.2f} vmax={v[a:b].max():.2f}")
