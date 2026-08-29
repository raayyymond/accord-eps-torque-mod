# -*- coding: utf-8 -*-
"""Per-route severity, done CORRECTLY: slope-corrected excess, not engaged/manual ratio.

The engaged/manual ratio is contaminated -- both symptom bands correlate ~0.9 with a 30-45 Hz
control band that contains neither symptom, i.e. the ratio is elevated BROADBAND on some routes
(different exposure when engaged vs manual).  The slope-corrected excess is band-specific by
construction: it divides a band by a power law fitted OUTSIDE it, on the SAME windows.
"""
import os,sys,glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,NPS=100.0,512
FIT=[(3.,6.),(26.,40.)]
def excess(P,f,fitm,lo,hi):
    g=fitm&(P>0)&(f>0)
    if g.sum()<8: return np.nan
    b,a=np.polyfit(np.log10(f[g]),np.log10(P[g]),1)
    m=(f>=lo)&(f<=hi)
    return float(np.max(P[m]/(10**(a+b*np.log10(f[m])))))
rows=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    tag=os.path.basename(p)[:-4]
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq','cs_rate')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    tq=np.asarray(z['cs_tq']).astype(float); rt=np.asarray(z['cs_rate']).astype(float)
    n=min(len(lat),len(kmh),len(tq),len(rt)); lat,kmh,tq,rt=lat[:n],kmh[:n],tq[:n],rt[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(tq)&np.isfinite(rt)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    at,ar=[],[]
    for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
        if (j-i)<NPS: continue
        for k in range(i,j-NPS,NPS//2):
            s,v=tq[k:k+NPS],rt[k:k+NPS]
            if np.std(s)<=0 or np.std(v)<=0: continue
            f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); at.append(P)
            f,Q=signal.welch(v-v.mean(),FS,nperseg=NPS,noverlap=NPS//2); ar.append(Q)
    if len(at)<4: continue
    fitm=np.zeros_like(f,bool)
    for lo,hi in FIT: fitm|=(f>=lo)&(f<=hi)
    T=np.median(np.asarray(at),0); Rr=np.median(np.asarray(ar),0)
    rows.append((tag,len(at),excess(T,f,fitm,5,12),excess(Rr,f,fitm,15,25)))
rows=[r for r in rows if np.isfinite(r[2]) and np.isfinite(r[3])]
R=np.array([r[2] for r in rows]); G=np.array([r[3] for r in rows])
print('%d routes, ENGAGED creep windows only, slope-corrected excess'%len(rows))
print('   RATCHET measured in cs_tq 5-12 Hz   GRIND measured in cs_rate 15-25 Hz')
print('   null for this statistic is ~3.9x')
print('')
print('%-10s %7s %7s %7s %7s %7s %7s'%('band','p10','p25','p50','p75','p90','max'))
for nm,v in (('RATCHET',R),('GRIND',G)):
    print('%-10s %7.1f %7.1f %7.1f %7.1f %7.1f %7.1f'
          %(nm,*[np.percentile(v,q) for q in (10,25,50,75,90)],v.max()))
print('')
print('fraction of routes ABOVE the ~3.9x null:  ratchet %.0f%%   grind %.0f%%'
      %(100*(R>3.9).mean(),100*(G>3.9).mean()))
c=np.corrcoef(np.log(R),np.log(G))[0,1]
print('')
print('corr(log ratchet excess, log grind excess) = %+.3f'%c)
print('   %s'%('still coupled -- a common cause survives the proper statistic'
              if c>0.5 else 'INDEPENDENT -- the earlier +0.748 was the broadband confound'
              if abs(c)<0.3 else 'weakly related'))
o=sorted(rows,key=lambda r:-r[2])
print('')
print('%-9s %9s %9s  %s'%('route','ratchet','grind','windows'))
print('-'*44)
for r in o[:6]: print('%-9s %8.1fx %8.1fx  %d'%(r[0],r[2],r[3],r[1]))
