import numpy as np, glob, os
from numpy.lib.stride_tricks import sliding_window_view
from scipy import signal
FS=100.0
tot={}
for f in sorted(glob.glob('analysis-2020accord/_scratch/cache/r*/r*.npz')):
    tag=os.path.basename(os.path.dirname(f))
    if os.path.basename(f)!=tag+'.npz': continue
    z=np.load(f,allow_pickle=True)
    need=('cs_v','cs_tq','cc_lat','cs_rate','co_tqcan')
    if any(k not in z.files for k in need): continue
    G=lambda k:np.asarray(z[k]).astype(float)
    v,tq,lat,rate,cmd=[G(k) for k in need]
    w=51;pad=np.pad(np.abs(tq),(w//2,w-1-w//2),mode='edge')
    ho=np.median(sliding_window_view(pad,w),axis=-1)[:len(tq)]<1200
    m=(lat>0.5)&ho&(v>1.0)
    if m.sum()<5000: continue
    x=np.nan_to_num(np.where(m,cmd,0.)); y=np.nan_to_num(np.where(m,rate,0.))
    fr,Pxy=signal.csd(x,y,FS,nperseg=1024,noverlap=512)
    _,Pxx=signal.welch(x,FS,nperseg=1024,noverlap=512)
    _,Pyy=signal.welch(y,FS,nperseg=1024,noverlap=512)
    tot.setdefault('n',[]).append(m.sum())
    for k,a in (('Pxx',Pxx),('Pyy',Pyy),('Pxy',Pxy),('fr',fr)): tot.setdefault(k,[]).append(a)
W=np.array(tot['n'],float); W/=W.sum(); fr=tot['fr'][0]
Pxx=np.sum([w*a for w,a in zip(W,tot['Pxx'])],axis=0)
Pyy=np.sum([w*a for w,a in zip(W,tot['Pyy'])],axis=0)
Pxy=np.sum([w*a for w,a in zip(W,tot['Pxy'])],axis=0)
C=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
df=fr[1]-fr[0]
cmd_tot=np.sum(Pxx)*df; rate_tot=np.sum(Pyy)*df
print("HOW MUCH OF THE PROBLEM CAN A COMMAND-SIDE FILTER REACH? (%d routes)"%len(W))
print("  band        %%cmd power  %%rate power   coh2    coherent rate power in band")
for lo,hi in [(0.1,1),(1,2),(2,5),(5,8),(8,12),(12,20),(20,30),(30,50)]:
    b=(fr>=lo)&(fr<hi)
    cp=np.sum(Pxx[b])*df/cmd_tot; rp=np.sum(Pyy[b])*df/rate_tot
    coh=np.mean(C[b]); cohp=np.sum(Pyy[b]*C[b])*df/rate_tot
    print("  %5.1f-%5.1f Hz  %8.4f%%  %8.4f%%   %.3f    %8.4f%% of ALL rate power"
          %(lo,hi,100*cp,100*rp,coh,100*cohp))
print("\n  COMMAND energy above  5 Hz: %.4f%%   above 10 Hz: %.4f%%"
      %(100*np.sum(Pxx[fr>=5])*df/cmd_tot, 100*np.sum(Pxx[fr>=10])*df/cmd_tot))
print("  RATE    energy above  5 Hz: %.4f%%   above 10 Hz: %.4f%%"
      %(100*np.sum(Pyy[fr>=5])*df/rate_tot, 100*np.sum(Pyy[fr>=10])*df/rate_tot))
print("  RATE energy above 5 Hz that is COHERENT with the command: %.4f%% of all rate power"
      %(100*np.sum(Pyy[fr>=5]*C[fr>=5])*df/rate_tot))
print("\n  => a command-side low-pass can remove AT MOST the coherent part.")
