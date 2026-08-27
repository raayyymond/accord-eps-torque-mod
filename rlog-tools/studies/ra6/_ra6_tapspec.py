r"""TAP SCALER SIZING + the RESHAPE duty table on route a6's OWN alpha, per-frame after LERP."""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "analysis-2020accord"))
import _gate2_boost_lib as L
try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
KPH, FS, CLAMP = 3.6, L.FS, 511.0
CNT_PER_KPH = 64.0
Y_STOCK = np.array([-9830.0, -5734.0, -1966.0]); X_CNT = np.array([0.0, 1280.0, 5760.0])
C2C_PER_B26 = 2**24/273.0
def yl(v, Y): return np.abs(np.interp(np.asarray(v,float)*CNT_PER_KPH, X_CNT, np.asarray(Y,float)))
OUT = {}

# ---- measured |c2c| pool, r77 + r78 engaged, for the scaler sizing
pool = []
for tag, dose, wsc in (('r77',1.0,1.6), ('r78',1.5,1.6)):
    d = L.load(tag)
    mt=np.asarray(d['ab_mt'],float); abt=np.asarray(d['ab_t1ab'],float); t=np.asarray(d['t'],float)
    j=np.clip(np.searchsorted(abt,t,side='right')-1,0,len(mt)-1)
    b26=mt[j]*wsc
    e=np.asarray(d['cc_lat'],float)>0.5
    v=(np.asarray(d['v_rear'],float) if 'v_rear' in d.files else 0.5*(np.asarray(d['ws_rl'],float)+np.asarray(d['ws_rr'],float)))*KPH
    c2c = b26*C2C_PER_B26/np.maximum(yl(v, Y_STOCK*dose),1.0)
    pool.append(c2c[e])
P = np.concatenate(pool)
print("="*110); print("1.  TAP SCALER SIZING for `gp-0x6c2c` on the 0x18F 10-bit lane (0..1023 unsigned).")
print("    Pool = r77 + r78 engaged, MEASURED, n = %d frames.  corpus max %.0f" % (len(P), P.max()))
print("="*110)
print("%8s %10s %12s %14s %16s %14s" % ('shift','LSB cnt','full scale','clip frac','clip frac p99.9','p99 in LSBs'))
for sh in (1,2,3,4,5):
    lsb = float(2**sh); fs_ = 1023*lsb
    print("%8s %10.0f %12.0f %14.6f %16s %14.1f"
          % ("sar %d"%sh, lsb, fs_, float(np.mean(P>=fs_)),
             "%.6f"%float(np.mean(P[P>=np.percentile(P,99.9)]>=fs_)), np.percentile(P,99)/lsb))
    OUT.setdefault('scaler',{})["sar %d"%sh]=dict(lsb=lsb, full_scale=fs_,
        clip=float(np.mean(P>=fs_)), p99_lsbs=float(np.percentile(P,99)/lsb))
print("  percentiles of measured |gp-0x6c2c| (engaged, r77+r78): p50 %.0f  p90 %.0f  p99 %.0f  p99.9 %.0f  max %.0f"
      % tuple(np.percentile(P,[50,90,99,99.9]).tolist()+[P.max()]))
OUT['c2c_pool']=dict(n=int(len(P)), **{("p%g"%p): float(np.percentile(P,p)) for p in (50,90,99,99.9)}, mx=float(P.max()))

# ---- RESHAPE duty on route a6's OWN alpha, evaluated per-frame after LERP
print(); print("="*110)
print("2.  RESHAPE DUTY ON ROUTE a6's OWN ENGAGED ALPHA -- per-frame delivered coefficient after")
print("    LERP (NOT a uniform stock-relative k).  Same held-out-validated law + residual spread.")
print("="*110)
d6=L.load('ra6'); e6=np.asarray(d6['cc_lat'],float)>0.5
v6=np.asarray(d6['v_rear'],float)*KPH
rf6=np.asarray(d6['rate_f'],float); kk=int(round(0.05*FS))|1
a6=np.convolve(np.abs(np.gradient(rf6)*FS), np.ones(kk)/kk, mode='same')
d7=L.load('r77'); mt=np.asarray(d7['ab_mt'],float); abt=np.asarray(d7['ab_t1ab'],float); t7=np.asarray(d7['t'],float)
j7=np.clip(np.searchsorted(abt,t7,side='right')-1,0,len(mt)-1); b77=mt[j7]*1.6
e7=np.asarray(d7['cc_lat'],float)>0.5
v7=(np.asarray(d7['v_rear'],float) if 'v_rear' in d7.files else 0.5*(np.asarray(d7['ws_rl'],float)+np.asarray(d7['ws_rr'],float)))*KPH
rf7=np.asarray(d7['rate_f'],float); a7=np.convolve(np.abs(np.gradient(rf7)*FS), np.ones(kk)/kk, mode='same')
Y7=yl(v7, Y_STOCK)
m=e7&(b77>0)&(a7>0)
lhs=np.log(b77[m])-np.log(Y7[m])
sl,ic=np.polyfit(np.log(a7[m]),lhs,1); res=lhs-(sl*np.log(a7[m])+ic)
print("  law (pure-LERP form): log(|b26|/Y_eff) = %.4f*log(alpha) %+.4f   resid sd %.3f" % (sl,ic,res.std()))
rg=np.random.default_rng(17); NS=12
base=np.exp(sl*np.log(np.clip(a6,1e-6,None))[None,:]+ic+rg.choice(res,(NS,len(a6))))
RES={'V106 today':(-29490.,-17202.,-5898.),'RESHAPE A':(-29490.,-29490.,-29490.),
     'RESHAPE B':(-29490.,-24000.,-16000.),'RESHAPE C':(-29490.,-29490.,-20000.)}
BANDS=[('40-70',40,70),('>=70',70,1e9),('<16',0,16)]
print("%14s %8s %9s %9s %9s %9s %9s %13s" % ('variant','speed','n','p50','p90','p99','max','duty>=511'))
for nm,Y in RES.items():
    Ye=yl(v6,Y)
    pred=base*Ye[None,:]
    for lbl,lo,hi in BANDS:
        mm=e6&(v6>=lo)&(v6<hi)
        if mm.sum()<200: continue
        X=pred[:,mm]
        print("%14s %8s %9d %9.1f %9.1f %9.1f %9.1f %13.5f"
              % (nm,lbl,int(mm.sum()),*[np.percentile(X,p) for p in (50,90,99)],X.max(),float(np.mean(X>=CLAMP))))
        OUT.setdefault('reshape_a6',{}).setdefault(nm,{})[lbl]=dict(n=int(mm.sum()),
            duty511=float(np.mean(X>=CLAMP)), **{("p%g"%p): float(np.percentile(X,p)) for p in (50,90,99)})
json.dump(OUT, open(os.path.join(ROOT,'analysis-2020accord','_scratch/out/_ra6_tapspec.json'),'w'), indent=1, default=float)
print("\nwrote analysis-2020accord/_scratch/out/_ra6_tapspec.json")
