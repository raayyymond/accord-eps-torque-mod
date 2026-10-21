# Band energy of the 0x18F torque-sensor signal (100 Hz) in 1-s windows at v < 6 m/s, by hand state x engagement.
# Grind #1 lives at 18-22 Hz, grind #2 aliases into 40-49 Hz on this grid. V298 r79 vs V299 r9c/r9d.
import numpy as np, time
from scipy import signal
t0=time.time()
C="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280/"
R=[("r79 V298","r79_a1f5d2_al.npz"),("r9c V299","r9c_7f2f4d_al.npz"),("r9d V299","r9d_371ec9_al.npz")]
bands=[(5,9),(15,25),(35,50)]
for nm,f in R:
    W=np.load(C+f); t=W["t18"]; tq=W["tq"]/1.024
    v=np.interp(t,W["tcs"],W["vego"]); ke=np.clip(np.searchsorted(W["te4"],t)-1,0,len(W["te4"])-1)
    eng=(W["req"][ke]==1)&(W["sca"]==1)
    ang=np.interp(t,W["t14"],W["ang"]); w=-W["rate"]/8.0
    hp=signal.sosfiltfilt(signal.butter(4,4,'hp',fs=100,output='sos'),tq)
    N=len(t)//100
    rows={}
    for i in range(N):
        s=slice(i*100,(i+1)*100)
        if v[s].max()>=6: continue
        e=eng[s].mean()>0.95; d=eng[s].mean()<0.05
        if not (e or d): continue
        h=np.median(np.abs(tq[s])); hand = 'on' if h>600 else ('off' if h<300 else None)
        if hand is None: continue
        turning = np.median(np.abs(w[s]))>30
        f,P=signal.periodogram(hp[s],fs=100,window='hann')
        bp=[np.sqrt(P[(f>=a)&(f<b)].sum()) for a,b in bands]
        rows.setdefault(('eng' if e else 'dis',hand,'turn' if turning else 'still'),[]).append(bp)
    print(f"== {nm}")
    for k in sorted(rows):
        a=np.array(rows[k])
        print(f"  {k[0]:>3} hands-{k[1]:<3} {k[2]:<5} n={len(a):4d}  rms 5-9 / 15-25 / 35-50 Hz  p50 "+
              " / ".join(f"{x:5.1f}" for x in np.median(a,0))+"   p95 "+" / ".join(f"{x:5.1f}" for x in np.percentile(a,95,0)))
print(f"{time.time()-t0:.1f} s")
