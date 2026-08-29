# -*- coding: utf-8 -*-
"""Operating-point stratification on the FULL corpus.

Two results from the 9-route subset are now operational instructions on the drive card:
  * ratchet excess MONOTONE in command (17.0 -> 58.1, 3.4x)  => "include real curvature"
  * grind excess PEAKS mid-command and DIES above 1500 ct    => "take the grind verdict from
                                                                 the mid-command windows"
If either is wrong the drive is mis-specified, so both are re-tested at full n.
"""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
ROUTES = ['r78','r79','r7e','r7f','r81','r82','r85','r95','r96','r9e',
          'r21','r77','ra4','ra5','ra6','r1e','r22','r97','r24']

def windows(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): return []
    z=np.load(p,allow_pickle=True)
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq','sc_tq','cs_rate')): return []
    lat=np.asarray(z['cc_lat']).astype(float); v=np.asarray(z['cs_v']).astype(float)
    a=np.asarray(z['cs_tq']).astype(float); rate=np.asarray(z['cs_rate']).astype(float)
    cmd=np.asarray(z['sc_tq']).astype(float)
    n=min(len(lat),len(v),len(a),len(rate),len(cmd))
    lat,kmh,a,rate,cmd=lat[:n],v[:n]*3.6,a[:n],rate[:n],cmd[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(a)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    st,en=np.where(d==1)[0],np.where(d==-1)[0]
    out=[]
    for i,j in zip(st,en):
        for k in range(i,j-NPS+1,NPS//2):
            w=a[k:k+NPS]
            if np.std(w)>0:
                out.append((w,kmh[k:k+NPS].mean(),np.abs(rate[k:k+NPS]).mean(),np.abs(cmd[k:k+NPS]).mean()))
    return out

def band_of(ws,bd):
    acc,f=[],None
    for w in ws:
        f,P=signal.welch(w-w.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    M=np.median(np.asarray(acc),0)
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use&=~((f>=lo)&(f<=hi))
    if use.sum()<6: return np.nan,np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    m=(f>=bd[0])&(f<=bd[1]); r=M[m]/bg[m]
    return float(np.max(r)),float(f[m][int(np.argmax(r))])

ALL=[]
for t in ROUTES: ALL.extend(windows(t))
print('pooled windows: %d  (was 244 on 9 routes)\n'%len(ALL))
for nm,idx,edges,old in (('SPEED km/h',1,[1,6,10,14,18,24],None),
                         ('|RATE| deg/s',2,[0,3,6,12,25,1e9],None),
                         ('|COMMAND| ct',3,[0,100,250,600,1500,1e9],
                          {'100-250':(17.0,5.1),'250-600':(19.4,8.5),'600-1500':(39.4,12.6),'1500-1e+09':(58.1,6.0)})):
    print('%-14s %-7s | %-9s %-9s | %-9s %-9s %s'%(nm,'n win','RAT Hz','RAT exc','GRD Hz','GRD exc','n=9 (rat/grd)'))
    pk=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        sel=[w for w in ALL if lo<=w[idx]<hi]
        if len(sel)<15:
            print('%-14s %-7d | -- too few'%('%g-%g'%(lo,hi),len(sel))); continue
        r_exc,r_hz=band_of([s[0] for s in sel],RATCHET)
        g_exc,g_hz=band_of([s[0] for s in sel],GRIND)
        key='%g-%g'%(lo,hi)
        o=old.get(key) if old else None
        print('%-14s %-7d | %-9.2f %-9.1f | %-9.2f %-9.1f %s'%(key,len(sel),r_hz,r_exc,g_hz,g_exc,
              ('%.1f / %.1f'%o) if o else ''))
        if np.isfinite(r_hz): pk.append(r_hz)
    if len(pk)>=3:
        print('   => ratchet peak spread %.2f-%.2f Hz, CV %.1f %%\n'%(min(pk),max(pk),100*np.std(pk)/np.mean(pk)))
    else: print()
