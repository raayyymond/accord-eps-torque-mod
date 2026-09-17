"""THE GOAL METRIC on rev 6.4, against rev 5, with a real noise floor.
Split by the regime the operator's notes actually live in:
  notes 3/4/5 (large angle, jerky, rate transients)  -> BELOW 15 m/s
  note 2      (5-10 s looseness on straight roads)   -> ABOVE 15 m/s
"""
import math, numpy as np
from scipy import signal
CA='analysis-2020accord/_scratch/cache/tau/'
BANDS=[('SLOW  0.05-0.15',0.05,0.15,60.),('MID   0.15-0.30',0.15,0.30,40.),
       ('FINE  0.30-0.60',0.30,0.60,24.),('TRANS 0.60-1.20',0.60,1.20,12.),('FAST  1.20-3.00',1.20,3.00,8.)]

def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),
                sa=np.interp(t,D['t_cst'],D['sa_deg']),sr=np.interp(t,D['t_cst'],D['sr_deg']),
                v=np.interp(t,D['t_cst'],D['vego']),pr=np.interp(t,D['t_cst'],D['spress'])>0.5,
                lad=D['cs_la_des'],laa=D['cs_la_act'],out=D['cs_out'])

def runs_for(S, vlo, vhi, minlen):
    t,FS=S['t'],S['FS']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi)
    out,n,i=[],len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=minlen: out.append((i,j+1))
        i=j+1
    return out

def band_tf(segs, FS, f1, f2):
    use=[s for s in segs if len(s[0])>=int(2**np.floor(np.log2(len(s[0]))))]
    if not use: return None
    nps=int(2**np.floor(np.log2(min(len(x) for x,_ in use))))
    if nps<64: return None
    Pxx=Pxy=None; fr=None; sec=0
    for x,y in use:
        xs,ys=x-x.mean(),y-y.mean()
        f,pxx=signal.welch(xs,FS,nperseg=nps,noverlap=nps//2)
        _,pxy=signal.csd(xs,ys,FS,nperseg=nps,noverlap=nps//2)
        w=len(xs); Pxx=pxx*w if Pxx is None else Pxx+pxx*w
        Pxy=pxy*w if Pxy is None else Pxy+pxy*w; fr=f; sec+=w/FS
    sel=(fr>=f1)&(fr<f2)
    if sel.sum()<2: return None
    H=Pxy[sel].sum()/Pxx[sel].sum()
    return abs(H), np.degrees(np.angle(H)), sel.sum(), len(use), sec

def score(sets, vlo, vhi, label):
    print(f"\n  {label}   ({vlo}-{vhi} m/s)")
    print(f"    {'band':>16} {'|H|':>8} {'phase':>8} {'sec':>6} {'runs':>5} {'split-half':>12}   verdict")
    FS=sets[0]['FS']
    for name,f1,f2,ml in BANDS:
        segs=[]
        for S in sets:
            for a,b in runs_for(S,vlo,vhi,ml):
                segs.append((S['lad'][a:b], S['laa'][a:b]))
        r=band_tf(segs,FS,f1,f2)
        if r is None: print(f"    {name:>16}   (no run >= {ml:.0f}s)"); continue
        mag,ph,nb,nr,sec=r
        ra=band_tf(segs[0::2],FS,f1,f2); rb=band_tf(segs[1::2],FS,f1,f2)
        sh=f"{ra[0]:.2f}/{rb[0]:.2f}" if (ra and rb) else "n/a"
        spread=abs(ra[0]-rb[0]) if (ra and rb) else None
        v=('MATCHES' if 0.9<=mag<=1.1 else 'UNDER' if mag<0.9 else 'OVER')
        if spread is not None and abs(mag-1.0)<spread: v+=' (within noise)'
        print(f"    {name:>16} {mag:8.3f} {ph:+8.1f} {sec:6.0f} {nr:5d} {sh:>12}   {v}")

A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); C=load('r76_v293_ident.npz')
print("="*98); print("CONTROLS"); print("="*98)
segs=[]
for S in (A,B):
    for a,b in runs_for(S,15.,34.,24.): segs.append((S['lad'][a:b],S['lad'][a:b]))
for name,f1,f2,ml in BANDS[:4]:
    r=band_tf(segs,A['FS'],f1,f2)
    if r: print(f"  positive control {name:>16}: |H|={r[0]:.4f} phase={r[1]:+.2f} deg")

print()
print("="*98); print("REV 6.4  (routes 6c + 6d pooled, 1185 s usable)"); print("="*98)
score([A,B], 15.0, 34.0, "HIGHWAY -- where note 2 (5-10 s looseness) lives")
score([A,B],  5.0, 15.0, "LOW SPEED -- where notes 3/4/5 (large angle, jerk, rate) live")
print()
print("="*98); print("REV 5  (route 76, 488 s usable) -- the comparison"); print("="*98)
score([C], 15.0, 34.0, "HIGHWAY")
score([C],  5.0, 15.0, "LOW SPEED")
