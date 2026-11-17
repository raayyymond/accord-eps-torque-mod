"""Buzz census: >10 Hz content of wheel rate (0x14A) and torque sensor (0x18F) by condition. Cache only."""
import sys, glob, os
import numpy as np
from scipy import signal
def s16(d,i): return ((d[:,i].astype(np.int32)<<8)|d[:,i+1]).astype(np.int16).astype(float)
def load(p):
    z=np.load(p); t=z['t_14a']; n=min(len(t),len(z['t_18f']))
    d=dict(ang=-0.1*s16(z['d_14a'],0)[:n], rate=-s16(z['d_14a'],2)[:n], tq=-s16(z['d_18f'],0)[:n])
    cc=z['cc']; d['req']=np.interp(t[:n],cc[:,0],cc[:,1])>0.5
    cs=z['cs']; d['v']=np.interp(t[:n],cs[:,0],cs[:,1]); return d
b,a=signal.butter(4,10/50,'high'); bl,al=signal.butter(2,3/50,'low')
for C in sys.argv[1:]:
    rows=[]; spec={}
    for p in sorted(glob.glob(os.path.join(C,'seg*.npz'))):
        d=load(p); n=len(d['ang'])
        hr=signal.filtfilt(b,a,d['rate']); ht=signal.filtfilt(b,a,d['tq'])
        sr=signal.filtfilt(bl,al,d['rate'])
        W=64
        for i in range(0,n-W,W):
            s=slice(i,i+W)
            ang=d['ang'][s].mean(); r=sr[s].mean()
            x=hr[s]*np.hanning(W); P=np.abs(np.fft.rfft(x))**2; f=np.fft.rfftfreq(W,0.01)
            rows.append((d['req'][s].mean()>0.5, d['v'][s].mean(), ang, r, hr[s].std(), ht[s].std(), f[np.argmax(P)], abs(d['tq'][s].mean())))
    R=np.array(rows,float)
    eng=R[:,0]>0.5; mov=R[:,1]>2; ang=np.abs(R[:,2]); rt=R[:,3]; toC=(np.sign(R[:,2])*np.sign(rt)<0)&(np.abs(rt)>5); away=(np.sign(R[:,2])*np.sign(rt)>0)&(np.abs(rt)>5); still=np.abs(rt)<2
    print('\n==',C,'windows',len(R),'engaged %.0f%%'%(100*eng.mean()))
    print('  condition                          n   rate>10Hz rms p50/p90   tq>10Hz rms p50/p90   peak f p25/p50/p75')
    def row(name,m):
        m=m&mov
        if m.sum()<5: print('  %-32s %4d  (too few)'%(name,m.sum())); return
        print('  %-32s %4d   %5.1f / %5.1f          %5.0f / %5.0f        %4.1f / %4.1f / %4.1f'%(name,m.sum(),np.median(R[m,4]),np.percentile(R[m,4],90),np.median(R[m,5]),np.percentile(R[m,5],90),*np.percentile(R[m,6],[25,50,75])))
    for en,lab in ((False,'MANUAL '),(True,'ENGAGED')):
        e=eng==en
        row(lab+' wheel still',e&still)
        row(lab+' to centre  |ang|<30',e&toC&(ang<30))
        row(lab+' to centre  |ang|>30',e&toC&(ang>=30))
        row(lab+' away       |ang|<30',e&away&(ang<30))
        row(lab+' away       |ang|>30',e&away&(ang>=30))
