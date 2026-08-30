import sys, os, glob
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import clip_duty_and_v238_dose as C
import slope_cap_band_size as S
import numpy as np, assist_map_mirror as AM
from scipy import signal
from assist_map_mirror import u16, TP, _lerp_u16

NX=[u16(TP+0x7936+2*i) for i in range(4)]; NY=[u16(TP+0x793E+2*i) for i in range(4)]
V240=[round(y*0.6) for y in NY]
def fn(Y): return lambda sc: min(4096,_lerp_u16(int(sc),NX,Y))

BANDS=[('ratchet 6-9',6,9),('grind 9-15',9,15),('grind 15-22',15,22),
       ('pump 22-40',22,40),('all 1-50',1,50)]

def bandpow(b82,b84,fs,k,lo,hi):
    npg=min(1024,(len(b82)//4)*2)
    if npg<256: return np.nan
    f,P82=signal.welch(b82-b82.mean(),fs,nperseg=npg)
    _,P84=signal.welch(b84-b84.mean(),fs,nperseg=npg)
    _,Px =signal.csd(b82-b82.mean(),b84-b84.mean(),fs,nperseg=npg)
    m=(f>=lo)&(f<=hi)
    Hk=np.array([C.H(k,ff,1000.0) for ff in f])
    return float((P82[m]+Hk[m]**2*P84[m]+2*Hk[m]*np.real(Px[m])).sum())

caches=[]
for c in sorted(glob.glob('_scratch/cache/*/*.npz')):
    try: z=np.load(c,allow_pickle=True)
    except Exception: continue
    if not all(k in z.files for k in C.REQUIRED) or 't' not in z.files: continue
    if (np.asarray(z['cc_lat'],float)>0.5).sum()<1500: continue
    caches.append(c)
    if len(caches)>=14: break

print('V240 (slew x0.600) ACROSS BANDS -- %d routes\n' % len(caches))
print('  %-14s %12s %10s %10s' % ('band','ratio','min','max'))
print('  '+'-'*50)
res={b[0]:[] for b in BANDS}
for c in caches:
    z=np.load(c,allow_pickle=True); t=np.asarray(z['t'],float); fs=1.0/np.median(np.diff(t))
    C.g69a0_of=fn(NY); S.g69a0_of=C.g69a0_of
    r82,r84,e=S.lane_series(z,2048); AM.CAL_7384=2048
    C.g69a0_of=fn(V240); S.g69a0_of=C.g69a0_of
    n82,n84,_=S.lane_series(z,2048); AM.CAL_7384=2048
    for nm,lo,hi in BANDS:
        b0=bandpow(r82[e],r84[e],fs,20,lo,hi)
        b1=bandpow(n82[e],n84[e],fs,20,lo,hi)
        if b0 and b0>0 and np.isfinite(b1): res[nm].append(b1/b0)
for nm,_,_ in BANDS:
    v=np.array(res[nm])
    if len(v): print('  %-14s %12.4f %10.3f %10.3f   (%+.1f %%)' % (nm,np.median(v),v.min(),v.max(),100*(np.median(v)-1)))
print()
print('  ratio < 1 = less lane gain in that band.')
print('  \U0001f6d1 the caches run at ~101 Hz so 22-40 Hz is ALIASED from 52-71 Hz -- see the record.')
