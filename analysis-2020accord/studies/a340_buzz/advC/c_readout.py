import sys,glob,os
sys.path.insert(0,'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/_scratch')
import numpy as np
from scipy import signal
from a340_buzz_lib import load,segs,FS
R='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/_scratch/cache/'
bb,ba=signal.butter(4,[8/50,20/50],'band')
def rms1s(x): return np.sqrt(np.convolve(x*x,np.ones(100)/100,'same'))
def run(dirs,lab):
    out={}
    for d in dirs:
        for s,p in segs(d):
            try: D=load(p)
            except Exception as e: continue
            if len(D["rate"])<300: continue
            r=signal.filtfilt(bb,ba,D["rate"]); q=rms1s(r)
            for name,lo,hi in (('1-8',1,8),('10-20',10,20),('>20',20,40)):
                m=D['req']&~D['pressed']&(D['v']>=lo)&(D['v']<hi)
                out.setdefault(name,[]).append(q[m])
    for name,l in out.items():
        a=np.concatenate(l)
        if len(a)<500: print(f'{lab:22s} {name:6s} n={len(a)/100:.0f}s too few'); continue
        # 2-s runs above 4
        print(f'{lab:22s} {name:6s} n={len(a)/100:6.0f}s p50 {np.percentile(a,50):5.2f} p90 {np.percentile(a,90):5.2f} p99 {np.percentile(a,99):5.2f} frac>4 {100*(a>4).mean():5.1f}%')
run([R+'a340_user55'],'A340 REV3 (buzz)')
run([R+'a340_user5d'],'A340 stock')
run(sorted(glob.glob(R+'a160_v300_*')),'A160 V300 (6 routes)')
run([R+'a160_b8_all',R+'a160_b9_all'],'A160 b8/b9')
