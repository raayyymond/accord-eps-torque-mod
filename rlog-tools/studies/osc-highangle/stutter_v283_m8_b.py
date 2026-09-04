import os,sys,numpy as np
H=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,H)
import stutter_v283 as SV, strongturn_r32_r33 as ST
V,FS,CPD=SV.V,SV.FS,SV.CPD
R4=("r35","r36","r37","r38")
SH={"r35":0.57*np.exp(1j*np.radians(104.)),"r36":0.69*np.exp(1j*np.radians(85.)),
    "r37":0.47*np.exp(1j*np.radians(99.)),"r38":0.42*np.exp(1j*np.radians(95.))}
L0=0.90
rt={t:V.Route(t) for t in R4}
eps=[]
for t in R4:
    r=rt[t]
    for e in ST.fixed_thr_episodes(r,thr=60):
        if e["ang"]>=30 and e["fdom"]>=6: eps.append((t,r.idx[int(e["t0"]*FS):int((e["t0"]+e["dur"])*FS)]))
r=rt["r35"];S=SV.sim_ki(r,*SV.V280R2,kpY=np.full(5,248.),ki=0)
ref=S["ref_deg"][r.i100];w=np.abs(r.wire)/CPD
st=r.eng&(np.abs(r.ang)>=30)&(r.idx>=40)&(r.idx<=200)&(np.abs(r.tq_raw)<1216)&(ref>5)&(w<0.5*ref)
sti=r.idx[st]
lt=lambda X,Y,i: np.interp(np.asarray(i,float),np.asarray(X,float),np.asarray(Y,float))
def sc(X,Y):
    ben=float(lt(X,Y,sti).mean()/248.)
    wv,wt=0.,""
    for t,ix in eps:
        v=abs(SH[t]*(float(lt(X,Y,ix).mean())/248.)+(1-SH[t]))*L0
        if v>wv: wv,wt=v,t
    return ben,wv,wt
print("RESTRICTED SEARCH: a >= 32, so idx 0-32 stays EXACTLY 248 (the unmeasured 12-32 band untouched).")
print(" %8s %8s %6s | %-26s %5s"%("benefit","ring max","route","X","K"))
c=[]
for a in (32,36,40):
    for b in range(a+4,129,4):
        for cc in range(b+4,177,4):
            for d in range(cc+4,233,4):
                for K in (341,380,420,460,512,560,645):
                    X=[0,a,b,cc,d];Y=[248,248,K,K,248]
                    ben,wv,wt=sc(X,Y); c.append((ben,wv,wt,tuple(X),K))
print("  searched",len(c))
for lim in (0.93,0.94,0.95,0.96,0.97,0.98,0.99,0.999):
    p=[x for x in c if x[1]<=lim]
    if not p: continue
    bb=max(p,key=lambda z:z[0])
    print(" %8.3f %8.3f %6s | %-26s %5d   (<= %.3f)"%(bb[0],bb[1],bb[2],str(list(bb[3])),bb[4],lim))
print()
print("For reference, the same margin ladder with a >= 16 (touches idx 16-32):")
c2=[]
for a in (16,20,24,28):
    for b in range(a+4,129,4):
        for cc in range(b+4,177,4):
            for d in range(cc+4,233,4):
                for K in (341,420,512,645):
                    X=[0,a,b,cc,d];Y=[248,248,K,K,248]
                    ben,wv,wt=sc(X,Y); c2.append((ben,wv,wt,tuple(X),K))
for lim in (0.94,0.96,0.98,0.999):
    p=[x for x in c2 if x[1]<=lim]
    if not p: continue
    bb=max(p,key=lambda z:z[0])
    print(" %8.3f %8.3f %6s | %-26s %5d   (<= %.3f)"%(bb[0],bb[1],bb[2],str(list(bb[3])),bb[4],lim))
