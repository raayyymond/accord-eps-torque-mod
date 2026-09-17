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
u=V.usable(S,2.5,8.0)
segs=V.runs(u,S['t'],min_s=5.12)
a,b = segs[0]
x = V.deriv(ad[a:b])   # exact s3_refloop convention
print("segment len", b-a, "raw max|.|", np.max(np.abs(x)), "at idx", np.argmax(np.abs(x)))
print("first 5 samples of x:", x[:5])
print("last 5 samples of x:", x[-5:])

# Welch on this ONE segment alone (no other segments mixed in), exactly as s3_refloop does per-run before duration-weighted summing
f,p = signal.welch(x - x.mean(), V.FS, nperseg=512)
df = f[1]-f[0]
for lo,hi in [(1,2),(2,3)]:
    m=(f>=lo)&(f<hi)
    print(f"  this-segment-only welch band {lo}-{hi}: rms={np.sqrt(np.sum(p[m])*df):.2f}")

# Now what s3_refloop.py ACTUALLY reports is duration-weighted across BOTH segments of route 64 -- reproduce that
seg2a,seg2b = segs[1]
x2 = V.deriv(ad[seg2a:seg2b])
f2,p2 = signal.welch(x2-x2.mean(), V.FS, nperseg=512)
Xtot = p*(b-a) + p2*(seg2b-seg2a)
ntot = (b-a)+(seg2b-seg2a)
Xavg = Xtot/ntot
for lo,hi in [(1,2),(2,3)]:
    m=(f>=lo)&(f<hi)
    print(f"  duration-weighted BOTH segments band {lo}-{hi}: rms={np.sqrt(np.sum(Xavg[m])*df):.2f}   (should match s3_refloop.json: 2.99 / 2.82)")
