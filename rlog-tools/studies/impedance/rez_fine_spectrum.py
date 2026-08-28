import numpy as np
from scipy import signal
from numpy.lib.stride_tricks import sliding_window_view
FS=100.0
def stack(routes):
    X=[];Y=[]
    for r in routes:
        z=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
        G=lambda k:np.asarray(z[k]).astype(float)
        rate,tq,lat,v=[G(k) for k in ('cs_rate','cs_tq','cc_lat','cs_v')]
        w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
        med=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]
        m=(lat>0.5)&(med<1200)&(v>1.0)
        X.append(np.nan_to_num(np.where(m,rate,0.))); Y.append(np.nan_to_num(np.where(m,tq,0.)))
    return np.concatenate(X),np.concatenate(Y)
x,y=stack(['22','23'])
f,Pxy=signal.csd(x,y,FS,nperseg=2048,noverlap=1536)
_,Pxx=signal.welch(x,FS,nperseg=2048,noverlap=1536)
_,Pyy=signal.welch(y,FS,nperseg=2048,noverlap=1536)
H=Pxy/np.maximum(Pxx,1e-30); C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
print("FINE Re(Z) SPECTRUM, V112 (routes 22+23 pooled), engaged + low-torque + moving")
print("0.049 Hz resolution, 20.5 s windows.  Negative = the loop PUTS ENERGY IN.\n")
print("   Hz     Re(Z)    coh2   |  Hz     Re(Z)    coh2   |  Hz     Re(Z)    coh2")
sel=(f>=2)&(f<=34)
ff=f[sel]; hh=H[sel].real; cc=C[sel]
# average into 0.5 Hz bins for legibility
edges=np.arange(2,34.01,0.5)
rows=[]
for i in range(len(edges)-1):
    b=(ff>=edges[i])&(ff<edges[i+1])
    if b.any(): rows.append((edges[i],np.mean(hh[b]),np.mean(cc[b])))
for i in range(0,len(rows),3):
    line=""
    for j in range(3):
        if i+j<len(rows):
            a,v,c=rows[i+j]
            line+="  %5.1f %8.0f  %.3f  |"%(a,v,c)
    print(line.rstrip('|'))
mn=min(rows,key=lambda r:r[1])
print("\n  MOST ANTI-DAMPED 0.5 Hz bin: %.1f Hz at Re(Z) = %.0f (coh2 %.3f)"%mn)
neg=[r for r in rows if r[1]<0]
print("  anti-damped span: %.1f - %.1f Hz"%(min(r[0] for r in neg),max(r[0] for r in neg)+0.5))
print("  zero crossing (f0): ", end="")
for i in range(len(rows)-1):
    if rows[i][1]<0<=rows[i+1][1]:
        print("%.2f Hz"%(rows[i][0]+0.5*(-rows[i][1])/(rows[i+1][1]-rows[i][1])),end="  ")
print()
print("\n  SYMPTOM FREQUENCIES:  peak-turn oscillation 7.42 Hz  |  grind #1 ~18-22 Hz (V62 record)")
for tgt in (7.42,8.0,12.0,18.0,20.0,22.0):
    k=int(np.argmin(np.abs(ff-tgt)))
    print("    %5.2f Hz -> Re(Z) %7.0f  coh2 %.3f"%(tgt,hh[k],cc[k]))
