"""Does CONCATENATING non-contiguous engaged samples inflate the 'true' long-FFT band power?
Each splice is a step discontinuity => broadband leakage, worst for the arm with the LEAST
real content in the band.  That is STOCK."""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
import numpy as np, v102_xb_lib as L
L.ROUTES["97"]=L._mk("97","V9b-STOCK",gain=891,clamp=512,leverB=False,idcode=0,bits="stock")
L.ROUTES["96"]=L._mk("96","V102",gain=5346,clamp=3072,leverB=False,idcode=3,bits="v102")
ARMS=[("97","STOCK 1x"),("85","V100 4x"),("95","V101 8x"),("96","V102 6x")]
LO,HI=21.5,25.5
def bp(x):
    x=np.asarray(x,float); n=len(x)
    X=np.fft.rfft(x-x.mean()); f=np.fft.rfftfreq(n,1/L.FS)
    p=(np.abs(X)**2)*2.0/(n**2); p[0]/=2.0
    if n%2==0: p[-1]/=2.0
    return float(p[(f>=LO)&(f<HI)].sum())
print("%-11s %6s %8s %14s %14s %10s"%("arm","runs","splices","CONCAT (1 FFT)","per-run mean","inflation"))
for rt,nm in ARMS:
    runs=[]
    for blk in L.all_blocks(rt):
        eng=blk["cc_lat"]>0.5; idx=np.flatnonzero(eng)
        if not len(idx): continue
        brk=np.flatnonzero(np.diff(idx)!=1)
        for a,b in zip([0]+list(brk+1),list(brk+1)+[len(idx)]):
            if b-a>=500: runs.append(np.asarray(blk["tq"],float)[idx[a]:idx[b-1]+1])
    if len(runs)<2: continue
    cat=bp(np.concatenate(runs))
    per=float(np.mean([bp(r) for r in runs]))
    steps=[abs(runs[i+1][0]-runs[i][-1]) for i in range(len(runs)-1)]
    print("  %-11s %6d %8d %14.2f %14.2f %10.3fx   (median splice step %.0f ct)"%(
        nm,len(runs),len(runs)-1,cat,per,cat/per,np.median(steps)))
