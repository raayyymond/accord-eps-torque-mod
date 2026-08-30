# -*- coding: utf-8 -*-
"""OPTIMISE THE BIQUAD DIRECTLY AGAINST NET DAMPING, weighted by the lane's own measured spectrum.

V232's geometry was chosen on |H| proxies -- cut 22-40, hold 6-15 -- before net damping existed as a
metric here. The real objective is the energy the lane exchanges with the column per unit time:

    J(C) = SUM_f  |C(f)/Honda(f)| * cos( phi_meas(f) + arg(C(f)/Honda(f)) ) * P_meas(f)

phi_meas and P_meas are measured PER BIN on gp-0x6b86 (ra4/ra5/ra6, engaged, coherence-gated), so the
band table is replaced by the real curve. cos < 0 is damping, so J is minimised (most negative) when the
lane removes the most energy. Honda's own geometry is J = J0 by construction.

Safety gates carried from the builders, non-negotiable:
  * 0-5 Hz passband floor >= 0.99   (must notch, not turn base assist down)
  * peak |H| <= 1.03 below 20 Hz    (no resonance where the mode lives)
  * r <= 0.98                       (float32 pole margin)
"""
import cmath, glob, math, os, struct, sys
import numpy as np
from scipy.signal import csd, welch, coherence
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
FS=1000.0; R=os.environ['ACCORD_FIRMWARE_ROOT']+'/analysis-2020accord/'
A8,AC,B0,B4=0xC60A8,0xC60AC,0xC60B0,0xC60B4
def f32(b,o): return struct.unpack_from('<f',b,o)[0]
def imgf(p):
    g=[q for q in glob.glob(R+'*plain_image.bin')
       if p in os.path.basename(q) and not os.path.basename(q).startswith('SUPERSEDED')]
    return open(g[0],'rb').read() if g else None
HON=tuple(f32(imgf('_v122_'),o) for o in (A8,AC,B0,B4))
V232=tuple(f32(imgf('_v232_'),o) for o in (A8,AC,B0,B4))
def H(c,f):
    a8,ac,b0,b4=c; z=cmath.exp(2j*math.pi*f/FS)
    return b4*(z*z+b0*z+1.0)/(z*z+a8*z+ac)
def coeffs(fz,fp,r):
    tz,tp=2*math.pi*fz/FS,2*math.pi*fp/FS
    b0=-2*math.cos(tz); a8=-2*r*math.cos(tp); ac=r*r
    return a8,ac,b0,(1+a8+ac)/(2+b0)

# ---- measure phi(f) and P(f) per bin on the notch lane ----
acc_ph, acc_p, F = [], [], None
for tag in ('ra4','ra5','ra6'):
    p='analysis-2020accord/_scratch/cache/%s/%s.npz'%(tag,tag)
    if not os.path.exists(p): continue
    z=np.load(p,allow_pickle=True); ks=set(z.files)
    if not {'t','cs_rate','cc_lat','tq'} <= ks: continue
    t=np.asarray(z['t']).astype(float); fs=1/np.median(np.diff(t))
    w=np.asarray(z['cs_rate']).astype(float); T=np.asarray(z['tq']).astype(float)
    m=np.asarray(z['cc_lat']).astype(float)>0.5
    if 'cs_v' in ks: m &= np.abs(np.asarray(z['cs_v']).astype(float))>0.3
    n=int(round(20*fs)); idx=np.flatnonzero(m); PH=[];PW=[]
    for run in np.split(idx,np.flatnonzero(np.diff(idx)>1)+1):
        for k in range(0,len(run)-n+1,n):
            s=run[k:k+n]; x=w[s]-w[s].mean(); y=T[s]-T[s].mean()
            npg=min(len(s),int(round(4*fs)))
            f,Pxy=csd(x,y,fs=fs,nperseg=npg); _,Pyy=welch(y,fs=fs,nperseg=npg)
            _,cxy=coherence(x,y,fs=fs,nperseg=npg)
            g=cxy>=0.30
            PH.append(np.where(g,np.angle(Pxy,deg=True),np.nan)); PW.append(np.where(g,Pyy,np.nan))
            F=f
    if PH:
        acc_ph.append(np.nanmedian(PH,axis=0)); acc_p.append(np.nanmedian(PW,axis=0))
PHI=np.nanmedian(acc_ph,axis=0); POW=np.nanmedian(acc_p,axis=0)
band=(F>=4)&(F<=45)&np.isfinite(PHI)&np.isfinite(POW)
Fb, PHIb, POWb = F[band], PHI[band], POW[band]
POWb = POWb/POWb.sum()
print('  measured lane: %d usable bins, %.1f-%.1f Hz' % (len(Fb),Fb.min(),Fb.max()))
print('  power-weighted mean cos(phi) with Honda in place: %+.4f  (negative = net damping)'
      % np.sum(POWb*np.cos(np.deg2rad(PHIb))))
print()

def J(c):
    rat=np.array([H(c,f)/H(HON,f) for f in Fb])
    return float(np.sum(POWb*np.abs(rat)*np.cos(np.deg2rad(PHIb+np.degrees(np.angle(rat))))))
