r"""ITEM 7 -- CHARACTERISE THE ONE THING THAT SEPARATES, IN WORDS THE OPERATOR CAN JUDGE.

No audible band separates stock from 6x, so item 7 cannot be delivered on the acoustic channel.
What CAN be delivered is a description of the 21-28 Hz mode, which separates 1x from 6x by 21x in
level -- expressed as speed, steering rate, and how much of his driving it occupies.  He is the
arbiter: this is phrased so he can confirm or reject it from the seat.
"""
import os, sys, numpy as np
from scipy import signal
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import acoustic_lib as A
try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
FS = 101.14792783296437
RATE_FIX = 1.0 / 0.7996          # rate_f = 0.7996 x true deg/s

def env(x, lo, hi):
    sos = signal.butter(4, [lo/(FS/2), hi/(FS/2)], btype='band', output='sos')
    return np.abs(signal.hilbert(signal.sosfiltfilt(sos, np.nan_to_num(x-np.nanmean(x)))))

print("="*118)
print("THE 21-28 Hz MODE, CHARACTERISED -- the only quantity that separates stock from 6x")
print("="*118)
print("\nA. HOW MUCH OF ENGAGED DRIVING IS IT PRESENT FOR?  (burst duty, threshold = stock p95)")
R97 = A.load('r97'); e97 = env(R97['rate_f'], 21, 28)
m97 = R97['can_eng'] & (R97['can_v'] < 16)
THR = np.percentile(e97[m97], 95)
print("%-6s %-9s %8s" % ('route','build','gain') + "".join("%12s"%s for s in
      ['<16 km/h','16-40','40-80','80+','ALL eng']))
for t in ['r97','r85','r96','r9e','ra4','r95']:
    R = A.load(t); e = env(R['rate_f'], 21, 28); row=[]
    for lo,hi in [(0,16),(16,40),(40,80),(80,200),(0,200)]:
        m = R['can_eng'] & (R['can_v']>=lo) & (R['can_v']<hi)
        row.append((e[m]>=THR).mean() if m.sum()>50 else np.nan)
    print("%-6s %-9s %8.0fx"%(t,A.NAMES[t],A.GAIN[t]) + "".join(
        ("%12.3f"%x) if np.isfinite(x) else "%12s"%'thin' for x in row))

print("\nB. DOES IT GET STRONGER WITH SPEED, OR WITH HOW FAST HE IS TURNING?")
print("   median 21-28 Hz envelope level, engaged, by |steering rate| (true deg/s):")
edges=[0,5,15,40,100,1000]
print("%-6s %-9s"%('route','build') + "".join("%13s"%("%g-%g deg/s"%(edges[i],edges[i+1]))
      for i in range(len(edges)-1)))
for t in ['r97','r96','r9e','ra4']:
    R = A.load(t); e = env(R['rate_f'], 21, 28)
    rr = np.abs(R['rate_f'])*RATE_FIX
    m = R['can_eng'] & (R['can_v']<16); row=[]
    for i in range(len(edges)-1):
        s = m & (rr>=edges[i]) & (rr<edges[i+1])
        row.append(np.median(e[s]) if s.sum()>50 else np.nan)
    print("%-6s %-9s"%(t,A.NAMES[t]) + "".join(("%13.2f"%x) if np.isfinite(x) else "%13s"%'thin'
          for x in row))
print("   and by SPEED, engaged:")
sp=[0,16,40,80,200]
print("%-6s %-9s"%('route','build') + "".join("%13s"%("%g-%g km/h"%(sp[i],sp[i+1]))
      for i in range(len(sp)-1)))
for t in ['r97','r96','r9e','ra4']:
    R = A.load(t); e = env(R['rate_f'], 21, 28); row=[]
    for i in range(len(sp)-1):
        s = R['can_eng'] & (R['can_v']>=sp[i]) & (R['can_v']<sp[i+1])
        row.append(np.median(e[s]) if s.sum()>50 else np.nan)
    print("%-6s %-9s"%(t,A.NAMES[t]) + "".join(("%13.2f"%x) if np.isfinite(x) else "%13s"%'thin'
          for x in row))

print("\nC. IS IT CONTINUOUS OR IN-AND-OUT?  burst-length distribution, engaged <16 km/h, 6x only")
print("%-6s %-9s %10s %10s %10s %10s %10s"%('route','build','n bursts','p50 s','p90 s','max s','gap p50 s'))
for t in ['r97','r96','r9e','ra4']:
    R = A.load(t); e = env(R['rate_f'], 21, 28)
    m = R['can_eng'] & (R['can_v']<16)
    lab = (e>=THR) & m
    i = np.flatnonzero(np.diff(lab.astype(np.int8))!=0)+1
    b = np.concatenate(([0],i,[len(lab)]))
    L=[(b[k+1]-b[k])/FS for k in range(len(b)-1) if lab[b[k]]]
    G=[(b[k+1]-b[k])/FS for k in range(len(b)-1) if (not lab[b[k]]) and m[b[k]]]
    L=[x for x in L if x>=0.1]
    if not L: print("%-6s %-9s   none"%(t,A.NAMES[t])); continue
    print("%-6s %-9s %10d %10.2f %10.2f %10.2f %10.2f"%(t,A.NAMES[t],len(L),
          np.percentile(L,50),np.percentile(L,90),max(L),np.percentile(G,50) if G else np.nan))
