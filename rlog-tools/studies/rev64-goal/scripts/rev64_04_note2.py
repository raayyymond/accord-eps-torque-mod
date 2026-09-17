"""NOTE 2 DIRECTLY: "a tiny, tiny bit of looseness ... fixed lane centering on straight roads,
like 5-10 seconds per oscillation" = 0.10-0.20 Hz.

Band TF says rev 6.4 OVER-delivers 1.235 at 0.15-0.30 Hz on the highway where rev 5 was 1.027.
Excess loop gain in that band is exactly what produces a slow overshoot cycle.

Two things to establish:
  (a) Is the over-delivery real? Cross-check the cross-spectral |H| with an INDEPENDENT
      time-domain band-passed regression (different estimator, same data).
  (b) Is there a spectral PEAK in the achieved lateral accel at 0.10-0.20 Hz on STRAIGHT roads
      that is NOT in the model's desired lateral accel? That is a loop-generated oscillation
      rather than faithful tracking of a wobbly setpoint.
"""
import math, numpy as np
from scipy import signal
CA='analysis-2020accord/_scratch/cache/tau/'
def load(f):
    D=np.load(CA+f,allow_pickle=True); t=D['t_cs']
    return dict(t=t,FS=1.0/float(np.median(np.diff(t))),act=D['cs_active'].astype(bool),
                sa=np.interp(t,D['t_cst'],D['sa_deg']),v=np.interp(t,D['t_cst'],D['vego']),
                pr=np.interp(t,D['t_cst'],D['spress'])>0.5,lad=D['cs_la_des'],laa=D['cs_la_act'])
A=load('r6c_rev64_ident.npz'); B=load('r6d_rev64_ident.npz'); C=load('r76_v293_ident.npz')
FS=A['FS']

def straight_runs(S,minlen):
    t=S['t']; m=S['act']&~S['pr']&(S['v']>15.0)
    # straight = small desired lateral accel, smoothed so a brief blip does not split a run
    sm=np.convolve(np.abs(S['lad']),np.ones(201)/201,mode='same')
    m=m&(sm<0.35)
    out,n,i=[],len(m),0
    while i<n:
        if not m[i]: i+=1; continue
        j=i
        while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
        if (j+1-i)/FS>=minlen: out.append((i,j+1))
        i=j+1
    return out

print("="*96)
print("(a) INDEPENDENT CROSS-CHECK of the over-delivery: band-passed time-domain regression")
print("    (zero-phase filtfilt bandpass on both signals, then slope of achieved on desired)")
print("="*96)
def bp_slope(sets,f1,f2,vlo,vhi,minlen=20.):
    sos=signal.butter(4,[f1,f2],btype='band',fs=FS,output='sos')
    num=den=0.0; sec=0.0; per=[]
    for S in sets:
        t=S['t']; m=S['act']&~S['pr']&(S['v']>=vlo)&(S['v']<vhi)
        n,i=len(m),0
        while i<n:
            if not m[i]: i+=1; continue
            j=i
            while j+1<n and m[j+1] and (t[j+1]-t[j])<4.0/FS: j+=1
            if (j+1-i)/FS>=minlen:
                x=signal.sosfiltfilt(sos,S['lad'][i:j+1]); y=signal.sosfiltfilt(sos,S['laa'][i:j+1])
                e=int(2.0*FS)  # drop filter edges
                x,y=x[e:-e],y[e:-e]
                if len(x)>100:
                    num+=float(np.dot(x,y)); den+=float(np.dot(x,x)); sec+=len(x)/FS
                    per.append(float(np.dot(x,y)/max(np.dot(x,x),1e-12)))
            i=j+1
    return (num/den if den>0 else float('nan')), sec, len(per), (np.std(per) if len(per)>1 else float('nan'))
print(f"  {'band':>14} {'rev 6.4 slope':>14} {'rev 5 slope':>13} {'6.4 sec':>9} {'6.4 per-run sd':>15}")
for lbl,f1,f2 in [('0.10-0.20 Hz',0.10,0.20),('0.15-0.30 Hz',0.15,0.30),('0.30-0.60 Hz',0.30,0.60)]:
    s64,sec,nr,sd=bp_slope([A,B],f1,f2,15.,34.)
    s5,_,_,_=bp_slope([C],f1,f2,15.,34.)
    print(f"  {lbl:>14} {s64:14.3f} {s5:13.3f} {sec:9.0f} {sd:15.3f}")

print()
print("="*96)
print("(b) IS THERE A LOOP-GENERATED OSCILLATION ON STRAIGHTS?")
print("    excess = achieved PSD / desired PSD on straight highway runs. >1 = the car adds motion")
print("    the model never asked for.")
print("="*96)
for tag,sets in [('REV 6.4',[A,B]),('REV 5',[C])]:
    segs=[]
    for S in sets:
        for a,b in straight_runs(S,40.):
            segs.append((S['lad'][a:b],S['laa'][a:b],S['sa'][a:b]))
    if not segs: print(f"\n  {tag}: no straight highway run >= 40 s"); continue
    nps=int(2**np.floor(np.log2(min(len(x) for x,_,_ in segs))))
    Pd=Pa=None; fr=None; sec=0
    for x,y,_ in segs:
        f,pd=signal.welch(x-x.mean(),FS,nperseg=nps,noverlap=nps//2)
        _,pa=signal.welch(y-y.mean(),FS,nperseg=nps,noverlap=nps//2)
        w=len(x); Pd=pd*w if Pd is None else Pd+pd*w; Pa=pa*w if Pa is None else Pa+pa*w
        fr=f; sec+=w/FS
    print(f"\n  {tag}: {len(segs)} straight runs, {sec:.0f} s, df={fr[1]-fr[0]:.4f} Hz")
    print(f"    {'freq Hz':>9} {'desired PSD':>13} {'achieved PSD':>13} {'excess':>8}")
    for lo,hi in [(0.05,0.10),(0.10,0.15),(0.15,0.20),(0.20,0.30),(0.30,0.45),(0.45,0.70)]:
        s=(fr>=lo)&(fr<hi)
        if s.sum()<1: continue
        d,a_=Pd[s].mean(),Pa[s].mean()
        print(f"    {lo:.2f}-{hi:.2f} {d:13.2e} {a_:13.2e} {a_/max(d,1e-30):8.2f}"
              + ("   <-- his 5-10 s" if (lo<=0.125<hi or lo<=0.15<hi) else ""))
