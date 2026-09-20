import sys
sys.path.insert(0, "C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/a_stickslip")
from ss_load import load_all
from sslib import k_of_v
import numpy as np

EP, W, EX, VAL = load_all()
col = lambda k: np.array([e[k] for e in EP])
g = col('group'); v = col('v'); route = col('route'); slip = col('slip'); aa_abs = col('abs_aa')
TQ = np.isin(g, ['T64', 'T64B', 'T5', 'T4'])

for lo,hi in [(2,8)]:
    m = TQ & (v>=lo)&(v<hi)
    kk = k_of_v(v[m])
    print("pooled corr slip vs |aa|:", np.corrcoef(slip[m], aa_abs[m])[0,1])
    print("pooled corr slip vs 1/k:", np.corrcoef(slip[m], 1/kk)[0,1])
    # within-route demeaned (fixed-effects) correlation
    rr = route[m]; s = slip[m].copy(); a = aa_abs[m].copy(); invk = (1/kk).copy()
    for rt in np.unique(rr):
        sel = rr==rt
        s[sel] -= s[sel].mean(); a[sel] -= a[sel].mean(); invk[sel] -= invk[sel].mean()
    print("within-route (demeaned) corr slip vs |aa|:", np.corrcoef(s,a)[0,1])
    print("within-route (demeaned) corr slip vs 1/k:", np.corrcoef(s,invk)[0,1])
    # route-cluster bootstrap CI for corr slip vs |aa|
    u = np.unique(rr); rng=np.random.default_rng(4); idx={c:np.where(rr==c)[0] for c in u}
    bs=[]
    for _ in range(3000):
        pick = rng.choice(u,len(u))
        ii = np.concatenate([idx[c] for c in pick])
        if len(np.unique(ii))>3:
            bs.append(np.corrcoef(slip[m][ii], aa_abs[m][ii])[0,1])
    bs=np.array(bs)
    print("corr(slip,|aa|) boot CI:", np.percentile(bs,[2.5,97.5]))
    bs2=[]
    for _ in range(3000):
        pick = rng.choice(u,len(u))
        ii = np.concatenate([idx[c] for c in pick])
        if len(np.unique(ii))>3:
            bs2.append(np.corrcoef(slip[m][ii], 1/kk[[np.where(m)[0].tolist().index(x) if False else 0 for x in []]] if False else (1/k_of_v(v[m][ii])))[0,1])
    # simpler recompute
    bs2=[]
    vmm = v[m]
    for _ in range(3000):
        pick = rng.choice(u,len(u))
        ii = np.concatenate([idx[c] for c in pick])
        if len(np.unique(ii))>3:
            kkk = k_of_v(vmm[ii])
            bs2.append(np.corrcoef(slip[m][ii], 1/kkk)[0,1])
    bs2=np.array(bs2)
    print("corr(slip,1/k) boot CI:", np.percentile(bs2,[2.5,97.5]))
