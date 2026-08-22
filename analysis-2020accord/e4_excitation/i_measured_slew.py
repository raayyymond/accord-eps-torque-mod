import sys, numpy as np
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
for r in ["73","75","76"]:
    t,e4,y,m,meta=M.load(r)
    eng=m["eng"]
    d=np.diff(e4); dt=np.diff(t); ok=eng[1:]&(dt>0.005)&(dt<0.015)
    rate=np.abs(d[ok]/dt[ok])
    step=np.abs(d[ok])
    print("route %s  |de4| per ~10ms frame: p50 %.1f p99 %.1f max %.1f  | implied ct/s p99 %.0f max %.0f  | frac(step>3.5) %.5f"%(
        r,np.percentile(step,50),np.percentile(step,99),step.max(),np.percentile(rate,99),rate.max(),(step>3.5).mean()))
