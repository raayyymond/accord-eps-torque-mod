import sys,json,time
from pathlib import Path
from multiprocessing import Pool
H=Path(__file__).resolve().parent; sys.path.insert(0,str(H)); sys.path.insert(0,str(H.parents[1]/"c1"))
import c1_lib as C, c1_time as T1
HT=T1.HT
ROWS=[(C.make_table([(3.1,952),(8.0,1321),(10.0,855),(11.9,699),(15.5,1044),(26.9,2041)]),"B1",112,56,20,512,True,"freeze"),
      (C.make_table([(3.1,1106),(8.0,1475),(10.0,989),(11.9,826),(15.5,1213),(26.9,2241)]),"B2tbl-proxy",112,56,20,512,True,"freeze"),
      (C.make_table([(3.1,1690),(8.0,1805),(10.0,1357),(11.9,1162),(15.5,1366),(26.9,2765)]),"B3",112,0,20,0,False,"none")]
rw=[C.c1_row(t,l,kp_base=kp,ki_base=ki,kd=kd,thr=thr,rampfrz=rf,pol=pol) for t,l,kp,ki,kd,thr,rf,pol in ROWS]
SPD=(3.0,8.0,12.5,19.0); SCN=("rh","s02","s05","ssm","st","ov_latch","sen_L16")
def main():
    jobs=[(nm,v,rw,"bc","ff",{}) for v in SPD for nm in SCN]
    t0=time.time()
    with Pool(8) as p: res=list(p.map(T1.job,jobs))
    Tb=HT.table(res,rw)
    print(f"bc member ({time.time()-t0:.0f}s): per row&speed dj | stick% | hunt | tg0.2 | hold | ov_latch | sen")
    for v in SPD:
        if ("rh",v) not in Tb: continue
        rh,st,s02,s05,ssm=(Tb[(n,v)] for n in ("rh","st","s02","s05","ssm"))
        cells=[]
        for i in range(len(rw)):
            dj=s02["dj_events"][i]+s05["dj_events"][i]+ssm["dj_events"][i]+rh["hold_slips"][i]+st["hold_slips"][i]
            stick=max(s02["stick_pct"][i],s05["stick_pct"][i],ssm["stick_pct"][i])
            la=Tb[("ov_latch",v)]["lurch_overshoot"][i] if ("ov_latch",v) in Tb else float('nan')
            se=Tb[("sen_L16",v)]["sen_excursion"][i] if ("sen_L16",v) in Tb else float('nan')
            cells.append(f"{ROWS[i][1]} dj{dj:2.0f} stk{stick:3.0f}% h{max(rh['hunt_p2p'][i],st['hunt_p2p'][i]):4.2f} tg{s02['track_gain'][i]:4.2f} hold{rh['hold_ratio'][i]:4.2f} ov{la:5.2f} sen{se:3.1f}")
        print(f" v{v:4g}: "+" | ".join(cells))
if __name__=="__main__":
    main()
