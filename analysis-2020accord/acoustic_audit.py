"""ACOUSTIC AUDIT -- independent verification of the audio caches before any analysis.

Checks, per route:  frame-rate / gaps / coverage / clipping / timebase alignment against the
CAN cache, unit sanity on v_rear, and the engaged & manual <16 km/h census.
NO CONTRAST IS COMPUTED HERE.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gate2_boost_lib as L
try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
KPH = 3.6
TAGS = ['r97', 'r85', 'r96', 'r9e', 'ra4']
NAMES = {'r97':'STOCK 1x','r85':'V100 4x','r96':'V102 6x','r9e':'V103 6x','ra4':'V104 6x','r95':'V101 8x'}
HOP_S = 256/16000.0

print("="*120)
print("ACOUSTIC EXTRACTION AUDIT  (independent re-read of _cache_*/*_audio.npz)")
print("="*120)
rows=[]
for t in TAGS:
    fa = os.path.join(HERE, '_cache_%s'%t, '%s_audio.npz'%t)
    if not os.path.exists(fa):
        print("  %-5s  NO AUDIO CACHE"%t); continue
    a = np.load(fa)
    d = L.load(t)
    sr,nfft,hop,nb,ns,nc = a['meta']
    ta = a['t'].astype(float)
    dt = np.diff(ta)
    # a "gap" = a frame step more than 2x the nominal hop
    gap = dt > 2*HOP_S
    gap_s = dt[gap].sum()
    tc = d['t'].astype(float)
    v_ms = d['v_rear'].astype(float)
    # UNIT CHECK
    rows.append((t,sr,nfft,hop,nb,ns,nc,ta,dt,gap,gap_s,tc,v_ms,d,a))

print("\n%-6s %-9s %8s %12s %10s %8s %9s %9s %10s %9s" %
      ('route','build','blocks','PCM samples','audio s','clip','frames','fr rate','n gaps','gap s'))
for (t,sr,nfft,hop,nb,ns,nc,ta,dt,gap,gap_s,tc,v_ms,d,a) in rows:
    print("%-6s %-9s %8d %12d %10.1f %8d %9d %9.3f %10d %9.1f" %
          (t,NAMES[t],nb,ns,ns/sr,nc,len(ta),1/np.median(dt),gap.sum(),gap_s))

print("\nTIMEBASE + UNIT CHECKS")
print("%-6s %-24s %-24s %10s %10s %10s" %
      ('route','audio t span (s)','CAN t span (s)','v_rear p50','x3.6 kph','cs_v p50'))
for (t,sr,nfft,hop,nb,ns,nc,ta,dt,gap,gap_s,tc,v_ms,d,a) in rows:
    print("%-6s %-24s %-24s %10.3f %10.2f %10.3f" %
          (t, "%.2f .. %.2f"%(ta[0],ta[-1]), "%.2f .. %.2f"%(tc[0],tc[-1]),
           np.median(v_ms), np.median(v_ms)*KPH, np.median(d['cs_v'].astype(float))))
print("  v_rear p50 ~ 15-25 => m/s (60-90 km/h).  If it read ~60-90 it would already be km/h.")

print("\nCENSUS -- engaged (cc_lat>0.5) and manual, by speed stratum, in ACOUSTIC FRAMES (s)")
STRATA=[(0,16),(16,40),(40,80),(80,200),(0,200)]
hdr = "%-6s %-9s"%('route','build') + "".join("%13s"%("eng %g-%g"%s) for s in STRATA)
print(hdr)
CEN={}
for (t,sr,nfft,hop,nb,ns,nc,ta,dt,gap,gap_s,tc,v_ms,d,a) in rows:
    eng = np.interp(ta, tc, (d['cc_lat'].astype(float)>0.5).astype(float))>0.5
    v = np.interp(ta, tc, v_ms)*KPH
    CEN[t]=dict(eng=eng,v=v)
    print("%-6s %-9s"%(t,NAMES[t]) + "".join("%13.1f"%(((eng)&(v>=lo)&(v<hi)).sum()*HOP_S) for lo,hi in STRATA))
print(hdr.replace('eng','man'))
for (t,sr,nfft,hop,nb,ns,nc,ta,dt,gap,gap_s,tc,v_ms,d,a) in rows:
    eng=CEN[t]['eng']; v=CEN[t]['v']
    print("%-6s %-9s"%(t,NAMES[t]) + "".join("%13.1f"%(((~eng)&(v>=lo)&(v<hi)).sum()*HOP_S) for lo,hi in STRATA))

print("\nSTATIONARY FRACTION of the MANUAL arm (v < 1 km/h) -- ra4's manual arm is ~74%% parked")
for t in CEN:
    m=~CEN[t]['eng']; v=CEN[t]['v']
    lo=m&(v<16)
    print("   %-5s manual <16 km/h: %6.1f s, of which parked (v<1) %6.1f s = %.1f%%"
          %(t, lo.sum()*HOP_S, (lo&(v<1)).sum()*HOP_S, 100*(lo&(v<1)).sum()/max(lo.sum(),1)))

print("\nSPEED DISTRIBUTION inside the <16 km/h ENGAGED stratum (km/h percentiles)")
print("%-6s %8s %8s %8s %8s %8s"%('route','p10','p25','p50','p75','p90'))
for t in CEN:
    m=CEN[t]['eng']&(CEN[t]['v']<16)
    if m.sum()<10: print("%-6s  too few"%t); continue
    q=np.percentile(CEN[t]['v'][m],[10,25,50,75,90])
    print("%-6s %8.2f %8.2f %8.2f %8.2f %8.2f"%(t,*q))
