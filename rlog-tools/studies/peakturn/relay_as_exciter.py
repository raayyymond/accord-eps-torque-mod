import numpy as np
from scipy import signal
RATE_SCALE=4.7121
z=np.load('analysis-2020accord/_scratch/cache/r23/r23.npz',allow_pickle=True)
G=lambda k:np.asarray(z[k]).astype(float)
t,ang,rate,v,tq,cmd,lat=[G(k) for k in ('t','ang','cs_rate','cs_v','cs_tq','co_tqcan','cc_lat')]
wire=G('ab_mt'); wt=G('ab_t1ab')
raw=wire*1.6                       # |gp-0x6abc| in raw counts
THR=1800/12.0                      # V112 relay saturation threshold = 150 ct = 31.8 deg/s
print("WAS THE COULOMB RELAY SWITCHING DURING THE PEAK-TURN EVENT?")
print("  V112 knee 1800 -> relay saturates above |gp-0x6abc| = %.0f ct = %.1f deg/s\n"%(THR,THR/RATE_SCALE))
w=(wt>=444.0)&(wt<=449.5)
print("   t        raw |6abc|   deg/s   SATURATED?")
for i in np.where(w)[0]:
    print("  %7.2f     %6.0f    %6.1f      %s"%(wt[i],raw[i],raw[i]/RATE_SCALE,"YES" if raw[i]>=THR else ""))
sub=raw[w]
print("\n  during the event: n=%d  duty(saturated) = %.4f   p50 %.0f  max %.0f ct"
      %(len(sub),np.mean(sub>=THR),np.median(sub),sub.max()))
eng=(np.interp(wt,t,lat)>0.9)
print("  route-23 engaged baseline duty = %.4f"%np.mean(raw[eng]>=THR))
print("  => the event's relay duty is %.1fx the route baseline"
      %(np.mean(sub>=THR)/max(np.mean(raw[eng]>=THR),1e-9)))

print("\nDOES RELAY SWITCHING PREDICT THE 6-9 Hz LINE?  (all engaged 1.28 s windows, r22+r23)")
rows=[]
for r in ('22','23'):
    zz=np.load('analysis-2020accord/_scratch/cache/r%s/r%s.npz'%(r,r),allow_pickle=True)
    g=lambda k:np.asarray(zz[k]).astype(float)
    tt,rr,ll=g('t'),g('cs_rate'),g('cc_lat')
    ww=g('ab_mt')*1.6; wtt=g('ab_t1ab')
    satw=(ww>=THR).astype(float)
    sat=np.interp(tt,wtt,satw)
    for a in range(0,len(tt)-128,64):
        sl=slice(a,a+128)
        if ll[sl].mean()<0.99: continue
        f,P=signal.welch(rr[sl]-np.mean(rr[sl]),100.0,nperseg=128,noverlap=64)
        b=(f>=6)&(f<=9)
        rows.append((np.mean(sat[sl]),np.sqrt(np.sum(P[b])*(f[1]-f[0]))))
R=np.array(rows)
print("  relay duty in window   n     6-9 Hz RATE rms p50   p90    max")
for lo,hi in [(0,0.01),(0.01,0.1),(0.1,0.3),(0.3,0.6),(0.6,1.01)]:
    s=(R[:,0]>=lo)&(R[:,0]<hi)
    if s.sum()>=8:
        print("     %.2f-%.2f        %5d      %8.2f  %6.2f %6.2f"
              %(lo,hi,s.sum(),np.percentile(R[s,1],50),np.percentile(R[s,1],90),R[s,1].max()))
ok=R[:,0]>0
print("  corr(relay duty, 6-9 Hz rate rms) = %.3f  (n=%d windows)"%(np.corrcoef(R[:,0],R[:,1])[0,1],len(R)))
