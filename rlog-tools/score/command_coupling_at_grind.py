# -*- coding: utf-8 -*-
"""Is the LKAS command's 20 Hz content REAL, and is it coupled to the grind?

The operator's third symptom is "peak command oscillation".  sc_tq shows a 3.3x excess at 20.12 Hz,
the grind frequency.  But the record establishes the LKAS lane is a ~1-5 Hz low-pass, so openpilot
CANNOT command a 20 Hz oscillation.  Something else must explain that 3.3x.

A lead/lag test is NOT usable here: at 20 Hz one period is 50 ms = 5 samples at 100 Hz, so lag is
resolvable only modulo half a period, and openpilot's latency is 1-3 periods.  Coherence is usable.

    coherent with cs_rate at 20 Hz  => the command tracks the motion; it is REACTING, and fixing
                                       the grind fixes the command oscillation with it
    NOT coherent                    => the 20 Hz in sc_tq is quantisation / sampling artefact and
                                       is not a real command oscillation at all
"""
import os,sys,glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,SEG,NP=100.0,2048,256
C={k:[] for k in ('c20','c8','c1','s20','s8','s1')}
qsteps=[]; rng=np.random.default_rng(0)
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_rate','sc_tq')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    rt=np.asarray(z['cs_rate']).astype(float); cm=np.asarray(z['sc_tq']).astype(float)
    n=min(len(lat),len(kmh),len(rt),len(cm)); lat,kmh,rt,cm=lat[:n],kmh[:n],rt[:n],cm[:n]
    u=np.unique(cm); dv=np.abs(np.diff(u)); dv=dv[dv>0]
    if len(dv): qsteps.append(dv.min())
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(rt)&np.isfinite(cm)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
        for k in range(i,j-SEG,SEG//2):
            a,b=cm[k:k+SEG],rt[k:k+SEG]
            if len(a)<SEG or np.std(a)<=0 or np.std(b)<=0: continue
            f,Cxy=signal.coherence(a,b,FS,nperseg=NP)
            for lbl,hz in (('c1',1.0),('c8',8.0),('c20',20.0)):
                C[lbl].append(Cxy[np.argmin(abs(f-hz))])
            f,Cxy=signal.coherence(a,rng.permutation(b),FS,nperseg=NP)
            for lbl,hz in (('s1',1.0),('s8',8.0),('s20',20.0)):
                C[lbl].append(Cxy[np.argmin(abs(f-hz))])
print('%d engaged-creep episodes of %d samples'%(len(C['c20']),SEG))
print('LKAS command quantisation step (median over routes): %.4f'%np.median(qsteps))
print('')
print('%-24s %9s %9s %9s'%('pair','@ 1 Hz','@ 8 Hz','@ 20 Hz'))
print('-'*54)
print('%-24s %9.3f %9.3f %9.3f'%('sc_tq x cs_rate',np.median(C['c1']),np.median(C['c8']),np.median(C['c20'])))
print('%-24s %9.3f %9.3f %9.3f'%('SHUFFLED floor',np.median(C['s1']),np.median(C['s8']),np.median(C['s20'])))
e=[np.median(C['c%d'%h])-np.median(C['s%d'%h]) for h in (1,8,20)]
print('%-24s %+9.3f %+9.3f %+9.3f'%('excess over floor',*e))
print('')
if e[2]>0.15:
    print('=> the command IS coupled to the motion at 20 Hz.  Since the LKAS lane cannot COMMAND')
    print('   20 Hz, the command must be TRACKING it => openpilot is REACTING to the grind,')
    print('   and fixing the grind removes the command oscillation with it.  No separate lever.')
elif e[2]<0.05:
    print('=> NOT coupled at 20 Hz: the 3.3x in sc_tq is a quantisation/sampling artefact, not a')
    print('   real command oscillation.  The third symptom has no 20 Hz component to fix.')
else:
    print('=> marginal at this power.')
