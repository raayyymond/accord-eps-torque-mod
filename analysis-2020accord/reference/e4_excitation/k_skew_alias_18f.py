"""Three checks demanded before the numbers stand:
   A. +-2-sample skew sweep on the route-73 SIGNED gp-0x6b98 reconstruction.
   B. 0x18F column-torque band ratio, with the one-frame staleness swept -1/0/+1.
   C. Aliasing fold-in bound on 427 (fs = 49.835 Hz -> [40.835, 43.835] folds onto 6-9 Hz).
"""
import sys, numpy as np, json
sys.path.insert(0,'analysis-2020accord')
import e4_to_6b98_coherence as M
rng=np.random.default_rng(42)
NPS=512; WN=np.hanning(NPS); U=(WN**2).sum()
FS427=49.835

def blocks_of(msk,t):
    out=[]
    for a,b in M.episodes(msk,t,5.2):
        s=a;n=int(20*M.FS)
        while s+NPS<=b:
            e=min(s+n,b)
            if e-s>=NPS: out.append((s,e))
            s=e
    return out
def F(sig,blks):
    A=[]
    for a,b in blks:
        for s in range(a,b-NPS+1,NPS//2):
            x=sig[s:s+NPS]; A.append(np.fft.rfft((x-x.mean())*WN))
    return np.array(A)
def bandstat(X,Y,f,lo,hi,corr=True):
    b=M.band(f,lo,hi)
    sxx=(np.abs(X[:,b])**2).mean(0).sum(); syy=(np.abs(Y[:,b])**2).mean(0).sum()
    sxy=(np.conj(X[:,b])*Y[:,b]).mean(0).sum()
    c=float(np.mean(M.interp_corr(f[b]))) if corr else 1.0
    return (abs(sxy)**2/max(sxx*syy,1e-30), abs(sxy)/max(sxx,1e-30)/np.sqrt(c),
            float(np.sqrt(2*sxx/(U*NPS))), float(np.sqrt(2*syy/(U*NPS))/np.sqrt(c)))
def rmsband(X,f,lo,hi):
    b=M.band(f,lo,hi); return float(np.sqrt(2*(np.abs(X[:,b])**2).mean(0).sum()/(U*NPS)))

# ================= A. SKEW SWEEP on the signed reconstruction =================
z=dict(np.load('_scratch/cache/r73/r73.npz',allow_pickle=True))
t=np.asarray(z["t"],float); e4=np.asarray(z["e4tq"],float)
pr=np.asarray(z["probe"],int)&0xFF                # SAFE partner of t
abt=np.asarray(z["ab_t1ab"],float); mt=np.asarray(z["ab_mt"],float)
o=np.argsort(abt); abt,mt=abt[o],mt[o]
raw14_t=np.asarray(z["raw14_t"],float); raw14_b4=np.asarray(z["raw14_b4"],int)&0xFF
eng=np.asarray(z["e4req"],float)>0.5; press=np.asarray(z["cs_press"],float)>0.5
off=eng&~press
blks=blocks_of(off,t); f=np.fft.rfftfreq(NPS,1/M.FS)
E=F(e4,blks)
print("=== A. SKEW SWEEP: route 73 signed gp-0x6b98 = sign(0x14A b4 b7) * 427mag * 8 ===")
print("   engaged |gp-0x6b98| p50 = %.1f ct (kit record 208 ct); sign duty(neg) = %.4f"%(
    np.percentile(np.interp(t,abt,mt*8.0)[eng],50), (pr[eng]&0x80).astype(bool).mean()))
print("   skew   g2(0.5-3)  H1(0.5-3)   g2(6-9)   H1(6-9)   g2(20-24)   sign-flip rate /s")
for sk in (-2,-1,0,1,2):
    k=np.clip(np.searchsorted(t,abt)+sk,0,len(t)-1)
    sgn=np.where((pr[k]&0x80)!=0,-1.0,1.0)
    y=np.interp(t,abt,sgn*mt*8.0)
    Y=F(y,blks)
    r1=bandstat(E,Y,f,0.5,3.0); r2=bandstat(E,Y,f,6.0,9.0); r3=bandstat(E,Y,f,20.,24.)
    fl=np.mean(np.abs(np.diff(sgn))>0)*FS427
    print("   %+d     %7.4f    %6.3f     %7.4f   %6.3f    %7.4f      %.2f"%(sk,r1[0],r1[1],r2[0],r2[1],r3[0],fl))
# the raw14 pair as an independent route to the same sign
k2=np.clip(np.searchsorted(raw14_t,abt),0,len(raw14_t)-1)
sgn2=np.where((raw14_b4[k2]&0x80)!=0,-1.0,1.0)
y2=np.interp(t,abt,sgn2*mt*8.0); Y2=F(y2,blks)
r1=bandstat(E,Y2,f,0.5,3.0); r2=bandstat(E,Y2,f,6.0,9.0)
print("   (raw14_t,raw14_b4) independent pair:      g2(0.5-3)=%.4f H1=%.3f | g2(6-9)=%.4f H1=%.3f"%(r1[0],r1[1],r2[0],r2[1]))

# ================= B. 0x18F COLUMN TORQUE band ratio, staleness swept =========
print("\n=== B. 0x18F STEER_TORQUE_SENSOR band ratio (tq = i16be(0x18F,0)*-1, HELD-LAST => 1 frame stale) ===")
tq=np.asarray(z["tq"],float)
for route in ["73","75","76"]:
    zz=dict(np.load('_cache_r%s/r%s.npz'%(route,route),allow_pickle=True))
    tt=np.asarray(zz["t"],float); ee=np.asarray(zz["e4tq"],float); qq=np.asarray(zz["tq"],float)
    en=np.asarray(zz["e4req"],float)>0.5; pp=np.asarray(zz["cs_press"],float)>0.5
    bl=blocks_of(en&~pp,tt)
    if len(bl)<4: continue
    Ee=F(ee,bl)
    print("  route %s HANDS-OFF (%d blocks)"%(route,len(bl)))
    for sh in (-1,0,1):
        q=np.roll(qq,-sh)   # sh=+1 advances tq one row = the staleness correction
        Q=F(q,bl)
        a=bandstat(Ee,Q,f,0.5,3.0,corr=False); c=bandstat(Ee,Q,f,6.0,9.0,corr=False)
        print("     shift %+d row  H1(0.5-3)=%.4f  H1(6-9)=%.4f  RATIO 6-9/0.5-3 = %.3f   [g2 %.4f / %.4f]"%(
            sh,a[1],c[1],c[1]/max(a[1],1e-30),a[0],c[0]))

# ================= C. ALIASING FOLD-IN BOUND ==================================
print("\n=== C. 427 ALIASING FOLD-IN (fs=49.835 => [%.3f, %.3f] Hz folds onto 6-9 Hz) ==="%(FS427-9,FS427-6))
print("    instrument: 0x18F column torque at 100 Hz -- unaliased to 50 Hz -- used for the SHAPE only [BELIEF]")
for route in ["73","75","76"]:
    zz=dict(np.load('_cache_r%s/r%s.npz'%(route,route),allow_pickle=True))
    tt=np.asarray(zz["t"],float); qq=np.asarray(zz["tq"],float)
    en=np.asarray(zz["e4req"],float)>0.5; pp=np.asarray(zz["cs_press"],float)>0.5
    bl=blocks_of(en&~pp,tt)
    if len(bl)<4: continue
    Q=F(qq,bl)
    p69=rmsband(Q,f,6,9)**2/3.0
    pfold=rmsband(Q,f,FS427-9,FS427-6)**2/3.0
    p2024=rmsband(Q,f,20,24)**2/4.0
    pf2024=rmsband(Q,f,FS427-24,FS427-20)**2/4.0
    R=pfold/max(p69,1e-30)
    print("  route %s: 0x18F PSD 6-9Hz %8.1f | PSD %.1f-%.1fHz %8.1f  => fold ratio R = %.4f"%(
        route,p69,FS427-9,FS427-6,pfold,R))
    print("            (20-24Hz check: PSD %8.1f vs folding band %8.1f => R = %.4f)"%(p2024,pf2024,pf2024/max(p2024,1e-30)))
