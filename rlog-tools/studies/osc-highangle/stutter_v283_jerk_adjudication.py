# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_jerk_adjudication.py -- diff my S4 wheel-rate jerk against v283read s
d|tq_raw|/dt on matched gates, and correct the across-run-boundary derivative defect.  stutter283, 2026-09-03."""
import os,sys,numpy as np
H=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));sys.path.insert(0,H)
import stutter_v283 as SV
V,FS,CPD=SV.V,SV.FS,SV.CPD
R=("r35","r36","r37","r38"); rt={t:V.Route(t) for t in R}
def runs_of(m,n=100):
    d=np.diff(np.r_[0,m.astype(int),0])
    return [(a,b) for a,b in zip(np.flatnonzero(d==1),np.flatnonzero(d==-1)) if b-a>=n]
def p95_within(x,segs,q=95):
    """derivative taken WITHIN each contiguous run only -- never across a mask boundary"""
    d=[np.abs(np.diff(x[a:b]))*FS for a,b in segs if b-a>=2]
    return (float(np.percentile(np.concatenate(d),q)),len(np.concatenate(d))) if d else (np.nan,0)
def p95_naive(x,mask,q=95):
    return float(np.percentile(np.abs(np.diff(x[mask]))*FS,q))
GATES={
 "MINE  |tq|>=1216 & |ang|>=30 & v<=10 & runs>=1s": lambda r: r.eng&(np.abs(r.ang)>=30)&(r.vego<=10)&(np.abs(r.tq_raw)>=1216),
 "v283read-ish |tq|>=1000 & |ang|>=30       ": lambda r: r.eng&(np.abs(r.ang)>=30)&(np.abs(r.tq_raw)>=1000),
 "|tq|>=1000, no angle gate                 ": lambda r: r.eng&(np.abs(r.tq_raw)>=1000),
}
print("SIGNALS: wire = 0x18F wheel RATE (deg/s).  bar = |tq_raw| MAGNITUDE (raw, already x1.024).  tap = 427 delivered torque |T| (counts).")
print("All p95 of |d/dt|.  'naive' = np.diff over the boolean-masked array (diffs ACROSS run boundaries -- my original S4 code).")
print("'within' = derivative taken inside each contiguous run only.  Runs >= 1 s where the gate says so, else >= 2 samples.\n")
for gname,gf in GATES.items():
    need=1 if "runs>=1s" in gname else 2
    print("=== GATE: %s"%gname)
    print("   %-5s %7s | %-28s | %-28s | %-28s"%("route","secs","wire-rate jerk p95 deg/s^2","d|bar|/dt p95 raw/s","d|tap|/dt p95 counts/s"))
    base={}
    for t in R:
        r=rt[t]; m=gf(r); segs=runs_of(m,100 if need==1 else 2)
        if not segs: print("   %-5s  (none)"%t); continue
        n=sum(b-a for a,b in segs)
        wj,_=p95_within(r.wire/CPD,segs); wn=p95_naive(r.wire/CPD,m)
        bj,_=p95_within(np.abs(r.tq_raw),segs)
        tj,_=p95_within(np.abs(r.T_meas),segs)
        base[t]=(wj,bj,tj)
        d=lambda v,k: "" if t=="r35" else " (%+.0f%%)"%(100*(v/base["r35"][k]-1))
        print("   %-5s %7.1f | within %6.0f%-10s naive %6.0f | %6.0f%-12s | %6.0f%s"%(
            t,n/FS,wj,d(wj,0),wn,bj,d(bj,1),tj,d(tj,2)))
    print()
print("HANDS-LIGHT control gate (the 'micro-jerk 1167 -> 713/1283/863' row): |tq|<1216 & idx>=40 & |ang|>=30 & v<=10, runs>=1s")
print("   %-5s %7s | %-30s | %-24s"%("route","secs","wire-rate jerk p95","d|tap|/dt p95"))
b0=None
for t in R:
    r=rt[t]; m=r.eng&(np.abs(r.ang)>=30)&(r.vego<=10)&(np.abs(r.tq_raw)<1216)&(r.idx>=40); segs=runs_of(m,100)
    if not segs: continue
    wj,_=p95_within(r.wire/CPD,segs); wn=p95_naive(r.wire/CPD,m); tj,_=p95_within(np.abs(r.T_meas),segs)
    if b0 is None: b0=(wj,tj)
    print("   %-5s %7.1f | within %6.0f (%+5.0f%%)  naive %6.0f | %6.0f (%+5.0f%%)"%(
        t,sum(b-a for a,b in segs)/FS,wj,100*(wj/b0[0]-1),wn,tj,100*(tj/b0[1]-1)))
