"""My headline used cs_la_des = pid_log.desiredLateralAccel, which the instr stream showed is the
SHAPED setpoint (post delay-compensation, post the two Accord ref-filter poles), not the model's
demand. The goal says "match the MODEL's desired lateral acceleration".

Redo it against the model reference (cs_des_curv * v^2) and report BOTH, so the shaping stage's
own contribution is visible as the difference.
"""
import math, numpy as np
from scipy import signal
CA='analysis-2020accord/_scratch/cache/tau/'
BANDS=[('SLOW  0.05-0.15',0.05,0.15,60.),('MID   0.15-0.30',0.15,0.30,40.),
       ('FINE  0.30-0.60',0.30,0.60,24.),('TRANS 0.60-1.20',0.60,1.20,12.)]
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    v=np.interp(t,D['t_cst'],D['vego'])
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),v=v,
                pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                setpt=D['cs_la_des'], model=D['cs_des_curv']*v*v, laa=D['cs_la_act'])
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); C=load('r76_v293_ident.npz')
FS=A['FS']
def segs(sets,vlo,vhi,ml,xk,yk):
    out=[]
    for S in sets:
        t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi); n,i=len(m),0
        while i<n:
            if not m[i]: i+=1; continue
            j=i
            while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
            if (j+1-i)/FS>=ml: out.append((S[xk][i:j+1],S[yk][i:j+1]))
            i=j+1
    return out
def band(sg,f1,f2):
    if not sg: return None
    nps=int(2**np.floor(np.log2(min(len(x) for x,_ in sg))))
    if nps<64: return None
    Pxx=Pyy=Pxy=None; fr=None; sec=0
    for x,y in sg:
        xs,ys=x-x.mean(),y-y.mean()
        f,pxx=signal.welch(xs,FS,nperseg=nps,noverlap=nps//2)
        _,pyy=signal.welch(ys,FS,nperseg=nps,noverlap=nps//2)
        _,pxy=signal.csd(xs,ys,FS,nperseg=nps,noverlap=nps//2)
        w=len(xs); Pxx=pxx*w if Pxx is None else Pxx+pxx*w
        Pyy=pyy*w if Pyy is None else Pyy+pyy*w; Pxy=pxy*w if Pxy is None else Pxy+pxy*w
        fr=f; sec+=w/FS
    s=(fr>=f1)&(fr<f2)
    if s.sum()<2: return None
    Hf=np.abs(Pxy[s])/np.maximum(Pxx[s],1e-30)
    coh=np.abs(Pxy[s])**2/np.maximum(Pxx[s]*Pyy[s],1e-30)
    return float(np.average(Hf,weights=Pxx[s])), float(np.average(coh,weights=Pxx[s])), sec, len(sg)

print("="*104)
print("SANITY: does cs_des_curv * v^2 actually differ from cs_la_des?  (if identical, the caveat is moot)")
print("="*104)
for tag,S in [('6c',A),('6d',B),('76',C)]:
    m=S['act']&~S['pr']&(S['v']>15)
    r=np.corrcoef(S['setpt'][m],S['model'][m])[0,1]
    sl=float(np.dot(S['model'][m],S['setpt'][m])/np.dot(S['model'][m],S['model'][m]))
    print(f"  {tag}: corr(setpoint, model) = {r:.4f}   slope setpoint/model = {sl:.3f}   "
          f"rms model {np.std(S['model'][m]):.3f}  rms setpoint {np.std(S['setpt'][m]):.3f}")

print()
print("="*104)
print("THE GOAL, BOTH REFERENCES.  |H| = 1.000 is a perfect match.  Highway 15-34 m/s.")
print("="*104)
for tag,sets in [('REV 6.4 (6c+6d)',[A,B]),('REV 5 (route 76)',[C])]:
    print(f"\n  {tag}")
    print(f"    {'band':>16} | {'vs SHAPED SETPOINT':^26} | {'vs MODEL DEMAND':^26}")
    print(f"    {'':>16} | {'|H|':>7} {'coh':>6} {'s':>5} {'n':>4} | {'|H|':>7} {'coh':>6} {'s':>5} {'n':>4}")
    for name,f1,f2,ml in BANDS:
        rs=band(segs(sets,15.,34.,ml,'setpt','laa'),f1,f2)
        rm=band(segs(sets,15.,34.,ml,'model','laa'),f1,f2)
        c1=f"{rs[0]:7.3f} {rs[1]:6.3f} {rs[2]:5.0f} {rs[3]:4d}" if rs else f"{'--':>7} {'--':>6} {'--':>5} {'--':>4}"
        c2=f"{rm[0]:7.3f} {rm[1]:6.3f} {rm[2]:5.0f} {rm[3]:4d}" if rm else f"{'--':>7} {'--':>6} {'--':>5} {'--':>4}"
        print(f"    {name:>16} | {c1} | {c2}")

print()
print("="*104)
print("THE SHAPING STAGE ITSELF:  model -> setpoint  (should be ~1.0 below 1 Hz 'by design')")
print("="*104)
for tag,sets in [('REV 6.4',[A,B]),('REV 5',[C])]:
    print(f"\n  {tag}")
    print(f"    {'band':>16} {'|H|':>8} {'coh':>7}   (1.000 = the shaping is transparent in this band)")
    for name,f1,f2,ml in BANDS:
        r=band(segs(sets,15.,34.,ml,'model','setpt'),f1,f2)
        if r: print(f"    {name:>16} {r[0]:8.3f} {r[1]:7.3f}")
