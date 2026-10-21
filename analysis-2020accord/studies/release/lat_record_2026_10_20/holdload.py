# Lane tap (T = 8*field) vs |wheel angle| in quasi-static engaged hands-off holds, by speed band. V298 r79, V299 r9c/r9d.
import numpy as np, time
t0=time.time()
C="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280/"
import sys
TQ=float(sys.argv[1])
R=[("r79","r79_a1f5d2_al.npz"),("r9c","r9c_7f2f4d_al.npz"),("r9d","r9d_371ec9_al.npz")]
for nm,f in R:
    W=np.load(C+f)
    t=W["t18"]
    ang=np.interp(t,W["t14"],W["ang"])
    w=-W["rate"]/8.0
    tq=W["tq"]/1.024                               # raw counts
    fld=((np.interp(t,W["t1ab"],W["b0"]).astype(int)&3)<<8)|np.interp(t,W["t1ab"],W["b1"]).astype(int)
    # nearest-sample for bytes:
    k=np.clip(np.searchsorted(W["t1ab"],t)-1,0,len(W["t1ab"])-1)
    fld=((W["b0"][k].astype(int)&3)<<8)|W["b1"][k].astype(int)
    T=np.where(fld>=512,-1.0,1.0)*(fld&511)*8.0
    v=np.interp(t,W["tcs"],W["vego"])
    ke=np.clip(np.searchsorted(W["te4"],t)-1,0,len(W["te4"])-1)
    req=W["req"][ke]; cmd=W["cmd"][ke]; sp=-cmd/10.0
    eng=(req==1)&(W["sca"]==1)
    qs=(np.abs(w)<15)&(np.abs(tq)<TQ)&eng
    print(f"== {nm}: engaged {eng.mean()*100:.1f}% frames, quasi-static hands-off {qs.sum()} frames")
    print("  v band | |ang| bin | n | |T| p50 / p90 (lane counts) | %rail p90 | |sp-ang| p50")
    for vlo,vhi in [(0,3),(3,6),(6,9),(9,12.5)]:
        for alo,ahi in [(30,90),(90,180),(180,270),(270,360),(360,450)]:
            m=qs&(v>=vlo)&(v<vhi)&(np.abs(ang)>=alo)&(np.abs(ang)<ahi)
            if m.sum()<20: continue
            a=np.abs(T[m]); e=np.abs(sp[m]-ang[m])
            print(f"  {vlo:>4}-{vhi:<4} | {alo:>3}-{ahi:<3} | {m.sum():5d} | {np.percentile(a,50):6.0f} / {np.percentile(a,90):6.0f} | {np.percentile(a,90)/2461*100:5.1f} | {np.percentile(e,50):5.1f}")
print(f"{time.time()-t0:.1f} s")
