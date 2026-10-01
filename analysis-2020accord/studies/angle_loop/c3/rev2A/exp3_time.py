# -*- coding: utf-8 -*-
"""exp3_time.py -- rev2A time-domain re-score: N1 lurch (both directions), N5 reversal overshoot, N4 S-bend tracking,
N2/N3 small-signal in the dip, turn-hold at Ki18, F3 rate-invalid fault.  Columns C3-P (orig) vs R1-P (rev2A) vs P2."""
import os,sys
from pathlib import Path
import numpy as np
os.environ.setdefault("OPENBLAS_NUM_THREADS","1")
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE)); sys.path.insert(0,str(HERE.parents[1]/"refute_c3_nonlinear"))
import rev2a_lane as RL            # registers R1-*, defines Rev2ALane
import c3nl_sim as S
import c3nl_lens as LN
S.Lane=RL.Rev2ALane               # S.run now builds Rev2ALane (per-column cfg)

def runscn(name, impls, members, speeds, age=0):
    out={}
    for mb in members:
        cols=[dict(impl=i,member=mb,v=v,age=age) for v in speeds for i in impls]
        scn,meta=LN.build(name,cols)
        r=S.run(cols,scn)
        m=LN.metrics(name,meta,r,cols)
        # index helper
        idx={(i,v):k for k,(v,i) in enumerate([(v,i) for v in speeds for i in impls])}
        out[mb]=(m,idx)
    return out

IMPLS=["C3-P","R1-P","P2"]
SPD=[8.0,10.0,11.75,12.5,15.0,17.0,20.0,26.9]
MEMS=["nominal","bc","F_hi","b_lo*J_hi"]

print("================ N1: release lurch, OUTWARD hold 2*Ah 3s (word 511) -- the direction C3-P's theta-bound winds up")
for name in ("out_2_511_3",):
    R=runscn(name,IMPLS,MEMS,SPD)
    for mb in MEMS:
        m,idx=R[mb]
        print(f" {name} {mb}:")
        for v in SPD:
            vals={i:(m['over'][idx[(i,v)]],m['under'][idx[(i,v)]]) for i in IMPLS}
            print(f"   v{v:5}: C3-P over {vals['C3-P'][0]:5.1f}/und {vals['C3-P'][1]:4.1f}  R1-P over {vals['R1-P'][0]:5.1f}/und {vals['R1-P'][1]:4.1f}  P2 over {vals['P2'][0]:5.1f}/und {vals['P2'][1]:4.1f}")

print("\n================ N1: straight-road nudge 5deg 3s (word 511)")
for name in ("nudge_5_511_3",):
    R=runscn(name,IMPLS,["nominal","b_lo*J_hi"],SPD)
    for mb in ["nominal","b_lo*J_hi"]:
        m,idx=R[mb]; print(f" {name} {mb}: over-centre max by speed")
        print("   "+"  ".join(f"v{v}:C3P {m['over'][idx[('C3-P',v)]]:.1f}/R1 {m['over'][idx[('R1-P',v)]]:.1f}/P2 {m['over'][idx[('P2',v)]]:.1f}" for v in SPD))

print("\n================ N1 control: INWARD partial drag 0.5*Ah 3s (word 511) -- must stay bounded for all")
R=runscn("part_0.5_511_3",IMPLS,["b_lo*J_hi"],SPD)
m,idx=R["b_lo*J_hi"]
print("   "+"  ".join(f"v{v}:C3P {m['over'][idx[('C3-P',v)]]:.1f}/R1 {m['over'][idx[('R1-P',v)]]:.1f}/P2 {m['over'][idx[('P2',v)]]:.1f}" for v in SPD))

print("\n================ N5: held-turn REVERSAL overshoot (rev_2) ovs2 (fraction of A past the target)")
R=runscn("rev_2",IMPLS,["nominal","b_lo*J_hi"],[9.5,12.75,15.0,19.0])
for mb in ["nominal","b_lo*J_hi"]:
    m,idx=R[mb]; print(f" {mb}: "+"  ".join(f"v{v}:C3P {m['ovs2'][idx[('C3-P',v)]]:.2f}/R1 {m['ovs2'][idx[('R1-P',v)]]:.2f}/P2 {m['ovs2'][idx[('P2',v)]]:.2f}" for v in [9.5,12.75,15.0,19.0]))

print("\n================ N4: S-bend tracking slope (scurve_1.5), gated members")
R=runscn("scurve_1.5",IMPLS,["nominal","bc","b_lo*J_hi"],[15.0,16.0,17.0,17.5])
for mb in ["nominal","bc","b_lo*J_hi"]:
    m,idx=R[mb]; print(f" {mb}: "+"  ".join(f"v{v}:C3P {m['slope'][idx[('C3-P',v)]]:.3f}/R1 {m['slope'][idx[('R1-P',v)]]:.3f}/P2 {m['slope'][idx[('P2',v)]]:.3f}" for v in [15.0,16.0,17.0,17.5]))

print("\n================ N2/N3: small-signal in-phase gain, +-0.5deg 0.2Hz, the 11-12.5 window")
R=runscn("small_0.5_0.2",IMPLS,["nominal","bc","F_hi"],[11.25,11.5,11.75,12.0,12.25])
for mb in ["nominal","bc","F_hi"]:
    m,idx=R[mb]; print(f" {mb}: "+"  ".join(f"v{v}:C3P {m['gain'][idx[('C3-P',v)]]:.2f}/R1 {m['gain'][idx[('R1-P',v)]]:.2f}/P2 {m['gain'][idx[('P2',v)]]:.2f}" for v in [11.25,11.5,11.75,12.0,12.25]))
print("   dwell-jump events +-1deg 0.3Hz (small_1_0.3), 10-12.5 band sum:")
R=runscn("small_1_0.3",IMPLS,["nominal","bc","F_hi","b_lo*J_hi"],[10.0,10.5,11.0,11.5,12.0,12.5])
for mb in ["nominal","bc","F_hi","b_lo*J_hi"]:
    m,idx=R[mb]
    tot={i:int(sum(m['dj'][idx[(i,v)]] for v in [10.0,10.5,11.0,11.5,12.0,12.5])) for i in IMPLS}
    print(f"   {mb}: C3-P {tot['C3-P']}  R1-P {tot['R1-P']}  P2 {tot['P2']}")
