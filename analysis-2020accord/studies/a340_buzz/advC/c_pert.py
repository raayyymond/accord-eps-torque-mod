import sys,os,math,itertools,time
t0=time.time()
KIT="C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0,KIT+"/analysis-2020accord/studies/release")
import numpy as np
import gate2_rescore_stock_terms as G
HF=G.HF; ZI=G.zi
FH=np.unique(np.concatenate([np.logspace(-1,math.log10(480.0),900),[5.0,30.0,200.0]]))
ROWS_S=list(G.DA_Y_S); AUTH=5328/5346
def F_da(f,v,rows,K2,dl,scale):
    Y=float(np.interp(v*3.6*64.0,G.DA_X,rows))
    chain=1024.0*G.ema(f,37/128.0)*(1-G.zi(f))*32.0*G.ema(f,K2/64.0)/512.0
    return scale*Y*G.DA_SCALE*chain*G.KAPPA_M*(2j*np.pi*np.asarray(f,float))*G.zi(f)**dl
fm,Hm,cohm,_,_=G.measure_htb(); HTBH=G.htb_model(FH,G.fit_two_mass(fm,Hm,cohm))
def case(v,bm,km,Jm,dl,xd,scale,f2=None,r2=0.0,z2=0.03):
    c=G.ctl_v299(v); pn=HF.plant_at('nominal',v)
    kw=dict(J=Jm/(1-r2) if r2 else Jm,b=pn.b*bm,k=pn.k*km)
    if r2: kw.update(f2=f2,zeta2=z2,r2=r2)
    P=HF.Plant(**kw).frf(FH)
    Fr=G.F_r24(FH,v,G.r24_gain_stock(v)-2.0,-1.0,HTBH)
    Fl=F_da(FH,v,ROWS_S,22,dl,scale)
    Pc=P/(1-P*(Fl+Fr))*AUTH
    L=G.C_fb_v299(FH,c)*Pc*ZI(FH)**xd
    mag=np.abs(L); ph=np.unwrap(np.angle(L))
    im=L.imag; jx=np.where((np.sign(im[:-1])!=np.sign(im[1:]))&(L.real[:-1]<0))[0]
    below=[abs(L[j]) for j in jx if abs(L[j])<1.0]; above=[abs(L[j]) for j in jx if abs(L[j])>=1.0]
    gm=20*math.log10(1/max(below)) if below else 99.
    S=1/(1+L);T=L*S; b=(FH>=5)&(FH<=30)
    return gm,20*math.log10(np.abs(T[b]).max()),FH[b][np.argmax(np.abs(T[b]))],np.abs(S).max(),bool(above)
if __name__=="__main__":
    print("probe v=1:",case(1.0,1,1,0.035,2,0,1)); print("central v=3:",case(3.0,1.6,1.3,0.035,2,0,1))
    # one-at-a-time from central (b1.6,k1.3,Jm .035, lane dl 2, extra angle delay 0, lane scale 1)
    base=dict(bm=1.6,km=1.3,Jm=0.035,dl=2,xd=0,scale=1.0)
    for v in (1.0,3.0,5.0,8.0):
        print(f"--- v={v} central:",["%.1f"%x if not isinstance(x,bool) else x for x in case(v,**base)])
        for name,vals in (('bm',(0,0.1,0.2,0.3,0.5,1.0)),('km',(0.7,1.0,2.0)),('Jm',(0.012,0.02,0.07,0.15)),('dl',(3,4,5)),('xd',(5,10,20)),('scale',(0.5,2.0))):
            out=[]
            for x in vals:
                kw=dict(base);kw[name]=x;g,T,fT,Ms,en=case(v,**kw)
                out.append(f"{name}={x}:GM{g:.1f}/T{T:+.1f}@{fT:.0f}{'*' if (g<3 or T>6) else ('f' if (g<6 or T>3) else '')}")
            print('   ',' '.join(out))
    # two-mass
    print('--- two-mass 10-20 Hz, zeta .03, rim share .3/.6, b x0.5/1.6, v=3,8')
    for v in (3.0,8.0):
      for f2 in (10,13,16.5,20):
        for r2 in (0.3,0.6):
          for bm in (0.5,1.6):
            g,T,fT,Ms,en=case(v,bm,1.3,0.035,2,0,1.0,f2,r2)
            print(f'   v{v} f2={f2} r2={r2} b{bm}: GM{g:.1f} T{T:+.1f}@{fT:.0f}'+(' *' if (g<3 or T>6) else (' f' if g<6 or T>3 else '')))
    # nearest failing: grid, min multiplicative distance from central in (bm down, km down, Jm down, dl up, scale)
    best=[]
    for v in (3.0,5.0,8.0):
      for bm,km,Jm,dl,xd,sc in itertools.product((1.6,1.0,0.7,0.5,0.3,0.2,0.1,0.0),(1.3,1.0,0.7),(0.035,0.02,0.012),(2,3,4),(0,10,20),(1.0,0.5)):
        g,T,fT,Ms,en=case(v,bm,km,Jm,dl,xd,sc)
        if g<6 or T>3:
            d=abs(math.log(1.6/max(bm,0.03)))+abs(math.log(1.3/km))+abs(math.log(0.035/Jm))+0.3*(dl-2)+0.05*xd+abs(math.log(sc))
            best.append((d,v,bm,km,Jm,dl,xd,sc,g,T,fT))
    best.sort()
    print('nearest failing points (dist, v,bm,km,Jm,dl,xd,scale | GM, T, fT):')
    for b in best[:12]: print('  %.2f v%g bm%.2f km%.1f Jm%.3f dl%d xd%d sc%.1f | GM%.1f T%+.1f@%.0f'%b)
    print('wall %.1f s'%(time.time()-t0))
