import sys, os, glob
sys.path.insert(0, os.path.abspath('rlog-tools/score'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from scipy import signal, stats
import impedance_phase_delay_test as T

rows=[]
for c in sorted(glob.glob('_scratch/cache/*/*.npz')):
    try: z=np.load(c, allow_pickle=True)
    except Exception: continue
    if not {'tq','rate_f','cc_lat','t'} <= set(z.files): continue
    eng=np.asarray(z['cc_lat'],float)>0.5
    tq=np.asarray(z['tq'],float); rt=np.asarray(z['rate_f'],float)
    n=min(len(eng),len(tq),len(rt)); eng,tq,rt=eng[:n],tq[:n],rt[:n]
    if eng.sum()<3000: continue
    t=np.asarray(z['t'],float)[:n]; fs=1.0/np.median(np.diff(t))
    x,y=tq[eng],rt[eng]
    if len(x)<8192: continue
    f,Pxy=signal.csd(y,x,fs,nperseg=1024)
    _,Pxx=signal.welch(y,fs,nperseg=1024); _,Pyy=signal.welch(x,fs,nperseg=1024)
    coh=np.abs(Pxy)**2/np.maximum(Pxx*Pyy,1e-30)
    m=(f>=3)&(f<=20)&(coh>=0.30)
    if m.sum()<8: continue
    ph=np.unwrap(np.angle(Pxy[m])); ff=f[m]
    A=np.vstack([ff,np.ones_like(ff)]).T
    sol,_,_,_=np.linalg.lstsq(A,ph,rcond=None)
    r2=1-((ph-A@sol)**2).sum()/max(((ph-ph.mean())**2).sum(),1e-30)
    tau=-sol[0]/(2*np.pi)
    if not (0.005 < tau < 0.10) or r2 < 0.5: continue
    # the ZERO CROSSING of Re(Z): lowest f in 3-20 where Re(Z) turns negative and stays
    band=(f>=3)&(f<=20)
    re=np.real(Pxy[band]); fb=f[band]
    neg=np.where(re<0)[0]
    fx = fb[neg[0]] if len(neg) else np.nan
    # and the frequency of MOST NEGATIVE Re(Z), normalised by band power
    k=np.argmin(re/np.maximum(np.abs(Pxy[band]),1e-30))
    fmin=fb[k]
    rows.append((os.path.basename(c), 1000*tau, r2, 1/(4*tau), fx, fmin))
    if len(rows)>=40: break

print('TAU vs THE ANTI-DAMPING CROSSOVER -- does the delay SET the frequency?\n')
print('  %-14s %8s %6s %10s %10s %10s' % ('route','tau ms','R^2','1/(4tau)','Re<0 from','most neg'))
print('  '+'-'*66)
for r in sorted(rows, key=lambda x:x[1])[:26]:
    print('  %-14s %8.2f %6.3f %10.2f %10.2f %10.2f' % r)
if len(rows)>4:
    q=np.array([r[3] for r in rows]); fx=np.array([r[4] for r in rows]); fm=np.array([r[5] for r in rows])
    ok=np.isfinite(fx)
    print('  '+'-'*66)
    print('  %d routes' % len(rows))
    for nm,v in (('crossover Re(Z)<0', fx[ok]), ('most-negative f', fm[ok])):
        rr=stats.pearsonr(q[ok], v)
        sp=stats.spearmanr(q[ok], v)
        print('  1/(4tau) vs %-18s  pearson r=%+.3f p=%.4f   spearman rho=%+.3f p=%.4f'
              % (nm, rr[0], rr[1], sp[0], sp[1]))
    print('  median 1/(4tau) = %.2f Hz   median crossover = %.2f Hz   median most-neg = %.2f Hz'
          % (np.median(q), np.median(fx[ok]), np.median(fm[ok])))
    print()
    print('  \U0001f6d1 CONTROL: a POSITIVE correlation is what the delay hypothesis predicts.')
    print('     A null correlation means tau and the crossover are independent, and the linear')
    print('     phase fit is describing something other than the mechanism that sets the ratchet.')