def gates(c):
    if min(abs(H(c,f)) for f in np.arange(0.25,5.01,0.25)) < 0.99: return False
    if max(abs(H(c,f)) for f in np.arange(0.5,20.01,0.25)) > 1.03: return False
    # NO-BOOST CONSTRAINT, added after V233 failed its builder gate. The optimiser had found a
    # geometry that BOOSTS the pumping band 1.27-1.83x and relies on a ~70 deg phase rotation to
    # neutralise the product -- a knife-edge, and exactly the class of sign assumption that produced
    # the aborted V94 drive. Any benefit must now come from genuine attenuation, not boost+rotation.
    for f in np.arange(19.0,32.01,0.25):
        if abs(H(c,f)) > abs(H(HON,f)): return False
    return True

J0, J232 = J(HON), J(V232)
print('  J(Honda) = %+.5f      J(V232) = %+.5f   (%.1f %% better)' % (J0,J232,100*(J0-J232)/abs(J0)))
print()
best=None
for fz in np.arange(20.0,60.01,0.5):
    for fp in np.arange(max(4.0,fz-16),fz+8.01,0.5):
        for r in np.arange(0.70,0.9801,0.01):
            c=coeffs(fz,fp,r)
            if not gates(c): continue
            j=J(c)
            if best is None or j<best[0]: best=(j,fz,fp,r,c)
j,fz,fp,r,c=best
print('  OPTIMUM: zeros %.1f Hz, poles %.1f Hz, r %.2f' % (fz,fp,r))
print('    J = %+.5f   vs Honda %+.5f   vs V232 %+.5f' % (j,J0,J232))
print('    improvement over Honda %.1f %%,  over V232 %.1f %%'
      % (100*(J0-j)/abs(J0), 100*(J232-j)/abs(J232)))
print('    bytes %s' % struct.pack('<ffff',*c).hex())
print('    |H| 7.79 %.4f  10.5 %.4f  18.5 %.4f  30 %.4f  55 %.4f'
      % tuple(abs(H(c,f)) for f in (7.79,10.5,18.5,30.0,55.0)))
print('    0-5 Hz floor %.4f' % min(abs(H(c,f)) for f in np.arange(0.25,5.01,0.25)))


print()
print('='*96)
print('  RE-OPTIMISED under the NO-BOOST constraint in the pumping band')
print('='*96)
best2=None
for fz in np.arange(16.0,50.01,0.5):
    for fp in np.arange(max(4.0,fz-16),fz+8.01,0.5):
        for r in np.arange(0.70,0.9801,0.01):
            cc=coeffs(fz,fp,r)
            if not gates(cc): continue
            jj=J(cc)
            if best2 is None or jj<best2[0]: best2=(jj,fz,fp,r,cc)
if best2 is None:
    print('  nothing qualifies under the no-boost constraint.')
else:
    jj,fz2,fp2,r2,c2=best2
    print('  OPTIMUM: zeros %.1f Hz, poles %.1f Hz, r %.2f' % (fz2,fp2,r2))
    print('    J %+.5f   Honda %+.5f   V232 %+.5f   (%.1f %% better than Honda, %.1f %% than V232)'
          % (jj,J0,J232,100*(J0-jj)/abs(J0),100*(J232-jj)/abs(J232)))
    print('    bytes %s' % struct.pack('<ffff',*c2).hex())
    print('    |H| 7.79 %.4f  10.5 %.4f  18.5 %.4f  26 %.4f  30 %.4f  55 %.4f'
          % tuple(abs(H(c2,f)) for f in (7.79,10.5,18.5,26.0,30.0,55.0)))
    print('    Honda   7.79 %.4f  10.5 %.4f  18.5 %.4f  26 %.4f  30 %.4f  55 %.4f'
          % tuple(abs(H(HON,f)) for f in (7.79,10.5,18.5,26.0,30.0,55.0)))
    print('    0-5 Hz floor %.4f' % min(abs(H(c2,f)) for f in np.arange(0.25,5.01,0.25)))
    BANDS=[('6-9',6,9,-0.918),('9-12',9,12,-0.989),('12-15',12,15,-0.629),
           ('22-30',22,30,+0.936),('30-40',30,40,+0.821)]
    cells=[]
    for nm,lo,hi,cm in BANDS:
        phm=math.degrees(math.acos(cm))
        v=np.mean([abs(H(c2,f)/H(HON,f))*math.cos(math.radians(phm+math.degrees(cmath.phase(H(c2,f)/H(HON,f)))))/cm
                   for f in np.linspace(lo,hi,40)])
        cells.append(v)
    print('    net: %s' % '  '.join('%s %.3fx'%(BANDS[i][0],cells[i]) for i in range(5)))
    print('    damping bands %.3fx   pumping bands %+.3fx   (V232: 0.944x / +0.285x)'
          % (np.mean(cells[:3]),np.mean(cells[3:])))
    print()
    print('    ROBUSTNESS to phase error:')
    def JS(cand,d):
        rat=np.array([H(cand,f)/H(HON,f) for f in Fb])
        return float(np.sum(POWb*np.abs(rat)*np.cos(np.deg2rad(PHIb+d+np.degrees(np.angle(rat))))))
    print('      %s' % '  '.join('%+d: %+.4f'%(d,JS(c2,d)) for d in (-30,-15,0,15,30)))
    print('      V232 %s' % '  '.join('%+d: %+.4f'%(d,JS(V232,d)) for d in (-30,-15,0,15,30)))
