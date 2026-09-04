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
S0={t:SV.sim_ki(rt[t],*SV.V280R2,kpY=np.full(5,248.),ki=0) for t in R4}
stall={}
for t in R4:
    r=rt[t];ref=S0[t]["ref_deg"][r.i100];w=np.abs(r.wire)/CPD
    stall[t]=r.eng&(np.abs(r.ang)>=30)&(r.idx>=40)&(r.idx<=200)&(np.abs(r.tq_raw)<1216)&(ref>5)&(w<0.5*ref)
sti=rt["r35"].idx[stall["r35"]]
lt=lambda X,Y,i: np.interp(np.asarray(i,float),np.asarray(X,float),np.asarray(Y,float))
CAND=[("M1  flat 341",[0,68,112,136,208],[341]*5),
      ("M2  flat 400",[0,68,112,136,208],[400]*5),
      ("BAND Y-only",[0,68,112,136,208],[248,512,512,248,248]),
      ("M8-sketch  0,32,40,80,112 K420",[0,32,40,80,112],[248,248,420,420,248]),
      ("M8-cons 0,16,24,48,88 K512",[0,16,24,48,88],[248,248,512,512,248]),
      
      ("M8* 0,32,36,44,88 K512",[0,32,36,44,88],[248,248,512,512,248]),
      ("M8-alt 0,32,36,40,92 K512",[0,32,36,40,92],[248,248,512,512,248])]
print("%-32s | %5s %5s %5s %5s %5s %5s %5s | %7s | %-27s | %s"%("candidate","idx8","idx20","idx32","idx45","idx60","idx80","idx100","benefit","ring x0.90  r35   r36   r37   r38","worst"))
for nm,X,Y in CAND:
    ben=float(lt(X,Y,sti).mean()/248.)
    per={};wv,wt=0.,""
    for t,ix in eps:
        v=abs(SH[t]*(float(lt(X,Y,ix).mean())/248.)+(1-SH[t]))*L0
        per[t]=max(per.get(t,0.),v)
        if v>wv: wv,wt=v,t
    print("%-32s | %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f %5.0f | %7.3f | %-27s | %.3f %s"%(
        nm,*[lt(X,Y,i) for i in (8,20,32,45,60,80,100)],ben," ".join("%5.3f"%per.get(t,0) for t in R4),wv,wt))
print()
print("%-32s %-5s | %8s %8s %9s | %8s %8s"%("candidate","route","|P| p50","P-rail","sum-clamp","|T| p50","|T| stall"))
for nm,X,Y in CAND:
    for t in R4:
        r=rt[t];base=r.eng&(np.abs(r.ang)>=30)&(r.idx>=40)&(r.idx<=200)&(np.abs(r.tq_raw)<1216)
        kp=lt(X,Y,r.idx1k);E=S0[t]["E"]
        Pr=np.floor(E*kp/256);P=np.clip(Pr,-V.P_CLAMP,V.P_CLAMP)
        Dt=np.clip(S0[t]["D_raw"],-V.D_CLAMP,V.D_CLAMP)
        Sr=np.floor(V.SUM_MULT*(P+Dt)/256);Sc=np.clip(Sr,-V.SUM_CLAMP,V.SUM_CLAMP);Sc[~r.eng1k]=0.
        T=np.clip(np.floor(-V.output_lag(Sc)*V.GAIN/32768),-V.OUT_CAP,V.OUT_CAP)
        i=r.i100[base];isl=r.i100[stall[t]]
        print("%-32s %-5s | %8.0f %8.4f %9.4f | %8.0f %8.0f"%(nm if t=="r35" else "",t,
            np.median(np.abs(Pr[i])),float(np.mean(np.abs(Pr[i])>=V.P_CLAMP)),float(np.mean(np.abs(Sr[i])>=V.SUM_CLAMP)),
            np.median(np.abs(T[i])),np.median(np.abs(T[isl]))))
    print()
