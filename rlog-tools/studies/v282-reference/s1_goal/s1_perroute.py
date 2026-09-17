"""Per-route spectral |H| (model -> pose / act), speed >15 m/s pooled and per bin, bands 0.05-0.6 Hz. Split-half by segment order."""
import glob, json, numpy as np
from pathlib import Path
H='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/'
BA=["0.05-0.15","0.15-0.3","0.3-0.6"]
out=[]
def est(L,nm):
    Pxx=sum(s["Pxx"]*s["n"] for s in L); Pxy=sum(s["Pxy_"+nm]*s["n"] for s in L); Pyy=sum(s["Pyy_"+nm]*s["n"] for s in L)
    Hh=np.abs(Pxy)/Pxx; coh=np.abs(Pxy)**2/(Pxx*Pyy)
    return float(np.average(Hh,weights=Pxx)), float(np.average(coh,weights=Pxx)), float(np.degrees(np.angle(Pxy.sum())))
for f in sorted(glob.glob(H+"_red/*.npz")):
    D=np.load(f,allow_pickle=True); M=json.loads(str(D["meta"])); sp=list(D["specs"])
    for b in range(3):
        for vset,name in (((2,3),">15"),((3,),">22")):
            L=[s for s in sp if s["band"]==b and s["vb"] in vset]
            if not L: continue
            hp,cp,php=est(L,"pose"); ha,ca,pha=est(L,"act")
            h1=est(L[0::2],"pose")[0] if len(L)>1 else None; h2=est(L[1::2],"pose")[0] if len(L)>1 else None
            r=dict(route=M["route"],group=M["group"],band=BA[b],v=name,nseg=len(L),sec=sum(s["n"] for s in L)/100,
                   H_pose=hp,coh_pose=cp,ph_pose=php,H_act=ha,coh_act=ca,half_pose=[h1,h2],sR=M["sR"],lat_delay=M["lat_delay"])
            out.append(r)
            print(f"{M['group']:7s} {M['route']:22s} {name} {BA[b]:9s} pose {hp:.2f} (coh {cp:.2f}, half {h1 if h1 is None else round(h1,2)}/{h2 if h2 is None else round(h2,2)}) act {ha:.2f} sec {r['sec']:.0f} nseg {len(L)}")
    del D
json.dump(out,open(H+"s1_perroute.json","w"),indent=1)
