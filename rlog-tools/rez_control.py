"""POSITIVE CONTROL for the stock Re(Z): re-run MY pipeline on route 77 and check it reproduces
`v92_rez.log`'s published -3375.2 at 6-9 Hz.  If it does, my stock number is on the record's scale."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
import decode_v90_probe as P
CACHE = Path(r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord")
DEG2RAD = np.pi/180.0
RNG = np.random.default_rng(97_2026)
PUB = {"2-4":-1269.2,"4-6":-1418.5,"6-9":-3375.2,"9-12":-4593.1,"12-16":-3858.1,
       "16-18":-1610.7,"18-22":-652.5,"22-26":-267.8,"26-31":232.9,"31-35":772.9}
BANDS=[("2-4",2.,4.),("4-6",4.,6.),("6-9",6.,9.),("9-12",9.,12.),("12-16",12.,16.),
       ("16-18",16.,18.),("18-22",18.,22.),("22-26",22.,26.),("26-31",26.,31.),("31-35",31.,35.)]
z = np.load(CACHE/"_cache_r77"/"r77.npz", allow_pickle=True)
t=np.asarray(z["t"],float); tq=np.asarray(z["tq"],float)
rate=np.asarray(z["rate_f"],float)*DEG2RAD
lat=np.asarray(z["cc_lat"],float)>0.5
press=np.asarray(z["cs_press"],float)>0.5
v=np.abs(np.asarray(z["cs_v"],float))
mask=lat&(~press)&(v>0.5)
fs=1.0/float(np.median(np.diff(t)))
W=P._wins(mask,t,P.NW_Z,P.HOP_Z,(rate,tq,v))
print("route 77, fs %.2f Hz, mask engaged&hands-off&moving: %d frames = %.1f s"%(fs,mask.sum(),mask.sum()/fs))
print("  %d windows  (v92_rez.log published 221)"%len(W))
print("  %-8s %11s %11s %9s %8s   %s"%("band","MINE","PUBLISHED","delta%","coh2","CI(boot 200)"))
pairs=[(w[0],w[1]) for w in W]
for bn,lo,hi in BANDS:
    r=P._band_transfer(pairs,fs,P.NW_Z,[(bn,lo,hi)])[bn]
    bs=[P._band_transfer([pairs[k] for k in RNG.integers(0,len(pairs),len(pairs))],fs,P.NW_Z,[(bn,lo,hi)])[bn]["re_over_sxx"] for _ in range(200)]
    blo,bhi=np.percentile(bs,[2.5,97.5])
    d=100*(r["re_over_sxx"]-PUB[bn])/abs(PUB[bn])
    print("  %-8s %11.1f %11.1f %8.2f%% %8.3f   [%7.0f,%7.0f]"%(bn,r["re_over_sxx"],PUB[bn],d,r["coh2"],blo,bhi))
