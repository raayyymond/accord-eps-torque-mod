# -*- coding: utf-8 -*-
"""Is the GRIND the same mechanism as the ratchet, at a different plant mode?

The ratchet showed the 1-P.L signature: FIXED frequency (CV 5.5 % across speed) with
amplitude MONOTONE in command (17.0 -> 58.1, a 3.4x rise).  Both symptoms are now known to
be engaged-only.  If the grind shows the same signature, the two are ONE mechanism at two
plant resonances, V172 addresses both by the same route, and the drive tests them jointly.

If instead the grind's frequency MOVES with operating point, it is a different mechanism and
a grind result would not license anything about the ratchet.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
ROUTES = ['r78','r7e','r7f','r96','ra4','ra6','r1e','r22','r24']

def windows(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float); rate=np.asarray(z['cs_rate']).astype(float)
    cmd=np.asarray(z['sc_tq']).astype(float) if 'sc_tq' in z.files else np.zeros_like(a)
    n=min(len(lat),len(v),len(a),len(rate),len(cmd))
    lat,kmh,a,rate,cmd=lat[:n],v[:n]*3.6,a[:n],rate[:n],cmd[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    out=[]
    for i,j in zip(st,en):
        for k in range(i,j-NPS+1,NPS//2):
            w=a[k:k+NPS]
            if np.std(w)==0: continue
            out.append((w,kmh[k:k+NPS].mean(),np.abs(rate[k:k+NPS]).mean(),np.abs(cmd[k:k+NPS]).mean()))
    return out

def peak_of(ws, band):
    acc,f=[],None
    for w in ws:
        f,P=signal.welch(w-w.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    M=np.median(np.asarray(acc),0)
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use &= ~((f>=lo)&(f<=hi))
    if use.sum()<6: return np.nan,np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    m=(f>=band[0])&(f<=band[1]); r=M[m]/bg[m]
    return float(f[m][int(np.argmax(r))]), float(np.max(r))

ALL=[]
for t in ROUTES: ALL.extend(windows(t))
print('pooled windows: %d\n'%len(ALL))
for nm,idx,edges in (('SPEED km/h',1,[1,6,10,14,18,24]),
                     ('|RATE| deg/s',2,[0,3,6,12,25,1e9]),
                     ('|COMMAND| ct',3,[0,100,250,600,1500,1e9])):
    print('%-14s %-7s | %-9s %-9s | %-9s %s'%(nm,'n win','GRIND Hz','excess','RATCHET Hz','excess'))
    gp=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        sel=[w for w in ALL if lo<=w[idx]<hi]
        if len(sel)<12:
            print('%-14s %-7d | -- too few'%('%g-%g'%(lo,hi),len(sel))); continue
        gf,ge=peak_of([s[0] for s in sel],GRIND)
        rf,re_=peak_of([s[0] for s in sel],RATCHET)
        print('%-14s %-7d | %-9.2f %-9.1f | %-9.2f %.1f'%('%g-%g'%(lo,hi),len(sel),gf,ge,rf,re_))
        if np.isfinite(gf): gp.append(gf)
    if len(gp)>=3:
        print('   => GRIND peak spread %.2f-%.2f Hz, sd %.2f, CV %.1f %%\n'
              %(min(gp),max(gp),np.std(gp),100*np.std(gp)/np.mean(gp)))
    else: print()
