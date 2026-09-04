import os,sys,numpy as np
H=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,H)
import stutter_v283 as SV, strongturn_r32_r33 as ST
V,FS,CPD=SV.V,SV.FS,SV.CPD
R4=("r35","r36","r37","r38")
SH={"r35":0.57*np.exp(1j*np.radians(104.)),"r36":0.69*np.exp(1j*np.radians(85.)),
    "r37":0.47*np.exp(1j*np.radians(99.)),"r38":0.42*np.exp(1j*np.radians(95.))}
L0=0.90
rt={t:V.Route(t) for t in R4}
S0={t:SV.sim_ki(rt[t],*SV.V280R2,kpY=np.full(5,248.),ki=0) for t in R4}
eps=[]
for t in R4:
    r=rt[t]
    for e in ST.fixed_thr_episodes(r,thr=60):
        if e["ang"]>=30 and e["fdom"]>=6: eps.append((t,float(np.mean(r.idx[int(e["t0"]*FS):int((e["t0"]+e["dur"])*FS)]))))
# P-rail evaluation points: strong-turn hands-light frames, 100 Hz sample of (|E|, idx)
EI={}
stall={}
for t in R4:
    r=rt[t];ref=S0[t]["ref_deg"][r.i100];w=np.abs(r.wire)/CPD
    base=r.eng&(np.abs(r.ang)>=30)&(r.idx>=40)&(r.idx<=200)&(np.abs(r.tq_raw)<1216)
    stall[t]=base&(ref>5)&(w<0.5*ref)
    EI[t]=(np.abs(S0[t]["E"][r.i100][base]),r.idx[base])
sti=rt["r35"].idx[stall["r35"]]
lt=lambda X,Y,i: np.interp(np.asarray(i,float),np.asarray(X,float),np.asarray(Y,float))
def full(X,Y):
    ben=float(lt(X,Y,sti).mean()/248.)
    wv,wt=0.,""
    for t,m in eps:
        v=abs(SH[t]*(float(lt(X,Y,[m])[0])/248.)+(1-SH[t]))*L0
        if v>wv: wv,wt=v,t
    pr=0.
    for t in R4:
        aE,ix=EI[t]
        pr=max(pr,float(np.mean(aE*lt(X,Y,ix)/256.>=V.P_CLAMP)))
    return ben,wv,wt,pr
print("SEARCH with the P-RAIL GATE in the objective.  a=32 (idx 0-32 exactly 248).")
print("Gate: worst-episode ring x0.90 <= 0.96  AND  max-over-routes P-rail duty <= 0.006 (M1 flat 341 reads 0.0032; V283 0.0017).")
print(" %8s %8s %8s %6s | %-26s %5s"%("benefit","ring","P-rail","route","X","K"))
best=None;rows=[]
for b in range(36,113,4):
    for c in range(b+4,161,4):
        for d in range(c+4,209,4):
            for K in (380,420,460,512,560,600,645):
                X=[0,32,b,c,d];Y=[248,248,K,K,248]
                ben,wv,wt,pr=full(X,Y)
                rows.append((ben,wv,wt,pr,tuple(X),K))
print("  searched",len(rows))
ok=[x for x in rows if x[1]<=0.96 and x[3]<=0.006]
print("  passing BOTH gates:",len(ok))
for lim in (0.003,0.004,0.005,0.006):
    p=[x for x in ok if x[3]<=lim]
    if not p: continue
    bb=max(p,key=lambda z:z[0])
    print(" %8.3f %8.3f %8.4f %6s | %-26s %5d   (P-rail <= %.3f)"%(bb[0],bb[1],bb[3],bb[2],str(list(bb[4])),bb[5],lim))
print()
print("  ... and relaxing the ring gate to 0.98 with P-rail <= 0.004:")
p=[x for x in rows if x[1]<=0.98 and x[3]<=0.004]
if p:
    bb=max(p,key=lambda z:z[0]);print(" %8.3f %8.3f %8.4f %6s | %-26s %5d"%(bb[0],bb[1],bb[3],bb[2],str(list(bb[4])),bb[5]))
print()
print("  named reference points under the same three metrics:")
for nm,X,Y in [("V283 flat 248",[0,68,112,136,208],[248]*5),("M1 flat 341",[0,68,112,136,208],[341]*5),
               ("M2 flat 400",[0,68,112,136,208],[400]*5),("BAND Y-only",[0,68,112,136,208],[248,512,512,248,248]),
               ("M8-sketch 0,32,40,80,112 K420",[0,32,40,80,112],[248,248,420,420,248]),
               ("M8-cons 0,16,24,48,88 K512",[0,16,24,48,88],[248,248,512,512,248])]:
    ben,wv,wt,pr=full(X,Y)
    print(" %8.3f %8.3f %8.4f %6s | %s"%(ben,wv,pr,wt,nm))
