# -*- coding: utf-8 -*-
"""Does V195's WIDER notch threaten its own low shoulder?

A notch inside a loop adds lag BELOW itself.  V195's pole radius is 0.9000 vs V188's 0.9300, so it is
wider and its lag profile is different -- the shoulder check done for V188 does not transfer.

The danger pattern is a frequency where all three hold at once:
    the spectrum already has EXCESS (something is there to grow),
    the notch leaves |H| HIGH (loop gain is retained),
    and the notch adds LARGE lag.
For a notch these tend to be anti-correlated -- lag and attenuation grow together -- which is why a
notch is safer here than a low-pass.  Verify it for THIS pole radius, on cs_rate (where the grind is).
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
fly=co(img('v122')); v195=co(img('v195')); v189=co(img('v189'))
def H(c,x):
    z=cmath.exp(2j*math.pi*x/SEC_FS)
    return c['B4']*(z*z+c['B0']*z+1.0)/(z*z+c['A8']*z+c['AC'])
acc=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_rate')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    rt=np.asarray(z['cs_rate']).astype(float)
    n=min(len(lat),len(kmh),len(rt)); lat,kmh,rt=lat[:n],kmh[:n],rt[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(rt)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
        if (j-i)<NPS: continue
        for k in range(i,j-NPS,NPS//2):
            s=rt[k:k+NPS]
            if np.std(s)<=0: continue
            f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
M=np.median(np.asarray(acc),0)
FIT=[(3.,6.),(26.,40.)]
fm=np.zeros_like(f,bool)
for lo,hi in FIT: fm|=(f>=lo)&(f<=hi)
g=fm&(M>0)&(f>0)
b,a=np.polyfit(np.log10(f[g]),np.log10(M[g]),1)
bg=10**(a+b*np.log10(np.maximum(f,1e-9)))
def lag(c,x):
    d=math.degrees(cmath.phase(H(c,x))-cmath.phase(H(fly,x)))
    return d-360 if d>180 else (d+360 if d<-180 else d)
print('cs_rate, %d pooled engaged-creep windows'%len(acc))
print('%8s %9s   %8s %9s   %8s %9s   %s'
      %('f (Hz)','excess','V189 |H|','V189 lag','V195 |H|','V195 lag','risk'))
print('-'*84)
worst=[]
for i,x in enumerate(f):
    if not (9.0<=x<=19.0): continue
    ex=M[i]/max(bg[i],1e-30)
    h9=abs(H(v189,float(x)))/max(abs(H(fly,float(x))),1e-12); l9=lag(v189,float(x))
    h5=abs(H(v195,float(x)))/max(abs(H(fly,float(x))),1e-12); l5=lag(v195,float(x))
    r=''
    if ex>2.0 and h5>0.5 and l5<-30: r='<== EXCESS + GAIN + LAG'
    worst.append((ex*max(h5,0)*max(-l5,0),x,ex,h5,l5))
    if abs(x-round(x))<0.3 or r:
        print('%8.2f %9.2f   %8.3f %9.1f   %8.3f %9.1f   %s'%(x,ex,h9,l9,h5,l5,r))
worst.sort(reverse=True)
print('')
print('worst three frequencies by excess x retained-gain x lag (V195):')
for s,x,ex,h,l in worst[:3]:
    print('   %6.2f Hz  excess %5.2f  |H| %5.3f  lag %+6.1f deg'%(x,ex,h,l))
flag=[w for w in worst if w[2]>2.0 and w[3]>0.5 and w[4]<-30]
print('')
print('frequencies with excess>2 AND |H|>0.5 AND lag<-30: %d  => %s'
      %(len(flag),'CLEAR' if not flag else 'REVIEW: '+' '.join('%.1fHz'%w[1] for w in flag[:5])))
