# -*- coding: utf-8 -*-
"""exp4a: FAST tracking scenarios (S-bend, small-signal dip, turn-hold) for Ki 36/40/44 vs C3-P(56) vs P2."""
import os,sys
from pathlib import Path
import numpy as np
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import rev2a_lane as RL
import c3nl_sim as S
import c3nl_lens as LN
S.Lane=RL.Rev2ALane
IMPLS=["C3-P","R1-P36","R1-P40","R1-P44","P2"]
MEMS=("nominal","bc","F_hi","b_lo*J_hi")
print("S-bend 0.1Hz slope (worst member over 15-17.5 m/s):",flush=True)
for name in ("scurve_1.5","scurve_2"):
    worst={im:9.0 for im in IMPLS}
    for mb in MEMS:
        cols=[dict(impl=i,member=mb,v=v) for v in [15.0,16.0,17.0,17.5] for i in IMPLS]
        scn,meta=LN.build(name,cols); r=S.run(cols,scn); m=LN.metrics(name,meta,r,cols)
        for k,c in enumerate(cols): worst[c["impl"]]=min(worst[c["impl"]],m["slope"][k])
    print(f"  {name}: "+" ".join(f"{im}:{worst[im]:.3f}" for im in IMPLS),flush=True)
print("small-signal in-phase gain, min over the 11-12.5 dip:",flush=True)
for name in ("small_0.5_0.2","small_0.3_0.1"):
    worst={im:9.0 for im in IMPLS}
    for mb in ("nominal","bc","F_hi"):
        cols=[dict(impl=i,member=mb,v=v) for v in [11.0,11.5,11.75,12.0,12.5] for i in IMPLS]
        scn,meta=LN.build(name,cols); r=S.run(cols,scn); m=LN.metrics(name,meta,r,cols)
        for k,c in enumerate(cols): worst[c["impl"]]=min(worst[c["impl"]],m["gain"][k])
    print(f"  {name}: "+" ".join(f"{im}:{worst[im]:.2f}" for im in IMPLS),flush=True)
print("turn-hold (const curve a_lat 2.0, settled wheel/ref), min over 8-22 m/s and members:",flush=True)
def turnhold(member,a):
    speeds=[8.0,10.0,12.5,15.0,18.0,22.0]
    cols=[dict(impl=i,member=member,v=v) for v in speeds for i in IMPLS]
    sp=np.array([LN.S.tgt_alat(c["v"],a) for c in cols])
    ref=lambda t: sp*np.interp(t,[0,0.5,2.0,999],[0,0,1,1])
    r=S.run(cols,S.Scn(dur=8.0,ref=ref)); th=r["th"].astype(float); hold=th[-1500:].mean(0)/sp
    out={}
    for k,c in enumerate(cols): out.setdefault(c["impl"],[]).append(hold[k])
    return out
for a in (1.5,2.0,2.5):
    agg={im:9.0 for im in IMPLS}
    for mb in MEMS:
        o=turnhold(mb,a)
        for im in IMPLS: agg[im]=min(agg[im],min(o[im]))
    print(f"  a_lat {a}: "+" ".join(f"{im}:{agg[im]:.3f}" for im in IMPLS),flush=True)
