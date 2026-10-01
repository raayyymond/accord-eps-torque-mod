# -*- coding: utf-8 -*-
"""b_time.py -- the TIME harness (harness_time.run/metrics, UNMODIFIED) on the three panel-B tables, nominal + bc.
Reuses c1_time's job/member/scoring; each row carries its own table/kp/ki/kd + the I freeze (512 + ramp).  B2's D is
the FRESH rate in firmware; the harness D acts on the 100 Hz held rate, so B2 here is run with held D at Kd20 as a
PROXY for the low-frequency operator metrics (dwell-then-jump, stick-slip, dead zone, hold, tracking) -- those are set
by the Kp/Ki schedule and the I freeze, which B2 shares; the fresh D only improves HF texture/damping (see the GATE-2
Re(T/w) table).  B3 has Ki=0 (no I, no freeze).  ANALYSIS ONLY.
usage: python b_time.py run   |   python b_time.py score"""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]/"c1"))
import c1_lib as C
import c1_time as T1
HT = T1.HT
SPEEDS = T1.SPEEDS
OUT = HERE.parents[3] / "_scratch" / "angle_loop" / "B-robust-margins"

ROWS = [
  (C.make_table([(3.1,952),(8.0,1321),(10.0,855),(11.9,699),(15.5,1044),(26.9,2041)]), "B1 held Kd20 Ki56 (freeze512+ramp)", 112,56,20,512,True,"freeze"),
  (C.make_table([(3.1,1106),(8.0,1475),(10.0,989),(11.9,826),(15.5,1213),(26.9,2241)]), "B2 table (freshD proxy=held20) Ki56", 112,56,20,512,True,"freeze"),
  (C.make_table([(3.1,1690),(8.0,1805),(10.0,1357),(11.9,1162),(15.5,1366),(26.9,2765)]), "B3 Ki0 held Kd20 (no I, no freeze)", 112,0,20,0,False,"none"),
]
def rows():
    r=[]
    for tbl,lab,kp,ki,kd,thr,rf,pol in ROWS:
        r.append(C.c1_row(tbl, lab, kp_base=kp, ki_base=ki, kd=kd, thr=thr, rampfrz=rf, pol=pol))
    return r

SUITES = {"nominal": dict(members=("nominal",), scen=HT.SCENARIOS, outer="ff"),
          "bc": dict(members=("bc",), scen=HT.SCENARIOS, outer="ff")}

def run():
    rw=rows()
    for suite,s in SUITES.items():
        jobs=[(nm,v,rw,m,s["outer"],{}) for m in s["members"] for v in SPEEDS for nm in s["scen"]]
        t0=time.time(); out=[]
        with Pool(14) as pool:
            for i,res in enumerate(pool.imap_unordered(T1.job,jobs)):
                out.append(res)
        (OUT/f"time_{suite}.json").write_text(json.dumps(dict(rows=rw,results=out)))
        print(f"{suite}: {len(out)} runs, {time.time()-t0:.0f}s")

def score():
    import math
    lines=[]
    for suite in ("nominal","bc"):
        d=json.loads((OUT/f"time_{suite}.json").read_text()); rw,res=d["rows"],d["results"]
        by={}
        for r in res: by.setdefault(r["member"],[]).append(r)
        for mem,rr in by.items():
            Tb=HT.table(rr,rw)
            lines.append(f"\n===== {suite} / member {mem}: per row&speed: dj | stick% | deadzone(hold hunt p2p deg) | tg0.2 | hold | ov_latch | sentinel exc")
            lines.append("  m/s  " + " || ".join(f"{r['label'][:30]:^32s}" for r in rw))
            tot=[0]*len(rw)
            for v in SPEEDS:
                if ("rh",v) not in Tb: continue
                rh,st,s02,s05,ssm=(Tb[(n,v)] for n in ("rh","st","s02","s05","ssm"))
                cells=[]
                for i in range(len(rw)):
                    dj=s02["dj_events"][i]+s05["dj_events"][i]+ssm["dj_events"][i]+rh["hold_slips"][i]+st["hold_slips"][i]
                    tot[i]+=dj
                    stick=max(s02["stick_pct"][i],s05["stick_pct"][i],ssm["stick_pct"][i])
                    la=Tb[("ov_latch",v)]["lurch_overshoot"][i] if ("ov_latch",v) in Tb else float('nan')
                    se=Tb[("sen_L16",v)]["sen_excursion"][i] if ("sen_L16",v) in Tb else float('nan')
                    cells.append(f"{dj:2.0f} {stick:3.0f}% {max(rh['hunt_p2p'][i],st['hunt_p2p'][i]):4.2f} {s02['track_gain'][i]:4.2f} {rh['hold_ratio'][i]:4.2f} {la:4.2f} {se:3.1f}")
                lines.append(f"  {v:4g}  " + " || ".join(f"{c:32s}" for c in cells))
            lines.append("  total dj: " + "  ".join(f"{r['label'][:20]}={t:.0f}" for r,t in zip(rw,tot)))
    txt="\n".join(lines)
    (HERE/"time_score.txt").write_text(txt,encoding="utf-8"); print(txt)

if __name__=="__main__":
    (run if sys.argv[1]=="run" else score)()
