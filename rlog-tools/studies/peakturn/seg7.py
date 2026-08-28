import numpy as np
z=np.load('analysis-2020accord/_scratch/cache/r23/r23.npz',allow_pickle=True)
G=lambda k:np.asarray(z[k]).astype(float)
t=G('t');ang=G('ang');rate=G('cs_rate');v=G('cs_v');tq=G('cs_tq');cmd=G('co_tqcan')
lat=G('cc_lat');seg=G('seg');probe=G('ab_mt') if 'ab_mt' in z.files else None
m7=(seg==7)
print("SEGMENT 7: t %.1f..%.1f s  n=%d  v %.1f-%.1f m/s  engaged %.3f"
      %(t[m7].min(),t[m7].max(),m7.sum(),v[m7].min(),v[m7].max(),lat[m7].mean()))
print("\nSECOND-BY-SECOND, t=455..480  (your 21:46:48 should be t~468 if seg7 = 21:46:00-21:47:00)")
print("  t_rel  |ang| deg   rate p95  rate rms   |cmd| p95   |tq| p50   v m/s")
for s in range(455,481):
    w=m7&(t>=s)&(t<s+1)
    if w.sum()<10: continue
    r=np.abs(rate[w])
    # narrowband content: rms of the rate after removing a 0.5 s moving average
    print("  %5d   %7.1f   %7.1f   %7.2f   %8.0f   %7.0f   %5.1f"
          %(s,np.abs(ang[w]).mean(),np.percentile(r,95),
            np.std(rate[w]-np.convolve(np.pad(rate[w],(2,2),mode='edge'),np.ones(5)/5,'valid')),
            np.percentile(np.abs(cmd[w]),95),np.median(np.abs(tq[w])),v[w].mean()))
print("\nHARD-CURVE PEAKS IN SEGMENT 7 (|ang| local maxima > 50 deg):")
a=np.abs(ang); idx=np.where(m7)[0]
for i in idx[1:-1]:
    if a[i]>50 and a[i]>=a[i-1] and a[i]>a[i+1] and a[i]==np.max(a[max(i-150,0):i+150]):
        print("   t=%.1f s  |ang| %.1f deg  v %.1f m/s  |cmd| %.0f"%(t[i],a[i],v[i],abs(cmd[i])))
