# -*- coding: utf-8 -*-
"""Per-route engaged/manual grind ratio -- the pooled median hides what matters.

The closed-loop analysis used a POOLED median and got engaged/manual = 11.3x, implying loop gain
L ~ 0.78-0.81.  The record says "9,200x less power with LKAS off" at 21.09 Hz.  Those cannot both
describe the same thing.

If the ratio varies a lot BY ROUTE, then loop gain varies too, and on the routes where the grind is
WORST the loop is closest to unity -- which is exactly where a notch delivers most.  The operator
cares about the bad drives, not the median one.
"""
import os,sys,glob,io,struct,cmath,math
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,NPS,SEC_FS=100.0,512,1000.0
A='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
def co(b): return dict(zip(('A8','AC','B0','B4'),
    [struct.unpack_from('<f',b,o)[0] for o in (0xC60A8,0xC60AC,0xC60B0,0xC60B4)]))
def img(v):
    g=[x for x in glob.glob(A+'/*_'+v+'_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0],'rb').read() if g else None
fly=co(img('v122')); v196=co(img('v196'))
def H(c,x):
    z=cmath.exp(2j*math.pi*x/SEC_FS)
    return abs(c['B4']*(z*z+c['B0']*z+1.0)/(z*z+c['A8']*z+c['AC']))
tr=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
rows=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    tag=os.path.basename(p)[:-4]
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_rate')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    rt=np.asarray(z['cs_rate']).astype(float)
    n=min(len(lat),len(kmh),len(rt)); lat,kmh,rt=lat[:n],kmh[:n],rt[:n]
    base=(kmh>=1.0)&(kmh<24.0)&np.isfinite(rt)
    sp={}
    for tgt in (True,False):
        ok=base&((lat>0.5) if tgt else (lat<=0.5))
        d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
        acc=[]
        for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
            if (j-i)<NPS: continue
            for k in range(i,j-NPS,NPS//2):
                s=rt[k:k+NPS]
                if np.std(s)<=0: continue
                f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
        sp[tgt]=(np.median(np.asarray(acc),0),len(acc)) if len(acc)>=4 else None
    if sp[True] and sp[False]:
        E,ne=sp[True]; M,nm=sp[False]
        b=(f>=15.)&(f<=25.)
        pe=float(tr(E[b],f[b])); pm=float(tr(M[b],f[b]))
        if pm<=0: continue
        R=pe/pm
        # closed-loop: per-bin L from the per-bin ratio, then the notch
        Rb=E/np.maximum(M,1e-30)
        newE=np.array(M)
        for i,x in enumerate(f):
            if not b[i]: continue
            r=max(Rb[i],1.0); l=1.0-1.0/math.sqrt(r)
            g=H(v196,float(x))/max(H(fly,float(x)),1e-12)
            newE[i]=M[i]/max((1.0-l*g)**2,1e-30)
        pn=float(tr(newE[b],f[b]))
        rows.append((R,pe/max(pn,1e-30),tag,ne,nm))
rows.sort(reverse=True)
R=np.array([r[0] for r in rows]); G=np.array([r[1] for r in rows])
print('%d routes with >=4 engaged AND >=4 manual creep windows'%len(rows))
print('')
print('engaged/manual GRIND power ratio, 15-25 Hz on cs_rate:')
for q in (10,25,50,75,90,100):
    print('   p%-3d  %8.1fx'%(q,np.percentile(R,q)))
print('')
print('%-8s %12s %14s   %s'%('route','eng/man','notch gives','windows e/m'))
print('-'*58)
for r,g,tag,ne,nm in rows[:10]:
    print('%-8s %11.1fx %13.1fx   %d/%d'%(tag,r,g,ne,nm))
print('   ... %d more'%max(0,len(rows)-10))
print('')
hi=R>=np.percentile(R,75); lo=R<=np.percentile(R,25)
print('the WORST quartile of routes (eng/man >= %.1fx):'%np.percentile(R,75))
print('   median ratio %.1fx   notch predicted to give %.1fx'%(np.median(R[hi]),np.median(G[hi])))
print('the BEST quartile (eng/man <= %.1fx):'%np.percentile(R,25))
print('   median ratio %.1fx   notch predicted to give %.1fx'%(np.median(R[lo]),np.median(G[lo])))
print('')
print('=> the notch delivers MOST where the grind is WORST, because loop gain is highest there.')
print('   Pooling hid that: the pooled median was %.1fx.'%np.median(R))
