# -*- coding: utf-8 -*-
"""The notch prediction, rebuilt on sound footing.

The open-loop score (21.5x) multiplied the WHOLE spectrum by |H|^2, attenuating the broadband
disturbance floor -- which the notch, sitting in the ASSIST path, cannot touch.  The closed-loop
correction was withdrawn with the contaminated ratio it rested on.

The defensible model splits the measured spectrum:

    P(f) = B(f) + X(f)        B = the smooth background (road/plant/sensor floor)
                              X = the EXCESS, i.e. the resonance the loop amplifies

Only X goes through the assist path, so:

    P_new(f) = B(f) + X(f) * |H_new(f) / H_old(f)|^2

and the reported statistic is the same slope-corrected excess the scorer prints, so the prediction
is directly comparable to what a drive will show.
"""
import io,os,struct,sys,glob,cmath,math
import numpy as np
from scipy import signal
os.chdir('C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod')
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
FS,NPS,SEC_FS=100.0,512,1000.0
FIT=[(3.,6.),(26.,40.)]
A='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord'
def co(b): return dict(zip(('A8','AC','B0','B4'),
    [struct.unpack_from('<f',b,o)[0] for o in (0xC60A8,0xC60AC,0xC60B0,0xC60B4)]))
def img(v):
    g=[x for x in glob.glob(A+'/*_'+v+'_*plain_image.bin') if 'SUPERSEDED' not in x]
    return io.open(sorted(g)[0],'rb').read() if g else None
fly=co(img('v122')); v195=co(img('v195')); v188=co(img('v188'))
def H(c,x):
    z=cmath.exp(2j*math.pi*x/SEC_FS)
    return abs(c['B4']*(z*z+c['B0']*z+1.0)/(z*z+c['A8']*z+c['AC']))
rows=[]
for p in sorted(glob.glob('analysis-2020accord/_scratch/cache/*/*.npz')):
    tag=os.path.basename(p)[:-4]
    try: z=np.load(p,allow_pickle=True)
    except Exception: continue
    if any(k not in z.files for k in ('cc_lat','cs_v','cs_rate')): continue
    lat=np.asarray(z['cc_lat']).astype(float); kmh=np.asarray(z['cs_v']).astype(float)*3.6
    rt=np.asarray(z['cs_rate']).astype(float)
    n=min(len(lat),len(kmh),len(rt)); lat,kmh,rt=lat[:n],kmh[:n],rt[:n]
    ok=(lat>0.5)&(kmh>=1.0)&(kmh<24.0)&np.isfinite(rt)
    d=np.diff(np.concatenate(([0],ok.view(np.int8),[0])))
    acc=[]
    for i,j in zip(np.where(d==1)[0],np.where(d==-1)[0]):
        if (j-i)<NPS: continue
        for k in range(i,j-NPS,NPS//2):
            s=rt[k:k+NPS]
            if np.std(s)<=0: continue
            f,P=signal.welch(s-s.mean(),FS,nperseg=NPS,noverlap=NPS//2); acc.append(P)
    if len(acc)<4: continue
    P=np.median(np.asarray(acc),0)
    fm=np.zeros_like(f,bool)
    for lo,hi in FIT: fm|=(f>=lo)&(f<=hi)
    g=fm&(P>0)&(f>0)
    if g.sum()<8: continue
    b,a=np.polyfit(np.log10(f[g]),np.log10(P[g]),1)
    B=10**(a+b*np.log10(np.maximum(f,1e-9)))
    X=np.maximum(P-B,0.0)
    m=(f>=15.)&(f<=25.)
    def exc(spec):
        gg=fm&(spec>0)&(f>0)
        bb,aa=np.polyfit(np.log10(f[gg]),np.log10(spec[gg]),1)
        return float(np.max(spec[m]/(10**(aa+bb*np.log10(f[m])))))
    out=[tag,exc(P)]
    for c in (v188,v195):
        gain=np.array([(H(c,float(x))/max(H(fly,float(x)),1e-12))**2 for x in f])
        out.append(exc(B+X*gain))
    rows.append(out)
E0=np.array([r[1] for r in rows]); E8=np.array([r[2] for r in rows]); E5=np.array([r[3] for r in rows])
print('%d routes, cs_rate GRIND 15-25 Hz, slope-corrected excess (null ~3.9x)'%len(rows))
print('')
print('%-26s %7s %7s %7s %7s %7s'%('','p10','p25','p50','p75','p90'))
for nm,v in (('measured (flying build)',E0),('after V188 notch',E8),('after V195 notch',E5)):
    print('%-26s %7.1f %7.1f %7.1f %7.1f %7.1f'%(nm,*[np.percentile(v,q) for q in (10,25,50,75,90)]))
print('')
print('reduction factor (measured / predicted):')
for nm,v in (('V188',E8),('V195',E5)):
    r=E0/np.maximum(v,1e-9)
    print('   %-5s p25 %.1fx   median %.1fx   p75 %.1fx'%(nm,*[np.percentile(r,q) for q in (25,50,75)]))
print('')
for nm,v in (('V188',E8),('V195',E5)):
    print('   %-5s routes falling BELOW the ~3.9x null: %d of %d (%.0f%%)'
          %(nm,(v<3.9).sum(),len(v),100*(v<3.9).mean()))
print('')
print('=> this is directly comparable to what score_band_excess.py prints after a drive.')
print('   It attenuates ONLY the excess, never the background, so it cannot repeat the')
print('   floor-attenuation error that made the 21.5x figure wrong.')
