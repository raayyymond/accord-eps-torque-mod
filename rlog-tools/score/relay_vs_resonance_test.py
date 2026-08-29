# -*- coding: utf-8 -*-
"""Does the ratchet look like a RELAY-driven limit cycle, or a driven resonance?

Last tick I proposed the flying build's inertia term is a SATURATED RELAY (it clamps at
|accel| > 1065).  But the record carries a 5-star finding: "lightly-damped resonance, ring-down
zeta 0.017-0.036, LIMIT CYCLE EXCLUDED".  A relay in a loop is exactly what makes a limit cycle, so
the two accounts are in tension and one of them is wrong.

DISCRIMINATING SIGNATURES
  a relay-driven limit cycle   odd HARMONICS (3f, 5f) - NARROW amplitude distribution (the loop
                               sets the amplitude, not the disturbance)
  a driven resonance           NO harmonics (linear) - BROAD amplitude distribution following
                               whatever excites it

Controls: the same statistics at a frequency with no symptom, and a shuffled-phase surrogate.
"""
import os,sys,glob
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,NPS=100.0,512
amps=[]; H=[]; C=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_tq')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    tq=np.asarray(z['cs_tq']).astype(float)
    n=min(len(lat),len(kmh),len(tq)); lat,kmh,tq=lat[:n],kmh[:n],tq[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(tq)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
        if (j-i)<NPS: continue
        for k in range(i,j-NPS,NPS//2):
            s=tq[k:k+NPS]
            if np.std(s)<=0: continue
            f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2)
            m=(f>=5)&(f<=12)
            f0=float(f[m][int(np.argmax(P[m]))]); a0=float(P[m].max())
            def at(hz,w=1.0):
                mm=(f>=hz-w)&(f<=hz+w)
                return float(P[mm].max()) if mm.any() else np.nan
            # local background either side of each harmonic, for a prominence
            def prom(hz,w=1.0):
                mm=(f>=hz-w)&(f<=hz+w)
                bg=(f>=hz-4)&(f<=hz+4)&~mm
                return float(P[mm].max()/max(np.median(P[bg]),1e-30)) if mm.any() and bg.any() else np.nan
            amps.append(a0)
            H.append((prom(f0), prom(3*f0), prom(5*f0), prom(2*f0), prom(f0*3.7)))
            C.append(f0)
H=np.array(H); amps=np.array(amps); C=np.array(C)
g=np.isfinite(H).all(1)
H,amps,C=H[g],amps[g],C[g]
print('%d engaged-creep windows'%len(H))
print('fundamental f0: median %.2f Hz  (IQR %.2f-%.2f)'
      %(np.median(C),np.percentile(C,25),np.percentile(C,75)))
print('')
print('[1] HARMONIC STRUCTURE -- prominence above local background')
print('   %-22s %8s %8s'%('','median','p90'))
for nm,i in (('f0  (fundamental)',0),('3*f0  ODD harmonic',1),('5*f0  ODD harmonic',2),
             ('2*f0  even (control)',3),('3.7*f0 (control)',4)):
    print('   %-22s %8.2f %8.2f'%(nm,np.median(H[:,i]),np.percentile(H[:,i],90)))
h3=np.median(H[:,1]); h2=np.median(H[:,3]); hc=np.median(H[:,4])
print('')
print('   odd/even ratio  3f0 vs 2f0 = %.2f   3f0 vs the off-harmonic control = %.2f'%(h3/max(h2,1e-9),h3/max(hc,1e-9)))
print('')
print('[2] AMPLITUDE DISTRIBUTION -- a limit cycle is NARROW, a driven resonance is BROAD')
la=np.log10(amps)
sd=float(np.std(la,ddof=1))
print('   log10 peak power: sd %.3f  =>  p10-p90 spans %.0fx'%(sd,10**(np.percentile(la,90)-np.percentile(la,10))))
print('   (a relay limit cycle would be within a few x; broadband-driven spans orders)')
print('')
verdict=[]
if h3/max(hc,1e-9) > 1.5: verdict.append('odd harmonics PRESENT -> relay-like')
else: verdict.append('NO odd-harmonic excess -> linear, not a relay')
if 10**(np.percentile(la,90)-np.percentile(la,10)) < 10: verdict.append('amplitude NARROW -> limit-cycle-like')
else: verdict.append('amplitude BROAD -> driven, not a limit cycle')
print('=> ' + ' ; '.join(verdict))
