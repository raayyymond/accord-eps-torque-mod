# -*- coding: utf-8 -*-
"""DE-EMBED EACH ROUTE'S OWN BIQUAD BEFORE POOLING -- a correction to how V235 was designed.

gp-0x6b86 is measured DOWNSTREAM of the biquad. I pooled ra4/ra5/ra6 and then corrected as if HONDA's
filter had been in place on all three. It was not:

    ra4  V104   biquad f8c2c4bf 7576223f 0ebef0bf fc89c13f   (Honda angles, different b4)
    ra5  V105   biquad 56e1f0bf 3d0a673f 9eb8fcbf b51a4e3f   (V105's ~25.5 Hz notch)
    ra6  V106   biquad 56e1f0bf 3d0a673f 9eb8fcbf b51a4e3f   (same as ra5)

So the pooled phase carried each route's own notch. The fix: recover the lane's INTRINSIC response by
dividing out the biquad that was actually in force, then pool, then optimise a new biquad against that.

    phi_intrinsic(f) = phi_measured(f) - arg(H_route(f))
    P_intrinsic(f)   = P_measured(f) / |H_route(f)|^2

and the objective becomes, for a candidate C applied to the intrinsic lane:

    J(C) = SUM_f |C(f)| * cos( phi_intrinsic(f) + arg C(f) ) * P_intrinsic(f)
"""
import cmath, glob, math, os, struct, sys
import numpy as np
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS=1000.0; R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
A8=0xC60A8
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def imf(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
def coefs(b): return np.array([f32(b,A8),f32(b,A8+4),f32(b,A8+8),f32(b,A8+12)])
def Hv(C,f):
    z=np.exp(2j*np.pi*f/FS)[None,:]
    return (C[:,3:4]*(z*z+C[:,2:3]*z+1.0))/(z*z+C[:,0:1]*z+C[:,1:2])
HON=coefs(imf('_v122_')); V235=coefs(imf('_v235_')); V232=coefs(imf('_v232_'))
ROUTE_BIQ={'ra4':coefs(imf('_v104_')),'ra5':coefs(imf('_v105_')),'ra6':coefs(imf('_v106_'))}

def measure(tag):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float); T=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m); PH=[];PW=[];F=None
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,Pyy=welch(y,fs=fs,nperseg=npg)
            _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            g=cxy>=0.30
            PH.append(np.where(g,np.angle(Pxy,deg=True),np.nan)); PW.append(np.where(g,Pyy,np.nan)); F=f
    return F,np.nanmedian(PH,axis=0),np.nanmedian(PW,axis=0)

FI=None; PHl=[]; PWl=[]
for tag,C in ROUTE_BIQ.items():
    F,ph,pw=measure(tag)
    h=Hv(C[None,:],F)[0]
    PHl.append(ph-np.degrees(np.angle(h)))          # de-embed the phase
    PWl.append(pw/np.maximum(np.abs(h)**2,1e-12))   # de-embed the power
    FI=F
PHI=np.nanmedian(PHl,axis=0); POW=np.nanmedian(PWl,axis=0)
s=(FI>=4)&(FI<=45)&np.isfinite(PHI)&np.isfinite(POW)
Fb,PHIb,POWb=FI[s],PHI[s],POW[s]/POW[s].sum()

print('  INTRINSIC lane (biquad divided out), pooled over 3 routes:')
print('  %-10s %10s %9s %12s' % ('band','cos(phi)','power %','contribution'))
tot=0.0
for lo,hi in ((4,7),(7,10),(10,13),(13,16),(16,19),(19,22),(22,26),(26,32),(32,38),(38,45)):
    m=(Fb>=lo)&(Fb<hi)
    if not m.any(): continue
    c=np.average(np.cos(np.deg2rad(PHIb[m])),weights=POWb[m]); p=POWb[m].sum()
    tot+=(POWb[m]*np.cos(np.deg2rad(PHIb[m]))).sum()
    print('  %-10s %10.3f %8.1f%% %+12.4f  %s' % ('%d-%d'%(lo,hi),c,100*p,
          (POWb[m]*np.cos(np.deg2rad(PHIb[m]))).sum(),'PUMPS' if c>0 else 'damps'))
print('  total %+.4f' % tot)
print()

def J(C):
    h=Hv(C,Fb)
    return (POWb[None,:]*np.abs(h)*np.cos(np.deg2rad(PHIb[None,:]+np.degrees(np.angle(h))))).sum(axis=1)
cand=[]
for fz in np.arange(16.0,60.01,0.5):
    for fp in np.arange(4.0,64.01,0.5):
        if fp>fz+8 or fp<fz-16: continue
        for r in np.arange(0.70,0.9801,0.01):
            tz,tp=2*np.pi*fz/FS,2*np.pi*fp/FS
            b0=-2*np.cos(tz); a8=-2*r*np.cos(tp); ac=r*r
            cand.append((a8,ac,b0,(1+a8+ac)/(2+b0),fz,fp,r))
cand=np.array(cand); C=cand[:,:4]
FA=np.arange(0.25,80.01,0.25); FL=np.arange(0.25,5.01,0.25)
FPB=np.arange(19.0,32.01,0.25); FD=np.arange(6.0,15.01,0.5)
i=np.flatnonzero(np.abs(Hv(C,FA)).max(axis=1)<=1.0)
i=i[np.abs(Hv(C[i],FL)).min(axis=1)>=0.99]
hp=np.abs(Hv(HON[None,:],FPB))[0]; i=i[(np.abs(Hv(C[i],FPB))<=hp[None,:]+1e-12).all(axis=1)]
hd=Hv(HON[None,:],FD)[0]; rat=Hv(C[i],FD)/hd[None,:]
i=i[(np.abs(np.degrees(np.angle(rat))).max(axis=1)<=8.0)&(np.abs(rat).min(axis=1)>=0.97)]
jj=J(C[i]); k=np.argmin(jj)
print('  RE-OPTIMISED ON THE DE-EMBEDDED LANE (%d candidates pass the gates)' % len(i))
print('    J(Honda) %+.5f   J(V232) %+.5f   J(V235) %+.5f'
      % (J(HON[None,:])[0], J(V232[None,:])[0], J(V235[None,:])[0]))
print('    OPTIMUM: zeros %.1f Hz, poles %.1f Hz, r %.2f   J %+.5f'
      % (cand[i[k],4],cand[i[k],5],cand[i[k],6],jj[k]))
print('    bytes %s' % struct.pack('<ffff',*C[i[k]]).hex())
print()
d=(J(V235[None,:])[0]-jj[k])/abs(jj[k])
print('  V235 is %.1f %% off the de-embedded optimum.' % (100*d))
print('  %s' % ('=> the de-embedding does NOT move the answer materially; V235 stands.'
                if abs(d)<0.05 and J(V235[None,:])[0] < J(HON[None,:])[0] else
                '=> the de-embedding MOVES the answer. V235 was optimised against a contaminated curve.'))
