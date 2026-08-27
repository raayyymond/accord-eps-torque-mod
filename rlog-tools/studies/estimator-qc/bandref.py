"""Is the 'TRUE' long-FFT band power a valid reference, or is it LEAKAGE-CONTAMINATED?
route-v102 measures Hann/true = 0.551 on STOCK and reads it as 'the Hann estimator loses 45%'.
A boxcar long FFT has -13 dB sidelobes decaying as 1/f, so a run with large low-frequency content
leaks into 21.5-25.5 Hz.  Compare FOUR references on the SAME gap-free engaged samples."""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
import numpy as np, v102_xb_lib as L
L.ROUTES["97"]=L._mk("97","V9b-STOCK",gain=891,clamp=512,leverB=False,idcode=0,bits="stock")
L.ROUTES["96"]=L._mk("96","V102",gain=5346,clamp=3072,leverB=False,idcode=3,bits="v102")
ARMS=[("97","STOCK 1x"),("85","V100 4x"),("95","V101 8x"),("96","V102 6x")]
LO,HI=21.5,25.5

def bp_fft(x, win=None, detrend=True):
    """Band POWER over one contiguous run.  win=None -> BOXCAR (what a naive long FFT does)."""
    x=np.asarray(x,float); n=len(x)
    if detrend:
        r=np.arange(n,dtype=float); c=np.polyfit(r,x,1); x=x-(c[0]*r+c[1])
    w=np.ones(n) if win is None else np.hanning(n)
    y=x*w; scale=np.mean(w**2)
    X=np.fft.rfft(y); f=np.fft.rfftfreq(n,1/L.FS)
    p=(np.abs(X)**2)*2.0/(n**2)/scale
    p[0]/=2.0
    if n%2==0: p[-1]/=2.0
    return float(p[(f>=LO)&(f<HI)].sum())

print("Band POWER 21.5-25.5 Hz on `tq`, pooled over contiguous engaged runs >= 20 s")
print("%-11s %5s %12s %12s %12s %12s   %s"%("arm","runs","BOXCAR-noDT","BOXCAR+DT","HANN long","Hann 1s mean","1s/boxcar-noDT"))
for rt,nm in ARMS:
    runs=[]
    for blk in L.all_blocks(rt):
        eng=blk["cc_lat"]>0.5
        idx=np.flatnonzero(eng)
        if not len(idx): continue
        brk=np.flatnonzero(np.diff(idx)!=1)
        for a,b in zip([0]+list(brk+1),list(brk+1)+[len(idx)]):
            if b-a>=2000: runs.append(blk["tq"][idx[a]:idx[b-1]+1])
    if not runs: print("  %-11s no run >= 20 s"%nm); continue
    bnd,bd,hl,h1=[],[],[],[]
    w1=np.hanning(100)
    for x in runs:
        bnd.append(bp_fft(x,None,False)); bd.append(bp_fft(x,None,True)); hl.append(bp_fft(x,"h",True))
        ws=[L.bandrms(x[i:i+100],L.FS,LO,HI,w1)**2 for i in range(0,len(x)-100+1,50)]
        h1.append(np.mean(ws))
    m=lambda v: float(np.mean(v))
    print("  %-11s %5d %12.2f %12.2f %12.2f %12.2f   %8.3f"%(nm,len(runs),m(bnd),m(bd),m(hl),m(h1),m(h1)/m(bnd)))
print("\n  BOXCAR-noDT = a naive long FFT (no window, no detrend) -- the likely 'true' reference")
print("  HANN long   = same samples, Hann-windowed: the LEAKAGE-FREE reference")
print("  If BOXCAR-noDT >> HANN long, the 'true' value is leakage, not signal.")
