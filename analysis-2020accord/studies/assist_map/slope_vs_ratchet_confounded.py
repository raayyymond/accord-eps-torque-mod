# -*- coding: utf-8 -*-
"""Stratify torque WITHIN narrow command bands, to break the confound."""
import os, sys
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS, NPS = 100.0, 512
RATCHET, GRIND = (5.0, 12.0), (15.0, 25.0); BANDS = (RATCHET, GRIND)
ROUTES = ['r78','r7e','r7f','r96','ra4','ra6','r1e','r22','r24']
KX = [0,25,60,100,150,250,450,900,1800,4150]; KS = [6.16,5.26,3.05,1.78,0.86,0.34,0.14,0.06,0.01]
def slope(tq):
    a = abs(tq)
    for j in range(9):
        if a < KX[j+1]: return min(KS[j], 2.0)
    return min(KS[-1], 2.0)
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
            out.append((w,np.abs(w).mean(),np.abs(cmd[k:k+NPS]).mean(),np.abs(rate[k:k+NPS]).mean()))
    return out
def excess(ws):
    acc,f=[],None
    for w in ws:
        f,P=signal.welch(w-w.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    M=np.median(np.asarray(acc),0)
    use=(f>=3.0)&(f<=40.0)&(M>0)
    for lo,hi in BANDS: use &= ~((f>=lo)&(f<=hi))
    if use.sum()<6: return np.nan
    c=np.polyfit(np.log(f[use]),np.log(M[use]),1)
    bg=np.exp(np.polyval(c,np.log(np.maximum(f,1e-9))))
    m=(f>=RATCHET[0])&(f<=RATCHET[1])
    return float(np.max(M[m]/bg[m]))
ALL=[]
for t in ROUTES: ALL.extend(windows(t))
print('windows: %d\n'%len(ALL))
print('%-18s %-14s %-7s %-11s %-11s %s'%('command band','torque band','n','map slope','excess','mean |rate|'))
for clo,chi in ((0,600),(600,1500),(1500,1e9)):
    sub=[w for w in ALL if clo<=w[2]<chi]
    if len(sub)<24:
        print('%-18s  -- only %d windows'%('%g-%g'%(clo,chi),len(sub))); continue
    med=np.median([w[1] for w in sub])
    rows=[]
    for nm,sel in (('|tq| below med',[w for w in sub if w[1]<med]),
                   ('|tq| above med',[w for w in sub if w[1]>=med])):
        if len(sel)<12:
            print('%-18s %-14s %-7d  -- too few'%('%g-%g'%(clo,chi),nm,len(sel))); continue
        e=excess([s[0] for s in sel]); sl=np.mean([slope(s[1]) for s in sel])
        mr=np.mean([s[3] for s in sel])
        print('%-18s %-14s %-7d %-11.3f %-11.1f %.1f'%('%g-%g'%(clo,chi),nm,len(sel),sl,e,mr))
        rows.append((sl,e))
    if len(rows)==2:
        lo_s,lo_e=rows[0]; hi_s,hi_e=rows[1]
        d='HIGHER slope -> HIGHER excess (account SUPPORTED)' if (lo_s>hi_s)==(lo_e>hi_e) else 'contradicts the account'
        print('%-18s   => %s'%('','%s'%d))
