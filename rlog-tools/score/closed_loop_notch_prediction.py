# -*- coding: utf-8 -*-
"""CLOSED-LOOP prediction for the notch -- every estimate so far was OPEN-LOOP.

So far the notch's effect was estimated by multiplying the measured spectrum by |H|^2.  That treats
the filter as a feedforward attenuator.  But the grind is a CLOSED-LOOP instability, and in a loop

    engaged_output = disturbance / (1 - L)      LKAS off => L = 0 => output = disturbance

so the measured ENGAGED/MANUAL power ratio R(w) identifies the loop gain directly:

    R = 1 / |1 - L|^2     =>     |1 - L| = 1/sqrt(R)

Inserting the notch scales the loop gain by g = |H_new| / |H_flying|, so

    L' = L * g            R' = 1 / |1 - L'|^2

At the notch centre g -> 0, so L' -> 0 and R' -> 1: the engaged level falls all the way back to the
MANUAL level.  That is a far stronger claim than the open-loop 21.5x, and it is testable.

!! SIMPLIFICATION, STATED: L is taken as real and positive near the resonance (the worst case for
   stability).  Phase is not identified from a power ratio alone, so this is an ESTIMATE of the
   right order, not an exact figure.
"""
import io,os,struct,sys,glob,cmath,math
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

eng,man=[],[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_rate')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    rt=np.asarray(z['cs_rate']).astype(float)
    n=min(len(lat),len(kmh),len(rt)); lat,kmh,rt=lat[:n],kmh[:n],rt[:n]
    base=(kmh>=1.0)&(kmh<24.0)&np.isfinite(rt)
    for tgt,acc in ((True,eng),(False,man)):
        ok=base&((lat>0.5) if tgt else (lat<=0.5))
        d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
        for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
            if (j-i)<NPS: continue
            for k in range(i,j-NPS,NPS//2):
                s=rt[k:k+NPS]
                if np.std(s)<=0: continue
                f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
E=np.median(np.asarray(eng),0); M=np.median(np.asarray(man),0)
print('cs_rate: %d engaged / %d manual creep windows'%(len(eng),len(man)))
band=(f>=15.)&(f<=25.)
R=E/np.maximum(M,1e-30)
print('')
print('%8s %10s %10s %10s %10s %10s'%('f (Hz)','eng/man R','|1-L|','L est','notch g','R after'))
print('-'*64)
tr=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
Rn=np.array(R)
for i,x in enumerate(f):
    if not band[i]: continue
    r=max(R[i],1.0)
    l=1.0-1.0/math.sqrt(r)
    g=H(v196,float(x))/max(H(fly,float(x)),1e-12)
    l2=l*g
    r2=1.0/max((1.0-l2)**2,1e-30)
    Rn[i]=r2
    if abs(x-round(x))<0.3 or abs(x-19.75)<0.3:
        print('%8.2f %10.2f %10.4f %10.4f %10.4f %10.2f'%(x,r,1/math.sqrt(r),l,g,r2))
pe=float(tr(E[band],f[band])); pm=float(tr(M[band],f[band]))
pn=float(tr((M*Rn)[band],f[band]))
po=float(tr((E*np.array([ (H(v196,float(x))/max(H(fly,float(x)),1e-12))**2 for x in f]))[band],f[band]))
print('')
print('15-25 Hz band power on cs_rate:')
print('   engaged (measured)      %10.1f'%pe)
print('   manual  (measured)      %10.1f   <- the floor a broken loop returns to'%pm)
print('   OPEN-loop prediction    %10.1f   (x%.1f reduction)'%(po,pe/max(po,1e-30)))
print('   CLOSED-loop prediction  %10.1f   (x%.1f reduction)'%(pn,pe/max(pn,1e-30)))
print('')
print('=> engaged/manual in-band power ratio is %.1fx.'%(pe/max(pm,1e-30)))
print('')
print('   READ THIS CAREFULLY: the CLOSED-loop number is the SMALLER reduction, and it is the')
print('   honest one.  The open-loop estimate multiplies the WHOLE spectrum by |H|^2, which')
print('   attenuates the DISTURBANCE FLOOR as well -- but that floor is set by road and plant,')
print('   and the notch sits in the ASSIST path, so it cannot remove it.  The loop can only give')
print('   back what it added.')
print('   => the engaged/manual ratio is the CEILING on any assist-path fix in this band.')
