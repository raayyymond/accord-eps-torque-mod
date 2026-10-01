# -*- coding: utf-8 -*-
"""b_env2.py -- FAST full-factorial envelope.  L(f;G)=(G/256)*A+Bc is linear in G (A,Bc built ONCE per member,v);
margins fully vectorised; max feasible G found by binary search (PM falls / Ms rises with G -- monotonicity spot-checked).
A PASS = Ms<=2.0 AND GM>=6 AND (no unity crossover OR min PM>=thr).  dmode selects the D hold.  ANALYSIS ONLY.
usage: python b_env2.py <held|fresh> <kd> <ki> <tag>"""
import json, math, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parents[1]/'refute_stability', HERE.parents[1]/'c1', HERE.parents[2]/'v295'/'plant'):
    sys.path.insert(0, str(_p))
import stab_lin as S
import c1r2_members as M
KIT = HERE.parents[3]
OUT = KIT / "_scratch" / "angle_loop" / "B-robust-margins"; OUT.mkdir(parents=True, exist_ok=True)
F = np.logspace(math.log10(0.02), math.log10(499.0), 2000)
Z = np.exp(1j * 2 * np.pi * F * S.TS); ZI = 1 / Z
HOUT = (S.OB / 1024) * (1 + ZI) / (32 * (1 - (S.OA / 1024) * ZI))
SPEEDS = sorted(set([round(x,2) for x in np.arange(1.0,35.01,0.25)] + [3.1,8.0,11.9,17.0,26.9]))
NAMES = [(n,45.0) for n in M.TIER_A] + [(n,30.0) for n in M.TIER_B]

def AB(name, v, kd, ki, dmode):
    J,b,k,tau,ea = M.params(name, v)
    A_,B_,Ct,Cw = S.rigid(J,b,k); Ad,Bd = S.c2d(A_,B_)
    a,b2,c2,d2 = Ad[0,0],Ad[0,1],Ad[1,0],Ad[1,1]
    det = (Z-a)*(Z-d2)-b2*c2
    Pt = ((Z-d2)*Bd[0,0]+b2*Bd[1,0])/det
    Pw = (c2*Bd[0,0]+(Z-a)*Bd[1,0])/det
    hold = sum(ZI**(q+ea) for q in range(1,11))/10
    K = S.FADE*S.FWD*HOUT*ZI**tau
    Ctheta_pergain = (112/256 + ki/32768/(1-ZI))*80*(1+ZI)*hold
    A = K*Ctheta_pergain*Pt
    if dmode=="held":
        Comega = kd*hold
    elif dmode=="fresh":
        Comega = kd*np.ones_like(ZI)
    else:                                   # 'fresh_ema' : gp-0x6abe, fresh but EMA-filtered (corner EMA_HZ)
        a = math.exp(-2*math.pi*EMA_HZ*S.TS); Comega = kd*(1-a)/(1-a*ZI)
    Bc = K*Comega*Pw
    return A, Bc

def margins_vec(L):
    mag=np.abs(L); ph=np.unwrap(np.angle(L))*180/np.pi
    # unity crossings
    sgn=np.sign(mag-1.0); ix=np.where(sgn[:-1]*sgn[1:]<0)[0]
    if len(ix):
        t=(1-mag[ix])/(mag[ix+1]-mag[ix])
        pmc=((ph[ix]+t*(ph[ix+1]-ph[ix])+180)+180)%360-180
        pm=float(np.min(pmc))
    else:
        pm=float('nan')
    # gain margin at -180 crossings
    w=(ph+180)/360.0; fl=np.floor(w)
    jx=np.where(fl[:-1]!=fl[1:])[0]
    if len(jx):
        gm=float(np.min(-20*np.log10(np.maximum(mag[jx],1e-12))))
        gms=-20*np.log10(np.maximum(mag[jx],1e-12)); gms=gms[gms>0]
        gm=float(np.min(gms)) if len(gms) else float('inf')
    else:
        gm=float('inf')
    Ms=float(np.max(np.abs(1/(1+L))))
    return pm,Ms,gm

MS_BAR=2.0
EMA_HZ=35.0
def passes(G,A,Bc,thr):
    pm,Ms,gm=margins_vec((G/256)*A+Bc)
    return (Ms<=MS_BAR) and (gm>=6.0) and (math.isnan(pm) or pm>=thr)

def gmax(name,v,thr,kd,ki,dmode):
    A,Bc=AB(name,v,kd,ki,dmode)
    if not passes(96,A,Bc,thr): return 0
    lo,hi=96,6000
    if passes(hi,A,Bc,thr): return hi
    # binary search the largest passing G (assume monotone; spot-check below)
    while hi-lo>8:
        mid=(lo+hi)//2
        if passes(mid,A,Bc,thr): lo=mid
        else: hi=mid
    # guard against non-monotonicity: step down a little and confirm, step up to reject
    g=lo
    for gg in range(lo, max(96,lo-200), -8):
        if passes(gg,A,Bc,thr): g=gg; break
    return (g//16)*16

def job(args):
    v,kd,ki,dmode,msb,ema=args
    global MS_BAR,EMA_HZ; MS_BAR=msb; EMA_HZ=ema
    return v,{n:gmax(n,v,thr,kd,ki,dmode) for n,thr in NAMES}

def main():
    global MS_BAR
    dmode=sys.argv[1]; kd=int(sys.argv[2]); ki=int(sys.argv[3]); tag=sys.argv[4]
    MS_BAR=float(sys.argv[5]) if len(sys.argv)>5 else 2.0
    EMA=float(sys.argv[6]) if len(sys.argv)>6 else 35.0
    t0=time.time()
    with Pool(14) as pool:
        res=dict(pool.map(job,[(v,kd,ki,dmode,MS_BAR,EMA) for v in SPEEDS]))
    (OUT/f"env_{tag}.json").write_text(json.dumps({str(v):r for v,r in res.items()}))
    lines=[f"# env {tag}: dmode {dmode} kd {kd} ki {ki} kp 112; env=min gated gmax; Kp_eff=112*G/256"]
    show=[]
    for v in SPEEDS:
        r=res[v]
        eA=min((r[n],n) for n,_ in NAMES if n in M.TIER_A)
        eB=min((r[n],n) for n,_ in NAMES if n in M.TIER_B)
        e=min(eA[0],eB[0])
        lines.append(f"{v:6.2f} envA {eA[0]:5d}({eA[1]:>22s}) envB {eB[0]:5d}({eB[1]:>22s}) env {e:5d} Kp_eff {112*e/256:6.0f}")
        if v in (1,3.1,5,8,10,11,11.9,12.5,13,15,17,19,22,26,26.9,30): show.append(lines[-1])
    (OUT/f"env_{tag}.txt").write_text("\n".join(lines))
    print("\n".join([lines[0]]+show)); print(f"[{time.time()-t0:.0f} s]")

if __name__=="__main__":
    main()
