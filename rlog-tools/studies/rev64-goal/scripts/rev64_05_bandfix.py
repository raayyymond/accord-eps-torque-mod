"""Band metric done properly.

|sum(Sxy)|/sum(Sxx) averages a COMPLEX phasor across the band. Where phase rotates within the
band (high frequencies, transport delay 0.29 s), that cancels and biases |H| LOW. Fix: compute
H(f) per FFT bin, then average |H(f)| weighted by desired-signal power AND by coherence, and
report coherence so a low-coherence band can be discounted rather than believed.

Positive control and a delay negative control included; the delay control is the one that
exposes the bias, so it is the test that matters.
"""
import math, numpy as np
from scipy import signal
CA='analysis-2020accord/_scratch/cache/tau/'
BANDS=[('SLOW  0.05-0.15',0.05,0.15,60.),('MID   0.15-0.30',0.15,0.30,40.),
       ('FINE  0.30-0.60',0.30,0.60,24.),('TRANS 0.60-1.20',0.60,1.20,12.),('FAST  1.20-3.00',1.20,3.00,8.)]
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),
                v=np.interp(t,D['t_cst'],D['vego']),pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                lad=D['cs_la_des'],laa=D['cs_la_act'])
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); C=load('r76_v293_ident.npz')
FS=A['FS']
def segs_for(sets,vlo,vhi,minlen,ykey='laa'):
    out=[]
    for S in sets:
        t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi); n,i=len(m),0
        while i<n:
            if not m[i]: i+=1; continue
            j=i
            while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
            if (j+1-i)/FS>=minlen: out.append((S['lad'][i:j+1],S[ykey][i:j+1]))
            i=j+1
    return out
def band(segs,f1,f2):
    if not segs: return None
    nps=int(2**np.floor(np.log2(min(len(x) for x,_ in segs))))
    if nps<64: return None
    Pxx=Pyy=Pxy=None; fr=None; sec=0
    for x,y in segs:
        xs,ys=x-x.mean(),y-y.mean()
        f,pxx=signal.welch(xs,FS,nperseg=nps,noverlap=nps//2)
        _,pyy=signal.welch(ys,FS,nperseg=nps,noverlap=nps//2)
        _,pxy=signal.csd(xs,ys,FS,nperseg=nps,noverlap=nps//2)
        w=len(xs)
        Pxx=pxx*w if Pxx is None else Pxx+pxx*w
        Pyy=pyy*w if Pyy is None else Pyy+pyy*w
        Pxy=pxy*w if Pxy is None else Pxy+pxy*w
        fr=f; sec+=w/FS
    sel=(fr>=f1)&(fr<f2)
    if sel.sum()<2: return None
    Hf=np.abs(Pxy[sel])/np.maximum(Pxx[sel],1e-30)          # |H(f)| per bin -- no phasor cancellation
    coh=np.abs(Pxy[sel])**2/np.maximum(Pxx[sel]*Pyy[sel],1e-30)
    w=Pxx[sel]
    return (float(np.average(Hf,weights=w)),                 # power-weighted |H|
            float(np.average(coh,weights=w)),
            float(abs(Pxy[sel].sum()/Pxx[sel].sum())),       # the OLD (phasor-averaged) estimate
            sel.sum(), len(segs), sec)

print("="*100)
print("CONTROL: desired -> desired delayed 0.29 s.  TRUE |H| = 1.000 at every frequency.")
print("  If an estimator reads below 1.0 here, it is biased by phase rotation, not measuring the car.")
print("="*100)
lag=int(round(0.29*FS))
sets=[]
for S in (A,B):
    S2=dict(S); S2['laa']=np.concatenate([np.full(lag,S['lad'][0]),S['lad'][:-lag]]); sets.append(S2)
print(f"  {'band':>16} {'new |H|':>9} {'coh':>6} {'OLD phasor-avg':>16}   verdict")
for name,f1,f2,ml in BANDS:
    r=band(segs_for(sets,15.,34.,ml),f1,f2)
    if r: print(f"  {name:>16} {r[0]:9.3f} {r[1]:6.3f} {r[2]:16.3f}   "
                f"{'old estimator BIASED LOW' if r[2]<0.95 else 'both ok'}")

def show(tag,sets,vlo,vhi):
    print(f"\n  {tag}   ({vlo}-{vhi} m/s)")
    print(f"    {'band':>16} {'|H|':>8} {'coh':>6} {'sec':>6} {'runs':>5} {'split-half':>12}   verdict")
    for name,f1,f2,ml in BANDS:
        sg=segs_for(sets,vlo,vhi,ml); r=band(sg,f1,f2)
        if r is None: print(f"    {name:>16}   (no run >= {ml:.0f}s)"); continue
        ra=band(sg[0::2],f1,f2); rb=band(sg[1::2],f1,f2)
        sh=f"{ra[0]:.2f}/{rb[0]:.2f}" if (ra and rb) else "n/a"
        spread=abs(ra[0]-rb[0]) if (ra and rb) else 99
        v='MATCHES' if 0.9<=r[0]<=1.1 else ('UNDER' if r[0]<0.9 else 'OVER')
        if abs(r[0]-1.0)<spread: v+=' (within noise)'
        if r[1]<0.4: v+=' [LOW COHERENCE]'
        print(f"    {name:>16} {r[0]:8.3f} {r[1]:6.3f} {r[2+3]:6.0f} {r[4]:5d} {sh:>12}   {v}")

print()
print("="*100); print("THE GOAL, MEASURED PROPERLY"); print("="*100)
show("REV 6.4  HIGHWAY  (note 2 lives here)",[A,B],15.,34.)
show("REV 5    HIGHWAY",[C],15.,34.)
show("REV 6.4  LOW SPEED  (notes 3/4/5 live here)",[A,B],5.,15.)
show("REV 5    LOW SPEED",[C],5.,15.)
