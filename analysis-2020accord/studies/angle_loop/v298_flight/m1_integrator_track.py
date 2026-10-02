# m1_integrator_track.py -- M1: the REAL integrator state (I>>7, fitted per 2 s window with P and D fixed at the image arithmetic)
# vs the unbounded continuous replay, every 4 s along two engaged episodes.  ANALYSIS ONLY, cache-only, ~5 s.
import io, contextlib, numpy as np, time
import os
p=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'm1_loop_identity.py')
src=open(p,encoding='utf-8').read()
src=src[:src.index('# ================================================================================================ METHOD F')]
G={'__file__':p}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(src,p,'exec'),G)
src2=open(p,encoding='utf-8').read()
s2=src2[src2.index('RIN, ROUT = '):src2.index('# ---- exact per-tick')]
exec(compile(s2,p,'exec'),G)
zoh=G['zoh']; K=G['K']; t1ab=G['t1ab']; TAP=G['TAP']; tg=G['tg']; g=G['g']
for (A,B) in [(914.7,1074.7),(93.8,264.7)]:
    tk=np.arange(A,B,0.001)
    th,sp,abe,vw,tqs=G['lane_inputs'](tk); thp=np.r_[th[:1],th[:-1]]
    Ep,P,D,inc,f,frz,bound=G['lane_memoryless'](th,thp,sp,abe,vw,tqs)
    ramp=np.minimum(0x8000,328*np.arange(1,len(tk)+1)); inc=np.where(ramp>=0x8000,inc,0)
    I=np.cumsum(inc)
    PD=G['chain']((P+D)*f/256.0,ramp); one=G['chain'](f/256.0,ramp)  # per unit of I>>7
    Irep=G['chain']((I>>7)*f/256.0,ramp)
    print('episode',A,B)
    for t0 in np.arange(A+2,B-2,4.0):
        m=(t1ab>=t0)&(t1ab<t0+2)
        ti=t1ab[m]; y=TAP[m]
        pd=np.interp(ti,tk,PD); on=np.interp(ti,tk,one); ir=np.interp(ti,tk,Irep)
        # fit constant real I>>7 over the 2 s (P, D fixed; I increments inside 2 s ignored)
        Ireal=np.sum((y-pd)*on)/np.sum(on*on)
        j=np.searchsorted(tk,t0+1)
        mg=(tg>=t0)&(tg<t0+2)
        err=-(g['ew'][mg])/10.0
        print('  t %6.1f v %4.1f err %+5.2f deg |bar|max %4.0f tap %+5.1f | I>>7 real(fit) %+6.0f replay %+6.0f bound(E-dir) %+6.0f ang %+6.1f'%(
            t0,g['v'][mg].mean(),err.mean(),np.abs(g['bar'][mg]).max(),y.mean(),Ireal,I[j]>>7,np.sign(Ep[j])*bound[j],g['ang'][mg].mean()))
