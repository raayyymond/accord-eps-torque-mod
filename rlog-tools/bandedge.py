"""Independent test of route-v102's leakage diagnosis, using MY Hann estimator only.
If the 25.5 Hz edge is clipping V102's line, WIDENING the band must lift V102 far more than V101."""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
import numpy as np, v102_xb_lib as L
L.ROUTES["97"]=L._mk("97","V9b-STOCK",gain=891,clamp=512,leverB=False,idcode=0,bits="stock")
L.ROUTES["96"]=L._mk("96","V102",gain=5346,clamp=3072,leverB=False,idcode=3,bits="v102")
ARMS=[("97","STOCK 1x"),("85","V100 4x"),("95","V101 8x"),("96","V102 6x")]
NUM=[("21.5-25.5",21.5,25.5),("20-28",20.,28.),("18-30",18.,30.)]
for nfft,hop,wl in ((100,50,"1.00 s"),(256,128,"2.56 s")):
    win=np.hanning(nfft); df=100.0/nfft
    print("\n=== window %s  (df = %.3f Hz, Hann main lobe = +-%.2f Hz) ==="%(wl,df,2*df))
    W={rt:L.windows(rt,nfft=nfft,hop=hop,engaged=True,keep_raw=True) for rt,_ in ARMS}
    print("  %-10s"%"arm"+"".join("%20s"%("SHAPE "+n) for n,_,_ in NUM)+"   lift 18-30 / 21.5-25.5")
    for rt,nm in ARMS:
        vals=[]
        for bn,lo,hi in NUM:
            sh=[]
            for r in W[rt]:
                b,s=r["_blk"],r["_sl"]
                d=L.bandrms(b["tq"][s],L.FS,2.5,4.5,win)
                if d>0: sh.append(L.bandrms(b["tq"][s],L.FS,lo,hi,win)/d)
            vals.append(np.median(sh))
        print("  %-10s"%nm+"".join("%20.3f"%v for v in vals)+"   %8.2fx"%(vals[2]/vals[0]))
