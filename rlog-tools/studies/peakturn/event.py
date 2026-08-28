import numpy as np
from scipy import signal
z=np.load('analysis-2020accord/_scratch/cache/r23/r23.npz',allow_pickle=True)
G=lambda k:np.asarray(z[k]).astype(float)
t=G('t');ang=G('ang');rate=G('cs_rate');v=G('cs_v');tq=G('cs_tq');cmd=G('co_tqcan')
lat=G('cc_lat');mt=G('ab_mt');abt=G('ab_t1ab')
W=(t>=440)&(t<=458)
print("THE EVENT WINDOW t=440..458 s  (hard curve peaks at 448.6, |ang| 99.8 deg)")
print("  t      ang     rate    cmd    drvTq   v     |  ang is SIGNED; a fixed oscillation shows as")
print("                                              |  a steady ripple on rate at constant ang")
idx=np.where(W)[0]
for i in idx[::20]:
    print("  %6.2f %7.1f %7.1f %6.0f %7.0f %5.1f" % (t[i],ang[i],rate[i],cmd[i],tq[i],v[i]))

print("\nSPECTRUM OF THE STEERING RATE, 4 s windows across the curve")
for lo in (440,444,446,448,450,452,454):
    w=(t>=lo)&(t<lo+4)
    x=rate[w]-np.mean(rate[w])
    if len(x)<200: continue
    f,P=signal.welch(x,100.0,nperseg=256,noverlap=192)
    b=(f>=3)&(f<=45)
    pk=f[b][np.argmax(P[b])]
    tot=np.sum(P[(f>=1)&(f<=45)])
    # prominence: peak power vs median in band
    prom=P[b].max()/np.median(P[b])
    print("   t=%3d-%3d s  |ang| %5.1f  peak %5.2f Hz  prominence %5.1f  band rms %6.2f deg/s"
          %(lo,lo+4,np.abs(ang[w]).mean(),pk,prom,np.sqrt(tot*(f[1]-f[0]))))

print("\nZOOM: the 2 s straddling the peak, raw 100 Hz rate samples")
w=(t>=447.6)&(t<=449.6)
r=rate[w]; a=ang[w]; tt=t[w]
print("   " + " ".join("%.0f"%x for x in r[:60]))
x=r-np.mean(r)
f,P=signal.welch(x,100.0,nperseg=128,noverlap=96)
b=(f>=3)&(f<=45)
print("   peak %.2f Hz   prominence %.1f   rms %.2f deg/s   |ang| mean %.1f"
      %(f[b][np.argmax(P[b])],P[b].max()/np.median(P[b]),np.std(x),np.abs(a).mean()))

print("\nIS IT IN THE COMMAND TOO?  (a LOOP oscillation appears in both; a plant one only in rate)")
for lab,sig in (("rate",rate),("LKAS cmd",cmd),("driver tq",tq),("427 tap",mt)):
    w=(t>=446)&(t<=452)
    x=sig[w].astype(float); x=x-np.mean(x)
    f,P=signal.welch(x,100.0,nperseg=256,noverlap=192)
    b=(f>=3)&(f<=45)
    print("   %-10s peak %5.2f Hz  prominence %5.1f  rms %8.2f"
          %(lab,f[b][np.argmax(P[b])],P[b].max()/np.median(P[b]),np.std(x)))
