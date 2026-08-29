# -*- coding: utf-8 -*-
"""Is the ratchet/grind correlation a COMMON CAUSE, or just common EXPOSURE?

corr(log ratchet ratio, log grind ratio) = +0.748 across routes.  That would point to one
engaged-only driver behind both symptoms.  But it is equally consistent with routes simply differing
in how hard the system was working -- rougher road, more steering, more LKAS activity.

CONTROL: partial correlation, holding constant the engaged/manual ratio in a band with no symptom
in it.  If the correlation survives, it is not merely exposure.  Two controls are used:
  0.5-3 Hz  = the steering/LKAS activity band
  30-45 Hz  = the out-of-band control the scorers already use
"""
import os,sys,glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,NPS=100.0,512
tr=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
B={'ratchet':(5.,12.),'grind':(15.,25.),'act':(0.5,3.),'ctrl':(30.,45.)}
rows=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    tq=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(kmh),len(tq)); lat,kmh,tq=lat[:n],kmh[:n],tq[:n]
    base=(kmh>=1.0)&(kmh<24.0)&np.isfinite(tq)
    sp={}
    for tgt in (True,False):
        ok=base&((lat>0.5) if tgt else (lat<=0.5))
        d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
        acc=[]
        for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
            if (j-i)<NPS: continue
            for k in range(i,j-NPS,NPS//2):
                s=tq[k:k+NPS]
                if np.std(s)<=0: continue
                f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
        sp[tgt]=np.median(np.asarray(acc),0) if len(acc)>=4 else None
    if sp[True] is None or sp[False] is None: continue
    r={}
    for k,(lo,hi) in B.items():
        m=(f>=lo)&(f<=hi)
        pe=float(tr(sp[True][m],f[m])); pm=float(tr(sp[False][m],f[m]))
        r[k]=pe/pm if pm>0 else np.nan
    if all(np.isfinite(v) and v>0 for v in r.values()): rows.append(r)
L={k:np.log(np.array([r[k] for r in rows])) for k in B}
n=len(rows)
print('%d routes'%n)
def pc(x,y,z):
    """partial correlation of x,y given z"""
    bx=np.polyfit(z,x,1); by=np.polyfit(z,y,1)
    rx=x-np.polyval(bx,z); ry=y-np.polyval(by,z)
    return np.corrcoef(rx,ry)[0,1]
r0=np.corrcoef(L['ratchet'],L['grind'])[0,1]
print('')
print('corr(log ratchet, log grind)                       %+.3f'%r0)
for c in ('act','ctrl'):
    print('  partial, controlling for the %-4s band ratio    %+.3f'%(c,pc(L['ratchet'],L['grind'],L[c])))
print('')
print('for reference, how each symptom correlates with the controls:')
for k in ('ratchet','grind'):
    for c in ('act','ctrl'):
        print('  corr(log %-7s, log %-4s) = %+.3f'%(k,c,np.corrcoef(L[k],L[c])[0,1]))
p1=pc(L['ratchet'],L['grind'],L['act']); p2=pc(L['ratchet'],L['grind'],L['ctrl'])
print('')
if min(p1,p2)>0.45:
    print('=> the correlation SURVIVES both controls => a COMMON ENGAGED-ONLY CAUSE is supported,')
    print('   not merely common exposure.  One lever could move BOTH symptoms.')
elif max(p1,p2)<0.25:
    print('=> the correlation COLLAPSES under control => it was EXPOSURE. The symptoms are')
    print('   independent and separate levers remain the right design.')
else:
    print('=> partially attenuated: some shared cause, some shared exposure. Inconclusive at n=%d.'%n)
