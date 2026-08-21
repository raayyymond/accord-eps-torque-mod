"""Do MY reported V101 band ratios survive splitting on hands-ON?  I reported 22-26 = 29.85x stock."""
import sys
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools")
import numpy as np, v102_xb_lib as L
L.ROUTES["97"]=L._mk("97","V9b-STOCK",gain=891,clamp=512,leverB=False,idcode=0,bits="stock")
L.ROUTES["96"]=L._mk("96","V102",gain=5346,clamp=3072,leverB=False,idcode=3,bits="v102")
ARMS=[("97","STOCK"),("85","V100"),("95","V101"),("96","V102")]
W={}
for rt,_ in ARMS:
    r=L.windows(rt,nfft=256,hop=128,engaged=True,keep_raw=True)
    for rec in r:
        b,s=rec["_blk"],rec["_sl"]
        rec["press"]=float(np.mean(b["cs_press"][s]>0.5))
        rec["dtq"]=float(np.median(np.abs(b["tq"][s])))
    W[rt]=r
print("arm / subset / n / mean press / |tq| p50 / 6-9 Hz p50 / 22-26 Hz p50")
for rt,nm in ARMS:
    for tag,sub in (("ALL",W[rt]),
                    ("hands-OFF",[r for r in W[rt] if r["press"]<0.02]),
                    ("hands-ON ",[r for r in W[rt] if r["press"]>0.98])):
        if len(sub)<5: print("  %-8s %-10s n=%d  -- too few"%(nm,tag,len(sub))); continue
        print("  %-8s %-10s n=%4d  press %.3f  |tq|p50 %7.1f   6-9 %8.1f   22-26 %8.1f"%(
            nm,tag,len(sub),np.mean([r["press"] for r in sub]),np.median([r["dtq"] for r in sub]),
            np.median([r["tq|6-9"] for r in sub]),np.median([r["tq|22-26"] for r in sub])))
print("\n=== ratio to STOCK, HANDS-OFF WINDOWS ONLY (press<0.02), matched speed x rate ===")
import stock_r97_resonance as R
A=[r for r in W["97"] if r["press"]<0.02]
for rt,nm in ARMS:
    if rt=="97": continue
    B=[r for r in W[rt] if r["press"]<0.02]
    for bn in ("6-9","18-22","22-26","32-38"):
        m=R._matched_boot(A,B,"tq|"+bn)
        print("   %-6s %-7s %s"%(nm,bn,("%8.2fx [%6.2f,%6.2f] (%d cells)"%(m["r"],m["lo"],m["hi"],m["cells"])) if m else "no matched cell"))
