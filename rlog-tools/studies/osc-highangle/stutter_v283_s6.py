# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283_s6.py -- de-confound PREREG-V282 statistic (D): 0x14A bit-6 duty BY |T| BIN
in the (D) mask, and the duty reweighted to r35's own |T| distribution.  Subagent stutter283, 2026-09-03."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stutter_v283 as SV
V, FS, CPD = SV.V, SV.FS, SV.CPD
L=[]
def pr(s=""):
    print(s, flush=True); L.append(s)
routes={t:V.Route(t) for t in SV.ROUTES}
b4s={t:SV.load_b4(t,routes[t]) for t in SV.ROUTES}
EDG=[0,300,600,900,1200,1600,4000]
pr("S6 -- DE-CONFOUNDING statistic (D).  V283's Ki raised |T| in exactly the frames (D) is read on, and (D) = P(|r24| >= |T|) falls")
pr("   mechanically when |T| rises.  Below: bit-6 duty BY |T| BIN in the (D) mask, and the duty REWEIGHTED to r35's |T| distribution")
pr("   on the same mask (i.e. what V283's comparator would read if its delivered torque were V281 rev 3's).  r35 itself carries the OLD")
pr("   bit-6 comparator (duty 0.000) so it gives the |T| WEIGHTS only, never a duty.")
w35=None
for tag in SV.ROUTES:
    r=routes[tag]; b4=b4s[tag]
    m=r.eng&(np.abs(r.ang)>=30)&(r.idx>=68)
    T=np.abs(r.T_meas[m]); bit=((b4[m]>>6)&1).astype(float)
    h,_=np.histogram(T,EDG); h=h/max(h.sum(),1)
    if tag=="r35": w35=h
    cells=[]; duty=[]
    for i in range(len(EDG)-1):
        s=(T>=EDG[i])&(T<EDG[i+1])
        d=float(bit[s].mean()) if s.sum()>=20 else np.nan
        duty.append(d)
        cells.append("%4d-%4d: n%5d duty %s"%(EDG[i],EDG[i+1],s.sum(),("%.3f"%d) if s.sum()>=20 else "  -- "))
    duty=np.array(duty)
    ok=np.isfinite(duty)&(w35>0)
    rw=float(np.sum(duty[ok]*w35[ok])/np.sum(w35[ok])) if ok.any() else np.nan
    pr("  %s n %5d  raw duty %.3f | %s"%(tag,m.sum(),float(bit.mean()),"  ".join(cells)))
    pr("       |T| p50 %4.0f p90 %4.0f | r35-|T|-REWEIGHTED bit6 duty %s (coverage of r35 weights %.2f)"%(
        np.median(T),np.percentile(T,90),("%.3f"%rw) if np.isfinite(rw) else "n/a",float(np.sum(w35[ok])) if ok.any() else 0.0))
open(os.path.join(HERE,"_scratch","stutter_v283_s6.txt"),"w",encoding="utf-8").write("\n".join(L)+"\n")
